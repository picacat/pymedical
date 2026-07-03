import datetime
import re

from PyQt5.QtWidgets import QMessageBox

from libs import (
    class_utils,
    date_utils,
    dialog_utils,
    string_utils,
    system_utils,
    validator_utils,
)


# 尋找病患資料
def search_patient(
    ui, database, settings, keyword, verify_keyword=None, use_patient_key=False
):
    if keyword.isnumeric():
        if len(keyword) >= 7:
            sql = f"""
                SELECT * FROM patient
                WHERE
                    Telephone LIKE "%{keyword}%" OR
                    Cellphone LIKE "%{keyword}%"
            """
        else:
            if use_patient_key:
                sql = f"""
                    SELECT * FROM patient
                    WHERE
                        PatientKey = {keyword}
                """
            else:
                sql = f"""
                    SELECT * FROM patient
                    WHERE
                        (PatientKey = {keyword} OR
                         ChartNo = {keyword})
                """
    else:
        patient_key_script = ""
        if verify_keyword is not None:
            if "-" in verify_keyword or "." in verify_keyword or "/" in verify_keyword:
                pass
            elif verify_keyword.isnumeric():
                patient_key_script = f"(PatientKey = {verify_keyword}) OR "

        sql = f'''
            SELECT * FROM patient
            WHERE
                {patient_key_script}
                (Name like "%{keyword}%") OR
                (ID like "{keyword}%") OR
                (Birthday = "{keyword}") OR
                (Telephone LIKE "%{keyword}%") OR
                (Cellphone LIKE "%{keyword}%")
            ORDER BY PatientKey
        '''

    try:
        rows = database.select_record(sql)
    except Exception:
        return None

    row_count = len(rows)

    if row_count <= 0:
        if keyword.isnumeric() and len(keyword) == 10:
            keyword = f"{keyword[:4]}-{keyword[4:7]}-{keyword[7:10]}"
            sql = f"""
                SELECT * FROM patient
                WHERE
                    Telephone LIKE "%{keyword}%" OR
                    Cellphone LIKE "%{keyword}%"
            """
            try:
                rows = database.select_record(sql)
            except Exception:
                return None

            if len(rows) <= 0:
                return None
        else:
            return None
    elif row_count >= 2:
        dialog = dialog_utils.get_dialog_patient(ui, database, settings, rows)
        dialog.exec_()
        patient_key = dialog.get_patient_key()
        if patient_key is None:  # 取消查詢
            return -1

        sql = f"""
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        """
        rows = database.select_record(sql)

    return rows


def select_patient(
    parent, database, system_settings, table_name, primary_key_field, keyword=None
):
    primary_key = ""

    dialog = dialog_utils.get_dialog_select_patient(
        parent, database, system_settings, table_name, primary_key_field, keyword
    )
    if dialog.exec_():
        primary_key = dialog.get_primary_key()

    if primary_key in ["", None]:
        primary_key = -1

    dialog.deleteLater()

    return primary_key


def get_patient_by_keyword(
    parent, database, system_settings, table_name, primary_key_field, keyword=None
):
    if keyword is not None and keyword.isdigit() and len(keyword) <= 6:
        temp_keyword = validator_utils.get_exp_date(keyword)
        if temp_keyword == keyword:
            return keyword  # primary key

    condition = [
        f'Name LIKE "%{keyword}%"',
        f'ID LIKE "{keyword}%"',
        f'Telephone LIKE "%{keyword}%"',
        f'Cellphone LIKE "{keyword}%"',
    ]

    pattern = re.compile(validator_utils.DATE_REGEXP)
    pattern_zh_tw = re.compile(validator_utils.DATE_REGEXP_ZH_TW)
    try:
        if keyword.isdigit():
            if pattern.match(keyword) or pattern_zh_tw.match(keyword):
                date_keyword = date_utils.date_to_west_date(keyword)
            else:
                date_keyword = validator_utils.get_exp_date(keyword)

            condition.append(f'(Birthday = "{date_keyword}" OR PatientKey = {keyword})')
    except Exception:
        pass

    if len(keyword) >= 2:
        condition.append(f'Address LIKE "%{keyword}%"')

    condition = " OR ".join(condition)
    sql = f"""
        SELECT {primary_key_field} FROM {table_name}
        WHERE
            {condition}
    """
    try:
        rows = database.select_record(sql)
    except Exception:
        system_utils.show_message_box(
            QMessageBox.Critical,
            "資料查詢錯誤",
            '<font size="5" color="red"><b>資料查詢條件設定有誤, 請重新查詢.</b></font>',
            "請檢視查詢的內容是否有標點符號或其他字元.",
        )
        return None

    if len(rows) == 1:
        patient_key = rows[0][primary_key_field]
    else:
        patient_key = select_patient(
            parent,
            database,
            system_settings,
            table_name,
            primary_key_field,
            keyword,
        )

    return patient_key


# 取得性別
def get_gender(gender_code):
    gender = None

    if gender_code in ["1", "A", "C", "Y", "M"]:
        gender = "男"
    elif gender_code in ["2", "B", "D", "X", "F"]:
        gender = "女"

    return gender


# 取得國籍
def get_nationality(gender_code):
    nationality = "本國"

    if gender_code in ["1", "2"]:
        nationality = "本國"
    elif gender_code in ["C", "D"]:
        nationality = "外國"
    elif gender_code in ["A", "B"]:
        nationality = "居留證"
    elif gender_code in ["Y", "X"]:
        nationality = "遊民"

    return nationality


# 檢查兩年內未就診
def is_two_years_ago_visit(database, patient_key):
    two_year_ago_visit = False
    today = datetime.datetime.now()

    two_years_ago = today.replace(year=today.year - 2)
    last_month_year = two_years_ago.year
    last_month = two_years_ago.month - 1
    if last_month <= 0:
        last_month = 12
        last_month_year -= 1

    start_date = two_years_ago.replace(
        year=last_month_year, month=last_month, day=1
    ).strftime("%Y-%m-%d")

    # start_date = (today - datetime.timedelta(days=2*365)).replace(day=1).date()  # 健保規定兩年內未就診是指兩年內未就診的整月, 要從上月初開始算

    # sql = f'''
    #     SELECT CaseKey FROM cases
    #     WHERE
    #         PatientKey = {patient_key}
    # '''
    # rows = database.select_record(sql)
    # if len(rows) <= 0:  # 從來沒來過，不算兩年內未就診
    #     return False

    # 讀取start_date以後的病歷
    sql = f'''
        SELECT CaseKey FROM cases
        WHERE
            PatientKey = {patient_key} AND
            DATE(CaseDate) >= "{start_date}"
        LIMIT 1
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        two_year_ago_visit = True

    return two_year_ago_visit


# 檢查兩年內未就診
def is_no_return_days(database, patient_key, no_return_days):
    no_return = False
    start_date = (
        datetime.datetime.now() - datetime.timedelta(days=no_return_days)
    ).date()

    sql = f'''
        SELECT CaseKey FROM cases
        WHERE
            PatientKey = {patient_key} AND
            DATE(CaseDate) >= "{start_date}"
        LIMIT 1
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        no_return = True

    return no_return


# 取得初複診
def is_first_visit(database, patient_key):
    if patient_key in ["", None]:
        return False

    first_visit = False

    sql = f"""
        SELECT CaseKey FROM cases
        WHERE
            PatientKey = {patient_key}
        LIMIT 1
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        first_visit = True

    return first_visit


# 取得初複診
def get_visit(database, patient_key):
    visit = "複診"
    sql = f"""
        SELECT * FROM patient
        WHERE
            PatientKey = {patient_key}
    """
    row = database.select_record(sql)[0]
    if row["InitDate"] is None:
        return visit

    current_date = datetime.datetime.now()
    if (
        row["InitDate"].year == current_date.year
        and row["InitDate"].month == current_date.month
        and row["InitDate"].day == current_date.day
    ):
        visit = "初診"

    return visit


# 取得初診日期
def get_init_date(database, system_settings, patient_key):
    sql = f"""
        SELECT * FROM patient
        WHERE
            PatientKey = {patient_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    row = rows[0]
    init_date = string_utils.xstr(row["InitDate"])
    ins_judge_init_date = system_settings.field("電子化抽審初診日期")

    if (
        init_date != ""
        and ins_judge_init_date is not None
        and ins_judge_init_date != ""
        and init_date >= ins_judge_init_date
    ):
        init_date = string_utils.xstr(row["InitDate"].date())
        start_date = f"{init_date} 00:00:00"
        end_date = f"{init_date} 23:59:59"

        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                InsType = "健保" AND
                PatientKey = {patient_key} AND
                CaseDate BETWEEN "{start_date}" AND "{end_date}"
            ORDER BY CaseDate LIMIT 1
        '''
        rows = database.select_record(sql)
        if len(rows) > 0:  # 該筆病歷確實存在
            return init_date

    if ins_judge_init_date != "":
        end_date_script = f' AND CaseDate >= "{ins_judge_init_date}"'
    else:
        end_date_script = ""

    sql = f"""
        SELECT CaseDate FROM cases
        WHERE
            InsType = "健保" AND
            PatientKey = {patient_key}
            {end_date_script}
        ORDER BY CaseDate LIMIT 1
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        init_date = rows[0]["CaseDate"].date()

    return init_date


def get_patient_row(database, patient_key):
    if patient_key is None:
        return None

    sql = f"""
        SELECT * FROM patient
        WHERE
            PatientKey = {patient_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    return rows[0]


def get_card_no(database, patient_id):
    if patient_id is None:
        return None

    sql = f'''
        SELECT CardNo FROM patient
        WHERE
            ID = "{patient_id}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    return string_utils.xstr(rows[0]["CardNo"])


def get_gender_code(gender):
    gender_dict = {"男": "M", "女": "F"}

    try:
        gender_code = gender_dict[gender]
    except KeyError:
        gender_code = "UN"

    return gender_code


def get_marriage_code(marriage):
    if marriage == "已婚":
        marriage_code = "M"
    else:
        marriage_code = "S"

    return marriage_code


def get_zip_code(database, address_str):
    zip_code = "100"
    if address_str == "":
        return ""

    city_list = []
    rows = database.select_record("SELECT City FROM address_list GROUP BY city")
    for row in rows:
        city_list.append(row["City"])

    try:
        addr = class_utils.get_address(address_str)
        city = addr.flat(1)
        district = addr.flat(2)
        district = district.replace(city, "")

        if city == "平鎮":  # 特殊狀況, 有雙關鍵字
            city = "桃園市"
            district = "平鎮區"
        elif addr.tokens[0][addr.UNIT] == "縣" and city not in city_list:
            city = addr.tokens[0][addr.NAME] + "市"
            district = addr.tokens[1][addr.NAME] + "區"
        elif addr.tokens[0][addr.UNIT] == "市" and city not in city_list:
            city = None
            district = addr.tokens[0][addr.NAME]
            rows = database.select_record(f'''
                SELECT City, District FROM address_list
                WHERE
                    District LIKE "{district}%"
            ''')
            if len(rows) > 0:
                district = string_utils.xstr(rows[0]["District"])
                city = string_utils.xstr(rows[0]["City"])

        sql = f'''
            SELECT ZipCode FROM address_list
            WHERE
                City = "{city}" AND
                District = "{district}"
            LIMIT 1
        '''
        rows = database.select_record(sql)

        if len(rows) > 0:
            zip_code = rows[0]["ZipCode"][:3]
    except Exception:
        pass

    return zip_code


def get_patient_id(database, patient_key):
    sql = f"""
        SELECT ID FROM patient
        WHERE
            PatientKey = {patient_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    return string_utils.xstr(rows[0]["ID"])


def get_temp_patient(database, temp_patient_key, field):
    if temp_patient_key is None:
        return None

    sql = f"""
        SELECT * FROM temp_patient
        WHERE
            TempPatientKey = {temp_patient_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    row = rows[0]
    if field == "*":
        return row
    else:
        return row[field]


def get_patient_discount_type(database, patient_key):
    if patient_key in ["", None]:
        return None

    sql = f"""
        SELECT DiscountType FROM patient
        WHERE
            PatientKey = {patient_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    return string_utils.xstr(rows[0]["DiscountType"])


# 讀取初診照護病歷
def read_patient_new_care(database, patient_key, field):
    sql = f'''
        SELECT Value FROM patient_new_care
        WHERE
            PatientKey = {patient_key} AND
            Field = "{field}"
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None
    else:
        return string_utils.xstr(rows[0]["Value"])


# 寫入初診照護病歷
def write_patient_new_care(database, patient_key, field, value):
    fields = [
        "PatientKey",
        "Field",
        "Value",
    ]

    data = [patient_key, field, value]

    database.insert_record("patient_new_care", fields, data)


def get_patient_key(database, case_key):
    sql = f"SELECT PatientKey FROM cases WHERE CaseKey = {case_key}"
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    return rows[0]["PatientKey"]


def get_patient_key_by_id(database, pid):
    sql = f"SELECT PatientKey FROM patient WHERE ID = '{pid}'"
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    return rows[0]["PatientKey"]


def get_patient_extension_settings(database, patient_key, extension_type):
    sql = f'''
        SELECT * FROM patient_extension
        WHERE
            PatientKey = {patient_key} AND
            ExtensionType = "{extension_type}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    row = rows[0]

    return row["Content"]


def set_patient_extension_settings(database, patient_key, extension_type, content):
    sql = f'''
        DELETE FROM patient_extension
        WHERE
            PatientKey = {patient_key} AND
            ExtensionType = "{extension_type}"
    '''
    database.exec_sql(sql)

    fields = [
        "PatientKey",
        "ExtensionType",
        "Content",
    ]

    data = [patient_key, extension_type, content]

    database.insert_record("patient_extension", fields, data)


# 檢查是否為舊病患
def is_old_patient(database, patient_key, first_visit_date):
    sql = f"""
        SELECT CaseDate FROM cases
        WHERE
            PatientKey = '{patient_key}'
        ORDER BY CaseDate DESC LIMIT 1
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return False

    row = rows[0]
    try:
        init_date = string_utils.xstr(row["CaseDate"])[:10]
    except Exception:
        return False

    return True if init_date < first_visit_date else False
