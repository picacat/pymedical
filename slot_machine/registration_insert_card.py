#!/usr/bin/env python3
#coding: utf-8

import sys

from PyQt5 import QtWidgets, QtGui
import datetime

from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils
from libs import registration_utils


# 樣板 2018.01.31
class RegistrationInsertCard(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(RegistrationInsertCard, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_REGISTRATION_INSERT_CARD, self)
        style = '''
            QMainWindow#WindowRegistrationInsertCard 
            {background-image: url(./images/home.jpg);}
        '''
        self.ui.setStyleSheet(style)
        self.ui.label_message.setStyleSheet("QLabel {color : white; }")

        effect = QtWidgets.QGraphicsDropShadowEffect()
        effect.setBlurRadius(0)
        effect.setColor(QtGui.QColor('black'))
        effect.setOffset(1, 2)

        self.ui.label_message.setGraphicsEffect(effect)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_read_card.clicked.connect(self._read_card)
        self.ui.toolButton_cancel.clicked.connect(self._back_home)

    # 設定讀卡作業方式
    def set_read_type(self, read_type):
        self.read_type = read_type

    def _read_card(self):
        if not self.parent.ic_card.read_basic_data():  # 只讀最基本的資料
            return

        available_date, available_count = self.parent.ic_card.get_card_status()
        if available_count is None:
            return

        if available_count <= 3:
            self.parent.ic_card.update_hc(False)

        patient_id = self.parent.ic_card.basic_data['patient_id']
        sql = '''
            SELECT * FROM patient
            WHERE
                ID = "{patient_id}"
        '''.format(
            patient_id=patient_id
        )
        rows = self.database.select_record(sql)

        if self.read_type == '門診掛號':
            self.registration(rows)
        elif self.read_type == '批價給藥':
            self.charge(rows)
        elif self.read_type == '預約報到':
            self.reservation_arrival(rows)

    def registration(self, patient_rows):
        if len(patient_rows) <= 0:  # 初診
            self.parent.ic_card.read_register_basic_data()  # 多讀一次, 以確定健保身分
            self.parent.open_first_visit_registration(self.parent.ic_card.basic_data)
            return

        patient_row = patient_rows[0]
        patient_key = patient_row['PatientKey']
        reservation_record_rows = self._get_reservation_record(patient_key)
        if len(reservation_record_rows) > 0:
            self.parent.open_show_message('您今日有預約門診，<br>請先預約報到.')
            return

        medical_record_rows = self._get_medical_record(patient_key)
        if len(medical_record_rows) >= 1:
            self.parent.open_show_message('您今日已有門診，<br>不需重複掛號.')
            return

        self.parent.open_registration(
            self.parent.ic_card.basic_data,
            '門診掛號',
            doctor=None, reg_no=None, visit=None
        )

    def charge(self, patient_rows):
        if len(patient_rows) <= 0:  # 初診
            self.parent.open_show_message('找不到您於本診所的門診資料，<br>請先門診掛號.')
            return

        patient_row = patient_rows[0]
        patient_key = patient_row['PatientKey']

        medical_record_rows = self._get_medical_record(patient_key)
        if len(medical_record_rows) <= 0:
            self.parent.open_show_message('找不到您今日的門診資料，<br>請先門診掛號.')
            return

        doctor_done = True
        charge_done = True
        for medical_record_row in medical_record_rows:
            if string_utils.xstr(medical_record_row['DoctorDone']) != 'True':
                doctor_done = False
                break

            if string_utils.xstr(medical_record_row['ChargeDone']) != 'True':
                charge_done = False

        if not doctor_done:
            self.parent.open_show_message('您的病歷還在處理中，<br>請稍後再批價.')
            return

        if charge_done:
            self.parent.open_show_message('您已經批價繳費過了，<br>謝謝您的使用.')
            return

        medical_record_row = medical_record_rows[0]
        fees = [
            ['藥品負擔', number_utils.get_integer(medical_record_row['DrugShareFee'])],
            ['自費金額', number_utils.get_integer(medical_record_row['TotalFee'])],
        ]
        self.parent.open_charge_cash('批價繳費', medical_record_row['CaseKey'], fees)

    def reservation_arrival(self, patient_rows):
        if len(patient_rows) <= 0:  # 初診
            self.parent.open_show_message('找不到您於本診所的門診資料，<br>請先門診掛號.')
            return

        patient_row = patient_rows[0]
        patient_key = patient_row['PatientKey']
        reservation_record_rows = self._get_reservation_record(patient_key)
        if len(reservation_record_rows) <= 0:
            self.parent.open_show_message('找不到您今日的門診預約資料，<br>請先門診掛號.')
            return

        reservation_record_row = reservation_record_rows[0]
        if string_utils.xstr(reservation_record_row['Arrival']) == 'True':
            self.parent.open_show_message('您已預約報到過了，謝謝.')
            return

        period = string_utils.xstr(reservation_record_row['Period'])
        current_period = registration_utils.get_period(self.system_settings)
        if period != current_period:
            self.parent.open_show_message('您預約的班別是{0}，<br>請於{0}時報到, 謝謝.'.format(period))
            return

        self.parent.open_registration(
            self.parent.ic_card.basic_data,
            '預約報到',
            doctor=string_utils.xstr(reservation_record_row['Doctor']),
            reg_no=reservation_record_row['ReserveNo'],
            visit=None
        )

    def _get_medical_record(self, patient_key):
        start_date = datetime.datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.datetime.now().strftime('%Y-%m-%d 23:59:59')
        sql = '''
            SELECT * FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                PatientKey = {patient_key}
        '''.format(
            start_date=start_date,
            end_date=end_date,
            patient_key=patient_key,
        )

        rows = self.database.select_record(sql)

        return rows

    def _get_reservation_record(self, patient_key):
        start_date = datetime.datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.datetime.now().strftime('%Y-%m-%d 23:59:59')
        sql = '''
            SELECT * FROM reserve
            WHERE
                ReserveDate BETWEEN "{start_date}" AND "{end_date}" AND
                PatientKey = {patient_key}
        '''.format(
            start_date=start_date,
            end_date=end_date,
            patient_key=patient_key,
        )

        rows = self.database.select_record(sql)

        return rows

    def _back_home(self):
        self.parent.open_home()
