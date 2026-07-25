# -*- coding: utf-8 -*-

import datetime
import importlib
import os

from kiosk2.kiosk_pay import KioskPay
from libs import (
    number_utils, string_utils, system_utils, ui_utils)
from PyQt5 import QtCore, QtWidgets


# 2024.06.24 掛號機掛號頁面
class KioskPayment(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(KioskPayment, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None

        self.wait_seconds = 30
        self.home_timer = QtCore.QTimer(self)
        self.home_timer.timeout.connect(self._timeout)

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
            self, '請按繳費按鈕進行繳費!', 310, 1770, self.parent.TEXT_FONT, 42, self.parent.TEXT_COLOR)
        self._bring_to_front(self.label_header)

    # 設定信號
    def _set_signal(self):
        pass

    def _back_to_home(self):
        self.home_timer.stop()
        self.parent.open_kiosk_home()

    def set_payment_data(self, patient_key, identity_type):
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

        # # 檢查是否已經就診
        # if not self._is_medical_record_exists(patient_key):
        #     self._show_no_medical_record()
        #     self._back_to_home()
        #     return

        # 檢查是否就診完成
        case_row = self._get_case_row(patient_key)
        if case_row is None:
            self._show_no_medical_record()
            self._back_to_home()
            return

        if case_row['DoctorDone'] == 'False':
            self._show_not_doctor_done()
            self._back_to_home()
            return

        extra_purchase = False
        if case_row['ChargeDone'] == 'True':
            case_row = self._get_extra_purchase_row(patient_key)
            if case_row is None:
                self._show_charge_done()
                self._back_to_home()
                return
            else:
                extra_purchase = True

        name = string_utils.xstr(patient_row['Name'])
        name = string_utils.remove_not_chinese_character(name)

        label_header = system_utils.set_label(
            self, name + ' 您好', 50, 600, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)
        self._bring_to_front(label_header)

        label_header = system_utils.set_label(
            self, '以下是您今天的門診繳費明細:', 50, 720, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)
        self._bring_to_front(label_header)

        regist_fee = number_utils.get_integer(case_row['RegistFee'])
        self_total_fee = number_utils.get_integer(case_row['TotalFee'])

        if extra_purchase:
            total_amount = self_total_fee
            html = f'''
                <table width="98%" cellpadding="20" celllspacing="30" border="0" style="font-size: 84px;">
                    <tr>
                        <td>加購金額</td>
                        <td align=right>{self_total_fee}</td>
                    </tr>
                    <tr>
                        <td>合計金額</td>
                        <td align=right>{total_amount}</td>
                    </tr>
                </table>
            '''
        else:
            total_amount = regist_fee + self_total_fee
            html = f'''
                <table width="98%" cellpadding="20" celllspacing="30" border="0" style="font-size: 84px;">
                    <tr>
                        <td>掛號費</td>
                        <td align=right>{regist_fee}</td>
                    </tr>
                    <tr>
                        <td>自費金額</td>
                        <td align=right>{self_total_fee}</td>
                    </tr>
                    <tr>
                        <td>合計金額</td>
                        <td align=right>{total_amount}</td>
                    </tr>
                </table>
            '''

        label_html = system_utils.set_label(
            self, html, 200, 850, self.parent.TEXT_FONT, 72, self.parent.TEXT_COLOR)
        self._bring_to_front(label_html)

        self._set_payment_button('開始繳費', case_row['CaseKey'], total_amount)
        self._set_back_home_button('取消')

    def _bring_to_front(self, widget):
        widget.raise_()
        widget.show()

    def _get_current_date(self):
        return datetime.datetime.today().strftime('%Y-%m-%d')

    def _is_medical_record_exists(self, patient_key):
        case_row = self._get_case_row(patient_key)
        if not case_row:
            return False
        else:
            return True

    def _get_case_row(self, patient_key):
        sql = f'''
            SELECT
                CaseKey, Name, RegistFee, TotalFee, DoctorDone, ChargeDone
            FROM cases
            WHERE
                PatientKey = "{patient_key}" AND
                DATE(CaseDate) = "{self._get_current_date()}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return rows[0]
        else:
            return None

    def _get_extra_purchase_row(self, patient_key):
        sql = f'''
            SELECT
                CaseKey, Name, RegistFee, TotalFee, DoctorDone, ChargeDone
            FROM cases
            WHERE
                PatientKey = "{patient_key}" AND
                DATE(CaseDate) = "{self._get_current_date()}" AND
                ChargeDone = "False" AND
                TreatType = "加購"
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

    def _show_no_medical_record(self):
        from kiosk2.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_no_medical_record()
        dialog.exec_()
        del dialog

    def _show_not_doctor_done(self):
        from kiosk2.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_not_doctor_done()
        dialog.exec_()
        del dialog

    def _show_charge_done(self):
        from kiosk2.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_charge_done()
        dialog.exec_()
        del dialog

    def _set_back_home_button(self, button_text):
        self.wait_seconds = 30
        self.button_text_home = button_text
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
        system_utils.shadow_widget(self, self.push_button_home)
        self.push_button_home.move(x, y)
        self.push_button_home.raise_()
        self.push_button_home.show()
        self.push_button_home.clicked.connect(self._back_to_home)

        self.home_timer.start(1000)

    def _timeout(self):
        if not self.isVisible():
            self.home_timer.stop()
            return

        self.wait_seconds -= 1
        self.push_button_home.setText(f'{self.button_text_home}({self.wait_seconds}s)')
        if self.wait_seconds == 0:
            self._back_to_home()

    def _set_payment_button(self, button_text, case_key, total_amount):
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
        system_utils.shadow_widget(self, push_button)
        push_button.move(x, y)
        push_button.raise_()
        push_button.show()
        push_button.clicked.connect(lambda: self._open_kiosk_pay(case_key, total_amount))

    def _open_kiosk_pay(self, case_key, total_amount):
        self.home_timer.stop()
        self.hide()

        pay_dialog = KioskPay(self, self.database, self.system_settings, case_key, total_amount)
        pay_dialog.set_payment_data()
        result = pay_dialog.exec_()
        change_due = pay_dialog.get_change_due()
        pay_dialog.deleteLater()

        if result == QtWidgets.QDialog.Accepted:
            # 支付成功，導航到完成頁面
            self.parent.open_kiosk_completed('批價作業', change_due=change_due)
        elif result == QtWidgets.QDialog.Rejected:
            self.parent.open_kiosk_home()
