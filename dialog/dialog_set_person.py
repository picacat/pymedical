
# 設定抽成人員 2021-11-12
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils
from libs import personnel_utils
from libs import string_utils
from libs import prescript_utils


# 主視窗
class DialogSetPerson(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogSetPerson, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.prescript_key = args[3]
        self.set_type = args[4]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._read_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_SET_PERSON, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.setWindowTitle(self.set_type)
        self.ui.groupBox.setTitle(self.set_type)

        ui_utils.set_combo_box(
            self.ui.comboBox_massage_referrer,
            personnel_utils.get_person(self.database, '推拿師父'), None,
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_nursing_assistant,
            personnel_utils.get_person(self.database, '職員'), None,
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_dealer,
            personnel_utils.get_person(self.database, '職員'), None,
        )

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        pass

    def _read_data(self):
        sql = f'''
            SELECT InvoiceNo, MassageReferrer, NursingAssistant, Remark FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]
        self.ui.lineEdit_invoice_no.setText(string_utils.xstr(row['InvoiceNo']))

        massage_referrer = prescript_utils.get_pres_extend_value(self.database, self.prescript_key, '傷助推薦')
        if massage_referrer in [None, '']:
            massage_referrer = string_utils.xstr(row['MassageReferrer'])

        nursing_assistant = prescript_utils.get_pres_extend_value(self.database, self.prescript_key, '護佐')
        if nursing_assistant in [None, '']:
            nursing_assistant = string_utils.xstr(row['NursingAssistant'])

        self.ui.comboBox_massage_referrer.setCurrentText(massage_referrer)
        self.ui.comboBox_nursing_assistant.setCurrentText(nursing_assistant)

        sql = f'''
            SELECT Dealer, Remark FROM prescript
            WHERE
                PrescriptKey = {self.prescript_key}
        '''
        prescript_rows = self.database.select_record(sql)
        if len(prescript_rows) > 0:
            prescript_row = prescript_rows[0]
            self.ui.textEdit_remark.setText(string_utils.xstr(prescript_row['Remark']))
            self.ui.comboBox_dealer.setCurrentText(string_utils.xstr(prescript_row['Dealer']))
