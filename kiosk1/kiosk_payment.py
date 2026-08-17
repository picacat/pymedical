# -*- coding: UTF-8 -*-

import datetime
import importlib
import os
import threading

from PyQt5 import QtWidgets
from PyQt5.QtCore import QCoreApplication, QObject, pyqtSignal

from libs import (
    case_utils,
    class_utils,
    date_utils,
    log_utils,
    notification_utils,
    patient_utils,
    printer_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
)


class Communicate(QObject):
    update_cash_received = pyqtSignal(int)


# 2024.06.24 掛號機繳費頁面
class KioskPayment(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ic_card = args[2]
        self.case_key = None
        self.patient_key = None
        self.ui = None

        self._set_ui()
        self._set_signal()

        self.notification_client = notification_utils.NotificationClient(
            self,
            database=self.database,
            station=self.program_name,
        )

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(
            os.path.join(self.parent.UI_DIR, "kiosk_home.ui"), self
        )
        self.set_background()

    # 刪除所有控件
    def clear_all_widgets(self):
        for widget in self.findChildren(QtWidgets.QWidget):
            widget.setParent(None)
            widget.deleteLater()

    def set_background(self):
        label_background = system_utils.set_image(
            self, os.path.join(self.parent.IMAGE_DIR, "background.png"), 0, 0
        )
        self._bring_to_front(label_background)

        label_header = system_utils.set_label(
            self,
            self.parent.clinic_name,
            50,
            35,
            self.parent.TEXT_FONT,
            56,
            self.parent.LIGHT_TEXT_COLOR,
        )
        self._bring_to_front(label_header)

        label_header = system_utils.set_label(
            self,
            "掛號繳費系統",
            210,
            300,
            self.parent.TEXT_FONT,
            84,
            self.parent.LIGHT_TEXT_COLOR,
        )
        self._bring_to_front(label_header)

        label_header = system_utils.set_label(
            self,
            "請投入紙鈔、50或10元硬幣",
            310,
            1770,
            self.parent.TEXT_FONT,
            42,
            self.parent.TEXT_COLOR,
        )
        self._bring_to_front(label_header)

        self._set_cancel_button("取消繳費")

    def _set_cancel_button(self, button_text):
        color = self.parent.DARK_RED
        x, y = 350, 1400
        self.push_button = QtWidgets.QPushButton(self)
        self.push_button.resize(400, 100)
        self.push_button.setText(button_text)
        self.push_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};  /* 正常狀態背景顏色 */
                border: 2px solid {color};  /* 邊框顏色 */
                border-radius: 10px;        /* 圓角 */
                color: white;               /* 字體顏色 */
                font: 75 56pt "{self.parent.BUTTON_FONT}";
            }}
        """)
        self.push_button.move(x, y)
        self.push_button.raise_()
        self.push_button.show()
        self.push_button.clicked.connect(self._back_to_home)

    # 設定信號
    def _set_signal(self):
        pass

    def _back_to_home(self):
        self.stop_charge_cash()
        if self.inserted_cash > 0:
            self.kiosk.eject_cash(self.inserted_cash)

        del self.kiosk

        self.parent.open_kiosk_home()

    def _go_to_completed(self):
        self.parent.open_kiosk_completed(self.treat_type)

    def set_payment_data(
        self, patient_key, treat_type, card, course, regist_fee, diag_share_fee
    ):
        self.clear_all_widgets()
        self.set_background()

        self.patient_key = patient_key
        self.treat_type = treat_type
        self.card = card
        self.course = course
        self.regist_fee = regist_fee
        self.diag_share_fee = diag_share_fee
        self.total_amount = self.regist_fee + self.diag_share_fee

        x1 = 200
        x2 = 700
        font_size = 72

        LINE_HEIGHT = 150
        LINE1_Y = 700
        LINE2_Y = LINE1_Y + LINE_HEIGHT
        LINE3_Y = LINE2_Y + LINE_HEIGHT
        self.inserted_cash = 0

        header = system_utils.set_label(
            self,
            "應付金額: $",
            x1,
            LINE1_Y,
            self.parent.TEXT_FONT,
            font_size,
            self.parent.RED,
        )
        self._bring_to_front(header)

        label_total_amount = system_utils.set_label(
            self,
            str(self.total_amount),
            x2,
            LINE1_Y,
            self.parent.TEXT_FONT,
            font_size,
            self.parent.RED,
        )
        self._bring_to_front(label_total_amount)

        header = system_utils.set_label(
            self,
            "投入金額: $",
            x1,
            LINE2_Y,
            self.parent.TEXT_FONT,
            font_size,
            self.parent.DARK_GREEN,
        )
        self._bring_to_front(header)

        self.label_inserted_cash = system_utils.set_label(
            self,
            str(self.inserted_cash),
            x2,
            LINE2_Y,
            self.parent.TEXT_FONT,
            font_size,
            self.parent.DARK_GREEN,
        )
        self._bring_to_front(self.label_inserted_cash)

        header = system_utils.set_label(
            self,
            "尚餘金額: $",
            x1,
            LINE3_Y,
            self.parent.TEXT_FONT,
            font_size,
            self.parent.LIGHT_GREEN,
        )
        self._bring_to_front(header)

        self.label_remain = system_utils.set_label(
            self,
            str(self.total_amount - self.inserted_cash),
            x2,
            LINE3_Y,
            self.parent.TEXT_FONT,
            font_size,
            self.parent.LIGHT_GREEN,
        )
        self._bring_to_front(self.label_remain)

        self.start_charge_cash()

    def _bring_to_front(self, widget):
        widget.raise_()
        widget.show()

    def _get_reserve_row(self, patient_key):
        current_date = datetime.datetime.today().strftime("%Y-%m-%d")
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
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_no_iccard()
        dialog.exec_()
        del dialog

    def _show_no_patient(self):
        from kiosk1.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_no_patient()
        dialog.exec_()
        del dialog

    def _show_already_arrival(self):
        from kiosk1.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_already_arrival()
        dialog.exec_()
        del dialog

    def _query_self_pay_case(
        self, reserve_row, start_date, end_date, pres_days, remain_days
    ):
        from kiosk1.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.query_self_pay_case(
            reserve_row, start_date, end_date, pres_days, remain_days
        )
        dialog.exec_()
        self_pay_case = dialog.get_self_pay_case()
        del dialog

        return self_pay_case

    def _show_arrival_done(self):
        from kiosk1.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_arrival_done()
        dialog.exec_()
        del dialog

    def _check_ic_card_basic_data(self, reserve_row):
        patient_key = reserve_row["PatientKey"]
        patient_row = patient_utils.get_patient_row(self.database, patient_key)
        patient_card_no = string_utils.xstr(patient_row["CardNo"])
        card_no = self.ic_card.basic_data["card_no"]

        if patient_card_no != card_no:
            sql = f'''
                UPDATE patient
                SET
                    CardNo = "{card_no}"
                WHERE
                    PatientKey = {patient_key}
            '''
            self.database.exec_sql(sql)

        if patient_row["Birthday"] != self.ic_card.basic_data["birthday"]:
            birthday = self.ic_card.basic_data["birthday"]
            sql = f'''
                UPDATE patient
                SET
                    Birthday = "{birthday}"
                WHERE
                    PatientKey = {patient_key}
            '''
            self.database.exec_sql(sql)

        if (
            string_utils.xstr(patient_row["InsType"])
            != self.ic_card.basic_data["insured_mark"]
        ):
            ins_type = self.ic_card.basic_data["insured_mark"]
            sql = f'''
                UPDATE patient
                SET
                    InsType = "{ins_type}"
                WHERE
                    PatientKey = {patient_key}
            '''
            self.database.exec_sql(sql)

    def _write_ic_card(self):
        available_date, available_count = self.ic_card.get_card_status()
        if available_count is None:
            print("read card failed")
            return False

        now = datetime.datetime.now().strftime("%Y-%m-%d")
        if available_count <= 0 or available_date < now:
            self.ic_card.update_hc(show_message=False)

        if self.card == "自動取得":
            treat_item = "03"
        else:
            treat_item = "AA"

        error_code = self.ic_card.get_seq_number_256(treat_item, " ", "1")
        if error_code != 0:
            print("write failed, error code: ", error_code)

        return True

    def _insert_medical_record(self):
        patient_row = patient_utils.get_patient_row(self.database, self.patient_key)
        if patient_row is None:
            self._show_no_patient()
            return False

        ins_type = "健保"
        case_date = string_utils.xstr(datetime.datetime.now())
        patient_name = string_utils.xstr(patient_row["Name"])

        period = registration_utils.get_current_period(self.system_settings)
        room = self.system_settings.field("診療室")  # 取得預設診療室
        if room is None:
            room = 1

        reserve_row = self._get_reserve_row(self.patient_key)
        if reserve_row is None:
            reg_type = "一般門診"
            self.reserve_key = None
            doctor = registration_utils.get_schedule_doctor(self.database, room, period)
        else:
            reg_type = "預約門診"
            self.reserve_key = reserve_row["ReserveKey"]
            doctor = string_utils.xstr(reserve_row["Doctor"])

        regist_no = registration_utils.get_reg_no(
            self.database,
            self.system_settings,
            room,
            doctor,
            period,
            self.reserve_key,
        )

        card_abnormal = None
        course = None
        massager = None

        share_type = string_utils.xstr(patient_row["InsType"])
        remark = None
        payment_type = "現金"
        visit = "複診"
        area = None
        injury_type = "普通疾病"

        deposit_fee = None

        if self.card == "自動取得":
            card = string_utils.xstr(self.ic_card.treat_data["seq_number"])
            course = None
        else:
            card = self.card
            course = self.course

        s_diag_share_fee = self.diag_share_fee

        upload_type = "1"  # 正常卡序
        self.ic_card.treat_data["treat_after_check"] = upload_type
        security = case_utils.treat_data_to_xml(self.ic_card.treat_data)
        security = case_utils.update_xml_doc(security, "upload_type", upload_type)

        designated_doctor = "False"
        designated_massager = "False"

        doctor_done = "False"
        doctor_date = None
        charge_done = "False"
        charge_date = None
        charge_period = None
        registrar = "掛號機"

        fields = [
            "CaseDate",
            "PatientKey",
            "Name",
            "Visit",
            "RegistType",
            "TourArea",
            "Injury",
            "TreatType",
            "Share",
            "InsType",
            "Card",
            "Continuance",
            "XCard",
            "Period",
            "Room",
            "RegistNo",
            "Massager",
            "Register",
            "DesignatedDoctor",
            "DesignatedMassager",
            "ApplyType",
            "PharmacyType",
            "RegistFee",
            "DiagShareFee",
            "SDiagShareFee",
            "DepositFee",
            "Security",
            "Remark",
            "Doctor",
            "RegistPaymentType",
            "DoctorDone",
            "DoctorDate",
            "ChargeDone",
            "ChargeDate",
            "ChargePeriod",
        ]

        data = [
            case_date,
            self.patient_key,
            patient_name,
            visit,
            reg_type,
            area,
            injury_type,
            self.treat_type,
            share_type,
            ins_type,
            card,
            course,
            card_abnormal,
            period,
            room,
            regist_no,
            massager,
            registrar,
            designated_doctor,
            designated_massager,
            "申報",
            "申報" if self.system_settings.field("申報藥事服務費") == "Y" else "不申報",
            self.regist_fee,
            self.diag_share_fee,
            s_diag_share_fee,
            deposit_fee,
            security,
            remark,
            doctor,
            payment_type,
            doctor_done,
            doctor_date,
            charge_done,
            charge_date,
            charge_period,
        ]
        case_key = self.database.insert_record("cases", fields, data)

        identification = case_utils.extract_security_xml(security, "就醫識別碼")
        registered_date = date_utils.west_datetime_to_nhi_datetime(
            case_utils.extract_security_xml(security, "寫卡時間")
        )
        case_utils.clear_case_extend(self.database, case_key, "原就醫識別碼")
        case_utils.set_case_extend(
            self.database, case_key, "原就醫識別碼", identification
        )

        case_utils.clear_case_extend(self.database, case_key, "實際就醫日期")
        case_utils.set_case_extend(
            self.database, case_key, "實際就醫日期", registered_date
        )

        now = date_utils.now_to_str()
        log = f"{patient_name}於{now}完成{ins_type}掛號, 卡序:{card}, 主治醫師: {room}診{doctor}醫師"

        if self.regist_fee != "0":
            log += f", 掛號費: {self.regist_fee}"
        if s_diag_share_fee != "0":
            log += f", 門診負擔: {s_diag_share_fee}"
        if deposit_fee != "0":
            log += f", 欠卡費: {deposit_fee}"

        log_utils.write_event_log(self.database, registrar, "掛號存檔", "掛號作業", log)

        case_row = {
            "case_key": case_key,
            "case_date": case_date,
            "patient_key": self.patient_key,
            "name": patient_name,
            "visit": visit,
            "regist_type": reg_type,
            "treat_type": self.treat_type,
            "share": share_type,
            "ins_type": ins_type,
            "card": card,
            "continuance": course,
            "period": period,
            "room": room,
            "regist_no": regist_no,
            "doctor": doctor,
            "massager": massager,
            "remark": remark,
            "vhc_req_code": None,
            "doctor_done": doctor_done,
        }

        return case_row

    def _insert_wait(self, case_row):
        fields = [
            "CaseKey",
            "CaseDate",
            "PatientKey",
            "Name",
            "Visit",
            "RegistType",
            "TreatType",
            "Share",
            "InsType",
            "Card",
            "Continuance",
            "Period",
            "Room",
            "RegistNo",
            "Doctor",
            "Massager",
            "Remark",
            "VHCReqCode",
            "DoctorDone",
        ]
        data = [
            case_row["case_key"],
            case_row["case_date"],
            case_row["patient_key"],
            case_row["name"],
            case_row["visit"],
            case_row["regist_type"],
            case_row["treat_type"],
            case_row["share"],
            case_row["ins_type"],
            case_row["card"],
            case_row["continuance"],
            case_row["period"],
            case_row["room"],
            case_row["regist_no"],
            case_row["doctor"],
            case_row["massager"],
            case_row["remark"],
            case_row["vhc_req_code"],
            case_row["doctor_done"],
        ]
        self.database.insert_record("wait", fields, data)

    def _update_reservation(self, reserve_key):
        sql = f"""
            UPDATE reserve
            SET
                Arrival = "True"
            WHERE
                ReserveKey = {reserve_key}
        """
        self.database.exec_sql(sql)

    def _send_broadcast_data(self, case_row):
        doctor = string_utils.xstr(case_row["doctor"])
        room = string_utils.xstr(case_row["room"])
        message = ",".join(
            [
                self.system_settings.field("院所名稱"),
                "掛號作業",
                doctor,
                room,
            ]
        )

        self.notification_client.send_data(message)  # 新管道：資料庫

    def start_charge_cash(self):
        self.inserted_cash = 0
        self.comm = Communicate()
        self.comm.update_cash_received.connect(self._update_cash_received)

        self.kiosk = class_utils.get_jetway(self.system_settings)
        if not self.kiosk.connected:
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Warning,
                "錯誤",
                '<font size="5" color="red"><b>收鈔機無法啟動, 請檢查收鈔機是否備妥.</b></font>',
                "請檢查收鈔機的狀態.",
            )
            self.close()
            return

        self.stop_event = threading.Event()
        self.charge_cash_thread = threading.Thread(
            target=self.kiosk.charge_cash,
            args=(self.total_amount, self.comm.update_cash_received, self.stop_event),
        )
        self.charge_cash_thread.start()

    def stop_charge_cash(self):
        self.stop_event.set()
        self.charge_cash_thread.join()

    def _update_cash_received(self, receipt_cash):
        self.inserted_cash = receipt_cash
        self.label_inserted_cash.setText(f"{self.inserted_cash}")
        self.label_inserted_cash.adjustSize()

        if self.inserted_cash >= self.total_amount:
            self.label_remain.setText(f"{self.total_amount - self.inserted_cash}")
            self.label_remain.adjustSize()

            remain_cash = self.inserted_cash - self.total_amount
            self.stop_charge_cash()
            if remain_cash > 0:
                self.kiosk.eject_cash(remain_cash)

            self.payment_done = True
            del self.kiosk
            self.push_button.hide()
            self._save_files()
            self._go_to_completed()
            return

        remain = self.total_amount - self.inserted_cash
        self.label_remain.setText(f"{remain}")
        self.label_remain.adjustSize()

    def is_payment_done(self):
        return self.payment_done

    def _save_files(self):
        dialog = self.parent.show_in_progress()
        QCoreApplication.processEvents()
        write_ic_card = self._write_ic_card()
        dialog.close()
        if not write_ic_card:
            return

        case_row = self._insert_medical_record()
        if case_row is None:
            return

        self._insert_wait(case_row)
        if self.reserve_key is not None:
            self._update_reservation(self.reserve_key)

        self._send_broadcast_data(case_row)
        printer_utils.print_regist_form(
            self, self.database, self.system_settings, case_row["case_key"], "列印"
        )
