# -*- coding: UTF-8 -*-
# 加強照護醫令的申報次數限制（特定癌症、慢性腎臟病）

import calendar
import datetime

# 每個 tuple 是 (區間類型, 該區間內最多申報次數, 提醒文字)
# 區間為 [start_date, case_date]，start_date 由 case_date 推回
CARE_LIMITS = {
    # 特定癌症
    "P56005": ("month", 12, "每人每月申報上限為 12 次，第 13 次以上不申報"),
    "P56006": ("days60", 1, "限 60 日申報一次，60 天內不可重複申報"),
    "P56007": ("days60", 1, "限 60 日申報一次，60 天內不可重複申報"),
    # 慢性腎臟病 (CKD)
    "P64010": ("week", 3, "每週限申報 3 次，每週第 4 次以上不申報"),
    "P64011": ("days56", 1, "限 56 天(含)以上申報一次，56 天內不可重複申報"),
    "P64012": ("months6", 1, "限每 6 個月申報一次，6 個月內不可重複申報"),
}


def add_months(date, months):
    """date 加減 months 個月，日期超過該月天數時取該月最後一天"""
    month_index = date.year * 12 + (date.month - 1) + months
    year, month = divmod(month_index, 12)
    month += 1
    day = min(date.day, calendar.monthrange(year, month)[1])
    return date.replace(year=year, month=month, day=day)


def get_care_start_date(period, case_date):
    """依限制類型，從就診日推回區間起點 (datetime.date)"""
    if period == "month":
        return case_date.replace(day=1)
    if period == "week":
        # 以週一為一週的第一天 (date.weekday(): 週一=0 … 週日=6)
        return case_date - datetime.timedelta(days=case_date.weekday())
    if period == "days60":
        return case_date - datetime.timedelta(days=59)  # 含當日共 60 天
    if period == "days56":
        return case_date - datetime.timedelta(days=55)  # 含當日共 56 天
    if period == "months6":
        return add_months(case_date, -6) + datetime.timedelta(days=1)

    return case_date


def get_care_dates(database, patient_key, case_key, case_date, treat_code):
    """該病患在限制區間內已申報此照護醫令的就診日期 (排除 case_key 本身)

    case_date 為 datetime.date；回傳 list of datetime，由早到晚
    """
    period, _, _ = CARE_LIMITS[treat_code]
    start_date = get_care_start_date(period, case_date)

    sql = """
        SELECT cases.CaseDate
        FROM prescript
            INNER JOIN cases ON prescript.CaseKey = cases.CaseKey
        WHERE
            cases.PatientKey = %s AND
            cases.CaseKey != %s AND
            cases.CaseDate BETWEEN %s AND %s AND
            prescript.InsCode = %s
        ORDER BY cases.CaseDate
    """
    rows = database.select_record(
        sql,
        (
            patient_key,
            case_key,
            start_date.strftime("%Y-%m-%d 00:00:00"),
            case_date.strftime("%Y-%m-%d 23:59:59"),
            treat_code,
        ),
    )

    return [row["CaseDate"] for row in rows]


def check_care_limit(database, patient_key, case_key, case_date, treat_code):
    """檢查照護醫令是否超過申報限制

    回傳 (is_valid, care_dates)；不在限制清單內的醫令一律 (True, [])
    """
    if treat_code not in CARE_LIMITS:
        return True, []

    _, max_count, _ = CARE_LIMITS[treat_code]
    care_dates = get_care_dates(database, patient_key, case_key, case_date, treat_code)

    return len(care_dates) < max_count, care_dates
