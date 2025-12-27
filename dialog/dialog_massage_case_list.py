
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime

from libs import ui_utils
from libs import system_utils
from libs import nhi_utils
from libs import patient_utils
from libs import massage_utils
from libs import dialog_utils


# 病歷查詢視窗
class DialogMassageCaseList(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMassageCaseList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MASSAGE_CASE_LIST, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.dateEdit_start_date.setDate(datetime.datetime.now())
        self.ui.dateEdit_end_date.setDate(datetime.datetime.now())
        self._set_combo_box()
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.label_massage_customer_key.setEnabled(False)
        self.ui.lineEdit_massage_customer_key.setEnabled(False)
        self.ui.toolButton_select_patient.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.toolButton_select_patient.clicked.connect(lambda: self._select_patient(None))

        self.ui.radioButton_range_date.clicked.connect(self._set_date)
        self.ui.radioButton_all_date.clicked.connect(self._set_date)

        self.ui.radioButton_all_massage_customer.clicked.connect(self._set_customer)
        self.ui.radioButton_assigned_massage_customer.clicked.connect(self._set_customer)

    # 設定comboBox
    def _set_combo_box(self):
        script = 'select * from person where Position IN("推拿師父") '
        rows = self.database.select_record(script)
        massager_list = []
        for row in rows:
            massager_list.append(row['Name'])

        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_treat_type, massage_utils.TREAT_TYPE, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_massager, massager_list, '全部')

    def _set_customer(self):
        if self.ui.radioButton_all_massage_customer.isChecked():
            self.ui.lineEdit_massage_customer_key.setText('')
            enabled = False
        else:
            enabled = True

        self.ui.label_massage_customer_key.setEnabled(enabled)
        self.ui.lineEdit_massage_customer_key.setEnabled(enabled)
        self.ui.toolButton_select_patient.setEnabled(enabled)

        if self.ui.radioButton_assigned_massage_customer.isChecked():
            self.ui.lineEdit_massage_customer_key.setFocus()

    def _set_date(self):
        if self.ui.radioButton_all_date.isChecked():
            enabled = False
            self.ui.radioButton_assigned_massage_customer.setChecked(True)
            self._set_customer()
            self.ui.lineEdit_massage_customer_key.setFocus()
        else:
            enabled = True
            self.ui.radioButton_all_massage_customer.setChecked(True)
            self._set_customer()

        self.ui.label_date.setEnabled(enabled)
        self.ui.label_between.setEnabled(enabled)
        self.ui.label_period.setEnabled(enabled)
        self.ui.dateEdit_start_date.setEnabled(enabled)
        self.ui.dateEdit_end_date.setEnabled(enabled)
        self.ui.comboBox_period.setEnabled(enabled)

    # 設定 mysql script
    def get_sql(self):
        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')

        condition = []
        script = '''
            SELECT * FROM massage_cases
        '''

        if self.ui.radioButton_range_date.isChecked():
            condition.append(f'(massage_cases.CaseDate BETWEEN "{start_date}" AND "{end_date}")')
            period = self.ui.comboBox_period.currentText()
            if period != '全部':
                condition.append(f'massage_cases.Period = "{period}"')

        treat_type = self.ui.comboBox_treat_type.currentText()
        if treat_type != '全部':
            condition.append(f'massage_cases.TreatType = "{treat_type}"')

        massager = self.ui.comboBox_massager.currentText()
        if massager != '全部':
            condition.append(f'massage_cases.Massager = "{massager}"')

        keyword = self.ui.lineEdit_massage_customer_key.text()
        if keyword != '':
            massage_customer_key = patient_utils.get_patient_by_keyword(
                self, self.database, self.system_settings,
                'massage_customer', 'MassageCustomerKey', keyword
            )
            if massage_customer_key in ['', None]:
                self.ui.lineEdit_massage_customer_key.setText('')
            else:
                condition.append(f'massage_cases.MassageCustomerKey = {massage_customer_key}')

        if len(condition) > 0:
            condition = ' AND '.join(condition)
            script += f'WHERE {condition}'

        period_list = str(nhi_utils.PERIOD)[1:-1]
        script += f'''
            ORDER BY DATE(massage_cases.CaseDate), FIELD(massage_cases.Period, {period_list})
        '''

        if self.ui.radioButton_all_date.isChecked() and self.ui.lineEdit_massage_customer_key.text() == '':
            script = ''

        return script

    def accepted_button_clicked(self):
        pass

    def _select_patient(self, keyword=None):
        massage_customer_key = ''

        dialog = dialog_utils.get_dialog_select_patient(
            self, self.database, self.system_settings, 'massage_customer', 'MassageCustomerKey', keyword
        )
        if dialog.exec_():
            massage_customer_key = dialog.get_primary_key()

        self.ui.lineEdit_massage_customer_key.setText(massage_customer_key)

        dialog.deleteLater()
