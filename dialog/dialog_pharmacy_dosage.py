# 藥局配藥秤重 2026.08.22
# -*- coding: UTF-8 -*-
#
# 沿革
# ----
# 2026.08.19  worker 執行緒不再直接呼叫 GUI 與資料庫，改用 signal 回主執行緒。
#             （原本 _get_weight() 在背景執行緒裡呼叫 accept()、setEnabled()
#              與 save_pres_extend()，是配藥時畫面反白凍住的根因）
#
# 2026.08.21  兩個「秤對了卻沒記錄到」的漏洞：
#
#   一、_closing 把已完成的訊號吃掉
#       worker 發出 dosage_ready_signal 之後、主執行緒還沒處理到之前，
#       若對話框先因任何原因進入關閉流程（按取消、按 Esc、視窗被關），
#       _on_dosage_ready() 就被 _closing 擋掉，那一味藥秤是對的，
#       但「調劑完成」沒有寫進資料庫。
#
#       改法：把「寫入」從訊號處理中獨立出來成 _commit_dosage()，
#       由 _on_dosage_ready() 和 close_all() 兩條路徑共同呼叫，
#       用 _saved 旗標保證只寫一次。worker 一旦判定合格就先設
#       _dosage_ready，之後不管走哪條路關閉，都會補上這一筆。
#
#   二、序列埠緩衝區積壓，判定用的是過期的秤值
#       原本迴圈每 10ms 只 readline() 一行，但電子秤送得比這更快時，
#       緩衝區會越積越多，拿到的是幾秒前的重量——穩定判定和誤差比對
#       全建立在過期資料上。30 味藥連續配下來，越後面越嚴重。
#
#       改法：每一輪把緩衝區抽乾，只取最新一行。
#       同時穩定判定從「數到 scale_time*10 次」改成「連續穩定
#       scale_time 秒」——前者會隨電子秤的送出頻率浮動，送得越快
#       就越早判定為穩定（提早通過），後者不會。
#
#       另外 __init__ 的 self.ser.read(10) 可能停在某一行中間，
#       之後第一次 readline() 會拿到半行殘料，因此開場先 reset。
#
# 2026.08.22  視窗標題加上病人姓名。
#             主程式已修好「配到一半名單跳走」的問題，但配錯人的代價
#             太高，值得讓藥師自己也能發現：萬一以後又有任何原因讓
#             選取列跳掉，抬頭就會看到名字不對。

import datetime
import sys
import threading
import time

import serial
from pygame import mixer
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox

from libs import (
    case_utils,
    number_utils,
    prescript_utils,
    string_utils,
    system_utils,
    ui_utils,
)

# 允許誤差（公克）
DOSAGE_TOLERANCE = 0.1

# worker 迴圈的輪詢間隔（秒）
POLL_INTERVAL = 0.01

# 關閉時等待 worker 收工的時間（秒）
THREAD_JOIN_TIMEOUT = 2.0

# 除錯記錄檔。確認穩定後可以把 DEBUG_LOG 設成 None 關掉。
DEBUG_LOG = "pharmacy_debug.log"


def _log(message):
    """永不拋例外的記錄。pythonw.exe 下 sys.stdout 是 None，print 會炸。"""
    if not DEBUG_LOG:
        return

    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as log_file:
            log_file.write(
                f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S.%f} {message}\n"
            )
    except Exception:
        pass


# 配藥秤重
class DialogPharmacyDosage(QtWidgets.QDialog):
    # 每次讀到重量（worker → 主執行緒）
    update_dosage_signal = QtCore.pyqtSignal(str)
    # 重量穩定且誤差合格（worker → 主執行緒）
    dosage_ready_signal = QtCore.pyqtSignal()
    # 序列埠異常（worker → 主執行緒）
    scale_error_signal = QtCore.pyqtSignal(str)

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.prescript_key = args[2]
        self.medicine_key = args[3]
        self.medicine_code = args[4]
        self.medicine_set = args[5]
        self.scale_time = args[6]
        self.qrcode = ""

        self.ui = None
        self.ser = None
        self.serial_thread = None
        self.running = True  # 用於控制執行緒的旗標
        self.current_weight = 0
        self.total_dosage = 0
        self.case_key = None
        self._closing = False  # 避免 close_all() 重入
        self._dosage_ready = False  # worker 判定合格（可能還沒寫入）
        self._saved = False  # 已寫入資料庫，保證只寫一次

        # mixer.init() 失敗也必須有這個屬性，否則主執行緒的 slot 會炸
        self.sound_played = False
        self.sound_enabled = False
        try:
            mixer.init()
            mixer.music.load("./icq.mp3")
            self.sound_enabled = True
        except Exception:
            pass

        self._set_ui()
        self._set_signal()
        self._set_data()

        if not self._open_serial():
            return

        _log(f"open prescript={self.prescript_key} target={self.total_dosage}")
        self._start_worker()

    # ------------------------------------------------------------------
    # 序列埠
    # ------------------------------------------------------------------
    def _get_com_port(self):
        com = self.system_settings.field("電子秤連接埠")
        com_port = None

        if sys.platform == "win32":
            com_port = f"COM{com}"
        elif sys.platform == "linux":
            com_port = f"/dev/ttyUSB{com}"

        return com_port

    def _open_serial(self):
        """開啟電子秤。失敗時排程關閉對話框並回傳 False。"""
        com_port = self._get_com_port()

        try:
            self.ser = serial.Serial(
                port=com_port,  # 串口號
                baudrate=9600,  # 波特率，根據你的設備進行設定
                timeout=1,  # 讀取超時時間
            )
        except Exception as e:
            _log(f"open serial failed prescript={self.prescript_key}: {e}")
            self.ser = None

        if self.ser is None:
            self._show_scale_error()
            return False

        try:
            response = self.ser.read(10)
        except Exception:
            response = b""

        if len(response) == 0:
            _log(f"scale no response prescript={self.prescript_key}")
            self._show_scale_error()
            return False

        # read(10) 可能停在某一行中間，殘料會讓第一次 readline() 取到半行
        try:
            self.ser.reset_input_buffer()
        except Exception:
            pass

        return True

    def _show_scale_error(self, message=None):
        system_utils.show_message_box(
            QMessageBox.Critical,
            "電子秤有誤",
            message
            or "<h1>無法連線至電子秤，請檢查電子秤的電源是否開啟或連接線是否接妥。</h1>",
            "無法連接至電子秤.",
        )
        # exec_() 還沒開始，直接 reject() 沒有用，排到事件迴圈啟動後再關
        QtCore.QTimer.singleShot(0, self.reject)

    def _start_worker(self):
        self.serial_thread = threading.Thread(target=self._get_weight)
        self.serial_thread.daemon = True
        self.serial_thread.start()

    # 解構
    def __del__(self):
        self.close_all()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PHARMACY_DOSAGE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("確定")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")

        self._set_font_size()

    def _set_font_size(self):
        font_size = 18
        self.ui.setStyleSheet(
            f'font-family: "Microsoft JhengHei"; font-size: {font_size}pt;'
        )

        font_size = 96
        self.ui.label_medicine_name.setStyleSheet(
            f"font-size: {font_size}pt; font-weight: bold"
        )

        font_size = 64
        label_list = [
            self.ui.label_2,
            self.ui.label_3,
            self.ui.label_4,
            self.ui.label_5,
            self.ui.label_dosage,
            self.ui.label_current_dosage,
        ]
        for widget in label_list:
            widget.setStyleSheet(f"font-size: {font_size}pt;")

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.keyPressEvent = self.keyPressEvent

        # worker → 主執行緒。全部是預設的 AutoConnection，跨執行緒時
        # 自動變成 QueuedConnection，slot 一定在主執行緒執行。
        self.update_dosage_signal.connect(self._update_dosage_label)
        self.dosage_ready_signal.connect(self._on_dosage_ready)
        self.scale_error_signal.connect(self._on_scale_error)

    def keyPressEvent(self, event):
        # 秤重期間掃到的條碼一律忽略，避免誤觸 Enter 關閉對話框
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.qrcode = ""
            return

        self.qrcode += event.text()

    def _check_dosage_ok(self):
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        weight = abs(
            number_utils.get_float(self.total_dosage)
            - number_utils.get_float(self.current_weight)
        )
        if abs(round(weight, 1)) > DOSAGE_TOLERANCE:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "劑量錯誤",
                "<h1>劑量誤差超過0.1，請重新調整劑量。</h1>",
                "請再確認劑量是否正確.",
            )
            return

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        self.accept()

    def _set_data(self):
        sql = f"""
            SELECT * FROM medicine
            WHERE
                MedicineKey = {self.medicine_key}
        """
        medicine_rows = self.database.select_record(sql)
        if len(medicine_rows) <= 0:
            return

        medicine_row = medicine_rows[0]
        medicine_name = string_utils.xstr(medicine_row["MedicineName"])
        self.ui.label_medicine_name.setText(medicine_name)

        sql = f"""
            SELECT * FROM prescript
            WHERE
                PrescriptKey = {self.prescript_key}
        """
        prescript_rows = self.database.select_record(sql)
        if len(prescript_rows) <= 0:
            return

        prescript_row = prescript_rows[0]
        dosage = number_utils.get_float(prescript_row["Dosage"])
        self.case_key = prescript_row["CaseKey"]
        pres_days = case_utils.get_pres_days(
            self.database, self.case_key, self.medicine_set
        )
        self.total_dosage = round(number_utils.get_float(dosage * pres_days), 1)

        self.ui.label_dosage.setText(string_utils.xstr(self.total_dosage))
        self.ui.progressBar_scale.setMaximum(int(self.total_dosage * 100))
        self.ui.progressBar_scale.setValue(0)

        self._set_window_title(medicine_name)

    def _get_patient_name(self):
        """取得這張處方的病人姓名。查不到就回傳空字串，不影響配藥。"""
        if self.case_key in [None, ""]:
            return ""

        sql = f"""
            SELECT patient.Name FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                cases.CaseKey = {self.case_key}
        """
        try:
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                return string_utils.xstr(rows[0]["Name"])
        except Exception as e:
            _log(f"patient name failed case={self.case_key}: {e}")

        return ""

    def _set_window_title(self, medicine_name):
        """標題放病人姓名，讓藥師一眼就能確認配的是誰的藥"""
        patient_name = self._get_patient_name()
        if patient_name:
            self.setWindowTitle(f"{patient_name} — {medicine_name}")
        else:
            self.setWindowTitle(medicine_name)

    # ------------------------------------------------------------------
    # worker 執行緒：只讀序列埠，不碰 GUI、不碰資料庫
    # ------------------------------------------------------------------
    def _read_latest(self):
        """把緩衝區抽乾，只回傳最新一行。

        原本每輪只讀一行，電子秤送得比 100Hz 快時緩衝區會持續累積，
        取到的是幾秒前的重量。連續配藥時越後面越嚴重。
        """
        data = None

        while self.ser and self.ser.in_waiting:
            line = self.ser.readline().decode("utf-8", errors="ignore").strip()
            if line and "No." not in line:
                data = line

        return data

    def _get_weight(self):
        last_weight = None
        stable_since = None
        target = number_utils.get_float(self.total_dosage)

        while self.running:
            try:
                data = self._read_latest()
            except serial.SerialException as e:
                # 關閉對話框時主執行緒會 close() 這個 port，屬正常結束
                if self.running:
                    self.scale_error_signal.emit(str(e))
                break
            except Exception:
                time.sleep(POLL_INTERVAL)
                continue

            if data is None:
                time.sleep(POLL_INTERVAL)
                continue

            data = data.replace("g", "")

            # 自己算，不要回頭讀 self.current_weight ——
            # signal 是佇列傳遞，主執行緒還沒處理到，讀回來的是上一輪的值
            current_weight = number_utils.get_float(data)

            self.update_dosage_signal.emit(data)

            # 穩定判定改用時間基準。原本數固定次數，會隨電子秤的送出
            # 頻率浮動：送得越快就越早判定為穩定，等於提早通過。
            if last_weight is not None and current_weight == last_weight:
                if stable_since is None:
                    stable_since = time.monotonic()
                elif time.monotonic() - stable_since >= self.scale_time:
                    deviation = current_weight - target
                    if abs(round(deviation, 1)) <= DOSAGE_TOLERANCE:
                        # 先立旗標再發訊號：訊號萬一沒被處理到（對話框
                        # 同時被關閉），close_all() 會據此補寫
                        self._dosage_ready = True
                        self.running = False
                        _log(
                            f"stable prescript={self.prescript_key} "
                            f"weight={current_weight} target={target}"
                        )
                        self.dosage_ready_signal.emit()
                        break

                    stable_since = None
            else:
                stable_since = None

            last_weight = current_weight

            time.sleep(POLL_INTERVAL)

    # ------------------------------------------------------------------
    # 主執行緒：接收 worker 的通知
    # ------------------------------------------------------------------
    def _commit_dosage(self):
        """寫入調劑完成。唯一的寫入點，保證只寫一次。

        由兩條路徑呼叫：
          * _on_dosage_ready()：正常流程
          * close_all()：訊號還沒送達就關閉時的補救

        必須在主執行緒執行（資料庫連線與 GUI 共用），因此 __del__
        觸發時直接放棄——那時 Qt 物件多半已經在拆了。
        """
        if self._saved or not self._dosage_ready:
            return False

        if threading.current_thread() is not threading.main_thread():
            _log(f"commit skipped (not main thread) prescript={self.prescript_key}")
            return False

        self._saved = True
        self.save_pres_extend()
        return True

    def _on_dosage_ready(self):
        _log(
            f"ready prescript={self.prescript_key} weight={self.current_weight} "
            f"closing={self._closing} saved={self._saved}"
        )

        committed = self._commit_dosage()
        if committed:
            self._beep()

        if not self._closing:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
            self.accept()

    def _on_scale_error(self, message):
        if self._closing:
            return

        _log(f"scale error prescript={self.prescript_key}: {message}")
        self._show_scale_error()

    def _update_dosage_label(self, data):
        if self._closing:
            return

        self.current_weight = number_utils.get_float(data)
        self.ui.label_current_dosage.setText(string_utils.xstr(self.current_weight))
        weight = int(number_utils.get_float(self.current_weight) * 100)

        maximum = self.ui.progressBar_scale.maximum()

        if weight < maximum:
            self._display_image("./icons/emblem-synchronizing.png")
            self.sound_played = False
            self.ui.progressBar_scale.setStyleSheet(None)
            self._show_current_dosage(None)
        elif weight > maximum:
            self._display_image("./icons/emblem-important.png")
            self.sound_played = False
            self.ui.progressBar_scale.setStyleSheet("""
                QProgressBar {
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                    background-color: transparent; /* 無進度時背景透明 */
                }
                QProgressBar::chunk {
                    background-color: red;  /* 有進度時的顏色 */
                    width: 20px;
                }
            """)
            self._show_current_dosage("red")
        else:
            self.ui.progressBar_scale.setStyleSheet("""
                QProgressBar {
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                    background-color: transparent; /* 無進度時背景透明 */
                }
                QProgressBar::chunk {
                    background-color: green;  /* 有進度時的顏色 */
                    width: 20px;
                }
            """)
            self._show_current_dosage("green")
            if not self.sound_played:
                self._display_image("./icons/emblem-default.png")

        self.ui.progressBar_scale.setValue(weight)

        if maximum > 0:
            percentage = (weight / maximum) * 100
            self.ui.progressBar_scale.setFormat(f"{percentage:.0f}%")  # 設置顯示格式

    def _show_current_dosage(self, color):
        font_size = 64

        if color is None:
            style = f"font-size: {font_size}pt;"
        else:
            style = f"font-size: {font_size}pt; color: {color}; font-weight: bold"

        self.ui.label_current_dosage.setStyleSheet(style)
        self.ui.label_3.setStyleSheet(style)
        self.ui.label_4.setStyleSheet(style)

    def _display_image(self, filename):
        icon_size = 320
        self.ui.label_image.setPixmap(QtGui.QPixmap(filename))
        self.ui.label_image.setMaximumWidth(icon_size)
        self.ui.label_image.setMaximumHeight(icon_size)
        self.ui.label_image.setScaledContents(True)

    def _beep(self):
        if not self.sound_enabled:
            return

        try:
            mixer.music.play()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 關閉
    # ------------------------------------------------------------------
    def close_all(self):
        """停止執行緒後才關閉序列埠。

        先補寫可能遺漏的調劑記錄：worker 已判定合格、但 dosage_ready
        訊號還沒被主執行緒處理到就走到這裡的情況（按取消、按 Esc、
        視窗被關），原本會整筆丟失。
        """
        try:
            if self._commit_dosage():
                _log(f"commit on close prescript={self.prescript_key}")
        except Exception as e:
            _log(f"commit on close failed prescript={self.prescript_key}: {e}")

        if self._closing:
            return

        self._closing = True
        self.running = False  # 停止執行緒

        thread = getattr(self, "serial_thread", None)
        if thread is not None and thread.is_alive():
            if thread is not threading.current_thread():
                thread.join(THREAD_JOIN_TIMEOUT)
                if thread.is_alive():
                    _log(f"thread join timeout prescript={self.prescript_key}")
        self.serial_thread = None

        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

        _log(
            f"close prescript={self.prescript_key} "
            f"ready={self._dosage_ready} saved={self._saved}"
        )

    def closeEvent(self, event):
        self.close_all()
        event.accept()

    def accept(self):
        self.close_all()
        super().accept()

    def reject(self):
        self.close_all()
        super().reject()

    def accepted_button_clicked(self):
        self.close_all()
        self.accept()

    def rejected_button_clicked(self):
        self.close_all()
        self.reject()

    def save_pres_extend(self):
        try:
            prescript_utils.remove_pres_extend_row(
                self.database, self.prescript_key, "調劑完成"
            )
        except Exception as e:
            _log(f"remove failed prescript={self.prescript_key}: {e}")

        try:
            prescript_utils.insert_pres_extend_row(
                self.database, self.prescript_key, "調劑完成", "是"
            )
        except Exception as e:
            _log(f"insert failed prescript={self.prescript_key}: {e}")

        # 回讀驗證：寫進去了沒有，當下就知道，不必等藥師發現
        try:
            value = prescript_utils.get_pres_extend_value(
                self.database, self.prescript_key, "調劑完成"
            )
            if value != "是":
                _log(f"*** WRITE LOST prescript={self.prescript_key} value={value}")
            else:
                _log(f"verify ok prescript={self.prescript_key}")
        except Exception as e:
            _log(f"verify failed prescript={self.prescript_key}: {e}")
