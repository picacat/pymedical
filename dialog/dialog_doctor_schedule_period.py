
# 新增醫師班表(班別) 2022.03.04
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils
from libs import string_utils


# 主視窗
class DialogDoctorSchedulePeriod(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogDoctorSchedulePeriod, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.weekday = args[2]
        self.period = args[3]

        self.ui = None

        self._set_ui()
        self._set_signal()

        self._read_schedule()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_DOCTOR_SCHEDULE_PERIOD, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        self.combo_box_list = [
            self.ui.comboBox_room1,
            self.ui.comboBox_room2,
            self.ui.comboBox_room3,
            None,
            self.ui.comboBox_room5,
            self.ui.comboBox_room6,
            self.ui.comboBox_room7,
            self.ui.comboBox_room8,
            self.ui.comboBox_room9,
            self.ui.comboBox_room10,
            self.ui.comboBox_room11,
            self.ui.comboBox_room12,
            self.ui.comboBox_room13,
            None,
            self.ui.comboBox_room15,
            self.ui.comboBox_room16,
            self.ui.comboBox_room17,
            self.ui.comboBox_room18,
            self.ui.comboBox_room19,
            self.ui.comboBox_room20,
        ]
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

        for combo_box in self.combo_box_list:
            if combo_box is None:
                continue

            ui_utils.set_combo_box(combo_box, doctor_list, None)

    def _read_schedule(self):
        sql = f'''
            SELECT Room, {self.weekday} AS Doctor FROM doctor_schedule
            WHERE
                Period = "{self.period}"
            ORDER BY Room
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            room = row['Room']
            if room is None:
                continue

            self.combo_box_list[room-1].setCurrentText(string_utils.xstr(row['Doctor']))

    def accepted_button_clicked(self):
        self._save_doctor_schedule()

    def _save_doctor_schedule(self):
        fields = ['Room', 'Period', self.weekday]

        for i, combo_box in enumerate(self.combo_box_list):
            if combo_box is None:
                continue

            doctor = combo_box.currentText()
            room = i + 1

            sql = f'''
                SELECT * FROM doctor_schedule
                WHERE
                    Room = {room} AND
                    Period = "{self.period}"
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                if doctor != '':
                    data = [room, self.period, doctor]
                    self.database.insert_record('doctor_schedule', fields, data)
            else:
                if doctor != '':
                    doctor = f'"{doctor}"'
                else:
                    doctor = 'NULL'

                self.database.exec_sql(f'''
                    UPDATE doctor_schedule
                    SET
                        {self.weekday} = {doctor}
                    WHERE
                        Room = {room} AND
                        Period = "{self.period}"
                ''')

            sql = f'''
                SELECT * FROM doctor_schedule
                WHERE
                    Room = {room} AND
                    Period = "{self.period}"
            '''
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                row = rows[0]
                doctor_schedule_key = row['DoctorScheduleKey']
                Monday = string_utils.xstr(row['Monday'])
                Tuesday = string_utils.xstr(row['Tuesday'])
                Wednesday = string_utils.xstr(row['Wednesday'])
                Thursday = string_utils.xstr(row['Thursday'])
                Friday = string_utils.xstr(row['Friday'])
                Saturday = string_utils.xstr(row['Saturday'])
                Sunday = string_utils.xstr(row['Sunday'])

                if Monday == '' and \
                   Tuesday == '' and \
                   Wednesday == '' and \
                   Thursday == '' and \
                   Friday == '' and \
                   Saturday == '' and \
                   Sunday == '':
                    self.database.exec_sql(f'''
                        DELETE FROM doctor_schedule
                        WHERE
                            DoctorScheduleKey = {doctor_schedule_key}
                    ''')
