# -*- coding: UTF-8 -*-

import datetime
import time

from PyQt5 import QtCore, QtGui, QtWidgets

from libs import (
    case_utils,
    cshis_utils,
    date_utils,
    log_utils,
    nhi_utils,
    notification_utils,
    number_utils,
    patient_utils,
    printer_utils,
    registration_utils,
    string_utils,
    ui_utils,
)


# 板橋新生堂
class DetectUnplugThread(QtCore.QThread):
    card_unplug = QtCore.pyqtSignal("QString")

    def __init__(self, parent, ic_card):
        super().__init__()
        self.parent = parent
        self.ic_card = ic_card
        self._stop = False
        self._medical_record_posted = False

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

            if error_code == 0 and self._medical_record_posted:
                self._stop = False
                self._medical_record_posted = False

                self.ic_card.close_com()
                self.card_unplug.emit("card_unplug")
                break

        self.ic_card.close_com()

    def set_medical_record_posted(self):
        self._medical_record_posted = True

    def stop(self):
        self._stop = True


# 已插入健保卡, 準備存檔
class PyCashierCompleted(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ic_card = args[2]
        self.ui = None

        self.detect_unplug_thread = DetectUnplugThread(self, self.ic_card)
        self.detect_unplug_thread.card_unplug.connect(self.card_unplug)

        self.notification_client = notification_utils.NotificationClient(
            self,
            database=self.database,
            station="掛號機",
        )

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PYCASHIER2_COMPLETED, self)
        style = """
            QMainWindow#WindowCompleted
            {background-image: url(./images/pycashier_bg.jpg);}
        """
        self.ui.setStyleSheet(style)

        widget_list = [
            self.ui.label_message,
            self.ui.label_hint,
        ]
        self._set_widget_shadow(widget_list)

    def _set_widget_shadow(self, widget_list):
        blur_radius = 0

        shadow_list = []
        for i in range(len(widget_list)):
            shadow_list.append(QtWidgets.QGraphicsDropShadowEffect())
            shadow_list[i].setBlurRadius(blur_radius)
            shadow_list[i].setColor(QtGui.QColor("black"))
            shadow_list[i].setOffset(1, 2)

            if i == 0:
                widget_list[i].setStyleSheet("QLabel {color : black}")
            else:
                widget_list[i].setStyleSheet("QLabel {color : red}")

            widget_list[i].setGraphicsEffect(shadow_list[i])

    # 設定信號
    def _set_signal(self):
        pass

    def set_writing_data(self, **kwargs):
        payment_type = kwargs["payment_type"]
        room = kwargs["room"]
        doctor = kwargs["doctor"]

        if payment_type == "掛號繳費":
            case_key = self._write_ic_card_from_registration(**kwargs)
            self._print_registration_form(case_key)
        elif payment_type == "批價繳費":
            self._save_records(**kwargs)
            message = "批價完成<br>請取出健保卡"
            self._set_label_message(message, "請取出健保卡", message)
            self._print_receipt_form(**kwargs)

        self._send_broadcast_data(doctor, room, payment_type)

        QtCore.QCoreApplication.processEvents()
        self.detect_ic_card_removed()
        self.detect_unplug_thread.set_medical_record_posted()

    def _print_registration_form(self, case_key):
        printer_utils.print_regist_form(
            self, self.database, self.system_settings, case_key, "系統設定"
        )

    def _print_receipt_form(self, **kwargs):
        case_key = kwargs["case_key"]

        printer_utils.print_ins_receipt(
            self, self.database, self.system_settings, case_key, "print"
        )
        printer_utils.print_misc_form(
            self, self.database, self.system_settings, case_key, "print"
        )

    def _write_ic_card_from_registration(self, **kwargs):
        QtCore.QCoreApplication.processEvents()
        message = "請勿取出健保卡"
        self._set_label_message(
            f'<font size="5">{message}</font>',
            "掛號存檔及寫入健保卡中<br>請稍後...",
            message,
        )

        QtCore.QCoreApplication.processEvents()
        case_key = self._insert_medical_record(**kwargs)

        self.ic_card.close_com()
        time.sleep(2)
        QtCore.QCoreApplication.processEvents()
        self._set_label_message(
            """<font size="5">
                 請將健保卡交予櫃台<br>
                 完成報到手續
               </font>
            """,
            "請取出健保卡",
            "請將健保卡交予櫃台, 完成報到手續",
        )

        return case_key

    def _save_records(self, **kwargs):
        case_key = kwargs["case_key"]
        drug_share_fee = kwargs["drug_share_fee"]
        total_fee = kwargs["total_fee"]

        sql = f"""
            SELECT WaitKey FROM wait
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            wait_key = row["WaitKey"]
            self.database.exec_sql(
                f'UPDATE wait SET ChargeDone = "True" WHERE WaitKey = {wait_key}'
            )

        fields = [
            "Cashier",
            "SDrugShareFee",
            "ReceiptFee",
            "ChargeDone",
            "ChargeDate",
            "ChargePeriod",
        ]
        data = [
            "掛號機",
            drug_share_fee,
            total_fee,
            "True",
            date_utils.now_to_str(),
            registration_utils.get_current_period(self.system_settings),
        ]
        self.database.update_record("cases", fields, "CaseKey", case_key, data)

        case_utils.set_case_extend(self.database, case_key, "掛號機批價", "是")

    def _write_ic_card(self, patient_key, course, share_type, treat_after_check):
        time.sleep(2)

        available_date, available_count = self.ic_card.get_card_status()
        if available_count is None:
            return False

        now = datetime.datetime.now().strftime("%Y-%m-%d")
        if available_count <= 0 or available_date < now:
            self.ic_card.update_hc(False)

        ic_card_ok = self.ic_card.write_ic_card(
            "掛號寫卡", patient_key, course, share_type, treat_after_check
        )

        if ic_card_ok:
            return True
        else:
            return False

    @staticmethod
    def _get_security(ic_card, card, card_abnormal):
        if ic_card is None:
            security = case_utils.create_security_xml()
        else:
            security = case_utils.treat_data_to_xml(ic_card.treat_data)

        upload_type = "1"  # 上傳格式
        if card in nhi_utils.ABNORMAL_CARD or card_abnormal in nhi_utils.ABNORMAL_CARD:
            upload_type = "2"

        treat_after_check = "1"  # 補卡註記
        if card == "欠卡":
            treat_after_check = "2"

        security = case_utils.update_xml_doc(security, "upload_type", upload_type)

        security = case_utils.update_xml_doc(
            security, "treat_after_check", treat_after_check
        )

        return security

    def _insert_medical_record(self, **kwargs):
        patient_key = kwargs["patient_key"]
        patient_row = patient_utils.get_patient_row(self.database, patient_key)

        period = kwargs["period"]
        room = kwargs["room"]
        regist_no = kwargs["regist_no"]
        doctor = kwargs["doctor"]
        card = kwargs["card"]
        course = kwargs["course"]
        treat_type = kwargs["treat_type"]
        regist_type = kwargs["regist_type"]
        regist_fee = kwargs["regist_fee"]
        diag_share_fee = kwargs["diag_share_fee"]
        reserve_key = kwargs["reserve_key"]

        case_date = string_utils.xstr(datetime.datetime.now())
        patient_name = string_utils.xstr(patient_row["Name"])
        share_type = string_utils.xstr(patient_row["InsType"])
        ins_type = "健保"
        visit = "複診"
        card_abnormal = ""

        if self._write_ic_card(
            patient_key, course, share_type, cshis_utils.NORMAL_CARD
        ):
            if card == "自動取得":
                card = self.ic_card.treat_data["seq_number"]

        security = self._get_security(self.ic_card, card, card_abnormal)

        fields = [
            "CaseDate",
            "PatientKey",
            "Name",
            "Visit",
            "RegistType",
            "Injury",
            "TreatType",
            "Share",
            "InsType",
            "Card",
            "Continuance",
            "Period",
            "Room",
            "RegistNo",
            "Register",
            "ApplyType",
            "PharmacyType",
            "RegistFee",
            "DiagShareFee",
            "SDiagShareFee",
            "Security",
            "Doctor",
        ]

        data = [
            case_date,
            patient_key,
            patient_name,
            visit,
            regist_type,
            "普通疾病",
            treat_type,
            share_type,
            ins_type,
            card,
            course,
            period,
            room,
            regist_no,
            "掛號機",
            "申報",
            "申報" if self.system_settings.field("申報藥事服務費") == "Y" else "不申報",
            regist_fee,
            diag_share_fee,
            diag_share_fee,
            security,
            doctor,
        ]
        case_key = self.database.insert_record("cases", fields, data)

        self.insert_wait(
            case_key=case_key,
            case_date=case_date,
            patient_key=patient_key,
            patient_name=patient_name,
            visit=visit,
            regist_type=regist_type,
            treat_type=treat_type,
            share_type=share_type,
            ins_type=ins_type,
            card=card,
            course=course,
            period=period,
            room=room,
            regist_no=regist_no,
            doctor=doctor,
        )

        if regist_type == "預約門診" and reserve_key is not None:
            self._update_reservation_arrival(reserve_key)

        now = date_utils.now_to_str()
        card = card + f"-{course}" if number_utils.get_integer(course) >= 1 else card
        log = f"{patient_name}於{now}完成健保掛號, 卡序:{card}, 主治醫師: {room}診{doctor}醫師"

        if regist_fee != "0":
            log += f", 掛號費: {regist_fee}"
        if diag_share_fee != "0":
            log += f", 門診負擔: {diag_share_fee}"

        log_utils.write_event_log(
            self.database,
            self.system_settings.field("使用者"),
            "掛號存檔",
            "掛號機",
            log,
        )

        return case_key

    def _update_reservation_arrival(self, reserve_key):
        sql = f"""
            UPDATE reserve
            SET
                Arrival = "True"
            WHERE
                ReserveKey = {reserve_key}
        """
        self.database.exec_sql(sql)

    def insert_wait(self, **kwargs):
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
        ]

        data = [
            kwargs["case_key"],
            kwargs["case_date"],
            kwargs["patient_key"],
            kwargs["patient_name"],
            kwargs["visit"],
            kwargs["regist_type"],
            kwargs["treat_type"],
            kwargs["share_type"],
            kwargs["ins_type"],
            kwargs["card"],
            kwargs["course"],
            kwargs["period"],
            kwargs["room"],
            kwargs["regist_no"],
            kwargs["doctor"],
        ]
        self.database.insert_record("wait", fields, data)

    def _get_reservation_row(self, reserve_key):
        sql = f"""
            SELECT * FROM reserve
            WHERE
                ReserveKey = {reserve_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return rows[0]

    def _set_label_message(self, message, hint, sentence):
        self.ui.label_message.setText(message)
        self.ui.label_hint.setText(hint)

    def card_unplug(self, detected):
        if detected == "card_unplug":
            self._back_home()

    def detect_ic_card_removed(self):
        self.detect_unplug_thread.start()

    def _back_home(self):
        self.parent.open_pycashier_home()

    def _send_broadcast_data(self, doctor, room, payment_type):
        if payment_type == "掛號繳費":
            program_name = "門診掛號"
        elif payment_type == "批價繳費":
            program_name = "批價作業"
        else:
            program_name = ""

        message = ",".join(
            [
                self.system_settings.field("院所名稱"),
                program_name,
                doctor,
                string_utils.xstr(room),
            ]
        )

        self.notification_client.send_data(message)  # 新管道：資料庫
