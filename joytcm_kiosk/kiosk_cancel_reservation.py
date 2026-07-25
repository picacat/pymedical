# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui
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
from libs import patient_utils
from libs import charge_utils
from libs import system_utils
from libs import nhi_utils


# 2025.03.22 掛號機取消預約掛號頁面
class KioskCancelReservation(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(KioskCancelReservation, self).__init__(parent)
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
        system_utils.set_image(self, os.path.join(self.parent.IMAGE_DIR, 'home.png'), 0, 0)

    # 設定信號
    def _set_signal(self):
        pass

    def _back_to_home(self):
        self.parent.open_kiosk_home()

    def set_cancel_reservation(self):
        dialog = self.parent.show_in_progress()
        # 強制刷新事件循環，確保對話框立即顯示
        QCoreApplication.processEvents()

        read_ic_card = self.ic_card.read_register_basic_data(show_warning=False)
        dialog.close()

        if not read_ic_card:
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

        row = rows[0]
        patient_key = row['PatientKey']
        reserve_row = self._get_reserve_row(patient_key)
        if reserve_row is None:
            self._show_no_reservation()
            self._back_to_home()
            return

        current_date = datetime.datetime.today().strftime('%Y-%m-%d')
        if reserve_row['ReserveDate'].date().strftime('%Y-%m-%d') == current_date:
            self._show_cancel_not_today()
            self._back_to_home()
            return

        self._query_cancel_reservation(reserve_row)
        self._back_to_home()

    def _get_reserve_row(self, patient_key):
        current_date = datetime.datetime.today().strftime('%Y-%m-%d')
        sql = f'''
            SELECT * FROM reserve
            WHERE
                PatientKey = "{patient_key}" AND
                Arrival = "False" AND
                DATE(ReserveDate) >= "{current_date}"
            ORDER BY ReserveDate LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return rows[0]
        else:
            return None

    def _show_no_iccard(self):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_no_iccard()
        dialog.exec_()
        del dialog

    def _show_write_iccard_error(self, error_code):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_write_iccard_error(error_code)
        dialog.exec_()
        del dialog

    def _show_no_patient(self):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_no_patient()
        dialog.exec_()
        del dialog

    def _show_no_reservation(self):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_no_reservation()
        dialog.exec_()
        del dialog

    def _show_cancel_not_today(self):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_cancel_not_today()
        dialog.exec_()
        del dialog

    def _show_already_arrival(self):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_already_arrival()
        dialog.exec_()
        del dialog

    def _query_self_pay_case(self, reserve_row, start_date, end_date, pres_days, remain_days):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.query_self_pay_case(reserve_row, start_date, end_date, pres_days, remain_days)
        dialog.exec_()
        self_pay_case = dialog.get_self_pay_case()
        del dialog

        return self_pay_case

    def _show_cancel_done(self):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.set_cancel_done()
        dialog.exec_()
        del dialog

    # 詢問是否預約報到
    def _query_cancel_reservation(self, reserve_row):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self.parent, self.database, self.system_settings)
        dialog.cancel_reservation(reserve_row)
        dialog.exec_()
        cancel_reservation = dialog.get_cancel()
        del dialog

        if cancel_reservation:
            dialog = self.parent.show_in_progress()
            # 強制刷新事件循環，確保對話框立即顯示
            QCoreApplication.processEvents()

            self._cancel_reservation(reserve_row)
            dialog.close()

    # 確定取消預約報到
    def _cancel_reservation(self, reserve_row):
        reserve_key = reserve_row['ReserveKey']
        sql = f'''
            DELETE FROM reserve
            WHERE
                ReserveKey = {reserve_key}
        '''
        self.database.exec_sql(sql)
        self._show_cancel_done()
