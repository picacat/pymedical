
# -*- coding: utf-8 -*-

import string
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (case_utils, charge_utils, class_utils, nhi_utils,
                  number_utils, patient_utils, personnel_utils,
                  prescript_utils, string_utils, system_utils, ui_utils)


class MedicalRecordFees(QtWidgets.QMainWindow):
    """病歷資料批價頁面2018.01.31."""

    INS_COLUMN = {
        'DiagFee': 0,
        'InterDrugFee': 1,
        'PharmacyFee': 2,
        'AcupunctureFee': 3,
        'MassageFee': 4,
        'DislocateFee': 5,
        'ExamFee': 6,
        'InsTotalFee': 7,
        'DiagShareFee': 8,
        'DrugShareFee': 9,
        'InsApplyFee': 10,
        'AgentFee': 11,
    }
    SELF_COLUMN = {
        'RegistFee': 0,
        'ReceiptDiagShare': 1,
        'ReceiptDrugShare': 2,
        'DepositFee': 3,
        'RefundFee': 4,
        'SDiagFee': 5,
        'SDrugFee': 6,
        'SHerbFee': 7,
        'SExpensiveFee': 8,
        'SAcupunctureFee': 9,
        'SMassageFee': 10,
        'SMaterialFee': 11,
        'SExamFee': 12,
        'SelfTotalFee': 13,
        'DiscountFee': 14,
        'TotalFee': 15,
        'ReceiptFee': 16,
    }

    # 初始化
    def __init__(self, parent=None, *args):
        super(MedicalRecordFees, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.medical_record = args[2]
        self.case_key = args[3]
        self.patient_key = args[4]
        self.call_from = args[5]
        self.ui = None

        self._set_ui()
        self._set_signal()

        if self.case_key is None:
            self._set_new_self_medical_fees()
        else:
            self._read_fees()

        self.user_name = system_utils.get_user_name(self.system_settings)
        self._set_permission()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_MEDICAL_RECORD_FEES, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_ins_fees = class_utils.get_table_widget(self.ui.tableWidget_ins_fees, self.database)
        self.table_widget_cash_fees = class_utils.get_table_widget(self.ui.tableWidget_cash_fees, self.database)
        self.ui.tableWidget_ins_fees.resizeRowsToContents()
        self.ui.tableWidget_cash_fees.resizeRowsToContents()
        # self._set_table_width()
        self.ins_table_headers = [
            '診察費', '藥費', '調劑費', '針灸費', '傷科費', '脫臼費', '加計費',
            '健保合計', '門診負擔', '藥品負擔', '健保申請', '代辦費',
        ]
        self.ui.tableWidget_ins_fees.setVerticalHeaderLabels(self.ins_table_headers)

        self.self_table_headers = [
            '掛號費', '實收診負', '實收藥負', '欠卡費', '還卡費',
            '診察費', '一般藥費', '水藥費', '高貴藥費', '針灸費', '民俗調理', '材料費', '檢驗費', '自費合計',
            '折扣金額', '自費應收', '自費實收',
        ]
        self.ui.tableWidget_cash_fees.setVerticalHeaderLabels(self.self_table_headers)

        self._set_discount_visible()
        self._set_payment_type()
        tc_massage_field_name = self.system_settings.field('民俗調理欄位名稱')
        if tc_massage_field_name not in ['', None]:
            self.ui.tableWidget_cash_fees.setVerticalHeaderItem(
                10, QtWidgets.QTableWidgetItem(tc_massage_field_name)
            )

    def _set_payment_type(self):
        ui_utils.set_combo_box(self.ui.comboBox_regist_payment_type, nhi_utils.PAYMENT_TYPE)
        ui_utils.set_combo_box(self.ui.comboBox_charge_payment_type, nhi_utils.PAYMENT_TYPE)

    def _set_discount_visible(self):
        if self.system_settings.field('自費折扣方式') == '個別折扣':
            enabled = False
            self.ui.label_discount.setVisible(enabled)
            self.ui.spinBox_discount.setVisible(enabled)
            self.ui.label_percent.setVisible(enabled)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_calculate_fees.clicked.connect(lambda: self.calculate_fees(auto_calculate_fees=True))
        self.ui.tableWidget_cash_fees.keyPressEvent = self._table_widget_cash_fees_key_press
        self.ui.spinBox_discount.valueChanged.connect(self._calculate_discount)
        self.ui.tableWidget_cash_fees.cellClicked.connect(self._cell_clicked)
        self.ui.tableWidget_ins_fees.cellClicked.connect(self._cell_clicked)

    def _cell_clicked(self):
        system_utils.set_keyboard_layout('英文')

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return
        
        if personnel_utils.get_permission(self.database, '醫師看診作業', '病歷登錄', self.user_name) == 'Y':
            return

        if personnel_utils.get_permission(self.database, '病歷資料', '病歷修正', self.user_name) == 'Y':
            return

        self.ui.toolButton_calculate_fees.setEnabled(False)
        self.ui.tableWidget_ins_fees.setEnabled(False)
        self.ui.tableWidget_cash_fees.setEnabled(False)

        for row_no in range(self.ui.tableWidget_ins_fees.rowCount()):
            for col_no in range(self.ui.tableWidget_ins_fees.columnCount()):
                item = self.ui.tableWidget_ins_fees.item(row_no, col_no)
                if item is None:
                    continue

                item.setForeground(QtGui.QColor('black'))

        for row_no in range(self.ui.tableWidget_cash_fees.rowCount()):
            for col_no in range(self.ui.tableWidget_cash_fees.columnCount()):
                item = self.ui.tableWidget_cash_fees.item(row_no, col_no)
                if item is None:
                    continue

                item.setForeground(QtGui.QColor('black'))

    def _table_widget_cash_fees_key_press(self, event):
        system_utils.set_keyboard_layout('英文')
        key = event.key()
        current_row = self.ui.tableWidget_cash_fees.currentRow()

        if key in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Down, QtCore.Qt.Key_Up]:
            if current_row not in [self.SELF_COLUMN['ReceiptFee']]:
                self._calculate_own_expense_total()
                self._reset_discount_fee()
                self._calculate_own_expense_total()  # 再重算一次
                self._set_cash_fee_editable()

        if key in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
            self.ui.tableWidget_cash_fees.setCurrentCell(current_row+1, 0)

        return QtWidgets.QTableWidget.keyPressEvent(self.ui.tableWidget_cash_fees, event)

    def _reset_discount_fee(self):
        discount_fee = charge_utils.get_table_widget_item_fee(
            self.ui.tableWidget_cash_fees, self.SELF_COLUMN['DiscountFee'], 0
        )
        self_total_fee = charge_utils.get_table_widget_item_fee(
            self.ui.tableWidget_cash_fees, self.SELF_COLUMN['SelfTotalFee'], 0
        )

        if self.system_settings.field('自費折扣方式') == '統一折扣':
            discount_fee = charge_utils.get_discount_fee(
                self.system_settings, self_total_fee, self.ui.spinBox_discount.value()
            )

        self.ui.tableWidget_cash_fees.setItem(
            self.SELF_COLUMN['DiscountFee'],
            0,
            QtWidgets.QTableWidgetItem(string_utils.xstr(discount_fee))
        )

        item = self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['DiscountFee'], 0)
        if item:
            item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            item.setForeground(QtGui.QColor('red'))

    def _set_table_width(self):
        self.table_widget_ins_fees.set_table_heading_width([90])
        self.table_widget_cash_fees.set_table_heading_width([100])

    def _set_new_self_medical_fees(self):
        ins_fees = [
            [-1, None],
            [0, None],
            [1, None],
            [2, None],
            [3, None],
            [4, None],
            [5, None],
            [6, None],
            [7, None],
            [8, None],
            [9, None],
            [10, None],
        ]

        cash_fees = [
            [-1, None],
            [0, None],
            [1, None],
            [2, None],
            [3, None],
            [4, None],
            [5, None],
            [6, None],
            [7, None],
            [8, None],
            [9, None],
            [10, None],
            [11, None],
            [12, None],
            [13, None],
            [14, None],
            [15, None],
            [16, None],
        ]

        for fees in ins_fees:
            if fees[1] is None:
                fees[1] = 0
            self.ui.tableWidget_ins_fees.setItem(
                fees[0], 1, QtWidgets.QTableWidgetItem(string_utils.xstr(fees[1])))

        for fees in cash_fees:
            if fees[1] is None:
                fees[1] = 0
            self.ui.tableWidget_cash_fees.setItem(
                fees[0], 1, QtWidgets.QTableWidgetItem(string_utils.xstr(fees[1])))

        self.ui.tableWidget_ins_fees.setAlternatingRowColors(True)
        self.ui.tableWidget_cash_fees.setAlternatingRowColors(True)

        self._adjust_table_widget_align()

    def _read_fees(self):
        sql = f'''
            SELECT * FROM cases WHERE
            CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]

        self.ui.spinBox_discount.setValue(number_utils.get_integer(row['DiscountRate']))

        diag_share_fee = row['DiagShareFee']
        drug_share_fee = row['DrugShareFee']
        receipt_diag_share_fee = row['SDiagShareFee']
        receipt_drug_share_fee = row['SDrugShareFee']

        self.ui.comboBox_regist_payment_type.setCurrentText(row['RegistPaymentType'])
        self.ui.comboBox_charge_payment_type.setCurrentText(row['ChargePaymentType'])

        ins_fees = [
            [-1, row['DiagFee']],
            [0, row['InterDrugFee']],
            [1, row['PharmacyFee']],
            [2, row['AcupunctureFee']],
            [3, row['MassageFee']],
            [4, row['DislocateFee']],
            [5, row['ExamFee']],
            [6, row['InsTotalFee']],
            [7, diag_share_fee],
            [8, drug_share_fee],
            [9, row['InsApplyFee']],
            [10, row['AgentFee']],
        ]

        cash_fees = [
            [-1, row['RegistFee']],
            [0, receipt_diag_share_fee],
            [1, receipt_drug_share_fee],
            [2, row['DepositFee']],
            [3, row['RefundFee']],
            [4, row['SDiagFee']],
            [5, row['SDrugFee']],
            [6, row['SHerbFee']],
            [7, row['SExpensiveFee']],
            [8, row['SAcupunctureFee']],
            [9, row['SMassageFee']],
            [10, row['SMaterialFee']],
            [11, row['SExamFee']],
            [12, row['SelfTotalFee']],
            [13, row['DiscountFee']],
            [14, row['TotalFee']],
            [15, row['ReceiptFee']],
        ]

        for fees in ins_fees:
            if fees[1] is None:
                fees[1] = 0
            self.ui.tableWidget_ins_fees.setItem(
                fees[0], 1, QtWidgets.QTableWidgetItem(string_utils.xstr(fees[1])))

        for fees in cash_fees:
            if fees[1] is None:
                fees[1] = 0
            self.ui.tableWidget_cash_fees.setItem(
                fees[0], 1, QtWidgets.QTableWidgetItem(string_utils.xstr(fees[1])))

        if string_utils.xstr(row['TreatType']) in nhi_utils.CARE_TREAT:
            self.ins_table_headers[5] = '加強照護費'
            self.ui.tableWidget_ins_fees.setVerticalHeaderLabels(self.ins_table_headers)

        if string_utils.xstr(row['TreatType']) in nhi_utils.HOME_CARE:
            self.self_table_headers[10] = '代收費'
            self.ui.tableWidget_cash_fees.setVerticalHeaderLabels(self.self_table_headers)

        self.ui.tableWidget_ins_fees.setAlternatingRowColors(True)
        self.ui.tableWidget_cash_fees.setAlternatingRowColors(True)

        self._adjust_table_widget_align()
        self._set_cash_fee_editable()

    def _set_cash_fee_editable(self):
        readonly_fields = [
            self.SELF_COLUMN['SelfTotalFee'],
            self.SELF_COLUMN['TotalFee']
        ]
        for field_no in readonly_fields:
            item = self.ui.tableWidget_cash_fees.item(field_no, 0)
            item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            item.setFlags(QtCore.Qt.ItemIsEnabled)

        user_name = system_utils.get_user_name(self.system_settings)
        if user_name == '超級使用者':
            pass
        elif personnel_utils.get_permission(self.database, '病歷資料', '更改自費實收金額', user_name) != 'Y':
            item = self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['ReceiptFee'], 0)
            item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            item.setFlags(QtCore.Qt.ItemIsEnabled)

    def _adjust_table_widget_align(self):
        for row_no in range(self.ui.tableWidget_ins_fees.rowCount()):
            if self.ui.tableWidget_ins_fees.item(row_no, 0) is None:
                continue

            self.ui.tableWidget_ins_fees.item(
                row_no, 0).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )
            if row_no in [
                self.INS_COLUMN['DiagShareFee'],
                self.INS_COLUMN['DrugShareFee'],
            ]:
                self.ui.tableWidget_ins_fees.item(
                    row_no, 0).setForeground(
                    QtGui.QColor('red')
                )
            if row_no in [self.INS_COLUMN['AgentFee']]:
                self.ui.tableWidget_ins_fees.item(
                    row_no, 0).setForeground(
                    QtGui.QColor('darkgreen')
                )

        for row_no in range(self.ui.tableWidget_cash_fees.rowCount()):
            if self.ui.tableWidget_cash_fees.item(row_no, 0) is None:
                continue

            self.ui.tableWidget_cash_fees.item(
                row_no, 0).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )

            if row_no in [self.SELF_COLUMN['DiscountFee']]:
                self.ui.tableWidget_cash_fees.item(
                    row_no, 0).setForeground(
                    QtGui.QColor('red')
                )

    def _check_home_care_share_fee(self):
        diag_share_fee = number_utils.get_integer(
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['DiagShareFee'], 0).text()
        )

        ins_total_fee = number_utils.get_integer(
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['InsTotalFee'], 0).text()
        )
        inter_drug_fee = number_utils.get_integer(
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['InterDrugFee'], 0).text()
        )
        pharmacy_fee = number_utils.get_integer(
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['PharmacyFee'], 0).text()
        )
        receipt_diag_share_fee = number_utils.get_integer(
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['ReceiptDiagShare'], 0).text()
        )
        if diag_share_fee > receipt_diag_share_fee:
            treat_fee = ins_total_fee - inter_drug_fee - pharmacy_fee
            system_utils.show_message_box(
                QMessageBox.Information,
                '加收費用提醒',
                f'''
                    <font size="5" color="blue"><b>
                        門診掛號預收門診負擔為{receipt_diag_share_fee}元, 實際應收門診負擔為{diag_share_fee}元,
                        請加收門診負擔{diag_share_fee - receipt_diag_share_fee}元.
                    </b></font>
                ''',
                f'''
                    居家醫療應收門診負擔為診療費用的5%,<br>
                    診療費用{treat_fee} * 5% = {diag_share_fee}
                '''
            )

    def calculate_fees(self, auto_calculate_fees=False):
        ins_type = string_utils.xstr(self.parent.tab_registration.comboBox_ins_type.currentText())
        if ins_type == '健保':
            self.calculate_ins_fees()

        self.calculate_self_fees(self.parent.tab_list, auto_calculate_fees=auto_calculate_fees)

    def _get_infectious_drug(self):
        is_infectious_drug = False
        is_ins_drug = False

        tableWidget_prescript = self.parent.tab_list[0].tableWidget_prescript
        for row_no in range(tableWidget_prescript.rowCount()):
            medicine_name_item = tableWidget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'])
            if medicine_name_item is None:
                continue

            ins_code_item = tableWidget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO['InsCode'])
            if ins_code_item is None:
                continue

            medicine_name = medicine_name_item.text()
            ins_code = ins_code_item.text()

            if '台灣清冠一號' in medicine_name:
                is_infectious_drug = True
            elif ins_code != '':
                is_ins_drug = True

        if is_infectious_drug and is_ins_drug:
            infectious_drug = '台灣清冠一號及科學中藥'
        elif is_infectious_drug:
            infectious_drug = '台灣清冠一號'
        elif is_ins_drug:
            infectious_drug = '科學中藥'
        else:
            infectious_drug = '未開藥'

        return infectious_drug

    def calculate_ins_fees(self):
        ins_type = string_utils.xstr(self.parent.tab_registration.comboBox_ins_type.currentText())
        if ins_type == '自費':
            ins_fee = charge_utils.clear_ins_fee()
            self._set_ins_fee(ins_fee)
            self._set_receipt_drug_share_fee(None, 0)
            self._set_receipt_diag_share_fee(None, 0)
            self._adjust_table_widget_align()
            return

        if self.parent.tab_registration.ui.comboBox_apply_type.currentText() == '補報差額':
            return

        if self.parent.tab_list[0] is None:
            return

        try:
            pres_days = number_utils.get_integer(self.parent.tab_list[0].ui.comboBox_pres_days.currentText())
        except ValueError:
            self.parent.tab_list[0].comboBox_pres_days.setCurrentText(None)
            pres_days = number_utils.get_integer(self.parent.tab_list[0].ui.comboBox_pres_days.currentText())

        tab_ins_care = self.parent.tab_list[10]
        if tab_ins_care is not None:
            table_widget_ins_care = tab_ins_care.ui.tableWidget_prescript
        else:
            table_widget_ins_care = None

        infectious_drug = self._get_infectious_drug()
        isolation_position = self.parent.tab_registration.ui.comboBox_isolation_position.currentText()

        primary_treatment = self.parent.tab_list[0].comboBox_treatment.currentText()
        secondary_treatment = self.parent.tab_list[0].comboBox_second_treatment.currentText()
        course = number_utils.get_integer(self.parent.tab_registration.comboBox_course.currentText())
        treatment = nhi_utils.get_treatment(
            self.database, self.case_key, primary_treatment, secondary_treatment, course)

        try:
            integrate_care = self.parent.check_box_integrate_care.isChecked()  # 有可能還沒create widget, 會造成不會批價
        except Exception:
            integrate_care = False

        ins_fee = charge_utils.get_ins_fee(
            self.database, self.system_settings,
            table_widget_ins_care,
            case_key=self.case_key,
            reg_type=string_utils.xstr(self.parent.tab_registration.comboBox_reg_type.currentText()),
            treat_type=string_utils.xstr(self.parent.tab_registration.comboBox_treat_type.currentText()),
            share=string_utils.xstr(self.parent.tab_registration.comboBox_share_type.currentText()),
            course=course,
            pres_days=pres_days,
            pharmacy_type=string_utils.xstr(self.parent.tab_registration.comboBox_pharmacy_type.currentText()),
            treatment=treatment,
            second_treatment=self.parent.tab_list[0].comboBox_second_treatment.currentText(),
            infectious_drug=infectious_drug,
            isolation_position=isolation_position,
            integrate_care=integrate_care,
        )

        self._set_ins_fee(ins_fee)

    def _set_ins_fee(self, ins_fee):
        ins_fees = [
            [self.INS_COLUMN['DiagFee'], ins_fee['diag_fee']],
            [self.INS_COLUMN['InterDrugFee'], ins_fee['drug_fee']],
            [self.INS_COLUMN['PharmacyFee'], ins_fee['pharmacy_fee']],
            [self.INS_COLUMN['AcupunctureFee'], ins_fee['acupuncture_fee']],
            [self.INS_COLUMN['MassageFee'], ins_fee['massage_fee']],
            [self.INS_COLUMN['DislocateFee'], ins_fee['dislocate_fee']],
            [self.INS_COLUMN['ExamFee'], ins_fee['exam_fee']],
            [self.INS_COLUMN['InsTotalFee'], ins_fee['ins_total_fee']],
            [self.INS_COLUMN['DiagShareFee'], ins_fee['diag_share_fee']],
            [self.INS_COLUMN['DrugShareFee'], ins_fee['drug_share_fee']],
            [self.INS_COLUMN['InsApplyFee'], ins_fee['ins_apply_fee']],
            [self.INS_COLUMN['AgentFee'], ins_fee['agent_fee']],
        ]

        for fee in ins_fees:
            self.ui.tableWidget_ins_fees.setItem(
                fee[0], 0, QtWidgets.QTableWidgetItem(string_utils.xstr(fee[1]))
            )
        self._adjust_table_widget_align()

        receipt_diag_share_fee = ins_fee['diag_share_fee']
        receipt_drug_share_fee = ins_fee['drug_share_fee']
        discount_type = patient_utils.get_patient_discount_type(self.database, self.patient_key)

        # if self.call_from in ['醫師看診作業', '醫師看診作業-查詢']:
        self._set_receipt_drug_share_fee(discount_type, receipt_drug_share_fee)

        if self.system_settings.field('部份負擔連動') == 'Y' or \
                self.system_settings.field('檢查門診負擔多退少補') == 'Y':
            self._set_receipt_diag_share_fee(discount_type, receipt_diag_share_fee)

        self._adjust_table_widget_align()

    # 設定實收藥品負擔
    def _set_receipt_drug_share_fee(self, discount_type, receipt_drug_share_fee):
        drug_share_discount_fee = charge_utils.get_drug_share_discount_fee(self.database, discount_type)
        if drug_share_discount_fee is not None:
            receipt_drug_share_fee = drug_share_discount_fee

        self.ui.tableWidget_cash_fees.setItem(  # 實收藥品負擔
            self.SELF_COLUMN['ReceiptDrugShare'], 0,
            QtWidgets.QTableWidgetItem(string_utils.xstr(receipt_drug_share_fee))
        )

    # 設定實收門診負擔
    def _set_receipt_diag_share_fee(self, discount_type, receipt_diag_share_fee):
        diag_share_discount_fee = charge_utils.get_diag_share_discount_fee(self.database, discount_type)
        if diag_share_discount_fee is not None:
            receipt_diag_share_fee = diag_share_discount_fee

        self.ui.tableWidget_cash_fees.setItem(  # 實收門診負擔
            self.SELF_COLUMN['ReceiptDiagShare'], 0,
            QtWidgets.QTableWidgetItem(string_utils.xstr(receipt_diag_share_fee))
        )

    def auto_cashier(self):
        discount_type = patient_utils.get_patient_discount_type(self.database, self.patient_key)

        diag_share_fee = number_utils.get_integer(
            charge_utils.get_table_widget_item_fee(
                self.ui.tableWidget_ins_fees, self.INS_COLUMN['DiagShareFee'], 0
            )
        )
        receipt_diag_share_fee = diag_share_fee
        diag_share_discount_fee = charge_utils.get_diag_share_discount_fee(self.database, discount_type)
        if diag_share_discount_fee is not None:
            diag_share_fee = diag_share_discount_fee

        drug_share_fee = number_utils.get_integer(
            charge_utils.get_table_widget_item_fee(
                self.ui.tableWidget_ins_fees, self.INS_COLUMN['DrugShareFee'], 0
            )
        )
        receipt_drug_share_fee = drug_share_fee
        drug_share_discount_fee = charge_utils.get_drug_share_discount_fee(
            self.database, string_utils.xstr(discount_type)
        )
        if drug_share_discount_fee is not None:
            receipt_drug_share_fee = drug_share_discount_fee

        self.ui.tableWidget_cash_fees.setItem(
            self.SELF_COLUMN['ReceiptDiagShare'], 0,
            QtWidgets.QTableWidgetItem(string_utils.xstr(receipt_diag_share_fee))
        )
        self.ui.tableWidget_cash_fees.setItem(
            self.SELF_COLUMN['ReceiptDrugShare'], 0,
            QtWidgets.QTableWidgetItem(string_utils.xstr(receipt_drug_share_fee))
        )

        # total_fee = number_utils.get_integer(
        #     charge_utils.get_table_widget_item_fee(
        #         self.ui.tableWidget_cash_fees, self.SELF_COLUMN['TotalFee'], 0
        #     )
        # )
        # self.ui.tableWidget_cash_fees.setItem(    # 不可自動帶出, 否則永遠不會有欠款
        #     self.SELF_COLUMN['ReceiptFee'], 0,
        #     QtWidgets.QTableWidgetItem(string_utils.xstr(total_fee))
        # )

    def get_total_fee(self):
        self_fee = charge_utils.get_self_fee(self.parent, self.database, self.system_settings, self.parent.tab_list)

        self_total_fee = number_utils.get_integer(
            self_fee['diag_fee'] + self_fee['drug_fee'] + self_fee['herb_fee'] + self_fee['expensive_fee'] +
            self_fee['acupuncture_fee'] + self_fee['massage_fee'] +
            self_fee['material_fee'] + self_fee['exam_fee']
        )
        if self.system_settings.field('自費折扣方式') == '統一折扣':
            self_fee['discount_fee'] = self_total_fee - (self_total_fee * self.ui.spinBox_discount.value() / 100)

        self_fee['diag_fee'] = number_utils.round_up(self_fee['diag_fee'])
        self_fee['drug_fee'] = number_utils.round_up(self_fee['drug_fee'])
        self_fee['herb_fee'] = number_utils.round_up(self_fee['herb_fee'])  # 四捨五入
        self_fee['expensive_fee'] = number_utils.round_up(self_fee['expensive_fee'])
        self_fee['acupuncture_fee'] = number_utils.round_up(self_fee['acupuncture_fee'])
        self_fee['massage_fee'] = number_utils.round_up(self_fee['massage_fee'])
        self_fee['material_fee'] = number_utils.round_up(self_fee['material_fee'])
        self_fee['exam_fee'] = number_utils.round_up(self_fee['exam_fee'])

        self_fee['discount_fee'] = number_utils.round_up(self_fee['discount_fee'])

        self_total_fee = number_utils.get_integer(
            self_fee['diag_fee'] +
            self_fee['drug_fee'] +
            self_fee['herb_fee'] +
            self_fee['expensive_fee'] +
            self_fee['acupuncture_fee'] +
            self_fee['massage_fee'] +
            self_fee['material_fee'] +
            self_fee['exam_fee']
        )
        total_fee = number_utils.get_integer(self_total_fee - self_fee['discount_fee'])

        return total_fee

    # 自費批價
    def calculate_self_fees(self, tab_list, auto_calculate_fees=False):
        if not auto_calculate_fees and self.system_settings.field('手動批價') == 'Y':
            return

        self_fee = charge_utils.get_self_fee(self.parent, self.database, self.system_settings, tab_list)
        ins_type = string_utils.xstr(self.parent.tab_registration.comboBox_ins_type.currentText())

        self_fee['diag_fee'] = number_utils.round_up(self_fee['diag_fee'])
        self_fee['drug_fee'] = number_utils.round_up(self_fee['drug_fee'])
        self_fee['herb_fee'] = number_utils.round_up(self_fee['herb_fee'])  # 四捨五入
        self_fee['expensive_fee'] = number_utils.round_up(self_fee['expensive_fee'])
        self_fee['acupuncture_fee'] = number_utils.round_up(self_fee['acupuncture_fee'])
        self_fee['massage_fee'] = number_utils.round_up(self_fee['massage_fee'])
        self_fee['material_fee'] = number_utils.round_up(self_fee['material_fee'])
        self_fee['exam_fee'] = number_utils.round_up(self_fee['exam_fee'])
        self_fee['discount_fee'] = number_utils.round_up(self_fee['discount_fee'])

        self_total_fee = number_utils.get_integer(
            self_fee['diag_fee'] +
            self_fee['drug_fee'] +
            self_fee['herb_fee'] +
            self_fee['expensive_fee'] +
            self_fee['acupuncture_fee'] +
            self_fee['massage_fee'] +
            self_fee['material_fee'] +
            self_fee['exam_fee']
        )

        if self_total_fee > 0 and ins_type == '自費' and self_fee['diag_fee'] == 0:
            visit = string_utils.xstr(self.parent.tab_registration.comboBox_visit.currentText())            
            diag_fee = charge_utils.get_misc_fee(self.database, f'{visit}診察費')
            if diag_fee > 0:
                self_fee['diag_fee'] = diag_fee
                self_total_fee += diag_fee

        if self.system_settings.field('自費折扣方式') == '統一折扣':
            # discount_fee = self_total_fee - (self_total_fee * self.ui.spinBox_discount.value() / 100)
            discount_fee = charge_utils.get_discount_fee(
                self.system_settings, self_total_fee, self.ui.spinBox_discount.value()
            )
            self_fee['discount_fee'] = discount_fee

        self_fees = [
            [self.SELF_COLUMN['SDiagFee'], self_fee['diag_fee']],
            [self.SELF_COLUMN['SDrugFee'], self_fee['drug_fee']],
            [self.SELF_COLUMN['SHerbFee'], self_fee['herb_fee']],
            [self.SELF_COLUMN['SExpensiveFee'], self_fee['expensive_fee']],
            [self.SELF_COLUMN['SAcupunctureFee'], self_fee['acupuncture_fee']],
            [self.SELF_COLUMN['SMassageFee'], self_fee['massage_fee']],
            [self.SELF_COLUMN['SMaterialFee'], self_fee['material_fee']],
            [self.SELF_COLUMN['SExamFee'], self_fee['exam_fee']],
            [self.SELF_COLUMN['DiscountFee'], self_fee['discount_fee']],
        ]

        for fee in self_fees:
            self.ui.tableWidget_cash_fees.setItem(
                fee[0], 0, QtWidgets.QTableWidgetItem(string_utils.xstr(fee[1]))
            )

        self._calculate_own_expense_total()

        # if self.system_settings.field('自動完成批價作業') == 'Y' and not self.parent.is_doctor_done():  # 健保專用
        #     self.auto_cashier()

        self._adjust_table_widget_align()

    def _calculate_own_expense_total(self):
        current_row = self.ui.tableWidget_cash_fees.currentRow()
        for row_no in range(self.ui.tableWidget_cash_fees.rowCount()):
            self.ui.tableWidget_cash_fees.setCurrentCell(row_no, 0)

        self.ui.tableWidget_cash_fees.setCurrentCell(current_row, 0)

        diag_fee = charge_utils.get_table_widget_item_fee(
            self.ui.tableWidget_cash_fees, self.SELF_COLUMN['SDiagFee'], 0, reset_fee=True
        )
        drug_fee = charge_utils.get_table_widget_item_fee(
            self.ui.tableWidget_cash_fees, self.SELF_COLUMN['SDrugFee'], 0, reset_fee=True
        )
        herb_fee = charge_utils.get_table_widget_item_fee(
            self.ui.tableWidget_cash_fees, self.SELF_COLUMN['SHerbFee'], 0, reset_fee=True
        )
        expensive_fee = charge_utils.get_table_widget_item_fee(
            self.ui.tableWidget_cash_fees, self.SELF_COLUMN['SExpensiveFee'], 0, reset_fee=True
        )
        acupuncture_fee = charge_utils.get_table_widget_item_fee(
            self.ui.tableWidget_cash_fees, self.SELF_COLUMN['SAcupunctureFee'], 0, reset_fee=True
        )
        massage_fee = charge_utils.get_table_widget_item_fee(
            self.ui.tableWidget_cash_fees, self.SELF_COLUMN['SMassageFee'], 0, reset_fee=True
        )
        material_fee = charge_utils.get_table_widget_item_fee(
            self.ui.tableWidget_cash_fees, self.SELF_COLUMN['SMaterialFee'], 0, reset_fee=True
        )
        exam_fee = charge_utils.get_table_widget_item_fee(
            self.ui.tableWidget_cash_fees, self.SELF_COLUMN['SExamFee'], 0, reset_fee=True
        )
        self_total_fee = number_utils.get_integer(
                diag_fee + drug_fee + herb_fee + expensive_fee +
                acupuncture_fee + massage_fee +
                material_fee + exam_fee
        )

        discount_fee = charge_utils.get_table_widget_item_fee(
            self.ui.tableWidget_cash_fees, self.SELF_COLUMN['DiscountFee'], 0, reset_fee=True
        )
        total_fee = number_utils.get_integer(self_total_fee - discount_fee)

        # 2021.04.16 取消，造成結帳混亂
        # ins_type = string_utils.xstr(self.parent.tab_registration.comboBox_ins_type.currentText())
        # if ins_type == '自費':
        #     regist_fee = number_utils.get_integer(
        #         self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['RegistFee'], 0).text()
        #     )
        #     self_total_fee += regist_fee
        #     total_fee += regist_fee

        self.ui.tableWidget_cash_fees.setItem(
            self.SELF_COLUMN['SelfTotalFee'], 0,
            QtWidgets.QTableWidgetItem(string_utils.xstr(self_total_fee))
        )
        self.ui.tableWidget_cash_fees.setItem(
            self.SELF_COLUMN['DiscountFee'], 0,
            QtWidgets.QTableWidgetItem(string_utils.xstr(discount_fee))
        )
        self.ui.tableWidget_cash_fees.setItem(  # 應收金額
            self.SELF_COLUMN['TotalFee'], 0,
            QtWidgets.QTableWidgetItem(string_utils.xstr(total_fee))
        )

        # if self.system_settings.field('自動完成批價作業') == 'Y':
        self.ui.tableWidget_cash_fees.setItem(
            self.SELF_COLUMN['ReceiptFee'], 0,
            QtWidgets.QTableWidgetItem(string_utils.xstr(total_fee))
        )

        self._adjust_table_widget_align()

    def _calculate_discount(self):
        self_total_fee = charge_utils.get_table_widget_item_fee(
            self.ui.tableWidget_cash_fees, self.SELF_COLUMN['SelfTotalFee'], 0
        )
        discount_fee = charge_utils.get_discount_fee(
            self.system_settings, self_total_fee, self.ui.spinBox_discount.value()
        )
        self.ui.tableWidget_cash_fees.setItem(
            self.SELF_COLUMN['DiscountFee'], 0,
            QtWidgets.QTableWidgetItem(string_utils.xstr(discount_fee))
        )
        self._calculate_own_expense_total()

    def save_record(self, case_key=None):
        regist_type = string_utils.xstr(self.parent.tab_registration.comboBox_reg_type.currentText())
        treat_type = string_utils.xstr(self.parent.tab_registration.comboBox_treat_type.currentText())
        if self.call_from in ['醫師看診作業']:
            if treat_type in nhi_utils.HOME_CARE and regist_type not in nhi_utils.TOUR_TYPE:
                self._check_home_care_share_fee()

            ins_type = string_utils.xstr(self.parent.tab_registration.comboBox_ins_type.currentText())
            if ins_type == '健保' and self.system_settings.field('檢查門診負擔多退少補') == 'Y':
                self._check_receipt_diag_share_fee()

        self._update_ins_fees_data()
        self._update_cash_fees_data(case_key)

    # 檢查是否應加收或退還門診部份負擔 (有門診負擔優待者不檢查) 2025-04-02
    def _check_receipt_diag_share_fee(self):
        discount_type = patient_utils.get_patient_discount_type(self.database, self.patient_key)
        diag_share_discount_fee = charge_utils.get_diag_share_discount_fee(self.database, discount_type)
        if diag_share_discount_fee is not None:
            return

        receipt_diag_share_fee = number_utils.get_integer(self.medical_record['SDiagShareFee'])
        current_diag_share_fee = number_utils.get_integer(charge_utils.get_table_widget_item_fee(
            self.ui.tableWidget_ins_fees, self.INS_COLUMN['DiagShareFee'], 0
        ))
        if current_diag_share_fee == receipt_diag_share_fee:
            return

        fee = current_diag_share_fee - receipt_diag_share_fee
        if fee > 0:
            system_utils.show_message_box(
                QMessageBox.Warning,
                '請注意',
                f'<font color="red"><h2>處置內容變更，門診部份負擔應加收{fee}元!</h2></font>',
                '請加收門診部份負擔.'
            )
        else:
            system_utils.show_message_box(
                QMessageBox.Warning,
                '請注意',
                f'<font color="red"><h2>處置內容變更，門診部份負擔應退還{abs(fee)}元!</h2></font>',
                '請退還門診部份負擔.'
            )

    # 健保批價資料存檔
    def _update_ins_fees_data(self):
        if self.case_key is None:
            return

        fields = [
            'DiagFee', 'InterDrugFee', 'PharmacyFee',
            'AcupunctureFee', 'MassageFee', 'DislocateFee', 'ExamFee',
            'InsTotalFee', 'DiagShareFee', 'DrugShareFee', 'InsApplyFee', 'AgentFee',
        ]
        data = [
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['DiagFee'], 0).text(),
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['InterDrugFee'], 0).text(),
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['PharmacyFee'], 0).text(),
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['AcupunctureFee'], 0).text(),
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['MassageFee'], 0).text(),
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['DislocateFee'], 0).text(),
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['ExamFee'], 0).text(),
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['InsTotalFee'], 0).text(),
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['DiagShareFee'], 0).text(),
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['DrugShareFee'], 0).text(),
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['InsApplyFee'], 0).text(),
            self.ui.tableWidget_ins_fees.item(self.INS_COLUMN['AgentFee'], 0).text(),
        ]

        self.database.update_record('cases', fields, 'CaseKey', self.case_key, data)

    # 檢查是否需要補退掛號費用
    def _check_cash_fees(self, receipt_regist_fee, receipt_diag_share_fee):
        sql = f'''
            SELECT Birthday, DiscountType FROM patient
            WHERE
            PatientKey = {self.patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return receipt_regist_fee, receipt_diag_share_fee

        row = rows[0]

        try:
            birthday = row['Birthday'].strftime('%Y-%m-%d')
        except Exception:
            birthday = ''

        discount_type = string_utils.xstr(row['DiscountType'])

        ins_type = string_utils.xstr(self.parent.tab_registration.comboBox_ins_type.currentText())
        regist_type = string_utils.xstr(self.parent.tab_registration.comboBox_reg_type.currentText())
        treat_type = string_utils.xstr(self.parent.tab_registration.comboBox_treat_type.currentText())
        share_type = string_utils.xstr(self.parent.tab_registration.comboBox_share_type.currentText())
        visit = string_utils.xstr(self.parent.tab_registration.comboBox_visit.currentText())
        course = number_utils.get_integer(self.parent.tab_registration.comboBox_course.currentText())

        regist_fee = charge_utils.get_regist_fee(
            self.database, self.system_settings,
            birthday,
            discount_type,
            ins_type,
            share_type,
            treat_type,
            course,
            visit,
        )
        if ins_type == '健保':
            diag_share_fee = charge_utils.get_diag_share_fee(
                self.database, self.system_settings,
                share_type,
                treat_type,
                course,
                regist_type,
            )
            diag_share_discount_fee = charge_utils.get_diag_share_discount_fee(
                self.database, discount_type,
            )

            if diag_share_discount_fee is not None:
                diag_share_fee = diag_share_discount_fee
        else:
            diag_share_fee = 0

        remark_list = [] 
        reg_fee = 0
        if receipt_regist_fee != regist_fee:
            remark = f'掛號費應收: {regist_fee}元, 實收: {receipt_regist_fee}元'
            if receipt_regist_fee > regist_fee:
                remark += f', 應退: {receipt_regist_fee - regist_fee}元'
            elif receipt_regist_fee < regist_fee:
                remark += f', 應補: {regist_fee - receipt_regist_fee}元'

            reg_fee = regist_fee - receipt_regist_fee
            remark_list.append(remark)

            receipt_regist_fee = regist_fee

        share_fee = 0
        if receipt_diag_share_fee != diag_share_fee:
            remark = f'門診負擔應收: {diag_share_fee}元, 實收: {receipt_diag_share_fee}元'
            if receipt_diag_share_fee > diag_share_fee:
                remark += f', 應退: {receipt_diag_share_fee - diag_share_fee}元'
            elif receipt_diag_share_fee < diag_share_fee:
                remark += f', 應補: {diag_share_fee - receipt_diag_share_fee}元'

            share_fee = diag_share_fee - receipt_diag_share_fee
            remark_list.append(remark)

            receipt_diag_share_fee = diag_share_fee

        if len(remark_list) > 0: 
            total_fee = reg_fee + share_fee
            if total_fee > 0:
                remark_list.append(f'合計應補: {total_fee}元')
            elif total_fee < 0:
                remark_list.append(f'合計應退: {abs(total_fee)}元')

            if self.case_key is not None:
                case_utils.clear_case_extend(self.database, self.case_key, '掛號費用')
                case_utils.set_case_extend(
                    self.database, self.case_key, '掛號費用', '\n'.join(remark_list))

        return receipt_regist_fee, receipt_diag_share_fee

    # 自費批價資料存檔
    def _update_cash_fees_data(self, case_key=None):
        if case_key is None:
            case_key = self.case_key

        regist_fee = number_utils.get_integer(
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['RegistFee'], 0).text())

        receipt_diag_share_fee = number_utils.get_integer(
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['ReceiptDiagShare'], 0).text())

        if self.system_settings.field('病歷存檔檢查補退掛號費用') == 'Y' and not self.parent.is_doctor_done():  # 醫師候診中才檢查
            regist_fee, receipt_diag_share_fee = self._check_cash_fees(regist_fee, receipt_diag_share_fee)

        fields = [
            'RegistFee', 'SDiagShareFee', 'SDrugShareFee', 'DepositFee', 'RefundFee',
            'SDiagFee', 'SDrugFee', 'SHerbFee', 'SExpensiveFee',
            'SAcupunctureFee', 'SMassageFee', 'SMaterialFee', 'SExamFee',
            'SelfTotalFee', 'DiscountFee', 'TotalFee', 'ReceiptFee', 'DiscountRate',
            'RegistPaymentType', 'ChargePaymentType',
        ]

        data = [
            regist_fee,
            receipt_diag_share_fee,
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['ReceiptDrugShare'], 0).text(),
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['DepositFee'], 0).text(),
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['RefundFee'], 0).text(),
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['SDiagFee'], 0).text(),
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['SDrugFee'], 0).text(),
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['SHerbFee'], 0).text(),
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['SExpensiveFee'], 0).text(),
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['SAcupunctureFee'], 0).text(),
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['SMassageFee'], 0).text(),
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['SMaterialFee'], 0).text(),
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['SExamFee'], 0).text(),
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['SelfTotalFee'], 0).text(),
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['DiscountFee'], 0).text(),
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['TotalFee'], 0).text(),
            self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['ReceiptFee'], 0).text(),
            self.ui.spinBox_discount.value(),
            self.ui.comboBox_regist_payment_type.currentText(),
            self.ui.comboBox_charge_payment_type.currentText(),
        ]
        self.database.update_record('cases', fields, 'CaseKey', case_key, data)

        if self.system_settings.field('自動完成批價作業') != 'Y':
            return

        receipt_fee = (
                number_utils.get_integer(
                    self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['ReceiptFee'], 0).text()
                )
        )
        total_fee = (
                number_utils.get_integer(
                    self.ui.tableWidget_cash_fees.item(self.SELF_COLUMN['TotalFee'], 0).text()
                )
        )

        if receipt_fee < total_fee:
            self._write_debt(case_key, receipt_fee, total_fee)

    def _write_debt(self, case_key, receipt_fee, total_fee):
        debt_fee = total_fee - receipt_fee
        message = f'''
            <h3>
                <font color="red">
                    此人應收金額為{total_fee}, 實收金額為 {receipt_fee}, 是否欠款 {debt_fee} 元?
                </font>
            </h3>
        '''
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('批價存檔')
        msg_box.setText(message)
        msg_box.setInformativeText("注意！存檔後, 將產生一筆欠款資料!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        save_debt = msg_box.exec_()
        if not save_debt:
            return

        fields = [
            'CaseKey', 'PatientKey', 'DebtType', 'Name', 'CaseDate', 'Period', 'Doctor', 'Fee'
        ]

        data = [
            case_key,
            self.patient_key,
            '批價欠款',
            string_utils.xstr(self.medical_record['Name']),
            self.parent.tab_registration.lineEdit_case_date.text(),
            self.parent.tab_registration.comboBox_period.currentText(),
            self.parent.tab_registration.comboBox_doctor.currentText(),
            debt_fee,
        ]
        self.database.insert_record('debt', fields, data)

        fields = ['DebtFee']
        data = [debt_fee]
        self.database.update_record('cases', fields, 'CaseKey', case_key, data)
