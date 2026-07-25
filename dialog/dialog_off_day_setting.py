
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox, QPushButton
from libs import class_utils

import datetime

from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import nhi_utils
from libs import registration_utils


# 暫停預約設定 2019.10.25
class DialogOffDaySetting(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogOffDaySetting, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.table_name = args[2]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_off_day()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_OFF_DAY_SETTING, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Close).setText('關閉')
        self.ui.dateEdit_off_date.setDate(datetime.datetime.now().date())

        self.table_widget_off_day = class_utils.get_table_widget(
            self.ui.tableWidget_off_day, self.database
        )
        self.table_widget_off_day.set_column_hidden([0])
        self._set_table_width()
        self._set_combo_box()
        if self.table_name == 'massage_off_day_list':
            field_name = '推拿師父'
            self.ui.label_therapist.setText(field_name)
            self.ui.tableWidget_off_day.setHorizontalHeaderLabels(
                ['off_day_key', '暫停預約日期', '班別', field_name, '備註', '刪除']
            )

    def _set_table_width(self):
        width = [100, 130, 60, 120, 260, 60]
        self.table_widget_off_day.set_table_heading_width(width)

    def _set_combo_box(self):
        if self.table_name == 'off_day_list':
            condition = ' Position IN("醫師", "支援醫師") AND ID IS NOT NULL '
        else:
            condition = ' Position IN("推拿師父") '

        sql = f'''
            SELECT * FROM person
            WHERE
                {condition}
        '''
        rows = self.database.select_record(sql)
        doctor_list = []
        for row in rows:
            doctor_list.append(string_utils.xstr(row['Name']))

        ui_utils.set_combo_box(self.ui.comboBox_doctor, doctor_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD)

        period = registration_utils.get_current_period(self.system_settings)
        self.ui.comboBox_period.setCurrentText(period)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.pushButton_insert_off_day.clicked.connect(self._insert_off_day)

    def _read_off_day(self):
        period_list = string_utils.xstr(nhi_utils.PERIOD)[1:-1]
        self.ui.tableWidget_off_day.setRowCount(0)
        sql = f'''
            SELECT * FROM {self.table_name}
            ORDER BY OffDate DESC, FIELD(Period, {period_list})
        '''
        self.table_widget_off_day.set_db_data(sql, self._set_table_data)

    def _get_therapist_field(self):
        if self.table_name == 'off_day_list':
            field = 'Doctor'
        else:
            field = 'Massager'

        return field

    def _set_table_data(self, row_no, row):
        field = self._get_therapist_field()

        therapist = string_utils.xstr(row[field])
        remark = ''
        if therapist in ['', None]:
            remark = '全院暫停預約'

        off_day_row = [
            string_utils.xstr(row['OffDayListKey']),
            string_utils.xstr(row['OffDate']),
            string_utils.xstr(row['Period']),
            therapist,
            remark,
            None,
        ]

        for col_no in range(len(off_day_row)):
            self.ui.tableWidget_off_day.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(off_day_row[col_no])
            )
            if col_no in [2]:
                self.ui.tableWidget_off_day.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

        button = QPushButton(self.ui.tableWidget_off_day)
        button.setIcon(QtGui.QIcon('./icons/cancel.svg'))
        button.setFlat(True)
        button.clicked.connect(self._remove_off_day)
        self.ui.tableWidget_off_day.setCellWidget(row_no, 5, button)

    def _remove_off_day(self):
        off_day_list_key = self.table_widget_off_day.field_value(0)
        if off_day_list_key is None:
            return

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('刪除休診資料')
        msg_box.setText("<font size='4' color='red'><b>確定刪除此暫停預約設定?</b></font>")
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        self.database.exec_sql(f'''
            DELETE FROM {self.table_name}
            WHERE
                OffDayListKey = {off_day_list_key}
        ''')
        self.ui.tableWidget_off_day.removeRow(self.ui.tableWidget_off_day.currentRow())

    def accepted_button_clicked(self):
        self.close()

    def _insert_off_day(self):
        therapist_field = self._get_therapist_field()
        therapist = self.ui.comboBox_doctor.currentText()
        if therapist == '':
            therapist = None

        field = [
            'OffDate', 'Period', therapist_field,
        ]
        data = [
            self.ui.dateEdit_off_date.date().toString('yyyy-MM-dd'),
            self.ui.comboBox_period.currentText(),
            therapist,
        ]

        self.database.insert_record(self.table_name, field, data)
        self._read_off_day()
