# -*- coding: UTF-8 -*-
# alleypin api for Line app
import time

import requests
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox

from libs import (
    case_utils,
    date_utils,
    number_utils,
    patient_utils,
    personnel_utils,
    registration_utils,
    string_utils,
)

ALLEYPIN_URL = "https://openapi.alleypinapis.com"
# ALLEYPIN_URL = 'https://openapi-stg.alleypinapis.com'

# 💡 新增：用來暫存 Token，避免頻繁登入
_AUTH_CACHE = {
    "access_token": None,
    "client_id": None,
    "refresh_ticket": None,
    "expires_at": 0,
}


def _request_api(method, url, command=None, auth=None):
    """
    統一處理對 Alleypin API 的 HTTP 請求
    """
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {auth}"

    try:
        # 使用 requests.request 可以動態傳入 GET, POST, PUT, DELETE
        # 加入 timeout=10，避免網路異常時整個 PyQt 介面卡死
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=command,  # requests 的 json 參數會自動幫我們做 json.dumps()
            timeout=10,
        )

        # 檢查 HTTP 狀態碼，如果不是 2xx，會觸發 HTTPError
        response.raise_for_status()

        # 嘗試回傳 JSON
        if response.content:
            return response.json()
        return None

    except requests.exceptions.RequestException as e:
        # 這裡未來可以換成寫入 log 檔案，目前先印出錯誤方便除錯
        print(f"API Request Failed ({method} {url}): {e}")
        return None


def get_period(period):
    period_dict = {
        "早班": "morning",
        "午班": "afternoon",
        "晚班": "evening",
    }
    try:
        period = period_dict[period]
    except Exception:
        period = "free"

    return period


def get_auth(system_settings):
    current_time = time.time()

    # 💡 檢查快取：如果 Token 存在且還沒過期 (設定存活 3000 秒 = 50 分鐘)，直接回傳
    if _AUTH_CACHE["access_token"] and current_time < _AUTH_CACHE["expires_at"]:
        return (
            _AUTH_CACHE["access_token"],
            _AUTH_CACHE["client_id"],
            _AUTH_CACHE["refresh_ticket"],
        )

    url = ALLEYPIN_URL + "/v1/auth/login"
    appID = system_settings.field("appID")
    secret = system_settings.field("secret")
    clinic_id = system_settings.field("院所代號")
    command = {
        "appID": appID,
        "secret": secret,
        "serviceStoreID": clinic_id,
    }

    result = _request_api("POST", url, command=command)

    if result is None:
        return None, None, None

    access_token = result["accessToken"]
    client_id = result["clientID"]
    refresh_ticket = result["refreshTicket"]

    # 💡 更新快取資料與到期時間
    _AUTH_CACHE["access_token"] = access_token
    _AUTH_CACHE["client_id"] = client_id
    _AUTH_CACHE["refresh_ticket"] = refresh_ticket
    _AUTH_CACHE["expires_at"] = current_time + 3000  # 確保提早過期重新獲取

    return access_token, client_id, refresh_ticket


def add_webhook_endpoint(system_settings, auth):
    url = ALLEYPIN_URL + "/v1/webhook"
    webhook_url = system_settings.field("webhook")
    command = {
        "webhookEndpoint": webhook_url,
    }
    result = _request_api("POST", url, command=command, auth=auth)
    if result is None:
        return None

    return result


def add_reservation_table(**kwargs):
    auth = kwargs["auth"]
    date = kwargs["date"]
    doctor_id = kwargs["doctor_id"]
    doctor_name = kwargs["doctor_name"]
    room_id = kwargs["room_id"]
    room_name = kwargs["room_name"]
    subject_id = kwargs["subject_id"]
    subject_name = kwargs["subject_name"]
    period = get_period(kwargs["period"])
    can_reservation = kwargs["can_reservation"]

    url = ALLEYPIN_URL + "/v1/schedules"
    command = {
        "date": date,
        "doctorID": doctor_id,
        "doctorName": doctor_name,
        "roomID": f"{room_id}",
        "roomName": room_name,
        "subjectID": subject_id,
        "subjectName": subject_name,
        "period": period,
        "canReservation": can_reservation,
    }
    result = _request_api("POST", url, command=command, auth=auth)

    if result is None:
        return None
    try:
        id = result["id"]
    except Exception:
        id = None

    return id


def update_reservation_table(**kwargs):
    auth = kwargs["auth"]
    date = kwargs["date"]
    doctor_id = kwargs["doctor_id"]
    doctor_name = kwargs["doctor_name"]
    room_id = kwargs["room_id"]
    room_name = kwargs["room_name"]
    subject_id = kwargs["subject_id"]
    subject_name = kwargs["subject_name"]
    period = get_period(kwargs["period"])
    can_reservation = kwargs["can_reservation"]
    schedule_id = kwargs["schedule_id"]

    url = ALLEYPIN_URL + f"/v1/schedules/{schedule_id}"
    command = {
        "canReservation": can_reservation,
        "date": date,
        "doctorID": doctor_id,
        "doctorName": doctor_name,
        "roomID": f"{room_id}",
        "roomName": room_name,
        "subjectID": subject_id,
        "subjectName": subject_name,
        "period": period,
    }
    result = _request_api("PUT", url, command=command, auth=auth)
    if result is None:
        return None


def get_reservation_table(**kwargs):
    auth = kwargs["auth"]
    start_date = kwargs["start_date"]
    end_date = kwargs["end_date"]

    url = (
        ALLEYPIN_URL
        + f"/v1/schedules?page=1&size=1000&startTime={start_date}&endTime={end_date}"
    )
    result = _request_api("GET", url, auth=auth)
    if result is None:
        return None

    try:
        schedules = result["schedules"]
    except Exception:
        schedules = None

    return schedules


def get_nationality(nationality):
    nationality_dict = {
        "本國": "twID",
        "外國": "pdID",
        "居留證": "pdID",
        "遊民": "hisID",
    }
    try:
        nationality = nationality_dict[nationality]
    except Exception:
        nationality = "hisID"

    return nationality


def add_appointment(**kwargs):
    auth = kwargs["auth"]
    patient_key = kwargs["patient_key"]
    reserve_key = kwargs["reserve_key"]
    schedule_id = kwargs["schedule_id"]

    birthday = kwargs["birthday"]
    try:
        birthday = time.mktime(birthday.timetuple())
    except Exception:
        birthday = 946656000  # 2000-01-01

    gender = kwargs["gender"]
    patient_id = kwargs["patient_id"]
    nationality = get_nationality(kwargs["nationality"])
    patient_name = kwargs["patient_name"]
    phone = kwargs["phone"]
    reserve_no = kwargs["reserve_no"]
    reserve_time = kwargs["reserve_time"]
    remark = kwargs["remark"]

    if phone in ["", None]:
        phone = "None"

    url = ALLEYPIN_URL + "/v1/appointments"
    command = {
        "customerID": f"{patient_key}",
        "platformID": f"{reserve_key}",
        "scheduleID": schedule_id,
        "birthday": int(birthday),
        "gender": gender,
        "idNum": patient_id,
        "idType": nationality,
        "name": patient_name,
        "phone": phone,
        "seq": reserve_no,
        "note": f"{remark}",
        "appointmentTime": reserve_time,
    }

    result = _request_api("POST", url, command=command, auth=auth)
    if result is None:
        return None

    try:
        id = result["id"]
    except Exception:
        id = None

    return id


def cancel_appointment(**kwargs):
    auth = kwargs["auth"]
    id = kwargs["id"]

    url = ALLEYPIN_URL + f"/v1/appointments/{id}"
    command = None

    result = _request_api("DELETE", url, command=command, auth=auth)
    if result is None:
        return None


def change_appointment(**kwargs):
    auth = kwargs["auth"]
    id = kwargs["id"]
    schedule_id = kwargs["schedule_id"]
    reserve_no = kwargs["reserve_no"]
    reserve_time = kwargs["reserve_time"]

    url = ALLEYPIN_URL + f"/v1/appointments/{id}/changeSchedule"
    command = {
        "scheduleID": schedule_id,
        "seq": reserve_no,
        "appointmentTime": reserve_time,
    }
    result = _request_api("POST", url, command=command, auth=auth)
    if result is None:
        return None


def checkin_appointment(**kwargs):
    auth = kwargs["auth"]
    id = kwargs["id"]

    url = ALLEYPIN_URL + f"/v1/appointments/{id}/checkIn"
    command = None
    result = _request_api("POST", url, command=command, auth=auth)
    if result is None:
        return None


def message_box(title, message, hint):
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setInformativeText(hint)
    msg_box.setStandardButtons(QMessageBox.NoButton)

    return msg_box


def get_schedule_id(database, appointment_date, period, doctor):
    year = appointment_date.year
    month = appointment_date.month
    day = appointment_date.day
    sql = f'''
        SELECT ScheduleID FROM doctor_month_schedule
        WHERE
            Year = {year} AND
            Month = {month} AND
            Day = {day} AND
            Period = "{period}" AND
            Doctor = "{doctor}"
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    row = rows[0]

    return row["ScheduleID"]


def cancel_outpatient_alleypin_appointments(database, system_settings, case_key):
    id = case_utils.get_case_extend(database, case_key, "ScheduleID")
    if id in ["", None]:
        return

    auth_token, _, _ = get_auth(system_settings)
    cancel_appointment(auth=auth_token, id=id)
    case_utils.clear_case_extend(database, case_key, "ScheduleID")


def cancel_reservation_alleypin_appointments(database, system_settings, reserve_key):
    sql = f"""
        SELECT PatInitial FROM reserve
        WHERE
            ReserveKey = {reserve_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]
    id = row["PatInitial"]
    if id is None:
        return

    auth_token, _, _ = get_auth(system_settings)
    cancel_appointment(auth=auth_token, id=id)


def update_progresses(database, system_settings, case_key):
    sql = f"""
        SELECT CaseDate, Period, Doctor FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    row = rows[0]

    period = string_utils.xstr(row["Period"])
    doctor = string_utils.xstr(row["Doctor"])
    schedule_id = get_schedule_id(database, row["CaseDate"], period, doctor)
    progress_id = _get_progress_id(database, schedule_id)

    auth_token, _, _ = get_auth(system_settings)
    if progress_id is None:
        progress_id = _create_progresses(
            database, period, doctor, schedule_id, auth_token
        )
        _update_progress_id(database, schedule_id, progress_id)
    else:
        _update_progresses(database, period, doctor, progress_id, auth_token)


def _update_progress_id(database, schedule_id, progress_id):
    sql = f'''
        UPDATE doctor_month_schedule
        SET
            ProgressID = "{progress_id}"
        WHERE
            ScheduleID = "{schedule_id}"
    '''
    database.exec_sql(sql)


def _get_progress_id(database, schedule_id):
    sql = f'''
        SELECT ProgressID FROM doctor_month_schedule
        WHERE
            ScheduleID = "{schedule_id}"
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None
    else:
        return rows[0]["ProgressID"]


def _get_wait_status(database, period, doctor):
    sql = f'''
        SELECT RegistNo, InProgress FROM wait
        WHERE
            Doctor = "{doctor}" AND
            Period = "{period}" AND
            DoctorDone = "False"
    '''
    rows = database.select_record(sql)
    wait_count = len(rows)

    if wait_count <= 0:
        return 1, 1

    current_seq = None
    for row in rows:
        in_progress = string_utils.xstr(row["InProgress"])
        if in_progress == "Y":
            current_seq = number_utils.get_integer(row["RegistNo"])
            break

    if current_seq is None:
        sql = f'''
            SELECT RegistNo FROM wait
            WHERE
                Doctor = "{doctor}" AND
                DoctorDone = "True"
            ORDER BY RegistNo DESC LIMIT 1
        '''
        rows = database.select_record(sql)
        if len(rows) <= 0:
            current_seq = 1
        else:
            current_seq = number_utils.get_integer(rows[0]["RegistNo"])

    return wait_count, current_seq


def _create_progresses(database, period, doctor, schedule_id, auth):
    wait_count, current_seq = _get_wait_status(database, period, doctor)
    url = ALLEYPIN_URL + "/v1/progresses"
    command = {
        "scheduleID": schedule_id,
        "currentSeq": current_seq,
        "waitingCount": wait_count,
    }
    result = _request_api("POST", url, command=command, auth=auth)
    if result is None:
        return None

    try:
        id = result["id"]
    except Exception:
        id = None

    return id


def _update_progresses(database, period, doctor, progress_id, auth):
    wait_count, current_seq = _get_wait_status(database, period, doctor)

    url = ALLEYPIN_URL + f"/v1/progresses/{progress_id}"
    command = {
        "currentSeq": current_seq,
        "waitingCount": wait_count,
    }
    result = _request_api("PUT", url, command=command, auth=auth)
    if result is None:
        return None


def add_case_alleypin_appointments(database, system_settings, case_key):
    sql = f"""
        SELECT cases.*,
                patient.ID, patient.Nationality, patient.Birthday, patient.Gender, patient.Cellphone FROM cases
            LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    row = rows[0]

    patient_key = row["PatientKey"]
    schedule_id = get_schedule_id(
        database, row["CaseDate"], row["Period"], row["Doctor"]
    )
    patient_id = row["ID"]
    birthday = row["Birthday"]

    try:
        gender = patient_utils.get_gender_code(string_utils.xstr(row["Gender"]))
    except Exception:
        if patient_id[1] == "1":
            gender = "M"
        else:
            gender = "F"

    try:
        nationality = row["Nationality"]
    except Exception:
        nationality = "本國"

    patient_name = row["Name"]
    phone = row["Cellphone"]
    regist_no = row["RegistNo"]
    remark = row["Remark"]

    auth_token, _, _ = get_auth(system_settings)
    id = add_appointment(
        auth=auth_token,
        patient_key=patient_key,
        schedule_id=schedule_id,
        reserve_key=case_key,
        birthday=birthday,
        gender=gender,
        patient_id=patient_id,
        nationality=nationality,
        patient_name=patient_name,
        phone=phone,
        reserve_no=regist_no,
        reserve_time=None,
        remark=remark,
    )

    return id


def add_reservation_alleypin_appointments(database, system_settings, reserve_key):
    sql = f"""
        SELECT Source FROM reserve
        WHERE
            ReserveKey = {reserve_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]
    if row["Source"] in ["初診預約", "視訊初診預約"]:
        sql = f"""
            SELECT
                reserve.*,
                temp_patient.ID, temp_patient.Birthday, temp_patient.Cellphone
            FROM reserve
                LEFT JOIN temp_patient ON temp_patient.TempPatientKey = reserve.PatientKey
            WHERE
                ReserveKey = {reserve_key}
        """
    else:
        sql = f"""
            SELECT
                reserve.*,
                patient.ID, patient.Birthday, patient.Nationality, patient.Gender, patient.Cellphone
            FROM reserve
                LEFT JOIN patient ON patient.PatientKey = reserve.PatientKey
            WHERE
                ReserveKey = {reserve_key}
        """

    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]
    patient_key = row["PatientKey"]
    schedule_id = get_schedule_id(
        database, row["ReserveDate"], row["Period"], row["Doctor"]
    )
    patient_id = row["ID"]
    birthday = row["Birthday"]

    try:
        gender = patient_utils.get_gender_code(string_utils.xstr(row["Gender"]))
    except Exception:
        try:
            if patient_id[1] == "1":
                gender = "M"
            else:
                gender = "F"
        except Exception:
            gender = "M"

    try:
        nationality = row["Nationality"]
    except Exception:
        nationality = "本國"

    patient_name = row["Name"]
    phone = row["Cellphone"]
    reserve_no = row["ReserveNo"]
    remark = row["Remark"]
    reserve_time = row["ReserveDate"].strftime("%H:%M")

    auth_token, _, _ = get_auth(system_settings)
    id = add_appointment(
        auth=auth_token,
        patient_key=patient_key,
        schedule_id=schedule_id,
        reserve_key=reserve_key,
        birthday=birthday,
        gender=gender,
        patient_id=patient_id,
        nationality=nationality,
        patient_name=patient_name,
        phone=phone,
        reserve_no=reserve_no,
        reserve_time=reserve_time,
        remark=remark,
    )
    sql = f'''
        UPDATE reserve
        SET
            PatInitial = "{id}"
        WHERE
            ReserveKey = {reserve_key}
    '''
    database.exec_sql(sql)


def change_reservation_alleypin_appointments(database, system_settings, reserve_key):
    sql = f"""
        SELECT Source FROM reserve
        WHERE
            ReserveKey = {reserve_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]
    if row["Source"] in ["初診預約", "視訊初診預約"]:
        sql = f"""
            SELECT
                reserve.*,
                temp_patient.ID, temp_patient.Birthday, temp_patient.Cellphone
            FROM reserve
                LEFT JOIN temp_patient ON temp_patient.TempPatientKey = reserve.PatientKey
            WHERE
                ReserveKey = {reserve_key}
        """
    else:
        sql = f"""
            SELECT
                reserve.*,
                patient.ID, patient.Birthday, patient.Nationality, patient.Gender, patient.Cellphone
            FROM reserve
                LEFT JOIN patient ON patient.PatientKey = reserve.PatientKey
            WHERE
                ReserveKey = {reserve_key}
        """

    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]
    id = row["PatInitial"]
    schedule_id = get_schedule_id(
        database, row["ReserveDate"], row["Period"], row["Doctor"]
    )

    reserve_no = row["ReserveNo"]
    reserve_time = row["ReserveDate"].strftime("%H:%M")

    auth_token, _, _ = get_auth(system_settings)
    id = change_appointment(
        auth=auth_token,
        id=id,
        schedule_id=schedule_id,
        reserve_no=reserve_no,
        reserve_time=reserve_time,
    )


def outpatient_checkin_alleypin_appointments(database, system_settings, case_key):
    id = add_case_alleypin_appointments(database, system_settings, case_key)
    if id is None:
        return

    case_utils.set_case_extend(database, case_key, "ScheduleID", id)

    auth_token, _, _ = get_auth(system_settings)
    checkin_appointment(auth=auth_token, id=id)


def reservation_checkin_alleypin_appointments(database, system_settings, reserve_key):
    sql = f"""
        SELECT PatInitial FROM reserve
        WHERE
            ReserveKey = {reserve_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]
    id = row["PatInitial"]
    if id is None:
        return

    auth_token, _, _ = get_auth(system_settings)
    checkin_appointment(auth=auth_token, id=id)


def set_alleypin_reservation_table(
    parent, database, system_settings, year, month, doctor
):
    auth_token, _, _ = get_auth(system_settings)

    doctor_id = personnel_utils.get_person_field_value(database, doctor, "PersonKey")

    sql = f'''
        SELECT * FROM doctor_month_schedule
        WHERE
            Year = {year} AND
            Month = {month} AND
            Doctor = "{doctor}"
    '''
    rows = database.select_record(sql)
    row_count = len(rows)
    progress_dialog = QtWidgets.QProgressDialog(
        "正在上傳班表檔中, 請稍後...",
        "取消",
        0,
        row_count,
        parent,
    )
    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
    progress_dialog.setValue(0)

    for row_no, row in enumerate(rows):
        day = row["Day"]
        if row["CanReservation"] == "True":
            can_reservation = True
        else:
            can_reservation = False

        schedule_key = row["DoctorMonthScheduleKey"]
        reservation_date = f"{year}-{month:0>2}-{day:0>2}"
        weekday = date_utils.str_to_date(reservation_date).weekday()
        period = row["Period"]
        room = registration_utils.get_room(database, period, doctor, weekday=weekday)
        schedule_id = row["ScheduleID"]

        if schedule_id in [None, "None", ""]:
            schedule_id = add_reservation_table(
                auth=auth_token,
                date=reservation_date,
                doctor_id=doctor_id,
                doctor_name=doctor,
                room_id=room,
                room_name=f"{room}診",
                subject_id="60",
                subject_name="中醫科",
                period=period,
                can_reservation=can_reservation,
            )
            sql = f'''
                UPDATE doctor_month_schedule
                SET
                    ScheduleID = "{schedule_id}"
                WHERE
                    DoctorMonthScheduleKey = {schedule_key}
            '''
            database.exec_sql(sql)
        else:
            update_reservation_table(
                auth=auth_token,
                date=reservation_date,
                doctor_id=doctor_id,
                doctor_name=doctor,
                room_id=room,
                room_name=f"{room}診",
                subject_id="60",
                subject_name="中醫科",
                period=period,
                can_reservation=can_reservation,
                schedule_id=schedule_id,
            )

        progress_dialog.setValue(row_no)

    progress_dialog.setValue(row_count)
    progress_dialog.deleteLater()


def add_webhook(system_settings):
    auth_token, _, _ = get_auth(system_settings)

    id = add_webhook_endpoint(system_settings, auth_token)

    return id
