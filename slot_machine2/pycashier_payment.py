# -*- coding: UTF-8 -*-

import sys

from PyQt5 import QtWidgets, QtGui, QtCore
import datetime
import time

from libs import ui_utils
from libs import string_utils
from libs import case_utils
from libs import number_utils
from libs import registration_utils
from libs import charge_utils
from libs import patient_utils
from libs import cshis_utils
from libs import printer_utils


class DetectPaymentCardThread(QtCore.QThread):
    cancel_payment = QtCore.pyqtSignal('QString')

    def __init__(self, parent, ic_card, coinsys):
        super(DetectPaymentCardThread, self).__init__()
        self.parent = parent
        self.ic_card = ic_card
        self.coinsys = coinsys
        self._stop = False
        self.payment_type = None
        self.label_received_fee = None

    def run(self):
        self.ic_card.close_com()
        self.ic_card.open_com()

        self._total_fee = None

        while True:
            QtCore.QCoreApplication.processEvents()

            if self._stop:
                self._stop = False
                self.ic_card.close_com()
                break

            payment_done = self.coinsys.is_payment_done()
            if payment_done:
                self.cancel_payment.emit(self.payment_type)
                break
            else:
                receipt_fee = self.coinsys.get_payment()
                if receipt_fee is not None and self.label_received_fee is not None:
                    self.label_received_fee.setText(string_utils.xstr(receipt_fee))
                    if receipt_fee >= self.total_fee:
                        self.cancel_payment.emit(self.payment_type)
                        break

            error_code = self.ic_card.get_ic_card_status(manual_open_com=True)
            if error_code == 4000:
                self.ic_card.close_com()
                self.ic_card.open_com()
                continue

            if error_code == 0:
                self._stop = False
                self.ic_card.close_com()
                if receipt_fee is not None and receipt_fee > 0:
                    self.coinsys.cancel_payment()

                self.cancel_payment.emit('cancel_payment')
                break

        self.ic_card.close_com()

    def stop(self):
        self._stop = True

    def set_total_fee(self, total_fee):
        self.total_fee = total_fee

    def set_label_received_fee(self, label_received_fee):
        self.label_received_fee = label_received_fee

    def set_payment_type(self, payment_type):
        self.payment_type = payment_type


# 已插入健保卡, 準備收費
class PyCashierPayment(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(PyCashierPayment, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ic_card = args[2]
        self.coinsys = args[3]
        self.ui = None

        self.detect_payment_thread = DetectPaymentCardThread(self, self.ic_card, self.coinsys)
        self.detect_payment_thread.cancel_payment.connect(self.cancel_payment)
        self.pregnant_treat_type_list = ['助孕照護', '保胎照護']

        self.payment_row = {
            'payment_type': None,
            'patient_key': None,
            'period': None,
            'room': 1,
            'regist_fee': 0,
            'diag_share_fee': 0,
            'card': None,
            'course': None,
            'share_type': None,
            'treat_type': None,
            'regist_type': None,
            'doctor': None,
            'regist_no': 0,
            'case_key': None,
            'reserve_key': None,
            'drug_share_fee': 0,
            'total_fee': 0,
        }

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PYCASHIER_PAYMENT, self)
        style = '''
            QMainWindow#WindowPayment
            {background-image: url(./images/pycashier_bg.jpg);}
        '''
        self.ui.setStyleSheet(style)

        widget_list = [
            self.ui.label_message,
            self.ui.label_hint,
            self.ui.label_1,
            self.ui.label_2,
            self.ui.label_3,
            self.ui.label_4,
            self.ui.label_regist_fee,
            self.ui.label_share_fee,
            self.ui.label_total_fee,
            self.ui.label_received_fee,
        ]
        self._set_widget_shadow(widget_list)

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
        pass

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

    # 自動連續療程 - 30天內.
    def _auto_completion_course(self, patient_row):
        patient_key = patient_row['PatientKey']

        default_card = '自動取得'
        treat_type = '內科'

        today = datetime.date.today()
        last_treat_date = (today - datetime.timedelta(days=30-1)).strftime('%Y-%m-%d 00:00:00')
        sql = f'''
            SELECT TreatType, Card, Continuance, Share FROM cases
            WHERE
                (CaseDate >= "{last_treat_date}") AND
                (PatientKey = {patient_key}) AND
                (InsType = "健保") AND
                (Continuance >= 1)
            ORDER BY CaseDate DESC LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return default_card, None, string_utils.xstr(patient_row['InsType']), treat_type

        row = rows[0]

        # 2019.04.29 上次為內科, 為避免療程中刷卡, 不要自動續療程
        if number_utils.get_integer(row['Continuance']) <= 0:
            return default_card, None, string_utils.xstr(patient_row['InsType']), treat_type

        card = string_utils.xstr(row['Card'])
        share_type = string_utils.xstr(row['Share'])
        treat_type = string_utils.xstr(row['TreatType'])
        course = string_utils.xstr(row['Continuance'] + 1)  # 療程自動續1次

        message = registration_utils.check_course_complete_in_days(
            self.database, patient_key, card, course, 30)
        if message is not None or number_utils.get_integer(course) > 6:  # 療程已滿
            card = '自動取得'
            course = None
            treat_type = '內科'

        return card, course, share_type, treat_type

    def _charge_payment(self, case_key):
        self.payment_row['case_key'] = case_key

        sql = f'''
            SELECT cases.*, patient.DiscountType FROM cases
                LEFT JOIN patient ON cases.PatientKey = patient.PatientKey
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]

        patient_name = string_utils.xstr(row['Name'])
        room = row['Room']
        doctor = string_utils.xstr(row['Doctor'])
        drug_share_fee = number_utils.get_integer(row['DrugShareFee'])
        drug_share_discount_fee = charge_utils.get_drug_share_discount_fee(
            self.database, string_utils.xstr(row['DiscountType'])
        )
        if drug_share_discount_fee is not None:
            drug_share_fee = drug_share_discount_fee

        self_total_fee = number_utils.get_integer(row['TotalFee'])

        self.payment_row['room'] = room
        self.payment_row['doctor'] = doctor
        self.payment_row['drug_share_fee'] = drug_share_fee
        self.payment_row['total_fee'] = self_total_fee

        total_fee = drug_share_fee + self_total_fee
        if total_fee <= 0:
            message = f'''
                {patient_name} 您好<br><br>
                您今天不需繳費<br>
                請取出健保卡<br>
            '''
            hint = '''
                請取出健保卡<br>
            '''
            case_utils.set_case_extend(self.database, case_key, '掛號機批價', '是')
        else:
            message = f'''
                {patient_name} 您好<br><br>
                以下是您今天的門診繳費明細<br>
            '''
            hint = '''
                注意! <br>
                請勿取出健保卡<br>
                若您正在繳費且尚未繳清<br>
                取出卡片將會取消批價繳費<br>
                並退還您已繳費的金額
            '''

        self._set_label_message(message, hint)

        self.ui.label_1.setText('自費金額')
        self.ui.label_regist_fee.setText(string_utils.xstr(self_total_fee))

        self.ui.label_2.setText('藥品負擔')
        self.ui.label_share_fee.setText(string_utils.xstr(drug_share_fee))

        self.ui.label_total_fee.setText(string_utils.xstr(total_fee))
        self.ui.label_received_fee.setText('0')

        if total_fee > 0:
            self.coinsys.start_payment(total_fee)
        else:
            self.coinsys.cancel_payment()

        self.detect_payment_thread.set_total_fee(total_fee)
        self.detect_payment_thread.set_label_received_fee(self.ui.label_received_fee)
        self.detect_payment_thread.set_payment_type('批價繳費')

    def set_payment_data(self, patient_key, regist_type, keyword):
        self.payment_row['case_key'] = None
        self.payment_row['drug_share_fee'] = 0
        self.payment_row['total_fee'] = 0
        time.sleep(1)

        if regist_type == '批價繳費':
            self._charge_payment(keyword)
            return

        if regist_type == '門診掛號':
            doctor = keyword
        elif regist_type == '預約報到':
            doctor = self._get_reservation_doctor(keyword)
        else:
            doctor = ''

        patient_row = patient_utils.get_patient_row(self.database, patient_key)
        patient_name = string_utils.xstr(patient_row['Name'])

        card, course, share_type, treat_type = self._auto_completion_course(patient_row)
        discount_type = string_utils.xstr(patient_row['DiscountType'])

        last_treat_type = registration_utils.get_last_treat_type(self.database, patient_key)
        if treat_type == '內科' and last_treat_type in self.pregnant_treat_type_list:
            treat_type = last_treat_type

        regist_fee = charge_utils.get_regist_fee(
            self.database, self.system_settings,
            string_utils.xstr(patient_row['Birthday']),
            discount_type, '健保', share_type, treat_type, course,
        )
        diag_share_fee = charge_utils.get_diag_share_fee(
            self.database, self.system_settings, share_type, treat_type, course,
        )
        diag_share_discount_fee = charge_utils.get_diag_share_discount_fee(self.database, discount_type)

        if diag_share_discount_fee is not None:
            diag_share_fee = diag_share_discount_fee

        self.payment_row['patient_key'] = patient_key
        self.payment_row['card'] = card
        self.payment_row['course'] = course
        self.payment_row['share_type'] = share_type
        self.payment_row['treat_type'] = treat_type
        self.payment_row['regist_fee'] = regist_fee
        self.payment_row['diag_share_fee'] = diag_share_fee

        total_fee = regist_fee + diag_share_fee

        self.ui.label_1.setText('掛號費')
        self.ui.label_regist_fee.setText(string_utils.xstr(regist_fee))

        self.ui.label_2.setText('門診負擔')
        self.ui.label_share_fee.setText(string_utils.xstr(diag_share_fee))
        self.ui.label_total_fee.setText(string_utils.xstr(total_fee))
        self.ui.label_received_fee.setText('0')

        if regist_type == '門診掛號':
            self._set_outpatient(patient_name, keyword)
        elif regist_type == '預約報到':
            self._set_reservation_arrival(patient_name, keyword)

        self.coinsys.start_payment(total_fee)
        self.detect_payment_thread.set_total_fee(total_fee)
        self.detect_payment_thread.set_label_received_fee(self.ui.label_received_fee)
        self.detect_payment_thread.set_payment_type('掛號繳費')

    def _set_outpatient(self, patient_name, doctor):
        period = registration_utils.get_current_period(self.system_settings)
        room = registration_utils.get_room(self.database, period, doctor)

        reserve_key = None

        reg_no = registration_utils.get_reg_no(
            self.database, self.system_settings, room, doctor, period, reserve_key,
        )  # 取得診號

        self.payment_row['period'] = period
        self.payment_row['room'] = room
        self.payment_row['doctor'] = doctor
        self.payment_row['regist_no'] = reg_no
        self.payment_row['regist_type'] = '一般門診'
        self.payment_row['reserve_key'] = reserve_key

        card = self.payment_row['card']
        if card == '自動取得':
            card = ''
        else:
            if number_utils.get_integer(self.payment_row['course']) >= 1:
                card += f'-{self.payment_row["course"]}'

            card = f'，卡序: {card}'

        message = f'''
            {patient_name} 您好<br>
            <font color="red" size="4">請繳交掛號費用</font><br><br>
            <font color="yellow">繳費的過程中<br>
            請勿將健保卡取出</font><br><br>
            以下是收費明細<br>
        '''
        hint = '''
            注意! <br>
            請勿取出健保卡<br>
            若您正在繳費且尚未繳清<br>
            取出卡片將會取消掛號<br>
            並退還您已繳費的金額
        '''
        self._set_label_message(message, hint)

    def _get_reservation_row(self, reserve_key):
        sql = f'''
            SELECT * FROM reserve
            WHERE
                ReserveKey = {reserve_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return rows[0]

    def _get_reservation_doctor(self, reserve_key):
        sql = f'''
            SELECT * FROM reserve
            WHERE
                ReserveKey = {reserve_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return string_utils.xstr(rows[0]['Doctor'])

    def _set_reservation_arrival(self, patient_name, reserve_key):
        reservation_row = self._get_reservation_row(reserve_key)
        doctor = string_utils.xstr(reservation_row['Doctor'])

        period = registration_utils.get_current_period(self.system_settings)
        room = registration_utils.get_room(self.database, period, doctor)

        reg_no = registration_utils.get_reg_no(
            self.database, self.system_settings, room, doctor, period, reserve_key,
        )  # 取得診號

        self.payment_row['period'] = period
        self.payment_row['room'] = room
        self.payment_row['doctor'] = doctor
        self.payment_row['regist_no'] = reg_no
        self.payment_row['regist_type'] = '預約門診'
        self.payment_row['reserve_key'] = reserve_key

        message = f'''
            {patient_name} 您好<br>
            <font size="5">請繳交掛號費用</font><br><br>
            <font color="yellow">繳費的過程中<br>
            請勿將健保卡取出</font><br><br>
            以下是收費明細<br>
        '''
        hint = '''
            注意! <br>
            請勿取出健保卡<br>
            若您正在繳費且尚未繳清<br>
            取出卡片將會取消預約掛號<br>
            並退還您已繳費的金額
        '''
        self._set_label_message(message, hint)

    def _set_label_message(self, message, hint):
        self.ui.label_message.setText(message)
        self.ui.label_hint.setText(hint)

    def cancel_payment(self, detected):
        self.coinsys.cancel_payment()

        if detected == 'cancel_payment':
            self._back_home()
        elif detected in ['掛號繳費', '批價繳費']:
            if detected == '批價繳費':
                case_key = self.payment_row['case_key']
                try:
                    card = self.payment_row['card']
                    if card in ['', None, '自動取得']:
                        self._rewrite_ic_card(self.payment_row)
                except Exception:
                    pass

                self.ic_card.write_ic_medical_record(case_key, cshis_utils.NORMAL_CARD)
                printer_utils.print_ins_receipt(
                    self, self.database, self.system_settings, case_key, 'print'
                )
                try:
                    if number_utils.get_integer(self.payment_row['total_fee']) > 0:
                        printer_utils.print_misc_form(
                            self, self.database, self.system_settings, case_key, '系統設定')
                except Exception:
                    pass

            self._open_pycashier_completed(detected)

    def detect_ic_card_removed(self):
        self.detect_payment_thread.start()

    def _back_home(self):
        self.parent.open_pycashier_home()

    def _open_pycashier_completed(self, payment_type):
        self.parent.open_pycashier_completed(
            payment_type=payment_type,
            patient_key=self.payment_row['patient_key'],
            period=self.payment_row['period'],
            room=self.payment_row['room'],
            regist_no=self.payment_row['regist_no'],
            doctor=self.payment_row['doctor'],
            card=self.payment_row['card'],
            course=self.payment_row['course'],
            share_type=self.payment_row['share_type'],
            treat_type=self.payment_row['treat_type'],
            regist_type=self.payment_row['regist_type'],
            regist_fee=self.payment_row['regist_fee'],
            diag_share_fee=self.payment_row['diag_share_fee'],
            case_key=self.payment_row['case_key'],
            reserve_key=self.payment_row['reserve_key'],
            drug_share_fee=self.payment_row['drug_share_fee'],
            total_fee=self.payment_row['total_fee'],
        )

    def _rewrite_ic_card(self, payment_row):
        case_key = payment_row['case_key']
        patient_key = payment_row['patient_key']
        patient_row = patient_utils.get_patient_row(self.database, patient_key)
        course = payment_row['course']
        share_type = string_utils.xstr(patient_row['InsType'])
        card = payment_row['card']
        card_abnormal = ''

        if self._write_ic_card(patient_key, course, share_type, cshis_utils.NORMAL_CARD):
            card = self.ic_card.treat_data['seq_number']

        security = self._get_security(self.ic_card, card, card_abnormal)

        fields = ['Card', 'Security']
        data = [card, security]
        self.database.update_record('cases', fields, 'CaseKey', case_key, data)
