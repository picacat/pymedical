# 藥局配藥秤重 2026.08.19
# -*- coding: UTF-8 -*-
#
# 本版針對「配藥時對話框反白凍住」所做的修正。
#
# 原版的 _get_weight() 跑在 threading.Thread 裡，卻直接做了三件
# 只能在主執行緒做的事：
#
#   1. self.accept() —— 從外部執行緒終止主執行緒正在跑的 exec_()
#      巢狀事件迴圈。Qt 對此的行為是未定義的，偶爾主執行緒就卡在
#      裡面出不來，視窗停止重繪 → 白畫面。
#
#   2. self.ui.buttonBox.button(...).setEnabled(True) —— 同上，
#      Qt widget 一律只能在建立它的執行緒操作。
#
#   3. save_pres_extend() —— 在 worker 執行緒用共用的 self.database
#      下 DELETE/INSERT。過去主執行緒在 exec_() 裡不碰資料庫，這條
#      連線實際上只有 worker 在用，所以僥倖沒事；改用 notification
#      之後主執行緒每 500ms 也在同一條連線上輪詢，兩邊就撞上了。
#
# 修正方式：worker 只做序列埠讀取，其餘一律用 signal 丟回主執行緒。
#
#   * weight_signal        每次讀到重量 → 主執行緒更新畫面
#   * dosage_ready_signal  重量穩定且誤差合格 → 主執行緒寫資料庫、關對話框
#   * scale_error_signal   序列埠異常 → 主執行緒顯示訊息並關閉
#
# 其他一併修正：
#   * serial.Serial() 失敗時 self.ser 未指派，下一行 self.ser.read(10)
#     會 AttributeError
#   * close_all() 直接 ser.close()，此時 worker 可能正卡在 readline()，
#     Windows 上關閉有未完成讀取的序列埠 handle 會阻塞 → 先 join 再關
#   * mixer.init() 失敗時 self.sound_played 未定義，_update_dosage_label
#     讀到就 AttributeError（在 slot 裡逃出的例外會讓 PyQt5 直接 abort）
#   * _set_data() 中途 return 時 self.total_dosage 未定義
#   * 穩定判斷改用 worker 自己算出的重量，不再回頭讀主執行緒才會更新的
#     self.current_weight（signal 是佇列傳遞，讀回來的值會落後一輪）

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
        """開啟電子秤。失敗時排程關閉對話框並回傳 False。

        原版在 serial.Serial() 失敗時只跳訊息就往下走，self.ser 從未
        指派，下一行 self.ser.read(10) 直接 AttributeError。
        """
        com_port = self._get_com_port()

        try:
            self.ser = serial.Serial(
                port=com_port,  # 串口號
                baudrate=9600,  # 波特率，根據你的設備進行設定
                timeout=1,  # 讀取超時時間
            )
        except Exception:
            self.ser = None

        if self.ser is None:
            self._show_scale_error()
            return False

        try:
            response = self.ser.read(10)
        except Exception:
            response = b""

        if len(response) == 0:
            self._show_scale_error()
            return False

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

    # ------------------------------------------------------------------
    # worker 執行緒：只讀序列埠，不碰 GUI、不碰資料庫
    # ------------------------------------------------------------------
    def _get_weight(self):
        last_weight = None
        stable_count = 0
        stable_target = max(1, int(self.scale_time * 10))
        tolerance_target = number_utils.get_float(self.total_dosage)

        while self.running:
            try:
                if not self.ser or not self.ser.in_waiting:
                    time.sleep(POLL_INTERVAL)
                    continue

                data = self.ser.readline().decode("utf-8", errors="ignore").strip()
            except serial.SerialException as e:
                # 關閉對話框時主執行緒會 close() 這個 port，屬正常結束
                if self.running:
                    self.scale_error_signal.emit(str(e))
                break
            except Exception:
                time.sleep(POLL_INTERVAL)
                continue

            if "No." in data:
                continue

            data = data.replace("g", "")

            # 自己算，不要回頭讀 self.current_weight ——
            # signal 是佇列傳遞，主執行緒還沒處理到，讀回來的是上一輪的值
            current_weight = number_utils.get_float(data)

            self.update_dosage_signal.emit(data)

            if last_weight is not None and current_weight == last_weight:
                stable_count += 1
            else:
                stable_count = 0

            # 穩定 scale_time 秒（sleep 0.01 要加上運算損耗，約等於 0.1）
            if stable_count >= stable_target:
                deviation = current_weight - tolerance_target
                if abs(round(deviation, 1)) <= DOSAGE_TOLERANCE:
                    # 寫資料庫、關對話框一律交給主執行緒
                    self.running = False
                    self.dosage_ready_signal.emit()
                    break

                stable_count = 0

            last_weight = current_weight

            time.sleep(POLL_INTERVAL)

    # ------------------------------------------------------------------
    # 主執行緒：接收 worker 的通知
    # ------------------------------------------------------------------
    def _on_dosage_ready(self):
        """重量合格。這裡是主執行緒，才可以寫資料庫、關對話框。"""
        if self._closing:
            return

        self.save_pres_extend()
        self._beep()
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        self.accept()

    def _on_scale_error(self, message):
        if self._closing:
            return

        print(f"scale error: {message}")
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

        原版直接 ser.close()，此時 worker 可能正卡在 readline() 裡，
        Windows 上關閉一個有未完成讀取的序列埠 handle 會阻塞主執行緒。
        """
        if self._closing:
            return

        self._closing = True
        self.running = False  # 停止執行緒

        thread = getattr(self, "serial_thread", None)
        if thread is not None and thread.is_alive():
            if thread is not threading.current_thread():
                thread.join(THREAD_JOIN_TIMEOUT)
        self.serial_thread = None

        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

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
            print(f"remove_pres_extend_row failed: {e}")

        try:
            prescript_utils.insert_pres_extend_row(
                self.database, self.prescript_key, "調劑完成", "是"
            )
        except Exception as e:
            print(f"insert_pres_extend_row failed: {e}")
