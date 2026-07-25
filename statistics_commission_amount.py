
# -*- coding: UTF-8 -*-

import calendar

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (class_utils, export_utils, number_utils, personnel_utils,
                  printer_utils, purchase_utils, string_utils, system_utils,
                  ui_utils)


# 自費銷售抽成總表 2021.06.07
class StatisticsCommissionAmount(QtWidgets.QMainWindow):
    program_name = '自費銷售抽成總表'

    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsCommissionAmount, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.year = args[2]
        self.month = args[3]
        self.ui = None

        self.last_day = calendar.monthrange(int(self.year), int(self.month))[1]
        self.start_date = f'{self.year}-{self.month}-01 00:00:00'
        self.end_date = f'{self.year}-{self.month}-{self.last_day} 23:59:59'

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_permission()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_COMMISSION_AMOUNT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_seller = class_utils.get_table_widget(self.ui.tableWidget_seller, self.database)
        self.ui.tableWidget_seller.setColumnCount(self.last_day+3)
        header = ['銷售者', '職稱']
        width = [100, 100]
        for i in range(self.last_day):
            date_label = f'{self.month:0>2}/{i+1:0>2}'
            header.append(date_label)
            width.append(65)

        header.append('抽成合計')
        width.append(100)

        self.ui.tableWidget_seller.setHorizontalHeaderLabels(header)
        self.table_widget_seller.set_table_heading_width(width)

        purchase_utils.set_purchase_list_table(self.database, self.ui.tableWidget_self_prescript)

        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.toolButton_export_seller.setEnabled(False)
            self.ui.toolButton_export_prescript.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_seller.itemSelectionChanged.connect(self._table_seller_changed)
        self.ui.tableWidget_self_prescript.doubleClicked.connect(self._open_medical_record)
        self.ui.toolButton_export_seller.clicked.connect(self._export_seller)
        self.ui.toolButton_export_prescript.clicked.connect(self._export_prescript)
        self.ui.toolButton_print_self_prescript.clicked.connect(self._print_self_prescript)
        self.ui.toolButton_print_seller.clicked.connect(self._print_seller)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(
                self.database, self.program_name, '匯出Excel', self.user_name) != 'Y':
            self.ui.toolButton_export_seller.setEnabled(False)
            self.ui.toolButton_export_prescript.setEnabled(False)
            self.ui.toolButton_print_self_prescript.setEnabled(False)

    def _open_medical_record(self):
        row_no = self.ui.tableWidget_self_prescript.currentRow()
        case_key_item = self.ui.tableWidget_self_prescript.item(row_no, purchase_utils.PURCHASE_COL_NO['case_key'])
        if case_key_item is None:
            return

        self.parent.parent.open_medical_record(case_key_item.text())

    def _table_seller_changed(self):
        row_no = self.ui.tableWidget_seller.currentRow()
        item = self.ui.tableWidget_seller.item(row_no, 0)

        if item is None:
            return

        seller = item.text()
        position = self.ui.tableWidget_seller.item(row_no, 1).text()
        self._read_prescript(seller, position)

    def start_calculate(self):
        self._set_seller()
        self._calculate_commission()
        self._calculate_daily_commission_total()
        self._calculate_total_seller()

        self.ui.tableWidget_seller.setCurrentCell(self.ui.tableWidget_seller.rowCount()-1, 1)
        self._table_seller_changed()

    def _set_seller(self):
        self._set_seller_row('醫師')
        self._set_seller_row('傷助推薦')
        self._set_seller_row('護佐')

    def _calculate_total_seller(self):
        total_list = ['合計', ''] + [0] * (self.last_day + 1)
        for row_no in range(self.ui.tableWidget_seller.rowCount()):
            for col_no in range(2, self.ui.tableWidget_seller.columnCount()):
                total_list[col_no] += number_utils.get_integer(
                    self.ui.tableWidget_seller.item(row_no, col_no).text()
                )

        row_no = self.ui.tableWidget_seller.rowCount()
        self.ui.tableWidget_seller.setRowCount(self.ui.tableWidget_seller.rowCount() + 1)
        font = QtGui.QFont()
        font.setBold(True)
        for col_no, value in enumerate(total_list):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, value)
            self.ui.tableWidget_seller.setItem(row_no, col_no, item)
            if col_no >= 2:
                self.ui.tableWidget_seller.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

            self.ui.tableWidget_seller.item(row_no, col_no).setFont(font)

    def _calculate_daily_commission_total(self):
        for row_no in range(self.ui.tableWidget_seller.rowCount()):
            total_commission = 0
            for col_no in range(2, self.ui.tableWidget_seller.columnCount()-1):
                daily_commission = number_utils.get_integer(self.ui.tableWidget_seller.item(row_no, col_no).text())
                total_commission += daily_commission

            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, total_commission)
            col_no = self.ui.tableWidget_seller.columnCount() - 1
            self.ui.tableWidget_seller.setItem(row_no, col_no, item)
            self.ui.tableWidget_seller.item(row_no, col_no).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )

    def _set_seller_row(self, position):
        if position == '醫師':
            position_field = 'cases.Doctor'
            position_condition = 'person.Position IN("醫師", "支援醫師") '
        elif position == '傷助推薦':
            position_field = 'cases.MassageReferrer'
            position_condition = 'person.Position = "推拿師父" '
        elif position == '護佐':
            position_field = 'cases.NursingAssistant'
            position_condition = 'person.Position NOT IN ("醫師", "支援醫師", "推拿師父") '
        else:
            return

        sql = f'''
            SELECT cases.CaseKey, {position_field} AS Seller FROM cases
                LEFT JOIN person ON {position_field} = person.Name
                LEFT JOIN prescript ON cases.CaseKey = prescript.CaseKey
            WHERE
                cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                prescript.MedicineSet >= 2 AND
                {position_condition}
            GROUP BY {position_field}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self._set_table_seller(rows, position)

    def _set_table_seller(self, rows, position):
        for row in rows:
            row_no = self.ui.tableWidget_seller.rowCount()
            self.ui.tableWidget_seller.setRowCount(row_no + 1)
            data = [string_utils.xstr(row['Seller']), position]
            for col_no in range(len(data)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, data[col_no])
                self.ui.tableWidget_seller.setItem(row_no, col_no, item)

    def _calculate_commission(self):
        row_count = self.ui.tableWidget_seller.rowCount()

        self.progress_dialog = QtWidgets.QProgressDialog(
            '門診收入統計中, 請稍後...', '取消', 0, row_count, self
        )
        for row_no in range(row_count):
            self.progress_dialog.setValue(row_no)
            QtCore.QCoreApplication.processEvents()

            self.ui.tableWidget_seller.setCurrentCell(row_no, 0)
            item = self.ui.tableWidget_seller.item(row_no, 0)
            if item is None:
                continue

            seller = item.text()
            position = self.ui.tableWidget_seller.item(row_no, 1).text()
            self._read_prescript(seller, position)
            self._calculate_monthly_commission()

        self.progress_dialog.setValue(row_count)
        self.progress_dialog.deleteLater()

    def _calculate_monthly_commission(self):
        row_no = self.ui.tableWidget_seller.currentRow()
        position = self.ui.tableWidget_seller.item(row_no, 1).text()

        for col_no in range(2, self.ui.tableWidget_seller.columnCount()-1):
            case_date = f'{self.year}-{self.month:0>2}-{col_no-1:0>2}'
            commission = self._get_daily_commission(case_date, position)
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, commission)
            self.ui.tableWidget_seller.setItem(row_no, col_no, item)
            self.ui.tableWidget_seller.item(row_no, col_no).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )

    def _get_daily_commission(self, case_date, position):
        total_commission = 0
        for row_no in range(self.ui.tableWidget_self_prescript.rowCount()):
            case_date_item = self.ui.tableWidget_self_prescript.item(
                row_no, purchase_utils.PURCHASE_COL_NO['case_date'])
            if case_date_item is None:
                continue

            if case_date != case_date_item.text():
                continue

            col_no = {
                '醫師': purchase_utils.PURCHASE_COL_NO['doctor_commission'],
                '傷助推薦': purchase_utils.PURCHASE_COL_NO['massager_commission'],
                '護佐': purchase_utils.PURCHASE_COL_NO['cashier_commission'],
            }
            commission_item = self.ui.tableWidget_self_prescript.item(row_no, col_no[position])
            if commission_item is None:
                continue

            total_commission += number_utils.get_integer(commission_item.text())

        return total_commission

    def _read_prescript(self, seller, position):
        seller_field = ''
        if position == '醫師':
            seller_field = 'cases.Doctor'
        elif position == '傷助推薦':
            seller_field = 'cases.MassageReferrer'
        elif position == '護佐':
            seller_field = 'cases.NursingAssistant'

        seller_condition = f'AND {seller_field} = "{seller}"'
        if seller == '合計':
            seller_condition = ''

        sql = f'''
            SELECT
                prescript.*,
                cases.CaseKey, cases.CaseDate AS SaleDate, cases.Period, cases.PatientKey, cases.Name, cases.InsType,
                cases.RegistType, cases.Doctor, cases.MassageReferrer, cases.NursingAssistant,
                cases.InvoiceNo, cases.TreatType
            FROM prescript
                LEFT JOIN cases ON prescript.CaseKey = cases.CaseKey
            WHERE
                cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                (prescript.MedicineSet >= 2 AND prescript.MedicineSet != 11 AND
                 (prescript.Price != 0 OR
                 (prescript.Price = 0 AND MedicineType NOT IN ("水藥", "穴道")))
                )
                {seller_condition}
            ORDER BY prescript.CaseKey, prescript.MedicineName, prescript.PrescriptKey
        '''
        rows = self.database.select_record(sql)

        self.ui.tableWidget_self_prescript.setRowCount(0)

        row_no = 0
        for row in rows:
            if not purchase_utils.set_purchase_list_data(
               self.database, self.ui.tableWidget_self_prescript, row, row_no):
                continue

            row_no += 1

        purchase_utils.calculate_purchase_list_total(self.ui.tableWidget_self_prescript)

    def export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出自費產品銷售統計",
            '{0}至{1}{2}自費產品銷售統計表.xlsx'.format(
                self.start_date[:10], self.end_date[:10], self.doctor
            ),
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_self_prescript, [0],
            [8, 16, 17, 18, 19, 20, 21, 22, 23, 25, 28, 30, 32]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            '<h3>自費產品銷售統計表{0}匯出完成.</h3>'.format(excel_file_name),
            'Microsoft Excel 格式.'
        )

    def _export_seller(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{self.year}-{self.month:0>2}自費銷售抽成總表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(excel_file_name, self.ui.tableWidget_seller)

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>醫師銷售業績統計檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _export_prescript(self):
        seller = self.ui.tableWidget_seller.item(self.ui.tableWidget_seller.currentRow(), 0).text()
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{self.year}-{self.month:0>2}{seller}自費銷售抽成明細.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_self_prescript, [0, 1], [9, 11, 12, 13, 14, 15, 17]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>自費銷售業績明細檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _print_self_prescript(self):
        printer_utils.print_purchase_list(
            self, self.database, self.system_settings,
            self.start_date, self.end_date,
            self.tableWidget_self_prescript,
        )

    def _print_seller(self):
        printer_utils.print_seller(
            self, self.database, self.system_settings,
            self.start_date, self.end_date, self.tableWidget_seller,
        )
        
