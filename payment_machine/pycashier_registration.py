# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore
import datetime
import time

from libs import ui_utils
from libs import string_utils
from libs import cshis_utils
from libs import case_utils
from libs import date_utils
from libs import number_utils
from libs import registration_utils
from libs import system_utils


# 2021.11.01 掛號機掛號頁面
class DetectRegistrationCardThread(QtCore.QThread):
    cancel_registration = QtCore.pyqtSignal('QString')

    def __init__(self, parent, ic_card):
        super(DetectRegistrationCardThread, self).__init__()
        self.parent = parent
        self.ic_card = ic_card
        self._stop = False

    def run(self):
        self.ic_card.close_com()
        self.ic_card.open_com()

        while True:
            QtCore.QCoreApplication.processEvents()

            if self._stop:
                self._stop = False
                self.ic_card.close_com()
                break

            error_code = self.ic_card.get_ic_card_status(manual_open_com=True)
            if error_code == 4000:
                self.ic_card.close_com()
                self.ic_card.open_com()
                continue

            if error_code == 0:
                self._stop = False
                self.ic_card.close_com()
                self.cancel_registration.emit('cancel_registration')
                break

        self.ic_card.close_com()

    def stop(self):
        self._stop = True


# 已插入健保卡, 準備開始掛號
class PyCashierRegistration(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(PyCashierRegistration, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ic_card = args[2]
        self.case_key = None
        self.patient_key = None
        self.ui = None

        self.detect_registration_thread = DetectRegistrationCardThread(self, self.ic_card)
        self.detect_registration_thread.cancel_registration.connect(self.cancel_registration)

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PYCASHIER2_REGISTRATION, self)
        style = '''
            QMainWindow#WindowRegistration
            {background-image: url(./images/pycashier_bg.jpg);}
        '''
        self.ui.setStyleSheet(style)

        widget_list = [self.ui.label_message, self.ui.label_hint]
        self._set_widget_shadow(widget_list)

        self.button_list = [
            self.ui.pushButton_1,
            self.ui.pushButton_2,
            self.ui.pushButton_3,
            self.ui.pushButton_4,
            self.ui.pushButton_5,
        ]

    def _set_widget_shadow(self, widget_list):
        blur_radius = 0

        shadow_list = []
        for i in range(len(widget_list)):
            shadow_list.append(QtWidgets.QGraphicsDropShadowEffect())
            shadow_list[i].setBlurRadius(blur_radius)
            shadow_list[i].setColor(QtGui.QColor('black'))
            shadow_list[i].setOffset(1, 2)

            widget_list[i].setStyleSheet("QLabel {color : white}")
            widget_list[i].setGraphicsEffect(shadow_list[i])

    # 設定信號
    def _set_signal(self):
        self.ui.pushButton_1.clicked.connect(self._button_clicked)
        self.ui.pushButton_2.clicked.connect(self._button_clicked)
        self.ui.pushButton_3.clicked.connect(self._button_clicked)
        self.ui.pushButton_4.clicked.connect(self._button_clicked)
        self.ui.pushButton_5.clicked.connect(self._button_clicked)

    def _get_patient_row(self, patient_id):
        sql = f'''
            SELECT * FROM patient
            WHERE
                ID = "{patient_id}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None
        else:
            return rows[0]

    def set_registration_data(self):
        print('a')
        time.sleep(1)

        for button in self.button_list:
            button.setVisible(False)

        print('b')
        self.patient_id = None
        if not self.ic_card.read_basic_data():
            return

        print('c')
        patient_id = self.ic_card.basic_data['patient_id']
        patient_name = self.ic_card.basic_data['name']
        patient_row = self._get_patient_row(patient_id)

        print('d')
        if patient_row is None:
            print('d1')
            self._show_patient_first_visit(patient_name)
        else:
            print('d2')
            self._check_registration_type(patient_row)

    def _show_patient_first_visit(self, patient_name):
        message = f'''
            {patient_name} 您好<br>
            系統查不到您的資料<br>
            請至掛號櫃台<br>
            辦理初診掛號作業<br>
            謝謝

        '''
        hint = '請取出健保卡'

        self._set_label_message(message, hint)

    def _get_deposit_row(self, patient_row):
        patient_key = patient_row['PatientKey']
        _, deposit_row = registration_utils.check_deposit(             # 檢查健保欠卡未還
            self.database, self.system_settings, patient_key
        )

        return deposit_row

    def _show_deposit(self, deposit_row):
        patient_name = string_utils.xstr(deposit_row['Name'])
        deposit_date = string_utils.xstr(deposit_row['CaseDate'].date())

        message = f'''
            {patient_name} 您好<br><br>
            您在{deposit_date}<br>
            有欠卡的記錄<br>
            請至掛號櫃台<br>
            辦理補卡及<br>
            門診掛號作業, 謝謝

        '''
        hint = '請取出健保卡'

        self._set_label_message(message, hint)

    def _set_label_message(self, message, hint):
        self.ui.label_message.setText(message)
        self.ui.label_hint.setText(hint)

        sentence = message.replace('<br>', ', ')
        # system_utils.speak(sentence)

    def _is_charge_done(self, patient_row):
        patient_key = patient_row['PatientKey']
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        sql = f'''
            SELECT * FROM cases
            WHERE
                PatientKey = {patient_key} AND
                DATE(CaseDate) = "{today}" AND
                DoctorDone = "True"
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return False, None

        row = rows[0]
        case_key = row['CaseKey']

        charge_status = case_utils.get_case_extend(self.database, case_key, '掛號機批價')
        if charge_status is None or charge_status != '是':
            return False, row
        else:
            return True, row

    def _is_completed_diag(self, patient_row):
        patient_key = patient_row['PatientKey']
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        sql = f'''
            SELECT * FROM cases
            WHERE
                PatientKey = {patient_key} AND
                DATE(CaseDate) = "{today}" AND
                DoctorDone = "True"
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return None
        else:
            return rows[0]

    def _is_registered(self, patient_row):
        patient_key = patient_row['PatientKey']
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        sql = f'''
            SELECT * FROM cases
            WHERE
                PatientKey = {patient_key} AND
                DATE(CaseDate) = "{today}" AND
                DoctorDone = "False"
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return None
        else:
            return rows[0]

    def _show_waiting(self, case_row):
        patient_name = string_utils.xstr(case_row['Name'])

        message = f'''
            {patient_name} 您好<br><br>
            您尚未就診，無法批價<br>
            請洽詢櫃台，謝謝<br>
        '''
        hint = '請取出健保卡'

        self._set_label_message(message, hint)

    def _show_registered(self, patient_row):
        patient_name = string_utils.xstr(patient_row['Name'])

        message = f'''
            {patient_name} 您好<br><br>
            您尚未完成<br>
            門診掛號手續<br>
            請至櫃台辦理<br>
            謝謝您的使用

        '''
        hint = '請取出健保卡'

        self._set_label_message(message, hint)

    def _show_completed_diag(self, case_row):
        patient_name = string_utils.xstr(case_row['Name'])

        message = f'''
            {patient_name} 您好<br><br>
            您已完成批價<br>
            謝謝您的使用

        '''
        hint = '<font color="red">請取出健保卡</font>'

        self._set_label_message(message, hint)

    def _charge_fee(self, case_row):
        self.case_key = case_row['CaseKey']
        self.patient_key = case_row['PatientKey']

        patient_name = string_utils.xstr(case_row['Name'])
        doctor = string_utils.xstr(case_row['Doctor'])

        message = f'''
            {patient_name} 您好<br><br>
            您已完成{doctor}醫師的門診<br>
            請問您現在要批價繳費嗎?
        '''
        hint = '''
            注意! <br>
            請勿取出健保卡<br>
            若您想要取消批價繳費<br>
            請將健保卡取出
        '''
        self._set_label_message(message, hint)
        self.button_list[0].setVisible(True)
        self.button_list[0].setText('我要批價繳費')

        self.button_list[0].animateClick()

        # self.detect_registration_thread.stop()
        # self._set_charge_data()

    def _get_reservation_row(self, patient_row):
        patient_key = patient_row['PatientKey']
        start_date = datetime.datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.datetime.now().strftime('%Y-%m-%d 23:59:59')

        sql = f'''
            SELECT * FROM reserve
            WHERE
                ReserveDate BETWEEN "{start_date}" AND "{end_date}" AND
                Arrival = "False" AND
                PatientKey = {patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return rows[0]

    def _check_registration_type(self, patient_row):
        deposit_row = self._get_deposit_row(patient_row)
        if deposit_row is not None:
            self._show_deposit(deposit_row)
            return

        charge_done, case_row = self._is_charge_done(patient_row)
        if case_row is not None:  # 已經繳費過了
            if charge_done:
                self._show_completed_diag(case_row)
            else:
                self._charge_fee(case_row)

            return

        case_row = self._is_registered(patient_row)
        if case_row is not None:
            self._show_waiting(case_row)
            return

        reservation_row = self._get_reservation_row(patient_row)
        if reservation_row is not None:
            self._reservation_registration(reservation_row)
            return

        self._show_registered(patient_row)  # 暫時的 2022.12.07
        return

        # self._outpatient_registration(patient_row)

    def _reservation_registration(self, reservation_row):
        # period = string_utils.xstr(reservation_row['Period'])
        # current_period = registration_utils.get_current_period(self.system_settings)

        # if period == current_period:
        #     self._reservation_arrival_on_time(reservation_row)
        # elif (current_period == '晚班' and period in ['早班', '午班']) or \
        #      (current_period == '午班' and period in ['早班']):
        #     self._reservation_arrival_late(current_period, reservation_row)
        # else:
        #     self._reservation_arrival_early(current_period, reservation_row)

        patient_name = string_utils.xstr(reservation_row['Name'])
        message = f'''
            {patient_name} 您好<br><br>
            請至掛號櫃台<br>
            辦理預約掛號報到<br>
            謝謝
        '''
        hint = '請取出健保卡'

        self._set_label_message(message, hint)

    def _reservation_arrival_late(self, current_period, reservation_row):
        patient_name = string_utils.xstr(reservation_row['Name'])
        period = string_utils.xstr(reservation_row['Period'])
        doctor = string_utils.xstr(reservation_row['Doctor'])
        message = f'''
            {patient_name} 您好<br><br>
            您預約的是{period}的{doctor}醫師<br>
            目前是{current_period}，已經過號<br>
            請至掛號櫃台<br>
            重新辦理現場門診掛號<br>
            不便之處請見諒<br>
            謝謝

        '''
        hint = '請取出健保卡'

        self._set_label_message(message, hint)

    def _reservation_arrival_early(self, current_period, reservation_row):
        patient_name = string_utils.xstr(reservation_row['Name'])
        period = string_utils.xstr(reservation_row['Period'])
        doctor = string_utils.xstr(reservation_row['Doctor'])
        message = f'''
            {patient_name} 您好<br><br>
            您預約的是{period}的{doctor}醫師<br>
            目前是{current_period}，時間還沒到<br>
            請於{period}時間再來預約報到<br>
            謝謝

        '''
        hint = '請取出健保卡'

        self._set_label_message(message, hint)

    def _reservation_arrival_on_time(self, reservation_row):
        self.patient_key = reservation_row['PatientKey']
        patient_name = string_utils.xstr(reservation_row['Name'])
        period = string_utils.xstr(reservation_row['Period'])
        doctor = string_utils.xstr(reservation_row['Doctor'])
        room = string_utils.xstr(reservation_row['Room'])
        reserve_no = string_utils.xstr(reservation_row['ReserveNo'])
        self.reserve_key = reservation_row['ReserveKey']

        message = f'''
            {patient_name} 您好<br><br>
            您有預約{period}<br>
            {doctor}醫師 {room}診{reserve_no}號<br><br>
            請按預約報到
        '''
        hint = '''
            注意! <br>
            請勿取出健保卡<br>
            若您想要取消預約報到<br>
            請將健保卡取出
        '''
        self._set_label_message(message, hint)
        self.button_list[0].setVisible(True)
        self.button_list[0].setText('預約報到')

        # self.button_list[1].setVisible(True)
        # self.button_list[1].setText('取消預約報到請取出健保卡')

    def _outpatient_registration(self, patient_row):
        patient_name = string_utils.xstr(patient_row['Name'])
        self.patient_key = patient_row['PatientKey']

        message = f'''
            {patient_name} 您好<br><br>
            請選擇要掛號的醫師
        '''
        hint = '''
            注意! <br>
            請勿取出健保卡<br>
            若您想要取消門診掛號<br>
            請將健保卡取出
        '''
        self._set_label_message(message, hint)
        self._set_doctor_buttons()

    def cancel_registration(self, detected):
        if detected == 'cancel_registration':
            self._back_home()

    def detect_ic_card_removed(self):
        self.detect_registration_thread.start()

    def _set_doctor_buttons(self):
        doctor_list = self._get_doctor_schedule_list()
        for i, doctor in enumerate(doctor_list):
            self.button_list[i].setVisible(True)
            self.button_list[i].setText(f'我要掛{doctor}醫師的門診')

    def _get_doctor_schedule_list(self):
        current_period = registration_utils.get_current_period(self.system_settings)
        weekday = date_utils.WEEK_DAY_LIST[datetime.datetime.now().weekday()]

        sql = f'''
            SELECT * FROM doctor_schedule
            WHERE
                Period = "{current_period}" AND
                {weekday} IS NOT NULL AND
                LENGTH({weekday}) > 0
            GROUP BY Room
            ORDER BY Room
        '''
        rows = self.database.select_record(sql)

        doctor_list = []
        for row in rows:
            doctor_list.append(string_utils.xstr(row[weekday]))

        return doctor_list

    def _button_clicked(self):
        sender_name = self.sender().text()
        self.detect_registration_thread.stop()

        if sender_name == '預約報到':
            self._set_reservation_arrival_data()
        elif '我要掛' in sender_name:
            self._set_outpatient_data(sender_name)
        elif '批價繳費' in sender_name:
            self._set_charge_data()

    def _set_outpatient_data(self, sender_name):
        doctor = sender_name.split('我要掛')[1].split('醫師的門診')[0]
        self.parent.open_pycashier_payment(self.patient_key, '門診掛號', doctor)

    def _set_charge_data(self):
        self.parent.open_pycashier_payment(self.patient_key, '批價繳費', self.case_key)

    # 預約報到
    def _set_reservation_arrival_data(self):
        self.parent.open_pycashier_payment(self.patient_key, '預約報到', self.reserve_key)

    def _save_file(self):
        ic_card = self._write_ic_card(cshis_utils.NORMAL_CARD)

        if not ic_card:  # 取得安全簽章失敗
            self.parent.open_show_message('<font color="yellow">健保卡無法掛號，請改至櫃檯掛號.</font>')
            return

        case_key = self._insert_medical_record(ic_card)
        self._insert_wait(case_key, ic_card)
        if self.registration_type == '預約報到':
            self._registration_arrival()

        self.socket_client.send_data('新增掛號資料')
        fees = [
            ['掛號費', self.regist_fee],
            ['門診負擔', self.diag_share_fee],
        ]
        self.parent.open_charge_cash('門診掛號', case_key, fees)

    def _write_ic_card(self, treat_after_check):
        ic_card_ok = self.parent.ic_card.write_ic_card(
            '掛號寫卡',
            self.patient_key,
            self.course,
            treat_after_check,
        )

        if ic_card_ok:
            return self.parent.ic_card
        else:
            return False

    # 新增病歷
    def _insert_medical_record(self, ic_card=None):
        fields = [
            'CaseDate', 'PatientKey', 'Name', 'Visit', 'RegistType', 'Injury',
            'TreatType', 'Share', 'InsType', 'Card', 'Continuance', 'Period',
            'Room', 'RegistNo', 'Register',
            'ApplyType', 'PharmacyType',
            'RegistFee', 'DiagShareFee', 'SDiagShareFee', 'Security',
        ]

        if self.card is not None:
            card = self.card
        else:
            card = ic_card.treat_data['seq_number']

        security = case_utils.treat_data_to_xml(ic_card.treat_data)
        security = case_utils.update_xml_doc(
            self.database, security, 'upload_type', '1')
        security = case_utils.update_xml_doc(
            self.database, security, 'treat_after_check', '1')

        data = [
            string_utils.xstr(datetime.datetime.now()),
            self.patient_key,
            self.name,
            self.visit,
            self.reg_type,
            self.injury_type,
            self.treat_type,
            self.share_type,
            self.ins_type,
            card,
            self.course,
            self.period,
            self.room,
            self.reg_no,
            '掛號機',
            '申報',
            '申報' if self.system_settings.field('申報藥事服務費') == 'Y' else '不申報',
            0,  # regist_fee
            self.diag_share_fee,
            0,  # receipt_diag_share_fee
            security,
        ]
        case_key = self.database.insert_record('cases', fields, data)

        return case_key

    # 新增候診名單
    def _insert_wait(self, case_key, ic_card):
        if self.card is not None:
            card = self.card
        else:
            card = ic_card.treat_data['seq_number']

        fields = [
            'CaseKey', 'CaseDate', 'PatientKey', 'Name', 'Visit', 'RegistType',
            'TreatType', 'Share', 'InsType', 'Card', 'Continuance', 'Period',
            'Room', 'RegistNo', 'Doctor',
        ]
        data = [
            case_key,
            string_utils.xstr(datetime.datetime.now()),
            self.patient_key,
            self.name,
            self.visit,
            self.reg_type,
            self.treat_type,
            self.share_type,
            self.ins_type,
            card,
            self.course,
            self.period,
            self.room,
            self.reg_no,
            self.doctor,
        ]
        self.database.insert_record('wait', fields, data)

    def _back_home(self):
        self.parent.open_pycashier_home()

    def _completion_course(self, patient_key):
        today = datetime.date.today()
        last_treat_date = (today - datetime.timedelta(days=30)).strftime('%Y-%m-%d 00:00:00')
        sql = '''
              SELECT TreatType, Card, Continuance, XCard FROM cases WHERE
              (CaseDate >= "{0}") AND
              (PatientKey = {1}) AND
              (InsType = "健保")
              ORDER BY CaseDate DESC LIMIT 1
          '''.format(last_treat_date, patient_key)
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None, None, None

        row = rows[0]

        course = number_utils.get_integer(row['Continuance'])
        if course <= 0:  # 療程被內科切斷, 為了避免療程中刷卡, 開新療程
            return None, None, None

        if course >= 6:  # 療程已滿
            return None, None, None

        treat_type = string_utils.xstr(row['TreatType'])
        card = string_utils.xstr(row['Card'])
        course = string_utils.xstr(row['Continuance'] + 1)  # 療程自動續1次

        return treat_type, card, course

    # 取得診別
    def _get_room(self, period, doctor):
        room = 1

        week_day_list = [
            'Monday',
            'Tuesday',
            'Wednesday',
            'Thursday',
            'Friday',
            'Saturday',
            'Sunday',
        ]

        today = datetime.datetime.now().weekday()
        weekday = week_day_list[today]

        sql = f'''
            SELECT * FROM doctor_schedule
            WHERE
                Period = "{period}" AND
                {weekday} = "{doctor}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return room

        room = rows[0]['Room']

        return room

    def _registration_arrival(self):
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
            patient_key=self.patient_key,
        )

        rows = self.database.select_record(sql)

        if len(rows) > 0:
            self.database.exec_sql(
                'UPDATE reserve SET Arrival = "True" WHERE ReserveKey = {0}'.format(
                    rows[0]['ReserveKey']
                )
            )

