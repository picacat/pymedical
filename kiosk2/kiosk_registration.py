# -*- coding: utf-8 -*-

import datetime
import importlib
import os

from libs import (
    string_utils, system_utils, ui_utils, registration_utils, charge_utils, log_utils)
from PyQt5 import QtCore, QtWidgets


# 2024.06.24 掛號機掛號頁面
class KioskRegistration(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(KioskRegistration, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None

        self.home_timer = QtCore.QTimer(self)
        self.home_timer.timeout.connect(self._timeout)
        self.wait_seconds = 30

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
        self.ui = ui_utils.load_ui_file(os.path.join(self.parent.UI_DIR, 'kiosk_home.ui'), self)
        self.set_background()

    # 刪除所有控件
    def clear_all_widgets(self):
        for widget in self.findChildren(QtWidgets.QWidget):
            widget.setParent(None)
            widget.deleteLater()

    def set_background(self):
        label_background = system_utils.set_image(
            self, os.path.join(self.parent.IMAGE_DIR, 'background.png'), 0, 0)
        self._bring_to_front(label_background)

        label_header = system_utils.set_label(
            self, self.parent.clinic_name, 50, 35, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)
        self._bring_to_front(label_header)

        label_header = system_utils.set_label(
            self, '掛號繳費系統', 210, 300, self.parent.TEXT_FONT, 84, self.parent.TEXT_COLOR)
        self._bring_to_front(label_header)

        self.label_header = system_utils.set_label(
            self, '報到後請至候診區等候，謝謝!', 310, 1770, self.parent.TEXT_FONT, 42, self.parent.TEXT_COLOR)
        self._bring_to_front(self.label_header)

    # 設定信號
    def _set_signal(self):
        pass

    def _back_to_home(self):
        self.home_timer.stop()
        self.parent.open_kiosk_home()

    def set_registration_data(self, patient_key, identity_type):
        self.clear_all_widgets()
        self.set_background()

        if identity_type == '讀取健保卡':
            self.label_header.setText('請別忘了取回健保卡喔!')

        patient_row = self._get_patient_row(patient_key)
        if not patient_row:  # 找不到資料
            self._show_no_patient()
            self._back_to_home()
            return

        patient_key = patient_row['PatientKey']

        # 檢查今天是否有預約
        if not self._is_reservation_today(patient_key):
            self._show_no_reservation()
            self._back_to_home()
            return

        # 檢查今天是否已經報到
        if self._is_arrival(patient_key):
            self._show_arrival_done()
            self._back_to_home()
            return

        # 檢查是否已經掛號
        if self._is_registered(patient_key):
            self._show_already_registed()
            self._back_to_home()
            return

        name = string_utils.xstr(patient_row['Name'])
        debt_mark = name[-1]
        name = string_utils.remove_not_chinese_character(name)

        debt_hint = ''
        if debt_mark == '$':
            debt_hint = '''
                <tr>
                    <td colspan="2" style="color: red;">您尚有欠款未結</td>
                </tr>
                <tr>
                    <td colspan="2" style="color: red;">請與櫃台聯絡</td>
                </tr>
            '''
        elif debt_mark == '#':
            debt_hint = '''
                <tr>
                    <td colspan="2" style="color: red;">您上次找零未取</td>
                </tr>
                <tr>
                    <td colspan="2" style="color: red;">請與櫃台聯絡</td>
                </tr>
            '''

        label_header = system_utils.set_label(
            self, name + ' 您好', 50, 600, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)
        self._bring_to_front(label_header)

        label_header = system_utils.set_label(
            self, '以下是您今天的預約明細:', 50, 720, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)
        self._bring_to_front(label_header)

        row = self._get_reserve_row(patient_key)
        html = f'''
            <table width="98%" cellpadding="20" celllspacing="30" border="0" style="font-size: 84px;">
                <tr>
                    <td>預約班別:</td>
                    <td align=left>{row["Period"]}</td>
                </tr>
                <tr>
                    <td>預約醫師:</td>
                    <td align=left>{row["Doctor"]}</td>
                </tr>
                {debt_hint}
            </table>
        '''

        label_html = system_utils.set_label(
            self, html, 200, 850, self.parent.TEXT_FONT, 72, self.parent.TEXT_COLOR)
        self._bring_to_front(label_html)

        self._set_arrival_button('完成報到', patient_key)
        self._set_back_home_button('取消')

    def _bring_to_front(self, widget):
        widget.raise_()
        widget.show()

    def _get_current_date(self):
        return datetime.datetime.today().strftime('%Y-%m-%d')

    def _is_reservation_today(self, patient_key):
        row = self._get_reserve_row(patient_key)
        if not row:
            return False
        else:
            return True

    def _is_arrival(self, patient_key):
        reserve_row = self._get_reserve_row(patient_key)
        if not reserve_row or reserve_row['Arrival'] == 'False':
            return False
        else:
            return True

    def _is_registered(self, patient_key):
        case_row = self._get_case_row(patient_key)
        if not case_row:
            return False
        else:
            return True

    def _get_reserve_row(self, patient_key):
        sql = f'''
            SELECT * FROM reserve
            WHERE
                PatientKey = "{patient_key}" AND
                DATE(ReserveDate) = "{self._get_current_date()}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return rows[0]
        else:
            return None

    def _get_case_row(self, patient_key):
        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                PatientKey = "{patient_key}" AND
                DATE(CaseDate) = "{self._get_current_date()}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return rows[0]
        else:
            return None

    def _get_patient_row(self, patient_key):
        sql = f'''
            SELECT PatientKey, Name, Birthday, DiscountType FROM patient
            WHERE
                PatientKey = "{patient_key}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return rows[0]
        else:
            return None

    def _show_no_patient(self):
        from kiosk2.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_no_patient()
        dialog.exec_()
        del dialog

    def _show_no_reservation(self):
        from kiosk2.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_no_reservation()
        dialog.exec_()
        del dialog

    def _show_already_registed(self):
        from kiosk2.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_already_registed()
        dialog.exec_()
        del dialog

    def _show_arrival_done(self):
        from kiosk2.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_arrival_done()
        dialog.exec_()
        del dialog

    def _set_back_home_button(self, button_text):
        self.button_text_home = button_text
        self.wait_seconds = 30
        color = self.parent.DARK_RED
        x, y = 600, 1400

        self.push_button_home = QtWidgets.QPushButton(self)
        self.push_button_home.resize(400, 100)
        self.push_button_home.setText(f'{self.button_text_home}({self.wait_seconds}s)')
        self.push_button_home.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};  /* 正常狀態背景顏色 */
                border: 2px solid {color};  /* 邊框顏色 */
                border-radius: 10px;        /* 圓角 */
                color: white;               /* 字體顏色 */
                font: 75 42pt "{self.parent.BUTTON_FONT}";
            }}
        """)
        self.push_button_home.move(x, y)
        system_utils.shadow_widget(self, self.push_button_home)
        self.push_button_home.raise_()
        self.push_button_home.show()
        self.push_button_home.clicked.connect(self._back_to_home)

        self.home_timer.start(1000)

    def _timeout(self):
        # 如果視窗已經被關掉 / 看不到，就不要再跑倒數
        if not self.isVisible():
            self.home_timer.stop()
            return

        self.wait_seconds -= 1
        self.push_button_home.setText(f'{self.button_text_home}({self.wait_seconds}s)')
        if self.wait_seconds == 0:
            self._back_to_home()

    def _set_arrival_button(self, button_text, patient_key):
        color = self.parent.DARK_GREEN
        x, y = 100, 1400
        push_button = QtWidgets.QPushButton(self)
        push_button.resize(450, 100)
        push_button.setText(button_text)
        push_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};  /* 正常狀態背景顏色 */
                border: 2px solid {color};  /* 邊框顏色 */
                border-radius: 10px;        /* 圓角 */
                color: white;               /* 字體顏色 */
                font: 75 42pt "{self.parent.BUTTON_FONT}";
            }}
        """)
        push_button.move(x, y)
        system_utils.shadow_widget(self, push_button)
        push_button.raise_()
        push_button.show()
        push_button.clicked.connect(lambda: self._finish_registration(patient_key=patient_key))

    def _finish_registration(self, patient_key):
        case_row = self._insert_medical_record(patient_key)
        self._insert_wait(case_row)
        self._update_reserve(case_row['reserve_key'])

        self._write_event_log(case_row)
        self._send_socket_data(case_row)

        self.parent.open_kiosk_completed('預約報到', case_row['case_key'])

    def _write_event_log(self, case_record):
        log = f"{case_record['name']}於{case_record['case_date']}完成掛號機預約報到"

        if case_record['regist_fee'] != 0:
            log += f', 掛號費: {case_record["regist_fee"]}'

        log_utils.write_event_log(
            self.database, '掛號機',
            '掛號機預約報到', '門診掛號', log
        )

    # 新增病歷
    def _insert_medical_record(self, patient_key):
        patient_row = self._get_patient_row(patient_key)
        reserve_row = self._get_reserve_row(patient_key)
        reserve_key = reserve_row['ReserveKey']

        ins_type = '自費'
        share_type = '基層醫療'
        treat_type = '內科'
        period = registration_utils.get_current_period(self.system_settings)
        doctor = reserve_row['Doctor']
        room = reserve_row['Room']

        reg_no = registration_utils.get_reg_no(
            self.database, self.system_settings, room, doctor, period, reserve_key,
        )

        try:
            birthday = patient_row['Birthday'].strftime('%Y-%m-%d')
        except Exception:
            birthday = ''

        regist_fee = charge_utils.get_regist_fee(
            self.database, self.system_settings,
            birthday,
            string_utils.xstr(patient_row['DiscountType']),
            ins_type, share_type, treat_type,
        )

        case_row = {
            'case_date': string_utils.xstr(datetime.datetime.now()),
            'patient_key': patient_key,
            'reserve_key': reserve_key,
            'name': string_utils.xstr(patient_row['Name']),
            'visit': '複診',
            'regist_type': '預約門診',
            'treat_type': treat_type,
            'share_type': share_type,
            'injury_type': '普通疾病',
            'ins_type': ins_type,
            'card': '免卡',
            'period': period,
            'room': room,
            'regist_no': reg_no,
            'registrar': '掛號機',
            'regist_fee': regist_fee,
            'diag_share_fee': 0,
            's_diag_share_fee': 0,
            'deposit_fee': 0,
            'doctor': doctor,
            'doctor_done': 'False',
            'regist_payment_type': '現金',
        }

        fields = [
            'CaseDate', 'PatientKey', 'Name', 'Visit', 'RegistType', 'Injury',
            'TreatType', 'Share', 'InsType', 'Card', 'Room', 'Period', 'RegistNo', 'Register',
            'RegistFee', 'DiagShareFee', 'SDiagShareFee', 'DepositFee',
            'Doctor', 'RegistPaymentType', 'DoctorDone',
        ]

        data = [
            case_row['case_date'],
            case_row['patient_key'],
            case_row['name'],
            case_row['visit'],
            case_row['regist_type'],
            case_row['injury_type'],
            case_row['treat_type'],
            case_row['share_type'],
            case_row['ins_type'],
            case_row['card'],
            case_row['room'],
            case_row['period'],
            case_row['regist_no'],
            case_row['registrar'],

            case_row['regist_fee'],
            case_row['diag_share_fee'],
            case_row['s_diag_share_fee'],
            case_row['deposit_fee'],

            case_row['doctor'],
            case_row['regist_payment_type'],
            case_row['doctor_done'],
        ]

        case_key = self.database.insert_record('cases', fields, data)
        case_row['case_key'] = case_key

        return case_row

    def _insert_wait(self, case_row):
        fields = [
            'CaseKey', 'CaseDate', 'PatientKey', 'Name', 'Visit', 'RegistType',
            'TreatType', 'Share', 'InsType', 'Card', 'Period',
            'Room', 'RegistNo', 'Doctor', 'DoctorDone',
        ]
        data = [
            case_row['case_key'],
            case_row['case_date'],
            case_row['patient_key'],
            case_row['name'],
            case_row['visit'],
            case_row['regist_type'],
            case_row['treat_type'],
            case_row['share_type'],
            case_row['ins_type'],
            case_row['card'],
            case_row['period'],
            case_row['room'],
            case_row['regist_no'],
            case_row['doctor'],
            case_row['doctor_done'],
        ]
        self.database.insert_record('wait', fields, data)

    def _update_reserve(self, reserve_key):
        sql = f"""
            UPDATE reserve
            SET
                Arrival = "True"
            WHERE
                ReserveKey = {reserve_key}
        """
        self.database.exec_sql(sql)

    def _send_socket_data(self, case_row):
        self.parent.socket_client.send_data(
            ','.join([
                self.system_settings.field('院所名稱'),
                '門診掛號',
                string_utils.xstr(case_row['doctor']),
                string_utils.xstr(case_row['room']),
            ])
        )
