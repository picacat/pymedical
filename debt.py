
# 欠還款作業 2022.09.28
# -*- coding: UTF-8 -*-

import datetime

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from libs import (class_utils, date_utils, dialog_utils, export_utils,
                  number_utils, personnel_utils, string_utils, system_utils,
                  ui_utils)


# 欠還款作業
class Debt(QtWidgets.QMainWindow):
    program_name = '欠還款作業'

    # 初始化
    def __init__(self, parent=None, *args):
        super(Debt, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DEBT, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_debt = class_utils.get_table_widget(self.ui.tableWidget_debt, self.database)
        self.table_widget_debt.set_column_hidden([0, 1])
        self._set_date()
        # database._set_table_width()
        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.action_export_to_excel.setEnabled(False)

    def _set_date(self):
        this_year = datetime.date.today().replace(month=1, day=1)
        self.ui.dateEdit_start_date.setDate(this_year)
        self.ui.dateEdit_end_date.setDate(datetime.date.today())

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_debt)
        self.ui.action_pay_back.triggered.connect(self.pay_back)
        self.ui.action_add_debt.triggered.connect(self._add_debt)
        self.ui.action_find_debt.triggered.connect(lambda: self._select_patient(None))
        self.ui.action_modify_debt.triggered.connect(self._modify_debt)
        self.ui.action_remove_debt.triggered.connect(self._remove_debt)
        self.ui.tableWidget_debt.itemSelectionChanged.connect(self._debt_item_selection_changed)
        self.ui.action_open_medical_record.triggered.connect(self.open_medical_record)
        self.ui.action_export_to_excel.triggered.connect(self._export_to_excel)
        self.ui.tableWidget_debt.doubleClicked.connect(self.open_medical_record)
        self.ui.action_change_repayment_date.triggered.connect(self._change_repayment_date)
        self.ui.action_change_repayment_period.triggered.connect(self._change_repayment_period)
        self.ui.dateEdit_start_date.dateChanged.connect(lambda: self.read_debt(None))
        self.ui.dateEdit_end_date.dateChanged.connect(lambda: self.read_debt(None))
        self.ui.radioButton_debt.clicked.connect(lambda: self.read_debt(None))
        self.ui.radioButton_repayment.clicked.connect(lambda: self.read_debt(None))
        self.ui.radioButton_all.clicked.connect(lambda: self.read_debt(None))
        self.ui.action_clear_repayment.triggered.connect(self._clear_repayment)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(self.database, self.program_name, '現金還款', self.user_name) != 'Y':
            self.ui.action_pay_back.setEnabled(False)
        if personnel_utils.get_permission(self.database, self.program_name, '調閱病歷', self.user_name) != 'Y':
            self.ui.action_open_medical_record.setEnabled(False)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [80, 100, 40, 120, 100, 120, 60, 80, 80, 180, 120, 120, 120, 400]
        self.table_widget_income.set_table_heading_width(width)

    def read_debt(self, patient_key=None):
        self.ui.tableWidget_debt.setRowCount(0)

        if self.ui.radioButton_debt.isChecked():
            self._read_debt_data(patient_key)
        elif self.ui.radioButton_repayment.isChecked():
            self._read_repayment_data(patient_key)
        else:
            self._read_debt_data(patient_key)            
            self._read_repayment_data(patient_key)

        self.ui.tableWidget_debt.resizeColumnsToContents()
        self._set_tool_button()

    def _read_debt_data(self, patient_key=None):
        patient_key_script = ''
        if patient_key is not None:
            patient_key_script = f' AND debt.PatientKey = {patient_key}'

        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')
        sql = f'''
            SELECT debt.*, cases.Doctor FROM debt
                LEFT JOIN cases ON cases.CaseKey = debt.CaseKey
            WHERE
                debt.CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                (ReturnDate1 IS NULL OR
                 COALESCE(Fee1, 0) + COALESCE(Fee2, 0) + COALESCE(Fee3, 0) < COALESCE(Fee, 0))
                {patient_key_script}
            ORDER BY DATE(debt.CaseDate) DESC, PatientKey
        '''
        self.table_widget_debt.set_db_data(sql, self._set_table_data)

    def _read_repayment_data(self, patient_key=None):
        patient_key_script = ''
        if patient_key is not None:
            patient_key_script = f' AND debt.PatientKey = {patient_key}'

        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')
        sql = f'''
            SELECT * FROM debt
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                ReturnDate1 IS NOT NULL AND
                COALESCE(Fee1, 0) + COALESCE(Fee2, 0) + COALESCE(Fee3, 0) >= COALESCE(Fee, 0)      
                {patient_key_script}
            ORDER BY DATE(ReturnDate1) DESC, PatientKey
        '''
            
        rows = self.database.select_record(sql)

        row_no = self.ui.tableWidget_debt.rowCount()
        for row in rows:
            self.ui.tableWidget_debt.setRowCount(row_no+1)
            self._set_table_data(row_no, row)

            row_no += 1

    def _set_tool_button(self):
        if self.ui.tableWidget_debt.rowCount() <= 0:
            enabled = False
        else:
            enabled = True

        self.ui.action_open_medical_record.setEnabled(enabled)
        self.ui.action_pay_back.setEnabled(enabled)
        self.ui.action_remove_debt.setEnabled(enabled)

        self._set_permission()

    def _set_table_data(self, row_no, row):
        case_key = number_utils.get_integer(row['CaseKey'])
        if row['ReturnDate1'] is not None:
            return_date1 = row['ReturnDate1'].date()
        else:
            return_date1 = None

        if row['ReturnDate2'] is not None:
            return_date2 = row['ReturnDate2'].date()
        else:
            return_date2 = None

        if row['ReturnDate3'] is not None:
            return_date3 = row['ReturnDate3'].date()
        else:
            return_date3 = None

        debt = number_utils.get_integer(row['Fee'])
        return_fee1 = number_utils.get_integer(row['Fee1'])
        return_fee2 = number_utils.get_integer(row['Fee2'])
        return_fee3 = number_utils.get_integer(row['Fee3'])
        arrears = debt - return_fee1 - return_fee2 - return_fee3

        medical_record = [
            string_utils.xstr(row['DebtKey']),
            string_utils.xstr(case_key),
            string_utils.xstr(row['CaseDate'].date()),
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['DebtType']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            debt,
            string_utils.xstr(return_date1),
            string_utils.xstr(row['Period1']),
            return_fee1,
            string_utils.xstr(return_date2),
            string_utils.xstr(row['Period2']),
            return_fee2,
            string_utils.xstr(return_date3),
            string_utils.xstr(row['Period3']),
            return_fee3,
            arrears,
            string_utils.xstr(row['PaymentType']),
            string_utils.xstr(row['Cashier1']),
            string_utils.xstr(row['Doctor']),
        ]

        for col_no in range(len(medical_record)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medical_record[col_no])

            self.ui.tableWidget_debt.setItem(row_no, col_no, item)
            if col_no in [5, 7, 10, 13, 16, 17]:
                self.ui.tableWidget_debt.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [3, 4, 9]:
                self.ui.tableWidget_debt.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def pay_back(self):
        debt_key = self.table_widget_debt.field_value(0)
        case_key = self.table_widget_debt.field_value(1)

        dialog = dialog_utils.get_dialog_debt(
            self, self.database, self.system_settings, debt_key, case_key,
        )
        if dialog.exec_():
            self.refresh_record(debt_key)

        dialog.deleteLater()

    def refresh_record(self, debt_key):
        sql = f'''
            SELECT * FROM debt
            WHERE
                DebtKey = {debt_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            self._set_table_data(self.ui.tableWidget_debt.currentRow(), rows[0])

    def open_medical_record(self):
        if (self.user_name != '超級使用者' and
                personnel_utils.get_permission(self.database, self.program_name, '調閱病歷', self.user_name) != 'Y'):
            return

        case_key = self.table_widget_debt.field_value(1)
        self.parent.open_medical_record(case_key, '病歷查詢')

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_debt(self):
        self.close_all()
        self.close_tab()

    def _debt_item_selection_changed(self):
        self._set_tool_button()

    def _add_debt(self):
        dialog = dialog_utils.get_dialog_add_debt(
            self, self.database, self.system_settings
        )

        if dialog.exec_():
            self.read_debt()

        dialog.close_all()
        dialog.deleteLater()

    def _modify_debt(self):
        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')
        debt = number_utils.get_integer(self.table_widget_debt.field_value(7))
        debt, ok = input_dialog.getInt(
            self, '更改欠款', '請輸入欲更改的欠款金額', debt, 0, 1000000, 10)
        if not ok:
            return

        debt_key = self.table_widget_debt.field_value(0)
        self.database.exec_sql(f'UPDATE debt SET Fee = {debt} WHERE DebtKey = {debt_key}')
        self.refresh_record(debt_key)

    def _select_patient(self, keyword=None):
        dialog = dialog_utils.get_dialog_select_patient(
            self, self.database, self.system_settings, 'patient', 'PatientKey', keyword
        )
        if dialog.exec_():
            patient_key = dialog.get_primary_key()
        else:
            patient_key = None

        dialog.deleteLater()

        if patient_key not in ['', None]:
            self.read_debt(patient_key)

    def _remove_debt(self):
        msg_box = dialog_utils.get_message_box(
            '刪除欠款資料', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除此筆欠款資料?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_debt.field_value(0)
        self.database.delete_record('debt', 'DebtKey', key)
        self.ui.tableWidget_debt.removeRow(self.ui.tableWidget_debt.currentRow())

    def _export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出Excel檔案", f'{self.system_settings.field("院所名稱")}欠款資料.xlsx',
            "excel檔案 (*.xlsx)",
            options=options
        )

        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_debt, [0, 1], [5, 7, 10]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            'Excel資料匯出完成',
            f'<h3>{excel_file_name}匯出完成.</h3>',
            'Excel檔案格式.'
        )

    def _change_repayment_date(self):
        repayment_date = date_utils.get_dialog_date(
            self, self.database, self.system_settings, call_from=self.program_name)
        if repayment_date is None:
            return

        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        repayment_date = f'{repayment_date} {current_time}'

        debt_key = self.table_widget_debt.field_value(0)
        sql = f'''
            UPDATE debt
            SET
                ReturnDate1 = "{repayment_date}"
            WHERE
                DebtKey = {debt_key}
        '''
        self.database.exec_sql(sql)
        self.refresh_record(debt_key)

    def _change_repayment_period(self):
        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')
        items = ('早班', '午班', '晚班')
        period, ok = input_dialog.getItem(
            self, '選擇班別', '請選擇還款班別', items, 0, False)
        if not ok or not period:
            return

        debt_key = self.table_widget_debt.field_value(0)
        sql = f'''
            UPDATE debt
            SET
                Period1 = "{period}"
            WHERE
                DebtKey = {debt_key}
        '''
        self.database.exec_sql(sql)
        self.refresh_record(debt_key)

    def _clear_repayment(self):
        msg_box = dialog_utils.get_message_box(
            '還原成未還款狀態', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定還原此筆還款資料為未還款狀態?</b></font>',
            '注意！資料回復後, 將變成欠款狀態!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        debt_key = self.table_widget_debt.field_value(0)
        sql = f'''
            UPDATE debt
            SET
                PaymentType = NULL,

                ReturnDate1 = NULL,
                Period1 = NULL,
                Cashier1 = NULL,
                Fee1 = NULL,

                ReturnDate2 = NULL,
                Period2 = NULL,
                Cashier2 = NULL,
                Fee2 = NULL,

                ReturnDate3 = NULL,
                Period3 = NULL,
                Cashier3 = NULL,
                Fee3 = NULL,

                TotalReturn = NULL
            WHERE
                DebtKey = {debt_key}
        '''
        self.database.exec_sql(sql)

        self.refresh_record(debt_key)
