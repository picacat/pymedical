# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

import datetime

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QPushButton

from libs import (
    case_utils,
    class_utils,
    cshis_utils,
    date_utils,
    db_utils,
    dialog_utils,
    export_utils,
    log_utils,
    nhi_utils,
    number_utils,
    personnel_utils,
    printer_utils,
    stock_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 主視窗
class MedicalRecordList(QtWidgets.QMainWindow):
    program_name = "病歷查詢"

    # 初始化
    def __init__(self, parent=None, *args):
        super(MedicalRecordList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]
        self.dialog_setting = {
            "dialog_executed": False,
            "start_date": None,
            "end_date": None,
            "enable_end_date": False,
            "period": None,
            "ins_type": None,
            "regist_type": None,
            "treat_type": None,
            "share_type": None,
            "injury_type": None,
            "apply_type": None,
            "person": None,
            "registrar": None,
            "room": None,
            "archive_database": False,
        }
        self.column = {
            "CaseKey": 0,
            "PrintMark": 1,
            "Image": 2,
            "VersionHistory": 3,
            "CaseDate": 4,
            "Period": 5,
            "DoctorDone": 6,
            "DoctorDoneTime": 7,
            "ChargeDone": 8,
            "Room": 9,
            "RegistNo": 10,
            "PatientKey": 11,
            "Name": 12,
            "ID": 13,
            "Gender": 14,
            "Birthday": 15,
            "Age": 16,
            "Visit": 17,
            "RegistType": 18,
            "TourArea": 19,
            "InsType": 20,
            "ApplyType": 21,
            "PharmacyType": 22,
            "Share": 23,
            "TreatType": 24,
            "Card": 25,
            "Course": 26,
            "PresDays": 27,
            "Doctor": 28,
            "DiseaseName": 29,
            "Massager": 30,
            "RegistFee": 31,
            "DiagShareFee": 32,
            "DrugShareFee": 33,
            "TotalFee": 34,
            "DiscountFee": 35,
            "DiagFee": 36,
            "InterDrugFee": 37,
            "PharmacyFee": 38,
            "TreatFee": 39,
            "InsApplyFee": 40,
            "PatientTelephone": 41,
            "PatientAddress": 42,
            "PatientRemark": 43,
            "InvoiceNo": 44,
        }

        self.patient_key = None
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.medical_record_rows = None
        self.total_pages = 1
        self.current_page = 1
        self.sql = None
        self.medicine_list = []

        self._set_ui()
        self._set_signal()
        self._set_permission()
        self._set_check()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_MEDICAL_RECORD_LIST, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_medical_record_list = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record_list, self.database
        )
        self.table_widget_medical_record_list.set_column_hidden([0])
        self.table_widget_medical_record_list.set_parent(self.parent)
        # database._set_table_width()
        self._set_tool_button()

        self.ui.spinBox_count_per_page.setValue(
            number_utils.get_integer(self.system_settings.field("病歷查詢一頁筆數"))
        )
        if self.system_settings.field("病歷查詢檢視方式") == "精簡檢視":
            self.ui.radioButton_simple.setChecked(True)
            self._set_view_state("精簡顯示")

    def _set_permission(self):
        if self.user_name == "超級使用者":
            return

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "關檔", self.user_name
            )
            != "Y"
        ):
            self.ui.action_close_case.setEnabled(False)
            self.ui.action_open_case.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "調閱病歷", self.user_name
            )
            != "Y"
        ):
            self.ui.action_open_record.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "病歷刪除", self.user_name
            )
            != "Y"
        ):
            self.ui.action_delete_record.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "匯出實體病歷", self.user_name
            )
            != "Y"
        ):
            self.ui.action_export_cases_pdf.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "匯出收費明細", self.user_name
            )
            != "Y"
        ):
            self.ui.action_export_fees_pdf.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "列印單據", self.user_name
            )
            != "Y"
        ):
            self.ui.action_print_prescript.setEnabled(False)
            self.ui.action_print_receipt.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "列印報表", self.user_name
            )
            != "Y"
        ):
            self.ui.action_print_cases.setEnabled(False)
            self.ui.action_print_fees.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, "系統作業", "關閉匯出功能", self.user_name
            )
            == "Y"
        ):
            self.ui.action_export_cases_pdf.setEnabled(False)
            self.ui.action_export_cases_pdf2.setEnabled(False)
            self.ui.action_export_fees_pdf.setEnabled(False)
            self.ui.action_export_excel.setEnabled(False)
            self.ui.action_export_medical_record_excel.setEnabled(False)
            self.ui.action_export_marked_medical_record_excel.setEnabled(False)
            self.ui.action_export_medical_record_diagnosis_excel.setEnabled(False)
            self.ui.action_export_json.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.action_requery.triggered.connect(self.open_dialog)
        self.ui.action_delete_record.triggered.connect(self.delete_medical_record)
        self.ui.action_close.triggered.connect(self.close_medical_record_list)
        self.ui.action_open_record.triggered.connect(
            lambda: self.open_medical_record(case_key=None)
        )
        self.ui.action_open_ins_record.triggered.connect(self.open_ins_medical_record)
        self.ui.action_open_marked_records.triggered.connect(self._open_marked_records)
        self.ui.action_print_prescript.triggered.connect(self._print_prescript)
        self.ui.action_print_receipt.triggered.connect(self._print_receipt)
        self.ui.action_print_non_dosage_receipt.triggered.connect(
            self._print_non_dosage_receipt
        )
        self.ui.action_print_misc.triggered.connect(self._print_misc)
        self.ui.action_print_misc2.triggered.connect(self._print_misc2)
        self.ui.action_print_misc3.triggered.connect(self._print_misc3)
        self.ui.action_print_prescription_bag.triggered.connect(
            self._print_prescription_bag
        )
        self.ui.action_print_cases.triggered.connect(self._print_cases)
        self.ui.action_print_cases_without_treat.triggered.connect(self._print_cases)
        self.ui.action_print_cases2.triggered.connect(
            lambda: self._print_cases(print_self_prescript=True)
        )
        self.ui.action_print_cases3.triggered.connect(
            lambda: self._print_cases(print_patient=False)
        )
        self.ui.action_export_cases_pdf.triggered.connect(self._print_cases)
        self.ui.action_export_cases_pdf2.triggered.connect(
            lambda: self._print_cases(print_self_prescript=True)
        )
        self.ui.action_print_fees.triggered.connect(self._print_fees)
        self.ui.action_export_fees_pdf.triggered.connect(self._print_fees)
        self.ui.action_set_check.triggered.connect(self._set_check)
        self.ui.action_set_uncheck.triggered.connect(self._set_check)
        self.ui.action_set_block_check.triggered.connect(self._set_block_check)
        self.ui.action_export_excel.triggered.connect(self._export_to_excel)
        self.ui.action_export_medical_record_excel.triggered.connect(
            self._export_medical_record_to_excel
        )
        self.ui.action_export_marked_medical_record_excel.triggered.connect(
            self._export_marked_medical_record_to_excel
        )
        self.ui.action_export_medical_record_diagnosis_excel.triggered.connect(
            self._export_medical_record_diagnosis_excel
        )
        self.ui.action_set_traditional_health_case.triggered.connect(
            self._set_traditional_health_case
        )

        self.ui.action_export_json.triggered.connect(self._export_to_json)
        self.ui.action_print_registration.triggered.connect(self._print_registration)
        self.ui.action_print_massage.triggered.connect(self._print_massage)

        self.ui.action_print_marked_registration_form.triggered.connect(
            self._print_marked_registration_form
        )

        self.ui.action_print_marked_ins_prescript.triggered.connect(
            self._print_marked_ins_prescript
        )
        self.ui.action_print_marked_ins_receipt.triggered.connect(
            self._print_marked_ins_receipt
        )

        self.ui.action_print_marked_self_prescript.triggered.connect(
            self._print_marked_self_prescript
        )
        self.ui.action_print_marked_self_receipt.triggered.connect(
            self._print_marked_self_receipt
        )
        self.ui.action_print_marked_self_receipt1.triggered.connect(
            self._print_marked_self_receipt1
        )
        self.ui.action_print_referral_form.triggered.connect(self._print_referral_form)

        self.ui.action_change_ins_type.triggered.connect(self._change_ins_type)
        self.ui.action_change_apply_type.triggered.connect(self._change_apply_type)
        self.ui.action_change_pharmacy_type.triggered.connect(
            self._change_pharmacy_type
        )
        self.ui.action_change_injury_type.triggered.connect(self._change_injury_type)
        self.ui.action_change_doctor.triggered.connect(self._change_doctor)
        self.ui.tableWidget_medical_record_list.doubleClicked.connect(
            lambda: self.open_medical_record(case_key=None)
        )
        self.ui.tableWidget_medical_record_list.keyPressEvent = (
            self._table_widget_medical_record_key_press
        )
        self.ui.tableWidget_medical_record_list.horizontalHeader().sectionClicked.connect(
            self._header_clicked
        )

        self.ui.pushButton_top.clicked.connect(self._top_record)
        self.ui.pushButton_next.clicked.connect(self._next_record)
        self.ui.pushButton_prev.clicked.connect(self._prev_record)
        self.ui.pushButton_bottom.clicked.connect(self._bottom_record)
        self.ui.spinBox_move_page.valueChanged.connect(self._spin_box_move_page)

        self.ui.action_generate_security.triggered.connect(self._generate_security)
        self.ui.action_print_correction_reg_income.triggered.connect(
            self._print_correction_reg_income
        )
        self.ui.action_print_care_income.triggered.connect(
            self._print_correction_reg_income
        )
        self.ui.radioButton_normal.clicked.connect(
            lambda: self._set_view_state("詳細檢視")
        )
        self.ui.radioButton_simple.clicked.connect(
            lambda: self._set_view_state("精簡顯示")
        )
        self.ui.action_show_all.triggered.connect(self._show_all_cases)
        self.ui.action_write_ic_treatment.triggered.connect(self._write_ic_treatment)
        self.ui.action_rewrite_ic_card.triggered.connect(self._rewrite_ic_card)
        self.ui.action_rewrite_ic_prescript.triggered.connect(
            self._rewrite_ic_prescript
        )
        self.ui.action_cancel_ic_card.triggered.connect(self._cancel_ic_card)
        self.ui.action_print_medical_certificate.triggered.connect(
            self._print_medical_certificate
        )
        self.ui.action_export_case_to_word.triggered.connect(self._export_case_to_word)
        self.ui.action_unlock_progress.triggered.connect(self._unlock_progress)
        self.ui.action_get_identification.triggered.connect(self._get_identification)
        self.action_export_correction_reg_income_txt.triggered.connect(
            self._export_correction_reg_income_txt
        )
        self.ui.action_close_case.triggered.connect(self._close_case)
        self.ui.action_open_case.triggered.connect(self._open_case)

    def _set_view_state(self, view_mode="詳細檢視"):
        hide_columns = [
            self.column["Image"],
            self.column["VersionHistory"],
            self.column["DoctorDone"],
            self.column["ChargeDone"],
            self.column["Room"],
            self.column["Gender"],
            self.column["Birthday"],
            self.column["Age"],
            self.column["RegistType"],
            self.column["Visit"],
            self.column["TourArea"],
            self.column["ApplyType"],
            self.column["PharmacyType"],
            self.column["Massager"],
            self.column["PatientTelephone"],
            self.column["PatientAddress"],
            self.column["PatientRemark"],
            self.column["InvoiceNo"],
        ]

        for col_no in hide_columns:
            if view_mode == "詳細檢視":
                self.ui.tableWidget_medical_record_list.showColumn(col_no)
            else:
                self.ui.tableWidget_medical_record_list.hideColumn(col_no)

        # 設定欄位寬度

    def _set_table_width(self):
        width = [
            70,
            10,
            40,
            160,
            50,
            40,
            40,
            40,
            50,
            80,
            80,
            40,
            120,
            50,
            50,
            90,
            80,
            80,
            70,
            40,
            40,
            80,
            200,
            200,
            80,
            80,
            80,
            80,
            80,
            80,
            80,
            80,
            80,
            400,
        ]
        self.table_widget_medical_record_list.set_table_heading_width(width)

    @staticmethod
    def get_select_fields():
        select_fields = """
            cases.CaseKey, cases.CaseDate AS CDate, DATE_FORMAT(cases.CaseDate, '%Y-%m-%d %H:%i') AS CaseDate,
            DoctorDate, ChargeDate, cases.SpecialCode, cases.Visit,
            cases.PatientKey, cases.Name, cases.Period, ChargePeriod, cases.InsType, cases.ApplyType,
            cases.PharmacyType, cases.Injury, cases.RegistType, cases.TourArea,
            cases.Share, cases.RegistNo, cases.Card, cases.Continuance, cases.TreatType,
            PresDays1, PresDays2, DiseaseCode1, DiseaseName1, DiseaseName2, DiseaseName3,
            cases.Doctor, cases.Massager, cases.Room, RegistFee, SDiagShareFee, SDrugShareFee,
            cases.DiagFee, cases.InterDrugFee, cases.PharmacyFee, cases.InsApplyFee,
            cases.AcupunctureFee, cases.MassageFee, cases.DislocateFee,
            cases.DoctorDone, cases.ChargeDone,
            SelfTotalFee, TotalFee, cases.DiscountFee,
            patient.Gender, patient.ID, patient.Birthday, patient.Telephone, patient.Address, patient.Cellphone,
            patient.NursingHome, patient.Remark AS PatientRemark,
            cases.InvoiceNo, cases.IsClosed,
            wait.InProgress
        """

        return select_fields

    def open_medical_record_list(self, patient_key):
        self.patient_key = patient_key
        self.medicine_list = []
        self.sql = f"""
            SELECT
                {self.get_select_fields()}
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = {patient_key}
                LEFT JOIN wait ON wait.CaseKey = cases.CaseKey
            WHERE
                cases.PatientKey = {patient_key}
            ORDER BY CaseDate
        """
        rows = self.database.select_record(self.sql)
        self.medical_record_rows = len(rows)
        self._read_medical_record_list(self.sql, self.medicine_list)

    # 讀取病歷
    def open_dialog(self):
        self._set_tool_button()

        dialog = dialog_utils.get_dialog_medical_record_list(
            self, self.database, self.system_settings
        )
        if self.dialog_setting["dialog_executed"]:
            dialog.ui.dateEdit_start_date.setDate(self.dialog_setting["start_date"])
            dialog.ui.dateEdit_end_date.setDate(self.dialog_setting["end_date"])
            dialog.ui.comboBox_period.setCurrentText(self.dialog_setting["period"])
            dialog.ui.comboBox_ins_type.setCurrentText(self.dialog_setting["ins_type"])
            dialog.ui.comboBox_regist_type.setCurrentText(
                self.dialog_setting["regist_type"]
            )
            dialog.ui.comboBox_treat_type.setCurrentText(
                self.dialog_setting["treat_type"]
            )
            dialog.ui.comboBox_share_type.setCurrentText(
                self.dialog_setting["share_type"]
            )
            dialog.ui.comboBox_injury_type.setCurrentText(
                self.dialog_setting["injury_type"]
            )
            dialog.ui.comboBox_apply_type.setCurrentText(
                self.dialog_setting["apply_type"]
            )
            dialog.ui.comboBox_doctor.setCurrentText(self.dialog_setting["person"])
            dialog.ui.comboBox_registrar.setCurrentText(
                self.dialog_setting["registrar"]
            )
            dialog.ui.comboBox_room.setCurrentText(self.dialog_setting["room"])
            dialog.ui.checkBox_enable_end_date.setChecked(
                self.dialog_setting["enable_end_date"]
            )
            dialog.ui.radioButton_archive_database.setChecked(
                self.dialog_setting["archive_database"]
            )

            dialog.set_end_date()

        if dialog.exec_():
            self.dialog_setting["dialog_executed"] = True
            self.dialog_setting["start_date"] = dialog.ui.dateEdit_start_date.date()
            self.dialog_setting["end_date"] = dialog.ui.dateEdit_end_date.date()
            self.dialog_setting["period"] = dialog.ui.comboBox_period.currentText()
            self.dialog_setting["ins_type"] = dialog.ui.comboBox_ins_type.currentText()
            self.dialog_setting["regist_type"] = (
                dialog.ui.comboBox_regist_type.currentText()
            )
            self.dialog_setting["treat_type"] = (
                dialog.ui.comboBox_treat_type.currentText()
            )
            self.dialog_setting["share_type"] = (
                dialog.ui.comboBox_share_type.currentText()
            )
            self.dialog_setting["injury_type"] = (
                dialog.ui.comboBox_injury_type.currentText()
            )
            self.dialog_setting["apply_type"] = (
                dialog.ui.comboBox_apply_type.currentText()
            )
            self.dialog_setting["person"] = dialog.ui.comboBox_doctor.currentText()
            self.dialog_setting["registrar"] = (
                dialog.ui.comboBox_registrar.currentText()
            )
            self.dialog_setting["room"] = dialog.ui.comboBox_room.currentText()
            self.dialog_setting["enable_end_date"] = (
                dialog.ui.checkBox_enable_end_date.isChecked()
            )
            self.dialog_setting["archive_database"] = (
                dialog.ui.radioButton_archive_database.isChecked()
            )

            dialog.set_end_date()

            self.sql = dialog.get_sql()
            archive_database = self._get_archive_database()
            rows = archive_database.select_record(self.sql)
            self.medical_record_rows = len(rows)

        dialog.close_all()
        dialog.deleteLater()

        if self.sql is None:
            return

        if dialog.ui.groupBox_advance_search.isChecked():
            self.medicine_list = dialog.ui.lineEdit_medicine_name.text().split()
        else:
            self.medicine_list = []

        self._read_medical_record_list(self.sql, self.medicine_list)

    def _get_archive_database(self):
        archive_database = self.database

        archive_database_name = self.system_settings.field("封存資料庫名稱")
        if self.dialog_setting["archive_database"] and archive_database_name not in [
            "",
            None,
        ]:
            archive_database = class_utils.get_db(
                host=self.database.host,
                user=self.database.user,
                password=self.database.password,
                database=archive_database_name,
                charset=self.database.charset,
            )

        return archive_database

    def _read_medical_record_list(self, sql, medicine_list, page=1):
        if sql is None:
            return

        count_per_page = self.ui.spinBox_count_per_page.value()
        start_index = (page - 1) * count_per_page

        limited_sql = f"{sql} LIMIT {start_index}, {count_per_page}"

        archive_database = self._get_archive_database()
        try:
            self.table_widget_medical_record_list.set_db_data(
                limited_sql, self._set_table_data, archive_database=archive_database
            )
        except Exception:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "資料查詢錯誤",
                '<font size="5" color="red"><b>病歷資料查詢條件設定有誤, 請重新查詢.</b></font>',
                "請檢查查詢的內容是否有標點符號或其他字元.",
            )
            return

        if len(medicine_list) > 0:
            self._check_advance_search(medicine_list)

        self._set_tool_button()

        self.total_pages = int(self.medical_record_rows / count_per_page)
        if self.medical_record_rows % count_per_page > 0:
            self.total_pages += 1

        if self.total_pages == 0:
            self.total_pages = 1

        self.ui.spinBox_move_page.setMaximum(self.total_pages)
        self.ui.label_total_pages.setText(f"共{self.total_pages}頁")
        self._set_page_button()

        self.ui.label_record_count.setText(
            f"共 {self.ui.tableWidget_medical_record_list.rowCount()} 筆"
        )

        if (
            self.ui.tableWidget_medical_record_list.rowCount() > 0
            and self.system_settings.field("病歷查詢顯示合計") == "Y"
        ):
            self._calculate_total()

    def _set_page_button(self):
        self.ui.label_current_page.setText(f"第{self.current_page}頁")
        self.ui.spinBox_move_page.setValue(self.current_page)

    def _spin_box_move_page(self):
        self.current_page = self.ui.spinBox_move_page.value()

        self._read_medical_record_list(self.sql, self.medicine_list, self.current_page)
        self._set_page_button()

    def _top_record(self):
        self.current_page = 1

        self._read_medical_record_list(self.sql, self.medicine_list, self.current_page)
        self._set_page_button()

    def _prev_record(self):
        if self.current_page > 1:
            self.current_page -= 1

        self._read_medical_record_list(self.sql, self.medicine_list, self.current_page)
        self._set_page_button()

    def _next_record(self):
        if self.current_page < self.total_pages:
            self.current_page += 1

        self._read_medical_record_list(self.sql, self.medicine_list, self.current_page)
        self._set_page_button()

    def _bottom_record(self):
        self.current_page = self.total_pages

        self._read_medical_record_list(self.sql, self.medicine_list, self.current_page)
        self._set_page_button()

    def _check_advance_search(self, medicine_list):
        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount(), -1, -1):
            item = self.ui.tableWidget_medical_record_list.item(row_no, 0)
            if item is None:
                continue

            case_key = item.text()
            for medicine_name in medicine_list:
                sql = f"""
                    SELECT * FROM prescript
                    WHERE
                        CaseKey = {case_key} AND
                        MedicineName LIKE "%{medicine_name}%"
                    LIMIT 1
                """
                rows = self.database.select_record(sql)
                if len(rows) <= 0:
                    self.ui.tableWidget_medical_record_list.removeRow(row_no)
                    break

    def _set_tool_button(self):
        if self.ui.tableWidget_medical_record_list.rowCount() > 0:
            enabled = True
        else:
            enabled = False

        self.ui.action_open_record.setEnabled(enabled)
        self.ui.action_delete_record.setEnabled(enabled)
        self.ui.action_print_registration.setEnabled(enabled)
        self.ui.action_print_prescript.setEnabled(enabled)
        self.ui.action_print_receipt.setEnabled(enabled)
        self.ui.action_print_misc.setEnabled(enabled)
        self.ui.action_print_misc2.setEnabled(enabled)

        self._set_permission()

    def _get_self_prescript_count(self, case_key):
        sql = f"""
            SELECT PrescriptKey FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2
            LIMIT 1
        """

        rows = self.database.select_record(sql)

        return len(rows)

    def _set_table_data(self, row_no, row):
        case_key = string_utils.xstr(row["CaseKey"])
        is_closed = bool(row["IsClosed"])

        if row["InsType"] == "健保":
            medicine_set = 1
        else:
            medicine_set = 2

        card = string_utils.xstr(row["Card"])
        if card == "免卡":
            card = None

        pres_days = case_utils.get_pres_days(
            self.database, row["CaseKey"], medicine_set
        )
        if pres_days <= 0:
            pres_days = None
            pharmacy_type = None
        else:
            pharmacy_type = string_utils.xstr(row["PharmacyType"])

        ins_type = string_utils.xstr(row["InsType"])
        if ins_type == "健保":
            apply_type = string_utils.xstr(row["ApplyType"])
        else:
            apply_type = None

        special_code = string_utils.xstr(row["SpecialCode"])
        self_total_fee = number_utils.get_integer(row["SelfTotalFee"])

        patient_telephone = []
        telephone = string_utils.xstr(row["Telephone"])
        cellphone = string_utils.xstr(row["Cellphone"])
        if telephone != "":
            patient_telephone.append(telephone)
        if cellphone != "":
            patient_telephone.append(cellphone)

        patient_telephone = ", ".join(patient_telephone)
        patient_address = string_utils.xstr(row["Address"])
        if (
            personnel_utils.get_permission(
                self.database, "病患資料", "遮蔽電話地址", self.user_name
            )
            == "Y"
        ):
            patient_telephone = "*" * len(patient_telephone)
            patient_address = "*" * len(patient_address)

        patient_remark = string_utils.get_str(row["PatientRemark"], "utf8")[:20]
        patient_remark = string_utils.replace_ascii_char(["\n"], patient_remark)
        share_type = string_utils.xstr(row["Share"])
        regist_type = string_utils.xstr(row["RegistType"])
        treat_type = string_utils.xstr(row["TreatType"])
        injury = string_utils.xstr(row["Injury"])
        visit = string_utils.xstr(row["Visit"])
        disease_name = case_utils.get_disease_name_all(row)

        treat_fee = (
            number_utils.get_integer(row["AcupunctureFee"])
            + number_utils.get_integer(row["MassageFee"])
            + number_utils.get_integer(row["DislocateFee"])
        )

        try:
            age_year, _ = date_utils.get_age(row["Birthday"], row["CDate"])
        except Exception:
            age_year = None

        tour_area = string_utils.xstr(row["TourArea"])
        if tour_area == "":
            tour_area = string_utils.xstr(row["NursingHome"])

        # tour_area = string_utils.shorten_middle(tour_area, 10)

        if tour_area == "":
            tour_area = "本院"

        try:
            doctor_done_time = row["DoctorDate"].strftime("%H:%M")
        except Exception:
            doctor_done_time = None

        case_date = string_utils.xstr(row["CaseDate"])
        birthday = string_utils.xstr(row["Birthday"])
        if self.system_settings.field("日期格式") == "民國年":
            case_date = date_utils.date_to_zh_tw_date(row["CaseDate"])
            try:
                birthday = date_utils.date_to_zh_tw_date(
                    string_utils.xstr(row["Birthday"])
                )
            except Exception:
                birthday = None

        medical_record = [
            case_key,
            None,
            None,
            None,
            case_date,
            string_utils.xstr(row["Period"]),
            None,
            doctor_done_time,
            None,
            row["Room"],
            row["RegistNo"],
            row["PatientKey"],
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["ID"]),
            string_utils.xstr(row["Gender"]),
            birthday,
            age_year,
            visit,
            regist_type[:4],
            tour_area,
            ins_type,
            apply_type,
            pharmacy_type,
            share_type[:4],
            treat_type,
            card,
            row["Continuance"],
            pres_days,
            string_utils.xstr(row["Doctor"]),
            disease_name,
            string_utils.xstr(row["Massager"]),
            number_utils.get_integer(row["RegistFee"]),
            number_utils.get_integer(row["SDiagShareFee"]),
            number_utils.get_integer(row["SDrugShareFee"]),
            number_utils.get_integer(row["TotalFee"]),
            number_utils.get_integer(row["DiscountFee"]),
            number_utils.get_integer(row["DiagFee"]),
            number_utils.get_integer(row["InterDrugFee"]),
            number_utils.get_integer(row["PharmacyFee"]),
            treat_fee,
            number_utils.get_integer(row["InsApplyFee"]),
            patient_telephone,
            patient_address,
            patient_remark,
            string_utils.xstr(row["InvoiceNo"]),
        ]

        self_prescript_count = self._get_self_prescript_count(case_key)

        self.ui.tableWidget_medical_record_list.setCellWidget(
            row_no, self.column["TreatType"], None
        )

        for col_no in range(len(medical_record)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medical_record[col_no])
            self.ui.tableWidget_medical_record_list.setItem(
                row_no,
                col_no,
                item,
            )
            if col_no in [
                self.column["Room"],
                self.column["RegistNo"],
                self.column["PatientKey"],
                self.column["Age"],
                self.column["PresDays"],
                self.column["RegistFee"],
                self.column["DiagShareFee"],
                self.column["DrugShareFee"],
                self.column["TotalFee"],
                self.column["DiscountFee"],
                self.column["DiagFee"],
                self.column["InterDrugFee"],
                self.column["PharmacyFee"],
                self.column["TreatFee"],
                self.column["InsApplyFee"],
            ]:
                self.ui.tableWidget_medical_record_list.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            elif col_no in [
                self.column["Period"],
                self.column["Gender"],
                self.column["Visit"],
                self.column["TourArea"],
                self.column["Course"],
                self.column["ApplyType"],
                self.column["PharmacyType"],
            ]:
                self.ui.tableWidget_medical_record_list.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

            if self_total_fee > 0 or self_prescript_count > 0 or ins_type == "自費":
                if treat_type == "民俗調理":
                    self.ui.tableWidget_medical_record_list.item(
                        row_no, col_no
                    ).setForeground(QtGui.QColor("brown"))
                else:
                    self.ui.tableWidget_medical_record_list.item(
                        row_no, col_no
                    ).setForeground(QtGui.QColor("blue"))

            if string_utils.xstr(row["TreatType"]) == "自購":
                self.ui.tableWidget_medical_record_list.item(
                    row_no, col_no
                ).setForeground(QtGui.QColor("darkGreen"))
            if string_utils.xstr(row["InProgress"]) == "Y":
                self.ui.tableWidget_medical_record_list.item(
                    row_no, col_no
                ).setForeground(QtGui.QColor("red"))

            if string_utils.xstr(row["ApplyType"]) == "不申報":
                self.ui.tableWidget_medical_record_list.item(
                    row_no, col_no
                ).setForeground(QtGui.QColor("gray"))

            if string_utils.xstr(row["TreatType"]) in nhi_utils.SPECIAL_CODE_DICT:
                self.ui.tableWidget_medical_record_list.item(
                    row_no, col_no
                ).setForeground(QtGui.QColor("magenta"))

            if is_closed:
                item = self.ui.tableWidget_medical_record_list.item(row_no, col_no)
                font = item.font()
                item.setForeground(QtGui.QColor("#2F4F4F"))  # DarkSlateGray
                font.setItalic(True)
                item.setFont(font)

        color = None
        col_no = self.column["Share"]
        if share_type == "榮民":
            color = "green"
        elif share_type in ["低收入戶", "中低收入戶"]:
            color = "darkMagenta"
        elif share_type == "山地離島":
            color = "magenta"
        elif share_type == "職業傷害":
            color = "brown"
        elif treat_type == "居家醫療":
            color = "red"
            col_no = self.column["TreatType"]

        if regist_type in nhi_utils.TOUR_TYPE + nhi_utils.LONG_TERM_CARE:
            color = "red"
            col_no = self.column["RegistType"]
        elif regist_type in nhi_utils.TELECOM_TYPE + nhi_utils.INFECTIOUS_TYPE:
            color = "green"
            col_no = self.column["RegistType"]
        elif regist_type in nhi_utils.SPECIAL_PHARMACY_TYPE:
            color = "darkMagenta"
            col_no = self.column["RegistType"]
        elif regist_type in nhi_utils.CORRECTION_REG_TYPE + nhi_utils.GOTO_LACK_AREA:
            color = "darkRed"
            col_no = self.column["RegistType"]

        if color is not None:
            self.ui.tableWidget_medical_record_list.item(row_no, col_no).setForeground(
                QtGui.QColor(color)
            )

        if number_utils.get_integer(pres_days) > 7:
            self.ui.tableWidget_medical_record_list.item(
                row_no, self.column["PresDays"]
            ).setForeground(QtGui.QColor("red"))
            if special_code != "":
                self.ui.tableWidget_medical_record_list.item(
                    row_no, self.column["DiseaseName"]
                ).setForeground(QtGui.QColor("red"))

        if visit == "初診":
            self.ui.tableWidget_medical_record_list.item(
                row_no, self.column["Visit"]
            ).setForeground(QtGui.QColor("red"))

        args = [injury]
        if case_utils.get_case_extend(self.database, case_key, "整合醫療照護") == "Y":
            args.append("整合醫療照護")

        self._set_treat_type(row_no, treat_type, *args)
        self._set_print_check_box(row_no)
        self._set_done_status(row, row_no)
        self._set_image_status(row, row_no)
        self._set_version_history(row, row_no)

    def _set_treat_type(self, row_no, treat_type, *args):
        col_no = self.column["TreatType"]

        set_extra_treat_type = False
        for arg in args:
            if arg not in ["主訴職災", "整合醫療照護"]:
                continue

            treat_type += f'<br><font size="2" color="red">({arg})</font>'
            set_extra_treat_type = True

        if not set_extra_treat_type:
            return

        self.ui.tableWidget_medical_record_list.setItem(row_no, col_no, None)

        treat_type_label = QtWidgets.QLabel()
        treat_type_label.setStyleSheet("padding: 1px")
        treat_type_label.setText(treat_type)
        self.ui.tableWidget_medical_record_list.setCellWidget(
            row_no, col_no, treat_type_label
        )

    def _set_print_check_box(self, row_no):
        check_box_print = QtWidgets.QCheckBox()
        check_box_print.setChecked(False)
        check_box_print.setStyleSheet("padding-left: 20px")
        col_no = self.column["PrintMark"]

        self.ui.tableWidget_medical_record_list.setCellWidget(
            row_no, col_no, check_box_print
        )
        self.ui.tableWidget_medical_record_list.item(row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _set_done_status(self, row, row_no):
        is_closed = bool(row["IsClosed"])
        if is_closed:
            case_utils.set_close_case_icon(
                self.ui.tableWidget_medical_record_list,
                row_no,
                self.column["DoctorDone"],
                is_closed,
            )
            return

        in_progress = string_utils.xstr(row["InProgress"])
        if in_progress == "Y":
            case_utils.set_in_progress_icon(
                self.ui.tableWidget_medical_record_list,
                row_no,
                self.column["DoctorDone"],
                in_progress,
            )
            return

        gtk_apply = "./icons/gtk-apply.svg"
        gtk_close = "./icons/gtk-close.svg"
        if (
            string_utils.xstr(row["DoctorDone"]) == "True"
            and row["DoctorDate"] is not None
        ):
            gtk_icon_file = gtk_apply
            property_value = True
        else:
            gtk_icon_file = gtk_close
            property_value = False

        ui_utils.set_table_widget_field_icon(
            self.ui.tableWidget_medical_record_list,
            row_no,
            self.column["DoctorDone"],
            gtk_icon_file,
            "doctor_done",
            property_value,
            self._done_button_clicked,
        )

        if (
            string_utils.xstr(row["ChargeDone"]) == "True"
            and row["ChargeDate"] is not None
            and row["ChargePeriod"] is not None
        ):
            gtk_icon_file = gtk_apply
            property_value = True
        else:
            gtk_icon_file = gtk_close
            property_value = False

        ui_utils.set_table_widget_field_icon(
            self.ui.tableWidget_medical_record_list,
            row_no,
            self.column["ChargeDone"],
            gtk_icon_file,
            "charge_done",
            property_value,
            self._done_button_clicked,
        )

    # 更改完診或批價狀態
    def _done_button_clicked(self):
        property_name = string_utils.get_str(
            self.sender().dynamicPropertyNames()[0], "utf-8"
        )

        row_no = self.ui.tableWidget_medical_record_list.currentRow()
        doctor_done = self.ui.tableWidget_medical_record_list.cellWidget(
            row_no, self.column["DoctorDone"]
        ).property(property_name)
        if doctor_done:
            return

        dialog = dialog_utils.get_dialog_medical_record_done(
            self,
            self.database,
            self.system_settings,
            self.table_widget_medical_record_list.field_value(self.column["CaseKey"]),
            property_name,
        )
        if dialog.exec_():
            self.refresh_medical_record()

        dialog.deleteLater()

    def _set_image_status(self, row, row_no):
        patient_key = string_utils.xstr(row["PatientKey"])
        sql = f"""
            SELECT ImageKey FROM images
            WHERE
                PatientKey = {patient_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self.ui.tableWidget_medical_record_list.setCellWidget(
                row_no, self.column["Image"], None
            )
            return

        gtk_icon_file = "./icons/camera-photo.png"
        property_value = True
        ui_utils.set_table_widget_field_icon(
            self.ui.tableWidget_medical_record_list,
            row_no,
            self.column["Image"],
            gtk_icon_file,
            "has_image",
            property_value,
            self._image_button_clicked,
        )

    def _set_version_history(self, row, row_no):
        case_key = string_utils.xstr(row["CaseKey"])
        sql = f"""
            SELECT BackupRecordsKey FROM backup_records
            WHERE
                TableName = "cases" AND
                KeyField = "CaseKey" AND
                KeyValue = {case_key} AND
                Deleter = "編輯備份"
            ORDER BY DeleteDateTime
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self.ui.tableWidget_medical_record_list.setCellWidget(
                row_no, self.column["VersionHistory"], None
            )
            return

        # gtk_icon_file = './icons/accessories-text-editor.png'
        gtk_icon_file = "./icons/stock_edit.svg"
        property_value = True
        ui_utils.set_table_widget_field_icon(
            self.ui.tableWidget_medical_record_list,
            row_no,
            self.column["VersionHistory"],
            gtk_icon_file,
            "has_version_history",
            property_value,
            self._version_history_button_clicked,
        )

    def _image_button_clicked(self):
        pass

    def _version_history_button_clicked(self):
        pass

    def delete_medical_record(self):
        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        row = self.database.select_record(
            f"SELECT IsClosed FROM cases WHERE CaseKey = {case_key}"
        )[0]
        if bool(row["IsClosed"]) is True:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "無法刪除",
                '<font size="5" color="red"><b>病歷資料已經關檔, 無法執行刪除作業.</b></font>',
                "",
            )
            return

        name = self.table_widget_medical_record_list.field_value(self.column["Name"])
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("刪除病歷資料")
        msg_box.setText(f"""
            <font size='4' color='red'>
                <b>確定刪除<font color='blue'> {name} </font>的病歷資料?</b>
            </font>
        """)
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        if self.user_name == "超級使用者":
            pass
        elif not system_utils.verify_confirm_code():
            return

        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        if case_key is None:
            return

        case_utils.backup_medical_record(
            self.database,
            case_key,
            self.system_settings.field("使用者"),
            datetime.datetime.now(),
        )  # 備份資料

        if self.system_settings.field("調整庫存量") == "即時調整":
            try:
                stock_utils.restore_prescript_quantity(self.database, case_key)
            except Exception:
                pass

        self._delete_medical_record(case_key)
        self._write_log(name)

        current_row = self.ui.tableWidget_medical_record_list.currentRow()
        self.ui.tableWidget_medical_record_list.removeRow(current_row)

    def _write_log(self, name):
        card = self.table_widget_medical_record_list.field_value(self.column["Card"])
        course = self.table_widget_medical_record_list.field_value(
            self.column["Course"]
        )

        card = card + f"-{course}" if number_utils.get_integer(course) >= 1 else card
        room = self.table_widget_medical_record_list.field_value(self.column["Room"])
        doctor = self.table_widget_medical_record_list.field_value(
            self.column["Doctor"]
        )
        log = f"{name}於{date_utils.now_to_str()}執行病歷刪除, 卡序:{card}, 主治醫師: {room}診{doctor}醫師"
        self._write_event_log("資料刪除", log)

    def _open_marked_records(self):
        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            self.ui.tableWidget_medical_record_list.setCurrentCell(row_no, 0)

            try:
                check_box_print_mark = (
                    self.ui.tableWidget_medical_record_list.cellWidget(
                        row_no, self.column["PrintMark"]
                    )
                )
                if not check_box_print_mark.isChecked():
                    continue
            except Exception:
                continue

            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            self.open_medical_record(case_key)

    def open_medical_record(self, case_key=None):
        if self.user_name == "超級使用者":
            pass
        elif (
            personnel_utils.get_permission(
                self.database, self.program_name, "調閱病歷", self.user_name
            )
            != "Y"
        ):
            if case_key is None:
                system_utils.show_message_box(
                    QMessageBox.Warning,
                    "權限不足",
                    f"<h3>{self.user_name}，您的權限[{self.program_name}:調閱病歷]未被授權，無法進入病歷.</h3>",
                    "請確認是否獲得調閱病歷的權限",
                )
            else:
                pass

            return

        if case_key is None:
            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )

        database = self._get_archive_database()
        self.parent.open_medical_record(case_key, "病歷查詢", archive_database=database)

    # 重新顯示資料 call from pymedical (call from here is not working)
    def refresh_medical_record(self, case_key=None):
        if case_key is None:
            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )

        if case_key in ["", None]:
            return

        row_no = self.ui.tableWidget_medical_record_list.currentRow()
        check_box_print_mark = self.ui.tableWidget_medical_record_list.cellWidget(
            row_no, self.column["PrintMark"]
        )
        checked = check_box_print_mark.isChecked()

        sql = f"""
            SELECT
                {self.get_select_fields()}
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
                LEFT JOIN wait ON wait.CaseKey = cases.CaseKey
            WHERE
                cases.CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        current_row = self.ui.tableWidget_medical_record_list.currentRow()
        self._set_table_data(current_row, row)

        check_box_print_mark = self.ui.tableWidget_medical_record_list.cellWidget(
            current_row, self.column["PrintMark"]
        )
        check_box_print_mark.setChecked(checked)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_medical_record_list(self):
        self.close_all()
        self.close_tab()

    # 列印掛號收據
    def _print_registration(self):
        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        self.print_registration_form("直接列印", case_key)

    # 列印掛號收據
    def _print_massage(self):
        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        printer_utils.print_massage_form(
            self, self.database, self.system_settings, case_key, "直接列印"
        )

    # 列印掛號收據
    def print_registration_form(self, printable, case_key=False):
        if not case_key:
            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )

        database = self._get_archive_database()
        printer_utils.print_regist_form(
            self, database, self.system_settings, case_key, printable
        )

    # 列印處方箋
    def print_prescript_form(self, case_key, print_type):
        database = self._get_archive_database()

        printer_utils.print_prescription_form(
            self, database, self.system_settings, case_key, print_type
        )

    # 列印費用收據
    def print_receipt_form(
        self, case_key, print_type, print_dosage=True, print_only_medicine_set2=False
    ):
        database = self._get_archive_database()

        printer_utils.print_receipt_form(
            self,
            database,
            self.system_settings,
            case_key,
            print_type,
            print_dosage=print_dosage,
            print_only_medicine_set2=print_only_medicine_set2,
        )

    # 列印其他收據1
    def print_misc_form(self, case_key, print_type):
        database = self._get_archive_database()

        printer_utils.print_misc_form(
            self, database, self.system_settings, case_key, print_type
        )

    # 列印其他收據2
    def print_misc_form2(self, case_key, print_type):
        database = self._get_archive_database()

        printer_utils.print_misc_form2(
            self, database, self.system_settings, case_key, print_type
        )

    # 列印其他收據3
    def print_misc_form3(self, case_key, print_type):
        database = self._get_archive_database()

        printer_utils.print_misc_form3(
            self, database, self.system_settings, case_key, print_type
        )

    # 列印藥袋
    def print_prescription_bag_form(self, case_key, print_type):
        database = self._get_archive_database()

        printer_utils.print_prescription_bag_form(
            self, database, self.system_settings, case_key, print_type
        )

    # 列印處方箋
    def _print_prescript(self):
        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        self.print_prescript_form(case_key, "選擇列印")

    # 列印註記掛號收據
    def _print_marked_registration_form(self):
        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            self.ui.tableWidget_medical_record_list.setCurrentCell(row_no, 0)

            try:
                check_box_print_mark = (
                    self.ui.tableWidget_medical_record_list.cellWidget(
                        row_no, self.column["PrintMark"]
                    )
                )
                if not check_box_print_mark.isChecked():
                    continue
            except Exception:
                continue

            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            self.print_registration_form("直接列印", case_key)

    # 列印註記健保處方箋
    def _print_marked_ins_prescript(self):
        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            self.ui.tableWidget_medical_record_list.setCurrentCell(row_no, 0)

            try:
                check_box_print_mark = (
                    self.ui.tableWidget_medical_record_list.cellWidget(
                        row_no, self.column["PrintMark"]
                    )
                )
                if not check_box_print_mark.isChecked():
                    continue
            except Exception:
                continue

            ins_type = self.table_widget_medical_record_list.field_value(
                self.column["InsType"]
            )
            if ins_type != "健保":
                continue

            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            self.print_prescript_form(case_key, "健保處方")

    # 列印註記健保費用收據
    def _print_marked_ins_receipt(self):
        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            self.ui.tableWidget_medical_record_list.setCurrentCell(row_no, 0)

            try:
                check_box_print_mark = (
                    self.ui.tableWidget_medical_record_list.cellWidget(
                        row_no, self.column["PrintMark"]
                    )
                )
                if not check_box_print_mark.isChecked():
                    continue
            except Exception:
                continue

            ins_type = self.table_widget_medical_record_list.field_value(
                self.column["InsType"]
            )
            if ins_type != "健保":
                continue

            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            self.print_receipt_form(case_key, "健保收據")

    # 列印註記健保處方箋
    def _print_marked_self_prescript(self):
        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            self.ui.tableWidget_medical_record_list.setCurrentCell(row_no, 0)

            try:
                check_box_print_mark = (
                    self.ui.tableWidget_medical_record_list.cellWidget(
                        row_no, self.column["PrintMark"]
                    )
                )
                if not check_box_print_mark.isChecked():
                    continue
            except Exception:
                continue

            # ins_type = self.table_widget_medical_record_list.field_value(self.column['InsType'])
            # if ins_type != '健保':
            #     continue

            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            self.print_prescript_form(case_key, "自費處方")

    # 列印註記健保費用收據
    def _print_marked_self_receipt(self):
        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            self.ui.tableWidget_medical_record_list.setCurrentCell(row_no, 0)

            try:
                check_box_print_mark = (
                    self.ui.tableWidget_medical_record_list.cellWidget(
                        row_no, self.column["PrintMark"]
                    )
                )
                if not check_box_print_mark.isChecked():
                    continue
            except Exception:
                continue

            # ins_type = self.table_widget_medical_record_list.field_value(self.column['InsType'])
            # if ins_type != '健保':
            #     continue

            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            self.print_receipt_form(case_key, "自費收據")

    # 列印註記健保費用收據1
    def _print_marked_self_receipt1(self):
        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            self.ui.tableWidget_medical_record_list.setCurrentCell(row_no, 0)

            try:
                check_box_print_mark = (
                    self.ui.tableWidget_medical_record_list.cellWidget(
                        row_no, self.column["PrintMark"]
                    )
                )
                if not check_box_print_mark.isChecked():
                    continue
            except Exception:
                continue

            # ins_type = self.table_widget_medical_record_list.field_value(self.column['InsType'])
            # if ins_type != '健保':
            #     continue

            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            self.print_receipt_form(case_key, "自費收據", print_only_medicine_set2=True)

    # 列印醫療收據
    def _print_receipt(self):
        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        self.print_receipt_form(case_key, "選擇列印")

    # 列印醫療收據
    def _print_non_dosage_receipt(self):
        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        self.print_receipt_form(case_key, "選擇列印", print_dosage=False)

    # 列印其他收據1
    def _print_misc(self):
        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        self.print_misc_form(case_key, "選擇列印")

    # 列印其他收據2
    def _print_misc2(self):
        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        self.print_misc_form2(case_key, "選擇列印")

    # 列印其他收據3
    def _print_misc3(self):
        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        self.print_misc_form3(case_key, "選擇列印")

    # 列印藥袋
    def _print_prescription_bag(self):
        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        self.print_prescription_bag_form(case_key, "選擇列印")

    def _set_check(self):
        sender_name = self.sender().objectName()
        if sender_name == "action_set_check":
            check = True
        else:
            check = False

        row_count = self.ui.tableWidget_medical_record_list.rowCount()
        for row_no in range(row_count):
            try:
                check_box = self.ui.tableWidget_medical_record_list.cellWidget(
                    row_no, self.column["PrintMark"]
                )
                check_box.setChecked(check)
            except Exception:
                continue

    def _set_block_check(self):
        row_count = self.ui.tableWidget_medical_record_list.rowCount()
        for row_no in range(row_count):
            try:
                check_box = self.ui.tableWidget_medical_record_list.cellWidget(
                    row_no, self.column["PrintMark"]
                )
                check_box.setChecked(False)
            except Exception:
                continue

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")

        row_count = self.ui.tableWidget_medical_record_list.rowCount()
        start_no, ok = input_dialog.getInt(
            self, "區段註記", "請輸入區段註記起始號", 1, 1, row_count, 1
        )
        if not ok:
            return

        end_no, ok = input_dialog.getInt(
            self,
            "區段註記",
            "請輸入區段註記結束號",
            row_count,
            1,
            row_count,
            self.column["PrintMark"],
        )
        if not ok:
            return

        for row_no in range(row_count):
            if row_no + 1 < start_no or row_no + 1 > end_no:
                continue

            check_box = self.ui.tableWidget_medical_record_list.cellWidget(
                row_no, self.column["PrintMark"]
            )
            if check_box is None:
                continue

            check_box.setChecked(True)

    # 列印實體病歷 (病歷摘要)
    def _print_cases(self, print_self_prescript=False, print_patient=True):
        database = self._get_archive_database()

        row_count = self.ui.tableWidget_medical_record_list.rowCount()
        patient_key = self.ui.tableWidget_medical_record_list.item(
            0, self.column["PatientKey"]
        ).text()

        for row_no in range(1, row_count):  # 檢查是否同一病患
            try:
                check_box = self.ui.tableWidget_medical_record_list.cellWidget(
                    row_no, self.column["PrintMark"]
                )
                if not check_box.isChecked():
                    continue
            except Exception:
                continue

            next_patient_key = self.ui.tableWidget_medical_record_list.item(
                row_no, self.column["PatientKey"]
            )
            if next_patient_key is None:
                break
            else:
                next_patient_key = next_patient_key.text()
                if patient_key != next_patient_key:
                    patient_key = None
                    break

        case_key_list = []
        for row_no in range(row_count):
            try:
                check_box = self.ui.tableWidget_medical_record_list.cellWidget(
                    row_no, self.column["PrintMark"]
                )
                if check_box.isChecked():
                    case_key_list.append(
                        self.ui.tableWidget_medical_record_list.item(
                            row_no, self.column["CaseKey"]
                        ).text()
                    )
            except AttributeError:
                continue

        if len(case_key_list) <= 0:
            return

        if patient_key is not None:
            patient_key_condition = f"AND PatientKey = {patient_key}"
        else:
            patient_key_condition = ""

        case_key_list = ",".join(case_key_list)
        sql = f"""
            SELECT * FROM cases
            WHERE
                CaseKey IN({case_key_list})
                {patient_key_condition}
            ORDER BY PatientKey, CaseDate
        """

        sender_name = self.sender().objectName()

        if sender_name in [
            "action_print_cases",
            "action_print_cases2",
            "action_print_cases3",
        ]:
            if not print_patient:
                patient_key = None

            printer_utils.print_form_medical_records(
                self,
                database,
                self.system_settings,
                patient_key,
                sql,
                None,
                None,
                print_self_prescript=print_self_prescript,
            )
        elif sender_name in ["action_print_cases_without_treat"]:
            printer_utils.print_form_medical_records(
                self,
                database,
                self.system_settings,
                patient_key,
                sql,
                None,
                None,
                print_self_prescript=print_self_prescript,
                print_treat_item=False,
            )
        else:
            printer_utils.print_form_medical_records(
                self,
                database,
                self.system_settings,
                patient_key,
                sql,
                None,
                None,
                print_type="pdf_by_dialog",
                print_treat_item=True,
            )

    def _print_fees(self):
        row_count = self.ui.tableWidget_medical_record_list.rowCount()
        patient_key = self.ui.tableWidget_medical_record_list.item(
            0, self.column["PatientKey"]
        ).text()

        for row_no in range(1, row_count):  # 檢查是否同一病患
            try:
                check_box = self.ui.tableWidget_medical_record_list.cellWidget(
                    row_no, self.column["PrintMark"]
                )
                if not check_box.isChecked():
                    continue
            except Exception:
                continue

            next_patient_key = self.ui.tableWidget_medical_record_list.item(
                row_no, self.column["PatientKey"]
            )
            if next_patient_key is None:
                break
            else:
                next_patient_key = next_patient_key.text()
                if patient_key != next_patient_key:
                    patient_key = None
                    break

        case_key_list = []
        for row_no in range(row_count):
            try:
                check_box = self.ui.tableWidget_medical_record_list.cellWidget(
                    row_no, self.column["PrintMark"]
                )
                if check_box.isChecked():
                    case_key_list.append(
                        self.ui.tableWidget_medical_record_list.item(
                            row_no, self.column["CaseKey"]
                        ).text()
                    )
            except Exception:
                continue

        if len(case_key_list) <= 0:
            return

        if patient_key is not None:
            patient_key_condition = f"AND PatientKey = {patient_key}"
        else:
            patient_key_condition = ""

        case_key_list = ",".join(case_key_list)
        sql = f"""
            SELECT * FROM cases
            WHERE
                CaseKey IN({case_key_list})
                {patient_key_condition}
            ORDER BY CaseKey
        """

        sender_name = self.sender().objectName()
        database = self._get_archive_database()
        if sender_name == "action_print_fees":
            printer_utils.print_form_medical_fees(
                self,
                database,
                self.system_settings,
                patient_key,
                sql,
            )
        else:
            printer_utils.print_form_medical_fees(
                self,
                database,
                self.system_settings,
                patient_key,
                sql,
                "pdf_by_dialog",
            )

    # 匯出病歷資料 2019.10.14
    def _export_medical_record_to_excel(self):
        options = QFileDialog.Options()
        start_date = self.dialog_setting["start_date"].toString("yyyy-MM-dd")
        end_date = self.dialog_setting["end_date"].toString("yyyy-MM-dd")
        person = self.dialog_setting["person"]
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出病歷資料",
            f"{start_date}至{end_date}{person}病歷資料.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_medical_record_list,
            [
                self.column["CaseKey"],
                self.column["Image"],
                self.column["VersionHistory"],
                self.column["PrintMark"],
                self.column["DoctorDone"],
                self.column["ChargeDone"],
            ],
            [
                self.column["PresDays"],
                self.column["RegistFee"],
                self.column["DiagShareFee"],
                self.column["DrugShareFee"],
                self.column["TotalFee"],
                self.column["DiagFee"],
                self.column["InterDrugFee"],
                self.column["PharmacyFee"],
                self.column["TreatFee"],
                self.column["InsApplyFee"],
            ],
            f"{start_date}至{end_date}{person}病歷資料",
            calc_total=False,
        )
        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>病歷資料{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    # 匯出註記病歷資料 2023.10.28
    def _export_marked_medical_record_to_excel(self):
        options = QFileDialog.Options()
        start_date = self.dialog_setting["start_date"].toString("yyyy-MM-dd")
        end_date = self.dialog_setting["end_date"].toString("yyyy-MM-dd")
        person = self.dialog_setting["person"]
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出註記病歷資料",
            f"{start_date}至{end_date}{person}註記病歷資料.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_medical_record_list,
            [
                self.column["CaseKey"],
                self.column["Image"],
                self.column["VersionHistory"],
                self.column["PrintMark"],
                self.column["DoctorDone"],
                self.column["ChargeDone"],
            ],
            [
                self.column["PresDays"],
                self.column["RegistFee"],
                self.column["DiagShareFee"],
                self.column["DrugShareFee"],
                self.column["TotalFee"],
                self.column["DiagFee"],
                self.column["InterDrugFee"],
                self.column["PharmacyFee"],
                self.column["TreatFee"],
                self.column["InsApplyFee"],
            ],
            f"{start_date}至{end_date}{person}註記病歷資料",
            calc_total=False,
            mark_col_no=1,
        )
        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>病歷資料{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    # 匯出病歷診斷資料 2020.08.20
    def _export_medical_record_diagnosis_excel(self):
        options = QFileDialog.Options()
        start_date = self.dialog_setting["start_date"].toString("yyyy-MM-dd")
        end_date = self.dialog_setting["end_date"].toString("yyyy-MM-dd")
        person = self.dialog_setting["person"]
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出病歷診斷資料",
            f"{start_date}至{end_date}{person}病歷診斷資料.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        database = self._get_archive_database()
        export_utils.export_medical_record_diagnosis_excel(
            database,
            excel_file_name,
            self.ui.tableWidget_medical_record_list,
            f"{start_date}至{end_date}{person}病歷診斷資料",
        )
        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>病歷診斷資料{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def _get_medical_record_rows(self):
        database = self._get_archive_database()

        medical_record_rows = []
        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            try:
                check_box = self.ui.tableWidget_medical_record_list.cellWidget(
                    row_no, 1
                )
                if not check_box.isChecked():
                    continue
            except Exception:
                continue

            case_key = self.ui.tableWidget_medical_record_list.item(row_no, 0).text()
            sql = f"""
                SELECT
                    cases.DepositFee, cases.Massager, patient.DiscountType, cases.DiscountFee
                FROM cases
                    LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
                WHERE
                    CaseKey = {case_key}
            """
            case_row = database.select_record(sql)
            if len(case_row) > 0:
                case_row = case_row[0]
                deposit_fee = number_utils.get_integer(case_row["DepositFee"])
                discount_fee = number_utils.get_integer(case_row["DiscountFee"])
                massager = string_utils.xstr(case_row["Massager"])
                discount_type = string_utils.xstr(case_row["DiscountType"])
            else:
                deposit_fee = 0
                discount_fee = 0
                massager = ""
                discount_type = ""

            case_date = self.ui.tableWidget_medical_record_list.item(
                row_no, self.column["CaseDate"]
            ).text()[:10]
            period = self.ui.tableWidget_medical_record_list.item(
                row_no, self.column["Period"]
            ).text()[:1]
            next_case_date = self.ui.tableWidget_medical_record_list.item(
                row_no + 1, self.column["CaseDate"]
            )
            if next_case_date is not None:
                next_case_date = next_case_date.text()[:10]

            next_period = self.ui.tableWidget_medical_record_list.item(
                row_no + 1, self.column["Period"]
            )
            if next_period is not None:
                next_period = next_period.text()[:1]

            ins_type = self.ui.tableWidget_medical_record_list.item(
                row_no, self.column["InsType"]
            ).text()
            try:
                treat_type = self.ui.tableWidget_medical_record_list.item(
                    row_no, self.column["TreatType"]
                ).text()
            except Exception:
                treat_type = ""

            card = self.ui.tableWidget_medical_record_list.item(
                row_no, self.column["Card"]
            ).text()
            if card in ["免卡", None]:
                card = ""

            regist_fee = number_utils.get_integer(
                self.ui.tableWidget_medical_record_list.item(
                    row_no, self.column["RegistFee"]
                ).text()
            )
            diag_share_fee = number_utils.get_integer(
                self.ui.tableWidget_medical_record_list.item(
                    row_no, self.column["DiagShareFee"]
                ).text()
            )
            drug_share_fee = number_utils.get_integer(
                self.ui.tableWidget_medical_record_list.item(
                    row_no, self.column["DrugShareFee"]
                ).text()
            )
            total_fee = number_utils.get_integer(
                self.ui.tableWidget_medical_record_list.item(
                    row_no, self.column["TotalFee"]
                ).text()
            )
            doctor = self.ui.tableWidget_medical_record_list.item(
                row_no, self.column["Doctor"]
            ).text()
            patient_key = self.ui.tableWidget_medical_record_list.item(
                row_no, self.column["PatientKey"]
            ).text()
            name = self.ui.tableWidget_medical_record_list.item(
                row_no, self.column["Name"]
            ).text()
            regist_no = self.ui.tableWidget_medical_record_list.item(
                row_no, self.column["RegistNo"]
            ).text()
            course = self.ui.tableWidget_medical_record_list.item(
                row_no, self.column["Course"]
            ).text()

            row = {
                "CaseKey": case_key,
                "CaseDate": case_date,
                "Period": period,
                "NextCaseDate": next_case_date,
                "NextPeriod": next_period,
                "InsType": ins_type,
                "TreatType": treat_type,
                "Card": card,
                "RegistFee": regist_fee,
                "DiagShareFee": diag_share_fee,
                "DrugShareFee": drug_share_fee,
                "DepositFee": deposit_fee,
                "Massager": massager,
                "DiscountType": discount_type,
                "DiscountFee": discount_fee,
                "Doctor": doctor,
                "PatientKey": patient_key,
                "Name": name,
                "RegistNo": regist_no,
                "Course": course,
                "TotalFee": total_fee,
            }
            medical_record_rows.append(row)

        return medical_record_rows

    # 匯出日報表 2019.07.01
    def _export_to_excel(self):
        options = QFileDialog.Options()
        start_date = self.dialog_setting["start_date"].toString("yyyy-MM-dd")
        end_date = self.dialog_setting["end_date"].toString("yyyy-MM-dd")
        person = self.dialog_setting["person"]
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出日報表",
            f"{start_date}至{end_date}{person}門診日報表.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        database = self._get_archive_database()
        medical_record_rows = self._get_medical_record_rows()

        export_utils.export_daily_medical_records_to_excel(
            database,
            self.system_settings,
            excel_file_name,
            medical_record_rows,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>門診日報表{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    # 匯出JSON 2019.09.26
    def _export_to_json(self):
        options = QFileDialog.Options()
        start_date = self.dialog_setting["start_date"].toString("yyyy-MM-dd")
        end_date = self.dialog_setting["end_date"].toString("yyyy-MM-dd")
        json_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出JSON檔案",
            f"{start_date}至{end_date}病歷資料.json",
            "json檔案 (*.json)",
            options=options,
        )
        if not json_file_name:
            return

        database = self._get_archive_database()
        row_count = self.ui.tableWidget_medical_record_list.rowCount()
        case_key_list = []
        for row_no in range(row_count):
            try:
                check_box = self.ui.tableWidget_medical_record_list.cellWidget(
                    row_no, self.column["PrintMark"]
                )
                if not check_box.isChecked():
                    continue
            except AttributeError:
                continue

            case_key = self.ui.tableWidget_medical_record_list.item(
                row_no, self.column["CaseKey"]
            ).text()
            case_key_list.append(case_key)

        if len(case_key_list) <= 0:
            return

        db_utils.export_medical_record_to_json(
            self, database, json_file_name, case_key_list
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "JSON資料匯出完成",
            f"<h3>病歷資料 {json_file_name}匯出完成.</h3>",
            "JSON 檔案格式.",
        )

        log = f"{date_utils.now_to_str()}匯出JSON檔案, 檔案名稱: {json_file_name}"
        self._write_event_log("JSON資料匯出", log)

    def _write_event_log(self, log_type, log):
        log_utils.write_event_log(
            self.database,
            self.system_settings.field("使用者"),
            log_type,
            self.program_name,
            log,
        )

    def _table_widget_medical_record_key_press(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Return or key == QtCore.Qt.Key_Enter:
            self.open_medical_record()

        return QtWidgets.QTableWidget.keyPressEvent(
            self.ui.tableWidget_medical_record_list, event
        )

    def _change_ins_type(self):
        items = nhi_utils.INS_TYPE
        ins_type, ok = QInputDialog.getItem(
            self, "更改保險類別", "請選擇保險類別, 更改前請先註記病歷", items, 0, False
        )

        if not ok:
            return

        database = self._get_archive_database()
        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            self.ui.tableWidget_medical_record_list.setCurrentCell(row_no, 0)

            try:
                change_mark = self.ui.tableWidget_medical_record_list.cellWidget(
                    row_no, self.column["PrintMark"]
                )
                if not change_mark.isChecked():
                    continue
            except Exception:
                continue

            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            database.exec_sql(f'''
                UPDATE cases
                SET
                    InsType = "{ins_type}"
                WHERE
                    CaseKey = {case_key}
            ''')
            self.refresh_medical_record(case_key)

    def _change_apply_type(self):
        items = nhi_utils.APPLY_TYPE
        apply_type, ok = QInputDialog.getItem(
            self,
            "醫療費用申報方式",
            "請選擇醫療費用申報方式, 更改前請先註記病歷",
            items,
            0,
            False,
        )

        if not ok:
            return

        database = self._get_archive_database()
        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            self.ui.tableWidget_medical_record_list.setCurrentCell(row_no, 0)

            try:
                change_mark = self.ui.tableWidget_medical_record_list.cellWidget(
                    row_no, self.column["PrintMark"]
                )
                if not change_mark.isChecked():
                    continue
            except Exception:
                continue

            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            database.exec_sql(f'''
                UPDATE cases
                SET
                    ApplyType = "{apply_type}"
                WHERE
                    CaseKey = {case_key}
            ''')
            self.refresh_medical_record(case_key)

    def _change_pharmacy_type(self):
        items = ["申報", "不申報"]
        pharmacy_type, ok = QInputDialog.getItem(
            self,
            "調劑費申報方式",
            "請選擇調劑費申報方式, 更改前請先註記病歷",
            items,
            0,
            False,
        )

        if not ok:
            return

        database = self._get_archive_database()
        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            self.ui.tableWidget_medical_record_list.setCurrentCell(row_no, 0)

            try:
                change_mark = self.ui.tableWidget_medical_record_list.cellWidget(
                    row_no, self.column["PrintMark"]
                )
                if not change_mark.isChecked():
                    continue
            except Exception:
                continue

            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            database.exec_sql(f'''
                UPDATE cases
                SET
                    PharmacyType = "{pharmacy_type}"
                WHERE
                    CaseKey = {case_key}
            ''')
            self.refresh_medical_record(case_key)

    def _change_injury_type(self):
        items = ["申報", "不申報"]
        injury_type, ok = QInputDialog.getItem(
            self,
            "主訴職災申報方式",
            "請選擇主訴職災申報方式, 更改前請先註記病歷",
            items,
            0,
            False,
        )

        if not ok:
            return

        if injury_type == "申報":
            injury_type = "主訴職災"
        else:
            injury_type = "普通疾病"

        database = self._get_archive_database()
        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            self.ui.tableWidget_medical_record_list.setCurrentCell(row_no, 0)

            try:
                change_mark = self.ui.tableWidget_medical_record_list.cellWidget(
                    row_no, self.column["PrintMark"]
                )
                if not change_mark.isChecked():
                    continue
            except Exception:
                continue

            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            database.exec_sql(f'''
                UPDATE cases
                SET
                    Injury = "{injury_type}"
                WHERE
                    CaseKey = {case_key}
            ''')
            self.refresh_medical_record(case_key)

    def _change_doctor(self):
        items = personnel_utils.get_person(self.database, "醫師")
        doctor, ok = QInputDialog.getItem(
            self,
            "變更主治醫師",
            "請選擇主治醫師姓名, 更改前請先註記病歷",
            items,
            0,
            False,
        )

        if not ok:
            return

        database = self._get_archive_database()
        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            self.ui.tableWidget_medical_record_list.setCurrentCell(row_no, 0)

            try:
                change_mark = self.ui.tableWidget_medical_record_list.cellWidget(
                    row_no, self.column["PrintMark"]
                )
                if not change_mark.isChecked():
                    continue
            except Exception:
                continue

            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            database.exec_sql(f'''
                UPDATE cases
                SET
                    Doctor = "{doctor}"
                WHERE
                    CaseKey = {case_key}
            ''')
            self.refresh_medical_record(case_key)

    def _header_clicked(self, col_no):
        if col_no != self.column["PrintMark"]:
            return

        row_count = self.ui.tableWidget_medical_record_list.rowCount()
        for row_no in range(row_count):
            try:
                check_box = self.ui.tableWidget_medical_record_list.cellWidget(
                    row_no, col_no
                )
                check_box.setChecked(not check_box.isChecked())
            except AttributeError:
                continue

    def _set_traditional_health_case(self):
        database = self._get_archive_database()

        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        ins_type = self.table_widget_medical_record_list.field_value(
            self.column["InsType"]
        )
        if ins_type == "健保":
            case_utils.write_traditional_health_care(
                database,
                self.system_settings,
                case_key,
                traditional_health_care_fee=None,
                massager=None,
            )
            self._read_medical_record_list(self.sql, self.medicine_list)

    def _generate_security(self):
        card = self.table_widget_medical_record_list.field_value(self.column["Card"])
        if card not in nhi_utils.ABNORMAL_CARD_DICT:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "簽章錯誤",
                '<font size="5" color="red"><b>此病歷資料非異常卡序病歷, 不可動態產生產生異常卡序安全簽章.</b></font>',
                "請檢查卡序是否正確.",
            )
            return

        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )

        security = case_utils.create_security_xml()
        upload_type = "2"
        treat_after_check = "1"  # 補卡註記
        security = case_utils.update_xml_doc(security, "upload_type", upload_type)
        security = case_utils.update_xml_doc(
            security, "treat_after_check", treat_after_check
        )
        security = security.decode("utf-8")

        database = self._get_archive_database()
        sql = f"""
            UPDATE cases
            SET
                Security = '{security}'
            WHERE
                CaseKey = {case_key}
        """
        database.exec_sql(sql)
        system_utils.show_message_box(
            QMessageBox.Information,
            "簽章完成",
            '<font size="5" color="red"><b>異常卡序安全簽章產生成功.</b></font>',
            "請檢查安全簽章是否正確.",
        )

    def _print_correction_reg_income(self):
        printer_utils.print_correction_reg_income(
            self.parent,
            self.database,
            self.system_settings,
            self.ui.tableWidget_medical_record_list,
            self.column,
        )

    # 匯出矯正機構入文字檔 2025.11.12
    def _export_correction_reg_income_txt(self):
        options = QFileDialog.Options()
        start_date = self.dialog_setting["start_date"].toString("yyyy-MM-dd")
        end_date = self.dialog_setting["end_date"].toString("yyyy-MM-dd")
        person = self.dialog_setting["person"]
        txt_filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出矯正機關現金日報表TXT",
            f"{start_date}至{end_date}矯正機關現金日報表.txt",
            "Text Files (*.txt)",
            options=options,
        )
        if not txt_filename:
            return

        export_utils.export_correction_reg_income_txt(
            self.database,
            self.system_settings,
            txt_filename,
            self.ui.tableWidget_medical_record_list,
            self.column,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>矯正機關現金日報表{txt_filename}匯出完成.</h3>",
            "txt 格式.",
        )

    def _calculate_total(self):
        row_count = self.ui.tableWidget_medical_record_list.rowCount()
        regist_fee, diag_share_fee, drug_share_fee, total_fee = 0, 0, 0, 0
        diag_fee, inter_drug_fee, pharmacy_fee, treat_fee, ins_apply_fee = 0, 0, 0, 0, 0
        discount_fee = 0

        for row_no in range(row_count):
            try:
                regist_fee += number_utils.get_integer(
                    self.ui.tableWidget_medical_record_list.item(
                        row_no, self.column["RegistFee"]
                    ).text()
                )
            except Exception:
                pass

            try:
                diag_share_fee += number_utils.get_integer(
                    self.ui.tableWidget_medical_record_list.item(
                        row_no, self.column["DiagShareFee"]
                    ).text()
                )
            except Exception:
                pass

            try:
                drug_share_fee += number_utils.get_integer(
                    self.ui.tableWidget_medical_record_list.item(
                        row_no, self.column["DrugShareFee"]
                    ).text()
                )
            except Exception:
                pass

            try:
                total_fee += number_utils.get_integer(
                    self.ui.tableWidget_medical_record_list.item(
                        row_no, self.column["TotalFee"]
                    ).text()
                )
            except Exception:
                pass

            try:
                discount_fee += number_utils.get_integer(
                    self.ui.tableWidget_medical_record_list.item(
                        row_no, self.column["DiscountFee"]
                    ).text()
                )
            except Exception:
                pass

            try:
                diag_fee += number_utils.get_integer(
                    self.ui.tableWidget_medical_record_list.item(
                        row_no, self.column["DiagFee"]
                    ).text()
                )
            except Exception:
                pass

            try:
                inter_drug_fee += number_utils.get_integer(
                    self.ui.tableWidget_medical_record_list.item(
                        row_no, self.column["InterDrugFee"]
                    ).text()
                )
            except Exception:
                pass

            try:
                pharmacy_fee += number_utils.get_integer(
                    self.ui.tableWidget_medical_record_list.item(
                        row_no, self.column["PharmacyFee"]
                    ).text()
                )
            except Exception:
                pass

            try:
                treat_fee += number_utils.get_integer(
                    self.ui.tableWidget_medical_record_list.item(
                        row_no, self.column["TreatFee"]
                    ).text()
                )
            except Exception:
                pass

            try:
                ins_apply_fee += number_utils.get_integer(
                    self.ui.tableWidget_medical_record_list.item(
                        row_no, self.column["InsApplyFee"]
                    ).text()
                )
            except Exception:
                pass

        total_record = [
            None,
            None,
            None,
            None,
            "合計",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            string_utils.xstr(regist_fee),
            string_utils.xstr(diag_share_fee),
            string_utils.xstr(drug_share_fee),
            string_utils.xstr(total_fee),
            string_utils.xstr(discount_fee),
            string_utils.xstr(diag_fee),
            string_utils.xstr(inter_drug_fee),
            string_utils.xstr(pharmacy_fee),
            string_utils.xstr(treat_fee),
            string_utils.xstr(ins_apply_fee),
        ]

        self.ui.tableWidget_medical_record_list.setRowCount(row_count + 1)

        font = QtGui.QFont()
        font.setBold(True)
        for col_no in range(len(total_record)):
            self.ui.tableWidget_medical_record_list.setItem(
                row_count, col_no, QtWidgets.QTableWidgetItem(total_record[col_no])
            )
            if col_no in [
                self.column["RegistFee"],
                self.column["DiagShareFee"],
                self.column["DrugShareFee"],
                self.column["TotalFee"],
                self.column["DiagFee"],
                self.column["InterDrugFee"],
                self.column["PharmacyFee"],
                self.column["TreatFee"],
                self.column["InsApplyFee"],
            ]:
                self.ui.tableWidget_medical_record_list.item(
                    row_count, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.ui.tableWidget_medical_record_list.item(row_count, col_no).setFont(
                font
            )

        self.ui.tableWidget_medical_record_list.resizeColumnsToContents()

    def _show_all_cases(self):
        if self.system_settings.field("病歷查詢預設健保") != "Y":
            return

        keyword = 'AND cases.InsType = "健保"'
        if keyword not in self.sql:
            keyword = ' cases.InsType = "健保" AND '
            if keyword not in self.sql:
                return

        self.sql = self.sql.replace(keyword, "")
        self.sql = self.sql.replace(
            "AND (Position1 IS NULL OR LENGTH(Position1) = 0)", ""
        )
        rows = self.database.select_record(self.sql)
        self.medical_record_rows = len(rows)
        self._read_medical_record_list(self.sql, self.medicine_list)

    def open_ins_medical_record(self):
        if self.user_name == "超級使用者":
            pass
        elif (
            personnel_utils.get_permission(
                self.database, self.program_name, "調閱病歷", self.user_name
            )
            != "Y"
        ):
            system_utils.show_message_box(
                QMessageBox.Warning,
                "權限不足",
                f"<h3>{self.user_name}，您的權限[{self.program_name}:調閱病歷]未被授權，無法進入病歷.</h3>",
                "請確認是否獲得調閱病歷的權限",
            )

            return

        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )

        database = self._get_archive_database()
        self.parent.open_medical_record(
            case_key, "病歷查詢健保病歷", archive_database=database
        )

    def _print_referral_form(self):
        database = self._get_archive_database()
        patient_key = self.table_widget_medical_record_list.field_value(
            self.column["PatientKey"]
        )
        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )

        printer_utils.print_referral_form(
            self, database, self.system_settings, patient_key, case_key, None
        )

    def _is_today(self):
        today = date_utils.date_to_str()
        case_date = self.table_widget_medical_record_list.field_value(
            self.column["CaseDate"]
        )[:10]
        if case_date != today:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "ic卡作業錯誤",
                '<font size="5" color="red"><b>非今日門診病歷, 不得執行IC卡作業.</b></font>',
                "只有今日門診病歷才能執行IC卡各項作業.",
            )
            return False
        else:
            return True

    def _write_ic_treatment(self):
        if not self._is_today():
            return

        name = self.table_widget_medical_record_list.field_value(self.column["Name"])
        msg_box = dialog_utils.get_message_box(
            "寫入健保卡就醫資料",
            QMessageBox.Question,
            f"<h3>確定寫入{name}的健保卡就醫資料?</h3>",
            "注意! 請插入健保卡!",
        )
        write_ic_card = msg_box.exec_()
        if not write_ic_card:
            return

        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        patient_key = self.table_widget_medical_record_list.field_value(
            self.column["PatientKey"]
        )
        card = self.table_widget_medical_record_list.field_value(self.column["Card"])

        if card == "":
            self._rewrite_ic_card()
            self.refresh_medical_record()
            return

        ic_card_type = case_utils.get_ic_card_type(self.database, case_key)
        if ic_card_type == "虛擬健保卡":
            ic_card = class_utils.get_vhccshis(
                self, self.database, self.system_settings, None
            )
        else:
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)

        if not ic_card.insert_correct_ic_card(patient_key):
            return

        ic_card.write_ic_medical_record(case_key, cshis_utils.NORMAL_CARD)
        self.refresh_medical_record()

    def _rewrite_ic_card(self):
        if not self._is_today():
            return

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
            "請注意! 如果要取得新卡序, 請先修正掛號資料, 將原來的卡序清除, 這樣才會產生新的卡序，否則只會重寫診療及醫令資料."
        )
        msg_box.addButton(QPushButton("重新寫入"), QMessageBox.YesRole)
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        cancel = msg_box.exec_()
        if cancel:
            return

        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        patient_key = self.table_widget_medical_record_list.field_value(
            self.column["PatientKey"]
        )
        share_type = self.table_widget_medical_record_list.field_value(
            self.column["Share"]
        )
        card = self.table_widget_medical_record_list.field_value(self.column["Card"])
        course = number_utils.get_integer(
            self.table_widget_medical_record_list.field_value(self.column["Course"])
        )

        if course == 0:
            course = None

        ic_card_type = case_utils.get_ic_card_type(self.database, case_key)
        if ic_card_type == "虛擬健保卡":
            ic_card = class_utils.get_vhccshis(
                self, self.database, self.system_settings, None
            )
        else:
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)

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
        self.update_wait_by_ic_card(ic_card, case_key)
        self.refresh_medical_record()

    def update_cases_by_ic_card(self, ic_card, case_key, original_card, course):
        if ic_card is None:
            return

        fields = [
            "Card",
            "Continuance",
            "Security",
        ]
        card = string_utils.xstr(ic_card.treat_data["seq_number"])
        if card == "":
            card = original_card

        security = case_utils.treat_data_to_xml(ic_card.treat_data)

        treat_after_check = "1"  # 1:正常 2:補卡
        security = case_utils.update_xml_doc(
            security, "treat_after_check", treat_after_check
        )
        security = case_utils.update_xml_doc(
            security, "prescript_sign_time", date_utils.now_to_str()
        )
        security = case_utils.update_xml_doc(security, "upload_type", "1")
        data = [
            card,
            course,
            security,
        ]
        self.database.update_record("cases", fields, "CaseKey", case_key, data)

    def update_wait_by_ic_card(self, ic_card, case_key):
        if ic_card is None:
            return

        card = ic_card.treat_data["seq_number"]
        sql = f'''
            UPDATE wait
            SET
                Card = "{card}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

    def _rewrite_ic_prescript(self):
        if not self._is_today():
            return

        name = self.table_widget_medical_record_list.field_value(self.column["Name"])
        msg_box = dialog_utils.get_message_box(
            "重新寫入健保卡醫令資料",
            QMessageBox.Question,
            f"<h3>確定重新寫入{name}的健保卡醫令資料?</h3>",
            "注意！請插入健保卡!",
        )
        write_ic_card = msg_box.exec_()
        if not write_ic_card:
            return

        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
        patient_key = self.table_widget_medical_record_list.field_value(
            self.column["PatientKey"]
        )

        ic_card_type = case_utils.get_ic_card_type(self.database, case_key)
        if ic_card_type == "虛擬健保卡":
            ic_card = class_utils.get_vhccshis(
                self, self.database, self.system_settings, None
            )
        else:
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)

        if not ic_card.insert_correct_ic_card(patient_key):
            return

        ic_card.rewrite_ic_prescript(case_key)
        self.refresh_medical_record()

    def _cancel_ic_card(self):
        if not self._is_today():
            return

        name = self.table_widget_medical_record_list.field_value(self.column["Name"])
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

        case_key = self.table_widget_medical_record_list.field_value(
            self.column["CaseKey"]
        )
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
            self.database.delete_record("wait", "CaseKey", case_key)
            return

        ic_card_type = case_utils.get_ic_card_type(self.database, case_key)
        if ic_card_type == "虛擬健保卡":
            ic_card = class_utils.get_vhccshis(
                self, self.database, self.system_settings, None
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
            self._delete_medical_record(case_key)
            self._write_log(name)
            current_row = self.ui.tableWidget_medical_record_list.currentRow()
            self.ui.tableWidget_medical_record_list.removeRow(current_row)

    def _delete_medical_record(self, case_key):
        self.database.delete_record("wait", "CaseKey", case_key)
        self.database.delete_record("cases", "CaseKey", case_key)
        self.database.delete_record("prescript", "CaseKey", case_key)
        self.database.delete_record("dosage", "CaseKey", case_key)
        self.database.delete_record("deposit", "CaseKey", case_key)
        self.database.delete_record("debt", "CaseKey", case_key)

    def _print_medical_certificate(self):
        row_no = self.ui.tableWidget_medical_record_list.currentRow()
        case_key = self.ui.tableWidget_medical_record_list.item(
            row_no, self.column["CaseKey"]
        ).text()
        database = self._get_archive_database()
        printer_utils.print_form_medical_certificate(
            self,
            database,
            self.system_settings,
            case_key,
        )

    # 匯出病歷至word
    def _export_case_to_word(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d")
        default_filename = f"{now}匯出病歷.docx"
        filename = dialog_utils.get_save_dialog_filename(
            self, "匯出病歷", default_filename
        )

        if not filename:
            return

        case_key_list = []
        current_row_no = self.ui.tableWidget_medical_record_list.currentRow()

        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            self.ui.tableWidget_medical_record_list.setCurrentCell(row_no, 0)

            try:
                check_box_print_mark = (
                    self.ui.tableWidget_medical_record_list.cellWidget(
                        row_no, self.column["PrintMark"]
                    )
                )
                if not check_box_print_mark.isChecked():
                    continue
            except Exception:
                continue

            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            case_key_list.append(case_key)

        if not case_key_list:
            self.ui.tableWidget_medical_record_list.setCurrentCell(current_row_no, 0)
            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            case_key_list.append(case_key)

        export_utils.export_case_to_word(
            self.database, filename, case_key_list=case_key_list
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "病歷匯出完成",
            f"<h3>病歷資料{filename}匯出完成.</h3>",
            "Microsoft Docx 格式.",
        )

    def _unlock_progress(self):
        row_no = self.ui.tableWidget_medical_record_list.currentRow()
        case_key = self.ui.tableWidget_medical_record_list.item(
            row_no, self.column["CaseKey"]
        ).text()
        sql = f"""
            UPDATE wait SET InProgress = "N"
            WHERE
                CaseKey = {case_key}
        """
        self.database.exec_sql(sql)

        self.refresh_medical_record()

    def _get_identification(self):
        row_no = self.ui.tableWidget_medical_record_list.currentRow()
        case_key = self.ui.tableWidget_medical_record_list.item(
            row_no, self.column["CaseKey"]
        ).text()
        cshis_utils.set_identification(
            self, self.database, self.system_settings, case_key
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "簽章完成",
            '<font size="5" color="red"><b>異常卡序安全簽章產生成功.</b></font>',
            "請檢查安全簽章是否正確.",
        )

    # 關檔
    def _close_case(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("關檔")
        msg_box.setText("""
            <font size='4' color='red'>
                <b>確定將病歷資料關檔?</b>
            </font>
        """)
        msg_box.setInformativeText("注意！資料關檔後, 將無法刪除及編輯!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        close_case = msg_box.exec_()
        if not close_case:
            return

        self._set_case("關檔")

    # 開檔
    def _open_case(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("開檔")
        msg_box.setText("""
            <font size='4' color='red'>
                <b>確定將病歷資料開檔?</b>
            </font>
        """)
        msg_box.setInformativeText("注意！資料開後, 將可以刪除及編輯!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        open_case = msg_box.exec_()
        if not open_case:
            return

        self._set_case("開檔")

    def _set_case(self, option):
        if option == "關檔":
            close_option = "IsClosed = True"
        else:
            close_option = "IsClosed = False"

        for row_no in range(self.ui.tableWidget_medical_record_list.rowCount()):
            self.ui.tableWidget_medical_record_list.setCurrentCell(row_no, 0)

            try:
                check_box_close_mark = (
                    self.ui.tableWidget_medical_record_list.cellWidget(
                        row_no, self.column["PrintMark"]
                    )
                )
                if not check_box_close_mark.isChecked():
                    continue
            except Exception:
                continue

            case_key = self.table_widget_medical_record_list.field_value(
                self.column["CaseKey"]
            )
            sql = f"""
                UPDATE cases
                SET
                    {close_option}
                WHERE
                    CaseKey = {case_key}
            """
            self.database.exec_sql(sql)
            case_utils.set_close_case_icon(
                self.ui.tableWidget_medical_record_list,
                row_no,
                self.column["DoctorDone"],
                True,
            )
            self.ui.tableWidget_medical_record_list.setCellWidget(
                row_no, self.column["ChargeDone"], None
            )

            self.refresh_medical_record()

        system_utils.show_message_box(
            QMessageBox.Information,
            f"{option}完成",
            f'<font size="5" color="blue"><b>病歷資料{option}完成.</b></font>',
            "",
        )
