from flask import Flask, request, jsonify
import datetime

from classes import db
from classes import system_settings

from libs import string_utils
from libs import number_utils
from libs import date_utils
from libs import registration_utils

app = Flask(__name__)


CONFIG_FILE1 = './pymedical1_api.conf'
# CONFIG_FILE2 = './pymedical2_api.conf'
# CONFIG_FILE3 = './pymedical3_api.conf'
# CONFIG_FILE4 = './pymedical4_api.conf'

database1 = db.Database(CONFIG_FILE1)
# database2 = db.Database(CONFIG_FILE2)
# database3 = db.Database(CONFIG_FILE3)
# database4 = db.Database(CONFIG_FILE4)

system_setting1 = system_settings.SystemSettings(database1, CONFIG_FILE1)
# system_setting2 = system_settings.SystemSettings(database2, CONFIG_FILE2)
# system_setting3 = system_settings.SystemSettings(database3, CONFIG_FILE3)
# system_setting4 = system_settings.SystemSettings(database4, CONFIG_FILE4)

clinic_list = [
    '板橋新生堂中醫診所',
    # '林錡宏中醫診所',
    # '明醫中醫診所',
    # '厚德堂中醫診所',
]

db_list = {
    '板橋新生堂中醫診所': database1,
    # '林錡宏中醫診所': database2,
    # '明醫中醫診所': database3,
    # '厚德堂中醫診所': database4,
}

setting_list = {
    '板橋新生堂中醫診所': system_setting1,
    # '林錡宏中醫診所': system_setting2,
    # '明醫中醫診所': system_setting3,
    # '厚德堂中醫診所': system_setting4,
}

clinic_name_alias_list = {
    '板橋新生堂中醫診所': '板橋新生堂中醫診所',
    # '林錡宏中醫診所': '明醫中醫聯合診所',
    # '明醫中醫診所': '明醫中醫聯合診所',
}


@app.route('/')
def index():
    rows = []
    return jsonify(rows)


def _get_week_day_name(reserve_date):
    weekday = date_utils.str_to_date(reserve_date).weekday()
    week_day_name = date_utils.get_weekday_name(weekday)

    return week_day_name


def _get_reservation_table(database, reserve_date, period, doctor):
    status = {}
    weekday_name = _get_week_day_name(reserve_date)

    sql = f'''
        SELECT Time, ReserveNo, Period FROM reservation_table
        WHERE
            Doctor = "{doctor}" AND
            Period = "{period}" AND
            ReserveNo IS NOT NULL AND
            Weekday = "{weekday_name}"
        ORDER BY ReserveNo
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:  # 先讀指定班表, 找不到再讀一般班表
        sql = f'''
            SELECT Time, ReserveNo, Period FROM reservation_table
            WHERE
                Doctor = "{doctor}" AND
                Period = "{period}" AND
                ReserveNo IS NOT NULL AND
                Weekday IS NULL
            ORDER BY ReserveNo
        '''
        rows = database.select_record(sql)

    return rows


def _get_patient_row(database, patient_id):
    sql = f'''
        SELECT * FROM patient
        WHERE
            ID = "{patient_id}"
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        row = None
    else:
        row = rows[0]

    return row


def _get_current_period(system_settings):
    current_time = datetime.datetime.now().strftime('%H:%M')
    try:
        if current_time >= system_settings.field('晚班時間'):
            period = '晚班'
        elif current_time >= system_settings.field('午班時間'):
            period = '午班'
        else:
            period = '早班'
    except TypeError:
        period = '早班'

    return period

def _create_temp_patient(database, patient_name, patient_id, birthday, cellphone, email):
    sql = f'''
        SELECT TempPatientKey from temp_patient
        WHERE
            ID = "{patient_id}" AND
            Name = "{patient_name}"
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        return rows[0]['TempPatientKey']

    fields = ['Name', 'ID', 'Birthday', 'Cellphone', 'Address']
    data = [patient_name, patient_id, birthday, cellphone, email]

    temp_patient_key = database.insert_record('temp_patient', fields, data)

    return temp_patient_key


# 取得候診名單
@app.route('/waiting_list')
def get_waiting_list():
    status = {}

    today = datetime.datetime.today().strftime('%Y-%m-%d')

    clinic_waiting_status = {}
    for clinic_name in clinic_list:
        database = db_list[clinic_name]
        system_settings = setting_list[clinic_name]
        current_period = _get_current_period(system_settings)

        sql = f'''
            SELECT * FROM wait
            WHERE
                Date(CaseDate) = "{today}" AND
                Period = "{current_period}" AND
                DoctorDone = "False"
            ORDER BY Room, RegistNo
        '''
        rows = database.select_record(sql)
        if len(rows) == 0:
            sql = f'''
                SELECT * FROM wait
                WHERE
                    Date(CaseDate) = "{today}" AND
                    Period = "{current_period}" AND
                    DoctorDone = "True"
                GROUP BY Doctor
                HAVING COUNT(*) > 0
                ORDER BY RegistNo DESC LIMIT 1
            '''
            rows = database.select_record(sql)

        wait_status = {}
        waiting_count = {}
        waiting_list = {}
        for row in rows:
            room = row['Room']
            room_name = f'room{room}'
            waiting_count[room_name] = {}

        for row in rows:
            room = row['Room']
            doctor = string_utils.xstr(row['Doctor'])
            regist_no = row['RegistNo']
            room_name = f'room{room}'
            try:
                waiting_list[room].append(regist_no)
            except KeyError:
                waiting_list[room] = [regist_no]

            waiting_count[room_name]['waiting_list'] = waiting_list[room]
            waiting_count[room_name]['doctor'] = doctor

            sql = f'''
                SELECT SeqNumber FROM seq_number
                WHERE
                    Date(CaseDate) = "{today}" AND
                    Room = "{room}"
                LIMIT 1
            '''
            rows = database.select_record(sql)
            if len(rows) <= 0:
                current_seq_no = 0
            else:
                current_seq_no = number_utils.get_integer(rows[0]['SeqNumber'])

            waiting_count[room_name]['current_seq_no'] = current_seq_no

            # in_progress = string_utils.xstr(row['InProgress'])
            # if in_progress == 'Y':
            #     waiting_count[room_name]['in_progress'] = regist_no

            waiting_count[room_name]['status'] = "success"
            clinic_waiting_status[clinic_name] = waiting_count

        wait_status['waiting_list'] = clinic_waiting_status

    return jsonify(wait_status)


# 查詢初診身份資
@app.route('/first_visit', methods=['GET', 'POST'])
def first_visit():
    status = {}
    patient_id = request.json['patient_id']
    clinic_name = request.json['clinic_name']

    if clinic_name is None:
        status['status'] = 'error'
        status['message'] = 'clinic_name is required'
        return jsonify(status)

    try:
        database = db_list[clinic_name]
    except Exception:
        status['status'] = 'error'
        status['message'] = 'clinic_name error'
        return jsonify(status)

    if patient_id is None:
        status['status'] = 'error'
        status['message'] = 'patient_id is required'
        return jsonify(status)

    patient_row = _get_patient_row(database, patient_id)

    status['status'] = 'success'
    if patient_row is None:
        status['data'] = '初診'
    else:
        status['data'] = '複診'

    return jsonify(status)


# 查詢預約資料
@app.route('/list_reservation', methods=['GET', 'POST'])
def list_reservation():
    status = {}
    patient_id = request.json['patient_id']
    clinic_name = request.json['clinic_name']

    if clinic_name is None:
        status['status'] = 'error'
        status['message'] = 'clinic_name id is required'
        return jsonify(status)

    try:
        database = db_list[clinic_name]
    except Exception:
        status['status'] = 'error'
        status['message'] = 'clinic_name error'
        return jsonify(status)

    if patient_id is None:
        status['status'] = 'error'
        status['message'] = 'patient_id is required'
        return jsonify(status)

    patient_row = _get_patient_row(database, patient_id)
    if patient_row is None:
        status['status'] = 'error'
        status['message'] = 'patient not found'
        return jsonify(status)

    today = date_utils.date_to_str()
    patient_key = patient_row['PatientKey']
    sql = f'''
        SELECT reserve.*, patient.Birthday, patient.ID, patient.Cellphone FROM reserve
            LEFT JOIN patient ON patient.PatientKey = reserve.PatientKey
        WHERE
            reserve.PatientKey = {patient_key} AND
            DATE(ReserveDate) >= "{today}" AND
            Arrival = "False"
    '''
    rows = database.select_record(sql)

    reservation_list = []
    for row in rows:
        reserve_date = f"{row['ReserveDate'].year}-{row['ReserveDate'].month:0>2}-{row['ReserveDate'].day:0>2}"
        reservation_table = {}
        reservation_table['clinic_name'] = clinic_name
        reservation_table['reservation_date'] = reserve_date
        reservation_table['period'] = row['Period']
        reservation_table['doctor'] = row['Doctor']
        reservation_table['room'] = row['Room']
        reservation_table['reservation_no'] = row['ReserveNo']
        reservation_table['patient_name'] = row['Name']
        reservation_table['patient_id'] = patient_id
        try:
            reservation_table['birthday'] = row['Birthday'].strftime('%Y-%m-%d')
        except Exception:
            reservation_table['birthday'] = None

        reservation_table['cellphone'] = row['Cellphone']
        reservation_table['reserve_key'] = row['ReserveKey']
        reservation_table['patient_key'] = row['PatientKey']

        reservation_list.append(reservation_table)

    return jsonify(reservation_list)


# 寫入預約掛號
@app.route('/write_reservation', methods=['GET', 'POST'])
def write_reservation():
    status = {}
    clinic_name = request.json['clinic_name']
    reservation_date = request.json['reservation_date']
    reservation_time = request.json['reservation_time']
    reservation_no = request.json['reservation_no']
    visit = request.json['visit']

    period = request.json['period']
    doctor = request.json['doctor']
    patient_id = request.json['patient_id']
    patient_name = request.json['patient_name']
    birthday = request.json['birthday']
    cellphone = request.json['cellphone']
    email = request.json['email']

    if clinic_name is None:
        status['status'] = 'error'
        status['message'] = 'clinic_name id is required'
        return jsonify(status)

    try:
        database = db_list[clinic_name]
    except Exception:
        status['status'] = 'error'
        status['message'] = 'clinic_name error'
        return jsonify(status)

    if patient_id is None:
        status['status'] = 'error'
        status['message'] = 'patient_id is required'
        return jsonify(status)

    if visit not in ['初診', '複診']:
        visit = '複診'

    if reservation_date is None:
        status['status'] = 'error'
        status['message'] = 'reservation_date is required'
        return jsonify(status)

    if reservation_time is None:
        status['status'] = 'error'
        status['message'] = 'reservation_time is required'
        return jsonify(status)

    if reservation_no is None:
        status['status'] = 'error'
        status['message'] = 'reservation_no is required'
        return jsonify(status)

    if period is None:
        status['status'] = 'error'
        status['message'] = 'period is required'
        return jsonify(status)

    if doctor is None:
        status['status'] = 'error'
        status['message'] = 'doctor is required'
        return jsonify(status)

    if visit == '初診':
        if patient_name is None:
            status['status'] = 'error'
            status['message'] = 'patient_name is required'
            return jsonify(status)

        patient_key = _create_temp_patient(database, patient_name, patient_id, birthday, cellphone, email)
        source = '網路初診預約'
    else:
        patient_row = _get_patient_row(database, patient_id)
        if patient_row is None:
            status['status'] = 'error'
            status['message'] = 'patient not found'
            return jsonify(status)

        patient_key = patient_row['PatientKey']
        source = '網路預約'

    if registration_utils.is_reservation_full(database, reservation_date, period, reservation_no, doctor):
        status['status'] = 'error'
        status['message'] = 'reservation full'
        return jsonify(status)

    reservation_exists = registration_utils.is_reservation_exists(database, patient_key, reservation_date)
    if reservation_exists:
        status['status'] = 'error'
        status['message'] = 'reservation exists'
        return jsonify(status)

    if reservation_time not in [None, '']:
        reservation_date = f'{reservation_date} {reservation_time}:00'

    room = registration_utils.get_room(database, period, doctor)
    fields = [
        'PatientKey', 'Name', 'ReserveDate', 'Period',
        'Room', 'ReserveNo', 'Doctor', 'Source',
        'CreateTime',

    ]

    data = [
        patient_key,
        patient_name,
        date_utils.str_to_date(reservation_date),
        period,
        room,
        reservation_no,
        doctor,
        source,
        datetime.datetime.now(),
    ]
    reserve_key = database.insert_record('reserve', fields, data)

    status['status'] = 'success'
    status['data'] = {
        'reserve_key': reserve_key,
        'patient_key': patient_key,
    }

    return jsonify(status)


@app.route('/cancel_reservation', methods=['GET', 'POST'])
def cancel_reservation():
    status = {}
    clinic_name = request.json['clinic_name']
    reserve_key = request.json['reserve_key']
    patient_key = request.json['patient_key']

    if clinic_name is None:
        status['status'] = 'error'
        status['message'] = 'clinic_name id is required'
        return jsonify(status)

    try:
        database = db_list[clinic_name]
    except Exception:
        status['status'] = 'error'
        status['message'] = 'clinic_name error'
        return jsonify(status)

    if patient_key is None:
        status['status'] = 'error'
        status['message'] = 'patient_key is required'
        return jsonify(status)

    if reserve_key is None:
        status['status'] = 'error'
        status['message'] = 'reserve_key is required'
        return jsonify(status)

    sql = f'''
        DELETE FROM reserve
        WHERE
            PatientKey = {patient_key} AND
            ReserveKey = {reserve_key}
    '''
    database.exec_sql(sql)

    status['status'] = 'success'
    status['message'] = 'reservation canceled'

    return jsonify(status)
