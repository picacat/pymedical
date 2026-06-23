# -*- coding: UTF-8 -*-

import datetime
import importlib
import os

from PyQt5 import QtWidgets
from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtWidgets import QLineEdit

from libs import (
    case_utils,
    charge_utils,
    date_utils,
    log_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    registration_utils,
    string_utils,
    system_utils,
)


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
        self.clinic_name = self.system_settings.field("院所名稱")

        self._qr_input = None  # 隱藏輸入框
        self._qr_waiting = False  # 是否正在等待掃描

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
        system_utils.set_image(
            self, os.path.join(self.parent.IMAGE_DIR, "home.png"), 0, 0
        )

        # 建立隱藏的 QLineEdit 接收掃描器輸入
        self._qr_input = QLineEdit(self)
        self._qr_input.setGeometry(0, 0, 1, 1)  # 縮到最小、不可見
        self._qr_input.setStyleSheet("opacity: 0;")
        self._qr_input.hide()

    # 設定信號
    def _set_signal(self):
        self._qr_input.returnPressed.connect(self._on_qr_scanned)

    def _back_to_home(self):
        self.ic_card.ic_card_type = "健保卡"  # 恢復健保卡模式
        self.ic_card.qrcode = None  # 清除 QR code

        self.parent.open_kiosk_home()

    def set_vhc_registration_data(self):
        dialog = self.parent.show_vhc_in_progress()
        # 強制刷新事件循環，確保對話框立即顯示
        QCoreApplication.processEvents()

        # 清空輸入框，顯示並 focus，等待掃描器輸入
        self._qr_input.clear()
        self._qr_input.show()
        self._qr_input.setFocus()
        self._qr_waiting = True

        # 可選：設定逾時（例如 30 秒沒掃就取消）
        self._qr_timer = QTimer(self)
        self._qr_timer.setSingleShot(True)
        self._qr_timer.timeout.connect(self._on_qr_timeout)
        self._qr_timer.start(30000)  # 30 秒

        # 儲存 dialog 供之後關閉
        self._vhc_dialog = dialog

        # 監聽 dialog 被關閉（按取消或直接關閉視窗）
        dialog.finished.connect(self._on_qr_cancelled)

    def _on_qr_cancelled(self):
        if not self._qr_waiting:
            return  # 已經掃描成功或已逾時，不重複處理

        self._qr_waiting = False
        self._qr_timer.stop()
        self._qr_input.hide()
        self._back_to_home()

    # ----------------------------------------------------------------
    # 掃描成功 callback
    # ----------------------------------------------------------------
    def _on_qr_scanned(self):
        if not self._qr_waiting:
            return

        self._qr_waiting = False
        self._qr_timer.stop()
        self._qr_input.hide()

        qr_data = self._qr_input.text().strip()
        self._vhc_dialog.close()

        if not qr_data:
            self._show_no_iccard()  # 空資料視同讀取失敗
            self._back_to_home()
            return

        self.ic_card.ic_card_type = "虛擬健保卡"
        self.ic_card.qrcode = qr_data
        if not self.ic_card.read_register_basic_data(show_warning=False):
            self._show_no_iccard()
            self._back_to_home()
            return

        self._process_data()

    # ----------------------------------------------------------------
    # 逾時 callback
    # ----------------------------------------------------------------
    def _on_qr_timeout(self):
        if not self._qr_waiting:
            return

        self._qr_waiting = False
        self._qr_input.hide()
        self._vhc_dialog.close()

        self._back_to_home()

    def set_registration_data(self):
        dialog = self.parent.show_in_progress()
        # 強制刷新事件循環，確保對話框立即顯示
        QCoreApplication.processEvents()

        read_ic_card = self.ic_card.read_register_basic_data(show_warning=False)
        dialog.close()

        if not read_ic_card:
            self._show_no_iccard()
            self._back_to_home()
            return

        self._process_data()

    def _process_data(self):
        patient_id = self.ic_card.basic_data["patient_id"]
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
        patient_key = row["PatientKey"]
        reserve_row = self._get_reserve_row(patient_key)
        if reserve_row is None:
            self._show_no_reservation()
            self._back_to_home()
            return

        if reserve_row["Arrival"] == "True":
            self._show_already_arrival()
            self._back_to_home()
            return

        start_date, end_date, pres_days, remain_days = (
            registration_utils.check_prescription_finished(  # 檢查上次健保給藥是否服藥完畢
                self.database,
                self.system_settings,
                None,
                patient_key,
                manual_message=True,
            )
        )

        if (
            start_date is not None and remain_days is not None and remain_days >= 2
        ):  # 上次開藥還有兩天
            if self._query_self_pay_case(
                reserve_row, start_date, end_date, pres_days, remain_days
            ):  # 改掛自費
                self._reservation_arrival(reserve_row, ins_type="自費")
            else:  # 不要繼續門診
                self._back_to_home()
                return
        else:  # 正常預約報到
            self._arrival_ins_checkin(reserve_row)

        self._back_to_home()

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
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_no_iccard()
        dialog.exec_()
        del dialog

    def _show_write_iccard_error(self, error_code):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_write_iccard_error(error_code)
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

    def _show_no_reservation(self):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_no_reservation()
        dialog.exec_()
        del dialog

    def _show_not_on_time(self):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_not_on_time()
        dialog.exec_()
        del dialog

    def _show_already_arrival(self):
        from joytcm_kiosk.dialog import dialog_message_box

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
        from joytcm_kiosk.dialog import dialog_message_box

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
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_arrival_done()
        dialog.exec_()
        del dialog

    # 詢問是否預約報到
    def _arrival_ins_checkin(self, reserve_row, ins_type="健保"):
        from joytcm_kiosk.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.arrival_checkin(reserve_row)
        dialog.exec_()
        arrival = dialog.get_arrival()
        del dialog

        if arrival:
            dialog = self.parent.show_in_progress()
            # 強制刷新事件循環，確保對話框立即顯示
            QCoreApplication.processEvents()

            self._reservation_arrival(reserve_row, ins_type)
            dialog.close()

    # 確定預約報到
    def _reservation_arrival(self, reserve_row, ins_type="健保"):
        self._check_ic_card_basic_data(
            reserve_row
        )  # 自費也順便檢查基本資料是否與健保卡一致

        if ins_type == "健保":
            patient_key = reserve_row["PatientKey"]
            self.treat_type, self.card, self.course = self._auto_completion_course(
                patient_key
            )
            if not self._write_ic_card():  # 健保才要讀取健保卡
                print("write card failed")
                return

        self._save_files(reserve_row, ins_type)
        self._send_socket_data(reserve_row)
        self._show_arrival_done()

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
        if self.ic_card.ic_card_type == "虛擬健保卡":
            pass
        else:
            available_date, available_count = self.ic_card.get_card_status()
            if available_count is None:
                print("read card failed")
                return False

            now = datetime.datetime.now().strftime("%Y-%m-%d")
            if available_count <= 0 or available_date < now:
                self.ic_card.update_hc(show_message=False)

        if self.card == "自動取得":
            ic_card_treat = "03"
        else:
            ic_card_treat = "AA"

        if self.ic_card.ic_card_type == "虛擬健保卡":
            self.ic_card.verify_vhc_card()  # ← 先驗證

        error_code = self.ic_card.get_seq_number_256(ic_card_treat, " ", "1")

        if error_code != 0:
            self._show_write_iccard_error(error_code)
            return False

        return True

    def _save_files(self, reserve_row, ins_type):
        case_row = self._insert_medical_record(reserve_row, ins_type)
        self._insert_wait(case_row)
        self._update_reservation(reserve_row)

    def _insert_medical_record(self, reserve_row, ins_type):
        patient_key = reserve_row["PatientKey"]
        patient_row = patient_utils.get_patient_row(self.database, patient_key)
        if patient_row is None:
            self._show_no_patient()
            return False

        patient_discount = string_utils.xstr(patient_row["DiscountType"])
        birthday = string_utils.xstr(patient_row["Birthday"])

        case_date = string_utils.xstr(datetime.datetime.now())
        period = registration_utils.get_current_period(self.system_settings)
        patient_name = string_utils.xstr(patient_row["Name"])
        regist_no = number_utils.get_integer(reserve_row["ReserveNo"])
        card_abnormal = None
        course = None
        doctor = string_utils.xstr(reserve_row["Doctor"])
        room = string_utils.xstr(
            registration_utils.get_room(self.database, period, doctor)
        )
        massager = None

        share_type = string_utils.xstr(patient_row["InsType"])

        try:
            age_year, _ = date_utils.get_age(
                patient_row["Birthday"], datetime.datetime.now()
            )
        except Exception:
            age_year = None

        if age_year is not None and age_year < 3:
            share_type = "三歲兒童"

        treat_type = self.treat_type
        remark = None
        payment_type = "現金"
        visit = "複診"
        reg_type = "一般門診"
        area = None
        injury_type = "普通疾病"

        regist_fee = charge_utils.get_regist_fee(
            self.database,
            self.system_settings,
            birthday,
            patient_discount,
            ins_type,
            share_type,
            treat_type,
            course,
            visit,
        )
        deposit_fee = None

        if ins_type == "健保":
            if self.card == "自動取得":
                card = string_utils.xstr(self.ic_card.treat_data["seq_number"])
            else:
                card = self.card
                course = self.course

            diag_share_fee = charge_utils.get_diag_share_fee(
                self.database,
                self.system_settings,
                share_type,
                treat_type,
                course,
                reg_type,
            )
            s_diag_share_fee = diag_share_fee

            upload_type = "1"  # 正常卡序
            self.ic_card.treat_data["treat_after_check"] = upload_type
            security = case_utils.treat_data_to_xml(self.ic_card.treat_data)
            security = case_utils.update_xml_doc(security, "upload_type", upload_type)
        else:
            card = "免卡"
            diag_share_fee = None
            s_diag_share_fee = None
            upload_type = None
            security = None

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
            patient_key,
            patient_name,
            visit,
            reg_type,
            area,
            injury_type,
            treat_type,
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
            regist_fee,
            diag_share_fee,
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

        if regist_fee != "0":
            log += f", 掛號費: {regist_fee}"
        if s_diag_share_fee != "0":
            log += f", 門診負擔: {s_diag_share_fee}"
        if deposit_fee != "0":
            log += f", 欠卡費: {deposit_fee}"

        log_utils.write_event_log(
            self.database,
            self.system_settings.field("使用者"),
            "掛號存檔",
            "掛號作業",
            log,
        )

        case_row = {
            "case_key": case_key,
            "case_date": case_date,
            "patient_key": patient_key,
            "name": patient_name,
            "visit": visit,
            "regist_type": reg_type,
            "treat_type": treat_type,
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

    def _update_reservation(self, reserve_row):
        reserve_key = reserve_row["ReserveKey"]
        sql = f"""
            UPDATE reserve
            SET
                Arrival = "True"
            WHERE
                ReserveKey = {reserve_key}
        """
        self.database.exec_sql(sql)

    def _send_socket_data(self, reserve_row):
        doctor = string_utils.xstr(reserve_row["Doctor"])
        room = string_utils.xstr(reserve_row["Room"])
        self.parent.send_socket_data(doctor, room, "門診掛號")

    # 自動連續療程 - 30天內.
    def _auto_completion_course(self, patient_key):
        today = datetime.date.today()
        default_card = "自動取得"
        treat_type = "內科"
        last_treat_date = (today - datetime.timedelta(days=30 - 1)).strftime(
            "%Y-%m-%d 00:00:00"
        )

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
        treat_type = string_utils.xstr(row["TreatType"])

        if treat_type in nhi_utils.PREGNANT_CARE_TREAT + [
            "慢性腎病照護"
        ]:  # 助孕照護，保胎照護、慢性腎病照護要續療程
            pass
        elif treat_type in nhi_utils.IMPROVE_CARE_TREAT:  # 加強照護除外
            return treat_type, default_card, None

        # 2019.04.29 上次為內科, 為避免療程中刷卡, 不要自動續療程
        if number_utils.get_integer(row["Continuance"]) <= 0:
            return treat_type, default_card, None

        card = string_utils.xstr(row["Card"])
        if number_utils.get_integer(row["Continuance"]) >= 6:  # 正常卡序療程已滿
            return treat_type, default_card, None

        course = string_utils.xstr(row["Continuance"] + 1)  # 療程自動續1次

        return treat_type, card, course
