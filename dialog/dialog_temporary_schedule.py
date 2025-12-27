
# 新增臨時班表 2022.02.09
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime

from libs import system_utils
from libs import ui_utils
from libs import nhi_utils
from libs import personnel_utils


# 主視窗
class DialogTemporarySchedule(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogTemporarySchedule, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.temporary_schedule_key = args[2]
        self.ui = None

        self._set_ui()
        self._set_signal()
        if self.temporary_schedule_key is not None:
            self._set_temporary_schedule()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_TEMPORARY_SCHEDULE, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        self.ui.dateEdit_case_date.setDate(datetime.datetime.now())
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD, '早班')
        ui_utils.set_combo_box(self.ui.comboBox_schedule_type, ['請假', '代班', '加診'], '請假')

        doctor_list = personnel_utils.get_person(self.database, '醫師', None)
        ui_utils.set_combo_box(self.ui.comboBox_doctor, doctor_list)
        ui_utils.set_combo_box(self.ui.comboBox_agent, doctor_list, None)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        if self.temporary_schedule_key is not None:
            self._update_temporary_schedule()
        else:
            self._write_temporary_schedule()

    def _set_temporary_schedule(self):
        sql = f'''
            SELECT * from temporary_schedule
            WHERE
                TemporaryScheduleKey = {self.temporary_schedule_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self.ui.dateEdit_case_date.setDate(row['CaseDate'])
        self.ui.comboBox_schedule_type.setCurrentText(row['ScheduleType'])
        self.ui.spinBox_room.setValue(row['Room'])
        self.ui.comboBox_period.setCurrentText(row['Period'])
        self.ui.comboBox_doctor.setCurrentText(row['Name'])
        self.ui.comboBox_agent.setCurrentText(row['Agent'])
        self.ui.lineEdit_remark.setText(row['Remark'])

    def _write_temporary_schedule(self):
        fields = ['CaseDate', 'ScheduleType', 'Room', 'Period', 'Position', 'Name', 'Agent', 'Remark']

        data = [
            self.ui.dateEdit_case_date.date().toString('yyyy-MM-dd'),
            self.ui.comboBox_schedule_type.currentText(),
            self.ui.spinBox_room.value(),
            self.ui.comboBox_period.currentText(),
            '醫師',
            self.ui.comboBox_doctor.currentText(),
            self.ui.comboBox_agent.currentText(),
            self.ui.lineEdit_remark.text(),
        ]

        self.database.insert_record('temporary_schedule', fields, data)

    def _update_temporary_schedule(self):
        fields = ['CaseDate', 'ScheduleType', 'Room', 'Period', 'Position', 'Name', 'Agent', 'Remark']

        data = [
            self.ui.dateEdit_case_date.date().toString('yyyy-MM-dd'),
            self.ui.comboBox_schedule_type.currentText(),
            self.ui.spinBox_room.value(),
            self.ui.comboBox_period.currentText(),
            '醫師',
            self.ui.comboBox_doctor.currentText(),
            self.ui.comboBox_agent.currentText(),
            self.ui.lineEdit_remark.text(),
        ]

        self.database.update_record(
            'temporary_schedule', fields, 'TemporaryScheduleKey', self.temporary_schedule_key, data)
