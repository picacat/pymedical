# 藥局作業 2026.08.22
# -*- coding: UTF-8 -*-
#
# 沿革
# ----
# 2026.08.19  修正配藥時不定時凍住、畫面反白：
#   1. NotificationServer 使用獨立的資料庫連線（self.notification_db），
#      不再與 GUI 共用 self.database。輪詢的 SELECT 與畫面上的查詢在同
#      一條 MySQL 連線上交錯，會造成連線狀態錯亂，接著觸發 _reconnect()，
#      而重連是在主執行緒阻塞的。
#   2. 改用 handler 而不是 update_signal 交付訊息（slot 逃出的例外會讓
#      PyQt5 直接 abort）。
#   3. 調劑中暫停通知處理，只記錄 _pending_reload。
#   4. _read_pharmacy_list() 加重入旗標。
#   5. 配藥狀態改用布林旗標 self._processing，label_status 只是它的顯示。
#   6. 閒置時每分鐘保底重讀一次名單。
#   7. _is_scale_reset_to_zero() 加絕對逾時。
#
# 2026.08.22  ★ 配藥配到一半，新名單進來導致選取列跳走，藥師沒發現就
#             繼續配，等於配到別的病人身上。這是 08-19 版引入的迴歸：
#             舊版收到通知時若正在配藥是「直接丟棄」，改成「記下來稍後
#             補做」之後，對話框一關就重建名單；而排序是 PrescriptKey
#             DESC，新病人排在最上面，重建後選取列落回第 0 列。
#
#   修正一：名單重建後還原選取列（_get_current_key / _restore_current_key）
#           以 CaseKey + 處方別 為鍵，重建後找回原本那一列；找不到
#           （已配完、換班別）才回到預設位置。重建期間 blockSignals，
#           避免 itemSelectionChanged 一路觸發 _pharmacy_list_changed。
#
#   修正二：整張處方配完之前不因通知而重建（_is_pharmacy_busy）
#           原本的 _is_pharmacy_processing() 只涵蓋對話框開著的那幾秒，
#           真正該保護的是「這張處方配了一部分、還沒配完」的整段期間。
#
#           但保底重讀刻意不受這一條約束——否則藥師若中途離開，名單
#           會無限期停止更新，新病人不會出現。因為修正一已經會還原
#           選取列，保底重讀是安全的。

import configparser
import datetime
import os
import sys
import time

import serial
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QInputDialog, QMessageBox, QPushButton

from libs import (
    case_utils,
    class_utils,
    date_utils,
    dialog_utils,
    module_utils,
    notification_utils,
    number_utils,
    prescript_utils,
    printer_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
)

# 導入 Windows 平台相關模塊
if sys.platform == "win32":
    from win32 import win32gui, win32print
    from win32.lib import win32con

    try:
        import pyuac
    except Exception:
        system_utils.pip3_install("pyuac")


# 通知去抖動間隔（毫秒）：短時間內連續多則通知只重載一次
RELOAD_DEBOUNCE_INTERVAL = 400

# 閒置保底重讀間隔（毫秒）
IDLE_REFRESH_INTERVAL = 60000

# 電子秤讀值的絕對逾時（秒）
SCALE_READ_TIMEOUT = 5.0


# 藥局作業 2024-05-20 邵秉家
class PyPharmacy(QtWidgets.QMainWindow):
    program_name = "批價作業"

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent

        self._set_db(config_file)
        if not self.database.connected():
            if self.splash is not None:
                self.splash.finish(self)

            if config_file is None:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.setWindowTitle("連線失敗")
                msg_box.setText(
                    "<font size='4' color='red'><b>無法連線至資料庫主機, 請檢查網路設定.</b></font>"
                )
                msg_box.setInformativeText(
                    "請檢查 pymedical.conf 內的設定, 確定資料庫連線設定是否正確."
                )
                msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
                msg_box.exec_()
            else:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.setWindowTitle("連線失敗")
                msg_box.setText(
                    "<font size='4' color='red'><b>無法連線至資料庫主機, 請檢查傳遞的參數.</b></font>"
                )
                msg_box.setInformativeText("請檢查傳遞的參數是否正確.")
                msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
                msg_box.exec_()

            sys.exit(0)

        self.version = system_utils.get_system_version()
        self.ui = None

        # 配藥狀態與重載控制旗標。必須在任何 UI 動作之前設定，
        # 因為 _is_pharmacy_processing() 可能在初始化途中被呼叫。
        self._processing = False  # 是否正在配藥（含掃碼前的檢查）
        self._reloading = False  # _read_pharmacy_list 是否正在執行
        self._pending_reload = False  # 暫停期間是否有待處理的名單更新

        self.notification_db = None
        self.notification_server = None
        self._reload_timer = None
        self._idle_refresh_timer = None

        self.system_settings = class_utils.get_system_settings(
            self.database, self.config_file
        )
        self.user_name = system_utils.get_user_name(self.system_settings)
        self.clinic_name = self.system_settings.field("院所名稱")

        self.scale_time = round(
            number_utils.get_float(self.system_settings.field("電子秤測重時間")), 1
        )
        if self.scale_time == 0:
            self.scale_time = 1.5

        self.qrcode = ""

        self.com_port = self.system_settings.field("電子秤連接埠")

        self._set_ui()
        self._set_signal()
        self._set_notification_server()
        self._set_permission()

        self.read_wait()

    def _set_db(self, config_file):
        if config_file is not None:
            BASE_DIR = os.path.abspath(os.path.join(os.path.dirname("__file__")))
            self.config_file = os.path.join(BASE_DIR, config_file)
            self.database = class_utils.get_db(self.config_file)
            self.host = self.database.host
        else:
            self.database = class_utils.get_db()
            self.config_file = self.database.CONFIG_FILE
            self.host = self.database.host

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        self._stop_notification()

    def closeEvent(self, event):
        # 直接按視窗右上角關閉時，close_app() 不會被呼叫
        self._stop_notification()
        super().closeEvent(event)

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PY_PHARMACY, self)
        self.table_widget_charge_list = class_utils.get_table_widget(
            self.ui.tableWidget_pharmacy_list, self.database
        )
        self.table_widget_prescript = class_utils.get_table_widget(
            self.ui.tableWidget_prescript, self.database
        )
        self.ui.setWindowTitle(f"{self.clinic_name} 藥局配藥系統")

        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        system_utils.set_theme(self.ui, self.system_settings)

        self.ui.action_print_receipt.setEnabled(False)
        self.ui.action_print_drug_bag.setEnabled(False)

        self.table_widget_charge_list.set_column_hidden([0, 1])
        self.table_widget_prescript.set_column_hidden([0, 1])

        self._set_radio_button_period()
        self._set_table_width()
        self._set_status_bar()
        self._set_font_size()

    # ------------------------------------------------------------------
    # 站台通知
    # ------------------------------------------------------------------
    def _set_notification_server(self):
        """建立通知接收端。

        輪詢必須使用自己的資料庫連線：NotificationServer 的 QTimer 跑在
        主執行緒，每 500ms 下一句 SELECT，若與 GUI 共用 self.database，
        這句會插進畫面查詢的 cursor 之間，造成連線狀態錯亂。

        另外用 handler 而非 update_signal，理由見 notification_utils 的
        _deliver() 說明（slot 逃出的例外會讓 PyQt5 直接 abort）。
        """
        # 去抖動計時器：多則通知合併成一次重載
        self._reload_timer = QtCore.QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(RELOAD_DEBOUNCE_INTERVAL)
        self._reload_timer.timeout.connect(self._read_pharmacy_list)

        # 保底重讀：即使通知完全失效，名單最多延遲一分鐘也會自己更新
        self._idle_refresh_timer = QtCore.QTimer(self)
        self._idle_refresh_timer.setInterval(IDLE_REFRESH_INTERVAL)
        self._idle_refresh_timer.timeout.connect(self._idle_refresh)
        self._idle_refresh_timer.start()

        try:
            self.notification_db = class_utils.get_db(self.config_file)
            if not self.notification_db.connected():
                self.notification_db = None
        except Exception as e:
            print(f"（通知連線建立失敗：{e}）")
            self.notification_db = None

        if self.notification_db is None:
            # 降級運作：沒有通知，但保底重讀仍在，名單不會卡住
            print("（通知連線無法建立，改由定時重讀維持名單更新）")
            return

        try:
            self.notification_server = notification_utils.NotificationServer(
                self,
                database=self.notification_db,
                station="pymedical",
                channels=[notification_utils.CHANNEL_WAITING_LIST],
                handler=self._on_notification,
            )
        except Exception as e:
            print(f"（通知接收端建立失敗：{e}）")
            self.notification_server = None

    def _on_notification(self, channel, message):
        """收到通知。這裡只決定「要不要重載」，絕不直接動表格。"""
        if channel != notification_utils.CHANNEL_WAITING_LIST:
            return

        try:
            fields = message.split(",")
            if fields[0] != self.clinic_name:  # 其他分院呼叫
                return
            if fields[1] != "醫師看診作業":  # 與舊 UDP 版行為一致
                return
        except (AttributeError, IndexError):
            # 訊息格式不如預期，忽略即可，不要讓例外往外傳
            return

        if self._is_pharmacy_busy():
            # 配藥中（含整張處方配到一半）：只記下來，稍後再補
            self._pending_reload = True
            return

        self._reload_timer.start()

    def _idle_refresh(self):
        """閒置時的保底重讀。

        這裡刻意只擋「對話框開著」，不擋 _is_pharmacy_busy()——否則
        藥師配到一半離開，名單就無限期不更新，新病人不會出現。
        選取列已經會被還原，所以中途重建是安全的。
        """
        if self._is_pharmacy_processing() or self._reloading:
            return

        self._read_pharmacy_list()

    def _resume_notification(self):
        """配藥結束，回到等待狀態並補做暫停期間累積的更新"""
        self._set_pharmacy_processing(False)

        # 整張處方還沒配完就先不要重建，等最後一味配完再說
        if self._pending_reload and not self._is_pharmacy_busy():
            self._pending_reload = False
            self._reload_timer.start()

    def _stop_notification(self):
        """關閉流程中呼叫，絕不可拋例外"""
        for timer in (
            getattr(self, "_reload_timer", None),
            getattr(self, "_idle_refresh_timer", None),
        ):
            if timer is None:
                continue
            try:
                timer.stop()
            except Exception:
                pass

        server = getattr(self, "notification_server", None)
        if server is not None:
            try:
                server.stop()
            except Exception:
                pass

        database = getattr(self, "notification_db", None)
        if database is not None:
            try:
                database.close()
            except Exception:
                pass
            self.notification_db = None

    # 設定 status bar
    def _set_status_bar(self):
        self.label_scale_time = QtWidgets.QLabel()
        self.label_scale_time.setFixedWidth(230)
        self.label_scale_time.setText("電子秤測重時間: " + str(self.scale_time) + "秒")
        self.ui.statusbar.addPermanentWidget(self.label_scale_time)

    def _set_font_size(self):
        font_size = 20
        self.ui.setStyleSheet(
            f"font-size: {font_size}pt; font-family: Microsoft JhengHei; font-weight: bold"
        )
        self.ui.tableWidget_pharmacy_list.setStyleSheet(
            f"font-size: {font_size}pt; font-family: Microsoft JhengHei; font-weight: bold"
        )
        self.ui.tableWidget_prescript.setStyleSheet(
            f"font-size: {font_size}pt; font-family: Microsoft JhengHei; font-weight: bold"
        )

    def _set_table_width(self):
        width = [100, 100, 70, 100, 130, 80, 100, 170, 120]
        self.table_widget_charge_list.set_table_heading_width(width)

        width = [100, 100, 380, 130, 110, 130, 90]
        self.table_widget_prescript.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_app)
        self.ui.action_print_receipt.triggered.connect(
            lambda: self._print_receipt(None)
        )
        self.ui.action_print_drug_bag.triggered.connect(
            lambda: self._print_prescript_bag(None)
        )
        self.ui.action_medicine_settings.triggered.connect(
            self._open_dialog_medicine_settings
        )
        self.ui.action_set_scale_time.triggered.connect(self._set_scale_time)

        self.ui.radioButton_not_dispensing.clicked.connect(self.read_wait)
        self.ui.radioButton_dispensing.clicked.connect(self.read_wait)
        self.ui.radioButton_all.clicked.connect(self.read_wait)

        self.ui.radioButton_period_all.clicked.connect(self.read_wait)
        self.ui.radioButton_period1.clicked.connect(self.read_wait)
        self.ui.radioButton_period2.clicked.connect(self.read_wait)
        self.ui.radioButton_period3.clicked.connect(self.read_wait)

        self.ui.tableWidget_pharmacy_list.itemSelectionChanged.connect(
            self._pharmacy_list_changed
        )
        self.ui.keyPressEvent = self.keyPressEvent
        self.ui.tableWidget_pharmacy_list.keyPressEvent = self.keyPressEvent
        self.ui.tableWidget_prescript.keyPressEvent = self.keyPressEvent

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            if "case" in self.qrcode:
                self.locate_cases(self.qrcode)
            else:
                self.open_dialog_pharmacy(self.qrcode)

            self.qrcode = ""
        else:
            self.qrcode += event.text()

    def locate_cases(self, data):
        data = data.replace("case", "")

        case_key = number_utils.get_integer(data[:8])
        medicine_set = number_utils.get_integer(data[8:])
        if medicine_set == 1:
            pharmacy_type = "健保處方"
        else:
            pharmacy_type = f"自費處方{medicine_set - 1}"

        for row_no in range(self.ui.tableWidget_pharmacy_list.rowCount()):
            current_case_key = self.ui.tableWidget_pharmacy_list.item(row_no, 1)
            if current_case_key is None:
                continue

            current_case_key = current_case_key.text()
            current_pharmacy_type = self.ui.tableWidget_pharmacy_list.item(row_no, 7)
            if current_pharmacy_type is None:
                continue

            current_pharmacy_type = current_pharmacy_type.text()

            if string_utils.xstr(case_key) != current_case_key:
                continue

            if pharmacy_type != current_pharmacy_type:
                continue

            self.ui.tableWidget_pharmacy_list.setCurrentCell(row_no, 1)
            break

    def _get_com_port(self):
        com_port = None

        if sys.platform == "win32":
            com_port = f"COM{self.com_port}"
        elif sys.platform == "linux":
            com_port = f"/dev/ttyUSB{self.com_port}"

        return com_port

    def _is_scale_reset_to_zero(self):
        """電子秤是否已歸零。

        原版的 while True 有兩條 continue（decode 失敗、讀到 'No.'）
        都不累加 time_out，理論上可以永久空轉，而這一段跑在主執行緒，
        空轉就是畫面反白。這裡加上絕對逾時作為硬上限。
        """
        com_port = self._get_com_port()
        try:
            ser = serial.Serial(
                port=com_port,  # 串口號
                baudrate=9600,  # 波特率，根據你的設備進行設定
                timeout=1,  # 讀取超時時間
            )
        except Exception:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "電子秤有誤",
                "<h1>無法連線至電子秤，請檢查電子秤的電源是否開啟或連接線是否接妥。</h1>",
                "無法連接至電子秤.",
            )
            return False

        weight = None
        time_out = 0
        start_time = time.time()

        try:
            while True:
                # 絕對逾時：任何一條路徑都不可能無限迴圈
                if time.time() - start_time > SCALE_READ_TIMEOUT:
                    break

                try:
                    data = ser.readline().decode("ascii").strip()
                except Exception:
                    continue

                if "No." in data:
                    continue

                # 讀取逾時會得到空字串，視同 0（維持原版行為）
                weight = round(number_utils.get_float(data.replace("g", "")), 1)
                if weight == 0 or time_out > 10:
                    break

                time_out += 1
                time.sleep(0.2)
        except serial.SerialException as e:
            print(f"init com port failed: {e}")
        finally:
            try:
                ser.close()
            except Exception:
                pass

        return weight == 0

    # ------------------------------------------------------------------
    # 配藥
    # ------------------------------------------------------------------
    def open_dialog_pharmacy(self, data):
        """掃碼配藥的進入點。

        整段包 try/finally，是因為前面幾道檢查（不需調劑、已調劑完成、
        查無此藥、電子秤未歸零）都是 return，而 _is_scale_reset_to_zero()
        最長會阻塞數秒。這段期間若讓通知重建表格，使用者手上這筆的
        case_key 就換掉了。
        """
        self._set_pharmacy_processing(True)
        try:
            self._open_dialog_pharmacy(data)
        finally:
            self._resume_notification()

    def _open_dialog_pharmacy(self, data):
        case_key = self.table_widget_charge_list.field_value(1)
        if case_key in [None, ""]:
            return

        medicine_set = self._get_medicine_set()
        if not self._ready_to_serve(case_key, medicine_set):
            system_utils.show_message_box(
                QMessageBox.Warning,
                "不需調劑",
                "<h1>此病歷不需要調劑，請重新掃描.</h1>",
                "請再確認是否正確.",
            )
            return

        if self._is_prescript_done(case_key, medicine_set):
            system_utils.show_message_box(
                QMessageBox.Warning,
                "調劑完成",
                "<h1>此病歷已調劑完成，請重新掃描.</h1>",
                "請再確認是否正確.",
            )
            return

        sql = f'''
            SELECT MedicineKey, MedicineCode FROM medicine
            WHERE
                MedicineCode = "{data}"
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            sql = f'''
                SELECT MedicineKey, Description AS MedicineCode FROM medextend
                WHERE
                    ExtendType = "藥品條碼" AND
                    Description = "{data}"
                LIMIT 1
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "查無此藥",
                    "<h1>查無此藥，請重新掃描.</h1>",
                    "請再確認是否拿錯.",
                )
                return

        if not self._is_scale_reset_to_zero():
            system_utils.show_message_box(
                QMessageBox.Critical,
                "電子秤有誤",
                "<h1>電子秤尚未歸零，請確認電子秤的狀態.</h1>",
                "請確認電子秤上是否其他藥品.",
            )
            return

        row = rows[0]
        medicine_key = string_utils.xstr(row["MedicineKey"])
        medicine_code = string_utils.xstr(row["MedicineCode"])

        prescript_key, medicine_name = None, ""
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            current_medicine_key = self.ui.tableWidget_prescript.item(row_no, 1)
            if current_medicine_key is None:
                continue

            current_medicine_key = current_medicine_key.text()
            if current_medicine_key != medicine_key:
                continue

            prescript_item = self.ui.tableWidget_prescript.item(row_no, 0)
            if prescript_item is None:
                continue

            prescript_key = prescript_item.text()
            medicine_name_item = self.ui.tableWidget_prescript.item(row_no, 2)
            if medicine_name_item is not None:
                medicine_name = medicine_name_item.text()

            self.ui.tableWidget_prescript.setCurrentCell(row_no, 0)
            break

        if prescript_key is None:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "查無此藥",
                "<h1>查無此藥，請重新掃描.</h1>",
                "請再確認是否拿錯.",
            )
            return

        is_druged = prescript_utils.get_pres_extend_value(
            self.database, prescript_key, "調劑完成"
        )
        if is_druged == "是":
            system_utils.show_message_box(
                QMessageBox.Critical,
                "已經配過此藥了",
                f"<h1>{medicine_name}已經調劑完成，請勿重複調劑.</h1>",
                "請再確認是否調劑過.",
            )
            return

        dialog = dialog_utils.get_dialog_pharmacy_dosage(
            self,
            self.database,
            self.system_settings,
            prescript_key,
            medicine_key,
            medicine_code,
            medicine_set,
            self.scale_time,
        )

        try:
            dialog.exec_()
        finally:
            del dialog

        self.raise_()

        case_key = self.table_widget_charge_list.field_value(1)
        self._read_prescript(case_key)
        self.ui.tableWidget_prescript.setFocus()
        QtCore.QTimer.singleShot(0, self._focus_prescript)

        if not self._is_one_pharmacy_processing() or self._is_pharmacy_done():
            self._filter_pharmacy_list()
            self._read_pharmacy_list()
            case_key = self.table_widget_charge_list.field_value(1)
            self._read_prescript(case_key)
            # 剛剛已經重載過，暫停期間累積的更新視同已滿足
            self._pending_reload = False

        self.raise_()
        self.ui.tableWidget_prescript.setFocus()
        QtCore.QTimer.singleShot(0, self._focus_prescript)

    def _focus_prescript(self):
        self.activateWindow()  # 若跨視窗切換，建議打開
        self.raise_()
        self.ui.tableWidget_prescript.setFocus()

    def _open_dialog_medicine_settings(self):
        dialog = dialog_utils.get_dialog_medicine_settings(
            self, self.database, self.system_settings
        )
        dialog.exec_()

    def _set_permission(self):
        if self.user_name == "超級使用者":
            return

    def close_app(self):
        self._stop_notification()
        self.close_all()
        self.close()

    def _set_radio_button_period(self):
        period = registration_utils.get_current_period(self.system_settings)

        if period == "早班":
            self.ui.radioButton_period1.setChecked(True)
        elif period == "午班":
            self.ui.radioButton_period2.setChecked(True)
        elif period == "晚班":
            self.ui.radioButton_period3.setChecked(True)

    def _set_current_period(self):
        period = registration_utils.get_current_period(self.system_settings)

        if period == "早班":
            self.ui.radioButton_period1.setChecked(True)
        elif period == "午班":
            self.ui.radioButton_period2.setChecked(True)
        elif period == "晚班":
            self.ui.radioButton_period3.setChecked(True)

    def read_wait(self):
        self._read_pharmacy_list()
        if self.table_widget_charge_list.row_count() <= 0:
            enabled = False
        else:
            enabled = True

        self.ui.action_print_receipt.setEnabled(enabled)
        self.ui.action_print_drug_bag.setEnabled(enabled)

        self._set_permission()
        self._filter_pharmacy_list()
        self._set_current_row()

        self._pharmacy_list_changed()

    def _get_period_script(self, table_name):
        period_script = ""

        if self.ui.radioButton_period1.isChecked():
            period_script = f' AND {table_name}.Period = "早班" '
        elif self.ui.radioButton_period2.isChecked():
            period_script = f' AND {table_name}.Period = "午班" '
        elif self.ui.radioButton_period3.isChecked():
            period_script = f' AND {table_name}.Period = "晚班" '

        return period_script

    # ------------------------------------------------------------------
    # 選取列的保存與還原
    # ------------------------------------------------------------------
    def _get_current_key(self):
        """記住目前選取的是哪一筆（病歷 + 處方別）。

        不能用 row_no —— 名單一重建，同一個 row_no 就是別人了。
        排序是 PrescriptKey DESC，新病人排在最上面，重建後選取列會
        落回第 0 列，藥師沒發現就會配到別的病人身上。
        """
        return (
            self.table_widget_charge_list.field_value(1),  # CaseKey
            self.table_widget_charge_list.field_value(7),  # 健保處方 / 自費處方N
        )

    def _restore_current_key(self, case_key, pharmacy_type):
        """重建後找回原本那一列。找不到就回傳 False。"""
        if case_key in [None, ""]:
            return False

        for row_no in range(self.ui.tableWidget_pharmacy_list.rowCount()):
            case_item = self.ui.tableWidget_pharmacy_list.item(row_no, 1)
            type_item = self.ui.tableWidget_pharmacy_list.item(row_no, 7)
            if case_item is None or type_item is None:
                continue

            if case_item.text() != case_key:
                continue

            if pharmacy_type is not None and type_item.text() != pharmacy_type:
                continue

            self.ui.tableWidget_pharmacy_list.setCurrentCell(row_no, 0)
            return True

        return False

    def _read_pharmacy_list(self):
        """重讀候診名單。

        重入防護：這支流程包含一次大查詢，加上每一列的
        _set_pharmacy_ok() → _is_prescript_done() → 每筆處方一次
        get_pres_extend_value()（N+1）。中途只要有任何 processEvents()，
        計時器或選取變更就有機會在表格重建到一半時再叫一次。
        """
        if self._reloading:
            self._pending_reload = True
            if self._reload_timer is not None:
                self._reload_timer.start()  # 稍後再試
            return

        self._reloading = True
        try:
            # 先記住藥師目前在配哪一筆
            current_case_key, current_pharmacy_type = self._get_current_key()

            period_script = self._get_period_script("cases")

            order_script = "ORDER BY prescript.PrescriptKey DESC"

            sql = f"""
                SELECT wait.WaitKey, wait.PatientKey, wait.Name,
                       cases.CaseKey, cases.CaseDate, cases.InsType,
                       cases.RegistNo, cases.Doctor, cases.TotalFee, cases.DrugDone,
                       patient.Gender, patient.Birthday, patient.DiscountType,
                       prescript.MedicineSet
                FROM wait
                    LEFT JOIN patient ON patient.PatientKey = wait.PatientKey
                    LEFT JOIN cases ON cases.CaseKey = wait.CaseKey
                    LEFT JOIN prescript ON prescript.CaseKey = wait.CaseKey
                WHERE
                    cases.DoctorDone = "True" AND
                    prescript.MedicineType NOT IN ("穴道", "處置")
                    {period_script}
                GROUP BY wait.CaseKey, prescript.MedicineSet
                {order_script}
            """

            # 重建期間不要讓 itemSelectionChanged 一路觸發
            # _pharmacy_list_changed（每次都會再查兩輪資料庫）
            self.ui.tableWidget_pharmacy_list.blockSignals(True)
            try:
                self.table_widget_charge_list.set_db_data(sql, self._set_pharmacy_list)
                self._filter_pharmacy_list()

                if not self._restore_current_key(
                    current_case_key, current_pharmacy_type
                ):
                    # 原本那筆不在了（已配完、換班別）才回到預設位置
                    self._set_current_row()
            finally:
                self.ui.tableWidget_pharmacy_list.blockSignals(False)

            self._pharmacy_list_changed()
            self._pending_reload = False
        finally:
            self._reloading = False

    def _filter_pharmacy_list(self):
        if self.ui.radioButton_not_dispensing.isChecked():
            dispensing = "未調劑"
        elif self.ui.radioButton_dispensing.isChecked():
            dispensing = "已調劑"
        else:
            return

        for row_no in range(self.ui.tableWidget_pharmacy_list.rowCount() - 1, -1, -1):
            label_image = self.ui.tableWidget_pharmacy_list.cellWidget(row_no, 9)

            if (
                dispensing == "已調劑"
                and label_image is None
                or dispensing == "未調劑"
                and label_image is not None
            ):
                self.ui.tableWidget_pharmacy_list.removeRow(row_no)

    def _set_pharmacy_list(self, row_no, row):
        case_key = string_utils.xstr(row["CaseKey"])
        medicine_set = number_utils.get_integer(row["MedicineSet"])

        if medicine_set == 1:
            pharmacy_type = "健保處方"
        else:
            pharmacy_type = f"自費處方{medicine_set - 1}"

        age_year, _ = date_utils.get_age(row["Birthday"], row["CaseDate"])
        if age_year is None:
            age = ""
        else:
            age = f"{age_year}歲"

        wait_row = [
            string_utils.xstr(row["WaitKey"]),
            case_key,
            string_utils.xstr(row["RegistNo"]),
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["Gender"]),
            age,
            pharmacy_type,
            string_utils.xstr(row["Doctor"]),
            None,
        ]

        for col_no in range(len(wait_row)):
            self.ui.tableWidget_pharmacy_list.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(wait_row[col_no])
            )
            if col_no in [2, 3, 4, 5, 6, 8]:
                self.ui.tableWidget_pharmacy_list.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if "自費" in pharmacy_type:
                self.ui.tableWidget_pharmacy_list.item(row_no, col_no).setForeground(
                    QtGui.QColor("blue")
                )

        self._set_pharmacy_ok(case_key, medicine_set, row_no, 9)

    def _ready_to_serve(self, case_key, medicine_set):
        ready_to_reserve = True

        dosage_row = case_utils.get_dosage_row(self.database, case_key, medicine_set)
        if len(dosage_row) > 0:
            dosage_row = dosage_row[0]
            no_pharmacy = string_utils.xstr(dosage_row["NoPharmacy"])
            if no_pharmacy == "Y":
                ready_to_reserve = False

        return ready_to_reserve

    def _set_pharmacy_ok(self, case_key, medicine_set, row_no, col_no):
        if row_no is None or row_no < 0:
            return

        if not self._ready_to_serve(case_key, medicine_set):
            image_file = "./icons/gtk-close.svg"
            self._set_table_widget_image(
                self.ui.tableWidget_pharmacy_list, row_no, col_no, image_file
            )
            self._set_row_color(self.ui.tableWidget_pharmacy_list, row_no, "gray")
            return

        is_prescript_done = self._is_prescript_done(case_key, medicine_set)

        if is_prescript_done:
            image_file = "./icons/gtk-ok.svg"
            self._set_row_color(self.ui.tableWidget_pharmacy_list, row_no, "gray")
        else:
            image_file = None

        self._set_table_widget_image(
            self.ui.tableWidget_pharmacy_list, row_no, col_no, image_file
        )

    def _is_prescript_done(self, case_key, medicine_set):
        if case_key in [None, ""] or medicine_set is None:
            return False

        sql = f"""
            SELECT PrescriptKey FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = {medicine_set} AND
                prescript.MedicineName NOT IN ("自費粉藥", "自費水藥", "自費藥費") AND
                prescript.MedicineType IN ("單方", "複方")
        """
        rows = self.database.select_record(sql)

        pharmacy_done = True
        for row in rows:
            prescript_key = string_utils.xstr(row["PrescriptKey"])
            is_druged = prescript_utils.get_pres_extend_value(
                self.database, prescript_key, "調劑完成"
            )
            if is_druged in ["否", None]:
                pharmacy_done = False
                break

        return pharmacy_done

    def _set_drug_done(self, drug_done=False):
        wait_key = self.table_widget_charge_list.field_value(0)
        case_key = self.table_widget_charge_list.field_value(1)

        if drug_done:
            self._save_records(wait_key=wait_key, case_key=case_key)
        else:
            self._save_records(wait_key=wait_key, case_key=case_key, drug_done="False")

    def _pharmacy_list_changed(self):
        case_key = self.table_widget_charge_list.field_value(1)
        self._read_prescript(case_key)
        self._read_dosage(case_key)

    def _read_dosage(self, case_key):
        medicine_set = self._get_medicine_set()
        if medicine_set is None or case_key in [None, ""]:
            self.ui.label_patient.setText(None)
            self.ui.tableWidget_prescript.setRowCount(0)
            return

        sql = f"""
            SELECT dosage.*, cases.SDrugShareFee FROM dosage
                LEFT JOIN cases ON cases.CaseKey = dosage.CaseKey
            WHERE
                dosage.CaseKey = {case_key} AND
                MedicineSet = {medicine_set}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self.ui.label_patient.setText(None)
            return

        row = rows[0]

        packages = number_utils.get_integer(row["Packages"])
        if packages == 0:
            packages = 1

        pres_days = number_utils.get_integer(row["Days"])
        if pres_days == 0:
            pres_days = 1

        instruction = string_utils.xstr(row["Instruction"])
        total_dosge = self._get_total_dosage()

        dosage = f"""一日 {packages}包 {pres_days}日份，總量 {total_dosge}克，共 {packages * pres_days}包，{instruction}服用"""
        if medicine_set == 1:
            fee = number_utils.get_integer(row["SDrugShareFee"])
            self.ui.label_fee.setText(f"藥品負擔: {fee}")
        else:
            fee = number_utils.get_integer(row["SelfTotalFee"])
            self.ui.label_fee.setText(f"自費金額: {fee}")

        self.ui.label_patient.setText(dosage)

    def _get_total_dosage(self):
        total_dosage = 0
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            dosage = self.ui.tableWidget_prescript.item(row_no, 5)
            if dosage is None:
                continue

            dosage = dosage.text().replace("克", "")
            total_dosage += number_utils.get_float(dosage)

        return round(total_dosage, 1)

    def _show_medical_record(self, case_key):
        if case_key in [None, ""]:
            return

    def _get_medicine_set(self):
        pharmacy_type = self.table_widget_charge_list.field_value(7)
        if pharmacy_type is None:
            return None

        if pharmacy_type == "健保處方":
            medicine_set = 1
        else:
            medicine_set = (
                number_utils.get_integer(pharmacy_type.replace("自費處方", "")) + 1
            )

        return medicine_set

    def _read_prescript(self, case_key):
        medicine_set = self._get_medicine_set()
        if medicine_set is None or case_key in [None, ""]:
            return

        sql = f"""
            SELECT prescript.* FROM prescript
                LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
            WHERE
                prescript.CaseKey = {case_key} AND
                prescript.MedicineSet = {medicine_set} AND
                prescript.MedicineName NOT IN ("自費粉藥", "自費水藥", "自費藥費") AND
                prescript.MedicineType IN ("單方", "複方")
            GROUP BY prescript.PrescriptKey
            ORDER BY SUBSTRING(medicine.Location, 1, 1), CAST(SUBSTRING(medicine.Location, 2) AS UNSIGNED) DESC
        """

        self.table_widget_prescript.set_db_data(sql, self._set_prescript_data)

        if not self._ready_to_serve(case_key, medicine_set):
            image_file = "./icons/gtk-close.svg"
            for row_no in range(self.ui.tableWidget_prescript.rowCount()):
                self._set_row_color(self.ui.tableWidget_prescript, row_no, "gray")
                self._set_table_widget_image(
                    self.ui.tableWidget_prescript, row_no, 6, image_file
                )
        elif self._is_prescript_done(case_key, medicine_set):
            row_no = self.ui.tableWidget_pharmacy_list.currentRow()
            # currentRow() 在名單為空或剛重建時會是 -1
            if row_no >= 0:
                self._set_pharmacy_ok(case_key, medicine_set, row_no, 9)

    def _is_one_pharmacy_processing(self):
        pharmacy_processing = False
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            label_image = self.ui.tableWidget_prescript.cellWidget(row_no, 6)
            if label_image is not None:
                pharmacy_processing = True
                break

        return pharmacy_processing

    def _is_pharmacy_done(self):
        pharmacy_done = True
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            label_image = self.ui.tableWidget_prescript.cellWidget(row_no, 6)
            if label_image is None:
                pharmacy_done = False
                break

        return pharmacy_done

    def _set_pharmacy_done(self):
        case_key = self.table_widget_charge_list.field_value(1)
        if case_key in [None, ""]:
            return

        sql = f"""
            SELECT DrugDone FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        drug_done = string_utils.xstr(row["DrugDone"])
        if drug_done == "False":
            self.database.exec_sql(
                f'UPDATE cases SET DrugDone = "True" WHERE CaseKey = {case_key}'
            )

    def _set_prescript_data(self, row_no, row):
        medicine_set = self._get_medicine_set()

        prescript_key = string_utils.xstr(row["PrescriptKey"])
        medicine_key = string_utils.xstr(row["MedicineKey"])
        case_key = string_utils.xstr(row["CaseKey"])
        location = None

        medicine_row = prescript_utils.get_medicine_record(self.database, medicine_key)
        if medicine_row is not None:
            location = string_utils.xstr(medicine_row["Location"])

        medicine_name = string_utils.xstr(row["MedicineName"])
        pres_days = case_utils.get_pres_days(
            self.database, case_key, medicine_set=medicine_set
        )
        dosage = round(number_utils.get_float(row["Dosage"]), 1)
        total_dosage = round(pres_days * dosage, 1)
        unit = string_utils.xstr(row["Unit"])

        prescript_row = [
            prescript_key,
            medicine_key,
            medicine_name,
            location,
            f"{string_utils.xstr(dosage)}{unit}",
            f"{string_utils.xstr(total_dosage)}{unit}",
            None,
        ]

        for col_no in range(len(prescript_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, string_utils.xstr(prescript_row[col_no]))
            self.ui.tableWidget_prescript.setItem(row_no, col_no, item)
            if col_no in [4, 5]:
                self.ui.tableWidget_prescript.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

        self._set_prescript_ok(prescript_key, row_no, 6)

    def _set_row_color(self, in_table_widget, row_no, color):
        if row_no is None or row_no < 0:
            return

        for col_no in range(in_table_widget.columnCount()):
            item = in_table_widget.item(row_no, col_no)
            if item is None:  # 表格重建途中該列可能還沒有 item
                continue

            item.setForeground(QtGui.QColor(color))

    def _set_prescript_ok(self, prescript_key, row_no, col_no):
        is_druged = prescript_utils.get_pres_extend_value(
            self.database, prescript_key, "調劑完成"
        )
        if is_druged == "是":
            image_file = "./icons/gtk-ok.svg"
            self._set_row_color(self.ui.tableWidget_prescript, row_no, "gray")
        else:
            image_file = None

        self._set_table_widget_image(
            self.ui.tableWidget_prescript, row_no, col_no, image_file
        )

    def _set_table_widget_image(self, in_table_widget, row_no, col_no, image_file):
        if row_no is None or row_no < 0:
            return

        if image_file is None:
            in_table_widget.setCellWidget(row_no, col_no, None)
            return

        image_label = QtWidgets.QLabel(in_table_widget)
        image_label.setText(f'''
            <img src="{image_file}" width="36" height="36" style="padding-left=10px"/>
        ''')

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(image_label)

        # 将布局的间距设置为 0 以完全居中
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(image_label, QtCore.Qt.AlignCenter)  # 水平和垂直居中
        widget.setLayout(layout)

        in_table_widget.setCellWidget(row_no, col_no, widget)

    def refresh_wait(self):
        self._set_current_period()

        self.read_wait()

    def _set_current_row(self):
        for row_no in range(self.ui.tableWidget_pharmacy_list.rowCount()):
            self.ui.tableWidget_pharmacy_list.setCurrentCell(row_no, 0)
            label_image = self.ui.tableWidget_pharmacy_list.cellWidget(row_no, 9)
            if label_image is None:
                break

    def _save_records(self, wait_key, case_key, drug_done="True"):
        if wait_key not in ["", None]:
            self.database.exec_sql(
                f'UPDATE wait SET DrugDone = "{drug_done}" WHERE WaitKey = {wait_key}'
            )

        if case_key in ["", None]:
            return

        fields = ["DrugDone"]
        data = [drug_done]

        self.database.update_record("cases", fields, "CaseKey", case_key, data)

    # 列印醫療收據
    def _print_receipt(self, case_key=None):
        sender_name = self.sender().objectName()
        if sender_name == "action_print_receipt":
            print_type = "選擇列印"
        else:
            print_type = "系統設定"

        if case_key is None:
            case_key = self.table_widget_charge_list.field_value(1)

        printer_utils.print_receipt_form(
            self, self.database, self.system_settings, case_key, print_type
        )

    # 列印藥袋
    def _print_prescript_bag(self, case_key=None):
        sender_name = self.sender().objectName()
        if sender_name == "action_print_misc":
            print_type = "選擇列印"
        else:
            print_type = "系統設定"

        if case_key is None:
            case_key = self.table_widget_charge_list.field_value(1)

        printer_utils.print_prescription_bag_form(
            self, self.database, self.system_settings, case_key, print_type
        )

    # 重新顯示已就診候診名單（保留給外部呼叫者，例如 refresh_wait）
    def _refresh_waiting_data(self, data):
        if self._is_pharmacy_busy():  # 配藥中不要重新顯示名單
            self._pending_reload = True
            return

        try:
            fields = data.split(",")
            if fields[0] != self.clinic_name:  # 其他分院呼叫
                return
            if fields[1] != "醫師看診作業":
                return
        except (AttributeError, IndexError):
            return

        self._read_pharmacy_list()

    # ------------------------------------------------------------------
    # 配藥狀態
    # ------------------------------------------------------------------
    def _set_pharmacy_processing(self, processing):
        """配藥狀態改用布林旗標，label 只是它的顯示。

        原本讀 label_status 的文字判斷，只要 dialog 中途例外跳出，
        狀態就永遠停在「調劑中」，通知從此不再運作，而且沒有任何錯誤。
        """
        self._processing = bool(processing)
        self.ui.label_status.setText("調劑中" if self._processing else "等待中")

    def _is_pharmacy_processing(self):
        """秤重對話框是否開著（只涵蓋那幾秒）"""
        return getattr(self, "_processing", False)

    def _is_pharmacy_busy(self):
        """配藥中：對話框開著，或這張處方配到一半還沒配完。

        通知重建名單要看的是這一個，不是 _is_pharmacy_processing()——
        藥師配完一味、正要拿下一味時，對話框是關著的，但這張處方還
        沒結束，這段期間名單絕不能動。
        """
        if self._is_pharmacy_processing():
            return True

        return self._is_one_pharmacy_processing() and not self._is_pharmacy_done()

    # 重新顯示狀態列
    def refresh_status_bar(self):
        today = datetime.datetime.today()
        weekday = date_utils.get_weekday_name(today.weekday())
        current_date = f"{today.strftime('%Y-%m-%d')} ({weekday[-1]})"
        self.label_today.setText(current_date)

        self.label_user_name.setText(f"使用者: {self.system_settings.field('使用者')}")
        self.label_station_no.setText(
            f"工作站編號: {self.system_settings.field('工作站編號')}"
        )
        self.label_ip.setText(f"本機IP: {self.system_settings.field('使用者IP')}")
        self.label_config_file.setText(f"設定檔: {self.config_file}")
        self.label_scale_time.setText(f"版本: {self.version}")
        self.label_server_ip.setText(f"伺服器IP: {self.host}")

    def _set_scale_time(self):
        input_dialog = QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")
        scale_time, ok = input_dialog.getDouble(
            self,
            "設定測重時間",
            "請輸入電子秤測重時間",
            self.scale_time,
            0.5,
            10,
            1,
            QtCore.Qt.WindowFlags(),
            0.1,
        )
        if not ok:
            return

        self.scale_time = scale_time
        self.system_settings.post("電子秤測重時間", self.scale_time)
        self.label_scale_time.setText("電子秤測重時間: " + str(self.scale_time) + "秒")


def set_high_dpi_attributes():
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_Use96Dpi, True)
    # QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)


def set_windows_scale_factor():
    hDC = win32gui.GetDC(0)
    real_width = win32print.GetDeviceCaps(hDC, win32con.DESKTOPHORZRES)
    screen_scale_rate = "1.25" if real_width == 2560 else "1.0"
    os.environ["QT_SCALE_FACTOR"] = screen_scale_rate


def handle_login(py_pharmacy):
    login_dialog = module_utils.get_login(
        py_pharmacy, py_pharmacy.database, py_pharmacy.system_settings
    )
    login_dialog.exec_()
    if not login_dialog.login_ok:
        login_dialog.deleteLater()
        py_pharmacy.deleteLater()

        return None, None

    user_name = login_dialog.user_name
    position = login_dialog.position
    login_dialog.deleteLater()

    return user_name, position


def setup_user_environment(py_pharmacy, user_name, position):
    current_ip_address = system_utils.get_ip()

    py_pharmacy.system_settings.post("使用者", user_name)
    py_pharmacy.system_settings.post("使用者ip", current_ip_address)
    py_pharmacy.system_settings.post(
        "登入日期", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    py_pharmacy.refresh_status_bar()
    QtWidgets.qApp.processEvents()


def configure_main_window(py_pharmacy, config):
    try:
        full_screen = config["settings"].getboolean("full_screen")
    except Exception:
        full_screen = True

    if full_screen is None:
        full_screen = True

    if full_screen:
        QtCore.QTimer.singleShot(1000, py_pharmacy.showMaximized)
        py_pharmacy.showMaximized()
    else:
        py_pharmacy.resize(1920, 1080)
        system_utils.center_window(py_pharmacy)
        py_pharmacy.show()


# 主程式
def main():
    set_high_dpi_attributes()
    if sys.platform == "win32":
        set_windows_scale_factor()

    app = QtWidgets.QApplication(sys.argv)
    QtGui.QFontDatabase.addApplicationFont("code128.ttf")

    translator = QtCore.QTranslator()
    translator.load("./qtbase_zh_TW.qm")
    app.installTranslator(translator)

    py_pharmacy = PyPharmacy(None, sys.argv)

    # user_name, position = handle_login(py_pharmacy)
    # if not user_name:
    #     return

    # setup_user_environment(py_pharmacy, user_name, position)
    configure_main_window(py_pharmacy, config)
    sys.exit(app.exec_())


# 程式進入點
if __name__ == "__main__":
    try:
        config_file = sys.argv[1]
    except IndexError:
        config_file = "pymedical.conf"

    config = configparser.ConfigParser()
    config.read(config_file)
    try:
        run_as_admin = config["settings"].getboolean("run_as_admin")
    except KeyError:
        run_as_admin = False

    if sys.platform == "win32" and run_as_admin:
        if not pyuac.isUserAdmin():
            pyuac.runAsAdmin()
        else:
            main()
    else:
        main()
