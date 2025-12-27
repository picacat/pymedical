
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from libs import ui_utils
from libs import system_utils
from libs import nhi_utils


# 主視窗
class DialogInputShare(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInputShare, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        try:
            self.charge_settings_key = args[2]
        except IndexError:
            self.charge_settings_key = None

        try:
            self.charge_type = args[3]
        except IndexError:
            self.charge_type = None

        self.ui = None

        self._set_ui()
        self._set_signal()
        if self.charge_settings_key is not None:
            if self.charge_type == '門診負擔':
                self._edit_diag_share()
            else:
                self._edit_drug_share()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INPUT_SHARE, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('存檔')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.groupBox.setTitle(self.charge_type)
        self._set_combo_box()
        self.ui.lineEdit_item_name.setFocus()

    # 設定comboBox
    def _set_combo_box(self):
        ui_utils.set_combo_box(self.ui.comboBox_share_type, nhi_utils.SHARE_TYPE)

        if self.charge_type == '藥品負擔':
            self.ui.label_treat_type.hide()
            self.ui.comboBox_treat_type.hide()
            self.ui.label_course.hide()
            self.ui.comboBox_course.hide()
        else:
            ui_utils.set_combo_box(self.ui.comboBox_treat_type, nhi_utils.TREAT_TYPE)
            ui_utils.set_combo_box(self.ui.comboBox_course, nhi_utils.COURSE_TYPE)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def _edit_diag_share(self):
        sql = f'''
            SELECT * FROM charge_settings
            WHERE
                ChargeSettingsKey = {self.charge_settings_key}
        '''
        row_data = self.database.select_record(sql)[0]
        self.ui.lineEdit_item_name.setText(row_data['ItemName'])
        self.ui.comboBox_share_type.setCurrentText(row_data['ShareType'])
        self.ui.comboBox_treat_type.setCurrentText(row_data['TreatType'])
        self.ui.comboBox_course.setCurrentText(row_data['Course'])
        self.ui.lineEdit_ins_code.setText(row_data['InsCode'])
        self.ui.spinBox_amount.setValue(row_data['Amount'])
        self.ui.lineEdit_remark.setText(row_data['Remark'])

    def _edit_drug_share(self):
        sql = f'''
            SELECT * FROM charge_settings
            WHERE
                ChargeSettingsKey = {self.charge_settings_key}
        '''
        row_data = self.database.select_record(sql)[0]
        self.ui.lineEdit_item_name.setText(row_data['ItemName'])
        self.ui.comboBox_share_type.setCurrentText(row_data['ShareType'])
        self.ui.lineEdit_ins_code.setText(row_data['InsCode'])
        self.ui.spinBox_amount.setValue(row_data['Amount'])
        self.ui.lineEdit_remark.setText(row_data['Remark'])

    def accepted_button_clicked(self):
        if self.charge_settings_key is None:
            return

        if self.charge_type == '門診負擔':
            self._save_diag_share()
        else:
            self._save_drug_share()

    def _save_diag_share(self):
        fields = ['ItemName', 'ShareType', 'TreatType', 'Course', 'InsCode', 'Amount', 'Remark']
        data = [
            self.ui.lineEdit_item_name.text(),
            self.ui.comboBox_share_type.currentText(),
            self.ui.comboBox_treat_type.currentText(),
            self.ui.comboBox_course.currentText(),
            self.ui.lineEdit_ins_code.text(),
            self.ui.spinBox_amount.value(),
            self.ui.lineEdit_remark.text()
        ]

        self.database.update_record('charge_settings', fields, 'ChargeSettingsKey',
                                    self.charge_settings_key, data)

    def _save_drug_share(self):
        fields = ['ItemName', 'ShareType', 'InsCode', 'Amount', 'Remark']
        data = [
            self.ui.lineEdit_item_name.text(),
            self.ui.comboBox_share_type.currentText(),
            self.ui.lineEdit_ins_code.text(),
            self.ui.spinBox_amount.value(),
            self.ui.lineEdit_remark.text()
        ]

        self.database.update_record('charge_settings', fields, 'ChargeSettingsKey',
                                    self.charge_settings_key, data)
