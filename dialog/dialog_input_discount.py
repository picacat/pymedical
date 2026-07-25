
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from libs import ui_utils
from libs import system_utils
from libs import charge_utils


# 主視窗
class DialogInputDiscount(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInputDiscount, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        try:
            self.charge_settings_key = args[2]
        except IndexError:
            self.charge_settings_key = None

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INPUT_DISCOUNT, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('存檔')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.lineEdit_item_name.setFocus()
        self._set_combo_box()

    def _set_combo_box(self):
        ui_utils.set_combo_box(self.ui.comboBox_charge_type, charge_utils.DISCOUNT_TYPE)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def _edit_charge_settings(self):
        sql = f'''
            SELECT * FROM charge_settings
            WHERE
                ChargeSettingsKey = {self.charge_settings_key}
        '''
        row_data = self.database.select_record(sql)[0]
        self.ui.comboBox_charge_type.setCurrentText(row_data['ChargeType'])
        self.ui.lineEdit_item_name.setText(row_data['ItemName'])
        self.ui.spinBox_amount.setValue(row_data['Amount'])

    def accepted_button_clicked(self):
        if self.charge_settings_key is None:
            return

        fields = ['ChargeType', 'ItemName', 'Amount']
        data = [
            self.ui.comboBox_charge_type.currentText(),
            self.ui.lineEdit_item_name.text(),
            self.ui.spinBox_amount.value(),
        ]

        self.database.update_record('charge_settings', fields, 'ChargeSettingsKey',
                                    self.charge_settings_key, data)
