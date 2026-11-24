# -*- coding: UTF-8 -*-


from PyQt5 import QtCore, QtWidgets

from libs import (
    class_utils,
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

        print(self.start_date, self.end_date)
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
            70,
            80,
            80,
            50,
            100,
            110,
        ]
        self.table_widget_amount.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_amount.setRowCount(0)

        self._read_data()

    def _read_data(self):
        sql = """
            SELECT prescript.*, cases.Name, cases.Cashier FROM prescript
                LEFT JOIN cases ON prescript.CaseKey = cases.CaseKey
            WHERE
                cases.CaseDate BETWEEN %s AND %s AND
                (cases.Doctor IS NULL OR LENGTH(cases.Doctor) = 0) AND
                MedicineSet >= 2 AND
                Amount > 0
            ORDER BY cases.CaseDate, cases.PatientKey, prescript.PrescriptKey
        """
        params = (self.start_date, self.end_date)
        self.table_widget_amount.set_db_data(sql, self._set_table_data, params=params)

    def _set_table_data(self, row_no, row):
        case_key = string_utils.xstr(row["CaseKey"])
        quantity = number_utils.get_float(row["Dosage"])
        price = number_utils.get_float(row["Price"])
        amount = number_utils.get_float(row["Amount"])
        amount_row = [
            case_key,
            string_utils.xstr(row["CaseDate"].strftime("%Y-%m-%d")),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["MedicineName"]),
            string_utils.xstr(row["Unit"]),
            round(quantity, 2),
            round(price, 2),
            None,
            round(amount, 2),
            string_utils.xstr(row["Cashier"]),
        ]

        for col_no in range(len(amount_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, amount_row[col_no])
            self.ui.tableWidget_amount.setItem(row_no, col_no, item)

            if col_no in [1, 2, 4, 9]:
                self.ui.tableWidget_amount.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            elif col_no in [5, 6, 7, 8]:
                self.ui.tableWidget_amount.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
