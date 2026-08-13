# -*- coding: UTF-8 -*-

import datetime
import json
import re

import sip
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (
    alleypin_utils,
    case_utils,
    charge_utils,
    class_utils,
    cshis_utils,
    date_utils,
    db_utils,
    dialog_utils,
    log_utils,
    module_utils,
    nhi_utils,
    notification_utils,
    number_utils,
    personnel_utils,
    prescript_utils,
    printer_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
    vhc_utils,
    web_utils,
)


# 病歷資料 2026-07-18
class MedicalRecord(QtWidgets.QMainWindow):
    program_name = "醫師看診作業"

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.call_from = args[3]
        try:
            self.patient_key = args[4]
        except Exception:
            self.patient_key = None

        if self.call_from == "參考病歷":
            self.patient_key = 0

        self.append_new_case_key = self.case_key

        self.medical_record = None
        self.patient_record = None
        self.ins_type = None
        self.record_saved = False
        self.first_record = None
        self.last_record = None
        self.input_code = ""

        self.ui = None
        self._deleted = False
        self.user_name = system_utils.get_user_name(self.system_settings)
        self._init_tab()
        self.close_tab_warning = True
        self.socket_client = class_utils.get_socket_client()
        self.notification_client = notification_utils.NotificationClient(
            self,
            database=self.database,
            station=self.program_name,
        )
        self.wait_key = self._get_wait_key()

        if not self._read_data():
            return

        self._set_ui()
        self._set_signal()

        if self.system_settings.field("輸入主訴資料自動補全") == "Y":
            self.dict_autocomplete_symptom = class_utils.get_dict_autocomplete(
                self.ui.textEdit_symptom, self.database, "主訴"
            )
            self.dict_autocomplete_tongue = class_utils.get_dict_autocomplete(
                self.ui.textEdit_tongue, self.database, "舌診"
            )
            self.dict_autocomplete_pulse = class_utils.get_dict_autocomplete(
                self.ui.textEdit_pulse, self.database, "脈象"
            )
            self.dict_autocomplete_remark = class_utils.get_dict_autocomplete(
                self.ui.textEdit_remark, self.database, "備註"
            )

        self._set_data()
        self._set_prescript_tab_cornor_widget()

        try:
            self.is_closed = bool(self.medical_record["IsClosed"])
        except Exception:
            self.is_closed = False

        if self.call_from == "醫師看診作業":
            self._set_in_progress("Y")
            self._prompt_hint()

        if self.case_key is None:
            return

        self._set_permission()
        self._set_extra_tab()
        self._set_background_color()

        if self.system_settings.field("病歷主訴大字體") == "Y":
            self._set_symptom_large_font()
            self._set_patient_large_font()

        self.refresh_wait()
        self._check_infectious_date()
        self._set_tab_cornor_widget()
        self._read_case_extend()
        self._set_broadcast_voice()
        self.dialog_patient_memo = dialog_utils.get_dialog_patient_memo(
            self, self.database, self.system_settings, self.patient_key
        )
        self._set_case_closed()

    # def _set_case_closed(self):
    #     if self.medical_record is None:
    #         return

    #     if not self.is_closed:
    #         return

    #     for widget in self.findChildren(
    #         (
    #             QtWidgets.QLineEdit,
    #             QtWidgets.QTextEdit,
    #         )
    #     ):
    #         widget.setReadOnly(self.is_closed)

    #     for widget in self.findChildren((QtWidgets.QTableWidget,)):
    #         widget.horizontalHeader().setSectionsMovable(False)
    #         widget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    #         widget.setAcceptDrops(False)
    #         widget.setDragEnabled(False)
    #         widget.blockSignals(True)

    #     # 2. 處理選擇控制項 (ComboBox 沒有 setReadOnly，通常用 setEnabled)
    #     for widget in self.findChildren(
    #         (
    #             QtWidgets.QComboBox,
    #             QtWidgets.QCheckBox,
    #             QtWidgets.QAction,
    #             QtWidgets.QToolButton,
    #             QtWidgets.QRadioButton,
    #             QtWidgets.QPushButton,
    #             QtWidgets.QSpinBox,
    #         )
    #     ):
    #         widget.setEnabled(not self.is_closed)

    #     self.ui.action_save.triggered.connect(self.save_medical_record)
    #     self.ui.action_save_and_pdf.triggered.connect(self.save_medical_record)
    #     self.ui.action_force_save.triggered.connect(
    #         lambda: self.save_medical_record(force_save=True)
    #     )

    #     self.ui.action_save_and_print.triggered.connect(self.save_medical_record)
    #     self.ui.action_save_and_print_prescript.triggered.connect(
    #         self.save_medical_record
    #     )
    #     self.ui.action_save_and_print_receipt.triggered.connect(
    #         self.save_medical_record
    #     )
    #     self.ui.action_save_and_print_misc.triggered.connect(self.save_medical_record)

    #     for action in self.findChildren(QtWidgets.QAction):
    #         if action in [
    #             self.ui.action_close,
    #             self.ui.action_save,
    #             self.ui.action_save_and_pdf,
    #             self.ui.action_force_save,
    #             self.ui.action_save_and_print,
    #             self.ui.action_save_and_print_prescript,
    #             self.ui.action_save_and_print_receipt,
    #             self.ui.action_save_and_print_misc,
    #         ]:
    #             action.setEnabled(True)
    #             continue

    #         action.setEnabled(not self.is_closed)

    #     exception_widgets = [
    #         self.ui.textEdit_symptom,
    #         self.ui.textEdit_tongue,
    #         self.ui.textEdit_pulse,
    #         self.ui.textEdit_remark,
    #     ]
    #     for widget in exception_widgets:
    #         widget.setEnabled(self.is_closed)
    #         widget.setReadOnly(not self.is_closed)
    def _set_case_closed(self):
        if self.medical_record is None:
            return

        if not self.is_closed:
            return

        # 1. 文字輸入控制項設為唯讀
        for widget in self.findChildren(
            (
                QtWidgets.QLineEdit,
                QtWidgets.QTextEdit,
            )
        ):
            widget.setReadOnly(True)

        # 2. 表格控制項禁止編輯與拖曳
        for widget in self.findChildren((QtWidgets.QTableWidget,)):
            widget.horizontalHeader().setSectionsMovable(False)
            widget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            widget.setAcceptDrops(False)
            widget.setDragEnabled(False)
            widget.blockSignals(True)

        # 3. 選擇控制項 (ComboBox 沒有 setReadOnly，改用 setEnabled)
        for widget in self.findChildren(
            (
                QtWidgets.QComboBox,
                QtWidgets.QCheckBox,
                QtWidgets.QToolButton,
                QtWidgets.QRadioButton,
                QtWidgets.QPushButton,
                QtWidgets.QSpinBox,
            )
        ):
            widget.setEnabled(False)

        # 4. Action: 除了存檔與關閉相關的以外全部停用
        #    (這些 action 在 _set_signal 已連接過, 這裡絕對不可再 connect,
        #     否則存檔會被執行兩次)
        allowed_actions = [
            self.ui.action_close,
            self.ui.action_save,
            self.ui.action_save_and_pdf,
            self.ui.action_force_save,
            self.ui.action_save_and_print,
            self.ui.action_save_and_print_prescript,
            self.ui.action_save_and_print_receipt,
            self.ui.action_save_and_print_misc,
        ]
        for action in self.findChildren(QtWidgets.QAction):
            action.setEnabled(action in allowed_actions)

        # 5. 望聞問切: 保持可捲動/選取/複製, 但不可編輯
        exception_widgets = [
            self.ui.textEdit_symptom,
            self.ui.textEdit_tongue,
            self.ui.textEdit_pulse,
            self.ui.textEdit_remark,
        ]
        for widget in exception_widgets:
            widget.setEnabled(True)
            widget.setReadOnly(True)

    def _read_case_extend(self):
        if (
            case_utils.get_case_extend(self.database, self.case_key, "整合醫療照護")
            == "Y"
        ):
            try:
                self.check_box_integrate_care.setChecked(True)
                self.check_box_integrate_care.setEnabled(True)
                self.check_box_integrate_care.setStyleSheet(
                    "color: red; font-weight: bold"
                )
            except Exception:
                pass

        if (
            case_utils.get_case_extend(self.database, self.case_key, "不申報慢性病")
            == "Y"
        ):
            try:
                self.check_box_chronic_code.setChecked(True)
                self.check_box_chronic_code.setStyleSheet(
                    "color: darkGreen; font-weight: bold"
                )
            except Exception:
                pass

    def _prompt_birth_date(self):
        birth_date = self.patient_record["Birthday"]
        if date_utils.is_birthday_today(birth_date):
            name = self.patient_record["Name"]
            age, _ = date_utils.get_age(birth_date)
            system_utils.show_message_box(
                QMessageBox.Information,
                "恭喜生日快樂",
                f'<font size="5" color="deepPink"><b>{name}今天{age}歲生日, 請獻上生日的祝福吧！.</b></font>',
                f"{name}的出生日期是{birth_date.year}年{birth_date.month}月{birth_date.day}日",
            )

    def _prompt_hint(self):
        self._prompt_injury()
        self._prompt_allergy()
        self._prompt_ckd()

        try:
            self._prompt_birth_date()
        except Exception:
            pass

    def _prompt_injury(self):
        if self.medical_record["Injury"] == "主訴職災":
            return

        sql = """
            SELECT Injury FROM cases
            WHERE
                CaseKey != %s AND PatientKey = %s AND InsType = "健保"
            ORDER BY CaseDate DESC LIMIT 1
        """
        rows = self.database.select_record(sql, (self.case_key, self.patient_key))

        if len(rows) <= 0:
            return

        row = rows[0]
        if string_utils.xstr(row["Injury"]) != "主訴職災":
            return

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("提示")
        msg_box.setText(
            "<font size='5' color='blue'><b>上次門診為主訴職災，請問是否繼續?</b></font>"
        )
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("繼續"), QMessageBox.YesRole)
        continue_injury = msg_box.exec_()
        if not continue_injury:
            return

        self.ui.checkBox_complaint_injury.blockSignals(True)
        self.ui.checkBox_complaint_injury.setChecked(True)
        self.ui.checkBox_complaint_injury.blockSignals(False)
        self.tab_registration.ui.comboBox_injury_type.setCurrentText("主訴職災")
        self.ui.checkBox_complaint_injury.setStyleSheet("color: red; font-weight: bold")

    def _prompt_allergy(self):
        allergy = string_utils.get_str(
            self.patient_record["Allergy"], encoding="utf-8"
        ).strip()
        if allergy in [None, "", "無"]:
            return

        system_utils.show_message_box(
            QMessageBox.Critical,
            "過敏提醒",
            f"""
                <font size="5" color="red"><b>
                    注意! 此病人有過敏史， 過敏內容為: <br>
                    {allergy}
                </b></font>
            """,
            "請注意病患過敏的用藥",
        )

    def _prompt_ckd(self):
        treat_type = self.tab_registration.ui.comboBox_treat_type.currentText()
        if treat_type not in ["慢性腎病照護"]:
            return

        sql = """
            SELECT PrescriptKey FROM prescript
                LEFT JOIN cases ON cases.CaseKey = prescript.CaseKey
            WHERE
                InsCode BETWEEN "P64001" AND "P64010" AND
                cases.PatientKey = %s
        """
        params = (self.patient_key,)
        rows = self.database.select_record(sql, params)
        if len(rows) < 2:  # 至少看過兩次ckd照護
            return

        sql = """
            SELECT PrescriptKey FROM prescript
                LEFT JOIN cases ON cases.CaseKey = prescript.CaseKey
            WHERE
                InsCode = "P64011" AND
                cases.PatientKey = %s
        """
        params = (self.patient_key,)
        rows = self.database.select_record(sql, params)
        if len(rows) <= 0:  # 沒做過P64011
            return

        case_date = self.medical_record["CaseDate"].date()
        sql = """
            SELECT cases.CaseDate FROM prescript
                LEFT JOIN cases on cases.CaseKey = prescript.CaseKey
            WHERE
                prescript.CaseKey != %s AND
                DATE(prescript.CaseDate) <= %s AND
                cases.PatientKey = %s AND
                InsCode = "P64012"
            ORDER BY cases.CaseDate DESC LIMIT 1
        """
        params = (self.case_key, case_date.strftime("%Y-%m-%d"), self.patient_key)
        rows = self.database.select_record(sql, params)

        if len(rows) > 0:
            last_case_date = rows[0]["CaseDate"].date()
            delta = case_date - last_case_date
            if delta.days <= 180:  # 六個月內有申報過，本次不能申報
                return

        system_utils.show_message_box(
            QMessageBox.Information,
            "慢性腎病照護提醒",
            """
                <font size="5" color="blue"><b>
                    注意! 此病人符合申報CKD治療功能性評估(P64012)資格<br>
                </b></font>
            """,
            "僅提醒符合資格，是否申報請依當時情況評估",
        )

    def _set_symptom_large_font(self):
        style_sheet = self.ui.textEdit_symptom.styleSheet()
        style_sheet += "; font-size: 24px;"

        self.ui.textEdit_symptom.setStyleSheet(style_sheet)
        self.ui.textEdit_tongue.setStyleSheet(style_sheet)
        self.ui.textEdit_pulse.setStyleSheet(style_sheet)
        self.ui.textEdit_remark.setStyleSheet(style_sheet)
        self.ui.textEdit_patient_remark.setStyleSheet(style_sheet)

        style_sheet = self.ui.lineEdit_disease_code1.styleSheet()
        style_sheet += "; font-size: 24px;"
        self.ui.lineEdit_disease_code1.setStyleSheet(style_sheet)
        self.ui.lineEdit_disease_name1.setStyleSheet(style_sheet)
        # self.ui.lineEdit_disease_code2.setStyleSheet(style_sheet)
        # self.ui.lineEdit_disease_name2.setStyleSheet(style_sheet)
        # self.ui.lineEdit_disease_code3.setStyleSheet(style_sheet)
        # self.ui.lineEdit_disease_name3.setStyleSheet(style_sheet)

    def _set_patient_large_font(self):
        self.ui.label_case_date.setStyleSheet(
            self.ui.label_case_date.styleSheet() + "; font-size: 24px;"
        )
        self.ui.label_ins_type.setStyleSheet(
            self.ui.label_ins_type.styleSheet() + "; font-size: 24px;"
        )
        self.ui.label_patient_name.setStyleSheet(
            self.ui.label_patient_name.styleSheet() + "; font-size: 24px;"
        )
        self.ui.label_regist_no.setStyleSheet(
            self.ui.label_regist_no.styleSheet() + "; font-size: 24px;"
        )
        self.ui.label_share_type.setStyleSheet(
            self.ui.label_share_type.styleSheet() + "; font-size: 24px;"
        )
        self.ui.label_card.setStyleSheet(
            self.ui.label_card.styleSheet() + "; font-size: 24px;"
        )

    def _init_tab(self):
        self.tab_ins_prescript = None
        self.tab_self_prescript1 = None
        self.tab_self_prescript2 = None
        self.tab_self_prescript3 = None
        self.tab_self_prescript4 = None
        self.tab_self_prescript5 = None
        self.tab_self_prescript6 = None
        self.tab_self_prescript7 = None
        self.tab_self_prescript8 = None
        self.tab_self_prescript9 = None
        self.tab_ins_care = None
        self.tab_list = [
            self.tab_ins_prescript,
            self.tab_self_prescript1,
            self.tab_self_prescript2,
            self.tab_self_prescript3,
            self.tab_self_prescript4,
            self.tab_self_prescript5,
            self.tab_self_prescript6,
            self.tab_self_prescript7,
            self.tab_self_prescript8,
            self.tab_self_prescript9,
            self.tab_ins_care,
        ]
        self.max_tab = len(self.tab_list)

    # 解構
    def __del__(self):
        try:
            self.dialog_patient_memo.close()
        except Exception:
            pass

        self.close_all()

    # 關閉
    def close_all(self):
        if self._deleted:
            return

        self._deleted = True
        if self.call_from in ["醫師看診作業", "離開不存檔"]:
            self._set_in_progress(None)

        if self.system_settings.field("不要自動切換輸入法") == "Y":
            pass
        else:
            system_utils.set_keyboard_layout("中文")

    # 設定GUI
    def _set_ui(self):
        ui_file = ui_utils.get_medical_record_ui_file(self.system_settings)
        self.ui = ui_utils.load_ui_file(ui_file, self)

        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        self.add_tab_button = QtWidgets.QToolButton()
        self.add_tab_button.setIcon(QtGui.QIcon("./icons/document-new.svg"))
        self.add_tab_button.clicked.connect(self.add_prescript_tab)

        self._set_tongue()
        self._set_pulse()

        if (
            self.system_settings.field("健保自費分開") == "Y"
            or self.call_from == "病歷查詢健保病歷"
        ):
            pass
        else:
            self.ui.tabWidget_prescript.setCornerWidget(
                self.add_tab_button, QtCore.Qt.TopLeftCorner
            )

        try:
            if self.system_settings.field("顯示次診斷3") == "Y":
                self._show_disease4(True)
            else:
                self._show_disease4(False)
        except Exception:
            pass

        self.ui.toolButton_add_symptom_dict.setEnabled(False)
        if self.case_key is None:
            self.tab_registration = None
            self.tab_order = None
            self.tab_family = None
            self.tab_examination = None
            self.tab_image = None
            # self._set_toolbar(False)
            return

        self.tab_registration = module_utils.get_medical_record_registration(
            self, self.database, self.system_settings, self.case_key, self.call_from
        )
        self.ui.tabWidget_medical.addTab(self.tab_registration, "門診資料")
        self.tab_registration.set_special_code()

        self.medical_record["DiagDate"] = (
            self.tab_registration.ui.lineEdit_diag_start_time.text()
        )
        if self.medical_record["DiagDate"] == "":
            self.medical_record["DiagDate"] = self.medical_record["CaseDate"]
        else:
            self.medical_record["DiagDate"] = date_utils.str_to_datetime(
                self.medical_record["DiagDate"]
            )

        self.tab_order = module_utils.get_medical_record_order(
            self, self.database, self.system_settings, self.case_key, self.call_from
        )
        self.ui.tabWidget_medical.addTab(self.tab_order, "醫囑")
        if self.tab_order.get_order_count() > 0:
            self.ui.tabWidget_medical.setTabIcon(
                self.ui.tabWidget_medical.indexOf(self.tab_order), ui_utils.ICON_STAR
            )

        # self.disease_code_changed()
        self.rearrange_disease_codes()

        self._set_hosts()

        if self.patient_key is None:
            self.ui.action_patient.setEnabled(False)
            self.ui.action_past_history.setEnabled(False)
            self.ui.action_open_hosts.setEnabled(False)
            self.ui.action_append_self_medical_record.setEnabled(False)
            return

        if (
            self.call_from not in ["病歷查詢健保病歷"]
            and self.system_settings.field("顯示家族病歷") == "Y"
        ):
            self.tab_family = module_utils.get_medical_record_family(
                self, self.database, self.system_settings, self.case_key, self.call_from
            )
            self.ui.tabWidget_medical.addTab(self.tab_family, "家族病歷")

        self.tab_examination = module_utils.get_medical_record_examination(
            self, self.database, self.system_settings, self.patient_key, self.call_from
        )
        self.ui.tabWidget_medical.addTab(self.tab_examination, "檢驗報告")

        self.tab_image = module_utils.get_medical_record_image(
            self, self.database, self.system_settings, self.case_key, self.patient_key
        )
        self.ui.tabWidget_medical.addTab(self.tab_image, "病歷影像")
        if self.tab_image.get_image_count() > 0:
            self.ui.tabWidget_medical.setTabIcon(
                self.ui.tabWidget_medical.indexOf(self.tab_image), ui_utils.ICON_STAR
            )

        self._set_event_filter()

        doctor = self.medical_record["Doctor"]
        if doctor is not None:
            self.ui.groupBox_diagnostic.setTitle(f"診斷  (主治醫師: {doctor})")

        if (
            self.call_from == "醫師看診作業"
            and personnel_utils.get_permission(
                self.database,
                "醫師看診作業",
                "候診病歷非主治醫師不可存檔",
                self.user_name,
            )
            == "Y"
            and self.user_name != doctor
        ):
            self.ui.action_save.setEnabled(False)
            self.ui.action_force_save.setEnabled(False)
            self.ui.action_save_and_print.setEnabled(False)
            self.ui.action_save_and_print_prescript.setEnabled(False)
            self.ui.action_save_and_print_receipt.setEnabled(False)
            self.ui.action_save_and_print_misc.setEnabled(False)

        if self.system_settings.field("病歷資料不顯示病患備註") == "Y":
            self.ui.label_patient_remark.setVisible(False)
            self.ui.textEdit_patient_remark.setVisible(False)
            self.ui.textEdit_remark.setMaximumHeight(160)
        # self.ui.groupBox_patient.setVisible(False)
        # self.ui.action_conflict_drug.setVisible(False)  # 2026-01-01 關閉中西藥交互(web 1.0)

    def _set_tongue(self):
        max_tongue = 5
        default_tongue_list = ["舌淡紅", "苔薄白", "苔薄黃", "有齒痕"]
        custum_tongue_list = []

        for i in range(1, max_tongue + 1):
            tongue = self.system_settings.field(f"舌診{i}")
            if tongue not in ["", None]:
                custum_tongue_list.append(tongue)

        if len(custum_tongue_list) > 0:
            tongue_list = custum_tongue_list
        else:
            tongue_list = default_tongue_list

        for tongue in tongue_list:
            button = QtWidgets.QToolButton()
            button.setText(tongue)
            button.clicked.connect(lambda: self._tongue_button_click(button))
            self.ui.horizontalLayout_tongue.addWidget(button)

        spacer = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.ui.horizontalLayout_tongue.addItem(spacer)

    def _tongue_button_click(self, sender):
        tongue = self.sender().text()
        self.insert_text(self.ui.textEdit_tongue, tongue, "", insert_comma=True)

    def _set_pulse(self):
        max_pulse = 10
        default_pulse_list = [
            "左",
            "右",
            "浮",
            "沉",
            "滑",
            "弦",
            "細",
            "濡",
            "遲",
            "數",
        ]
        custum_pulse_list = []

        for i in range(1, max_pulse + 1):
            pulse = self.system_settings.field(f"脈象{i}")
            if pulse not in ["", None]:
                custum_pulse_list.append(pulse)

        if len(custum_pulse_list) > 0:
            pulse_list = custum_pulse_list
        else:
            pulse_list = default_pulse_list

        # pulse_list.append(', ')
        for pulse in pulse_list:
            button = QtWidgets.QToolButton()
            button.setText(pulse)
            button.clicked.connect(lambda: self._pulse_button_click(button))
            self.ui.horizontalLayout_pulse.addWidget(button)

        spacer = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.ui.horizontalLayout_pulse.addItem(spacer)

    def _pulse_button_click(self, sender):
        pulse = self.sender().text()
        if pulse in ["左", "右"]:
            pulse += "脈:"

        if pulse in ["左脈:", "右脈:"] and self.ui.textEdit_pulse.toPlainText() != "":
            self.insert_text(self.ui.textEdit_pulse, pulse, "", insert_comma=True)
        else:
            self.insert_text(self.ui.textEdit_pulse, pulse, "", insert_comma=False)

    def _show_memo(self):
        sql = f"""
            SELECT * FROM case_extension
            WHERE
                CaseKey = {self.case_key} AND
                ExtensionType = "Memo"
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self._set_memo_button()
            return

    def _set_memo_button(self):
        self.add_extra_memo_button = QtWidgets.QPushButton()
        self.add_extra_memo_button.setIcon(QtGui.QIcon("./icons/document-new.svg"))
        self.add_extra_memo_button.setText("Memo")
        self.add_extra_memo_button.setFlat(True)
        self.ui.tabWidget_past_record.setCornerWidget(
            self.add_extra_memo_button, QtCore.Qt.TopRightCorner
        )

    def _show_disease4(self, visible):
        self.ui.pushButton_disease4.setVisible(visible)
        self.ui.lineEdit_disease_code4.setVisible(visible)
        self.ui.lineEdit_disease_name4.setVisible(visible)
        self.ui.toolButton_disease4.setVisible(visible)

    def _set_toolbar(self, enabled):
        action_list = [
            self.ui.action_past_history,
            self.ui.action_patient,
            self.ui.action_med_vpn,
            self.ui.action_conflict_drug,
            self.ui.action_capture_image,
            self.ui.action_exam_result,
            self.ui.action_reservation,
            self.ui.action_append_self_medical_record,
            self.ui.action_save_and_print,
        ]

        for action in action_list:
            action.setEnabled(enabled)

    def _set_background_color(self):
        if self.tab_registration.comboBox_ins_type.currentText() == "自費":
            background_color = ui_utils.GRADIENT_COLOR
        elif (
            self.tab_registration.comboBox_reg_type.currentText()
            in nhi_utils.TELECOM_TYPE
        ):
            background_color = ui_utils.VIDEO_DIAG_COLOR
        elif (
            self.tab_registration.comboBox_share_type.currentText()
            in nhi_utils.INFECTIOUS_TYPE
            and self.tab_registration.comboBox_injury_type.currentText()
            in nhi_utils.INFECTIOUS_TYPE
        ):
            background_color = ui_utils.INFECTIOUS_DIAG_COLOR
        else:
            return

        self.ui.textEdit_symptom.setStyleSheet(background_color)
        self.ui.textEdit_tongue.setStyleSheet(background_color)
        self.ui.textEdit_pulse.setStyleSheet(background_color)
        self.ui.textEdit_remark.setStyleSheet(background_color)
        self.ui.lineEdit_disease_code1.setStyleSheet(background_color)
        self.ui.lineEdit_disease_name1.setStyleSheet(background_color)
        self.ui.lineEdit_disease_code2.setStyleSheet(background_color)
        self.ui.lineEdit_disease_name2.setStyleSheet(background_color)
        self.ui.lineEdit_disease_code3.setStyleSheet(background_color)
        self.ui.lineEdit_disease_name3.setStyleSheet(background_color)
        self.ui.lineEdit_disease_code4.setStyleSheet(background_color)
        self.ui.lineEdit_disease_name4.setStyleSheet(background_color)
        self.ui.lineEdit_distinguish.setStyleSheet(background_color)
        self.ui.lineEdit_cure.setStyleSheet(background_color)

        # self.ui.groupBox_patient.setStyleSheet(background_color)

        # try:
        #     self.tab_medical_record_recently_history.textEdit_past.setStyleSheet(background_color)
        # except AttributeError:
        #     pass

        # try:
        #     self.tab_medical_record_fees.tableWidget_ins_fees.setStyleSheet(background_color)
        # except AttributeError:
        #     pass

        # try:
        #     self.tab_medical_record_fees.tableWidget_cash_fees.setStyleSheet(background_color)
        # except AttributeError:
        #     pass

        # for tab_index in range(self.ui.tabWidget_prescript.count()):
        #     tab = self.ui.tabWidget_prescript.widget(tab_index)
        #     tab.tableWidget_prescript.setStyleSheet(background_color)

    def _set_event_filter(self):
        self.ui.textEdit_symptom.installEventFilter(self)
        self.ui.textEdit_tongue.installEventFilter(self)
        self.ui.textEdit_pulse.installEventFilter(self)
        self.ui.textEdit_remark.installEventFilter(self)
        self.ui.lineEdit_disease_code1.installEventFilter(self)
        self.ui.lineEdit_disease_code2.installEventFilter(self)
        self.ui.lineEdit_disease_code3.installEventFilter(self)
        self.ui.lineEdit_disease_code4.installEventFilter(self)
        self.ui.lineEdit_distinguish.installEventFilter(self)
        self.ui.lineEdit_cure.installEventFilter(self)

    def eventFilter(self, source, event):
        obj_name = source.objectName()

        if obj_name in [
            "textEdit_symptom",
            "textEdit_tongue",
            "textEdit_pulse",
            "textEdit_remark",
            "lineEdit_distinguish",
            "lineEdit_cure",
        ]:
            if event.type() == QtCore.QEvent.FocusIn:
                if self.system_settings.field("不要自動切換輸入法") == "Y":
                    pass
                elif self.system_settings.field("望聞問切輸入法預設英數") == "Y":
                    system_utils.set_keyboard_layout("英文")
                else:
                    system_utils.set_keyboard_layout("中文")
            elif event.type() == QtCore.QEvent.FocusOut:
                if not self.is_doctor_done():  # 病歷登錄要自動存檔
                    self.update_diagnosis_data()

        elif obj_name in [
            "lineEdit_disease_code1",
            "lineEdit_disease_code2",
            "lineEdit_disease_code3",
            "lineEdit_disease_code4",
        ]:
            if event.type() == QtCore.QEvent.FocusIn:
                if self.system_settings.field("不要自動切換輸入法") == "Y":
                    pass
                elif self.system_settings.field("診斷碼輸入法預設中文") == "Y":
                    system_utils.set_keyboard_layout("中文")
                else:
                    system_utils.set_keyboard_layout("英文")
            elif event.type() == QtCore.QEvent.FocusOut:
                if not self.is_doctor_done():  # 病歷登錄要自動存檔
                    self.update_diagnosis_data()

        return False

    def _set_hosts(self):
        sql = """
            SELECT * FROM hosts
            ORDER BY HostsKey
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self.ui.action_open_hosts.setVisible(False)

    def _open_medical_record_hosts(self):
        patient_id = string_utils.xstr(self.patient_record["ID"])
        if patient_id == "":
            system_utils.show_message_box(
                QMessageBox.Critical,
                "無法查詢",
                '<font size="5" color="red"><b>注意! 此病人無身份證號，無法查詢.</b></font>',
                "請確認病患資料有身份證號",
            )
            return

        dialog = dialog_utils.get_dialog_medical_record_hosts(
            self,
            self.database,
            self.system_settings,
            patient_id,
        )
        dialog.exec_()
        dialog.deleteLater()

    # 處方集
    def _open_medical_record_collection(self):
        dialog = dialog_utils.get_dialog_medical_record_collection(
            self,
            self.database,
            self.system_settings,
            self.medical_record["CaseDate"],
        )
        dialog.exec_()
        dialog.deleteLater()

    def _get_current_medicine_set(self):
        medicine_set = None

        tab_index = self.ui.tabWidget_prescript.currentIndex()
        current_tab_text = self.ui.tabWidget_prescript.tabText(tab_index)

        if current_tab_text == "健保":
            medicine_set = 1
        elif current_tab_text == "加強照護":
            medicine_set = 11
        elif "自費" in current_tab_text:
            medicine_set = (
                number_utils.get_integer(current_tab_text.split("自費")[1]) + 1
            )

        return medicine_set

    # 經驗方
    def _open_medical_record_experience(self):
        medicine_set = self._get_current_medicine_set()

        dialog = dialog_utils.get_dialog_medical_record_experience(
            self,
            self.database,
            self.system_settings,
            self.medical_record["CaseDate"],
            medicine_set,
        )
        dialog.exec_()
        dialog.deleteLater()

    # 設定信號
    def _set_signal(self):
        self.ui.action_past_history.triggered.connect(self._open_past_history)
        self.ui.action_save.triggered.connect(self.save_medical_record)
        self.ui.action_save_and_pdf.triggered.connect(self.save_medical_record)
        self.ui.action_force_save.triggered.connect(
            lambda: self.save_medical_record(force_save=True)
        )

        self.ui.action_save_and_print.triggered.connect(self.save_medical_record)
        self.ui.action_save_and_print_prescript.triggered.connect(
            self.save_medical_record
        )
        self.ui.action_save_and_print_receipt.triggered.connect(
            self.save_medical_record
        )
        self.ui.action_save_and_print_misc.triggered.connect(self.save_medical_record)

        self.ui.action_exam_precheck.triggered.connect(self._exam_precheck)
        self.ui.action_conflict_drug.triggered.connect(self._conflict_drug)

        self.ui.action_reference_prescript.triggered.connect(
            self._open_reference_prescript
        )

        self.ui.action_dictionary.triggered.connect(self.open_dictionary)
        self.ui.action_reference.triggered.connect(self._open_medical_record_reference)
        self.ui.action_close.triggered.connect(self.close_medical_record)
        self.ui.action_close_without_saving.triggered.connect(
            lambda: self.close_medical_record(close_without_saving=True)
        )
        self.ui.action_patient.triggered.connect(self.modify_patient)
        self.ui.action_capture_image.triggered.connect(self.capture_image)
        self.ui.action_append_self_medical_record.triggered.connect(
            self._append_new_self_medical_record
        )
        self.ui.action_open_hosts.triggered.connect(self._open_medical_record_hosts)
        self.ui.action_medical_record_collection.triggered.connect(
            self._open_medical_record_collection
        )
        self.ui.action_medical_record_experience.triggered.connect(
            self._open_medical_record_experience
        )
        self.ui.action_reservation.triggered.connect(self._open_reservation)
        self.ui.action_exam_result.triggered.connect(self._open_exam_result)
        self.ui.action_med_vpn.triggered.connect(self._open_med_vpn)
        self.ui.action_medical_record_version_history.triggered.connect(
            self._medical_record_version_history
        )
        self.ui.action_medicine_to_herb.triggered.connect(self._medicine_to_herb)
        self.ui.action_broadcast_voice.triggered.connect(self._send_voice_data)

        self.ui.toolButton_blood_measure.clicked.connect(
            self._tool_button_blood_measure_clicked
        )
        self.ui.toolButton_symptom.clicked.connect(self._tool_button_dictionary_clicked)
        self.ui.toolButton_symptom_kt.clicked.connect(
            self._tool_button_dictionary_clicked
        )
        self.ui.toolButton_tongue.clicked.connect(self._tool_button_dictionary_clicked)
        self.ui.toolButton_pulse.clicked.connect(self._tool_button_dictionary_clicked)
        self.ui.toolButton_remark.clicked.connect(self._tool_button_dictionary_clicked)
        self.ui.toolButton_today.clicked.connect(self._insert_today)
        self.ui.toolButton_calendar.clicked.connect(self._insert_calendar)
        self.ui.toolButton_add_symptom_dict.clicked.connect(self._add_symptom_dict)
        self.ui.textEdit_symptom.selectionChanged.connect(
            self._symptom_selection_changed
        )

        self.ui.toolButton_symptom_picker.clicked.connect(
            self._tool_button_picker_clicked
        )
        self.ui.toolButton_tongue_picker.clicked.connect(
            self._tool_button_picker_clicked
        )
        # self.ui.toolButton_pulse_picker.clicked.connect(self._tool_button_picker_clicked)

        self.ui.toolButton_disease1.clicked.connect(
            self._tool_button_dictionary_clicked
        )
        self.ui.toolButton_disease2.clicked.connect(
            self._tool_button_dictionary_clicked
        )
        self.ui.toolButton_disease3.clicked.connect(
            self._tool_button_dictionary_clicked
        )
        self.ui.toolButton_disease4.clicked.connect(
            self._tool_button_dictionary_clicked
        )
        self.ui.toolButton_distincts.clicked.connect(
            self._tool_button_dictionary_clicked
        )
        self.ui.toolButton_cure.clicked.connect(self._tool_button_dictionary_clicked)

        self.ui.pushButton_symptom.clicked.connect(self._tool_button_dictionary_clicked)
        self.ui.pushButton_tongue.clicked.connect(self._tool_button_dictionary_clicked)
        self.ui.pushButton_pulse.clicked.connect(self._tool_button_dictionary_clicked)
        self.ui.pushButton_remark.clicked.connect(self._tool_button_dictionary_clicked)
        self.ui.pushButton_disease1.clicked.connect(
            self._tool_button_dictionary_clicked
        )
        self.ui.pushButton_disease2.clicked.connect(
            self._tool_button_dictionary_clicked
        )
        self.ui.pushButton_disease3.clicked.connect(
            self._tool_button_dictionary_clicked
        )
        self.ui.pushButton_disease4.clicked.connect(
            self._tool_button_dictionary_clicked
        )
        self.ui.pushButton_distincts.clicked.connect(
            self._tool_button_dictionary_clicked
        )
        self.ui.pushButton_cure.clicked.connect(self._tool_button_dictionary_clicked)

        self.ui.tabWidget_prescript.tabCloseRequested.connect(
            self.close_prescript_tab
        )  # 關閉分頁
        self.ui.tabWidget_prescript.tabBar().tabMoved.connect(self._tab_moved)
        self.ui.tabWidget_prescript.currentChanged.connect(
            self._tab_changed
        )  # 切換分頁

        self.ui.textEdit_symptom.keyPressEvent = self._text_edit_key_press
        self.ui.textEdit_tongue.keyPressEvent = self._text_edit_key_press
        self.ui.textEdit_pulse.keyPressEvent = self._text_edit_key_press
        self.ui.textEdit_remark.keyPressEvent = self._text_edit_key_press

        self.ui.checkBox_complaint_injury.clicked.connect(self._complaint_injury)

        self.ui.lineEdit_disease_code1.textChanged.connect(self.disease_code_changed)
        self.ui.lineEdit_disease_code1.returnPressed.connect(
            self.disease_code_return_pressed
        )
        self.ui.lineEdit_disease_code1.editingFinished.connect(
            self.disease_code_editing_finished
        )

        self.ui.lineEdit_disease_code2.textChanged.connect(self.disease_code_changed)
        self.ui.lineEdit_disease_code2.editingFinished.connect(
            self.disease_code_editing_finished
        )
        self.ui.lineEdit_disease_code2.returnPressed.connect(
            self.disease_code_return_pressed
        )

        self.ui.lineEdit_disease_code3.textChanged.connect(self.disease_code_changed)
        self.ui.lineEdit_disease_code3.returnPressed.connect(
            self.disease_code_return_pressed
        )
        self.ui.lineEdit_disease_code3.editingFinished.connect(
            self.disease_code_editing_finished
        )

        self.ui.lineEdit_disease_code4.textChanged.connect(self.disease_code_changed)
        self.ui.lineEdit_disease_code4.returnPressed.connect(
            self.disease_code_return_pressed
        )
        self.ui.lineEdit_disease_code4.editingFinished.connect(
            self.disease_code_editing_finished
        )
        self.ui.action_open_memo.triggered.connect(self._open_patient_memo)

    def _open_patient_memo(self):
        self.dialog_patient_memo.show_patient_memo()

    # 檢查是否開啟tab
    def tab_past_exists(self, tab_text):
        if self.ui.tabWidget_past_record.count() <= 0:
            return False

        for i in range(self.ui.tabWidget_past_record.count()):
            if self.ui.tabWidget_past_record.tabText(i) == tab_text:
                self.ui.tabWidget_past_record.setCurrentIndex(i)
                return True

        return False

    # 檢查是否開啟tab
    def get_tab_past_index(self, tab_text):
        if self.ui.tabWidget_past_record.count() <= 0:
            return None

        for i in range(self.ui.tabWidget_past_record.count()):
            if self.ui.tabWidget_past_record.tabText(i) == tab_text:
                return i

        return None

    def _integrate_care_clicked(self):
        # try:
        #     age_year, _ = date_utils.get_age(
        #         self.patient_record['Birthday'], self.medical_record['CaseDate'])
        #     if self.age_year is not None and age_year < 4:
        #         system_utils.show_message_box(
        #             QMessageBox.Critical,
        #             '提醒',
        #             '<font size="5" color="red"><b>4歲以下兒童不得申報整合醫療照護.</b></font>',
        #             '未滿四歲兒童之門診診察費業已加成20%，不能再申報整合醫療照護加成.'
        #         )
        #         self.check_box_integrate_care.setChecked(False)
        #         return
        # except Exception:
        #     pass

        self.calculate_ins_fees()

        self.check_box_integrate_care.setStyleSheet(None)
        if not self.check_box_integrate_care.isChecked():
            return

        self.check_box_integrate_care.setStyleSheet("color: red; font-weight: bold")
        dialog = dialog_utils.get_dialog_integrate_care(
            self, self.database, self.system_settings, self.case_key
        )
        dialog.exec_()

        if not dialog.is_select_integrate_care():
            self.check_box_integrate_care.setStyleSheet(None)
            self.check_box_integrate_care.setChecked(False)

        symptom = dialog.get_symptom()
        self.calculate_ins_fees()
        dialog.deleteLater()

        if symptom is not None:
            self._set_integrate_care_symptom(symptom)

    def _set_integrate_care_symptom(self, symptom):
        self.insert_text(
            self.ui.textEdit_symptom, symptom + "\n", "", insert_comma=False
        )

    # 顯示看診計時器
    def _set_tab_cornor_widget(self):
        tab_corner_widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout(tab_corner_widget)
        h_layout.setContentsMargins(4, 4, 4, 4)
        h_layout.setSpacing(8)

        if self.medical_record["InsType"] == "自費":
            self._set_regist_typex_corner_widget(tab_corner_widget, h_layout)
        else:
            self._set_chronic_code(tab_corner_widget, h_layout)
            self._set_integrate_care(tab_corner_widget, h_layout)

        if (
            self.call_from in ["醫師看診作業", "新增自費病歷", "加購自費病歷"]
            and self.system_settings.field("顯示看診計時器") == "Y"
        ):
            self._set_timer(tab_corner_widget, h_layout)

        self.ui.tabWidget_medical.setCornerWidget(
            tab_corner_widget, QtCore.Qt.TopRightCorner
        )

    def _set_regist_typex_corner_widget(self, tab_corner_widget, h_layout):
        label = QtWidgets.QLabel(tab_corner_widget)
        label.setText("自費科別 ")
        h_layout.addWidget(label)

        try:
            regist_typex = string_utils.xstr(self.medical_record["RegistTypex"])
        except Exception:
            regist_typex = ""

        if regist_typex == "":
            regist_typex = nhi_utils.REGIST_TYPEX[0]

        self.combo_box_regist_typex = QtWidgets.QComboBox(tab_corner_widget)
        ui_utils.set_combo_box(
            self.combo_box_regist_typex, nhi_utils.REGIST_TYPEX, regist_typex
        )
        h_layout.addWidget(self.combo_box_regist_typex)

    def _set_integrate_care(self, tab_corner_widget, h_layout):
        self.check_box_integrate_care = QtWidgets.QCheckBox(tab_corner_widget)
        self.check_box_integrate_care.setText("整合醫療照護")
        self.check_box_integrate_care.clicked.connect(self._integrate_care_clicked)
        treat_type = self.tab_registration.ui.comboBox_treat_type.currentText()
        course = number_utils.get_integer(
            self.tab_registration.ui.comboBox_course.currentText()
        )

        if treat_type in nhi_utils.IMPROVE_CARE_TREAT:  # 試辦計畫不可申報
            self.check_box_integrate_care.setEnabled(False)

        if (
            self.call_from == "醫師看診作業"
            and treat_type in nhi_utils.IMPROVE_CARE_TREAT
        ):  # 試辦計畫不可申報
            self.check_box_integrate_care.setEnabled(False)
        elif course >= 2:  # 2024-01-17 中區健保局  療程不可申報
            self.check_box_integrate_care.setEnabled(False)

        h_layout.addWidget(self.check_box_integrate_care)

    def _set_chronic_code(self, tab_corner_widget, h_layout):
        self.check_box_chronic_code = QtWidgets.QCheckBox(tab_corner_widget)
        self.check_box_chronic_code.setText("不申報慢性病")
        self.check_box_chronic_code.clicked.connect(self._chronic_code_clicked)

        h_layout.addWidget(self.check_box_chronic_code)

    def _chronic_code_clicked(self):
        self.tab_registration.ui.checkBox_no_special_code.setChecked(
            self.check_box_chronic_code.isChecked()
        )

        if self.check_box_chronic_code.isChecked():
            self.check_box_chronic_code.setStyleSheet(
                "color: darkGreen; font-weight: bold"
            )
        else:
            self.check_box_chronic_code.setStyleSheet(None)

        self.check_chronic_disease()
        self.tab_registration.check_chronic_disease()

    # 看診時間提醒
    def _set_timer(self, tab_corner_widget, h_layout):
        label = QtWidgets.QLabel(tab_corner_widget)
        label.setText("看診計時:")
        h_layout.addWidget(label)

        self.lcd_number = QtWidgets.QLCDNumber(tab_corner_widget)
        self.lcd_number.setSegmentStyle(self.lcd_number.SegmentStyle.Flat)
        self.lcd_number.setFrameShape(QtWidgets.QFrame.NoFrame)
        # self.lcd_number.setStyleSheet('color: darkGreen')
        h_layout.addWidget(self.lcd_number)

        self.BLINKING_TIME = 20  # 看診警告時間(分鐘)
        self.lcd_number.display("00:00")
        self.timer = QtCore.QTimer(self)
        self.set_blinking = False
        self.minutes = 0
        self.seconds = 0
        self.timer.start(1000)
        self.timer.timeout.connect(self._timeout)

    def _timeout(self):
        self.seconds += 1
        if self.seconds >= 60:
            self.minutes += 1
            self.seconds = 0

        self.lcd_number.display(f"{self.minutes:0>2}:{self.seconds:0>2}")

        if self.minutes >= self.BLINKING_TIME and not self.set_blinking:
            self.set_blinking = True
            self._set_blinking_timer()

    def _set_blinking_timer(self):
        self.micro_seconds = 0

        self.blink_timer = QtCore.QTimer(self)
        self.blink_timer.start(100)
        self.blink_timer.timeout.connect(self._blink_timeout)

    def _blink_timeout(self):
        self.micro_seconds += 1
        if self.micro_seconds >= 5:
            self.micro_seconds = 0

        if self.micro_seconds <= 2:
            self.lcd_number.setStyleSheet("color: white")
        else:
            self.lcd_number.setStyleSheet("color: red")

    # 顯示處方放大紐
    def _set_prescript_tab_cornor_widget(self):
        tab_corner_widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout(tab_corner_widget)
        h_layout.setContentsMargins(4, 4, 4, 4)
        h_layout.setSpacing(8)

        self.tool_button_zoom = QtWidgets.QToolButton(tab_corner_widget)
        self.tool_button_zoom.setToolTip("放大處方頁面")
        self.tool_button_zoom.clicked.connect(self._prescript_zoom_clicked)

        icon = QtGui.QIcon("./icons/arrow-up.png")
        self.tool_button_zoom.setIcon(icon)

        h_layout.addWidget(self.tool_button_zoom)

        self.ui.tabWidget_prescript.setCornerWidget(
            tab_corner_widget, QtCore.Qt.TopRightCorner
        )

    def _prescript_zoom_clicked(self):
        self.ui.groupBox_diagnostic.setVisible(
            not self.ui.groupBox_diagnostic.isVisible()
        )
        if self.ui.groupBox_diagnostic.isVisible():
            icon = QtGui.QIcon("./icons/arrow-up.png")
            self.tool_button_zoom.setToolTip("放大處方頁面")
        else:
            icon = QtGui.QIcon("./icons/arrow-down.png")
            self.tool_button_zoom.setToolTip("還原處方頁面")

        self.tool_button_zoom.setIcon(icon)

    def _auto_uppercase(self, line_edit_disease_code):
        disease_code = line_edit_disease_code.text()
        line_edit_disease_code.setText(disease_code.upper())

    def _tab_moved(self, move_to_index):
        tab_no = 0
        for tab_index in range(self.ui.tabWidget_prescript.count()):
            tab_name = self.ui.tabWidget_prescript.tabText(tab_index)
            if tab_name in ["健保", "加強照護"]:
                continue

            tab_no += 1
            self.ui.tabWidget_prescript.setTabText(tab_index, f"自費{tab_no}")
            tab = self.ui.tabWidget_prescript.widget(tab_index)
            tab.medicine_set = tab_no + 1
            for row_no in range(tab.tableWidget_prescript.rowCount()):
                tab.tableWidget_prescript.setItem(
                    row_no, 0, QtWidgets.QTableWidgetItem("-1")
                )

        self._adjust_tabs()

    def _adjust_tabs(self):
        tab_index_dict = {
            "健保": 0,
            "自費1": 1,
            "自費2": 2,
            "自費3": 3,
            "自費4": 4,
            "自費5": 5,
            "自費6": 6,
            "自費7": 7,
            "自費8": 8,
            "自費9": 9,
            "加強照護": 10,
        }

        for tab_index in range(self.ui.tabWidget_prescript.count()):
            tab_name = self.ui.tabWidget_prescript.tabText(tab_index)
            current_tab = self.ui.tabWidget_prescript.widget(tab_index)

            self.tab_list[tab_index_dict[tab_name]] = current_tab

    def _tab_changed(self, i):
        tab_name = self.ui.tabWidget_prescript.tabText(i)

        # if (self.call_from != '醫師看診作業' and
        #         personnel_utils.get_permission(self.database, '病歷資料', '病歷修正', self.user_name) != 'Y'):
        #     movable = False
        if tab_name == "健保":
            movable = False
        else:
            movable = True

        self.ui.tabWidget_prescript.setMovable(movable)

        try:
            self.tab_list[i].tableWidget_prescript.setFocus()
        except Exception:
            pass

    def close_prescript_tab(self, current_index):
        current_tab = self.ui.tabWidget_prescript.widget(current_index)
        tab_name = self.ui.tabWidget_prescript.tabText(current_index)
        if tab_name == "健保":
            return

        if self.close_tab_warning:
            msg_box = dialog_utils.get_message_box(
                f"關閉{tab_name}頁面",
                QMessageBox.Warning,
                f'<font size="5" color="red"><b>確定關閉{tab_name}病歷處方頁面?</b></font>',
                "注意！資料刪除後, 將無法回復!",
            )
            close_tab = msg_box.exec_()
            if not close_tab:
                return

        self.close_tab_warning = True

        for i in range(1, len(self.tab_list)):
            if tab_name == f"自費{i}":
                self.tab_list[i] = None

        self.tab_medical_record_fees.calculate_fees()
        current_tab.close_all()
        current_tab.deleteLater()

        sip.delete(current_tab)  # 真正的刪除分頁

        self.tab_medical_record_fees.calculate_fees()

    # 關閉所有自費處方頁
    def close_all_self_prescript_tabs(self):
        for i in range(len(self.tab_list), 0, -1):
            current_tab = self.ui.tabWidget_prescript.widget(i)
            if current_tab is not None:
                tab_name = self.ui.tabWidget_prescript.tabText(i)
                if tab_name == "加強照護":  # 加強照護不要關閉
                    continue

                self.close_tab_warning = False
                self.close_prescript_tab(i)

    def close_medical_record(self, close_without_saving=False):
        if close_without_saving:
            self.call_from = "離開不存檔"

        self.close_all()
        self.close_tab()

    def modify_patient(self):
        self.parent.open_patient_record(self.patient_key, "門診掛號")

    def disease_code_editing_finished(self):
        disease_list = [
            [self.ui.lineEdit_disease_code1, self.ui.lineEdit_disease_name1],
            [self.ui.lineEdit_disease_code2, self.ui.lineEdit_disease_name2],
            [self.ui.lineEdit_disease_code3, self.ui.lineEdit_disease_name3],
            [self.ui.lineEdit_disease_code4, self.ui.lineEdit_disease_name4],
        ]

        for i, (code_field, name_field) in enumerate(disease_list):
            # 有碼無名 = 查詢失敗或沒查, 清掉
            if code_field.text() != "" and name_field.text() == "":
                code_field.blockSignals(True)
                code_field.setText("")
                code_field.blockSignals(False)

        self.rearrange_disease_codes()

    def _get_disease_list(self):
        return [
            [
                self.ui.lineEdit_disease_code1,
                self.ui.lineEdit_disease_name1,
                self.ui.toolButton_disease1,
                self.ui.pushButton_disease1,
            ],
            [
                self.ui.lineEdit_disease_code2,
                self.ui.lineEdit_disease_name2,
                self.ui.toolButton_disease2,
                self.ui.pushButton_disease2,
            ],
            [
                self.ui.lineEdit_disease_code3,
                self.ui.lineEdit_disease_name3,
                self.ui.toolButton_disease3,
                self.ui.pushButton_disease3,
            ],
            [
                self.ui.lineEdit_disease_code4,
                self.ui.lineEdit_disease_name4,
                self.ui.toolButton_disease4,
                self.ui.pushButton_disease4,
            ],
        ]

    def disease_code_changed(self):
        # 打字中觸發: 設定 enabled 狀態; 若 code 被清空, 連 name 一併清掉
        disease_list = self._get_disease_list()
        for row_no, (code_edit, name_edit, tool_button, push_button) in enumerate(
            disease_list
        ):
            if code_edit.text().strip() == "":
                if name_edit.text() != "":
                    name_edit.setText("")
                    name_edit.setToolTip("")
                code_edit.setToolTip("")

            enabled = row_no == 0 or disease_list[row_no - 1][0].text().strip() != ""
            code_edit.setEnabled(enabled)
            tool_button.setEnabled(enabled)
            push_button.setEnabled(enabled)

    def rearrange_disease_codes(self):
        if getattr(self, "_in_rearrange", False):
            return

        self._in_rearrange = True
        try:
            disease_list = self._get_disease_list()

            # 1. 收集非空白的診斷碼 (病名已確認的才正規化)
            entries = []
            for code_edit, name_edit, _, _ in disease_list:
                icd_code = code_edit.text().strip().upper()
                if icd_code != "":
                    entries.append((icd_code, name_edit.text()))

            # 2. 遞補重填
            for row_no, (code_edit, name_edit, _, _) in enumerate(disease_list):
                if row_no < len(entries):
                    icd_code, disease_name = entries[row_no]
                    if code_edit.text() != icd_code:
                        code_edit.blockSignals(True)
                        code_edit.setText(icd_code)
                        code_edit.blockSignals(False)
                        name_edit.setText(disease_name)
                    case_utils.set_disease_tool_tip(
                        self.database,
                        code_edit,
                        name_edit,
                        self.parent.complicated_treat_list,
                    )
                else:
                    code_edit.blockSignals(True)
                    code_edit.setText("")
                    code_edit.blockSignals(False)
                    name_edit.setText("")
                    code_edit.setToolTip("")
                    name_edit.setToolTip("")

            # 3. enabled 狀態
            self.disease_code_changed()

            # check_chronic_disease 本來就會先清再重建 special_code,
            # 不需要靠 shifted 另外清
            self.check_chronic_disease()
        finally:
            self._in_rearrange = False

    def check_chronic_disease(self):
        if self.tab_registration is None:
            return

        self.tab_registration.ui.lineEdit_special_code.setText("")

        disease_list = [
            self.ui.lineEdit_disease_code1,
            self.ui.lineEdit_disease_code2,
            self.ui.lineEdit_disease_code3,
            self.ui.lineEdit_disease_code4,
        ]

        for icd_field in disease_list:
            icd_code = icd_field.text().strip()
            if not icd_code:
                continue

            icd_code = re.sub(r"[\\\"\']", "", icd_code)

            try:
                rows = self.database.select_record(
                    "SELECT SpecialCode FROM icd10 WHERE ICDCode = %s", (icd_code,)
                )
            except Exception as e:
                print(f"[資料庫查詢錯誤] {e}")
                continue

            if (
                rows
                and not self.tab_registration.ui.checkBox_no_special_code.isChecked()
            ):
                special_code = string_utils.xstr(rows[0]["SpecialCode"])
                if self.tab_registration.ui.lineEdit_special_code.text() == "":
                    self.tab_registration.ui.lineEdit_special_code.setText(special_code)

    # 檢查診斷碼是否為2023最新版
    def check_disease_valid(self):
        disease_list = [
            [self.ui.lineEdit_disease_code1, self.ui.lineEdit_disease_name1],
            [self.ui.lineEdit_disease_code2, self.ui.lineEdit_disease_name2],
            [self.ui.lineEdit_disease_code3, self.ui.lineEdit_disease_name3],
            [self.ui.lineEdit_disease_code4, self.ui.lineEdit_disease_name4],
        ]

        for code_field, name_field in disease_list:
            icd_code = code_field.text().strip()
            if not icd_code:
                continue

            icd_code = re.sub(r"[\\\"\']", "", icd_code)

            try:
                rows = self.database.select_record(
                    "SELECT ICD10Key FROM icd10 WHERE ICDCode = %s", (icd_code,)
                )
            except Exception as e:
                print(f"[資料庫查詢錯誤] {e}")
                rows = []

            if not rows:
                code_field.blockSignals(True)
                name_field.blockSignals(True)

                code_field.setText("")
                code_field.setToolTip("")
                name_field.setText("")
                name_field.setToolTip("")

                code_field.blockSignals(False)
                name_field.blockSignals(False)

    # 檢查診斷碼是否可以執行複雜性處置
    def check_complicated_treat_disease(self, disease_code):
        if self.tab_list[0] is None:  # 非健保不檢查
            return

        treatment = string_utils.xstr(self.tab_list[0].comboBox_treatment.currentText())
        second_treatment = string_utils.xstr(
            self.tab_list[0].comboBox_second_treatment.currentText()
        )

        if (
            treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST
            or second_treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST
        ):
            return

        hint_list = []
        hint = "以上僅供參考"
        treat_type = None

        if (
            disease_code in self.parent.moderate_complicated_acupuncture_list
            and treatment not in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST
            and second_treatment not in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST
        ):
            hint_list.append(
                '<font size="5" color="blue"><b>可申報中度複雜性針灸!</b></font>'
            )
            treat_type = "中度複雜性針灸"

        if (
            disease_code in self.parent.highly_complicated_acupuncture_list
            and treatment not in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST
            and second_treatment not in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST
        ):
            hint_list.append(
                '<font size="5" color="blue"><b>可申報高度複雜性針灸!</b></font>'
            )
            if treat_type is None:
                treat_type = "高度複雜性針灸"

        if (
            disease_code in self.parent.moderate_complicated_massage_list
            and treatment not in nhi_utils.MODERATE_COMPLICATED_MASSAGE_LIST
            and second_treatment not in nhi_utils.MODERATE_COMPLICATED_MASSAGE_LIST
        ):
            hint_list.append(
                '<font size="5" color="blue"><b>可申報中度複雜性傷科!</b></font>'
            )
            if treat_type is None:
                treat_type = "中度複雜性傷科"
        if (
            disease_code in self.parent.highly_complicated_massage_list
            and treatment not in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_LIST
            and second_treatment not in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_LIST
        ):
            hint_list.append(
                '<font size="5" color="blue"><b>可申報高度複雜性傷科!</b></font>'
            )
            if treat_type is None:
                treat_type = "高度複雜性傷科"

        try:
            rows = self.database.select_record(
                """
                SELECT SpecialCode FROM icd10
                WHERE
                    ICDCode = %s AND
                    SpecialCode IS NOT NULL AND
                    LENGTH(SpecialCode) > 0
                """,
                (disease_code,),
            )
            if len(rows) > 0:
                hint_list.append(
                    '<font size="5" color="red"><b>此診斷碼為慢性病</b></font>'
                )
        except Exception:
            pass

        if len(hint_list) > 0:
            if (
                self.system_settings.field("輸入病名後不要彈出複雜性針傷提示視窗")
                == "Y"
            ) or treat_type in [
                None,
                self.tab_list[0].comboBox_treatment.currentText(),
            ]:
                pass
            else:
                if treat_type is not None and self.tab_list[
                    0
                ].comboBox_treatment.currentText() in ["", None]:
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Warning)
                    msg_box.setWindowTitle("提醒")
                    msg_box.setText(
                        f"""<font size="5"><b>診斷碼 {disease_code}</b></font><br>
                        {"<br>".join(hint_list)}"""
                    )
                    close_button = QPushButton("關閉")
                    treat_button = QPushButton(f"執行{treat_type}")
                    msg_box.addButton(close_button, QMessageBox.NoRole)
                    msg_box.addButton(treat_button, QMessageBox.YesRole)
                    msg_box.setDefaultButton(close_button)  # Enter 預設落在關閉
                    msg_box.setEscapeButton(close_button)  # Esc / 右上角 X 也視同關閉

                    msg_box.exec_()
                    if msg_box.clickedButton() is treat_button:
                        self.tab_list[0].comboBox_treatment.setCurrentText(treat_type)
                else:
                    system_utils.show_message_box(
                        QMessageBox.Information,
                        "提醒",
                        f"""<font size="5"><b>診斷碼 {disease_code}</b></font><br>
                        {"<br>".join(hint_list)}""",
                        hint,
                    )

    def disease_code_return_pressed(self):
        icd_code = self.sender().text().strip()
        if not icd_code:
            return

        # 移除特殊符號（\ " '）
        icd_code = re.sub(r"[\\\"\']", "", icd_code)

        # 對應 sender 找出 name 欄位
        sender_name = self.sender().objectName()
        line_edit_disease_name = {
            "lineEdit_disease_code1": self.ui.lineEdit_disease_name1,
            "lineEdit_disease_code2": self.ui.lineEdit_disease_name2,
            "lineEdit_disease_code3": self.ui.lineEdit_disease_name3,
            "lineEdit_disease_code4": self.ui.lineEdit_disease_name4,
        }.get(sender_name)

        if not line_edit_disease_name:
            return

        # 組合 SQL 查詢
        if icd_code.isdigit():
            sql = """
                SELECT
                    icd10.ICD10Key,
                    icd10.ICDCode,
                    icd10.ChineseName,
                    icd10.EnglishName,
                    icd10.SpecialCode
                FROM icdmap
                    LEFT JOIN icd10 ON icdmap.ICD10Code = icd10.ICDCode
                WHERE
                    ICD9Code LIKE %s
                ORDER BY icd10.ICDCode LIMIT 2
            """
            params = (f"{icd_code}%",)
        else:
            keyword_list = icd_code.split()
            params = [f"{icd_code}%", f"{icd_code}%"]

            chinese_name_script = " AND ".join(
                ["ChineseName LIKE %s" for _ in keyword_list]
            )
            english_keyword_list = [k for k in keyword_list if len(k) >= 5]
            english_name_script = " AND ".join(
                ["UPPER(EnglishName) LIKE %s" for _ in english_keyword_list]
            )

            conditions = ["(ICDCode LIKE %s OR InputCode LIKE %s)"]
            if chinese_name_script:
                conditions.append(f"({chinese_name_script})")
                params += [f"%{k}%" for k in keyword_list]
            if english_name_script:
                conditions.append(f"({english_name_script})")
                params += [f"%{k.upper()}%" for k in english_keyword_list]

            sql = f"""
                SELECT * FROM icd10
                WHERE {" OR ".join(conditions)}
                LIMIT 2
            """
            params = tuple(params)

        try:
            rows = self.database.select_record(sql, params)
        except Exception as e:
            print(f"[ICD 查詢錯誤] {e}")
            system_utils.show_message_box(
                QMessageBox.Critical,
                "錯誤",
                "<b>查詢診斷碼時發生錯誤，請稍後再試。</b>",
                str(e),
            )
            return

        # 根據查詢結果處理
        if not rows:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "無此病名",
                '<font size="5" color="red"><b>找不到此關鍵字的病名, 請重新輸入.</b></font>',
                "請確定輸入的關鍵字是否正確.",
            )
            self.sender().setText("")  # ✅ 改為空字串
            return

        elif len(rows) == 1:
            self._set_disease(
                self.sender(),
                line_edit_disease_name,
                string_utils.xstr(rows[0]["ICDCode"]).upper(),
                string_utils.xstr(rows[0]["ChineseName"]),
            )
            if sender_name == "lineEdit_disease_code1":
                try:
                    self.tab_registration.ui.lineEdit_special_code.setText(
                        string_utils.xstr(rows[0]["SpecialCode"])
                    )
                except Exception:
                    pass

        elif len(rows) >= 2:
            self._open_disease_dialog(icd_code, self.sender(), line_edit_disease_name)

        if self.ui.lineEdit_disease_code1.text() == "":
            return

        # 額外處理複雜治療對應
        self.check_complicated_treat_disease(self.sender().text())

        # 自動移至下一欄位
        focus_order = {
            self.ui.lineEdit_disease_name1: self.ui.lineEdit_disease_code2,
            self.ui.lineEdit_disease_name2: self.ui.lineEdit_disease_code3,
            self.ui.lineEdit_disease_name3: self.ui.lineEdit_disease_code4,
        }

        next_field = focus_order.get(line_edit_disease_name)
        if next_field:
            next_field.setFocus(True)

    def _open_disease_dialog(
        self, icd_code, line_edit_disease_code, line_edit_disease_name
    ):
        dialog = dialog_utils.get_dialog_disease_picker(
            self, self.database, self.system_settings, icd_code
        )

        if dialog.exec_():
            icd10_key = dialog.icd10_key
            icd_code = dialog.icd_code
            disease_name = dialog.chinese_name
            special_code = dialog.special_code
            self._set_disease(
                line_edit_disease_code,
                line_edit_disease_name,
                icd_code,
                disease_name,
            )

            if self.tab_registration is not None:
                if line_edit_disease_code == self.ui.lineEdit_disease_code1:
                    self.tab_registration.ui.lineEdit_special_code.setText(
                        string_utils.xstr(special_code)
                    )
                db_utils.increment_hit_rate(
                    self.database, "icd10", "ICD10Key", icd10_key
                )

        dialog.close_all()
        dialog.deleteLater()

    def _set_disease(
        self, line_edit_disease_code, line_edit_disease_name, icd_code, disease_name
    ):
        line_edit_disease_code.setText(icd_code)
        line_edit_disease_name.setText(disease_name)
        try:
            case_utils.set_disease_tool_tip(
                self.database,
                line_edit_disease_code,
                line_edit_disease_name,
                self.parent.complicated_treat_list,
            )
        except Exception:
            pass

    def _insert_template_patient(self):
        fields = ["Name", "ID", "Birthday"]
        data = ["參考病歷", "A123456789", "1980-01-01"]

        self.database.exec_sql('DELETE FROM patient WHERE Name = "參考病歷"')
        self.database.insert_record("patient", fields, data)
        self.database.exec_sql(
            'UPDATE patient SET PatientKey = 0 WHERE Name = "參考病歷"'
        )

    def _read_data(self):
        read_result = True

        if self.patient_key is not None:
            sql = """
                SELECT * FROM patient
                WHERE
                    PatientKey = %s
            """
            params = (self.patient_key,)
            try:
                self.patient_record: dict = self.database.select_record(
                    sql, params=params
                )[0]
            except Exception:
                self.patient_record = None
                if self.call_from == "參考病歷":
                    self._insert_template_patient()
                else:
                    return read_result

        if self.case_key is None:
            return read_result

        try:
            sql = """
                SELECT * FROM cases
                WHERE
                    CaseKey = %s
            """
            params = (self.case_key,)
            self.medical_record: dict = self.database.select_record(sql, params=params)[
                0
            ]
            self.ins_type = string_utils.xstr(self.medical_record["InsType"])
        except Exception:
            self.medical_record = None
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Critical,
                "資料遺失",
                '<font size="5" color="red"><b>找不到病歷資料, 請重新掛號.</b></font>',
                "資料不明原因遺失.",
            )
            read_result = False

        if self.medical_record is None:
            return read_result

        # 同一個人，不必重讀
        if (
            self.patient_record is not None
            and self.patient_record["PatientKey"] == self.medical_record["PatientKey"]
        ):
            return read_result

        try:
            sql = """
                SELECT * FROM patient
                WHERE
                    PatientKey = %s
            """
            params = (self.medical_record["PatientKey"],)
            self.patient_record = self.database.select_record(sql, params=params)[0]
            self.patient_key = self.patient_record["PatientKey"]
        except IndexError:
            if self.patient_record is not None:
                system_utils.show_message_box(
                    QtWidgets.QMessageBox.Critical,
                    "資料遺失",
                    '<font size="5" color="red"><b>找不到病患資料, 請更新病歷內的病歷號碼.</b></font>',
                    "資料不明原因遺失.",
                )

        return read_result

    def _set_data(self):
        self._set_patient_data()
        if self.call_from in ["新增自費病歷", "加購自費病歷"]:
            self._read_recently_history()
            self.case_key = None
            self.ins_type = "自費"
            self._read_fees()
            self.add_prescript_tab(2)
            return

        self._set_medical_record(self.medical_record)
        self._set_prescripts()
        self._set_fees()
        self._set_misc()

    def _set_permission(self):
        # if self.call_from == '醫師看診作業':
        #     return
        if self.user_name == "超級使用者":
            return

        if (
            personnel_utils.get_permission(
                self.database, "病患查詢", "調閱資料", self.user_name
            )
            != "Y"
        ):
            self.ui.action_patient.setEnabled(False)

        if (
            personnel_utils.get_permission(
                self.database, "醫師看診作業", "病歷登錄", self.user_name
            )
            == "Y"
        ):
            return

        if (
            personnel_utils.get_permission(
                self.database, "病歷資料", "病歷修正", self.user_name
            )
            == "Y"
        ):
            return

        self.ui.action_save.setEnabled(False)
        self.ui.action_past_history.setEnabled(False)
        self.ui.action_open_hosts.setEnabled(False)
        self.ui.action_medical_record_collection.setEnabled(False)
        self.ui.action_capture_image.setEnabled(False)
        self.ui.action_save_and_print.setEnabled(False)
        self.ui.action_save_and_print_prescript.setEnabled(False)
        self.ui.action_save_and_print_receipt.setEnabled(False)
        self.ui.action_save_and_print_misc.setEnabled(False)

        self.ui.action_dictionary.setEnabled(False)
        self.ui.action_append_self_medical_record.setEnabled(False)
        self.ui.action_reference.setEnabled(False)
        self.ui.action_reservation.setEnabled(False)

        self.ui.textEdit_symptom.setReadOnly(True)
        self.ui.textEdit_tongue.setReadOnly(True)
        self.ui.textEdit_pulse.setReadOnly(True)
        self.ui.textEdit_remark.setReadOnly(True)

        self.ui.lineEdit_disease_code1.setReadOnly(True)
        self.ui.lineEdit_disease_code2.setReadOnly(True)
        self.ui.lineEdit_disease_code3.setReadOnly(True)
        self.ui.lineEdit_disease_code4.setReadOnly(True)

        self.ui.lineEdit_distinguish.setReadOnly(True)
        self.ui.lineEdit_cure.setReadOnly(True)

        self.ui.toolButton_symptom.setEnabled(False)
        self.ui.toolButton_today.setEnabled(False)
        self.ui.toolButton_add_symptom_dict.setEnabled(False)
        self.ui.checkBox_reference.setEnabled(False)
        self.ui.checkBox_complaint_injury.setEnabled(False)

        self.ui.toolButton_tongue.setEnabled(False)
        self.ui.toolButton_pulse.setEnabled(False)
        self.ui.toolButton_remark.setEnabled(False)

        self.ui.toolButton_disease1.setEnabled(False)
        self.ui.toolButton_disease2.setEnabled(False)
        self.ui.toolButton_disease3.setEnabled(False)
        self.ui.toolButton_disease4.setEnabled(False)

        self.ui.toolButton_distincts.setEnabled(False)
        self.ui.toolButton_cure.setEnabled(False)

        self.ui.tabWidget_prescript.setTabsClosable(False)
        self.ui.tabWidget_prescript.setMovable(False)

        if (
            personnel_utils.get_permission(
                self.database, "病歷資料", "僅能修改主訴舌診脈象備註", self.user_name
            )
            == "Y"
        ):
            self.ui.toolButton_symptom.setEnabled(True)
            self.ui.toolButton_today.setEnabled(True)
            self.ui.toolButton_add_symptom_dict.setEnabled(True)
            self.ui.checkBox_reference.setEnabled(True)
            self.ui.checkBox_complaint_injury.setEnabled(True)

            self.ui.toolButton_tongue.setEnabled(True)
            self.ui.toolButton_pulse.setEnabled(True)
            self.ui.toolButton_remark.setEnabled(True)

            self.ui.textEdit_symptom.setReadOnly(False)
            self.ui.textEdit_tongue.setReadOnly(False)
            self.ui.textEdit_pulse.setReadOnly(False)
            self.ui.textEdit_remark.setReadOnly(False)

    # 設定看診中
    def _set_in_progress(self, in_progress):
        if self.wait_key is None:
            return

        # in_progress 為 "Y" 或 None, 直接寫入 (None 會存成 SQL NULL)
        sql = "UPDATE wait SET InProgress = %s WHERE WaitKey = %s"
        self.database.exec_sql(sql, (in_progress, self.wait_key))

        if in_progress is not None and self.system_settings.field("alleypin") == "Y":
            alleypin_utils.update_progresses(
                self.database, self.system_settings, self.case_key
            )

        self._send_socket_data()

    def _get_wait_key(self):
        if self.case_key is None:
            return None

        sql = f"""
            SELECT WaitKey FROM wait
            WHERE
                CaseKey = {self.case_key}
        """
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            wait_key = None
        else:
            wait_key = rows[0]["WaitKey"]

        return wait_key

    def _set_patient_data(self):
        self.age_year = None
        if self.case_key is None:
            self.ui.label_case_date.setText(
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            self.ui.label_ins_type.setText(self.call_from)
            self.ui.label_patient_name.setText(self.call_from)
            self.ui.label_regist_no.setText("0")
            self.ui.label_share_type.setText(self.call_from)
            self.ui.label_card.setText(self.call_from)
            return

        if self.patient_record is None:
            name = string_utils.xstr(self.medical_record["Name"])
            self.ui.label_case_date.setText(
                self.medical_record["CaseDate"].strftime("%Y-%m-%d %H:%M")
            )
            self.ui.label_ins_type.setText(self.ins_type)
            self.ui.label_patient_name.setText(string_utils.xstr(name))
            self.ui.label_regist_no.setText(None)
            self.ui.label_share_type.setText(None)
            self.ui.label_card.setText(None)
            return

        patient_key = string_utils.xstr(self.patient_record["PatientKey"])
        treat_type = string_utils.xstr(self.medical_record["TreatType"])
        self.ui.groupBox_patient.setTitle(
            f"病患基本資料 (病歷號: {patient_key}, {treat_type})"
        )
        name = string_utils.xstr(self.patient_record["Name"])

        case_date = self.medical_record["CaseDate"].strftime("%Y-%m-%d %H:%M")
        birthday = self.patient_record["Birthday"]
        if self.system_settings.field("日期格式") == "民國年":
            case_date = date_utils.date_to_zh_tw_date(case_date)
            try:
                birthday = date_utils.date_to_zh_tw_date(
                    string_utils.xstr(self.patient_record["Birthday"])
                )
            except Exception:
                pass

        self.age_year, age_month = date_utils.get_age(
            self.patient_record["Birthday"], self.medical_record["CaseDate"]
        )
        if self.age_year is None:
            age = ""
            birthdate = ""
        else:
            age = f"{self.age_year}.{age_month}"
            birthdate = f'<br><font color="darkMagenta">{birthday} ({age})</font>'

        if self.age_year is not None and 0 <= self.age_year < 17:
            self.tab_growth_chart = module_utils.get_medical_record_growth_chart(
                self, self.database, self.system_settings, self.case_key, self.call_from
            )
            self.ui.tabWidget_medical.addTab(self.tab_growth_chart, "生長曲線")
            self.tab_growth_chart.plot_chart()

        gender = self.patient_record["Gender"]
        if gender in ["男", "女"]:
            gender = f"({gender})"
        else:
            gender = ""

        ins_type = string_utils.xstr(self.ins_type)
        visit = string_utils.xstr(self.medical_record["Visit"])
        if visit == "初診":
            visit = f'<font color="red">{visit}</font>'

        name += f" {gender}" + birthdate

        card = string_utils.xstr(self.medical_record["Card"])
        if number_utils.get_integer(self.medical_record["Continuance"]) >= 1:
            card += "-" + string_utils.xstr(self.medical_record["Continuance"])

        regist_no = string_utils.xstr(self.medical_record["RegistNo"])
        regist_type = string_utils.xstr(self.medical_record["RegistType"])
        if regist_type != "一般門診":
            regist_type = f'<font color="red">{regist_type}</font>'

        self.ui.label_case_date.setText(case_date)
        self.ui.label_ins_type.setText(f"{ins_type} - {visit}")
        self.ui.label_patient_name.setText(string_utils.xstr(name))
        self.ui.label_regist_no.setText(
            string_utils.xstr(f"{regist_no} ({regist_type})")
        )
        self.ui.label_share_type.setText(
            string_utils.xstr(self.medical_record["Share"])
        )
        self.ui.label_card.setText(string_utils.xstr(card))

        patient_remark = string_utils.get_str(self.patient_record["Remark"], "utf8")
        self.ui.textEdit_patient_remark.setText(patient_remark)

    # 參考用 FontMetrics and elided text
    def _set_patient_remark(self):
        patient_remark = string_utils.get_str(self.patient_record["Remark"], "utf8")
        patient_remark = string_utils.replace_ascii_char(["\n"], patient_remark)
        if patient_remark == "":
            self.ui.label_patient_remark.setText("")
            return

        patient_remark = f"病患備註: {patient_remark}"
        metrics = QtGui.QFontMetrics(self.font())
        width = 290
        elided = metrics.elidedText(patient_remark, QtCore.Qt.ElideRight, width)
        self.ui.label_patient_remark.setText(elided)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def record_modified(self):
        modified = False
        try:
            if (
                self.ui.textEdit_symptom.document().isModified()
                or self.ui.textEdit_tongue.document().isModified()
                or self.ui.textEdit_pulse.document().isModified()
                or self.ui.textEdit_remark.document().isModified()
                or self.ui.textEdit_patient_remark.document().isModified()
                or self.ui.lineEdit_disease_code1.isModified()
                or self.ui.lineEdit_disease_code2.isModified()
                or self.ui.lineEdit_disease_code3.isModified()
                or self.ui.lineEdit_disease_code4.isModified()
                or self.ui.lineEdit_distinguish.isModified()
                or self.ui.lineEdit_cure.isModified()
            ):
                modified = True
        except AttributeError:
            pass

        return modified

    def _tool_button_dictionary_clicked(self):
        sender_name = self.sender().objectName()
        tool_button_dict = {
            "toolButton_symptom": "主訴",
            "toolButton_symptom_kt": "國泰主訴",
            "toolButton_tongue": "舌診",
            "toolButton_pulse": "脈象",
            "toolButton_remark": "備註",
            "toolButton_disease1": "病名1",
            "toolButton_disease2": "病名2",
            "toolButton_disease3": "病名3",
            "toolButton_disease4": "病名4",
            "toolButton_distincts": "辨證",
            "toolButton_cure": "治則",
            "pushButton_symptom": "主訴",
            "pushButton_tongue": "舌診",
            "pushButton_pulse": "脈象",
            "pushButton_remark": "備註",
            "pushButton_disease1": "病名1",
            "pushButton_disease2": "病名2",
            "pushButton_disease3": "病名3",
            "pushButton_disease4": "病名4",
            "pushButton_distincts": "辨證",
            "pushButton_cure": "治則",
        }

        self.open_dictionary(None, tool_button_dict[sender_name])
        if not self.is_doctor_done():  # 病歷登錄要自動存檔
            self.update_diagnosis_data()

    def open_dictionary(self, medicine_set, dialog_type=None):
        if not dialog_type:
            if self.ui.textEdit_symptom.hasFocus():
                dialog_type = "主訴"
            elif self.ui.textEdit_tongue.hasFocus():
                dialog_type = "舌診"
            elif self.ui.textEdit_pulse.hasFocus():
                dialog_type = "脈象"
            elif self.ui.textEdit_remark.hasFocus():
                dialog_type = "備註"
            elif self.ui.lineEdit_distinguish.hasFocus():
                dialog_type = "辨證"
            elif self.ui.lineEdit_cure.hasFocus():
                dialog_type = "治則"
            elif self.ui.lineEdit_disease_code1.hasFocus():
                dialog_type = "病名1"
            elif self.ui.lineEdit_disease_code2.hasFocus():
                dialog_type = "病名2"
            elif self.ui.lineEdit_disease_code3.hasFocus():
                dialog_type = "病名3"
            elif self.ui.lineEdit_disease_code4.hasFocus():
                dialog_type = "病名4"
            else:
                for i in range(len(self.tab_list)):
                    if (
                        self.tab_list[i] is not None
                        and self.tab_list[i].ui.tableWidget_prescript.hasFocus()
                    ):
                        if i == 0:
                            dialog_type = "健保處方"
                        else:
                            dialog_type = "自費處方"

                        medicine_set = i + 1
                    elif (
                        self.tab_list[0] is not None
                        and self.tab_list[0].ui.tableWidget_treat.hasFocus()
                    ):
                        dialog_type = "健保處置"
                        medicine_set = 1

        if dialog_type is None:
            return

        text_edit = {
            "主訴": self.ui.textEdit_symptom,
            "國泰主訴": self.ui.textEdit_symptom,
            "舌診": self.ui.textEdit_tongue,
            "脈象": self.ui.textEdit_pulse,
            "備註": self.ui.textEdit_remark,
            "辨證": self.ui.lineEdit_distinguish,
            "治則": self.ui.lineEdit_cure,
            "病名1": self.ui.lineEdit_disease_code1,
            "病名2": self.ui.lineEdit_disease_code2,
            "病名3": self.ui.lineEdit_disease_code3,
            "病名4": self.ui.lineEdit_disease_code4,
        }
        dialog = None
        if dialog_type in ["主訴", "舌診", "脈象", "備註"]:
            dialog = dialog_utils.get_dialog_inquiry(
                self,
                self.database,
                self.system_settings,
                dialog_type,
                text_edit[dialog_type],
            )
        elif dialog_type in ["國泰主訴"]:
            dialog = dialog_utils.get_dialog_symptom_kt(
                self,
                self.database,
                self.system_settings,
                text_edit[dialog_type],
                text_edit["舌診"],
            )
        elif dialog_type in ["辨證"]:
            dialog = dialog_utils.get_dialog_diagnosis(
                self,
                self.database,
                self.system_settings,
                dialog_type,
                text_edit[dialog_type],
                text_edit["治則"],
            )
        elif dialog_type in ["治則"]:
            dialog = dialog_utils.get_dialog_diagnosis(
                self,
                self.database,
                self.system_settings,
                dialog_type,
                text_edit[dialog_type],
                None,
            )
        elif dialog_type in ["病名1", "病名2", "病名3", "病名4"]:
            line_edit = self.ui.lineEdit_disease_name1

            if dialog_type == "病名1":
                line_edit = self.ui.lineEdit_disease_name1
            elif dialog_type == "病名2":
                line_edit = self.ui.lineEdit_disease_name2
            elif dialog_type == "病名3":
                line_edit = self.ui.lineEdit_disease_name3
            elif dialog_type == "病名4":
                line_edit = self.ui.lineEdit_disease_name4

            if self.tab_registration is None:
                line_special_code = None
            else:
                line_special_code = self.tab_registration.ui.lineEdit_special_code

            disease_type = "常用病名"
            if self.tab_list[0] is not None:
                treatment = string_utils.xstr(
                    self.tab_list[0].comboBox_treatment.currentText()
                )
            else:
                treatment = ""

            if dialog_type == "病名1" and treatment != "":
                disease_type = treatment

            if (
                dialog_type == "病名2"
                and self.sender().objectName() == "toolButton_disease2"
            ):
                dialog = dialog_utils.get_dialog_external_causes(
                    self,
                    self.database,
                    self.system_settings,
                    self.case_key,
                    self.ui.lineEdit_disease_code2,
                    self.ui.lineEdit_disease_name2,
                )

            else:
                dialog = dialog_utils.get_dialog_disease(
                    self,
                    self.database,
                    self.system_settings,
                    self.case_key,
                    text_edit[dialog_type],
                    line_edit,
                    line_special_code,
                    self.ui.lineEdit_disease_code2,
                    self.ui.lineEdit_disease_name2,
                    disease_type,
                )
        elif dialog_type in ["健保處方", "自費處方"] and medicine_set is not None:
            if dialog_type == "健保處方":
                dict_type = "健保藥品"
            else:
                dict_type = "藥品"

            dialog = dialog_utils.get_dialog_medicine(
                self,
                self.database,
                self.system_settings,
                self.tab_list[medicine_set - 1].tableWidget_prescript,
                medicine_set,
                dict_type,
            )
        elif (
            dialog_type in ["健保處置", "自費處置", "健保針灸處置", "健保傷科處置"]
            and medicine_set is not None
        ):
            if dialog_type in ["健保處置", "自費處置"]:
                treat = "處置"
            else:
                treat = dialog_type

            dialog = dialog_utils.get_dialog_medicine(
                self,
                self.database,
                self.system_settings,
                self.tab_list[medicine_set - 1].tableWidget_prescript,
                medicine_set,
                treat,
            )

        if dialog is None:
            return

        dialog.exec_()
        dialog.deleteLater()

    def open_dict_examination(self, medicine_set):
        dialog = dialog_utils.get_dialog_examination(
            self,
            self.database,
            self.system_settings,
            self.tab_list[medicine_set - 1].tableWidget_prescript,
            medicine_set,
        )
        dialog.exec_()
        dialog.deleteLater()

    # 顯示病歷
    def _set_medical_record(self, row):
        if self.case_key is None:
            return

        self._set_diagnostic(row)
        self._set_reference(row)
        self._set_injury(row)

    def _set_diagnostic(self, row):
        self.ui.textEdit_symptom.setText(string_utils.get_str(row["Symptom"], "utf8"))
        self.ui.textEdit_tongue.setText(string_utils.get_str(row["Tongue"], "utf8"))
        self.ui.textEdit_pulse.setText(string_utils.get_str(row["Pulse"], "utf8"))
        self.ui.textEdit_remark.setText(string_utils.get_str(row["Remark"], "utf8"))

        disease_field_list = [
            [self.ui.lineEdit_disease_code1, self.ui.lineEdit_disease_name1],
            [self.ui.lineEdit_disease_code2, self.ui.lineEdit_disease_name2],
            [self.ui.lineEdit_disease_code3, self.ui.lineEdit_disease_name3],
            [self.ui.lineEdit_disease_code4, self.ui.lineEdit_disease_name4],
        ]

        for i, disease_field in enumerate(disease_field_list):
            try:
                disease_code = string_utils.get_str(row[f"DiseaseCode{i + 1}"], "utf8")
            except Exception:
                continue

            disease_name = string_utils.get_str(row[f"DiseaseName{i + 1}"], "utf8")

            disease_field[0].blockSignals(True)  # 新增
            disease_field[0].setText(disease_code)
            disease_field[0].blockSignals(False)  # 新增

            disease_field[1].setText(disease_name)
            case_utils.set_disease_tool_tip(
                self.database,
                disease_field[0],
                disease_field[1],
                self.parent.complicated_treat_list,
            )

        self.ui.lineEdit_distinguish.setText(
            string_utils.get_str(row["Distincts"], "utf8")
        )
        self.ui.lineEdit_cure.setText(string_utils.get_str(row["Cure"], "utf8"))
        # self.disease_code_changed()
        self.rearrange_disease_codes()

    def _set_reference(self, row):
        if row["Reference"] == "True":
            self.ui.checkBox_reference.setChecked(True)
        else:
            self.ui.checkBox_reference.setChecked(False)

    def _set_injury(self, row):
        if row["Injury"] == "主訴職災":
            self.ui.checkBox_complaint_injury.setChecked(True)
            self.ui.checkBox_complaint_injury.setStyleSheet(
                "color: red; font-weight: bold"
            )
        else:
            self.ui.checkBox_complaint_injury.setChecked(False)
            self.ui.checkBox_complaint_injury.setStyleSheet(None)

    # 顯示處方
    def _set_prescripts(self):
        if self.case_key is None:  # 參考病歷
            self.add_prescript_tab(1)
            self.add_prescript_tab(2)
            return

        if self.ins_type == "健保":  # 健保一定要開啟
            self.add_prescript_tab(1)
            if (
                self.system_settings.field("健保自費分開") == "Y"
                or self.call_from == "病歷查詢健保病歷"
            ):
                return

        self._set_self_prescripts()

    def _set_self_prescripts(self):
        # 讀取自費資料
        sql = f"""
            SELECT MedicineSet FROM prescript
            WHERE
                CaseKey = {self.case_key} AND
                MedicineSet >= 2 AND
                MedicineSet != 11
            GROUP BY MedicineSet
            ORDER BY MedicineSet
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:  # 沒有自費處方
            default_tab = 1  # 預設開啟自費1

            if not self.is_doctor_done():  # 候診病歷要開啟預設空白自費頁
                custom_tab = self.system_settings.field("預設空白自費頁")
                if custom_tab is not None:
                    default_tab = custom_tab

            page_count = number_utils.get_integer(default_tab) + 1  # 自費編號從2開始

            for i in range(2, page_count + 1):
                rows.append({"MedicineSet": i})

        for row in rows:
            self.add_prescript_tab(row["MedicineSet"])

    def _set_fees(self):
        if self.call_from == "醫師看診作業":
            self._read_recently_history()
            self._read_exam_precheck()
            self._read_fees()
        else:
            self._read_fees()
            self._read_recently_history()
            self._read_exam_precheck()

        if self.system_settings.field("顯示備忘錄") == "Y":
            try:
                self._add_tab_memo()
            except Exception:
                pass

    # 設定雜項 (這個要在 _set_fees 之後才能執行)
    def _set_misc(self):
        if self.call_from != "醫師看診作業":
            return

        if self.system_settings.field("自動顯示過去病歷") == "Y":
            self._open_past_history()

        if self.ins_type == "健保":
            self._medical_record_precheck()

    def _check_infectious_date(self):
        if (
            string_utils.xstr(self.medical_record["InsType"]) != "健保"
            or string_utils.xstr(self.medical_record["Share"])
            not in nhi_utils.INFECTIOUS_TYPE
            or string_utils.xstr(self.medical_record["Injury"])
            not in nhi_utils.INFECTIOUS_TYPE
        ):
            return

        infectious_date = case_utils.get_case_extend(
            self.database, self.case_key, "確診日期"
        )
        if infectious_date is None:
            infectious_date = date_utils.get_dialog_date(
                self,
                self.database,
                self.system_settings,
                title="請選擇隔離通知書隔離日期或PCR陽性採檢日期",
                current_date=self.medical_record["CaseDate"].date(),
                date_type="date",
                call_from=self.program_name,
            )
            if infectious_date is not None:
                case_utils.set_case_extend(
                    self.database,
                    self.case_key,
                    "確診日期",
                    infectious_date.toString("yyyy-MM-dd 00:00:00"),
                )

    def _get_new_tab(self, max_medicine_set):
        tab_name = None
        medicine_set = 2
        for i in range(
            2, max_medicine_set + 1
        ):  # MedicineSet2 ~ MedicineSet7  最多六帖藥
            tab_name = f"自費{medicine_set - 1}"
            if self._tab_exists(tab_name):
                medicine_set += 1
                if medicine_set > max_medicine_set:
                    return False, None
                else:
                    continue
            else:
                break

        return tab_name, medicine_set

    def add_additional_prescript(self):
        pass

    # 新增加強照護處方
    def add_care_prescript(self):
        medicine_set = 11
        self.tab_list[10] = module_utils.get_ins_care_record(
            self, self.database, self.system_settings, self.case_key, medicine_set
        )
        # self.tab_list[10].refresh_prescript()
        self.ui.tabWidget_prescript.addTab(self.tab_list[10], "加強照護")
        self.ui.tabWidget_prescript.tabBar().setTabButton(
            self.ui.tabWidget_prescript.indexOf(self.tab_list[10]),
            QtWidgets.QTabBar.RightSide,
            None,
        )

    # 新增自費處方
    def add_prescript_tab(self, medicine_set=None):
        if medicine_set in (1, 11):  # 健保處方頁  1=健保 11=加強照護,
            self.tab_list[0] = module_utils.get_ins_prescript_record(
                self,
                self.database,
                self.system_settings,
                self.case_key,
                1,
                self.call_from,
            )
            self.ui.tabWidget_prescript.addTab(self.tab_list[0], "健保")
            self.ui.tabWidget_prescript.tabBar().setTabButton(
                self.ui.tabWidget_prescript.indexOf(self.tab_list[0]),
                QtWidgets.QTabBar.RightSide,
                None,
            )

            if (
                self.medical_record is not None
                and self.medical_record["TreatType"]
                in nhi_utils.IMPROVE_CARE_TREAT + nhi_utils.CHILD_CARE_TREAT
            ):
                self.add_care_prescript()

            return

        set_current_tab = False
        clear_prescript = False
        if not medicine_set:  # 新增自費處方按鈕
            medicine_set = 2
            set_current_tab = True
            clear_prescript = True

        tab_name = f"自費{medicine_set - 1}"
        if self._tab_exists(tab_name):
            tab_name, medicine_set = self._get_new_tab(self.max_tab)

        if not tab_name:
            return

        current_tab = None
        new_tab = module_utils.get_self_prescript_record(
            self,
            self.database,
            self.system_settings,
            self.case_key,
            medicine_set,
            self.call_from,
        )

        for i in range(1, self.max_tab):
            if tab_name == f"自費{i}":
                self.tab_list[i] = new_tab
                self.tab_list[i].append_null_medicine()
                current_tab = self.tab_list[i]

        if current_tab is None:
            return

        self.ui.tabWidget_prescript.addTab(current_tab, tab_name)
        current_tab.set_tab_icon()

        if clear_prescript:
            current_tab.tableWidget_prescript.setRowCount(0)
            current_tab.append_null_medicine()

        if set_current_tab:
            self.ui.tabWidget_prescript.setCurrentWidget(current_tab)

        return current_tab

    # 檢查是否開啟tab
    def _tab_exists(self, tab_text):
        if self.ui.tabWidget_prescript.count() <= 0:
            return False

        for i in range(self.ui.tabWidget_prescript.count()):
            if self.ui.tabWidget_prescript.tabText(i) == tab_text:
                return True

        return False

    def _read_recently_history(self):
        if self.patient_record is None:
            return

        self.tab_medical_record_recently_history = (
            module_utils.get_medical_record_recently_history(
                self,
                self.database,
                self.system_settings,
                self.case_key,
                self.patient_key,
                self.call_from,
            )
        )
        self.ui.tabWidget_past_record.addTab(
            self.tab_medical_record_recently_history, "最近病歷"
        )

    def _add_tab_memo(self):
        self.tab_memo = module_utils.get_medical_record_memo(
            self, self.database, self.system_settings, self.case_key, self.patient_key
        )
        self.ui.tabWidget_past_record.addTab(self.tab_memo, "備忘錄")

    def _read_exam_precheck(self):
        if self.case_key is None:
            return

        sql = f"""
            SELECT * FROM case_extension
            WHERE
                CaseKey = {self.case_key} AND
                ExtensionType = "診前檢查"
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.tab_exam_precheck = dialog_utils.get_dialog_exam_precheck(
            self, self.database, self.system_settings, self.case_key, "病歷資料"
        )
        self.ui.tabWidget_past_record.addTab(self.tab_exam_precheck, "診前檢查")

    def _read_fees(self):
        tab_name = "批價明細"
        self.tab_medical_record_fees = module_utils.get_medical_record_fees(
            self,
            self.database,
            self.system_settings,
            self.medical_record,
            self.case_key,
            self.patient_key,
            self.call_from,
        )
        self.ui.tabWidget_past_record.addTab(self.tab_medical_record_fees, tab_name)
        tab_index = self._get_tab_index(tab_name)
        self.ui.tabWidget_past_record.tabBar().setTabTextColor(
            tab_index, QtGui.QColor("darkCyan")
        )

    def _get_tab_index(self, tab_name):
        current_index = 0
        for i in range(self.ui.tabWidget_past_record.count()):
            if self.ui.tabWidget_past_record.tabText(i) == tab_name:
                current_index = i
                break

        return current_index

    # 新增自費病歷
    def save_new_self_medical_record(self):
        self.record_saved = True
        self._set_doctor()

        case_key = self._insert_medical_record()
        self.update_diagnosis_data(case_key)
        self.tab_registration.case_key = case_key
        self.tab_registration.data_changed = True
        self.tab_registration.save_record()
        self.tab_medical_record_fees.save_record(case_key)

        self._set_doctor_done(case_key)
        self._set_charge_done(case_key)

        self._insert_wait_record(case_key)
        self._set_wait_done(case_key)

        for medicine_set, tab_prescript in zip(
            range(1, self.max_tab + 1), self.tab_list
        ):
            if tab_prescript is not None:
                try:
                    tab_prescript.case_key = case_key
                except RuntimeError:  # 關閉處方頁, 刪除整個處方
                    self.remove_prescript(medicine_set)
            else:
                self.remove_prescript(medicine_set)

        if not self.save_prescript():
            return False

        try:
            menu_item = self.sender().text()
        except AttributeError:
            menu_item = ""

        if "存檔列印" in menu_item:
            self._print(case_key)
        elif menu_item == "存檔後選擇列印處方":
            self._print_prescript(case_key, "選擇列印")
        elif menu_item == "存檔後選擇列印費用收據":
            self._print_receipt(case_key, "選擇列印")
        elif menu_item == "存檔後選擇列印其他收據":
            self._print_misc(case_key, "選擇列印")
            self._print_misc2(case_key, "選擇列印")
            self._print_misc3(case_key, "選擇列印")

        self._send_socket_data()

        self.close_all()
        self.close_tab()

    # 新增自費病歷
    def _insert_medical_record(self):
        fields = [
            "PatientKey",
            "CaseDate",
        ]

        data = [
            self.patient_key,
            self.tab_registration.lineEdit_case_date.text(),
        ]
        case_key = self.database.insert_record("cases", fields, data)

        return case_key

    # 新增自費病歷候診名單
    def _insert_wait_record(self, case_key):
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
            "Period",
            "Room",
            "RegistNo",
            "Doctor",
            "Massager",
        ]
        data = [
            case_key,
            self.tab_registration.lineEdit_case_date.text(),
            self.patient_key,
            self.tab_registration.lineEdit_name.text(),
            self.tab_registration.comboBox_visit.currentText(),
            self.tab_registration.comboBox_reg_type.currentText(),
            self.tab_registration.comboBox_treat_type.currentText(),
            self.tab_registration.comboBox_share_type.currentText(),
            self.tab_registration.comboBox_ins_type.currentText(),
            self.tab_registration.comboBox_period.currentText(),
            self.tab_registration.comboBox_room.currentText(),
            self.tab_registration.lineEdit_regist_no.text(),
            self.tab_registration.comboBox_doctor.currentText(),
            self.tab_registration.comboBox_massager.currentText(),
        ]
        self.database.insert_record("wait", fields, data)

    def _get_disease_name(self, icd_code):
        sql = "SELECT ChineseName FROM icd10 WHERE ICDCode = %s LIMIT 1"
        rows = self.database.select_record(sql, (icd_code,))

        if len(rows) <= 0:
            return None
        else:
            return string_utils.xstr(rows[0]["ChineseName"])

    def _check_disease_name(self):
        disease_code1 = self.ui.lineEdit_disease_code1.text()
        disease_name1 = self.ui.lineEdit_disease_name1.text()
        disease_code2 = self.ui.lineEdit_disease_code2.text()
        disease_name2 = self.ui.lineEdit_disease_name2.text()
        disease_code3 = self.ui.lineEdit_disease_code3.text()
        disease_name3 = self.ui.lineEdit_disease_name3.text()
        disease_code4 = self.ui.lineEdit_disease_code4.text()
        disease_name4 = self.ui.lineEdit_disease_name4.text()

        if disease_code1 != "" and disease_name1 == "":
            disease_name1 = self._get_disease_name(disease_code1)
            if disease_name1 not in [None, ""]:
                self.ui.lineEdit_disease_name1.setText(disease_name1)

        if disease_code2 != "" and disease_name2 == "":
            disease_name2 = self._get_disease_name(disease_code2)
            if disease_name2 not in [None, ""]:
                self.ui.lineEdit_disease_name2.setText(disease_name2)

        if disease_code3 != "" and disease_name3 == "":
            disease_name3 = self._get_disease_name(disease_code3)
            if disease_name3 not in [None, ""]:
                self.ui.lineEdit_disease_name3.setText(disease_name3)

        if disease_code4 != "" and disease_name4 == "":
            disease_name4 = self._get_disease_name(disease_code4)
            if disease_name4 not in [None, ""]:
                self.ui.lineEdit_disease_name4.setText(disease_name4)

    # 病歷存檔
    def save_medical_record(self, print_form=False, force_save=False):
        if self.system_settings.field("不要自動切換輸入法") == "Y":
            pass
        else:
            system_utils.set_keyboard_layout("中文")

        self._check_disease_name()

        # if self.call_from == '醫師看診作業' and self.system_settings.field('手動批價') != 'Y':
        #     self.calculate_self_fees()  # 自費重新批價 2023-05-09 龍潭懷恩堂  # 2023-05-25 取消，因為會讓手動批價失效

        if self.call_from == "參考病歷":
            self.save_reference_medical_record()
            return

        if self.call_from in ["新增自費病歷", "加購自費病歷"]:
            self.save_new_self_medical_record()
            return

        if self.tab_past_exists("備忘錄"):
            self.tab_memo.save_memo()

        if self.is_doctor_done():
            backup_date = self.medical_record["TimeStamp"]
            try:
                case_utils.backup_medical_record(
                    self.database,
                    self.case_key,
                    "編輯備份",
                    backup_date,
                    self.user_name,
                )  # 編輯前備份資料
            except Exception:
                pass

        if (
            self.ins_type == "健保"
            and self.tab_registration.comboBox_ins_type.currentText() == "健保"
        ):
            treat_type = self.tab_registration.ui.comboBox_treat_type.currentText()
            card = self.tab_registration.ui.comboBox_card.currentText()
            course = number_utils.get_integer(
                self.tab_registration.ui.comboBox_course.currentText()
            )
            special_code = self.tab_registration.ui.lineEdit_special_code.text()
            disease_code1 = string_utils.xstr(self.ui.lineEdit_disease_code1.text())
            disease_code2 = string_utils.xstr(self.ui.lineEdit_disease_code2.text())
            disease_code3 = string_utils.xstr(self.ui.lineEdit_disease_code3.text())
            disease_code4 = string_utils.xstr(self.ui.lineEdit_disease_code4.text())
            treatment = string_utils.xstr(
                self.tab_list[0].comboBox_treatment.currentText()
            )
            second_treatment = string_utils.xstr(
                self.tab_list[0].comboBox_second_treatment.currentText()
            )
            pres_days = number_utils.get_integer(
                self.tab_list[0].ui.comboBox_pres_days.currentText()
            )
            packages = number_utils.get_integer(
                self.tab_list[0].ui.comboBox_package.currentText()
            )
            instruction = self.tab_list[0].ui.comboBox_instruction.currentText()
            symptom = self.ui.textEdit_symptom.toPlainText()
            tongue = self.ui.textEdit_tongue.toPlainText()
            pulse = self.ui.textEdit_pulse.toPlainText()
            distinguish = string_utils.xstr(self.ui.lineEdit_distinguish.text())[:40]
            cure = string_utils.xstr(self.ui.lineEdit_cure.text())[:40]
            ins_apply_fee = charge_utils.get_table_widget_item_fee(
                self.tab_medical_record_fees.ui.tableWidget_ins_fees,
                self.tab_medical_record_fees.INS_COLUMN["InsApplyFee"],
                0,
            )
            deposit_fee = charge_utils.get_table_widget_item_fee(
                self.tab_medical_record_fees.ui.tableWidget_cash_fees,
                self.tab_medical_record_fees.SELF_COLUMN["DepositFee"],
                0,
            )

            table_widget_ins_prescript = self.tab_list[0].ui.tableWidget_prescript
            table_widget_ins_treat = self.tab_list[0].ui.tableWidget_treat

            if self.tab_list[10] is not None:
                table_widget_ins_care = self.tab_list[10].ui.tableWidget_prescript
            else:
                table_widget_ins_care = None

            no_pharmacy = "N"
            try:
                if self.tab_list[0] is not None:
                    if self.tab_list[0].ui.checkBox_no_pharmacy.isChecked():
                        no_pharmacy = "Y"
                    else:
                        no_pharmacy = "N"
            except Exception:
                pass

            record_check = module_utils.get_medical_record_check(
                self,
                database=self.database,
                system_settings=self.system_settings,
                call_from=self.call_from,
                medical_record=self.medical_record,
                patient_record=self.patient_record,
                treat_type=treat_type,
                card=card,
                course=course,
                disease_code1=disease_code1,
                disease_code2=disease_code2,
                disease_code3=disease_code3,
                disease_code4=disease_code4,
                special_code=special_code,
                treatment=treatment,
                second_treatment=second_treatment,
                pres_days=pres_days,
                packages=packages,
                instruction=instruction,
                table_widget_ins_prescript=table_widget_ins_prescript,
                table_widget_ins_treat=table_widget_ins_treat,
                table_widget_ins_care=table_widget_ins_care,
                symptom=symptom,
                tongue=tongue,
                pulse=pulse,
                distinguish=distinguish,
                cure=cure,
                integrate_care=self.check_box_integrate_care.isChecked(),
                no_pharmacy=no_pharmacy,
                ins_apply_fee=ins_apply_fee,
                deposit_fee=deposit_fee,
            )

            check_ok = record_check.check_medical_record()
            record_check.deleteLater()

            if force_save:
                check_ok = True

            if not check_ok:
                return

        if not self._check_self_pres_days():
            return

        # if self.system_settings.field("自費開藥劑量必須大於0") == 'Y':
        #     if not self._check_self_dosage():
        #         return

        if not self._check_fees():  # 檢查批價
            return

        self.record_saved = True
        self._set_necessary_fields()

        if self.call_from == "醫師看診作業":
            doctor_done = True
        else:
            doctor_done = False

        if force_save:
            check_prescript = False
        else:
            check_prescript = True

        if not self.update_medical_record(
            set_doctor_done=doctor_done, check_prescript=check_prescript
        ):
            return

        try:
            self.update_patient_record()
        except Exception:
            pass

        if (
            self.ins_type == "自費"
            and string_utils.xstr(self.medical_record["TreatType"]) != "自購"
        ):
            self._set_self_treat_type()

        card = string_utils.xstr(self.medical_record["Card"])
        xcard = string_utils.xstr(self.medical_record["XCard"])
        ic_card_type = case_utils.get_ic_card_type(self.database, self.case_key)

        if (
            (self.ins_type == "健保")
            and (self.call_from == "醫師看診作業")
            and (self.system_settings.field("產生醫令簽章位置") == "診療")
            and (self.system_settings.field("使用讀卡機") == "Y")
            and (card[:4] not in nhi_utils.ABNORMAL_CARD)
            and (xcard[:4] not in nhi_utils.ABNORMAL_CARD)
            and (card != "欠卡")
        ):
            if (
                ic_card_type == "虛擬健保卡"
                and self.system_settings.field("虛擬健保卡統一在掛號作業") == "Y"
            ):
                pass
            else:
                if ic_card_type == "虛擬健保卡":
                    qrcode = None
                    vhc_req_code = vhc_utils.get_vhc_req_code_from_wait(
                        self.database, self.wait_key
                    )
                    if vhc_req_code is not None:
                        patient_id = string_utils.xstr(self.patient_record["ID"])
                        ic_card = class_utils.get_cshis(
                            self, self.database, self.system_settings
                        )
                        req_code = ic_card.request_token(patient_id)

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
                        msg_box.addButton(
                            QPushButton("病患已經授權"), QMessageBox.YesRole
                        )
                        get_response = msg_box.exec_()
                        if not get_response:
                            return

                        ic_card = class_utils.get_cshis(
                            self, self.database, self.system_settings
                        )
                        qrcode = ic_card.get_response_token(req_code)
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
                    ic_card = class_utils.get_cshis(
                        self, self.database, self.system_settings
                    )

                while True:
                    if ic_card.insert_correct_ic_card(self.patient_key):
                        if (
                            card == "IC"
                            or self.system_settings.field("產生安全簽章位置") == "診療"
                            and card != "欠卡"
                            and card[:4] not in nhi_utils.ABNORMAL_CARD
                        ):
                            if not self._write_ic_card(ic_card):
                                break

                        ic_card.write_ic_medical_record(
                            self.case_key, cshis_utils.NORMAL_CARD
                        )
                        break

                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Warning)
                    msg_box.setWindowTitle("繼續存檔")
                    msg_box.setText(
                        "<font size='4' color='red'><b>讀卡機作業失敗, 是否繼續存檔?</b></font>"
                    )
                    msg_box.setInformativeText(
                        "注意！繼續存檔, 不會影響當日IC卡資料上傳!"
                    )
                    msg_box.addButton(QPushButton("再試一次寫卡"), QMessageBox.NoRole)
                    msg_box.addButton(
                        QPushButton("放棄寫卡, 繼續存檔"), QMessageBox.YesRole
                    )
                    msg_box.addButton(
                        QPushButton("取消存檔, 繼續編輯"), QMessageBox.RejectRole
                    )
                    continue_save = msg_box.exec_()
                    if continue_save == 2:  # 取消存檔，繼續編輯
                        self.update_medical_record(set_doctor_done=False)
                        return
                    elif continue_save == 1:  # 放棄寫卡，繼續存檔
                        break
        try:
            menu_item = self.sender().text()
        except AttributeError:
            menu_item = ""

        self._set_drug_no()
        if "存檔列印" in menu_item or print_form:
            self._print(self.case_key)
            if self.system_settings.field("電子處方箋路徑") not in ["", None]:
                prescript_utils.save_electrical_prescript(
                    self.database, self.system_settings, self.case_key
                )
        elif menu_item == "存檔後選擇列印處方":
            self._print_prescript(self.case_key, "選擇列印")
        elif menu_item == "存檔後選擇列印費用收據":
            self._print_receipt(self.case_key, "選擇列印")
        elif menu_item == "存檔後選擇列印其他收據":
            self._print_misc(self.case_key, "選擇列印")
            self._print_misc2(self.case_key, "選擇列印")
            self._print_misc3(self.case_key, "選擇列印")

        if "存檔列印並匯出PDF" in menu_item:
            self._print_receipt(self.case_key, "pdf")

        self._write_log()

        self.close_all()
        self.close_tab()

    def _write_ic_card(self, ic_card):
        available_date, available_count = ic_card.get_card_status()
        if available_count is None:
            return False

        now = datetime.datetime.now().strftime("%Y-%m-%d")
        if available_count <= 0 or available_date < now:
            ic_card.update_hc(False)

        ic_card_ok = ic_card.write_ic_card(
            "掛號寫卡",
            self.patient_key,
            number_utils.get_integer(
                self.tab_registration.ui.comboBox_course.currentText()
            ),
            self.tab_registration.ui.comboBox_share_type.currentText(),
            cshis_utils.NORMAL_CARD,
        )
        if not ic_card_ok:
            return False

        card = string_utils.xstr(self.medical_record["Card"])
        if card == "IC":
            card = string_utils.xstr(
                ic_card_ok.treat_data["seq_number"]
            )  # 有產生卡號才更新

        security = case_utils.treat_data_to_xml(ic_card_ok.treat_data)
        security = case_utils.update_xml_doc(security, "upload_type", "1")
        security = case_utils.update_xml_doc(
            security, "treat_after_check", cshis_utils.NORMAL_CARD
        )

        fields = ["Card", "Security"]
        data = [card, security]
        self.database.update_record("cases", fields, "CaseKey", self.case_key, data)

        return True

    def _check_self_pres_days(self):
        ins_pres_days = 0
        for tab_index in range(self.ui.tabWidget_prescript.count()):
            current_tab = self.ui.tabWidget_prescript.widget(tab_index)
            tab_name = self.ui.tabWidget_prescript.tabText(tab_index)
            if tab_name == "健保":
                ins_pres_days = number_utils.get_integer(
                    current_tab.comboBox_pres_days.currentText()
                )
                break

        for tab_index in range(self.ui.tabWidget_prescript.count()):
            current_tab = self.ui.tabWidget_prescript.widget(tab_index)
            tab_name = self.ui.tabWidget_prescript.tabText(tab_index)
            if tab_name in ["健保", "加強照護"]:
                continue

            try:
                self_pres_days = number_utils.get_integer(
                    current_tab.comboBox_pres_days.currentText()
                )
            except AttributeError:
                continue

            table_widget_prescript = current_tab.tableWidget_prescript
            for row_no in range(table_widget_prescript.rowCount()):
                medicine_name = table_widget_prescript.item(
                    row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
                )
                if medicine_name is None:
                    continue

                medicine_name = medicine_name.text()
                if (
                    self.ins_type == "健保"
                    and "混合(科藥+自費藥" in medicine_name
                    and self_pres_days != ins_pres_days
                ):
                    system_utils.show_message_box(
                        QMessageBox.Critical,
                        "給藥天數錯誤",
                        f"""
                            <font size="5" color="red">
                              <b>
                               {tab_name}(混合科藥+自費藥)給藥天數與健保不符! 請更正.
                               </b>
                            </font>
                        """,
                        f"健保給藥天數為{ins_pres_days}天, {tab_name}給藥天數為{self_pres_days}天.",
                    )
                    return False

        return True

    # 檢查自費劑量空白 (無單價不檢查) 2019.12.10
    def _check_self_dosage(self):
        for tab_index in range(self.ui.tabWidget_prescript.count()):
            current_tab = self.ui.tabWidget_prescript.widget(tab_index)
            tab_name = self.ui.tabWidget_prescript.tabText(tab_index)
            if tab_name in ["健保", "加強照護"]:
                continue

            try:
                if not current_tab.check_ins_drug_single_day_price():
                    return False
            except Exception:
                return True

            table_widget_prescript = current_tab.tableWidget_prescript
            for row_no in range(table_widget_prescript.rowCount()):
                medicine_name = table_widget_prescript.item(
                    row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
                )
                if medicine_name is None:
                    continue

                medicine_name = medicine_name.text()
                if medicine_name == "":
                    continue

                dosage = table_widget_prescript.item(
                    row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
                )
                if dosage is not None and dosage.text() != "":
                    continue

                price = table_widget_prescript.item(
                    row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Price"]
                )
                if price is None or number_utils.get_float(price.text()) == 0:
                    continue

                unit = table_widget_prescript.item(
                    row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Unit"]
                )
                if unit is not None and unit.text() == "":
                    continue

                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "劑量空白",
                    f"""
                        <font size="5" color="red">
                          <b>
                           {tab_name}: {medicine_name} 劑量空白! 請更正.
                           </b>
                        </font>
                    """,
                    "請輸入劑量.",
                )
                return False

        return True

    def _check_fees(self):
        # if self.call_from == '醫師看診作業':
        #     return True

        if self.system_settings.field("手動批價") == "Y":
            return True

        if self.call_from == "病歷查詢健保病歷":
            return True

        old_total_fee = number_utils.get_integer(
            charge_utils.get_table_widget_item_fee(
                self.tab_medical_record_fees.ui.tableWidget_cash_fees,
                self.tab_medical_record_fees.SELF_COLUMN["TotalFee"],
                0,
            )
        )

        new_total_fee = self.tab_medical_record_fees.get_total_fee()
        if new_total_fee != old_total_fee:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("批價變更")
            msg_box.setText(
                f"""
                    <font size="5" color="red">
                      <b>
                       自費批價金額與電腦計算出的批價金額不符! <br>
                       自費批價金額為 ${old_total_fee}, <br>
                       電腦自動批價金額為 ${new_total_fee}
                       </b>
                    </font>
                """
            )
            msg_box.setInformativeText("請選擇以下的選項.")
            msg_box.addButton(
                QPushButton(f"使用目前的自費金額 ${old_total_fee}"), QMessageBox.NoRole
            )
            msg_box.addButton(
                QPushButton(f"使用電腦自動批價的金額 ${new_total_fee}"),
                QMessageBox.YesRole,
            )
            calculate_fee = msg_box.exec_()
            if calculate_fee:
                self.tab_medical_record_fees.calculate_fees()

        return True

    def _print(self, case_key=None):
        if case_key is None:
            case_key = self.case_key

        print_mode = "系統設定"

        print_order = self.system_settings.field("病歷存檔列印順序")
        if print_order == "列印順序1":
            self._print_prescript(case_key, print_mode)
            self._print_receipt(case_key, print_mode)
            self._print_misc(case_key, print_mode)
            self._print_misc2(case_key, print_mode)
            self._print_misc3(case_key, print_mode)
            self._print_prescript_bag(case_key, print_mode)
        elif print_order == "列印順序2":
            self._print_misc(case_key, print_mode)
            self._print_misc2(case_key, print_mode)
            self._print_misc3(case_key, print_mode)
            self._print_prescript(case_key, print_mode)
            self._print_receipt(case_key, print_mode)
            self._print_prescript_bag(case_key, print_mode)
        elif print_order == "列印順序3":
            self._print_misc(case_key, print_mode)
            self._print_misc2(case_key, print_mode)
            self._print_misc3(case_key, print_mode)
            self._print_receipt(case_key, print_mode)
            self._print_prescript(case_key, print_mode)
            self._print_prescript_bag(case_key, print_mode)
        else:
            self._print_receipt(case_key, print_mode)
            self._print_misc(case_key, print_mode)
            self._print_misc2(case_key, print_mode)
            self._print_misc3(case_key, print_mode)
            self._print_prescript(case_key, print_mode)
            self._print_prescript_bag(case_key, print_mode)

    # 列印處方
    def _print_prescript(self, case_key, print_mode):
        printer_utils.print_prescription_form(
            self, self.database, self.system_settings, case_key, print_mode
        )

    # 列印收據
    def _print_receipt(self, case_key, print_mode):
        printer_utils.print_receipt_form(
            self, self.database, self.system_settings, case_key, print_mode
        )

    # 列印其他收據
    def _print_misc(self, case_key, print_mode):
        printer_utils.print_misc_form(
            self, self.database, self.system_settings, case_key, print_mode
        )

    # 列印其他收據2
    def _print_misc2(self, case_key, print_mode):
        printer_utils.print_misc_form2(
            self, self.database, self.system_settings, case_key, print_mode
        )

    # 列印其他收據3
    def _print_misc3(self, case_key, print_mode):
        printer_utils.print_misc_form3(
            self, self.database, self.system_settings, case_key, print_mode
        )

    # 列印藥袋
    def _print_prescript_bag(self, case_key, print_mode):
        printer_utils.print_prescription_bag_form(
            self, self.database, self.system_settings, case_key, print_mode
        )

    # 設定必要欄位
    def _set_necessary_fields(self):
        if self.call_from == "醫師看診作業":  # 所有病歷都要設定
            self._set_doctor()

        if self.ins_type == "健保":
            self._set_treatment_and_course()

    def _set_self_treat_type(self):
        exclude_list = (
            nhi_utils.HOME_CARE + nhi_utils.TRADITIONAL_TREAT + nhi_utils.PURCHASE
        )
        current_treat_type = self.tab_registration.ui.comboBox_treat_type.currentText()
        if current_treat_type in exclude_list:
            return

        if string_utils.xstr(self.medical_record["TreatType"]) in exclude_list:
            return

        if current_treat_type in nhi_utils.INS_TREAT:
            treat_type = current_treat_type
        else:
            treat_type = "自費"

        self.database.exec_sql(
            "UPDATE cases SET TreatType = %s WHERE CaseKey = %s",
            (treat_type, self.case_key),
        )

    # 設定主治醫師姓名
    def _set_doctor(self):
        current_doctor = self.tab_registration.ui.comboBox_doctor.currentText()
        if current_doctor == "全部醫師":
            self.tab_registration.ui.comboBox_doctor.setCurrentText(self.user_name)
            return

        if current_doctor in ["", None]:
            self.tab_registration.ui.comboBox_doctor.setCurrentText(self.user_name)
        elif current_doctor != self.user_name:
            if self.system_settings.field("病歷存檔檢查醫師姓名") == "Y":
                msg_box = dialog_utils.get_message_box(
                    "醫師姓名不同",
                    QMessageBox.Warning,
                    f"""<font color="red"><b>
                            掛號醫師為 「{current_doctor}」, 與使用者名稱 「{self.user_name}」不符!<br>
                            [確定] 改為「{self.user_name}」醫師<br>
                            [取消] 維持原「{current_doctor}」醫師
                        </b></font>
                    """,
                    "若使用者名稱不對, 請重新登入.",
                )
                change_doctor = msg_box.exec_()
                if change_doctor:
                    self.tab_registration.ui.comboBox_doctor.setCurrentText(
                        self.user_name
                    )
            else:
                self.tab_registration.ui.comboBox_doctor.setCurrentText(self.user_name)

    # 設定就醫類別及療程
    def _set_treatment_and_course(self):
        if self.tab_registration.ui.comboBox_ins_type.currentText() in [
            "自費"
        ]:  # 自費不要變更
            return

        if (
            self.tab_registration.ui.comboBox_treat_type.currentText()
            in nhi_utils.HOME_CARE
        ):  # 居家醫療不要變更
            self.tab_registration.ui.comboBox_course.setCurrentText(None)
            return

        treat_type = self.tab_registration.ui.comboBox_treat_type.currentText()
        if treat_type in ["慢性腎病照護", "助孕照護", "保胎照護"]:
            pass
        elif treat_type in nhi_utils.CARE_TREAT:
            self.tab_registration.ui.comboBox_course.setCurrentText(None)
            return

        primary_treatment = string_utils.xstr(
            self.tab_list[0].comboBox_treatment.currentText()
        )
        second_treatment = string_utils.xstr(
            self.tab_list[0].comboBox_second_treatment.currentText()
        )
        course = number_utils.get_integer(
            self.tab_registration.ui.comboBox_course.currentText()
        )
        treatment = nhi_utils.get_treatment(
            self.database, self.case_key, primary_treatment, second_treatment, course
        )
        treatment = prescript_utils.truncate_treatment(treatment)

        if treatment not in ["", None]:
            if treat_type not in ["慢性腎病照護", "助孕照護", "保胎照護"]:
                treat_type = prescript_utils.truncate_treatment(treatment)
                self.tab_registration.ui.comboBox_treat_type.setCurrentText(treatment)

            if course <= 0:
                self.tab_registration.ui.comboBox_course.setCurrentText("1")
        else:
            if (
                self.tab_registration.ui.comboBox_treat_type.currentText() != "醫療諮詢"
                and treat_type not in ["慢性腎病照護", "助孕照護", "保胎照護"]
            ):
                self.tab_registration.ui.comboBox_treat_type.setCurrentText("內科")

            if course >= 1:
                self.tab_registration.ui.comboBox_course.setCurrentText(None)

    # 病歷存檔
    def update_medical_record(self, set_doctor_done=False, check_prescript=True):
        # if self.ins_type == '健保':  # 健保存檔前再批價一次  # void 2022.01.14, 存檔後編輯實收負擔會無法變更
        #     self.calculate_ins_fees()

        self.update_diagnosis_data()
        self.tab_registration.save_record()
        self.tab_order.save_record()
        if self.tab_pregnant is not None:
            self.tab_pregnant.save_pregnant_data()

        if set_doctor_done:  # 還沒有完成醫師診療作業
            self._set_doctor_done()
            self._set_charge_done()
            self._set_wait_done()
            self._send_socket_data()
        else:  # 修正病歷存檔 2024.09.04
            # self._set_doctor_done(doctor_done='False')
            # self._set_charge_done(charge_done='False')
            # self._set_wait_done(wait_done='False')
            self._set_ins_upload_status()

        if not self.save_prescript(check_prescript=check_prescript):
            return False

        self.tab_medical_record_fees.save_record()

        if self.medical_record["InsType"] == "健保":
            if self.check_box_integrate_care.isChecked():
                case_utils.set_case_extend(
                    self.database, self.case_key, "整合醫療照護", "Y"
                )
            else:
                case_utils.clear_case_extend(
                    self.database, self.case_key, "整合醫療照護"
                )

        return True

    def _set_drug_no(self):
        if number_utils.get_integer(self.medical_record["DrugNo"]) > 0:  # 已經存在
            return

        sql = " SELECT * FROM dosage WHERE CaseKey = %s AND Days > 0"
        params = (self.case_key,)
        rows = self.database.select_record(sql, params)
        if len(rows) <= 0:
            sql = """
                SELECT PrescriptKey FROM prescript
                WHERE
                    CaseKey = %s AND
                    MedicineType NOT IN ("穴道", "處置")
            """
            params = (self.case_key,)
            rows = self.database.select_record(sql, params)
            if len(rows) <= 0:  # 檢查是否有開藥
                return

        drug_no = case_utils.get_drug_no(
            self.database, self.system_settings, self.medical_record["CaseDate"]
        )
        sql = """
            UPDATE cases
            SET
                DrugNo = %s
            WHERE
                CaseKey = %s
        """
        params = (drug_no, self.case_key)
        self.database.exec_sql(sql, params)

    def update_patient_record(self):
        if not self.ui.textEdit_patient_remark.document().isModified():
            return

        remark = self.ui.textEdit_patient_remark.toPlainText()

        sql = "UPDATE patient SET Remark = %s WHERE PatientKey = %s"
        self.database.exec_sql(sql, (remark, self.patient_key))

    def _set_ins_upload_status(self):
        sql = f"""
            SELECT CaseKey FROM cases
            WHERE
                CaseKey = {self.case_key} AND
                (ExtractValue(Security, "//upload_time") != "")
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:  # 還未上傳過，不需要記錄在已修改名單內
            return

        fields = ["CaseKey", "ExtendType", "Content"]
        data = [
            self.case_key,
            "IC已上傳資料修正",
            datetime.datetime.now(),
        ]
        self.database.insert_record("caseextend", fields, data)

    def _send_socket_data(self):
        message = ",".join(
            [
                self.system_settings.field("院所名稱"),
                self.program_name,
                self.user_name,
                self.tab_registration.comboBox_room.currentText(),
            ]
        )

        self.socket_client.send_data(message)  # 舊管道：UDP
        self.notification_client.send_data(message)  # 新管道：資料庫

    def _set_doctor_done(self, case_key=None, doctor_done="True"):
        if case_key is None:
            case_key = self.case_key

        self.database.exec_sql(
            """
            UPDATE cases SET DoctorDone = %s, DoctorDate = %s WHERE CaseKey = %s
        """,
            (doctor_done, date_utils.now_to_str(), case_key),
        )

    def _set_charge_done(self, case_key=None, charge_done="True"):
        if self.system_settings.field("自動完成批價作業") != "Y":
            return

        if (
            self.system_settings.field("在掛號機批價繳費") == "Y"
            and string_utils.xstr(self.medical_record["Register"]) == "掛號機"
        ):  # 2024.10.01 經由掛號機掛號來的病患，由掛號機批價
            return

        if self.system_settings.field("視訊診療須經過批價作業") == "Y":
            injury = string_utils.xstr(self.medical_record["Injury"])
            regist_type = string_utils.xstr(self.medical_record["RegistType"])
            if (
                injury in nhi_utils.INFECTIOUS_INJURY_TYPE
                or regist_type in nhi_utils.TELECOM_TYPE
            ):
                return

        if case_key is None:
            case_key = self.case_key

        charge_date = date_utils.now_to_str()
        charge_period = registration_utils.get_current_period(self.system_settings)
        cashier = self.system_settings.field("使用者")
        sql = """
            UPDATE cases
            SET
                ChargeDone = %s, ChargeDate = %s, ChargePeriod = %s, Cashier = %s
            WHERE
                CaseKey = %s
        """
        params = (charge_done, charge_date, charge_period, cashier, case_key)
        self.database.exec_sql(sql, params)

    def _set_wait_done(self, case_key=None, wait_done="True"):
        if case_key is None:
            case_key = self.case_key

        if self.system_settings.field("自動完成批價作業") == "Y":
            sql = """
                UPDATE wait
                SET
                    DoctorDone = %s, ChargeDone = %s
                WHERE
                    CaseKey = %s
            """
            params = (wait_done, wait_done, case_key)
        else:
            sql = """
                UPDATE wait
                SET
                    DoctorDone = %s
                WHERE
                    CaseKey = %s
            """
            params = (wait_done, case_key)

        self.database.exec_sql(sql, params)

    # 診斷資料存檔
    def update_diagnosis_data(self, case_key=None):
        if case_key is None:
            case_key = self.case_key

        if self.ui.checkBox_reference.isChecked():
            reference = "True"
        else:
            reference = "False"

        symptom = self.ui.textEdit_symptom.toPlainText()
        symptom = string_utils.remove_bom(symptom)
        # symptom = string_utils.remove_mb4(symptom)

        try:
            regist_typex = self.combo_box_regist_typex.currentText()
        except Exception:
            regist_typex = "內科"

        fields = [
            "RegistTypex",
            "Symptom",
            "Tongue",
            "Pulse",
            "Remark",
            "DiseaseCode1",
            "DiseaseCode2",
            "DiseaseCode3",
            "DiseaseCode4",
            "DiseaseName1",
            "DiseaseName2",
            "DiseaseName3",
            "DiseaseName4",
            "Distincts",
            "Cure",
            "Reference",
        ]

        data = [
            regist_typex,
            symptom,
            self.ui.textEdit_tongue.toPlainText(),
            self.ui.textEdit_pulse.toPlainText(),
            self.ui.textEdit_remark.toPlainText(),
            self.ui.lineEdit_disease_code1.text(),
            self.ui.lineEdit_disease_code2.text(),
            self.ui.lineEdit_disease_code3.text(),
            self.ui.lineEdit_disease_code4.text(),
            self.ui.lineEdit_disease_name1.text(),
            self.ui.lineEdit_disease_name2.text(),
            self.ui.lineEdit_disease_name3.text(),
            self.ui.lineEdit_disease_name4.text(),
            self.ui.lineEdit_distinguish.text()[:40],
            self.ui.lineEdit_cure.text()[:40],
            reference,
        ]

        try:
            self.database.update_record("cases", fields, "CaseKey", case_key, data)
        except Exception:
            del fields[0]
            del data[0]
            self.database.update_record("cases", fields, "CaseKey", case_key, data)

    def save_prescript(self, check_prescript=True):
        check_ok = True

        if self.call_from == "病歷查詢健保病歷":
            max_tab = 1
        else:
            max_tab = self.max_tab

        for medicine_set, tab_prescript in zip(range(1, max_tab + 1), self.tab_list):
            if tab_prescript is not None:
                try:
                    if not tab_prescript.save_prescript(
                        check_prescript=check_prescript
                    ):
                        self.ui.tabWidget_prescript.setCurrentIndex(medicine_set - 1)
                        check_ok = False
                        system_utils.show_message_box(
                            QMessageBox.Critical,
                            "劑量檢查結果提醒",
                            '<h3><font color="red">劑量檢查有誤，請更改劑量</font></h3>',
                            "請重新調整劑量.",
                        )
                except RuntimeError:  # 關閉處方頁, 刪除整個處方
                    self.remove_prescript(medicine_set)
            else:
                self.remove_prescript(medicine_set)

        return check_ok

    def remove_prescript(self, medicine_set):
        if self.case_key is None:
            return

        self.database.exec_sql(
            "DELETE FROM prescript WHERE CaseKey = %s AND MedicineSet = %s",
            (self.case_key, medicine_set),
        )
        self.database.exec_sql(
            "DELETE FROM dosage WHERE CaseKey = %s AND MedicineSet = %s",
            (self.case_key, medicine_set),
        )

    # 健保重新批價
    def calculate_ins_fees(self):
        try:
            self.tab_medical_record_fees.calculate_ins_fees()
        except AttributeError:
            pass

    # 自費重新批價
    def calculate_self_fees(self):
        try:
            self.tab_medical_record_fees.calculate_self_fees(
                self.tab_list,
            )
        except AttributeError:
            pass

    # 顯示拷貝過去病歷視窗
    def _open_past_history(self):
        dialog = dialog_utils.get_dialog_medical_record_past_history(
            self,
            self.database,
            self.system_settings,
            self.case_key,
            self.patient_key,
            "病歷登錄",
        )
        dialog.exec_()
        dialog.deleteLater()

    # 顯示參考病歷
    def _open_medical_record_reference(self):
        dialog = dialog_utils.get_dialog_medical_record_reference(
            self,
            self.database,
            self.system_settings,
            self.case_key,
        )
        dialog.exec_()
        dialog.deleteLater()

    # 顯示參考處方
    def _open_reference_prescript(self):
        icd_code = self.ui.lineEdit_disease_code1.text()

        dialog = dialog_utils.get_dialog_reference_prescript(
            self,
            self.database,
            self.system_settings,
            icd_code,
        )
        dialog.exec_()
        dialog.deleteLater()

    def _text_edit_key_press(self, event):
        # 判斷當前焦點元件（哪一個 QTextEdit）
        if self.ui.textEdit_symptom.hasFocus():
            diagnostic_type = "主訴"
            sender = self.ui.textEdit_symptom
        elif self.ui.textEdit_tongue.hasFocus():
            diagnostic_type = "舌診"
            sender = self.ui.textEdit_tongue
        elif self.ui.textEdit_pulse.hasFocus():
            diagnostic_type = "脈象"
            sender = self.ui.textEdit_pulse
        elif self.ui.textEdit_remark.hasFocus():
            diagnostic_type = "備註"
            sender = self.ui.textEdit_remark
        else:
            diagnostic_type = "主訴"
            sender = self.ui.textEdit_symptom

        key = event.key()
        char = event.text()

        # 濾掉組字階段（輸入法還沒 commit 的文字），避免干擾
        if not char.strip() and key not in [Qt.Key_Enter, Qt.Key_Return]:
            return QtWidgets.QTextEdit.keyPressEvent(sender, event)

        # 更新輸入碼（自定查詢用）
        self.input_code += char

        # 特殊按鍵處理
        if key in [
            Qt.Key_Enter,
            Qt.Key_Return,
            Qt.Key_Escape,
            Qt.Key_Space,
            Qt.Key_Comma,
            Qt.Key_Up,
            Qt.Key_Down,
            Qt.Key_Left,
            Qt.Key_Right,
        ]:
            if key in [Qt.Key_Enter, Qt.Key_Return]:
                self.input_code = self.input_code[:-1]  # 去掉回車符號

                if self.input_code != "":
                    input_code = self.input_code  # 複製變數進 lambda 閉包
                    if self.system_settings.field("輸入主訴資料自動補全") == "Y":
                        pass
                    else:
                        QtCore.QTimer.singleShot(
                            50,
                            lambda: self._query_diagnostic_dict(
                                event, sender, input_code, diagnostic_type
                            ),
                        )

                else:
                    return QtWidgets.QTextEdit.keyPressEvent(sender, event)

            # 按下其他控制鍵則重置輸入碼
            self.input_code = ""
        elif key in [Qt.Key_Backspace, Qt.Key_Delete]:
            if len(self.input_code) > 1:
                self.input_code = self.input_code[:-2]
            else:
                self.input_code = ""

        # 正常傳遞事件給原生 QTextEdit 處理
        if key not in [Qt.Key_Enter, Qt.Key_Return]:
            return QtWidgets.QTextEdit.keyPressEvent(sender, event)

    def _query_diagnostic_dict(self, event, sender, input_code, diagnostic_type):
        clean_input_code = string_utils.replace_ascii_char(["\\", '"', "'"], input_code)
        order_type = """
            ORDER BY LENGTH(ClinicName), CAST(CONVERT(`ClinicName` using big5) AS BINARY)
        """
        if self.system_settings.field("詞庫排序") == "點擊率":
            order_type = "ORDER BY HitRate DESC"
        elif self.system_settings.field("詞庫排序") == "最後點擊時戳":
            order_type = "ORDER BY TimeStamp DESC"

        sql = f"""
            SELECT ClinicKey, ClinicName FROM clinic
            WHERE
                ClinicType = %s AND
                InputCode LIKE %s
            GROUP BY ClinicName
            {order_type}
        """
        rows = self.database.select_record(
            sql, (diagnostic_type, f"{clean_input_code}%")
        )
        row_count = len(rows)

        if row_count <= 0:
            return QtWidgets.QTextEdit.keyPressEvent(sender, event)
        elif row_count == 1:
            self.insert_text(
                sender, string_utils.xstr(rows[0]["ClinicName"]), input_code
            )
            clinic_key = string_utils.xstr(rows[0]["ClinicKey"])
            db_utils.increment_hit_rate(
                self.database, "clinic", "ClinicKey", clinic_key
            )
        else:
            dialog = dialog_utils.get_dialog_diagnostic_picker(
                self,
                self.database,
                self.system_settings,
                sender,
                diagnostic_type,
                clean_input_code,
            )

            if dialog.exec_():
                clinic_name = dialog.clinic_name
                self.insert_text(sender, clinic_name, dialog.input_code)

            dialog.close_all()
            dialog.deleteLater()

    def _tool_button_picker_clicked(self):
        sender_name = self.sender().objectName()

        tool_button_dict = {
            "toolButton_symptom_picker": ["主訴", self.ui.textEdit_symptom],
            "toolButton_tongue_picker": ["舌診", self.ui.textEdit_tongue],
            "toolButton_pulse_picker": ["脈象", self.ui.textEdit_pulse],
        }

        clinic_type = tool_button_dict[sender_name][0]
        text_edit = tool_button_dict[sender_name][1]
        dialog = dialog_utils.get_dialog_diagnostic_picker(
            self,
            self.database,
            self.system_settings,
            text_edit,
            clinic_type,
            "",
        )

        if dialog.exec_():
            clinic_name = dialog.clinic_name
            self.insert_text(self.ui.textEdit_tongue, clinic_name, "")

        dialog.close_all()
        dialog.deleteLater()

    def insert_text(self, text_edit, text, input_code, insert_comma=True):
        system_utils.insert_text(text_edit, text, input_code, insert_comma)

    def _medical_record_precheck(self):
        self._check_pres_days()
        if self.system_settings.field("療程開藥兩次以上提醒") == "Y":
            self._check_course_medicine_two_times()

        self._check_highly_massage_course()

    # 檢查上次健保給藥是否服藥完畢
    def _check_pres_days(self):
        message = registration_utils.check_prescription_finished(
            self.database, self.system_settings, self.case_key, self.patient_key
        )
        if message is not None:
            system_utils.show_message_box(
                QMessageBox.Warning,
                "檢查結果提醒",
                f'<h3><font color="red">{message}</font></h3>',
                "請注意用藥重複.",
            )

    # 檢查上次健保給藥是否服藥完畢
    def _check_course_medicine_two_times(self):
        card = string_utils.xstr(self.medical_record["Card"])
        course = number_utils.get_integer(self.medical_record["Continuance"])

        message = registration_utils.check_course_medicine_two_times(
            self.database, self.system_settings, self.patient_key, card, course
        )
        if message is not None:
            system_utils.show_message_box(
                QMessageBox.Warning,
                "檢查結果提醒",
                f"<h3>{message}</h3>",
                "請注意療程開藥次數.",
            )

    def _check_highly_massage_course(self):
        course = number_utils.get_integer(self.medical_record["Continuance"])
        if course <= 1:
            return

        case_date = self.medical_record["CaseDate"]
        card = string_utils.xstr(self.medical_record["Card"])

        treatment = registration_utils.get_first_course_treatment(
            self.database,
            self.system_settings,
            case_date,
            self.patient_key,
            card,
            course,
        )

        if treatment in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT:
            system_utils.show_message_box(
                QMessageBox.Warning,
                "高度複雜傷科後續治療提醒",
                '<h3><font color="red">本療程第一次為高度複雜性傷科，今日只能執行一般針灸或一般傷科治療。</font></h3>',
                "請注意！此為高度複雜傷科療程後續治療的限制.",
            )

    # 新增自費
    def _append_new_self_medical_record(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("目前病歷存檔")
        msg_box.setText(
            "<font size='4' color='red'><b>是否先將目前的病歷存檔送出, 再輸入新增的自費病歷?</b></font>"
        )
        msg_box.setInformativeText("注意！存檔後, 請繼續輸入新增的自費病歷!")
        msg_box.addButton(QPushButton("存檔列印"), QMessageBox.YesRole)
        msg_box.addButton(QPushButton("存檔不印"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("否"), QMessageBox.RejectRole)
        save_current_record = msg_box.exec_()

        if save_current_record == QMessageBox.AcceptRole:
            self.save_medical_record(print_form=True)
        elif save_current_record == QMessageBox.RejectRole:
            self.save_medical_record(print_form=False)
        else:
            pass

        self.parent.append_self_medical_record(
            self.append_new_case_key,
            self.patient_key,
            self.patient_record["Name"],
        )

    # 清除病歷
    def clear_medical_record(self):
        self.clear_medical_record_option = False

        msg_box = dialog_utils.get_message_box(
            "清除病歷",
            QMessageBox.Warning,
            '<font size="5" color="red"><b>確定清除此病歷? (包含望聞問切及處方資料)</b></font>',
            "注意！病歷清除後, 若不存檔, 還可復原!",
        )
        clear_medical_record = msg_box.exec_()
        if not clear_medical_record:
            return

        self.clear_medical_record_option = True
        self.ui.textEdit_symptom.setText(None)
        self.ui.textEdit_tongue.setText(None)
        self.ui.textEdit_pulse.setText(None)
        self.ui.textEdit_remark.setText(None)

        self.ui.lineEdit_disease_code4.setText(None)
        self.ui.lineEdit_disease_code3.setText(None)
        self.ui.lineEdit_disease_code2.setText(None)
        self.ui.lineEdit_disease_code1.setText(None)
        self.ui.lineEdit_distinguish.setText(None)
        self.ui.lineEdit_cure.setText(None)

    def _insert_today(self):
        try:
            today = date_utils.west_date_to_nhi_date(
                self.medical_record["CaseDate"].date(), "/"
            )
        except Exception:
            today = date_utils.west_date_to_nhi_date(
                datetime.date.today().strftime("%Y-%m-%d"), "/"
            )
        self.insert_text(self.ui.textEdit_symptom, today + " ", "", insert_comma=False)
        self.ui.textEdit_symptom.setFocus()

    def _insert_calendar(self):
        insert_date = date_utils.get_dialog_date(
            self, self.database, self.system_settings, zh_tw=True, call_from="輸入主訴"
        )
        if insert_date is None:
            return

        self.insert_text(
            self.ui.textEdit_symptom, insert_date + " ", "", insert_comma=False
        )
        self.ui.textEdit_symptom.setFocus()

    def _symptom_selection_changed(self):
        selected_text = self.ui.textEdit_symptom.textCursor().selectedText().strip()

        if selected_text == "":
            enabled = False
        else:
            enabled = True

        self.ui.toolButton_add_symptom_dict.setEnabled(enabled)

    def _add_symptom_dict(self):
        selected_text = (
            self.ui.textEdit_symptom.textCursor().selectedText().strip()[:40]
        )
        dialog = dialog_utils.get_dialog_add_diagnostic_dict(
            self,
            self.database,
            self.system_settings,
            "主訴",
            selected_text,
        )
        dialog.exec_()
        dialog.deleteLater()

    def _open_reservation(self):
        doctor = self.tab_registration.ui.comboBox_doctor.currentText()
        if doctor == "":
            doctor = self.user_name

        self.parent.open_reservation(None, self.patient_key, doctor)

    def _open_exam_result(self):
        url = self.system_settings.field("檢驗所伺服器")
        hosp_id = self.system_settings.field("檢驗所用戶代碼")
        login_pws = self.system_settings.field("檢驗所密碼")

        if url is None or hosp_id is None or login_pws is None:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "參數未設定",
                '<font size="5" color="red"><b>系統設定內沒有設定醫事檢驗所連線資訊, 無法取得檢驗資料.</b></font>',
                "請至系統設定完成醫師檢驗所連線各項設定.",
            )
            return

        dialog = dialog_utils.get_dialog_exam_result(
            self, self.database, self.system_settings, self.patient_key
        )
        dialog.exec_()
        dialog.deleteLater()

    # 開啟病歷影像
    def capture_image(self):
        if self.system_settings.field("影像檔路徑") in ["", None]:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "路徑未設定",
                '<font size="5" color="red"><b>系統設定內的影像資料檔路徑未設定, 無法執行及讀取影像資料功能.</b></font>',
                "請至系統設定->其他->設定影像資料檔路徑.",
            )
            return

        dialog = dialog_utils.get_dialog_capture_image(
            self,
            self.database,
            self.system_settings,
            self.case_key,
            self.patient_key,
            "病歷影像",
        )
        if dialog.camera is not None and dialog.camera.isOpened():
            dialog.exec_()

        dialog.deleteLater()

        self.tab_image.read_images()

    def _write_log(self):
        name = self.medical_record["Name"]
        log_time = date_utils.now_to_str()
        log_message = f"{name}於{log_time}完成病歷存檔"

        for tab_index in range(self.ui.tabWidget_prescript.count()):
            tab = self.tab_list[tab_index]
            if tab is None:
                continue

            tab_name = self.ui.tabWidget_prescript.tabText(tab_index)
            row_count = tab.ui.tableWidget_prescript.rowCount()
            if tab.ui.tableWidget_prescript.item(0, 0) is None:
                continue

            log_message += f", {tab_name}: {row_count}筆藥品"

        total_fee = number_utils.get_integer(
            charge_utils.get_table_widget_item_fee(
                self.tab_medical_record_fees.ui.tableWidget_cash_fees,
                self.tab_medical_record_fees.SELF_COLUMN["TotalFee"],
                0,
            )
        )
        log_message += f", 自費金額: {total_fee}"

        if self.call_from == "醫師看診作業":
            operation = "病歷存檔"
        else:
            operation = "病歷修正"

        log_utils.write_event_log(
            self.database, self.user_name, operation, self.call_from, log_message
        )

    def _open_med_vpn(self):
        # web_utils.open_med_vpn(self.system_settings)
        web_utils.open_nhi_medcloud(use_virtual_card=False)

    def is_doctor_done(self):
        if self.case_key is None:
            return False

        doctor_done = False

        sql = f"""
            SELECT DoctorDone FROM cases
            WHERE
                CaseKey = {self.case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return False

        row = rows[0]
        if string_utils.xstr(row["DoctorDone"]) == "True":
            doctor_done = True

        return doctor_done

    def set_focus(self):
        self.ui.textEdit_symptom.setFocus()

    def _complaint_injury(self, checked):
        if checked:
            reply = QMessageBox.question(
                self,
                "確認主訴職災",
                "您確定要設定本病歷為主訴職災嗎？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.tab_registration.ui.comboBox_injury_type.setCurrentText("主訴職災")
                self.ui.checkBox_complaint_injury.setStyleSheet(
                    "color: red; font-weight: bold"
                )
            else:
                self.ui.checkBox_complaint_injury.blockSignals(True)  # 暫時禁用信號
                self.ui.checkBox_complaint_injury.setChecked(False)  # 還原為未選中狀態
                self.ui.checkBox_complaint_injury.blockSignals(False)  # 重新啟用信號
                return
        else:
            self.ui.checkBox_complaint_injury.setStyleSheet(None)
            if self.tab_registration.ui.comboBox_share_type.currentText() == "職業傷害":
                injury_type = "職業傷害"
            else:
                injury_type = "普通疾病"

            self.tab_registration.ui.comboBox_injury_type.setCurrentText(injury_type)

    def _exam_precheck(self):
        dialog = dialog_utils.get_dialog_exam_precheck(
            self,
            self.database,
            self.system_settings,
            self.case_key,
            "病歷登錄",
        )
        dialog.exec_()
        if dialog.ui.checkBox_copy_to_remark.isChecked():
            remark = dialog.get_remark()
            self.insert_text(
                self.ui.textEdit_remark, remark + "\n", "", insert_comma=False
            )

        try:
            self.tab_exam_precheck.set_case_extension()
        except AttributeError:
            self._read_exam_precheck()

        try:
            if self.tab_growth_chart is not None:
                self.tab_growth_chart.plot_chart()
        except Exception:
            pass

        dialog.deleteLater()

    def _conflict_drug(self):
        if self.ins_type != "健保":
            return

        patient_id = string_utils.xstr(self.patient_record["ID"])
        if patient_id == "":
            return

        doctor = self.medical_record["Doctor"]
        doctor_id = personnel_utils.get_person_field_value(
            self.database, string_utils.xstr(doctor), "ID"
        )

        if doctor_id == "":
            return

        system_utils.show_message_box(
            QMessageBox.Information,
            "藥物交互作用讀取前提醒",
            '<font size="5"><b>讀取中西藥交互作用資料前，請插入病人健保卡並完成醫事卡認證</b></font>',
            "中西藥交互作用 2.0 隱私權認證說明.",
        )

        table_widget = self.tab_list[0].ui.tableWidget_prescript

        dialog = dialog_utils.get_dialog_conflict_drug(
            self,
            self.database,
            self.system_settings,
            doctor_id,
            patient_id,
            table_widget,
        )
        dialog.exec_()
        dialog.deleteLater()

    def _check_patient_birthday_today(self):
        if self.patient_record["Birthday"] is None:
            return

        age, _ = date_utils.get_age(self.patient_record["Birthday"])
        birth_year = self.patient_record["Birthday"].year
        birth_month = self.patient_record["Birthday"].month
        birth_day = self.patient_record["Birthday"].day
        current_month = datetime.datetime.now().month
        current_day = datetime.datetime.now().day

        if birth_month != current_month or birth_day != current_day:
            return

        name = string_utils.xstr(self.medical_record["Name"])
        system_utils.show_message_box(
            QMessageBox.Information,
            "恭喜生日快樂",
            f'<font size="5" color="deepPink"><b>{name}今天{age}歲生日, 請獻上生日的祝福吧！.</b></font>',
            f"{name}的出生日期是{birth_year}年{birth_month}月{birth_day}日",
        )

    def _set_extra_tab(self):
        self.tab_pregnant = None

        treat_type = self.medical_record["TreatType"]
        if treat_type == "助孕照護":
            try:
                gender = self.patient_record["Gender"]
            except Exception:
                return

            if gender == "女":
                self.tab_pregnant = module_utils.get_pregnant_female(
                    self,
                    self.database,
                    self.system_settings,
                    self.case_key,
                    self.call_from,
                )
            else:
                self.tab_pregnant = module_utils.get_pregnant_male(
                    self,
                    self.database,
                    self.system_settings,
                    self.case_key,
                    self.call_from,
                )

        elif treat_type == "保胎照護":
            self.tab_pregnant = module_utils.get_keep_baby(
                self, self.database, self.system_settings, self.case_key, self.call_from
            )
        else:
            return

        self.ui.tabWidget_medical.addTab(self.tab_pregnant, treat_type)

    def _medical_record_version_history(self):
        dialog = dialog_utils.get_dialog_medical_record_version_history(
            self, self.database, self.system_settings, self.case_key
        )
        if dialog.exec_():
            backup_records_key = dialog.table_widget_medical_record.field_value(0)
            self._restore_medical_record_json(backup_records_key)

        dialog.deleteLater()

    def _restore_medical_record_json(self, backup_records_key):
        sql = f"""
            SELECT * FROM backup_records
            WHERE
                BackupRecordsKey = {backup_records_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        json_medical_record = json.loads(row["JSON"])[0]

        sql = f"""
            SELECT * FROM backup_records
            WHERE
                TableName = "prescript" AND
                KeyField = "BackupRecordsKey" AND
                KeyValue = {backup_records_key}
        """
        rows = self.database.select_record(sql)
        prescript_json_rows = json.loads(rows[0]["JSON"])

        self._set_medical_record(json_medical_record)

        max_medicine_set = case_utils.get_max_medicine_set_from_json(
            prescript_json_rows
        )
        if max_medicine_set is None:
            return

        for medicine_set in range(1, max_medicine_set + 1):
            self.tab_list[medicine_set - 1].copy_prescript_from_json(
                backup_records_key,
                json_medical_record,
                prescript_json_rows,
                medicine_set,
            )

    def refresh_wait(self):
        if self.call_from not in ["醫師看診作業", "新增自費病歷", "加購自費病歷"]:
            return

        try:
            doctor = self.medical_record["Doctor"]
        except Exception:
            return

        rows = self.database.select_record(
            'SELECT WaitKey FROM wait WHERE Doctor = %s AND DoctorDone = "False"',
            (doctor,),
        )
        if len(rows) >= 2:
            waiting_count = f", 目前尚有候診等待病患: {len(rows) - 1}人"
        else:
            waiting_count = ", 目前無候診等待病患"

        self.ui.groupBox_diagnostic.setTitle(
            f"診斷  (主治醫師: {doctor}){waiting_count}"
        )

    # 參考病歷存檔
    def save_reference_medical_record(self):
        diagnostic_dict = {
            "symptom": self.ui.textEdit_symptom.toPlainText(),
            "tongue": self.ui.textEdit_tongue.toPlainText(),
            "pulse": self.ui.textEdit_pulse.toPlainText(),
            "remark": self.ui.textEdit_remark.toPlainText(),
            "disease_code1": self.ui.lineEdit_disease_code1.text(),
            "disease_code2": self.ui.lineEdit_disease_code2.text(),
            "disease_code3": self.ui.lineEdit_disease_code3.text(),
            "disease_code4": self.ui.lineEdit_disease_code4.text(),
            "distinguish": self.ui.lineEdit_distinguish.text(),
            "cure": self.ui.lineEdit_cure.text(),
            "treatment": self.tab_list[0].comboBox_treatment.currentText(),
        }

        prescript_rows = []
        dosage_rows = []
        for medicine_set, tab_prescript in zip(
            range(1, self.max_tab + 1), self.tab_list
        ):
            if tab_prescript is not None:
                prescript_rows += self._get_prescript_rows(medicine_set, tab_prescript)
                dosage_rows += self._get_dosage_row(medicine_set, tab_prescript)

        medical_record_dict = {
            "diagnostic": diagnostic_dict,
            "prescript": prescript_rows,
            "dosage": dosage_rows,
        }

        medical_record_json = json.dumps(medical_record_dict)
        fields = ["TableName", "KeyField", "KeyValue", "JSON"]
        data = [
            "reference_medical_record",
            "disease_code",
            diagnostic_dict["disease_code1"],
            medical_record_json,
        ]
        self.database.insert_record("extension_json", fields, data)

        self.close_all()
        self.close_tab()

    def _get_prescript_rows(self, medicine_set, tab_prescript):
        prescript_rows = []
        table_widget_prescript = tab_prescript.tableWidget_prescript

        for row_no in range(table_widget_prescript.rowCount()):
            medicine_key_item = table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["MedicineKey"]
            )
            if medicine_key_item is None:
                continue

            medicine_key = medicine_key_item.text()
            medicine_type = table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["MedicineType"]
            ).text()
            medicine_name = table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["MedicineName"]
            ).text()
            ins_code = table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["InsCode"]
            ).text()
            dosage = table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["Dosage"]
            ).text()
            dosage_mode = table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["DosageMode"]
            ).text()
            unit = table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["Unit"]
            ).text()
            row = {}
            row["medicine_set"] = medicine_set
            row["medicine_key"] = medicine_key
            row["medicine_type"] = medicine_type
            row["medicine_name"] = medicine_name
            row["ins_code"] = ins_code
            row["dosage"] = dosage
            row["dosage_mode"] = dosage_mode
            row["unit"] = unit

            prescript_rows.append(row)

        if medicine_set == 1:
            table_widget_treat = tab_prescript.tableWidget_treat
            for row_no in range(table_widget_treat.rowCount()):
                medicine_key_item = table_widget_treat.item(
                    row_no, prescript_utils.INS_TREAT_COL_NO["MedicineKey"]
                )
                if medicine_key_item is None:
                    continue

                medicine_key = medicine_key_item.text()
                medicine_type = table_widget_treat.item(
                    row_no, prescript_utils.INS_TREAT_COL_NO["MedicineType"]
                ).text()
                medicine_name = table_widget_treat.item(
                    row_no, prescript_utils.INS_TREAT_COL_NO["MedicineName"]
                ).text()
                ins_code = table_widget_treat.item(
                    row_no, prescript_utils.INS_TREAT_COL_NO["InsCode"]
                ).text()
                row = {}
                row["medicine_set"] = medicine_set
                row["medicine_key"] = medicine_key
                row["medicine_type"] = medicine_type
                row["medicine_name"] = medicine_name
                row["ins_code"] = ins_code
                row["dosage"] = None
                row["dosage_mode"] = None
                row["unit"] = None

                prescript_rows.append(row)

        return prescript_rows

    def _get_dosage_row(self, medicine_set, tab_prescript):
        dosage_row = []

        row = {}
        row["medicine_set"] = medicine_set
        row["package"] = tab_prescript.comboBox_package.currentText()
        row["presdays"] = tab_prescript.comboBox_pres_days.currentText()
        row["instruction"] = tab_prescript.comboBox_instruction.currentText()
        dosage_row.append(row)

        return dosage_row

    def _medicine_to_herb(self):
        medicine_set = self._get_current_medicine_set()
        if medicine_set is not None and medicine_set >= 2:  # 自費處方才轉
            self.tab_list[medicine_set - 1].medicine_to_herb()

    def _tool_button_blood_measure_clicked(self):
        patient_id = self.patient_record["ID"]
        try:
            script = system_utils.get_blood_measure_data(
                self.parent, self.system_settings, patient_id
            )
        except Exception:
            return

        self.insert_text(self.ui.textEdit_symptom, script, "", insert_comma=False)

    def _tongue_quick_click(self):
        tongue = self.sender().text()
        self.insert_text(self.ui.textEdit_tongue, tongue, "", insert_comma=True)

    def _pulse_quick_click(self):
        pulse = self.sender().text()
        self.insert_text(self.ui.textEdit_pulse, pulse, "", insert_comma=False)

    def _set_broadcast_voice(self):
        if not self.parent.tab_exists("醫師看診作業") or self.wait_key is None:
            self.ui.action_broadcast_voice.setVisible(False)

    def _send_voice_data(self):
        sql = f"""
            SELECT RegistNo, Name, Room FROM wait
            WHERE
                WaitKey = {self.wait_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        current_tab = None
        tab_widget = self.parent.tabWidget_window
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) == "醫師看診作業":
                current_tab = tab_widget.widget(i)

        if current_tab is None:
            return

        row = rows[0]
        regist_no = number_utils.get_integer(row["RegistNo"])
        name = string_utils.xstr(row["Name"])
        room = string_utils.xstr(number_utils.get_integer(row["Room"]))

        current_tab.send_voice_data(regist_no=regist_no, name=name, room=room)
