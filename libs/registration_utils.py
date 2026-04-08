# 2018-03-27 掛號作業用

import datetime
import json

from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import date_utils, nhi_utils, number_utils, personnel_utils, string_utils

CANCER_ACUPUNCTURE_TIMES_LIMIT = 10


# 取得班別
def get_current_period(system_settings, current_time=None):
    if current_time is None:
        current_time = datetime.datetime.now().strftime("%H:%M")

    try:
        if current_time >= system_settings.field("晚班時間"):
            period = "晚班"
        elif current_time >= system_settings.field("午班時間"):
            period = "午班"
        else:
            period = "早班"
    except TypeError:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("讀取班別資料失敗")
        msg_box.setText("無法取得系統班別時間, 無法產生班別資料.")
        msg_box.setInformativeText(
            "請檢查[系統設定]->[院所設定]->[班別時間設定]的早午晚班別時間設定."
        )
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()
        return

    return period


# 取得指定診別起始號
def get_designate_room_start_no(system_settings, period, room, doctor):
    start_no_json = system_settings.field(f"指定診別起始號-{room}")

    if start_no_json in ["", None]:
        start_no_json = system_settings.field(f"指定診別起始號-{doctor}")
        if start_no_json in ["", None]:
            return None

    start_no_dict = json.loads(start_no_json)
    try:
        start_no_1 = start_no_dict["早班"]
        start_no_2 = start_no_dict["午班"]
        start_no_3 = start_no_dict["晚班"]
    except Exception:
        return None

    result = {
        "早班": number_utils.get_integer(start_no_1),
        "午班": number_utils.get_integer(start_no_2),
        "晚班": number_utils.get_integer(start_no_3),
    }

    return result[period]


# 取得今日最後的診號
def get_last_reg_no(
    database, system_settings, start_date, end_date, period, room, doctor
):
    max_regist_no = system_settings.field("診號累加器最大號")
    reg_no_mode = system_settings.field("現場掛號給號模式")

    if (
        max_regist_no not in ["", None]
        and max_regist_no.isdigit()
        and int(max_regist_no) > 0
    ):
        max_regist_no_condition = f" And RegistNo <= {max_regist_no}"
    else:
        max_regist_no_condition = ""

    sql = f'''
        SELECT RegistNo, RegistType FROM cases
        WHERE
            CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
            RegistNo > 0 AND
            Position1 IS NULL
            {max_regist_no_condition}
    '''
    # 健保民俗調理不能算診號

    if system_settings.field("分診") == "Y":
        sql += f" AND Room = {room}"

    if system_settings.field("分班") == "Y":
        sql += f' AND Period = "{period}"'

    rows = database.select_record(sql)

    last_reg_no_rows = []
    reg_no_rows = []  # 使用者可能會把預約報到病人的預約診號手動改成現場的診號
    for row in rows:
        reg_no_rows.append(row["RegistNo"])

        # 一定要讀現場號，否則預約報到後，現場號會變成預約號之後, 早成中間許多現場號空號
        if (
            reg_no_mode in ["單號", "雙號", "預約班表", "連續號"]
            and row["RegistType"] != "預約門診"
        ):
            last_reg_no_rows.append(row["RegistNo"])

    if len(last_reg_no_rows) > 0:
        last_reg_no = last_reg_no_rows[-1]
    else:
        if system_settings.field("分班") == "Y":
            if system_settings.field("分診") == "Y":
                reg_no = get_designate_room_start_no(
                    system_settings, period, room, doctor
                )
                if reg_no is None:
                    reg_no = system_settings.field(f"{period}起始號")
            else:
                reg_no = system_settings.field(f"{period}起始號")
        else:
            reg_no = system_settings.field("早班起始號")

        try:
            last_reg_no = int(reg_no) - 1
        except TypeError:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("讀取診號起始號資料失敗")
            msg_box.setText("無法取得班別起始號資料, 無法產生診號.")
            msg_box.setInformativeText(
                "請檢查[系統設定]->[診號控制]->[給號方式]的早午晚班起始號設定."
            )
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return 0

    if last_reg_no is None:
        last_reg_no = 0

    return reg_no_rows, number_utils.get_integer(last_reg_no)


# 取得今日最後的診號
def get_odd_seqauence(
    database, system_settings, start_date, end_date, period, room, doctor
):
    sql = f'''
        SELECT RegistNo, RegistType FROM cases
        WHERE
            CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
            RegistNo > 0 AND
            Position1 IS NULL
    '''
    # 健保民俗調理不能算診號

    if system_settings.field("分診") == "Y":
        sql += f" AND Room = {room}"

    if system_settings.field("分班") == "Y":
        sql += f' AND Period = "{period}"'

    sql += " ORDER BY RegistNo DESC LIMIT 1"
    rows = database.select_record(sql)

    if len(rows) <= 0:
        reg_no = 0
    else:
        reg_no = number_utils.get_integer(rows[0]["RegistNo"])

    if reg_no % 2 == 0:
        reg_no += 1
    else:
        reg_no += 2

    return reg_no


def get_reg_no_on_site(database, system_settings, doctor, period):
    start_date = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
    end_date = datetime.datetime.now().strftime("%Y-%m-%d 23:59:59")
    start_no = number_utils.get_integer(system_settings.field(f"{period}起始號"))
    site_no_mode = system_settings.field("現場掛號給號模式")

    sql = f'''
        SELECT RegistNo FROM cases
        WHERE
            CaseDate BETWEEN "{start_date}" AND "{end_date}"
    '''

    if system_settings.field("分班") == "Y":
        sql += f' AND Period = "{period}"'

    if system_settings.field("分診") == "Y":
        sql += f' AND Doctor = "{doctor}"'

    sql += "ORDER BY RegistNo DESC LIMIT 1"

    rows = database.select_record(sql)
    if len(rows) <= 0:
        regist_no = start_no
        # if regist_no % 2 == 1:
        #     regist_no += 1
    else:
        last_reg_no = rows[0]["RegistNo"]
        if site_no_mode == "連續號":
            regist_no = last_reg_no + 1
        elif site_no_mode == "單號":
            if last_reg_no % 2 == 1:
                regist_no = last_reg_no + 2
            else:
                regist_no = last_reg_no + 1
        elif site_no_mode == "雙號":
            if last_reg_no % 2 == 1:
                regist_no = last_reg_no + 1
            else:
                regist_no = last_reg_no + 2
        else:
            regist_no += 1

    return regist_no


def get_reg_no_by_even_sequence(database, system_settings, doctor, period):
    start_date = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
    end_date = datetime.datetime.now().strftime("%Y-%m-%d 23:59:59")
    start_no = number_utils.get_integer(system_settings.field(f"{period}起始號"))

    sql = f'''
        SELECT MAX(RegistNo) AS MaxRegistNo FROM cases
        WHERE
            CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
            MOD(RegistNo, 2) = 0
    '''

    if system_settings.field("分班") == "Y":
        sql += f' AND Period = "{period}"'

    if system_settings.field("分診") == "Y":
        sql += f' AND Doctor = "{doctor}"'

    sql += "ORDER BY RegistNo"

    rows = database.select_record(sql)
    if len(rows) <= 0:
        regist_no = start_no + 1
    else:
        row = rows[0]
        regist_no = number_utils.get_integer(row["MaxRegistNo"]) + 2

    return regist_no


def get_max_regist_no(database, system_settings, doctor, period):
    start_no = number_utils.get_integer(system_settings.field(f"{period}起始號"))

    sql = """
        SELECT MAX(RegistNo) AS MaxRegistNo FROM wait
        WHERE
            DoctorDone = "False"
    """
    if system_settings.field("分班") == "Y":
        sql += f' AND Period = "{period}"'

    if system_settings.field("分診") == "Y":
        sql += f' AND Doctor = "{doctor}"'

    rows = database.select_record(sql)
    if rows:
        max_regist_no = number_utils.get_integer(rows[0]["MaxRegistNo"])
    else:
        max_regist_no = start_no

    return max_regist_no


def get_next_number(numbers):
    if not numbers:
        return 1  # 空清單就從 1 開始

    numbers = sorted(numbers)

    # 找出中間的缺口
    for i in range(len(numbers) - 1):
        if numbers[i + 1] - numbers[i] > 1:
            return numbers[i] + 1

    # 沒有缺口就取最後一個 +1
    return numbers[-1] + 1


# 取得雙號順序遞補現場號
def get_reg_no_by_even_sequence_fill_reg_no(database, system_settings, doctor, period):
    sql = """
        SELECT RegistNo FROM wait
        WHERE
            DoctorDone = "False"
    """

    if system_settings.field("分班") == "Y":
        sql += f' AND Period = "{period}"'

    if system_settings.field("分診") == "Y":
        sql += f' AND Doctor = "{doctor}"'

    sql += "ORDER BY RegistNo"

    rows = database.select_record(sql)
    if len(rows) > 0:
        regist_no_list = []
        for row in rows:
            regist_no_list.append(row["RegistNo"])

        regist_no = get_next_number(regist_no_list)
        return regist_no

    sql = """
        SELECT RegistNo FROM wait
        WHERE
            DoctorDone = "True"
    """

    if system_settings.field("分班") == "Y":
        sql += f' AND Period = "{period}"'

    if system_settings.field("分診") == "Y":
        sql += f' AND Doctor = "{doctor}"'

    sql += "ORDER BY RegistNo DESC LIMIT 1"
    rows = database.select_record(sql)
    if not rows:
        return 1

    row = rows[0]
    regist_no = number_utils.get_integer(row["RegistNo"]) + 1
    return regist_no


def get_reg_no_by_sequence(database, system_settings, doctor, period):
    start_date = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
    end_date = datetime.datetime.now().strftime("%Y-%m-%d 23:59:59")
    start_no = number_utils.get_integer(system_settings.field(f"{period}起始號"))

    sql = f'''
        SELECT MAX(RegistNo) AS MaxRegistNo FROM cases
        WHERE
            CaseDate BETWEEN "{start_date}" AND "{end_date}"
    '''

    if system_settings.field("分班") == "Y":
        sql += f' AND Period = "{period}"'

    if system_settings.field("分診") == "Y":
        sql += f' AND Doctor = "{doctor}"'

    sql += "ORDER BY RegistNo"

    rows = database.select_record(sql)
    if len(rows) <= 0:
        regist_no = start_no
    else:
        row = rows[0]
        regist_no = number_utils.get_integer(row["MaxRegistNo"]) + 1

    return regist_no


# 取得診號
def get_reg_no(database, system_settings, room, doctor, period=None, reserve_key=None):
    if reserve_key is not None:
        reserve_no_mode = system_settings.field("預約報到給號模式")
        if reserve_no_mode == "零號":
            return 0
        elif reserve_no_mode == "根據現場設定":
            reg_no = get_reg_no_on_site(database, system_settings, doctor, period)
            return reg_no
        elif reserve_no_mode == "雙號順序":
            if system_settings.field("優先遞補現場號") == "Y":
                reg_no = get_reg_no_by_even_sequence_fill_reg_no(
                    database, system_settings, doctor, period
                )
            else:
                reg_no = get_reg_no_by_even_sequence(
                    database, system_settings, doctor, period
                )

            return reg_no
        elif reserve_no_mode == "就醫順序":
            reg_no = get_reg_no_by_sequence(database, system_settings, doctor, period)
            return reg_no

        sql = f"""
            SELECT ReserveNo FROM reserve
            WHERE
                ReserveKey = {reserve_key}
        """
        rows = database.select_record(sql)

        if len(rows) > 0:
            return number_utils.get_integer(rows[0]["ReserveNo"])

    start_date = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
    end_date = datetime.datetime.now().strftime("%Y-%m-%d 23:59:59")
    if period is None:
        period = get_current_period(system_settings)

    if system_settings.field("現場掛號給號模式") == "就醫順序":
        reg_no = get_reg_no_by_sequence(database, system_settings, doctor, period)
        return reg_no
    elif system_settings.field("現場掛號給號模式") == "單號順序":
        reg_no = get_odd_seqauence(
            database,
            system_settings,
            start_date,
            end_date,
            period,
            room,
            doctor,
        )
        return int(reg_no)

    reg_no_rows, last_reg_no = get_last_reg_no(
        database,
        system_settings,
        start_date,
        end_date,
        period,
        room,
        doctor,
    )
    reg_no = get_reg_no_by_mode(
        database, system_settings, period, room, doctor, last_reg_no
    )

    while True:
        if reg_no not in reg_no_rows:
            break

        if system_settings.field("現場掛號給號模式") == "連續號":
            last_reg_no += 1
        else:
            last_reg_no += 2

        reg_no = get_reg_no_by_mode(
            database, system_settings, period, room, doctor, last_reg_no
        )

    return int(reg_no)


def is_reg_no_exists(
    database, start_date, end_date, period, room, reg_no, patient_key=None
):
    is_exists = False

    patient_condition = ""
    if patient_key is not None:
        patient_condition = f"AND PatientKey != {patient_key}"

    if room is None:
        room = 1

    sql = f'''
        SELECT RegistNo FROM cases
        WHERE
            CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
            Period = "{period}" AND
            Room = {room} AND
            RegistNo = {reg_no}
            {patient_condition}
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        is_exists = True

    return is_exists


def is_reg_number_exists(
    database, start_date, end_date, period, room, reg_no, patient_key=None
):
    is_exists = False

    patient_condition = ""
    if patient_key is not None:
        patient_condition = f"AND PatientKey != {patient_key}"

    if room is None:
        room = 1

    sql = f'''
        SELECT RegistNo FROM cases
        WHERE
            CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
            Period = "{period}" AND
            Room = {room} AND
            RegistNo = {reg_no}
            {patient_condition}
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        is_exists = True

    return is_exists


# 診號模式
def get_reg_no_by_mode(database, system_settings, period, room, doctor, reg_no):
    if reg_no is None:
        reg_no = 0

    if system_settings.field("現場掛號給號模式") == "雙號":
        if reg_no % 2 == 1:
            reg_no += 1
        else:
            reg_no += 2
    elif system_settings.field("現場掛號給號模式") == "單號":
        if number_utils.get_integer(reg_no) % 2 == 0:
            reg_no += 1
        else:
            reg_no += 2
    elif system_settings.field("現場掛號給號模式") == "預約班表":
        period_condition = ""
        doctor_condition = ""
        if period is not None:
            period_condition = f'AND Period = "{period}"'
        if doctor is not None:
            doctor_condition = f'AND Doctor = "{doctor}"'

        reg_no += 1
        sql = f"""
            SELECT * FROM reservation_table
            WHERE
                ReserveNo >= {reg_no}
                {period_condition}
                {doctor_condition}
            ORDER BY ReserveNo
        """
        rows = database.select_record(sql)

        for row in rows:
            if reg_no != row["ReserveNo"]:
                break

            if system_settings.field("釋出預約號") == "Y":
                if check_release_reserve_no(
                    database, room, period, doctor, reg_no
                ):  # 可以釋出預約號, 不再繼續往下檢查
                    break

            reg_no += 1
    elif system_settings.field("現場掛號給號模式") == "連續號":
        period_condition = ""
        doctor_condition = ""
        if system_settings.field("分班") == "Y" and period is not None:
            period_condition = f'AND Period = "{period}"'
        if system_settings.field("分診") == "Y" and doctor is not None:
            doctor_condition = f'AND Doctor = "{doctor}"'

        reg_no += 1
        start_date = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
        end_date = datetime.datetime.now().strftime("%Y-%m-%d 23:59:59")
        sql = f'''
            SELECT ReserveNo FROM reserve
            WHERE
                ReserveDate BETWEEN "{start_date}" AND "{end_date}" AND
                ReserveNo >= {reg_no}
                {period_condition}
                {doctor_condition}
            ORDER BY ReserveNo
        '''
        rows = database.select_record(sql)

        for row in rows:
            if reg_no != number_utils.get_integer(row["ReserveNo"]):
                break

            reg_no += 1
    else:
        reg_no += 1

    return reg_no


# 2019.03.12 檢查是否可以釋出預約號碼 (只檢查今日，其他日期不可佔用)
def check_release_reserve_no(database, room, period, doctor, reg_no):
    release_reserve_no = False

    start_date = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
    end_date = datetime.datetime.now().strftime("%Y-%m-%d 23:59:59")

    sql = f'''
        SELECT * FROM reserve
        WHERE
            ReserveDate BETWEEN "{start_date}" AND "{end_date}" AND
            Period = "{period}" AND
            Doctor = "{doctor}" AND
            ReserveNo = {reg_no}
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:  # 無人佔用, 可以釋出
        release_reserve_no = True

    return release_reserve_no


# 檢查健保重複就診
def check_record_duplicated(database, patient_key, case_date):
    start_date = case_date.strftime("%Y-%m-%d 00:00:00")
    end_date = case_date.strftime("%Y-%m-%d 23:59:59")
    sql = f'''
        SELECT * FROM cases
        WHERE
            PatientKey = {patient_key} AND
            CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
            InsType = "健保"
    '''
    rows = database.select_record(sql)

    if len(rows) > 0:
        return True
    else:
        return False


# 取得當月健保針傷門診就診次數
def get_treat_times(database, patient_key):
    start_date = datetime.datetime.now().strftime("%Y-%m-01 00:00:00")
    end_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
        "%Y-%m-%d 23:59:59"
    )
    ins_treat_list = tuple(nhi_utils.INS_TREAT)

    sql = f'''
        SELECT CaseKey from cases
        WHERE
            (PatientKey = {patient_key}) AND
            (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
            (InsType = "健保") AND
            (cases.Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
            (cases.TreatType NOT IN ("居家醫療")) AND
            (cases.Share NOT IN ("山地離島")) AND
            (Continuance between 1 AND 6) AND
            (TreatType in {ins_treat_list})
    '''
    rows = database.select_record(sql)

    return len(rows)


# 檢查當月健保針傷門診就診次數
def check_treat_times(database, system_settings, patient_key):
    message = None
    treat_times = get_treat_times(database, patient_key)
    treat_times_limit = number_utils.get_integer(system_settings.field("針傷警告次數"))
    if treat_times >= treat_times_limit:
        message = f"* 針傷次數警告: 本月針傷次數共{treat_times}次, 已達系統設定{treat_times_limit}次的限制.<br>"

    return message


# 取得當月健保有診察費就診次數
def get_diag_fee_times(database, patient_key):
    start_date = datetime.datetime.now().strftime("%Y-%m-01 00:00:00")
    end_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
        "%Y-%m-%d 23:59:59"
    )

    sql = f'''
        SELECT CaseKey from cases
        WHERE
            (PatientKey = {patient_key}) AND
            (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
            (InsType = "健保") AND
            ((Continuance IS NULL) OR (Continuance <= 1)) AND
            (DiagFee > 0)
    '''
    rows = database.select_record(sql)

    return len(rows)


# 檢查當月健保有診察費就診次數
def check_diag_fee_times(database, system_settings, patient_key):
    message = None
    diag_fee_times = get_diag_fee_times(database, patient_key)
    diag_fee_times_limit = number_utils.get_integer(
        system_settings.field("首次警告次數")
    )
    if diag_fee_times >= diag_fee_times_limit:
        message = f"* 診察次數警告: 本月診察次數共{diag_fee_times}次, 已達系統設定{diag_fee_times_limit}次的限制.<br>"

    return message


# 檢查欠卡
def check_deposit(database, system_settings, patient_key):
    message = None
    present = datetime.datetime.now()
    if system_settings.field("欠卡日期檢查範圍") == "10天前":
        start_date = (present - datetime.timedelta(days=9)).strftime(
            "%Y-%m-%d 00:00:00"
        )  # 10天內未還卡
    elif system_settings.field("欠卡日期檢查範圍") == "本月1日":
        start_date = datetime.date(present.year, present.month, 1).strftime(
            "%Y-%m-%d 00:00:00"
        )  # 本月1日
    elif system_settings.field("欠卡日期檢查範圍") == "上個月20日":
        start_date = datetime.date(present.year, present.month, 1) - datetime.timedelta(
            10
        )  # 至上個月20日
        start_date = start_date.strftime("%Y-%m-%d 00:00:00")
    else:
        start_date = datetime.date(present.year, present.month, 1) - datetime.timedelta(
            1
        )  # 至上個月1日
        start_date = start_date.strftime("%Y-%m-01 00:00:00")

    end_date = (present - datetime.timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")
    sql = f'''
        SELECT CaseDate, Name FROM cases
        WHERE
            (PatientKey = {patient_key}) AND
            (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
            (InsType = "健保") AND
            (Card = "欠卡")
    '''
    rows = database.select_record(sql)

    if len(rows) > 0:
        row = rows[0]
        year = row["CaseDate"].year
        month = row["CaseDate"].month
        day = row["CaseDate"].day
        message = f"* 欠卡提醒: {year}年{month}月{day}日門診尚有欠卡未還."
    else:
        row = None

    return message, row


# 檢查欠款
def check_debt(database, patient_key):
    message = None

    sql = f"""
        SELECT * FROM debt
        WHERE
            PatientKey = {patient_key} AND
            (ReturnDate1 IS NULL OR
            Fee1 + Fee2 + Fee3 < Fee)
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        message = ""
        for row in rows:
            case_date = row["CaseDate"].strftime("%Y-%m-%d")
            debt_type = string_utils.xstr(row["DebtType"])
            debt = number_utils.get_integer(row["Fee"])
            return_fee = number_utils.get_integer(row["Fee1"])
            arrears = debt - return_fee

            message += (
                f"* 欠款提醒: {case_date} 門診尚有{debt_type} {arrears} 未還.<br>"
            )

    return message


# 檢查昨日內科或新療程刷卡
def check_card_yesterday(database, patient_key, course=None):
    message = None

    if number_utils.get_integer(course) >= 1:  # 療程無隔日過卡問題, 不檢查
        return message

    start_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
        "%Y-%m-%d 00:00:00"
    )
    end_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
        "%Y-%m-%d 23:59:59"
    )
    sql = f'''
        SELECT CaseKey FROM cases
        WHERE
            (PatientKey = {patient_key}) AND
            (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
            (InsType = "健保") AND
            ((Continuance IS NULL) OR (Continuance <= 0)) AND
            (TreatType NOT IN {tuple(nhi_utils.CARE_TREAT)})
    '''
    rows = database.select_record(sql)

    if len(rows) > 0:
        message = "* 隔日過卡提醒: 昨日有內科或療程首次門診.<br>"

    return message


# 檢查上次給藥是否用完
def check_prescription_finished(
    database, system_settings, case_key, patient_key, in_date=None, manual_message=False
):
    message = None

    if in_date is None:
        in_date = datetime.date.today()
    else:
        in_date = in_date.date()

    if case_key in [None, ""]:
        case_condition = ""
    else:
        case_condition = f"(cases.CaseKey != {case_key}) AND "

    end_date = (in_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")
    sql = f'''
        SELECT cases.CaseDate, cases.Name, dosage.Days FROM cases
            LEFT JOIN dosage on dosage.CaseKey = cases.CaseKey
        WHERE
            {case_condition}
            (cases.PatientKey = {patient_key}) AND
            (cases.CaseDate <= "{end_date}") AND
            (cases.InsType = "健保") AND
            (dosage.MedicineSet = 1) AND (dosage.Days > 0)
        ORDER BY CaseDate DESC LIMIT 1
    '''
    rows = database.select_record(sql)

    remain_days = 0

    if len(rows) > 0:
        row = rows[0]
        prescription_days = number_utils.get_integer(row["Days"])
        last_prescription_date = row["CaseDate"].date()
        days = (in_date - last_prescription_date).days + 1  # 已服用天數, 開藥當日算一日

        if system_settings.field("當日用藥重複檢查次日起算") == "Y":  # 給藥次日開始算起
            days -= 1

        remain_days = prescription_days - days  # 剩餘藥日
        if remain_days > 0:  # 藥還有剩
            name = string_utils.xstr(row["Name"])
            case_date = rows[0]["CaseDate"].strftime("%Y-%m-%d")
            message = f"""
                * 用藥檢查:<br>
                {name}在{case_date}開了{prescription_days}日藥,<br>
                至{in_date.strftime("%Y-%m-%d")}為止尚有{remain_days}日藥未服用完畢.
            """
            if (
                remain_days >= 2
                and system_settings.field("用藥重複二日不能存檔") == "Y"
            ):
                message += "<br>用藥重複>=2日, 無法存檔"

    if manual_message:
        if remain_days > 0:  # 藥還有剩
            return (
                case_date,
                in_date.strftime("%Y-%m-%d"),
                prescription_days,
                remain_days,
            )
        else:
            return None, None, None, None
    else:
        return message


# 檢查上次給藥是否用完
def check_course_medicine_two_times(
    database, system_settings, patient_key, card, course
):
    message = None

    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=30)).strftime("%Y-%m-%d 00:00:00")
    yesterday = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")

    sql = f'''
        SELECT cases.CaseDate, cases.Continuance, dosage.Days FROM cases
            LEFT JOIN dosage on dosage.CaseKey = cases.CaseKey
        WHERE
            CaseDate BETWEEN "{start_date}" AND "{yesterday}" AND
            PatientKey = {patient_key} AND
            Card = "{card}" AND
            Continuance >= 1 AND
            Continuance < {course} AND
            dosage.Days > 0
        ORDER BY CaseDate
    '''
    rows = database.select_record(sql)

    if len(rows) >= 2:
        message = """
            <html>
            療程開藥兩次(含)以上，開藥明細如下:<br>
            <table align=center cellpadding="2" cellspacing="0" width="98%"
             style="border-width: 1px; border-style: solid;">
                <thead>
                    <tr bgcolor="lightgray">
                        <th align=center>門診日期</th>
                        <th align=center>卡序</th>
                        <th align=center>給藥天數</th>
                    </tr>
                </thead>
                <tbody>
        """
        for row in rows:
            case_date_str = row["CaseDate"].strftime("%Y-%m-%d")
            course = number_utils.get_integer(row["Continuance"])
            pres_days = number_utils.get_integer(row["Days"])
            message += f"""
                <tr>
                    <td align=center>{case_date_str}</td>
                    <td align=center>{card}-{course}</td>
                    <td align=center>{pres_days}</td>
                </tr>
            """

        message += "</tbody></table></html>"

    return message


# 療程未完成
def check_course_complete(database, patient_key, course):
    if number_utils.get_integer(course) >= 2:  # 療程無問題, 不檢查
        return None

    start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime(
        "%Y-%m-%d 00:00:00"
    )
    end_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
        "%Y-%m-%d 23:59:59"
    )
    sql = f'''
        SELECT CaseDate, Card, Continuance FROM cases
        WHERE
            (PatientKey = {patient_key}) AND
            (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
            (InsType = "健保") AND
            (Continuance >= 1)
        ORDER BY CaseDate DESC LIMIT 1
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:  # 療程超過30天
        return None

    row = rows[0]
    card = string_utils.xstr(row["Card"])
    course = number_utils.get_integer(row["Continuance"])

    if course >= 6:  # 療程已經完成
        return None

    message = check_course_complete_in_days(
        database, patient_key, card, course, 30, save_check=True
    )  # 療程還沒有超過30天
    if message is None:
        return None
    else:
        case_date = row["CaseDate"].date()
        message = f"* 療程提醒: {case_date}到今天尚未超過30日只到療程{course}, 尚未完成全部療程.<br>"

    return message


# 同療程days日未完成
def check_course_complete_in_days(
    database, patient_key, card, course, days, save_check=False
):
    course = number_utils.get_integer(course)
    if course <= 0:  # 療程首次或內科不檢查
        return None

    start_date = (datetime.datetime.now() - datetime.timedelta(days=days - 1)).strftime(
        "%Y-%m-%d 00:00:00"
    )
    end_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
        "%Y-%m-%d 23:59:59"
    )
    sql = f'''
        SELECT Continuance FROM cases
        WHERE
            (PatientKey = {patient_key}) AND
            (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
            (InsType = "健保") AND
            (Card = "{card}") AND
            (Continuance = 1)
        ORDER BY CaseDate DESC LIMIT 1
    '''
    rows = database.select_record(sql)
    if save_check:
        if len(rows) > 0:
            return "療程尚未完成另開新卡序"
        else:
            return None

    message = None
    if (
        len(rows) <= 0
    ):  # 找不到代表療程已經不在天數內，已過期 例如: 30天內有找到第一次, 代表療程第一次到現在還沒超過30天 (欠卡例外, 卡序為欠卡可能第一次有取得卡序)
        message = f"* 療程提醒: 療程已超過{days}日, 尚未完成全部療程.<br>"

        if card == "欠卡":  # 2024-08-25 德林提醒
            sql = f'''
                SELECT Card FROM cases
                WHERE
                    (PatientKey = {patient_key}) AND
                    (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
                    (InsType = "健保") AND
                    (Continuance = 1)
                ORDER BY CaseDate DESC LIMIT 1
            '''
            rows = database.select_record(sql)
            if len(rows) > 0:
                first_card = string_utils.xstr(rows[0]["Card"])
                sql = f'''
                    SELECT Continuance FROM cases
                    WHERE
                        (PatientKey = {patient_key}) AND
                        (Card = "{first_card}") AND
                        (Continuance = 6)
                    ORDER BY CaseDate DESC LIMIT 1
                '''
                rows = database.select_record(sql)
                if len(rows) <= 0:  # 要確定第一次的欠卡沒有做滿6次
                    message = None

    return message


# 取得診別
def get_room(database, period, doctor, weekday=None):
    default_room = personnel_utils.get_person_field_value(database, doctor, "Room")
    if default_room in ["", None]:
        default_room = 1

    today = datetime.datetime.now().weekday()
    if weekday is None:
        weekday = date_utils.WEEK_DAY_LIST[today]

    sql = f'''
        SELECT * FROM doctor_schedule
        WHERE
            Period = "{period}" AND
            {weekday} = "{doctor}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        case_date = datetime.datetime.now().strftime("%Y-%m-%d")
        sql = f'''
            SELECT Room FROM temporary_schedule
            WHERE
                CaseDate = "{case_date}" AND
                Period = "{period}" AND
                Position = "醫師" AND
                Name = "{doctor}"
        '''
        rows = database.select_record(sql)
        if len(rows) <= 0:
            return default_room
        else:
            return rows[0]["Room"]

    room = rows[0]["Room"]

    return room


# Monday=0, Tuesday=1...Sunday=6
def get_schedule_doctor(database, room, period, reservation_date=None):
    if reservation_date is None:
        reservation_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if room is None:
        room = 1

    sql = f'''
        SELECT Name FROM temporary_schedule
        WHERE
            DATE(CaseDate) = "{reservation_date}" AND
            Period = "{period}" AND
            Position = "醫師" AND
            Room = {room} AND
            ScheduleType IN ("代班", "加診")
    '''
    rows = database.select_record(sql)
    if len(rows) >= 1:
        return string_utils.xstr(rows[0]["Name"])

    sql = f'''
        SELECT * FROM doctor_schedule
        WHERE
            Room = {room} AND
            Period = "{period}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        sql = f'''
            SELECT Name FROM temporary_schedule
            WHERE
                CaseDate = "{reservation_date}" AND
                Period = "{period}" AND
                Position = "醫師" AND
                Room = {room}
        '''
        rows = database.select_record(sql)
        if len(rows) <= 0:
            return None
        else:
            return string_utils.xstr(rows[0]["Name"])

    row = rows[0]
    doctor_list = [
        string_utils.xstr(row["Monday"]),
        string_utils.xstr(row["Tuesday"]),
        string_utils.xstr(row["Wednesday"]),
        string_utils.xstr(row["Thursday"]),
        string_utils.xstr(row["Friday"]),
        string_utils.xstr(row["Saturday"]),
        string_utils.xstr(row["Sunday"]),
    ]

    today = datetime.datetime.now().weekday()

    return doctor_list[today]


# Monday=0, Tuesday=1...Sunday=6
def get_schedule_doctor_by_date_period(database, weekday_name, period):
    doctor_list = []

    sql = f'''
        SELECT {weekday_name} FROM doctor_schedule
        WHERE
            Period = "{period}" AND
            {weekday_name} IS NOT NULL AND
            LENGTH({weekday_name}) > 0
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return doctor_list

    for row in rows:
        doctor_list.append(string_utils.xstr(row[weekday_name]))

    return doctor_list


def get_temporary_in_duty_doctor(database, schedule_date, period):
    sql = f'''
        SELECT Name FROM temporary_schedule
        WHERE
            CaseDate = "{schedule_date}" AND
            Period = "{period}" AND
            ScheduleType = "代班"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    row = rows[0]
    in_duty_doctor = string_utils.xstr(row["Name"])

    return in_duty_doctor


def get_temporary_agent_doctor(database, schedule_date, period, current_doctor):
    sql = f'''
        SELECT Agent FROM temporary_schedule
        WHERE
            CaseDate = "{schedule_date}" AND
            Period = "{period}" AND
            Name = "{current_doctor}" AND
            ScheduleType = "代班"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    row = rows[0]
    agen_doctor = string_utils.xstr(row["Agent"])

    return agen_doctor


def get_temporary_doctor_schedule(database, case_date, schedule_type, period):
    if schedule_type in ["加診", "代班", "代班或加診"]:
        schedule_type_condition = ' ScheduleType IN ("加診", "代班")'
    elif schedule_type == "請假":
        schedule_type_condition = ' ScheduleType IN ("請假", "代班")'
    else:
        schedule_type_condition = f' ScheduleType = "{schedule_type}"'

    sql = f'''
        SELECT ScheduleType, Name, Agent FROM temporary_schedule
        WHERE
            DATE(CaseDate) = "{case_date}" AND
            Period = "{period}" AND
            Position = "醫師" AND
            {schedule_type_condition}
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    doctor_list = []
    for row in rows:
        if schedule_type in ["請假", "代班或加診", "加診"]:
            if (
                string_utils.xstr(row["ScheduleType"]) == "代班"
                and string_utils.xstr(row["Agent"]) != ""
            ):
                if schedule_type == "請假":
                    doctor_list.append(
                        string_utils.xstr(row["Name"])
                    )  # 代班有輸入代班醫師，主治醫師也算請假
                else:
                    doctor_list.append(string_utils.xstr(row["Agent"]))
            else:
                doctor_list.append(string_utils.xstr(row["Name"]))
        else:
            doctor_list.append(string_utils.xstr(row["Agent"]))

    return doctor_list


def set_temporary_doctor_schedule(
    database, period, in_duty_doctor_list, case_date=None
):
    if case_date is None:
        case_date = datetime.datetime.now().strftime("%Y-%m-%d")

    temporary_doctor_list = get_temporary_doctor_schedule(
        database, case_date, "代班或加診", period
    )

    if temporary_doctor_list is not None:
        for doctor in temporary_doctor_list:
            if doctor not in in_duty_doctor_list:
                in_duty_doctor_list.append(doctor)

    temporary_doctor_list = get_temporary_doctor_schedule(
        database, case_date, "請假", period
    )

    if temporary_doctor_list is not None:
        for doctor in temporary_doctor_list:
            if doctor in in_duty_doctor_list:
                in_duty_doctor_list.remove(doctor)


# 檢查預約是否已滿
def is_reservation_full(database, reservation_date, period, reserve_no, doctor):
    is_full = False

    reservation_date = reservation_date.split(" ")[0]
    start_date = f"{reservation_date} 00:00:00"
    end_date = f"{reservation_date} 23:59:59"

    sql = f'''
        SELECT ReserveKey FROM reserve
        WHERE
            ReserveDate BETWEEN "{start_date}" AND "{end_date}" AND
            Period = "{period}" AND
            ReserveNo = {reserve_no} AND
            Doctor = "{doctor}"
    '''
    rows = database.select_record(sql)

    if len(rows) > 0:
        is_full = True

    return is_full


def get_electric_drug_no(database, system_settings, case_date, case_key):
    drug_no = 1

    sql = f"""
        SELECT Room, RegistNo FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return drug_no

    row = rows[0]
    room = row["Room"]
    regist_no = row["RegistNo"]

    drug_no = f"{room:0>2}{regist_no:0>3}"

    return drug_no


def get_last_treat_type(database, patient_key):
    sql = f"""
        SELECT TreatType FROM cases
        WHERE
            PatientKey = {patient_key} AND
            InsType = "健保"
        ORDER BY CaseDate DESC LIMIT 1
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    row = rows[0]
    return string_utils.xstr(row["TreatType"])


def is_reservation_table_hide(database, weekday, period, doctor, reserve_no):
    sql = f'''
        SELECT ReservationTableHideKey FROM reservation_table_hide
        WHERE
            Weekday = "{weekday}" AND
            Period = "{period}" AND
            Doctor = "{doctor}" AND
            ReserveNo = "{reserve_no}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return False
    else:
        return True


# 是否在權限清單內
def is_in_permission_list(database, patient_key, permission_type, reservation_date):
    in_permission_list = False
    sql = f'''
        SELECT * FROM permission_list
        WHERE
            PermissionType = "{permission_type}" AND
            PatientKey = {patient_key} AND
            StartDate <= "{reservation_date}" AND
            EndDate >= "{reservation_date}"
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        in_permission_list = True

    return in_permission_list


# 是否在預約名單內
def is_in_reservation_list(database, patient_key, reservation_date):
    ins_reservation_list = False

    sql = f'''
        SELECT ReserveKey FROM reserve
        WHERE
            PatientKey = {patient_key} AND
            DATE(ReserveDate) = "{reservation_date}"
        LIMIT 1
    '''

    rows = database.select_record(sql)
    if len(rows) > 0:
        ins_reservation_list = True

    return ins_reservation_list


def get_hosp_name(database, hosp_id):
    sql = f'''
        SELECT HospName FROM hospid
        WHERE
            HospID = "{hosp_id}"
    '''
    try:
        rows = database.select_record(sql)
    except Exception:
        return hosp_id

    if len(rows) <= 0:
        return hosp_id

    row = rows[0]

    return string_utils.xstr(row["HospName"])


# 寫入暫存預約備註
def set_reserve_temp_remark(
    database, reservation_date, period, doctor, row_no, col_no, remark
):
    sql = f'''
        DELETE FROM reserve_temp_remark
        WHERE
            ReserveDate = "{reservation_date}" AND
            Period = "{period}" AND
            Doctor = "{doctor}" AND
            RowNo = {row_no} AND
            ColNo = {col_no}
    '''
    database.exec_sql(sql)

    if remark in [None, ""]:
        return

    fields = [
        "ReserveDate",
        "Period",
        "Doctor",
        "RowNo",
        "ColNo",
        "Remark",
    ]

    data = [
        reservation_date,
        period,
        doctor,
        row_no,
        col_no,
        remark,
    ]

    database.insert_record("reserve_temp_remark", fields, data)


# 讀取暫存預約備註
def get_reserve_temp_remark(database, reservation_date, period, doctor, row_no, col_no):
    sql = f'''
        SELECT Remark FROM reserve_temp_remark
        WHERE
            ReserveDate = "{reservation_date}" AND
            Period = "{period}" AND
            Doctor = "{doctor}" AND
            RowNo = {row_no} AND
            ColNo = {col_no}
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    row = rows[0]

    return string_utils.xstr(row["Remark"])


def get_agent_doctor(database, case_date, period, doctor, room):
    sql = f'''
        SELECT * FROM temporary_schedule
        WHERE
            CaseDate = "{case_date}" AND
            Period = "{period}" AND
            ScheduleType IN ("請假", "代班") AND
            Position = "醫師" AND
            Name = "{doctor}"
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return doctor, room

    row = rows[0]
    doctor = string_utils.xstr(row["Agent"])
    room = number_utils.get_integer(row["Room"])
    return doctor, room


def get_return_card_days(system_settings):
    return_card_days = number_utils.get_integer(system_settings.field("還卡期限"))
    if return_card_days <= 0:
        return_card_days = 7

    return return_card_days


# 是否在權限清單內
def is_today_already_visited(database, patient_key):
    already_visited = False
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    sql = f'''
        SELECT CaseKey FROM cases
        WHERE
            DATE(CaseDate) = "{today}" AND
            PatientKey = {patient_key} AND
            TreatType != "自購"

    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        already_visited = True

    return already_visited


# 檢查上次給藥是否用完
def get_first_course_treatment(
    database, system_settings, case_date, patient_key, card, course
):
    today = datetime.date.today()
    start_date = (case_date - datetime.timedelta(days=30)).strftime("%Y-%m-01 00:00:00")
    yesterday = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")

    sql = f'''
        SELECT Treatment FROM cases
        WHERE
            CaseDate BETWEEN "{start_date}" AND "{yesterday}" AND
            PatientKey = {patient_key} AND
            Card = "{card}" AND
            Continuance = 1
        ORDER BY CaseDate
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    row = rows[0]
    treatment = string_utils.xstr(row["Treatment"])

    return treatment


# 檢查當月健保針傷門診就診次數
def check_cancer_acupuncture_times(database, system_settings, patient_key):
    message = None
    cancer_acupuncture_times = get_cancer_acupuncture_times(database, patient_key)
    if cancer_acupuncture_times > CANCER_ACUPUNCTURE_TIMES_LIMIT:
        message = f"""
            * 癌症針灸次數警告:<br>
            本月癌症門診針灸次數共{cancer_acupuncture_times}次, 已達系統設定{CANCER_ACUPUNCTURE_TIMES_LIMIT}次的限制.
            <br>
        """

    return message


def get_cancer_acupuncture_times(database, patient_key):
    start_date = datetime.datetime.now().strftime("%Y-%m-01 00:00:00")
    end_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
        "%Y-%m-%d 23:59:59"
    )

    sql = f'''
        SELECT CaseKey from cases
        WHERE
            (PatientKey = {patient_key}) AND
            (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
            (InsType = "健保") AND
            (TreatType LIKE "%癌%") AND
            (Treatment LIKE "%針%")
    '''
    rows = database.select_record(sql)

    return len(rows)
