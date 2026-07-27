import calendar
import datetime

import requests

from libs import dialog_utils, number_utils

WEEK_DAY_LIST = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


# 取得年齡
def get_age(birth_date, current_date=datetime.datetime.now()):
    if birth_date is None or current_date is None:
        return None, None

    year = (
        current_date.year
        - birth_date.year
        - ((current_date.month, current_date.day) < (birth_date.month, birth_date.day))
    )

    if current_date.month == birth_date.month:
        if current_date.day >= birth_date.day:  # 生日已滿
            month = 0
        else:
            month = 11
    elif current_date.month < birth_date.month:
        month = 12 - (birth_date.month - current_date.month)
    else:
        month = current_date.month - birth_date.month

    # month = current_date.month - birth_date.month if current_date.month >= birth_date.month \
    #     else 12 - (birth_date.month - current_date.month)

    year = max(year, 0)

    return year, month


# 取得年齡
def get_age_month(birth_date, current_date=datetime.datetime.now()):
    year, month = get_age(birth_date, current_date)

    age_monmth = number_utils.get_integer(year) * 12 + number_utils.get_integer(month)

    return age_monmth


# 取得日期分隔符號
def get_date_separator(in_date):
    separator = ""

    if in_date.find("-") > 0:
        separator = "-"
    elif in_date.find("/") > 0:
        separator = "/"
    elif in_date.find(".") > 0:
        separator = "."

    return separator


# 轉換為民國年
def date_to_zh_tw_date(in_date):
    separator = get_date_separator(in_date)

    try:
        new_date = in_date.split(separator)
    except ValueError:
        return in_date

    try:
        year = int(new_date[0])
    except ValueError:
        return in_date

    if year > 1900:  # 非西元曆
        year -= 1911

    try:
        month = new_date[1]
        day = new_date[2]
        zh_tw_date = f"{year:0>3}{separator}{month:0>2}{separator}{day:0>2}"
    except IndexError:
        return in_date

    return zh_tw_date


# 轉換為西元年
def date_to_west_date(in_date):
    separator = get_date_separator(in_date)
    new_date = in_date.split(separator)

    try:
        year = int(new_date[0])
    except ValueError:
        return in_date

    if year < 1900:  # 非西元曆
        year += 1911

    try:
        month = new_date[1]
        day = new_date[2]
        west_date = f"{year}-{month:0>2}-{day:0>2}"
    except IndexError:
        return in_date

    return west_date


# 健保民國年轉為西元年
def nhi_date_to_west_date(nhi_date):
    if nhi_date is None or nhi_date == "":
        return nhi_date

    try:
        year, month, day = int(nhi_date[:3]), int(nhi_date[3:5]), int(nhi_date[5:7])
    except Exception:
        return nhi_date

    year += 1911

    try:
        west_date = f"{year}-{month:0>2}-{day:0>2}"
    except IndexError:
        return nhi_date

    return west_date


# 健保民國日期時間轉為西元日期時間
def nhi_datetime_to_west_datetime(nhi_datetime):
    if nhi_datetime in [None, ""]:
        return nhi_datetime

    year, month, day = (
        int(nhi_datetime[:3]),
        int(nhi_datetime[3:5]),
        int(nhi_datetime[5:7]),
    )
    hour, minute, second = (
        int(nhi_datetime[7:9]),
        int(nhi_datetime[9:11]),
        int(nhi_datetime[11:13]),
    )
    year += 1911

    try:
        west_datetime = (
            f"{year}-{month:0>2}-{day:0>2} {hour:0>2}:{minute:0>2}:{second:0>2}"
        )
    except IndexError:
        return nhi_datetime

    return west_datetime


# 西元日期時間轉健保日期時間
def west_datetime_to_nhi_datetime(param):
    if param in [None, ""]:
        return param

    if type(param) is str:
        param = datetime.datetime.strptime(param, "%Y-%m-%d %H:%M:%S")

    year = param.year - 1911
    nhi_datetime = f"{year:0>3}{param.month:0>2}{param.day:0>2}{param.hour:0>2}{param.minute:0>2}{param.second:0>2}"

    return nhi_datetime


# 西元日期轉健保日期 YYYY-MM-DD -> YYYMMDD
def west_date_to_nhi_date(in_date, separator="", mask=False):
    if in_date is None:
        return in_date

    if type(in_date) is str:
        in_date = datetime.datetime.strptime(in_date, "%Y-%m-%d")

    year = in_date.year - 1911
    if mask:
        nhi_date = f"{year:0>3}{separator}*{separator}*"
    else:
        nhi_date = (
            f"{year:0>3}{separator}{in_date.month:0>2}{separator}{in_date.day:0>2}"
        )

    return nhi_date


def get_weekday_name(weekday, region="zh_TW"):
    if region == "zh_TW":
        weekday_name = [
            "星期一",
            "星期二",
            "星期三",
            "星期四",
            "星期五",
            "星期六",
            "星期日",
        ]
    else:
        weekday_name = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

    return weekday_name[weekday]


# 取得現在時間
def now_to_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def now_to_nhi_str():
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")


def str_to_date(in_date):
    try:
        date = datetime.datetime.strptime(in_date, "%Y-%m-%d").date()
    except ValueError:
        try:
            date = datetime.datetime.strptime(in_date, "%Y-%m-%d %H:%M").date()
        except ValueError:
            date = datetime.datetime.strptime(in_date, "%Y-%m-%d %H:%M:%S").date()

    return date


def str_to_datetime(in_datetime):
    try:
        date = datetime.datetime.strptime(in_datetime, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        date = None

    return date


# 取得現在日期
def date_to_str():
    return datetime.datetime.now().strftime("%Y-%m-%d")


def get_start_date_by_year_month(year, month):
    start_date = f"{year}-{month}-01 00:00:00"

    return start_date


def get_end_date_by_year_month(year, month):
    last_day = calendar.monthrange(year, month)[1]
    end_date = f"{year}-{month}-{last_day} 23:59:59"

    return end_date


def get_two_month_date(
    database, system_settings, patient_key, apply_year, apply_month, month_range=None
):
    if month_range is None:
        month_range = 2  # 預設維持原本的兩個月

    month = number_utils.get_integer(apply_month)

    # 往前推 month_range - 1 個月 (含申報月本身共 month_range 個月)
    total_months = apply_year * 12 + (month - 1) - (month_range - 1)
    year = total_months // 12
    month = total_months % 12 + 1

    start_date = get_start_date_by_year_month(year, month)  # 區間起始月
    start_date2 = get_end_date_by_year_month(year, month)  # 起始月最後一日

    sql = """
        SELECT CaseKey FROM cases
        WHERE
            InsType = "健保" AND
            CaseDate BETWEEN %s AND %s AND
            PatientKey = %s
    """
    params = (start_date, start_date2, patient_key)
    rows = database.select_record(sql, params=params)  # 檢查區間起始月是否有病歷
    if len(rows) <= 0:  # 如果沒病歷, 找出最後一次的病歷
        ins_judge_init_date = system_settings.field("電子化抽審初診日期")
        if ins_judge_init_date != "":
            end_date_script = f' AND CaseDate >= "{ins_judge_init_date}"'
        else:
            end_date_script = ""

        sql = f"""
            SELECT CaseDate FROM cases
            WHERE
                InsType = "健保" AND
                PatientKey = %s AND
                CaseDate < %s
                {end_date_script}
            ORDER BY CaseDate DESC LIMIT 1
        """
        params = (patient_key, start_date)
        rows = database.select_record(sql, params=params)
        if len(rows) > 0:
            start_date = rows[0]["CaseDate"].strftime("%Y-%m-%d 00:00:00")

    end_date = get_end_date_by_year_month(apply_year, apply_month)
    return start_date, end_date


def add_months(in_date, months):
    month = in_date.month - 1 + months
    year = in_date.year + month // 12
    month = month % 12 + 1
    day = min(in_date.day, calendar.monthrange(year, month)[1])

    return datetime.date(year, month, day)


# def get_week_list(year, month):
#     first_day = datetime.date(int(year), int(month), 1).isocalendar()
#     week_no = first_day[1]

#     week_list = []
#     for i in range(5):  # 總共有5週
#         if week_no > 54:
#             week_no = 1

#         week_date = f'{year}-W{week_no}'
#         first_day = datetime.datetime.strptime(week_date + '-1', '%Y-W%W-%w')

#         first_date = datetime.date(first_day.year, first_day.month, first_day.day) - datetime.timedelta(days=1)

#         last_day = first_day + datetime.timedelta(days=5)
#         last_date = datetime.date(last_day.year, last_day.month, last_day.day)

#         week_list.append([first_date, last_date, week_no])
#         week_no += 1

#     return week_list


def get_week_list(year, month):
    # 取得該月份的第一天和最後一天
    year = int(year)
    month = int(month)
    first_day_of_month = datetime.date(year, month, 1)
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    first_day_next_month = datetime.date(next_year, next_month, 1)
    last_day_of_month = first_day_next_month - datetime.timedelta(days=1)

    # 初始化週列表
    week_list = []
    current_day = first_day_of_month

    while current_day <= last_day_of_month:
        # 找到當前日期的 ISO 週數
        iso_year, iso_week, iso_weekday = current_day.isocalendar()

        # 找到該週的第一天（週一）和最後一天（週日）
        week_start = current_day - datetime.timedelta(days=iso_weekday - 1)
        week_end = week_start + datetime.timedelta(days=6)

        # 如果該週與指定月份有交集，則加入列表
        if week_end >= first_day_of_month and week_start <= last_day_of_month:
            week_list.append([week_start, week_end, iso_week])

        # 跳到下一週
        current_day = week_end + datetime.timedelta(days=1)

    return week_list


def is_birthday_today(birth_date):
    if birth_date is None:
        return False

    birth_month = birth_date.month
    birth_day = birth_date.day
    current_month = datetime.datetime.now().month
    current_day = datetime.datetime.now().day

    return birth_month == current_month and birth_day == current_day


def get_dialog_date(
    parent,
    database,
    system_settings,
    title=None,
    zh_tw=False,
    current_date=None,
    date_type="str",
    call_from=None,
):
    dialog = dialog_utils.get_dialog_calendar(
        parent, database, system_settings, call_from
    )
    if current_date is None:
        current_date = datetime.datetime.today()

    dialog.ui.calendarWidget.setSelectedDate(current_date)
    if title is not None:
        dialog.ui.groupBox_calendar.setTitle(title)

    if not dialog.exec_():
        dialog.deleteLater()
        return None

    selected_date = dialog.ui.calendarWidget.selectedDate()
    if date_type == "str":
        selected_date = selected_date.toString("yyyy/MM/dd")

    if zh_tw:
        selected_date = date_to_zh_tw_date(selected_date)

    if dialog.ui.checkBox_infectious_date.isChecked():
        selected_date = f"確診日期: {selected_date}"
    if dialog.ui.checkBox_injury.isChecked():
        selected_date = f"{selected_date}{dialog.ui.checkBox_injury.text()}"

    dialog.deleteLater()

    return selected_date


def get_time_server_date():
    url = "http://worldtimeapi.org/api/timezone/Asia/Taipei"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        datetime_str = data["datetime"]
        current_datetime = datetime_str[:10]
    except Exception:
        current_datetime = datetime.datetime.today().strftime("%Y-%m-%d")

    return current_datetime


def get_default_date(system_settings):
    today = datetime.datetime.now()
    current_date = today
    if system_settings.field("日期查詢預設為昨日") == "Y":
        current_date = today + datetime.timedelta(days=-1)

    return current_date
