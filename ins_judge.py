# -*- coding: UTF-8 -*-

import csv
import io
import webbrowser
import zipfile

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QPushButton

from libs import (
    date_utils,
    dialog_utils,
    module_utils,
    nhi_utils,
    number_utils,
    personnel_utils,
    printer_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 健保抽審 2018.01.31
class InsJudge(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.apply_year = None
        self.apply_month = None
        self.apply_date = None
        self.apply_upload_date = None
        self.apply_type = None
        self.apply_type_code = None
        self.clinic_id = None
        self.period = "全月"
        self.months = 2
        self.user_name = system_utils.get_user_name(self.system_settings)

        self.ui = None

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INS_JUDGE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        if (
            personnel_utils.get_permission(
                self.database, "系統作業", "關閉匯出功能", self.user_name
            )
            == "Y"
        ):
            self.ui.action_export_ins_order_pdf.setEnabled(False)
            self.ui.action_export_medical_record_pdf.setEnabled(False)
            self.ui.action_export_medical_chart_pdf.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.action_requery.triggered.connect(self.open_dialog)
        self.ui.action_upload_emr.triggered.connect(self._upload_emr)
        self.ui.action_print_ins_order_mark.triggered.connect(
            self._print_ins_order_mark
        )
        self.ui.action_print_medical_record_mark.triggered.connect(
            self._print_medical_record_mark
        )
        self.ui.action_print_chart_mark.triggered.connect(self._print_chart_mark)
        self.ui.action_close.triggered.connect(self.close_app)
        self.ui.action_preview_pdf.triggered.connect(self._preview_pdf)
        self.ui.action_import_csv.triggered.connect(self._import_csv)
        self.ui.action_export_ins_order_pdf.triggered.connect(
            self._export_ins_order_pdf
        )
        self.ui.action_export_medical_record_pdf.triggered.connect(
            self._export_medical_record_pdf
        )
        self.ui.action_export_medical_chart_pdf.triggered.connect(
            self._export_medical_chart_pdf
        )
        self.ui.action_open_csv_file.triggered.connect(self._open_csv_file)

    def open_medical_record(self, case_key):
        self.parent.open_medical_record(case_key, "健保抽審")

    def open_dialog(self):
        dialog = dialog_utils.get_dialog_ins_judge(
            self.ui, self.database, self.system_settings
        )
        if self.apply_year is not None:
            dialog.ui.comboBox_year.setCurrentText(string_utils.xstr(self.apply_year))
            dialog.ui.comboBox_month.setCurrentText(string_utils.xstr(self.apply_month))
            dialog.ui.lineEdit_clinic_id.setText(self.clinic_id)
            dialog.ui.comboBox_period.setCurrentText(self.period)
            dialog.ui.dateEdit_apply.setDate(self.apply_upload_date)
            dialog.ui.spinBox_months.setValue(self.months)

            if self.apply_type == "申報":
                dialog.ui.radioButton_apply.setChecked(True)
            else:
                dialog.ui.radioButton_reapply.setChecked(True)

        if dialog.exec_():
            self.apply_year = number_utils.get_integer(
                dialog.ui.comboBox_year.currentText()
            )
            self.apply_month = number_utils.get_integer(
                dialog.ui.comboBox_month.currentText()
            )
            self.clinic_id = dialog.ui.lineEdit_clinic_id.text()
            self.period = dialog.ui.comboBox_period.currentText()

            if dialog.ui.radioButton_apply.isChecked():
                self.apply_type = "申報"  # 申報
            else:
                self.apply_type = "補報"  # 補報

            self.apply_type_code = nhi_utils.APPLY_TYPE_CODE[self.apply_type]
            self.apply_date = f"{self.apply_year - 1911:0>3}{self.apply_month:0>2}"
            self.apply_upload_date = dialog.ui.dateEdit_apply.date()
            self.months = dialog.ui.spinBox_months.value()

            self._add_ins_apply_tab()

        dialog.close_all()
        dialog.deleteLater()

        enabled = False
        if (
            self.ui.tabWidget_ins_data.count() > 0
            and self.tab_ins_apply_tab.tabWidget_ins_apply.count() > 0
        ):
            enabled = True

        self.ui.action_import_csv.setEnabled(enabled)
        self.ui.action_upload_emr.setEnabled(enabled)
        self.ui.action_preview_pdf.setEnabled(enabled)
        self.ui.action_print_ins_order_mark.setEnabled(enabled)
        self.ui.action_print_medical_record_mark.setEnabled(enabled)
        self.ui.action_print_chart_mark.setEnabled(enabled)

    def _add_ins_apply_tab(self, ins_list=None):
        self.ui.tabWidget_ins_data.clear()

        self.tab_ins_apply_tab = module_utils.get_ins_apply_tab(
            self,
            self.database,
            self.system_settings,
            self.apply_year,
            self.apply_month,
            self.period,
            self.apply_type,
            self.clinic_id,
            months=self.months,
            ins_list=ins_list,
        )

        self.ui.tabWidget_ins_data.addTab(self.tab_ins_apply_tab, "申報資料")

    # 電子化抽審
    def _upload_emr(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("電子化抽審")
        msg_box.setText(
            "<font size='4' color='red'><b>確定上傳電子抽審檔案?</b></font>"
        )
        msg_box.setInformativeText("注意！資料上傳前, 請檢查病歷是否完整!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        upload_emr = msg_box.exec_()
        if not upload_emr:
            return

        ins_emr = module_utils.get_ins_upload_emr(
            self,
            self.database,
            self.system_settings,
            self.apply_date,
            self.apply_type,
            self.period,
            self.clinic_id,
            self.apply_upload_date,
        )

        ins_emr.upload_emr_files()
        del ins_emr

    # 列印醫令註記
    def _print_ins_order_mark(self):
        if self.apply_date is None:
            return

        msg_box = dialog_utils.get_message_box(
            "列印醫令註記",
            QMessageBox.Question,
            '<font size="5" color="red"><b>確定列印所有的醫令註記?</b></font>',
            "資料將直接輸出至印表機",
        )
        print_record = msg_box.exec_()
        if not print_record:
            return

        sql = f'''
            SELECT InsApplyKey
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                Note = "*"
            ORDER BY CaseType, Sequence
        '''
        rows = self.database.select_record(sql)
        record_count = len(rows)
        if record_count <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            "正在列印醫令中, 請稍後...", "取消", 0, record_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            progress_dialog.setValue(row_no)
            if progress_dialog.wasCanceled():
                break

            ins_apply_key = row["InsApplyKey"]
            printer_utils.print_form_ins_apply_order(
                self,
                self.database,
                self.system_settings,
                self.apply_year,
                self.apply_month,
                self.apply_type,
                ins_apply_key,
                "print",
            )
        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()

    # 列印雙月病歷註記
    def _print_medical_record_mark(self):
        if self.apply_date is None:
            return

        msg_box = dialog_utils.get_message_box(
            "列印雙月病歷註記",
            QMessageBox.Question,
            '<font size="5" color="red"><b>確定列印所有的雙月病歷註記?</b></font>',
            "資料將直接輸出至印表機",
        )
        print_record = msg_box.exec_()
        if not print_record:
            return

        patient_key_list = []
        sql = f'''
            SELECT InsApplyKey, PatientKey
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                Note = "*"
            ORDER BY CaseType, Sequence
        '''
        rows = self.database.select_record(sql)
        record_count = len(rows)
        if record_count <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            "正在列印雙月病歷中, 請稍後...", "取消", 0, record_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            progress_dialog.setValue(row_no)
            if progress_dialog.wasCanceled():
                break

            patient_key = row["PatientKey"]
            if patient_key in patient_key_list:
                continue

            patient_key_list.append(patient_key)
            start_date, end_date = date_utils.get_two_month_date(
                self.database,
                self.system_settings,
                patient_key,
                self.apply_year,
                self.apply_month,
                month_range=self.months,
            )

            printer_utils.print_form_medical_records(
                self,
                self.database,
                self.system_settings,
                patient_key,
                None,
                start_date,
                end_date,
                "print",
            )

        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()

    # 列印病歷首頁註記
    def _print_chart_mark(self):
        if self.apply_date is None:
            return

        msg_box = dialog_utils.get_message_box(
            "列印病歷首頁註記",
            QMessageBox.Question,
            '<font size="5" color="red"><b>確定列印所有的病歷首頁註記?</b></font>',
            "資料將直接輸出至印表機",
        )
        print_record = msg_box.exec_()
        if not print_record:
            return

        patient_key_list = []
        sql = f'''
            SELECT InsApplyKey, PatientKey
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                Note = "*"
            ORDER BY CaseType, Sequence
        '''
        rows = self.database.select_record(sql)
        record_count = len(rows)
        if record_count <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            "正在列印病歷首頁中, 請稍後...", "取消", 0, record_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            progress_dialog.setValue(row_no)
            if progress_dialog.wasCanceled():
                break

            patient_key = row["PatientKey"]
            if patient_key in patient_key_list:
                continue

            patient_key_list.append(patient_key)
            printer_utils.print_form_medical_chart(
                self,
                self.database,
                self.system_settings,
                patient_key,
                self.apply_date,
                "print",
            )

        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()

    def _preview_pdf(self):
        ins_emr = module_utils.get_ins_upload_emr(
            self,
            self.database,
            self.system_settings,
            self.apply_date,
            self.apply_type,
            self.period,
            self.clinic_id,
            self.apply_upload_date,
        )

        ins_emr.create_emr_files()
        webbrowser.open(f"file:///{ins_emr.EXPORT_DIR}")

        del ins_emr

    def _import_csv(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        csv_filename, _ = QFileDialog.getOpenFileName(
            self, "匯入抽審CSV檔", "*.csv", "csv檔 (*.csv)", options=options
        )
        if not csv_filename:
            return

        with open(csv_filename, "r", encoding="big5") as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                clinic_id = row[0].replace("'", "")
                if clinic_id == "醫事機構代碼":
                    continue

                if clinic_id != self.clinic_id:
                    system_utils.show_message_box(
                        QMessageBox.Critical,
                        "抽審檔院所代號有誤",
                        f"""<h3><font color="red">
                            抽審檔的院所代號有誤，請重新匯入.<br>
                            院所代號: {self.clinic_id}<br>
                            錯誤代號: {clinic_id}
                            </font></h3>""",
                        "請重新選擇正確的抽審檔.",
                    )
                    return

                apply_date = row[1].replace("'", "")
                if apply_date != self.apply_date:
                    system_utils.show_message_box(
                        QMessageBox.Critical,
                        "抽審檔月份有誤",
                        '<h3><font color="red">抽審檔的費用年月有誤，請重新匯入.</font></h3>',
                        "請重新選擇正確的抽審檔.",
                    )
                    return

                break

            sql = f'''
                UPDATE insapply
                SET
                    Note = NULL
                WHERE
                    ClinicID = "{self.clinic_id}" AND
                    ApplyDate = "{apply_date}" AND
                    ApplyPeriod = "{self.period}" AND
                    ApplyType = "{self.apply_type_code}"
            '''
            self.database.exec_sql(sql)

        with open(csv_filename, "r", encoding="big5") as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                clinic_id = row[0].replace("'", "")
                if clinic_id == "醫事機構代碼":
                    continue

                case_type = row[4].replace("'", "")
                sequence = row[5]

                sql = f'''
                    UPDATE insapply
                    SET
                        Note = "*"
                    WHERE
                        ClinicID = "{self.clinic_id}" AND
                        ApplyDate = "{apply_date}" AND
                        ApplyPeriod = "{self.period}" AND
                        ApplyType = "{self.apply_type_code}" AND
                        CaseType = "{case_type}" AND
                        Sequence = {sequence}
                '''
                self.database.exec_sql(sql)

        system_utils.show_message_box(
            QMessageBox.Information,
            "匯入成功",
            "<h3>抽審檔匯入完成，已完成所有資料的註記.</h3>",
            "抽審檔匯入完成.",
        )
        self._add_ins_apply_tab()

    # 匯出醫令pdf
    def _print_ins_order(self, print_type="print"):
        if self.apply_date is None:
            return

        msg_box = dialog_utils.get_message_box(
            "列印醫令註記",
            QMessageBox.Question,
            '<font size="5" color="red"><b>確定列印所有的醫令註記?</b></font>',
            "資料將直接輸出至印表機",
        )
        print_record = msg_box.exec_()
        if not print_record:
            return

        sql = f'''
            SELECT InsApplyKey
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                Note = "*"
            ORDER BY CaseType, Sequence
        '''
        rows = self.database.select_record(sql)
        record_count = len(rows)
        if record_count <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            "正在列印醫令中, 請稍後...", "取消", 0, record_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            progress_dialog.setValue(row_no)
            if progress_dialog.wasCanceled():
                break

            ins_apply_key = row["InsApplyKey"]
            printer_utils.print_form_ins_apply_order(
                self,
                self.database,
                self.system_settings,
                self.apply_year,
                self.apply_month,
                self.apply_type,
                ins_apply_key,
                print_type,
            )
        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()

    def _export_ins_order_pdf(self):
        tab = self.ui.tabWidget_ins_data.currentWidget()
        tab.export_ins_order()

    def _export_medical_record_pdf(self):
        tab = self.ui.tabWidget_ins_data.currentWidget()
        tab.export_medical_record()

    def _export_medical_chart_pdf(self):
        tab = self.ui.tabWidget_ins_data.currentWidget()
        tab.export_medical_chart()

    def _open_csv_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "開啟抽審檔",
            "",  # ← 建議路徑先清空，才能顯示副檔名過濾
            "所有檔案 (*);;zip檔 (*.zip);;csv檔 (*.csv)",
            options=options,
        )
        if not filename:
            return

        ins_list = []
        if zipfile.is_zipfile(filename):
            with zipfile.ZipFile(filename, "r") as zip_ref:
                name_list = zip_ref.namelist()  # 印出所有檔案名稱
                if len(name_list) <= 0:
                    return

                csv_filename = name_list[0]
                with zip_ref.open(csv_filename) as f:
                    # 需要先轉成 TextIO 才能用 csv.reader
                    text_file = io.TextIOWrapper(f, encoding="utf-8")
                    reader = csv.reader(text_file)
                    for row in reader:
                        ins_list.append(row)
        else:
            with open(filename, encoding="utf-8", newline="") as csv_file:
                csv_reader = csv.reader(csv_file)
                for row in csv_reader:
                    ins_list.append(row)

        ins_list = ins_list[1:]
        self._add_ins_apply_tab(ins_list)
