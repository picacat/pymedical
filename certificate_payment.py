# -*- coding: UTF-8 -*-

import calendar
import datetime
import os

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from libs import (certificate_utils, charge_utils, class_utils, date_utils,
                  dialog_utils, export_utils, number_utils, personnel_utils,
                  prescript_utils, printer_utils, registration_utils,
                  string_utils, system_utils, ui_utils)


# 醫療費用證明 2018.12.27
class CertificatePayment(QtWidgets.QMainWindow):
    program_name = '醫療費用證明書'

    # 初始化
    def __init__(self, parent=None, *args):
        super(CertificatePayment, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.auto_create_list = args[2]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._read_certificate()

        if self.auto_create_list is not None:
            self._auto_create_certificate_payment()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_CERTIFICATE_PAYMENT, self)
        system_utils.set_css(self, self.system_settings)

        self.table_widget_certificate_list = class_utils.get_table_widget(
            self.ui.tableWidget_certificate_list, self.database)
        self.table_widget_certificate_list.set_column_hidden([0, 1])

        self.table_widget_certificate_items = class_utils.get_table_widget(
            self.ui.tableWidget_certificate_items, self.database)
        self.table_widget_certificate_items.set_column_hidden([0, 1])

        self._set_table_width()
        medicine_fee_field_name = self.system_settings.field('醫療費用證明自費藥費欄位名稱')
        treat_fee_field_name = self.system_settings.field('醫療費用證明自費處置欄位名稱')
        misc_fee_field_name = self.system_settings.field('醫療費用證明其他費用欄位名稱')
        total_fee_field_name = self.system_settings.field('醫療費用證明自費金額欄位名稱')

        if medicine_fee_field_name in ['', None]:
            medicine_fee_field_name = '自費藥費'
        if treat_fee_field_name in ['', None]:
            treat_fee_field_name = '處置費'
        if misc_fee_field_name in ['', None]:
            misc_fee_field_name = '其他費用'
        if total_fee_field_name in ['', None]:
            total_fee_field_name = '自費金額'

        column_header = [
            None, None, '門診日期', '保險', '掛號費', '門診負擔', '藥品負擔', '自付金額', '健保申報',
            medicine_fee_field_name, treat_fee_field_name, misc_fee_field_name, '折扣',
            total_fee_field_name, '自付合計', '診治醫師',
        ]
        self.ui.tableWidget_certificate_items.setHorizontalHeaderLabels(column_header)

        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.action_export_certificate_list_excel.setEnabled(False)
            self.ui.action_export_certificate_list_by_month_to_excel.setEnabled(False)
            self.ui.action_export_certificate_list_by_year_to_excel.setEnabled(False)
            self.ui.toolButton_export_self_pdf.setEnabled(False)
            self.ui.toolButton_export_case_excel.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_certificate_payment)
        self.ui.action_add_certificate.triggered.connect(self._add_certificate)
        self.ui.action_modify_certificate_date.triggered.connect(self._modify_certificate_date)
        self.ui.action_add_certificate_fee.triggered.connect(self._add_certificate_fee)
        self.ui.action_remove_certificate.triggered.connect(self._remove_certificate)
        self.ui.action_query_certificate.triggered.connect(self._query_certificate)
        self.ui.action_export_certificate_list_excel.triggered.connect(self._export_certificate_list_excel)
        self.ui.action_export_certificate_list_by_month_to_excel.triggered.connect(
            lambda: self._export_certificate_list_by_month_to_excel('by_month')
        )
        self.ui.action_export_certificate_list_by_year_to_excel.triggered.connect(
            lambda: self._export_certificate_list_by_month_to_excel(list_type='by_year')
        )

        self.ui.action_print_certificate.triggered.connect(self._print_certificate)
        self.ui.action_print_certificate_2.triggered.connect(self._print_certificate)
        self.ui.action_print_certificate_cash.triggered.connect(self._print_certificate_cash)

        self.ui.action_print_certificate_cash2.triggered.connect(self._print_certificate_cash2)
        self.ui.action_print_certificate_ins_only.triggered.connect(
            lambda: self._print_certificate_cash2(form_type='ins_only'))
        self.ui.action_print_certificate_self_only.triggered.connect(
            lambda: self._print_certificate_cash2(form_type='self_only'))

        self.ui.action_print_certificate_total.triggered.connect(self._print_certificate_total)
        self.ui.action_print_certificate_cash_total.triggered.connect(self._print_certificate_cash_total)
        self.ui.action_print_certificate_receipt.triggered.connect(self._print_certificate_receipt)
        self.ui.action_print_certificate_prescript.triggered.connect(
            lambda: self._print_certificate_prescript(form_type=None))
        self.ui.action_print_certificate_self_medicine.triggered.connect(
            lambda: self._print_certificate_prescript(form_type='self_only'))
        self.ui.action_print_certificate_ins_fee.triggered.connect(self._print_certificate_ins_fee)

        self.ui.action_print_certificate_pdf.triggered.connect(self._print_certificate_pdf)
        self.ui.action_print_certificate_cash_pdf.triggered.connect(self._print_certificate_cash_pdf)
        self.ui.action_print_certificate_total_pdf.triggered.connect(self._print_certificate_total_pdf)
        self.ui.action_print_certificate_prescript_pdf.triggered.connect(self._print_certificate_prescript_pdf)

        self.ui.tableWidget_certificate_list.itemSelectionChanged.connect(self._table_item_changed)
        self.ui.tableWidget_certificate_items.itemChanged.connect(self._cert_item_changed)
        self.ui.tableWidget_certificate_items.doubleClicked.connect(self._open_medical_record)
        self.ui.toolButton_calculate_fees.clicked.connect(self._calculate_fees)
        self.ui.toolButton_remove_item.clicked.connect(self._remove_item)
        self.ui.toolButton_print_self.clicked.connect(self._print_self)
        self.ui.toolButton_export_self_pdf.clicked.connect(self._export_self_pdf)
        self.ui.toolButton_add_medical_record.clicked.connect(self._add_medical_record)
        self.ui.toolButton_export_case_excel.clicked.connect(self._export_case_excel)
        self.ui.toolButton_add_cert_fee.clicked.connect(self._add_cert_fee)
        self.ui.toolButton_change_ins_type.clicked.connect(self._change_ins_type)

    def _open_medical_record(self):
        case_key = self.table_widget_certificate_items.field_value(1)
        if case_key in [None, '']:
            return

        self.parent.open_medical_record(case_key)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_certificate_payment(self):
        self.close_all()
        self.close_tab()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 100, 130, 80, 90, 50, 90, 130, 130, 65, 65]
        self.table_widget_certificate_list.set_table_heading_width(width)

    def _read_certificate(self, sql=None):
        if sql is None:
            start_date = datetime.datetime.now().strftime("%Y-01-01 00:00:00")

            sql = f'''
                SELECT certificate.*, cases.ChargeDone FROM certificate
                    LEFT JOIN cases ON cases.CaseKey = certificate.CaseKey
                WHERE
                    CertificateDate >= "{start_date}" AND
                    CertificateType = "收費證明"
                ORDER BY CertificateKey DESC
            '''

        self.table_widget_certificate_list.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        charge_done = ''
        if string_utils.xstr(row['ChargeDone']) == 'True':
            charge_done = '是'

        certificate_date = string_utils.xstr(row['CertificateDate'])
        start_date = string_utils.xstr(row['StartDate'])
        end_date = string_utils.xstr(row['EndDate'])
        if self.system_settings.field('日期格式') == '民國年':
            certificate_date = date_utils.date_to_zh_tw_date(certificate_date)
            start_date = date_utils.date_to_zh_tw_date(start_date)
            end_date = date_utils.date_to_zh_tw_date(end_date)

        certificate_record = [
            string_utils.xstr(row['CertificateKey']),
            string_utils.xstr(row['CaseKey']),
            certificate_date,
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['InsType']),
            string_utils.xstr(row['Doctor']),
            start_date,
            end_date,
            string_utils.xstr(row['CertificateFee']),
            charge_done,
        ]

        for column in range(len(certificate_record)):
            self.ui.tableWidget_certificate_list.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(certificate_record[column])
            )
            if column in [3, 9]:
                self.ui.tableWidget_certificate_list.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif column in [5, 10]:
                self.ui.tableWidget_certificate_list.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _table_item_changed(self):
        self.ui.tableWidget_certificate_items.setRowCount(0)

        certificate_key = self.table_widget_certificate_list.field_value(0)
        if certificate_key is None:
            self.ui.tableWidget_certificate_items.setRowCount(0)
            return

        sql = f'''
            SELECT certificate_items.*, cases.Doctor FROM certificate_items
                LEFT JOIN cases ON certificate_items.CaseKey = cases.CaseKey
            WHERE
                CertificateKey = {certificate_key}
            ORDER BY CaseDate
        '''
        self.table_widget_certificate_items.set_db_data(sql, self._set_certificate_items_data, set_focus=False)
        self._calculate_items_total()

    def _cert_item_changed(self):
        row_no = self.ui.tableWidget_certificate_items.currentRow()
        if self.ui.tableWidget_certificate_items.item(row_no, 2) is None:
            return

        self.ui.tableWidget_certificate_items.itemChanged.disconnect()
        self._calculate_items_subtotal(row_no)
        self._calculate_items_total()
        self.ui.tableWidget_certificate_items.itemChanged.connect(self._cert_item_changed)

    def _calculate_items_subtotal(self, row_no):
        regist_fee = number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 4).text())
        diag_share_fee = number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 5).text())
        drug_share_fee = number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 6).text())
        cash_fee = regist_fee + diag_share_fee + drug_share_fee

        ins_apply_fee = number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 8).text())
        self_drug_fee = number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 9).text())
        treat_fee = number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 10).text())
        misc_fee = number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 11).text())
        discount_fee = number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 12).text())
        total_fee = self_drug_fee + treat_fee + misc_fee - discount_fee

        cash_total = cash_fee + total_fee

        self.ui.tableWidget_certificate_items.setItem(
            row_no, 7, QtWidgets.QTableWidgetItem(string_utils.xstr(cash_fee))
        )
        self.ui.tableWidget_certificate_items.setItem(
            row_no, 13, QtWidgets.QTableWidgetItem(string_utils.xstr(total_fee))
        )
        self.ui.tableWidget_certificate_items.setItem(
            row_no, 14, QtWidgets.QTableWidgetItem(string_utils.xstr(cash_total))
        )

        self.ui.tableWidget_certificate_items.item(
            row_no, 7).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        self.ui.tableWidget_certificate_items.item(
            row_no, 13).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        self.ui.tableWidget_certificate_items.item(
            row_no, 14).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        item = self.ui.tableWidget_certificate_items.item(row_no, 0)
        if item is None:
            return

        certificate_items_key = item.text()
        if certificate_items_key == '':
            return
        
        sql = f'''
            UPDATE certificate_items
            SET
                RegistFee = {regist_fee},
                SDiagShareFee = {diag_share_fee},
                SDrugShareFee = {drug_share_fee},
                InsApplyFee = {ins_apply_fee},
                SDrugFee = {self_drug_fee},
                SDiagFee = NULL,
                SHerbFee = NULL,
                SExpensiveFee = NULL,
                SAcupunctureFee = {treat_fee},
                SMassageFee = NULL,
                SDislocateFee = NULL,
                SMaterialFee = {misc_fee},
                SExamFee = NULL,
                DiscountFee = {discount_fee},
                TotalFee = {total_fee}
            WHERE
                CertificateItemsKey = {certificate_items_key}
        '''
        self.database.exec_sql(sql)

    def _set_certificate_items_data(self, row_no, row):
        treat_fee = (
            number_utils.get_integer(row['SDiagFee']) +
            number_utils.get_integer(row['SAcupunctureFee']) +
            number_utils.get_integer(row['SMassageFee']) +
            number_utils.get_integer(row['SDislocateFee'])
        )

        misc_fee = (
            number_utils.get_integer(row['SMaterialFee']) +
            number_utils.get_integer(row['SExamFee'])
        )
        discount_fee = number_utils.get_integer(row['DiscountFee'])
        total_fee = number_utils.get_integer(row['TotalFee'])
        self_drug_fee = (
                number_utils.get_integer(row['SDrugFee']) +
                number_utils.get_integer(row['SHerbFee']) +
                number_utils.get_integer(row['SExpensiveFee'])
        )
        cash_total = (
                number_utils.get_integer(row['RegistFee']) +
                number_utils.get_integer(row['SDiagShareFee']) +
                number_utils.get_integer(row['SDrugShareFee'])
        )
        payment = cash_total + total_fee

        case_date = string_utils.xstr(row['CaseDate'].date())
        if self.system_settings.field('日期格式') == '民國年':
            case_date = date_utils.date_to_zh_tw_date(case_date)

        certificate_items_record = [
            string_utils.xstr(row['CertificateItemsKey']),
            string_utils.xstr(row['CaseKey']),
            case_date,
            string_utils.xstr(row['InsType']),
            string_utils.xstr(number_utils.get_integer(row['RegistFee'])),
            string_utils.xstr(number_utils.get_integer(row['SDiagShareFee'])),
            string_utils.xstr(number_utils.get_integer(row['SDrugShareFee'])),
            string_utils.xstr(cash_total),
            string_utils.xstr(number_utils.get_integer(row['InsApplyFee'])),
            string_utils.xstr(self_drug_fee),
            string_utils.xstr(treat_fee),
            string_utils.xstr(misc_fee),
            string_utils.xstr(discount_fee),
            string_utils.xstr(total_fee),
            string_utils.xstr(payment),
            string_utils.xstr(row['Doctor']),
        ]

        for col_no in range(len(certificate_items_record)):
            self.ui.tableWidget_certificate_items.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(certificate_items_record[col_no])
            )
            if col_no in range(4, 15):
                self.ui.tableWidget_certificate_items.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _calculate_items_total(self):
        row_count = self.ui.tableWidget_certificate_items.rowCount()

        for row_no in range(row_count):
            item = self.ui.tableWidget_certificate_items.item(row_no, 2)
            if item is None:
                continue

            if item.text() == '合計':
                self.ui.tableWidget_certificate_items.removeRow(row_no)
                row_count = self.ui.tableWidget_certificate_items.rowCount()
                break

        regist_fee = 0
        diag_share_fee = 0
        drug_share_fee = 0
        cash_fee = 0
        ins_apply_fee = 0
        self_drug_fee = 0
        treat_fee = 0
        misc_fee = 0
        discount_fee = 0
        total_fee = 0
        cash_total = 0
        for row_no in range(row_count):
            item = self.ui.tableWidget_certificate_items.item(row_no, 2)
            if item is None:
                continue

            regist_fee += number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 4).text())
            diag_share_fee += number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 5).text())
            drug_share_fee += number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 6).text())
            cash_fee += number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 7).text())
            ins_apply_fee += number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 8).text())
            self_drug_fee += number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 9).text())
            treat_fee += number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 10).text())
            misc_fee += number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 11).text())
            discount_fee += number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 12).text())
            total_fee += number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 13).text())
            cash_total += number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 14).text())

        total_fee_row = [
            None,
            None,
            '合計',
            None,
            string_utils.xstr(regist_fee),
            string_utils.xstr(diag_share_fee),
            string_utils.xstr(drug_share_fee),
            string_utils.xstr(cash_fee),
            string_utils.xstr(ins_apply_fee),
            string_utils.xstr(self_drug_fee),
            string_utils.xstr(treat_fee),
            string_utils.xstr(misc_fee),
            string_utils.xstr(discount_fee),
            string_utils.xstr(total_fee),
            string_utils.xstr(cash_total),
        ]

        self.ui.tableWidget_certificate_items.setRowCount(row_count + 1)
        for col_no in range(len(total_fee_row)):
            self.ui.tableWidget_certificate_items.setItem(
                row_count, col_no,
                QtWidgets.QTableWidgetItem(total_fee_row[col_no])
            )
            if col_no >= 4:
                self.ui.tableWidget_certificate_items.item(
                    row_count, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    # 開立證明
    def _add_certificate(self):
        dialog = dialog_utils.get_dialog_certificate_payment(
            self, self.database, self.system_settings, None
        )

        if dialog.exec_():
            self._read_certificate()
            self._table_item_changed()

        dialog.close_all()
        dialog.deleteLater()

    def _remove_certificate(self):
        name = self.table_widget_certificate_list.field_value(4)
        msg_box = dialog_utils.get_message_box(
            '刪除醫療費用證明', QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定刪除 {name} 的費用證明書?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        certificate_key = self.table_widget_certificate_list.field_value(0)
        certificate_date = self.table_widget_certificate_list.field_value(2)
        patient_key = self.table_widget_certificate_list.field_value(3)

        self.database.exec_sql(f'DELETE FROM certificate WHERE CertificateKey = {certificate_key}')
        self.database.exec_sql(f'DELETE FROM certificate_items WHERE CertificateKey = {certificate_key}')

        sql = f'''
            SELECT cases.CaseKey FROM cases
                LEFT JOIN prescript ON prescript.CaseKey = prescript.CaseKey
            WHERE
                DATE(cases.CaseDate) = "{certificate_date}" AND
                PatientKey = {patient_key} AND
                InsType = "自費" AND
                TreatType = "開立證明" AND
                prescript.MedicineName = "醫療費用證明書"
            GROUP BY cases.CaseKey
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            case_key = rows[0]['CaseKey']
            self.database.exec_sql(f'DELETE FROM cases WHERE CaseKey = {case_key}')
            self.database.exec_sql(f'DELETE FROM wait WHERE CaseKey = {case_key}')

        current_row = self.ui.tableWidget_certificate_list.currentRow()
        self.ui.tableWidget_certificate_list.removeRow(current_row)
        self._table_item_changed()

    # 產生開立證明費
    def _add_certificate_fee(self):
        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')
        certificate_fee, ok = input_dialog.getInt(
            self, '開立證明費', '請輸入開立證明書費用', 100, 0, 1000, 50)
        if not ok:
            return

        certificate_key = self.table_widget_certificate_list.field_value(0)
        current_row = self.ui.tableWidget_certificate_list.currentRow()
        self.database.exec_sql(f'''
            UPDATE certificate SET
                CertificateFee = {certificate_fee}
            WHERE
                CertificateKey = {certificate_key}
        ''')
        # self._set_medical_record_certificate_fee(certificate_fee)
        # self._set_certificate_items_fee(certificate_fee)
        self.refresh_certificate(certificate_key, current_row)
        self._table_item_changed()

    def _set_medical_record_certificate_fee(self, certificate_fee):
        case_key = self.ui.tableWidget_certificate_items.item(0, 1)  # 抓第一筆來開立
        if case_key is None:
            return

        case_key = number_utils.get_integer(case_key.text())
        if case_key <= 0:
            return

        sql = f'''
            SELECT * FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2 AND
                (MedicineName LIKE "%診斷證明書%" OR
                 MedicineName LIKE "%診斷書%")
        '''
        rows = self.database.select_record(sql)

        if len(rows) > 0:  # 已經開立過證明書
            return

        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]

        material_fee = number_utils.get_integer(row['SMaterialFee'])
        discount_fee = number_utils.get_integer(row['DiscountFee'])
        self_total_fee = number_utils.get_integer(row['SelfTotalFee'])
        receipt_fee = number_utils.get_integer(row['ReceiptFee'])
        total_fee = number_utils.get_integer(row['TotalFee'])

        material_fee += certificate_fee
        discount_fee += certificate_fee
        self_total_fee += certificate_fee
        receipt_fee += certificate_fee
        total_fee += certificate_fee

        fields = ['SMaterialFee', 'SelfTotalFee', 'DiscountFee', 'ReceiptFee', 'TotalFee']
        data = [material_fee, self_total_fee, discount_fee, receipt_fee, total_fee]
        self.database.update_record('cases', fields, 'CaseKey', case_key, data)

        max_medicine_set = prescript_utils.get_max_medicine_set(self.database, case_key)
        self._insert_prescript(case_key, row['CaseDate'], max_medicine_set+1, certificate_fee)

    def _set_certificate_items_fee(self, certificate_fee):
        certificate_items_key = self.ui.tableWidget_certificate_items.item(0, 0)  # 抓第一筆來開立
        if certificate_items_key is None:
            return

        certificate_items_key = number_utils.get_integer(certificate_items_key.text())
        if certificate_items_key <= 0:
            return

        sql = f'''
            SELECT * FROM certificate_items
            WHERE
                CertificateItemsKey = {certificate_items_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]

        material_fee = number_utils.get_integer(row['SMaterialFee'])
        self_total_fee = number_utils.get_integer(row['SelfTotalFee'])
        discount_fee = number_utils.get_integer(row['DiscountFee'])
        receipt_fee = number_utils.get_integer(row['ReceiptFee'])
        total_fee = number_utils.get_integer(row['TotalFee'])

        material_fee += certificate_fee
        self_total_fee += certificate_fee
        discount_fee += certificate_fee
        receipt_fee += certificate_fee
        total_fee += certificate_fee

        fields = ['SMaterialFee', 'SelfTotalFee', 'DiscountFee', 'ReceiptFee', 'TotalFee']
        data = [material_fee, self_total_fee, discount_fee, receipt_fee, total_fee]
        self.database.update_record(
            'certificate_items', fields, 'CertificateItemsKey', certificate_items_key, data
        )

    def refresh_certificate(self, certificate_key, current_row):
        sql = f'''
            SELECT certificate.*, cases.ChargeDone
            FROM certificate
                LEFT JOIN cases ON cases.CaseKey = certificate.CaseKey
            WHERE
                CertificateKey = {certificate_key}
        '''
        row = self.database.select_record(sql)[0]
        self._set_table_data(current_row, row)

    def _print_certificate(self):
        show_tax_declare = False

        if self.sender().objectName() == 'action_print_certificate':
            show_tax_declare = True

        printer_utils.print_form_certificate_payment(
            self, self.database, self.system_settings,
            self.table_widget_certificate_list.field_value(0), show_tax_declare,
        )

    def _print_certificate_cash(self):
        printer_utils.print_form_certificate_cash_payment(
            self, self.database, self.system_settings,
            self.table_widget_certificate_list.field_value(0),
        )

    def _print_certificate_cash2(self, form_type=None):
        printer_utils.print_form_certificate_cash_payment2(
            self, self.database, self.system_settings,
            self.table_widget_certificate_list.field_value(0),
            form_type=form_type,
        )

    def _print_certificate_total(self):
        printer_utils.print_form_certificate_total(
            self, self.database, self.system_settings,
            self.table_widget_certificate_list.field_value(0),
            print_ins_fee=True
        )

    def _print_certificate_cash_total(self):
        printer_utils.print_form_certificate_total(
            self, self.database, self.system_settings,
            self.table_widget_certificate_list.field_value(0),
            print_ins_fee=False
        )

    def _print_certificate_receipt(self):
        printer_utils.print_form_certificate_receipt(
            self, self.database, self.system_settings,
            self.table_widget_certificate_list.field_value(0),
        )

    def _print_certificate_prescript(self, form_type=None):
        printer_utils.print_form_certificate_prescript(
            self, self.database, self.system_settings,
            self.table_widget_certificate_list.field_value(0),
            form_type=form_type,
        )

    def _print_certificate_pdf(self):
        printer_utils.print_form_certificate_payment(
            self, self.database, self.system_settings,
            self.table_widget_certificate_list.field_value(0), 'pdf_by_dialog',
        )

    def _print_certificate_cash_pdf(self):
        printer_utils.print_form_certificate_cash_payment(
            self, self.database, self.system_settings,
            self.table_widget_certificate_list.field_value(0), 'pdf_by_dialog',
        )

    def _print_certificate_total_pdf(self):
        printer_utils.print_form_certificate_total(
            self, self.database, self.system_settings,
            self.table_widget_certificate_list.field_value(0), 'pdf_by_dialog',
        )

    def _print_certificate_prescript_pdf(self):
        printer_utils.print_form_certificate_prescript(
            self, self.database, self.system_settings,
            self.table_widget_certificate_list.field_value(0), 'pdf_by_dialog',
        )

    def _query_certificate(self):
        dialog = dialog_utils.get_dialog_certificate_query(
            self, self.database, self.system_settings,
            '收費證明',
        )

        if dialog.exec_():
            sql = dialog.sql
            self._read_certificate(sql)
            self._table_item_changed()

        dialog.close_all()
        dialog.deleteLater()

    def _auto_create_certificate_payment(self):
        dialog = dialog_utils.get_dialog_certificate_payment(
            self, self.database, self.system_settings, self.auto_create_list,
        )

        if dialog.exec_():
            self._read_certificate()
            self._table_item_changed()

        dialog.close_all()
        dialog.deleteLater()

    def _remove_item(self):
        msg_box = dialog_utils.get_message_box(
            '刪除醫療費用項目', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除此筆明細單項?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        certificate_item_key = self.table_widget_certificate_items.field_value(0)
        if certificate_item_key is None:
            return

        self.database.delete_record('certificate_items', 'CertificateItemsKey', certificate_item_key)
        self._table_item_changed()

    def _calculate_fees(self):
        correct_list = []
        for row_no in range(self.ui.tableWidget_certificate_items.rowCount()):
            case_key = self.ui.tableWidget_certificate_items.item(row_no, 1)
            if case_key is None:
                continue

            case_key = case_key.text()
            if case_key == '':
                continue

            sql = f'''
                SELECT * FROM cases
                WHERE
                    CaseKey = {case_key}
            '''
            rows = self.database.select_record(sql)

            if len(rows) <= 0:
                continue

            row = rows[0]

            if self.system_settings.field('手動批價') == 'Y':
                self_total_fee = number_utils.get_integer(row['SelfTotalFee'])
            else:
                self_total_fee = charge_utils.get_self_total_fee(self.database, case_key)

            discount_fee = number_utils.get_integer(row['DiscountFee'])
            total_fee = self_total_fee - discount_fee
            item_total_fee = self.ui.tableWidget_certificate_items.item(row_no, 9)

            if item_total_fee is None:
                item_total_fee = 0
            else:
                item_total_fee = number_utils.get_integer(item_total_fee.text())

            if item_total_fee != total_fee:
                certificate_items_key = self.ui.tableWidget_certificate_items.item(row_no, 0).text()
                correct_list.append([certificate_items_key, case_key, total_fee])

        if len(correct_list) <= 0:
            system_utils.show_message_box(
                QMessageBox.Information,
                '批價檢查',
                '<font size="5" color="blue"><b>所有批價資料均為正確, 重新批價結果與原始資料相同.</b></font>',
                '批價資料正確, 不需更新.'
            )
            return

        dialog = dialog_utils.get_dialog_certificate_items(
            self, self.database, self.system_settings, self.ui.tableWidget_certificate_items, correct_list,
        )
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

        self._table_item_changed()

    def _print_self(self):
        printer_utils.print_form_certificate_self_prescript(
            self, self.database, self.system_settings,
            self.table_widget_certificate_list.field_value(0), 'preview',
        )

    def _export_self_pdf(self):
        printer_utils.print_form_certificate_self_prescript(
            self, self.database, self.system_settings,
            self.table_widget_certificate_list.field_value(0), 'pdf_by_dialog',
        )

    def _export_certificate_list_excel(self):
        options = QFileDialog.Options()
        last_dir = system_utils.get_last_directory('醫療費用證明書')

        excel_filename = os.path.join(last_dir, '開立收費證明明細.xlsx')
        excel_filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出開立收費證明明細",
            excel_filename,
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_filename:
            return

        system_utils.set_last_directory('醫療費用證明書', excel_filename)
        medical_record_rows = self._get_medical_record_rows()

        export_utils.export_daily_medical_records_to_excel(
            self.database, self.system_settings, excel_filename,
            medical_record_rows, show_summary=False,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>{excel_filename}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _export_case_excel(self):
        name = self.ui.tableWidget_certificate_list.item(
            self.ui.tableWidget_certificate_list.currentRow(), 4).text()
        start_date = self.ui.tableWidget_certificate_list.item(
            self.ui.tableWidget_certificate_list.currentRow(), 7).text()
        end_date = self.ui.tableWidget_certificate_list.item(
            self.ui.tableWidget_certificate_list.currentRow(), 8).text()

        last_dir = system_utils.get_last_directory('醫療費用證明書')
        excel_filename = os.path.join(last_dir, f'{name}_{start_date}至{end_date}醫療費用明細.xlsx')

        options = QFileDialog.Options()
        excel_filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出開立收費證明明細",
            excel_filename,
            "excel檔案 (*.xlsx);Text Files (*.txt)", options=options
        )
        if not excel_filename:
            return

        system_utils.set_last_directory('醫療費用證明書', excel_filename)

        patient_key = self.ui.tableWidget_certificate_list.item(
            self.ui.tableWidget_certificate_list.currentRow(), 3).text()
        sql = f'SELECT * FROM patient WHERE PatientKey = {patient_key}'
        rows = self.database.select_record(sql)
        patient_id = string_utils.xstr(rows[0]['ID'])
        birthday = string_utils.xstr(rows[0]['Birthday'])
        telephone = string_utils.xstr(rows[0]['Telephone'])
        if telephone in ['', None]:
            telephone = string_utils.xstr(rows[0]['Cellphone'])

        address = string_utils.xstr(rows[0]['Address'])

        export_utils.export_certificate_payment_to_excel(
            excel_file_name=excel_filename,
            clinic_name=self.system_settings.field('院所名稱'),
            clinic_telephone=self.system_settings.field('院所電話'),
            clinic_address=self.system_settings.field('院所地址'),
            start_date=start_date,
            end_date=end_date,
            patient_key=patient_key,
            name=name,
            patient_id=patient_id,
            birthday=birthday,
            telephone=telephone,
            address=address,
            table_widget_certificate_items=self.ui.tableWidget_certificate_items,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>{excel_filename}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _get_current_year(self):
        current_year = datetime.datetime.now().year

        case_date_item = self.ui.tableWidget_certificate_list.item(0, 2)
        if case_date_item is not None:
            case_date = case_date_item.text()
            current_year = int(case_date.split('-')[0])

        return current_year

    def _export_certificate_list_by_month_to_excel(self, list_type='by_month'):
        current_year = self._get_current_year()
        month = None

        if list_type == 'by_month':
            items = [str(i) for i in range(1, 13)]
            month, ok = QInputDialog.getItem(
                self, "選擇月份", "請選擇要匯出的月份", items, 0, False
            )

            if not ok:
                return

            month = int(month)
            filename = f'{current_year}年{month:0>2}月開立收費證明明細.xlsx'
        else:
            filename = f'{current_year}年度開立收費證明明細.xlsx'

        options = QFileDialog.Options()
        excel_filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出開立收費證明明細",
            filename,
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_filename:
            return

        self._export_to_excel(excel_filename, current_year, month, list_type)

    def _export_to_excel(self, excel_filename, year=None, month=None,  list_type='by_month'):
        start_date, end_date = None, None

        if year is not None and month is not None:
            last_day = calendar.monthrange(year, month)[1]
            start_date = f'{year}-{month:0>2}-01'
            end_date = f'{year}-{month:0>2}-{last_day:0>2}'

        selected_rows = []
        for row_no in range(self.ui.tableWidget_certificate_list.rowCount()):
            case_date = self.ui.tableWidget_certificate_list.item(row_no, 2).text()
            if list_type == 'by_month':
                if start_date <= case_date <= end_date:
                    pass
                else:
                    continue

            self.ui.tableWidget_certificate_list.setCurrentCell(row_no, 0)
            last_item_row_no = self.ui.tableWidget_certificate_items.rowCount() - 1
            selected_rows.append(
                [
                    self.ui.tableWidget_certificate_list.item(row_no, 2).text(),
                    self.ui.tableWidget_certificate_list.item(row_no, 3).text(),
                    self.ui.tableWidget_certificate_list.item(row_no, 4).text(),
                    self.ui.tableWidget_certificate_list.item(row_no, 5).text(),
                    self.ui.tableWidget_certificate_list.item(row_no, 6).text(),
                    self.ui.tableWidget_certificate_list.item(row_no, 7).text(),
                    self.ui.tableWidget_certificate_list.item(row_no, 8).text(),
                    self.ui.tableWidget_certificate_list.item(row_no, 9).text(),


                    self.ui.tableWidget_certificate_items.item(last_item_row_no, 4).text(),
                    self.ui.tableWidget_certificate_items.item(last_item_row_no, 5).text(),
                    self.ui.tableWidget_certificate_items.item(last_item_row_no, 6).text(),
                    self.ui.tableWidget_certificate_items.item(last_item_row_no, 7).text(),
                    self.ui.tableWidget_certificate_items.item(last_item_row_no, 8).text(),
                    self.ui.tableWidget_certificate_items.item(last_item_row_no, 9).text(),
                    self.ui.tableWidget_certificate_items.item(last_item_row_no, 10).text(),
                    self.ui.tableWidget_certificate_items.item(last_item_row_no, 11).text(),
                    self.ui.tableWidget_certificate_items.item(last_item_row_no, 12).text(),
                    self.ui.tableWidget_certificate_items.item(last_item_row_no, 13).text(),
                    self.ui.tableWidget_certificate_items.item(last_item_row_no, 14).text(),
                ]
            )

        self.ui.tableWidget_certificate_list.setCurrentCell(0, 0)
        if len(selected_rows) <= 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                '查無資料',
                '<font color="red"><h3>這段期間查無開立費用證明資料, 請重新查詢!</h3></font>',
                '請確認日期是否輸入正確.'
            )
            return

        if month is None:
            title = f'{self.system_settings.field("院所名稱")}{year}年度'
        else:
            title = f'{self.system_settings.field("院所名稱")}{year}年{month}月份'

        title += ' 開立證明一覽表'

        header_list = [
            '開立日期', '病歷號碼', '姓名', '保險', '主治醫師', '診療日期', '結束日期', '開立證明費',
            '掛號費', '門診負擔', '藥品負擔', '自付金額', '健保申報', '自費藥費', '自費處置',
            '其他費用', '折扣', '自費金額', '自付合計',
        ]

        export_utils.export_list_to_excel(
            excel_filename, header_list, selected_rows,
            [1, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18], title,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>{excel_filename}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _get_medical_record_rows(self):
        medical_record_rows = []

        row_count = self.ui.tableWidget_certificate_list.rowCount()
        progress_dialog = QtWidgets.QProgressDialog(
            '正在產生excel檔中, 請稍後...', '取消', 0, row_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no in range(row_count):
            self.ui.tableWidget_certificate_list.setCurrentCell(row_no, 2)
            self._export_certificate_detail(medical_record_rows)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()

        return medical_record_rows

    def _export_certificate_detail(self, medical_record_rows):
        for row_no in range(self.ui.tableWidget_certificate_items.rowCount()):
            case_key = self.ui.tableWidget_certificate_items.item(row_no, 1)
            if case_key is None or case_key.text() == '':
                continue

            case_key = case_key.text()
            case_row = self._get_medical_record_row(case_key)
            if case_row is not None:
                medical_record_rows.append(case_row)

    def _get_medical_record_row(self, case_key):
        sql = f'''
            SELECT
                cases.*, patient.DiscountType
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) > 0:
            row = rows[0]
        else:
            return None

        total_fee = number_utils.get_integer(row['TotalFee'])
        if total_fee <= 0:
            return None

        massager = string_utils.xstr(row['Massager'])
        discount_type = string_utils.xstr(row['DiscountType'])
        discount_fee = number_utils.get_integer(row['DiscountFee'])

        case_date = string_utils.xstr(row['CaseDate'].date())[:10]
        period = string_utils.xstr(row['Period'])[:1]
        next_case_date = None
        next_period = None

        ins_type = string_utils.xstr(row['InsType'])
        treat_type = string_utils.xstr(row['TreatType'])
        card = string_utils.xstr(row['Card'])
        if card in ['免卡', None]:
            card = ''

        regist_fee = 0
        diag_share_fee = 0
        drug_share_fee = 0
        deposit_fee = 0

        doctor = string_utils.xstr(row['Doctor'])
        patient_key = string_utils.xstr(row['PatientKey'])
        name = string_utils.xstr(row['Name'])
        regist_no = string_utils.xstr(row['RegistNo'])
        course = string_utils.xstr(row['Continuance'])

        case_row = {
            'CaseKey': case_key,
            'CaseDate': case_date,
            'Period': period,
            'NextCaseDate': next_case_date,
            'NextPeriod': next_period,
            'InsType': ins_type,
            'TreatType': treat_type,
            'Card': card,
            'RegistFee': regist_fee,
            'DiagShareFee': diag_share_fee,
            'DrugShareFee': drug_share_fee,
            'DepositFee': deposit_fee,
            'Massager': massager,
            'DiscountType': discount_type,
            'Doctor': doctor,
            'PatientKey': patient_key,
            'Name': name,
            'RegistNo': regist_no,
            'Course': course,
            'TotalFee': total_fee,
            'DiscountFee': discount_fee,
        }

        return case_row

    # 新增病歷資料
    def _add_medical_record(self):
        case_date = date_utils.get_dialog_date(self, self.database, self.system_settings, call_from=self.program_name)
        if case_date is None:
            return

        certificate_key = self.table_widget_certificate_list.field_value(0)
        patient_key = self.table_widget_certificate_list.field_value(3)
        dialog_case_key = dialog_utils.get_dialog_medical_record_picker(
            self, self.database, self.system_settings, case_date, patient_key,
        )
        result = dialog_case_key.exec_()
        if not result:
            dialog_case_key.deleteLater()
            return

        case_key = dialog_case_key.get_case_key()
        certificate_utils.insert_certificate_items(self.database, certificate_key, case_key)
        self._table_item_changed()

        dialog_case_key.deleteLater()

    # 新增開立證明費病歷資料
    def _add_cert_fee(self):
        case_date = date_utils.get_dialog_date(self, self.database, self.system_settings, call_from=self.program_name)
        if case_date is None:
            return

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')
        cert_fee, ok = input_dialog.getInt(
            self, '開立證明費', '請輸入開立證明書費用', 100, 0, 1000, 50)
        if not ok:
            return

        certificate_key = self.table_widget_certificate_list.field_value(0)
        patient_key = self.table_widget_certificate_list.field_value(3)
        name = self.table_widget_certificate_list.field_value(4)

        case_key = self._insert_medical_record(patient_key, name, case_date, cert_fee)
        self._insert_prescript(case_key, case_date, 2, cert_fee)
        certificate_utils.insert_certificate_items(self.database, certificate_key, case_key)

        self._table_item_changed()

    def _insert_medical_record(self, patient_key, name, case_date, cert_fee):
        user = self.system_settings.field('使用者')
        period = registration_utils.get_current_period(self.system_settings)

        fields = [
            'PatientKey', 'Name', 'CaseDate',
            'Period', 'InsType',
            'TreatType', 'Register', 'Cashier',
            'SMaterialFee', 'SelfTotalFee', 'TotalFee', 'ReceiptFee',
            'DoctorDate', 'DoctorDone', 'ChargeDate', 'ChargePeriod', 'ChargeDone',
        ]

        data = [
            patient_key,
            name,
            case_date,
            period,
            '自費',
            '開立證明',
            user, user,
            cert_fee,
            cert_fee,
            cert_fee,
            cert_fee,
            case_date, 'True',
            case_date, period, 'True',
        ]

        case_key = self.database.insert_record('cases', fields, data)

        return case_key

    def _insert_prescript(self, case_key, case_date, medicine_set, certificate_fee):
        fields = [
            'PrescriptNo', 'CaseKey', 'CaseDate', 'MedicineSet',
            'MedicineType', 'MedicineName', 'DosageMode', 'Dosage',
            'Unit', 'Price', 'Amount'
        ]
        data = [
            1, case_key, case_date, medicine_set,
            '器材', '診斷證明書', '日劑量', 1,
            '份', certificate_fee, certificate_fee
        ]
        self.database.insert_record('prescript', fields, data)

    def _change_ins_type(self):
        certificate_item_key = self.table_widget_certificate_items.field_value(0)
        if certificate_item_key is None:
            return

        ins_type = self.table_widget_certificate_items.field_value(3)
        if ins_type == '健保':
            ins_type = '自費'
        else:
            ins_type = '健保'

        self.database.exec_sql(f'''
            UPDATE certificate_items
            SET
                InsType = "{ins_type}"
            WHERE
                CertificateItemsKey = {certificate_item_key}
        ''')
        self._table_item_changed()

    # 修改開立日期
    def _modify_certificate_date(self):
        certificate_key = self.table_widget_certificate_list.field_value(0)
        certificate_date = date_utils.str_to_date(self.table_widget_certificate_list.field_value(2))

        dialog = dialog_utils.get_dialog_calendar(
            self, self.database, self.system_settings, '開立費用證明')

        dialog.ui.calendarWidget.setSelectedDate(certificate_date)

        if not dialog.exec_():
            dialog.deleteLater()
            return

        current_date = dialog.ui.calendarWidget.selectedDate()
        year = current_date.year()
        month = current_date.month()
        day = current_date.day()
        cert_date = f'{year}-{month:0>2}-{day:0>2}'
        sql =  f'''
            UPDATE certificate
            SET
                CertificateDate = "{cert_date}"
            WHERE
                CertificateKey = {certificate_key}
        '''
        self.database.exec_sql(sql)
        self._read_certificate()

        dialog.deleteLater()

    def _print_certificate_ins_fee(self):
        printer_utils.print_form_certificate_ins_fee(
            self, self.database, self.system_settings,
            self.table_widget_certificate_list.field_value(0),
        )
