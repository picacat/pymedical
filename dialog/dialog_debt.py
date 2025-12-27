
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime

from libs import system_utils
from libs import ui_utils
from libs import nhi_utils
from libs import personnel_utils
from libs import registration_utils
from libs import string_utils
from libs import number_utils


# 主視窗
class DialogDebt(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogDebt, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.debt_key = args[2]
        self.case_key = args[3]

        self.debt_row = None
        self.case_row = None

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_DEBT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        ui_utils.set_combo_box(self.ui.comboBox_payment_type, nhi_utils.PAYMENT_TYPE)
        self._set_debt_data()

    def _set_debt_data(self):
        sql = f'''
            SELECT * FROM debt
            WHERE
                DebtKey = {self.debt_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.debt_row = rows[0]

        self.ui.dateEdit_return_date.setDate(datetime.datetime.today())

        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD)
        ui_utils.set_combo_box(
            self.ui.comboBox_cashier,
            personnel_utils.get_person(self.database, '全部'),
        )

        self.ui.comboBox_cashier.setCurrentText(self.system_settings.field('使用者'))
        period = registration_utils.get_current_period(self.system_settings)
        self.ui.comboBox_period.setCurrentText(period)

        fee = number_utils.get_integer(self.debt_row['Fee'])
        fee1 = number_utils.get_integer(self.debt_row['Fee1'])
        fee2 = number_utils.get_integer(self.debt_row['Fee2'])
        fee3 = number_utils.get_integer(self.debt_row['Fee3'])

        remain =  fee - (fee1 + fee2 + fee3)

        self.ui.lineEdit_debt.setText(string_utils.xstr(remain))
        self.ui.lineEdit_pay_back.setText(self.ui.lineEdit_debt.text())
        self.ui.lineEdit_pay_back.setFocus()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        self._update_debt()

    def _update_debt(self):
        sql = f'''
            SELECT * FROM debt
            WHERE
                DebtKey = {self.debt_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        debt_row = rows[0]
        if debt_row['Fee1'] in [0, None]:
            fields = ['ReturnDate1', 'Period1', 'Fee1', 'Cashier1' ]
        elif debt_row['Fee2'] in [0, None]:
            fields = ['ReturnDate2', 'Period2', 'Fee2', 'Cashier2' ]
        else:
            fields = ['ReturnDate3', 'Period3', 'Fee3', 'Cashier3' ]
    
        fields += ['TotalReturn', 'PaymentType']

        current_return_fee = number_utils.get_integer(self.ui.lineEdit_pay_back.text())
        total_retun_fee = number_utils.get_integer(debt_row['TotalReturn']) + current_return_fee

        data = [
            self.ui.dateEdit_return_date.date().toString('yyyy-MM-dd 00:00:00'),
            self.ui.comboBox_period.currentText(),
            current_return_fee,
            self.ui.comboBox_cashier.currentText(),
            total_retun_fee,
            self.ui.comboBox_payment_type.currentText(),
        ]

        self.database.update_record('debt', fields, 'DebtKey', self.debt_key, data)
