# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils


# 輸入藥師跟診表
class DialogPharmacistSchedule(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPharmacistSchedule, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.schedule_date = args[2]
        self.person1 = args[3]
        self.person2 = args[4]
        self.person3 = args[5]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PHARMACIST_SCHEDULE, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.lineEdit_schedule_date.setText(self.schedule_date)
        self._set_combo_box_pharmacist()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def _set_combo_box_pharmacist(self):
        script = '''
            SELECT * FROM person
            WHERE
                Position = "藥師"
        '''
        rows = self.database.select_record(script)
        pharmacist_list = []
        for row in rows:
            pharmacist_list.append(row['Name'])

        ui_utils.set_combo_box(self.ui.comboBox_person1, pharmacist_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_person2, pharmacist_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_person3, pharmacist_list, None)

        self.ui.comboBox_person1.setCurrentText(self.person1)
        self.ui.comboBox_person2.setCurrentText(self.person2)
        self.ui.comboBox_person3.setCurrentText(self.person3)

    def accepted_button_clicked(self):
        pass
