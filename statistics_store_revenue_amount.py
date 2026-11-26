# -*- coding: UTF-8 -*-


from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (
    class_utils,
    export_utils,
    number_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 門市收入金額統計 2026-11-24
class StatisticsStoreRevenueAmount(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.ui = None

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
            ui_utils.UI_STATISTICS_STORE_REVENUE_AMOUNT, self
        )
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_amount = class_utils.get_table_widget(
            self.ui.tableWidget_amount, self.database
        )
        self.table_widget_amount.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        width = [
            100,
            150,
            110,
            300,
            80,
            80,
            50,
            80,
            50,
            80,
            110,
        ]
        self.table_widget_amount.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_amount.doubleClicked.connect(self._open_medical_record)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_amount.setRowCount(0)

        self._read_data()
        self._calculate_total()

    def _read_data(self):
        sql = """
            SELECT prescript.*, dosage.Days, cases.Name, cases.Cashier
            FROM prescript
                INNER JOIN cases ON prescript.CaseKey = cases.CaseKey
                INNER JOIN dosage ON dosage.CaseKey = prescript.CaseKey
                                AND dosage.MedicineSet = prescript.MedicineSet
            WHERE
                cases.CaseDate >= %s AND
                cases.CaseDate < DATE_ADD(%s, INTERVAL 1 DAY) AND
                COALESCE(cases.Doctor, '') = '' AND
                prescript.MedicineSet >= 2 AND
                prescript.Amount > 0
            ORDER BY cases.CaseDate, cases.PatientKey, prescript.PrescriptKey
        """
        params = (self.start_date, self.end_date)
        self.table_widget_amount.set_db_data(sql, self._set_table_data, params=params)

    def _set_table_data(self, row_no, row):
        case_key = string_utils.xstr(row["CaseKey"])
        quantity = number_utils.get_float(row["Dosage"])
        price = number_utils.get_float(row["Price"])
        amount = number_utils.get_float(row["Amount"])
        pres_days = number_utils.get_integer(row["Days"])
        if pres_days <= 0:
            pres_days = 1

        subtotal = round(amount * pres_days, 2)
        amount_row = [
            case_key,
            row["CaseDate"].strftime("%Y-%m-%d"),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["MedicineName"]),
            string_utils.xstr(row["Unit"]),
            round(price, 2),
            round(quantity, 2),
            round(amount, 2),
            pres_days,
            subtotal,
            string_utils.xstr(row["Cashier"]),
        ]

        for col_no in range(len(amount_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, amount_row[col_no])
            self.ui.tableWidget_amount.setItem(row_no, col_no, item)

            if col_no in [1, 2, 4, 10]:
                self.ui.tableWidget_amount.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            elif col_no in [5, 6, 7, 8, 9]:
                self.ui.tableWidget_amount.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _calculate_total(self):
        table = self.ui.tableWidget_amount
        row_count = table.rowCount()
        if row_count <= 0:
            return

        total = 0.0
        for row_no in range(row_count):
            item = table.item(row_no, 9)
            if item is not None:
                total += number_utils.get_float(item.data(QtCore.Qt.EditRole))

        table.insertRow(row_count)

        font = table.font()
        font.setBold(True)

        total_row = {
            3: "合計",
            9: round(total, 2),
        }
        for col_no in range(table.columnCount()):
            item = QtWidgets.QTableWidgetItem()
            if col_no in total_row:
                item.setData(QtCore.Qt.EditRole, total_row[col_no])
            item.setFont(font)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
            if col_no == 9:
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            table.setItem(row_count, col_no, item)

    def export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出Excel檔案",
            f"{self.start_date}至{self.end_date}門市收入統計表.xlsx",
            "excel檔案 (*.xlsx)",
            options=options,
        )

        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_amount, [0], [5, 6, 7, 8, 9]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "Excel資料匯出完成",
            f"<h3>{excel_file_name}匯出完成.</h3>",
            "Excel檔案格式.",
        )

    def _open_medical_record(self):
        case_key = self.table_widget_amount.field_value(0)
        self.parent.parent.open_medical_record(case_key, "病歷查詢")
