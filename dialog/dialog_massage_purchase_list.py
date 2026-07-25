
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime
from libs import ui_utils
from libs import system_utils
from libs import nhi_utils
from libs import string_utils


# 自購藥查詢對話方塊
class DialogMassagePurchaseList(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMassagePurchaseList, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MASSAGE_PURCHASE_LIST, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.dateEdit_start_date.setDate(datetime.datetime.now())
        self.ui.dateEdit_end_date.setDate(datetime.datetime.now())
        self._set_combo_box()
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    # 設定comboBox
    def _set_combo_box(self):
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD, '全部')

        sql = '''
            SELECT * FROM person
            WHERE
                Position NOT IN ("醫師", "支援醫師")
        '''
        rows = self.database.select_record(sql)
        cashier_list = []
        for row in rows:
            cashier_list.append(string_utils.xstr(row['Name']))

        sql = '''
            SELECT * FROM person
            WHERE
                Position IN ("推拿師父")
        '''
        rows = self.database.select_record(sql)
        massager_list = []
        for row in rows:
            massager_list.append(string_utils.xstr(row['Name']))

        ui_utils.set_combo_box(self.ui.comboBox_cashier, cashier_list, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_massager, massager_list, '全部')

    # 設定 mysql script
    def get_sql(self):
        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')

        script = f'''
            SELECT * FROM massage_cases
            WHERE
                (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
                (InsType = "自費") AND
                (TreatType = "購買商品")
            '''

        period = self.ui.comboBox_period.currentText()
        if period != '全部':
            script += f' AND Period = "{period}"'

        cashier = self.ui.comboBox_cashier.currentText()
        if cashier != '全部':
            script += f' AND Cashier = "{cashier}"'

        massager = self.ui.comboBox_massager.currentText()
        if massager != '全部':
            script += f' AND Massager = "{massager}"'

        script += " ORDER BY CaseDate"

        return script

    def accepted_button_clicked(self):
        pass
