
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from libs import ui_utils
from libs import system_utils
from libs import nhi_utils


# 主視窗
class DialogInputRegist(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInputRegist, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INPUT_REGIST, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self._set_combo_box()
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('存檔')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.label_percent.setVisible(False)
        self.ui.lineEdit_item_name.setFocus()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.comboBox_ins_type.currentTextChanged.connect(self._set_spin_box_amount)

    # 設定comboBox
    def _set_combo_box(self):
        ui_utils.set_combo_box(self.ui.comboBox_ins_type, nhi_utils.INS_TYPE + ['備註', '自費折扣'], '不分類')
        ui_utils.set_combo_box(self.ui.comboBox_share_type, nhi_utils.SHARE_TYPE, '不分類')
        ui_utils.set_combo_box(self.ui.comboBox_treat_type, nhi_utils.TREAT_TYPE, '不分類')
        ui_utils.set_combo_box(self.ui.comboBox_course, nhi_utils.COURSE_TYPE)

    def _set_spin_box_amount(self):
        if self.ui.comboBox_ins_type.currentText() == '自費折扣':
            self.ui.spinBox_amount.setRange(0, 100)
            self.ui.label_percent.setVisible(True)

        else:
            self.ui.spinBox_amount.setRange(0, 999999)
            self.ui.label_percent.setVisible(False)

    def _edit_charge_settings(self):
        sql = f'''
            SELECT * FROM charge_settings
            WHERE
                ChargeSettingsKey = {self.charge_settings_key}
        '''
        row_data = self.database.select_record(sql)[0]
        self.ui.lineEdit_item_name.setText(row_data['ItemName'])
        self.ui.comboBox_ins_type.setCurrentText(row_data['InsType'])
        self.ui.comboBox_share_type.setCurrentText(row_data['ShareType'])
        self.ui.comboBox_treat_type.setCurrentText(row_data['TreatType'])
        self.ui.comboBox_course.setCurrentText(row_data['Course'])
        self.ui.spinBox_amount.setValue(row_data['Amount'])
        self.ui.lineEdit_remark.setText(row_data['Remark'])

    def accepted_button_clicked(self):
        if self.charge_settings_key is None:
            return

        fields = ['ItemName', 'InsType', 'ShareType', 'TreatType', 'Course', 'Amount', 'Remark']
        data = [
            self.ui.lineEdit_item_name.text(),
            self.ui.comboBox_ins_type.currentText(),
            self.ui.comboBox_share_type.currentText(),
            self.ui.comboBox_treat_type.currentText(),
            self.ui.comboBox_course.currentText(),
            self.ui.spinBox_amount.value(),
            self.ui.lineEdit_remark.text()
        ]
        self.database.update_record('charge_settings', fields, 'ChargeSettingsKey',
                                    self.charge_settings_key, data)
