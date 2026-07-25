import datetime
import os

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (
    class_utils,
    date_utils,
    dialog_utils,
    export_utils,
    number_utils,
    personnel_utils,
    printer_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 診斷證明書 2018.12.24
class CertificateDiagnosis(QtWidgets.QMainWindow):
    """診斷證明書2018.12.24."""

    # 初始化
    def __init__(self, parent=None, *args):
        """初始化 CertificateDiagnosis."""
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._read_certificate()

    # 解構
    def __del__(self):
        """解構相關資源."""
        self.close_all()

    # 關閉
    def close_all(self):
        """關閉這個tab."""

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_CERTIFICATE_DIAGNOSIS, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_certificate_list = class_utils.get_table_widget(
            self.ui.tableWidget_certificate_list, self.database
        )
        self.table_widget_certificate_list.set_column_hidden([0, 1])
        self._set_table_width()

        if (
            personnel_utils.get_permission(
                self.database, "系統作業", "關閉匯出功能", self.user_name
            )
            == "Y"
        ):
            self.ui.action_export_to_excel.setEnabled(False)
            self.ui.action_export_certificate_list_excel.setEnabled(False)
            self.ui.action_print_certificate_pdf.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_certificate_diagnosis)
        self.ui.action_add_certificate.triggered.connect(self._add_certificate)
        self.ui.action_modify_certificate.triggered.connect(self._modify_certificate)
        self.ui.action_modify_certificate_date.triggered.connect(
            self._modify_certificate_date
        )
        self.ui.action_remove_certificate.triggered.connect(
            lambda: self.remove_certificate(show_warning=True)
        )
        self.ui.action_print_certificate.triggered.connect(self._print_certificate)
        self.ui.action_print_certificate_proof.triggered.connect(
            self._print_certificate_proof
        )
        self.ui.action_print_certificate_summary.triggered.connect(
            self._print_certificate_summary
        )
        self.ui.action_print_diagnosis_proof.triggered.connect(
            self._print_diagnosis_proof
        )
        self.ui.action_print_certificate_pdf.triggered.connect(
            self._print_certificate_pdf
        )
        self.ui.action_print_receipt.triggered.connect(self._print_receipt)
        self.ui.action_query_certificate.triggered.connect(self._query_certificate)
        self.ui.action_export_certificate_payment.triggered.connect(
            self._export_certificate_payment
        )
        self.ui.action_export_certificate_list_excel.triggered.connect(
            self._export_certificate_list_excel
        )
        self.ui.action_export_table_to_excel.triggered.connect(
            self._export_table_to_excel
        )
        self.ui.action_export_to_excel.triggered.connect(self._export_to_excel)

        self.ui.tableWidget_certificate_list.doubleClicked.connect(
            self._modify_certificate
        )
        self.ui.tableWidget_certificate_list.itemSelectionChanged.connect(
            self._item_changed
        )

    def close_tab(self):
        """關閉tab."""
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_certificate_diagnosis(self):
        """關閉開立診斷證明視窗."""
        self.close_all()
        self.close_tab()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 100, 130, 80, 100, 80, 100, 130, 130, 100, 300, 350, 100, 70]
        self.table_widget_certificate_list.set_table_heading_width(width)

    def _read_certificate(self, sql=None):
        if sql is None:
            start_date = datetime.datetime.now().strftime("%Y-01-01 00:00:00")

            sql = f"""
                SELECT certificate.*, cases.ChargeDone FROM certificate
                    LEFT JOIN cases ON cases.CaseKey = certificate.CaseKey
                WHERE
                    CertificateDate >= "{start_date}" AND
                    CertificateType = "診斷證明"
                ORDER BY CertificateKey DESC
            """

        self.table_widget_certificate_list.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        charge_done = ""
        if string_utils.xstr(row["ChargeDone"]) == "True":
            charge_done = "是"

        treat_type = string_utils.xstr(row["TreatType"])
        if treat_type == "":
            treat_type = "全部"

        certificate_date = string_utils.xstr(row["CertificateDate"])
        start_date = string_utils.xstr(row["StartDate"])
        end_date = string_utils.xstr(row["EndDate"])
        if self.system_settings.field("日期格式") == "民國年":
            certificate_date = date_utils.date_to_zh_tw_date(certificate_date)
            start_date = date_utils.date_to_zh_tw_date(start_date)
            end_date = date_utils.date_to_zh_tw_date(end_date)

        certificate_record = [
            string_utils.xstr(row["CertificateKey"]),
            string_utils.xstr(row["CaseKey"]),
            certificate_date,
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["InsType"]),
            treat_type,
            start_date,
            end_date,
            string_utils.xstr(row["Doctor"]),
            string_utils.get_str(row["Diagnosis"], "utf8"),
            string_utils.get_str(row["DoctorComment"], "utf8"),
            string_utils.xstr(row["CertificateFee"]),
            charge_done,
        ]

        for column in range(len(certificate_record)):
            self.ui.tableWidget_certificate_list.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(certificate_record[column])
            )
            if column in [3, 12]:
                self.ui.tableWidget_certificate_list.item(
                    row_no, column
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            elif column in [5, 6, 13]:
                self.ui.tableWidget_certificate_list.item(
                    row_no, column
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    # 開立證明
    def _add_certificate(self):
        dialog = dialog_utils.get_dialog_certificate_diagnosis(
            self, self.database, self.system_settings, None
        )

        if dialog.exec_():
            self._read_certificate()

        dialog.close_all()
        dialog.deleteLater()

    # 修改證明
    def _modify_certificate(self):
        certificate_key = self.table_widget_certificate_list.field_value(0)

        dialog = dialog_utils.get_dialog_certificate_diagnosis(
            self,
            self.database,
            self.system_settings,
            certificate_key,
        )

        if dialog.exec_():
            self._read_certificate()

        dialog.close_all()
        dialog.deleteLater()

    # 修改開立日期
    def _modify_certificate_date(self):
        certificate_key = self.table_widget_certificate_list.field_value(0)
        certificate_date = date_utils.str_to_date(
            self.table_widget_certificate_list.field_value(2)
        )

        dialog = dialog_utils.get_dialog_calendar(
            self, self.database, self.system_settings, "開立診斷證明"
        )

        dialog.ui.calendarWidget.setSelectedDate(certificate_date)

        if not dialog.exec_():
            dialog.deleteLater()
            return

        current_date = dialog.ui.calendarWidget.selectedDate()
        year = current_date.year()
        month = current_date.month()
        day = current_date.day()
        cert_date = f"{year}-{month:0>2}-{day:0>2}"
        sql = f"""
            UPDATE certificate
            SET
                CertificateDate = "{cert_date}"
            WHERE
                CertificateKey = {certificate_key}
        """
        self.database.exec_sql(sql)
        self._read_certificate()

        dialog.deleteLater()

    def remove_certificate(self, show_warning=True):
        if show_warning:
            name = self.table_widget_certificate_list.field_value(4)
            msg_box = dialog_utils.get_message_box(
                "刪除診斷證明書",
                QMessageBox.Warning,
                f'<font size="5" color="red"><b>確定刪除 {name} 的診斷證明書?</b></font>',
                "注意！資料刪除後, 將無法回復!",
            )
            remove_record = msg_box.exec_()
            if not remove_record:
                return

        certificate_key = self.table_widget_certificate_list.field_value(0)
        case_key = self.table_widget_certificate_list.field_value(1)

        self.database.exec_sql(
            f"DELETE FROM certificate WHERE CertificateKey = {certificate_key}"
        )
        self.database.exec_sql(
            f"DELETE FROM certificate_items WHERE CertificateKey = {certificate_key}"
        )
        self.database.exec_sql(f"DELETE FROM cases WHERE CaseKey = {case_key}")
        self.database.exec_sql(f"DELETE FROM wait WHERE CaseKey = {case_key}")

        current_row = self.ui.tableWidget_certificate_list.currentRow()
        self.ui.tableWidget_certificate_list.removeRow(current_row)

    def _print_certificate(self):
        printer_utils.print_form_certificate_diagnosis(
            self,
            self.database,
            self.system_settings,
            self.table_widget_certificate_list.field_value(0),
            "診斷證明書",
        )

    def _print_certificate_proof(self):
        printer_utils.print_form_certificate_diagnosis(
            self,
            self.database,
            self.system_settings,
            self.table_widget_certificate_list.field_value(0),
            "就醫證明書",
        )

    def _print_certificate_summary(self):
        printer_utils.print_form_certificate_diagnosis(
            self,
            self.database,
            self.system_settings,
            self.table_widget_certificate_list.field_value(0),
            "病歷摘要",
        )

    def _print_diagnosis_proof(self):
        printer_utils.print_form_diagnosis_proof(
            self,
            self.database,
            self.system_settings,
            self.table_widget_certificate_list.field_value(0),
            "就醫證明書",
        )

    def _print_certificate_pdf(self):
        printer_utils.print_form_certificate_diagnosis(
            self,
            self.database,
            self.system_settings,
            self.table_widget_certificate_list.field_value(0),
            "診斷證明書",
            "pdf_by_dialog",
        )

    def _query_certificate(self):
        dialog = dialog_utils.get_dialog_certificate_query(
            self,
            self.database,
            self.system_settings,
            "診斷證明",
        )

        if dialog.exec_():
            sql = dialog.sql
            self._read_certificate(sql)

        dialog.close_all()
        dialog.deleteLater()

    def _export_certificate_payment(self):
        patient_key = self.table_widget_certificate_list.field_value(3)

        if patient_key is None:
            return

        name = self.table_widget_certificate_list.field_value(4)
        msg_box = dialog_utils.get_message_box(
            "自動產生醫療費用證明書",
            QMessageBox.Question,
            f'<font size="5" color="red"><b>確定自動產生 {name} 的醫療費用證明書?</b></font>',
            "系統將自動產生資料, 請檢視是否正確",
        )
        create_record = msg_box.exec_()
        if not create_record:
            return

        ins_type = self.table_widget_certificate_list.field_value(5)
        treat_type = self.table_widget_certificate_list.field_value(6)
        start_date = self.table_widget_certificate_list.field_value(7)
        end_date = self.table_widget_certificate_list.field_value(8)
        doctor = self.table_widget_certificate_list.field_value(9)

        auto_create_list = [
            patient_key,
            name,
            ins_type,
            treat_type,
            start_date,
            end_date,
            doctor,
        ]

        self.parent.create_certificate_payment(auto_create_list)

    # 列印醫療收據
    def _print_receipt(self):
        case_key = self.table_widget_certificate_list.field_value(1)
        if case_key in ["0", "", None]:
            return

        printer_utils.print_receipt_form(
            self, self.database, self.system_settings, case_key, "選擇列印"
        )

    def _item_changed(self):
        self.ui.action_print_receipt.setEnabled(True)

        case_key = self.table_widget_certificate_list.field_value(1)
        if case_key in ["0", "", None]:
            self.ui.action_print_receipt.setEnabled(False)

    def _export_to_excel(self):
        name = self.table_widget_certificate_list.field_value(4)

        last_dir = system_utils.get_last_directory("診斷證明書")
        options = QFileDialog.Options()
        excel_filename = os.path.join(last_dir, f"{name}的診斷證明書.xlsx")
        excel_filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出診斷證明書",
            excel_filename,
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_filename:
            return

        system_utils.set_last_directory("診斷證明書", excel_filename)
        certificate_key = self.table_widget_certificate_list.field_value(0)

        export_utils.export_certificate_diagnosis(
            self.database,
            self.system_settings,
            excel_filename,
            certificate_key,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>{excel_filename}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def _export_certificate_list_excel(self):
        options = QFileDialog.Options()
        last_dir = system_utils.get_last_directory("診斷證明書")

        excel_filename = os.path.join(last_dir, "開立診斷證明明細.xlsx")
        excel_filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出開立診斷證明明細",
            excel_filename,
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_filename:
            return

        system_utils.set_last_directory("診斷證明書", excel_filename)
        medical_record_rows = self._get_medical_record_rows()

        export_utils.export_daily_medical_records_to_excel(
            self.database,
            self.system_settings,
            excel_filename,
            medical_record_rows,
            show_summary=False,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>{excel_filename}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def _get_medical_record_rows(self):
        medical_record_rows = []

        row_count = self.ui.tableWidget_certificate_list.rowCount()
        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生excel檔中, 請稍後...", "取消", 0, row_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no in range(row_count):
            certificate_key = self.ui.tableWidget_certificate_list.item(row_no, 0)
            if certificate_key is None:
                continue

            certificate_key = certificate_key.text()
            self._export_certificate_detail(certificate_key, medical_record_rows)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()

        return medical_record_rows

    def _export_certificate_detail(self, certificate_key, medical_record_rows):
        sql = f"""
            SELECT CaseKey FROM certificate_items
            WHERE
                CertificateKey = {certificate_key}
            ORDER BY CaseKey
        """
        rows = self.database.select_record(sql)
        for row in rows:
            case_key = row["CaseKey"]
            if case_key is None:
                continue

            case_row = self._get_medical_record_row(case_key)
            if case_row is not None:
                medical_record_rows.append(case_row)

    def _get_medical_record_row(self, case_key):
        sql = f"""
            SELECT
                cases.*, patient.DiscountType
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)

        if len(rows) > 0:
            row = rows[0]
        else:
            return None

        discount_fee = number_utils.get_integer(row["DiscountFee"])
        total_fee = number_utils.get_integer(row["TotalFee"])
        if total_fee <= 0:
            return None

        massager = string_utils.xstr(row["Massager"])
        discount_type = string_utils.xstr(row["DiscountType"])

        case_date = string_utils.xstr(row["CaseDate"].date())[:10]
        period = string_utils.xstr(row["Period"])[:1]
        next_case_date = None
        next_period = None

        ins_type = string_utils.xstr(row["InsType"])
        treat_type = string_utils.xstr(row["TreatType"])
        card = string_utils.xstr(row["Card"])
        if card in ["免卡", None]:
            card = ""

        regist_fee = 0
        diag_share_fee = 0
        drug_share_fee = 0
        deposit_fee = 0

        doctor = string_utils.xstr(row["Doctor"])
        patient_key = string_utils.xstr(row["PatientKey"])
        name = string_utils.xstr(row["Name"])
        regist_no = string_utils.xstr(row["RegistNo"])
        course = string_utils.xstr(row["Continuance"])

        case_row = {
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
            "Doctor": doctor,
            "PatientKey": patient_key,
            "Name": name,
            "RegistNo": regist_no,
            "Course": course,
            "DiscountFee": discount_fee,
            "TotalFee": total_fee,
        }

        return case_row

    def _export_table_to_excel(self):
        name = self.table_widget_certificate_list.field_value(4)

        last_dir = system_utils.get_last_directory("診斷證明書")
        options = QFileDialog.Options()
        excel_filename = os.path.join(last_dir, "今年度的診斷證明書.xlsx")
        excel_filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出診斷證明書",
            excel_filename,
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_filename:
            return

        system_utils.set_last_directory("診斷證明書", excel_filename)

        export_utils.export_table_widget_to_excel(
            excel_filename,
            self.ui.tableWidget_certificate_list,
            [0, 1],
            [3, 12],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>{excel_filename}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )
