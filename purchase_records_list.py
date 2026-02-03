
# -*- coding: utf-8 -*-

import datetime

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from libs import (charge_utils, date_utils, db_utils, dialog_utils,
                  export_utils, medicine_utils, number_utils, personnel_utils,
                  prescript_utils, printer_utils, purchase_utils, system_utils,
                  ui_utils)


# 自費銷售記錄 2021.10.01
class PurchaseRecordList(QtWidgets.QMainWindow):
    """自費銷售記錄"""
    
    # 初始化
    def __init__(self, parent=None, *args):
        super(PurchaseRecordList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.dialog = args[2]
        self.no_zero_bonus = args[3]
        self.ui = None

        self.start_date = self.dialog.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')
        self.end_date = self.dialog.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')
        if self.dialog.ui.radioButton_period1.isChecked():
            self.period = '早班'
        elif self.dialog.ui.radioButton_period2.isChecked():
            self.period = '午班'
        elif self.dialog.ui.radioButton_period3.isChecked():
            self.period = '晚班'
        else:
            self.period = '全部'

        self.programe_name = '自費銷售記錄'
        self.user_name = system_utils.get_user_name(self.system_settings)

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PURCHASE_RECORDS_LIST, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        purchase_utils.set_purchase_list_table(self.database, self.ui.tableWidget_self_prescript)
        purchase_utils.set_purchase_list_table(self.database, self.ui.tableWidget_self_prescript_agent)
        self._set_text_edit_remark()
        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.toolButton_export_agent.setEnabled(False)

    def _set_text_edit_remark(self):
        html = '''
            <html>
                <head>
                    <meta charset="UTF-8">
                </head>
                <body>
                    注意事項
                    <ol>
                        <li>
                            <font color="red">
                                若折扣金額低於售價8折，則沒有抽成； 8折以上，抽成減半。
                            </font>
                        </li>
                        <li>換貨時，須注意金額是否沖銷平衡</li>
                        <li>未付清品項不得換貨</li>
                        <li>產品名稱若包含「代收」關鍵字，該筆記錄不會列在銷售記錄內，而是列在代收費用。</li>
                    </ol>
                </body>
            </html>
        '''
        self.ui.textEdit_remark.setHtml(html)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_self_prescript.doubleClicked.connect(self._open_medical_record)
        self.ui.tableWidget_self_prescript.itemSelectionChanged.connect(self._prescript_item_changed)
        self.ui.toolButton_return.clicked.connect(self._return_button_pressed)
        self.ui.toolButton_return_course.clicked.connect(self._return_course)
        self.ui.toolButton_set_discount.clicked.connect(self._set_discount)
        self.ui.toolButton_exchange.clicked.connect(self._exchange_button_pressed)
        self.ui.toolButton_delete.clicked.connect(self._delete_prescript)
        self.ui.toolButton_set_person.clicked.connect(self._set_person)
        self.ui.toolButton_set_single_person.clicked.connect(self._set_single_person)
        self.ui.toolButton_set_debt.clicked.connect(self._set_debt)
        self.ui.toolButton_set_agent_debt.clicked.connect(self._set_agent_debt)
        self.ui.toolButton_repayment.clicked.connect(self._set_repayment)
        self.ui.toolButton_export_agent.clicked.connect(self._export_agent)

    def _open_medical_record(self):
        row_no = self.ui.tableWidget_self_prescript.currentRow()
        case_key_item = self.ui.tableWidget_self_prescript.item(row_no, purchase_utils.PURCHASE_COL_NO['case_key'])
        if case_key_item is None:
            return

        self.parent.parent.open_medical_record(case_key_item.text())

    def start_calculate(self):
        rows = self._read_prescript()
        self._set_prescript_table(rows)

        agent_rows = self._read_agent_prescript()
        self._set_agent_prescript_table(agent_rows)

    def _get_advance_sql(self):
        sql = ''
        patient_key = self.dialog.lineEdit_patient_key.text().strip()
        doctor = self.dialog.comboBox_doctor.currentText()
        massage_referrer = self.dialog.comboBox_massage_referrer.currentText()
        nursing_assistant = self.dialog.comboBox_nursing_assistant.currentText()
        medicine_name = self.dialog.lineEdit_medicine_name.text().strip()

        if patient_key != '':
            sql += f'AND cases.PatientKey = {patient_key}'
        if doctor != '':
            sql += f'AND cases.Doctor = "{doctor}"'
        if massage_referrer != '':
            sql += f'AND cases.MassageReferrer = "{massage_referrer}"'
        if nursing_assistant != '':
            sql += f'AND cases.NursingAssistant = "{nursing_assistant}"'
        if medicine_name != '':
            sql += f'AND MedicineName LIKE "%{medicine_name}%"'

        return sql

    def _get_sql_condition(self):
        sql_condition = '''
            (prescript.MedicineSet >= 2 AND
             prescript.MedicineSet != 11 AND
             MedicineName != "民俗調理"
             AND MedicineName NOT LIKE "%代收%")
        '''

        if self.dialog.ui.radioButton_date.isChecked():                 # 日期查詢
            if self.period != '全部':
                sql_condition += f'''
                    AND (
                        (cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                            cases.Period = "{self.period}") OR
                        (prescript.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                            cases.Period = "{self.period}") OR
                        (debt.ReturnDate1 BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                            debt.Period1 = "{self.period}" AND debt.PrescriptKey > 0)
                    )
                '''
            else:
                sql_condition += f'''
                    AND (
                        (cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") OR
                        prescript.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" OR
                        (debt.ReturnDate1 BETWEEN "{self.start_date}" AND "{self.end_date}" AND debt.PrescriptKey > 0)
                    )
                '''

            if self.dialog.checkBox_debt.isChecked():
                sql_condition += ' AND cases.TotalFee > ReceiptFee'

            if self.dialog.ui.groupBox_advance.isChecked():
                sql_condition += self._get_advance_sql()
        elif self.dialog.ui.radioButton_invoice_no.isChecked():         # 單據號碼
            invoice_no = self.dialog.ui.lineEdit_invoice_no.text().strip()
            invoice_no_2 = self.dialog.ui.lineEdit_invoice_no_2.text().strip()
            if invoice_no_2 != '':
                sql_condition += f' AND cases.InvoiceNo BETWEEN "{invoice_no}" AND "{invoice_no_2}"'
            else:
                sql_condition += f' AND cases.InvoiceNo = "{invoice_no}"'

        return sql_condition

    def _read_prescript(self, prescript_key=None):
        sql_condition = ''

        if prescript_key is not None:
            sql_condition = f'prescript.PrescriptKey = {prescript_key}'
        else:
            sql_condition = self._get_sql_condition()

        sql = f'''
            SELECT
                prescript.*,
                cases.CaseKey, cases.CaseDate AS SaleDate, cases.Period, cases.PatientKey, cases.Name, cases.InsType,
                cases.Doctor, cases.MassageReferrer, cases.NursingAssistant,
                cases.InvoiceNo, cases.TreatType
            FROM prescript
                LEFT JOIN cases ON prescript.CaseKey = cases.CaseKey
                LEFT JOIN debt ON debt.CaseKey = prescript.CaseKey
            WHERE
                {sql_condition}
            GROUP BY prescript.PrescriptKey
            ORDER BY prescript.CaseKey, prescript.PrescriptNo, PrescriptKey
        '''
        # ORDER BY prescript.CaseKey, prescript.TimeStamp

        rows = self.database.select_record(sql)

        return rows

    def _is_herb_or_powder(self, case_key):
        sql = f'''
            SELECT * FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineName IN ("自費水藥", "自費粉藥")
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return True

        return False

    def _check_single_compound(self, case_key, medicine_type):
        if medicine_type == '成方表頭':
            return False

        sql = f'''
            SELECT MedicineKey FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineType = "成方表頭"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return False

        row = rows[0]
        medicine_key = row['MedicineKey']
        single_compound = medicine_utils.get_medicine_extend(self.database, medicine_key, '成方單項')
        title_compound = medicine_utils.get_medicine_extend(self.database, medicine_key, '成方抬頭')
        if single_compound == 'Y' and title_compound == 'Y':
            return True

        return False

    def _set_prescript_table(self, rows):
        self.ui.tableWidget_self_prescript.setRowCount(0)
        row_no = 0
        for row in rows:
            if not purchase_utils.set_purchase_list_data(
                    self.database, self.ui.tableWidget_self_prescript, row, row_no,
                    query_start_date=self.start_date[:10], query_end_date=self.end_date[:10]):
                continue

            row_no += 1

        if self.no_zero_bonus:
            self._filter_zero_bonus()

        purchase_utils.calculate_purchase_list_total(
            self.ui.tableWidget_self_prescript, self.start_date[:10], self.end_date[:10])

    def _filter_zero_bonus(self):
        for row_no in range(self.ui.tableWidget_self_prescript.rowCount(), -1, -1):
            bonus = self.ui.tableWidget_self_prescript.item(
                row_no, purchase_utils.PURCHASE_COL_NO['doctor_commission'])
            if bonus is None or number_utils.get_integer(bonus.text()) == 0:
                self.ui.tableWidget_self_prescript.hideRow(row_no)

    def _get_return_quantity(self, row_no):
        medicine_name = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['medicine_name']).text()
        quantity = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['quantity']).text()
        quantity = number_utils.get_integer(quantity)

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')
        quantity, ok = input_dialog.getInt(
            self, '退貨', f'請輸入<font color="blue"><b>「{medicine_name}」</font>退貨數量', 1, 1, quantity, 1)
        if not ok:
            return None

        return quantity

    def _get_return_dealer(self):
        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')

        items = personnel_utils.get_person(self.database, '全部')
        dealer, ok = input_dialog.getItem(
            self, '經手人', '請選擇經手人', items, 0, False)

        if not ok:
            return None

        return dealer

    def _return_button_pressed(self):
        row_no = self.ui.tableWidget_self_prescript.currentRow()
        case_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['case_key']).text()
        medicine_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['medicine_key']).text()
        medicine_name = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['medicine_name']).text()
        invoice_no = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['invoice_no']).text()

        dialog = dialog_utils.get_dialog_return_goods(
            self, self.database, self.system_settings, case_key, medicine_key, medicine_name, invoice_no,
        )
        if not dialog.exec_():
            dialog.deleteLater()
            return

        return_date = dialog.ui.dateEdit_return_date.date().toString('yyyy-MM-dd')
        quantity = dialog.ui.spinBox_quantity.value()
        dealer = dialog.ui.comboBox_dealer.currentText()

        self._return_goods(row_no, return_date, quantity, dealer)

        system_utils.show_message_box(
            QMessageBox.Information,
            '退貨完成',
            '<font size="5" color="blue"><b>已完成退貨作業.</b></font>',
            '退貨成功.'
        )
        dialog.deleteLater()

    def _get_start_row_no(self, row_no, invoice_no):
        for i in range(row_no, -1, -1):
            row_no = i

            item = self.ui.tableWidget_self_prescript.item(
                i-1, purchase_utils.PURCHASE_COL_NO['invoice_no'])
            if item is None:
                break

            if item.text() != invoice_no:
                break

        return row_no

    def _get_end_row_no(self, row_no, invoice_no):
        for i in range(row_no, self.ui.tableWidget_self_prescript.rowCount()):
            row_no = i

            item = self.ui.tableWidget_self_prescript.item(
                i+1, purchase_utils.PURCHASE_COL_NO['invoice_no'])
            if item is None:
                break

            if item.text() != invoice_no:
                break

        return row_no

    def _return_course(self):
        row_no = self.ui.tableWidget_self_prescript.currentRow()
        invoice_no = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['invoice_no']).text()
        if invoice_no in ['', None]:
            return

        start_row_no = self._get_start_row_no(row_no, invoice_no)
        end_row_no = self._get_end_row_no(row_no, invoice_no)

        dialog = dialog_utils.get_dialog_calendar(self, self.database, self.system_settings, '自費銷售記錄')
        today = datetime.datetime.today()

        dialog.ui.calendarWidget.setSelectedDate(today)
        dialog.ui.groupBox_calendar.setTitle('請選擇退貨日期')

        if not dialog.exec_():
            dialog.deleteLater()
            return

        return_date = dialog.ui.calendarWidget.selectedDate().toString('yyyy-MM-dd')
        dealer = self.system_settings.field('使用者')
        current_row_no = start_row_no
        for i in range(start_row_no, end_row_no+1):
            quantity = number_utils.get_integer(self.ui.tableWidget_self_prescript.item(
                current_row_no, purchase_utils.PURCHASE_COL_NO['quantity']).text())
            self._return_goods(current_row_no, return_date, quantity, dealer)
            current_row_no += 2

    def _return_goods(self, row_no, return_date, quantity, dealer):
        prescript_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['prescript_key']).text()
        db_utils.update_timestamp(self.database, 'prescript', 'PrescriptKey', prescript_key)

        case_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['case_key']).text()
        medicine_set = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['medicine_set']).text()
        medicine_type = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['medicine_type']).text()
        medicine_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['medicine_key']).text()
        medicine_name = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['medicine_name']).text()
        unit = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['unit']).text()
        price = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['price']).text()
        discount = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['discount']).text()
        promotion = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['promotion']).text()
        remark = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['remark']).text()
        debt = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['debt']).text()

        price = number_utils.get_integer(price)
        discount = -number_utils.get_integer(discount)
        quantity = -number_utils.get_integer(quantity)
        amount = price * quantity

        medicine_name += ' (退貨)'

        fields = [
            'CaseKey', 'CaseDate', 'MedicineSet', 'MedicineType', 'MedicineKey',
            'MedicineName', 'Dosage', 'Unit', 'Price', 'DiscountFee', 'Amount',
            'Promotion', 'Dealer', 'Remark', 'debt',
        ]
        data = [
            case_key, return_date, medicine_set, medicine_type, medicine_key,
            medicine_name, quantity, unit, price, discount, amount,
            promotion, dealer, remark, debt,
        ]
        prescript_key = self.database.insert_record('prescript', fields, data)
        self._insert_row(prescript_key, row_no+1)
        self._update_self_fees(case_key, medicine_type, amount)

        purchase_utils.calculate_purchase_list_total(self.ui.tableWidget_self_prescript)

        self.ui.tableWidget_self_prescript.removeRow(self.ui.tableWidget_self_prescript.rowCount() - 1)

    def _update_self_fees(self, case_key, medicine_type, amount):
        field = charge_utils.get_medicine_type_charge_field(self.database, medicine_type)
        charge_field = charge_utils.get_charge_field(field, medicine_type)
        if charge_field == 'diag_fee':
            charge_field = 'SDiagFee'
        elif charge_field == 'drug_fee':
            charge_field = 'SDrugFee'
        elif charge_field == 'herb_fee':
            charge_field = 'SHerbFee'
        elif charge_field == 'expensive_fee':
            charge_field = 'SExpensiveFee'
        elif charge_field == 'acupuncture_fee':
            charge_field = 'SAcupunctureFee'
        elif charge_field == 'massage_fee':
            charge_field = 'SMassageFee'
        elif charge_field == 'material_fee':
            charge_field = 'SMaterialFee'
        elif charge_field == 'exam_fee':
            charge_field = 'SExamFee'
        else:
            charge_field = 'SDrugFee'

        sql = f'''
            UPDATE cases SET
                {charge_field} = {charge_field} + {amount},
                SelfTotalFee = SelfTotalFee + {amount},
                TotalFee = TotalFee + {amount},
                ReceiptFee = TotalFee
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

    def _insert_row(self, prescript_key, row_no):
        rows = self._read_prescript(prescript_key=prescript_key)
        if len(rows) <= 0:
            return

        row = rows[0]
        self.ui.tableWidget_self_prescript.insertRow(row_no)
        purchase_utils.set_purchase_list_data(self.database, self.ui.tableWidget_self_prescript, row, row_no)

    def _delete_prescript(self):
        msg_box = dialog_utils.get_message_box(
            '退貨刪除', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除退貨的資料嗎?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        row_no = self.ui.tableWidget_self_prescript.currentRow()
        prescript_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['prescript_key']).text()
        price = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['price']).text()

        case_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['case_key']).text()
        medicine_type = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['medicine_type']).text()
        amount = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['total_fee']).text()
        amount = abs(number_utils.get_integer(amount))

        self.database.exec_sql(f'DELETE FROM prescript WHERE PrescriptKey = {prescript_key}')
        self.ui.tableWidget_self_prescript.removeRow(row_no)
        self._update_self_fees(case_key, medicine_type, amount)

        purchase_utils.calculate_purchase_list_total(self.ui.tableWidget_self_prescript)

    def _prescript_item_changed(self):
        enabled = True
        course_enabled = True

        row_no = self.ui.tableWidget_self_prescript.currentRow()
        try:
            medicine_name = self.ui.tableWidget_self_prescript.item(
                row_no, purchase_utils.PURCHASE_COL_NO['medicine_name']).text()
        except Exception:
            medicine_name = ''

        invoice_no = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['invoice_no'])
        if invoice_no is None or invoice_no.text() == '':
            course_enabled = False

        if '合計' in medicine_name or '(退貨)' in medicine_name or '(換貨)' in medicine_name:
            enabled = False
        elif purchase_utils.is_returned_goods(self.database, self.ui.tableWidget_self_prescript, row_no):
            enabled = False

        self.ui.toolButton_return.setEnabled(enabled)
        self.ui.toolButton_return_course.setEnabled(course_enabled)
        self.ui.toolButton_set_discount.setEnabled(enabled)
        self.ui.toolButton_exchange.setEnabled(enabled)
        self.ui.toolButton_set_person.setEnabled(enabled)
        self.ui.toolButton_set_single_person.setEnabled(enabled)
        self.ui.toolButton_delete.setEnabled(not enabled)

        if '合計' in medicine_name:
            self.ui.toolButton_delete.setEnabled(enabled)

        debt = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['debt'])

        if debt is not None and number_utils.get_integer(debt.text()) > 0:
            self.ui.toolButton_exchange.setEnabled(False)

        if debt is not None and number_utils.get_integer(debt.text()) > 0 and '合計' not in medicine_name:
            self.ui.toolButton_repayment.setEnabled(True)
        else:
            self.ui.toolButton_repayment.setEnabled(False)

    def _exchange_button_pressed(self):
        row_no = self.ui.tableWidget_self_prescript.currentRow()
        case_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['case_key']).text()
        medicine_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['medicine_key']).text()
        medicine_set = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['medicine_set']).text()
        medicine_name = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['medicine_name']).text()
        quantity = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['quantity']).text()
        quantity = number_utils.get_integer(quantity)
        invoice_no = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['invoice_no']).text()
        receipt_fee = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['receipt_fee']).text()

        dialog = dialog_utils.get_dialog_exchange_goods(
            self, self.database, self.system_settings, case_key, medicine_key, medicine_set,
            medicine_name, quantity, invoice_no, receipt_fee)

        if not dialog.exec_():
            dialog.deleteLater()
            return

        exchange_date = dialog.ui.dateEdit_exchange_date.date().toString('yyyy-MM-dd')
        quantity = dialog.ui.spinBox_quantity.value()
        dealer = dialog.ui.comboBox_dealer.currentText()
        self._return_goods(row_no, exchange_date, quantity, dealer)

        for i in range(dialog.tableWidget_prescript.rowCount()):
            check_box = dialog.tableWidget_prescript.cellWidget(
                i, purchase_utils.PRESCRIPT_COL_NO['Promotion'])

            if check_box.isChecked():
                promotion = '是'
            else:
                promotion = None

            medicine_row = {
                'medicine_key': dialog.ui.tableWidget_prescript.item(
                    i, purchase_utils.PRESCRIPT_COL_NO['MedicineKey']).text(),
                'medicine_type': dialog.ui.tableWidget_prescript.item(
                    i, purchase_utils.PRESCRIPT_COL_NO['MedicineType']).text(),
                'medicine_name': dialog.ui.tableWidget_prescript.item(
                    i, purchase_utils.PRESCRIPT_COL_NO['MedicineName']).text(),
                'unit': dialog.ui.tableWidget_prescript.item(
                    i, purchase_utils.PRESCRIPT_COL_NO['Unit']).text(),
                'quantity': dialog.ui.tableWidget_prescript.item(
                    i, purchase_utils.PRESCRIPT_COL_NO['Quantity']).text(),
                'price': dialog.ui.tableWidget_prescript.item(
                    i, purchase_utils.PRESCRIPT_COL_NO['Price']).text(),
                'amount': dialog.ui.tableWidget_prescript.item(
                    i, purchase_utils.PRESCRIPT_COL_NO['Amount']).text(),
                'discount_fee': dialog.ui.tableWidget_prescript.item(
                    i, purchase_utils.PRESCRIPT_COL_NO['DiscountFee']).text(),
                'promotion': promotion,
            }
            self._exchange_goods(row_no, exchange_date, medicine_row, dealer)

    def _exchange_goods(self, row_no, exchange_date, medicine_row, dealer):
        prescript_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['prescript_key']).text()
        db_utils.update_timestamp(self.database, 'prescript', 'PrescriptKey', prescript_key)

        case_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['case_key']).text()
        medicine_set = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['medicine_set']).text()

        medicine_key = medicine_row['medicine_key']
        medicine_type = medicine_row['medicine_type']
        medicine_name = medicine_row['medicine_name']
        unit = medicine_row['unit']
        try:
            quantity = number_utils.get_float(medicine_row['quantity'])
        except Exception:
            quantity = None

        price = medicine_row['price']
        amount = medicine_row['amount']
        discount_fee = medicine_row['discount_fee']

        if medicine_row['promotion']:
            promotion = '是'
        else:
            promotion = None

        medicine_name += ' (換貨)'

        fields = [
            'CaseKey', 'CaseDate', 'MedicineSet', 'MedicineType', 'MedicineKey',
            'MedicineName', 'Dosage', 'Unit', 'Price', 'Amount',
            'Promotion', 'DiscountFee', 'Dealer',
        ]
        data = [
            case_key, exchange_date, medicine_set, medicine_type, medicine_key,
            medicine_name, quantity, unit, price, amount,
            promotion, discount_fee, dealer,
        ]
        prescript_key = self.database.insert_record('prescript', fields, data)
        self._insert_row(prescript_key, row_no+2)
        self._update_self_fees(case_key, medicine_type, amount)
        purchase_utils.calculate_purchase_list_total(self.ui.tableWidget_self_prescript)
        self.ui.tableWidget_self_prescript.removeRow(self.ui.tableWidget_self_prescript.rowCount() - 1)

    def export_prescript(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{self.start_date[:10]}至{self.end_date[:10]}自費銷售抽成明細.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_self_prescript,
            [purchase_utils.PURCHASE_COL_NO['prescript_key'],
             purchase_utils.PURCHASE_COL_NO['case_key'],
             purchase_utils.PURCHASE_COL_NO['medicine_set'],
             purchase_utils.PURCHASE_COL_NO['medicine_type'],
             purchase_utils.PURCHASE_COL_NO['medicine_key']],
            [
             purchase_utils.PURCHASE_COL_NO['patient_key'],
             purchase_utils.PURCHASE_COL_NO['quantity'],
             purchase_utils.PURCHASE_COL_NO['price'],
             purchase_utils.PURCHASE_COL_NO['pres_days'],
             purchase_utils.PURCHASE_COL_NO['discount'],
             purchase_utils.PURCHASE_COL_NO['total_fee'],
             purchase_utils.PURCHASE_COL_NO['receipt_fee'],
             purchase_utils.PURCHASE_COL_NO['debt'],
             purchase_utils.PURCHASE_COL_NO['repayment'],
             purchase_utils.PURCHASE_COL_NO['return_fee'],
             purchase_utils.PURCHASE_COL_NO['doctor_commission'],
             purchase_utils.PURCHASE_COL_NO['massager_commission'],
             purchase_utils.PURCHASE_COL_NO['cashier_commission']]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>自費銷售業績明細檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def print_purchase_list(self):
        printer_utils.print_purchase_list(
            self, self.database, self.system_settings, self.start_date[:10], self.end_date[:10],
            self.tableWidget_self_prescript, self.tableWidget_self_prescript_agent,
            no_zero_bonus=self.no_zero_bonus,
        )

    def _set_person(self):
        row_no = self.ui.tableWidget_self_prescript.currentRow()
        case_key_item = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['case_key'])
        if case_key_item is None:
            system_utils.show_message_box(
                QMessageBox.Information,
                '注意',
                '<font size="5" color="red"><b>請選擇銷售資料.</b></font>',
                '未選擇任何資料.'
            )
            return

        case_key = case_key_item.text()
        prescript_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['prescript_key']).text()

        dialog = dialog_utils.get_dialog_set_person(
            self, self.database, self.system_settings, case_key, prescript_key, '銷售設定'
        )

        if not dialog.exec_():
            dialog.deleteLater()
            return

        fields = ['InvoiceNo', 'MassageReferrer', 'NursingAssistant']
        data = [
            dialog.ui.lineEdit_invoice_no.text(),
            dialog.ui.comboBox_massage_referrer.currentText(),
            dialog.ui.comboBox_nursing_assistant.currentText(),
        ]
        self.database.update_record('cases', fields, 'CaseKey', case_key, data)

        if dialog.ui.checkBox_promotion.isChecked():
            promotion_script = ',Promotion = "Y"'
        else:
            promotion_script = ',Promotion = NULL'

        sql = f'''
            UPDATE prescript
            SET
                Dealer = "{dialog.ui.comboBox_dealer.currentText()}",
                Remark = "{dialog.ui.textEdit_remark.toPlainText()}"
                {promotion_script}
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2
        '''
        self.database.exec_sql(sql)

        dialog.deleteLater()

        self._refresh_by_cases(case_key)

    def _set_single_person(self):
        row_no = self.ui.tableWidget_self_prescript.currentRow()
        case_key_item = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['case_key'])
        if case_key_item is None:
            system_utils.show_message_box(
                QMessageBox.Information,
                '注意',
                '<font size="5" color="red"><b>請選擇單一品項資料.</b></font>',
                '未選擇任何資料.'
            )
            return

        case_key = case_key_item.text()
        prescript_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['prescript_key']).text()

        dialog = dialog_utils.get_dialog_set_person(
            self, self.database, self.system_settings, case_key, prescript_key, '單一品項銷售設定'
        )

        if not dialog.exec_():
            dialog.deleteLater()
            return

        fields = ['InvoiceNo']
        data = [
            dialog.ui.lineEdit_invoice_no.text(),
        ]
        self.database.update_record('cases', fields, 'CaseKey', case_key, data)

        massage_referrer = dialog.ui.comboBox_massage_referrer.currentText()
        nursing_assistant = dialog.ui.comboBox_nursing_assistant.currentText()

        prescript_utils.remove_pres_extend_row(self.database, prescript_key, '傷助推薦')
        prescript_utils.remove_pres_extend_row(self.database, prescript_key, '護佐')

        if massage_referrer != '':
            prescript_utils.insert_pres_extend_row(self.database, prescript_key, '傷助推薦', massage_referrer)

        if nursing_assistant != '':
            prescript_utils.insert_pres_extend_row(self.database, prescript_key, '護佐', nursing_assistant)

        if dialog.ui.checkBox_promotion.isChecked():
            promotion_script = ',Promotion = "Y"'
        else:
            promotion_script = ',Promotion = NULL'

        sql = f'''
            UPDATE prescript
            SET
                Dealer = "{dialog.ui.comboBox_dealer.currentText()}",
                Remark = "{dialog.ui.textEdit_remark.toPlainText()}"
                {promotion_script}
            WHERE
                PrescriptKey = {prescript_key}
        '''
        self.database.exec_sql(sql)

        dialog.deleteLater()

        self._refresh_by_prescript(row_no, prescript_key)

    def _refresh_by_cases(self, in_case_key):
        for row_no in range(self.ui.tableWidget_self_prescript.rowCount()):
            case_key_item = self.ui.tableWidget_self_prescript.item(
                row_no, purchase_utils.PURCHASE_COL_NO['case_key'])
            if case_key_item is None:
                continue

            if in_case_key == case_key_item.text():
                prescript_key = self.ui.tableWidget_self_prescript.item(
                    row_no, purchase_utils.PURCHASE_COL_NO['prescript_key']).text()
                rows = self._read_prescript(prescript_key=prescript_key)
                if len(rows) <= 0:
                    continue

                row = rows[0]
                purchase_utils.set_purchase_list_data(
                    self.database, self.ui.tableWidget_self_prescript, row, row_no, refresh_record=True)

        purchase_utils.calculate_purchase_list_total(self.ui.tableWidget_self_prescript)

    def _refresh_by_prescript(self, row_no, in_prescript_key):
        rows = self._read_prescript(prescript_key=in_prescript_key)
        if len(rows) <= 0:
            return

        row = rows[0]
        purchase_utils.set_purchase_list_data(
            self.database, self.ui.tableWidget_self_prescript, row, row_no, refresh_record=True)
        purchase_utils.calculate_purchase_list_total(self.ui.tableWidget_self_prescript)

    def _set_debt(self):
        row_no = self.ui.tableWidget_self_prescript.currentRow()
        prescript_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['prescript_key']).text()

        rows = self.database.select_record(f'SELECT Amount, Debt FROM prescript WHERE PrescriptKey = {prescript_key}')
        if len(rows) <= 0:
            return

        row = rows[0]
        debt = number_utils.get_integer(row['Debt'])
        amount = number_utils.get_integer(row['Amount'])

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')
        debt, ok = input_dialog.getInt(self, '設定欠款', '請輸入欠款', debt, 0, 99999999, 1)
        if not ok:
            return

        sql = f'''
            UPDATE prescript
            SET
                Debt = {debt}
            WHERE
                PrescriptKey = {prescript_key}
        '''
        self.database.exec_sql(sql)

        self._refresh_by_prescript(row_no, prescript_key)
        self._insert_debt(row_no, prescript_key, debt)
        self._prescript_item_changed()
        purchase_utils.calculate_purchase_list_total(
            self.ui.tableWidget_self_prescript, self.start_date[:10], self.end_date[:10])
        
    def _set_agent_debt(self):
        row_no = self.ui.tableWidget_self_prescript_agent.currentRow()
        prescript_key_item = self.ui.tableWidget_self_prescript_agent.item(
            row_no, purchase_utils.PURCHASE_COL_NO['prescript_key'])
        if prescript_key_item is None:
            system_utils.show_message_box(
                QMessageBox.Information,
                '注意',
                '<font size="5" color="red"><b>請選擇代收費用的資料.</b></font>',
                '未選擇任何資料.'
            )
            return

        prescript_key = prescript_key_item.text()
        rows = self.database.select_record(f'SELECT Amount, Debt FROM prescript WHERE PrescriptKey = {prescript_key}')
        if len(rows) <= 0:
            return

        row = rows[0]
        debt = number_utils.get_integer(row['Debt'])

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')
        debt, ok = input_dialog.getInt(self, '設定欠款', '請輸入欠款', debt, 0, 99999999, 1)
        if not ok:
            return

        sql = f'''
            UPDATE prescript
            SET
                Debt = {debt}
            WHERE
                PrescriptKey = {prescript_key}
        '''
        self.database.exec_sql(sql)

        row = self._read_agent_prescript(prescript_key=prescript_key)[0]
        purchase_utils.set_purchase_list_data(
            self.database, self.ui.tableWidget_self_prescript_agent, row, row_no)
        self._insert_debt(row_no, prescript_key, debt)

    def _insert_debt(self, row_no, prescript_key, debt_fee):
        case_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['case_key']).text()
        case_date = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['case_date']).text()
        period = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['period']).text()
        patient_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['patient_key']).text()
        name = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['name']).text()
        doctor = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['doctor']).text()

        self.database.exec_sql(f'DELETE FROM debt WHERE PrescriptKey = {prescript_key}')  # 清除原有的欠款
        fields = ['DebtFee']
        data = [debt_fee]
        self.database.exec_sql(f'UPDATE cases SET DebtFee = {debt_fee} WHERE CaseKey = {case_key}')

        if debt_fee <= 0:
            return

        fields = [
            'CaseKey', 'PrescriptKey', 'PatientKey', 'DebtType', 'Name', 'CaseDate', 'Period', 'Doctor', 'Fee'
        ]

        data = [
            case_key,
            prescript_key,
            patient_key,
            '批價欠款',
            name,
            case_date,
            period,
            doctor,
            debt_fee,
        ]
        self.database.insert_record('debt', fields, data)

    def _set_repayment(self):
        repayment_date = date_utils.get_dialog_date(
            self, self.database, self.system_settings, call_from=self.programe_name)
        if repayment_date is None:
            return

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')
        items = ('早班', '午班', '晚班')
        period, ok = input_dialog.getItem(
            self, '選擇班別', '請選擇還款班別', items, 0, False)
        if not ok or not period:
            return

        row_no = self.ui.tableWidget_self_prescript.currentRow()
        prescript_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['prescript_key']).text()

        rows = self.database.select_record(f'SELECT Debt FROM prescript WHERE PrescriptKey = {prescript_key}')
        if len(rows) <= 0:
            return

        row = rows[0]
        debt = number_utils.get_integer(row['Debt'])

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')
        repayment, ok = input_dialog.getInt(
            self, '輸入還款金額', '請輸入還款金額', debt, 0, 10000000, 100)
        if not ok:
            return

        rows = self.database.select_record(f'SELECT * FROM debt WHERE PrescriptKey = {prescript_key}')
        if len(rows) <= 0:
            self._insert_debt(row_no, prescript_key, debt)

        sql = f'''
            UPDATE debt
            SET
                ReturnDate1 = "{repayment_date}",
                Period1 = "{period}",
                Fee1 = {repayment},
                TotalReturn = {repayment}
            WHERE
                PrescriptKey = {prescript_key}
        '''
        self.database.exec_sql(sql)
        self._refresh_by_prescript(row_no, prescript_key)

    def _get_agent_sql_condition(self):
        # sql_condition = '''
        #     (prescript.MedicineSet >= 2 AND prescript.MedicineSet != 11 AND MedicineName != "民俗調理" AND
        #      (prescript.Price != 0 OR
        #      (prescript.Price = 0 AND MedicineType NOT IN ("單方", "複方", "水藥")))
        #     )
        # '''
        sql_condition = '''
            (prescript.MedicineSet >= 2 AND
             prescript.MedicineSet != 11 AND
             MedicineName != "民俗調理"
             AND MedicineName LIKE "%代收%")
        '''

        if self.dialog.ui.radioButton_date.isChecked():                 # 日期查詢
            sql_condition += f'''
                AND (
                    cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" OR
                    prescript.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" OR
                    (debt.ReturnDate1 BETWEEN "{self.start_date}" AND "{self.end_date}" AND debt.PrescriptKey > 0)
                )
            '''
            if self.period != '全部':
                sql_condition += f' AND cases.Period = "{self.period}"'

            if self.dialog.checkBox_debt.isChecked():
                sql_condition += ' AND cases.TotalFee > ReceiptFee'

            if self.dialog.ui.groupBox_advance.isChecked():
                sql_condition += self._get_advance_sql()
        elif self.dialog.ui.radioButton_invoice_no.isChecked():         # 單據號碼
            invoice_no = self.dialog.ui.lineEdit_invoice_no.text().strip()
            invoice_no_2 = self.dialog.ui.lineEdit_invoice_no_2.text().strip()
            if invoice_no_2 != '':
                sql_condition += f' AND cases.InvoiceNo BETWEEN "{invoice_no}" AND "{invoice_no_2}"'
            else:
                sql_condition += f' AND cases.InvoiceNo = "{invoice_no}"'

        return sql_condition

    def _read_agent_prescript(self, prescript_key=None):
        sql_condition = ''

        if prescript_key is not None:
            sql_condition = f'prescript.PrescriptKey = {prescript_key}'
        else:
            sql_condition = self._get_agent_sql_condition()

        sql = f'''
            SELECT
                prescript.*,
                cases.CaseKey, cases.CaseDate AS SaleDate, cases.Period, cases.PatientKey, cases.Name, cases.InsType,
                cases.Doctor, cases.MassageReferrer, cases.NursingAssistant,
                cases.InvoiceNo, cases.TreatType
            FROM prescript
                LEFT JOIN cases ON prescript.CaseKey = cases.CaseKey
                LEFT JOIN debt ON debt.CaseKey = prescript.CaseKey
            WHERE
                {sql_condition}
            ORDER BY prescript.CaseKey, prescript.PrescriptNo, PrescriptKey
        '''
        # ORDER BY prescript.CaseKey, prescript.TimeStamp

        rows = self.database.select_record(sql)

        return rows

    def _set_agent_prescript_table(self, rows):
        self.ui.tableWidget_self_prescript_agent.setRowCount(0)
        row_no = 0
        for row in rows:
            if not purchase_utils.set_purchase_list_data(
               self.database, self.ui.tableWidget_self_prescript_agent, row, row_no):
                continue

            row_no += 1

        purchase_utils.calculate_purchase_list_total(
            self.ui.tableWidget_self_prescript_agent, self.start_date[:10], self.end_date[:10])

    def _export_agent(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{self.start_date[:10]}至{self.end_date[:10]}代收自費銷售明細.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_self_prescript_agent,
            [purchase_utils.PURCHASE_COL_NO['prescript_key'],
             purchase_utils.PURCHASE_COL_NO['case_key'],
             purchase_utils.PURCHASE_COL_NO['medicine_set'],
             purchase_utils.PURCHASE_COL_NO['medicine_type'],
             purchase_utils.PURCHASE_COL_NO['medicine_key']],
            [
             purchase_utils.PURCHASE_COL_NO['patient_key'],
             purchase_utils.PURCHASE_COL_NO['quantity'],
             purchase_utils.PURCHASE_COL_NO['price'],
             purchase_utils.PURCHASE_COL_NO['pres_days'],
             purchase_utils.PURCHASE_COL_NO['discount'],
             purchase_utils.PURCHASE_COL_NO['total_fee'],
             purchase_utils.PURCHASE_COL_NO['receipt_fee'],
             purchase_utils.PURCHASE_COL_NO['debt'],
             purchase_utils.PURCHASE_COL_NO['repayment'],
             purchase_utils.PURCHASE_COL_NO['return_fee'],
             purchase_utils.PURCHASE_COL_NO['doctor_commission'],
             purchase_utils.PURCHASE_COL_NO['massager_commission'],
             purchase_utils.PURCHASE_COL_NO['cashier_commission']]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>代收自費銷售明細檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _set_discount(self):
        row_no = self.ui.tableWidget_self_prescript.currentRow()
        item = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['total_fee'])
        if item is not None:
            max_discount_fee = number_utils.get_integer(item.text())
        else:
            max_discount_fee = 100000

        print(max_discount_fee)
        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')
        discount_fee, ok = input_dialog.getInt(
            self, '退貨', f'請輸入折扣金額', 0, 0, max_discount_fee, 1)
        if not ok:
            return None

        prescript_key = self.ui.tableWidget_self_prescript.item(
            row_no, purchase_utils.PURCHASE_COL_NO['prescript_key']).text()
        
        fields = ['DiscountFee']
        data = [discount_fee]
        self.database.update_record('prescript', fields, 'PrescriptKey', prescript_key, data)
        self._refresh_by_prescript(row_no, prescript_key)
