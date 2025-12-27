# -*- coding: UTF-8 -*-
# 海納川 web service 2022-11-19

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from libs import string_utils


# 傳送目前看診號
def send_seq_number(**kwargs):
    system_settings = kwargs['system_settings']

    url = system_settings.field('webservice')
    if url in [None, '']:
        return

    seq_number = kwargs['seq_number']
    room = kwargs['room']
    doctor = kwargs['doctor']
    clinic_id = system_settings.field('院所代號')

    json_data = {
        "tp": "num",
        "current_no": string_utils.xstr(seq_number),
        "room": room,
        "doctor": doctor,
        "clinic": clinic_id,
    }

    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        response = session.post(url, json=json_data, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        response = None

    return response


# 新增預約
def add_reservation(database, system_settings, reserve_key):
    sql = f'''
        SELECT reserve.*, patient.ID, patient.Birthday FROM reserve
            LEFT JOIN patient ON patient.PatientKey = reserve.PatientKey
        WHERE
            ReserveKey = {reserve_key}
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return

    row = rows[0]
    reserve_date = row['ReserveDate'].strftime('%Y-%m-%d')
    reserve_time = row['ReserveDate'].strftime('%H:%M')
    period = string_utils.xstr(row['Period'])
    patient_key = string_utils.xstr(row['PatientKey'])
    name = string_utils.xstr(row['Name'])
    try:
        birthday = row['Birthday'].strftime('%Y-%m-%d')
    except Exception:
        birthday = None

    patient_id = string_utils.xstr(row['ID'])
    doctor = string_utils.xstr(row['Doctor'])
    room = string_utils.xstr(row['Room'])
    reserve_no = string_utils.xstr(row['ReserveNo'])
    source = string_utils.xstr(row['Source'])
    clinic_id = system_settings.field('院所代號')
    url = system_settings.field('webservice')

    if source in ['初診預約']:
        visit = '初診'
    else:
        visit = '複診'

    json_data = {
        "tp": "reserve",
        "clinic": clinic_id,
        "reservation_date": reserve_date,
        "reservation_time": reserve_time,
        "reservation_no": string_utils.xstr(reserve_no),
        "visit": visit,
        "period": period,
        "room": room,
        "doctor": doctor,
        "patient_id": patient_id,
        "patient_name": name,
        "birthday": birthday,
        "patient_key": patient_key,
        "reserve_key": reserve_key,
    }

    requests.post(url, json=json_data)


# 取消預約
def cancel_reservation(**kwargs):
    system_settings = kwargs['system_settings']
    patient_key = kwargs['patient_key']
    reserve_key = kwargs['reserve_key']
    clinic_id = system_settings.field('院所代號')
    url = system_settings.field('webservice')

    json_data = {
        "tp": "cancelReserve",
        "patient_key": string_utils.xstr(patient_key),
        "reserve_key": string_utils.xstr(reserve_key),
        "clinic": clinic_id,
    }

    requests.post(url, json=json_data)


# 更改預約時間
def change_reservation(database, system_settings, reserve_key, patient_key):
    cancel_reservation(
        system_settings=system_settings,
        patient_key=string_utils.xstr(patient_key),
        reserve_key=string_utils.xstr(reserve_key),
    )
    add_reservation(database, system_settings, reserve_key)
