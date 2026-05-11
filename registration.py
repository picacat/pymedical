# -* coding: utf-8 -*-

import datetime
import platform
import re
import subprocess
import sys

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (
    alleypin_utils,
    case_utils,
    charge_utils,
    class_utils,
    cshis_utils,
    date_utils,
    dialog_utils,
    log_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    personnel_utils,
    prescript_utils,
    printer_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
    validator_utils,
    vhc_utils,
    web_utils,
)


# 門診掛號 2026-04-09
class Registration(QtWidgets.QMainWindow):
    """門診掛號 2018.01.22."""

    program_name = "門診掛號"

    # 初始化
    def __init__(self, parent=None, *args):
        """掛號作業初始化."""
        super(Registration, self).__init__(parent)
        self._parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None
        self.dialog_history = dialog_utils.get_dialog_past_history(
            self, self.database, self.system_settings
        )
        self.socket_client = class_utils.get_socket_client()
        self.reserve_key = None
        self.user_name = system_utils.get_user_name(self.system_settings)
        self.vhc_ic_card = None

        self.smart_card_reader = None

        self.pregnant_treat_type_list = ["助孕照護", "保胎照護"]
        self.temp_card_list = ["XX1", "XX2", "XX3", "XX4", "XX5"]
        self.wait_column = {
            "WaitKey": 0,
            "CaseKey": 1,
            "Progress": 2,
            "CaseTime": 3,
            "PatientKey": 4,
            "Name": 5,
            "Room": 6,
            "RegistNo": 7,
            "Gender": 8,
            "InsType": 9,
            "RegistType": 10,
            "ShareType": 11,
            "TreatType": 12,
            "Visit": 13,
            "Card": 14,
            "Doctor": 15,
            "RegistFee": 16,
            "DiagShareFee": 17,
            "DepositFee": 18,
            "SelfMassageFee": 19,
            "ReqCode": 20,
            "Massager": 21,
            "Remark": 22,
        }
        self.wait_done_column = {
            "WaitKey": 0,
            "CaseKey": 1,
            "PatientKey": 2,
            "Name": 3,
            "Gender": 4,
            "InsType": 5,
            "ShareType": 6,
            "TreatType": 7,
            "PresDays": 8,
            "Visit": 9,
            "Card": 10,
            "Room": 11,
            "RegistNo": 12,
            "WriteCard": 13,
            "Doctor": 14,
            "DrugNo": 15,
            "RegistFee": 16,
            "DiagShareFee": 17,
            "DrugShareFee": 18,
            "DepositFee": 19,
            "TotalFee": 20,
            "MassageFee": 21,
            "ReceiptFee": 22,
            "Remark": 23,
        }

        self.default_treat_type = self.system_settings.field("預設就醫類別")
        if self.default_treat_type is None:
            self.default_treat_type = "內科"

        self.led_port = self.system_settings.field("叫號燈連接埠")
        self.led_ip = self.system_settings.field("叫號燈ip")
        self.tab_corner_widget = None

        self._set_ui()
        self._set_signal()
        self._set_permission()

        if (
            self.system_settings.field("使用讀卡機") == "N"
            and self.system_settings.field("新特約期間使用晶片讀卡機") == "Y"
        ):
            self._init_smart_card()

    # 解構
    def __del__(self):
        self.close_all()
        try:
            self.dialog_history.close()
        except Exception:
            pass

    # 關閉
    def close_all(self):
        self.socket_client.close()

    def close_tab(self):
        current_tab = self._parent.ui.tabWidget_window.currentIndex()
        self._parent.close_tab(current_tab)

    def close_registration(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_REGISTRATION, self)

        system_utils.set_css(self, self.system_settings)
        # ui_utils.set_completer(
        #     self.database,
        #     'SELECT Name FROM patient GROUP BY Name ORDER BY Name',
        #     'Name',
        #     self.ui.lineEdit_query
        # )
        self.table_widget_wait = class_utils.get_table_widget(
            self.ui.tableWidget_wait, self.database
        )
        self.table_widget_wait.set_column_hidden([0, 1])
        self.table_widget_wait.set_parent(self._parent)
        self.table_widget_wait_completed = class_utils.get_table_widget(
            self.ui.tableWidget_wait_completed, self.database
        )
        self.table_widget_wait_completed.set_column_hidden([0, 1])

        if self.system_settings.field("掛號名單顯示民俗調理費") != "Y":  # 顯示速度太慢
            self.table_widget_wait.set_column_hidden(
                [self.wait_column["SelfMassageFee"]]
            )
            self.table_widget_wait_completed.set_column_hidden(
                [self.wait_done_column["MassageFee"]]
            )

        self.table_widget_first_visit = class_utils.get_table_widget(
            self.ui.tableWidget_first_visit, self.database
        )
        self.ui.lineEdit_query.setFocus()
        self._set_reg_mode(True)
        self._set_combo_box()
        self._set_table_width()
        self._set_reader_status()

        self.ui.tabWidget_list.setCurrentIndex(0)
        if self.system_settings.field("掛號作業顯示初診統計") == "Y":
            self.ui.groupBox_visit_count.setVisible(True)
        else:
            self.ui.groupBox_visit_count.setVisible(False)

        period = registration_utils.get_current_period(self.system_settings)
        self._set_radio_button_period(period)

        if (
            personnel_utils.get_permission(
                self.database, "病患資料", "遮蔽電話地址", self.user_name
            )
            == "Y"
        ):
            self.ui.lineEdit_telephone.setEchoMode(QtWidgets.QLineEdit.Password)
            self.ui.lineEdit_cellphone.setEchoMode(QtWidgets.QLineEdit.Password)
            self.ui.lineEdit_address.setEchoMode(QtWidgets.QLineEdit.Password)

        system_utils.disable_mouse_wheel(self, QtWidgets.QComboBox)
        system_utils.disable_mouse_wheel(self, QtWidgets.QSpinBox)
        system_utils.disable_mouse_wheel(self, QtWidgets.QDateTimeEdit)

        if self.system_settings.field("掛號類別") == "居家醫療":
            self.ui.label_massage_fee.setText("代收費")

        if self.system_settings.field("讀卡機控制軟體版本") == "cshis6":
            self.ui.checkBox_request_token.setEnabled(True)
        else:
            self.ui.checkBox_request_token.setEnabled(False)

        led_list = self._get_led_list()
        if len(led_list) > 0:
            self._set_tab_widget_corner_widget()

    def _set_tab_widget_corner_widget(self):
        self.tab_corner_widget = QtWidgets.QWidget()

        h_layout = QtWidgets.QHBoxLayout(self.tab_corner_widget)
        h_layout.setContentsMargins(4, 4, 4, 4)
        h_layout.setSpacing(8)

        self._set_calling_bulletin_led(self.tab_corner_widget, h_layout)
        self.ui.tabWidget_list.setCornerWidget(
            self.tab_corner_widget, QtCore.Qt.TopRightCorner
        )

    def _set_calling_bulletin_led(self, tab_corner_widget, h_layout):
        label = QtWidgets.QLabel(tab_corner_widget)
        label.setText("叫號燈: ")
        h_layout.addWidget(label)

        self.label_led_info = QtWidgets.QLabel(tab_corner_widget)
        h_layout.addWidget(self.label_led_info)

        self._refresh_led_list()

    def _refresh_led_list(self):
        self.led_list = self._get_led_list()
        if len(self.led_list) <= 0:
            return

        if self.tab_corner_widget is None:
            self._set_tab_widget_corner_widget()

        led_info = []
        for item in self.led_list:
            room = item[0]
            seq_number = item[1]
            led_info.append(f"{room}診: {seq_number}號")

        self.label_led_info.setText(", ".join(led_info))

    def _get_led_list(self):
        sql = """
            SELECT * FROM seq_number
            WHERE
                Room > 0
            GROUP BY Room ORDER BY Room
        """
        rows = self.database.select_record(sql)

        led_list = []
        for row in rows:
            room = number_utils.get_integer(row["Room"])
            sql = f"SELECT SeqNumber FROM seq_number WHERE Room = {room}"
            seq_rows = self.database.select_record(sql)
            if len(seq_rows) > 0:
                seq_number = number_utils.get_integer(seq_rows[0]["SeqNumber"])
                led_list.append([room, seq_number])

        return led_list

    def _set_radio_button_period(self, period):
        if period == "早班":
            self.ui.radioButton_period1.setChecked(True)
        elif period == "午班":
            self.ui.radioButton_period2.setChecked(True)
        elif period == "晚班":
            self.ui.radioButton_period3.setChecked(True)

    # 設定信號
    def _set_signal(self):
        self.ui.action_new_patient.triggered.connect(self._new_patient)
        self.ui.action_reservation.triggered.connect(self._reservation)
        self.ui.action_cancel.triggered.connect(self._cancel_registration)
        self.ui.action_ic_card.triggered.connect(self._registration_by_ic_card)
        self.ui.action_vhc_ic_card.triggered.connect(
            lambda: self._registration_by_vhc_ic_card(None)
        )
        self.ui.action_read_vhc_image.triggered.connect(self._read_vhc_image)
        self.ui.action_save.triggered.connect(self._save_records)
        self.ui.action_save_no_print.triggered.connect(self._save_records)
        self.ui.action_close.triggered.connect(self.close_registration)
        self.ui.action_clear_wait.triggered.connect(self._clear_wait)
        self.ui.action_med_vpn.triggered.connect(self._open_med_vpn)
        self.ui.action_med_vpn_vhc.triggered.connect(self._open_med_vpn)
        self.ui.action_quick_write_ic_card.triggered.connect(
            self._action_quick_write_ic_treatment
        )
        self.ui.action_print_registration.triggered.connect(self.print_wait)
        self.ui.action_print_massage.triggered.connect(self.print_wait_massage)

        self.ui.action_write_ic_treatment_by_qrcode.triggered.connect(
            self.write_ic_treatment_by_qrcode
        )
        self.ui.action_rewrite_vhc_card.triggered.connect(
            lambda: self.rewrite_vhc_card_by_qrcode(None)
        )
        self.ui.action_rewrite_vhc_prescript.triggered.connect(
            self.rewrite_vhc_prescript_by_qrcode
        )

        self.ui.toolButton_query.clicked.connect(self.query_patient)
        self.ui.toolButton_delete_wait.clicked.connect(
            lambda: self.delete_wait_list(show_warning=True)
        )
        self.ui.toolButton_ic_cancel.clicked.connect(self.cancel_ic_card)
        self.ui.toolButton_print_wait.clicked.connect(self.print_wait)
        self.ui.toolButton_print_wait_2.clicked.connect(self.print_wait)
        self.ui.toolButton_precheck.clicked.connect(self._exam_precheck)
        self.ui.toolButton_precheck2.clicked.connect(self._exam_precheck)
        # self.ui.toolButton_print_prescript.clicked.connect(self._print_prescript)
        self.ui.toolButton_print_receipt.clicked.connect(self._print_receipt)
        self.ui.toolButton_print_misc1.clicked.connect(self._print_misc1)
        self.ui.toolButton_print_misc2.clicked.connect(self._print_misc2)
        self.ui.toolButton_modify_patient.clicked.connect(self._modify_patient)
        self.ui.toolButton_modify_patient2.clicked.connect(self._modify_patient)
        self.ui.toolButton_modify_wait.clicked.connect(self._modify_wait)
        self.ui.toolButton_edit_cases.clicked.connect(self._modify_wait)
        self.ui.toolButton_ic_cancel_2.clicked.connect(self.cancel_ic_card)
        self.ui.toolButton_write_ic_treatment.clicked.connect(self.write_ic_treatment)
        self.ui.toolButton_rewrite_ic_card.clicked.connect(self.rewrite_ic_card)
        self.ui.action_rewrite_identifier.triggered.connect(self._rewrite_identifier)
        self.ui.action_rewrite_vhc_card_all.triggered.connect(
            lambda: self.rewrite_ic_card("虛擬健保卡")
        )
        self.ui.toolButton_rewrite_ic_prescript.clicked.connect(
            self.rewrite_ic_prescript
        )
        self.ui.toolButton_quick_ic_card.clicked.connect(self._quick_write_ic_treatment)
        self.ui.toolButton_request_req_code.clicked.connect(
            lambda: self._request_req_code(show_message=True)
        )
        self.ui.toolButton_vhc_get_seq_number.clicked.connect(self._vhc_get_seq_number)
        self.ui.toolButton_past_history.clicked.connect(self._open_past_history)

        self.ui.tableWidget_wait.doubleClicked.connect(self._modify_wait)
        self.ui.tableWidget_wait_completed.doubleClicked.connect(self._modify_wait)

        self.ui.lineEdit_query.returnPressed.connect(self.query_patient)
        self.ui.comboBox_reg_type.currentIndexChanged.connect(self._selection_changed)
        self.ui.comboBox_patient_share.currentIndexChanged.connect(
            self._selection_changed
        )
        self.ui.comboBox_patient_discount.currentIndexChanged.connect(
            self._selection_changed
        )
        self.ui.comboBox_ins_type.currentIndexChanged.connect(self._selection_changed)
        self.ui.comboBox_share_type.currentIndexChanged.connect(self._selection_changed)
        self.ui.comboBox_injury_type.currentIndexChanged.connect(
            self._selection_changed
        )
        self.ui.comboBox_treat_type.currentIndexChanged.connect(self._selection_changed)
        self.ui.comboBox_card.currentTextChanged.connect(self._selection_changed)
        self.ui.comboBox_course.currentIndexChanged.connect(self._selection_changed)
        self.ui.comboBox_visit.currentIndexChanged.connect(self._selection_changed)
        self.ui.comboBox_doctor.currentIndexChanged.connect(self._selection_changed)
        self.ui.comboBox_massager.currentIndexChanged.connect(self._selection_changed)
        self.ui.comboBox_period.currentIndexChanged.connect(self._selection_changed)
        self.ui.comboBox_room.currentIndexChanged.connect(self._selection_changed)
        self.ui.comboBox_patient_discount.currentIndexChanged.connect(
            self._set_regist_fee
        )
        self.ui.comboBox_remark.currentIndexChanged.connect(self._set_massage_fee)

        self.ui.lineEdit_regist_fee.textChanged.connect(self._selection_changed)
        self.ui.lineEdit_diag_share_fee.textChanged.connect(self._selection_changed)
        self.ui.lineEdit_deposit_fee.textChanged.connect(self._selection_changed)
        self.ui.lineEdit_traditional_health_care_fee.textChanged.connect(
            self._selection_changed
        )
        self.ui.tabWidget_list.currentChanged.connect(
            self._waiting_list_tab_changed
        )  # 切換分頁
        self.ui.tableWidget_wait_completed.itemSelectionChanged.connect(
            self._wait_completed_table_item_changed
        )
        self.ui.tableWidget_wait.itemSelectionChanged.connect(
            self._wait_table_item_changed
        )
        self.ui.spinBox_reg_no.valueChanged.connect(self._spin_box_reg_no_changed)

        self.ui.radioButton_all.clicked.connect(self._read_wait_completed)
        self.ui.radioButton_period1.clicked.connect(self._read_wait_completed)
        self.ui.radioButton_period2.clicked.connect(self._read_wait_completed)
        self.ui.radioButton_period3.clicked.connect(self._read_wait_completed)

        self.ui.dateEdit_case_date.dateChanged.connect(self._case_date_changed)
        self.ui.checkBox_easy_mode.clicked.connect(self._set_easy_mode)
        self.ui.checkBox_vegetarian.clicked.connect(self._set_vegetarian_color)
        self.ui.checkBox_no_nhi_vpn.clicked.connect(self._set_no_nhi_vpn)

    def _set_no_nhi_vpn(self):
        check_box = self.ui.checkBox_no_nhi_vpn
        if check_box.isChecked():
            style_sheet = "color:red; font-weight:bold"
            enabled = False
        else:
            style_sheet = None
            enabled = True

        check_box.setStyleSheet(style_sheet)
        self.ui.checkBox_request_token.setEnabled(enabled)

    def _set_vegetarian_color(self):
        check_box = self.ui.checkBox_vegetarian
        if check_box.isChecked():
            check_box.setStyleSheet("color:red; font-weight:bold")
        else:
            check_box.setStyleSheet(None)

    def _case_date_changed(self):
        if self._is_today():
            return

        custom_date = self.ui.dateEdit_case_date.date().toString("yyyy-MM-dd")
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("更改門診日期")
        msg_box.setText(
            f"""
            <font size="5" color="red">
                <b>確定要將門診日期改為 {custom_date} 嗎?
            </font>
            """
        )
        msg_box.setInformativeText("請確認門診日期是否變更")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        apply_change = msg_box.exec_()
        if not apply_change:
            self.ui.dateEdit_case_date.setDate(datetime.datetime.today())

    def _set_permission(self):
        if self.user_name == "超級使用者":
            return

        if (
            personnel_utils.get_permission(
                self.database, "預約掛號", "執行預約掛號", self.user_name
            )
            != "Y"
        ):
            self.ui.action_reservation.setEnabled(False)

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "修正候診名單", self.user_name
            )
            != "Y"
        ):
            self.ui.toolButton_modify_wait.setEnabled(False)
            self.ui.toolButton_edit_cases.setEnabled(False)

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "刪除候診名單", self.user_name
            )
            != "Y"
        ):
            self.ui.toolButton_delete_wait.setEnabled(False)

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "健保卡退掛", self.user_name
            )
            != "Y"
        ):
            self.ui.toolButton_ic_cancel.setEnabled(False)
            self.ui.toolButton_ic_cancel_2.setEnabled(False)

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "健保卡寫卡", self.user_name
            )
            != "Y"
        ):
            self.ui.toolButton_write_ic_treatment.setEnabled(False)
            self.ui.toolButton_rewrite_ic_card.setEnabled(False)
            self.ui.toolButton_rewrite_ic_prescript.setEnabled(False)

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "病患資料修正", self.user_name
            )
            != "Y"
        ):
            self.ui.toolButton_modify_patient.setEnabled(False)
            self.ui.toolButton_modify_patient2.setEnabled(False)
            self.ui.toolButton_precheck2.setEnabled(False)

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "補印收據", self.user_name
            )
            != "Y"
        ):
            self.ui.toolButton_print_wait.setEnabled(False)
            self.ui.toolButton_print_wait_2.setEnabled(False)

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "初診掛號", self.user_name
            )
            != "Y"
        ):
            self.ui.action_new_patient.setEnabled(False)

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "清除非本日候診名單", self.user_name
            )
            != "Y"
        ):
            self.ui.action_clear_wait.setEnabled(False)

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "開啟雲端藥歷", self.user_name
            )
            != "Y"
        ):
            self.ui.action_med_vpn.setEnabled(False)

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "健保卡掛號", self.user_name
            )
            != "Y"
        ):
            self.ui.action_ic_card.setEnabled(False)
            self.ui.action_vhc_ic_card.setEnabled(False)

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "人工手動掛號", self.user_name
            )
            != "Y"
        ):
            self.ui.groupBox_search_patient.setEnabled(False)

    def _registration_by_ic_card(self):
        if self.smart_card_reader is not None:
            self._registration_by_smart_card()
            return

        self.vhc_ic_card = None
        ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        if ic_card.cshis is None:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "無法驅動讀卡機",
                '<font size="5" color="red"><b>無法載入健保讀卡機驅動程式, 無法執行健保卡掛號.</b></font>',
                "請確定讀卡機驅動程式是否正確.",
            )
            return

        if not ic_card.read_register_basic_data():
            return

        available_date, available_count = ic_card.get_card_status()
        ic_card.basic_data["card_valid_date"] = available_date
        ic_card.basic_data["card_available_count"] = available_count

        patient_id = ic_card.basic_data["patient_id"]
        sql = f'''
            SELECT * FROM patient
            WHERE
                ID = "{patient_id}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:  # 找不到資料
            if self._check_first_visit_reservation(ic_card):
                return

            self._select_new_patient(ic_card)
        else:
            row = rows[0]
            self._get_patient(row["ID"], ic_card)

    # 檢查是否有網路初診預約
    def _check_first_visit_reservation(self, ic_card):
        reservation_exists = False

        start_date = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
        end_date = datetime.datetime.now().strftime("%Y-%m-%d 23:59:59")

        patient_id = ic_card.basic_data["patient_id"]
        sql = f'''
            SELECT temp_patient.*, reserve.* FROM temp_patient
                LEFT JOIN reserve ON temp_patient.TempPatientKey = reserve.PatientKey
            WHERE
                ReserveDate BETWEEN "{start_date}" AND "{end_date}" AND
                Arrival = "False" AND
                temp_patient.ID = "{patient_id}"
        '''
        rows = self.database.select_record(sql)

        if len(rows) > 0:
            reservation_exists = True

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("今日已有初診預約掛號")
            msg_box.setText(
                """
                <font size="5" color="blue">
                  <b>此人今日已有初診預約掛號, 是否預約報到!<br>
                </font>
                """
            )
            msg_box.setInformativeText("初診預約掛號已存在")
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            arrival = msg_box.exec_()
            if arrival:
                self._parent.close_tab_by_name(
                    "新病患資料"
                )  # 先關閉可能已開啟的初診登錄頁面
                self._cancel_registration()
                reserve_key = rows[0]["ReserveKey"]
                self._parent.open_reservation(reserve_key, None, None)
            else:
                self._cancel_registration()

            return reservation_exists

    def _select_new_patient(self, ic_card):
        card_no = ic_card.basic_data["card_no"]
        name = ic_card.basic_data["name"]
        patient_id = ic_card.basic_data["patient_id"]
        birthday = ic_card.basic_data["birthday"]
        gender = ic_card.basic_data["gender"]
        card_date = ic_card.basic_data["card_date"]
        cancel_mark = ic_card.basic_data["cancel_mark"]
        insured_mark = ic_card.basic_data["insured_mark"]
        emg_phone = ic_card.basic_data["emg_phone"]

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("查無資料")
        msg_box.setText(f"""
            <font size="5" color="red">
              <b>資料庫內找不到此病患的資料, 是否為初診病患?</b><br><br>
            </font>
            <font size="5" color="black">
              <b>卡片號碼</b>: {card_no}<br>
              <b>病患姓名</b>: {name}<br>
              <b>身分證號</b>: {patient_id}<br>
              <b>出生日期</b>: {birthday}<br>
              <b>病患性別</b>: {gender}<br>
              <b>發卡日期</b>: {card_date}<br>
              <b>保險身份</b>: {insured_mark}<br>
              <b>卡片註記</b>: {cancel_mark}<br>
              <b>緊急電話</b>: {emg_phone}<br>
            </font>
        """)
        msg_box.setInformativeText(
            """
            <font color="blue">
              <b>如果不是初診病患, 請確定此人基本資料的身分證欄位是否正確!</b><br>
            <font>
            <font color="green">
              (請至->病患資料->查詢此人資料->修正身分證資料)
            <font>
            """
        )
        msg_box.addButton(QPushButton("確定初診病患"), QMessageBox.AcceptRole)  # 0
        msg_box.addButton(QPushButton("確定此人正確"), QMessageBox.AcceptRole)  # 1
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)  # 2
        result = msg_box.exec_()
        if result == 0:
            self._parent.close_tab_by_name(
                "新病患資料"
            )  # 先關閉可能已開啟的初診登錄頁面
            self._parent.open_patient_record(None, "門診掛號", ic_card)
        elif result == 1:  # 此人正確
            name = ic_card.basic_data["name"]
            birthday = ic_card.basic_data["birthday"]
            sql = f'''
                SELECT PatientKey, ID FROM patient
                WHERE
                    Name = "{name}" AND
                    Birthday = "{birthday}"
            '''
            rows = self.database.select_record(sql)
            if len(rows) != 1:
                return

            patient_key = rows[0]["PatientKey"]
            patient_id = ic_card.basic_data["patient_id"]
            sql = f'''
                UPDATE patient
                SET
                    ID = "{patient_id}"
                WHERE
                    PatientKey = {patient_key}
            '''
            self.database.exec_sql(sql)
            self._get_patient(patient_id, ic_card)

    # 初診掛號
    def _new_patient(self):
        self._parent.open_patient_record(None, "門診掛號")

    def _modify_patient(self):
        tab_name = self.ui.tabWidget_list.tabText(self.ui.tabWidget_list.currentIndex())
        if tab_name == "候診名單":
            patient_key = self.ui.tableWidget_wait.item(
                self.ui.tableWidget_wait.currentRow(), self.wait_column["PatientKey"]
            )
        else:
            patient_key = self.ui.tableWidget_wait_completed.item(
                self.ui.tableWidget_wait_completed.currentRow(),
                self.wait_done_column["PatientKey"],
            )

        if patient_key is None:
            return

        patient_key = patient_key.text()
        self._parent.open_patient_record(patient_key, "門診掛號")

    def _set_table_width(self):
        width = [
            100,
            100,
            45,
            60,
            70,
            85,
            20,
            45,
            45,
            50,
            90,
            90,
            100,
            50,
            80,
            30,
            80,
            80,
            80,
            80,
            80,
            80,
        ]
        # self.table_widget_wait.set_table_heading_width(width)

        width = [
            100,
            100,
            70,
            90,
            45,
            50,
            80,
            100,
            40,
            50,
            65,
            30,
            30,
            50,
            60,
            80,
            80,
            80,
            80,
            80,
            400,
        ]
        # self.table_widget_wait_completed.set_table_heading_width(width)

        width = [120, 120, 120, 120]
        self.table_widget_first_visit.set_table_heading_width(width)

    def refresh_wait(self):
        self._refresh_led_list()

        if not self.ui.tabWidget_list.isEnabled():
            return

        self.read_wait()

    def read_wait(self):
        order_type = self.system_settings.field("掛號候診名單排序方式")
        if order_type == "時間排序":
            order_by_script = "ORDER BY wait.CaseDate, wait.Room"
        elif order_type == "診號排序":
            order_by_script = "ORDER BY wait.RegistNo, wait.Room"
        else:
            order_by_script = "ORDER BY wait.Room, wait.RegistNo"

        sql = f"""
            SELECT
                wait.*, patient.Gender, patient.ChartNo,
                cases.RegistFee, cases.SDiagShareFee, cases.DepositFee, cases.SMassageFee
            FROM wait
                LEFT JOIN patient ON wait.PatientKey = patient.PatientKey
                LEFT JOIN cases ON wait.CaseKey = cases.CaseKey
            WHERE
                wait.DoctorDone = "False"
            {order_by_script}
        """
        self.table_widget_wait.set_db_data(sql, self._set_wait_data)
        row_count = self.table_widget_wait.row_count()

        if row_count > 0:
            self._set_wait_tool_button(True)
        else:
            self._set_wait_tool_button(False)

        if self.system_settings.field("掛號作業顯示初診統計") == "Y":
            self._read_first_visit()

    def _read_first_visit(self):
        today = datetime.datetime.now()

        last_month = (
            datetime.date(today.year, today.month, 1) - datetime.timedelta(1)
        ).replace(day=1)
        start_date = f"{last_month} 00:00:00"
        end_date = f"{today.strftime('%Y-%m-%d')} 23:59:59"

        sql = f'''
            SELECT Doctor FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                InsType = "健保" AND
                Doctor IS NOT NULL AND LENGTH(Doctor) > 0
            GROUP BY Doctor
        '''
        self.table_widget_first_visit.set_db_data(sql, self._set_first_visit_data)

    def _get_visit_count(self, doctor):
        today = datetime.datetime.now()

        last_month = (
            datetime.date(today.year, today.month, 1) - datetime.timedelta(1)
        ).replace(day=1)
        start_date = f"{last_month} 00:00:00"
        end_date = f"{today.strftime('%Y-%m-%d')} 23:59:59"

        sql = f'''
            SELECT DesignatedDoctor FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                InsType = "健保" AND
                Visit = "初診" AND
                Doctor = "{doctor}"
        '''
        rows = self.database.select_record(sql)

        undesignated_doctor = 0
        designated_doctor = 0
        for row in rows:
            if string_utils.xstr(row["DesignatedDoctor"]) == "True":
                designated_doctor += 1
            else:
                undesignated_doctor += 1

        return undesignated_doctor, designated_doctor

    def _set_first_visit_data(self, row_no, row):
        doctor = string_utils.xstr(row["Doctor"])
        undesignated_doctor, designated_doctor = self._get_visit_count(doctor)

        first_visit_row = [
            doctor,
            undesignated_doctor,
            designated_doctor,
            undesignated_doctor + designated_doctor,
        ]

        for col_no in range(len(first_visit_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, first_visit_row[col_no])
            self.ui.tableWidget_first_visit.setItem(
                row_no,
                col_no,
                item,
            )
            if col_no in [1, 2, 3]:
                self.ui.tableWidget_first_visit.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    # 顯示資料
    def _set_wait_data(self, row_no, row):
        case_key = string_utils.xstr(row["CaseKey"])
        patient_key = row["PatientKey"]

        # chart_no = row['ChartNo']
        # if chart_no not in [None, '']:
        #     patient_key = '*' + chart_no

        case_time = string_utils.xstr(row["CaseDate"].time())[:5]
        card = string_utils.xstr(row["Card"])
        course = number_utils.get_integer(row["Continuance"])

        card_str = self._set_card(card, course)
        ins_type = string_utils.xstr(row["InsType"])
        if self.system_settings.field("掛號名單顯示民俗調理費") == "Y":  # 顯示速度太慢
            traditional_health_care_fee = (
                charge_utils.get_traditional_health_care_fee_from_case(
                    self.database, case_key, ins_type=ins_type
                )
            )
        else:
            traditional_health_care_fee = 0

        wait_row = [
            string_utils.xstr(row["WaitKey"]),
            case_key,
            None,
            case_time,
            patient_key,
            string_utils.xstr(row["Name"]),
            row["Room"],
            row["RegistNo"],
            string_utils.xstr(row["Gender"]),
            ins_type,
            string_utils.xstr(row["RegistType"]),
            string_utils.xstr(row["Share"]),
            string_utils.xstr(row["TreatType"])[:10],
            string_utils.xstr(row["Visit"]),
            card_str,
            string_utils.xstr(row["Doctor"]),
            string_utils.xstr(row["RegistFee"]),
            string_utils.xstr(row["SDiagShareFee"]),
            string_utils.xstr(row["DepositFee"]),
            traditional_health_care_fee,
            string_utils.xstr(row["Massager"]),
            string_utils.xstr(row["Remark"]),
        ]

        in_progress = string_utils.xstr(row["InProgress"])
        case_utils.set_in_progress_icon(
            self.ui.tableWidget_wait, row_no, self.wait_column["Progress"], in_progress
        )

        for col_no in range(len(wait_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, wait_row[col_no])
            self.ui.tableWidget_wait.setItem(
                row_no,
                col_no,
                item,
            )
            if col_no in [
                self.wait_column["PatientKey"],
                self.wait_column["RegistNo"],
                self.wait_column["RegistFee"],
                self.wait_column["DiagShareFee"],
                self.wait_column["DepositFee"],
                self.wait_column["SelfMassageFee"],
            ]:
                self.ui.tableWidget_wait.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [
                self.wait_column["Progress"],
                self.wait_column["CaseTime"],
                self.wait_column["Room"],
                self.wait_column["Gender"],
                self.wait_column["InsType"],
                self.wait_column["Visit"],
            ]:
                self.ui.tableWidget_wait.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            color = None
            if in_progress == "Y":
                color = "red"
            elif row["Visit"] == "初診":
                color = "darkgreen"
            elif row["RegistType"] == "預約門診":
                color = "purple"
            elif row["InsType"] == "自費":
                color = "blue"

            if color is not None:
                self.ui.tableWidget_wait.item(row_no, col_no).setForeground(
                    QtGui.QColor(color)
                )

    def _set_wait_tool_button(self, enabled):
        self.ui.toolButton_modify_wait.setEnabled(enabled)
        self.ui.toolButton_delete_wait.setEnabled(enabled)
        self.ui.toolButton_ic_cancel.setEnabled(enabled)
        self.ui.toolButton_modify_patient.setEnabled(enabled)
        self.ui.toolButton_print_wait.setEnabled(enabled)
        self.ui.toolButton_precheck.setEnabled(enabled)
        self.ui.toolButton_request_req_code.setEnabled(enabled)
        self.ui.toolButton_vhc_get_seq_number.setEnabled(enabled)
        self.ui.toolButton_past_history.setEnabled(enabled)
        if self.system_settings.field("使用讀卡機") == "N":
            self.ui.toolButton_ic_cancel.setEnabled(False)

        self._set_permission()

    def _set_wait_completed_tool_button(self, enabled):
        self.ui.toolButton_edit_cases.setEnabled(enabled)
        self.ui.toolButton_write_ic_treatment.setEnabled(enabled)
        self.ui.toolButton_ic_cancel_2.setEnabled(enabled)
        self.ui.toolButton_modify_patient2.setEnabled(enabled)
        self.ui.toolButton_precheck2.setEnabled(enabled)
        self.ui.toolButton_print_wait_2.setEnabled(enabled)
        # self.ui.toolButton_print_prescript.setEnabled(enabled)
        self.ui.toolButton_print_receipt.setEnabled(enabled)
        self.ui.toolButton_print_misc1.setEnabled(enabled)
        self.ui.toolButton_print_misc2.setEnabled(enabled)
        if self.system_settings.field("使用讀卡機") == "N":
            self.ui.toolButton_write_ic_treatment.setEnabled(False)
            self.ui.toolButton_ic_cancel_2.setEnabled(False)

        self._set_permission()

    def _set_reader_status(self):
        if self.system_settings.field("使用讀卡機") == "N":
            self.ui.action_ic_card.setEnabled(False)
            self.ui.action_vhc_ic_card.setEnabled(False)

            if self.system_settings.field("新特約期間使用晶片讀卡機") == "Y":
                self.ui.action_ic_card.setEnabled(True)

    # 設定掛號模式
    def _set_reg_mode(self, enabled, ic_card=None):
        if enabled:
            self.ui.groupBox_registration.setTitle("掛號資料")

        if ic_card:
            try:
                valid_date = ic_card.basic_data["card_valid_date"]
                available_count = ic_card.basic_data["card_available_count"]
                self.ui.groupBox_patient.setTitle(
                    f"病患資料 - (健保卡有效期限至: {valid_date} 可用次數: {available_count}次)"
                )
            except Exception:
                self.ui.groupBox_patient.setTitle("病患資料")
        else:
            self.ui.groupBox_patient.setTitle("病患資料")

        self.ui.action_ic_card.setEnabled(enabled)
        self.ui.action_vhc_ic_card.setEnabled(enabled)

        if enabled:
            self._set_reader_status()

        self.ui.action_new_patient.setEnabled(enabled)
        self.ui.action_reservation.setEnabled(enabled)
        self.ui.action_cancel.setEnabled(not enabled)
        self.ui.action_save.setEnabled(not enabled)
        self.ui.action_save_no_print.setEnabled(not enabled)

        self.ui.groupBox_search_patient.setEnabled(enabled)
        self.ui.tabWidget_list.setEnabled(enabled)
        self.ui.groupBox_patient.setEnabled(not enabled)
        self.ui.groupBox_registration.setEnabled(not enabled)

        self.ui.comboBox_card_abnormal.setEnabled(False)
        # database.ui.tabWidget_list.setCurrentIndex(0)

        self._clear_group_box_patient()
        self._clear_group_box_registration()

        self._set_permission()

    # 清除病患資料欄位
    def _clear_group_box_patient(self):
        self.ui.lineEdit_patient_key.clear()
        self.ui.lineEdit_chart_no.clear()
        self.ui.lineEdit_name.clear()
        self.ui.lineEdit_id.clear()
        self.ui.lineEdit_birthday.clear()
        self.ui.lineEdit_telephone.clear()
        self.ui.lineEdit_cellphone.clear()
        self.ui.lineEdit_address.clear()
        self.ui.lineEdit_patient_remark.clear()
        self.ui.comboBox_patient_share.setCurrentIndex(0)
        self.ui.comboBox_patient_discount.setCurrentIndex(0)
        self.ui.comboBox_gender.setCurrentIndex(0)
        self.ui.lineEdit_age.setText(None)
        self.ui.checkBox_vegetarian.setChecked(False)
        self.ui.checkBox_vegetarian.setStyleSheet(None)

    # 清除掛號資料欄位
    def _clear_group_box_registration(self):
        self._check_area()

        self.ui.comboBox_visit.setCurrentIndex(0)
        self.ui.comboBox_share_type.setCurrentIndex(0)
        self.ui.comboBox_injury_type.setCurrentIndex(0)
        self.ui.comboBox_treat_type.setCurrentIndex(0)

        self.ui.comboBox_card.setCurrentIndex(0)
        self.ui.comboBox_course.setCurrentIndex(0)
        self.ui.checkBox_request_token.setChecked(False)

        self.ui.comboBox_doctor.setCurrentIndex(0)
        self.ui.comboBox_massager.setCurrentIndex(0)
        self.ui.spinBox_reg_no.setValue(0)
        self.ui.comboBox_room.setCurrentIndex(0)
        self.ui.lineEdit_regist_fee.clear()
        self.ui.lineEdit_diag_share_fee.clear()
        self.ui.lineEdit_deposit_fee.clear()
        self.ui.lineEdit_traditional_health_care_fee.clear()
        self.ui.lineEdit_total_amount.clear()
        self.ui.lineEdit_receipt_fee.clear()
        self.ui.comboBox_remark.setCurrentIndex(0)
        self.ui.comboBox_payment_type.setCurrentIndex(0)

        self.ui.checkBox_designated_doctor.setChecked(False)
        self.ui.checkBox_designated_massager.setChecked(False)
        self.ui.dateEdit_case_date.setDate(datetime.datetime.today())

    # 設定 comboBox
    def _set_combo_box(self):
        ui_utils.set_combo_box(self.ui.comboBox_patient_share, nhi_utils.INSURED_TYPE)
        ui_utils.set_combo_box(
            self.ui.comboBox_patient_discount, "掛號優待", self.database
        )
        ui_utils.set_combo_box(self.ui.comboBox_ins_type, nhi_utils.INS_TYPE)
        ui_utils.set_combo_box(self.ui.comboBox_visit, nhi_utils.VISIT)

        ui_utils.set_combo_box(
            self.ui.comboBox_reg_type, nhi_utils.REG_TYPE, "一般門診"
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_injury_type, nhi_utils.INJURY_TYPE, "普通疾病"
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_share_type, nhi_utils.SHARE_TYPE, "基層醫療"
        )

        ui_utils.set_combo_box(self.ui.comboBox_card, nhi_utils.CARD)
        ui_utils.set_combo_box(self.ui.comboBox_course, nhi_utils.COURSE, None)
        ui_utils.set_combo_box(
            self.ui.comboBox_card_abnormal, nhi_utils.ABNORMAL_CARD_WITH_HINT, None
        )
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD)
        ui_utils.set_combo_box(self.ui.comboBox_room, nhi_utils.ROOM)
        ui_utils.set_combo_box(self.ui.comboBox_gender, nhi_utils.GENDER, None)
        # ui_utils.set_combo_box(
        #     self.ui.comboBox_doctor,
        #     personnel_utils.get_person(self.database, '醫師',
        #                                exclude_person='值班醫師', include_person='全部醫師'))
        ui_utils.set_combo_box(
            self.ui.comboBox_doctor,
            personnel_utils.get_person(
                self.database, "醫師", exclude_person="值班醫師"
            ),
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_massager,
            personnel_utils.get_person(self.database, "推拿師父"),
            None,
        )

        ui_utils.set_combo_box(self.ui.comboBox_payment_type, nhi_utils.PAYMENT_TYPE)
        system_utils.set_combo_box_treat_type(self.ui.comboBox_treat_type)
        self._set_combo_box_remark()

        self._check_area()

        ui_utils.set_combo_box_item_color(
            self.ui.comboBox_reg_type,
            [
                None,
                None,
                None,
                QtGui.QBrush(QtCore.Qt.red),
                QtGui.QBrush(QtCore.Qt.darkCyan),
                QtGui.QBrush(QtCore.Qt.darkCyan),
                QtGui.QBrush(QtCore.Qt.darkCyan),
                QtGui.QBrush(QtCore.Qt.darkBlue),
                QtGui.QBrush(QtCore.Qt.darkBlue),
                QtGui.QBrush(QtCore.Qt.darkBlue),
                QtGui.QBrush(QtCore.Qt.darkBlue),
                QtGui.QBrush(QtCore.Qt.darkBlue),
                QtGui.QBrush(QtCore.Qt.darkGreen),
                QtGui.QBrush(QtCore.Qt.darkGreen),
                QtGui.QBrush(QtCore.Qt.darkGreen),
                QtGui.QBrush(QtCore.Qt.darkGreen),
                QtGui.QBrush(QtCore.Qt.darkGreen),
                QtGui.QBrush(QtCore.Qt.blue),
                QtGui.QBrush(QtCore.Qt.blue),
                QtGui.QBrush(QtCore.Qt.blue),
                QtGui.QBrush(QtCore.Qt.blue),
                QtGui.QBrush(QtCore.Qt.magenta),
                QtGui.QBrush(QtCore.Qt.magenta),
            ],
        )
        ui_utils.set_combo_box_item_color(
            self.ui.comboBox_card,
            [
                None,
                None,
                QtGui.QBrush(QtCore.Qt.red),
                QtGui.QBrush(QtCore.Qt.blue),
                QtGui.QBrush(QtCore.Qt.blue),
                QtGui.QBrush(QtCore.Qt.darkCyan),
                QtGui.QBrush(QtCore.Qt.darkCyan),
                QtGui.QBrush(QtCore.Qt.darkCyan),
                QtGui.QBrush(QtCore.Qt.darkCyan),
                QtGui.QBrush(QtCore.Qt.darkCyan),
                QtGui.QBrush(QtCore.Qt.magenta),
                QtGui.QBrush(QtCore.Qt.magenta),
                QtGui.QBrush(QtCore.Qt.magenta),
                QtGui.QBrush(QtCore.Qt.darkGreen),
                QtGui.QBrush(QtCore.Qt.darkGreen),
                QtGui.QBrush(QtCore.Qt.darkGray),
                QtGui.QBrush(QtCore.Qt.darkGray),
                QtGui.QBrush(QtCore.Qt.darkGray),
                QtGui.QBrush(QtCore.Qt.darkRed),
                QtGui.QBrush(QtCore.Qt.darkGray),
                QtGui.QBrush(QtCore.Qt.darkGray),
            ],
        )

    def _set_combo_box_remark(self):
        sql = """
            SELECT ClinicName FROM clinic
            WHERE
                ClinicType = "備註"
            ORDER BY LENGTH(ClinicName), CAST(CONVERT(`ClinicName` using big5) AS BINARY)
        """
        rows = self.database.select_record(sql)
        remark_list = []
        for row in rows:
            remark_list.append(string_utils.xstr(row["ClinicName"]))

        ui_utils.set_combo_box(self.ui.comboBox_remark, remark_list, None)

    def _reset_action_button_text(self):
        self.ui.action_save.setText("掛號存檔[F10]")
        self.ui.action_save_no_print.setText("掛號存檔不印[F11]")
        self.ui.action_cancel.setText("取消掛號[Esc]")

        self._set_combo_box_color()

    # 取消掛號
    def _cancel_registration(self):
        self.reserve_key = None
        self.vhc_ic_card = None
        self._reset_action_button_text()
        self._set_reg_mode(True)
        self.ui.groupBox_search_patient.setEnabled(True)
        self.ui.lineEdit_query.setFocus()
        self.dialog_history.close()

        self._set_combo_box_color()

    def _get_card_sequence(self):
        if self.system_settings.field("產生安全簽章位置") == "診療":
            card_sequence = "IC"
        else:
            card_sequence = "自動取得"

        if self.system_settings.field("掛號類別") == "居家醫療":
            patient_key = self.ui.lineEdit_patient_key.text()
            today = date_utils.now_to_str()
            card_sequence = nhi_utils.get_home_care_card(
                self.database, patient_key, today
            )
            if card_sequence is not None and card_sequence[:4] in ["F000"]:
                card_sequence = "自動取得"

        return card_sequence

    # comboBox 內容變更
    def _selection_changed(self):
        sender_name = self.sender().objectName()
        card = self._get_card(self.ui.comboBox_card.currentText(), " ")

        if sender_name == "comboBox_patient_share":
            self.ui.comboBox_share_type.setCurrentText(
                self.ui.comboBox_patient_share.currentText()
            )
            self._set_diag_share_fee()
        elif sender_name == "comboBox_patient_discount":
            self._set_regist_fee()
            self._set_diag_share_fee()
        elif sender_name == "comboBox_ins_type":
            if self.ui.comboBox_ins_type.currentText() == "健保":
                card_sequence = self._get_card_sequence()
                self.ui.comboBox_card.setCurrentText(card_sequence)
            else:
                self.ui.comboBox_card.setCurrentText("免卡")

            self._set_regist_fee()
            self._set_diag_share_fee()
            self._set_deposit_fee()
            self._set_traditional_health_care_fee()
        elif sender_name == "comboBox_reg_type":
            self._check_area()
            if self.ui.comboBox_reg_type.currentText() in nhi_utils.TELECOM_TYPE:
                system_utils.show_message_box(
                    QMessageBox.Warning,
                    "視訊/電話門診",
                    '<font size="5" color="blue"><b>以視訊或電話門診方式就診, 仍須讀取健保卡，若要過卡，請選擇卡序「自動取得」</b></font>',
                    "請確定是否報請衛生局核准申報視訊門診。<br>以視訊門診之病人，請於視訊時出示健保卡核對身份，並拍照留存。",
                )
                if card[:4] != nhi_utils.INFECTIOUS_INJURY_CARD:
                    self.ui.comboBox_card.setCurrentText(
                        nhi_utils.INFECTIOUS_CARD_DICT[nhi_utils.INFECTIOUS_INJURY_CARD]
                    )
            elif (
                self.ui.comboBox_reg_type.currentText()
                in nhi_utils.SPECIAL_PHARMACY_TYPE
            ):
                system_utils.show_message_box(
                    QMessageBox.Warning,
                    "領取長期藥品",
                    '<font size="5" color="blue"><b>請病患提供切結文件, 一次領取2或3個月用藥</b></font>',
                    "預定出國者, 請提供機票或船票影本",
                )
            if self.ui.comboBox_reg_type.currentText() in nhi_utils.INFECTIOUS_TYPE:
                self.ui.comboBox_share_type.setCurrentText(
                    nhi_utils.INFECTIOUS_INJURY_TYPE[0]
                )
                self.ui.comboBox_injury_type.setCurrentText(
                    nhi_utils.INFECTIOUS_INJURY_TYPE[0]
                )

                if (
                    "修正存檔" in self.ui.action_save.text()
                    or "修正存檔不印" in self.ui.action_save_no_print.text()
                ):
                    case_key = self.ui.groupBox_registration.title().split("-")[-1]
                    infectious_date = case_utils.get_case_extend(
                        self.database, case_key, "確診日期"
                    )
                else:
                    infectious_date = None

                if infectious_date is None:
                    infectious_date = date_utils.get_dialog_date(
                        self,
                        self.database,
                        self.system_settings,
                        title="請選擇隔離通知書隔離日期或PCR陽性採檢日期",
                        current_date=datetime.datetime.today(),
                        date_type="date",
                        call_from=self.program_name,
                    )
                    if infectious_date is not None:
                        self.ui.comboBox_remark.setCurrentText(
                            f"確診日期: {infectious_date.toString('yyyy-MM-dd')}"
                        )
            elif (
                self.ui.comboBox_injury_type.currentText()
                not in nhi_utils.OCCUPATIONAL_INJURY_TYPE
            ):
                self.ui.comboBox_injury_type.setCurrentText("普通疾病")
                self.ui.comboBox_share_type.setCurrentText(
                    self.ui.comboBox_patient_share.currentText()
                )

            self._set_combo_box_color()
        elif sender_name == "comboBox_share_type":
            self._check_area()
            if (
                self.ui.comboBox_share_type.currentText()
                in nhi_utils.MAIN_OCCUPATIONAL_INJURY_TYPE
            ):
                if (
                    self.ui.comboBox_injury_type.currentText()
                    not in nhi_utils.MAIN_OCCUPATIONAL_INJURY_TYPE
                ):
                    self.ui.comboBox_injury_type.setCurrentText(
                        nhi_utils.MAIN_OCCUPATIONAL_INJURY_TYPE[0]
                    )
                if card[:4] != nhi_utils.OCCUPATIONAL_INJURY_CARD:
                    self.ui.comboBox_card.setCurrentText(
                        nhi_utils.INJURY_CARD_DICT[nhi_utils.OCCUPATIONAL_INJURY_CARD]
                    )
            elif (
                self.ui.comboBox_share_type.currentText()
                in nhi_utils.INFECTIOUS_INJURY_TYPE
            ):
                if (
                    self.ui.comboBox_injury_type.currentText()
                    not in nhi_utils.INFECTIOUS_INJURY_TYPE
                ):
                    self.ui.comboBox_injury_type.setCurrentText(
                        nhi_utils.INFECTIOUS_INJURY_TYPE[0]
                    )
                if card[:4] != nhi_utils.INFECTIOUS_INJURY_CARD:
                    self.ui.comboBox_card.setCurrentText(
                        nhi_utils.INFECTIOUS_CARD_DICT[nhi_utils.INFECTIOUS_INJURY_CARD]
                    )
            else:
                if self.ui.comboBox_injury_type.currentText() != "普通疾病":
                    self.ui.comboBox_injury_type.setCurrentText("普通疾病")
                    card_sequence = self._get_card_sequence()
                    self.ui.comboBox_card.setCurrentText(card_sequence)

            self._set_regist_fee()
            self._set_diag_share_fee()
            self._set_combo_box_color()
        elif sender_name == "comboBox_injury_type":
            if (
                self.ui.comboBox_injury_type.currentText()
                in nhi_utils.MAIN_OCCUPATIONAL_INJURY_TYPE
            ):
                if (
                    self.ui.comboBox_share_type.currentText()
                    != nhi_utils.MAIN_OCCUPATIONAL_INJURY_TYPE[0]
                ):
                    self.ui.comboBox_share_type.setCurrentText(
                        nhi_utils.MAIN_OCCUPATIONAL_INJURY_TYPE[0]
                    )
                if card[:4] != nhi_utils.OCCUPATIONAL_INJURY_CARD:
                    self.ui.comboBox_card.setCurrentText(
                        nhi_utils.INJURY_CARD_DICT[nhi_utils.OCCUPATIONAL_INJURY_CARD]
                    )
            elif (
                self.ui.comboBox_injury_type.currentText()
                in nhi_utils.INFECTIOUS_INJURY_TYPE
            ):
                if (
                    self.ui.comboBox_share_type.currentText()
                    != nhi_utils.INFECTIOUS_INJURY_TYPE[0]
                ):
                    self.ui.comboBox_share_type.setCurrentText(
                        nhi_utils.INFECTIOUS_INJURY_TYPE[0]
                    )
                if card[:4] != nhi_utils.INFECTIOUS_INJURY_CARD:
                    self.ui.comboBox_card.setCurrentText(
                        nhi_utils.INFECTIOUS_CARD_DICT[nhi_utils.INFECTIOUS_INJURY_CARD]
                    )
            else:
                if (
                    card[:4] != nhi_utils.OCCUPATIONAL_INJURY_CARD
                    and self.ui.comboBox_share_type.currentText()
                    != self.ui.comboBox_patient_share.currentText()
                ):
                    self.ui.comboBox_share_type.setCurrentText(
                        self.ui.comboBox_patient_share.currentText()
                    )
                    card_sequence = self._get_card_sequence()
                    self.ui.comboBox_card.setCurrentText(card_sequence)

            self._set_diag_share_fee()
        elif sender_name == "comboBox_treat_type":
            self._set_regist_fee()
            self._set_diag_share_fee()
            if (
                self.ui.comboBox_treat_type.currentText()
                in ["內科"] + nhi_utils.CARE_TREAT
            ):
                card_sequence = self._get_card_sequence()
                self.ui.comboBox_card.setCurrentText(card_sequence)
                self.ui.comboBox_course.setCurrentText(None)
            elif self.ui.comboBox_treat_type.currentText() in nhi_utils.TRI_HEAT_TREAT:
                self._set_self_fee(self.ui.comboBox_treat_type.currentText())
        elif sender_name == "comboBox_card":
            card = card.upper()
            self.ui.comboBox_card.setCurrentText(card)

            if card == "欠卡":
                pass
            elif card in ["自動取得", "IC"]:
                if (
                    self.ui.comboBox_treat_type.currentText()
                    not in nhi_utils.CARE_TREAT
                ):
                    self.ui.comboBox_treat_type.setCurrentText(self.default_treat_type)

                self.ui.comboBox_course.setCurrentText(None)
            else:
                self.ui.comboBox_course.setCurrentText(None)

            if card in ["", "自動取"]:
                self.ui.comboBox_card.setCurrentText("自動取得")

            self._set_deposit_fee()
            if card[:4] == nhi_utils.OCCUPATIONAL_INJURY_CARD:
                if (
                    self.ui.comboBox_injury_type.currentText()
                    not in nhi_utils.MAIN_OCCUPATIONAL_INJURY_TYPE
                ):
                    self.ui.comboBox_injury_type.setCurrentText(
                        nhi_utils.MAIN_OCCUPATIONAL_INJURY_TYPE[0]
                    )
            elif (
                card[:4] == nhi_utils.INFECTIOUS_INJURY_CARD
                and self.ui.comboBox_reg_type.currentText()
                not in nhi_utils.INFECTIOUS_INJURY_TYPE + nhi_utils.TELECOM_TYPE
            ):
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("一般視訊門診或covid-19確診門診")
                msg_box.setText(
                    """
                    <font size="5" color="blue">
                    <b>請問病患為一般視訊門診或covid-19確診門診?<br>
                    </font>
                    """
                )
                msg_box.setInformativeText("請選擇門診類別")
                msg_box.addButton(QPushButton("一般視訊門診"), QMessageBox.NoRole)
                msg_box.addButton(QPushButton("covid-19確診門診"), QMessageBox.YesRole)
                covid19 = msg_box.exec_()
                if covid19:
                    # self.ui.comboBox_injury_type.setCurrentText(nhi_utils.INFECTIOUS_INJURY_TYPE[0])
                    self.ui.comboBox_reg_type.setCurrentText(
                        nhi_utils.INFECTIOUS_INJURY_TYPE[0]
                    )
                else:
                    self.ui.comboBox_reg_type.setCurrentText(nhi_utils.TELECOM_TYPE[0])
            else:
                if self.ui.comboBox_injury_type.currentText() in ["職業傷害", "職業病"]:
                    self.ui.comboBox_injury_type.setCurrentText("普通疾病")

        elif sender_name == "comboBox_course":
            if number_utils.get_integer(self.ui.comboBox_course.currentText()) >= 2:
                self.ui.comboBox_card_abnormal.setEnabled(True)
            else:
                self.ui.comboBox_card_abnormal.setCurrentText(None)
                self.ui.comboBox_card_abnormal.setEnabled(False)

            self._set_regist_fee()
            self._set_diag_share_fee()
        elif sender_name == "comboBox_visit":
            visit = (
                self.ui.comboBox_visit.currentText()
            )  # 以實際有沒有來過診所為判斷條件
            self._set_regist_fee(visit=visit)
            self._set_diag_share_fee()
        elif sender_name == "comboBox_massager":
            self._set_traditional_health_care_fee()
        elif sender_name == "comboBox_doctor":
            doctor = self.ui.comboBox_doctor.currentText()
            if doctor == "":
                return

            period = self.ui.comboBox_period.currentText()
            room = string_utils.xstr(
                registration_utils.get_room(self.database, period, doctor)
            )

            self.ui.comboBox_room.disconnect()
            self.ui.comboBox_room.setCurrentText(room)
            self.ui.comboBox_room.currentIndexChanged.connect(self._selection_changed)

            if (
                "掛號存檔" in self.ui.action_save.text()
            ):  # 門診掛號非修正時, 重新取得診號
                reg_no = registration_utils.get_reg_no(
                    self.database,
                    self.system_settings,
                    room,
                    doctor,
                    period,
                    self.reserve_key,
                )  # 取得診號
                self.ui.spinBox_reg_no.setValue(int(reg_no))
        elif sender_name == "comboBox_room":
            room = self.ui.comboBox_room.currentText()
            period = self.ui.comboBox_period.currentText()

            if self.system_settings.field("掛號診別更改不要連動醫師姓名") == "Y":
                doctor = self.ui.comboBox_doctor.currentText()
            else:
                doctor = registration_utils.get_schedule_doctor(
                    self.database, room, period
                )

            if doctor in ["", None]:
                sql = f'''
                    SELECT Name FROM person
                    WHERE
                        Room = "{room}" AND
                        Position IN ("醫師", "支援醫師")
                '''
                rows = self.database.select_record(sql)
                if len(rows) > 0:
                    doctor = string_utils.xstr(rows[0]["Name"])

            self.ui.comboBox_doctor.setCurrentText(doctor)

            if "掛號存檔" in self.ui.action_save.text():  # 門診掛號
                reg_no = registration_utils.get_reg_no(  # 取得診號
                    self.database,
                    self.system_settings,
                    room,
                    doctor,
                    period,
                    self.reserve_key,
                )
            else:  # 掛號修正
                current_room = self.table_widget_wait.field_value(
                    self.wait_column["Room"]
                )
                current_regist_no = self.table_widget_wait.field_value(
                    self.wait_column["RegistNo"]
                )

                if current_room != room:  # 換診間重新取得診號
                    reg_no = registration_utils.get_reg_no(
                        self.database,
                        self.system_settings,
                        room,
                        doctor,
                        period,
                        self.reserve_key,
                    )
                else:  # 還原原來的診號
                    reg_no = current_regist_no
                    current_doctor = self.table_widget_wait.field_value(
                        self.wait_column["Doctor"]
                    )
                    self.ui.comboBox_doctor.setCurrentText(current_doctor)

            self.ui.spinBox_reg_no.setValue(int(reg_no))

        elif (
            sender_name in ["comboBox_period", "comboBox_room"]
            and "掛號存檔" in self.ui.action_save.text()
        ):
            period = self.ui.comboBox_period.currentText()
            room = self.ui.comboBox_room.currentText()
            doctor = self.ui.comboBox_doctor.currentText()

            schedule_doctor = registration_utils.get_schedule_doctor(
                self.database, room, period
            )
            if schedule_doctor != "" and schedule_doctor != doctor:
                self.ui.comboBox_doctor.setCurrentText(schedule_doctor)

            reg_no = registration_utils.get_reg_no(
                self.database,
                self.system_settings,
                room,
                doctor,
                period,
                self.reserve_key,
            )  # 取得診號
            self.ui.spinBox_reg_no.setValue(int(reg_no))
        elif sender_name == "lineEdit_regist_fee":
            self._set_total_amount()
        elif sender_name == "lineEdit_diag_share_fee":
            self._set_total_amount()
        elif sender_name == "lineEdit_deposit_fee":
            self._set_total_amount()
        elif sender_name == "lineEdit_traditional_health_care_fee":
            self._set_total_amount()

        if "IC06" in self.ui.comboBox_card.currentText():
            self.ui.comboBox_card_abnormal.setEnabled(True)

    def _set_self_fee(self, item_name):
        self_fee = charge_utils.get_charge_settings_fee(
            self.database, "自費", "自費", item_name
        )
        if self_fee is None:
            return

        self.ui.lineEdit_traditional_health_care_fee.setText(str(self_fee))

    # 開始查詢病患資料
    def query_patient(self):
        keyword = string_utils.xstr(self.ui.lineEdit_query.text())
        if keyword == "":
            return

        if len(keyword) >= 172:
            self._registration_by_vhc_ic_card(keyword)
            return
        elif len(keyword) >= 11:
            pass
        else:
            pattern = re.compile(validator_utils.DATE_REGEXP)
            if pattern.match(keyword):
                keyword = date_utils.date_to_west_date(keyword)
            else:
                keyword = validator_utils.get_exp_date(keyword)

        self._get_patient(keyword, use_patient_key=False)

    def _get_patient(self, keyword, ic_card=None, use_patient_key=True):
        verify_keyword = self.ui.lineEdit_query.text()

        row = patient_utils.search_patient(
            self.ui,
            self.database,
            self.system_settings,
            keyword,
            verify_keyword,
            use_patient_key=use_patient_key,
        )
        if row is None:  # 找不到資料
            keyword = self.ui.lineEdit_query.text()
            dialog = dialog_utils.get_dialog_select_patient(
                self,
                self.database,
                self.system_settings,
                "patient",
                "PatientKey",
                keyword,
            )
            if dialog.table_widget_patient_list.row_count() <= 0:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "查無資料",
                    '<font size="5" color="red"><b>找不到有關的病患資料, 請檢查關鍵字是否有誤.</b></font>',
                    "請確定輸入資料的正確性, 生日請輸入YYYY-MM-DD.",
                )
                self.ui.lineEdit_query.setFocus()
                return

            if dialog.exec_():
                patient_key = dialog.get_primary_key()
                self._get_patient(patient_key)

            del dialog
        elif row == -1:  # 取消查詢
            self.ui.lineEdit_query.setFocus()
        else:  # 已選取病患
            self._prepare_registration_data(row, ic_card)

        self.ui.lineEdit_query.clear()

    # 掛號修正
    def _modify_wait(self):
        if (
            self.user_name != "超級使用者"
            and personnel_utils.get_permission(
                self.database, self.program_name, "修正候診名單", self.user_name
            )
            != "Y"
        ):
            return

        tab_name = self.ui.tabWidget_list.tabText(self.ui.tabWidget_list.currentIndex())
        if tab_name == "候診名單":
            case_key = self.ui.tableWidget_wait.item(
                self.ui.tableWidget_wait.currentRow(), self.wait_column["CaseKey"]
            )
            in_use = self.ui.tableWidget_wait.cellWidget(
                self.ui.tableWidget_wait.currentRow(), self.wait_column["Progress"]
            )
        else:
            case_key = self.ui.tableWidget_wait_completed.item(
                self.ui.tableWidget_wait_completed.currentRow(),
                self.wait_done_column["CaseKey"],
            )
            in_use = None

        if in_use:
            system_utils.show_message_box(
                QMessageBox.Warning,
                "無法修正掛號資料",
                '<font size="5" color="red"><b>此筆資料正在看診中, 請於看診後再修正.</b></font>',
                "請於資料看診完畢後再至已就診名單修正.",
            )
            return

        if case_key is None:
            return

        case_key = case_key.text()
        self.ui.groupBox_registration.setTitle(f"掛號資料-{case_key}")

        self._set_reg_mode(False)
        self.ui.action_save.setText("修正存檔[F10]")
        self.ui.action_save_no_print.setText("修正存檔不印[F11]")
        self.ui.action_cancel.setText("取消修正")

        sql = f"""
            SELECT * FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        medical_record = rows[0]
        patient_key = medical_record["PatientKey"]
        if patient_key is None:
            return

        sql = f"""
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        patient_record = rows[0]
        self._set_patient_data(patient_record, modify_wait=True)
        self._set_registration_data(patient_key, medical_record)
        self._set_charge(medical_record)

        if tab_name == "已就診名單":
            self.ui.comboBox_room.setEnabled(False)
            self.ui.comboBox_doctor.setEnabled(False)

    def _check_ic_card_basic_data(self, ic_card, row, use_vhc_ic_card=False):
        if ic_card is None:
            return

        patient_key = row["PatientKey"]
        patient_card_no = string_utils.xstr(row["CardNo"])
        card_no = ic_card.basic_data["card_no"]

        patient_modified = False
        if patient_card_no != card_no:
            sql = f'''
                UPDATE patient
                SET
                    CardNo = "{card_no}"
                WHERE
                    PatientKey = {patient_key}
            '''
            self.database.exec_sql(sql)
            patient_modified = True

        if row["Birthday"] != ic_card.basic_data["birthday"]:
            birthday = ic_card.basic_data["birthday"]
            sql = f'''
                UPDATE patient
                SET
                    Birthday = "{birthday}"
                WHERE
                    PatientKey = {patient_key}
            '''
            self.database.exec_sql(sql)
            patient_modified = True

        if string_utils.xstr(row["InsType"]) != ic_card.basic_data["insured_mark"]:
            ins_type = ic_card.basic_data["insured_mark"]
            sql = f'''
                UPDATE patient
                SET
                    InsType = "{ins_type}"
                WHERE
                    PatientKey = {patient_key}
            '''
            self.database.exec_sql(sql)
            row["InsType"] = ins_type
            patient_modified = True

        if patient_modified and not use_vhc_ic_card:
            row["Birthday"] = datetime.datetime.strptime(
                ic_card.basic_data["birthday"], "%Y-%m-%d"
            ).date()
            self._set_patient_data(row, verify_id=False)

    def _rename_patient_name(self, patient_key, patient_name):
        sql = f'''
            UPDATE patient
            SET
                Name = "{patient_name}"
            WHERE
                PatientKey = {patient_key}
        '''
        self.database.exec_sql(sql)

    def _need_ic_rename(self, patient_key, ic_name, name):
        if name == ic_name:
            return False

        exclude_characters = ["?", "？", "*", "＊"]

        for character in exclude_characters:
            if character in ic_name:
                return False

        msg_box = dialog_utils.get_message_box(
            "更改姓名",
            QMessageBox.Warning,
            f"""<font size="5" color="red"><b>
                電腦資料庫內的病患姓名「{name}」, 與健保卡的病患姓名「{ic_name}」不同, 是否改為「{ic_name}」?
                </b></font>
            """,
            f"注意！請確認病患「{name}」是否已改名為「{ic_name}」, 或「{name}」尚未去健保署更正卡片姓名!",
        )
        rename = msg_box.exec_()
        if rename:
            self._rename_patient_name(patient_key, ic_name)
            return True

        return False

    # 準備掛號
    def _prepare_registration_data(self, row, ic_card=None):
        patient_key = row[0]["PatientKey"]
        message = None

        if self.system_settings.field("欠款未還不能掛號") == "Y":
            message = registration_utils.check_debt(
                self.database, patient_key
            )  # 檢查欠款
            if message is not None:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "欠款尚未結清",
                    f'<font size="5" color="red"><b>{message}無法繼續掛號。</b></font>',
                    "請至欠還款作業結清欠款.",
                )
                return

        # name = row[0]['Name']  # 不要將病患資料中的姓名與ic卡的姓名同步 2023.09.22
        # if ic_card is not None:
        #     ic_name = ic_card.basic_data['name']
        #     if self._need_ic_rename(patient_key, ic_name, name):
        #         sql = f'''
        #             SELECT * FROM patient
        #             WHERE
        #                 PatientKey = {patient_key}
        #         '''
        #         row = self.database.select_record(sql)

        self._set_reg_mode(False, ic_card)
        self._set_patient_data(row[0])
        self._set_registration_data(patient_key)
        self._check_ic_card_basic_data(ic_card, row[0])

        if not self._check_registration_duplicate(patient_key):
            return False

        if not self._check_deposit(patient_key, ic_card):
            self._parent.open_return_card(patient_key)
            return False

        if self._check_reservation_exists(patient_key):
            return False

        if self.ui.comboBox_ins_type.currentText() == "健保":  # 健保才自動連續療程
            card, course = self._auto_completion_course(patient_key)

            # if self.ui.checkBox_no_nhi_vpn.isChecked() and system_utils.ping_ip(nhi_utils.VPN_IP):
            #     system_utils.show_message_box(
            #         QMessageBox.Warning,
            #         '健保VPN網路已連線',
            #         f'<font size="5" color="red"><b>中華電信健保醫療網VPN似乎已經恢復連線，幫您將健保VPN網路斷線取消打勾，並請您插入健保卡</b></font>',
            #         '網路測試連線正常，可插入健保卡繼續掛號作業.'
            #     )
            #     self.ui.checkBox_no_nhi_vpn.setChecked(False)
            #     self._set_no_nhi_vpn()
            #     try:
            #         if self.system_settings.field('使用讀卡機') == 'Y':
            #             ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
            #             if ic_card is not None:
            #                 ic_card.verify_sam(show_message=False)
            #     except Exception:
            #         pass

            if self.ui.checkBox_no_nhi_vpn.isChecked():
                if card != "A020" and number_utils.get_integer(course) >= 2:
                    self.ui.comboBox_card_abnormal.setCurrentIndex(3)
                else:
                    card = "A020"

            self.ui.comboBox_card.setCurrentText(card)
            self.ui.comboBox_course.setCurrentText(course)

            if self.ui.comboBox_treat_type.currentText() == "慢性腎病照護":
                if course is not None and number_utils.get_integer(course) >= 2:
                    message = registration_utils.check_ckd_week(
                        self.database,
                        patient_key,
                        card,
                    )

                if message is not None:
                    system_utils.show_message_box(
                        QMessageBox.Warning,
                        "慢性腎病CKD警告",
                        f'<font size="5" color="red"><b>{message}</b></font>',
                        "將改為一般門診.",
                    )
                    self.ui.comboBox_treat_type.setCurrentText("內科")

            message = registration_utils.check_course_complete_in_days(
                self.database, patient_key, card, course, 30
            )
            if message is not None:
                system_utils.show_message_box(
                    QMessageBox.Warning,
                    "療程已超過30日",
                    f'<font size="5" color="red"><b>{message}</b></font>',
                    "即將開啟新的療程.",
                )
                card_sequence = self._get_card_sequence()
                self.ui.comboBox_card.setCurrentText(card_sequence)
                self.ui.comboBox_course.setCurrentIndex(0)
                self.ui.comboBox_injury_type.setCurrentIndex(0)

        self._registration_precheck(patient_key)
        self._set_regist_fee()
        self._set_diag_share_fee()
        self._set_traditional_health_care_fee()

        self._show_past_history(patient_key, ic_card)
        self._set_last_doctor(patient_key)

        self.ui.comboBox_card.setFocus()

    def _set_last_doctor(self, patient_key):
        period = self.ui.comboBox_period.currentText()
        weekday_name = self._get_week_day_name("en_US")

        in_duty_doctor_list = registration_utils.get_schedule_doctor_by_date_period(
            self.database, weekday_name, period
        )

        sql = f"""
            SELECT Doctor FROM cases
            WHERE
                PatientKey = {patient_key}
            ORDER BY CaseDate DESC LIMIT 1
        """
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        doctor = string_utils.xstr(rows[0]["Doctor"])
        if doctor in in_duty_doctor_list:
            self.ui.comboBox_doctor.setCurrentText(doctor)

        today = datetime.datetime.today().strftime("%Y-%m-%d")
        agent_doctor = registration_utils.get_temporary_agent_doctor(
            self.database, today, period, doctor
        )

        if agent_doctor is not None:
            self.ui.comboBox_doctor.setCurrentText(agent_doctor)

    # 檢查今日是否有預約
    def _check_reservation_exists(self, patient_key):
        if self.reserve_key is not None:  # 預約報到, 不需檢查
            return

        reservation_exists = False

        start_date = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
        end_date = datetime.datetime.now().strftime("%Y-%m-%d 23:59:59")

        sql = f'''
            SELECT * FROM reserve
            WHERE
                ReserveDate BETWEEN "{start_date}" AND "{end_date}" AND
                Arrival = "False" AND
                PatientKey = {patient_key} AND
                Source NOT IN("初診預約", "網路初診預約", "視訊初診預約", "特殊預約")
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]

            # current_period = registration_utils.get_current_period(self.system_settings)
            # reserve_period = string_utils.xstr(row['Period'])
            # if reserve_period != current_period:
            #     title = '預約報到逾時'
            #     message = f'<font size="5" color="red"><b>今日預約為{reserve_period}已經逾時, 即將改為現場預約.</b></font>'

            #     if (current_period == '早班' and reserve_period in ['午班', '晚班']) or \
            #             (current_period == '午班' and reserve_period == '晚班'):
            #         title = '預約報到提早'
            #         message = f'<font size="5" color="red"><b>今日預約為{reserve_period}無法提早報到，即將改為現場預約.</b></font>'

            #     if title in ['預約報到逾時']:
            #         system_utils.show_message_box(
            #             QMessageBox.Critical,
            #             title,
            #             message,
            #             '請提醒病人注意預約報到時間.'
            #         )

            #         return False

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("今日已有預約掛號")
            msg_box.setText(
                """
                <font size="5" color="blue">
                  <b>此人今日已有預約掛號, 是否預約報到!<br>
                </font>
                """
            )
            msg_box.setInformativeText("預約掛號資料已存在")
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            ready_to_arrival = msg_box.exec_()
            if ready_to_arrival:
                reservation_exists = True
                vhc_ic_card = self.vhc_ic_card
                self._cancel_registration()
                reserve_key = row["ReserveKey"]
                self._parent.open_reservation(
                    reserve_key, None, None, vhc_ic_card=vhc_ic_card
                )

        return reservation_exists

    # 自動連續療程 - 30天內.
    def _auto_completion_course(self, patient_key):
        default_card = self._get_card_sequence()

        if self.system_settings.field("新特約期間") == "Y":
            default_card = case_utils.get_new_opening_card(self.database, patient_key)

        if (
            self.ui.comboBox_reg_type.currentText()
            in nhi_utils.TOUR_TYPE + nhi_utils.LONG_TERM_CARE
        ):  # 巡迴醫療及中醫長照除外
            return default_card, None

        today = datetime.date.today()
        last_treat_date = (today - datetime.timedelta(days=30 - 1)).strftime(
            "%Y-%m-%d 00:00:00"
        )

        if (
            self.ui.comboBox_treat_type.currentText() in nhi_utils.PREGNANT_CARE_TREAT
        ):  # 2024.12.13 助孕照護，保胎照護，上次有開藥，不要續療程
            sql = f'''
                SELECT cases.CaseKey FROM cases
                    LEFT JOIN dosage ON dosage.CaseKey = cases.CaseKey
                WHERE
                    (CaseDate >= "{last_treat_date}") AND
                    (TreatType IN {tuple(nhi_utils.PREGNANT_CARE_TREAT)}) AND
                    (PatientKey = {patient_key}) AND
                    (InsType = "健保") AND
                    (dosage.Days > 0)
                ORDER BY CaseDate DESC LIMIT 1
            '''
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                return default_card, None

        if self.system_settings.field("療程中斷不續療程") == "Y":
            sql = f'''
                SELECT CaseDate, RegistType, TreatType, Card, Continuance, Share, Injury, XCard, Massager FROM cases
                WHERE
                    (CaseDate >= "{last_treat_date}") AND
                    (RegistType NOT IN {tuple(nhi_utils.TOUR_TYPE + nhi_utils.LONG_TERM_CARE)}) AND
                    (TreatType != "居家醫療") AND
                    (PatientKey = {patient_key}) AND
                    (InsType = "健保")
                ORDER BY CaseDate DESC LIMIT 1
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                return default_card, None

            row = rows[0]
            if (
                number_utils.get_integer(row["Continuance"]) <= 0
            ):  # 上次病歷內科，不要續療程
                return default_card, None

        sql = f'''
            SELECT CaseDate, RegistType, TreatType, Card, Continuance, Share, Injury, XCard, Massager FROM cases
            WHERE
                (CaseDate >= "{last_treat_date}") AND
                (PatientKey = {patient_key}) AND
                (InsType = "健保") AND
                (Continuance >= 1)
            ORDER BY CaseDate DESC LIMIT 1
        '''

        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return default_card, None

        row = rows[0]
        treat_type = string_utils.xstr(row["TreatType"])

        if treat_type in nhi_utils.HOME_CARE:  # 居家醫療除外
            self.ui.comboBox_treat_type.setCurrentText(treat_type)
            return default_card, None

        if treat_type in nhi_utils.PREGNANT_CARE_TREAT + [
            "慢性腎病照護"
        ]:  # 助孕照護，保胎照護、慢性腎病照護要續療程
            pass
        elif treat_type in nhi_utils.IMPROVE_CARE_TREAT:  # 加強照護除外
            self.ui.comboBox_treat_type.setCurrentText(treat_type)
            return default_card, None

        if (
            treat_type in nhi_utils.TOUR_TYPE + nhi_utils.LONG_TERM_CARE
        ):  # 巡迴醫療及中醫長照除外
            return default_card, None

        # 2019.04.29 上次為內科, 為避免療程中刷卡, 不要自動續療程
        if number_utils.get_integer(row["Continuance"]) <= 0:
            return default_card, None

        card = string_utils.xstr(row["Card"])
        if (
            card[:4] in nhi_utils.MANUAL_CARD_LIST
            and number_utils.get_integer(row["Continuance"]) >= 6
        ):  # 異常卡序療程已滿
            if (
                self.system_settings.field("新特約期間") != "Y"
                and card[:4] in nhi_utils.ABNORMAL_CARD
            ):  # 非特約期間異常卡序不傲自動連號
                return default_card, None
            else:
                if len(card) >= 5:
                    index = int(card[4])
                    if index >= 9:
                        index = ""
                    else:
                        index += 1
                else:
                    index = 1

                default_card = f"{card[:4]}{index}"

                return default_card, None
        elif number_utils.get_integer(row["Continuance"]) >= 6:  # 正常卡序療程已滿
            if (
                treat_type in nhi_utils.PREGNANT_CARE_TREAT
            ):  # 助孕照護，保胎照護，其他照護
                self.ui.comboBox_treat_type.setCurrentText(treat_type)

            return default_card, None

        if card == "欠卡":
            deposit_date = row["CaseDate"].date()
            present = datetime.datetime.today().date()
            delta = present - deposit_date
            if delta.days > 10:  # 超過10天不可續療程
                return card, None

        share_type = string_utils.xstr(row["Share"])
        injury_type = string_utils.xstr(row["Injury"])
        course = string_utils.xstr(row["Continuance"] + 1)  # 療程自動續1次
        massager = string_utils.xstr(row["Massager"])

        start_date = case_utils.get_course_start_date(
            self.database, patient_key, row["CaseDate"], card, course
        )
        system_utils.set_combo_box_treat_type(self.ui.comboBox_treat_type, start_date)

        treat_found = False
        for i in range(self.ui.comboBox_treat_type.count()):
            if treat_type == self.ui.comboBox_treat_type.itemText(i):
                treat_found = True
                break

        if not treat_found:
            self.ui.comboBox_treat_type.insertItem(1, treat_type)

        self.ui.comboBox_massager.setCurrentText(massager)
        self.ui.comboBox_treat_type.setCurrentText(treat_type)

        if share_type not in ["基層醫療"]:
            self.ui.comboBox_share_type.setCurrentText(share_type)

        self.ui.comboBox_card.setCurrentText(card)
        self.ui.comboBox_course.setCurrentText(course)
        self.ui.comboBox_injury_type.setCurrentText(injury_type)

        self._set_combo_box_color()

        return card, course

    # 掛號預檢
    def _registration_precheck(self, patient_key):
        if self.ui.comboBox_ins_type.currentText() != "健保":  # 自費不檢查
            return

        warning_message = []

        message, _ = registration_utils.check_deposit(  # 檢查健保欠卡未還
            self.database, self.system_settings, patient_key
        )
        if message is not None:
            warning_message.append(message)

        message = registration_utils.check_cancer_acupuncture_times(  # 檢查當月癌症次數
            self.database, self.system_settings, patient_key
        )
        if message is not None:
            warning_message.append(message)

        message = registration_utils.check_treat_times(  # 檢查當月健保針傷次數
            self.database, self.system_settings, patient_key
        )
        if message is not None:
            warning_message.append(message)

        message = registration_utils.check_diag_fee_times(  # 檢查當月健保診察費次數
            self.database, self.system_settings, patient_key
        )
        if message is not None:
            warning_message.append(message)

        message = registration_utils.check_debt(self.database, patient_key)  # 檢查欠款
        if message is not None:
            warning_message.append(message)

        message = registration_utils.check_card_yesterday(
            self.database, patient_key
        )  # 檢查隔日過卡
        if message is not None:
            warning_message.append(message)

        if self.ui.comboBox_treat_type.currentText() == "慢性腎病照護":
            last_case_date, _, pres_days, remain = (
                registration_utils.check_prescription_finished(  # 檢查上次健保給藥是否服藥完畢
                    self.database,
                    self.system_settings,
                    None,
                    patient_key,
                    manual_message=True,
                )
            )
            if last_case_date is not None:
                system_utils.show_message_box(
                    QMessageBox.Warning,
                    "慢性腎病照護警告",
                    f"""<b><font size="5" color="red">
                        慢性腎病照護於{last_case_date}開立{pres_days}日藥，
                        尚有{remain}日藥未結束，不可另開CKD門診
                        </font></b>
                    """,
                    "即將改為一般門診",
                )
                self.ui.comboBox_treat_type.setCurrentText("內科")
                return
        else:
            message = registration_utils.check_prescription_finished(  # 檢查上次健保給藥是否服藥完畢
                self.database, self.system_settings, None, patient_key
            )
            if message is not None:
                warning_message.append(message)

        warning_message = "<br>".join(warning_message)

        if len(warning_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Warning,
                "掛號檢查結果提醒",
                f'<b><font size="5" color="red">{warning_message}</font></b>',
                "請注意! 以上的狀況提示並非資料發生錯誤, 若有疑問, 請至 [病歷查詢] 檢查該筆資料的內容.",
            )
            # if '無法存檔' in warning_message and \
            #         number_utils.get_integer(self.ui.comboBox_course.currentText()) <= 1:
            #     self.ui.comboBox_ins_type.setCurrentText('自費')

    def _get_duplicate_reg_no(self, patient_key):
        sql = f"""
            SELECT RegistNo FROM cases
            WHERE
                DATE(CaseDate) = DATE(NOW()) AND
                PatientKey = {patient_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return 0

        reg_no = number_utils.get_integer(rows[0]["RegistNo"])

        return reg_no

    # 檢查當日重複就診
    def _check_registration_duplicate(self, patient_key):
        if registration_utils.check_record_duplicated(
            self.database, patient_key, datetime.datetime.now()
        ):
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("重複就診")
            msg_box.setText(
                """
                <font size="5" color="red">
                  <b>此人今日已有健保門診, 請改掛自費或取消掛號!<br>
                </font>
                """
            )
            msg_box.setInformativeText("健保規定不可同日重複就診")
            msg_box.addButton(QPushButton("改掛自費"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消掛號"), QMessageBox.NoRole)
            cancel = msg_box.exec_()
            if cancel:
                self._cancel_registration()
                return False

            self.ui.comboBox_ins_type.setCurrentText("自費")
            duplicate_reg_no = self._get_duplicate_reg_no(patient_key)
            self.ui.spinBox_reg_no.setValue(duplicate_reg_no)

        return True

    # 檢查欠卡是否已還
    def _check_deposit(self, patient_key, ic_card):
        message, _ = registration_utils.check_deposit(
            self.database, self.system_settings, patient_key
        )  # 檢查欠卡
        if ic_card is not None and message is not None:  # 讀健保卡且上次未還卡
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("欠卡未還")
            msg_box.setText(f"""
                <font size="5" color="red">
                  <b>{message}<br>
                </font>
            """)
            msg_box.setInformativeText(
                "請注意！如果欠卡日期尚未過期, 請至 [健保卡欠還卡]作業執行[健保還卡]後，再繼續掛號!"
            )
            msg_box.addButton(
                QPushButton("取消掛號，先讓我完成還卡作業"), QMessageBox.NoRole
            )  # 0
            msg_box.addButton(QPushButton("繼續掛號"), QMessageBox.AcceptRole)  # 1
            continue_regist = msg_box.exec_()
            if not continue_regist:
                self._cancel_registration()
                return False

        return True

    # 顯示病患資料
    def _set_patient_data(self, row, modify_wait=False, verify_id=True):
        birth_date = row["Birthday"]
        try:
            # birthday = date_utils.date_to_zh_tw_date(birth_date.strftime('%Y-%m-%d'))
            birthday = birth_date.strftime("%Y-%m-%d")
        except Exception:
            birthday = ""

        share_type = nhi_utils.get_share_type(
            string_utils.xstr(row["InsType"]).strip(None)
        )
        name = string_utils.xstr(row["Name"]).replace("\n", "")

        self.ui.lineEdit_patient_key.setText(string_utils.xstr(row["PatientKey"]))
        self.ui.lineEdit_chart_no.setText(string_utils.xstr(row["ChartNo"]))
        self.ui.lineEdit_name.setText(name)
        self.ui.lineEdit_id.setText(string_utils.xstr(row["ID"]).strip(None))
        self.ui.comboBox_patient_share.setCurrentText(share_type)
        self.ui.comboBox_patient_discount.setCurrentText(
            string_utils.xstr(row["DiscountType"]).strip(None)
        )
        self.ui.comboBox_gender.setCurrentText(
            string_utils.xstr(row["Gender"]).strip(None)
        )
        self.ui.lineEdit_birthday.setText(birthday)
        age_year, _ = date_utils.get_age(birth_date, datetime.datetime.now())
        if age_year is None:
            age = "N/A"
        else:
            # age = f'{age_year}歲{age_month}月'
            age = f"{age_year}歲"

        self.ui.lineEdit_age.setStyleSheet(None)
        old_man_age = number_utils.get_integer(
            self.system_settings.field("老人優待年齡")
        )
        if number_utils.get_integer(age_year) >= old_man_age:
            age += "(老人)"
            self.ui.lineEdit_age.setStyleSheet("color: red;")

        child_age = number_utils.get_integer(self.system_settings.field("兒童優待年齡"))
        if age != "N/A" and number_utils.get_integer(age_year) <= child_age:
            age += "(兒童)"
            self.ui.lineEdit_age.setStyleSheet("color: green;")

        vegetarian = patient_utils.get_patient_extension_settings(
            self.database, row["PatientKey"], "吃素"
        )
        if vegetarian == "Y":
            self.ui.checkBox_vegetarian.setChecked(True)

        self._set_vegetarian_color()

        self.ui.lineEdit_age.setText(age)
        self.ui.lineEdit_telephone.setText(string_utils.xstr(row["Telephone"]))
        self.ui.lineEdit_cellphone.setText(string_utils.xstr(row["Cellphone"]))
        self.ui.lineEdit_address.setText(string_utils.xstr(row["Address"]).strip(None))
        self.ui.lineEdit_patient_remark.setText(
            string_utils.get_str(row["Remark"], "utf8")
        )
        if verify_id:
            self._verify_id(self.ui.lineEdit_id.text())

        self.ui.comboBox_card.setFocus()
        self._set_combo_box_color()

        if not modify_wait and date_utils.is_birthday_today(birth_date):
            system_utils.show_message_box(
                QMessageBox.Information,
                "恭喜生日快樂",
                f'<font size="5" color="deepPink"><b>{name}今天{age_year}歲生日, 請獻上生日的祝福吧！.</b></font>',
                f"{name}的出生日期是{birth_date.year}年{birth_date.month}月{birth_date.day}日",
            )

    # 檢查身分證
    @staticmethod
    def _verify_id(patient_id):
        pattern = re.compile(validator_utils.ID_REGEXP)
        if not pattern.match(patient_id):  # 測試卡
            return

        if not validator_utils.verify_id(patient_id):
            system_utils.show_message_box(
                QMessageBox.Warning,
                "身分證檢查錯誤",
                '<font size="5" color="red"><b>身分證可能有誤，請確認身分證號碼是否輸入正確!</b></font>',
                "如果確定身分證號正確，可以忽略此項警告.",
            )

    def _get_share_type(self, reg_type):
        share_type = self.ui.comboBox_patient_share.currentText()

        if share_type in ["基層醫療", "中低收入戶"]:
            try:
                age = int(self.ui.lineEdit_age.text().split("歲")[0])
            except ValueError:
                age = None

            if age is not None and age < 3:
                share_type = "三歲兒童"

        if reg_type in nhi_utils.TOUR_MOUNTAIN_ISLAND:
            share_type = "山地離島"

        return share_type

    @staticmethod
    def _get_reg_type(reg_type):
        if reg_type == "":
            reg_type = "一般門診"

        return reg_type

    def _get_week_day_name(self, region="zh_TW"):
        today = datetime.datetime.now().weekday()
        week_day_name = date_utils.get_weekday_name(today, region)

        return week_day_name

    def _set_combo_box_doctor(self, current_doctor):
        period = self.ui.comboBox_period.currentText()

        if self.system_settings.field("掛號選擇當診醫師") == "Y":
            weekday_name = self._get_week_day_name("en_US")
            in_duty_doctor_list = registration_utils.get_schedule_doctor_by_date_period(
                self.database, weekday_name, period
            )
        else:
            # in_duty_doctor_list = personnel_utils.get_person(
            #     self.database, '醫師', exclude_person='值班醫師', include_person='全部醫師')
            in_duty_doctor_list = personnel_utils.get_person(
                self.database, "醫師", exclude_person="值班醫師"
            )
            in_duty_doctor_list.insert(0, None)

        case_date = datetime.datetime.now().strftime("%Y-%m-%d")
        temporary_doctor_list = registration_utils.get_temporary_doctor_schedule(
            self.database, case_date, "代班或加診", period
        )

        registration_utils.set_temporary_doctor_schedule(
            self.database, period, in_duty_doctor_list
        )
        ui_utils.set_combo_box(self.ui.comboBox_doctor, in_duty_doctor_list)

        if temporary_doctor_list is not None and len(temporary_doctor_list) > 0:
            schedule_doctor = temporary_doctor_list[0]
        else:
            schedule_doctor = self.ui.comboBox_doctor.itemText(0)

        if current_doctor is not None:
            doctor_found = False
            for i in range(self.ui.comboBox_doctor.count()):
                doctor = self.ui.comboBox_doctor.itemText(i)
                if current_doctor == doctor:
                    doctor_found = True
                    break

            if not doctor_found:
                self.ui.comboBox_doctor.addItem(current_doctor)
        else:
            current_doctor = schedule_doctor

        self.ui.comboBox_doctor.setCurrentText(current_doctor)

    # 設定掛號資料
    def _set_registration_data(self, patient_key, medical_record=None):
        resource_type = self.system_settings.field("資源類別")
        self.ui.comboBox_room.disconnect()
        self.ui.comboBox_doctor.disconnect()
        self.ui.comboBox_room.setEnabled(True)
        self.ui.comboBox_doctor.setEnabled(True)
        case_date = datetime.datetime.now()
        payment_type = "現金"

        if medical_record is None:  # 門診掛號
            reg_type = self.system_settings.field("掛號類別")
            if resource_type in nhi_utils.LACK_RESOURCE_TYPE:
                reg_type = resource_type

            reg_type = self._get_reg_type(reg_type)
            if reg_type in nhi_utils.TOUR_TYPE_WITH_GOTO_LACK_AREA:
                reg_area = self.system_settings.field("巡迴區域")
            elif reg_type in nhi_utils.CORRECTION_REG_TYPE:
                reg_area = self.system_settings.field("矯正機關")
            else:
                reg_area = None

            injury_type = "普通疾病"
            treat_type = self.default_treat_type
            visit = patient_utils.get_visit(self.database, patient_key)

            no_return_days = number_utils.get_integer(
                self.system_settings.field("未回診天數")
            )
            if visit == "複診":
                if patient_utils.is_two_years_ago_visit(self.database, patient_key):
                    system_utils.show_message_box(
                        QMessageBox.Critical,
                        "兩年內未就診",
                        '<font size="5" color="red"><b>注意! 此病患兩年內未就診.</b></font>',
                        "請確定是否兩年內未就診.",
                    )
                    if self.system_settings.field("申報初診照護") == "Y":
                        visit = "初診"
                elif no_return_days > 0 and patient_utils.is_no_return_days(
                    self.database, patient_key, no_return_days
                ):
                    system_utils.show_message_box(
                        QMessageBox.Critical,
                        f"{no_return_days}天內未回診",
                        f'<font size="5" color="red"><b>注意! 此病患{no_return_days}天內未回診.</b></font>',
                        f"請確定是否{no_return_days}天內未就診.",
                    )

            first_visit_date = self.system_settings.field("新診所初診日期")
            if first_visit_date is not None and first_visit_date != "1900-01-01":
                is_old_patient = patient_utils.is_old_patient(
                    self.database, patient_key, first_visit_date
                )
                if is_old_patient:
                    system_utils.show_message_box(
                        QMessageBox.Information,
                        "舊診所病人",
                        '<font size="5" color="red"><b>注意! 此病患為舊診所病人, 請填寫病歷表</b></font>',
                        "請確定是否為舊診所病人.",
                    )

            card = self._get_card_sequence()
            course = None
            xcard = None
            ins_type = self.system_settings.field("預設門診類別")

            share_type = self._get_share_type(reg_type)
            last_share_type = case_utils.get_last_share_type(self.database, patient_key)
            if last_share_type in ["重大傷病"]:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("重大傷病提醒")
                msg_box.setText("""
                    <font size='5' color='blue'>
                        <b>此病人上次門診為重大傷病，本次門診也要以重大傷病就診嗎?</b>
                    </font>
                """)
                msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
                msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
                ill_record = msg_box.exec_()
                if ill_record:
                    share_type = last_share_type

            room = self.system_settings.field("診療室")  # 取得預設診療室
            period = registration_utils.get_current_period(self.system_settings)
            doctor = registration_utils.get_schedule_doctor(
                self.database, room, period
            )  # 醫師要先取得，以便確定是否佔用預約號

            self._check_area()

            if doctor is None or doctor == "":
                doctor_found = False
                for i in range(1, 21):
                    room = string_utils.xstr(i)
                    doctor = registration_utils.get_schedule_doctor(
                        self.database, room, period
                    )  # 醫師要先取得，以便確定是否佔用預約號
                    if doctor is not None and doctor != "":
                        doctor_found = True
                        break

                if not doctor_found:
                    room = 1

            if (
                self.ui.spinBox_reg_no.value() == 0
            ):  # 取得診號  (已在room, therapist, period on changed時取得, 不需要重複再取)
                reg_no = registration_utils.get_reg_no(
                    self.database,
                    self.system_settings,
                    room,
                    doctor,
                    period,
                    self.reserve_key,
                )
                self.ui.spinBox_reg_no.setValue(reg_no)

            massager = None
            remark = None

            if self.system_settings.field("掛號新療程自動帶出上次就醫類別") == "Y":
                last_treat_type = registration_utils.get_last_treat_type(
                    self.database, patient_key
                )
                if treat_type == "內科":
                    treat_type = last_treat_type

            today = datetime.datetime.today().strftime("%Y-%m-%d")
            agent_doctor = registration_utils.get_temporary_agent_doctor(
                self.database, today, period, doctor
            )

            if agent_doctor is not None:
                doctor = agent_doctor

            if self.system_settings.field("掛號類別") == "居家醫療":
                treat_type = "居家醫療"
                card = nhi_utils.get_home_care_card(self.database, patient_key, today)

            if ins_type == "自費":
                card = "免卡"

        else:  # 掛號修正
            reg_type = medical_record["RegistType"]
            reg_area = medical_record["TourArea"]
            injury_type = medical_record["Injury"]
            treat_type = medical_record["TreatType"]
            visit = medical_record["Visit"]
            ins_type = medical_record["InsType"]
            share_type = medical_record["Share"]
            room = medical_record["Room"]

            reg_no = number_utils.get_integer(medical_record["RegistNo"])
            self.ui.spinBox_reg_no.setValue(reg_no)

            period = medical_record["Period"]
            case_date = medical_record["CaseDate"].date()
            card = medical_record["Card"]

            course = string_utils.xstr(medical_record["Continuance"])
            xcard = string_utils.xstr(medical_record["XCard"])
            if xcard in nhi_utils.ABNORMAL_CARD:
                xcard = nhi_utils.ABNORMAL_CARD_DICT[xcard]
            doctor = str(medical_record["Doctor"])
            massager = medical_record["Massager"]
            payment_type = medical_record["RegistPaymentType"]
            remark = string_utils.get_str(medical_record["Remark"], "utf8")

            if medical_record["DesignatedDoctor"] == "True":
                self.ui.checkBox_designated_doctor.setChecked(True)
            if medical_record["DesignatedMassager"] == "True":
                self.ui.checkBox_designated_massager.setChecked(True)

        self.ui.comboBox_reg_type.setCurrentText(reg_type)
        self.ui.comboBox_area.setCurrentText(reg_area)
        self.ui.comboBox_injury_type.setCurrentText(injury_type)
        self.ui.comboBox_treat_type.setCurrentText(treat_type)
        self.ui.comboBox_visit.setCurrentText(visit)
        self.ui.comboBox_ins_type.setCurrentText(ins_type)
        self.ui.comboBox_share_type.setCurrentText(share_type)
        self.ui.comboBox_room.setCurrentText(string_utils.xstr(room))
        self.ui.comboBox_doctor.setCurrentText(doctor)
        self.ui.comboBox_period.setCurrentText(period)
        self.ui.comboBox_massager.setCurrentText(massager)
        self.ui.comboBox_payment_type.setCurrentText(payment_type)
        self.ui.comboBox_remark.setCurrentText(remark)

        self.ui.comboBox_room.currentIndexChanged.connect(self._selection_changed)
        self.ui.comboBox_doctor.currentIndexChanged.connect(self._selection_changed)
        self.ui.dateEdit_case_date.setDate(case_date)

        self._set_combo_box_doctor(doctor)
        self._set_combo_box_color()

        self.ui.comboBox_card.setCurrentText(card)
        self.ui.comboBox_course.setCurrentText(course)
        self.ui.comboBox_card_abnormal.setCurrentText(xcard)

    def _set_combo_box_color(self):
        self.ui.comboBox_patient_share.setStyleSheet("background-color: None")
        self.ui.comboBox_patient_discount.setStyleSheet("background-color: None")
        self.ui.comboBox_share_type.setStyleSheet("background-color: None")
        self.ui.comboBox_injury_type.setStyleSheet("background-color: None")
        self.ui.comboBox_reg_type.setStyleSheet("background-color: None")
        self.ui.comboBox_area.setStyleSheet("background-color: None")

        if self.ui.comboBox_patient_discount.currentText() not in ["", None]:
            self.ui.comboBox_patient_discount.setStyleSheet("background-color: wheat")

        if self.ui.comboBox_patient_share.currentText() in ["榮民"]:
            self.ui.comboBox_patient_share.setStyleSheet("background-color: lightgreen")
        elif self.ui.comboBox_patient_share.currentText() in ["低收入戶"]:
            self.ui.comboBox_patient_share.setStyleSheet("background-color: lightpink")

        if self.ui.comboBox_share_type.currentText() in ["榮民"]:
            self.ui.comboBox_share_type.setStyleSheet("background-color: lightpink")
        elif self.ui.comboBox_share_type.currentText() in ["低收入戶"]:
            self.ui.comboBox_share_type.setStyleSheet("background-color: lightgreen")
        elif self.ui.comboBox_share_type.currentText() in ["職業傷害"]:
            self.ui.comboBox_share_type.setStyleSheet("background-color: lightblue")
        elif self.ui.comboBox_share_type.currentText() in ["山地離島"]:
            self.ui.comboBox_share_type.setStyleSheet("background-color: lightgreen")
        elif self.ui.comboBox_share_type.currentText() in nhi_utils.INFECTIOUS_TYPE:
            self.ui.comboBox_share_type.setStyleSheet("background-color: lightgreen")

        if (
            self.ui.comboBox_reg_type.currentText()
            in nhi_utils.TOUR_TYPE_WITH_GOTO_LACK_AREA
        ):
            self.ui.comboBox_reg_type.setStyleSheet("background-color: lightgreen")
            self.ui.comboBox_area.setStyleSheet("background-color: lightgreen")
        elif self.ui.comboBox_reg_type.currentText() in nhi_utils.CORRECTION_REG_TYPE:
            self.ui.comboBox_reg_type.setStyleSheet("background-color: lightpink")
            self.ui.comboBox_area.setStyleSheet("background-color: lightpink")
        elif (
            self.ui.comboBox_reg_type.currentText()
            in nhi_utils.INFECTIOUS_TYPE + nhi_utils.TELECOM_TYPE
        ):
            self.ui.comboBox_reg_type.setStyleSheet("background-color: lightgreen")

        if self.ui.comboBox_injury_type.currentText() in nhi_utils.INFECTIOUS_TYPE:
            self.ui.comboBox_injury_type.setStyleSheet("background-color: lightgreen")
        elif (
            self.ui.comboBox_injury_type.currentText()
            in nhi_utils.OCCUPATIONAL_INJURY_TYPE
        ):
            self.ui.comboBox_injury_type.setStyleSheet("background-color: lightblue")

    def _check_area(self):
        if (
            self.system_settings.field("資源類別") in ["一般", "資源不足開業"]
            and self.system_settings.field("掛號類別")
            not in nhi_utils.TOUR_TYPE + nhi_utils.CORRECTION_REG_TYPE
        ):
            self.ui.comboBox_area.clear()
            self.ui.comboBox_area.setEnabled(False)
            return

        if self.system_settings.field("資源類別") in nhi_utils.GOTO_LACK_AREA:
            reg_type = self.system_settings.field("資源類別")
        else:
            reg_type = self.system_settings.field("掛號類別")

        tour_area_list = nhi_utils.get_area_list(reg_type)
        self.ui.comboBox_area.setEnabled(True)
        self.ui.comboBox_reg_type.setCurrentText(reg_type)

        if reg_type in nhi_utils.GOTO_LACK_AREA:
            ui_utils.set_combo_box(self.ui.comboBox_area, tour_area_list, None)
            self.ui.comboBox_area.setCurrentText(self.system_settings.field("巡迴區域"))
        elif reg_type in nhi_utils.TOUR_TYPE:
            ui_utils.set_combo_box(self.ui.comboBox_area, tour_area_list, None)
            self.ui.comboBox_area.setCurrentText(self.system_settings.field("巡迴區域"))
            self.ui.comboBox_share_type.setCurrentText("山地離島")
        elif reg_type in nhi_utils.CORRECTION_REG_TYPE:
            ui_utils.set_combo_box(self.ui.comboBox_area, tour_area_list, None)
            self.ui.comboBox_area.setCurrentText(self.system_settings.field("矯正機關"))

        self._set_combo_box_color()

    # 設定掛號費
    def _set_regist_fee(self, visit=None):
        if visit is None:
            patient_key = self.ui.lineEdit_patient_key.text()
            is_first_visit = patient_utils.is_first_visit(self.database, patient_key)
            if is_first_visit:
                visit = "初診"
            else:
                visit = "複診"

        # visit = self.ui.comboBox_visit.currentText()  # 以實際有沒有來過診所為判斷條件

        ins_type = self.ui.comboBox_ins_type.currentText()
        regist_fee = charge_utils.get_regist_fee(
            self.database,
            self.system_settings,
            self.ui.lineEdit_birthday.text(),
            self.ui.comboBox_patient_discount.currentText(),
            ins_type,
            self.ui.comboBox_share_type.currentText(),
            self.ui.comboBox_treat_type.currentText(),
            self.ui.comboBox_course.currentText(),
            visit,
        )

        self.ui.lineEdit_regist_fee.setText(str(regist_fee))
        self._set_total_amount()

    # 檢查掛號費是否需要多退少補 2025-03-06 恆德
    def _check_ins_regist_fee(self, case_key, current_regist_fee):
        sql = f'''
            SELECT
                RegistFee FROM cases
            WHERE
                CaseKey = "{case_key}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        regist_fee = number_utils.get_integer(rows[0]["RegistFee"])
        current_regist_fee = number_utils.get_integer(current_regist_fee)

        if current_regist_fee > regist_fee:
            system_utils.show_message_box(
                QMessageBox.Warning,
                "應補掛號費",
                f"""<font size="5" color="red"><b>原本掛號費為 {regist_fee}，現在掛號費為 {current_regist_fee}<br>
                                                  請補足掛號費差額 {current_regist_fee - regist_fee}<br>
                </b></font>""",
                "請補足掛號費差額.",
            )
        elif current_regist_fee < regist_fee:
            system_utils.show_message_box(
                QMessageBox.Warning,
                "應退掛號費",
                f"""<font size="5" color="red"><b>原本掛號費為 {regist_fee}，現在掛號費為 {current_regist_fee}<br>
                                                  請退還掛號費差額 {regist_fee - current_regist_fee}元<br>
                </b></font>""",
                "請退還掛號費差額.",
            )

    # 設定門診負擔
    def _set_diag_share_fee(self):
        if self.ui.comboBox_ins_type.currentText() == "健保":
            diag_share_fee = charge_utils.get_diag_share_fee(
                self.database,
                self.system_settings,
                self.ui.comboBox_share_type.currentText(),
                self.ui.comboBox_treat_type.currentText(),
                self.ui.comboBox_course.currentText(),
                self.ui.comboBox_reg_type.currentText(),
            )
            diag_share_discount_fee = charge_utils.get_diag_share_discount_fee(
                self.database, self.ui.comboBox_patient_discount.currentText()
            )

            if diag_share_discount_fee is not None:
                diag_share_fee = diag_share_discount_fee
        else:
            diag_share_fee = 0

        self.ui.lineEdit_diag_share_fee.setText(str(diag_share_fee))
        self._set_total_amount()

    def _set_deposit_fee(self):
        if self.ui.comboBox_ins_type.currentText() == "健保":
            deposit_fee = charge_utils.get_deposit_fee(
                self.database, self.ui.comboBox_card.currentText()
            )
        else:
            deposit_fee = 0

        self.ui.lineEdit_deposit_fee.setText(str(deposit_fee))
        self._set_total_amount()

    def _set_traditional_health_care_fee(self):
        massager = self.ui.comboBox_massager.currentText()

        traditional_health_care_fee = charge_utils.get_traditional_health_care_fee(
            self.database,
            self.system_settings,
            self.ui.comboBox_ins_type.currentText(),
            number_utils.get_integer(self.ui.comboBox_course.currentText()),
            massager,
        )
        if traditional_health_care_fee == 0:
            return

        self.ui.lineEdit_traditional_health_care_fee.setText(
            str(traditional_health_care_fee)
        )
        self._set_total_amount()

    # 設定收費資料
    def _set_charge(self, medical_record):
        case_key = medical_record["CaseKey"]
        regist_fee = medical_record["RegistFee"]
        diag_share_fee = medical_record["SDiagShareFee"]
        deposit_fee = medical_record["DepositFee"]
        ins_type = medical_record["InsType"]
        traditional_health_care_fee = (
            charge_utils.get_traditional_health_care_fee_from_case(
                self.database, case_key, ins_type=ins_type
            )
        )

        self.ui.lineEdit_regist_fee.setText(str(regist_fee))
        self.ui.lineEdit_diag_share_fee.setText(str(diag_share_fee))
        self.ui.lineEdit_deposit_fee.setText(str(deposit_fee))
        self.ui.lineEdit_traditional_health_care_fee.setText(
            str(traditional_health_care_fee)
        )
        self._set_total_amount(case_key)

    # 設定收費總金額
    def _set_total_amount(self, case_key=None):
        try:
            regist_fee = number_utils.get_integer(self.ui.lineEdit_regist_fee.text())
        except ValueError:
            regist_fee = 0

        try:
            diag_share_fee = number_utils.get_integer(
                self.ui.lineEdit_diag_share_fee.text()
            )
        except ValueError:
            diag_share_fee = 0

        try:
            deposit_fee = number_utils.get_integer(self.ui.lineEdit_deposit_fee.text())
        except ValueError:
            deposit_fee = 0

        try:
            traditional_health_care_fee = number_utils.get_integer(
                self.ui.lineEdit_traditional_health_care_fee.text()
            )
        except ValueError:
            traditional_health_care_fee = 0

        total_amount = (
            regist_fee + diag_share_fee + deposit_fee + traditional_health_care_fee
        )

        if case_key is not None:
            sql = f"""
                SELECT * FROM debt
                WHERE
                    CaseKey = {case_key} AND
                    DebtType = "掛號欠款"
            """
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                row = rows[0]
                debt = number_utils.get_integer(row["Fee"])
                total_amount -= debt

        self.ui.lineEdit_regist_fee.setText(str(regist_fee))
        self.ui.lineEdit_diag_share_fee.setText(str(diag_share_fee))
        self.ui.lineEdit_deposit_fee.setText(str(deposit_fee))
        self.ui.lineEdit_traditional_health_care_fee.setText(
            str(traditional_health_care_fee)
        )
        self.ui.lineEdit_total_amount.setText(str(total_amount))
        self.ui.lineEdit_receipt_fee.setText(str(total_amount))

    def _show_past_history(self, patient_key, ic_card=None):
        self.dialog_history.show_past_history(patient_key, ic_card)

    def _get_card(self, card, separator="-"):
        if card is None:
            return card

        if separator in card:
            card = string_utils.xstr(card).split(separator)[0]

        return string_utils.xstr(card)

    def _get_course(self, card):
        if card is None:
            return None

        if "-" in card:
            course = number_utils.get_integer(card.split("-")[1])
        else:
            course = None

        return course

    def _set_card(self, card, course):
        if number_utils.get_integer(course) >= 1:
            card = card + f"-{course}"

        return card

    # 刪除候診名單
    def delete_wait_list(self, show_warning=None):
        tab_name = self.ui.tabWidget_list.tabText(self.ui.tabWidget_list.currentIndex())
        now = date_utils.now_to_str()
        if tab_name == "候診名單":
            wait_key = self.table_widget_wait.field_value(self.wait_column["WaitKey"])
            case_key = self.table_widget_wait.field_value(self.wait_column["CaseKey"])
            name = self.table_widget_wait.field_value(self.wait_column["Name"])
            card = self.table_widget_wait.field_value(self.wait_column["Card"])
            room = self.table_widget_wait.field_value(self.wait_column["Room"])
            doctor = self.table_widget_wait.field_value(self.wait_column["Doctor"])
            table_widget = self.ui.tableWidget_wait
        else:
            wait_key = self.table_widget_wait_completed.field_value(
                self.wait_done_column["WaitKey"]
            )
            case_key = self.table_widget_wait_completed.field_value(
                self.wait_done_column["CaseKey"]
            )
            name = self.table_widget_wait_completed.field_value(
                self.wait_done_column["Name"]
            )
            card = self.table_widget_wait_completed.field_value(
                self.wait_done_column["Card"]
            )
            room = self.table_widget_wait_completed.field_value(
                self.wait_done_column["Room"]
            )
            doctor = self.table_widget_wait_completed.field_value(
                self.wait_done_column["Doctor"]
            )
            table_widget = self.ui.tableWidget_wait_completed

        if show_warning:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("刪除掛號資料")
            msg_box.setText(f"""
                <font size='4' color='red'>
                    <b>確定刪除 <font color='blue'>{name}</font> 的掛號資料?</b>
                </font>
            """)
            msg_box.setInformativeText("注意！掛號資料刪除後無法回復!")
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            delete_record = msg_box.exec_()
            if not delete_record:
                return

            if self.user_name == "超級使用者":
                pass
            elif not system_utils.verify_confirm_code():
                return

        self.database.delete_record("wait", "WaitKey", wait_key)

        if (
            self.system_settings.field("alleypin") == "Y"
        ):  # 在刪除病歷檔前推播，否則資料會找不到
            try:
                alleypin_utils.cancel_outpatient_alleypin_appointments(
                    self.database, self.system_settings, case_key
                )
                alleypin_utils.update_progresses(
                    self.database, self.system_settings, case_key
                )
            except Exception:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "翔評主機連線錯誤",
                    '<font size="5" color="red"><b>翔評伺服器連線發生錯誤, 請聯絡翔評客服.</b></font>',
                    "翔評主機網路不通.",
                )

        self.database.delete_record("deposit", "CaseKey", case_key)
        self.database.delete_record("debt", "CaseKey", case_key)
        self.database.delete_record("cases", "CaseKey", case_key)
        case_utils.delete_traditional_health_care(self.database, case_key)

        log = f"{name}於{now}執行掛號刪除, 卡序:{card}, 主治醫師: {room}診{doctor}醫師"
        self._write_event_log("資料刪除", log)

        sql = f"""
            SELECT PrescriptKey FROM prescript
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        for row in rows:
            prescript_key = row["PrescriptKey"]
            self.database.delete_record("presextend", "PrescriptKey", prescript_key)

        self.database.delete_record("prescript", "CaseKey", case_key)

        table_widget.removeRow(table_widget.currentRow())
        if self.ui.tableWidget_wait.rowCount() <= 0:
            self._set_wait_tool_button(False)
        if self.ui.tableWidget_wait_completed.rowCount() <= 0:
            self._set_wait_completed_tool_button(False)

        self._send_socket_data(doctor, room)

    def _send_socket_data(self, doctor, room):
        self.socket_client.send_data(
            ",".join(
                [
                    self.system_settings.field("院所名稱"),
                    self.program_name,
                    doctor,
                    room,
                ]
            )
        )

    # IC卡退掛
    def cancel_ic_card(self):
        tab_name = self.ui.tabWidget_list.tabText(self.ui.tabWidget_list.currentIndex())
        if tab_name == "候診名單":
            table_widget_wait = self.ui.tableWidget_wait
            # case_key = self.table_widget_wait.field_value(self.wait_column['CaseKey'])  # 2022-11-11
            # name = self.table_widget_wait.field_value(self.wait_column['Name'])
        else:
            table_widget_wait = self.ui.tableWidget_wait_completed
            # case_key = self.table_widget_wait_completed.field_value(self.wait_done_column['CaseKey'])
            # name = self.table_widget_wait_completed.field_value(self.wait_done_column['Name'])

        row_no = table_widget_wait.currentRow()
        try:
            case_key = table_widget_wait.item(
                row_no, self.wait_column["CaseKey"]
            ).text()
            wait_key = table_widget_wait.item(
                row_no, self.wait_column["WaitKey"]
            ).text()
            name = table_widget_wait.item(row_no, self.wait_column["Name"]).text()
        except Exception:
            return

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("健保IC卡退掛")
        msg_box.setText(f"""
            <font size='4' color='red'>
                <b>確定將<font color='blue'>{name}</font>的IC卡掛號資料退掛?</b>
            </font>
        """)
        msg_box.setInformativeText("注意！IC卡退掛後, 將回復原來健保卡序!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        cancel_ic_card = msg_box.exec_()
        if not cancel_ic_card:
            return

        if self.user_name == "超級使用者":
            pass
        elif not system_utils.verify_confirm_code():
            return

        sql = f"""
            SELECT Continuance, Share, Security FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "查無資料",
                '<font size="5" color="red"><b>找不到病歷資料, 無法執行IC卡退掛作業.</b></font>',
                "請確定資料是否存在, 如不存在, 請直接刪除掛號資料.",
            )
            return

        row = rows[0]
        course = number_utils.get_integer(row["Continuance"])
        share_type = string_utils.xstr(row["Share"])
        if course >= 2 or share_type == "職業傷害":  # 療程不須退掛, 直接刪除
            self.delete_wait_list(show_warning=True)
            tab_name = self.ui.tabWidget_list.tabText(
                self.ui.tabWidget_list.currentIndex()
            )
            if tab_name == "候診名單":
                self.read_wait()
            else:
                self._read_wait_completed()
            return

        ic_card_type = case_utils.get_ic_card_type(self.database, case_key)
        if ic_card_type == "虛擬健保卡":
            qrcode = None
            vhc_req_code = vhc_utils.get_vhc_req_code_from_wait(self.database, wait_key)
            if vhc_req_code is not None:
                self._request_req_code(show_message=False)
                vhc_req_code = vhc_utils.get_vhc_req_code_from_wait(
                    self.database, wait_key
                )

                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("取得病患授權")
                msg_box.setText(
                    """
                    <font size="5" color="blue">
                    <b>請問病患是否已在健保快易通授權?<br>
                    </font>
                    """
                )
                msg_box.setInformativeText("取得虛擬健保卡授權")
                msg_box.addButton(QPushButton("尚未取得"), QMessageBox.NoRole)
                msg_box.addButton(QPushButton("病患已經授權"), QMessageBox.YesRole)
                get_response = msg_box.exec_()
                if not get_response:
                    return

                ic_card = class_utils.get_cshis(
                    self, self.database, self.system_settings
                )
                qrcode = ic_card.get_response_token(vhc_req_code)
                if qrcode is None:
                    system_utils.show_message_box(
                        QMessageBox.Critical,
                        "無法寫卡",
                        '<font size="5" color="red"><b>無法使用虛擬健保卡寫卡, 無法取得授權.</b></font>',
                        "請重新取得授權.",
                    )
                    return

            ic_card = class_utils.get_vhccshis(
                self, self.database, self.system_settings, qrcode
            )
        else:
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)

        card_datetime = case_utils.extract_security_xml(row["Security"], "寫卡時間")
        if string_utils.xstr(card_datetime) == "":
            system_utils.show_message_box(
                QMessageBox.Critical,
                "查無資料",
                '<font size="5" color="red"><b>找不到健保IC卡讀卡資料, 無法執行IC卡退掛作業.</b></font>',
                "請確定此筆病歷是否成功的讀卡, 如不成功, 請直接刪除掛號資料.",
            )
            return

        nhi_datetime = date_utils.west_datetime_to_nhi_datetime(card_datetime)
        if ic_card.return_seq_number(nhi_datetime):
            self.delete_wait_list(show_warning=False)

        tab_name = self.ui.tabWidget_list.tabText(self.ui.tabWidget_list.currentIndex())
        if tab_name == "候診名單":
            self.read_wait()
        else:
            self._read_wait_completed()

    def _check_ins_ok_before_save(self):
        ins_type = self.ui.comboBox_ins_type.currentText()
        if ins_type != "健保":
            return True

        patient_key = self.ui.lineEdit_patient_key.text()
        course = self.ui.comboBox_course.currentText()

        if (
            number_utils.get_integer(course) <= 1
            and self.system_settings.field("隔日過卡不能存檔") == "Y"
        ):
            message = registration_utils.check_card_yesterday(
                self.database, patient_key
            )  # 檢查隔日過卡
            if message is not None:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "隔日過卡",
                    '<font size="5" color="red"><b>昨日有內科或療程首次病歷! 今日為隔日過卡, 無法存檔.</b></font>',
                    "請確定可否變更為自費病歷或針傷療程.",
                )
                return False

        return True

    def _is_regist_no_exists(self):
        room = self.ui.comboBox_room.currentText()
        regist_no = self.ui.spinBox_reg_no.value()
        period = self.ui.comboBox_period.currentText()
        start_date = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
        end_date = datetime.datetime.now().strftime("%Y-%m-%d 23:59:59")
        patient_key = self.ui.lineEdit_patient_key.text()

        if registration_utils.is_reg_no_exists(
            self.database, start_date, end_date, period, room, regist_no, patient_key
        ):
            return True
        else:
            return False

    # 掛號存檔/修正存檔
    def _save_records(self):
        if (
            self.system_settings.field("掛號診號不可重複") == "Y"
            and self._is_regist_no_exists()
        ):
            system_utils.show_message_box(
                QMessageBox.Critical,
                "診號重複",
                '<font size="5" color="red"><b>診號重複, 請重新設定診號後再存檔.</b></font>',
                "請確定診號是否重複設定.",
            )
            return

        room = self.ui.comboBox_room.currentText()
        doctor = self.ui.comboBox_doctor.currentText()
        if doctor in [None, ""]:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "醫師欄位空白",
                '<font size="5" color="red"><b>尚未選擇門診醫師, 請選擇門診醫師後再存檔.</b></font>',
                "請確定醫師班表是否設定.",
            )
            return

        if not self._check_ins_ok_before_save():
            return

        card = self._get_card(self.ui.comboBox_card.currentText(), " ")

        if (
            "掛號存檔" in self.ui.action_save.text()
            and not self._verify_registration_data(card)
        ):
            return

        ic_card, req_code = self._process_ic_card(card)
        if ic_card is None:  # 不須讀卡
            if (
                self.ui.comboBox_ins_type.currentText() == "健保"
                and not self.ui.checkBox_request_token.isChecked()
                and card == "自動取得"
            ):
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "卡序有誤",
                    '<font size="5" color="red"><b>讀卡機無法作業, 請選擇異常卡序後再存檔.</b></font>',
                    "讀卡機無法作業.",
                )
                return
            else:
                pass
        elif not ic_card:  # 取得安全簽章失敗
            return

        if self.ui.checkBox_request_token.isChecked() and (
            not req_code or req_code == "error"
        ):
            system_utils.show_message_box(
                QMessageBox.Critical,
                "請求錯誤",
                '<font size="5" color="red"><b>無法請求病患虛擬健保卡授權碼，請確認病患是否安裝申請健保快易通App。</b></font>',
                "無法取得授權碼.",
            )
            return

        if (
            "修正存檔" in self.ui.action_save.text()
            or "修正存檔不印" in self.ui.action_save_no_print.text()
        ):
            case_key = self.ui.groupBox_registration.title().split("-")[-1]
            if card == "欠卡":  # 掛號修正存檔, 原欠卡卡序若已取得卡序, 刪除欠卡資料
                self.database.delete_record("deposit", "CaseKey", case_key)

        self._save_patient()
        case_key = self._save_medical_record(ic_card)

        if self._is_today():  # 掛號今日門診才執行下列程式
            self._save_wait(case_key, req_code)
            self._save_deposit(case_key, card)
            self._save_debt(case_key)

            if self.reserve_key is not None:
                self._update_reservation(self.reserve_key)
            else:
                if self.system_settings.field("alleypin") == "Y":
                    try:
                        alleypin_utils.outpatient_checkin_alleypin_appointments(
                            self.database, self.system_settings, case_key
                        )
                        alleypin_utils.update_progresses(
                            self.database, self.system_settings, case_key
                        )
                    except Exception:
                        system_utils.show_message_box(
                            QMessageBox.Critical,
                            "翔評主機連線錯誤",
                            '<font size="5" color="red"><b>翔評伺服器連線發生錯誤, 請聯絡翔評客服.</b></font>',
                            "翔評主機網路不通.",
                        )

            self.read_wait()
            self._send_socket_data(doctor, room)

            sender_name = self.sender().objectName()

            total_amount = number_utils.get_integer(
                self.ui.lineEdit_total_amount.text()
            )  # 應收金額非實收金額
            if (
                self.system_settings.field("掛號收據無金額不列印") == "Y"
                and total_amount <= 0
            ):  # 金正中醫 2022.12.27
                pass
            elif (
                sender_name == "action_save"
                and "掛號存檔" in self.ui.action_save.text()
            ):
                self.print_regist(
                    self.ui.comboBox_ins_type.currentText(),
                    self.ui.comboBox_treat_type.currentText(),
                    "系統設定",
                    case_key,
                )

            if self.ui.checkBox_request_token.isChecked():
                system_utils.show_message_box(
                    QMessageBox.Information,
                    "請求授權成功",
                    '<font size="5" color="darkblue"><b>虛擬健保卡已送出授權請求，請病人至健保快易通同意授權。</font>',
                    "病人授權同意後，請按下完成授權按鈕",
                )

        self.reserve_key = None
        self.dialog_history.close()
        self._set_reg_mode(True)
        self.ui.groupBox_search_patient.setEnabled(True)
        self.ui.lineEdit_query.setFocus()

        self._reset_action_button_text()

    def _update_reservation(self, reserve_key):
        sql = f"""
            UPDATE reserve
            SET
                Arrival = "True"
            WHERE
                ReserveKey = {reserve_key}
        """
        self.database.exec_sql(sql)

        if self.system_settings.field("alleypin") == "Y":
            try:
                alleypin_utils.reservation_checkin_alleypin_appointments(
                    self.database, self.system_settings, reserve_key
                )
            except Exception:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "翔評主機連線錯誤",
                    '<font size="5" color="red"><b>翔評伺服器連線發生錯誤, 請聯絡翔評客服.</b></font>',
                    "翔評主機網路不通.",
                )

    # 存檔前檢查
    def _verify_registration_data(self, card):
        if self.ui.comboBox_ins_type.currentText() != "健保":  # 自費不檢查
            return True

        if (
            self.ui.comboBox_reg_type.currentText()
            in nhi_utils.TOUR_TYPE + nhi_utils.LONG_TERM_CARE
        ):  # 巡迴醫療不檢查
            return True

        patient_key = self.ui.lineEdit_patient_key.text()
        warning_message = []
        course = self.ui.comboBox_course.currentText()

        # 檢查隔日過卡
        message = registration_utils.check_card_yesterday(
            self.database, patient_key, course
        )
        if message is not None:
            warning_message.append(message)

        if self.system_settings.field("掛號療程14日未完成提醒") == "Y":
            message = (
                registration_utils.check_course_complete_in_days(  # 檢查療程14日未完成
                    self.database, patient_key, card, course, 14
                )
            )
            if message is not None:
                warning_message.append(message)

        message = registration_utils.check_course_complete(
            self.database, patient_key, course
        )
        if message is not None:
            warning_message.append(message)

        if len(warning_message) > 0:
            warning_message = "\n".join(warning_message)
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("掛號存檔前檢查結果")
            msg_box.setText(f"<h3>{warning_message}</h3>")
            msg_box.setInformativeText(
                "請詢問主治醫師此病患是否繼續以此方式掛號, 或變更其他方式掛號"
            )
            msg_box.addButton(QPushButton("繼續掛號"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消掛號"), QMessageBox.NoRole)
            cancel = msg_box.exec_()
            if cancel:
                self._cancel_registration()
                return False

        return True

    def _process_ic_card(self, card):
        if self.ui.comboBox_ins_type.currentText() != "健保":
            return None, None

        if card in ["免卡"] + self.temp_card_list:
            return None, None

        if (
            self.system_settings.field("產生安全簽章位置") != "掛號"
            or self.system_settings.field("使用讀卡機") != "Y"
        ):
            return None, None

        if self.ui.checkBox_request_token.isChecked():
            patient_id = self.ui.lineEdit_id.text()
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
            req_code = ic_card.request_token(patient_id)

            return None, req_code

        if (
            "修正存檔" in self.ui.action_save.text()
            or "修正存檔不印" in self.ui.action_save_no_print.text()
        ):
            if (
                card not in ["自動取得", "欠卡"] + nhi_utils.ABNORMAL_CARD
            ):  # 掛號修正存檔, 卡序若為自動取得或欠卡及異常卡序, 要產生卡序及安全簽章
                return None, None

        card_abnormal = string_utils.xstr(
            self.ui.comboBox_card_abnormal.currentText()
        ).split(" ")[0]
        if (
            card == "欠卡"
            or card[:4] in nhi_utils.ABNORMAL_CARD
            or card_abnormal in nhi_utils.ABNORMAL_CARD
        ):
            if card[:4] in ["A020", "F000"] or card_abnormal in [
                "A020",
                "F000",
            ]:  # 2024-12-31 A020網路不通無法取得就醫識別碼
                return None, None

            ic_card = self._write_ic_card_abnormal()
        else:
            if self.vhc_ic_card is None:
                ic_card = self._write_ic_card(cshis_utils.NORMAL_CARD)
            else:
                ic_card = self._write_vhc_ic_card(cshis_utils.NORMAL_CARD)
                self.vhc_ic_card = None

        return ic_card, None

    def _write_ic_card_abnormal(self):
        patient_id = self.ui.lineEdit_id.text()
        if patient_id == "":  # 無法取得就醫識別碼
            return None

        try:
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
            ic_card_ok = ic_card.write_ic_card_abnormal(patient_id)
        except Exception:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "錯誤",
                """
                    <font size="5" color="red">
                        <b>請確認讀卡機控制軟體版本必須為5.1.5.3以後.</b>
                    </font>
                """,
                "請確定讀卡機控制軟體版本是否過時.",
            )
            return None

        return ic_card_ok

    def _write_ic_card(self, treat_after_check):
        ic_card = class_utils.get_cshis(self, self.database, self.system_settings)

        try:
            available_date, available_count = ic_card.get_card_status()
        except Exception:
            return False

        if available_count is None:
            return False

        now = datetime.datetime.now().strftime("%Y-%m-%d")
        if available_count <= 0 or available_date < now:
            ic_card.update_hc(False)

        card = self._get_card(self.ui.comboBox_card.currentText(), " ")

        if (
            self.ui.comboBox_treat_type.currentText() == "居家醫療"
            and card != "自動取得"
        ):
            treat_type = "居家醫療"
        else:
            treat_type = None

        ic_card_ok = ic_card.write_ic_card(
            "掛號寫卡",
            self.ui.lineEdit_patient_key.text(),
            self.ui.comboBox_course.currentText(),
            self.ui.comboBox_share_type.currentText(),
            treat_after_check,
            treat_type=treat_type,
        )

        if (
            self.ui.comboBox_treat_type.currentText() == "居家醫療"
            and card != "自動取得"
        ):
            return ic_card_ok

        if ic_card_ok:
            seq_number = string_utils.xstr(
                ic_card.treat_data["seq_number"]
            )  # 有產生卡號才更新
            if card != "IC06" and seq_number != "":
                self.ui.comboBox_card.setCurrentText(seq_number)

            return ic_card_ok
        else:
            return False

    def _write_vhc_ic_card(self, treat_after_check):
        ic_card_ok = self.vhc_ic_card.write_ic_card(
            "掛號寫卡",
            self.ui.lineEdit_patient_key.text(),
            self.ui.comboBox_course.currentText(),
            self.ui.comboBox_share_type.currentText(),
            treat_after_check,
        )

        card = self._get_card(self.ui.comboBox_card.currentText(), " ")
        if ic_card_ok:
            seq_number = string_utils.xstr(
                self.vhc_ic_card.treat_data["seq_number"]
            )  # 有產生卡號才更新
            if card != "IC06" and seq_number != "":
                self.ui.comboBox_card.setCurrentText(seq_number)

            return ic_card_ok
        else:
            return False

    # 病患資料存檔
    def _save_patient(self):
        patient_key = self.ui.lineEdit_patient_key.text()
        vegetarian = patient_utils.get_patient_extension_settings(
            self.database, patient_key, "吃素"
        )
        if self.ui.checkBox_vegetarian.isChecked() and vegetarian != "Y":
            patient_utils.set_patient_extension_settings(
                self.database, patient_key, "吃素", "Y"
            )
        elif not self.ui.checkBox_vegetarian.isChecked() and vegetarian == "Y":
            patient_utils.set_patient_extension_settings(
                self.database, patient_key, "吃素", None
            )

        patient_modified = False
        if (
            self.ui.lineEdit_name.isModified()
            or self.ui.lineEdit_chart_no.isModified()
            or self.ui.lineEdit_id.isModified()
            or self.ui.lineEdit_birthday.isModified()
            or self.ui.lineEdit_telephone.isModified()
            or self.ui.lineEdit_cellphone.isModified()
            or self.ui.lineEdit_address.isModified()
            or self.ui.lineEdit_patient_remark.isModified()
        ):
            patient_modified = True

        sql = f"""
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        """
        try:
            row = self.database.select_record(sql)[0]
            share_type = nhi_utils.get_share_type(row["InsType"])
            discount = string_utils.xstr(row["DiscountType"])
            gender = string_utils.xstr(row["Gender"])
            if self.ui.comboBox_patient_share.currentText() != share_type:
                patient_modified = True
            if self.ui.comboBox_patient_discount.currentText() != discount:
                patient_modified = True
            if self.ui.comboBox_gender.currentText() != gender:
                patient_modified = True
        except IndexError:
            pass

        if not patient_modified:
            return

        fields = [
            "ChartNo",
            "Name",
            "ID",
            "Birthday",
            "Telephone",
            "Cellphone",
            "Address",
            "InsType",
            "DiscountType",
            "Gender",
            "Remark",
        ]
        data = [
            self.ui.lineEdit_chart_no.text(),
            self.ui.lineEdit_name.text(),
            self.ui.lineEdit_id.text()[:10],
            self.ui.lineEdit_birthday.text(),
            self.ui.lineEdit_telephone.text()[:15],
            self.ui.lineEdit_cellphone.text()[:15],
            self.ui.lineEdit_address.text()[:50],
            self.ui.comboBox_patient_share.currentText(),
            self.ui.comboBox_patient_discount.currentText(),
            self.ui.comboBox_gender.currentText(),
            self.ui.lineEdit_patient_remark.text(),
        ]
        self.database.update_record(
            "patient", fields, "PatientKey", self.ui.lineEdit_patient_key.text(), data
        )

    def _get_designated_data(self):
        massager = self.ui.comboBox_massager.currentText()
        designated_doctor = "False"
        designated_massager = "False"

        if self.ui.checkBox_designated_doctor.isChecked():
            designated_doctor = "True"
        if massager != "" and self.ui.checkBox_designated_massager.isChecked():
            designated_massager = "True"

        return designated_doctor, designated_massager

    # 病歷存檔
    def _save_medical_record(self, ic_card=None):
        if "掛號存檔" in self.ui.action_save.text():
            case_key = self._insert_medical_record(ic_card)
        else:
            case_key = self._update_medical_record(ic_card)

        return case_key

    def _get_security(self, ic_card, card, card_abnormal):
        card = self._get_card(card)
        if ic_card is None:
            security = case_utils.create_security_xml()
        else:
            security = case_utils.treat_data_to_xml(ic_card.treat_data)

        upload_type = "1"  # 上傳格式
        if card in nhi_utils.ABNORMAL_CARD or card_abnormal in nhi_utils.ABNORMAL_CARD:
            upload_type = "2"

        treat_after_check = "1"  # 補卡註記
        if card == "欠卡":
            treat_after_check = "2"

        security = case_utils.update_xml_doc(security, "upload_type", upload_type)

        security = case_utils.update_xml_doc(
            security, "treat_after_check", treat_after_check
        )

        return security

    def _get_symptom(self):
        symptom = None

        reg_type = self.ui.comboBox_reg_type.currentText()
        if reg_type in nhi_utils.TELECOM_TYPE:
            today = date_utils.now_to_str()
            symptom = f"/* {today} 以{reg_type}方式進行診療 */<br>"

        return symptom

    def _set_traffic_allowance(self, case_key):
        traffic_allowance_fee = number_utils.get_integer(
            self.ui.lineEdit_traditional_health_care_fee.text()
        )
        if traffic_allowance_fee <= 0:
            return

        case_utils.insert_traditional_health_care_prescript(
            self.database,
            self.system_settings,
            case_key,
            traffic_allowance_fee,
            folk_massage_name="代收費",
        )

        fields = ["SMassageFee", "SelfTotalFee", "TotalFee", "ReceiptFee"]
        data = [
            traffic_allowance_fee,
            traffic_allowance_fee,
            traffic_allowance_fee,
            traffic_allowance_fee,
        ]
        self.database.update_record("cases", fields, "CaseKey", case_key, data)

    def _check_traditional_health_care_fee(self, ins_type, case_key):
        traditional_health_care_fee = number_utils.get_integer(
            self.ui.lineEdit_traditional_health_care_fee.text()
        )

        treat_type = self.ui.comboBox_treat_type.currentText()
        if ins_type == "自費":
            if traditional_health_care_fee > 0:
                if treat_type in nhi_utils.TRI_HEAT_TREAT:
                    fields = [
                        "TreatType",
                        "SMassageFee",
                        "SelfTotalFee",
                        "TotalFee",
                        "ReceiptFee",
                    ]
                    data = [
                        treat_type,
                        traditional_health_care_fee,
                        traditional_health_care_fee,
                        traditional_health_care_fee,
                        traditional_health_care_fee,
                    ]
                    self.database.update_record(
                        "cases", fields, "CaseKey", case_key, data
                    )
                    case_utils.remove_traditional_health_care_prescript(
                        self.database,
                        self.system_settings,
                        case_key,
                        folk_massage_name=treat_type,
                    )
                    case_utils.insert_traditional_health_care_prescript(
                        self.database,
                        self.system_settings,
                        case_key,
                        traditional_health_care_fee,
                        folk_massage_name=treat_type,
                    )

                    return
                elif treat_type == "自費健保":
                    pass
                else:
                    treat_type = "民俗調理"

                fields = [
                    "TreatType",
                    "SMassageFee",
                    "SelfTotalFee",
                    "TotalFee",
                    "ReceiptFee",
                ]
                data = [
                    treat_type,
                    traditional_health_care_fee,
                    traditional_health_care_fee,
                    traditional_health_care_fee,
                    traditional_health_care_fee,
                ]
                self.database.update_record("cases", fields, "CaseKey", case_key, data)
                case_utils.remove_traditional_health_care_prescript(
                    self.database, self.system_settings, case_key
                )
                case_utils.insert_traditional_health_care_prescript(
                    self.database,
                    self.system_settings,
                    case_key,
                    traditional_health_care_fee,
                )
            elif self.ui.comboBox_treat_type.currentText() == "民俗調理":
                fields = ["SMassageFee", "SelfTotalFee", "TotalFee", "ReceiptFee"]
                data = [
                    traditional_health_care_fee,
                    traditional_health_care_fee,
                    traditional_health_care_fee,
                    traditional_health_care_fee,
                ]
                self.database.update_record("cases", fields, "CaseKey", case_key, data)
                case_utils.remove_traditional_health_care_prescript(
                    self.database, self.system_settings, case_key
                )

            return

        # 以下是健保民俗調理
        write_health_care = False

        sql = f"""
            SELECT TotalFee FROM cases
            WHERE
                InsType = "自費" AND
                Position1 = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            total_fee = number_utils.get_integer(row["TotalFee"])
            if traditional_health_care_fee == 0:
                case_utils.delete_traditional_health_care(self.database, case_key)
            elif traditional_health_care_fee != total_fee:
                write_health_care = True
        elif (
            self.ui.comboBox_massager.currentText() != ""
            or traditional_health_care_fee > 0
        ):
            write_health_care = True

        if write_health_care:
            try:
                self._write_traditional_health_care(
                    ins_type, case_key, traditional_health_care_fee
                )
            except ValueError:
                pass

    def _check_self_diag_fee(self, ins_type, case_key):
        if ins_type != "自費":
            return

        self_diag_fee = charge_utils.get_self_diag_fee(self.database)
        if self_diag_fee in [None, 0]:
            return

        case_utils.insert_prescript(
            self.database, case_key, "診察", "自費診察費", 1, "次", self_diag_fee
        )

        fields = ["SDiagFee", "SelfTotalFee", "TotalFee", "ReceiptFee"]
        data = [self_diag_fee, self_diag_fee, self_diag_fee, self_diag_fee]
        self.database.update_record("cases", fields, "CaseKey", case_key, data)

    def _get_case_date(self):
        case_date = string_utils.xstr(datetime.datetime.now())

        today = date_utils.date_to_str()
        custom_date = self.ui.dateEdit_case_date.date().toString("yyyy-MM-dd")
        if custom_date != today:
            hour = string_utils.xstr(datetime.datetime.now().hour)
            minute = string_utils.xstr(datetime.datetime.now().minute)
            second = string_utils.xstr(datetime.datetime.now().second)
            case_date = f"{custom_date} {hour}:{minute}:{second}"

        return case_date

    def _is_today(self):
        today = date_utils.date_to_str()
        custom_date = self.ui.dateEdit_case_date.date().toString("yyyy-MM-dd")
        if custom_date != today:
            return False
        else:
            return True

    # 新增病歷
    def _insert_medical_record(self, ic_card=None):
        patient_name = self.ui.lineEdit_name.text()
        card = self._get_card(self.ui.comboBox_card.currentText(), " ")
        course = number_utils.str_to_int(self.ui.comboBox_course.currentText())
        period = self.ui.comboBox_period.currentText()

        card_abnormal = self._get_card(
            self.ui.comboBox_card_abnormal.currentText(), " "
        )
        ins_type = self.ui.comboBox_ins_type.currentText()
        security = self._get_security(ic_card, card, card_abnormal)
        designated_doctor, designated_massager = self._get_designated_data()
        room = self.ui.comboBox_room.currentText()
        doctor = self.ui.comboBox_doctor.currentText()

        regist_fee = self.ui.lineEdit_regist_fee.text()
        s_diag_share_fee = self.ui.lineEdit_diag_share_fee.text()
        deposit_fee = self.ui.lineEdit_deposit_fee.text()

        if self.ui.comboBox_ins_type.currentText() == "健保":
            diag_share_fee = charge_utils.get_diag_share_fee(
                self.database,
                self.system_settings,
                self.ui.comboBox_share_type.currentText(),
                self.ui.comboBox_treat_type.currentText(),
                self.ui.comboBox_course.currentText(),
                self.ui.comboBox_reg_type.currentText(),
            )
        else:
            diag_share_fee = 0

        doctor_done = "False"
        doctor_date = None
        charge_done = "False"
        charge_date = None
        charge_period = None
        if (
            self.ui.comboBox_ins_type.currentText() == "自費"
            and self.ui.comboBox_treat_type.currentText() == "民俗調理"
            and self.system_settings.field("候診名單顯示自費民俗調理") != "Y"
        ):
            doctor_done = "True"
            doctor_date = datetime.datetime.now()
            charge_done = "True"
            charge_date = datetime.datetime.now()
            charge_period = period

        fields = [
            "CaseDate",
            "PatientKey",
            "Name",
            "Visit",
            "RegistType",
            "TourArea",
            "Injury",
            "TreatType",
            "Share",
            "InsType",
            "Card",
            "Continuance",
            "XCard",
            "Period",
            "Room",
            "RegistNo",
            "Massager",
            "Register",
            "DesignatedDoctor",
            "DesignatedMassager",
            "ApplyType",
            "PharmacyType",
            "RegistFee",
            "DiagShareFee",
            "SDiagShareFee",
            "DepositFee",
            "Security",
            "Remark",
            "Doctor",
            "RegistPaymentType",
            "DoctorDone",
            "DoctorDate",
            "ChargeDone",
            "ChargeDate",
            "ChargePeriod",
        ]

        treat_type = self.ui.comboBox_treat_type.currentText()
        share_type = self.ui.comboBox_share_type.currentText()
        remark = self.ui.comboBox_remark.currentText()
        payment_type = self.ui.comboBox_payment_type.currentText()
        case_date = self._get_case_date()

        data = [
            case_date,
            self.ui.lineEdit_patient_key.text(),
            patient_name,
            self.ui.comboBox_visit.currentText(),
            self.ui.comboBox_reg_type.currentText(),
            self.ui.comboBox_area.currentText(),
            self.ui.comboBox_injury_type.currentText(),
            treat_type,
            share_type,
            ins_type,
            card[:6],
            course,
            card_abnormal,
            period,
            room,
            self.ui.spinBox_reg_no.value(),
            self.ui.comboBox_massager.currentText(),
            self.system_settings.field("使用者"),
            designated_doctor,
            designated_massager,
            "申報",
            "申報" if self.system_settings.field("申報藥事服務費") == "Y" else "不申報",
            regist_fee,
            diag_share_fee,
            s_diag_share_fee,
            deposit_fee,
            security,
            remark,
            doctor,
            payment_type,
            doctor_done,
            doctor_date,
            charge_done,
            charge_date,
            charge_period,
        ]
        case_key = self.database.insert_record("cases", fields, data)

        if "確診日期:" in remark:
            try:
                infectious_date = remark.split("確診日期:")[1].strip()
                case_utils.set_case_extend(
                    self.database,
                    case_key,
                    "確診日期",
                    f"{infectious_date.strip()} 00:00:00",
                )
            except Exception:
                pass

        try:
            ic_card_type = ic_card.ic_card_type
        except Exception:
            ic_card_type = None

        if ic_card_type == "虛擬健保卡":
            case_utils.set_case_extend(
                self.database, case_key, "健保卡種類", ic_card_type
            )

        self._set_identification(case_key, card, security)

        if (
            self.ui.comboBox_share_type.currentText()
            in nhi_utils.INFECTIOUS_INJURY_TYPE
        ):
            self._insert_infectious_case(case_key, share_type, treat_type, course)

        if (
            self.ui.comboBox_treat_type.currentText() in nhi_utils.HOME_CARE
        ):  # 居家醫療不寫入民俗調理 2024-10-20 善揚
            self._set_traffic_allowance(case_key)  # 交通費
        else:
            self._check_traditional_health_care_fee(ins_type, case_key)

        self._check_self_diag_fee(ins_type, case_key)

        now = date_utils.now_to_str()
        card = self._set_card(card, course)
        doctor = self.ui.comboBox_doctor.currentText()
        log = f"{patient_name}於{now}完成{ins_type}掛號, 卡序:{card}, 主治醫師: {room}診{doctor}醫師"

        if regist_fee != "0":
            log += f", 掛號費: {regist_fee}"
        if s_diag_share_fee != "0":
            log += f", 門診負擔: {s_diag_share_fee}"
        if deposit_fee != "0":
            log += f", 欠卡費: {deposit_fee}"

        self._write_event_log("掛號存檔", log)

        return case_key

    def _insert_infectious_case(self, case_key, share, treatment, course):
        ins_code, medicine_name = None, None

        items = [
            "(順天堂)台灣清冠一號濃縮顆粒",
            "(莊松榮)台灣清冠一號濃縮顆粒",
            "(康福)台灣清冠一號濃縮顆粒",
            "(勸奉堂)台灣清冠一號濃縮顆粒",
            "(勝昌)台灣清冠一號濃縮顆粒",
            "(華佗)台灣清冠一號濃縮顆粒",
            "(漢聖)台灣清冠一號濃縮顆粒",
            "(天一)台灣清冠一號濃縮顆粒",
            "(天明)台灣清冠一號濃縮顆粒",
            "(科達)台灣清冠一號濃縮顆粒",
            "(富田)台灣清冠一號濃縮顆粒",
        ]
        item, ok = QInputDialog.getItem(
            self, "藥廠名稱", "請選擇台灣清冠一號藥廠", items, 0, False
        )
        if ok and item:
            ins_code, medicine_name, dosage = (
                prescript_utils.get_infectious_drug_factory(item)
            )

        ins_code = charge_utils.get_ins_code_from_charge_settings(
            self.database, "處置費", "台灣清冠一號藥品補助費"
        )
        case_date, _ = case_utils.get_case_date(self.database, case_key)
        treat_fee = charge_utils.get_ins_fee_from_ins_code(
            self.database, ins_code, case_date=case_date
        )
        diag_fee = charge_utils.get_ins_fee_from_ins_code(
            self.database, "E5204C", case_date=case_date
        )
        medicine_set = 1
        packages = 3
        pres_days = 5

        inter_drug_fee = treat_fee * pres_days
        ins_apply_fee = inter_drug_fee + diag_fee

        drug_fee = 0
        agent_fee = charge_utils.get_ins_agent_fee(
            self.database,
            self.system_settings,
            share,
            treatment,
            course,
            drug_fee,
        )

        fields = [
            "DiseaseCode1",
            "DiseaseName1",
            "DiagFee",
            "InterDrugFee",
            "InsApplyFee",
            "InsTotalFee",
            "AgentFee",
        ]
        data = [
            "U071",
            "確認COVID-19病毒感染",
            diag_fee,
            inter_drug_fee,
            ins_apply_fee,
            ins_apply_fee,
            agent_fee,
        ]
        self.database.update_record("cases", fields, "CaseKey", case_key, data)

        if medicine_name is not None:
            fields = [
                "PrescriptNo",
                "CaseKey",
                "CaseDate",
                "MedicineSet",
                "MedicineType",
                "InsCode",
                "MedicineName",
                "DosageMode",
                "Dosage",
                "Unit",
            ]
            data = [
                1,
                case_key,
                date_utils.now_to_str(),
                medicine_set,
                "複方",
                ins_code,
                medicine_name,
                "日劑量",
                dosage,
                "克",
            ]
            self.database.insert_record("prescript", fields, data)

        fields = ["CaseKey", "MedicineSet", "Packages", "Days", "Instruction"]
        data = [case_key, medicine_set, packages, pres_days, "飯後"]
        self.database.insert_record("dosage", fields, data)

    def _write_traditional_health_care(
        self, ins_type, in_case_key, traditional_health_care_fee
    ):
        treat_type = self.ui.comboBox_treat_type.currentText()

        if ins_type == "健保" or (ins_type == "自費" and treat_type != "民俗調理"):
            case_utils.write_traditional_health_care(
                self.database,
                self.system_settings,
                in_case_key,
                traditional_health_care_fee=traditional_health_care_fee,
                massager=self.ui.comboBox_massager.currentText(),
            )
        else:
            case_utils.update_traditional_health_care(
                self.database,
                self.system_settings,
                in_case_key,
                traditional_health_care_fee=traditional_health_care_fee,
            )

    def _save_wait(self, case_key, req_code):
        if "掛號存檔" in self.ui.action_save.text():
            self.insert_wait(case_key, req_code)
        else:
            tab_name = self.ui.tabWidget_list.tabText(
                self.ui.tabWidget_list.currentIndex()
            )
            if tab_name == "候診名單":
                wait_key = self._get_wait_key(case_key, self.ui.tableWidget_wait)
            else:
                wait_key = self._get_wait_key(
                    case_key, self.ui.tableWidget_wait_completed
                )

            if wait_key is None:
                return

            self.update_wait(wait_key)

            if tab_name == "候診名單":
                self.read_wait()
            else:
                self._read_wait_completed()

    def _write_event_log(self, log_type, log):
        log_utils.write_event_log(
            self.database,
            self.system_settings.field("使用者"),
            log_type,
            self.program_name,
            log,
        )

    def _get_wait_key(self, case_key, table_widget_wait):
        wait_key = None

        for row_no in range(table_widget_wait.rowCount()):
            if (
                table_widget_wait.item(row_no, self.wait_column["CaseKey"]).text()
                == case_key
            ):
                wait_key = table_widget_wait.item(
                    row_no, self.wait_column["WaitKey"]
                ).text()
                break

        return wait_key

    # 新增候診名單
    def insert_wait(self, case_key, req_code):
        if (
            self.ui.checkBox_request_token.isChecked()
            and self.ui.comboBox_card.currentText() == "自動取得"
        ):
            card = "請求授權"
        else:
            # card = self._get_card(self.ui.comboBox_card.currentText(), ' ')[:4]
            card = self._get_card(self.ui.comboBox_card.currentText(), " ")

        doctor_done = "False"
        if (
            self.ui.comboBox_ins_type.currentText() == "自費"
            and self.ui.comboBox_treat_type.currentText() == "民俗調理"
            and self.system_settings.field("候診名單顯示自費民俗調理") != "Y"
        ):
            doctor_done = "True"

        fields = [
            "CaseKey",
            "CaseDate",
            "PatientKey",
            "Name",
            "Visit",
            "RegistType",
            "TreatType",
            "Share",
            "InsType",
            "Card",
            "Continuance",
            "Period",
            "Room",
            "RegistNo",
            "Doctor",
            "Massager",
            "Remark",
            "VHCReqCode",
            "DoctorDone",
        ]
        data = [
            case_key,
            string_utils.xstr(datetime.datetime.now()),
            self.ui.lineEdit_patient_key.text(),
            self.ui.lineEdit_name.text(),
            self.ui.comboBox_visit.currentText(),
            self.ui.comboBox_reg_type.currentText(),
            self.ui.comboBox_treat_type.currentText(),
            self.ui.comboBox_share_type.currentText(),
            self.ui.comboBox_ins_type.currentText(),
            card,
            number_utils.str_to_int(self.ui.comboBox_course.currentText()),
            self.ui.comboBox_period.currentText(),
            self.ui.comboBox_room.currentText(),
            self.ui.spinBox_reg_no.value(),
            self.ui.comboBox_doctor.currentText(),
            self.ui.comboBox_massager.currentText(),
            self.ui.comboBox_remark.currentText(),
            req_code,
            doctor_done,
        ]
        self.database.insert_record("wait", fields, data)

    def _save_deposit(self, case_key, card):
        if card != "欠卡":
            return

        sql = f"""
            SELECT * FROM deposit
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return

        self._insert_deposit(case_key)

    def _save_debt(self, case_key):
        total_amount = number_utils.get_integer(self.ui.lineEdit_total_amount.text())
        receipt_fee = number_utils.get_integer(self.ui.lineEdit_receipt_fee.text())
        if receipt_fee >= total_amount:  # 無欠款
            return

        sql = f"""
            SELECT * FROM debt
            WHERE
                CaseKey = {case_key} AND
                DebtType = "掛號欠款"
        """
        rows = self.database.select_record(sql)
        if len(rows) > 0:  # 欠款檔已經存在
            return

        fields = [
            "CaseKey",
            "PatientKey",
            "DebtType",
            "Name",
            "CaseDate",
            "Period",
            "Doctor",
            "Fee",
        ]

        data = [
            case_key,
            self.ui.lineEdit_patient_key.text(),
            "掛號欠款",
            self.ui.lineEdit_name.text(),
            string_utils.xstr(datetime.datetime.now()),
            self.ui.comboBox_period.currentText(),
            None,
            total_amount - receipt_fee,
        ]

        self.database.insert_record("debt", fields, data)

    def _insert_deposit(self, case_key):
        fields = ["CaseKey", "PatientKey", "Name", "DepositDate", "Register", "Fee"]

        data = [
            case_key,
            self.ui.lineEdit_patient_key.text(),
            self.ui.lineEdit_name.text(),
            string_utils.xstr(datetime.datetime.now()),
            self.system_settings.field("使用者"),
            self.ui.lineEdit_deposit_fee.text(),
        ]

        self.database.insert_record("deposit", fields, data)

    def _get_wait_list_field(self, case_key, field_no):
        field_value = None

        for row_no in range(self.ui.tableWidget_wait.rowCount()):
            case_key_item = self.ui.tableWidget_wait.item(
                row_no, self.wait_column["CaseKey"]
            ).text()
            if case_key != case_key_item:
                continue

            item = self.ui.tableWidget_wait.item(row_no, field_no)
            if item is not None:
                field_value = item.text()

            break

        return field_value

    # 修正病歷
    def _update_medical_record(self, ic_card=None):
        case_key = self.ui.groupBox_registration.title().split("-")[-1]
        ins_type = self.ui.comboBox_ins_type.currentText()

        charge_utils.calculate_ins_fee(
            self.database, self.system_settings, case_key, ins_type=ins_type
        )  # 自費也要將健保批價歸零 2023.09.13 太初

        if case_key in ["", None]:
            tab_name = self.ui.tabWidget_list.tabText(
                self.ui.tabWidget_list.currentIndex()
            )
            if tab_name == "候診名單":
                case_key = self.table_widget_wait.field_value(
                    self.wait_column["CaseKey"]
                )
            else:
                case_key = self.table_widget_wait_completed.field_value(
                    self.wait_done_column["CaseKey"]
                )

        fields = [
            "CaseDate",
            "Name",
            "Visit",
            "RegistType",
            "TourArea",
            "Injury",
            "TreatType",
            "Share",
            "InsType",
            "Card",
            "Continuance",
            "XCard",
            "Period",
            "Room",
            "RegistNo",
            "Doctor",
            "Massager",
            "DesignatedDoctor",
            "DesignatedMassager",
            "ApplyType",
            "PharmacyType",
            "RegistFee",
            "DiagShareFee",
            "SDiagShareFee",
            "DepositFee",
            "Remark",
            "RegistPaymentType",
        ]

        diag_share_fee = charge_utils.get_diag_share_fee(
            self.database,
            self.system_settings,
            self.ui.comboBox_share_type.currentText(),
            self.ui.comboBox_treat_type.currentText(),
            self.ui.comboBox_course.currentText(),
            self.ui.comboBox_reg_type.currentText(),
        )
        patient_key = self.ui.lineEdit_patient_key.text()
        patient_name = self.ui.lineEdit_name.text()
        card = self._get_card(self.ui.comboBox_card.currentText(), " ")
        course = number_utils.str_to_int(self.ui.comboBox_course.currentText())
        card_abnormal = self._get_card(
            self.ui.comboBox_card_abnormal.currentText(), " "
        )
        room = self.ui.comboBox_room.currentText()
        regist_no = self.ui.spinBox_reg_no.value()
        doctor = self.ui.comboBox_doctor.currentText()
        massager = self.ui.comboBox_massager.currentText()
        designated_doctor, designated_massager = self._get_designated_data()

        regist_fee = self.ui.lineEdit_regist_fee.text()
        deposit_fee = self.ui.lineEdit_deposit_fee.text()
        ins_type = self.ui.comboBox_ins_type.currentText()
        s_diag_share_fee = self.ui.lineEdit_diag_share_fee.text()
        remark = self.ui.comboBox_remark.currentText()
        payment_type = self.ui.comboBox_payment_type.currentText()
        treat_type = self.ui.comboBox_treat_type.currentText()

        case_date = self._get_case_date()

        self._check_traditional_health_care_fee(ins_type, case_key)
        self._check_ins_regist_fee(case_key, regist_fee)

        if ins_type == "自費":
            if treat_type == "自費健保":
                pass
            else:
                diag_share_fee = 0
                s_diag_share_fee = 0

        data = [
            case_date,
            patient_name,
            self.ui.comboBox_visit.currentText(),
            self.ui.comboBox_reg_type.currentText(),
            self.ui.comboBox_area.currentText(),
            self.ui.comboBox_injury_type.currentText(),
            treat_type,
            self.ui.comboBox_share_type.currentText(),
            self.ui.comboBox_ins_type.currentText(),
            card[:6],
            course,
            card_abnormal,
            self.ui.comboBox_period.currentText(),
            room,
            regist_no,
            doctor,
            massager,
            designated_doctor,
            designated_massager,
            "申報",
            "申報" if self.system_settings.field("申報藥事服務費") == "Y" else "不申報",
            regist_fee,
            diag_share_fee,
            s_diag_share_fee,
            deposit_fee,
            remark,
            payment_type,
        ]

        self.database.update_record("cases", fields, "CaseKey", case_key, data)

        try:
            self._update_traditional_healthy_data(case_key, patient_key, massager)
        except Exception:
            pass

        if "確診日期:" in remark:
            try:
                infectious_date = remark.split("確診日期:")[-1]
                case_utils.set_case_extend(
                    self.database,
                    case_key,
                    "確診日期",
                    f"{infectious_date.strip()} 00:00:00",
                )
            except Exception:
                pass

        if ic_card is not None:  # 重新產生卡序
            security = self._get_security(ic_card, card, card_abnormal)
            fields = ["Security"]
            data = [security]
            self.database.update_record("cases", fields, "CaseKey", case_key, data)
            origin_card = self._get_card(
                self._get_wait_list_field(case_key, self.wait_column["Card"])
            )
            if origin_card == "欠卡":
                self.database.delete_record("deposit", "CaseKey", case_key)

            self._set_identification(case_key, card, security)

        now = date_utils.now_to_str()
        card = self._set_card(card, course)
        log = f"{patient_name}於{now}執行掛號修正, 卡序:{card}, 主治醫師: {room}診{doctor}醫師"

        if regist_fee != "0":
            log += f", 掛號費: {regist_fee}"
        if s_diag_share_fee != "0":
            log += f", 門診負擔: {s_diag_share_fee}"
        if deposit_fee != "0":
            log += f", 欠卡費: {deposit_fee}"

        self._write_event_log("掛號修正", log)

        return case_key

    def _set_identification(self, case_key, card, security):
        if card not in ["欠卡"]:
            return

        try:
            identification = case_utils.extract_security_xml(security, "就醫識別碼")
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                case_utils.extract_security_xml(security, "寫卡時間")
            )
            case_utils.clear_case_extend(self.database, case_key, "原就醫識別碼")
            case_utils.set_case_extend(
                self.database, case_key, "原就醫識別碼", identification
            )

            case_utils.clear_case_extend(self.database, case_key, "實際就醫日期")
            case_utils.set_case_extend(
                self.database, case_key, "實際就醫日期", registered_date
            )
        except Exception:
            pass

    # 更新推拿師
    def _update_traditional_healthy_data(self, case_key, patient_key, massager):
        sql = f'''
            UPDATE cases
            SET
                Massager = "{massager}"
            WHERE
                PatientKey = {patient_key} AND
                TreatType = "民俗調理" AND
                Position1 = {case_key}
        '''
        self.database.exec_sql(sql)

    # 修正候診名單
    def update_wait(self, wait_key):
        renew_case_date = False

        sql = f"""
            SELECT Card FROM wait
            WHERE
                WaitKey = {wait_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            if string_utils.xstr(row["Card"]) in self.temp_card_list:
                renew_case_date = True

        fields = [
            "Name",
            "Visit",
            "RegistType",
            "TreatType",
            "Share",
            "InsType",
            "Card",
            "Continuance",
            "Period",
            "Room",
            "RegistNo",
            "Doctor",
            "Massager",
            "Remark",
        ]

        card = self._get_card(self.ui.comboBox_card.currentText(), " ")
        data = [
            self.ui.lineEdit_name.text(),
            self.ui.comboBox_visit.currentText(),
            self.ui.comboBox_reg_type.currentText(),
            self.ui.comboBox_treat_type.currentText(),
            self.ui.comboBox_share_type.currentText(),
            self.ui.comboBox_ins_type.currentText(),
            # card[:4],
            card,
            number_utils.str_to_int(self.ui.comboBox_course.currentText()),
            self.ui.comboBox_period.currentText(),
            self.ui.comboBox_room.currentText(),
            self.ui.spinBox_reg_no.value(),
            self.ui.comboBox_doctor.currentText(),
            self.ui.comboBox_massager.currentText(),
            self.ui.comboBox_remark.currentText()[:100],
        ]
        if renew_case_date:
            fields.append("CaseDate")
            data.append(datetime.datetime.now())

        self.database.update_record("wait", fields, "WaitKey", wait_key, data)

    # 診前檢查
    def _exam_precheck(self):
        tab_name = self.ui.tabWidget_list.tabText(self.ui.tabWidget_list.currentIndex())
        if tab_name == "候診名單":
            case_key = self.table_widget_wait.field_value(self.wait_column["CaseKey"])
        else:
            case_key = self.table_widget_wait_completed.field_value(
                self.wait_done_column["CaseKey"]
            )

        dialog = dialog_utils.get_dialog_exam_precheck(
            self,
            self.database,
            self.system_settings,
            case_key,
            "掛號作業",
        )
        dialog.exec_()
        dialog.deleteLater()

    # 補印掛號收據
    def print_wait(self):
        tab_name = self.ui.tabWidget_list.tabText(self.ui.tabWidget_list.currentIndex())
        if tab_name == "候診名單":
            case_key = self.table_widget_wait.field_value(self.wait_column["CaseKey"])
            ins_type = self.table_widget_wait.field_value(self.wait_column["InsType"])
            treat_type = self.table_widget_wait.field_value(
                self.wait_column["TreatType"]
            )
        else:
            case_key = self.table_widget_wait_completed.field_value(
                self.wait_done_column["CaseKey"]
            )
            ins_type = self.table_widget_wait_completed.field_value(
                self.wait_done_column["InsType"]
            )
            treat_type = self.table_widget_wait_completed.field_value(
                self.wait_done_column["TreatType"]
            )

        self.print_regist(ins_type, treat_type, "直接列印", case_key)

    def print_wait_massage(self):
        tab_name = self.ui.tabWidget_list.tabText(self.ui.tabWidget_list.currentIndex())
        if tab_name == "候診名單":
            case_key = self.table_widget_wait.field_value(self.wait_column["CaseKey"])
        else:
            case_key = self.table_widget_wait_completed.field_value(
                self.wait_done_column["CaseKey"]
            )

        if not case_utils.is_traditional_health_case(self.database, case_key):
            system_utils.show_message_box(
                QMessageBox.Critical,
                "錯誤",
                """
                    <font size="5" color="red">
                        <b>非民俗調理病歷, 無法列印.</b>
                    </font>
                """,
                "請確定是否為民俗調理.",
            )
            return

        self.print_massage_form("直接列印", case_key)

    # 列印掛號收據
    def print_regist(self, ins_type, treat_type, printable, case_key=False):
        if not case_key:
            case_key = self.table_widget_wait.field_value(self.wait_column["CaseKey"])

        if ins_type == "健保":
            self.print_registration_form(printable, case_key)
            if case_utils.is_traditional_health_case(
                self.database, case_key
            ) or case_utils.is_self_traditional_health_case(self.database, case_key):
                self.print_massage_form(printable, case_key)
        elif ins_type == "自費":
            if treat_type == "自費健保":
                self.print_registration_form(printable, case_key)
            else:
                self.print_registration_form(printable, case_key)

            if (
                treat_type == "民俗調理"
                or case_utils.is_traditional_health_case(self.database, case_key)
                or case_utils.is_self_traditional_health_case(self.database, case_key)
            ):
                self.print_massage_form(printable, case_key)

    # 列印掛號收據
    def print_registration_form(self, printable, case_key=None):
        regist_fee = 0
        diag_share_fee = 0
        deposit_fee = 0

        if case_key is not None:
            sql = f"""
                SELECT RegistFee, SDiagShareFee, DepositFee FROM cases
                WHERE
                    CaseKey = {case_key}
            """
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                row = rows[0]
                regist_fee = number_utils.get_integer(row["RegistFee"])
                diag_share_fee = number_utils.get_integer(row["SDiagShareFee"])
                deposit_fee = number_utils.get_integer(row["DepositFee"])

        total_amount = regist_fee + diag_share_fee + deposit_fee

        if (
            self.system_settings.field("掛號收據無金額不列印") == "Y"
            and total_amount <= 0
        ):  # 金正中醫 2022.12.27
            return

        if not case_key:
            case_key = self.table_widget_wait.field_value(self.wait_column["CaseKey"])

        printer_utils.print_regist_form(
            self, self.database, self.system_settings, case_key, printable
        )

    # 列印民俗調理單
    def print_massage_form(self, printable, case_key=False):
        if (
            self.ui.comboBox_treat_type.currentText() in nhi_utils.HOME_CARE
        ):  # 居家醫療不列印 2024-10-20 善揚
            return

        if not case_key:
            case_key = self.table_widget_wait.field_value(self.wait_column["CaseKey"])

        printer_utils.print_massage_form(
            self, self.database, self.system_settings, case_key, printable
        )

    # 列印處方箋
    def _print_prescript(self):
        case_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["CaseKey"]
        )
        printer_utils.print_prescription_form(
            self, self.database, self.system_settings, case_key, "選擇列印"
        )

    # 列印費用收據
    def _print_receipt(self):
        case_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["CaseKey"]
        )
        printer_utils.print_receipt_form(
            self, self.database, self.system_settings, case_key, "選擇列印"
        )

    # 列印其他收據1
    def _print_misc1(self):
        case_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["CaseKey"]
        )
        printer_utils.print_misc_form(
            self, self.database, self.system_settings, case_key, "選擇列印"
        )

    # 列印其他收據2
    def _print_misc2(self):
        case_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["CaseKey"]
        )
        printer_utils.print_misc_form2(
            self, self.database, self.system_settings, case_key, "選擇列印"
        )

    def _reservation(self):
        self._parent.open_reservation(None, None, None)

    def reservation_arrival(
        self, reserve_key, late=False, late_remark="預約到報過號", vhc_ic_card=None
    ):
        """預約報到."""
        self.reserve_key = None
        sql = f"""
            SELECT * FROM reserve
            WHERE
                ReserveKey = {reserve_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self._cancel_registration()
        self.vhc_ic_card = vhc_ic_card
        self.reserve_key = reserve_key
        row = rows[0]
        doctor = string_utils.xstr(row["Doctor"])
        period = string_utils.xstr(row["Period"])
        remark = string_utils.xstr(row["Remark"])
        self._get_patient(string_utils.xstr(row["PatientKey"]))
        self.ui.comboBox_reg_type.setCurrentText("預約門診")
        self.ui.comboBox_doctor.setCurrentText(doctor)
        self.ui.comboBox_remark.setCurrentText(remark)

        room = registration_utils.get_room(self.database, period, doctor)
        if room is None:
            room = row["Room"]

        self.ui.comboBox_room.setCurrentText(string_utils.xstr(room))
        if late:
            self.ui.comboBox_remark.setCurrentText(late_remark)

        reg_type = self.ui.comboBox_reg_type.currentText()
        share_type = self._get_share_type(reg_type)
        self.ui.comboBox_share_type.setCurrentText(share_type)

    def _waiting_list_tab_changed(self, i):
        tab_name = self.ui.tabWidget_list.tabText(i)
        period = registration_utils.get_current_period(self.system_settings)
        self._set_radio_button_period(period)

        if tab_name == "候診名單":
            self.read_wait()
        else:
            self._read_wait_completed()

    def _get_period_script(self, table_name):
        period_script = ""

        if self.ui.radioButton_period1.isChecked():
            period_script = f' AND {table_name}.Period = "早班" '
        elif self.ui.radioButton_period2.isChecked():
            period_script = f' AND {table_name}.Period = "午班" '
        elif self.ui.radioButton_period3.isChecked():
            period_script = f' AND {table_name}.Period = "晚班" '

        return period_script

    def _read_wait_completed(self):
        period_script = self._get_period_script("cases")
        if self.system_settings.field("掛號已就診名單顯示自購藥病歷") == "Y":
            purchase_script = ""
        else:
            purchase_script = ' AND wait.TreatType NOT IN ("自購")'

        sql = f"""
            SELECT
                wait.WaitKey, cases.*, patient.Gender
            FROM wait
                LEFT JOIN patient ON wait.PatientKey = patient.PatientKey
                LEFT JOIN cases ON wait.CaseKey = cases.CaseKey
            WHERE
                cases.DoctorDone = "True"
                {purchase_script}
                {period_script}
            ORDER BY FIELD(cases.Period, "晚班", "午班", "早班"), cases.RegistNo DESC
        """

        self.table_widget_wait_completed.set_db_data(sql, self._set_wait_completed_data)
        row_count = self.table_widget_wait_completed.row_count()

        if row_count > 0:
            self._set_wait_completed_tool_button(True)
        else:
            self._set_wait_completed_tool_button(False)

        self._wait_completed_table_item_changed()

    def _set_wait_completed_data(self, row_no, row):
        case_key = row["CaseKey"]
        pres_days = case_utils.get_pres_days(self.database, case_key)
        if pres_days <= 0:
            pres_days = ""

        prescript_sign = case_utils.extract_security_xml(row["Security"], "醫令時間")
        ins_type = string_utils.xstr(row["InsType"])
        # card = string_utils.xstr(row['Card'])[:4]
        card = string_utils.xstr(row["Card"])  # 不能只取前四碼
        course = number_utils.get_integer(row["Continuance"])
        xcard = string_utils.xstr(row["XCard"])[:4]

        card_str = self._set_card(card, course)

        if (
            ins_type != "健保"
            or card == "欠卡"
            or card[:4] in nhi_utils.ABNORMAL_CARD
            or xcard in nhi_utils.ABNORMAL_CARD
        ):
            ic_wrote = "略"
        elif prescript_sign is None:
            ic_wrote = "否"
        else:
            ic_wrote = "是"

        if card[:4] in nhi_utils.INFECTIOUS_CARD and prescript_sign is None:
            ic_wrote = "否"

        regist_fee = number_utils.get_integer(row["RegistFee"])
        diag_share_fee = number_utils.get_integer(row["SDiagShareFee"])
        drug_share_fee = number_utils.get_integer(row["SDrugShareFee"])
        deposit_fee = number_utils.get_integer(row["DepositFee"])
        ins_type = string_utils.xstr(row["InsType"])
        total_fee = number_utils.get_integer(row["TotalFee"])

        if self.system_settings.field("掛號名單顯示民俗調理費") == "Y":  # 顯示速度太慢
            traditional_health_care_fee = (
                charge_utils.get_traditional_health_care_fee_from_case(
                    self.database, case_key, ins_type=ins_type
                )
            )
        else:
            traditional_health_care_fee = 0

        if ins_type == "自費":
            total_fee -= traditional_health_care_fee  # 這樣才不會重複算到民俗調理費

        receipt_fee = (
            regist_fee
            + diag_share_fee
            + drug_share_fee
            + deposit_fee
            + total_fee
            + traditional_health_care_fee
        )

        remark = string_utils.get_str(row["Remark"], "utf8")[:20]
        remark = string_utils.replace_ascii_char(["\n"], remark)

        wait_row = [
            string_utils.xstr(row["WaitKey"]),
            case_key,
            row["PatientKey"],
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["Gender"]),
            ins_type,
            string_utils.xstr(row["Share"]),
            string_utils.xstr(row["TreatType"]),
            pres_days,
            string_utils.xstr(row["Visit"]),
            card_str,
            row["Room"],
            row["RegistNo"],
            string_utils.xstr(ic_wrote),
            string_utils.xstr(row["Doctor"]),
            row["DrugNo"],
            regist_fee,
            diag_share_fee,
            drug_share_fee,
            deposit_fee,
            total_fee,
            traditional_health_care_fee,
            receipt_fee,
            remark,
        ]

        for col_no in range(len(wait_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, wait_row[col_no])

            self.ui.tableWidget_wait_completed.setItem(
                row_no,
                col_no,
                item,
            )
            if col_no in [
                self.wait_done_column["PatientKey"],
                self.wait_done_column["Room"],
                self.wait_done_column["PresDays"],
                self.wait_done_column["RegistNo"],
                self.wait_done_column["DrugNo"],
                self.wait_done_column["RegistFee"],
                self.wait_done_column["DiagShareFee"],
                self.wait_done_column["DrugShareFee"],
                self.wait_done_column["DepositFee"],
                self.wait_done_column["TotalFee"],
                self.wait_done_column["MassageFee"],
                self.wait_done_column["ReceiptFee"],
            ]:
                self.ui.tableWidget_wait_completed.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            elif col_no in [
                self.wait_done_column["Gender"],
                self.wait_done_column["Visit"],
                self.wait_done_column["WriteCard"],
            ]:
                self.ui.tableWidget_wait_completed.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

            if number_utils.get_integer(row["TotalFee"]) > 0:
                self.ui.tableWidget_wait_completed.item(row_no, col_no).setForeground(
                    QtGui.QColor("blue")
                )
            elif course >= 2:
                self.ui.tableWidget_wait_completed.item(row_no, col_no).setForeground(
                    QtGui.QColor("darkGreen")
                )

            if ic_wrote == "否":
                self.ui.tableWidget_wait_completed.item(row_no, col_no).setForeground(
                    QtGui.QColor("darkred")
                )

    def _wait_table_item_changed(self):
        row_no = self.ui.tableWidget_wait.currentRow()
        wait_key = self.ui.tableWidget_wait.item(row_no, self.wait_column["WaitKey"])
        if wait_key is None:
            return

        wait_key = wait_key.text()
        if vhc_utils.get_vhc_req_code_from_wait(self.database, wait_key) is None:
            enabled = False
        else:
            enabled = True

        self.ui.toolButton_vhc_get_seq_number.setEnabled(enabled)

    def _wait_completed_table_item_changed(self):
        row_no = self.ui.tableWidget_wait_completed.currentRow()
        ic_wrote = self.ui.tableWidget_wait_completed.item(
            row_no, self.wait_done_column["WriteCard"]
        )
        if ic_wrote is not None:
            ic_wrote = ic_wrote.text()

        card = self.ui.tableWidget_wait_completed.item(
            row_no, self.wait_done_column["Card"]
        )
        if card is not None:
            card = card.text()

        self.ui.toolButton_write_ic_treatment.setEnabled(False)  # IC寫卡
        self.ui.toolButton_rewrite_ic_card.setEnabled(False)  # 重寫IC
        self.ui.toolButton_rewrite_ic_prescript.setEnabled(False)  # 重寫醫令
        self.ui.toolButton_ic_cancel_2.setEnabled(False)  # IC退掛

        if ic_wrote in ["是", "否"]:
            self.ui.toolButton_ic_cancel_2.setEnabled(True)  # IC退掛
            self.ui.toolButton_rewrite_ic_card.setEnabled(True)  # 重寫IC

            if ic_wrote == "是":
                self.ui.toolButton_rewrite_ic_prescript.setEnabled(True)  # 重寫醫令
            elif ic_wrote == "否":
                self.ui.toolButton_write_ic_treatment.setEnabled(True)  # IC寫卡
                if card in nhi_utils.INFECTIOUS_CARD:
                    self.ui.toolButton_write_ic_treatment.setEnabled(False)  # IC寫卡

        self._set_permission()

    # 快速寫入健保卡
    def _action_quick_write_ic_treatment(self):
        self._read_wait_completed()
        self._quick_write_ic_treatment()

    def _request_req_code(self, show_message=True):
        tab_name = self.ui.tabWidget_list.tabText(self.ui.tabWidget_list.currentIndex())
        if tab_name == "候診名單":
            wait_key = self.table_widget_wait.field_value(self.wait_column["WaitKey"])
            patient_key = self.table_widget_wait.field_value(
                self.wait_column["PatientKey"]
            )
        else:
            wait_key = self.table_widget_wait_completed.field_value(
                self.wait_done_column["WaitKey"]
            )
            patient_key = self.table_widget_wait_completed.field_value(
                self.wait_done_column["PatientKey"]
            )

        patient_id = patient_utils.get_patient_id(self.database, patient_key)
        ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        req_code = ic_card.request_token(patient_id)

        sql = f'''
            UPDATE wait
            SET
                VHCReqCode = "{req_code}"
            WHERE
                WaitKey = {wait_key}
        '''

        self.database.exec_sql(sql)
        if show_message:
            system_utils.show_message_box(
                QMessageBox.Information,
                "請求成功",
                """
                    <font size="5" color="red">
                        <b>虛擬健保卡授權碼請求成功.</b>
                    </font>
                """,
                "請求完成.",
            )
            self.read_wait()
            self._wait_table_item_changed()

    def _vhc_get_seq_number(self):
        wait_key = self.table_widget_wait.field_value(self.wait_column["WaitKey"])
        case_key = self.table_widget_wait.field_value(self.wait_column["CaseKey"])
        patient_key = self.table_widget_wait.field_value(self.wait_column["PatientKey"])
        share_type = self.table_widget_wait.field_value(self.wait_column["ShareType"])
        treat_type = self.table_widget_wait.field_value(self.wait_column["TreatType"])

        card = self._get_card(
            self.table_widget_wait.field_value(self.wait_column["Card"])
        )
        course = self._get_course(card)

        vhc_req_code = vhc_utils.get_vhc_req_code_from_wait(self.database, wait_key)
        if vhc_req_code is None:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "請求失敗",
                """
                    <font size="5" color="red">
                        <b>尚未取得虛擬健保卡授權, 請重新取得授權.</b>
                    </font>
                """,
                "請重新請求授權.",
            )
            return

        ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        qrcode = ic_card.get_response_token(vhc_req_code)
        self.vhc_ic_card = class_utils.get_vhccshis(
            self, self.database, self.system_settings, qrcode
        )

        if qrcode is None:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "請求失敗",
                """
                    <font size="5" color="red">
                        <b>請求虛擬健保卡就醫序號簽章失敗, 請重新請求授權.</b>
                    </font>
                """,
                "請重新請求授權.",
            )
            return

        row = patient_utils.get_patient_row(self.database, patient_key)
        if row is not None and self.vhc_ic_card.read_basic_data():
            self._check_ic_card_basic_data(self.vhc_ic_card, row, use_vhc_ic_card=True)

        if card in ["自動取得", "請求授權"]:  # 2025-05-13 居家醫療本月首次要取得卡序
            treat_type = None

        ic_card_ok = self.vhc_ic_card.write_ic_card(
            "掛號寫卡",
            patient_key,
            course,
            share_type,
            cshis_utils.NORMAL_CARD,
            treat_type=treat_type,
        )
        if not ic_card_ok:
            return

        self.update_cases_by_ic_card(self.vhc_ic_card, case_key, card, course)
        self.update_wait_by_ic_card(self.vhc_ic_card, card, case_key)
        case_utils.set_case_extend(self.database, case_key, "健保卡種類", "虛擬健保卡")
        self.read_wait()
        system_utils.show_message_box(
            QMessageBox.Information,
            "請求成功",
            """
                <font size="5" color="red">
                    <b>虛擬健保卡就醫序號請求成功.</b>
                </font>
            """,
            "請求完成.",
        )

    def _quick_write_ic_treatment(self):
        current_row = self.ui.tableWidget_wait_completed.currentRow()
        ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        if ic_card is None:
            return

        if not ic_card.read_basic_data():
            return

        patient_found = False
        for row_no in range(self.ui.tableWidget_wait_completed.rowCount()):
            self.ui.tableWidget_wait_completed.setCurrentCell(row_no, 2)
            ins_type = self.table_widget_wait_completed.field_value(
                self.wait_done_column["InsType"]
            )
            if ins_type != "健保":
                continue

            patient_key = self.table_widget_wait_completed.field_value(
                self.wait_done_column["PatientKey"]
            )
            patient_id = patient_utils.get_patient_id(self.database, patient_key)

            if ic_card.basic_data["patient_id"] == patient_id:
                patient_found = True
                break

        if not patient_found:
            name = ic_card.basic_data["name"]
            system_utils.show_message_box(
                QMessageBox.Critical,
                "找不到此人的病歷",
                f"""
                    <font size="5" color="red">
                        <b>找不到{name}的病歷, 無法執行健保卡就醫資料寫入作業.</b>
                    </font>
                """,
                "請確定插入的健保卡是否正確.",
            )
            self.ui.tableWidget_wait_completed.setCurrentCell(current_row, 2)
            return

        if (
            self.table_widget_wait_completed.field_value(
                self.wait_done_column["WriteCard"]
            )
            == "是"
        ):
            name = self.table_widget_wait_completed.field_value(3)
            system_utils.show_message_box(
                QMessageBox.Critical,
                "健保卡病歷已寫入",
                f"""
                    <font size="5" color="red">
                        <b>{name}的健保卡病歷已寫入, 不需要再執行健保卡就醫資料寫入作業.</b>
                    </font>
                """,
                "請取出健保卡.",
            )
            return

        case_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["CaseKey"]
        )
        card = self._get_card(
            self.table_widget_wait_completed.field_value(self.wait_done_column["Card"])
        )

        if card == "":
            self.rewrite_ic_card()
            self._read_wait_completed()
            return

        ic_card.write_ic_medical_record(case_key, cshis_utils.NORMAL_CARD)
        self._read_wait_completed()

    def write_ic_treatment(self):
        name = self.table_widget_wait_completed.field_value(
            self.wait_done_column["Name"]
        )

        msg_box = dialog_utils.get_message_box(
            "寫入健保卡就醫資料",
            QMessageBox.Question,
            f"<h3>確定寫入{name}的健保卡就醫資料?</h3>",
            "注意！請插入健保卡或掃描虛擬健保卡!",
        )
        write_ic_card = msg_box.exec_()
        if not write_ic_card:
            return

        wait_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["WaitKey"]
        )
        case_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["CaseKey"]
        )
        patient_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["PatientKey"]
        )
        card = self.table_widget_wait_completed.field_value(
            self.wait_done_column["Card"]
        )

        course = self._get_course(card)
        card = self._get_card(card)

        if card in ["", "自動取得"]:
            self.rewrite_ic_card()
            self._read_wait_completed()
            return

        ic_card_type = case_utils.get_ic_card_type(self.database, case_key)
        if ic_card_type == "虛擬健保卡":
            qrcode = None
            vhc_req_code = vhc_utils.get_vhc_req_code_from_wait(self.database, wait_key)
            if vhc_req_code is not None:
                self._request_req_code(show_message=False)
                vhc_req_code = vhc_utils.get_vhc_req_code_from_wait(
                    self.database, wait_key
                )

                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("取得病患授權")
                msg_box.setText(
                    """
                    <font size="5" color="blue">
                    <b>請問病患是否已在健保快易通授權?<br>
                    </font>
                    """
                )
                msg_box.setInformativeText("取得虛擬健保卡授權")
                msg_box.addButton(QPushButton("尚未取得"), QMessageBox.NoRole)
                msg_box.addButton(QPushButton("病患已經授權"), QMessageBox.YesRole)
                get_response = msg_box.exec_()
                if not get_response:
                    return

                ic_card = class_utils.get_cshis(
                    self, self.database, self.system_settings
                )
                qrcode = ic_card.get_response_token(vhc_req_code)
                if qrcode is None:
                    system_utils.show_message_box(
                        QMessageBox.Critical,
                        "無法寫卡",
                        '<font size="5" color="red"><b>無法使用虛擬健保卡寫卡, 無法取得授權.</b></font>',
                        "請重新取得授權.",
                    )
                    return

            ic_card = class_utils.get_vhccshis(
                self, self.database, self.system_settings, qrcode
            )
        else:
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)

            if not ic_card.insert_correct_ic_card(patient_key):
                return

        share_type = self.table_widget_wait_completed.field_value(
            self.wait_done_column["ShareType"]
        )

        security = case_utils.get_case_field_value(self.database, case_key, "Security")
        signature = case_utils.extract_security_xml(security, "安全簽章")

        # identifier = case_utils.extract_security_xml(security, '就醫識別碼')
        # ic_card_time = case_utils.extract_security_xml(security, '寫卡時間')
        # new_identifier = ic_card.get_identifier(ic_card_time)

        if signature in ["", None]:
            ic_card_ok = ic_card.write_ic_card(
                "掛號寫卡",
                patient_key,
                course,
                share_type,
                cshis_utils.NORMAL_CARD,
            )
            if not ic_card_ok:
                return

            self.update_cases_by_ic_card(ic_card, case_key, card, course)

        ic_card.write_ic_medical_record(case_key, cshis_utils.NORMAL_CARD)
        self.update_wait_by_ic_card(ic_card, card, case_key)
        self._read_wait_completed()

    def write_ic_treatment_by_qrcode(self):
        name = self.table_widget_wait_completed.field_value(
            self.wait_done_column["Name"]
        )

        msg_box = dialog_utils.get_message_box(
            "寫入健保卡就醫資料",
            QMessageBox.Question,
            f"<h3>確定寫入{name}的健保卡就醫資料?</h3>",
            "注意！請插入健保卡!",
        )
        write_ic_card = msg_box.exec_()
        if not write_ic_card:
            return

        case_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["CaseKey"]
        )
        patient_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["PatientKey"]
        )
        card = self._get_card(
            self.table_widget_wait_completed.field_value(self.wait_done_column["Card"])
        )

        qrcode = system_utils.get_qrcode_from_file(self)
        if qrcode is None:
            return

        if card == "":
            self.rewrite_vhc_card_by_qrcode(qrcode)
            self._read_wait_completed()
            return

        ic_card = class_utils.get_vhccshis(
            self, self.database, self.system_settings, qrcode
        )

        if not ic_card.insert_correct_ic_card(patient_key):
            return

        ic_card.write_ic_medical_record(case_key, cshis_utils.NORMAL_CARD)
        self._read_wait_completed()

    # 重寫醫令
    def rewrite_ic_prescript(self):
        name = self.table_widget_wait_completed.field_value(
            self.wait_done_column["Name"]
        )

        msg_box = dialog_utils.get_message_box(
            "重新寫入健保卡醫令資料",
            QMessageBox.Question,
            f"<h3>確定重新寫入{name}的健保卡醫令資料?</h3>",
            "注意！請插入健保卡!",
        )
        write_ic_card = msg_box.exec_()
        if not write_ic_card:
            return

        wait_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["WaitKey"]
        )
        case_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["CaseKey"]
        )
        patient_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["PatientKey"]
        )

        ic_card_type = case_utils.get_ic_card_type(self.database, case_key)
        if ic_card_type == "虛擬健保卡":
            qrcode = None
            vhc_req_code = vhc_utils.get_vhc_req_code_from_wait(self.database, wait_key)
            if vhc_req_code is not None:
                self._request_req_code(show_message=False)
                vhc_req_code = vhc_utils.get_vhc_req_code_from_wait(
                    self.database, wait_key
                )

                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("取得病患授權")
                msg_box.setText(
                    """
                    <font size="5" color="blue">
                    <b>請問病患是否已在健保快易通授權?<br>
                    </font>
                    """
                )
                msg_box.setInformativeText("取得虛擬健保卡授權")
                msg_box.addButton(QPushButton("尚未取得"), QMessageBox.NoRole)
                msg_box.addButton(QPushButton("病患已經授權"), QMessageBox.YesRole)
                get_response = msg_box.exec_()
                if not get_response:
                    return

                ic_card = class_utils.get_cshis(
                    self, self.database, self.system_settings
                )
                qrcode = ic_card.get_response_token(vhc_req_code)
                if qrcode is None:
                    system_utils.show_message_box(
                        QMessageBox.Critical,
                        "無法寫卡",
                        '<font size="5" color="red"><b>無法使用虛擬健保卡寫卡, 無法取得授權.</b></font>',
                        "請重新取得授權.",
                    )
                    return

            ic_card = class_utils.get_vhccshis(
                self, self.database, self.system_settings, qrcode
            )
        else:
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)

            if not ic_card.insert_correct_ic_card(patient_key):
                return

        ic_card.rewrite_ic_prescript(case_key)

    # 重寫醫令
    def rewrite_vhc_prescript_by_qrcode(self):
        name = self.table_widget_wait_completed.field_value(
            self.wait_done_column["Name"]
        )

        msg_box = dialog_utils.get_message_box(
            "重新寫入健保卡醫令資料",
            QMessageBox.Question,
            f"<h3>確定重新寫入{name}的健保卡醫令資料?</h3>",
            "注意！請插入健保卡!",
        )
        write_ic_card = msg_box.exec_()
        if not write_ic_card:
            return

        case_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["CaseKey"]
        )
        patient_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["PatientKey"]
        )

        qrcode = system_utils.get_qrcode_from_file(self)
        if qrcode is None:
            return

        ic_card = class_utils.get_vhccshis(
            self, self.database, self.system_settings, qrcode
        )

        if not ic_card.insert_correct_ic_card(patient_key):
            return

        ic_card.rewrite_ic_prescript(case_key)

    def _clear_wait(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("清除候診名單")
        msg_box.setText(
            """
            <font size="5" color="red">
              <b>確定清除非今日的候診名單?<br>
            </font>
            """
        )
        msg_box.setInformativeText("只會清除昨天未看診完畢的候診名單.")
        msg_box.addButton(QPushButton("清除候診名單"), QMessageBox.YesRole)
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        cancel = msg_box.exec_()
        if cancel:
            return

        self._parent.reset_wait()
        self.read_wait()

    def rewrite_ic_card(self, ic_card_type=None):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("重新寫入健保卡")
        msg_box.setText(
            """
            <font size="5" color="red">
              <b>確定要將病歷重新寫入健保卡?<br>
            </font>
            """
        )
        msg_box.setInformativeText(
            "請注意! 重寫IC會產生新的卡序，若只要寫處方, 請選擇 [重寫醫令]."
        )
        msg_box.addButton(QPushButton("重新寫入"), QMessageBox.YesRole)
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        cancel = msg_box.exec_()
        if cancel:
            return

        wait_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["WaitKey"]
        )
        case_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["CaseKey"]
        )
        patient_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["PatientKey"]
        )

        card = self.table_widget_wait_completed.field_value(
            self.wait_done_column["Card"]
        )

        course = self._get_course(card)
        card = self._get_card(card)

        if not ic_card_type or ic_card_type is None:
            ic_card_type = case_utils.get_ic_card_type(self.database, case_key)

        if ic_card_type == "虛擬健保卡":
            qrcode = None
            vhc_req_code = vhc_utils.get_vhc_req_code_from_wait(self.database, wait_key)
            if vhc_req_code is not None:
                self._request_req_code(show_message=False)
                vhc_req_code = vhc_utils.get_vhc_req_code_from_wait(
                    self.database, wait_key
                )

                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("取得病患授權")
                msg_box.setText(
                    """
                    <font size="5" color="blue">
                    <b>請問病患是否已在健保快易通授權?<br>
                    </font>
                    """
                )
                msg_box.setInformativeText("取得虛擬健保卡授權")
                msg_box.addButton(QPushButton("尚未取得"), QMessageBox.NoRole)
                msg_box.addButton(QPushButton("病患已經授權"), QMessageBox.YesRole)
                get_response = msg_box.exec_()
                if not get_response:
                    return

                ic_card = class_utils.get_cshis(
                    self, self.database, self.system_settings
                )
                qrcode = ic_card.get_response_token(vhc_req_code)
                if qrcode is None:
                    system_utils.show_message_box(
                        QMessageBox.Critical,
                        "無法寫卡",
                        '<font size="5" color="red"><b>無法使用虛擬健保卡寫卡, 無法取得授權.</b></font>',
                        "請重新取得授權.",
                    )
                    return

            ic_card = class_utils.get_vhccshis(
                self, self.database, self.system_settings, qrcode
            )
        else:
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)

            if not ic_card.insert_correct_ic_card(patient_key):
                return

        share_type = self.table_widget_wait_completed.field_value(
            self.wait_done_column["ShareType"]
        )

        ic_card_ok = ic_card.write_ic_card(
            "掛號寫卡",
            patient_key,
            course,
            share_type,
            cshis_utils.NORMAL_CARD,
        )
        if not ic_card_ok:
            return

        self.update_cases_by_ic_card(ic_card, case_key, card, course)

        if self.system_settings.field("讀卡機控制軟體版本") == "cshis6":
            ic_card.write_ic_medical_record(
                case_key, cshis_utils.NORMAL_CARD, reset_vhc_card=False
            )
        else:
            ic_card.write_ic_medical_record(case_key, cshis_utils.NORMAL_CARD)

        self.update_wait_by_ic_card(ic_card, card, case_key)
        self._read_wait_completed()

    # 重新取得就醫識別碼
    def _rewrite_identifier(self, ic_card_type=None):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("重新取得就醫識別碼")
        msg_box.setText(
            """
            <font size="5" color="red">
              <b>確定要重新取得就醫識別碼?<br>
            </font>
            """
        )
        msg_box.setInformativeText("請注意! 這樣會產生新的就醫識別碼.")
        msg_box.addButton(QPushButton("重新取得"), QMessageBox.YesRole)
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        cancel = msg_box.exec_()
        if cancel:
            return

        case_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["CaseKey"]
        )

        if not ic_card_type or ic_card_type is None:
            ic_card_type = case_utils.get_ic_card_type(self.database, case_key)

        # security = case_utils.get_case_field_value(self.database, case_key, 'Security')                 # ic_card_time = case_utils.extract_security_xml(security, '寫卡時間')
        # ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        # identifier = ic_card.get_identifier(ic_card_time)

    def rewrite_vhc_card_by_qrcode(self, qrcode=None):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("重新寫入健保卡")
        msg_box.setText(
            """
            <font size="5" color="red">
              <b>確定要將病歷重新寫入健保卡?<br>
            </font>
            """
        )
        msg_box.setInformativeText(
            "請注意! 重寫IC會產生新的卡序，若只要寫處方, 請選擇 [重寫醫令]."
        )
        msg_box.addButton(QPushButton("重新寫入"), QMessageBox.YesRole)
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        cancel = msg_box.exec_()
        if cancel:
            return

        case_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["CaseKey"]
        )
        patient_key = self.table_widget_wait_completed.field_value(
            self.wait_done_column["PatientKey"]
        )
        share_type = self.table_widget_wait_completed.field_value(
            self.wait_done_column["ShareType"]
        )

        card = self._get_card(
            self.table_widget_wait_completed.field_value(self.wait_done_column["Card"])
        )
        course = number_utils.get_integer(
            self.table_widget_wait_completed.field_value(
                self.wait_done_column["Continuance"]
            )
        )

        if course == 0:
            course = None

        if qrcode is None:
            qrcode = system_utils.get_qrcode_from_file(self)
            if qrcode is None:
                return

        ic_card = class_utils.get_vhccshis(
            self, self.database, self.system_settings, qrcode
        )

        ic_card_ok = ic_card.write_ic_card(
            "掛號寫卡",
            patient_key,
            course,
            share_type,
            cshis_utils.NORMAL_CARD,
        )
        if not ic_card_ok:
            return

        self.update_cases_by_ic_card(ic_card, case_key, card, course)
        ic_card.write_ic_medical_record(case_key, cshis_utils.NORMAL_CARD)
        self.update_wait_by_ic_card(ic_card, card, case_key)
        self._read_wait_completed()

    def update_cases_by_ic_card(self, ic_card, case_key, card, course):
        if ic_card is None:
            return

        fields = [
            "Card",
            "Continuance",
            "Security",
        ]
        seq_number = string_utils.xstr(ic_card.treat_data["seq_number"])
        if seq_number == "":
            seq_number = card

        security = case_utils.treat_data_to_xml(ic_card.treat_data)

        treat_after_check = "1"  # 1:正常 2:補卡
        security = case_utils.update_xml_doc(
            security, "treat_after_check", treat_after_check
        )
        security = case_utils.update_xml_doc(security, "upload_type", "1")
        data = [seq_number, course, security]
        self.database.update_record("cases", fields, "CaseKey", case_key, data)

    def update_wait_by_ic_card(self, ic_card, card, case_key):
        if ic_card is None:
            return

        seq_number = ic_card.treat_data["seq_number"]
        if seq_number == "":
            seq_number = card

        sql = f'''
            UPDATE wait
            SET
                Card = "{seq_number}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

    def _open_med_vpn(self):
        web_utils.open_med_vpn(self.system_settings)

    def _open_med_vpn_vhc(self):
        web_utils.open_med_vpn(self.system_settings, vhc_ic_card=True)

    def _spin_box_reg_no_changed(self):
        patient_key = self.ui.lineEdit_patient_key.text()
        if patient_key == "":
            return

        reg_no = self.ui.spinBox_reg_no.value()
        start_date = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
        end_date = datetime.datetime.now().strftime("%Y-%m-%d 23:59:59")
        period = self.ui.comboBox_period.currentText()
        reg_type = self.ui.comboBox_reg_type.currentText()

        sql = f'''
            SELECT ReserveNo FROM reserve
            WHERE
                PatientKey = {patient_key} AND
                ReserveDate BETWEEN "{start_date}" AND "{end_date}" AND
                Period = "{period}" AND
                ReserveNo = {reg_no}
        '''
        rows = self.database.select_record(sql)

        if len(rows) > 0:
            reg_type = "預約門診"

        self.ui.comboBox_reg_type.setCurrentText(reg_type)

    def _read_vhc_image(self):
        qrcode = system_utils.get_qrcode_from_file(self)
        if qrcode in ["", None]:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "無法辨識QRCode",
                '<font size="5" color="red"><b>無法辨識載入的QRCode檔截圖, 無法執行健保卡掛號.</b></font>',
                "請將截圖檔剪裁為適當的大小.",
            )
            return

        self._registration_by_vhc_ic_card(qrcode)

    def _registration_by_vhc_ic_card(self, qrcode=None):
        self.vhc_ic_card = class_utils.get_vhccshis(
            self, self.database, self.system_settings, qrcode
        )
        if not self.vhc_ic_card.read_register_basic_data():
            self.vhc_ic_card = None
            system_utils.set_keyboard_layout("英文")
            return

        patient_id = self.vhc_ic_card.basic_data["patient_id"]
        sql = f'''
            SELECT * FROM patient
            WHERE
                ID = "{patient_id}"
        '''
        row = self.database.select_record(sql)
        if not row:  # 找不到資料
            if self._check_first_visit_reservation(self.vhc_ic_card):
                return

            self._select_new_patient(self.vhc_ic_card)
        else:
            self._get_patient(row[0]["ID"], self.vhc_ic_card)

        system_utils.set_keyboard_layout("英文")

    def _set_easy_mode(self):
        easy_mode = self.ui.checkBox_easy_mode.isChecked()

        hide_columns = [
            self.wait_done_column["Gender"],
            self.wait_done_column["ShareType"],
            self.wait_done_column["TreatType"],
            self.wait_done_column["PresDays"],
            self.wait_done_column["Visit"],
            self.wait_done_column["Card"],
            self.wait_done_column["Room"],
            self.wait_done_column["RegistNo"],
            self.wait_done_column["Doctor"],
            self.wait_done_column["DrugNo"],
        ]

        for col_no in hide_columns:
            if easy_mode:
                self.ui.tableWidget_wait_completed.hideColumn(col_no)
            else:
                self.ui.tableWidget_wait_completed.showColumn(col_no)

    def _set_massage_fee(self):
        remark = self.ui.comboBox_remark.currentText()
        massage_fee = charge_utils.get_remark_fee(self.database, remark)
        if massage_fee > 0:
            self.ui.lineEdit_traditional_health_care_fee.setText(
                string_utils.xstr(massage_fee)
            )

    def _open_past_history(self):
        patient_key = self.table_widget_wait.field_value(self.wait_column["PatientKey"])
        self.dialog_history.show_past_history(patient_key, None)

    def _init_smart_card(self):
        try:
            from smartcard.System import readers
        except ImportError:
            print("未找到 smartcard 套件，正在安裝...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyscard"])
            from smartcard.System import readers

        self.SelectAPDU = [
            0x00,
            0xA4,
            0x04,
            0x00,
            0x10,
            0xD1,
            0x58,
            0x00,
            0x00,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x11,
            0x00,
        ]
        self.ReadProfileAPDU = [0x00, 0xCA, 0x11, 0x00, 0x02, 0x00, 0x00]

        try:
            self.smart_card_reader = readers()[0]
        except Exception:
            self.smart_card_reader = None

    def _registration_by_smart_card(self):
        connection = self.smart_card_reader.createConnection()
        try:
            connection.connect()
        except Exception:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "無法辨識卡片",
                '<font size="5" color="red"><b>無法辨識健保卡, 請確認健保卡是否正確放置.</b></font>',
                "請確認卡片是否正確放置.",
            )
            return

        data, _, _ = connection.transmit(self.SelectAPDU)
        data, _, _ = connection.transmit(self.ReadProfileAPDU)

        card_number = "".join(chr(i) for i in data[0:12])

        try:
            name = bytes(data[12:32]).decode("big5").rstrip("\x00")
        except Exception:
            name = "".join(chr(i) for i in data[12:32])

        name = name.rstrip()

        uid = "".join(chr(i) for i in data[32:42])
        birthday = "".join(chr(i) for i in data[42:49])
        gender = "".join(chr(i) for i in data[49:50])
        gender = patient_utils.get_gender(gender)
        card_date = "".join(chr(i) for i in data[50:57])

        birthday = date_utils.nhi_date_to_west_date(birthday)
        card_date = date_utils.nhi_date_to_west_date(card_date)

        basic_data = {
            "patient_id": uid,
            "name": name,
            "birthday": birthday,
            "gender": gender,
            "card_date": card_date,
            "card_valid_date": card_date,
            "card_available_count": 6,
            "card_no": card_number,
            "cancel_mark": "正常卡",
            "insured_mark": "基層醫療",
            "emg_phone": None,
        }

        class ICCard:
            def __init__(self):
                self.basic_data = {}

            def set_basic_data(self, data):
                self.basic_data = data

            def set_patient_id(self, patient_id):
                self.basic_data["patient_id"] = patient_id

        ic_card = ICCard()
        ic_card.set_basic_data(basic_data)

        patient_id = ic_card.basic_data["patient_id"]
        sql = f'''
            SELECT * FROM patient
            WHERE
                ID = "{patient_id}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:  # 找不到資料
            if self._check_first_visit_reservation(ic_card):
                return

            self._select_new_patient(ic_card)
        else:
            row = rows[0]
            self._get_patient(row["ID"], ic_card)

    def ping_vpn(self, ip):
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", ip]
        try:
            output = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3
            )
            return output.returncode == 0
        except subprocess.TimeoutExpired:
            return False
