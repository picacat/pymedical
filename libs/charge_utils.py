# 取得各項費用金額

import ast
import datetime
import json

from PyQt5 import QtCore, QtWidgets

from libs import (
    case_utils,
    date_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    personnel_utils,
    prescript_utils,
    string_utils,
)

DISCOUNT_TYPE = ["掛號費優待", "門診負擔優待", "藥品負擔優待", "自費掛號費優待"]
PROCESS_MEDICINE = "代煎水藥"


# 取得基本掛號費
def _get_basic_regist_fee(database, ins_type, visit="複診"):
    regist_fee = 0

    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "掛號費" AND
            ItemName = "基本掛號費" AND
            InsType = "{ins_type}"
    '''
    rows = database.select_record(sql)

    if not rows:
        # msg_box = QMessageBox()
        # msg_box.setIcon(QMessageBox.Critical)
        # msg_box.setWindowTitle("找不到基本掛號費")
        # msg_box.setText(
        #     "<font size='4' color='red'><b>找不到基本掛號費，請至收費資料->掛號費設定</b></font>"
        # )
        # msg_box.setInformativeText("請新增「基本掛號費」")
        # msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        # msg_box.exec_()
        sql = """
            SELECT * FROM charge_settings
            WHERE
                ChargeType = "掛號費" AND
                ItemName = "基本掛號費" AND
                InsType = "健保"
        """
        rows = database.select_record(sql)
        if not rows:
            return 0

        row = rows[0]
        regist_fee = number_utils.get_float(row["Amount"])

        return regist_fee

    row = rows[0]
    regist_fee = number_utils.get_float(row["Amount"])

    if visit == "初診":
        json_data = string_utils.xstr(row["Remark"])
        json_regist_remark_fee = get_json_remark_fee(
            json_data=json_data, field_name="初診"
        )
        if json_regist_remark_fee is not None:
            regist_fee = json_regist_remark_fee

    return regist_fee


# 基本掛號費
def _get_basic_discount_fee(database):
    discount_fee = 0
    sql = """
            SELECT * FROM charge_settings WHERE ChargeType = "掛號費優待" AND
            ItemName = "其他優待"
          """
    try:
        row = database.select_record(sql)[0]
    except IndexError:
        # msg_box = QMessageBox()
        # msg_box.setIcon(QMessageBox.Critical)
        # msg_box.setWindowTitle("找不到其他優待")
        # msg_box.setText(
        #     "<font size='4' color='red'><b>找不到其他優待，請至收費資料->掛號費優待設定</b></font>"
        # )
        # msg_box.setInformativeText("請新增「其他優待")
        # msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        # msg_box.exec_()
        return discount_fee

    if len(row) > 0:
        discount_fee = number_utils.get_integer(row["Amount"])

    return discount_fee


# 取得複合掛號費優待
def _get_compound_discount_fee(database, share_type, discount_type):
    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "掛號費優待" AND
            (ItemName = "{discount_type}{share_type}" OR
             ItemName = "{share_type}{discount_type}")
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        discount_fee = None
    else:
        discount_fee = number_utils.get_integer(rows[0]["Amount"])

    return discount_fee


# 取得掛號費優待
def _get_regist_discount_fee(database, discount_type):
    discount_fee = _get_basic_discount_fee(database)

    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "掛號費優待" AND
            ItemName = "{discount_type}"
    '''
    rows = database.select_record(sql)

    if len(rows) > 0:
        row = rows[0]
        discount_fee = number_utils.get_integer(row["Amount"])
    else:
        discount_type = discount_type.replace("療程", "")
        sql = f'''
            SELECT * FROM charge_settings
            WHERE
                ChargeType = "掛號費優待" AND
                ItemName = "{discount_type}"
        '''
        rows = database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            discount_fee = number_utils.get_integer(row["Amount"])

    return discount_fee


# 取得自費掛號費優待
def _get_self_regist_discount_fee(database, discount_type):
    discount_fee = None
    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "自費掛號費優待" AND
            ItemName = "{discount_type}"
    '''
    rows = database.select_record(sql)

    if len(rows) > 0:
        row = rows[0]
        discount_fee = number_utils.get_integer(row["Amount"])

    return discount_fee


# 取得掛號費設定的備註json值
def get_json_fee(system_settings, birthday, regist_fee, discount_type, json_data):
    try:
        regist_fee_dict = json.loads(json_data)
    except Exception:
        return None

    old_man = is_old_man(system_settings, birthday)
    child = is_child(system_settings, birthday)

    if discount_type in ["", None] and old_man:
        discount_type = "老人"
    elif discount_type in ["", None] and child:
        discount_type = "兒童"

    try:
        regist_fee = regist_fee_dict[discount_type]
    except Exception:
        return None

    return regist_fee


# 取得掛號費設定的備註json值
def get_json_remark_fee(json_data, field_name):
    try:
        # regist_fee_dict = json.loads(json_data)
        regist_fee_dict = ast.literal_eval(json_data)
    except Exception:
        return None

    try:
        regist_fee = regist_fee_dict[field_name]
    except Exception:
        return None

    return regist_fee


# 取得掛號費
def get_regist_fee(
    database,
    system_settings,
    birthday,
    discount_type,
    ins_type,
    share_type,
    treat_type,
    course=None,
    visit="複診",
):
    if share_type == "中低收入戶":
        share_type = "基層醫療"

    if ins_type == "自費":
        regist_fee = _get_basic_regist_fee(database, ins_type, visit=visit)
        if string_utils.xstr(discount_type) != "":  # 掛號費優待優先取得
            discount_fee = _get_self_regist_discount_fee(
                database, discount_type=discount_type
            )
            if discount_fee is not None:
                if discount_fee < 0:
                    regist_fee += discount_fee
                else:
                    regist_fee = discount_fee

        return regist_fee

    regist_fee = _get_basic_regist_fee(database, ins_type, visit=visit)
    course_type = nhi_utils.get_course_type(course)
    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "掛號費" AND
            InsType = "{ins_type}" AND
            ShareType = "{share_type}" AND
            TreatType = "不分類" AND
            Course = "{course_type}"
    '''
    try:
        rows = database.select_record(sql)
    except Exception:
        pass

    if len(rows) <= 0:
        sql = f'''
            SELECT * FROM charge_settings
            WHERE
                ChargeType = "掛號費" AND
                InsType = "{ins_type}" AND
                ShareType = "{share_type}"
        '''

        if "針" in treat_type:
            treat_type = "針灸治療"
        elif "傷科" in treat_type or "脫臼" in treat_type or "骨折" in treat_type:
            treat_type = "傷科治療"
        else:
            treat_type = "內科"

        if ins_type == "健保":
            sql += f'''
                AND
                TreatType = "{treat_type}" AND
                Course = "{course_type}"
            '''

        try:
            rows = database.select_record(sql)
        except Exception:
            pass

    if len(rows) > 0:
        row = rows[0]
        regist_fee = number_utils.get_integer(row["Amount"])

        remark = string_utils.xstr(row["Remark"])
        if remark == "排除其他優待":
            return number_utils.get_integer(regist_fee)
        elif remark != "":
            if visit == "初診":
                json_data = string_utils.xstr(rows[0]["Remark"])
                json_regist_remark_fee = get_json_remark_fee(
                    json_data=json_data, field_name="初診"
                )
                if json_regist_remark_fee is not None:
                    regist_fee = number_utils.get_integer(json_regist_remark_fee)

            json_regist_fee = get_json_fee(
                system_settings, birthday, regist_fee, discount_type, remark
            )
            if json_regist_fee is not None:
                regist_fee = number_utils.get_integer(json_regist_fee)
                return number_utils.get_integer(regist_fee)

    if string_utils.xstr(discount_type) != "":  # 掛號費優待優先取得
        discount_fee = None

        if share_type != "基層醫療" and discount_type != "":
            discount_fee = _get_compound_discount_fee(
                database, share_type, discount_type
            )

        if discount_fee is None and course_type == "療程":
            discount_fee = _get_regist_discount_fee(
                database, discount_type + course_type
            )

        if discount_fee is None:
            discount_fee = _get_regist_discount_fee(database, discount_type)

        if discount_fee >= 0:
            regist_fee = discount_fee
        else:
            regist_fee += discount_fee
    else:  # 最後檢查是否符合老人優待, 已經優待者就不檢查
        old_man_regist_fee = get_old_man_regist_fee(
            database, system_settings, birthday, course_type
        )
        child_regist_fee = get_child_regist_fee(
            database, system_settings, birthday, course_type
        )
        try:
            other_age_regist_fee = get_other_age_regist_fee(
                database, system_settings, birthday, course_type
            )
        except Exception:
            other_age_regist_fee = None

        if old_man_regist_fee is not None:
            if old_man_regist_fee >= 0:
                regist_fee = old_man_regist_fee
            else:
                regist_fee += old_man_regist_fee

            if share_type != "基層醫療":
                special_regist_fee = get_old_man_special_regist_fee(
                    database, share_type
                )
                if special_regist_fee is not None:
                    regist_fee = special_regist_fee
        elif child_regist_fee is not None:
            if child_regist_fee >= 0:
                regist_fee = child_regist_fee
            else:
                regist_fee += child_regist_fee

            if share_type != "基層醫療":
                special_regist_fee = get_child_special_regist_fee(database, share_type)
                if special_regist_fee is not None:
                    regist_fee = special_regist_fee
        elif other_age_regist_fee is not None:
            if other_age_regist_fee >= 0:
                regist_fee = other_age_regist_fee
            else:
                regist_fee += other_age_regist_fee

    return number_utils.get_integer(regist_fee)


def is_old_man(system_settings, birthday):
    old_man = False

    try:
        birthday = date_utils.str_to_date(birthday)
    except Exception:
        return False

    age_year, _ = date_utils.get_age(birthday, datetime.datetime.now())
    old_man_age = number_utils.get_integer(system_settings.field("老人優待年齡"))
    if age_year >= old_man_age:
        old_man = True

    return old_man


def is_child(system_settings, birthday):
    child = False

    try:
        birthday = date_utils.str_to_date(birthday)
    except Exception:
        return False

    age_year, _ = date_utils.get_age(birthday, datetime.datetime.now())
    child_age = number_utils.get_integer(system_settings.field("兒童優待年齡"))
    if age_year <= child_age:
        child = True

    return child


def get_old_man_regist_fee(database, system_settings, birthday, course_type):
    old_man_regist_fee = None
    if system_settings.field("老人優待") != "Y":
        return old_man_regist_fee

    if birthday == "":
        return old_man_regist_fee

    if is_old_man(system_settings, birthday):
        sql = f"""
            SELECT * FROM charge_settings
            WHERE
                ChargeType = "掛號費優待" AND
                ItemName = "年長病患{course_type}"
        """
        rows = database.select_record(sql)  # 檢查是否有指定首次或療程
        if len(rows) > 0:
            old_man_regist_fee = number_utils.get_integer(rows[0]["Amount"])
        else:
            sql = """
                SELECT * FROM charge_settings
                WHERE
                    ChargeType = "掛號費優待" AND
                    ItemName = "年長病患"
            """
            rows = database.select_record(sql)
            if len(rows) > 0:
                old_man_regist_fee = number_utils.get_integer(rows[0]["Amount"])

    return old_man_regist_fee


def get_child_regist_fee(database, system_settings, birthday, course_type):
    child_regist_fee = None
    if system_settings.field("兒童優待") != "Y":
        return child_regist_fee

    if birthday == "":
        return child_regist_fee

    if is_child(system_settings, birthday):
        sql = f"""
            SELECT * FROM charge_settings
            WHERE
                ChargeType = "掛號費優待" AND
                ItemName = "兒童病患{course_type}"
        """
        rows = database.select_record(sql)  # 檢查是否有指定首次或療程
        if len(rows) > 0:
            child_regist_fee = number_utils.get_integer(rows[0]["Amount"])
        else:
            sql = """
                SELECT * FROM charge_settings
                WHERE
                    ChargeType = "掛號費優待" AND
                    ItemName = "兒童病患"
            """
            rows = database.select_record(sql)
            if len(rows) > 0:
                child_regist_fee = number_utils.get_integer(rows[0]["Amount"])

    return child_regist_fee


def get_other_age_regist_fee(database, system_settings, birthday, course_type):
    other_age_regist_fee = None

    if birthday == "":
        return other_age_regist_fee

    sql = """
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "掛號費優待" AND
            ItemName LIKE "%-%"
    """
    rows = database.select_record(sql)  # xx-yy xx=min age, yy=max age
    if len(rows) <= 0:
        return other_age_regist_fee

    try:
        birthday = date_utils.str_to_date(birthday)
    except Exception:
        return other_age_regist_fee

    age_year, _ = date_utils.get_age(birthday, datetime.datetime.now())

    for row in rows:
        item_name = string_utils.xstr(row["ItemName"])
        min_age = number_utils.get_integer(item_name.split("-")[0])
        max_age = number_utils.get_integer(item_name.split("-")[1])
        if min_age <= age_year <= max_age:
            other_age_regist_fee = number_utils.get_integer(rows[0]["Amount"])
            break

    return other_age_regist_fee


def get_old_man_special_regist_fee(database, share_type):
    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "掛號費優待" AND
            (ItemName = "年長病患{share_type}" OR
             ItemName = "{share_type}年長病患")
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        old_man_regist_fee = None
    else:
        old_man_regist_fee = number_utils.get_integer(rows[0]["Amount"])

    return old_man_regist_fee


def get_child_special_regist_fee(database, share_type):
    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "掛號費優待" AND
            (ItemName = "兒童病患{share_type}" OR
             ItemName = "{share_type}兒童病患")
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        child_regist_fee = None
    else:
        child_regist_fee = number_utils.get_integer(rows[0]["Amount"])

    return child_regist_fee


# 取得欠卡費
def get_deposit_fee(database, card):
    deposit_fee = 0

    if card != "欠卡":
        return deposit_fee

    sql = """
            SELECT * FROM charge_settings WHERE ChargeType = "掛號費" AND ItemName = "欠卡費"
          """
    try:
        row = database.select_record(sql)[0]
    except IndexError:
        return deposit_fee

    if len(row) > 0:
        deposit_fee = number_utils.get_integer(row["Amount"])

    return deposit_fee


# 取得預設自費水藥費
def get_default_herb_fee(database):
    herb_fee = 0

    sql = """
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "自費" AND ItemName = "自費水藥"
    """
    try:
        row = database.select_record(sql)[0]
    except Exception:
        return herb_fee

    if len(row) > 0:
        herb_fee = number_utils.get_integer(row["Amount"])

    return herb_fee


def get_custom_herb_fee1(database, case_key, table_widget_prescript):
    """仁聿中醫專用"""

    default_herb_fee = get_renyu_default_herb_fee(database, case_key)
    is_herbal_decocation_service = prescript_utils.is_herbal_decocation_service(
        table_widget_prescript
    )
    net_weight = prescript_utils.get_herbal_net_weight(
        is_herbal_decocation_service, table_widget_prescript
    )

    if net_weight < 20:
        set_normal_price(database, table_widget_prescript)
        default_herb_fee = 50
    elif 20 <= net_weight < 50:
        pass
    else:  # 淨重超過50ㄎ克, 減去50克, 餘數 * 5元 + 基本費
        net_weight -= 50
        default_herb_fee += net_weight * 5

    herb_fee = default_herb_fee

    return herb_fee


def get_renyu_default_herb_fee(database, case_key):
    """仁聿中醫專用: 取得預設水藥費"""
    default_herb_fee = 300  # 水藥基本費$300

    sql = f"""
        SELECT CaseDate, patient.Birthday FROM cases
            LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    if not rows:
        return default_herb_fee

    row = rows[0]
    age_year, _ = date_utils.get_age(row["Birthday"], row["CaseDate"])
    age_year = number_utils.get_integer(age_year)
    if age_year > 18:
        default_herb_fee = 300
    elif 13 <= age_year <= 18:
        default_herb_fee = 270
    else:  # 13歲以下
        default_herb_fee = 200

    return default_herb_fee


def set_normal_price(database, table_widget_prescript):
    for row_no in range(table_widget_prescript.rowCount()):
        medicine_key = table_widget_prescript.item(
            row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineKey"]
        )

        if medicine_key in [None, ""]:
            continue

        sql = f"""
            SELECT SalePrice FROM medicine
            WHERE
                MedicineKey = {medicine_key.text()}
        """
        rows = database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        price = string_utils.get_formatted_str("單價", row["SalePrice"])

        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, price)
        table_widget_prescript.setItem(
            row_no,
            prescript_utils.SELF_PRESCRIPT_COL_NO["Price"],
            item,
        )


# 取得預設自費水藥費
def get_herb_fee_by_dosage(database, total_dosage):
    herb_fee = get_default_herb_fee(database)

    sql = """
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "自費水藥"
        ORDER BY LENGTH(ItemName), ItemName
    """
    rows = database.select_record(sql)

    for row in rows:
        try:
            min = number_utils.get_integer(
                string_utils.xstr(row["ItemName"]).split("-")[0]
            )
            max = number_utils.get_integer(
                string_utils.xstr(row["ItemName"]).split("-")[1]
            )
        except Exception:
            continue

        if min <= total_dosage <= max:
            herb_fee = number_utils.get_integer(row["Amount"])
            break

    return herb_fee


# 取得自費水藥費
def get_herb_fee(
    database,
    system_settings,
    item_name,
    total_dosage,
    case_key=None,
    table_widget_prescript=None,
):
    if system_settings.field("自費水藥批價原則") == "Y":
        herb_fee = get_herb_fee_by_dosage(database, total_dosage)
    # elif system_settings.field('院所名稱') in ['仁聿中醫診所']:
    #     herb_fee = get_custom_herb_fee1(database, case_key, table_widget_prescript)
    else:
        herb_fee = get_default_herb_fee(database)

    return herb_fee


# 取得自費項目其他項目費用
def get_misc_fee(database, item_name):
    misc_fee = 0

    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "自費" AND ItemName = "{item_name}"
    '''
    try:
        row = database.select_record(sql)[0]
    except IndexError:
        return misc_fee

    if len(row) > 0:
        misc_fee = number_utils.get_integer(row["Amount"])

    return misc_fee


# 取得掛號備註相同名稱的自費項目其他項目費用
def get_remark_fee(database, item_name):
    misc_fee = 0

    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "自費" AND InsType = "備註" AND ItemName = "{item_name}"
    '''
    try:
        row = database.select_record(sql)[0]
    except IndexError:
        return misc_fee

    if len(row) > 0:
        misc_fee = number_utils.get_integer(row["Amount"])

    return misc_fee


# 取得門診負擔 (treat_type 取代 treatment的原因: 掛號時須取得門診負擔, 以treat_type代表)
def get_diag_share_fee(
    database, system_settings, share_type, treat_type, course, reg_type=None
):
    diag_share_fee = 0

    if share_type in ["", None, "中低收入戶"]:
        share_type = "基層醫療"

    if share_type in ["山地離島"]:
        return diag_share_fee

    if share_type in nhi_utils.AGENT_SHARE:
        return diag_share_fee

    if treat_type in nhi_utils.HOME_CARE:
        diag_fee = get_ins_fee_from_ins_code(database, "P5408C")

        return number_utils.round_up(
            diag_fee * 5 / 100
        )  # 門診掛號居家醫療部份負擔: 申報費用 5%

    course_type = nhi_utils.get_course_type(course)
    if treat_type in nhi_utils.ACUPUNCTURE_TREAT:
        treat_type = "針灸治療"
    elif treat_type in nhi_utils.MASSAGE_TREAT:
        treat_type = "傷科治療"
    else:
        treat_type = "內科"

    sql = f'''
        SELECT Amount FROM charge_settings
        WHERE
            ChargeType = "門診負擔" AND
            ShareType = "{share_type}" AND
            TreatType = "{treat_type}" AND
            Course = "{course_type}"
        LIMIT 1
    '''

    try:
        row = database.select_record(sql)[0]
    except IndexError:
        # msg_box = QtWidgets.QMessageBox()
        # msg_box.setIcon(QtWidgets.QMessageBox.Critical)
        # msg_box.setWindowTitle("遺失部份負擔設定")
        # msg_box.setText(
        #     f"<font size='4' color='red'><b>遺失{share_type}{treat_type}{course_type}部份負擔設定，請檢查！</b></font>"
        # )
        # msg_box.setInformativeText("請至收費設定的「部份負擔」頁面新增")
        # msg_box.addButton(QtWidgets.QPushButton("確定"), QtWidgets.QMessageBox.YesRole)
        # msg_box.exec_()
        return diag_share_fee

    if len(row) > 0:
        diag_share_fee = number_utils.get_integer(row["Amount"])

    if (
        reg_type in nhi_utils.TOUR_FAR
        or reg_type in nhi_utils.LACK_AREA
        or system_settings.field("資源類別") in nhi_utils.TOUR_FAR
        or system_settings.field("資源類別") in nhi_utils.LACK_AREA
    ):
        diag_share_fee -= (
            diag_share_fee * nhi_utils.LACK_RESOURCE_DISCOUNT_RATE / 100
        )  # 資源不足及偏遠地區減免20%

    return number_utils.get_integer(diag_share_fee)


# 取得門診負擔優待
def get_diag_share_discount_fee(database, discount_type):
    diag_share_discount_fee = None

    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "門診負擔優待" AND
            ItemName = "{discount_type}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return diag_share_discount_fee

    row = rows[0]
    diag_share_discount_fee = number_utils.get_integer(row["Amount"])

    return diag_share_discount_fee


# 取得藥品負擔
def get_drug_share_fee(
    database, system_settings, share_type, ins_drug_fee, reg_type=None
):
    if share_type == "中低收入戶":
        share_type = "基層醫療"

    drug_share_fee = 0
    if share_type == "基層醫療":
        remark = None
        if ins_drug_fee <= 100:
            remark = "<=100"
        elif ins_drug_fee <= 200:
            remark = "<=200"
        elif ins_drug_fee <= 300:
            remark = "<=300"
        elif ins_drug_fee <= 400:
            remark = "<=400"
        elif ins_drug_fee <= 500:
            remark = "<=500"
        elif ins_drug_fee <= 600:
            remark = "<=600"
        elif ins_drug_fee <= 700:
            remark = "<=700"
        elif ins_drug_fee <= 800:
            remark = "<=800"
        elif ins_drug_fee <= 900:
            remark = "<=900"
        elif ins_drug_fee <= 1000:
            remark = "<=1000"
        elif ins_drug_fee > 1000:
            remark = ">1000"

        sql = f'''
            SELECT Amount FROM charge_settings
            WHERE
                (ChargeType = "藥品負擔") AND
                (ShareType = "{share_type}") AND
                (Remark = "{remark}")
            LIMIT 1
        '''
    else:
        sql = f'''
            SELECT Amount FROM charge_settings
            WHERE
                (ChargeType = "藥品負擔") AND
                (ShareType = "{share_type}")
            LIMIT 1
        '''

    try:
        row = database.select_record(sql)[0]
    except IndexError:
        return drug_share_fee

    if len(row) > 0:
        drug_share_fee = number_utils.get_integer(row["Amount"])

    resource_type = system_settings.field("資源類別")
    if (
        reg_type in nhi_utils.TOUR_FAR
        or reg_type in nhi_utils.LACK_AREA
        or resource_type in nhi_utils.TOUR_FAR
        or resource_type in nhi_utils.LACK_AREA
    ):
        drug_share_fee -= (
            drug_share_fee * nhi_utils.LACK_RESOURCE_DISCOUNT_RATE / 100
        )  # 資源不足及偏遠地區減免20%

    return number_utils.get_integer(drug_share_fee)


# 取得藥品負擔優待
def get_drug_share_discount_fee(database, discount_type):
    drug_share_discount_fee = None

    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "藥品負擔優待" AND
            ItemName = "{discount_type}"
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return drug_share_discount_fee

    row = rows[0]
    drug_share_discount_fee = number_utils.get_integer(row["Amount"])

    return drug_share_discount_fee


# 取得民俗條理費
def get_traditional_health_care_fee(
    database, system_settings, ins_type, course, massager
):
    traditional_health_care_fee = 0

    if system_settings.field("自動帶出民俗調理費") != "Y":
        return traditional_health_care_fee

    if massager in [None, ""]:
        return traditional_health_care_fee

    if course <= 1 and system_settings.field("療程首次民俗調理費") != "Y":
        return traditional_health_care_fee

    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "自費" AND
            ItemName = "民俗調理費" AND
            InsType = "{ins_type}"
    '''
    try:
        row = database.select_record(sql)[0]
    except IndexError:
        return traditional_health_care_fee

    if len(row) > 0:
        traditional_health_care_fee = number_utils.get_integer(row["Amount"])

    return traditional_health_care_fee


# 取得醫療費用金額
def get_ins_fee_from_ins_code(database, ins_code, case_date=None):
    ins_fee = 0

    if ins_code in [None, ""]:
        return ins_fee

    sql = f'''
        SELECT Amount, Remark FROM charge_settings
        WHERE
            InsCode = "{ins_code}"
        LIMIT 1
    '''

    rows = database.select_record(sql)
    if len(rows) <= 0:
        return ins_fee

    row = rows[0]
    ins_fee = number_utils.get_integer(row["Amount"])

    if case_date is not None:
        try:
            remark = string_utils.xstr(row["Remark"])
            old_charge_settings = json.loads(remark)

            case_date = case_date.strftime("%Y-%m-%d")
            old_date = old_charge_settings["原日期"]
            old_fee = old_charge_settings["原支付點數"]
            if old_date is not None and case_date < old_date:
                ins_fee = old_fee
        except Exception:
            pass

    return ins_fee


# 取得醫療費用名稱
def get_item_name_from_ins_code(database, ins_code):
    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            InsCode = "{ins_code}"
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return ins_code

    row = rows[0]
    item_name = string_utils.xstr(row["ItemName"])

    return item_name


# 取得健保門診診察費
# 取第一段診察費, 分有無護理人員, 支援醫師等到申報才調整
def get_ins_diag_fee(
    database, system_settings, course=1, diag_code=None, case_date=None
):
    ins_diag_fee = 0

    if course >= 2:  # 療程無診察費
        return ins_diag_fee

    if diag_code is None:
        nurse = system_settings.field("護士人數")
        if number_utils.get_integer(nurse) > 0:
            diag_code = "A01"
        else:
            diag_code = "A02"

    ins_diag_fee = get_ins_fee_from_ins_code(database, diag_code, case_date=case_date)

    return ins_diag_fee


# 取得健保藥費
# 藥費 = 每日藥費 * 給藥天數
def get_ins_drug_fee(database, pres_days, case_date=None):
    ins_drug_fee = 0

    if pres_days == 0:
        return ins_drug_fee

    drug_code = "A21"
    ins_drug_fee = (
        get_ins_fee_from_ins_code(database, drug_code, case_date=case_date) * pres_days
    )

    return ins_drug_fee


# 取得健保調劑費
# 調劑費 = 0: 不申報調劑費, 沒有申報藥費
# 調劑費 > 0: 藥師調劑, 醫師調劑
def get_ins_pharmacy_fee(
    database, system_settings, ins_drug_fee, pharmacy_type="申報", reg_type="一般門診"
):
    ins_pharmacy_fee = 0

    if ins_drug_fee == 0:
        return ins_pharmacy_fee

    if pharmacy_type not in ["申報"]:
        return ins_pharmacy_fee

    pharmacist = system_settings.field("藥師人數")

    if number_utils.get_integer(pharmacist) > 0:
        item_name = "藥師調劑"
    else:
        item_name = "醫師調劑"

    pharmacy_code = get_ins_code_from_charge_settings(database, "調劑費", item_name)
    ins_pharmacy_fee = get_ins_fee_from_ins_code(database, pharmacy_code)
    # ins_pharmacy_fee = get_extra_pharmacy_fee(reg_type, ins_pharmacy_fee)  # 調劑費加成 void 2022.09.08

    return ins_pharmacy_fee


# 計算調劑費加成
def get_extra_pharmacy_fee(reg_type, pharmacy_fee):
    # if reg_type in nhi_utils.CORRECTION_REG_TYPE:  # void 2022.09.08
    #     pharmacy_fee = number_utils.round_up(pharmacy_fee * 1.2)

    return pharmacy_fee


def get_ins_code_from_charge_settings(database, charge_type, item_name, fuzzy=False):
    ins_code = ""
    sql = f'''
        SELECT InsCode FROM charge_settings
        WHERE
            ChargeType = "{charge_type}"
    '''

    if fuzzy:
        sql += f' AND ItemName LIKE "{item_name}%"'
    else:
        sql += f' AND ItemName = "{item_name}"'

    sql += " LIMIT 1"
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ins_code

    return string_utils.xstr(rows[0]["InsCode"])


def get_ins_code_from_infectious_drug(database, medicine_name):
    ins_code = ""

    sql = f"""
        SELECT InsCode FROM medicine
        WHERE
            MedicineType IN ("單方", "複方") AND
            MedicineName LIKE "%{medicine_name}%" AND
            InsCode IS NOT NULL AND
            LENGTH(InsCode) > 0
        LIMIT 1
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ins_code

    return string_utils.xstr(rows[0]["InsCode"])


# 取得健保針灸費
def get_ins_acupuncture_fee(
    database,
    treatment,
    ins_drug_fee,
    course=None,
    case_date=None,
    long_term_care=False,
):
    ins_acupuncture_fee = 0

    if treatment not in nhi_utils.ACUPUNCTURE_DRUG_DICT:
        return ins_acupuncture_fee

    if long_term_care and treatment in [
        "一般針灸合併中度傷科",
        "電針合併中度傷科",
        "中度針灸合併中度傷科",
        "高度針灸合併中度傷科",
        "中度複雜性傷科",
    ]:
        treatment += "不分療程"

    if ins_drug_fee > 0:
        acupuncture_code = nhi_utils.ACUPUNCTURE_DRUG_DICT[treatment]
        if course >= 2:
            if acupuncture_code == "F03":
                acupuncture_code = "F04"
            elif acupuncture_code == "F06":
                acupuncture_code = "F07"
            elif acupuncture_code == "F09":
                acupuncture_code = "F10"
            elif acupuncture_code == "F12":
                acupuncture_code = "F13"
            elif acupuncture_code == "F15":
                acupuncture_code = "F16"
            elif acupuncture_code == "F20":
                acupuncture_code = "F21"
            elif acupuncture_code == "F23":
                acupuncture_code = "F24"
            elif acupuncture_code == "F26":
                acupuncture_code = "F27"
            elif acupuncture_code == "F29":
                acupuncture_code = "F30"
            elif acupuncture_code == "F32":
                acupuncture_code = "F33"
            elif acupuncture_code == "F43":
                acupuncture_code = "F44"
            elif acupuncture_code == "F46":
                acupuncture_code = "F47"
            elif acupuncture_code == "F49":
                acupuncture_code = "F50"
            elif acupuncture_code == "F60":
                acupuncture_code = "F61"
            elif acupuncture_code == "F63":
                acupuncture_code = "F64"
            elif acupuncture_code == "F66":
                acupuncture_code = "F67"
            # ------原來的轉換-----------------------------------------------------
            elif acupuncture_code == "F37":
                acupuncture_code = "F38"
            elif acupuncture_code == "F40":
                acupuncture_code = "F41"
            elif acupuncture_code == "F54":
                acupuncture_code = "F55"
            elif acupuncture_code == "F57":
                acupuncture_code = "F58"
            # --------------------------------------------------------------------
    else:
        acupuncture_code = nhi_utils.ACUPUNCTURE_DICT[treatment]
        if course >= 2:
            if acupuncture_code == "F03":
                acupuncture_code = "F05"
            elif acupuncture_code == "F06":
                acupuncture_code = "F08"
            elif acupuncture_code == "F09":
                acupuncture_code = "F11"
            elif acupuncture_code == "F12":
                acupuncture_code = "F14"
            elif acupuncture_code == "F15":
                acupuncture_code = "F17"
            elif acupuncture_code == "F20":
                acupuncture_code = "F22"
            elif acupuncture_code == "F23":
                acupuncture_code = "F25"
            elif acupuncture_code == "F26":
                acupuncture_code = "F28"
            elif acupuncture_code == "F29":
                acupuncture_code = "F31"
            elif acupuncture_code == "F32":
                acupuncture_code = "F34"
            elif acupuncture_code == "F43":
                acupuncture_code = "F45"
            elif acupuncture_code == "F46":
                acupuncture_code = "F48"
            elif acupuncture_code == "F49":
                acupuncture_code = "F51"
            elif acupuncture_code == "F60":
                acupuncture_code = "F62"
            elif acupuncture_code == "F63":
                acupuncture_code = "F65"
            elif acupuncture_code == "F66":
                acupuncture_code = "F68"
            # ------原來的轉換-----------------------------------------------------
            elif acupuncture_code == "F37":
                acupuncture_code = "F39"
            elif acupuncture_code == "F40":
                acupuncture_code = "F42"
            elif acupuncture_code == "F54":
                acupuncture_code = "F56"
            elif acupuncture_code == "F57":
                acupuncture_code = "F59"
            # --------------------------------------------------------------------

    ins_acupuncture_fee = get_ins_fee_from_ins_code(
        database, acupuncture_code, case_date=case_date
    )

    return ins_acupuncture_fee


# 取得健保傷科治療費
def get_ins_massage_fee(database, treatment, ins_drug_fee, long_term_care=False):
    ins_massage_fee = 0
    if treatment not in nhi_utils.MASSAGE_TREAT:
        return ins_massage_fee

    if long_term_care and treatment in ["中度複雜性傷科"]:  # 中度傷科才分不分療程
        treatment += "不分療程"

    if ins_drug_fee > 0:
        massage_code = nhi_utils.MASSAGE_DRUG_DICT[treatment]
    else:
        massage_code = nhi_utils.MASSAGE_DICT[treatment]

    ins_massage_fee = get_ins_fee_from_ins_code(database, massage_code)

    return ins_massage_fee


# 取得健保脫臼治療費
def get_ins_dislocate_fee(database, treatment, ins_drug_fee):
    ins_dislocate_fee = 0

    if treatment not in nhi_utils.DISLOCATE_TREAT:
        return ins_dislocate_fee

    if ins_drug_fee > 0:
        dislocate_code = nhi_utils.DISLOCATE_DRUG_DICT[treatment]
    else:
        dislocate_code = nhi_utils.DISLOCATE_DICT[treatment]

    ins_dislocate_fee = get_ins_fee_from_ins_code(database, dislocate_code)

    return ins_dislocate_fee


# 取得健保加計費
def get_ins_exam_fee(database, case_key, treatment, integrate_care=None):
    ins_exam_fee = 0

    if integrate_care is None:
        if case_utils.get_case_extend(database, case_key, "整合醫療照護") == "Y":
            ins_exam_fee += get_ins_fee_from_ins_code(database, "A91")
    elif integrate_care:
        ins_exam_fee += get_ins_fee_from_ins_code(database, "A91")

    patient_key = patient_utils.get_patient_key(database, case_key)
    if patient_key is not None:
        sql = f"""
            SELECT cases.CaseDate, cases.Continuance, cases.Treatment, patient.Birthday FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                CaseKey = {case_key}
        """
        rows = database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            age_year, _ = date_utils.get_age(row["Birthday"], row["CaseDate"])
            course = number_utils.get_integer(row["Continuance"])
            case_date = row["CaseDate"].strftime("%Y-%m-%d")
            # if age_year is not None and age_year < 7 and \
            if (
                case_date >= "2023-03-01"
                and age_year is not None
                and age_year < 7
                and treatment in nhi_utils.MASSAGE_TREAT
                and course <= 1
            ):
                ins_exam_fee += get_ins_fee_from_ins_code(database, "E90")

    return ins_exam_fee


# 取得健保加強照護費
def get_ins_care_fee_from_case_key(database, case_key):
    ins_care_fee = 0

    sql = f"""
        SELECT InsCode FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = 11
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ins_care_fee

    for row in rows:
        ins_care_fee += get_ins_fee_from_ins_code(
            database, string_utils.xstr(row["InsCode"])
        )

    return ins_care_fee


# 取得健保加強照護費  medical_record_rows = ins_card_record  field 12 => amount
def get_ins_care_fee_from_table_widget(table_widget):
    ins_care_fee = 0
    for row_no in range(table_widget.rowCount()):
        item = table_widget.item(row_no, prescript_utils.INS_CARE_COL_NO["Amount"])
        if item is None:
            continue

        amount = number_utils.get_integer(item.text())
        ins_care_fee += amount

    return ins_care_fee


# 取得健保代辦費
def get_ins_agent_fee(
    database,
    system_settings,
    share_type,
    treatment,
    course,
    ins_drug_fee,
    reg_type=None,
):
    ins_agent_fee = 0

    if share_type in ["重大傷病", "山地離島"]:  # 重大傷病, 山地離島: 無代辦費
        return ins_agent_fee

    if share_type in nhi_utils.AGENT_SHARE:
        diag_share_fee = get_diag_share_fee(  # 以基層醫療為代辦基礎
            database,
            system_settings,
            "基層醫療",
            nhi_utils.get_treat_type(treatment),
            course,
            reg_type,
        )
        drug_share_fee = get_drug_share_fee(
            database,
            system_settings,
            "基層醫療",
            ins_drug_fee,
            reg_type,
        )
        ins_agent_fee = diag_share_fee + drug_share_fee

    return ins_agent_fee


def clear_ins_fee():
    ins_fee = {
        "diag_fee": 0,
        "drug_fee": 0,
        "pharmacy_fee": 0,
        "acupuncture_fee": 0,
        "massage_fee": 0,
        "dislocate_fee": 0,
        "ins_total_fee": 0,
        "diag_share_fee": 0,
        "drug_share_fee": 0,
        "exam_fee": 0,
        "ins_apply_fee": 0,
        "agent_fee": 0,
    }

    return ins_fee


# 檢查診察費是否需要加成
def check_markup_diag_fee(diag_fee, regist_type):
    # if regist_type in nhi_utils.TOUR_TYPE:
    #     diag_fee = number_utils.get_integer(diag_fee * 1.1)  # 巡迴醫療診察費加成10%  有新的醫令

    # if regist_type in nhi_utils.CORRECTION_REG_TYPE:  # void 2022.09.08
    #     diag_fee = number_utils.get_integer(diag_fee * 1.1)  # 矯正機關內門診診察費加成10%

    return diag_fee


# 取得健保申報費用
def get_ins_fee(database, system_settings, table_widget_ins_care=None, **kwargs):
    pres_days = kwargs["pres_days"]
    infectious_drug = kwargs["infectious_drug"]

    try:
        isolation_position = kwargs["isolation_position"]
    except Exception:
        isolation_position = None

    try:
        integrate_care = kwargs["integrate_care"]
    except Exception:
        integrate_care = None

    case_key = kwargs["case_key"]
    # case_date, _ = case_utils.get_case_date(database, case_key)
    case_date = kwargs.get("case_date")
    if case_date is None:
        case_date, _ = case_utils.get_case_date(database, case_key)

    if kwargs["treat_type"] in nhi_utils.CARE_TREAT:
        ins_fee = get_ins_special_care_fee(
            database,
            system_settings,
            table_widget_ins_care,
            case_key=case_key,
            treat_type=kwargs["treat_type"],
            reg_type=kwargs["reg_type"],
            share=kwargs["share"],
            course=kwargs["course"],
            pres_days=pres_days,
            pharmacy_type=kwargs["pharmacy_type"],
            treatment=kwargs["treatment"],
        )
        ins_fee["exam_fee"] = get_ins_exam_fee(
            database, case_key, kwargs["treatment"], integrate_care
        )
        return ins_fee

    ins_fee = {}
    ins_fee["exam_fee"] = get_ins_exam_fee(
        database, case_key, kwargs["treatment"], integrate_care
    )

    if kwargs["treat_type"] in nhi_utils.HOME_CARE:
        diag_code = nhi_utils.get_home_care_ins_code(database, kwargs["reg_type"])
        ins_fee["diag_fee"] = get_ins_diag_fee(
            database, system_settings, kwargs["course"], diag_code, case_date=case_date
        )
    else:
        ins_fee["diag_fee"] = get_ins_diag_fee(
            database, system_settings, kwargs["course"], case_date=case_date
        )

    ins_fee["diag_fee"] = check_markup_diag_fee(ins_fee["diag_fee"], kwargs["reg_type"])

    # if kwargs['reg_type'] in nhi_utils.TOUR_TYPE:
    #     ins_fee['diag_fee'] = number_utils.get_integer(ins_fee['diag_fee'] * 1.1)  # 巡迴醫療診察費加成10%
    # elif kwargs['reg_type'] in nhi_utils.CORRECTION_REG_TYPE:
    #     ins_fee['diag_fee'] = number_utils.get_integer(ins_fee['diag_fee'] * 1.1)  # 矯正機關內門診診察費加成10%

    ins_fee["drug_fee"] = get_ins_drug_fee(database, pres_days, case_date=case_date)
    ins_fee["pharmacy_fee"] = get_ins_pharmacy_fee(
        database,
        system_settings,
        ins_fee["drug_fee"],
        kwargs["pharmacy_type"],
        kwargs["reg_type"],
    )

    if kwargs["reg_type"] in nhi_utils.LONG_TERM_CARE + nhi_utils.TOUR_TYPE:
        long_term_care = True
    else:
        long_term_care = False

    ins_fee["acupuncture_fee"] = get_ins_acupuncture_fee(
        database,
        kwargs["treatment"],
        ins_fee["drug_fee"],
        kwargs["course"],
        case_date=case_date.date(),
        long_term_care=long_term_care,
    )

    ins_fee["massage_fee"] = get_ins_massage_fee(
        database,
        kwargs["treatment"],
        ins_fee["drug_fee"],
        long_term_care=long_term_care,
    )

    ins_fee["dislocate_fee"] = get_ins_dislocate_fee(
        database, kwargs["treatment"], ins_fee["drug_fee"]
    )

    if kwargs["share"] in nhi_utils.INFECTIOUS_INJURY_TYPE:  # 法定傳染病通報隔離
        if isolation_position in [None, "", "居家"]:
            ins_fee["diag_fee"] = get_ins_fee_from_ins_code(
                database, "E5204C"
            )  # 遠距診療費

        infectious_drug_fee = 0
        ins_drug_fee = 0
        if infectious_drug in ["台灣清冠一號及科學中藥", "台灣清冠一號"]:
            amount = get_ins_fee_from_ins_code(database, "E5012C")  # 台灣清冠一號補助費
            infectious_drug_fee = amount * pres_days
            ins_fee["pharmacy_fee"] = 0

        if infectious_drug in ["台灣清冠一號及科學中藥", "科學中藥"]:
            ins_drug_fee = get_ins_drug_fee(database, pres_days)
            ins_fee["pharmacy_fee"] = get_ins_pharmacy_fee(
                database,
                system_settings,
                ins_fee["drug_fee"],
                kwargs["pharmacy_type"],
                kwargs["reg_type"],
            )

        ins_fee["drug_fee"] = infectious_drug_fee + ins_drug_fee

        ins_fee["acupuncture_fee"] = 0
        ins_fee["massage_fee"] = 0
        ins_fee["dislocate_fee"] = 0
    elif case_date.strftime("%Y-%m-%d") >= "2023-03-20" and infectious_drug in [
        "台灣清冠一號及科學中藥",
        "台灣清冠一號",
    ]:
        amount = get_ins_fee_from_ins_code(database, "E5012C")  # 台灣清冠一號補助費
        infectious_drug_fee = amount * pres_days

        ins_drug_fee = 0
        if infectious_drug in ["台灣清冠一號及科學中藥", "科學中藥"]:
            ins_drug_fee = get_ins_drug_fee(database, pres_days)
            ins_fee["pharmacy_fee"] = get_ins_pharmacy_fee(
                database,
                system_settings,
                ins_fee["drug_fee"],
                kwargs["pharmacy_type"],
                kwargs["reg_type"],
            )
        else:
            ins_fee["pharmacy_fee"] = 0

        ins_fee["drug_fee"] = infectious_drug_fee + ins_drug_fee

    ins_fee["ins_total_fee"] = (
        ins_fee["diag_fee"]
        + ins_fee["drug_fee"]
        + ins_fee["pharmacy_fee"]
        + ins_fee["acupuncture_fee"]
        + ins_fee["massage_fee"]
        + ins_fee["dislocate_fee"]
        + ins_fee["exam_fee"]
    )

    # 非山地離島居家醫療門診部份負擔 = 申報合計 * 0.05
    if (
        kwargs["treat_type"] in nhi_utils.HOME_CARE
        and kwargs["reg_type"] not in nhi_utils.TOUR_TYPE
        and kwargs["share"] not in nhi_utils.AGENT_SHARE
    ):
        treat_fee = (
            ins_fee["acupuncture_fee"]
            + ins_fee["massage_fee"]
            + ins_fee["dislocate_fee"]
        )
        ins_fee["diag_share_fee"] = number_utils.round_up(
            (ins_fee["diag_fee"] + treat_fee) * 0.05
        )
        if kwargs["share"] in nhi_utils.NON_SHARE_TYPE:
            ins_fee["diag_share_fee"] = 0
    else:
        ins_fee["diag_share_fee"] = get_diag_share_fee(
            database,
            system_settings,
            kwargs["share"],
            kwargs["treatment"],
            kwargs["course"],
            kwargs["reg_type"],
        )

    drug_fee = ins_fee["drug_fee"]
    ins_fee["drug_share_fee"] = get_drug_share_fee(
        database,
        system_settings,
        kwargs["share"],
        drug_fee,
        kwargs["reg_type"],
    )
    if case_date.strftime("%Y-%m-%d") >= "2023-03-20" and infectious_drug in [
        "台灣清冠一號及科學中藥"
    ]:
        drug_fee = get_ins_drug_fee(database, pres_days)
        ins_fee["drug_share_fee"] = get_drug_share_fee(
            database,
            system_settings,
            kwargs["share"],
            drug_fee,
            kwargs["reg_type"],
        )
    elif infectious_drug in ["台灣清冠一號"]:
        ins_fee["drug_share_fee"] = 0

    ins_fee["ins_apply_fee"] = (
        ins_fee["ins_total_fee"] - ins_fee["diag_share_fee"] - ins_fee["drug_share_fee"]
    )

    if kwargs["share"] in nhi_utils.INFECTIOUS_INJURY_TYPE:  # 清冠一號
        drug_fee = 0

    ins_fee["agent_fee"] = get_ins_agent_fee(
        database,
        system_settings,
        kwargs["share"],
        kwargs["treatment"],
        kwargs["course"],
        drug_fee,
    )

    return ins_fee


# 取得各項照護申報費用
def get_ins_special_care_fee(
    database, system_settings, table_widget_ins_care=None, **kwargs
):
    ins_fee = {}
    diag_fee, drug_fee, pharmacy_fee, acupuncture_fee, massage_fee = 0, 0, 0, 0, 0
    pres_days = kwargs["pres_days"]
    treatment = kwargs["treatment"]
    course = kwargs["course"]

    if table_widget_ins_care is None:
        care_fee = get_ins_care_fee_from_case_key(
            database, kwargs["case_key"]
        )  # 小兒氣喘, 小兒腦麻為包套, 照護費已包含藥費, 調劑費與針傷處置費
    else:
        care_fee = get_ins_care_fee_from_table_widget(
            table_widget_ins_care
        )  # 小兒氣喘, 小兒腦麻為包套, 照護費已包含藥費, 調劑費與針傷處置費

    if kwargs["treat_type"] in [
        "腦血管疾病",
        "兒童鼻炎",
    ]:  # 腦血管疾病, 兒童鼻炎可申報藥費及調劑費
        drug_fee = get_ins_drug_fee(database, pres_days)
        pharmacy_fee = get_ins_pharmacy_fee(
            database,
            system_settings,
            drug_fee,
            kwargs["pharmacy_type"],
            kwargs["reg_type"],
        )
    elif kwargs["treat_type"] in ["癌症中醫門診延長照護"]:
        drug_code = get_ins_code_from_charge_settings(
            database, "照護費", "中醫門診延長照護每日藥費"
        )
        pharmacy_code = get_ins_code_from_charge_settings(
            database, "照護費", "中醫門診延長照護藥品調劑費"
        )

        drug_fee = get_ins_fee_from_ins_code(database, drug_code) * pres_days
        pharmacy_fee = get_ins_fee_from_ins_code(database, pharmacy_code)

        if treatment in nhi_utils.GENERAL_ACUPUNCTURE_TREAT:
            treat_code = get_ins_code_from_charge_settings(
                database, "照護費", "中醫門診延長照護針灸治療處置費"
            )
            acupuncture_fee = get_ins_fee_from_ins_code(database, treat_code)
        elif treatment in nhi_utils.GENERAL_MASSAGE_TREAT:
            treat_code = get_ins_code_from_charge_settings(
                database, "照護費", "中醫門診延長照護傷科治療處置費"
            )
            massage_fee = get_ins_fee_from_ins_code(database, treat_code)
        elif treatment in nhi_utils.ACUPUNCTURE_TREAT:
            acupuncture_fee = get_ins_acupuncture_fee(
                database, treatment, drug_fee, course
            )
        elif treatment in nhi_utils.MASSAGE_TREAT:
            massage_fee = get_ins_massage_fee(database, treatment, drug_fee)

    if kwargs["treat_type"] in ["腦血管疾病"]:  # 腦血管疾病可申報藥費及調劑費
        care_fee = get_ins_fee_from_ins_code(database, "C05")  # 預設為C05 <= 3次

    if kwargs["treat_type"] in ["兒童鼻炎"]:  # 兒童鼻炎可申報診察費, 針灸費, 傷科費
        diag_fee = get_ins_diag_fee(database, system_settings, kwargs["course"])
        acupuncture_fee = get_ins_acupuncture_fee(
            database, kwargs["treatment"], drug_fee
        )
        massage_fee = get_ins_massage_fee(database, kwargs["treatment"], drug_fee)

    ins_fee["diag_fee"] = diag_fee
    ins_fee["drug_fee"] = drug_fee
    ins_fee["pharmacy_fee"] = pharmacy_fee
    ins_fee["acupuncture_fee"] = acupuncture_fee
    ins_fee["massage_fee"] = massage_fee
    ins_fee["dislocate_fee"] = care_fee
    ins_fee["exam_fee"] = 0

    ins_fee["ins_total_fee"] = (
        ins_fee["diag_fee"]
        + ins_fee["drug_fee"]
        + ins_fee["pharmacy_fee"]
        + ins_fee["acupuncture_fee"]
        + ins_fee["massage_fee"]
        + ins_fee["dislocate_fee"]
    )

    ins_fee["diag_share_fee"] = get_diag_share_fee(
        database,
        system_settings,
        kwargs["share"],
        kwargs["treat_type"],
        kwargs["course"],
    )
    if (
        kwargs["treat_type"]
        in nhi_utils.AUXILIARY_CARE_TREAT
        + nhi_utils.CANCER_CARE_TREAT
        + nhi_utils.PREGNANT_CARE_TREAT
        + ["慢性腎病照護"]
    ):  # 照護要申報藥品負擔
        virtual_drug_fee = get_ins_drug_fee(database, kwargs["pres_days"])
        ins_fee["drug_share_fee"] = get_drug_share_fee(
            database, system_settings, kwargs["share"], virtual_drug_fee
        )
    else:
        ins_fee["drug_share_fee"] = get_drug_share_fee(
            database, system_settings, kwargs["share"], drug_fee
        )

    ins_fee["ins_apply_fee"] = (
        ins_fee["ins_total_fee"] - ins_fee["diag_share_fee"] - ins_fee["drug_share_fee"]
    )
    ins_fee["agent_fee"] = get_ins_agent_fee(
        database,
        system_settings,
        kwargs["share"],
        kwargs["treatment"],
        kwargs["course"],
        drug_fee,
    )

    return ins_fee


# 重新批價
def calculate_ins_fee(database, system_settings, case_key, ins_type=None):
    sql = f"""
        SELECT
            CaseKey, InsType, RegistType, Share, Continuance, TreatType, PharmacyType, Treatment
        FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        row = rows[0]
    else:
        return

    pres_days = case_utils.get_pres_days(database, case_key)
    reg_type = string_utils.xstr(row["RegistType"])
    treat_type = string_utils.xstr(row["TreatType"])
    if ins_type is None:
        ins_type = string_utils.xstr(row["InsType"])

    share = string_utils.xstr(row["Share"])
    course = number_utils.get_integer(row["Continuance"])
    pharmacy_type = string_utils.xstr(row["PharmacyType"])
    treatment = string_utils.xstr(row["Treatment"])
    infectious_drug = prescript_utils.get_infectious_drug(database, row["CaseKey"])
    isolation_position = case_utils.get_case_extend(
        database, row["CaseKey"], "隔離處所"
    )

    ins_fee = get_ins_fee(
        database,
        system_settings,
        case_key=case_key,
        reg_type=reg_type,
        treat_type=treat_type,
        share=share,
        course=course,
        pres_days=pres_days,
        pharmacy_type=pharmacy_type,
        treatment=treatment,
        infectious_drug=infectious_drug,
        isolation_position=isolation_position,
    )

    if treat_type == "居家醫療" and ins_fee["pharmacy_fee"] > 0:
        pharmacy_type = "不申報"
        ins_fee["ins_total_fee"] -= ins_fee["pharmacy_fee"]
        ins_fee["ins_apply_fee"] -= ins_fee["pharmacy_fee"]
        ins_fee["pharmacy_fee"] = 0

    if ins_type != "健保":
        ins_fee = clear_ins_fee()

    fields = [
        "DiagFee",
        "InterDrugFee",
        "PharmacyType",
        "PharmacyFee",
        "AcupunctureFee",
        "MassageFee",
        "DislocateFee",
        "ExamFee",
        "InsTotalFee",
        "DiagShareFee",
        "DrugShareFee",
        "InsApplyFee",
        "AgentFee",
    ]

    data = [
        ins_fee["diag_fee"],
        ins_fee["drug_fee"],
        pharmacy_type,
        ins_fee["pharmacy_fee"],
        ins_fee["acupuncture_fee"],
        ins_fee["massage_fee"],
        ins_fee["dislocate_fee"],
        ins_fee["exam_fee"],
        ins_fee["ins_total_fee"],
        ins_fee["diag_share_fee"],
        ins_fee["drug_share_fee"],
        ins_fee["ins_apply_fee"],
        ins_fee["agent_fee"],
    ]

    database.update_record("cases", fields, "CaseKey", case_key, data)


# 自費批價
def get_self_fee(parent, database, system_settings, tab_list):
    self_fee = {
        "diag_fee": 0.0,
        "drug_fee": 0.0,
        "herb_fee": 0.0,
        "expensive_fee": 0.0,
        "acupuncture_fee": 0.0,
        "massage_fee": 0.0,
        "material_fee": 0.0,
        "exam_fee": 0.0,
        "discount_fee": 0.0,
    }

    # self_fee['diag_fee'] = get_misc_fee(database, '自費診察費')

    for medicine_set, tab in enumerate(tab_list):
        medicine_set += 1
        if medicine_set in [1, 11]:  # 健保=1, 加強照護=11, 不批價
            continue

        if tab is None:
            continue

        try:
            pres_days = number_utils.get_integer(
                tab.ui.comboBox_pres_days.currentText()
            )
            if pres_days <= 0:
                pres_days = 1
        except Exception:
            pres_days = 1

        try:
            packages = number_utils.get_integer(tab.ui.comboBox_package.currentText())
            if packages <= 0:
                packages = 1
        except Exception:
            packages = 1

        try:
            self_fee["discount_fee"] += number_utils.get_integer(
                tab.ui.lineEdit_discount_fee.text()
            )
        except Exception:
            pass

        calculate_self_fee(
            parent,
            database,
            system_settings,
            tab.ui.tableWidget_prescript,
            pres_days,
            packages,
            self_fee,
        )

    return self_fee


# 計算自費批價
def calculate_self_fee(
    parent,
    database,
    system_settings,
    table_widget_prescript,
    pres_days,
    packages,
    self_fee,
):
    dosage_mode = system_settings.field("劑量模式")
    by_package = system_settings.field("自費處方次劑量")
    clinic_name = system_settings.field("院所名稱")
    dosage_percent = system_settings.field("比例法劑量")

    try:
        row_count = table_widget_prescript.rowCount()
    except RuntimeError:
        return

    for row_no in range(row_count):
        item = table_widget_prescript.item(
            row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"]
        )
        if item is None:
            continue

        medicine_type = item.text().strip()
        try:
            medicine_name = table_widget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
            ).text()
            if medicine_name in ["自費粉藥"] and clinic_name == "專嘉中醫診所":
                pres_days = 1
        except Exception:
            pass

        amount = get_table_widget_item_fee(
            table_widget_prescript,
            row_no,
            prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"],
        )

        unit_item = table_widget_prescript.item(
            row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Unit"]
        )
        if unit_item is not None:
            unit = unit_item.text()
        else:
            unit = None

        single_item = False
        this_pres_days = pres_days
        instruction_item = table_widget_prescript.item(
            row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"]
        )

        try:
            treat_type = parent.tab_registration.ui.comboBox_treat_type.currentText()
        except Exception:
            treat_type = None

        if this_pres_days <= 0:
            this_pres_days = 1
        elif (
            treat_type != "自購"
            and instruction_item is not None
            and instruction_item.text() != ""
        ):
            try:
                this_pres_days = number_utils.get_integer(instruction_item.text())
                single_item = True
            except Exception:
                single_item = False

            if this_pres_days <= 0:
                this_pres_days = pres_days

        if dosage_percent == "Y":
            this_pres_days = 1

        subtotal = get_subtotal_fee(amount, this_pres_days)

        if not single_item:
            if dosage_mode == "次劑量" or (
                by_package == "Y" and unit in ["顆", "錠"]
            ):  # 2025-02-27 耀康
                subtotal *= packages

        field = get_medicine_type_charge_field(database, medicine_type)
        charge_field = get_charge_field(field, medicine_type)

        self_fee[charge_field] += subtotal


def get_charge_field(field, medicine_type):
    if field in [None, ""]:
        if medicine_type == "診察":
            charge_field = "diag_fee"
        elif medicine_type == "水藥":
            charge_field = "herb_fee"
        elif medicine_type == "高貴":
            charge_field = "expensive_fee"
        elif medicine_type == "穴道":
            charge_field = "acupuncture_fee"
        elif medicine_type == "處置":
            charge_field = "massage_fee"
        elif medicine_type == "器材":
            charge_field = "material_fee"
        elif medicine_type == "檢驗":
            charge_field = "exam_fee"
        else:
            charge_field = "drug_fee"
    else:
        if field == "診察費":
            charge_field = "diag_fee"
        elif field == "自費藥費":
            charge_field = "drug_fee"
        elif field == "水藥費":
            charge_field = "herb_fee"
        elif field == "高貴藥費":
            charge_field = "expensive_fee"
        elif field == "自費針灸費":
            charge_field = "acupuncture_fee"
        elif field == "民俗調理費":
            charge_field = "massage_fee"
        elif field == "自費材料費":
            charge_field = "material_fee"
        elif field == "檢驗費":
            charge_field = "exam_fee"
        elif field == "自費診察費":
            charge_field = "diag_fee"
        else:
            charge_field = "drug_fee"

    return charge_field


def get_medicine_type_charge_field(database, medicine_type):
    sql = f'''
        SELECT * FROM dict_groups
        WHERE
            DictGroupsType IN ("藥品類別", "處置類別") AND
            DictGroupsName = "{medicine_type}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    row = rows[0]

    return string_utils.xstr(row["DictGroupsTopLevel"])


# 計算處方金額小計
def get_subtotal_fee(amount, pres_days):
    subtotal = number_utils.get_float(amount) * pres_days  # 小計四捨五入後再 * 天數

    return subtotal


def get_markup_diag_fee(database, ins_apply_row, diag_fee):
    case_key = ins_apply_row["CaseKey1"]
    if case_key is None:
        return diag_fee

    sql = f"""
        SELECT RegistType FROM cases
        WHERE
            CaseKey = {case_key}
    """
    case_rows = database.select_record(sql)
    if len(case_rows) <= 0:
        return diag_fee

    case_row = case_rows[0]
    diag_fee = check_markup_diag_fee(
        diag_fee, regist_type=string_utils.xstr(case_row["RegistType"])
    )  # 檢查診察費是否需要加成

    return diag_fee


def update_ins_apply_diag_fee(database, system_settings, ins_apply_key, diag_code):
    sql = f"""
        SELECT * FROM insapply
        WHERE
            InsApplyKey = {ins_apply_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return

    row = rows[0]
    diag_fee = get_ins_diag_fee(database, system_settings, 0, diag_code)
    diag_fee = get_markup_diag_fee(database, row, diag_fee)

    ins_total_fee = row["InsTotalFee"] - row["DiagFee"] + diag_fee
    ins_apply_fee = row["InsApplyFee"] - row["DiagFee"] + diag_fee

    fields = ["DiagCode", "DiagFee", "InsTotalFee", "InsApplyFee"]
    data = [
        diag_code,
        diag_fee,
        ins_total_fee,
        ins_apply_fee,
    ]

    database.update_record("insapply", fields, "InsApplyKey", ins_apply_key, data)


def update_treat_fee(database, ins_apply_key, course, treat_percent):
    sql = f"""
        SELECT * FROM insapply
        WHERE
            InsApplyKey = {ins_apply_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return

    row = rows[0]
    treat_fee = row[f"TreatFee{course}"]
    adjusted_treat_fee = round(treat_fee / 100 * treat_percent, 1)

    total_treat_fee = row["TreatFee"] - treat_fee + adjusted_treat_fee
    ins_total_fee = row["InsTotalFee"] - treat_fee + adjusted_treat_fee
    ins_apply_fee = row["InsApplyFee"] - treat_fee + adjusted_treat_fee

    fields = [
        "TreatFee",
        "InsTotalFee",
        "InsApplyFee",
        f"Percent{course}",
        f"TreatFee{course}",
    ]

    data = [
        total_treat_fee,
        ins_total_fee,
        ins_apply_fee,
        treat_percent,
        adjusted_treat_fee,
    ]

    database.update_record("insapply", fields, "InsApplyKey", ins_apply_key, data)


def set_nhi_basic_data(database):
    fields = ["ChargeType", "ItemName", "InsCode", "Amount", "Remark"]
    rows = [
        ("診察費", "<=30人次門診診察費(有護理人員)", "A01", 340, "支援醫師不適用"),
        ("診察費", "<=30人次門診診察費", "A02", 330, None),
        ("診察費", "31-50人次門診診察費(有護理人員)", "A03", 230, "支援醫師不適用"),
        ("診察費", "31-50人次門診診察費", "A04", 220, None),
        ("診察費", "51-70人次門診診察費(有護理人員)", "A05", 160, "支援醫師不適用"),
        ("診察費", "51-70人次門診診察費", "A06", 150, None),
        ("診察費", "71-150人次門診診察費", "A07", 90, None),
        ("診察費", ">150人次門診診察費", "A08", 50, None),
        ("診察費", "山地離島門診診察費(有護理人員)", "A09", 340, None),
        ("診察費", "山地離島門診診察費", "A10", 330, None),
        (
            "診察費",
            "初診門診診察費加計",
            "A90",
            50,
            "2年以上新特約診所: 初診病患或2年內未就診病患",
        ),
        ("藥費", "每日藥費", "A21", 37, "一般案件給藥天數不得超過七日"),
        ("調劑費", "藥師調劑", "A31", 23, "須先報備，經證明核可後申報"),
        ("調劑費", "醫師調劑", "A32", 13, None),
        ("處置費", "針灸治療處置費-另開內服藥", "B41", 227, None),
        ("處置費", "針灸治療處置費", "B42", 227, None),
        ("處置費", "電針治療處置費-另開內服藥", "B43", 227, None),
        ("處置費", "電針治療處置費", "B44", 227, None),
        ("處置費", "複雜性針灸治療處置費-另開內服藥", "B45", 307, None),
        ("處置費", "複雜性針灸治療處置費", "B46", 307, None),
        ("處置費", "傷科治療處置費-另開內服藥", "B53", 227, None),
        (
            "處置費",
            "傷科治療處置費",
            "B54",
            227,
            "標準作業程序: (1)四診八綱辨證(2)診斷(3)理筋手法",
        ),
        ("處置費", "複雜性傷科治療處置費-另開內服藥", "B55", 307, None),
        ("處置費", "複雜性傷科治療處置費", "B56", 307, None),
        (
            "處置費",
            "骨折、脫臼整復第一線復位處置治療費",
            "B57",
            477,
            "B57「骨折、脫臼整復第一線復位處置治療」係指該患者受傷部位初次到醫療院所做接骨、復位之處理治療，且不得與B61併同申報",
        ),
        ("處置費", "脫臼整復費-同療程第一次就醫", "B61", 327, None),
        ("處置費", "脫臼整復費-同療程複診-另開內服藥", "B62", 227, None),
        ("處置費", "脫臼整復費-同療程複診", "B63", 227, None),
        # 2021-03-01 實施
        ("處置費", "一般針灸-另開內服藥", "D01", 227, None),
        ("處置費", "一般針灸", "D02", 227, None),
        ("處置費", "電針-另開內服藥", "D03", 227, None),
        ("處置費", "電針", "D04", 227, None),
        (
            "處置費",
            "中度複雜性針灸-另開內服藥",
            "D05",
            327,
            """支付規範:
                (1)須針灸二個(含)以上部位：頭頸部、軀幹部或四肢，任兩部位或以上。
                (2)須合併以下任一輔助治療：拔罐治療、放血治療、刮痧治療、熱療(含紅外線治療)、艾灸治療、電療或眼部特殊針灸。
                (3)治療時間合計十分鐘以上。""",
        ),
        (
            "處置費",
            "中度複雜性針灸",
            "D06",
            327,
            """支付規範:
                (1)須針灸二個(含)以上部位：頭頸部、軀幹部或四肢，任兩部位或以上。
                (2)須合併以下任一輔助治療：拔罐治療、放血治療、刮痧治療、熱療(含紅外線治療)、艾灸治療、電療或眼部特殊針灸。
                (3)治療時間合計十分鐘以上。""",
        ),
        (
            "處置費",
            "高度複雜性針灸-另開內服藥",
            "D07",
            427,
            """支付規範:
                (1)須針灸二個(含)以上部位：頭頸部、軀幹部或四肢，任兩部位或以上。
                (2)須合併以下任一輔助治療：拔罐治療、放血治療、刮痧治療、熱療(含紅外線治療)、艾灸治療、電療或眼部特殊針灸。
                (3)治療時間合計二十分鐘以上。""",
        ),
        (
            "處置費",
            "高度複雜性針灸",
            "D08",
            427,
            """支付規範:
                (1)須針灸二個(含)以上部位：頭頸部、軀幹部或四肢，任兩部位或以上。
                (2)須合併以下任一輔助治療：拔罐治療、放血治療、刮痧治療、熱療(含紅外線治療)、艾灸治療、電療或眼部特殊針灸。
                (3)治療時間合計二十分鐘以上。""",
        ),
        (
            "處置費",
            "一般傷科-另開內服藥",
            "E01",
            227,
            """標準作業程序:
                (1)四診八綱辨證(2)診斷(3)理筋手法
            適應症:
                (1)急慢性扭、挫、瘀傷: 踝扭傷、腰扭傷、頸部扭傷等。
                (2)肌腱炎: 網球肘、棒球肩、腕部橈側腱鞘炎等。
                      關節病變: 類風濕性關節炎、退化性關節炎、僵直性關節炎、痛風、冰凍肩(凝肩)等。""",
        ),
        (
            "處置費",
            "一般傷科",
            "E02",
            227,
            """標準作業程序:
                (1)四診八綱辨證(2)診斷(3)理筋手法
            適應症:
                (1)急慢性扭、挫、瘀傷: 踝扭傷、腰扭傷、頸部扭傷等。
                (2)肌腱炎: 網球肘、棒球肩、腕部橈側腱鞘炎等。
                      關節病變: 類風濕性關節炎、退化性關節炎、僵直性關節炎、痛風、冰凍肩(凝肩)等。""",
        ),
        (
            "處置費",
            "中度複雜性傷科治療-療程第一次-另開內服藥",
            "E03",
            427,
            """支付規範:
                (1)須合併以下任一輔助治療: 藥薰治療、拔罐治療、刮痧治療、電療、熱療(含紅外線治療)、膏布治療或夾板固定治療。
                (2)治療時間合計十分鐘以上。(3)療程第二次-第六次以一般傷科處置(E01, E02)申報。""",
        ),
        (
            "處置費",
            "中度複雜性傷科治療-療程第一次",
            "E04",
            427,
            """支付規範:
                (1)須合併以下任一輔助治療: 藥薰治療、拔罐治療、刮痧治療、電療、熱療(含紅外線治療)、膏布治療或夾板固定治療。
                (2)治療時間合計十分鐘以上。(3)療程第二次-第六次以一般傷科處置(E01, E02)申報。""",
        ),
        (
            "處置費",
            "高度複雜性傷科治療-多部位損傷-起始次-另開內服藥",
            "E05",
            877,
            """通則:
                1.起始次: 係指該病人受傷部位初次到醫療院所做之處理治療。脫臼整復、骨折之起始次處置，含再次復位、再次接骨。
                2.後續治療處置以一般傷科治療處置(E01, E02)申報。
                3.須合併以下任一輔助治療: 藥薰治療、拔罐治療、刮痧治療、電療、熱療(含紅外線治療)、膏布治療或夾板固定治療。
                4.治療時間合計二十分鐘以上。""",
        ),
        (
            "處置費",
            "高度複雜性傷科治療-多部位損傷-起始次",
            "E06",
            877,
            """通則:
                1.起始次: 係指該病人受傷部位初次到醫療院所做之處理治療。脫臼整復、骨折之起始次處置，含再次復位、再次接骨。
                2.後續治療處置以一般傷科治療處置(E01, E02)申報。
                3.須合併以下任一輔助治療: 藥薰治療、拔罐治療、刮痧治療、電療、熱療(含紅外線治療)、膏布治療或夾板固定治療。
                4.治療時間合計二十分鐘以上。""",
        ),
        (
            "處置費",
            "中度複雜性傷科合併特殊疾病-起始次-另開內服藥",
            "E07",
            877,
            """通則:
                1.起始次: 係指該病人受傷部位初次到醫療院所做之處理治療。脫臼整復、骨折之起始次處置，含再次復位、再次接骨。
                2.後續治療處置以一般傷科治療處置(E01, E02)申報。
                3.須合併以下任一輔助治療: 藥薰治療、拔罐治療、刮痧治療、電療、熱療(含紅外線治療)、膏布治療或夾板固定治療。
                4.治療時間合計二十分鐘以上。""",
        ),
        (
            "處置費",
            "中度複雜性傷科合併特殊疾病-起始次",
            "E08",
            877,
            """通則:
                1.起始次: 係指該病人受傷部位初次到醫療院所做之處理治療。脫臼整復、骨折之起始次處置，含再次復位、再次接骨。
                2.後續治療處置以一般傷科治療處置(E01, E02)申報。
                3.須合併以下任一輔助治療: 藥薰治療、拔罐治療、刮痧治療、電療、熱療(含紅外線治療)、膏布治療或夾板固定治療。
                4.治療時間合計二十分鐘以上。""",
        ),
        (
            "處置費",
            "脫臼整復復位-起始次-另開內服藥",
            "E09",
            1177,
            """通則:
                1.起始次: 係指該病人受傷部位初次到醫療院所做之處理治療。脫臼整復、骨折之起始次處置，含再次復位、再次接骨。
                2.後續治療處置以一般傷科治療處置(E01, E02)申報。
                3.須合併以下任一輔助治療: 藥薰治療、拔罐治療、刮痧治療、電療、熱療(含紅外線治療)、膏布治療或夾板固定治療。
                4.治療時間合計二十分鐘以上。""",
        ),
        (
            "處置費",
            "脫臼整復復位-起始次",
            "E10",
            1177,
            """通則:
                1.起始次: 係指該病人受傷部位初次到醫療院所做之處理治療。脫臼整復、骨折之起始次處置，含再次復位、再次接骨。
                2.後續治療處置以一般傷科治療處置(E01, E02)申報。
                3.須合併以下任一輔助治療: 藥薰治療、拔罐治療、刮痧治療、電療、熱療(含紅外線治療)、膏布治療或夾板固定治療。
                4.治療時間合計二十分鐘以上。""",
        ),
        (
            "處置費",
            "骨折復位-起始次-另開內服藥",
            "E11",
            1277,
            """通則:
                1.起始次: 係指該病人受傷部位初次到醫療院所做之處理治療。脫臼整復、骨折之起始次處置，含再次復位、再次接骨。
                2.後續治療處置以一般傷科治療處置(E01, E02)申報。
                3.須合併以下任一輔助治療: 藥薰治療、拔罐治療、刮痧治療、電療、熱療(含紅外線治療)、膏布治療或夾板固定治療。
                4.治療時間合計二十分鐘以上。""",
        ),
        (
            "處置費",
            "骨折復位-起始次",
            "E12",
            1277,
            """通則:
                1.起始次: 係指該病人受傷部位初次到醫療院所做之處理治療。脫臼整復、骨折之起始次處置，含再次復位、再次接骨。
                2.後續治療處置以一般傷科治療處置(E01, E02)申報。
                3.須合併以下任一輔助治療: 藥薰治療、拔罐治療、刮痧治療、電療、熱療(含紅外線治療)、膏布治療或夾板固定治療。
                4.治療時間合計二十分鐘以上。""",
        ),
        ("處置費", "中度針灸合併中度傷科-療程首次", "F37", 427, None),
        ("處置費", "中度針灸合併中度傷科-療程2-6次開藥", "F38", 327, None),
        ("處置費", "中度針灸合併中度傷科-療程2-6次未開藥", "F39", 327, None),
        ("處置費", "中度針灸合併高度傷科-療程首次", "F40", 877, None),
        ("處置費", "中度針灸合併高度傷科-療程2-6次開藥", "F41", 327, None),
        ("處置費", "中度針灸合併高度傷科-療程2-6次未開藥", "F42", 327, None),
        ("處置費", "高度針灸合併中度傷科-療程首次", "F54", 427, None),
        ("處置費", "高度針灸合併中度傷科-療程2-6次開藥", "F55", 427, None),
        ("處置費", "高度針灸合併中度傷科-療程2-6次未開藥", "F56", 427, None),
        ("處置費", "高度針灸合併高度傷科-療程首次", "F57", 877, None),
        ("處置費", "高度針灸合併高度傷科-療程2-6次開藥", "F58", 427, None),
        ("處置費", "高度針灸合併高度傷科-療程2-6次未開藥", "F59", 427, None),
        (
            "照護費",
            "小兒氣喘照護處置費(含氣霧吸入處置費)",
            "C01",
            1500,
            "照護處置費包括中醫四診診察費、口服藥(不得少於五天)、針灸治療處置費、穴位推拿按摩、穴位敷貼處置費、氣霧吸入處置費",
        ),
        (
            "照護費",
            "小兒氣喘照護處置費",
            "C02",
            1400,
            "照護處置費包括中醫四診診察費、口服藥(不得少於五天)、針灸治療處置費、穴位推拿按摩、穴位敷貼處置費",
        ),
        (
            "照護費",
            "小兒腦性麻痺照護處置費(含藥浴處置費)",
            "C03",
            1500,
            "照護處置費包括中醫四診診察費、口服藥(不得少於五天)、頭皮針及體針半刺治療處置費、穴位推拿按摩、督脈及神闕藥灸、藥浴處置費",
        ),
        (
            "照護費",
            "小兒腦性麻痺照護處置費",
            "C04",
            1400,
            "照護處置費包括中醫四診診察費、口服藥(不得少於五天)、頭皮針及體針半刺治療處置費、穴位推拿按摩、督脈及神闕藥灸",
        ),
        (
            "照護費",
            "腦血管疾病、顱腦損傷及脊髓損傷照護處置費(治療處置1-3次)",
            "C05",
            2000,
            "每月限申報一次，照護處置費包括中醫醫療診察費、同時執行針灸治療及傷科治療。首次收案即需進行衛教及巴氏量表，之後每三個月至少施行衛教及評估巴氏量表一次",
        ),
        (
            "照護費",
            "腦血管疾病、顱腦損傷及脊髓損傷照護處置費(治療處置4-6次)",
            "C06",
            3500,
            "每月限申報一次，照護處置費包括中醫醫療診察費、同時執行針灸治療及傷科治療。首次收案即需進行衛教及巴氏量表，之後每三個月至少施行衛教及評估巴氏量表一次",
        ),
        (
            "照護費",
            "腦血管疾病、顱腦損傷及脊髓損傷照護處置費(治療處置7-9次)",
            "C07",
            5500,
            "每月限申報一次，照護處置費包括中醫醫療診察費、同時執行針灸治療及傷科治療。首次收案即需進行衛教及巴氏量表，之後每三個月至少施行衛教及評估巴氏量表一次",
        ),
        (
            "照護費",
            "腦血管疾病、顱腦損傷及脊髓損傷照護處置費(治療處置10-12次)",
            "C08",
            7500,
            "每月限申報一次，照護處置費包括中醫醫療診察費、同時執行針灸治療及傷科治療。首次收案即需進行衛教及巴氏量表，之後每三個月至少施行衛教及評估巴氏量表一次",
        ),
        (
            "照護費",
            "腦血管疾病、顱腦損傷及脊髓損傷照護處置費(治療處置>=13次)",
            "C09",
            9500,
            "每月限申報一次，照護處置費包括中醫醫療診察費、同時執行針灸治療及傷科治療。首次收案即需進行衛教及巴氏量表，之後每三個月至少施行衛教及評估巴氏量表一次",
        ),
        (
            "照護費",
            "中醫助孕照護處置費(含針灸處置)",
            "P39001",
            1200,
            "包括中醫四診診察費，估排卵期評估，女性須含基礎體溫(BBT)、體質證型、濾泡期、排卵期、黃體期之月經週期療法之診療、口服藥(至少七天)、針灸治療處置費、衛教、營養飲食指導，單次門診須全部執行方能申請本項點數。",
        ),
        (
            "照護費",
            "中醫助孕照護處置費(不含針灸處置)",
            "P39002",
            900,
            "包括中醫四診診察費，估排卵期評估，女性須含基礎體溫(BBT)、體質證型、濾泡期、排卵期、黃體期之月經週期療法之診療、口服藥(至少七天)、衛教、營養飲食指導，單次門診須全部執行方能申請本項點數。",
        ),
        (
            "照護費",
            "中醫保胎照護處置費(含針灸處置)",
            "P39003",
            1200,
            "中醫四診診察費口服藥(至少七天)、針灸治療處置費、衛教、營養飲食指導，單次門診須全部執行方能申請本項點數。",
        ),
        (
            "照護費",
            "中醫保胎照護處置費(不含針灸處置)",
            "P39004",
            900,
            "中醫四診診察費口服藥(至少七天)、衛教、營養飲食指導，單次門診須全部執行方能申請本項點數。",
        ),
        (
            "照護費",
            "中醫助孕照護處置費(不含藥費)(同療程第1次)",
            "P39005",
            900,
            "中醫四診診察費[排卵期評估、女性須含基礎體溫(BBT)、濾泡期、排卵期、黃體期之月經週期療法之診療]、針灸治療處置費、衛教、營養飲食指導，單次門診須全部執行方能申請本項點數。",
        ),
        (
            "照護費",
            "中醫保胎照護處置費(不含藥費)(同療程第1次)",
            "P39006",
            900,
            "中醫四診診察費[排卵期評估、女性須含基礎體溫(BBT)、濾泡期、排卵期、黃體期之月經週期療法之診療]、針灸治療處置費、衛教、營養飲食指導，單次門診須全部執行方能申請本項點數。",
        ),
        (
            "照護費",
            "中醫助孕照護針灸處置費(不含藥費)(同療程第2-6次)",
            "P39007",
            300,
            "限與P39005合併申報、每週限申報3次。",
        ),
        (
            "照護費",
            "中醫保胎照護針灸處置費(不含藥費)(同療程第2-6次)",
            "P39008",
            300,
            "限與P39006合併申報、每週限申報3次。",
        ),
        (
            "照護費",
            "兒童過敏性鼻炎管理照護費",
            "P58005",
            200,
            "本項包含中醫護理衛教、營養飲食指導及經穴按摩指導，各項目皆須執行並於病歷詳細記載，方可申報費用。",
        ),
        (
            "照護費",
            "特定癌症門診加強照護費(給藥日數7天以下)",
            "P56001",
            700,
            "包含中醫輔助醫療診察費、口服藥",
        ),
        (
            "照護費",
            "特定癌症門診加強照護費(給藥日數8-14天)",
            "P56002",
            1050,
            "包含中醫輔助醫療診察費、口服藥",
        ),
        (
            "照護費",
            "特定癌症門診加強照護費(給藥日數15-21天)",
            "P56003",
            1400,
            "包含中醫輔助醫療診察費、口服藥",
        ),
        (
            "照護費",
            "特定癌症門診加強照護費(給藥日數22-28天)",
            "P56004",
            1750,
            "包含中醫輔助醫療診察費、口服藥",
        ),
        (
            "照護費",
            "特定癌症針灸或傷科治療處置費",
            "P56005",
            400,
            "本項處置費每月申報上限為 12 次，超出部分支付點數以零計。",
        ),
        (
            "照護費",
            "疾病管理照護費",
            "P56006",
            550,
            "1.包含中醫護理衛教及營養飲食指導。2.限三個月申報一次，申報此項目者，須參考衛教表單(如附件三)提供照護指導，並應併入病患之病歷紀錄備查。",
        ),
        (
            "照護費",
            "生理評估費",
            "P56007",
            1000,
            "1.癌症治療功能性評估：一般性量表 2.生活品質評估。前測(收案三日內)及後測(收案三個月內)量表皆完成，方可申請給付。限三個月申報一次，並於病歷詳細載明評估結果。",
        ),
        (
            "照護費",
            "中醫慢性腎臟病加強照護費（給藥日數 7 天以下）",
            "P64001",
            900,
            "1.包括中醫醫療四診診察費、口服藥費、調劑費、穴位按摩指導。2.第一次就診須檢附相關檢查數據，應併入病患病歷記錄備查。",
        ),
        (
            "照護費",
            "中醫慢性腎臟病加強照護費（給藥日數 8-14 天）",
            "P64002",
            1250,
            "1.包括中醫醫療四診診察費、口服藥費、調劑費、穴位按摩指導。2.第一次就診須檢附相關檢查數據，應併入病患病歷記錄備查。",
        ),
        (
            "照護費",
            "中醫慢性腎臟病加強照護費（給藥日數 15-21 天）",
            "P64003",
            1600,
            "1.包括中醫醫療四診診察費、口服藥費、調劑費、穴位按摩指導。2.第一次就診須檢附相關檢查數據，應併入病患病歷記錄備查。",
        ),
        (
            "照護費",
            "中醫慢性腎臟病加強照護費（給藥日數 22-28 天）",
            "P64004",
            1950,
            "1.包括中醫醫療四診診察費、口服藥費、調劑費、穴位按摩指導。2.第一次就診須檢附相關檢查數據，應併入病患病歷記錄備查。",
        ),
        (
            "照護費",
            "中醫慢性腎臟病加強照護費（給藥日數 7 天以下、針灸處置）",
            "P64005",
            1300,
            "1.包括中醫醫療四診診察費、口服藥費、調劑費、針灸處置費、穴位按摩指導。2.第一次就診須檢附相關檢查數據，應併入病患病歷記錄備查。",
        ),
        (
            "照護費",
            "中醫慢性腎臟病加強照護費（給藥日數 8-14 天、針灸處置）",
            "P64006",
            1650,
            "1.包括中醫醫療四診診察費、口服藥費、調劑費、針灸處置費、穴位按摩指導。2.第一次就診須檢附相關檢查數據，應併入病患病歷記錄備查。",
        ),
        (
            "照護費",
            "中醫慢性腎臟病加強照護費（給藥日數 15-21 天、針灸處置）",
            "P64007",
            2000,
            "1.包括中醫醫療四診診察費、口服藥費、調劑費、針灸處置費、穴位按摩指導。2.第一次就診須檢附相關檢查數據，應併入病患病歷記錄備查。",
        ),
        (
            "照護費",
            "中醫慢性腎臟病加強照護費（給藥日數 22-28 天、針灸處置）",
            "P64008",
            2350,
            "1.包括中醫醫療四診診察費、口服藥費、調劑費、針灸處置費、穴位按摩指導。2.第一次就診須檢附相關檢查數據，應併入病患病歷記錄備查。",
        ),
        (
            "照護費",
            "中醫慢性腎臟病加強照護費（未給口服藥、針灸處置同療程第1次）",
            "P64009",
            800,
            "1.包括中醫醫療四診診察費、針灸處置費、穴位按摩指導。2.第一次就診須檢附相關檢查數據，應併入病患病歷記錄備查。",
        ),
        (
            "照護費",
            "中醫慢性腎臟病針灸照護費（同療程第 2~6 次）",
            "P64010",
            300,
            "1.限與 P64009 合併申報；同次療程結束後統一申報。2.P64009 及 P64010 每週限申報3次。",
        ),
        ("照護費", "醣化血紅素 HbA1C", "09006C", 200, None),
        ("照護費", "肌酐 、血 Creatinine (B) CRTN", "09015C", 40, None),
        ("照護費", "低密度脂蛋白－膽固醇 LDL-C", "09044C", 250, None),
        ("照護費", "尿蛋白與尿液肌酸酐比值 UPCR", "P64013", 55, None),
        ("照護費", "尿微蛋白與尿液肌酸酐比值 UACR", "P64014", 80, None),
        (
            "照護費",
            "疾病管理照護費",
            "P64011",
            500,
            """
            1.中醫衛教、營養飲食指導、運動指導及檢查數據記載(雲端查詢)。
            2.須檢附相關檢查數據：
                CKD stage 2 病人後續每6個月須重新檢附於病歷；
                CKD stage 3~4 病人後續每3個月須重新檢附 於病歷；
                CKD stage 5 病人後續每個月須重新檢附於病歷。
            3.限 60 天申報一次。""",
        ),
        (
            "照護費",
            "中醫慢性腎臟病治療功能性評估",
            "P64012",
            700,
            """
            註 1：每一個案限每 6 個月申報一次費用(每次須同時完成各項所列之量表)
            註 2：需有病人新收案或前一次功能性評估之量表及檢驗檢查，且已於 VPN 登錄者，使得申報本項。
            註 3：申報 2 次加強照護費及 1 次疾病管理照護費後，始得申報 本項。""",
        ),
        (
            "診察費",
            "居家醫療訪視費",
            "P5408C",
            1553,
            "中醫師訪視費所訂點數含診察(含傷科指導)、處方、護理、電子資料處理及行政作業成本等。",
        ),
        (
            "診察費",
            "山地離島地區中醫師訪視費(次)",
            "P5409C",
            1709,
            "中醫師訪視費所訂點數含診察(含傷科指導)、處方、護理、電子資料處理及行政作業成本等。",
        ),
    ]

    for row in rows:
        database.insert_record("charge_settings", fields, row)


def set_diag_share_basic_data(database):
    fields = [
        "ChargeType",
        "ItemName",
        "ShareType",
        "TreatType",
        "Course",
        "InsCode",
        "Amount",
        "Remark",
    ]
    rows = [
        ("門診負擔", "一般內科", "基層醫療", "內科", "首次", "S10", 50, None),
        ("門診負擔", "一般傷科首次", "基層醫療", "傷科治療", "首次", "S10", 50, None),
        ("門診負擔", "一般傷科療程", "基層醫療", "傷科治療", "療程", "S10", 50, None),
        ("門診負擔", "一般針灸首次", "基層醫療", "針灸治療", "首次", "S10", 50, None),
        ("門診負擔", "一般針灸療程", "基層醫療", "針灸治療", "療程", "009", 0, None),
        ("門診負擔", "重大傷病內科", "重大傷病", "內科", "首次", "001", 0, None),
        (
            "門診負擔",
            "重大傷病傷科首次",
            "重大傷病",
            "傷科治療",
            "首次",
            "001",
            0,
            None,
        ),
        (
            "門診負擔",
            "重大傷病傷科療程",
            "重大傷病",
            "傷科治療",
            "療程",
            "001",
            0,
            None,
        ),
        (
            "門診負擔",
            "重大傷病針灸首次",
            "重大傷病",
            "針灸治療",
            "首次",
            "001",
            0,
            None,
        ),
        (
            "門診負擔",
            "重大傷病針灸療程",
            "重大傷病",
            "針灸治療",
            "療程",
            "001",
            0,
            None,
        ),
        ("門診負擔", "低收入戶內科", "低收入戶", "內科", "首次", "003", 0, None),
        (
            "門診負擔",
            "低收入戶傷科首次",
            "低收入戶",
            "傷科治療",
            "首次",
            "003",
            0,
            None,
        ),
        (
            "門診負擔",
            "低收入戶傷科療程",
            "低收入戶",
            "傷科治療",
            "療程",
            "003",
            0,
            None,
        ),
        (
            "門診負擔",
            "低收入戶針灸首次",
            "低收入戶",
            "針灸治療",
            "首次",
            "003",
            0,
            None,
        ),
        (
            "門診負擔",
            "低收入戶針灸療程",
            "低收入戶",
            "針灸治療",
            "療程",
            "003",
            0,
            None,
        ),
        ("門診負擔", "榮民內科", "榮民", "內科", "首次", "004", 0, None),
        ("門診負擔", "榮民傷科首次", "榮民", "傷科治療", "首次", "004", 0, None),
        ("門診負擔", "榮民傷科療程", "榮民", "傷科治療", "療程", "004", 0, None),
        ("門診負擔", "榮民針灸首次", "榮民", "針灸治療", "首次", "004", 0, None),
        ("門診負擔", "榮民針灸療程", "榮民", "針灸治療", "療程", "004", 0, None),
        ("門診負擔", "職業傷害內科", "職業傷害", "內科", "首次", "006", 0, None),
        (
            "門診負擔",
            "職業傷害傷科首次",
            "職業傷害",
            "傷科治療",
            "首次",
            "006",
            0,
            None,
        ),
        (
            "門診負擔",
            "職業傷害傷科療程",
            "職業傷害",
            "傷科治療",
            "療程",
            "006",
            0,
            None,
        ),
        (
            "門診負擔",
            "職業傷害針灸首次",
            "職業傷害",
            "針灸治療",
            "首次",
            "006",
            0,
            None,
        ),
        (
            "門診負擔",
            "職業傷害針灸療程",
            "職業傷害",
            "針灸治療",
            "療程",
            "006",
            0,
            None,
        ),
        ("門診負擔", "山地離島內科", "山地離島", "內科", "首次", "007", 0, None),
        (
            "門診負擔",
            "山地離島傷科首次",
            "山地離島",
            "傷科治療",
            "首次",
            "007",
            0,
            None,
        ),
        (
            "門診負擔",
            "山地離島傷科療程",
            "山地離島",
            "傷科治療",
            "療程",
            "007",
            0,
            None,
        ),
        (
            "門診負擔",
            "山地離島針灸首次",
            "山地離島",
            "針灸治療",
            "首次",
            "007",
            0,
            None,
        ),
        (
            "門診負擔",
            "山地離島針灸療程",
            "山地離島",
            "針灸治療",
            "療程",
            "007",
            0,
            None,
        ),
        ("門診負擔", "三歲兒童內科", "三歲兒童", "內科", "首次", "902", 0, None),
        (
            "門診負擔",
            "三歲兒童傷科首次",
            "三歲兒童",
            "傷科治療",
            "首次",
            "902",
            0,
            None,
        ),
        (
            "門診負擔",
            "三歲兒童傷科療程",
            "三歲兒童",
            "傷科治療",
            "療程",
            "902",
            0,
            None,
        ),
        (
            "門診負擔",
            "三歲兒童針灸首次",
            "三歲兒童",
            "針灸治療",
            "首次",
            "902",
            0,
            None,
        ),
        (
            "門診負擔",
            "三歲兒童針灸療程",
            "三歲兒童",
            "針灸治療",
            "療程",
            "902",
            0,
            None,
        ),
        ("門診負擔", "新生兒內科", "新生兒", "內科", "首次", "903", 0, None),
        ("門診負擔", "新生兒傷科首次", "新生兒", "傷科治療", "首次", "903", 0, None),
        ("門診負擔", "新生兒傷科療程", "新生兒", "傷科治療", "療程", "903", 0, None),
        ("門診負擔", "新生兒針灸首次", "新生兒", "針灸治療", "首次", "903", 0, None),
        ("門診負擔", "新生兒針灸療程", "新生兒", "針灸治療", "療程", "903", 0, None),
        ("門診負擔", "愛滋病內科", "愛滋病", "內科", "首次", "904", 0, None),
        ("門診負擔", "愛滋病傷科首次", "愛滋病", "傷科治療", "首次", "904", 0, None),
        ("門診負擔", "愛滋病傷科療程", "愛滋病", "傷科治療", "療程", "904", 0, None),
        ("門診負擔", "愛滋病針灸首次", "愛滋病", "針灸治療", "首次", "904", 0, None),
        ("門診負擔", "愛滋病針灸療程", "愛滋病", "針灸治療", "療程", "904", 0, None),
        ("門診負擔", "替代役男內科", "替代役男", "內科", "首次", "906", 0, None),
        (
            "門診負擔",
            "替代役男傷科首次",
            "替代役男",
            "傷科治療",
            "首次",
            "906",
            0,
            None,
        ),
        (
            "門診負擔",
            "替代役男傷科療程",
            "替代役男",
            "傷科治療",
            "療程",
            "906",
            0,
            None,
        ),
        (
            "門診負擔",
            "替代役男針灸首次",
            "替代役男",
            "針灸治療",
            "首次",
            "906",
            0,
            None,
        ),
        (
            "門診負擔",
            "替代役男針灸療程",
            "替代役男",
            "針灸治療",
            "療程",
            "906",
            0,
            None,
        ),
    ]
    for row in rows:
        database.insert_record("charge_settings", fields, row)


def set_drug_share_basic_data(database):
    fields = ["ChargeType", "ItemName", "ShareType", "InsCode", "Amount", "Remark"]
    rows = [
        ("藥品負擔", "藥費100點以下", "基層醫療", "S10", 0, "<=100"),
        ("藥品負擔", "藥費101-200", "基層醫療", "S20", 20, "<=200"),
        ("藥品負擔", "藥費201-300", "基層醫療", "S20", 40, "<=300"),
        ("藥品負擔", "藥費301-400", "基層醫療", "S20", 60, "<=400"),
        ("藥品負擔", "藥費401-500", "基層醫療", "S20", 80, "<=500"),
        ("藥品負擔", "藥費501-600", "基層醫療", "S20", 100, "<=600"),
        ("藥品負擔", "藥費601-700", "基層醫療", "S20", 120, "<=700"),
        ("藥品負擔", "藥費701-800", "基層醫療", "S20", 140, "<=800"),
        ("藥品負擔", "藥費801-900", "基層醫療", "S20", 160, "<=900"),
        ("藥品負擔", "藥費901-1000", "基層醫療", "S20", 180, "<=1000"),
        ("藥品負擔", "藥費1000以上", "基層醫療", "S20", 200, ">1000"),
        ("藥品負擔", "重大傷病", "重大傷病", "001", 0, None),
        ("藥品負擔", "低收入戶", "低收入戶", "003", 0, None),
        ("藥品負擔", "榮民", "榮民", "004", 0, None),
        ("藥品負擔", "職業傷害", "職業傷害", "006", 0, None),
        ("藥品負擔", "山地離島", "山地離島", "007", 0, None),
        (
            "藥品負擔",
            "其他免部份負擔",
            "其他免部份負擔",
            "009",
            0,
            "針灸療程2-6次, 百歲人瑞, 921震災",
        ),
        ("藥品負擔", "三歲以下兒童", "三歲兒童", "902", 0, None),
        ("藥品負擔", "新生兒依附", "新生兒", "903", 0, None),
        ("藥品負擔", "愛滋病", "愛滋病", "904", 0, None),
        ("藥品負擔", "替代役男", "替代役男", "906", 0, None),
    ]
    for row in rows:
        database.insert_record("charge_settings", fields, row)


def set_regist_fee_basic_data(database):
    fields = [
        "ChargeType",
        "ItemName",
        "InsType",
        "ShareType",
        "TreatType",
        "Course",
        "Amount",
        "Remark",
    ]
    rows = [
        ("掛號費", "基本掛號費", "健保", "不分類", "不分類", "首次", 100, None),
        ("掛號費", "基本掛號費", "自費", "不分類", "不分類", "首次", 50, None),
        ("掛號費", "欠卡費", "健保", "不分類", "不分類", "首次", 500, None),
        ("掛號費", "內科掛號費", "健保", "基層醫療", "內科", "首次", 100, None),
        ("掛號費", "傷科首次掛號費", "健保", "基層醫療", "傷科治療", "首次", 100, None),
        ("掛號費", "傷科療程掛號費", "健保", "基層醫療", "傷科治療", "療程", 100, None),
        ("掛號費", "針灸首次掛號費", "健保", "基層醫療", "針灸治療", "首次", 100, None),
        ("掛號費", "針灸療程掛號費", "健保", "基層醫療", "針灸治療", "療程", 150, None),
        ("掛號費", "榮民內科掛號費", "健保", "榮民", "內科", "首次", 0, None),
        ("掛號費", "榮民傷科首次掛號費", "健保", "榮民", "傷科治療", "首次", 0, None),
        ("掛號費", "榮民傷科療程掛號費", "健保", "榮民", "傷科治療", "療程", 0, None),
        ("掛號費", "榮民針灸首次掛號費", "健保", "榮民", "針灸治療", "首次", 0, None),
        ("掛號費", "榮民針灸療程掛號費", "健保", "榮民", "針灸治療", "療程", 0, None),
        ("掛號費", "低收入戶內科掛號費", "健保", "低收入戶", "內科", "首次", 0, None),
        (
            "掛號費",
            "低收入戶傷科首次掛號費",
            "健保",
            "低收入戶",
            "傷科治療",
            "首次",
            0,
            None,
        ),
        (
            "掛號費",
            "低收入戶傷科療程掛號費",
            "健保",
            "低收入戶",
            "傷科治療",
            "療程",
            0,
            None,
        ),
        (
            "掛號費",
            "低收入戶針灸首次掛號費",
            "健保",
            "低收入戶",
            "針灸治療",
            "首次",
            0,
            None,
        ),
        (
            "掛號費",
            "低收入戶針灸療程掛號費",
            "健保",
            "低收入戶",
            "針灸治療",
            "療程",
            0,
            None,
        ),
    ]
    for row in rows:
        database.insert_record("charge_settings", fields, row)


def set_discount_basic_data(database):
    fields = [
        "ChargeType",
        "ItemName",
        "InsType",
        "ShareType",
        "TreatType",
        "Amount",
        "Remark",
    ]
    rows = [
        ("掛號費優待", "年長病患", None, None, None, 0, None),
        ("掛號費優待", "殘障病患", None, None, None, 0, None),
        ("掛號費優待", "本院員工", None, None, None, 0, None),
        ("掛號費優待", "其他優待", None, None, None, 0, None),
    ]

    for row in rows:
        database.insert_record("charge_settings", fields, row)


def set_self_fee_basic_data(database):
    fields = ["ChargeType", "ItemName", "InsType", "Amount", "Remark"]
    rows = [
        ("自費", "民俗調理費", "健保", 0, None),
        ("自費", "民俗調理費", "自費", 0, None),
        ("自費", "代煎費", "自費", 30, "每一帖水藥的代煎費用"),
        ("自費", "自費水藥", "自費", 0, "每一帖水藥的費用"),
        ("自費", "自費粉藥", "自費", 0, "每日的單複方費用"),
    ]
    for row in rows:
        database.insert_record("charge_settings", fields, row)


def set_self_fee_certificate_data(database):
    fields = ["ChargeType", "ItemName", "InsType", "Amount", "Remark"]
    rows = [
        ("證明書費", "診斷證明書費", "自費", 100, "開立診斷證明書費用"),
        ("證明書費", "醫療費用證明書費", "自費", 100, "開立醫療費用證明書費用"),
    ]
    for row in rows:
        database.insert_record("charge_settings", fields, row)


def set_self_fee_tri_heat_data(database):
    fields = ["ChargeType", "ItemName", "InsType", "Amount", "Remark"]
    rows = [
        ("自費", "三伏貼", "不分類", 300, "三伏貼費用"),
        ("自費", "三九貼", "不分類", 300, "三九貼費用"),
    ]
    for row in rows:
        database.insert_record("charge_settings", fields, row)


def set_herb_fee_basic_data(database):
    fields = ["ChargeType", "ItemName", "Amount", "Remark"]
    rows = [
        ("自費水藥", "0-30", 150, "30錢以下 150元/帖"),
        ("自費水藥", "31-50", 200, "31-40錢 200元/帖"),
        ("自費水藥", "51-60", 230, "51-60錢 230元/帖"),
        ("自費水藥", "61-70", 260, "61-70錢 260元/帖"),
        ("自費水藥", "71-80", 290, "71-80錢 290元/帖"),
        ("自費水藥", "81-90", 320, "81-90錢 320元/帖"),
        ("自費水藥", "91-100", 350, "91-100錢 350元/帖"),
        ("自費水藥", "101-110", 380, "101-110錢 380元/帖"),
        ("自費水藥", "111-120", 410, "111-120錢 410元/帖"),
        ("自費水藥", "121-130", 440, "121-130錢 440元/帖"),
        ("自費水藥", "131-140", 470, "131-140錢 470元/帖"),
        ("自費水藥", "141-150", 500, "141-150錢 500元/帖"),
    ]
    for row in rows:
        database.insert_record("charge_settings", fields, row)


def get_table_widget_item_fee(table_widget, row_no, col_no, reset_fee=False):
    fee = table_widget.item(row_no, col_no)
    try:
        if fee is not None:
            fee = number_utils.get_float(fee.text())
        else:
            fee = 0.0
    except ValueError:
        fee = 0.0

    if reset_fee:
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, fee)
        table_widget.setItem(row_no, col_no, item)

    return fee


# 取得抽成率 2019.05.28
def get_commission_rate(
    database,
    medicine_key,
    name,
    treat_type=None,
    doctor=None,
    only_doctor=True,
    medicine_name=None,
):
    if medicine_name in ["自費粉藥", "自費水藥"]:
        sql = f'''
            SELECT * FROM charge_settings
            WHERE
                ChargeType = "自費" AND
                ItemName = "{medicine_name}{name}抽成率"
        '''
        rows = database.select_record(sql)
        if len(rows) > 0:
            commission_rate = f"{number_utils.get_integer(rows[0]['Amount'])}%"
            return commission_rate

    commission_rate = ""
    if medicine_key in [None, ""]:
        return commission_rate

    treat_type_condition = ""
    # if treat_type is not None and '櫃台' not in name:
    #     treat_type_condition = f' AND Remark = "{treat_type}"'

    if doctor is not None:
        sql = f'''
            SELECT * FROM commission
            WHERE
                MedicineKey = {medicine_key} AND
                Name = "{doctor}"
                {treat_type_condition}
        '''
        rows = database.select_record(sql)

        if len(rows) > 0:
            commission_rate = string_utils.xstr(rows[0]["Commission"])
            if commission_rate != "":
                return commission_rate

    sql = f'''
        SELECT * FROM commission
        WHERE
            MedicineKey = {medicine_key} AND
            Name = "{name}"
            {treat_type_condition}
    '''
    rows = database.select_record(sql)

    if len(rows) > 0:
        commission_rate = string_utils.xstr(rows[0]["Commission"])
        if commission_rate != "":
            return commission_rate

    if only_doctor and name not in [
        "醫師",
        "醫師分成",
    ]:  # 以下只有醫師才能讀取medicine的醫師抽成
        position = personnel_utils.get_person_field_value(database, name, "Position")
        if position not in ["醫師", "支援醫師"]:
            return ""

    sql = f"""
        SELECT * FROM medicine
        WHERE
            MedicineKey = {medicine_key}
    """
    rows = database.select_record(sql)

    medicine_type = None
    if len(rows) > 0:
        medicine_type = string_utils.xstr(rows[0]["MedicineType"])
        commission_rate = string_utils.xstr(rows[0]["Commission"])
        if commission_rate != "":
            return commission_rate

    if medicine_type is None:
        return commission_rate

    # ############################## 2025.03.05 新增 ##################################
    sql = f'''
        SELECT * FROM dict_groups
        WHERE
            DictGroupsType = "藥品類別" AND
            DictGroupsName = "{medicine_type}"
    '''
    rows = database.select_record(sql)

    if len(rows) > 0:
        commission_rate = string_utils.xstr(rows[0]["DictGroupsLevel2"])
        if commission_rate != "":
            return f"{commission_rate}%"

    return commission_rate


# 計算抽成 2019.05.28
def calc_commission(quantity, amount, commission_rate):
    if commission_rate is None:
        return None

    if "%" in commission_rate:
        commission_rate = number_utils.get_float(commission_rate.strip("%"))
        commission = amount * commission_rate / 100
    else:
        commission_rate = number_utils.get_float(commission_rate)
        commission = quantity * commission_rate

    commission = number_utils.round_up(commission)

    return commission


# 計算折扣
def get_discount_fee(system_settings, self_total_fee, discount_rate):
    if discount_rate < 0:
        return 0

    if system_settings.field("無折扣批價計算") == "Y":
        pass
    else:
        if discount_rate == 100:
            return 0

    rounded_type = system_settings.field("自費折扣進位")
    remainder_type = system_settings.field("自費折扣尾數")

    if rounded_type == "無條件進位":
        if discount_rate == 100:  # 判斷是否要無條件進位或捨去
            if (
                remainder_type == "尾數為0"
                and self_total_fee % 10 == 0
                or self_total_fee % 10 == 0
                or self_total_fee % 5 == 0
            ):
                return 0

    discount_fee = number_utils.get_integer(
        self_total_fee - (self_total_fee * discount_rate / 100)
    )
    total_fee = self_total_fee - discount_fee
    rounded_amount = get_amount(system_settings, total_fee)

    remainder = number_utils.get_integer(total_fee - rounded_amount)
    discount_fee += number_utils.get_integer(remainder)

    return discount_fee


# 計算金額
def get_amount(system_settings, amount):
    if amount == 0:
        return amount

    remainder = amount % 10  # 個位數
    rounded_type = system_settings.field("自費折扣進位")
    remainder_type = system_settings.field("自費折扣尾數")
    rounded_amount = amount

    if rounded_type == "四捨五入":
        rounded_amount = round(amount, -1)
    elif rounded_type == "無條件進位":
        if remainder_type == "尾數為0":
            rounded_amount = amount + (10 - remainder)
        else:  # 尾數為0或5
            if remainder in [0, 5]:  # 尾數剛好, 不用調整
                rounded_amount = amount
            elif remainder < 5:
                rounded_amount = amount + (5 - remainder)
            elif remainder > 5:
                rounded_amount = amount + (10 - remainder)
    elif rounded_type == "無條件捨去":
        if remainder_type == "尾數為0":
            rounded_amount = amount - remainder
        else:
            if remainder in [0, 5]:  # 尾數剛好, 不用調整
                rounded_amount = amount
            elif remainder < 5:
                rounded_amount = amount - remainder
            elif remainder > 5:
                rounded_amount = amount - (remainder - 5)

    return rounded_amount


# 取得自費金額
def get_self_total_fee(database, case_key):
    sql = f"""
        SELECT * FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet >= 2
        ORDER BY MedicineSet, PrescriptKey
    """
    rows = database.select_record(sql)

    self_total_fee = 0
    for row in rows:
        dosage = number_utils.get_float(row["Dosage"])
        price = number_utils.get_float(row["Price"])
        pres_days = case_utils.get_pres_days(database, case_key, row["MedicineSet"])
        if pres_days <= 0:
            pres_days = 1

        amount = dosage * price
        subtotal = get_subtotal_fee(amount, pres_days)
        self_total_fee += subtotal

    return self_total_fee


# 取得病歷某一帖自費金額
def get_medicine_set_fee(database, system_settings, case_key, medicine_set):
    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    if pres_days <= 0:
        pres_days = 1

    sql = f"""
        SELECT Amount FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set} AND
            Amount > 0
    """
    rows = database.select_record(sql)

    self_total_fee = 0
    for row in rows:
        amount = number_utils.get_float(row["Amount"])
        subtotal = get_subtotal_fee(amount, pres_days)
        self_total_fee += subtotal

    self_total_fee = number_utils.round_up(self_total_fee)
    discount_rate = case_utils.get_discount_rate(database, case_key, medicine_set)
    discount_fee = get_discount_fee(system_settings, self_total_fee, discount_rate)

    total_fee = self_total_fee - discount_fee

    return total_fee


def get_traditional_health_care_fee_from_case(database, case_key, ins_type="健保"):
    traditional_health_care_fee = 0

    if ins_type == "自費":
        sql = f"""
            SELECT TotalFee FROM cases
            WHERE
                CaseKey = {case_key} AND
                TreatType = "民俗調理"
        """
        rows = database.select_record(sql)

        if len(rows) > 0:
            traditional_health_care_fee = number_utils.get_integer(rows[0]["TotalFee"])

        return traditional_health_care_fee

    sql = f"""
        SELECT TotalFee FROM cases
        WHERE
            Position1 = "{case_key}"
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        traditional_health_care_fee = number_utils.get_integer(rows[0]["TotalFee"])
    else:
        sql = f"""
            SELECT TotalFee FROM cases
            WHERE
                CaseKey = {case_key} AND
                TreatType = "民俗調理"
        """
        rows = database.select_record(sql)
        if len(rows) > 0:
            traditional_health_care_fee = number_utils.get_integer(rows[0]["TotalFee"])
        else:
            traditional_health_care_fee = 0

    return traditional_health_care_fee


# 取得自費粉藥單日計價最高金額
def get_ins_drug_single_day_maximum_price(database):
    maximum_price = 0

    sql = """
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "自費" AND
            ItemName = "自費粉藥單日計價最高金額" AND
            InsType = "自費"
    """
    rows = database.select_record(sql)
    if len(rows) > 0:
        row = rows[0]
        maximum_price = number_utils.get_integer(row["Amount"])

    return maximum_price


# 取得自費水藥單日計價最低金額
def get_herb_single_day_minimum_price(database):
    minimum_price = 0

    sql = """
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "自費" AND
            ItemName = "自費水藥單日計價最低金額" AND
            InsType = "自費"
    """
    rows = database.select_record(sql)
    if len(rows) > 0:
        row = rows[0]
        minimum_price = number_utils.get_integer(row["Amount"])

    return minimum_price


# 取得自費診察費
def get_self_diag_fee(database):
    self_diag_fee = None

    sql = """
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "自費" AND
            InsType = "自費" AND
            ItemName = "自費診察費"
    """
    rows = database.select_record(sql)
    if len(rows) > 0:
        row = rows[0]
        self_diag_fee = number_utils.get_integer(row["Amount"])

    return self_diag_fee


# 取得收費設定費用
def get_charge_settings_fee(database, charge_type, ins_type, item_name):
    fee = None

    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "{charge_type}" AND
            InsType = "{ins_type}" AND
            ItemName = "{item_name}"
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        row = rows[0]
        fee = number_utils.get_integer(row["Amount"])

    return fee


def get_self_fee_discount_rate(database, item_name):
    if item_name in [None, ""]:
        return None

    discount_rate = None
    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "自費" AND
            InsType = "自費折扣" AND
            ItemName = "{item_name}"
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        row = rows[0]
        discount_rate = number_utils.get_integer(row["Amount"])

    return discount_rate


def get_doctor_period_fee(database, doctor):
    if doctor in [None, ""]:
        return 0

    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ItemName = "開診金" AND
            Remark = "{doctor}"
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        row = rows[0]
        period_fee = number_utils.get_integer(row["Amount"])
    else:
        period_fee = 0

    return period_fee


def get_min_discount_rate(database):
    min_discount_rate = 100

    sql = """
        SELECT * FROM charge_settings
        WHERE
            ItemName = "自費抽成最低抽成率"
    """
    rows = database.select_record(sql)
    if len(rows) > 0:
        row = rows[0]
        min_discount_rate = number_utils.get_integer(row["Amount"])

    return min_discount_rate


def ignore_discount(database):
    ignore = False

    sql = """
        SELECT * FROM charge_settings
        WHERE
            ItemName = "自費抽成有折扣照常計算"
    """
    rows = database.select_record(sql)
    if len(rows) > 0:
        ignore = True

    return ignore


# 取得自費藥品售價倍率 (售價 = 進價 * 倍率)
def get_ratio(database):
    sql = """
        SELECT * FROM charge_settings
        WHERE
            ItemName = "自費藥品售價倍率"
    """
    rows = database.select_record(sql)
    if not rows:
        return None

    ratio = number_utils.get_float(rows[0]["Remark"])

    return ratio


def get_fee_type(database, case_key, medicine_set):
    sql = f"""
        SELECT MedicineType FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set}
        ORDER BY PrescriptKey
        LIMIT 1
    """
    rows = database.select_record(sql)
    if not rows:
        return None

    medicine_type = string_utils.xstr(rows[0]["MedicineType"]).strip()

    field = get_medicine_type_charge_field(database, medicine_type)
    charge_field = get_charge_field(field, medicine_type)

    return charge_field
