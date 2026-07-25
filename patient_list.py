# -*- coding: UTF-8 -*-

import datetime

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QPushButton

from libs import (
    class_utils,
    date_utils,
    dialog_utils,
    export_utils,
    personnel_utils,
    printer_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 主視窗
class PatientList(QtWidgets.QMainWindow):
    program_name = "病患查詢"

    # 初始化
    def __init__(self, parent=None, *args):
        super(PatientList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.column = {
            "PrintMark": 0,
            "PatientKey": 1,
            "Name": 2,
            "Photo": 3,
            "Gender": 4,
            "Birthday": 5,
            "ID": 6,
            "Nationality": 7,
            "InsType": 8,
            "DiscountType": 9,
            "InitDate": 10,
            "Telephone": 11,
            "Cellphone": 12,
            "Email": 13,
            "Address": 14,
            "Remark": 15,
            "Survey": 16,
        }

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.image_file_path = self.system_settings.field("影像檔路徑")

        self.sql = None
        self.no_page = False
        self.patient_rows = None
        self.total_pages = 1
        self.current_page = 1

        self._set_ui()
        self._set_signal()
        self._set_permission()

        self.mask_phone_address = personnel_utils.get_permission(
            self.database, "病患資料", "遮蔽電話地址", self.user_name
        )

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PATIENT_LIST, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_patient_list = class_utils.get_table_widget(
            self.ui.tableWidget_patient_list, self.database
        )
        self.table_widget_patient_list.set_parent(self.parent)
        # database._set_table_width()
        self._set_tool_button()
        self.count_per_page = self.ui.spinBox_count_per_page.value()

    # 設定信號
    def _set_signal(self):
        self.ui.action_requery.triggered.connect(self.open_dialog)
        self.ui.action_insert_patient_key.triggered.connect(self._insert_patient_key)
        self.ui.action_delete_record.triggered.connect(self.delete_patient_record)
        self.ui.action_open_record.triggered.connect(self.open_patient_record)
        self.ui.action_open_medical_record.triggered.connect(self.open_medical_record)
        self.ui.action_close.triggered.connect(self.close_patient_list)
        self.ui.action_export_patient_list.triggered.connect(self.export_patient_list)
        self.ui.action_export_medical_record_excel.triggered.connect(
            self.export_medical_record_excel
        )
        self.ui.action_print_chart.triggered.connect(self._print_chart)
        self.ui.action_print_chart_pdf.triggered.connect(self._print_chart_pdf)
        self.ui.action_print_simple_chart.triggered.connect(self._print_simple_chart)
        self.ui.action_print_patient_new_care.triggered.connect(
            self._print_patient_new_care
        )
        self.ui.tableWidget_patient_list.doubleClicked.connect(self.open_patient_record)

        self.ui.pushButton_top.clicked.connect(self._top_record)
        self.ui.pushButton_next.clicked.connect(self._next_record)
        self.ui.pushButton_prev.clicked.connect(self._prev_record)
        self.ui.pushButton_bottom.clicked.connect(self._bottom_record)
        self.ui.spinBox_count_per_page.valueChanged.connect(self._set_count_per_page)
        self.ui.spinBox_move_page.valueChanged.connect(self._spin_box_move_page)
        self.ui.tableWidget_patient_list.horizontalHeader().sectionClicked.connect(
            self._header_clicked
        )

        self.ui.action_change_discount.triggered.connect(self._change_discount_type)
        self.ui.action_replace_discount_type.triggered.connect(
            self._replace_discount_type
        )
        self.ui.action_purge_temp_patient.triggered.connect(self._purge_temp_patient)
        self.ui.action_clear_invalid_patient_name.triggered.connect(
            self._clear_invalid_patient_name
        )

    def _set_permission(self):
        if self.user_name == "超級使用者":
            return

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "調閱資料", self.user_name
            )
            != "Y"
        ):
            self.ui.action_open_record.setEnabled(False)
            self.ui.action_open_medical_record.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "資料刪除", self.user_name
            )
            != "Y"
        ):
            self.ui.action_delete_record.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "匯出名單", self.user_name
            )
            != "Y"
        ):
            self.ui.action_export_patient_list.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, "系統作業", "關閉匯出功能", self.user_name
            )
            == "Y"
        ):
            self.ui.action_export_patient_list.setEnabled(False)
            self.ui.action_export_medical_record_excel.setEnabled(False)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [
            30,
            80,
            100,
            60,
            40,
            120,
            120,
            60,
            80,
            80,
            180,
            120,
            120,
            120,
            120,
            120,
        ]
        self.table_widget_patient_list.set_table_heading_width(width)

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_patient_list(
            self.ui, self.database, self.system_settings
        )
        if dialog.exec_():
            self.sql = dialog.get_sql()
            self.patient_rows = dialog.get_row_count()
            if dialog.checkBox_no_page.isChecked():
                self.no_page = True
            else:
                self.no_page = False

        dialog.close_all()
        dialog.deleteLater()
        if self.sql is None:
            return

        self._read_patient_list(self.sql)

    def _read_patient_list(self, sql, page=1):
        if sql is None:
            return

        start_index = (page - 1) * self.count_per_page

        if self.no_page:
            limited_sql = sql
            self.total_pages = 1
        else:
            limited_sql = f"{sql} LIMIT {start_index}, {self.count_per_page}"
            self.total_pages = int(self.patient_rows / self.count_per_page)
            if self.patient_rows % self.count_per_page > 0:
                self.total_pages += 1

            if self.total_pages == 0:
                self.total_pages = 1

        self.table_widget_patient_list.set_db_data(limited_sql, self._set_table_data)
        self._set_tool_button()

        self.ui.spinBox_move_page.setMaximum(self.total_pages)
        self.ui.label_total_pages.setText(f"共{self.total_pages}頁")
        self._set_page_button()

    def _enable_page_button(self, enabled):
        self.ui.pushButton_top.setEnabled(enabled)
        self.ui.pushButton_prev.setEnabled(enabled)
        self.ui.label_current_page.setEnabled(enabled)
        self.ui.pushButton_next.setEnabled(enabled)
        self.ui.pushButton_bottom.setEnabled(enabled)
        self.ui.label_total_pages.setEnabled(enabled)
        self.ui.label_page_jump.setEnabled(enabled)
        self.ui.spinBox_move_page.setEnabled(enabled)
        self.ui.label_page.setEnabled(enabled)

    def _set_page_button(self):
        self._enable_page_button(True)

        if self.no_page:
            self._enable_page_button(False)
        else:
            self.ui.label_current_page.setText(f"第{self.current_page}頁")
            self.ui.spinBox_move_page.setValue(self.current_page)

    def _set_count_per_page(self):
        self.count_per_page = self.ui.spinBox_count_per_page.value()

    def _spin_box_move_page(self):
        self.current_page = self.ui.spinBox_move_page.value()

        self._read_patient_list(self.sql, self.current_page)
        self._set_page_button()

    def _top_record(self):
        self.current_page = 1

        self._read_patient_list(self.sql, self.current_page)
        self._set_page_button()

    def _prev_record(self):
        if self.current_page > 1:
            self.current_page -= 1

        self._read_patient_list(self.sql, self.current_page)
        self._set_page_button()

    def _next_record(self):
        if self.current_page < self.total_pages:
            self.current_page += 1

        self._read_patient_list(self.sql, self.current_page)
        self._set_page_button()

    def _bottom_record(self):
        self.current_page = self.total_pages

        self._read_patient_list(self.sql, self.current_page)
        self._set_page_button()

    def _set_tool_button(self):
        if self.ui.tableWidget_patient_list.rowCount() > 0:
            enabled = True
        else:
            enabled = False

        self.ui.action_delete_record.setEnabled(enabled)
        self.ui.action_open_record.setEnabled(enabled)
        self.ui.action_open_medical_record.setEnabled(enabled)
        self.ui.action_export_patient_list.setEnabled(enabled)
        self.ui.action_print_chart.setEnabled(enabled)
        self.ui.action_print_simple_chart.setEnabled(enabled)
        self.ui.action_print_patient_new_care.setEnabled(enabled)

        self._set_permission()

    def _get_survey(self, patient_key):
        sql = """
            SELECT * FROM patient_extension
            WHERE
                PatientKey = %s AND
                ExtensionType = "從何處得知本診所"
        """
        rows = self.database.select_record(sql, (patient_key,))
        survey_list = []
        for row in rows:
            survey_list.append(string_utils.xstr(row["Content"]))

        return ", ".join(survey_list)

    def _set_table_data(self, row_no, row):
        patient_key = row["PatientKey"]
        remark = string_utils.get_str(row["Remark"], "utf8")[:20]
        remark = string_utils.replace_ascii_char(["\n"], remark)

        if self.system_settings.field("日期格式") == "民國年":
            try:
                birthday = date_utils.date_to_zh_tw_date(
                    string_utils.xstr(row["Birthday"])
                )
            except Exception:
                birthday = None
        else:
            birthday = string_utils.xstr(row["Birthday"])

        telephone = string_utils.xstr(row["Telephone"])
        cellphone = string_utils.xstr(row["Cellphone"])
        email = string_utils.xstr(row["Email"])
        address = string_utils.xstr(row["Address"])

        if self.mask_phone_address == "Y":
            telephone = "*" * len(telephone)
            cellphone = "*" * len(cellphone)
            email = "*" * len(email)
            address = "*" * len(address)

        survey = self._get_survey(patient_key)

        patient_row = [
            None,
            patient_key,
            string_utils.xstr(row["Name"]),
            None,
            string_utils.xstr(row["Gender"]),
            birthday,
            string_utils.xstr(row["ID"]),
            string_utils.xstr(row["Nationality"]),
            string_utils.xstr(row["InsType"]),
            string_utils.xstr(row["DiscountType"]),
            string_utils.xstr(row["InitDate"]),
            telephone,
            cellphone,
            email,
            address,
            remark,
            survey,
        ]

        for col_no in range(len(patient_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, patient_row[col_no])
            self.ui.tableWidget_patient_list.setItem(row_no, col_no, item)

            if col_no in [self.column["PatientKey"]]:
                self.ui.tableWidget_patient_list.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [self.column["Gender"]]:
                self.ui.tableWidget_patient_list.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
        self._set_check_box(row_no, False)
        if self.image_file_path not in ["", None]:
            self._set_photo(patient_key, row_no)

    def _set_check_box(self, row_no, check):
        check_box = QtWidgets.QCheckBox()
        check_box.setStyleSheet("padding-left: 20px")
        check_box.setChecked(check)
        col_no = 0

        self.ui.tableWidget_patient_list.setCellWidget(row_no, col_no, check_box)
        self.ui.tableWidget_patient_list.item(row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _set_photo(self, patient_key, row_no):
        filename = personnel_utils.get_personal_photo_filename(
            self.image_file_path, patient_key
        )
        if filename is None:
            self.ui.tableWidget_patient_list.setCellWidget(
                row_no, self.column["Photo"], None
            )
            return

        gtk_icon_file = filename
        property_value = True
        ui_utils.set_table_widget_field_icon(
            self.ui.tableWidget_patient_list,
            row_no,
            self.column["Photo"],
            gtk_icon_file,
            "has_image",
            property_value,
            self._photo_button_clicked,
        )

    def _photo_button_clicked(self):
        pass

    def delete_patient_record(self):
        name = self.table_widget_patient_list.field_value(self.column["Name"])
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("刪除病患資料")
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

        patient_key = self.table_widget_patient_list.field_value(
            self.column["PatientKey"]
        )
        self.database.delete_record("patient", "PatientKey", patient_key)
        current_row = self.ui.tableWidget_patient_list.currentRow()
        self.ui.tableWidget_patient_list.removeRow(current_row)

    def open_medical_record(self):
        if (
            self.user_name != "超級使用者"
            and personnel_utils.get_permission(
                self.database, self.program_name, "調閱資料", self.user_name
            )
            != "Y"
        ):
            return

        patient_key = self.table_widget_patient_list.field_value(
            self.column["PatientKey"]
        )
        self.parent.open_medical_record_list(patient_key)

    def open_patient_record(self):
        if (
            self.user_name != "超級使用者"
            and personnel_utils.get_permission(
                self.database, self.program_name, "調閱資料", self.user_name
            )
            != "Y"
        ):
            return

        patient_key = self.table_widget_patient_list.field_value(
            self.column["PatientKey"]
        )
        self.parent.open_patient_record(patient_key, "病患查詢")

    # 重新顯示資料 call from pymedical (call from here is not working)
    def refresh_patient_record(self):
        patient_key = self.table_widget_patient_list.field_value(
            self.column["PatientKey"]
        )
        if patient_key in [None, ""]:
            return

        sql = f"""
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        """
        row = self.database.select_record(sql)[0]
        if row is None:
            return

        current_row = self.ui.tableWidget_patient_list.currentRow()
        self._set_table_data(current_row, row)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_patient_list(self):
        self.close_all()
        self.close_tab()

    def export_patient_list(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出病患資料",
            "病患資料.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_patient_list,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>病患資料{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def export_medical_record_excel(self):
        dialog = dialog_utils.get_dialog_patient_medical_record(
            self.ui,
            self.database,
            self.system_settings,
            self.ui.tableWidget_patient_list,
        )

        if not dialog.exec_():
            dialog.deleteLater()
            return

        dialog.close_all()
        dialog.deleteLater()

    def _print_chart(self):
        patient_key = self.table_widget_patient_list.field_value(
            self.column["PatientKey"]
        )
        today = datetime.datetime.today().strftime("%Y-%m-%d")

        printer_utils.print_form_medical_chart(
            self, self.database, self.system_settings, patient_key, today, "preview"
        )

    def _print_chart_pdf(self):
        patient_key = self.table_widget_patient_list.field_value(
            self.column["PatientKey"]
        )
        today = datetime.datetime.today().strftime("%Y-%m-%d")

        printer_utils.print_form_medical_chart(
            self,
            self.database,
            self.system_settings,
            patient_key,
            today,
            "pdf_by_dialog",
        )

    def _print_simple_chart(self):
        patient_key = self.table_widget_patient_list.field_value(
            self.column["PatientKey"]
        )

        printer_utils.print_form_simple_medical_chart(
            self, self.database, self.system_settings, patient_key, "preview"
        )

    def _print_patient_new_care(self):
        patient_key = self.table_widget_patient_list.field_value(
            self.column["PatientKey"]
        )

        printer_utils.print_form_patient_new_care(
            self,
            self.database,
            self.system_settings,
            patient_key,
            None,
            None,
            "preview",
        )

    def _header_clicked(self, col_no):
        if col_no != self.column["PrintMark"]:
            return

        row_count = self.ui.tableWidget_patient_list.rowCount()
        for row_no in range(row_count):
            check_box = self.ui.tableWidget_patient_list.cellWidget(row_no, col_no)
            check_box.setChecked(not check_box.isChecked())

    def _change_discount_type(self):
        input_dialog = QInputDialog()
        input_dialog.setComboBoxEditable(True)

        items = ui_utils.get_discount_type(self.database)
        discount_type, ok = input_dialog.getItem(
            self,
            "更改優待類別",
            "請選擇優待類別, 更改前請先註記病患資料",
            items,
            0,
            False,
        )

        if not ok:
            return

        for row_no in range(self.ui.tableWidget_patient_list.rowCount()):
            self.ui.tableWidget_patient_list.setCurrentCell(row_no, 0)

            change_mark = self.ui.tableWidget_patient_list.cellWidget(
                row_no, self.column["PrintMark"]
            )
            if not change_mark.isChecked():
                continue

            patient_key = self.table_widget_patient_list.field_value(
                self.column["PatientKey"]
            )
            self.database.exec_sql(f'''
                UPDATE patient
                SET
                    DiscountType = "{discount_type}"
                WHERE
                    PatientKey = {patient_key}
            ''')
            self.refresh_patient_record()

        self.ui.tableWidget_patient_list.setCurrentCell(0, 0)

    def _replace_discount_type(self):
        discount_type, ok = QInputDialog.getText(
            self, "原優待類別", "請輸入原優待類別:", QtWidgets.QLineEdit.Normal, ""
        )
        if not ok or discount_type == "":
            return

        replace_discount_type, ok = QInputDialog.getText(
            self, "取代優待類別", "請輸入取代優待類別:", QtWidgets.QLineEdit.Normal, ""
        )
        if not ok or replace_discount_type == "":
            return

        sql = f'''
            UPDATE patient
            SET
                DiscountType = "{replace_discount_type}"
            WHERE
                DiscountType = "{discount_type}"
        '''

        self.database.exec_sql(sql)
        self._read_patient_list(self.sql)

    def _insert_patient_key(self):
        input_dialog = QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")
        patient_key, ok = input_dialog.getInt(
            self, "插入病歷號", "請輸入之前被刪除的病歷號", 0, 0, 99999999, 0
        )
        if not ok:
            return

        if patient_key == 0:
            return

        sql = f"""
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "病歷號已存在",
                '<h3><font color="red">此病歷已存在, 不可插入.</font></h3>',
                "請重新輸入病歷號.",
            )
            return

        fields = ["PatientKey"]
        data = [patient_key]
        self.database.insert_record("patient", fields, data)

        self._read_patient_list(self.sql)

    def _purge_temp_patient(self):
        dialog = dialog_utils.get_dialog_purge_temp_patient(
            self.ui, self.database, self.system_settings
        )
        if not dialog.exec_():
            dialog.deleteLater()
            return

        max_progress = dialog.ui.tableWidget_temp_patient.rowCount()
        progress_dialog = QtWidgets.QProgressDialog(
            "正在清除無效的初診病患資料中, 請稍後...", "取消", 0, max_progress, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no in range(dialog.ui.tableWidget_temp_patient.rowCount()):
            temp_patient_key = dialog.ui.tableWidget_temp_patient.item(row_no, 0).text()
            self.database.delete_record(
                "temp_patient", "TempPatientKey", temp_patient_key
            )

        progress_dialog.setValue(max_progress)
        progress_dialog.deleteLater()

        dialog.deleteLater()

        system_utils.show_message_box(
            QMessageBox.Information,
            "清除初診病患資料",
            '<font size="5" color="blue"><b>所有無效的初診病患資料均已清除.</b></font>',
            "資料清除完成.",
        )

    def _clear_invalid_patient_name(self):
        row_count = self.ui.tableWidget_patient_list.rowCount()
        max_progress = row_count
        progress_dialog = QtWidgets.QProgressDialog(
            "正在清除無效的初診病患資料中, 請稍後...", "取消", 0, max_progress, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no in range(row_count):
            item = self.ui.tableWidget_patient_list.item(row_no, 2)
            if item is None:
                continue

            name = item.text().strip()
            name = string_utils.remove_illegal_characters(name)
            patient_key = self.ui.tableWidget_patient_list.item(row_no, 1).text()
            self.database.exec_sql(f'''
                UPDATE patient
                SET
                    Name = "{name}"
                WHERE
                    PatientKey = {patient_key}
            ''')
            self.database.exec_sql(f'''
                UPDATE cases
                SET
                    Name = "{name}"
                WHERE
                    PatientKey = {patient_key}
            ''')

            progress_dialog.setValue(row_no + 1)

        progress_dialog.setValue(max_progress)
        progress_dialog.deleteLater()

        system_utils.show_message_box(
            QMessageBox.Information,
            "清除無效的病患姓名",
            '<font size="5" color="blue"><b>所有無效的病患姓名字元均已清除.</b></font>',
            "資料清除完成.",
        )
