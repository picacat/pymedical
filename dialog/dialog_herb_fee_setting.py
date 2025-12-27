
# 水藥批價原則設定 2021.12.10
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils
from libs import number_utils


# 主視窗
class DialogHerbFeeSetting(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogHerbFeeSetting, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.charge_settings_key = args[2]
        self.ui = None

        self._set_ui()
        self._set_signal()

        if self.charge_settings_key is not None:
            self._edit_charge_settings()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_HERB_FEE_SETTING, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

    # 設定信號
    def _set_signal(self):
        pass

    def accepted_button_clicked(self):
        pass

    def _edit_charge_settings(self):
        sql = f'''
            SELECT * FROM charge_settings
            WHERE
                ChargeSettingsKey = {self.charge_settings_key}
        '''
        row_data = self.database.select_record(sql)[0]

        item_name = row_data['ItemName']
        min_weight, max_weight = item_name.split('-')

        min_weight = number_utils.get_integer(min_weight)
        max_weight = number_utils.get_integer(max_weight)
        self.ui.spinBox_min_weight.setValue(min_weight)
        self.ui.spinBox_max_weight.setValue(max_weight)

        amount = number_utils.get_integer(row_data['Amount'])
        self.ui.spinBox_herb_fee.setValue(amount)

        self.ui.lineEdit_remark.setText(row_data['Remark'])

