# libs/db_utils.py

import datetime
import traceback
from libs import string_utils
from libs import class_utils


# 增加點擊率
def increment_hit_rate(database, table_name, primary_key_field, primary_key):
    if primary_key in [None, '']:
        return

    sql = f'''
        UPDATE {table_name}
        SET
            HitRate = HitRate + 1
        WHERE
            {primary_key_field} = {primary_key}
    '''
    database.exec_sql(sql)


def str_converter(field_value):
    import datetime

    if isinstance(field_value, datetime.datetime):
        field_value = field_value.__str__()
    elif isinstance(field_value, bytes):
        try:
            field_value = field_value.decode('utf8')
        except UnicodeDecodeError:
            field_value = field_value.decode('big5')
    else:
        field_value = field_value.__str__()

    return field_value


def mysql_to_json(rows):
    import json

    json_data = json.dumps(rows, indent=4, ensure_ascii=False, default=str_converter)

    return json_data


def set_default_data(database, table_name):
    if table_name == 'system_settings':
        set_system_settings_default_data(database)
    elif table_name == 'address_list':
        set_address_list_default_data(database)
    elif table_name == 'dict_groups':
        set_dict_groups_default_data(database)
    elif table_name == 'charge_settings':
        set_charge_settings_default_data(database)
    elif table_name == 'icd10':
        set_icd10_default_data(database)
    elif table_name == 'icdmap':
        set_icdmap_default_data(database)
    elif table_name == 'clinic':
        set_dict_diagnostic_default_data(database)
    elif table_name == 'medicine':
        set_dict_medicine_default_data(database)
    elif table_name == 'refcompound':
        set_dict_compound_default_data(database)


def set_system_settings_default_data(database):
    _system_settings = class_utils.get_system_settings(database, database.CONFIG_FILE)
    _system_settings.post('院所名稱', '中醫診所')
    _system_settings.post('健保業務', '台北業務組')
    _system_settings.post('資源類別', '一般')
    _system_settings.post('掛號類別', '一般門診')
    _system_settings.post('自動轉換一般針灸', 'Y')
    _system_settings.post('早班時間', '08:00')
    _system_settings.post('午班時間', '14:00')
    _system_settings.post('晚班時間', '18:00')
    _system_settings.post('護士人數', '0')
    _system_settings.post('藥師人數', '0')
    _system_settings.post('申報藥事服務費', 'Y')
    _system_settings.post('針灸認證合格', 'Y')
    _system_settings.post('針灸認證合格日期', '2019-01-01')

    _system_settings.post('早班起始號', '1')
    _system_settings.post('午班起始號', '1')
    _system_settings.post('晚班起始號', '1')
    _system_settings.post('現場掛號給號模式', '預約班表')

    _system_settings.post('預設門診類別', '健保')
    _system_settings.post('首次警告次數', '8')
    _system_settings.post('針傷警告次數', '20')

    _system_settings.post('列印藥品總量', 'Y')
    _system_settings.post('列印報表雙色印刷', 'Y')

    _system_settings.post('老人優待', 'Y')
    _system_settings.post('老人優待年齡', '65')

    _system_settings.post('外觀主題', 'Fusion')
    _system_settings.post('外觀顏色', '藍色')
    _system_settings.post('顯示側邊欄', 'Y')


def set_dict_groups_default_data(database):
    from convert import cvt_groups

    cvt_groups.cvt_pymedical_groups(database)
    cvt_groups.cvt_pymedical_disease_groups(database)
    cvt_groups.cvt_disease_common(database)
    cvt_groups.cvt_disease_treat(database)

    set_dict_diagnostic_groups_default_data(database)


def set_charge_settings_default_data(database):
    from libs import charge_utils

    charge_utils.set_nhi_basic_data(database)
    charge_utils.set_diag_share_basic_data(database)
    charge_utils.set_drug_share_basic_data(database)
    charge_utils.set_discount_basic_data(database)
    charge_utils.set_regist_fee_basic_data(database)


def set_dict_diagnostic_default_data(database):
    from PyQt5 import QtWidgets, QtCore
    import json

    filename = './mysql/default/diagnostic.json'
    field = [
        'ClinicType', 'ClinicCode', 'InputCode', 'ClinicName', 'Position', 'Groups',
    ]
    with open(filename, encoding='utf8') as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在產生診察詞庫檔中, 請稍後...', '取消', 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row['ClinicType'], row['ClinicCode'], row['InputCode'], row['ClinicName'],
                row['Position'], row['Groups'],
            ]
            database.insert_record('clinic', field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def set_dict_diagnostic_groups_default_data(database):
    from PyQt5 import QtWidgets, QtCore
    import json

    filename = './mysql/default/diagnostic_groups.json'
    field = [
        'DictOrderNo', 'DictGroupsType', 'DictGroupsTopLevel', 'DictGroupsLevel2',
        'DictGroupsName',
    ]
    with open(filename, encoding='utf8') as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在產生診察詞庫類別檔中, 請稍後...', '取消', 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row['DictOrderNo'], row['DictGroupsType'], row['DictGroupsTopLevel'], row['DictGroupsLevel2'],
                row['DictGroupsName'],
            ]
            database.insert_record('dict_groups', field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def set_icd10_default_data(database):
    from PyQt5 import QtWidgets, QtCore
    import json

    filename = './mysql/default/icd10.json'
    field = [
        'ICDCode', 'InputCode', 'ChineseName', 'EnglishName', 'SpecialCode', 'Groups',
    ]
    with open(filename, encoding='utf8') as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在產生ICD10病名檔中, 請稍後...', '取消', 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row['ICDCode'], row['InputCode'], row['ChineseName'], row['EnglishName'],
                row['SpecialCode'], row['Groups'],
            ]
            database.insert_record('icd10', field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def set_icdmap_default_data(database):
    from PyQt5 import QtWidgets, QtCore
    import json

    filename = './mysql/default/icdmap.json'
    field = [
        'ICD9Code', 'ICD9ChineseName', 'ICD9EnglishName',
        'ICD10Code', 'ICD10ChineseName', 'ICD10EnglishName',
        'Remark',
    ]
    with open(filename, encoding='utf8') as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在產生ICD_MAP病名對照檔中, 請稍後...', '取消', 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row['ICD9Code'], row['ICD9ChineseName'], row['ICD9EnglishName'],
                row['ICD10Code'], row['ICD10ChineseName'], row['ICD10EnglishName'],
                row['Remark']
            ]
            database.insert_record('icdmap', field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def set_address_list_default_data(database):
    from PyQt5 import QtWidgets, QtCore
    import json

    filename = './mysql/default/address_list.json'
    field = [
        'ZipCode', 'City', 'District', 'Street', 'MailRange',
    ]
    with open(filename, encoding='utf8') as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在產生地址詞庫檔中, 請稍後...', '取消', 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row['ZipCode'], row['City'], row['District'], row['Street'], row['MailRange']
            ]
            database.insert_record('address_list', field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def set_dict_medicine_default_data(database):
    from PyQt5 import QtWidgets, QtCore
    import json

    filename = './mysql/default/medicine.json'
    field = [
        'MedicineKey',
        'MedicineType', 'MedicineMode', 'MedicineCode', 'InputCode', 'InsCode', 'MedicineName',
        'Unit', 'Description'
    ]
    with open(filename, encoding='utf8') as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在產生處方詞庫檔中, 請稍後...', '取消', 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row['MedicineKey'],
                row['MedicineType'], row['MedicineMode'], row['MedicineCode'], row['InputCode'],
                row['InsCode'], row['MedicineName'], row['Unit'], row['Description'],
            ]
            database.insert_record('medicine', field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def set_dict_compound_default_data(database):
    from PyQt5 import QtWidgets, QtCore
    import json

    filename = './mysql/default/compound.json'
    field = [
        'CompoundKey', 'MedicineKey', 'Quantity', 'Unit',
    ]
    with open(filename, encoding='utf8') as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在產生成方詞庫檔中, 請稍後...', '取消', 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row['CompoundKey'], row['MedicineKey'], row['Quantity'], row['Unit'],
            ]
            database.insert_record('refcompound', field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def get_host_database_dict(database, function):
    database_list = {}

    sql = f'''
        SELECT * FROM hosts
        WHERE
            Function LIKE "%{function}%"
        ORDER BY HostsKey
    '''
    rows = database.select_record(sql)
    for row in rows:
        clinic_name = string_utils.xstr(row['ClinicName'])
        database_hosts = class_utils.get_db(
            host=row['Host'],
            user=row['UserName'],
            password=row['Password'],
            database=row['DatabaseName'],
            charset=row['Charset'],
        )
        database_list[clinic_name] = {
            'database': database_hosts,
            'Vendor': string_utils.xstr(row['Vendor']),
            'HISVersion': string_utils.xstr(row['HISVersion']),
            'image_dir': string_utils.xstr(row['ImageDir']),
        }

    return database_list


def get_external_host_database(database, item_type):
    try:
        host_dict = get_host_database_dict(database, item_type)
        host_name = list(host_dict)[0]
        external_database = host_dict[host_name]['database']
    except (KeyError, IndexError, AttributeError):
        external_database = None

    return external_database


def kill_processlist(database):
    sql = '''
        SELECT GROUP_CONCAT(CONCAT('KILL ',id,';') SEPARATOR ' ') FROM information_schema.processlist
        WHERE
            user <> 'system user';
    '''
    database.exec_sql(sql)


def get_patient_row(database, patient_key):
    sql = f'''
        SELECT * FROM patient
        WHERE
            PatientKey = {patient_key}
    '''
    rows = database.select_record(sql)

    return rows


def get_dosage_row(database, case_key):
    sql = f'''
        SELECT * FROM dosage
        WHERE
            CaseKey = {case_key}
        ORDER BY MedicineSet
    '''
    rows = database.select_record(sql)

    return rows


def get_prescript_row(database, case_key):
    sql = f'''
        SELECT * FROM prescript
        WHERE
            CaseKey = {case_key}
        ORDER BY PrescriptKey
    '''
    rows = database.select_record(sql)

    for row in rows:
        prescript_key = row['PrescriptKey']
        pres_extend_row = get_pres_extend_row(database, prescript_key)
        row['PresExtendJSON'] = pres_extend_row

    return rows


def get_pres_extend_treat_row(database, case_key):
    sql = f'''
        SELECT * FROM presextend
        WHERE
            PrescriptKey = {case_key} AND
            ExtendType = "處置簽章"
        ORDER BY PresExtendKey LIMIT 1
    '''
    rows = database.select_record(sql)

    return rows


def get_pres_extend_row(database, prescript_key):
    sql = f'''
        SELECT * FROM presextend
        WHERE
            PrescriptKey = {prescript_key} AND
            ExtendType = "處方簽章"
        ORDER BY PresExtendKey
    '''
    rows = database.select_record(sql)

    return rows


def export_medical_record_to_json(parent, database, filename, case_key_list):
    from PyQt5 import QtWidgets, QtCore

    case_key_list = str(case_key_list)[1:-1]

    if len(case_key_list) <= 0:
        return

    sql = f'''
        SELECT * FROM cases
        WHERE
            CaseKey in ({case_key_list})
    '''
    rows = database.select_record(sql)

    max_progress = len(rows)
    progress_dialog = QtWidgets.QProgressDialog(
        '正在匯出JSON病歷資料中, 請稍後...', '取消', 0, max_progress, parent
    )

    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
    progress_dialog.setValue(0)
    for i, row in enumerate(rows):
        case_key = row['CaseKey']
        patient_key = row['PatientKey']

        row['PatientJSON'] = get_patient_row(database, patient_key)
        row['TreatJSON'] = get_pres_extend_treat_row(database, case_key)
        row['DosageJSON'] = get_dosage_row(database, case_key)
        row['PrescriptJSON'] = get_prescript_row(database, case_key)
        progress_dialog.setValue(i)

    progress_dialog.setValue(max_progress)
    json_data = mysql_to_json(rows)
    text_file = open(filename, "w", encoding='utf8')
    text_file.write(str(json_data))
    text_file.close()


# 更新TimeStamp
def update_timestamp(database, table_name, primary_key_field, primary_key):
    if primary_key in [None, '']:
        return

    sql = f'''
        UPDATE {table_name}
        SET
            TimeStamp = "{datetime.datetime.now()}"
        WHERE
            {primary_key_field} = {primary_key}
    '''
    database.exec_sql(sql)


def get_current_database_name(database):
    sql = 'SELECT database()'

    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    return rows[0]['database()']


def with_transaction(func):
    """
    裝飾器：自動包裝資料庫交易操作流程（begin → commit → rollback）

    適用對象：
        實作以下方法的資料庫類別：
        - begin_transaction()
        - commit()
        - rollback()

    功能說明：
        - 於執行指定函式前自動啟動資料庫交易
        - 若執行成功，自動 commit()
        - 若發生例外，自動 rollback() 並印出 traceback

    使用方式：
        >>> from libs.db_utils import with_transaction
        >>> 
        >>> @with_transaction
        >>> def update_case(self, case_key):
        >>>     sql = f"UPDATE cases SET name = 'test' WHERE CaseKey = {case_key}"
        >>>     self.database.exec_sql(sql, auto_commit=False)

    備註：
        - 函式內部請使用 auto_commit=False，以免跳過 rollback 機制
        - 如需例外處理可於呼叫端使用 try/except 包裝

    Returns:
        原始函式執行結果（若無錯誤）
    Raises:
        原始例外錯誤，供呼叫端處理
    """
    def wrapper(self, *args, **kwargs):
        self.begin_transaction()
        try:
            result = func(self, *args, **kwargs)
            self.commit()
            return result
        except Exception as e:
            self.rollback()
            print(f"⚠️ Transaction rollback due to error: {e}")
            traceback.print_exc()
            raise e

    return wrapper
