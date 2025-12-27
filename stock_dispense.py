# -*- coding: UTF-8 -*-

import datetime
from PyQt5 import QtWidgets, QtCore

from libs import system_utils
from libs import ui_utils
from libs import class_utils
from libs import dialog_utils
from libs import number_utils
from libs import string_utils
from libs import date_utils


# 銷貨 2025.12.07
class StockDispense(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StockDispense, self).__init__(parent)
        self.parent = parent
        self.args = args
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.dialog_setting = {
            "dialog_executed": False,
            "year": None,
            "month": None,
        }

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STOCK_DISPENSE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        self.table_widget_stock_dispense = class_utils.get_table_widget(
            self.ui.tableWidget_stock_dispense, self.database)
        self.table_widget_stock_dispense.set_column_hidden([0])

        self.table_widget_medicine = class_utils.get_table_widget(
            self.ui.tableWidget_medicine, self.database)
        self.table_widget_medicine.set_column_hidden([0])

        self._set_table_width()

    def _set_table_width(self):
        width = [100, 130, 130, 90, 120, 250]
        self.table_widget_stock_dispense.set_table_heading_width(width)
        width = [100, 200, 80, 90, 90, 90, 90, 200]
        self.table_widget_medicine.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_app)
        self.ui.action_requery.triggered.connect(self.open_dialog)
        self.ui.action_update.triggered.connect(self._update_dispense)
        self.ui.tableWidget_stock_dispense.itemSelectionChanged.connect(self._stock_dispense_item_changed)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        self.close_all()
        self.close_tab()

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_date_picker(self, self.database, self.system_settings, None)

        if self.dialog_setting['dialog_executed']:
            dialog.ui.comboBox_year.setCurrentText(self.dialog_setting['year'])
            dialog.ui.comboBox_month.setCurrentText(self.dialog_setting['month'])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        year = dialog.ui.comboBox_year.currentText()
        month = dialog.ui.comboBox_month.currentText()

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['year'] = year
        self.dialog_setting['month'] = month

        dialog.deleteLater()

        self._read_dispense()

    def _read_dispense(self):
        year = self.dialog_setting['year']
        month = self.dialog_setting['month']
        start_date = date_utils.get_start_date_by_year_month(str(year), str(month))[:10]
        end_date = date_utils.get_end_date_by_year_month(int(year), int(month))[:10]

        self._read_dispense_data(start_date, end_date)
        self.ui.tableWidget_stock_dispense.setCurrentCell(0, 1)

    def _read_dispense_data(self, start_date, end_date):
        start_day = int(start_date.split('-')[2])
        end_day = int(end_date.split('-')[2])
        year = int(start_date.split('-')[0])
        month = int(start_date.split('-')[1])

        self.ui.tableWidget_stock_dispense.clearContents()
        self.ui.tableWidget_stock_dispense.setRowCount(end_day)

        for day in range(start_day, end_day + 1):
            case_date = f"{year}-{month:0>2}-{day:0>2}"
            row_no = day - 1
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, case_date)
            self.ui.tableWidget_stock_dispense.setItem(row_no, 1, item)

            sql = f'''
                SELECT * FROM stockdispense
                WHERE
                    CaseDate = "{case_date}"
            '''
            rows = self.database.select_record(sql)
            if not rows:
                continue

            row = rows[0]
            self._set_data(row_no, row)

    def _set_data(self, row_no, row):
        stock_dispense_key = row['StockDispenseKey']
        case_date = row['CaseDate'].strftime('%Y-%m-%d')
        archived_date = row['ArchivedDate'].strftime('%Y-%m-%d')
        status = '已過帳'
        user = string_utils.xstr(row['User'])
        remark = string_utils.xstr(row['Remark'])
        record = [stock_dispense_key, case_date, archived_date, status, user, remark]
        for col_no in range(len(record)):
            if col_no == 1:
                continue

            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, record[col_no])
            self.ui.tableWidget_stock_dispense.setItem(row_no, col_no, item)

    def _update_dispense(self):
        stock_dispense_key = self.table_widget_stock_dispense.field_value(0)
        if stock_dispense_key is not None:
            return

        msg_box = QtWidgets.QMessageBox()
        msg_box.setIcon(QtWidgets.QMessageBox.Warning)
        msg_box.setWindowTitle('準備過帳')
        msg_box.setText("""
            <font size='4' color='red'>
                <b>確定開始調整處方庫存量?</b>
            </font>
        """)
        msg_box.setInformativeText("注意！資料過帳後, 將無法回復!")
        msg_box.addButton(QtWidgets.QPushButton("取消"), QtWidgets.QMessageBox.NoRole)
        msg_box.addButton(QtWidgets.QPushButton("確定"), QtWidgets.QMessageBox.YesRole)
        update_record = msg_box.exec_()
        if not update_record:
            return

        self._insert_dispense()
        self._adjust_stock()
        self._stock_dispense_item_changed()

        system_utils.show_message_box(
            QtWidgets.QMessageBox.Information,
            "過帳完成",
            "<h3>單日過帳完成.</h3>",
            "請依照日期順序過帳",
        )

    def _insert_dispense(self):
        fields = ['CaseDate', 'ArchivedDate', 'User', 'Remark']
        case_date = self.table_widget_stock_dispense.field_value(1)
        archived_date = datetime.date.today().strftime('%Y-%m-%d')
        user = system_utils.get_user_name(self.system_settings)
        remark = self.table_widget_stock_dispense.field_value(5)
        data = [case_date, archived_date, user, remark]
        stock_dispense_key = self.database.insert_record('stockdispense', fields, data)

        sql = f'''
            SELECT * FROM stockdispense
            WHERE
                StockDispenseKey = "{stock_dispense_key}"
        '''
        row = self.database.select_record(sql)[0]
        row_no = self.ui.tableWidget_stock_dispense.currentRow()
        self._set_data(row_no, row)

    def _stock_dispense_item_changed(self):
        self.ui.action_update.setEnabled(True)

        case_date = self.table_widget_stock_dispense.field_value(1)
        archived_date = self.table_widget_stock_dispense.field_value(2)
        if archived_date is not None:
            self.ui.action_update.setEnabled(False)
            self.ui.tableWidget_medicine.setRowCount(0)
            return

        self._read_prescript(case_date)

    def _read_prescript(self, case_date):
        sql = f'''
            SELECT
                prescript.MedicineName, prescript.Unit,
                IFNULL(SUM(prescript.Dosage * IF(dosage.Days, dosage.Days, 1)), 0) AS TotalDosage,
                medicine.MedicineKey, medicine.Quantity, medicine.SafeQuantity
            FROM prescript
                LEFT JOIN cases ON prescript.CaseKey = cases.CaseKey
                LEFT JOIN medicine ON prescript.MedicineKey = medicine.MedicineKey
                LEFT JOIN dosage ON prescript.CaseKey = dosage.CaseKey
            WHERE
                DATE(cases.CaseDate) = "{case_date}" AND
                prescript.Dosage > 0 AND
                prescript.MedicineType NOT IN ("處置", "穴道") AND
                (dosage.MedicineSet = prescript.MedicineSet)
            GROUP BY prescript.MedicineName
            ORDER BY prescript.MedicineType, prescript.MedicineKey
        '''
        self.table_widget_medicine.set_db_data(sql, self._set_medicine_data)

    def _set_medicine_data(self, row_no, row):
        total_dosage = number_utils.get_float(row['TotalDosage'])
        quantity = number_utils.get_float(row['Quantity']) if row['Quantity'] is not None else None
        safe_quantity = number_utils.get_integer(row['SafeQuantity']) if row['SafeQuantity'] is not None else None
        stock_quantity = number_utils.get_float(quantity) - total_dosage \
            if quantity is not None and quantity > 0 else None
        if stock_quantity is not None and safe_quantity is not None and stock_quantity < safe_quantity:
            status = '存量不足'
        else:
            status = None

        medicine_row = [
            string_utils.xstr(row['MedicineKey']),
            string_utils.xstr(row['MedicineName']),
            string_utils.xstr(row['Unit']),
            quantity,
            total_dosage,
            stock_quantity,
            safe_quantity,
            status,
        ]

        for col_no in range(len(medicine_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medicine_row[col_no])

            self.ui.tableWidget_medicine.setItem(row_no, col_no, item)
            if col_no in [3, 4, 5, 6]:
                self.ui.tableWidget_medicine.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [2]:
                self.ui.tableWidget_medicine.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if status is not None:
                self.ui.tableWidget_medicine.item(
                    row_no, col_no).setForeground(QtCore.Qt.red)

    def _adjust_stock(self):
        for row_no in range(self.ui.tableWidget_medicine.rowCount()):
            self.ui.tableWidget_medicine.setCurrentCell(row_no, 0)
            medicine_key = self.table_widget_medicine.field_value(0)
            stock_quantity = self.table_widget_medicine.field_value(5)
            if stock_quantity in ['', None]:
                continue

            sql = f'''
                UPDATE medicine
                    SET Quantity = {stock_quantity}
                WHERE
                    MedicineKey = "{medicine_key}"
            '''
            self.database.exec_sql(sql)

        self.ui.tableWidget_medicine.setCurrentCell(0, 0)
