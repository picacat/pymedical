# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QCoreApplication
import datetime
import importlib
import os

from libs import log_utils
from libs import string_utils
from libs import case_utils
from libs import date_utils
from libs import number_utils
from libs import registration_utils
from libs import nhi_utils
from libs import charge_utils
from libs import ui_utils
from libs import system_utils


# 2024.06.24 掛號機掛號頁面
class KioskRegistration(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(KioskRegistration, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ic_card = args[2]
        self.case_key = None
        self.patient_key = None
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
            self, self.parent.clinic_name, 50, 35, self.parent.TEXT_FONT, 56, self.parent.LIGHT_TEXT_COLOR)
        self._bring_to_front(label_header)

        label_header = system_utils.set_label(
            self, '掛號繳費系統', 210, 300, self.parent.TEXT_FONT, 84, self.parent.LIGHT_TEXT_COLOR)
        self._bring_to_front(label_header)

        label_header = system_utils.set_label(
            self, '掛號過程中，請勿取出健保卡', 310, 1770, self.parent.TEXT_FONT, 42, self.parent.TEXT_COLOR)
        self._bring_to_front(label_header)

    # 設定信號
    def _set_signal(self):
        pass

    def _back_to_home(self):
        self.parent.open_kiosk_home()

    def set_registration_data(self, treat_type):
        # self.treat_type, self.card, self.course = self._auto_completion_course(1)
        # print(self.treat_type, self.card, self.course)

        self.clear_all_widgets()
        self.set_background()

        dialog = self.parent.show_in_progress()
        QCoreApplication.processEvents()
        ic_card_read = self.ic_card.read_register_basic_data(show_warning=False)
        dialog.close()

        if not ic_card_read:
            self._show_no_iccard()
            self._back_to_home()
            return

        available_date, available_count = self.ic_card.get_card_status()
        self.ic_card.basic_data['card_valid_date'] = available_date
        self.ic_card.basic_data['card_available_count'] = available_count

        patient_id = self.ic_card.basic_data['patient_id']
        sql = f'''
            SELECT * FROM patient
            WHERE
                ID = "{patient_id}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:  # 找不到資料
            self._show_no_patient()
            self._back_to_home()
            return

        patient_row = rows[0]
        self.patient_key = patient_row['PatientKey']

        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                PatientKey = "{self.patient_key}" AND
                DATE(CaseDate) = "{datetime.datetime.today().strftime('%Y-%m-%d')}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            self._show_already_registed()
            self._back_to_home()
            return

        today = datetime.date.today()
        last_treat_date = (today - datetime.timedelta(days=30-1)).strftime('%Y-%m-%d 00:00:00')
        sql = f'''
            SELECT CaseDate, RegistType, TreatType, Card, Continuance, Share, Injury, XCard, Massager FROM cases
            WHERE
                (CaseDate >= "{last_treat_date}") AND
                (PatientKey = {self.patient_key}) AND
                (InsType = "健保")
            ORDER BY CaseDate DESC LIMIT 1
        '''

        rows = self.database.select_record(sql)
        if rows:
            card = rows[0]['Card']
            if card == '欠卡':
                self._show_deposit_card_not_return()
                self._back_to_home()
                return

        if treat_type == '內科':
            start_date, end_date, pres_days, remain_days = registration_utils.check_prescription_finished(       # 檢查上次健保給藥是否服藥完畢
                self.database, self.system_settings, None, self.patient_key, manual_message=True
            )
            if start_date is not None and remain_days >= 1:  # 上次開藥還有1天
                self._show_prescript_not_finished(start_date, end_date, pres_days, remain_days)
                self._back_to_home()
                return

        name = string_utils.xstr(patient_row['Name'])

        label_header = system_utils.set_label(
            self, name + ' 您好', 50, 600, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)
        self._bring_to_front(label_header)

        label_header = system_utils.set_label(
            self, '以下是本次門診收費明細:', 50, 720, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)
        self._bring_to_front(label_header)

        visit = '複診'
        ins_type = '健保'
        regist_type = '一般門診'
        share_type = nhi_utils.get_share_type(string_utils.xstr(patient_row['InsType']).strip(None))
        discount_type = string_utils.xstr(patient_row['DiscountType'])
        
        birth_date = patient_row['Birthday']
        if birth_date is None:
            birth_date = ''
        else:
            birth_date = birth_date.strftime('%Y-%m-%d')

        # if treat_type == '內科':
        #     self.treat_type, self.card, self.course = treat_type, '自動取得', None
        # else:
        #     treat_type = '一般針灸'

        self.treat_type, self.card, self.course = self._auto_completion_course(self.patient_key)
        if self.card in ['自動取得']:
            self.treat_type, self.course = treat_type, None

        self.regist_fee = charge_utils.get_regist_fee(
            self.database, self.system_settings,
            birth_date,
            discount_type,
            ins_type,
            share_type,
            self.treat_type,
            self.course,
            visit,
        )
        self.diag_share_fee = charge_utils.get_diag_share_fee(
            self.database, self.system_settings,
            share_type,
            self.treat_type,
            self.course,
            regist_type,
        )
        diag_share_discount_fee = charge_utils.get_diag_share_discount_fee(
            self.database, discount_type
        )

        if diag_share_discount_fee is not None:
            self.diag_share_fee = diag_share_discount_fee

        self.total_amount = self.regist_fee + self.diag_share_fee

        html = f'''
            <table width="98%" cellpadding="20" celllspacing="30" border="0" style="font-size: 84px;">
                <tr>
                    <td>掛號費</td>
                    <td align=right>{self.regist_fee}</td>
                </tr>
                <tr>
                    <td>門診負擔</td>
                    <td align=right>{self.diag_share_fee}</td>
                </tr>
                <tr>
                    <td>合計金額</td>
                    <td align=right>{self.total_amount}</td>
                </tr>
            </table>
        '''

        label_html = system_utils.set_label(
            self, html, 200, 850, self.parent.TEXT_FONT, 72, self.parent.TEXT_COLOR)
        self._bring_to_front(label_html)

        self._set_payment_button('掛號並繳費')
        self._set_back_home_button('取消掛號')

    def _bring_to_front(self, widget):
        widget.raise_()
        widget.show()

    def _get_reserve_row(self, patient_key):
        current_date = datetime.datetime.today().strftime('%Y-%m-%d')
        sql = f'''
            SELECT * FROM reserve
            WHERE
                PatientKey = "{patient_key}" AND
                DATE(ReserveDate) = "{current_date}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return rows[0]
        else:
            return None

    def _show_no_iccard(self):
        from kiosk1.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_no_iccard()
        dialog.exec_()
        del dialog

    def _show_no_patient(self):
        from kiosk1.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_no_patient()
        dialog.exec_()
        del dialog

    def _show_already_registed(self):
        from kiosk1.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_already_registed()
        dialog.exec_()
        del dialog

    def _show_deposit_card_not_return(self):
        from kiosk1.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_deposit_card_not_return()
        dialog.exec_()
        del dialog

    def _show_prescript_not_finished(self, start_date, end_date, pres_days, remain_days):
        from kiosk1.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.show_prescript_not_finished(start_date, end_date, pres_days, remain_days)
        dialog.exec_()
        del dialog

    def _show_arrival_done(self):
        from kiosk1.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_arrival_done()
        dialog.exec_()
        del dialog

    def _set_back_home_button(self, button_text):
        color = self.parent.DARK_RED
        x, y = 600, 1400
        push_button = QtWidgets.QPushButton(self)
        push_button.resize(400, 100)
        push_button.setText(button_text)
        push_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};  /* 正常狀態背景顏色 */
                border: 2px solid {color};  /* 邊框顏色 */
                border-radius: 10px;        /* 圓角 */
                color: white;               /* 字體顏色 */
                font: 75 56pt "{self.parent.BUTTON_FONT}";
            }}
        """)
        push_button.move(x, y)
        push_button.raise_()
        push_button.show()
        push_button.clicked.connect(self._back_to_home)

    def _set_payment_button(self, button_text):
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
                font: 75 56pt "{self.parent.BUTTON_FONT}";
            }}
        """)
        push_button.move(x, y)
        push_button.raise_()
        push_button.show()
        push_button.clicked.connect(self._set_payment_data)

    def _set_payment_data(self):
        self.parent.open_kiosk_payment(
            self.patient_key, self.treat_type, self.card, self.course, self.regist_fee, self.diag_share_fee)

    # 自動連續療程 - 30天內.
    def _auto_completion_course(self, patient_key):
        today = datetime.date.today()
        default_card = '自動取得'
        treat_type = '一般針灸'
        last_treat_date = (today - datetime.timedelta(days=30-1)).strftime('%Y-%m-%d 00:00:00')

        sql = f'''
            SELECT CaseDate, RegistType, TreatType, Card, Continuance, Share, Injury, XCard, Massager FROM cases
            WHERE
                (CaseDate >= "{last_treat_date}") AND
                (PatientKey = {patient_key}) AND
                (InsType = "健保") AND
                (Continuance >= 1)
            ORDER BY CaseDate DESC LIMIT 1
        '''

        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return treat_type, default_card, None

        row = rows[0]
        treat_type = string_utils.xstr(row['TreatType'])

        if treat_type in nhi_utils.PREGNANT_CARE_TREAT + ['慢性腎病照護']:  # 助孕照護，保胎照護、慢性腎病照護要續療程
            pass
        elif treat_type in nhi_utils.IMPROVE_CARE_TREAT:  # 加強照護除外
            return treat_type, default_card, None

        # 2019.04.29 上次為內科, 為避免療程中刷卡, 不要自動續療程
        if number_utils.get_integer(row['Continuance']) <= 0:
            return treat_type, default_card, None

        card = string_utils.xstr(row['Card'])
        if number_utils.get_integer(row['Continuance']) >= 6:  # 正常卡序療程已滿
            return treat_type, default_card, None

        course = string_utils.xstr(row['Continuance'] + 1)  # 療程自動續1次

        return treat_type, card, course
