
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils
from libs import nhi_utils
from libs import number_utils
from libs import string_utils


# 主視窗
class DialogDoctorSchedule(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogDoctorSchedule, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.doctor_schedule_key = args[2]
        self.ui = None

        self._set_ui()
        self._set_signal()

        if self.doctor_schedule_key is not None:
            self._set_schedule_item()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_DOCTOR_SCHEDULE, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD, '早班')
        self._set_combo_box_doctor()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def _set_combo_box_doctor(self):
        sql = '''
            SELECT * FROM person
            WHERE
                Position IN ("醫師", "支援醫師")
        '''
        rows = self.database.select_record(sql)
        doctor_list = []
        for row in rows:
            doctor_list.append(row['Name'])

        ui_utils.set_combo_box(self.ui.comboBox_monday, doctor_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_tuesday, doctor_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_wednesday, doctor_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_thursday, doctor_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_friday, doctor_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_saturday, doctor_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_sunday, doctor_list, None)

    def accepted_button_clicked(self):
        self._save_doctor_schedule()

    def _save_doctor_schedule(self):
        fields = [
            'Room', 'Period',
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
        ]

        data = [
            self.ui.spinBox_room.value(),
            self.ui.comboBox_period.currentText(),
            self.ui.comboBox_monday.currentText(),
            self.ui.comboBox_tuesday.currentText(),
            self.ui.comboBox_wednesday.currentText(),
            self.ui.comboBox_thursday.currentText(),
            self.ui.comboBox_friday.currentText(),
            self.ui.comboBox_saturday.currentText(),
            self.ui.comboBox_sunday.currentText(),
        ]

        if self.doctor_schedule_key is None:
            self.database.insert_record('doctor_schedule', fields, data)
        else:
            self.database.update_record(
                'doctor_schedule', fields, 'DoctorScheduleKey',
                self.doctor_schedule_key, data
            )

    def _set_schedule_item(self):
        sql = f'''
            SELECT * FROM doctor_schedule
            WHERE
                DoctorScheduleKey = {self.doctor_schedule_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]

        self.ui.spinBox_room.setValue(number_utils.get_integer(row['Room']))
        self.ui.comboBox_period.setCurrentText(string_utils.xstr(row['Period']))
        self.ui.comboBox_monday.setCurrentText(string_utils.xstr(row['Monday']))
        self.ui.comboBox_tuesday.setCurrentText(string_utils.xstr(row['Tuesday']))
        self.ui.comboBox_wednesday.setCurrentText(string_utils.xstr(row['Wednesday']))
        self.ui.comboBox_thursday.setCurrentText(string_utils.xstr(row['Thursday']))
        self.ui.comboBox_friday.setCurrentText(string_utils.xstr(row['Friday']))
        self.ui.comboBox_saturday.setCurrentText(string_utils.xstr(row['Saturday']))
        self.ui.comboBox_sunday.setCurrentText(string_utils.xstr(row['Sunday']))
