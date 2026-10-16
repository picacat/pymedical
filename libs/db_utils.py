# libs/db_utils.py

import datetime
import re
import traceback

from libs import class_utils, string_utils


# 增加點擊率
def increment_hit_rate(database, table_name, primary_key_field, primary_key):
    if primary_key in [None, ""]:
        return

    sql = f"""
        UPDATE {table_name}
        SET
            HitRate = HitRate + 1
        WHERE
            {primary_key_field} = {primary_key}
    """
    database.exec_sql(sql)


def str_converter(field_value):
    import datetime

    if isinstance(field_value, datetime.datetime):
        field_value = field_value.__str__()
    elif isinstance(field_value, bytes):
        try:
            field_value = field_value.decode("utf8")
        except UnicodeDecodeError:
            field_value = field_value.decode("big5")
    else:
        field_value = field_value.__str__()

    return field_value


def mysql_to_json(rows):
    import json

    json_data = json.dumps(rows, indent=4, ensure_ascii=False, default=str_converter)

    return json_data


def set_default_data(database, table_name):
    if table_name == "system_settings":
        set_system_settings_default_data(database)
    elif table_name == "address_list":
        set_address_list_default_data(database)
    elif table_name == "dict_groups":
        set_dict_groups_default_data(database)
    elif table_name == "charge_settings":
        set_charge_settings_default_data(database)
    elif table_name == "icd10":
        set_icd10_default_data(database)
    elif table_name == "icdmap":
        set_icdmap_default_data(database)
    elif table_name == "clinic":
        set_dict_diagnostic_default_data(database)
    elif table_name == "medicine":
        set_dict_medicine_default_data(database)
    elif table_name == "drug":
        set_dict_drug_default_data(database)
    elif table_name == "refcompound":
        set_dict_compound_default_data(database)


def set_system_settings_default_data(database):
    _system_settings = class_utils.get_system_settings(database, database.CONFIG_FILE)
    _system_settings.post("院所名稱", "中醫診所")
    _system_settings.post("健保業務", "台北業務組")
    _system_settings.post("資源類別", "一般")
    _system_settings.post("掛號類別", "一般門診")
    _system_settings.post("自動轉換一般針灸", "Y")
    _system_settings.post("早班時間", "08:00")
    _system_settings.post("午班時間", "14:00")
    _system_settings.post("晚班時間", "18:00")
    _system_settings.post("護士人數", "0")
    _system_settings.post("藥師人數", "0")
    _system_settings.post("申報藥事服務費", "Y")
    _system_settings.post("針灸認證合格", "Y")
    _system_settings.post("針灸認證合格日期", "2019-01-01")

    _system_settings.post("早班起始號", "1")
    _system_settings.post("午班起始號", "1")
    _system_settings.post("晚班起始號", "1")
    _system_settings.post("現場掛號給號模式", "預約班表")

    _system_settings.post("過去病歷一頁筆數", "30")
    _system_settings.post("自動完成批價作業", "Y")
    _system_settings.post("顯示看診計時器", "Y")
    _system_settings.post("給藥包數", "3")
    _system_settings.post("給藥天數", "7")
    _system_settings.post("用藥指示", "飯後")
    _system_settings.post("候診名單顯示診別", "醫師診別")
    _system_settings.post("詞庫排序", "最後點擊時戳")
    _system_settings.post("診察詞庫排序", "最後點擊時戳")

    _system_settings.post("預設門診類別", "健保")
    _system_settings.post("首次警告次數", "8")
    _system_settings.post("針傷警告次數", "20")

    _system_settings.post("列印藥品總量", "Y")
    _system_settings.post("列印報表雙色印刷", "Y")

    _system_settings.post("老人優待", "Y")
    _system_settings.post("老人優待年齡", "65")

    _system_settings.post("外觀主題", "Fusion")
    _system_settings.post("外觀顏色", "灰色")
    _system_settings.post("顯示側邊欄", "Y")


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
    import json

    from PyQt5 import QtCore, QtWidgets

    filename = "./mysql/default/diagnostic.json"
    field = [
        "ClinicType",
        "ClinicCode",
        "InputCode",
        "ClinicName",
        "Position",
        "Groups",
    ]
    with open(filename, encoding="utf8") as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生診察詞庫檔中, 請稍後...", "取消", 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row["ClinicType"],
                row["ClinicCode"],
                row["InputCode"],
                row["ClinicName"],
                row["Position"],
                row["Groups"],
            ]
            database.insert_record("clinic", field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def set_dict_diagnostic_groups_default_data(database):
    import json

    from PyQt5 import QtCore, QtWidgets

    filename = "./mysql/default/diagnostic_groups.json"
    field = [
        "DictOrderNo",
        "DictGroupsType",
        "DictGroupsTopLevel",
        "DictGroupsLevel2",
        "DictGroupsName",
    ]
    with open(filename, encoding="utf8") as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生診察詞庫類別檔中, 請稍後...", "取消", 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row["DictOrderNo"],
                row["DictGroupsType"],
                row["DictGroupsTopLevel"],
                row["DictGroupsLevel2"],
                row["DictGroupsName"],
            ]
            database.insert_record("dict_groups", field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def set_icd10_default_data(database):
    import json

    from PyQt5 import QtCore, QtWidgets

    filename = "./mysql/default/icd10.json"
    field = [
        "ICDCode",
        "InputCode",
        "ChineseName",
        "EnglishName",
        "SpecialCode",
        "Groups",
    ]
    with open(filename, encoding="utf8") as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生ICD10病名檔中, 請稍後...", "取消", 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row["ICDCode"],
                row["InputCode"],
                row["ChineseName"],
                row["EnglishName"],
                row["SpecialCode"],
                row["Groups"],
            ]
            database.insert_record("icd10", field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def set_icdmap_default_data(database):
    import json

    from PyQt5 import QtCore, QtWidgets

    filename = "./mysql/default/icdmap.json"
    field = [
        "ICD9Code",
        "ICD9ChineseName",
        "ICD9EnglishName",
        "ICD10Code",
        "ICD10ChineseName",
        "ICD10EnglishName",
        "Remark",
    ]
    with open(filename, encoding="utf8") as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生ICD_MAP病名對照檔中, 請稍後...", "取消", 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row["ICD9Code"],
                row["ICD9ChineseName"],
                row["ICD9EnglishName"],
                row["ICD10Code"],
                row["ICD10ChineseName"],
                row["ICD10EnglishName"],
                row["Remark"],
            ]
            database.insert_record("icdmap", field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def set_address_list_default_data(database):
    import json

    from PyQt5 import QtCore, QtWidgets

    filename = "./mysql/default/address_list.json"
    field = [
        "ZipCode",
        "City",
        "District",
        "Street",
        "MailRange",
    ]
    with open(filename, encoding="utf8") as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生地址詞庫檔中, 請稍後...", "取消", 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row["ZipCode"],
                row["City"],
                row["District"],
                row["Street"],
                row["MailRange"],
            ]
            database.insert_record("address_list", field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def set_dict_medicine_default_data(database):
    import json

    from PyQt5 import QtCore, QtWidgets

    filename = "./mysql/default/medicine.json"
    field = [
        "MedicineKey",
        "MedicineType",
        "MedicineMode",
        "MedicineCode",
        "InputCode",
        "InsCode",
        "MedicineName",
        "DrugName",
        "Unit",
        "Description",
    ]
    with open(filename, encoding="utf8") as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生處方詞庫檔中, 請稍後...", "取消", 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row["MedicineKey"],
                row["MedicineType"],
                row["MedicineMode"],
                row["MedicineCode"],
                row["InputCode"],
                row["InsCode"],
                row["MedicineName"],
                row["DrugName"],
                row["Unit"],
                row["Description"],
            ]
            database.insert_record("medicine", field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def set_dict_drug_default_data(database):
    import json

    from PyQt5 import QtCore, QtWidgets

    filename = "./mysql/default/drug.json"
    field = [
        "DrugKey",
        "InsCode",
        "DrugName",
        "MedicineType",
        "Unit",
        "InsPrice",
        "Supplier",
        "ValidDate",
    ]
    with open(filename, encoding="utf8") as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生健保藥品資料檔中, 請稍後...", "取消", 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row["DrugKey"],
                row["InsCode"],
                row["DrugName"],
                row["MedicineType"],
                row["Unit"],
                row["InsPrice"],
                row["Supplier"],
                row["ValidDate"],
            ]
            database.insert_record("drug", field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def set_dict_compound_default_data(database):
    import json

    from PyQt5 import QtCore, QtWidgets

    filename = "./mysql/default/compound.json"
    field = [
        "CompoundKey",
        "MedicineKey",
        "Quantity",
        "Unit",
    ]
    with open(filename, encoding="utf8") as json_file:
        rows = json.load(json_file)
        row_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生成方詞庫檔中, 請稍後...", "取消", 0, row_count, None
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(rows):
            data = [
                row["CompoundKey"],
                row["MedicineKey"],
                row["Quantity"],
                row["Unit"],
            ]
            database.insert_record("refcompound", field, data)
            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()


def get_host_database_dict(database, function):
    database_list = {}

    sql = f"""
        SELECT * FROM hosts
        WHERE
            Function LIKE "%{function}%"
        ORDER BY HostsKey
    """
    rows = database.select_record(sql)
    for row in rows:
        clinic_name = string_utils.xstr(row["ClinicName"])
        database_hosts = class_utils.get_db(
            host=row["Host"],
            user=row["UserName"],
            password=row["Password"],
            database=row["DatabaseName"],
            charset=row["Charset"],
        )
        database_list[clinic_name] = {
            "database": database_hosts,
            "Vendor": string_utils.xstr(row["Vendor"]),
            "HISVersion": string_utils.xstr(row["HISVersion"]),
            "image_dir": string_utils.xstr(row["ImageDir"]),
        }

    return database_list


def get_external_host_database(database, item_type):
    try:
        host_dict = get_host_database_dict(database, item_type)
        host_name = list(host_dict)[0]
        external_database = host_dict[host_name]["database"]
    except (KeyError, IndexError, AttributeError):
        external_database = None

    return external_database


def kill_processlist(database):
    sql = """
        SELECT GROUP_CONCAT(CONCAT('KILL ',id,';') SEPARATOR ' ') FROM information_schema.processlist
        WHERE
            user <> 'system user';
    """
    database.exec_sql(sql)


def get_patient_row(database, patient_key):
    sql = f"""
        SELECT * FROM patient
        WHERE
            PatientKey = {patient_key}
    """
    rows = database.select_record(sql)

    return rows


def get_memo_row(database, patient_key):
    sql = f"""
        SELECT * FROM patient_extension
        WHERE
            PatientKey = {patient_key} AND
            ExtensionType = "Memo"
        ORDER BY PatientExtensionKey DESC LIMIT 1
    """
    rows = database.select_record(sql)

    return rows


def get_dosage_row(database, case_key):
    sql = f"""
        SELECT * FROM dosage
        WHERE
            CaseKey = {case_key}
        ORDER BY MedicineSet
    """
    rows = database.select_record(sql)

    return rows


def get_prescript_row(database, case_key):
    sql = f"""
        SELECT * FROM prescript
        WHERE
            CaseKey = {case_key}
        ORDER BY PrescriptKey
    """
    rows = database.select_record(sql)

    for row in rows:
        prescript_key = row["PrescriptKey"]
        pres_extend_row = get_pres_extend_row(database, prescript_key)
        row["PresExtendJSON"] = pres_extend_row

    return rows


def get_pres_extend_treat_row(database, case_key):
    sql = f"""
        SELECT * FROM presextend
        WHERE
            PrescriptKey = {case_key} AND
            ExtendType = "處置簽章"
        ORDER BY PresExtendKey LIMIT 1
    """
    rows = database.select_record(sql)

    return rows


def get_pres_extend_row(database, prescript_key):
    sql = f"""
        SELECT * FROM presextend
        WHERE
            PrescriptKey = {prescript_key} AND
            ExtendType = "處方簽章"
        ORDER BY PresExtendKey
    """
    rows = database.select_record(sql)

    return rows


# 更新TimeStamp
def update_timestamp(database, table_name, primary_key_field, primary_key):
    if primary_key in [None, ""]:
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
    sql = "SELECT database()"

    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    return rows[0]["database()"]


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


def in_placeholders(values):
    """產生 IN 子句的佔位符字串, 如 3 個值回傳 '%s, %s, %s'"""
    return ", ".join(["%s"] * len(values))


def get_case_keys_by_date_range(database, start_date, end_date):
    """
    取得日期區間內的病歷 CaseKey 清單
    start_date / end_date: 'yyyy-MM-dd' 字串 (含結束日當天)
    """
    end_next_day = (
        datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)
    ).strftime("%Y-%m-%d")

    sql = """
        SELECT CaseKey FROM cases
        WHERE
            CaseDate >= %s AND
            CaseDate < %s
        ORDER BY CaseKey
    """
    rows = database.select_record(sql, (start_date, end_next_day))

    return [row["CaseKey"] for row in rows]


def _group_rows(rows, key_field):
    """依指定欄位分組, 保留原本的排序"""
    grouped = {}
    for row in rows:
        grouped.setdefault(row[key_field], []).append(row)

    return grouped


def _fetch_export_children(database, case_keys, patient_keys, mask_sensitive=False):
    """
    一次撈回一個 chunk 所需的所有子表資料, 回傳分組後的 dict
    排序與原本單筆查詢 (get_dosage_row 等) 一致
    """
    case_params = tuple(case_keys)
    case_in = in_placeholders(case_keys)

    # 病患資料
    patient_dict = {}
    memo_dict = {}
    if patient_keys:
        patient_params = tuple(patient_keys)
        patient_in = in_placeholders(patient_keys)

        sql = f"""
            SELECT * FROM patient
            WHERE
                PatientKey IN ({patient_in})
        """
        patient_rows = database.select_record(sql, patient_params)
        if mask_sensitive:
            for row in patient_rows:
                mask_sensitive_fields(row)

        patient_dict = _group_rows(patient_rows, "PatientKey")

        # 遮蔽模式不匯出 Memo, 連查都不用查
        if not mask_sensitive:
            sql = f"""
                SELECT * FROM patient_extension
                WHERE
                    PatientKey IN ({patient_in}) AND
                    ExtensionType = "Memo"
                ORDER BY PatientExtensionKey DESC
            """
            for row in database.select_record(sql, patient_params):
                memo_dict.setdefault(row["PatientKey"], [row])

    # 處置簽章: presextend.PrescriptKey 存的是 CaseKey, 每筆病歷取第一筆
    treat_dict = {}
    if not mask_sensitive:  # 遮蔽模式不匯出處置簽章, 連查都不用查
        sql = f"""
            SELECT * FROM presextend
            WHERE
                PrescriptKey IN ({case_in}) AND
                ExtendType = "處置簽章"
            ORDER BY PresExtendKey
        """
        for row in database.select_record(sql, case_params):
            treat_dict.setdefault(row["PrescriptKey"], [row])

    # 劑量
    sql = f"""
        SELECT * FROM dosage
        WHERE
            CaseKey IN ({case_in})
        ORDER BY CaseKey, MedicineSet
    """
    dosage_dict = _group_rows(database.select_record(sql, case_params), "CaseKey")

    # 處方
    sql = f"""
        SELECT * FROM prescript
        WHERE
            CaseKey IN ({case_in})
        ORDER BY PrescriptKey
    """
    prescript_rows = database.select_record(sql, case_params)

    # 處方簽章
    pres_extend_dict = {}
    prescript_keys = [row["PrescriptKey"] for row in prescript_rows]
    if prescript_keys:
        sql = f"""
            SELECT * FROM presextend
            WHERE
                PrescriptKey IN ({in_placeholders(prescript_keys)}) AND
                ExtendType = "處方簽章"
            ORDER BY PresExtendKey
        """
        pres_extend_dict = _group_rows(
            database.select_record(sql, tuple(prescript_keys)), "PrescriptKey"
        )

    for row in prescript_rows:
        if mask_sensitive:
            continue  # 遮蔽模式不輸出處方簽章 (PresExtendJSON)

        row["PresExtendJSON"] = pres_extend_dict.get(row["PrescriptKey"], [])

    prescript_dict = _group_rows(prescript_rows, "CaseKey")

    return {
        "patient": patient_dict,
        "memo": memo_dict,
        "treat": treat_dict,
        "dosage": dosage_dict,
        "prescript": prescript_dict,
    }


def export_medical_record_to_json(
    parent, database, filename, case_key_list, mask_sensitive=False
):
    import json
    import os

    from PyQt5 import QtCore, QtWidgets

    case_key_list = [int(k) for k in case_key_list]
    if len(case_key_list) <= 0:
        return False

    BATCH_SIZE = 200
    total = len(case_key_list)

    progress_dialog = QtWidgets.QProgressDialog(
        "正在匯出JSON病歷資料中, 請稍後...", "取消", 0, total, parent
    )
    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
    progress_dialog.setValue(0)

    done = 0
    canceled = False

    with open(filename, "w", encoding="utf8") as f:
        f.write("[\n")
        first = True

        for start in range(0, total, BATCH_SIZE):
            chunk = case_key_list[start : start + BATCH_SIZE]
            sql = f"""
                SELECT * FROM cases
                WHERE
                    CaseKey IN ({in_placeholders(chunk)})
                ORDER BY CaseKey
            """
            rows = database.select_record(sql, tuple(chunk))
            if not rows:
                continue

            case_keys = [row["CaseKey"] for row in rows]
            patient_keys = list(
                {row["PatientKey"] for row in rows if row["PatientKey"] is not None}
            )
            children = _fetch_export_children(
                database, case_keys, patient_keys, mask_sensitive
            )

            for row in rows:
                if mask_sensitive:
                    mask_sensitive_fields(row)  # cases 本身也有 Name 等欄位

                case_key = row["CaseKey"]
                patient_key = row["PatientKey"]

                row["PatientJSON"] = children["patient"].get(patient_key, [])
                if not mask_sensitive:
                    row["TreatJSON"] = children["treat"].get(case_key, [])

                row["DosageJSON"] = children["dosage"].get(case_key, [])
                row["PrescriptJSON"] = children["prescript"].get(case_key, [])

                if not mask_sensitive:
                    row["MemoJson"] = children["memo"].get(patient_key, [])

                if not first:
                    f.write(",\n")
                json.dump(row, f, ensure_ascii=False, default=str_converter)
                first = False

                done += 1
                progress_dialog.setValue(done)
                if progress_dialog.wasCanceled():
                    canceled = True
                    break

            del rows, children
            if canceled:
                break

        f.write("\n]\n")

    progress_dialog.setValue(total)
    progress_dialog.deleteLater()

    if canceled:
        os.remove(filename)  # 不留半份檔案
        return False

    return True


def _to_text(value):
    if isinstance(value, bytes):
        try:
            return value.decode("utf8")
        except UnicodeDecodeError:
            return value.decode("big5")
    return str(value)


def mask_name(value):
    """王小明 → 王○明, 王明 → 王○, 歐陽小明 → 歐○○明"""
    s = _to_text(value).strip()
    n = len(s)
    if n <= 1:
        return s
    if n == 2:
        return s[0] + "○"
    return s[0] + "○" * (n - 2) + s[-1]


def mask_id(value):
    """A123456789 → A12****789"""
    s = _to_text(value).strip()
    n = len(s)
    if n <= 4:
        return "*" * n
    if n <= 7:
        return s[0] + "*" * (n - 1)
    return s[:3] + "*" * (n - 6) + s[-3:]


def mask_phone(value):
    """0912345678 → 0912***678"""
    s = _to_text(value).strip()
    n = len(s)
    if n <= 4:
        return "*" * n
    if n <= 7:
        return s[:2] + "*" * (n - 2)
    return s[:4] + "*" * (n - 7) + s[-3:]


_ADDRESS_PREFIX = re.compile(r"^(\d*\s*.*?[縣市])?(.*?[區鄉鎮市])?")


def mask_address(value):
    """保留縣市與鄉鎮區: 台北市中正區忠孝西路一段100號 → 台北市中正區○○○○"""
    s = _to_text(value).strip()
    match = _ADDRESS_PREFIX.match(s)
    prefix = match.group(0) if match else ""
    if not prefix:
        prefix = s[:3]
    return prefix + "○○○○"


def mask_birthday(value):
    """只保留出生年 (年齡在醫療資料上常用得到): 1980-05-12 → 1980-**-**"""
    s = _to_text(value).strip()
    return s[:4] + "-**-**" if len(s) >= 4 else "****"


def mask_email(value):
    """abc@gmail.com → a***@gmail.com"""
    s = _to_text(value).strip()
    if "@" not in s:
        return "***"
    local, domain = s.split("@", 1)
    return f"{local[:1]}***@{domain}"


# 欄位名稱 → 遮蔽函式; 依實際資料表欄位調整
SENSITIVE_FIELD_MASKERS = {
    "Name": mask_name,
    "Doctor": mask_name,
    "Pharmacist": mask_name,
    "Massager": mask_name,
    "Register": mask_name,
    "Cashier": mask_name,
    "MassageReferrer": mask_name,
    "NursingAssistant": mask_name,
    "ID": mask_id,
    "Birthday": mask_birthday,
    "Telephone": mask_phone,
    "Cellphone": mask_phone,
    "Address": mask_address,
    "Email": mask_email,
}


# 遮蔽模式下直接移除的欄位
EXCLUDED_FIELDS_WHEN_MASKED = [
    "Security",  # IC卡安全簽章
]


# 遮蔽模式下直接移除的欄位
def mask_sensitive_fields(row):
    for field in EXCLUDED_FIELDS_WHEN_MASKED:
        row.pop(field, None)

    for field, masker in SENSITIVE_FIELD_MASKERS.items():
        value = row.get(field)
        if value in (None, "", b""):
            continue
        row[field] = masker(value)

    return row
