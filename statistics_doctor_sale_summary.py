# -*- coding: UTF-8 -*-

import datetime

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (
    case_utils,
    class_utils,
    date_utils,
    export_utils,
    number_utils,
    printer_utils,
    purchase_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 醫師自費銷售金額總表 2022.01.12
class StatisticsDoctorSaleSummary(QtWidgets.QMainWindow):
    program_name = "醫師自費銷售金額總表"

    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDoctorSaleSummary, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.ins_type = args[4]
        self.doctor = args[5]
        self.ui = None

        self.year = date_utils.str_to_date(self.start_date).year
        self.month = date_utils.str_to_date(self.start_date).month

        dt = datetime.datetime.strptime(self.start_date, "%Y-%m-%d %H:%M:%S")
        self.start_day = dt.day

        dt = datetime.datetime.strptime(self.end_date, "%Y-%m-%d %H:%M:%S")
        self.end_day = dt.day

        self.medicine_type_list = ["藥丸", "湯包", "水藥", "其他"]
        self.other_medicine_type_list = self.medicine_type_list.copy()
        self.other_medicine_type_list.remove("其他")

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(
            ui_utils.UI_STATISTICS_DOCTOR_SALE_SUMMARY, self
        )
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_prescript = class_utils.get_table_widget(
            self.ui.tableWidget_prescript, self.database
        )

        # 產生日期清單：從 start_date 到 end_date
        self.date_range = []
        current_date = date_utils.str_to_date(self.start_date)
        end_date = date_utils.str_to_date(self.end_date)

        while current_date <= end_date:
            self.date_range.append(current_date)
            current_date += datetime.timedelta(days=1)

        self.ui.tableWidget_prescript.setColumnCount(len(self.date_range) + 3)

        header = ["醫師", "類別"]
        width = [100, 100]
        for date in self.date_range:
            label = f"{date.month}/{date.day}"
            header.append(label)
            width.append(65)

        header.append("合計")
        width.append(100)

        self.ui.tableWidget_prescript.setHorizontalHeaderLabels(header)
        self.table_widget_prescript.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        pass

    def _open_medical_record(self):
        row_no = self.ui.tableWidget_self_prescript.currentRow()
        case_key_item = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO["case_key"]
        )
        if case_key_item is None:
            return

        self.parent.parent.open_medical_record(case_key_item.text())

    def start_calculate(self):
        self._set_doctor_row()
        self._calculate_sales_volume()
        self._calculate_sales_volume_subtotal()

        if self.doctor == "全部":
            self._calculate_sales_volume_total()

        self.ui.tableWidget_prescript.setCurrentCell(0, 0)

    def _calculate_sales_volume_subtotal(self):
        subtotal_col_no = self.ui.tableWidget_prescript.columnCount() - 1

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            subtotal = 0
            item = self.ui.tableWidget_prescript.item(row_no, 0)
            if item is not None and item.text() == "合計":
                continue  # 跳過合計列

            for col_no in range(2, subtotal_col_no):  # ❗關鍵修正：不要多算到合計那欄
                cell_item = self.ui.tableWidget_prescript.item(row_no, col_no)
                if cell_item is not None:
                    subtotal += number_utils.get_integer(cell_item.text())

            self._set_table_widget_cell_value(
                row_no, subtotal_col_no, subtotal, QtCore.Qt.AlignRight
            )

    def _calculate_sales_volume_total(self):
        row_count = self.ui.tableWidget_prescript.rowCount()

        # 插入「合計」醫師欄位
        row = [{"Doctor": "合計"}]
        self._set_table_doctor(row)

        for medicine_type_row_no, medicine_type in enumerate(self.medicine_type_list):
            for col_no in range(2, self.ui.tableWidget_prescript.columnCount()):
                total = 0
                for row_no in range(self.ui.tableWidget_prescript.rowCount()):
                    doctor_item = self.ui.tableWidget_prescript.item(row_no, 0)
                    if doctor_item is not None and doctor_item.text() == "合計":
                        break

                    current_medicine_type_item = self.ui.tableWidget_prescript.item(
                        row_no, 1
                    )
                    if current_medicine_type_item is None:
                        continue

                    current_medicine_type = current_medicine_type_item.text()
                    if current_medicine_type != medicine_type:
                        continue

                    amount_item = self.ui.tableWidget_prescript.item(row_no, col_no)
                    if amount_item is None:
                        continue

                    total += number_utils.get_integer(amount_item.text())

                total_row_no = row_count + medicine_type_row_no
                self._set_table_widget_cell_value(
                    total_row_no, col_no, total, QtCore.Qt.AlignRight
                )

    def _set_doctor_row(self):
        doctor_condition = ""
        if self.doctor != "全部":
            doctor_condition = f'AND Doctor = "{self.doctor}"'

        sql = f'''
            SELECT Doctor FROM cases
                LEFT JOIN prescript ON cases.CaseKey = prescript.CaseKey
            WHERE
                cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                cases.Doctor IS NOT NULL AND LENGTH(cases.Doctor) > 0 AND
                prescript.MedicineSet >= 2 AND prescript.MedicineSet != 11
                {doctor_condition}
            GROUP BY Doctor
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self._set_table_doctor(rows)

    def _set_table_doctor(self, rows):
        for row in rows:
            start_row_no = None
            for i in range(len(self.medicine_type_list)):
                row_no = self.ui.tableWidget_prescript.rowCount()
                self.ui.tableWidget_prescript.setRowCount(row_no + 1)

                if i == 0:
                    start_row_no = row_no
                    item = QtWidgets.QTableWidgetItem()
                    item.setData(QtCore.Qt.EditRole, string_utils.xstr(row["Doctor"]))
                    self.ui.tableWidget_prescript.setItem(row_no, 0, item)

                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, self.medicine_type_list[i])
                self.ui.tableWidget_prescript.setItem(row_no, 1, item)

            self.ui.tableWidget_prescript.setSpan(
                start_row_no, 0, len(self.medicine_type_list), 1
            )

    def _calculate_sales_volume(self):
        row_count = self.ui.tableWidget_prescript.rowCount()

        self.progress_dialog = QtWidgets.QProgressDialog(
            "門診收入統計中, 請稍後...", "取消", 0, row_count, self
        )
        for row_no in range(row_count):
            self.progress_dialog.setValue(row_no)
            QtCore.QCoreApplication.processEvents()

            self.ui.tableWidget_prescript.setCurrentCell(row_no, 0)
            item = self.ui.tableWidget_prescript.item(row_no, 0)
            if item is None:
                continue

            doctor = item.text()
            self._calculate_sales_volume_by_doctor(row_no, doctor)

        self.progress_dialog.setValue(row_count)
        self.progress_dialog.deleteLater()

    def _calculate_sales_volume_by_doctor(self, start_row_no, doctor):
        rows = self._read_prescript(doctor)

        for row_no in range(start_row_no, start_row_no + len(self.medicine_type_list)):
            medicine_type = self.ui.tableWidget_prescript.item(row_no, 1).text()

            for offset, date in enumerate(self.date_range):
                col_no = offset + 2
                case_date = date.strftime("%Y-%m-%d")
                total_amount = self._get_total_amount(medicine_type, case_date, rows)
                self._set_table_widget_cell_value(
                    row_no, col_no, total_amount, QtCore.Qt.AlignRight
                )

    def _get_commission(self, medicine_key):
        if medicine_key in ["", None]:
            return None

        sql = f"SELECT Commission FROM medicine WHERE MedicineKey = {medicine_key}"
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]
        commission = row["Commission"]

        return commission

    def _get_total_amount(self, in_medicine_type, in_case_date, rows):
        total_amount = 0
        for row in rows:
            case_date = row["CaseDate"].date().strftime("%Y-%m-%d")
            if in_case_date != case_date:
                continue

            # medicine_key = string_utils.xstr(row['MedicineKey'])
            # commission = self._get_commission(medicine_key)
            # if commission == '0':
            #     continue

            massage_referrer = string_utils.xstr(row["MassageReferrer"])
            nursing_assistant = string_utils.xstr(row["NursingAssistant"])
            debt = number_utils.get_integer(row["Debt"])

            # if massage_referrer != '' or nursing_assistant != '':  # 有推薦者不算醫師的業績 2026-02-02 void
            #     continue

            medicine_type = string_utils.xstr(row["MedicineType"])
            if in_medicine_type == "其他":
                not_other = False
                for med_type in self.other_medicine_type_list:
                    if med_type in medicine_type:
                        not_other = True
                        break

                if not_other:
                    continue
            elif in_medicine_type not in medicine_type:
                continue

            days = case_utils.get_pres_days(
                self.database, row["CaseKey"], medicine_set=row["MedicineSet"]
            )
            if days <= 0:
                days = 1

            subtotal = number_utils.get_integer(row["Amount"]) * days
            discount_fee = self._get_discount_fee(row["CaseKey"], row["MedicineSet"])
            subtotal -= discount_fee  # 2026-03-11 佳禾: 要扣掉折扣金額
            if debt > 0:
                subtotal -= debt

            if in_medicine_type == "水藥":
                print(subtotal, row["MedicineName"])

            total_amount += subtotal

        repayment_total_amount = self._get_repayment(
            in_case_date, row["Doctor"], in_medicine_type
        )

        return total_amount + repayment_total_amount

    def _get_discount_fee(self, case_key, medicine_set):
        discount_fee = 0

        sql = f"""
            SELECT DiscountFee FROM dosage
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = {medicine_set} AND
                DiscountFee > 0
        """
        rows = self.database.select_record(sql)
        if rows:
            row = rows[0]
            discount_fee = number_utils.get_integer(row["DiscountFee"])

        return discount_fee

    def _get_repayment(self, case_date, doctor, in_medicine_type):
        if in_medicine_type == "其他":
            medicine_type_condition = (
                f' AND MedicineType NOT LIKE "%{in_medicine_type}%" '
            )
        else:
            medicine_type_condition = f' AND MedicineType LIKE "%{in_medicine_type}%" '

        sql = f'''
            SELECT prescript.* FROM debt
                LEFT JOIN prescript ON prescript.CaseKey = debt.CaseKey
            WHERE
                ReturnDate1 = "{case_date}" AND
                Doctor = "{doctor}" AND
                TotalReturn > 0
                {medicine_type_condition}
            GROUP BY prescript.PrescriptKey
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return 0

        # case_key = rows[0]["CaseKey"]

        repayment = 0
        for row in rows:
            repayment += number_utils.get_integer(row["Amount"])
            # medicine_set = row["MedicineSet"]
            # discount_fee = self._get_discount_fee(case_key, medicine_set)
            # repayment -= discount_fee

        return repayment

    def _set_table_widget_cell_value(self, row_no, col_no, value, align):
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, value)
        self.ui.tableWidget_prescript.setItem(row_no, col_no, item)
        self.ui.tableWidget_prescript.item(row_no, col_no).setTextAlignment(
            align | QtCore.Qt.AlignVCenter
        )

    def _read_prescript(self, doctor):
        ins_type_condition = ""
        if self.ins_type != "全部":
            ins_type_condition = f'AND cases.InsType = "{self.ins_type}"'

        sql = f'''
            SELECT
                prescript.*, cases.Name, cases.CaseDate, cases.InsType,
                cases.Doctor, cases.MassageReferrer, cases.NursingAssistant
            FROM prescript
                LEFT JOIN cases ON cases.CaseKey = prescript.CaseKey
            WHERE
                cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                prescript.MedicineSet >= 2 AND
                prescript.MedicineSet != 11 AND
                prescript.Amount > 0 AND
                cases.Doctor = "{doctor}"
                {ins_type_condition}
            GROUP BY PrescriptKey ORDER BY cases.CaseDate
        '''
        rows = self.database.select_record(sql)

        return rows

    def export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出自費產品銷售統計",
            "{0}至{1}{2}自費產品銷售統計表.xlsx".format(
                self.start_date[:10], self.end_date[:10], self.doctor
            ),
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_self_prescript,
            [0],
            [9, 11, 12, 13, 17],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            "<h3>自費產品銷售統計表{0}匯出完成.</h3>".format(excel_file_name),
            "Microsoft Excel 格式.",
        )

    def export_sales_volume(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f"{self.year}-{self.month:0>2}醫師自費銷售總表.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_prescript, None, None
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>醫師自費銷售總表檔{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def print_sale_summary(self):
        printer_utils.print_doctor_sale_summary(
            self,
            self.database,
            self.system_settings,
            self.start_date,
            self.end_date,
            self.ui.tableWidget_prescript,
        )
