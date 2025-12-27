# -*- coding: UTF-8 -*-
# 櫃台購藥 2014.09.22

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox, QPushButton, QFileDialog
import datetime

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils
from libs import personnel_utils
from libs import export_utils
from libs import printer_utils
from libs import dialog_utils
from libs import stock_utils


# 櫃台購藥
class PurchaseList(QtWidgets.QMainWindow):
    program_name = '櫃台購藥'

    # 初始化
    def __init__(self, parent=None, *args):
        super(PurchaseList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self.dialog_setting = {
            "dialog_executed": False,
            "start_date": None,
            "end_date": None,
            "period": None,
            "cashier": None,
            "therapist": None,
            "massager": None,
        }
        self.sql = None
        self.purchase_mode = None

        self._set_ui()
        self._set_signal()
        self._set_permission()

        self.read_purchase_today()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PURCHASE_LIST, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_purchase_list = class_utils.get_table_widget(
            self.ui.tableWidget_purchase_list, self.database
        )
        self._set_table_width()
        self._set_tool_button()

    # 設定信號
    def _set_signal(self):
        self.ui.action_requery.triggered.connect(self.open_dialog)
        self.ui.action_purchase.triggered.connect(self._purchase)
        self.ui.action_delete_record.triggered.connect(self.delete_purchase)
        self.ui.action_open_record.triggered.connect(self.open_medical_record)
        self.ui.action_close.triggered.connect(self.close_purchase_list)
        self.ui.action_print_receipt.triggered.connect(self._print_receipt)
        self.ui.action_export_excel.triggered.connect(self._export_to_excel)
        self.ui.tableWidget_purchase_list.doubleClicked.connect(self.open_medical_record)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(self.database, self.program_name, '購買商品', self.user_name) != 'Y':
            self.ui.action_purchase.setEnabled(False)
        if personnel_utils.get_permission(self.database, self.program_name, '購藥明細', self.user_name) != 'Y':
            self.ui.action_open_record.setEnabled(False)
        if personnel_utils.get_permission(self.database, self.program_name, '資料刪除', self.user_name) != 'Y':
            self.ui.action_delete_record.setEnabled(False)
        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.action_export_excel.setEnabled(False)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [80, 180, 60, 90, 100, 700, 90, 90, 90, 90, 90, 90]
        self.table_widget_purchase_list.set_table_heading_width(width)
        self.table_widget_purchase_list.set_column_hidden([0])

    # 讀取病歷
    def _get_sql(self):
        dialog = dialog_utils.get_dialog_purchase_list(self.ui, self.database, self.system_settings)
        if self.dialog_setting['dialog_executed']:
            dialog.ui.dateEdit_start_date.setDate(self.dialog_setting['start_date'])
            dialog.ui.dateEdit_end_date.setDate(self.dialog_setting['end_date'])
            dialog.ui.comboBox_period.setCurrentText(self.dialog_setting['period'])
            dialog.ui.comboBox_cashier.setCurrentText(self.dialog_setting['cashier'])
            dialog.ui.comboBox_doctor.setCurrentText(self.dialog_setting['therapist'])
            dialog.ui.comboBox_massager.setCurrentText(self.dialog_setting['massager'])

        result = dialog.exec_()
        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['start_date'] = dialog.ui.dateEdit_start_date.date()
        self.dialog_setting['end_date'] = dialog.ui.dateEdit_end_date.date()
        self.dialog_setting['period'] = dialog.comboBox_period.currentText()
        self.dialog_setting['cashier'] = dialog.comboBox_cashier.currentText()
        self.dialog_setting['therapist'] = dialog.comboBox_doctor.currentText()
        self.dialog_setting['massager'] = dialog.comboBox_massager.currentText()

        sql = dialog.get_sql()
        start_date = dialog.ui.dateEdit_start_date.date().toString('yyyy-MM-dd')
        end_date = dialog.ui.dateEdit_end_date.date().toString('yyyy-MM-dd')

        dialog.close_all()
        dialog.deleteLater()

        if result == 0:
            return None, None, None
        else:
            return sql, start_date, end_date

    def open_dialog(self):
        self.sql, start_date, end_date = self._get_sql()
        if self.sql is None:
            return

        self.ui.label_data_period.setText(f'資料期間: {start_date} 至 {end_date}')
        self._read_purchase_list()

    def _read_purchase_list(self):
        if self.sql is None:
            return

        self.table_widget_purchase_list.set_db_data(self.sql, self._set_table_data)
        self._calculate_total()
        self._set_tool_button()

    def read_purchase_today(self):
        start_date = datetime.datetime.now().strftime('%Y-%m-%d')
        end_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self.ui.label_data_period.setText(f'資料期間: {start_date} 至 {end_date}')

        start_date += ' 00:00:00'
        end_date += ' 23:59:59'

        self.sql = f'''
            SELECT * FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                TreatType = "自購"
            ORDER BY CaseDate DESC
        '''

        self._read_purchase_list()

    def _set_tool_button(self):
        if self.ui.tableWidget_purchase_list.rowCount() > 0:
            enabled = True
        else:
            enabled = False

        self.ui.action_delete_record.setEnabled(enabled)
        self.ui.action_print_receipt.setEnabled(enabled)
        self.ui.action_open_record.setEnabled(enabled)

        self._set_permission()

    def _set_table_data(self, row_no, row):
        content = self._get_purchase_content(row['CaseKey'])
        discount_fee = number_utils.get_integer(row['DiscountFee'])

        purchase_row = [
            string_utils.xstr(row['CaseKey']),
            string_utils.xstr(row['CaseDate']),
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            content,
            number_utils.get_integer(row['SelfTotalFee']),
            discount_fee,
            number_utils.get_integer(row['TotalFee']),
            string_utils.xstr(row['Cashier']),
            string_utils.xstr(row['Doctor']),
            string_utils.xstr(row['Massager']),
        ]

        for col_no in range(len(purchase_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, purchase_row[col_no])
            self.ui.tableWidget_purchase_list.setItem(
                row_no, col_no, item
            )
            if col_no in [3, 6, 7, 8]:
                self.ui.tableWidget_purchase_list.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [2]:
                self.ui.tableWidget_purchase_list.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if discount_fee > 0:
                self.ui.tableWidget_purchase_list.item(row_no, col_no).setForeground(
                    QtGui.QColor('red')
                )

    def _get_purchase_content(self, case_key):
        sql = f'''
            SELECT * FROM prescript
            WHERE
                CaseKey = {case_key}
            ORDER BY PrescriptKey
        '''
        rows = self.database.select_record(sql)
        content = []
        for row in rows:
            medicine_name = string_utils.xstr(row['MedicineName'])
            quantity = string_utils.xstr(row['Dosage'])
            unit = string_utils.xstr(row['Unit'])
            content.append(f'{medicine_name} ({quantity}{unit})')

        return ', '.join(content)

    def _calculate_total(self):
        row_count = self.ui.tableWidget_purchase_list.rowCount()
        self_total_fee, discount_fee, total_fee = 0, 0, 0

        for row_no in range(row_count):
            if self.ui.tableWidget_purchase_list.item(row_no, 4).text() == '合計':
                continue

            self_total_fee += number_utils.get_integer(
                self.ui.tableWidget_purchase_list.item(row_no, 6).text()
            )
            discount_fee += number_utils.get_integer(
                self.ui.tableWidget_purchase_list.item(row_no, 7).text()
            )
            total_fee += number_utils.get_integer(
                self.ui.tableWidget_purchase_list.item(row_no, 8).text()
            )

        total_record = [
            None, None, None, None,
            '合計',
            None,
            string_utils.xstr(self_total_fee),
            string_utils.xstr(discount_fee),
            string_utils.xstr(total_fee),
        ]

        row_no = self._get_total_row_no()
        if row_no is None:
            self.ui.tableWidget_purchase_list.setRowCount(row_count+1)
        else:
            row_count = row_no

        font = QtGui.QFont()
        font.setBold(True)
        for col_no in range(len(total_record)):
            self.ui.tableWidget_purchase_list.setItem(
                row_count, col_no,
                QtWidgets.QTableWidgetItem(total_record[col_no])
            )
            if col_no in [6, 7, 8]:
                self.ui.tableWidget_purchase_list.item(
                    row_count, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            self.ui.tableWidget_purchase_list.item(row_count, col_no).setFont(font)

    def _get_total_row_no(self):
        row_no = None

        row_count = self.ui.tableWidget_purchase_list.rowCount()
        for i in range(row_count):
            if self.ui.tableWidget_purchase_list.item(i, 4).text() == '合計':
                row_no = i
                break

        return row_no

    def delete_purchase(self):
        case_key = self.table_widget_purchase_list.field_value(0)
        if case_key in [None, '']:
            return

        name = self.table_widget_purchase_list.field_value(4)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('刪除購藥資料')
        msg_box.setText(f"""
            <font size='4' color='red'>
                <b>確定刪除<font color='blue'> {name} </font>的購藥資料?</b>
            </font>
        """)
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        case_key = self.table_widget_purchase_list.field_value(0)
        if case_key is None:
            return

        if self.system_settings.field('調整庫存量') == '即時調整':
            stock_utils.restore_prescript_quantity(self.database, case_key)

        self.database.delete_record('prescript', 'CaseKey', case_key)
        self.database.delete_record('cases', 'CaseKey', case_key)
        self.database.delete_record('wait', 'CaseKey', case_key)
        current_row = self.ui.tableWidget_purchase_list.currentRow()
        self.ui.tableWidget_purchase_list.removeRow(current_row)
        self._calculate_total()

    def open_medical_record(self):
        self.purchase_mode = '購藥明細'

        case_key = self.table_widget_purchase_list.field_value(0)
        if case_key in [None, '']:
            return

        self.parent.open_medical_record(case_key, '櫃台購藥')

    def get_case_key(self):
        if self.purchase_mode == '購買商品':
            case_key = None
        else:
            case_key = self.table_widget_purchase_list.field_value(0)

        return case_key

    # 重新顯示資料 call from pymedical (call from here is not working)
    def refresh_purchase(self, in_case_key):
        self._read_purchase_list()
        if in_case_key in [None, '']:
            return

        for row_no in range(self.ui.tableWidget_purchase_list.rowCount()):
            item = self.ui.tableWidget_purchase_list.item(row_no, 0)
            if item is None:
                continue

            case_key = item.text()
            if in_case_key == case_key:
                self.ui.tableWidget_purchase_list.setCurrentCell(row_no, 1)

    # 輸入購物資料
    def _purchase(self):
        self.purchase_mode = '購買商品'

        self.parent.open_purchase_tab()

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_purchase_list(self):
        self.close_all()
        self.close_tab()

    def _print_receipt(self):
        case_key = self.table_widget_purchase_list.field_value(0)
        if case_key in [None, '']:
            return

        printer_utils.print_receipt_form(
            self, self.database, self.system_settings, case_key, '選擇列印')

    # 匯出自購藥 2019.07.01
    def _export_to_excel(self):
        if self.dialog_setting['start_date'] is None:
            return

        options = QFileDialog.Options()
        start_date = self.dialog_setting['start_date'].toString('yyyy-MM-dd')
        end_date = self.dialog_setting['end_date'].toString('yyyy-MM-dd')
        period = self.dialog_setting['period']
        title = f'{start_date}至{end_date}{period}自購藥報表'
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出自購藥",
            f'{title}.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_purchase_list,
            [0], [3, 6, 7, 8], title
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>自購藥報表{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )
