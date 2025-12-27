# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils


# 輸入護理師跟診表
class DialogNurseSchedule(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogNurseSchedule, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.schedule_type = args[2]
        self.schedule_date = args[3]
        self.person = args[4]
        self.person1 = args[5]
        self.person2 = args[6]
        self.person3 = args[7]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_NURSE_SCHEDULE, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.lineEdit_schedule_date.setText(self.schedule_date)
        self.ui.lineEdit_person.setText(self.person)
        if self.schedule_type == '醫師':
            self.ui.label_person.setText('主治醫師')
            self.ui.label_person1.setText('早班護理師')
            self.ui.label_person2.setText('午班護理師')
            self.ui.label_person3.setText('晚班護理師')
            self._set_combo_box_nurse()
        else:
            self.ui.label_person.setText('值班護理師')
            self.ui.label_person1.setText('早班醫師')
            self.ui.label_person2.setText('午班醫師')
            self.ui.label_person3.setText('晚班醫師')
            self._set_combo_box_doctor()

        self._set_combo_box()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def _set_combo_box(self):
        self.ui.comboBox_person1.setCurrentText(self.person1)
        self.ui.comboBox_person2.setCurrentText(self.person2)
        self.ui.comboBox_person3.setCurrentText(self.person3)

        if self.schedule_type == '醫師':
            pass
            # self._set_combo_box_person_enabled()

    def _set_combo_box_person_enabled(self):
        nurse_fields = ['Nurse1', 'Nurse2', 'Nurse3']
        person_lables = [self.ui.label_person1, self.ui.label_person2, self.ui.label_person3]
        combo_box_person_list = [
            self.ui.comboBox_person1,
            self.ui.comboBox_person2,
            self.ui.comboBox_person3,
        ]

        for i in range(len(nurse_fields)):
            sql = f'''
                SELECT * FROM nurse_schedule
                WHERE
                    ScheduleDate = "{self.schedule_date}" AND
                    {nurse_fields[i]} IS NOT NULL AND
                    LENGTH({nurse_fields[i]}) > 0 AND
                    Doctor != "{self.person}"
            '''
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                enabled = False
            else:
                enabled = True

            combo_box_person_list[i].setEnabled(enabled)
            person_lables[i].setEnabled(enabled)

    def _set_combo_box_nurse(self):
        script = '''
            SELECT * FROM person
            WHERE
                Position IN ("護士", "護理師")
        '''
        rows = self.database.select_record(script)
        nurse_list = []
        for row in rows:
            nurse_list.append(row['Name'])

        ui_utils.set_combo_box(self.ui.comboBox_person1, nurse_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_person2, nurse_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_person3, nurse_list, None)

    def _set_combo_box_doctor(self):
        script = '''
            SELECT * FROM person
            WHERE
                Position = "醫師" AND
                (ID IS NOT NULL AND LENGTH(ID) > 0)
        '''
        rows = self.database.select_record(script)
        doctor_list = []
        for row in rows:
            doctor_list.append(row['Name'])

        ui_utils.set_combo_box(self.ui.comboBox_person1, doctor_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_person2, doctor_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_person3, doctor_list, None)

    def accepted_button_clicked(self):
        pass
