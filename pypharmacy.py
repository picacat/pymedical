# 藥局作業 2024.08.25
# -*- coding: UTF-8 -*-

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
        pass

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

        # highlight_color = self.ui.tableWidget_prescript.palette().color(QtGui.QPalette.Highlight)
        # highlight_color_str = highlight_color.name()
        # selection_style = f'''
        #     QTableWidget::item:selected {{
        #         color: white;  /* 设置选中的文字颜色为白色 */
        #         background-color: {highlight_color_str};  /* 设置选中的背景色为蓝色 */
        #         font-size: 24pt;
        #     }}
        # '''
        # self.ui.tableWidget_pharmacy_list.setStyleSheet(selection_style)
        # self.ui.tableWidget_prescript.setStyleSheet(selection_style)

    def _set_notification_server(self):
        channels = [notification_utils.CHANNEL_WAITING_LIST]
        self.notification_server = notification_utils.NotificationServer(
            self,
            database=self.database,
            station="pymedical",
            channels=channels,
        )
        self.notification_server.update_signal.connect(self._on_notification)

    def _on_notification(self, channel, message):
        if channel == notification_utils.CHANNEL_WAITING_LIST:
            self._refresh_waiting_data(message)

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
        if sys.platform == "win32":
            com_port = f"COM{self.com_port}"
        elif sys.platform == "linux":
            com_port = f"/dev/ttyUSB{self.com_port}"

        return com_port

    def _is_scale_reset_to_zero(self):
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

        time_out = 0
        while True:  # 只在running為True時執行
            try:
                try:
                    data = ser.readline().decode("ascii").strip()
                except Exception:
                    continue

                if "No." in data:
                    continue

                data = data.replace("g", "")
                weight = round(number_utils.get_float(data), 1)
                if weight == 0 or time_out > 10:
                    break

                time_out += 1
                time.sleep(0.2)
            except serial.SerialException as e:
                print(f"init com port failed: {e}")
                continue

        ser.close()

        weight = round(number_utils.get_float(data), 1)
        if weight > 0:
            return False
        else:
            return True

    def open_dialog_pharmacy(self, data):
        case_key = self.table_widget_charge_list.field_value(1)
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

        prescript_key, current_medicine_key = None, None
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            current_medicine_key = self.ui.tableWidget_prescript.item(row_no, 1)
            if current_medicine_key is None:
                continue

            current_medicine_key = current_medicine_key.text()
            if current_medicine_key != medicine_key:
                continue

            prescript_key = self.ui.tableWidget_prescript.item(row_no, 0)
            if prescript_key is None:
                continue

            prescript_key = prescript_key.text()
            medicine_name = self.ui.tableWidget_prescript.item(row_no, 2).text()
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

        self.ui.label_status.setText("調劑中")
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

        dialog.exec_()
        del dialog

        # self.activateWindow()
        self.raise_()

        case_key = self.table_widget_charge_list.field_value(1)
        self._read_prescript(case_key)
        self.ui.tableWidget_prescript.setFocus()
        QtCore.QTimer.singleShot(0, lambda: self._focus_prescript())

        if not self._is_one_pharmacy_processing() or self._is_pharmacy_done():
            self.ui.label_status.setText("等待中")
            self._filter_pharmacy_list()
            self._read_pharmacy_list()
            case_key = self.table_widget_charge_list.field_value(1)
            self._read_prescript(case_key)

        # self.activateWindow()
        self.raise_()
        self.ui.tableWidget_prescript.setFocus()
        QtCore.QTimer.singleShot(0, lambda: self._focus_prescript())

    def _focus_prescript(self):
        # 如果需要帶理由：
        # self.ui.tableWidget_prescript.setFocus(QtCore.Qt.OtherFocusReason)
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

    def _read_pharmacy_list(self):
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

        self.table_widget_charge_list.set_db_data(sql, self._set_pharmacy_list)
        self._pharmacy_list_changed()

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
        current_row_no = self.ui.tableWidget_pharmacy_list.currentRow()

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
        if medicine_set is None:
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
        if medicine_set is None:
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
            # elif col_no in [3]:
            #     self.ui.tableWidget_prescript.item(
            #         row_no, col_no).setTextAlignment(
            #         QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
            #     )

        self._set_prescript_ok(prescript_key, row_no, 6)

    def _set_row_color(self, in_table_widget, row_no, color):
        for col_no in range(in_table_widget.columnCount()):
            in_table_widget.item(row_no, col_no).setForeground(QtGui.QColor(color))

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

    # 重新顯示已就診候診名單
    def _refresh_waiting_data(self, data):
        if self._is_pharmacy_processing():  # 如果正在調劑，不要重新顯示名單
            return

        clinic_name = data.split(",")[0]
        if clinic_name != self.clinic_name:  # 其他分院呼叫
            return

        call_from = data.split(",")[1]
        if call_from == "醫師看診作業":
            self._read_pharmacy_list()

    # 是否正在調劑
    def _is_pharmacy_processing(self):
        if self.ui.label_status.text() == "調劑中":
            return True
        else:
            return False

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
