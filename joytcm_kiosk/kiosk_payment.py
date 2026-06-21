# -*- coding: UTF-8 -*-

import datetime
import gc
import importlib
import os

from PyQt5 import QtWidgets
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtGui import QPixmap

from libs import (
    class_utils,
    cshis_utils,
    date_utils,
    number_utils,
    printer_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 2024.09.30 掛號機批價繳費頁面
class KioskPayment(QtWidgets.QMainWindow):
    ICON_W = 64
    ICON_H = 64
    HEADER_SIZE = 32
    HEADER_COLOR = "black"
    ROW1 = 680
    ROW2 = 795
    ROW3 = 910
    ROW4 = 1025

    COL1 = 480
    COL2 = 990

    # 初始化
    def __init__(self, parent=None, *args):
        super(KioskPayment, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ic_card = args[2]
        self.case_key = None
        self.patient_key = None
        self.ui = None
        self.home_image = None

        self.current_date = datetime.datetime.today().strftime("%Y-%m-%d")
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
        self.ui = ui_utils.load_ui_file(
            os.path.join(self.parent.UI_DIR, "kiosk_payment.ui"), self
        )

    def _set_table_layout(self):
        image = system_utils.set_image(
            self,
            os.path.join(self.parent.IMAGE_DIR, "ok.png"),
            40,
            530,
            width=self.ICON_W,
            height=self.ICON_H,
        )
        self._bring_to_front(image)

        self.label_title = system_utils.set_label(
            self,
            "請確認XXX今日的繳費明細",
            130,
            530,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
        )
        self._bring_to_front(self.label_title)

        self.button_cancel = system_utils.set_button(
            self,
            "取消繳費",
            "white",
            40,
            1680,
            self.parent.BUTTON_FONT,
            self.parent.RED,
            self.parent.BUTTON_FONT_SIZE,
            340,
            self.parent.BUTTON_HEIGHT,
            self._back_to_home,
        )
        self._bring_to_front(self.button_cancel)

        button_ok = system_utils.set_button(
            self,
            "確認並開始繳費",
            "white",
            600,
            1170,
            self.parent.BUTTON_FONT,
            self.parent.DARK_GREEN,
            self.parent.BUTTON_FONT_SIZE,
            360,
            self.parent.BUTTON_HEIGHT,
            self._ready_to_payment,
            center=True,
        )
        self._bring_to_front(button_ok)

        self.label_image = system_utils.set_image(
            self, os.path.join(self.parent.IMAGE_DIR, "charge_table.png"), 32, 640
        )
        self._bring_to_front(self.label_image)

    def _bring_to_front(self, widget):
        widget.raise_()
        widget.show()

    def _align_right(self, label, x_pos, y, margin=0):
        label.adjustSize()  # 確保 QLabel 尺寸根據內容調整
        label_width = label.width()
        x = x_pos - label_width - margin
        label.move(x, y)

    def set_payment_table(self):
        self._set_table_layout()

        header = system_utils.set_label(
            self,
            "看診醫師",
            75,
            self.ROW1,
            self.parent.TEXT_FONT,
            self.HEADER_SIZE,
            self.HEADER_COLOR,
        )
        self._bring_to_front(header)

        self.label_doctor = system_utils.set_label(
            self,
            "黃子玶",
            345,
            self.ROW1,
            self.parent.TEXT_FONT,
            self.HEADER_SIZE,
            self.HEADER_COLOR,
        )
        self._bring_to_front(self.label_doctor)
        self._align_right(self.label_doctor, self.COL1, self.ROW1)

        header = system_utils.set_label(
            self,
            "掛號費",
            602,
            self.ROW1,
            self.parent.TEXT_FONT,
            self.HEADER_SIZE,
            self.HEADER_COLOR,
        )
        self._bring_to_front(header)

        self.label_regist_fee = system_utils.set_label(
            self,
            "250元",
            0,
            self.ROW1,
            self.parent.TEXT_FONT,
            self.HEADER_SIZE,
            self.HEADER_COLOR,
        )
        self._bring_to_front(self.label_regist_fee)
        self._align_right(self.label_regist_fee, self.COL2, self.ROW1)

        header = system_utils.set_label(
            self,
            "門診負擔",
            75,
            self.ROW2,
            self.parent.TEXT_FONT,
            self.HEADER_SIZE,
            self.HEADER_COLOR,
        )
        self._bring_to_front(header)

        self.label_diag_share_fee = system_utils.set_label(
            self,
            "50元",
            0,
            self.ROW2,
            self.parent.TEXT_FONT,
            self.HEADER_SIZE,
            self.HEADER_COLOR,
        )
        self._bring_to_front(self.label_diag_share_fee)
        self._align_right(self.label_diag_share_fee, self.COL1, self.ROW2)

        header = system_utils.set_label(
            self,
            "藥品負擔",
            585,
            self.ROW2,
            self.parent.TEXT_FONT,
            self.HEADER_SIZE,
            self.HEADER_COLOR,
        )
        self._bring_to_front(header)

        self.label_drug_share_fee = system_utils.set_label(
            self,
            "40元",
            0,
            self.ROW2,
            self.parent.TEXT_FONT,
            self.HEADER_SIZE,
            self.HEADER_COLOR,
        )
        self._bring_to_front(self.label_drug_share_fee)
        self._align_right(self.label_drug_share_fee, self.COL2, self.ROW2)

        header = system_utils.set_label(
            self,
            "自費金額",
            75,
            self.ROW3,
            self.parent.TEXT_FONT,
            self.HEADER_SIZE,
            self.HEADER_COLOR,
        )
        self._bring_to_front(header)

        self.label_total_fee = system_utils.set_label(
            self,
            "160元",
            345,
            self.ROW3,
            self.parent.TEXT_FONT,
            self.HEADER_SIZE,
            self.HEADER_COLOR,
        )
        self._bring_to_front(self.label_total_fee)
        self._align_right(self.label_total_fee, self.COL1, self.ROW3)

        header = system_utils.set_label(
            self,
            "費用總計",
            75,
            self.ROW4,
            self.parent.TEXT_FONT,
            self.HEADER_SIZE,
            self.HEADER_COLOR,
        )
        self._bring_to_front(header)

        self.label_total_amount = system_utils.set_label(
            self,
            "500元整",
            345,
            self.ROW4,
            self.parent.TEXT_FONT,
            self.HEADER_SIZE,
            self.HEADER_COLOR,
        )
        self._bring_to_front(self.label_total_amount)

    def _set_bottom_image(self):
        image = system_utils.set_image(
            self, os.path.join(self.parent.IMAGE_DIR, "bottom.png"), -23, 1773
        )
        image.raise_()
        image.show()

        image = system_utils.set_image(
            self, os.path.join(self.parent.IMAGE_DIR, "scan_me.png"), 838, 1628
        )
        image.raise_()
        image.show()

        image = system_utils.set_image(
            self,
            os.path.join(self.parent.IMAGE_DIR, "qrcode.png"),
            868,
            1700,
            width=160,
            height=160,
        )
        image.raise_()
        image.show()

    # 設定信號
    def _set_signal(self):
        pass

    def _back_to_home(self):
        self.parent.open_kiosk_home()

    def _set_home_image(self):
        self.home_image = system_utils.set_image(
            self, os.path.join(self.parent.IMAGE_DIR, "home.png"), 0, 0
        )
        self.home_image.raise_()
        self.home_image.show()

    def reset_central_widget(self):
        central_widget = self.centralWidget()
        if central_widget:
            # 刪除現有的中央控件
            self.setCentralWidget(None)
            central_widget.deleteLater()

        # 創建一個新的中央控件
        new_central_widget = QtWidgets.QWidget()
        self.setCentralWidget(new_central_widget)

    # 刪除所有控件
    def clear_all_widgets(self):
        for widget in self.findChildren(QtWidgets.QWidget):
            widget.setParent(None)
            widget.deleteLater()

    def set_payment_data(self):
        self.clear_all_widgets()
        self._set_bottom_image()

        dialog = self.parent.show_in_progress()
        QCoreApplication.processEvents()

        ic_card_read = self.ic_card.read_register_basic_data(show_warning=False)
        dialog.close()

        if not ic_card_read:
            self._set_home_image()
            self._show_no_iccard()
            self._back_to_home()
            return

        available_date, available_count = self.ic_card.get_card_status()
        self.ic_card.basic_data["card_valid_date"] = available_date
        self.ic_card.basic_data["card_available_count"] = available_count

        patient_id = self.ic_card.basic_data["patient_id"]
        sql = f'''
            SELECT * FROM patient
            WHERE
                ID = "{patient_id}"
        '''
        patient_rows = self.database.select_record(sql)
        if len(patient_rows) <= 0:  # 找不到資料
            self._set_home_image()
            self._show_no_patient()
            self._back_to_home()
            return

        patient_row = patient_rows[0]
        patient_key = patient_row["PatientKey"]

        sql = f'''
            SELECT CaseKey, Name, Doctor, RegistFee, SDiagShareFee, SDrugShareFee, TotalFee FROM cases
            WHERE
                PatientKey = "{patient_key}" AND
                DATE(CaseDate) = "{self.current_date}"
        '''
        case_rows = self.database.select_record(sql)
        if len(case_rows) <= 0:
            self._set_home_image()
            self._show_no_case_record()
            self._back_to_home()
            return

        case_row = case_rows[0]
        self.case_key = case_row["CaseKey"]

        if not self._is_doctor_done(patient_key):
            self._set_home_image()
            self._show_not_doctor_done()
            self._back_to_home()
            return

        if self._is_charge_done(patient_key):
            self._set_home_image()
            self._show_already_payment()
            self._back_to_home()
            return

        self._show_charge_table(case_row)

    def _is_doctor_done(self, patient_key):
        sql = f'''
            SELECT DoctorDone FROM cases
            WHERE
                PatientKey = "{patient_key}" AND
                DATE(CaseDate) = "{self.current_date}" AND
                DoctorDone = "True"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return True
        else:
            return False

    def _is_charge_done(self, patient_key):
        sql = f'''
            SELECT ChargeDone FROM cases
            WHERE
                PatientKey = "{patient_key}" AND
                DATE(CaseDate) = "{self.current_date}" AND
                ChargeDone = "True"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return True
        else:
            return False

    def _show_no_iccard(self):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_no_iccard()
        dialog.exec_()
        del dialog

    def _show_no_patient(self):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_no_patient()
        dialog.exec_()
        del dialog

    def _show_not_doctor_done(self):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_not_doctor_done()
        dialog.exec_()
        del dialog

    def _show_already_payment(self):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_already_payment()
        dialog.exec_()
        del dialog

    def _show_no_case_record(self):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_no_case_record()
        dialog.exec_()
        del dialog

    def _show_payment_done(self):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_payment_done()
        dialog.exec_()
        del dialog

    def _remove_home_image(self):
        if hasattr(self, "home_image") and self.home_image:
            self.home_image.setParent(None)
            self.home_image = None

    def _close_cash_in_machine(self):
        kiosk = class_utils.get_jetway(self.system_settings)
        kiosk.close_cash_in_machine()
        del kiosk
        gc.collect()

    def _show_charge_table(self, row):
        self._close_cash_in_machine()
        self.set_payment_table()

        name = string_utils.get_mask_name(row["Name"])
        name = f'<font color="{self.parent.LIGHT_GREEN}">{name}</font>'
        title = f"請確認{name}今日的繳費明細"
        self._set_label(self.label_title, title)

        self._set_label(self.label_doctor, string_utils.xstr(row["Doctor"]))
        self._align_right(self.label_doctor, self.COL1, self.ROW1)

        regist_fee = number_utils.get_integer(row["RegistFee"])
        self._set_label(self.label_regist_fee, f"{regist_fee}元")
        self._align_right(self.label_regist_fee, self.COL2, self.ROW1)

        diag_share_fee = number_utils.get_integer(row["SDiagShareFee"])
        self._set_label(self.label_diag_share_fee, f"{diag_share_fee}元")

        self._align_right(self.label_diag_share_fee, self.COL1, self.ROW2)

        drug_share_fee = number_utils.get_integer(row["SDrugShareFee"])
        self._set_label(self.label_drug_share_fee, f"{drug_share_fee}元")

        self._align_right(self.label_drug_share_fee, self.COL2, self.ROW2)

        total_fee = number_utils.get_integer(row["TotalFee"])
        self._set_label(self.label_total_fee, f"{total_fee}元")

        self._align_right(self.label_total_fee, self.COL1, self.ROW3)

        self.total_amount = regist_fee + diag_share_fee + drug_share_fee + total_fee
        self._set_label(self.label_total_amount, f"{self.total_amount}元整")

    def _set_label(self, label_value, text):
        label_value.setText(text)
        label_value.adjustSize()

    def _set_image(self, label_image, png_filename, x, y):
        pixmap = QPixmap(png_filename)
        label_image.setPixmap(pixmap)

        label_image.setFixedSize(pixmap.size())
        label_image.move(x, y)

    def _get_case_data(self, case_key):
        sql = f"""
            SELECT Doctor, Room, InsType FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None, None, None

        row = rows[0]
        ins_type = string_utils.xstr(row["InsType"])
        doctor = string_utils.xstr(row["Doctor"])
        room = string_utils.xstr(row["Room"])

        return ins_type, doctor, room

    def _ready_to_payment(self):
        from joytcm_kiosk.dialog import dialog_payment

        self.button_cancel.setVisible(False)

        module = importlib.reload(dialog_payment)
        dialog = module.DialogPayment(
            self.parent,
            self.database,
            self.system_settings,
            self.ic_card,
            self.case_key,
            self.total_amount,
        )
        dialog.exec_()
        is_payment_done = dialog.is_payment_done()
        del dialog

        if is_payment_done:
            ins_type, doctor, room = self._get_case_data(self.case_key)
            if ins_type == "健保":
                dialog = self.parent.show_in_progress()
                self._write_ic_card(self.case_key)
                dialog.close()

            self._print_receipt(self.case_key)
            self._set_data(self.case_key)
            self._show_payment_done()
            self.parent.send_socket_data(doctor, room, "批價作業")
            self._back_to_home()

        self.button_cancel.setVisible(True)

    def _print_receipt(self, case_key):
        printer_utils.print_misc_form(
            self, self.database, self.system_settings, case_key, "選擇列印"
        )

    def _set_data(self, case_key):
        charge_date = date_utils.now_to_str()
        charge_period = registration_utils.get_current_period(self.system_settings)
        cashier = "掛號機"
        sql = f'''
            UPDATE cases
            SET
                ChargeDone = "True",
                ChargeDate = "{charge_date}",
                ChargePeriod = "{charge_period}",
                Cashier = "{cashier}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

    def _write_ic_card(self, case_key):
        dialog = self.parent.show_in_progress()
        QCoreApplication.processEvents()
        self.ic_card.write_ic_medical_record(case_key, cshis_utils.NORMAL_CARD)
        dialog.close()
