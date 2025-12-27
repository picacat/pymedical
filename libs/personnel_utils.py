
import os

from libs import string_utils

PERMISSION_LIST = [
    ['掛號作業', '關閉掛號作業'],
    ['診療作業', '關閉診療作業'],
    ['醫務行政', '關閉醫務行政'],
    ['自費管理', '關閉自費管理'],
    ['申報作業', '關閉申報作業'],
    ['統計表', '關閉統計表'],
    ['分院統計', '關閉分院統計'],
    ['進銷存管理', '關閉進銷存管理'],
    ['設定', '關閉設定'],
    ['系統作業', '關閉系統作業'],
    ['病患資料', '遮蔽電話地址'],
    ['系統作業', '關閉匯出功能'],

    ['門診掛號', '執行門診掛號'],
    ['門診掛號', '修正候診名單'],
    ['門診掛號', '刪除候診名單'],
    ['門診掛號', '健保卡退掛'],
    ['門診掛號', '健保卡寫卡'],
    ['門診掛號', '補印收據'],
    ['門診掛號', '病患資料修正'],
    ['門診掛號', '初診掛號'],
    ['門診掛號', '清除非本日候診名單'],
    ['門診掛號', '開啟雲端藥歷'],
    ['門診掛號', '健保卡掛號'],
    ['門診掛號', '人工手動掛號'],

    ['預約掛號', '執行預約掛號'],
    ['預約掛號', '新增預約'],
    ['預約掛號', '更改預約'],
    ['預約掛號', '刪除預約'],
    ['預約掛號', '查詢預約'],
    ['預約掛號', '預約報到'],
    ['預約掛號', '暫停預約'],
    ['預約掛號', '保留預約'],
    ['預約掛號', '班表設定'],
    ['預約掛號', '匯出預約名單'],

    ['批價作業', '執行批價作業'],
    ['批價作業', '調閱病歷'],

    ['健保卡欠還卡', '執行健保卡欠還卡'],
    ['健保卡欠還卡', '健保還卡'],
    ['健保卡欠還卡', '調閱病歷'],
    ['健保卡欠還卡', '還原欠卡'],

    ['欠還款作業', '執行欠還款作業'],
    ['欠還款作業', '現金還款'],
    ['欠還款作業', '調閱病歷'],

    ['退貨', '執行退貨'],

    ['櫃台購藥', '執行櫃台購藥'],
    ['櫃台購藥', '購買商品'],
    ['櫃台購藥', '購藥明細'],
    ['櫃台購藥', '資料刪除'],
    ['櫃台購藥', '列印名單'],
    ['櫃台購藥', '輸入折扣'],

    ['掛號櫃台結帳', '執行掛號櫃台結帳'],
    ['掛號櫃台結帳', '進入病歷'],
    ['掛號櫃台結帳', '列印日報表'],
    ['掛號櫃台結帳', '匯出日報表'],

    ['病患查詢', '執行病患查詢'],
    ['病患查詢', '調閱資料'],
    ['病患查詢', '資料刪除'],
    ['病患查詢', '匯出名單'],

    ['病患資料', '病患修正'],

    ['健保IC卡資料上傳', '執行健保IC卡資料上傳'],

    ['醫師看診作業', '執行醫師看診作業'],
    ['醫師看診作業', '非醫師病歷登錄'],
    ['醫師看診作業', '病歷登錄'],
    ['醫師看診作業', '候診病歷非主治醫師不可存檔'],

    ['病歷資料', '僅能修改主訴舌診脈象備註'],
    ['病歷資料', '病歷修正'],
    ['病歷資料', '修改單價'],
    ['病歷資料', '更改自費實收金額'],

    ['病歷查詢', '執行病歷查詢'],
    ['病歷查詢', '調閱病歷'],
    ['病歷查詢', '病歷刪除'],
    ['病歷查詢', '匯出實體病歷'],
    ['病歷查詢', '匯出收費明細'],
    ['病歷查詢', '列印單據'],
    ['病歷查詢', '列印報表'],
    ['病歷查詢', '關檔'],

    ['病歷統計', '執行病歷統計'],
    ['病歷統計', '統計全部醫師'],
    ['系統設定', '執行系統設定'],
    ['收費設定', '執行收費設定'],
    ['診察資料', '執行診察資料'],

    ['處方資料', '執行處方資料'],
    ['處方資料', '輸入成方資料'],
    ['處方資料', '更改抽成'],

    ['健保卡讀卡機', '執行健保卡讀卡機'],

    ['醫師班表', '執行醫師班表'],
    ['藥師班表', '執行藥師班表'],
    ['護士跟診表', '執行護士跟診表'],

    ['使用者管理', '執行使用者管理'],
    ['使用者管理', '查看使用者密碼'],
    ['使用者管理', '新增使用者'],
    ['使用者管理', '刪除使用者'],
    ['使用者管理', '編輯使用者'],
    ['使用者管理', '設定權限'],

    ['健保藥品', '執行健保藥品'],

    ['匯出電子病歷交換檔', '執行匯出電子病歷交換檔'],
    ['醫療軟體更新', '執行醫療軟體更新'],
    ['資料回復', '執行資料回復'],

    ['診斷證明書', '執行診斷證明書'],
    ['醫療費用證明書', '執行醫療費用證明書'],

    ['申報檢查', '執行申報檢查'],
    ['健保申報', '執行健保申報'],
    ['健保抽審', '執行健保抽審'],
    ['健保申復', '執行健保申復'],

    ['日報表', '執行日報表'],
    ['醫師統計', '執行醫師統計'],
    ['醫師統計', '統計全部醫師'],
    ['醫師金額統計', '執行醫師金額統計'],
    ['醫師月報表', '執行醫師月報表'],
    ['自費抽成統計', '執行自費抽成統計'],
    ['診數統計', '執行診數統計'],
    ['回診率統計', '執行回診率統計'],
    ['回診率統計', '統計全部醫師'],
    ['未回診統計', '執行未回診統計'],
    ['用藥統計', '執行用藥統計'],
    ['用藥統計', '統計全部醫師'],
    ['健保申報業績', '執行健保申報業績'],
    ['健保申報業績', '統計全部醫師'],
    ['醫師銷售業績統計', '執行醫師銷售業績統計'],
    ['醫師銷售業績統計', '統計全部醫師'],
    ['健保門診優惠統計', '執行健保門診優惠統計'],
    ['健保門診優惠統計', '統計全部醫師'],
    ['綜合業績統計', '執行綜合業績統計'],
    ['業績成長統計', '執行業績成長統計'],
    ['推拿師統計', '執行推拿師統計'],

    ['匯出全部資料庫', '執行匯出全部資料庫'],
    ['匯入全部資料庫', '執行匯入全部資料庫'],

    ['自費銷售記錄', '匯出自費銷售記錄'],
    ['自費銷售抽成總表', '匯出Excel'],
    ['醫師自費銷售金額總表', '匯出Excel'],
    ['執行業務所得統計', '執行執行業務所得統計'],
]


# 取得醫事人員名單
def get_person(database, personnel_type, exclude_person=None, include_person=None):
    if personnel_type == '全部':
        position_condition = ''
    elif personnel_type == '全部醫師':
        position_condition = 'WHERE (Position IN("醫師", "支援醫師"))'
    elif personnel_type == '醫師':
        position_condition = 'WHERE (Position IN("醫師", "支援醫師") AND ID IS NOT NULL)'
    elif personnel_type == '有密碼醫師':
        position_condition = '''
            WHERE (
                Position IN("醫師", "支援醫師") AND
                ID IS NOT NULL AND LENGTH(ID) > 0 AND
                Password IS NOT NULL AND LENGTH(Password) > 0
            )
        '''
    elif personnel_type == '無逗點醫師':
        position_condition = '''
            WHERE (
                Position IN("醫師", "支援醫師") AND
                Name NOT LIKE "%,%" AND
                ID IS NOT NULL AND LENGTH(ID) > 0 AND
                Password IS NOT NULL AND LENGTH(Password) > 0
            )
        '''
    elif personnel_type == '職員':
        position_condition = 'WHERE (Position IN("職員", "護士", "其他"))'
    else:
        position_condition = f'WHERE Position = "{personnel_type}"'

    sql = f'''
        SELECT * FROM person
            {position_condition}
        ORDER BY PersonKey
    '''
    rows = database.select_record(sql)

    personnel_list = []
    for row in rows:
        name = string_utils.xstr(row['Name'])
        if exclude_person is not None and (name == exclude_person or name in exclude_person):
            continue

        personnel_list.append(name)

    if personnel_type == '全部':
        personnel_list += ['掛號機']

    if include_person is not None:
        personnel_list += ['全部醫師']

    return personnel_list


def convert_last_if_alpha(id_str):
    if not id_str:
        return id_str
    
    last = id_str[-1]
    if last.isalpha():
        # 只把最後一個字母轉成數字（A->1...）
        id_str = id_str[:-1] + str(ord(last.upper()) - ord('A') + 1)
    
    return id_str


def get_person_field_value(database, name, field):
    if string_utils.xstr(name) == '':
        return ''

    sql = f'''
        SELECT * FROM person WHERE
        Name = "{name}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ''

    value = string_utils.xstr(rows[0][field])
    # if field == 'ID':
    #     value = convert_last_if_alpha(value)

    return value

    
def get_person_field_count(database, name):
    if string_utils.xstr(name) == '':
        return ''

    sql = f'''
        SELECT * FROM person WHERE
        Name = "{name}"
    '''
    rows = database.select_record(sql)

    return len(rows)


def person_id_to_name(database, person_id):
    if string_utils.xstr(person_id) == '':
        return ''

    sql = f'''
        SELECT Name FROM person WHERE
        ID = "{person_id}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return person_id
    else:
        return string_utils.xstr(rows[0]['Name'])


def get_default_pharmacist(database):
    sql = '''
        SELECT * FROM person
        WHERE
            Position = "藥師" AND
            ID IS NOT NULL
        LIMIT 1
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ''

    return string_utils.xstr(rows[0]['Name'])


def get_pharmacist(database, schedule_date, period):
    pharmacist_name = ''

    sql = f'''
        SELECT * FROM pharmacist_schedule
        WHERE
            ScheduleDate = "{schedule_date}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return pharmacist_name

    row = rows[0]

    pharmacist_list = {
        '早班': string_utils.xstr(row['Pharmacist1']),
        '午班': string_utils.xstr(row['Pharmacist2']),
        '晚班': string_utils.xstr(row['Pharmacist3']),
    }

    return pharmacist_list[period]


def get_doctor_nurse(database, schedule_date, period, doctor):
    nurse_name = ''
    sql = f'''
        SELECT * FROM nurse_schedule
        WHERE
            ScheduleDate = "{schedule_date}" AND
            Doctor = "{doctor}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return nurse_name

    row = rows[0]

    nurse_list = {
        '早班': string_utils.xstr(row['Nurse1']),
        '午班': string_utils.xstr(row['Nurse2']),
        '晚班': string_utils.xstr(row['Nurse3']),
    }

    return nurse_list[period]


def get_nurse_doctor(database, schedule_date, period, nurse):
    nurse_fields = ['Nurse1', 'Nurse2', 'Nurse3']
    doctor_fields = ['', '', '']

    for i in range(len(nurse_fields)):
        sql = f'''
            SELECT * FROM nurse_schedule
            WHERE
                ScheduleDate = "{schedule_date}" AND
                {nurse_fields[i]} = "{nurse}"
        '''
        rows = database.select_record(sql)
        if len(rows) > 0:
            doctor_fields[i] = rows[0]['Doctor']

    doctor_list = {
        '早班': string_utils.xstr(doctor_fields[0]),
        '午班': string_utils.xstr(doctor_fields[1]),
        '晚班': string_utils.xstr(doctor_fields[2]),
    }

    return doctor_list[period]


def get_permission(database, program_name, permission_item, user_name):
    if user_name == '超級使用者':
        if permission_item in ['遮蔽電話地址', '關閉匯出功能']:
            permission = 'N'
        else:
            permission = 'Y'

        return permission

    sql = f'''
        SELECT * FROM person
        WHERE
            Name = "{user_name}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    person_key = rows[0]['PersonKey']
    sql = f'''
        SELECT * FROM permission
        WHERE
            PersonKey = {person_key} AND
            ProgramName = "{program_name}" AND
            PermissionItem = "{permission_item}"
        ORDER BY TimeStamp LIMIT 1
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    return string_utils.xstr(rows[0]['Permission'])


def get_personal_photo_filename(image_file_path, patient_key):
    if image_file_path in [None, '']:
        return None

    filename = f'patient_{patient_key:0>6}.jpg'
    full_filename = os.path.join(image_file_path, filename)

    if not os.path.isfile(full_filename):  # 檔案不存在
        return None

    return full_filename


# 取得人員數
def get_person_count(database, personnel_type):
    if personnel_type == '全部醫師':
        position = 'WHERE (Position IN("醫師", "支援醫師"))'
    elif personnel_type == '醫師':
        position = 'WHERE (Position IN("醫師", "支援醫師") AND ID IS NOT NULL)'
    else:
        position = f'WHERE Position = "{personnel_type}"'

    sql = f'''
        SELECT * FROM person
            {position}
        ORDER BY PersonKey
    '''
    rows = database.select_record(sql)

    return len(rows)
