from collections import defaultdict
from decimal import Decimal

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from libs import (
    class_utils,
    date_utils,
    dialog_utils,
    export_utils,
    nhi_utils,
    number_utils,
    personnel_utils,
    printer_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 健保申報資料 2019.01.31
class InsApplyList(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = args[2]
        self.apply_month = args[3]
        self.period = args[4]
        self.apply_type = args[5]
        self.clinic_id = args[6]
        self.case_type = args[7]
        self.months = args[8]
        self.ins_list = args[9]
        self.ui = None
        self.error_count = 0

        try:
            self.apply_date = nhi_utils.get_apply_date(
                self.apply_year, self.apply_month
            )
            self.apply_type_code = nhi_utils.APPLY_TYPE_CODE[self.apply_type]
        except Exception:
            self.apply_date = None
            self.apply_type_code = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self.read_data()

        self.ui.tableWidget_ins_apply_statistics.setVisible(False)
        if self.case_type in ["22"]:
            try:
                self.calculate_data()
                self.ui.tableWidget_ins_apply_statistics.setVisible(True)
            except Exception:
                pass

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INS_APPLY_LIST, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_ins_apply_list = class_utils.get_table_widget(
            self.ui.tableWidget_ins_apply_list, self.database
        )
        self.table_widget_ins_apply_statistics = class_utils.get_table_widget(
            self.ui.tableWidget_ins_apply_statistics, self.database
        )

        self.table_widget_ins_apply_list.set_column_hidden([0])
        if (
            personnel_utils.get_permission(
                self.database, "系統作業", "關閉匯出功能", self.user_name
            )
            == "Y"
        ):
            self.ui.toolButton_export.setEnabled(False)

        width = [100, 90, 220, 90, 60, 90]
        self.table_widget_ins_apply_statistics.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_ins_apply_list.doubleClicked.connect(
            self.open_medical_record
        )
        self.ui.toolButton_jump.clicked.connect(self._jump_sequence)
        self.ui.toolButton_change_sequence.clicked.connect(self._change_sequence)
        self.ui.toolButton_find_error.clicked.connect(self._find_error)
        self.ui.toolButton_bookmark.clicked.connect(self._toggle_checkbox)
        self.ui.toolButton_clear_bookmark.clicked.connect(self._clear_bookmark)
        self.ui.toolButton_open_medical_record.clicked.connect(self.open_medical_record)
        self.ui.toolButton_print_order.clicked.connect(
            lambda: self.print_order(print_type=None)
        )
        self.ui.toolButton_print_medical_records.clicked.connect(
            lambda: self.print_medical_records(print_type=None)
        )
        self.ui.toolButton_print_medical_chart.clicked.connect(
            lambda: self.print_medical_chart(print_type=None)
        )
        self.ui.toolButton_print_patient_new_care.clicked.connect(
            self._print_patient_new_care
        )
        self.ui.toolButton_edit_ins_list.clicked.connect(self._edit_ins_list)
        self.ui.toolButton_print_order_bookmark.clicked.connect(
            self._print_order_bookmark
        )
        self.ui.toolButton_export.clicked.connect(self._export_ins_apply)
        self.ui.tableWidget_ins_apply_list.horizontalHeader().sectionClicked.connect(
            self._header_clicked
        )

    def _header_clicked(self, col_no):
        if col_no != 1:
            return

        row_count = self.ui.tableWidget_ins_apply_list.rowCount()
        for row_no in range(row_count):
            try:
                check_box = self.ui.tableWidget_ins_apply_list.cellWidget(
                    row_no, col_no
                )
                check_box.setChecked(not check_box.isChecked())
            except AttributeError:
                continue

    def open_medical_record(self):
        ins_apply_key = self.table_widget_ins_apply_list.field_value(0)
        sql = f"""
            SELECT
                CaseKey1, CaseKey2, CaseKey3, CaseKey4, CaseKey5, CaseKey6,
                CaseKey7, CaseKey8, CaseKey9, CaseKey10, CaseKey11, CaseKey12,
                CaseKey13, CaseKey14, CaseKey15,
                CaseType, Sequence, SpecialCode1, Name
            FROM insapply
            WHERE
                InsApplyKey = {ins_apply_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        if string_utils.xstr(row["CaseType"]) == "30":
            case_key = row["CaseKey1"]
            self.parent.open_medical_record(case_key)
            return

        case_key_list = [
            row["CaseKey1"],
            row["CaseKey2"],
            row["CaseKey3"],
            row["CaseKey4"],
            row["CaseKey5"],
            row["CaseKey6"],
            row["CaseKey7"],
            row["CaseKey8"],
            row["CaseKey9"],
            row["CaseKey10"],
            row["CaseKey11"],
            row["CaseKey12"],
            row["CaseKey13"],
            row["CaseKey14"],
            row["CaseKey15"],
        ]

        available_case_key_list = []
        for case_key in case_key_list:
            if case_key not in [0, None]:
                available_case_key_list.append(case_key)

        if len(available_case_key_list) >= 2:
            case_key = self._open_medical_record_dialog(row, available_case_key_list)
        else:
            case_key = available_case_key_list[0]

        if case_key not in [0, None]:
            self.parent.open_medical_record(case_key)

    # 開啟病歷選擇視窗
    def _open_medical_record_dialog(self, row, case_key_list):
        dialog = dialog_utils.get_dialog_course_list(
            self, self.database, self.system_settings, case_key_list
        )
        case_type = string_utils.xstr(row["CaseType"])
        sequence = string_utils.xstr(row["Sequence"])
        name = string_utils.xstr(row["Name"])
        dialog.ui.label_header.setText(
            f"案件分類:{case_type}-{sequence:0>4} {name}的療程病歷明細"
        )
        dialog.exec_()
        case_key = dialog.selected_case_key
        dialog.close_all()
        dialog.deleteLater()

        return case_key

    def _get_judge_sql(self, case_type=None):
        sql_condition = []
        for row in self.ins_list:
            apply_date = row[2]
            apply_date = str(int(apply_date[:4]) - 1911) + apply_date[4:6]
            current_case_type = row[5]
            sequence = row[6]
            if case_type is None or (
                case_type is not None and current_case_type == case_type
            ):
                sql_condition.append(
                    f'(ApplyDate = "{apply_date}" AND CaseType = "{current_case_type}" AND Sequence = {sequence})'
                )

        sql = f"""
            SELECT * FROM insapply
            WHERE
                {" OR ".join(sql_condition)}
        """
        return sql

    def read_data(self):
        if self.case_type == "抽審":
            if self.ins_list is not None:
                sql = self._get_judge_sql()
                sql += " ORDER BY ApplyDate, CaseType, Sequence"
            else:
                sql = f'''
                    SELECT * FROM insapply
                    WHERE
                        ApplyDate = "{self.apply_date}" AND
                        ApplyType = "{self.apply_type_code}" AND
                        ApplyPeriod = "{self.period}" AND
                        ClinicID = "{self.clinic_id}" AND
                        Note = "*"
                    ORDER BY CaseType, Sequence
                '''
        else:
            if self.ins_list is not None:
                sql = self._get_judge_sql(case_type=self.case_type)
                sql += " ORDER BY ApplyDate, Sequence"
            else:
                sql = f'''
                    SELECT * FROM insapply
                    WHERE
                        ApplyDate = "{self.apply_date}" AND
                        ApplyType = "{self.apply_type_code}" AND
                        ApplyPeriod = "{self.period}" AND
                        ClinicID = "{self.clinic_id}" AND
                        CaseType = "{self.case_type}"
                    ORDER BY Sequence
                '''
        self.table_widget_ins_apply_list.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        ins_apply_row = [
            string_utils.xstr(row["InsApplyKey"]),
            None,
            string_utils.xstr(row["ClinicID"]),
            string_utils.xstr(row["ApplyDate"]),
            string_utils.xstr(row["ApplyPeriod"]),
            string_utils.xstr(row["ApplyType"]),
            string_utils.xstr(row["CaseType"]),
            row["Sequence"],
            string_utils.xstr(row["SpecialCode1"]),
            string_utils.xstr(row["SpecialCode2"]),
            string_utils.xstr(row["SpecialCode3"]),
            string_utils.xstr(row["SpecialCode4"]),
            string_utils.xstr(row["Class"]),
            string_utils.xstr(row["CaseDate"]),
            string_utils.xstr(row["StopDate"]),
            row["PatientKey"],
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["Birthday"]),
            string_utils.xstr(row["ID"]),
            string_utils.xstr(row["Card"]),
            string_utils.xstr(row["Injury"]),
            string_utils.xstr(row["ShareCode"]),
            string_utils.xstr(row["Visit"]),
            string_utils.xstr(row["DiseaseCode1"]),
            string_utils.xstr(row["DiseaseCode2"]),
            string_utils.xstr(row["DiseaseCode3"]),
            string_utils.xstr(row["DiseaseCode4"]),
            string_utils.xstr(row["PresDays"]),
            string_utils.xstr(row["PresType"]),
            string_utils.xstr(row["DoctorName"]),
            string_utils.xstr(row["DoctorID"]),
            string_utils.xstr(row["PharmacistID"]),
            row["DrugFee"],
            row["TreatFee"],
            string_utils.xstr(row["DiagCode"]),
            row["DiagFee"],
            string_utils.xstr(row["PharmacyCode"]),
            row["PharmacyFee"],
            row["InsTotalFee"],
            row["DiagShareFee"],
            row["DrugShareFee"],
            row["ShareFee"],
            row["InsApplyFee"],
            row["AgentFee"],
            row["Identifier"],
            row["ActualIdentifier"],
            row["OriginalIdentifier"],
            string_utils.xstr(row["Message"]),
        ]

        for col_no in range(len(ins_apply_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, ins_apply_row[col_no])
            self.ui.tableWidget_ins_apply_list.setItem(
                row_no,
                col_no,
                item,
            )
            if col_no in [1]:
                self.ui.tableWidget_ins_apply_list.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            elif col_no in [7, 15, 27, 32, 33, 35, 37, 38, 39, 40, 41, 42, 43]:
                self.ui.tableWidget_ins_apply_list.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            if row["Note"] is not None:
                self.ui.tableWidget_ins_apply_list.item(row_no, col_no).setForeground(
                    QtGui.QColor("blue")
                )

        error_message = string_utils.xstr(row["Message"])
        if error_message != "":
            if error_message == "初診照護病歷空白":  # 只有初診照護病歷空白不算錯誤
                self._set_row_color(row_no, "brown")
            else:
                self.error_count += 1
                self._set_row_color(row_no, "red")

        if string_utils.xstr(row["Note"]) == "*":
            checked = True
        else:
            checked = False

        self._set_check_box(row_no, checked)

    def _set_check_box(self, row_no, checked):
        check_box = QtWidgets.QCheckBox()
        check_box.setStyleSheet("padding-left: 20px")
        check_box.setChecked(checked)
        check_box.clicked.connect(self._update_bookmark)

        self.ui.tableWidget_ins_apply_list.setCellWidget(row_no, 1, check_box)

    def _set_row_color(self, row_no, color):
        for column_no in range(self.ui.tableWidget_ins_apply_list.columnCount()):
            self.ui.tableWidget_ins_apply_list.item(row_no, column_no).setForeground(
                QtGui.QColor(color)
            )

    # F2註記按鈕
    def _toggle_checkbox(self):
        row_no = self.ui.tableWidget_ins_apply_list.currentRow()
        check_box = self.ui.tableWidget_ins_apply_list.cellWidget(row_no, 1)
        check_box.setChecked(not check_box.isChecked())
        self._update_bookmark()

    # 清除註記按鈕
    def _clear_bookmark(self):
        msg_box = dialog_utils.get_message_box(
            "清除註記",
            QMessageBox.Warning,
            '<font size="5" color="red"><b>確定清除本頁全部的註記?</b></font>',
            "注意！ 註記清除後, 將無法回復!",
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        for row_no in range(self.ui.tableWidget_ins_apply_list.rowCount()):
            ins_apply_key = self.ui.tableWidget_ins_apply_list.item(row_no, 0).text()
            check_box = self.ui.tableWidget_ins_apply_list.cellWidget(row_no, 1)
            check_box.setChecked(False)
            self._update_bookmark_record(ins_apply_key, "NULL")

    # 註記
    def _update_bookmark(self):
        row_no = self.ui.tableWidget_ins_apply_list.currentRow()
        check_box = self.ui.tableWidget_ins_apply_list.cellWidget(row_no, 1)
        ins_apply_key = self.table_widget_ins_apply_list.field_value(0)

        if check_box.isChecked():
            bookmark_str = '"*"'
            color = "blue"
        else:
            bookmark_str = "NULL"
            color = "black"

        for col_no in range(self.ui.tableWidget_ins_apply_list.columnCount()):
            self.ui.tableWidget_ins_apply_list.item(row_no, col_no).setForeground(
                QtGui.QColor(color)
            )

        self._update_bookmark_record(ins_apply_key, bookmark_str)

    def _update_bookmark_record(self, ins_apply_key, bookmark_str):
        sql = f"""
            UPDATE insapply
            SET
                Note = {bookmark_str}
            WHERE
                InsApplyKey = {ins_apply_key}
        """
        self.database.exec_sql(sql)

    # 列印醫令明細
    def print_order(self, print_type=None):
        ins_apply_key = self.table_widget_ins_apply_list.field_value(0)

        ins_apply_date = self.table_widget_ins_apply_list.field_value(3)
        apply_year = int(ins_apply_date[:3])
        apply_month = int(ins_apply_date[3:5])

        printer_utils.print_form_ins_apply_order(
            self,
            self.database,
            self.system_settings,
            apply_year,
            apply_month,
            self.apply_type,
            ins_apply_key,
            print_type=print_type,
        )

    # 列印病歷
    def print_medical_records(self, print_type=None):
        patient_key = self.table_widget_ins_apply_list.field_value(15)

        ins_apply_date = self.table_widget_ins_apply_list.field_value(3)
        apply_year = int(ins_apply_date[:3]) + 1911
        apply_month = int(ins_apply_date[3:5])

        start_date, end_date = date_utils.get_two_month_date(
            self.database,
            self.system_settings,
            patient_key,
            apply_year,
            apply_month,
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
            print_type=print_type,
        )

    # 列印病歷首頁
    def print_medical_chart(self, print_type=None):
        patient_key = self.table_widget_ins_apply_list.field_value(15)

        printer_utils.print_form_medical_chart(
            self,
            self.database,
            self.system_settings,
            patient_key,
            self.apply_date,
            print_type=print_type,
        )

    def _get_case_key(self, ins_apply_key):
        sql = f"""
            SELECT CaseKey1 FROM insapply
            WHERE
                InsApplyKey = {ins_apply_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            case_key = None
        else:
            case_key = rows[0]["CaseKey1"]

        return case_key

    # 列印初診照護病歷
    def _print_patient_new_care(self):
        ins_apply_key = self.table_widget_ins_apply_list.field_value(0)
        patient_key = self.table_widget_ins_apply_list.field_value(15)
        case_key = self._get_case_key(ins_apply_key)

        printer_utils.print_form_patient_new_care(
            self,
            self.database,
            self.system_settings,
            patient_key,
            case_key,
            self.apply_date,
        )

    # 查詢流水號
    def _jump_sequence(self):
        input_dialog = QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")

        start_no = 1
        end_no = self.ui.tableWidget_ins_apply_list.rowCount()

        sequence, ok = input_dialog.getInt(
            self, "流水號查詢", "請輸入流水號", start_no, 0, end_no, 1
        )
        if not ok:
            return

        self.ui.tableWidget_ins_apply_list.setCurrentCell(sequence - 1, 1)
        self.ui.tableWidget_ins_apply_list.setFocus(True)

    # 查詢流水號
    def _change_sequence(self):
        input_dialog = QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")

        start_no = 1
        end_no = self.ui.tableWidget_ins_apply_list.rowCount()

        sequence, ok = input_dialog.getInt(
            self, "變更流水號", "請輸入流水號", start_no, 0, end_no, 1
        )
        if not ok:
            return

        ins_apply_key = self.table_widget_ins_apply_list.field_value(0)
        sql = f"""
            UPDATE insapply
            SET
                Sequence = {sequence}
            WHERE
                InsApplyKey = {ins_apply_key}
        """
        self.database.exec_sql(sql)

        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, sequence)
        row_no = self.ui.tableWidget_ins_apply_list.currentRow()
        col_no = 7
        self.ui.tableWidget_ins_apply_list.setItem(
            row_no,
            col_no,
            item,
        )
        self.ui.tableWidget_ins_apply_list.item(row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _find_error(self):
        self.table_widget_ins_apply_list.find_error(
            self.ui.tableWidget_ins_apply_list.columnCount() - 1
        )

    def _edit_ins_list(self):
        ins_apply_key = self.table_widget_ins_apply_list.field_value(0)
        sequence = self.table_widget_ins_apply_list.field_value(7)
        case_date = self.table_widget_ins_apply_list.field_value(13)
        end_date = self.table_widget_ins_apply_list.field_value(14)
        dialog = dialog_utils.get_dialog_ins_list_edit(
            self,
            self.database,
            self.system_settings,
            ins_apply_key,
            sequence,
            case_date,
            end_date,
        )

        dialog.exec_()
        dialog.deleteLater()

        sql = f"""
            SELECT *
            FROM insapply
            WHERE
                InsApplyKey = {ins_apply_key}
        """
        row = self.database.select_record(sql)[0]
        row_no = self.ui.tableWidget_ins_apply_list.currentRow()
        self._set_table_data(row_no, row)

    # 列印醫令註記按鈕
    def _print_order_bookmark(self):
        msg_box = dialog_utils.get_message_box(
            "列印醫令",
            QMessageBox.Question,
            '<font size="5" color="red"><b>確定列印本頁全部的醫令註記?</b></font>',
            "注意！ 會大量的列印!",
        )
        print_bookmark = msg_box.exec_()
        if not print_bookmark:
            return

        for row_no in range(self.ui.tableWidget_ins_apply_list.rowCount()):
            check_box = self.ui.tableWidget_ins_apply_list.cellWidget(row_no, 1)
            if not check_box.isChecked():
                continue

            ins_apply_key = self.ui.tableWidget_ins_apply_list.item(row_no, 0).text()
            ins_apply_date = self.ui.tableWidget_ins_apply_list.item(row_no, 3).text()
            apply_year = int(ins_apply_date[:3])
            apply_month = int(ins_apply_date[3:5])

            printer_utils.print_form_ins_apply_order(
                self,
                self.database,
                self.system_settings,
                apply_year,
                apply_month,
                self.apply_type,
                ins_apply_key,
                print_type="print",
            )

        msg_box = dialog_utils.get_message_box(
            "列印醫令",
            QMessageBox.Question,
            '<font size="5" color="blue"><b>列印完成/b></font>',
            "列印工作完成",
        )

    def _export_ins_apply(self):
        filename = f"{self.apply_date}案件分類{self.case_type}申報資料.xlsx"
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出申報資料",
            filename,
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_ins_apply_list,
            [0],
            [7, 15, 26, 31, 32, 34, 36, 37, 38, 39, 40],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>醫師門診日報表{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def _set_item(self, row_no, col_no, value, align=None):
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, value)
        self.ui.tableWidget_ins_apply_statistics.setItem(row_no, col_no, item)
        if align is not None:
            self.ui.tableWidget_ins_apply_statistics.item(
                row_no, col_no
            ).setTextAlignment(align | QtCore.Qt.AlignVCenter)

    def calculate_data(self):
        doctor_list = self._get_doctor_list()
        doctor_summary = self.aggregate_doctor_list(doctor_list)

        self.ui.tableWidget_ins_apply_statistics.setRowCount(0)
        for doctor, items in doctor_summary.items():
            for row_no, item in enumerate(items):
                self.ui.tableWidget_ins_apply_statistics.setRowCount(
                    self.ui.tableWidget_ins_apply_statistics.rowCount() + 1
                )
                current_row_no = self.ui.tableWidget_ins_apply_statistics.rowCount() - 1
                if row_no == 0:
                    self._set_item(current_row_no, 0, doctor)

                price = number_utils.get_integer(item["Price"])
                count = number_utils.get_integer(item["Count"])
                total_price = count * price
                self._set_item(current_row_no, 1, item["InsCode"])
                self._set_item(current_row_no, 2, item["MedicineName"])
                self._set_item(current_row_no, 3, price, align=QtCore.Qt.AlignRight)
                self._set_item(current_row_no, 4, count, align=QtCore.Qt.AlignRight)
                self._set_item(
                    current_row_no, 5, total_price, align=QtCore.Qt.AlignRight
                )

        self.ui.tableWidget_ins_apply_statistics.resizeRowsToContents()

    def aggregate_doctor_list(self, doctor_list):
        """
        將 doctor_list（doctor -> [ [rows...], [rows...] ] 或 [rows...]）彙整為：
        {
          '醫師A': [
             {'MedicineName': '...', 'InsCode': '...', 'Dosage': Decimal, 'Price': Decimal, 'Count': int},
             ...
          ],
          '醫師B': [...]
        }
        """
        result = {}

        for doctor, visits in doctor_list.items():
            bucket = {}

            def _iter_rows(visits):
                for v in visits:
                    if isinstance(v, dict):
                        yield v
                    else:
                        for r in v:
                            yield r

            for row in _iter_rows(visits):
                name = row.get("MedicineName", "")
                code = row.get("InsCode", None)
                dosage = row.get("Dosage", Decimal(0))
                price = row.get("Price", Decimal(0))
                if not isinstance(price, Decimal):
                    price = Decimal(str(price))
                if not isinstance(dosage, Decimal):
                    dosage = Decimal(str(dosage))

                key = (code, name)
                if key not in bucket:
                    bucket[key] = {
                        "MedicineName": name,
                        "InsCode": code,
                        "Dosage": dosage,  # 保留原本的劑量，不做加總
                        "Price": price,
                        "Count": 0,
                    }

                bucket[key]["Count"] += 1

            result[doctor] = list(bucket.values())

        return result

    def _get_doctor_list(self):
        doctor_list = defaultdict(list)
        special_values = set(nhi_utils.SPECIAL_CODE_DICT.values())

        def _cell_text(r, c):
            it = self.ui.tableWidget_ins_apply_list.item(r, c)
            return it.text().strip() if it is not None else None

        for row_no in range(self.ui.tableWidget_ins_apply_list.rowCount()):
            special_code1 = _cell_text(row_no, 8)
            special_code2 = _cell_text(row_no, 9)
            special_code3 = _cell_text(row_no, 10)
            special_code4 = _cell_text(row_no, 11)

            if all(
                code not in special_values
                for code in (special_code1, special_code2, special_code3, special_code4)
            ):
                continue

            ins_apply_key = self.ui.tableWidget_ins_apply_list.item(row_no, 0).text()
            doctor = self.ui.tableWidget_ins_apply_list.item(row_no, 29).text()
            case_key = self._get_case_key(ins_apply_key)
            ins_order_row = self._get_ins_order_row(case_key)
            for item in ins_order_row:
                item["Doctor"] = doctor

            doctor_list[doctor].append(ins_order_row)

        return doctor_list

    def _get_ins_order_row(self, case_key):
        sql = f"""
            SELECT MedicineName, InsCode, Dosage, Price FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 11
            GROUP BY PrescriptKey
            ORDER BY InsCode
        """
        rows = self.database.select_record(sql)

        return list(rows)
