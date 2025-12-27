# -*- coding: utf-8 -*-

import datetime
import json

from PyQt5 import QtChart, QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (case_utils, class_utils, cshis_utils, date_utils,
                  dialog_utils, hainachuan_utils, nhi_utils, number_utils,
                  patient_utils, personnel_utils, printer_utils,
                  registration_utils, statistics_utils, string_utils,
                  system_utils, ui_utils, web_utils)

WAITING_LIST_COL_NO = {
    'WaitKey': 0,
    'CaseKey': 1,
    'InProgress': 2,
    'RegistNo': 3,
    'PatientKey': 4,
    'Name': 5,
    'Gender': 6,
    'Age': 7,
    'Room': 8,
    'ReserveTime': 9,
    'CaseTime': 10,
    'WaitTime': 11,
    'InsType': 12,
    'RegistType': 13,
    'ShareType': 14,
    'TreatType': 15,
    'Visit': 16,
    'Card': 17,
    'Doctor': 18,
    'Remark': 19,
    'Massager': 20,
}

WAIT_DONE_LIST_COL_NO = {
    'WaitKey': 0,
    'CaseKey': 1,
    'Period': 2,
    'RegistTime': 3,
    'DoctorTime': 4,
    'RegistNo': 5,
    'Name': 6,
    'PatientKey': 7,
    'Gender': 8,
    'Age': 9,
    'Room': 10,
    'InsType': 11,
    'RegistType': 12,
    'ShareType': 13,
    'TreatType': 14,
    'Visit': 15,
    'Card': 16,
    'Course': 17,
    'WriteCard': 18,
    'DiseaseName': 19,
    'PresDays': 20,
    'TotalFee': 21,
    'Doctor': 22,
    'Massager': 23,
}

LATE_KEYWROD = '(過號)'


# 候診名單 2018.01.31
class WaitingList(QtWidgets.QMainWindow):
    program_name = '醫師看診作業'

    # 初始化
    def __init__(self, parent=None, *args):
        super(WaitingList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.statistics_dicts = args[2]
        self.ui = None

        self.tab_name = '候診名單'
        self.user_name = system_utils.get_user_name(self.system_settings)
        self.settings = QSettings('__settings.ini', QSettings.IniFormat)
        self.voice_client = class_utils.get_voice_client()
        self.led_port = self.system_settings.field('叫號燈連接埠')
        self.led_ip = self.system_settings.field('叫號燈ip')
        self.led_tcp_port = number_utils.get_integer(self.system_settings.field('叫號燈port'))
        self.ring_bell = self.system_settings.field('叫號燈響鈴')
        self.socket_client = class_utils.get_socket_client()

        self._set_ui()
        self._set_signal()
        self._set_permission()
        self._reset_seq_number()

        # database.read_wait()   # activate by pymedical.py->tab_changed

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_waiting_list(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_WAITING_LIST, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_waiting_list = class_utils.get_table_widget(self.ui.tableWidget_waiting_list, self.database)
        self.table_widget_waiting_list.set_parent(self.parent)
        self.table_widget_waiting_list.set_column_hidden([
            WAITING_LIST_COL_NO['WaitKey'],
            WAITING_LIST_COL_NO['CaseKey'],
        ])
        self.table_widget_reservation_list = class_utils.get_table_widget(
            self.ui.tableWidget_reservation_list, self.database)
        self.table_widget_reservation_list.set_column_hidden([0])
        self.ui.tabWidget_waiting_list.setCurrentIndex(0)

        if self.system_settings.field('醫師候診名單隱藏預約時間') == 'Y':
            self.table_widget_waiting_list.set_column_hidden([
                WAITING_LIST_COL_NO['ReserveTime'],
            ])
        if self.system_settings.field('醫師候診名單隱藏候診時間') == 'Y':
            self.table_widget_waiting_list.set_column_hidden([
                WAITING_LIST_COL_NO['WaitTime']
            ])

        self.table_widget_wait_completed = class_utils.get_table_widget(
            self.ui.tableWidget_wait_completed, self.database
        )
        self.table_widget_wait_completed.set_column_hidden([
            WAIT_DONE_LIST_COL_NO['WaitKey'], WAIT_DONE_LIST_COL_NO['CaseKey']])
        self.table_widget_statistics_list = class_utils.get_table_widget(
            self.ui.tableWidget_statistics_list, self.database)
        self._set_table_width()

        period = registration_utils.get_current_period(self.system_settings)
        self._set_radio_button_period(period)
        ui_utils.set_combo_box(self.ui.comboBox_order_type, ['升冪', '降冪'])
        wait_completed_list_order_type = self.settings.value("wait_completed_list", '升冪')
        self.ui.comboBox_order_type.setCurrentText(wait_completed_list_order_type)

        self._set_tab_widget_corner_widget()
        self._wait_completed_table_item_changed()
        self._set_led_button()

        if self.system_settings.field('預約班表不顯示時間') == 'Y':
            self.table_widget_reservation_list.set_column_hidden([1])

    def reset_tab_widget(self):
        self.ui.tabWidget_waiting_list.setCurrentIndex(0)

    def _get_current_room(self):
        default_room = personnel_utils.get_person_field_value(self.database, self.user_name, 'Room')

        sql = f'''
            SELECT Room FROM wait
            WHERE
                Doctor = "{self.user_name}"
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            room = default_room
        else:
            room = rows[0]['Room']

        return room

    def _get_seq_number(self):
        room = self._get_current_room()
        if room in ['', None]:
            return 0

        sql = f'''
            SELECT SeqNumber FROM seq_number
            WHERE
                Room = {room}
        '''
        try:
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                seq_number = 0
            else:
                seq_number = number_utils.get_integer(rows[0]['SeqNumber'])
        except Exception:
            seq_number = 0

        return seq_number

    def _set_tab_widget_corner_widget(self):
        self.ui.tabWidget_waiting_list.setCornerWidget(None)

        tab_corner_widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout(tab_corner_widget)
        h_layout.setContentsMargins(4, 4, 4, 4)
        h_layout.setSpacing(8)

        self._set_doctor_corner_widget(tab_corner_widget, h_layout)

        if number_utils.get_integer(self.led_port) > 0 or self.led_ip not in [None, '']:  # 春暉有叫號燈也有海納川，以叫號燈為主
            self._set_calling_bulletin_led(tab_corner_widget, h_layout)
        if self.system_settings.field('hainachuan') == 'Y' or self.system_settings.field('線上看診號同步') == 'Y':
            self._set_hainachuan_corner_widget(tab_corner_widget, h_layout)

        self.ui.tabWidget_waiting_list.setCornerWidget(tab_corner_widget, QtCore.Qt.TopRightCorner)

    def _set_doctor_corner_widget(self, tab_corner_widget, h_layout):
        self.combo_box_doctor = None
        position = personnel_utils.get_person_field_value(self.database, self.user_name, 'Position')
        if position not in ['醫師', '支援醫師']:
            return

        label = QtWidgets.QLabel(tab_corner_widget)
        label.setText('主治醫師')

        self.combo_box_doctor = QtWidgets.QComboBox()
        self.combo_box_doctor.currentTextChanged.connect(self._refresh_tab_widget)

        self._set_combo_box_doctor()

        h_layout.addWidget(label)
        h_layout.addWidget(self.combo_box_doctor)

    def _set_hainachuan_corner_widget(self, tab_corner_widget, h_layout):
        label = QtWidgets.QLabel(tab_corner_widget)
        label.setText('自訂目前看診號')
        h_layout.addWidget(label)

        self.spinBox_seq_number = QtWidgets.QSpinBox(tab_corner_widget)  # 自訂看診號
        self.spinBox_seq_number.setMaximum(999)

        seq_number = self._get_seq_number()
        self.spinBox_seq_number.setValue(seq_number)

         # 設置防抖機制
        self._seq_number_update_timer = QtCore.QTimer()
        self._seq_number_update_timer.setInterval(2000)  # 2秒
        self._seq_number_update_timer.setSingleShot(True)
        self._seq_number_update_timer.timeout.connect(self._seq_number_value_changed)  # 確保只連接一次
        self.spinBox_seq_number.valueChanged.connect(self._start_debounce_seq_number_update)

        h_layout.addWidget(self.spinBox_seq_number)

    def _start_debounce_seq_number_update(self):
        """
        當 spinBox 值改變時，啟動或重置防抖計時器。
        """
        self._seq_number_update_timer.start()

    def _set_calling_bulletin_led(self, tab_corner_widget, h_layout):
        label = QtWidgets.QLabel(tab_corner_widget)
        label.setText('自訂叫號燈號')
        h_layout.addWidget(label)

        self.spinBox_led_number = QtWidgets.QSpinBox(tab_corner_widget)  # 自訂叫號燈號
        self.spinBox_led_number.setMaximum(999)

        seq_number = self._get_seq_number()
        self.spinBox_led_number.setValue(seq_number)
        self.spinBox_led_number.setAlignment(QtCore.Qt.AlignRight)

        # 設置防抖機制
        self._led_number_update_timer = QtCore.QTimer()
        self._led_number_update_timer.setInterval(2000)  # 2秒
        self._led_number_update_timer.setSingleShot(True)
        self._led_number_update_timer.timeout.connect(self._led_number_value_changed)  # 確保只連接一次
        self.spinBox_led_number.valueChanged.connect(self._start_debounce_led_number_update)

        h_layout.addWidget(self.spinBox_led_number)

    def _start_debounce_led_number_update(self):
        """
        當 spinBox 值改變時，啟動或重置防抖計時器。
        """
        self._led_number_update_timer.start()

    def _led_number_value_changed(self):
        room = self._get_current_room()
        if room in ['', None]:
            room = 1

        seq_number = self.spinBox_led_number.value()

        sql = f'SELECT SeqNumber FROM seq_number WHERE room = {room}'
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            today = datetime.datetime.today().strftime('%Y-%m-%d')
            fields = ['CaseDate', 'Room', 'SeqNumber']
            data = [today, room, seq_number]
            self.database.insert_record('seq_number', fields, data)
        else:
            sql = f'''
                UPDATE seq_number
                SET
                    SeqNumber = {seq_number}
                WHERE
                    Room = {room}
            '''
            self.database.exec_sql(sql)

        self._start_flashing(self.spinBox_led_number)

    def _seq_number_value_changed(self):
        room = self._get_current_room()
        if room in ['', None]:
            room = 1

        seq_number = self.spinBox_seq_number.value()

        sql = f'SELECT SeqNumber FROM seq_number WHERE room = {room}'
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            today = datetime.datetime.today().strftime('%Y-%m-%d')
            fields = ['CaseDate', 'Room', 'SeqNumber']
            data = [today, room, seq_number]
            self.database.insert_record('seq_number', fields, data)
        else:
            sql = f'''
                UPDATE seq_number
                SET
                    SeqNumber = {seq_number}
                WHERE
                    Room = {room}
            '''
            self.database.exec_sql(sql)

        self._start_flashing(self.spinBox_seq_number)

        if self.system_settings.field('hainachuan') == 'Y':
            hainachuan_utils.send_seq_number(
                system_settings=self.system_settings,
                seq_number=seq_number,
                room=room,
                doctor=self.user_name,
            )

        self.voice_client.send_data('refresh_wait')
        self._refresh_waiting_list_color()

    def _refresh_waiting_list_color(self):
        current_seq_number = self.ui.spinBox_seq_number.value()
        if current_seq_number == 0:
            return

        for row_no in range(self.ui.tableWidget_waiting_list.rowCount()):
            item = self.ui.tableWidget_waiting_list.item(row_no, WAITING_LIST_COL_NO['RegistNo'])
            if item is None:
                continue

            color = self._get_waiting_list_font_color(row_no)
            for col_no in range(self.ui.tableWidget_waiting_list.columnCount()):
                self.ui.tableWidget_waiting_list.item(row_no, col_no).setForeground(color)

    def _set_combo_box_doctor(self):
        tab_name = self.ui.tabWidget_waiting_list.tabText(self.ui.tabWidget_waiting_list.currentIndex())
        if tab_name == '候診名單':
            doctor_done = "False"
        else:
            doctor_done = "True"

        sql = f'''
            SELECT Doctor FROM wait
            WHERE
                Doctor IS NOT NULL AND LENGTH(Doctor) > 0
            GROUP BY Doctor
            ORDER BY Room
        '''
        rows = self.database.select_record(sql)
        doctor_list = []
        for row in rows:
            doctor_list.append(string_utils.xstr(row['Doctor']))

        if self.user_name not in doctor_list:
            doctor_list.append(self.user_name)

        ui_utils.set_combo_box(self.combo_box_doctor, doctor_list, '全部')
        if self.system_settings.field('候診名單顯示診別') == '所有診別':
            self.combo_box_doctor.setCurrentText('全部')
        else:
            self.combo_box_doctor.setCurrentText(self.user_name)

    def _refresh_tab_widget(self):
        self.tab_name = self.ui.tabWidget_waiting_list.tabText(
            self.ui.tabWidget_waiting_list.currentIndex()
        )

        if self.tab_name == '候診名單':
            self.read_wait()
        else:
            self._read_wait_completed()

    def _set_radio_button_period(self, period):
        # if period == '早班':
        #     self.ui.radioButton_period1.setChecked(True)
        # elif period == '午班':
        #     self.ui.radioButton_period2.setChecked(True)
        # elif period == '晚班':
        #     self.ui.radioButton_period3.setChecked(True)

        self.ui.radioButton_all.setChecked(True)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_waiting_list.doubleClicked.connect(self.open_medical_record)
        self.ui.tableWidget_wait_completed.doubleClicked.connect(self.open_medical_record)
        self.ui.tabWidget_waiting_list.currentChanged.connect(self._waiting_list_tab_changed)   # 切換分頁
        self.ui.action_medical_record.triggered.connect(self.open_medical_record)
        self.ui.action_refresh_list.triggered.connect(self._refresh_tab_widget)
        self.ui.action_close.triggered.connect(self.close_waiting_list)
        self.ui.action_med_vpn.triggered.connect(self._open_med_vpn)
        self.ui.action_speech.triggered.connect(self._speech_arrival)
        self.ui.action_broadcast_voice.triggered.connect(lambda: self.send_voice_data())
        self.ui.action_broadcast_led.triggered.connect(lambda: self._send_led(custom=False))
        self.ui.action_custom_broadcast_led.triggered.connect(lambda: self._send_led(custom=True))
        self.ui.tableWidget_reservation_list.itemSelectionChanged.connect(self._show_last_medical_record)
        self.ui.toolButton_print_prescript.clicked.connect(lambda: self._print_prescript('選擇列印'))
        self.ui.toolButton_print_receipt.clicked.connect(lambda: self._print_receipt('選擇列印'))
        self.ui.toolButton_print_misc.clicked.connect(lambda: self._print_misc('選擇列印'))
        self.ui.toolButton_print_all.clicked.connect(self._print_all)
        self.ui.toolButton_unset_wait.clicked.connect(self._unset_wait_done)
        self.ui.toolButton_write_ic_card.clicked.connect(self._write_ic_treatment)
        self.ui.toolButton_rewrite_ic_card.clicked.connect(self._rewrite_ic_card)
        self.ui.toolButton_rewrite_ic_prescript.clicked.connect(self._rewrite_ic_prescript)
        self.ui.toolButton_extra_purchase.clicked.connect(self._extra_purchase)
        self.ui.action_set_late.triggered.connect(self._set_late)
        self.ui.action_cancel_late.triggered.connect(self._cancel_late)

        self.ui.action_change_ins_type.triggered.connect(self._change_ins_type)

        self.ui.tableWidget_waiting_list.keyPressEvent = self._table_widget_waiting_list_key_press
        self.ui.tableWidget_wait_completed.itemSelectionChanged.connect(
            self._wait_completed_table_item_changed
        )
        self.ui.tableWidget_waiting_list.itemSelectionChanged.connect(
            self._waiting_list_item_changed
        )

        self.ui.radioButton_all.clicked.connect(self._read_wait_completed)
        self.ui.radioButton_period1.clicked.connect(self._read_wait_completed)
        self.ui.radioButton_period2.clicked.connect(self._read_wait_completed)
        self.ui.radioButton_period3.clicked.connect(self._read_wait_completed)
        self.ui.comboBox_order_type.currentTextChanged.connect(self._combo_box_order_type_changed)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(self.database, self.program_name, '病歷登錄', self.user_name) != 'Y':
            self.ui.action_medical_record.setEnabled(False)
            # self.ui.action_speech.setEnabled(False)
            # self.ui.action_broadcast_voice.setEnabled(False)
            # self.ui.action_broadcast_led.setEnabled(False)
            self.ui.action_set_late.setEnabled(False)
            self.ui.action_cancel_late.setEnabled(False)

        if personnel_utils.get_permission(self.database, self.program_name, '非醫師病歷登錄', self.user_name) == 'Y':
            self.ui.action_medical_record.setEnabled(True)
            # self.ui.action_speech.setEnabled(True)
            # self.ui.action_broadcast_voice.setEnabled(True)
            # self.ui.action_broadcast_led.setEnabled(True)
            self.ui.action_set_late.setEnabled(True)
            self.ui.action_cancel_late.setEnabled(True)

    def _reset_seq_number(self):
        today = datetime.datetime.today().strftime('%Y-%m-%d')
        sql = f'''
            DELETE FROM seq_number
            WHERE
                CaseDate != "{today}"
        '''
        self.database.exec_sql(sql)

    def _set_table_width(self):
        if self.system_settings.field('醫師候診名單欄位固定寬度') == 'Y':
            width = [
                100, 100,
                45, 45, 80, 100, 45, 85, 45, 60, 60, 70, 50, 90,
                90, 90, 65, 90, 80, 220, 80]
            self.table_widget_waiting_list.set_table_heading_width(width)

        # width = [100, 100,
        #          45, 45, 80, 80, 45, 40, 45, 50, 50, 50, 90,
        #          60, 70, 45, 45, 130, 45, 60, 80, 80]
        # self.table_widget_wait_completed.set_table_heading_width(width)

        # width = [230, 70]
        # self.table_widget_statistics_list.set_table_heading_width(width)

    def _get_room_script(self, table_name, doctor=None):
        if self.system_settings.field('候診名單顯示診別') == '指定診別':
            room_no = self.system_settings.field('診療室')
            room = f'AND ({table_name}.Room = {room_no} OR {table_name}.Doctor = "全部醫師")'
        elif self.system_settings.field('候診名單顯示診別') == '醫師診別' and doctor != '全部':
            if doctor is None:
                doctor = self.user_name

            room = f'AND ({table_name}.Doctor = "{doctor}" OR {table_name}.Doctor = "全部醫師")'
        else:
            if doctor in ['全部', None]:
                room = ''  # 預設顯示診別為全部
            else:
                room = f'AND ({table_name}.Doctor = "{doctor}")'                

        return room

    def read_wait(self):
        if self.combo_box_doctor is not None:
            doctor = self.combo_box_doctor.currentText()
        else:
            if self.system_settings.field('候診名單顯示診別') == '所有診別':
                doctor = '全部'
            else:
                doctor = self.user_name                
            
        order_script = self._get_order_script('wait')
        room_script = self._get_room_script('wait', doctor=doctor)

        sql = f'''
            SELECT wait.*, patient.Gender, patient.Birthday FROM wait
                LEFT JOIN patient ON wait.PatientKey = patient.PatientKey
            WHERE
                DoctorDone = "False"
                {room_script}
                {order_script}
        '''
        self.table_widget_waiting_list.set_db_data(sql, self._set_table_data)

        row_count = self.table_widget_waiting_list.row_count()
        if row_count > 0:
            self._set_tool_button(True)
        else:
            self._set_tool_button(False)

        self._read_reservation(doctor)
        self._set_statistics_list(doctor)
        self._display_waiting_message()

        self.ui.tableWidget_waiting_list.setFocus()

    def _display_waiting_message(self):
        ins_count = 0
        for row_no in range(self.ui.tableWidget_waiting_list.rowCount()):
            item = self.ui.tableWidget_waiting_list.item(row_no, WAITING_LIST_COL_NO['InsType'])
            if item is None:
                continue

            ins_type = item.text()
            if ins_type in ['健保']:
                ins_count += 1

        reserve_count = 0
        # current_period = registration_utils.get_current_period(self.system_settings)
        for row_no in range(self.ui.tableWidget_reservation_list.rowCount()):
            # item = self.ui.tableWidget_reservation_list.item(row_no, 1)
            # if item is None:
            #     continue

            # period = item.text()
            # if period == current_period:
            #     reserve_count += 1

            reserve_count += 1

        self.ui.label_waiting_message.setText(f'目前候診人數: 健保 {ins_count} 人, 預約未報到 {reserve_count} 人')

    def _set_tool_button(self, enabled):
        self.ui.action_medical_record.setEnabled(enabled)
        self.ui.action_speech.setEnabled(enabled)
        self.ui.action_broadcast_voice.setEnabled(enabled)
        self.ui.action_set_late.setEnabled(enabled)
        self.ui.action_cancel_late.setEnabled(enabled)
        self._set_permission()
        self._set_led_button(enabled)

    def _set_led_button(self, enabled=False):
        if number_utils.get_integer(self.led_port) == 0 and self.led_ip in [None, '']:
            self.ui.action_broadcast_led.setEnabled(False)
            self.ui.action_custom_broadcast_led.setEnabled(False)
            return

        self.ui.action_broadcast_led.setEnabled(enabled)
        self.ui.action_custom_broadcast_led.setEnabled(enabled)

    def _get_reservation_time(self, patient_key, doctor):
        sql = f'''
            SELECT ReserveDate FROM reserve
            WHERE
                PatientKey = {patient_key} AND
                DATE(ReserveDate) = "{datetime.datetime.now().strftime("%Y-%m-%d")}" AND
                Doctor = "{doctor}"
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]
        reservation_time = row['ReserveDate'].strftime('%H:%M')

        return reservation_time

    def _set_table_data(self, row_no, row):
        patient_key = row['PatientKey']
        registration_time = row['CaseDate'].strftime('%H:%M')
        doctor = string_utils.xstr(row['Doctor'])
        ins_type = string_utils.xstr(row['InsType'])
        share_type = string_utils.xstr(row['Share'])[:2]
        regist_type = string_utils.xstr(row['RegistType'])[:4]
        treat_type = string_utils.xstr(row['TreatType'])[:10]
        card = string_utils.xstr(row['Card'])
        continuance = number_utils.get_integer(row['Continuance'])
        regist_no = number_utils.get_integer(row['RegistNo'])
        if continuance >= 1:
            card = f'{card}-{continuance}'

        try:
            reservation_time = self._get_reservation_time(patient_key, doctor)
        except Exception:
            reservation_time = None

        now = datetime.datetime.now()
        case_date = row['CaseDate']
        if now > case_date:
            time_delta = now - case_date
        else:
            time_delta = case_date - now

        wait_seconds = datetime.timedelta(seconds=time_delta.total_seconds()).seconds
        wait_minutes = wait_seconds // 60
        wait_time = f'{wait_minutes}分'

        age_year, age_month = date_utils.get_age(row['Birthday'], row['CaseDate'])
        if age_year is None:
            age = 'N/A'
        else:
            age = f'{age_year}歲{age_month}月'

        wait_row = [
            string_utils.xstr(row['WaitKey']),
            string_utils.xstr(row['CaseKey']),
            None,
            regist_no,
            patient_key,
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Gender']),
            age_year,
            row['Room'],
            reservation_time,
            registration_time,
            wait_time,
            ins_type,
            regist_type,
            share_type,
            treat_type,
            string_utils.xstr(row['Visit']),
            card,
            doctor,
            string_utils.xstr(row['Remark']),
            string_utils.xstr(row['Massager']),
        ]

        in_progress = string_utils.xstr(row['InProgress'])
        case_utils.set_in_progress_icon(
            self.ui.tableWidget_waiting_list,
            row_no, WAITING_LIST_COL_NO['InProgress'], in_progress
        )

        for col_no in range(len(wait_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, wait_row[col_no])
            self.ui.tableWidget_waiting_list.setItem(
                row_no, col_no, item,
            )
            if col_no in [WAITING_LIST_COL_NO['PatientKey'],
                          WAITING_LIST_COL_NO['Age'],
                          WAITING_LIST_COL_NO['Room'],
                          WAITING_LIST_COL_NO['RegistNo'],
                          WAITING_LIST_COL_NO['WaitTime']]:
                self.ui.tableWidget_waiting_list.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [WAITING_LIST_COL_NO['Gender'], WAITING_LIST_COL_NO['Visit']]:
                self.ui.tableWidget_waiting_list.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

        color = self._get_waiting_list_font_color(row_no)
        for col_no in range(self.ui.tableWidget_waiting_list.columnCount()):
            self.ui.tableWidget_waiting_list.item(row_no, col_no).setForeground(color)

        if regist_type == '預約門診':
            for col_no in range(self.ui.tableWidget_waiting_list.columnCount()):
                self.ui.tableWidget_waiting_list.item(row_no, col_no).setForeground(QtGui.QColor('purple'))

    def _get_waiting_list_font_color(self, row_no):
        color = QtGui.QColor('black')
        try:
            current_seq_number = self.ui.spinBox_seq_number.value()
        except Exception:
            try:
                current_seq_number = self.ui.spinBox_led_number.value()
            except Exception:
                current_seq_number = 0

        ins_type = self.ui.tableWidget_waiting_list.item(row_no, WAITING_LIST_COL_NO['InsType']).text()
        try:
            course = self.ui.tableWidget_waiting_list.item(row_no, WAITING_LIST_COL_NO['Card']).text().split('-')[1]
            course = number_utils.get_integer(course)
        except Exception:
            course = 0

        regist_no = number_utils.get_integer(
            self.ui.tableWidget_waiting_list.item(row_no, WAITING_LIST_COL_NO['RegistNo']).text())

        in_progress = self.ui.tableWidget_waiting_list.cellWidget(row_no, WAITING_LIST_COL_NO['InProgress'])

        if in_progress is not None:
            color = QtGui.QColor('red')
        elif ins_type == '自費':
            color = QtGui.QColor('blue')
        elif course >= 2:
            color = QtGui.QColor('darkGreen')

        if 0 < regist_no < current_seq_number:
            color = QtGui.QColor('red')

        return color

    def open_medical_record(self):
        if (self.user_name != '超級使用者' and
                personnel_utils.get_permission(
                    self.database, self.program_name, '病歷登錄', self.user_name) != 'Y' and
                personnel_utils.get_permission(
                    self.database, self.program_name, '非醫師病歷登錄', self.user_name) != 'Y'):
            return

        self.tab_name = self.ui.tabWidget_waiting_list.tabText(
            self.ui.tabWidget_waiting_list.currentIndex()
        )

        if self.tab_name == '候診名單':
            case_key = self.table_widget_waiting_list.field_value(WAITING_LIST_COL_NO['CaseKey'])
            call_from = '醫師看診作業'
        else:
            case_key = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['CaseKey'])
            call_from = '醫師看診作業-查詢'

        self.parent.open_medical_record(case_key, call_from, self.user_name)

    def _read_reservation(self, doctor=None):
        start_date = datetime.datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.datetime.now().strftime('%Y-%m-%d 23:59:59')

        room_script = self._get_room_script('reserve', doctor=doctor)

        period_script = ''
        if self.system_settings.field('醫師候診名單只顯示當班預約資料') == 'Y':
            current_period = registration_utils.get_current_period(self.system_settings)
            period_script = f' AND reserve.Period = "{current_period}"'

        period_list = str(nhi_utils.PERIOD)[1:-1]
        sql = f'''
            SELECT
                reserve.*,
                patient.Birthday, patient.Gender, patient.Cellphone, patient.Telephone
            FROM reserve
                LEFT JOIN patient ON patient.PatientKey = reserve.PatientKey
            WHERE
                ReserveDate BETWEEN "{start_date}" AND "{end_date}" AND
                reserve.Name NOT IN ("保留預約", "不預約") AND
                Arrival = "False"
                {room_script}
                {period_script}
            ORDER BY FIELD(Period, {period_list}), ReserveNo
        '''
        self.table_widget_reservation_list.set_db_data(sql, self._set_reservation_data)
        self._show_last_medical_record()
        if self.ui.tableWidget_reservation_list.rowCount() > 0:
            self.ui.groupBox_reserve.setVisible(True)
        else:
            self.ui.groupBox_reserve.setVisible(False)

    def _set_reservation_data(self, row_no, row):
        reserve_key = string_utils.xstr(row['ReserveKey'])
        reserve_date = string_utils.xstr(row['ReserveDate'].time().strftime('%H:%M'))
        period = string_utils.xstr(row['Period'])
        room = row['Room']
        reserve_no = row['ReserveNo']
        patient_key = row['PatientKey']
        name = string_utils.xstr(row['Name'])
        gender = string_utils.xstr(row['Gender'])

        if string_utils.xstr(row['Cellphone']) != '':
            phone = string_utils.xstr(row['Cellphone'])
        else:
            phone = string_utils.xstr(row['Telephone'])

        if personnel_utils.get_permission(self.database, '病患資料', '遮蔽電話地址', self.user_name) == 'Y':
            phone = '*' * len(phone)

        source = string_utils.xstr(row['Source'])
        if source in ['初診預約', '網路初診預約', '視訊初診預約']:
            sql = f'''
                SELECT * FROM temp_patient
                WHERE
                    TempPatientKey = {patient_key}
            '''
            rows = self.database.select_record(sql)
            gender = ''
            if len(rows) > 0:
                row = rows[0]
                id = string_utils.xstr(row['ID'])
                if id != '':
                    try:
                        gender = patient_utils.get_gender(id[1])
                    except Exception:
                        pass

            patient_key = source

        age_year, age_month = date_utils.get_age(
            row['Birthday'], datetime.datetime.now())
        if age_year is None:
            age = ''
        else:
            age = f'{age_year}歲'

        reservation_row = [
            reserve_key,
            reserve_date,
            period,
            room,
            reserve_no,
            patient_key,
            name,
            gender,
            age,
            phone,
        ]

        for col_no in range(len(reservation_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, reservation_row[col_no])
            self.ui.tableWidget_reservation_list.setItem(
                row_no, col_no, item,
            )

            if col_no in [3, 4, 5]:
                self.ui.tableWidget_reservation_list.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [1, 2, 7, 8]:
                self.ui.tableWidget_reservation_list.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if patient_key == '網路初診':
                self.ui.tableWidget_reservation_list.item(
                    row_no, col_no).setForeground(
                    QtGui.QColor('green')
                )

    def _show_last_medical_record(self):
        self.ui.textEdit_medical_record.setHtml(None)
        self.ui.label_reserve_chart.setText('上次病歷摘要')

        try:
            patient_key = self.table_widget_reservation_list.field_value(5)
            if patient_key in [None, '', 0, '初診預約', '網路初診']:
                return

            name = self.table_widget_reservation_list.field_value(6)
            self.ui.label_reserve_chart.setText(f'{name}上次病歷摘要')

            sql = f'''
                SELECT * FROM cases
                WHERE
                    PatientKey = {patient_key}
                ORDER BY CaseDate DESC LIMIT 1
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                self.ui.textEdit_medical_record.setHtml(
                    '<br><br><br><center>無過去病歷</center>'
                )

                return

            case_key = rows[0]['CaseKey']
            if case_key is None:
                return

            html = case_utils.get_medical_record_html(self.database, self.system_settings, case_key)
            self.ui.textEdit_medical_record.setHtml(html)
        except Exception:
            pass

    def _waiting_list_tab_changed(self, i):
        self.tab_name = self.ui.tabWidget_waiting_list.tabText(i)

        if self.tab_name == '候診名單':
            self.read_wait()
            self.ui.action_set_late.setEnabled(True)
            self.ui.action_cancel_late.setEnabled(True)
            self.ui.action_change_ins_type.setEnabled(True)
        else:
            self._read_wait_completed()
            self.ui.action_set_late.setEnabled(False)
            self.ui.action_cancel_late.setEnabled(False)
            self.ui.action_change_ins_type.setEnabled(False)

    def _get_period_script(self, table_name):
        period_script = ''

        if self.ui.radioButton_period1.isChecked():
            period_script = f' AND {table_name}.Period = "早班" '
        elif self.ui.radioButton_period2.isChecked():
            period_script = f' AND {table_name}.Period = "午班" '
        elif self.ui.radioButton_period3.isChecked():
            period_script = f' AND {table_name}.Period = "晚班" '

        return period_script

    def _get_order_script(self, table_name, descending=False):
        # period_list = str(nhi_utils.PERIOD)[1:-1]
        if descending:
            # order_script = f'ORDER BY FIELD({table_name}.Period, "晚班", "午班", "早班"), {table_name}.RegistNo'  # 預設為診號排序
            order_script = f'ORDER BY {table_name}.RegistNo'  # 預設為診號排序
        else:
            # order_script = f'ORDER BY FIELD({table_name}.Period, {period_list}), {table_name}.RegistNo'  # 預設為診號排序
            order_script = f'ORDER BY {table_name}.RegistNo'  # 預設為診號排序

        if self.system_settings.field('看診排序') == '時間排序':
            order_script = f'ORDER BY {table_name}.CaseDate'

        if descending:
            order_script += ' DESC'

        return order_script

    def _combo_box_order_type_changed(self):
        self.settings.setValue("wait_completed_list", self.ui.comboBox_order_type.currentText())
        self._read_wait_completed()

    def _read_wait_completed(self):
        if self.combo_box_doctor is not None:
            doctor = self.combo_box_doctor.currentText()
        else:
            if self.system_settings.field('候診名單顯示診別') == '所有診別':
                doctor = '全部'
            else:
                doctor = self.user_name

        if self.ui.comboBox_order_type.currentText() == '降冪':
            descending = True
        else:
            descending = False

        order_script = self._get_order_script('cases', descending=descending)
        room_script = self._get_room_script('cases', doctor=doctor)
        period_script = self._get_period_script('cases')

        sql = f'''
            SELECT wait.*, patient.Gender, patient.Birthday, cases.* FROM wait
                LEFT JOIN patient ON wait.PatientKey = patient.PatientKey
                LEFT JOIN cases ON wait.CaseKey = cases.CaseKey
            WHERE
                cases.DoctorDone = "True"
                {period_script}
                {room_script}
                {order_script}
        '''
        self.table_widget_wait_completed.set_db_data(sql, self._set_wait_completed_data)

    def _read_wait_completed_by_case_key(self, case_key):
        if self.combo_box_doctor is not None:
            doctor = self.combo_box_doctor.currentText()
        else:
            doctor = self.user_name

        if self.ui.comboBox_order_type.currentText() == '降冪':
            descending = True
        else:
            descending = False

        order_script = self._get_order_script('cases', descending=descending)
        room_script = self._get_room_script('cases', doctor=doctor)
        period_script = self._get_period_script('cases')
        case_key_script = f' AND wait.CaseKey = {case_key}'

        sql = f'''
            SELECT wait.*, patient.Gender, patient.Birthday, cases.* FROM wait
                LEFT JOIN patient ON wait.PatientKey = patient.PatientKey
                LEFT JOIN cases ON wait.CaseKey = cases.CaseKey
            WHERE
                cases.DoctorDone = "True" AND
                cases.TreatType != "自購"
                {case_key_script}
                {period_script}
                {room_script}
                {order_script}
        '''

        return sql

    def _set_wait_completed_data(self, row_no, row):
        signature = case_utils.extract_security_xml(row['Security'], '醫令時間')
        ins_type = string_utils.xstr(row['InsType'])
        card = string_utils.xstr(row['Card'])[:4]
        course = number_utils.get_integer(row['Continuance'])
        xcard = string_utils.xstr(row['XCard'])

        if ins_type != '健保' or card == '欠卡' or card in nhi_utils.ABNORMAL_CARD or xcard in nhi_utils.ABNORMAL_CARD:
            ic_wrote = '略'
        elif signature is None:
            ic_wrote = '否'
        else:
            ic_wrote = '是'

        pres_days = case_utils.get_pres_days(self.database, row['CaseKey'])

        age_year, age_month = date_utils.get_age(row['Birthday'], row['CaseDate'])
        if age_year is None:
            age = 'N/A'
        else:
            age = f'{age_year}'

        disease_name = string_utils.xstr(row['DiseaseName1'])
        if disease_name != '':
            disease_name = disease_name[:8]  # 只取前8個字元

        total_fee = number_utils.get_integer(row['TotalFee'])
        regist_time = row['CaseDate'].strftime('%H:%M')
        try:
            done_time = row['DoctorDate'].strftime('%H:%M')
        except Exception:
            done_time = ''

        wait_row = [
            string_utils.xstr(row['WaitKey']),
            string_utils.xstr(row['CaseKey']),
            row['Period'],
            regist_time,
            done_time,
            row['RegistNo'],
            string_utils.xstr(row['Name']),
            row['PatientKey'],
            string_utils.xstr(row['Gender']),
            age,
            row['Room'],
            ins_type,
            string_utils.xstr(row['RegistType'])[:2],
            string_utils.xstr(row['Share'])[:2],
            string_utils.xstr(row['TreatType']),
            string_utils.xstr(row['Visit']),
            card,
            row['Continuance'],
            ic_wrote,
            disease_name,
            pres_days,
            total_fee,
            string_utils.xstr(row['Doctor']),
            string_utils.xstr(row['Massager']),
        ]

        for col_no in range(len(wait_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, wait_row[col_no])
            self.ui.tableWidget_wait_completed.setItem(
                row_no, col_no, item,
            )
            if col_no in [
                WAIT_DONE_LIST_COL_NO['RegistNo'],
                WAIT_DONE_LIST_COL_NO['PatientKey'],
                WAIT_DONE_LIST_COL_NO['Age'],
                WAIT_DONE_LIST_COL_NO['PresDays'],
                WAIT_DONE_LIST_COL_NO['TotalFee'],
            ]:
                self.ui.tableWidget_wait_completed.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [
                WAIT_DONE_LIST_COL_NO['Period'],
                WAIT_DONE_LIST_COL_NO['RegistTime'],
                WAIT_DONE_LIST_COL_NO['Gender'],
                WAIT_DONE_LIST_COL_NO['Room'],
                WAIT_DONE_LIST_COL_NO['InsType'],
                WAIT_DONE_LIST_COL_NO['RegistType'],
                WAIT_DONE_LIST_COL_NO['ShareType'],
                WAIT_DONE_LIST_COL_NO['Visit'],
                WAIT_DONE_LIST_COL_NO['Card'],
                WAIT_DONE_LIST_COL_NO['Course'],
                WAIT_DONE_LIST_COL_NO['WriteCard'],
            ]:
                self.ui.tableWidget_wait_completed.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if ins_type == '自費' or total_fee > 0:
                self.ui.tableWidget_wait_completed.item(
                    row_no, col_no).setForeground(
                    QtGui.QColor('blue')
                )
            elif course >= 2:
                self.ui.tableWidget_wait_completed.item(
                    row_no, col_no).setForeground(
                    QtGui.QColor('darkGreen')
                )

    def _set_statistics_list(self, doctor=None):
        if doctor is None:
            doctor = self.user_name

        statistics_list = dict()

        statistics_list['本日健保已就診人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'wait', '當日', ['全部'], doctor,
        )
        statistics_list['本日健保內科人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'wait', '當日', ['內科', '一般'], doctor,
        )
        statistics_list['本日健保針灸人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'wait', '當日', nhi_utils.ACUPUNCTURE_TREAT, doctor,
        )
        statistics_list['本日健保傷科人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'wait', '當日', nhi_utils.MASSAGE_TREAT + nhi_utils.DISLOCATE_TREAT, doctor,
        )

        statistics_list['本日健保中度複針人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'wait', '當日',
            nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST,
            doctor,
        )
        statistics_list['本日健保高度複針人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'wait', '當日',
            nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST,
            doctor,
        )
        statistics_list['本日健保針傷合併人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'wait', '當日', nhi_utils.MERGE_TREAT_LIST, doctor,
        )
        statistics_list['本日健保中度複傷人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'wait', '當日',
            nhi_utils.MODERATE_COMPLICATED_MASSAGE_TREAT + nhi_utils.MODERATE_COMPLICATED_MASSAGE_TREAT,
            doctor,
        )
        statistics_list['本日健保高度複傷人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'wait', '當日',
            nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT, doctor,
        )
        statistics_list['本日健保脫臼整復人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'wait', '當日', ['脫臼整復復位', '脫臼整復復位'], doctor,
        )
        # statistics_list['本日健保骨折復位人數'] = statistics_utils.get_count_by_treat_type(
        #     self.database, 'wait', '當日', ['骨折復位', '骨折復位'], doctor,
        # )
        if self.system_settings.field('統計針傷給藥人數') == 'Y':
            statistics_list['本日健保針傷給藥人數'] = statistics_utils.get_treat_drug_count(
                self.database, '當日', doctor,
            )

        statistics_list['本月健保內科人數'] = self.statistics_dicts['本月健保內科人數'] + \
            statistics_list['本日健保內科人數']
        statistics_list['本月健保針灸人數'] = self.statistics_dicts['本月健保針灸人數'] + \
            statistics_list['本日健保針灸人數']
        statistics_list['本月健保傷科人數'] = self.statistics_dicts['本月健保傷科人數'] + \
            statistics_list['本日健保傷科人數']

        statistics_list['本月健保看診人數'] = (
                statistics_list['本月健保內科人數'] +
                statistics_list['本月健保針灸人數'] +
                statistics_list['本月健保傷科人數']
        )
        statistics_list['本月健保看診日數'] = self.statistics_dicts['本月健保看診日數']
        statistics_list['第一段診察費合理量'] = self.statistics_dicts['第一段診察費合理量']
        statistics_list['本月健保診察費人數'] = self.statistics_dicts['本月健保診察費人數']
        statistics_list['本月健保針傷限量'] = self.statistics_dicts['本月健保針傷限量']
        statistics_list['本月健保針傷合計'] = (
            statistics_list['本月健保針灸人數'] +
            statistics_list['本月健保傷科人數']
        )
        statistics_list['本月健保中度複針限量'] = self.statistics_dicts['本月健保中度複針限量']
        statistics_list['本月健保中度複針人數'] = self.statistics_dicts['本月健保中度複針人數']
        statistics_list['本月健保高度複針限量'] = self.statistics_dicts['本月健保高度複針限量']
        statistics_list['本月健保高度複針人數'] = self.statistics_dicts['本月健保高度複針人數']
        statistics_list['本月健保針傷合併限量'] = self.statistics_dicts['本月健保針傷合併限量']
        statistics_list['本月健保針傷合併人數'] = self.statistics_dicts['本月健保針傷合併人數']

        statistics_list['本月健保中度複傷人數'] = self.statistics_dicts['本月健保中度複傷人數']
        statistics_list['本月健保高度複傷人數'] = self.statistics_dicts['本月健保高度複傷人數']
        statistics_list['本月健保脫臼整復人數'] = self.statistics_dicts['本月健保脫臼整復人數']

        # 每次更新異動
        statistics_list['本月健保針傷合併人數'] += statistics_list['本日健保針傷合併人數']
        statistics_list['本月健保中度複針人數'] += statistics_list['本日健保中度複針人數']
        statistics_list['本月健保高度複針人數'] += statistics_list['本日健保高度複針人數']
        statistics_list['本月健保中度複傷人數'] += statistics_list['本日健保中度複傷人數']
        statistics_list['本月健保高度複傷人數'] += statistics_list['本日健保高度複傷人數']
        statistics_list['本月健保脫臼整復人數'] += statistics_list['本日健保脫臼整復人數']

        if self.system_settings.field('統計針傷給藥人數') == 'Y':  # 2024-10-28 看診完畢回到候診名單讀取速度會變慢
            statistics_list['本月健保針傷給藥人數'] = self.statistics_dicts['本月健保針傷給藥人數']
            statistics_list['本月健保針傷給藥人數'] += statistics_list['本日健保針傷給藥人數']

        self.table_widget_statistics_list.set_dict(statistics_list)

        row_list = [0, 4, 5, 6, 7, 8, 9, 10, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]
        for col_no in range(self.ui.tableWidget_statistics_list.rowCount()):
            for row_no in row_list:
                item = self.ui.tableWidget_statistics_list.item(row_no, col_no)
                if item is not None:
                    if row_no in [0]:
                        item.setForeground(QtGui.QColor('red'))
                    elif row_no in [16, 18, 20, 22, 24]:
                        item.setForeground(QtGui.QColor('red'))
                    elif row_no in [7, 8, 9, 10, 26, 27, 28, 29]:
                        item.setForeground(QtGui.QColor('green'))
                    elif row_no in [4, 5, 21, 23]:
                        item.setForeground(QtGui.QColor('magenta'))
                    elif row_no in [6, 25]:
                        item.setForeground(QtGui.QColor('blue'))

        self.ui.tableWidget_statistics_list.resizeColumnsToContents()
        self._plot_chart(statistics_list)

    def _plot_chart(self, statistics_list):
        set0 = QtChart.QBarSet("內")
        set1 = QtChart.QBarSet("針")
        set2 = QtChart.QBarSet("傷")
        set3 = QtChart.QBarSet("中針")
        set4 = QtChart.QBarSet("高針")
        set5 = QtChart.QBarSet("合併")

        set0 << statistics_list['本月健保內科人數']
        set1 << statistics_list['本月健保針灸人數']
        set2 << statistics_list['本月健保傷科人數']
        set3 << statistics_list['本月健保中度複針人數']
        set4 << statistics_list['本月健保高度複針人數']
        set5 << statistics_list['本月健保針傷合併人數']

        series = QtChart.QBarSeries()
        series.append(set0)
        series.append(set1)
        series.append(set2)
        series.append(set3)
        series.append(set5)

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle('本月人數統計表')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        year = datetime.datetime.now().year
        month = datetime.datetime.now().month
        calc_date = f'{year}年{month}月'
        categories = [calc_date]

        axis = QtChart.QBarCategoryAxis()
        axis.append(categories)
        chart.createDefaultAxes()
        chart.setAxisX(axis, series)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(QtCore.Qt.AlignBottom)

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)
        self.chartView.setFixedHeight(350)
        # self.chartView.setFixedWidth(300)

        existing_widget = self.ui.verticalLayout_chart.takeAt(0)
        if existing_widget:
            existing_widget.widget().setParent(None)

        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def _print_prescript(self, print_mode='選擇列印'):
        case_key = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['CaseKey'])
        printer_utils.print_prescription_form(
            self, self.database, self.system_settings, case_key, print_mode)

    def _print_receipt(self, print_mode='選擇列印'):
        case_key = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['CaseKey'])
        printer_utils.print_receipt_form(
            self, self.database, self.system_settings, case_key, print_mode)

    # 列印其他收據
    def _print_misc(self, print_mode='選擇列印'):
        case_key = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['CaseKey'])
        printer_utils.print_misc_form(
            self, self.database, self.system_settings, case_key, print_mode)

    def _print_all(self):
        print_mode = '系統設定'

        self._print_misc(print_mode)
        self._print_prescript(print_mode)
        self._print_receipt(print_mode)

    def _unset_wait_done(self):
        msg_box = dialog_utils.get_message_box(
            '還原成未看診資料', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定還原此筆資料為未看診狀態?</b></font>',
            '注意！資料還原後後, 將無法回復!'
        )
        unset_wait = msg_box.exec_()
        if not unset_wait:
            return

        case_key = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['CaseKey'])
        sql = f'''
            UPDATE cases
            SET
                DoctorDate = NULL, ChargeDate = NULL,
                DoctorDone = "False", ChargeDone = "False"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

        sql = f'''
            UPDATE wait
            SET
                DoctorDone = "False", ChargeDone = "False"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

        self._read_wait_completed()

    def _open_med_vpn(self):
        web_utils.open_med_vpn(self.system_settings)

    def _table_widget_waiting_list_key_press(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Return or key == QtCore.Qt.Key_Enter:
            self.open_medical_record()

        return QtWidgets.QTableWidget.keyPressEvent(self.ui.tableWidget_waiting_list, event)

    def _get_voice_dict(self, regist_no=None, name=None, room=None):
        if regist_no is None:
            regist_no = self.table_widget_waiting_list.field_value(3)

        if name is None:
            name = self.table_widget_waiting_list.field_value(5)
            name = string_utils.remove_not_chinese_character(name)

        if room is None:
            room = self.table_widget_waiting_list.field_value(8)

        voice_dict = {
            'clinic_name': self.system_settings.field('院所名稱'),
            'regist_no': string_utils.xstr(regist_no),
            'name': name,
            'room': string_utils.xstr(room),
            'program_name': self.program_name,
        }

        return voice_dict

    def _get_voice_sentence(self, voice_dict=None):
        if voice_dict is None:
            voice_dict = self._get_voice_dict()

        room = voice_dict['room']
        regist_no = voice_dict['regist_no']

        if self.system_settings.field('叫號包含病患姓名') == 'Y':
            name = voice_dict['name']
        else:
            name = ''

        voice_call_format = self.system_settings.field('自訂叫號格式')
        if voice_call_format not in ['', None]:
            name = voice_dict['name']
            try:
                voice_call_format = voice_call_format.replace('{room}', room)
            except Exception:
                pass

            try:
                voice_call_format = voice_call_format.replace('{regist_no}', regist_no)
            except Exception:
                pass

            try:
                voice_call_format = voice_call_format.replace('{name}', name)
            except Exception:
                pass

            sentence = voice_call_format
        elif self.system_settings.field('叫號不包含診療室') == 'Y':
            sentence = f"{regist_no}號 {name}, 請至診療室報到"
        else:
            sentence = f"{room}診 {regist_no}號 {name}, 請至{room}診報到"

        if self.system_settings.field('叫號包含下一位請準備') == 'Y':
            current_row_no = self.ui.tableWidget_waiting_list.currentRow()
            next_regist_no = self.ui.tableWidget_waiting_list.item(current_row_no+1, 3)
            if next_regist_no is not None:
                next_regist_no = next_regist_no.text()
                if self.system_settings.field('叫號包含病患姓名') == 'Y':                
                    next_name = self.ui.tableWidget_waiting_list.item(current_row_no+1, 5).text()
                else:
                    next_name = ''
                    
                sentence += f',  {next_regist_no}號{next_name} 請準備'

        return sentence

    def _speech_arrival(self):
        sentence = self._get_voice_sentence()
        if sentence is None:
            return

        system_utils.speak(sentence)

        if self.system_settings.field('叫號同時啟動叫號燈') == 'Y':
            self._send_led()

    def send_voice_data(self, regist_no=None, name=None, room=None):
        voice_dict = self._get_voice_dict(regist_no=regist_no, name=name, room=room)
        
        if self.system_settings.field('廣播叫號同步所有線上看診號') == 'Y':        
            try:
                regist_no = int(voice_dict['regist_no'])
                self.spinBox_seq_number.setValue(regist_no)            
            except Exception:
                return
        
        sentence = self._get_voice_sentence(voice_dict)
        voice_dict['sentence'] = sentence

        broadcast_json = json.dumps(voice_dict)
        self.voice_client.send_data(broadcast_json)

        if self.system_settings.field('叫號同時啟動叫號燈') == 'Y':
            self._send_led()

    def _send_led(self, custom=False):
        if number_utils.get_integer(self.led_port) > 0:
            self._send_com_data(custom=custom)
        elif self.led_ip not in ['', None]:
            self._send_tcpip_data(custom=custom)
        else:
            pass

        self._send_socket_data()

    def _send_com_data(self, custom=False):
        if custom:
            regist_no = self.spinBox_led_number.value()
        else:
            regist_no = self.table_widget_waiting_list.field_value(3)

        try:
            system_utils.send_to_com_port(self.led_port, regist_no)
        except Exception:
            pass

    def _send_tcpip_data(self, custom=False):
        if self.ring_bell == 'Y':
            ring_code = 0x01
        else:
            ring_code = 0x00

        head = [0x6d, 0x6d, 0x00]
        tail = [0x01, ring_code, 0x00]

        if custom:
            regist_no = self.spinBox_led_number.value()
        else:
            regist_no = self.table_widget_waiting_list.field_value(3)

            try:
                self.spinBox_led_number.setValue(int(regist_no))
            except Exception:
                pass

        regist_no = f'{regist_no:0>3}'
        data = head + [int(regist_no[0]), int(regist_no[1]), int(regist_no[2])] + tail

        try:
            system_utils.send_to_tcpip(self.led_ip, self.led_tcp_port, bytes(data))
        except Exception:
            pass

    def _write_ic_treatment(self):
        card = string_utils.xstr(self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['Card']))
        if card in ['', 'IC', '自動取得']:
            self._rewrite_ic_card(show_warning=False)
            self._read_wait_completed()
            return

        name = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['Name'])
        msg_box = dialog_utils.get_message_box(
            '寫入健保卡就醫資料', QMessageBox.Question,
            f'<h3>確定寫入{name}的健保卡就醫資料?</h3>',
            '注意! 請插入健保卡!'
        )
        write_ic_card = msg_box.exec_()
        if not write_ic_card:
            return

        case_key = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['CaseKey'])
        patient_key = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['PatientKey'])

        ic_card_type = case_utils.get_ic_card_type(self.database, case_key)
        if ic_card_type == '虛擬健保卡':
            ic_card = class_utils.get_vhccshis(self, self.database, self.system_settings, None)
        else:
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)

        if not ic_card.insert_correct_ic_card(patient_key):
            return

        ic_card.write_ic_medical_record(case_key, cshis_utils.NORMAL_CARD)
        self._read_wait_completed()

    def _rewrite_ic_card(self, show_warning=True):
        if show_warning:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle('重新寫入健保卡')
            msg_box.setText(
                '''
                <font size="5" color="red">
                <b>確定要將病歷重新寫入健保卡?<br>
                </font>
                '''
            )
            msg_box.setInformativeText(
                "請注意! 如果要取得新卡序, 請先修正掛號資料, 將原來的卡序清除, 這樣才會產生新的卡序，否則只會重寫診療及醫令資料."
            )
            msg_box.addButton(QPushButton("重新寫入"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            cancel = msg_box.exec_()
            if cancel:
                return

        case_key = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['CaseKey'])
        patient_key = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['PatientKey'])
        share_type = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['ShareType'])
        card = string_utils.xstr(self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['Card']))
        course = number_utils.get_integer(
            self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['Course']))

        if course == 0:
            course = None

        ic_card_type = case_utils.get_ic_card_type(self.database, case_key)
        if ic_card_type == '虛擬健保卡':
            ic_card = class_utils.get_vhccshis(self, self.database, self.system_settings, None)
        else:
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)

        ic_card_ok = ic_card.write_ic_card(
            '掛號寫卡',
            patient_key,
            course,
            share_type,
            cshis_utils.NORMAL_CARD,
        )
        if not ic_card_ok:
            return

        self.update_cases_by_ic_card(ic_card, case_key, card, course)
        ic_card.write_ic_medical_record(case_key, cshis_utils.NORMAL_CARD)
        self.update_wait_by_ic_card(ic_card, case_key)
        self._read_wait_completed()

    # 重寫醫令
    def _rewrite_ic_prescript(self):
        name = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['Name'])

        msg_box = dialog_utils.get_message_box(
            '重新寫入健保卡醫令資料', QMessageBox.Question,
            f'<h3>確定重新寫入{name}的健保卡醫令資料?</h3>',
            '注意！請插入健保卡!'
        )
        write_ic_card = msg_box.exec_()
        if not write_ic_card:
            return

        case_key = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['CaseKey'])
        patient_key = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['PatientKey'])

        ic_card_type = case_utils.get_ic_card_type(self.database, case_key)
        if ic_card_type == '虛擬健保卡':
            ic_card = class_utils.get_vhccshis(self, self.database, self.system_settings, None)
        else:
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)

        if not ic_card.insert_correct_ic_card(patient_key):
            return

        ic_card.rewrite_ic_prescript(case_key)
        self._read_wait_completed()

    def update_cases_by_ic_card(self, ic_card, case_key, original_card, course):
        if ic_card is None:
            return

        fields = [
            'Card', 'Continuance', 'Security',
        ]
        card = string_utils.xstr(ic_card.treat_data['seq_number'])
        if card == '':
            card = original_card

        security = case_utils.treat_data_to_xml(ic_card.treat_data)

        treat_after_check = '1'  # 1:正常 2:補卡
        security = case_utils.update_xml_doc(
            security, 'treat_after_check', treat_after_check)
        security = case_utils.update_xml_doc(
            security, 'prescript_sign_time', date_utils.now_to_str())
        security = case_utils.update_xml_doc(
            security, 'upload_type', '1')
        data = [
            card,
            course,
            security,
        ]
        self.database.update_record('cases', fields, 'CaseKey', case_key, data)

    def update_wait_by_ic_card(self, ic_card, case_key):
        if ic_card is None:
            return

        card = ic_card.treat_data['seq_number']
        sql = f'''
            UPDATE wait
            SET
                Card = "{card}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

    def _waiting_list_item_changed(self):
        self.ui.action_change_ins_type.setEnabled(True)
        row_no = self.ui.tableWidget_waiting_list.currentRow()
        ins_type = self.ui.tableWidget_waiting_list.item(row_no, WAITING_LIST_COL_NO['InsType'])
        if ins_type is None:
            return

        ins_type = ins_type.text()
        if ins_type == '自費':
            self.ui.action_change_ins_type.setEnabled(False)

    def _wait_completed_table_item_changed(self):
        row_no = self.ui.tableWidget_wait_completed.currentRow()

        case_key = self.ui.tableWidget_wait_completed.item(row_no, WAIT_DONE_LIST_COL_NO['CaseKey'])
        ic_wrote = self.ui.tableWidget_wait_completed.item(row_no, WAIT_DONE_LIST_COL_NO['WriteCard'])

        if ic_wrote is not None:
            ic_wrote = ic_wrote.text()

        self.ui.toolButton_print_prescript.setEnabled(False)
        self.ui.toolButton_print_receipt.setEnabled(False)
        self.ui.toolButton_print_misc.setEnabled(False)
        self.ui.toolButton_print_all.setEnabled(False)
        self.ui.toolButton_unset_wait.setEnabled(False)

        self.ui.toolButton_write_ic_card.setEnabled(False)
        self.ui.toolButton_rewrite_ic_card.setEnabled(False)
        self.ui.toolButton_rewrite_ic_prescript.setEnabled(False)

        if ic_wrote in ['是', '否']:
            self.ui.toolButton_rewrite_ic_card.setEnabled(True)
            if ic_wrote == '是':
                self.ui.toolButton_rewrite_ic_prescript.setEnabled(True)    # 重寫醫令
            elif ic_wrote == '否':
                self.ui.toolButton_write_ic_card.setEnabled(True)

        if case_key is not None:
            self.ui.toolButton_print_prescript.setEnabled(True)
            self.ui.toolButton_print_receipt.setEnabled(True)
            self.ui.toolButton_print_misc.setEnabled(True)
            self.ui.toolButton_print_all.setEnabled(True)
            self.ui.toolButton_unset_wait.setEnabled(True)

    # 重新顯示資料 call from pymedical (call from here is not working)
    def refresh_medical_record(self):
        tab_name = self.ui.tabWidget_waiting_list.tabText(self.ui.tabWidget_waiting_list.currentIndex())
        if tab_name == '候診名單':
            return

        case_key = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['CaseKey'])
        if case_key is None:
            return

        sql = self._read_wait_completed_by_case_key(case_key)
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        current_row = self.ui.tableWidget_wait_completed.currentRow()
        self._set_wait_completed_data(current_row, row)

    def _set_late(self):
        msg_box = dialog_utils.get_message_box(
            '設定為過號', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定設定此筆病歷為過號?</b></font>',
            '注意！資料設定後, 將無法回復!'
        )
        set_late = msg_box.exec_()
        if not set_late:
            return

        case_key = self.table_widget_waiting_list.field_value(WAITING_LIST_COL_NO['CaseKey'])
        remark = self.table_widget_waiting_list.field_value(WAITING_LIST_COL_NO['Remark'])

        if remark in ['', None]:
            remark = LATE_KEYWROD
        else:
            remark += LATE_KEYWROD

        sql = f'''
            UPDATE cases
            SET
                Remark = "{remark}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

        sql = f'''
            UPDATE wait
            SET
                Remark = "{remark}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

        self.read_wait()
        self.voice_client.send_data('refresh_wait')

    def _cancel_late(self):
        msg_box = dialog_utils.get_message_box(
            '取消過號', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定取消此筆過號病歷?</b></font>',
            '注意！資料設定後, 將無法回復!'
        )
        clear_late = msg_box.exec_()
        if not clear_late:
            return

        case_key = self.table_widget_waiting_list.field_value(WAITING_LIST_COL_NO['CaseKey'])
        remark = self.table_widget_waiting_list.field_value(WAITING_LIST_COL_NO['Remark'])

        if '過號' not in remark:
            self.voice_client.send_data('refresh_wait')
            return

        remark = remark.replace(LATE_KEYWROD, '')
        sql = f'''
            UPDATE cases
            SET
                Remark = "{remark}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

        sql = f'''
            UPDATE wait
            SET
                Remark = "{remark}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

        self.read_wait()
        self.voice_client.send_data('refresh_wait')

    def _change_ins_type(self):
        case_key = self.table_widget_waiting_list.field_value(WAITING_LIST_COL_NO['CaseKey'])
        name = self.table_widget_waiting_list.field_value(WAITING_LIST_COL_NO['Name'])

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('更改為自費')
        msg_box.setText(
            f'''
            <font size="5" color="red">
                <b>確定要將{name}的健保病歷改為自費病歷嗎?
            </font>
            '''
        )
        msg_box.setInformativeText('請確認是否變更為自費')
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        apply_change = msg_box.exec_()
        if not apply_change:
            return

        sql = f'''
            UPDATE cases
            SET
                InsType = "自費",
                Card = "免卡",
                Continuance = NULL,
                DiagFee = NULL,
                InterDrugFee = NULL,
                PharmacyFee = NULL,
                AcupunctureFee = NULL,
                MassageFee = NULL,
                DislocateFee = NULL,
                ExamFee = NULL,
                InsTotalFee = NULL,
                DiagShareFee = NULL,
                DrugShareFee = NULL,
                SDiagShareFee = NULL,
                SDrugShareFee = NULL,
                InsApplyFee = NULL,
                AgentFee = NULL
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)
        sql = f'''
            DELETE FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1
        '''
        self.database.exec_sql(sql)
        sql = f'''
            UPDATE wait
            SET
                InsType = "自費",
                Card = "免卡",
                Continuance = NULL
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

        self.read_wait()

    def _send_socket_data(self):
        room = self._get_current_room()

        self.socket_client.send_data(
            ','.join([
                self.system_settings.field('院所名稱'),
                self.program_name,
                self.user_name,
                string_utils.xstr(room),
            ])
        )

    def _start_flashing(self, widget):
        """啟動閃爍效果"""
        if not hasattr(self, "flash_timer"):
            # 初始化閃爍計時器
            self.flash_timer = QtCore.QTimer(self)
            self.flash_timer.setInterval(100)  # 每100毫秒切換一次背景色
            self.flash_timer.timeout.connect(lambda: self._toggle_flash(widget))

            # 設定閃爍持續時間計時器
            self.flash_duration_timer = QtCore.QTimer(self)
            self.flash_duration_timer.setInterval(1000)  # 持續閃爍1秒
            self.flash_duration_timer.setSingleShot(True)
            self.flash_duration_timer.timeout.connect(lambda: self._stop_flashing(widget))

        # 開始閃爍
        self.flash_timer.start()
        self.flash_duration_timer.start()
        self.is_flashing = True

    def _toggle_flash(self, widget):
        """切換閃爍效果（改變背景色）"""
        if self.is_flashing:
            current_style = widget.styleSheet()
            if "background-color: red" in current_style:
                widget.setStyleSheet("background-color: white;")
            else:
                widget.setStyleSheet("background-color: red;")

    def _stop_flashing(self, widget):
        """停止閃爍並恢復原本背景色"""
        self.flash_timer.stop()
        widget.setStyleSheet("")  # 恢復原本樣式
        self.is_flashing = False

    def _extra_purchase(self):
        case_key = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['CaseKey'])
        patient_key = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['PatientKey'])
        patient_name = self.table_widget_wait_completed.field_value(WAIT_DONE_LIST_COL_NO['Name'])
        self.parent.append_extra_medical_record(
            case_key,
            patient_key,
            patient_name,
        )
