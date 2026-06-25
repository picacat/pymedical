# -*- coding: utf-8 -*-

import calendar
import datetime
import html
import json
import re

import lxml
from lxml import etree as ET
from PyQt5 import QtGui, QtWidgets

from libs import (
    case_utils,
    date_utils,
    db_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    personnel_utils,
    prescript_utils,
    string_utils,
    system_utils,
)

INJURY_LIST = [
    "扭傷",
    "拉傷",
    "挫傷",
    "壓傷",
    "壓砸傷",
    "鈍傷",
    "損傷",
    "擦傷",
    "脫臼",
    "脫位",
    "疼痛",
    "關節炎",
    "關節痛",
    "撕裂傷",
    "骨折",
    "叮咬",
    "咬傷",
    "攣縮",
    "破裂",
    "壓迫",
]

SECURITY_XML_DICT = {
    "寫卡時間": "registered_date",
    "健保卡序": "seq_number",
    "院所代號": "clinic_id",
    "安全簽章": "security_signature",
    "安全模組": "sam_id",
    "同日就診": "register_duplicated",
    "上傳時間": "upload_time",
    "資料格式": "upload_type",
    "補卡註記": "treat_after_check",
    "醫令時間": "prescript_sign_time",
    "就醫識別碼": "identification",
}


def create_treat_data_xml_dict():
    security_xml_dict = {
        "registered_date": "",
        "seq_number": "",
        "clinic_id": "",
        "security_signature": "",
        "sam_id": "",
        "register_duplicated": "",
        "upload_time": "",
        "upload_type": "",
        "treat_after_check": "",
        "prescript_sign_time": "",
        "identification": "",
    }

    return security_xml_dict


# 產生xml檔
# treat_after_check: '1'-正常 '2'-補卡
def treat_data_to_xml(treat_data=None):
    treat_data["upload_time"] = ""
    treat_data["upload_type"] = ""
    treat_data["treat_after_check"] = ""
    treat_data["prescript_sign_time"] = ""

    doc = create_security_xml(treat_data)

    return doc


# 產生xml檔
# treat_after_check: '1'-正常 '2'-補卡
def create_security_xml(treat_data=None):
    if treat_data is None:
        treat_data = create_treat_data_xml_dict()

    root = ET.Element("DOCUMENT", content="cshis")
    treat_data_node = ET.SubElement(root, "treat_data")

    field_list = [
        "registered_date",
        "seq_number",
        "clinic_id",
        "security_signature",
        "sam_id",
        "register_duplicated",
        "upload_time",
        "upload_type",
        "treat_after_check",
        "prescript_sign_time",
        "identification",
    ]

    for field_name in field_list:
        xml_field = ET.SubElement(treat_data_node, field_name)
        xml_field.text = treat_data[field_name]

    xml = ET.tostring(root)

    return xml


def get_treat_data_xml_dict(xml_string):
    ic_card_xml = "".join(string_utils.get_str(xml_string, "utf-8"))
    security_xml_dict = create_treat_data_xml_dict()

    try:
        root = ET.fromstring(ic_card_xml)
    except lxml.etree.XMLSyntaxError:
        return None

    doc = root.xpath("//DOCUMENT/treat_data")[0]
    for field in doc:
        field_name = field.tag
        field_value = root.xpath(f"//DOCUMENT/treat_data/{field_name}")[0].text
        security_xml_dict[field_name] = field_value

    return security_xml_dict


# 取出病歷檔安全簽章XML
def extract_security_xml(xml_field, field):
    ic_card_xml = "".join(string_utils.get_str(xml_field, "utf-8"))
    if ic_card_xml in [None, ""]:
        return None

    field_name = SECURITY_XML_DICT[field]
    try:
        root = ET.fromstring(ic_card_xml)
        field_value = root.xpath(f"//DOCUMENT/treat_data/{field_name}")[0].text
    except Exception:
        return None

    return field_value


# 寫入病歷檔安全簽章XML
def update_xml_doc(xml_field, field_name, field_value):
    ic_card_xml = "".join(string_utils.get_str(xml_field, "utf-8"))

    root = ET.fromstring(ic_card_xml)
    root.xpath(f"//DOCUMENT/treat_data/{field_name}")[0].text = field_value

    return ET.tostring(root)


# 寫入病歷檔安全簽章XML
def update_xml(
    database, table_name, field_name, xml_field, field_value, primary_key, key_value
):
    xml_node = f"//{xml_field}"
    xml_value = f"<{xml_field}>{field_value}</{xml_field}>"

    sql = f"""
        UPDATE {table_name}
        SET
            {field_name} = UPDATEXML({field_name}, '{xml_node}', '{xml_value}')
        WHERE
            {primary_key} = {key_value}
    """
    database.exec_sql(sql)


def get_dosage_row(database, case_key, medicine_set=1):
    sql = f"""
        SELECT * FROM dosage
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set}
    """
    rows = database.select_record(sql)

    return rows


def get_doctor_done(database, case_key):
    sql = f"""
        SELECT DoctorDone FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return False

    row = rows[0]
    if row["DoctorDone"] == "True":
        return True
    else:
        return False


def set_pres_days(database, case_key, medicine_set=1, pres_days=0):
    sql = f"""
        SELECT * FROM dosage
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set}
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        sql = f"""
            UPDATE dosage
            SET
                Days = {pres_days}
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = {medicine_set}
        """
        database.exec_sql(sql)
    else:
        fields = ["CaseKey", "MedicineSet", "Days"]
        data = [case_key, medicine_set, pres_days]
        database.insert_record("dosage", fields, data)


def get_pres_days(database, case_key, medicine_set=1):
    if medicine_set is None:
        return 0

    sql = f"""
        SELECT Days FROM dosage
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set}
        LIMIT 1
    """
    try:
        rows = database.select_record(sql)
    except Exception:
        return 0

    if len(rows) > 0:
        pres_days = number_utils.get_integer(rows[0]["Days"])
    else:
        pres_days = 0

    return pres_days


def get_no_pharmacy(database, case_key):
    sql = f"""
        SELECT NoPharmacy FROM dosage
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = 1
        LIMIT 1
    """
    try:
        rows = database.select_record(sql)
    except Exception:
        return 0

    if len(rows) <= 0:
        return "N"

    row = rows[0]

    no_pharmacy = string_utils.xstr(row["NoPharmacy"])

    return no_pharmacy


def get_packages(database, case_key, medicine_set=1):
    if medicine_set is None:
        return 0

    sql = f"""
        SELECT Packages FROM dosage
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set}
        LIMIT 1
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        package = number_utils.get_integer(rows[0]["Packages"])
    else:
        package = 0

    return package


def get_instruction(database, case_key, medicine_set=1):
    sql = f"""
        SELECT Instruction FROM dosage
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set}
        LIMIT 1
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        instruction = string_utils.xstr(rows[0]["Instruction"])
    else:
        instruction = None

    return instruction


def get_dosage_mode(database, case_key, medicine_set=1):
    sql = f"""
        SELECT DosageMode FROM prescript
        WHERE
            CaseKey = {case_key} AND
            DosageMode IS NOT NULL AND LENGTH(DosageMode) > 0 AND
            MedicineSet = {medicine_set}
        LIMIT 1
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        dosage_mode = string_utils.xstr(rows[0]["DosageMode"])
    else:
        dosage_mode = None

    return dosage_mode


def get_discount_rate(database, case_key, medicine_set=1):
    sql = f"""
        SELECT DiscountRate FROM dosage
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set}
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        discount_rate = number_utils.get_integer(rows[0]["DiscountRate"])
    else:
        discount_rate = 100

    return discount_rate


def get_discount_fee(database, case_key, medicine_set=1):
    if case_key in [None, ""]:
        return None

    sql = f"""
        SELECT DiscountFee FROM dosage
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set}
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        discount_fee = number_utils.get_integer(rows[0]["DiscountFee"])
    else:
        discount_fee = None

    return discount_fee


def get_self_total_fee(database, case_key, medicine_set=1):
    sql = f"""
        SELECT SelfTotalFee FROM dosage
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set}
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        self_total_fee = number_utils.get_integer(rows[0]["SelfTotalFee"])
    else:
        self_total_fee = None

    return self_total_fee


def get_case_total_fee(database, case_key):
    sql = f"""
        SELECT TotalFee FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        total_fee = number_utils.get_integer(rows[0]["TotalFee"])
    else:
        total_fee = None

    return total_fee


def get_total_fee(database, case_key, medicine_set=1):
    sql = f"""
        SELECT TotalFee FROM dosage
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set}
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        total_fee = number_utils.get_integer(rows[0]["TotalFee"])
    else:
        total_fee = None

    return total_fee


def get_total_dosage(database, case_key, medicine_set=1):
    sql = f"""
        SELECT TotalDosage FROM dosage
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set}
        LIMIT 1
    """
    try:
        rows = database.select_record(sql)
    except Exception:
        return 0

    if len(rows) > 0:
        total_dosage = number_utils.get_float(rows[0]["TotalDosage"])
    else:
        total_dosage = 0

    return total_dosage


def get_host_pres_days(database, case_key, medicine_set=1):
    if medicine_set >= 4:
        return 0

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)

    return pres_days


def get_host_packages(database, case_key, medicine_set=1):
    if medicine_set >= 4:
        return 0

    sql = f"""
        SELECT Package{medicine_set} FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        package = number_utils.get_integer(rows[0][f"Package{medicine_set}"])
    else:
        package = 0

    return package


def get_host_instruction(database, case_key, medicine_set=1):
    if medicine_set >= 4:
        return None

    sql = f"""
        SELECT Instruction{medicine_set} FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        instruction = string_utils.xstr(rows[0][f"Instruction{medicine_set}"])
    else:
        instruction = None

    return instruction


# 取得病歷html格式
def get_medical_record_html(database, system_settings, case_key, show_separator=True):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]

    if show_separator:
        separator = "<hr>"
    else:
        separator = "<br>"

    case_date = string_utils.xstr(row["CaseDate"].date())
    if system_settings.field("日期格式") == "民國年":
        case_date = date_utils.date_to_zh_tw_date(case_date)

    if row["InsType"] == "健保":
        ins_type = str(row["Card"])
        injury_type = string_utils.xstr(row["Injury"])
        share_type = string_utils.xstr(row["Share"])

        if number_utils.get_integer(row["Continuance"]) >= 1:
            ins_type += "-" + str(row["Continuance"])

        if injury_type == "主訴職災":
            share_type = f'<font color="red">{injury_type}</font>'
        elif share_type == "榮民":
            share_type = f'<font color="green">{share_type}</font>'
        elif share_type in ["低收入戶", "中低收入戶"]:
            share_type = f'<font color="darkMagenta">{share_type}</font>'

        ins_type = f"<b>健保</b>: {ins_type} {share_type[:4]}"
    else:
        ins_type = '<b><font color="blue">自費</font></b>'

    doctor = string_utils.xstr(row["Doctor"])
    total_fee = number_utils.get_integer(row["TotalFee"])
    medical_record = f"<b>日期</b>: {case_date} {ins_type}"
    medical_record += f"<br><b>醫師</b>:{doctor}"

    max_medicine_set = prescript_utils.get_max_medicine_set(database, case_key)
    if row["InsType"] == "健保" and max_medicine_set >= 2:
        medical_record += (
            f' <b><font color="blue">(含自費, 金額: {total_fee})</font></b>'
        )

    medical_record += separator

    symptom = html.escape(string_utils.get_str(row["Symptom"], "utf8"))
    tongue = html.escape(string_utils.get_str(row["Tongue"], "utf8"))
    pulse = html.escape(string_utils.get_str(row["Pulse"], "utf8"))
    distincts = html.escape(string_utils.get_str(row["Distincts"], "utf8"))
    cure = html.escape(string_utils.get_str(row["Cure"], "utf8"))
    remark = string_utils.get_str(row["Remark"], "utf8")
    remark = html.escape(remark).replace("\n", "<br>")

    disease_code1 = string_utils.xstr(row["DiseaseCode1"])
    disease_name1 = string_utils.xstr(row["DiseaseName1"])
    disease_code2 = string_utils.xstr(row["DiseaseCode2"])
    disease_name2 = string_utils.xstr(row["DiseaseName2"])
    disease_code3 = string_utils.xstr(row["DiseaseCode3"])
    disease_name3 = string_utils.xstr(row["DiseaseName3"])
    try:
        disease_code4 = string_utils.xstr(row["DiseaseCode4"])
        disease_name4 = string_utils.xstr(row["DiseaseName4"])
    except Exception:
        disease_code4 = ""
        disease_name4 = ""

    disease_line = ""
    if disease_code1 != "":
        disease_line += f"<b>主診斷</b>:{disease_code1} {disease_name1}"
    if disease_code2 != "":
        disease_line += f"<br><b>次診斷1</b>:{disease_code2} {disease_name2}"
    if disease_code3 != "":
        disease_line += f"<br><b>次診斷2</b>:{disease_code3} {disease_name3}"
    if disease_code4 != "":
        disease_line += f"<br><b>次診斷3</b>:{disease_code4} {disease_name4}"

    if disease_line != "":
        medical_record += disease_line + separator

    if symptom != "":
        medical_record += f"<b>主訴</b>:{symptom}"

    if system_settings.field("過去病歷診察資料只顯示主訴") != "Y":
        if tongue != "":
            medical_record += f"{separator}<b>舌診</b>:{tongue}"
        if pulse != "":
            medical_record += f"{separator}<b>脈象</b>:{pulse}"
        if distincts != "":
            medical_record += f"{separator}<b>辨證</b>:{distincts}"
        if cure != "":
            medical_record += f"{separator}<b>治則</b>:{cure}"
        if remark != "":
            medical_record += f"{separator}<b>備註</b>: {remark}"

    # medical_record = f'''
    #     <div style="width: 95%;">
    #         {medical_record}
    #     </div>
    # '''

    prescript_record = get_prescript_record(database, system_settings, case_key)

    html_str = f"""
        <html>
            <head>
                <meta charset="UTF-8">
            </head>
            <body>
                {medical_record}
                {prescript_record}
            </body>
        </html>
    """

    return html_str


def get_prescript_record(
    database,
    system_settings,
    case_key,
    display_total_dosage=False,
    display_location=False,
):
    sql = f"""
        SELECT * FROM prescript
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return "<br><br><br><center>無開立處方</center><br>"

    html_str = get_prescript_medicine_record(
        database,
        system_settings,
        case_key,
        1,
        display_total_dosage=display_total_dosage,
        display_location=display_location,
    )
    html_str += get_ins_prescript_treat_record(database, system_settings, case_key)
    html_str += get_self_prescript_medicine_record(
        database, system_settings, case_key, display_total_dosage=display_total_dosage
    )

    return html_str


def get_prescript_html_data(
    database,
    system_settings,
    case_key,
    medicine_set,
    treatment=None,
    display_total_dosage=False,
    display_location=False,
):
    prescript_data = ""
    total_pres_dosage = 0.0
    total_fee = 0.0
    single_day_dosage = 0  # 2025-04-22

    treatment_script = ""
    if medicine_set == 1:  # 健保才過濾處方或處置
        if treatment is None:
            treatment_script = (
                ' AND prescript.MedicineType NOT IN ("穴道", "處置", "檢驗") '
            )
        else:
            treatment_script = (
                ' AND prescript.MedicineType IN ("穴道", "處置", "檢驗") '
            )

    sql = f"""
        SELECT * FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set}
            {treatment_script}
        ORDER BY PrescriptKey
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return prescript_data, total_pres_dosage, total_fee, single_day_dosage

    sequence = 0
    total_amount = 0.0
    pres_days = get_pres_days(database, case_key, medicine_set)
    if pres_days <= 0:
        pres_days = 1

    packages = get_packages(database, case_key, medicine_set)
    if packages <= 0:
        packages = 1

    for row in rows:
        medicine_name = string_utils.xstr(row["MedicineName"])
        if medicine_name in [
            "",
            "優待",
            "自費藥費",
            "自費粉藥",
            "自費水藥",
        ]:
            continue

        sequence += 1

        dosage = number_utils.get_float(row["Dosage"])
        single_day_dosage += dosage

        if dosage is None or dosage == 0.00:
            dosage_str = ""
            total_dosage_str = ""
        else:
            if system_settings.field("劑量模式") in ["日劑量"]:
                total_dosage = dosage * pres_days
                dosage_str = f"{dosage:.1f}"
                total_dosage_str = f"{total_dosage:.1f}"
            if system_settings.field("劑量模式") in ["總量"]:
                total_dosage = dosage
                dosage_str = f"{dosage:.1f}"
                total_dosage_str = f"{total_dosage:.1f}"
            elif system_settings.field("劑量模式") in ["次劑量"]:
                total_dosage = dosage * pres_days * packages
                dosage_str = f"{dosage:.2f}"
                total_dosage_str = f"{total_dosage:.2f}"
            else:
                total_dosage = dosage * pres_days
                dosage_str = f"{dosage:.1f}"
                total_dosage_str = f"{total_dosage:.1f}"

            if "代煎" in medicine_name:
                pass
            else:
                total_pres_dosage += total_dosage

        unit = string_utils.xstr(row["Unit"])
        instruction = string_utils.xstr(row["Instruction"])
        try:
            amount = number_utils.get_float(row["Amount"])
        except Exception:
            amount = 0

        total_amount += amount

        if medicine_set >= 2:
            font_color = "color: blue"
        else:
            font_color = ""

        medicine_name = string_utils.xstr(row["MedicineName"])
        location = get_location(database, row["MedicineKey"])
        try:
            location = get_location(database, row["MedicineKey"])
            if display_location and location != "":
                medicine_name = location + " " + medicine_name
        except Exception:
            pass

        sale_price = int(number_utils.get_float(row["Amount"]) * pres_days)
        if display_total_dosage:
            prescript_data += f"""
                <tr>
                    <td align="center" style="padding-right: 8px; {font_color}">{sequence}</td>
                    <td style="padding-left: 8px; {font_color}">{medicine_name}</td>
                    <td align="center" style="padding-right: 8px; {font_color}">{unit}</td>
                    <td align="right" style="padding-right: 8px; {font_color}">{dosage_str}</td>
                    <td align="right" style="padding-right: 8px; {font_color}">{total_dosage_str}</td>
                    <td style="padding-left: 8px; {font_color}">{instruction}</td>
                </tr>
            """
        elif medicine_set == 1:
            prescript_data += f"""
                <tr>
                    <td align="center" style="padding-right: 8px; {font_color}">{sequence}</td>
                    <td style="padding-left: 8px; {font_color}">{medicine_name}</td>
                    <td align="right" style="padding-right: 8px; {font_color}">{dosage_str} {unit}</td>
                    <td style="padding-left: 8px; {font_color}">{instruction}</td>
                </tr>
            """
        else:
            prescript_data += f"""
                <tr>
                    <td align="center" style="padding-right: 8px; {font_color}">{sequence}</td>
                    <td style="padding-left: 8px; {font_color}">{medicine_name}</td>
                    <td align="right" style="padding-right: 8px; {font_color}">{dosage_str} {unit}</td>
                    <td style="padding-left: 8px; {font_color}">{instruction}</td>
                    <td align="right" style="padding-right: 8px; {font_color}">{sale_price:,}</td>
                </tr>
            """

    total_fee = number_utils.round_up(total_amount * pres_days)

    return (
        prescript_data,
        round(total_pres_dosage, 3),
        total_fee,
        round(single_day_dosage, 3),
    )


def get_location(database, medicine_key):
    if medicine_key in ["", None]:
        return ""

    sql = f"""
        SELECT Location FROM medicine
        WHERE
            MedicineKey = {medicine_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""
    else:
        return string_utils.xstr(rows[0]["Location"])


def get_dosage_html(
    database, system_settings, case_key, medicine_set, total_dosage, total_fee
):
    dosage_data = ""

    try:
        rows = get_dosage_row(database, case_key, medicine_set)
        if len(rows) <= 0:
            return dosage_data
    except Exception:
        if medicine_set >= 4:
            return dosage_data

        rows = [{}]
        sql = f"""
            SELECT
                PresDays{medicine_set}, Package{medicine_set}, Instruction{medicine_set}
            FROM cases
            WHERE
                CaseKey = {case_key}
        """
        dosage_row = database.select_record(sql)

        if len(dosage_row) <= 0:
            return dosage_data

        rows[0]["Days"] = number_utils.get_integer(
            dosage_row[0][f"PresDays{medicine_set}"]
        )
        rows[0]["Packages"] = number_utils.get_integer(
            dosage_row[0][f"Package{medicine_set}"]
        )
        rows[0]["Instruction"] = string_utils.xstr(
            dosage_row[0][f"Instruction{medicine_set}"]
        )

    row = rows[0]
    pres_days = number_utils.get_integer(row["Days"])
    packages = number_utils.get_integer(row["Packages"])
    try:
        self_total_fee = number_utils.get_integer(row["SelfTotalFee"])
    except KeyError:
        self_total_fee = None

    if medicine_set == 1:
        col_span = 4
    else:
        col_span = 5

    if packages > 0 or pres_days > 0:
        instruction = string_utils.xstr(row["Instruction"])
        dosage_data = f'''
            <tr>
                <td style="text-align: left; padding-left: 30px;" colspan="{col_span}">
                    用法: {packages}包 {pres_days}日份 {instruction}服用 總量: {total_dosage}
                </td>
            </tr>
        '''

    # if self_total_fee is not None and self_total_fee > 0 and system_settings.field('手動批價') != 'Y':
    #     discount_rate = number_utils.get_integer(row['DiscountRate'])
    #     discount_fee = number_utils.get_integer(row['DiscountFee'])
    #     total_fee -= discount_fee

    #     dosage_total_fee = number_utils.get_integer(row['TotalFee'])
    #     dosage_td = f'''
    #         自費合計: ${self_total_fee:,} 優待: {discount_rate}% 折扣金額: ${discount_fee:,}
    #         應收金額: ${dosage_total_fee:,}
    #     '''
    #     if dosage_total_fee != total_fee:
    #         dosage_td += f'''
    #             <br>
    #             <font color="red">
    #                 請注意! 病歷資料自費處方{medicine_set-1}的檢核金額為${int(total_fee)},
    #                 與應收金額${dosage_total_fee}金額不相符.  請進入病歷內重新存檔.
    #             </font>
    #         '''

    #     dosage_data += f'''
    #         <tr>
    #             <td style="text-align: left; padding-left: 30px;" colspan="{col_span}">
    #                 {dosage_td}
    #             </td>
    #         </tr>
    #     '''

    return dosage_data


def get_prescript_medicine_record(
    database,
    system_settings,
    case_key,
    medicine_set,
    display_total_dosage=False,
    display_location=False,
):
    prescript_data, total_dosage, total_fee, single_day_dosage = (
        get_prescript_html_data(
            database,
            system_settings,
            case_key,
            medicine_set,
            display_total_dosage=display_total_dosage,
            display_location=display_location,
        )
    )

    if prescript_data == "":
        return ""

    prescript_data += get_dosage_html(
        database, system_settings, case_key, medicine_set, total_dosage, total_fee
    )
    if medicine_set == 1:
        prescript_heading = "健保處方"
    else:
        prescript_heading = f"自費處方{medicine_set - 1}"

    if display_total_dosage:
        table_head = f"""
            <tr bgcolor="LightGray">
                <th style="text-align: center; padding-left: 8px" width="7%">序</th>
                <th style="padding-left: 8px" width="38%" align="left">{prescript_heading}</th>
                <th style="padding-right: 8px" align="center" width="18%">單位</th>
                <th style="padding-right: 8px" align="right" width="12%">單量</th>
                <th style="padding-right: 8px" align="right" width="15%">總量</th>
                <th style="padding-left: 8px" align="left" width="10%">指示</th>
            </tr>
        """
    elif medicine_set == 1:
        table_head = f"""
            <tr bgcolor="LightGray">
                <th style="text-align: center; padding-left: 8px" width="10%">序</th>
                <th style="padding-left: 8px" width="50%" align="left">{prescript_heading}</th>
                <th style="padding-right: 8px" align="right" width="25%">日量{single_day_dosage}</th>
                <th style="padding-left: 8px" align="left" width="15%">指示</th>
            </tr>
        """
    else:
        table_head = f"""
            <tr bgcolor="LightGray" style="vertical-align: middle">
                <th style="text-align: center; padding-left: 8px" width="10%">序</th>
                <th style="padding-left: 8px" width="45%" align="left">{prescript_heading}</th>
                <th style="padding-right: 8px" align="right" width="20%">日量{single_day_dosage}</th>
                <th style="padding-left: 8px" align="left" width="10%">指示</th>
                <th style="padding-left: 8px" align="left" width="15%">金額</th>
            </tr>
        """

    prescript_html = f"""
        <table align=center cellpadding="2" cellspacing="0" width="98%"
        style="border-width: 1px; border-style: solid;">
            <thead>
                {table_head}
            </thead>
            <tbody>
                {prescript_data}
            </tbody>
        </table>
        <br>
    """

    return prescript_html


def get_ins_prescript_treat_record(database, system_settings, case_key):
    prescript_html = ""
    sql = f"""
        SELECT Treatment FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    treatment = string_utils.xstr(rows[0]["Treatment"])

    if treatment == "":
        return prescript_html

    treatment_data = f"""
        <tr>
            <td align="center" style="padding-right: 8px;">*</td>
            <td style="padding-left: 8px;">{treatment}</td>
            <td align="right" style="padding-right: 8px">1 次</td>
            <td style="padding-left: 8px;"></td>
        </tr>
    """
    prescript_data, _, _, _ = get_prescript_html_data(
        database, system_settings, case_key, 1, True
    )

    prescript_html = f"""
        <table align=center cellpadding="2" cellspacing="0" width="98%"
         style="border-width: 1px; border-style: solid;">
            <thead>
                <tr bgcolor="LightGray">
                    <th style="text-align: center; padding-left: 8px" width="10%">序</th>
                    <th style="padding-left: 8px" width="50%" align="left">健保處置</th>
                    <th style="padding-right: 8px" align="right" width="25%">次數</th>
                    <th style="padding-left: 8px" align="left" width="15%">備註</th>
                </tr>
            </thead>
            <tbody>
                {treatment_data}
                {prescript_data}
            </tbody>
        </table>
        <br>
    """

    return prescript_html


def get_self_prescript_medicine_record(
    database, system_settings, case_key, display_total_dosage=False
):
    prescript_html = ""

    max_medicine_set = prescript_utils.get_max_medicine_set(database, case_key)
    if max_medicine_set is None:
        return prescript_html

    for medicine_set in range(2, max_medicine_set + 1):
        prescript_html += get_prescript_medicine_record(
            database,
            system_settings,
            case_key,
            medicine_set,
            display_total_dosage=display_total_dosage,
            display_location=True,
        )

    return prescript_html


# 拷貝過去病歷
def copy_past_medical_record(
    database,
    system_settings,
    medical_record,
    case_key,
    copy_diagnostic,
    copy_remark,
    copy_disease,
    copy_ins_prescript,
    copy_ins_prescript_to,
    copy_ins_treat,
    copy_self_prescript,
    copy_self_prescript_to_ins,
    not_overwrite=False,
):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]
    ui = medical_record.ui
    if copy_diagnostic:
        ui.textEdit_symptom.setText(string_utils.get_str(row["Symptom"], "utf8"))
        ui.textEdit_tongue.setText(string_utils.get_str(row["Tongue"], "utf8"))
        ui.textEdit_pulse.setText(string_utils.get_str(row["Pulse"], "utf8"))
        ui.lineEdit_distinguish.setText(string_utils.xstr(row["Distincts"]))
        ui.lineEdit_cure.setText(string_utils.xstr(row["Cure"]))

    if copy_remark:
        ui.textEdit_remark.setText(string_utils.get_str(row["Remark"], "utf8"))

    if copy_disease:
        line_edit_disease = [
            [ui.lineEdit_disease_code1, ui.lineEdit_disease_name1],
            [ui.lineEdit_disease_code2, ui.lineEdit_disease_name2],
            [ui.lineEdit_disease_code3, ui.lineEdit_disease_name3],
        ]
        try:
            line_edit_disease.append(
                [ui.lineEdit_disease_code4, ui.lineEdit_disease_name4],
            )
        except Exception:
            pass

        error_message = []
        for i in range(len(line_edit_disease)):
            disease_code = string_utils.get_str(row[f"DiseaseCode{i + 1}"], "utf8")
            disease_name = string_utils.get_str(row[f"DiseaseName{i + 1}"], "utf8")

            if disease_code.isdigit():
                disease_code = icd9_to_icd10(database, disease_code)

            if disease_code == "":
                continue

            sql = f'''
                SELECT ICD10Key FROM icd10
                WHERE
                    ICDCode = "{disease_code}"
            '''
            disease_rows = database.select_record(sql)
            if len(disease_rows) <= 0:
                error_message.append(f"{disease_code} {disease_name}<br>")
                line_edit_disease[i][0].setText(None)
                line_edit_disease[i][1].setText(None)
                continue

            line_edit_disease[i][0].setText(disease_code)
            line_edit_disease[i][1].setText(disease_name)

        try:
            medical_record.tab_registration.ui.lineEdit_special_code.setText(
                string_utils.xstr(row["SpecialCode"])
            )
        except Exception:
            pass

        if len(error_message) > 0:
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Critical,
                "ICD10資料已作廢",
                f"<h3>{', '.join(error_message)}在2023年新版ICD10已無法使用, 請改用其他診斷碼.</h3>",
                "請改用其他診斷碼.",
            )

    if copy_ins_prescript:
        if copy_ins_prescript_to == "健保處方":
            if medical_record.tab_list[0] is not None:
                medical_record.tab_list[0].copy_past_prescript(case_key, "病歷拷貝")
                medical_record.tab_list[0].append_null_medicine()
        else:
            if medical_record.tab_list[1] is None:
                medical_record.add_prescript_tab(2)

            medical_record.tab_list[1].copy_past_prescript(case_key, 1)
            medical_record.tab_list[1].append_null_medicine()

    if copy_ins_treat:
        if medical_record.tab_list[0] is not None:
            medical_record.tab_list[0].copy_past_treat(case_key, "病歷拷貝")
            medical_record.tab_list[0].append_null_treat()
        elif medical_record.ins_type == "自費":
            medical_record.tab_list[1].copy_past_treat(case_key)
            medical_record.tab_list[1].append_null_medicine()

    if copy_self_prescript:
        if not_overwrite:
            pass
        else:
            medical_record.close_all_self_prescript_tabs()  # 本來已經拿掉，後來會造成重複拷貝的狀況，2021.02.10 恢復

        sql = f"""
            SELECT MedicineSet FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2
            GROUP BY MedicineSet ORDER BY MedicineSet
        """
        rows = database.select_record(sql)

        for row in rows:
            medicine_set = row["MedicineSet"]

            if medicine_set == 11:
                continue

            tab_index = medicine_set - 1
            if system_settings.field("健保自費分開") == "Y":
                pass
            elif (
                medical_record.tab_list[tab_index] is None
                or medical_record.tab_list[tab_index].tableWidget_prescript.item(
                    0, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
                )
                is None
            ):
                medical_record.add_prescript_tab(medicine_set)
            else:
                if (
                    medical_record.tab_list[tab_index].tableWidget_prescript.rowCount()
                    > 0
                ):  # 原本的自費處方已被拷貝佔用
                    medical_record.add_prescript_tab(medicine_set + 1)
                    tab_index += 1

            if medical_record.tab_list[tab_index] is None:
                continue

            medical_record.tab_list[tab_index].copy_past_prescript(
                case_key, medicine_set
            )
            medical_record.tab_list[tab_index].append_null_medicine()

    if copy_self_prescript_to_ins:
        sql = f"""
            SELECT MedicineSet FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2
            GROUP BY MedicineSet ORDER BY MedicineSet
        """
        rows = database.select_record(sql)

        for row in rows:
            medicine_set = row["MedicineSet"]
            if medicine_set == 11:
                continue

            if medical_record.tab_list[0] is not None:
                medical_record.tab_list[0].copy_past_prescript(case_key, medicine_set)
                medical_record.tab_list[0].append_null_medicine()

    if system_settings.field("健保自費分開") == "Y":
        pass
    elif (
        medical_record.tab_list[1] is None
    ):  # 2019.04.27 拷貝完, 清除所有自費處方後, 自動新增自費處方1
        medical_record.add_prescript_tab()
        medical_record.tab_list[1].append_null_medicine()
        medical_record.ui.tabWidget_prescript.setCurrentIndex(0)

    if medical_record.ins_type == "健保":
        medical_record.calculate_ins_fees()


# 拷貝處方集
def copy_collection(
    database,
    medical_record,
    case_date,
    medical_row,
    copy_diagnostic,
    copy_disease,
    copy_prescript,
):
    ui = medical_record.ui
    if copy_diagnostic:
        ui.textEdit_symptom.setText(
            string_utils.get_str(medical_row["Symptom"], "utf8")
        )
        ui.textEdit_tongue.setText(string_utils.get_str(medical_row["Tongue"], "utf8"))
        ui.textEdit_pulse.setText(string_utils.get_str(medical_row["Pulse"], "utf8"))
        ui.lineEdit_distinguish.setText(string_utils.xstr(medical_row["Distincts"]))
        ui.lineEdit_cure.setText(string_utils.xstr(medical_row["Cure"]))

    if copy_disease:
        line_edit_disease = [
            [ui.lineEdit_disease_code1, ui.lineEdit_disease_name1],
            [ui.lineEdit_disease_code2, ui.lineEdit_disease_name2],
            [ui.lineEdit_disease_code3, ui.lineEdit_disease_name3],
        ]
        disease_list = []
        for i in range(3):
            icd9_code = string_utils.xstr(medical_row[f"ICDCode{i + 1}"])
            if icd9_code == "":
                continue

            icd10_code, icd10_name = convert_icd9_to_icd10(database, icd9_code)
            if icd10_name is not None:
                disease_list.append([icd10_code, icd10_name])

        for item_no, item in enumerate(disease_list):
            disease_code = item[0]
            disease_name = item[1]

            line_edit_disease[item_no][0].setText(disease_code)
            line_edit_disease[item_no][1].setText(disease_name)

    if medical_record.tab_list[0] is None:  # 無健保處方
        return

    if copy_prescript:
        collection_key = medical_row["CollectionKey"]
        if collection_key is None:
            return

        sql = f"""
            SELECT * FROM collitems
            WHERE
                CollectionKey = {collection_key}
            ORDER BY CollectionSetKey
        """
        try:
            prescript_rows = database.select_record(sql)
        except Exception:
            prescript_rows = []

        treat_dict = {
            "針灸處置": "針灸治療",
            "傷科處置": "傷科治療",
        }
        medical_record.tab_list[0].ui.tableWidget_treat.setRowCount(0)
        medical_record.tab_list[0].set_treat_ui()

        for prescript_row in prescript_rows:
            medicine_name = string_utils.xstr(prescript_row["MedicineName"])
            if medicine_name in ["針灸處置", "傷科處置"]:
                treatment = treat_dict[medicine_name]
                if case_date.date() >= nhi_utils.INS_TREAT_2021_DATE:
                    treatment = convert_new_treatment(treatment)
                else:
                    treatment = convert_old_treatment(treatment)

                medical_record.tab_list[0].comboBox_treatment.setCurrentText(treatment)
                continue

            medicine_type = string_utils.xstr(prescript_row["MedicineType"])

            row = {
                "MedicineType": medicine_type,
                "MedicineKey": string_utils.xstr(prescript_row["MedicineKey"]),
                "MedicineName": string_utils.xstr(prescript_row["MedicineName"]),
                "InsCode": string_utils.xstr(prescript_row["InsCode"]),
                "Unit": string_utils.xstr(prescript_row["Unit"]),
            }
            if medicine_type in ["穴道", "處置"]:
                medical_record.tab_list[0].append_treat(row)
                medical_record.tab_list[0].append_null_treat()
            else:
                medical_record.tab_list[0].append_prescript(
                    row, prescript_row["Dosage"]
                )
                medical_record.tab_list[0].append_null_medicine()


# 拷貝經驗方
def copy_experience(
    database,
    medical_record,
    case_date,
    experience_row,
    medicine_set,
    copy_diagnostic,
    copy_disease,
    copy_prescript,
):
    ui = medical_record.ui
    if copy_diagnostic:
        ui.textEdit_symptom.setText(
            string_utils.get_str(experience_row["ExpSymptom"], "utf8")
        )
        ui.textEdit_tongue.setText(
            string_utils.get_str(experience_row["ExpTongue"], "utf8")
        )
        ui.textEdit_pulse.setText(
            string_utils.get_str(experience_row["ExpPulse"], "utf8")
        )
        ui.lineEdit_distinguish.setText(
            string_utils.xstr(experience_row["ExpDistincts"])
        )
        ui.lineEdit_cure.setText(string_utils.xstr(experience_row["ExpCure"]))

    if copy_disease:
        icd_code = string_utils.xstr(experience_row["ExpICDCode"])
        if icd_code != "":
            icd10_code, icd10_name = convert_icd9_to_icd10(database, icd_code)
            ui.lineEdit_disease_code1.setText(icd10_code)
            ui.lineEdit_disease_name1.setText(icd10_name)

    if copy_prescript:
        tab_index = medicine_set - 1
        experience_key = experience_row["ExperienceKey"]
        if experience_key is None:
            return

        sql = f"""
            SELECT * FROM expprescript
            WHERE
                ExperienceKey = {experience_key}
        """
        try:
            prescript_rows = database.select_record(sql)
        except Exception:
            prescript_rows = []

        for prescript_row in prescript_rows:
            medicine_key = None
            row = {
                "MedicineType": string_utils.xstr(prescript_row["MedicineType"]),
                "MedicineKey": medicine_key,
                "MedicineName": string_utils.xstr(prescript_row["MedicineName"]),
                "InsCode": string_utils.xstr(prescript_row["InsCode"]),
                "Unit": string_utils.xstr(prescript_row["Unit"]),
            }
            medical_record.tab_list[tab_index].append_prescript(row)
            medical_record.tab_list[tab_index].append_null_medicine()


# 拷貝分院過去病歷
def copy_host_medical_record(
    database,
    medical_record,
    case_key,
    copy_diagnostic,
    copy_remark,
    copy_disease,
    copy_ins_prescript,
    copy_ins_prescript_to,
    copy_ins_treat,
    copy_self_prescript,
):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]
    ui = medical_record.ui
    if copy_diagnostic:
        ui.textEdit_symptom.setText(string_utils.get_str(row["Symptom"], "utf8"))
        ui.textEdit_tongue.setText(string_utils.get_str(row["Tongue"], "utf8"))
        ui.textEdit_pulse.setText(string_utils.get_str(row["Pulse"], "utf8"))
        ui.lineEdit_distinguish.setText(string_utils.xstr(row["Distincts"]))
        ui.lineEdit_cure.setText(string_utils.xstr(row["Cure"]))

    if copy_remark:
        ui.textEdit_remark.setText(string_utils.get_str(row["Remark"], "utf8"))

    if copy_disease:
        line_edit_disease = [
            [ui.lineEdit_disease_code1, ui.lineEdit_disease_name1],
            [ui.lineEdit_disease_code2, ui.lineEdit_disease_name2],
            [ui.lineEdit_disease_code3, ui.lineEdit_disease_name3],
        ]

        for i in range(3):
            disease_code = string_utils.get_str(row[f"DiseaseCode{i + 1}"], "utf8")
            disease_name = string_utils.get_str(row[f"DiseaseName{i + 1}"], "utf8")

            if disease_code.isdigit():
                disease_code = icd9_to_icd10(database, disease_code)

            line_edit_disease[i][0].setText(disease_code)
            line_edit_disease[i][1].setText(disease_name)

        medical_record.tab_registration.ui.lineEdit_special_code.setText(
            string_utils.xstr(row["SpecialCode"])
        )

    medical_record.close_all_self_prescript_tabs()
    if copy_ins_prescript:
        if copy_ins_prescript_to == "健保處方":
            if medical_record.tab_list[0] is not None:
                medical_record.tab_list[0].copy_host_prescript(
                    database, case_key, "病歷拷貝"
                )
                medical_record.tab_list[0].append_null_medicine()
        else:
            if medical_record.tab_list[1] is None:
                medical_record.add_prescript_tab(2)

            medical_record.tab_list[1].copy_host_prescript(database, case_key, 1)
            medical_record.tab_list[1].append_null_medicine()

    if copy_ins_treat:
        if medical_record.tab_list[0] is not None:
            medical_record.tab_list[0].copy_host_treat(database, case_key, "病歷拷貝")
            medical_record.tab_list[0].append_null_treat()

    if copy_self_prescript:
        sql = f"""
            SELECT MedicineSet FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2
            GROUP BY MedicineSet
            ORDER BY MedicineSet
        """
        rows = database.select_record(sql)

        for row in rows:
            medicine_set = row["MedicineSet"]

            if medicine_set == 11:
                continue

            tab_index = medicine_set - 1
            if medical_record.tab_list[tab_index] is None:
                medical_record.add_prescript_tab(medicine_set)
            else:
                if (
                    medical_record.tab_list[tab_index].tableWidget_prescript.rowCount()
                    > 0
                ):  # 原本的自費處方已被拷貝佔用
                    medical_record.add_prescript_tab(medicine_set + 1)
                    tab_index += 1

            medical_record.tab_list[tab_index].copy_host_prescript(
                database, case_key, medicine_set
            )
            medical_record.tab_list[tab_index].append_null_medicine()

    if (
        medical_record.tab_list[1] is None
    ):  # 2019.04.27 拷貝完, 清除所有自費處方後, 自動新增自費處方1
        medical_record.add_prescript_tab()
        medical_record.tab_list[1].append_null_medicine()
        medical_record.ui.tabWidget_prescript.setCurrentIndex(0)


def icd9_to_icd10(database, icd9_code):
    sql = f'''
        SELECT * FROM icdmap
        WHERE
            ICD9Code = "{icd9_code}"
        ORDER BY ICD10Code
        LIMIT 1
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return icd9_code

    return string_utils.xstr(rows[0]["ICD10Code"])


#  取得中(英)文病名
def get_disease_name(database, disease_code, field_name=None):
    disease_name = ""
    if field_name is None:
        field_name = "ChineseName"

    if disease_code in ["", None]:
        return ""

    sql = f'''
        SELECT {field_name} FROM icd10
        WHERE
            ICDCode = "{disease_code}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return disease_name

    row = rows[0]
    disease_name = string_utils.xstr(row[field_name])

    return disease_name


def get_medicine_name(database, field_name, field_value):
    if field_name == "MedicineKey":
        condition = f"{field_name} = {field_value}"
    else:
        condition = f'{field_name} = "{field_value}"'

    sql = f"""
        SELECT MedicineName FROM medicine
        WHERE
            {condition}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    medicine_name = string_utils.xstr(row["MedicineName"])

    return medicine_name


def get_drug_name(database, ins_code):
    sql = f'''
        SELECT DrugName FROM drug
        WHERE
            InsCode = "{ins_code.strip()}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    drug_name = string_utils.xstr(row["DrugName"])

    return drug_name


def get_treat_name(database, ins_code):
    sql = f'''
        SELECT ItemName FROM charge_settings
        WHERE
            InsCode = "{ins_code.strip()}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    treat_name = string_utils.xstr(row["ItemName"])

    return treat_name


def get_disease_name_html(in_disease_name):
    if in_disease_name is None:
        return None

    for word in INJURY_LIST:
        new_word = f'<font color="red">{word}</font>'
        in_disease_name = in_disease_name.replace(word, new_word)

    word = "右側"
    new_word = f'<font color="blue">{word}</font>'
    in_disease_name = in_disease_name.replace(word, new_word)

    word = "左側"
    new_word = f'<font color="green">{word}</font>'
    in_disease_name = in_disease_name.replace(word, new_word)

    return QtWidgets.QLabel(in_disease_name)


def get_full_card(card, course):
    card = string_utils.xstr(card)
    if number_utils.get_integer(course) >= 1:
        card += f"-{course}"

    return card


def is_disease_code_neat(database, disease_code):
    is_neat = True

    sql = f'''
        SELECT ICD10Key FROM icd10
        WHERE
            ICDCode LIKE "{disease_code}%"
        GROUP BY ICDCode
    '''
    rows = database.select_record(sql)

    if len(rows) >= 2:
        is_neat = False

    return is_neat


def correct_neat_disease(database, case_key, index):
    new_icd_10 = {
        "M791": "M7910",
        "N8329": "N83299",
        "N183": "N1830",
        "K210": "K2100",
        "H8141": "H814",
        "H8142": "H814",
        "H8143": "H814",
        "H8149": "H814",
        "M266": "M26609",
        "F0281": "F02818",
        "F328": "F3289",
        "B373": "B3732",
        "N800": "N8000",
        "N801": "N80109",
        "T07": "T07XXXS",
        "H4011X0": "H401194",
        "H4011X3": "H401194",
        "H4011X4": "H401193",
        "K040": "K0401",
        "M2660": "M26609",
        "T149": "T1490XS",
        "R391": "R39198",
        "K830": "K8309",
        "K20": "K2090",
        "M545": "M5459",
        "S60011D": "M5459",
        "M2662": "M26629",
        "H34813": "H348132",
        "N8320": "N83209",
        "F0391": "F03918",
        "K5669": "K56699",
        "M5092": "M50920",
        "M4806": "M48061",
        "R972": "R9720",
        "N830": "N8300",
        "T148": "T148XXD",
    }

    disease_name_field = "DiseaseName" + str(index)
    disease_code_field = "DiseaseCode" + str(index)
    sql = f"""
        SELECT {disease_code_field}, {disease_name_field} FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    row = rows[0]
    disease_code = string_utils.xstr(row[disease_code_field])
    if disease_code in new_icd_10:
        sql = f'''
            UPDATE cases SET {disease_code_field} = "{new_icd_10[disease_code]}" WHERE CaseKey = {case_key}
        '''
        database.exec_sql(sql)
        return new_icd_10[disease_code]

    disease_name = string_utils.xstr(row[disease_name_field])
    if disease_name == "":
        return None

    sql = f'''
        SELECT * FROM icd10
        WHERE
            ICDCode != "{disease_code}" AND
            ChineseName = "{disease_name}"
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    row = rows[0]
    icd_code = string_utils.xstr(row["ICDCode"])
    sql = f'''
        UPDATE cases SET {disease_code_field} = "{icd_code}" WHERE CaseKey = {case_key}
    '''
    database.exec_sql(sql)

    return icd_code


def is_disease_code_exist(database, disease_code):
    is_exist = True

    sql = f'''
        SELECT ICD10Key FROM icd10
        WHERE
            ICDCode = "{disease_code}"
        LIMIT 1
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        is_exist = False

    return is_exist


def get_disease_special_code(database, disease_code):
    sql = f'''
        SELECT SpecialCode FROM icd10
        WHERE
            ICDCode = "{disease_code}"
        LIMIT 1
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    return string_utils.xstr(rows[0]["SpecialCode"]).strip()


# backup_records_key: 指定要回復的病歷
def restore_medical_record(database, backup_records_key):
    restore_cases(database, backup_records_key)
    restore_prescript(database, backup_records_key)
    restore_dosage(database, backup_records_key)


# 回復 cases
def restore_cases(database, backup_records_key):
    sql = f"""
        SELECT * FROM backup_records
        WHERE
            BackupRecordsKey = {backup_records_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = json.loads(rows[0]["JSON"])[0]

    fields = list(row.keys())
    data = list(row.values())
    database.insert_record("cases", fields, data)


# 回復 prescript
def restore_prescript(database, backup_records_key):
    sql = f"""
        SELECT * FROM backup_records
        WHERE
            TableName = "prescript" AND
            KeyField = "BackupRecordsKey" AND
            KeyValue = {backup_records_key}
    """
    rows = database.select_record(sql)
    prescript_rows = json.loads(rows[0]["JSON"])

    for row in prescript_rows:
        fields = list(row.keys())
        data = list(row.values())

        database.insert_record("prescript", fields, data)


# 回復 dosage
def restore_dosage(database, backup_records_key):
    sql = f"""
        SELECT * FROM backup_records
        WHERE
            TableName = "dosage" AND
            KeyField = "BackupRecordsKey" AND
            KeyValue = {backup_records_key}
    """
    rows = database.select_record(sql)
    dosage_rows = json.loads(rows[0]["JSON"])

    for row in dosage_rows:
        fields = list(row.keys())
        data = list(row.values())

        database.insert_record("dosage", fields, data)


def backup_medical_record(database, case_key, deleter, delete_datetime, editor=None):
    backup_records_key = backup_cases(
        database, case_key, deleter, delete_datetime, editor
    )
    backup_prescript(database, backup_records_key, case_key, deleter, delete_datetime)
    backup_dosage(database, backup_records_key, case_key, deleter, delete_datetime)


def backup_cases(database, case_key, deleter, delete_datetime, editor):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    json_data = db_utils.mysql_to_json(rows)
    if len(json_data) <= 0:
        return

    if deleter == "編輯備份":
        delete_datetime = rows[0]["TimeStamp"]

    fields = [
        "TableName",
        "KeyField",
        "KeyValue",
        "JSON",
        "Deleter",
        "DeleteDateTime",
        "Editor",
    ]

    data = [
        "cases",
        "CaseKey",
        case_key,
        json_data,
        deleter,
        delete_datetime,
        editor,
    ]

    backup_records_key = database.insert_record("backup_records", fields, data)

    return backup_records_key


def backup_prescript(database, backup_records_key, case_key, deleter, delete_datetime):
    sql = f"""
        SELECT * FROM prescript
        WHERE
            CaseKey = {case_key}
        ORDER BY PrescriptKey
    """
    rows = database.select_record(sql)

    json_data = db_utils.mysql_to_json(rows)
    if len(json_data) <= 0:
        return

    fields = [
        "TableName",
        "KeyField",
        "KeyValue",
        "JSON",
        "Deleter",
        "DeleteDateTime",
    ]
    data = [
        "prescript",
        "BackupRecordsKey",
        backup_records_key,
        json_data,
        deleter,
        delete_datetime,
    ]
    database.insert_record("backup_records", fields, data)


def backup_dosage(database, backup_records_key, case_key, deleter, delete_datetime):
    sql = f"""
        SELECT * FROM dosage
        WHERE
            CaseKey = {case_key}
        ORDER BY DosageKey
    """
    rows = database.select_record(sql)

    json_data = db_utils.mysql_to_json(rows)
    if len(json_data) <= 0:
        return

    fields = [
        "TableName",
        "KeyField",
        "KeyValue",
        "JSON",
        "Deleter",
        "DeleteDateTime",
    ]

    data = [
        "dosage",
        "BackupRecordsKey",
        backup_records_key,
        json_data,
        deleter,
        delete_datetime,
    ]
    database.insert_record("backup_records", fields, data)


def set_in_progress_icon(table_widget, row_no, col_no, in_progress):
    table_widget.setCellWidget(row_no, col_no, None)

    if in_progress == "Y":
        icon = QtGui.QIcon("./icons/user-info.png")
        button = QtWidgets.QPushButton(table_widget)
        button.setIcon(icon)
        button.setFlat(True)
        table_widget.setCellWidget(row_no, col_no, button)


def set_close_case_icon(table_widget, row_no, col_no, file_closed):
    table_widget.setCellWidget(row_no, col_no, None)

    if file_closed:
        icon = QtGui.QIcon("./icons/changes-prevent.png")
        button = QtWidgets.QPushButton(table_widget)
        button.setIcon(icon)
        button.setFlat(True)
        table_widget.setCellWidget(row_no, col_no, button)


def get_return_date(database, case_key):
    sql = f"""
        SELECT  ReturnDate FROM deposit
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    return rows[0]["ReturnDate"]


def convert_icd9_to_icd10(database, icd9_code):
    sql = f'''
        SELECT * FROM icdmap
        WHERE
            ICD9Code = "{icd9_code}"
        ORDER BY LENGTH(ICD10Code) DESC
        LIMIT 1
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return icd9_code, None

    row = rows[0]

    return string_utils.xstr(row["ICD10Code"]), string_utils.xstr(
        row["ICD10ChineseName"]
    )


# 取得病歷html格式
def get_medical_record_row_html(medical_record_row):
    if medical_record_row["InsType"] == "健保":
        card = str(medical_record_row["Card"])
        if number_utils.get_integer(medical_record_row["Continuance"]) >= 1:
            card += "-" + str(medical_record_row["Continuance"])
        card = f"<b>健保</b>: {card}"
    else:
        card = "<b>自費</b>"

    case_date = string_utils.xstr(medical_record_row["CaseDate"])
    doctor = string_utils.xstr(medical_record_row["Doctor"])
    medical_record = f"<b>日期</b>: {case_date} {card} <b>醫師</b>:{doctor}<hr>"

    symptom = string_utils.get_str(medical_record_row["Symptom"], "utf8")
    tongue = string_utils.get_str(medical_record_row["Tongue"], "utf8")
    pulse = string_utils.get_str(medical_record_row["Pulse"], "utf8")
    distincts = string_utils.get_str(medical_record_row["Distincts"], "utf8")
    cure = string_utils.get_str(medical_record_row["Cure"], "utf8")
    remark = string_utils.get_str(medical_record_row["Remark"], "utf8")
    disease_code1 = string_utils.xstr(medical_record_row["DiseaseCode1"])
    disease_name1 = string_utils.xstr(medical_record_row["DiseaseName1"])
    disease_code2 = string_utils.xstr(medical_record_row["DiseaseCode2"])
    disease_name2 = string_utils.xstr(medical_record_row["DiseaseName2"])
    disease_code3 = string_utils.xstr(medical_record_row["DiseaseCode3"])
    disease_name3 = string_utils.xstr(medical_record_row["DiseaseName3"])
    try:
        disease_code4 = string_utils.xstr(medical_record_row["DiseaseCode4"])
        disease_name4 = string_utils.xstr(medical_record_row["DiseaseName4"])
    except Exception:
        disease_code4 = ""
        disease_name4 = ""

    if symptom != "":
        medical_record += f"<b>主訴</b>: {symptom}<hr>"
    if tongue != "":
        medical_record += f"<b>舌診</b>: {tongue}<hr>"
    if pulse != "":
        medical_record += f"<b>脈象</b>: {pulse}<hr>"
    if distincts != "":
        medical_record += f"<b>辨證</b>: {distincts}<hr>"
    if cure != "":
        medical_record += f"<b>治則</b>: {cure}<hr>"
    if remark != "":
        medical_record += f"<b>備註</b>: {remark}<hr>"
    if disease_code1 != "":
        medical_record += f"<b>主診斷</b>: {disease_code1} {disease_name1}<br>"
    if disease_code2 != "":
        medical_record += f"<b>次診斷1</b>: {disease_code2} {disease_name2}<br>"
    if disease_code3 != "":
        medical_record += f"<b>次診斷2</b>: {disease_code3} {disease_name3}<br>"
    if disease_code4 != "":
        medical_record += f"<b>次診斷3</b>: {disease_code4} {disease_name4}<br>"

    medical_record = f"""
        <div style="width: 95%;">
            {medical_record}
        </div>
    """

    prescript_record = get_prescript_row_html(medical_record_row)

    html = f"""
        <html>
            <head>
                <meta charset="UTF-8">
            </head>
            <body>
                {medical_record}
                {prescript_record}
            </body>
        </html>
    """

    return html


def get_prescript_row_html(medical_record_row):
    rows = medical_record_row["PrescriptJSON"]

    if len(rows) <= 0:
        return "<br><br><br><center>無開立處方</center><br>"

    html = get_prescript_row_medicine_record(medical_record_row, 1)
    html += get_ins_prescript_treat_row_record(medical_record_row)
    html += get_self_prescript_medicine_row_record(medical_record_row)

    return html


def get_prescript_row_medicine_record(medical_record_row, medicine_set):
    rows = medical_record_row["PrescriptJSON"]
    medicine_rows = []
    for row in rows:
        if (
            row["MedicineType"] not in ["穴道", "處置", "檢驗"]
            and row["MedicineSet"] == medicine_set
        ):
            medicine_rows.append(row)

    prescript_data, total_dosage = get_prescript_row_html_data(
        medicine_rows, medicine_set
    )
    if prescript_data == "":
        return ""

    prescript_data += get_dosage_row_html(
        medical_record_row, medicine_set, total_dosage
    )
    if medicine_set == 1:
        prescript_heading = "健保處方"
    else:
        prescript_heading = f"自費處方{medicine_set - 1}"

    prescript_html = f"""
        <table align=center cellpadding="2" cellspacing="0" width="98%"
         style="border-width: 1px; border-style: solid;">
            <thead>
                <tr bgcolor="LightGray">
                    <th style="text-align: center; padding-left: 8px" width="10%">序</th>
                    <th style="padding-left: 8px" width="50%" align="left">{prescript_heading}</th>
                    <th style="padding-right: 8px" align="right" width="25%">劑量</th>
                    <th style="padding-left: 8px" align="left" width="15%">指示</th>
                </tr>
            </thead>
            <tbody>
                {prescript_data}
            </tbody>
        </table>
        <br>
    """

    return prescript_html


def get_prescript_row_html_data(rows, medicine_set):
    prescript_data = ""
    total_dosage = 0

    if len(rows) <= 0:
        return prescript_data, total_dosage

    sequence = 0
    for row in rows:
        if string_utils.xstr(row["MedicineName"]) in ["", "優待"]:
            continue

        sequence += 1

        if row["Dosage"] is None or row["Dosage"] == 0.00:
            dosage = ""
        else:
            dosage_value = number_utils.get_float(row["Dosage"])
            dosage = f"{dosage_value:.1f}"
            total_dosage += dosage_value

        unit = string_utils.xstr(row["Unit"])
        instruction = string_utils.xstr(row["Instruction"])

        if medicine_set >= 2:
            font_color = "color: navy"
        else:
            font_color = ""

        medicine_name = string_utils.xstr(row["MedicineName"])
        prescript_data += f"""
            <tr>
                <td align="center" style="padding-right: 8px; {font_color}">{sequence}</td>
                <td style="padding-left: 8px; {font_color}">{medicine_name}</td>
                <td align="right" style="padding-right: 8px; {font_color}">{dosage} {unit}</td>
                <td style="padding-left: 8px; {font_color}">{instruction}</td>
            </tr>
        """

    return prescript_data, total_dosage


def get_dosage_row_html(medical_record_row, medicine_set, total_dosage):
    dosage_data = ""

    rows = medical_record_row["DosageJSON"]
    if len(rows) <= 0:
        return dosage_data

    try:
        row = rows[medicine_set - 1]
    except IndexError:
        return dosage_data

    pres_days = number_utils.get_integer(row["Days"])
    packages = number_utils.get_integer(row["Packages"])
    try:
        self_total_fee = number_utils.get_integer(row["SelfTotalFee"])
    except KeyError:
        self_total_fee = None

    if packages > 0 or pres_days > 0:
        instruction = string_utils.xstr(row["Instruction"])
        dosage_data = f"""
            <tr>
                <td style="text-align: left; padding-left: 30px;" colspan="4">
                    用法: {packages}包 {pres_days}日份 {instruction}服用 總量: {total_dosage}
                </td>
            </tr>
        """

    if self_total_fee is not None and self_total_fee > 0:
        discount_rate = number_utils.get_integer(row["DiscountRate"])
        discount_fee = number_utils.get_integer(row["DiscountFee"])
        total_fee = number_utils.get_integer(row["TotalFee"])
        dosage_data += f"""
            <tr>
                <td style="text-align: left; padding-left: 30px;" colspan="4">
                    自費合計: ${self_total_fee:,} 優待: {discount_rate}% 折扣金額: ${discount_fee:,}
                    應收金額: ${total_fee:,}
                </td>
            </tr>
        """

    return dosage_data


def get_ins_prescript_treat_row_record(medical_record_row):
    medicine_set = 1
    prescript_html = ""
    treatment = string_utils.xstr(medical_record_row["Treatment"])

    if treatment == "":
        return prescript_html

    treatment_data = f"""
        <tr>
            <td align="center" style="padding-right: 8px;">*</td>
            <td style="padding-left: 8px;">{treatment}</td>
            <td align="right" style="padding-right: 8px">1 次</td>
            <td style="padding-left: 8px;"></td>
        </tr>
    """
    rows = medical_record_row["PrescriptJSON"]

    medicine_rows = []
    for row in rows:
        if (
            row["MedicineType"] in ["穴道", "處置", "檢驗"]
            and row["MedicineSet"] == medicine_set
        ):
            medicine_rows.append(row)

    prescript_data, _ = get_prescript_row_html_data(medicine_rows, medicine_set)

    prescript_html = f"""
        <table align=center cellpadding="2" cellspacing="0" width="98%"
         style="border-width: 1px; border-style: solid;">
            <thead>
                <tr bgcolor="LightGray">
                    <th style="text-align: center; padding-left: 8px" width="10%">序</th>
                    <th style="padding-left: 8px" width="50%" align="left">健保處置</th>
                    <th style="padding-right: 8px" align="right" width="25%">次數</th>
                    <th style="padding-left: 8px" align="left" width="15%">備註</th>
                </tr>
            </thead>
            <tbody>
                {treatment_data}
                {prescript_data}
            </tbody>
        </table>
        <br>
    """

    return prescript_html


def get_self_prescript_medicine_row_record(medical_record_row):
    prescript_html = ""

    max_medicine_set = 1
    rows = medical_record_row["PrescriptJSON"]
    for row in rows:
        medicine_set = row["MedicineSet"]
        if medicine_set > max_medicine_set:
            max_medicine_set = medicine_set

    if max_medicine_set <= 1:
        return prescript_html

    for medicine_set in range(2, max_medicine_set + 1):
        prescript_html += get_prescript_row_medicine_record(
            medical_record_row, medicine_set
        )

    return prescript_html


def get_new_opening_card(database, patient_key):
    card = "G000 新特約醫事機構"

    today = datetime.date.today()
    last_treat_date = (today - datetime.timedelta(days=30 - 1)).strftime(
        "%Y-%m-%d 00:00:00"
    )
    sql = f'''
        SELECT Card, Continuance FROM cases
        WHERE
            (CaseDate >= "{last_treat_date}") AND
            (PatientKey = {patient_key}) AND
            (InsType = "健保")
        ORDER BY CaseDate DESC LIMIT 1
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return card

    row = rows[0]

    course = number_utils.get_integer(row["Continuance"])
    if course <= 0 or course >= 6:
        try:
            card_sequence = string_utils.xstr(row["Card"])[4]
        except IndexError:
            card_sequence = 0

        card = f"G000{int(card_sequence) + 1} 新特約醫事機構"

        return card
    else:
        return card


def convert_new_treatment(treatment):
    new_treatment = treatment

    if treatment == "針灸治療":
        new_treatment = "一般針灸"
    elif treatment == "電針治療":
        new_treatment = "電針"
    elif treatment == "複雜針灸":
        new_treatment = "中度複雜性針灸"
    elif treatment in ["傷科治療", "脫臼整復"]:
        new_treatment = "一般傷科"
    elif treatment == "複雜傷科":
        new_treatment = "中度複雜性傷科"
    elif treatment in ["脫臼整復首次", "脫臼復位"]:
        new_treatment = "脫臼整復復位"

    return new_treatment


def convert_old_treatment(treatment):
    new_treatment = treatment

    if treatment == "一般針灸":
        new_treatment = "針灸治療"
    elif treatment == "電針":
        new_treatment = "電針治療"
    elif treatment == "中度複雜性針灸":
        new_treatment = "複雜針灸"
    elif treatment == "一般傷科":
        new_treatment = "傷科治療"
    elif treatment == "中度複雜性傷科":
        new_treatment = "複雜傷科"
    elif treatment == "脫臼整復復位":
        new_treatment = "脫臼復位"

    return new_treatment


def is_special_disease_ok(
    disease_code1, disease_code2, disease_code3, disease_code4, special_disease_list
):
    if (
        disease_code1 in special_disease_list
        or disease_code2 in special_disease_list
        or disease_code3 in special_disease_list
        or disease_code4 in special_disease_list
    ):
        check_ok = True
    else:
        check_ok = False

    return check_ok


def is_moderate_complicated_acupuncture_ok(
    disease_code1,
    disease_code2,
    disease_code3,
    disease_code4,
    moderate_complicated_acupuncture_list,
    special_disease_list,
):
    if (
        disease_code1 in moderate_complicated_acupuncture_list
        or disease_code2 in moderate_complicated_acupuncture_list
        or disease_code3 in moderate_complicated_acupuncture_list
        or disease_code4 in moderate_complicated_acupuncture_list
    ):
        check_ok = True
    elif is_special_disease_ok(
        disease_code1, disease_code2, disease_code3, disease_code4, special_disease_list
    ):
        check_ok = True
    else:
        check_ok = False

    return check_ok


def is_moderate_complicated_acupuncture_with_special_disease_ok(
    disease_code1,
    disease_code2,
    disease_code3,
    disease_code4,
    moderate_complicated_acupuncture_list,
    special_disease_list,
):
    if (
        disease_code1 in moderate_complicated_acupuncture_list
        or disease_code2 in moderate_complicated_acupuncture_list
        or disease_code3 in moderate_complicated_acupuncture_list
        or disease_code4 in moderate_complicated_acupuncture_list
    ) and is_special_disease_ok(
        disease_code1, disease_code2, disease_code3, disease_code4, special_disease_list
    ):
        check_ok = True
    else:
        check_ok = False

    return check_ok


# 檢查高度複雜性針灸病名範圍
def is_highly_complicated_acupuncture_ok(
    disease_code1,
    disease_code2,
    disease_code3,
    disease_code4,
    highly_complicated_acupuncture_list,
    moderate_complicated_acupuncture_list,
    special_disease_list,
):
    if (
        disease_code1 in highly_complicated_acupuncture_list
        or disease_code2 in highly_complicated_acupuncture_list
        or disease_code3 in highly_complicated_acupuncture_list
        or disease_code4 in highly_complicated_acupuncture_list
    ):
        check_ok = True
    elif is_moderate_complicated_acupuncture_with_special_disease_ok(
        disease_code1,
        disease_code2,
        disease_code3,
        disease_code4,
        moderate_complicated_acupuncture_list,
        special_disease_list,
    ):
        check_ok = True
    else:
        check_ok = False

    return check_ok


def is_moderate_complicated_massage_ok(
    disease_code1,
    disease_code2,
    disease_code3,
    disease_code4,
    moderate_complicated_massage_list,
    special_disease_list,
):
    if (
        disease_code1 in moderate_complicated_massage_list
        or disease_code2 in moderate_complicated_massage_list
        or disease_code3 in moderate_complicated_massage_list
        or disease_code4 in moderate_complicated_massage_list
    ):
        check_ok = True
    elif is_special_disease_ok(
        disease_code1, disease_code2, disease_code3, disease_code4, special_disease_list
    ):
        check_ok = True
    else:
        check_ok = False

    return check_ok


def is_moderate_complicated_massage_with_special_disease_ok(
    disease_code1,
    disease_code2,
    disease_code3,
    disease_code4,
    moderate_complicated_massage_list,
    special_disease_list,
):
    if (
        disease_code1 in moderate_complicated_massage_list
        or disease_code2 in moderate_complicated_massage_list
        or disease_code3 in moderate_complicated_massage_list
        or disease_code4 in moderate_complicated_massage_list
    ) and is_special_disease_ok(
        disease_code1, disease_code2, disease_code3, disease_code4, special_disease_list
    ):
        check_ok = True
    else:
        check_ok = False

    return check_ok


def is_highly_complicated_massage_ok(
    disease_code1,
    disease_code2,
    disease_code3,
    disease_code4,
    highly_complicated_massage_list,
    moderate_complicated_massage_list,
    special_disease_list,
):
    if (
        disease_code1 in highly_complicated_massage_list
        or disease_code2 in highly_complicated_massage_list
        or disease_code3 in highly_complicated_massage_list
        or disease_code4 in highly_complicated_massage_list
    ):
        check_ok = True
    elif is_moderate_complicated_massage_with_special_disease_ok(
        disease_code1,
        disease_code2,
        disease_code3,
        disease_code4,
        moderate_complicated_massage_list,
        special_disease_list,
    ):
        check_ok = True
    else:
        check_ok = False

    return check_ok


def is_dislocate_ok(
    disease_code1, disease_code2, disease_code3, disease_code4, dislocate_list
):
    if (
        disease_code1 in dislocate_list
        or disease_code2 in dislocate_list
        or disease_code3 in dislocate_list
        or disease_code4 in dislocate_list
    ):
        check_ok = True
    else:
        check_ok = False

    return check_ok


def is_fracture_ok(
    disease_code1, disease_code2, disease_code3, disease_code4, fracture_list
):
    if (
        disease_code1 in fracture_list
        or disease_code2 in fracture_list
        or disease_code3 in fracture_list
        or disease_code4 in fracture_list
    ):
        check_ok = True
    else:
        check_ok = False

    return check_ok


def check_treatment_disease(
    moderate_complicated_acupuncture_list,
    highly_complicated_acupuncture_list,
    moderate_complicated_massage_list,
    highly_complicated_massage_list,
    dislocate_list,
    fracture_list,
    special_disease_list,
    row,
):
    treatment = string_utils.xstr(row["Treatment"])
    if treatment == "":
        return True

    disease_code1 = string_utils.xstr(row["DiseaseCode1"])
    disease_code2 = string_utils.xstr(row["DiseaseCode2"])
    disease_code3 = string_utils.xstr(row["DiseaseCode3"])
    disease_code4 = string_utils.xstr(row["DiseaseCode4"])

    if treatment == "中度複雜性針灸":
        if is_moderate_complicated_acupuncture_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            moderate_complicated_acupuncture_list,
            special_disease_list,
        ):
            return True
    elif treatment == "高度複雜性針灸":
        if is_highly_complicated_acupuncture_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            highly_complicated_acupuncture_list,
            moderate_complicated_acupuncture_list,
            special_disease_list,
        ):
            return True
    elif treatment == "中度複雜性傷科":
        if is_moderate_complicated_massage_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            moderate_complicated_massage_list,
            special_disease_list,
        ):
            return True
    elif treatment == "高度複雜性傷科":
        if is_highly_complicated_massage_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            highly_complicated_massage_list,
            moderate_complicated_massage_list,
            special_disease_list,
        ):
            return True
    elif treatment in ["中度針灸合併中度傷科", "中度針灸合併中度傷科療程2-6次"]:
        acupuncture_ok = is_moderate_complicated_acupuncture_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            moderate_complicated_acupuncture_list,
            special_disease_list,
        )
        massage_ok = is_moderate_complicated_massage_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            moderate_complicated_massage_list,
            special_disease_list,
        )

        if acupuncture_ok and massage_ok:
            return True
    elif treatment in ["中度針灸合併高度傷科起始次", "中度針灸合併高度傷科後續治療"]:
        acupuncture_ok = is_moderate_complicated_acupuncture_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            moderate_complicated_acupuncture_list,
            special_disease_list,
        )
        massage_ok = is_highly_complicated_massage_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            highly_complicated_massage_list,
            moderate_complicated_massage_list,
            special_disease_list,
        )

        if acupuncture_ok and massage_ok:
            return True
    elif treatment in [
        "中度針灸合併中度傷科合併特殊疾病起始次",
        "中度針灸合併中度傷科合併特殊疾病後續治療",
    ]:
        acupuncture_ok = is_moderate_complicated_acupuncture_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            moderate_complicated_acupuncture_list,
            special_disease_list,
        )
        massage_ok = is_moderate_complicated_massage_with_special_disease_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            moderate_complicated_massage_list,
            special_disease_list,
        )

        if acupuncture_ok and massage_ok:
            return True
    elif treatment in ["高度針灸合併中度傷科", "高度針灸合併中度傷科療程2-6次"]:
        acupuncture_ok = is_highly_complicated_acupuncture_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            highly_complicated_acupuncture_list,
            moderate_complicated_acupuncture_list,
            special_disease_list,
        )
        massage_ok = is_moderate_complicated_massage_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            moderate_complicated_massage_list,
            special_disease_list,
        )

        if acupuncture_ok and massage_ok:
            return True
    elif treatment in ["高度針灸合併高度傷科起始次", "高度針灸合併高度傷科後續治療"]:
        acupuncture_ok = is_highly_complicated_acupuncture_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            highly_complicated_acupuncture_list,
            moderate_complicated_acupuncture_list,
            special_disease_list,
        )
        massage_ok = is_highly_complicated_massage_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            highly_complicated_massage_list,
            moderate_complicated_massage_list,
            special_disease_list,
        )

        if acupuncture_ok and massage_ok:
            return True
    elif treatment in [
        "高度針灸合併中度傷科合併特殊疾病起始次",
        "高度針灸合併中度傷科合併特殊疾病後續治療",
    ]:
        acupuncture_ok = is_highly_complicated_acupuncture_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            highly_complicated_acupuncture_list,
            moderate_complicated_acupuncture_list,
            special_disease_list,
        )
        massage_ok = is_moderate_complicated_massage_with_special_disease_ok(
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            moderate_complicated_massage_list,
            special_disease_list,
        )

        if acupuncture_ok and massage_ok:
            return True
    elif treatment == "脫臼整復復位":
        if is_dislocate_ok(
            disease_code1, disease_code2, disease_code3, disease_code4, dislocate_list
        ):
            return True
    elif treatment == "骨折復位":
        if is_fracture_ok(
            disease_code1, disease_code2, disease_code3, disease_code4, fracture_list
        ):
            return True
    else:
        return True

    return False


# 取得開始日期
def get_course_start_date(database, patient_key, case_date, card, course):
    start_date = case_date.date()

    if number_utils.get_integer(course) <= 1:
        return start_date

    last_month = (
        datetime.date(start_date.year, start_date.month, 1) - datetime.timedelta(1)
    ).replace(day=1)
    case_start_date = f"{last_month} 00:00:00"
    case_end_date = f"{start_date} 00:00:00"

    sql = f'''
        SELECT CaseDate FROM cases
        WHERE
            (PatientKey = {patient_key}) AND
            (CaseDate BETWEEN "{case_start_date}" AND "{case_end_date}") AND
            (InsType = "健保") AND
            (Continuance = 1) AND
            (Card = "{card}")
        LIMIT 1
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        start_date = rows[0]["CaseDate"].date()

    return start_date


# 取得開始日期
def is_last_month_course_duplicated(database, patient_key, case_date, card):
    start_date = case_date.date()

    last_month = (
        datetime.date(start_date.year, start_date.month, 1) - datetime.timedelta(1)
    ).replace(day=1)
    case_start_date = f"{last_month} 00:00:00"
    case_end_date = f"{start_date} 00:00:00"

    sql = f'''
        SELECT CaseDate FROM cases
        WHERE
            (PatientKey = {patient_key}) AND
            (CaseDate BETWEEN "{case_start_date}" AND "{case_end_date}") AND
            (InsType = "健保") AND
            (Continuance >= 1) AND
            (Card = "{card}")
    '''
    rows = database.select_record(sql)
    if 1 <= len(rows) <= 5:
        return True
    else:
        return False


# 取得當月複雜性針灸次數
def get_complicated_acupuncture_times(database, case_date, treatment):
    last_day = calendar.monthrange(case_date.year, case_date.month)[1]
    start_date = f"{case_date.year}-{case_date.month}-01 00:00:00"
    end_date = f"{case_date.year}-{case_date.month}-{last_day} 23:59:59"

    if treatment in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST:
        check_acupuncture_list = nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST
    elif treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST:
        check_acupuncture_list = nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST
    elif treatment in nhi_utils.MERGE_TREAT:
        check_acupuncture_list = nhi_utils.MERGE_TREAT
    else:
        return 0

    sql = f'''
        SELECT Doctor FROM cases
            LEFT JOIN person ON person.Name = cases.Doctor
        WHERE
            (person.Position = "醫師") AND
            (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
            (InsType = "健保") AND
            (Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
            (Share NOT IN ("山地離島")) AND
            (TreatType NOT IN ("居家醫療")) AND
            (Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡")
        GROUP BY Doctor
    '''
    rows = database.select_record(sql)
    doctor_count = len(rows)

    if doctor_count <= 0:
        return 0

    sql = f'''
        SELECT Treatment FROM cases
        WHERE
            (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
            (InsType = "健保") AND
            (Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
            (Share NOT IN ("山地離島")) AND
            (TreatType NOT IN ("居家醫療")) AND
            (Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
            (Treatment IN {tuple(check_acupuncture_list)})
    '''
    rows = database.select_record(sql)
    treat_count = len(rows)
    avg_acupuncture_times = int(treat_count) / doctor_count

    return avg_acupuncture_times


# 取得當月針傷合併次數
def get_merge_treatment_times(database, case_date, treatment):
    last_day = calendar.monthrange(case_date.year, case_date.month)[1]
    start_date = f"{case_date.year}-{case_date.month}-01 00:00:00"
    end_date = f"{case_date.year}-{case_date.month}-{last_day} 23:59:59"

    check_acupuncture_list = nhi_utils.MERGE_TREAT_LIST

    # 取得專任醫師人數
    sql = f'''
        SELECT Doctor FROM cases
            LEFT JOIN person ON person.Name = cases.Doctor
        WHERE
            (person.Position = "醫師") AND
            (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
            (InsType = "健保") AND
            (Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
            (Share NOT IN ("山地離島")) AND
            (TreatType NOT IN ("居家醫療")) AND
            (Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡")
        GROUP BY Doctor
    '''
    rows = database.select_record(sql)
    doctor_count = len(rows)

    if doctor_count <= 0:
        return 0

    sql = f'''
        SELECT Treatment FROM cases
        WHERE
            (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
            (InsType = "健保") AND
            (Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
            (Share NOT IN ("山地離島")) AND
            (TreatType NOT IN ("居家醫療")) AND
            (Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
            (Treatment IN {tuple(check_acupuncture_list)})
    '''
    rows = database.select_record(sql)
    treat_count = len(rows)
    avg_acupuncture_times = int(treat_count / doctor_count)

    return avg_acupuncture_times


def get_treatment_times_by_doctor(database, case_date, treat_list, doctor):
    last_day = calendar.monthrange(case_date.year, case_date.month)[1]
    start_date = f"{case_date.year}-{case_date.month}-01 00:00:00"
    end_date = f"{case_date.year}-{case_date.month}-{last_day} 23:59:59"

    sql = f'''
        SELECT Treatment FROM cases
        WHERE
            (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
            (InsType = "健保") AND
            (Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
            (Share NOT IN ("山地離島")) AND
            (TreatType NOT IN ("居家醫療")) AND
            (RegistType NOT IN ("照護機構中醫照護")) AND
            (Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
            (Treatment IN {tuple(treat_list)}) AND
            (Doctor = "{doctor}")
    '''
    rows = database.select_record(sql)

    return len(rows)


def delete_self_traditional_health_care(database, in_case_key):
    fields = [
        "SMassageFee",
        "SelfTotalFee",
        "TotalFee",
        "ReceiptFee",
    ]
    data = [0, 0, 0, 0]
    database.update_record("cases", fields, "CaseKey", in_case_key, data)
    database.exec_sql(f"DELETE FROM prescript WHERE CaseKey = {in_case_key}")


def delete_traditional_health_care(database, in_case_key):
    sql = f"""
        SELECT CaseKey FROM cases
        WHERE
            InsType = "自費" AND
            Position1 = {in_case_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]
    case_key = row["CaseKey"]
    database.exec_sql(f"DELETE FROM cases WHERE CaseKey = {case_key}")
    database.exec_sql(f"DELETE FROM prescript WHERE CaseKey = {case_key}")


def update_traditional_health_care(
    database, system_settings, in_case_key, traditional_health_care_fee
):
    sql = f"""
        SELECT
            CaseDate, Period, TreatType, DoctorDone, ChargeDone
        FROM cases
        WHERE
            CaseKey = {in_case_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    row = rows[0]

    treat_type = "民俗調理"
    # if string_utils.xstr(row['TreatType']) != treat_type:  # 只修改民俗調理的自費病歷
    #     return

    case_date = string_utils.xstr(datetime.datetime.now())
    period = string_utils.xstr(row["Period"])
    doctor_done = row["DoctorDone"]
    charge_done = row["ChargeDone"]

    fields = [
        "TreatType",
        "SMassageFee",
        "SelfTotalFee",
        "TotalFee",
        "ReceiptFee",
        "DoctorDate",
        "DoctorDone",
        "ChargeDate",
        "ChargeDone",
        "ChargePeriod",
    ]
    data = [
        treat_type,
        traditional_health_care_fee,
        traditional_health_care_fee,
        traditional_health_care_fee,
        traditional_health_care_fee,
    ]
    if system_settings.field("候診名單顯示自費民俗調理") == "Y":
        massage_status = [None, doctor_done, None, charge_done, None]
    else:
        massage_status = [case_date, "True", case_date, "True", period]

    data += massage_status

    database.update_record("cases", fields, "CaseKey", in_case_key, data)

    database.exec_sql(f"DELETE FROM prescript WHERE CaseKey = {in_case_key}")
    _insert_traditional_health_care_prescript(
        database, system_settings, in_case_key, traditional_health_care_fee
    )


def write_traditional_health_care(
    database,
    system_settings,
    in_case_key,
    traditional_health_care_fee=None,
    massager=None,
):
    case_key = insert_traditional_health_care_cases(
        database, in_case_key, traditional_health_care_fee, massager
    )

    if case_key is not None:
        insert_traditional_health_care_prescript(
            database, system_settings, case_key, traditional_health_care_fee
        )


def insert_traditional_health_care_cases(
    database, in_case_key, traditional_health_care_fee, massager
):
    sql = f"""
        SELECT
            CaseDate, Period, PatientKey, Name, DesignatedMassager, Room,
            Visit, RegistType, Injury, Share, RegistNo, Massager, Register
        FROM cases
        WHERE
            CaseKey = {in_case_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    row = rows[0]

    ins_type = "自費"
    treat_type = "民俗調理"
    case_date = row["CaseDate"]
    period = string_utils.xstr(row["Period"])
    patient_key = row["PatientKey"]
    patient_name = string_utils.xstr(row["Name"])
    designated_massager = row["DesignatedMassager"]
    room = row["Room"]
    visit = string_utils.xstr(row["Visit"])
    reg_type = string_utils.xstr(row["RegistType"])
    injury_type = string_utils.xstr(row["Injury"])
    share_type = string_utils.xstr(row["Share"])
    reg_no = string_utils.xstr(row["RegistNo"])
    registrar = string_utils.xstr(row["Register"])

    delete_traditional_health_care(database, in_case_key)

    fields = [
        "CaseDate",
        "DoctorDate",
        "ChargeDate",
        "PatientKey",
        "Name",
        "Visit",
        "RegistType",
        "Injury",
        "Share",
        "InsType",
        "TreatType",
        "Period",
        "ChargePeriod",
        "Room",
        "RegistNo",
        "Massager",
        "Register",
        "DesignatedMassager",
        "SMassageFee",
        "SelfTotalFee",
        "TotalFee",
        "ReceiptFee",
        "DoctorDone",
        "ChargeDone",
        "Position1",
        "ApplyType",
        "PharmacyType",
    ]

    data = [
        case_date,
        case_date,
        case_date,
        patient_key,
        patient_name,
        visit,
        reg_type,
        injury_type,
        share_type,
        ins_type,
        treat_type,
        period,
        period,
        room,
        reg_no,
        massager,
        registrar,
        designated_massager,
        traditional_health_care_fee,
        traditional_health_care_fee,
        traditional_health_care_fee,
        traditional_health_care_fee,
        "True",
        "True",
        in_case_key,
        "申報",
        "申報",
    ]

    case_key = database.insert_record("cases", fields, data)

    return case_key


def insert_traditional_health_care_prescript(
    database,
    system_settings,
    case_key,
    traditional_health_care_fee,
    folk_massage_name=None,
):
    medicine_set = 2
    if folk_massage_name is None:
        folk_massage_name = prescript_utils.get_folk_massage_name(system_settings)

    fields = [
        "PrescriptNo",
        "CaseKey",
        "CaseDate",
        "MedicineSet",
        "MedicineType",
        "MedicineKey",
        "MedicineName",
        "Dosage",
        "Unit",
        "Price",
        "Amount",
    ]

    data = [
        1,
        case_key,
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        medicine_set,
        "處置",
        0,
        folk_massage_name,
        1,
        "次",
        traditional_health_care_fee,
        traditional_health_care_fee,
    ]
    database.insert_record("prescript", fields, data)


def remove_traditional_health_care_prescript(
    database, system_settings, case_key, medicine_set=2, folk_massage_name=None
):
    if folk_massage_name is None:
        folk_massage_name = prescript_utils.get_folk_massage_name(system_settings)

    sql = f'''
        DELETE FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set} AND
            MedicineName = "{folk_massage_name}"
    '''
    database.exec_sql(sql)


def insert_prescript(
    database, case_key, medicine_type, medicine_name, dosage, unit, fee
):
    medicine_set = 2

    fields = [
        "PrescriptNo",
        "CaseKey",
        "CaseDate",
        "MedicineSet",
        "MedicineType",
        "MedicineKey",
        "MedicineName",
        "Dosage",
        "Unit",
        "Price",
        "Amount",
    ]

    data = [
        1,
        case_key,
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        medicine_set,
        medicine_type,
        0,
        medicine_name,
        dosage,
        unit,
        fee,
        dosage * fee,
    ]
    database.insert_record("prescript", fields, data)


def get_case_date(database, case_key):
    sql = f"SELECT CaseDate, Period FROM cases WHERE CaseKey = {case_key}"
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None, None

    row = rows[0]
    return row["CaseDate"], string_utils.xstr(row["Period"])


def get_first_course_field(
    database, case_date, patient_key, card, field, treat_item=None
):

    end_date = f"{case_date} 00:00:00"

    if treat_item == "AH":  # home care
        last_month = datetime.date(case_date.year, case_date.month, 1).replace(day=1)
        start_date = f"{last_month} 00:00:00"
        sql = f'''
            SELECT CaseDate, Name, {field} FROM cases
            WHERE
                PatientKey = {patient_key} AND
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                Card = "{card}" AND
                TreatType = "居家醫療"
            ORDER BY CaseDate LIMIT 1
        '''
    else:
        last_month = (
            datetime.date(case_date.year, case_date.month, 1) - datetime.timedelta(1)
        ).replace(day=1)
        start_date = f"{last_month} 00:00:00"
        sql = f'''
            SELECT {field} FROM cases
            WHERE
                PatientKey = {patient_key} AND
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                Card = "{card}" AND
                Continuance = 1
            ORDER BY CaseDate LIMIT 1
        '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        first_date = None
    else:
        first_date = rows[0][field]

    return first_date


def get_first_treat_date(database, case_date, patient_key, treat_type):
    if patient_key is None:
        return case_date

    sql = f'''
        SELECT CaseDate FROM cases
        WHERE
            PatientKey = {patient_key} AND
            TreatType = "{treat_type}"
        ORDER BY CaseDate LIMIT 1
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        init_date = case_date
    else:
        init_date = rows[0]["CaseDate"]

    return init_date


def is_traditional_health_case(database, case_key):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key} AND
            TreatType = "民俗調理" OR
            Position1 = {case_key}
        LIMIT 1
    """
    rows = database.select_record(sql)
    if len(rows) > 0:
        return True
    else:
        return False


def is_self_traditional_health_case(database, case_key):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key} AND
            SMassageFee > 0
        LIMIT 1
    """
    rows = database.select_record(sql)
    if len(rows) > 0:
        return True
    else:
        return False


def get_electrical_prescript_status(database, case_key):
    sql = f"""
        SELECT * FROM caseextend
        WHERE
            CaseKey = {case_key} AND
            ExtendType = "電子處方箋"
    """
    rows = database.select_record(sql)
    if len(rows) > 0:
        return "Y"
    else:
        return None


def set_electrical_prescript_status(database, case_key):
    sql = f"""
        SELECT * FROM caseextend
        WHERE
            CaseKey = {case_key} AND
            ExtendType = "電子處方箋"
    """
    rows = database.select_record(sql)
    if len(rows) > 0:
        return

    fields = ["CaseKey", "ExtendType", "Content"]
    data = [
        case_key,
        "電子處方箋",
        datetime.datetime.now(),
    ]
    database.insert_record("caseextend", fields, data)


def clear_case_extend(database, case_key, extend_type):
    sql = f'''
        DELETE FROM caseextend
        WHERE
            CaseKey = {case_key} AND
            ExtendType = "{extend_type}"
    '''
    database.exec_sql(sql)


def set_case_extend(database, case_key, extend_type, content):
    sql = f'''
        SELECT * FROM caseextend
        WHERE
            CaseKey = {case_key} AND
            ExtendType = "{extend_type}"
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        sql = f'''
            DELETE FROM caseextend
            WHERE
                CaseKey = {case_key} AND
                ExtendType = "{extend_type}"
        '''
        database.exec_sql(sql)

    fields = ["CaseKey", "ExtendType", "Content"]
    data = [
        case_key,
        extend_type,
        content,
    ]
    database.insert_record("caseextend", fields, data)


def get_case_extend(database, case_key, extend_type):
    content = None

    sql = f'''
        SELECT * FROM caseextend
        WHERE
            CaseKey = {case_key} AND
            ExtendType = "{extend_type}"
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        row = rows[0]
        content = string_utils.xstr(row["Content"])

    return content


# 取得病歷html格式
def get_medical_record_html_from_json(database, system_settings, backup_records_key):
    sql = f"""
        SELECT * FROM backup_records
        WHERE
            BackupRecordsKey = {backup_records_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    row = rows[0]
    json_medical_record = json.loads(row["JSON"])[0]

    # medical_record = f'<b>編輯日期</b>: {row["DeleteDateTime"]} <b>編輯者</b>: {row["Editor"]}<br>'
    medical_record = f"<b>編輯日期</b>: {row['DeleteDateTime']}<br>"

    case_date = json_medical_record["CaseDate"]
    if json_medical_record["InsType"] == "健保":
        ins_type = str(json_medical_record["Card"])
        injury_type = string_utils.xstr(json_medical_record["Injury"])
        share_type = string_utils.xstr(json_medical_record["Share"])

        if number_utils.get_integer(json_medical_record["Continuance"]) >= 1:
            ins_type += "-" + str(json_medical_record["Continuance"])

        if injury_type == "主訴職災":
            share_type = f'<font color="red">{injury_type}</font>'
        elif share_type == "榮民":
            share_type = f'<font color="green">{share_type}</font>'
        elif share_type in ["低收入戶", "中低收入戶"]:
            share_type = f'<font color="darkMagenta">{share_type}</font>'

        ins_type = f"<b>健保</b>: {ins_type} {share_type}"
    else:
        ins_type = "<b>自費</b>"

    doctor = string_utils.xstr(json_medical_record["Doctor"])
    medical_record += f"<b>日期</b>: {case_date} {ins_type} <b>醫師</b>:{doctor}<hr>"

    symptom = string_utils.get_str(json_medical_record["Symptom"], "utf8")
    tongue = string_utils.get_str(json_medical_record["Tongue"], "utf8")
    pulse = string_utils.get_str(json_medical_record["Pulse"], "utf8")
    distincts = string_utils.get_str(json_medical_record["Distincts"], "utf8")
    cure = string_utils.get_str(json_medical_record["Cure"], "utf8")
    remark = string_utils.get_str(json_medical_record["Remark"], "utf8")

    disease_code1 = string_utils.xstr(json_medical_record["DiseaseCode1"])
    disease_name1 = string_utils.xstr(json_medical_record["DiseaseName1"])
    disease_code2 = string_utils.xstr(json_medical_record["DiseaseCode2"])
    disease_name2 = string_utils.xstr(json_medical_record["DiseaseName2"])
    disease_code3 = string_utils.xstr(json_medical_record["DiseaseCode3"])
    disease_name3 = string_utils.xstr(json_medical_record["DiseaseName3"])
    try:
        disease_code4 = string_utils.xstr(json_medical_record["DiseaseCode4"])
        disease_name4 = string_utils.xstr(json_medical_record["DiseaseName4"])
    except Exception:
        disease_code4 = ""
        disease_name4 = ""

    if symptom != "":
        medical_record += f"<b>主訴</b>: {symptom}<hr>"
    if tongue != "":
        medical_record += f"<b>舌診</b>: {tongue}<hr>"
    if pulse != "":
        medical_record += f"<b>脈象</b>: {pulse}<hr>"
    if distincts != "":
        medical_record += f"<b>辨證</b>: {distincts}<hr>"
    if cure != "":
        medical_record += f"<b>治則</b>: {cure}<hr>"
    if remark != "":
        medical_record += f"<b>備註</b>: {remark}<hr>"
    if disease_code1 != "":
        medical_record += f"<b>主診斷</b>: {disease_code1} {disease_name1}<br>"
    if disease_code2 != "":
        medical_record += f"<b>次診斷1</b>: {disease_code2} {disease_name2}<br>"
    if disease_code3 != "":
        medical_record += f"<b>次診斷2</b>: {disease_code3} {disease_name3}<br>"
    if disease_code4 != "":
        medical_record += f"<b>次診斷3</b>: {disease_code4} {disease_name4}<br>"

    medical_record = f"""
        <div style="width: 95%;">
            {medical_record}
        </div>
    """

    prescript_record = get_prescript_record_from_json(
        database, system_settings, backup_records_key, json_medical_record
    )

    html = f"""
        <html>
            <head>
                <meta charset="UTF-8">
            </head>
            <body>
                {medical_record}
                {prescript_record}
            </body>
        </html>
    """

    return html


def get_prescript_record_from_json(
    database, system_settings, backup_records_key, json_medical_record
):
    sql = f"""
        SELECT * FROM backup_records
        WHERE
            TableName = "prescript" AND
            KeyField = "BackupRecordsKey" AND
            KeyValue = {backup_records_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return "<br><br><br><center>無開立處方</center><br>"

    row = rows[0]

    json_rows = json.loads(row["JSON"])
    dosage_mode = system_settings.field("劑量模式")
    html = get_prescript_medicine_record_from_json(
        database,
        system_settings,
        backup_records_key,
        json_rows,
        dosage_mode,
        medicine_set=1,
    )
    html += get_ins_prescript_treat_record_from_json(
        database, backup_records_key, json_rows, dosage_mode, json_medical_record
    )
    html += get_self_prescript_medicine_record_from_json(
        database, system_settings, backup_records_key, json_rows, dosage_mode
    )

    return html


def get_prescript_medicine_record_from_json(
    database, system_settings, backup_records_key, json_rows, dosage_mode, medicine_set
):
    prescript_data, total_dosage, total_fee, single_day_dosage = (
        get_prescript_html_data_from_json(
            database, backup_records_key, json_rows, dosage_mode, medicine_set
        )
    )

    if prescript_data == "":
        return ""

    prescript_data += get_dosage_html_from_json(
        database,
        system_settings,
        backup_records_key,
        medicine_set,
        total_dosage,
        total_fee,
    )

    if medicine_set == 1:
        prescript_heading = "健保處方"
    else:
        prescript_heading = f"自費處方{medicine_set - 1}"

    prescript_html = f"""
        <table align=center cellpadding="2" cellspacing="0" width="98%"
         style="border-width: 1px; border-style: solid;">
            <thead>
                <tr bgcolor="LightGray">
                    <th style="text-align: center; padding-left: 8px" width="10%">序</th>
                    <th style="padding-left: 8px" width="50%" align="left">{prescript_heading}</th>
                    <th style="padding-right: 8px" align="right" width="25%">劑量</th>
                    <th style="padding-left: 8px" align="left" width="15%">指示</th>
                </tr>
            </thead>
            <tbody>
                {prescript_data}
            </tbody>
        </table>
        <br>
    """

    return prescript_html


def get_dosage_html_from_json(
    database, system_settings, backup_records_key, medicine_set, total_dosage, total_fee
):
    dosage_data = ""

    sql = f"""
        SELECT * FROM backup_records
        WHERE
            TableName = "dosage" AND
            KeyField = "BackupRecordsKey" AND
            KeyValue = {backup_records_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return ""

    json_rows = json.loads(rows[0]["JSON"])
    row = None
    for json_row in json_rows:
        if json_row["MedicineSet"] == medicine_set:
            row = json_row
            break

    if row is None:
        return ""

    pres_days = number_utils.get_integer(row["Days"])
    packages = number_utils.get_integer(row["Packages"])
    try:
        self_total_fee = number_utils.get_integer(row["SelfTotalFee"])
    except KeyError:
        self_total_fee = None

    if packages > 0 or pres_days > 0:
        instruction = string_utils.xstr(row["Instruction"])
        dosage_data = f"""
            <tr>
                <td style="text-align: left; padding-left: 30px;" colspan="4">
                    用法: {packages}包 {pres_days}日份 {instruction}服用 總量: {total_dosage}
                </td>
            </tr>
        """

    if (
        self_total_fee is not None
        and self_total_fee > 0
        and system_settings.field("手動批價") != "Y"
    ):
        discount_rate = number_utils.get_integer(row["DiscountRate"])
        discount_fee = number_utils.get_integer(row["DiscountFee"])
        total_fee -= discount_fee

        dosage_total_fee = number_utils.get_integer(row["TotalFee"])
        dosage_td = f"""
            自費合計: ${self_total_fee:,} 優待: {discount_rate}% 折扣金額: ${discount_fee:,}
            應收金額: ${dosage_total_fee:,}
        """
        if dosage_total_fee != total_fee:
            dosage_td += f"""
                <br>
                <font color="red">
                    請注意! 病歷資料自費處方{medicine_set - 1}的檢核金額為${int(total_fee)},
                    與應收金額${dosage_total_fee}金額不相符.  請進入病歷內重新存檔.
                </font>
            """

        dosage_data += f"""
            <tr>
                <td style="text-align: left; padding-left: 30px;" colspan="4">
                    {dosage_td}
                </td>
            </tr>
        """

    return dosage_data


def get_prescript_html_data_from_json(
    database, backup_records_key, json_rows, dosage_mode, medicine_set, treatment=None
):
    prescript_data = ""
    total_dosage = 0.0
    total_fee = 0.0
    single_day_dosage = 0.0

    sequence = 0
    total_amount = 0.0
    pres_days = get_pres_days_from_json(database, backup_records_key, medicine_set)
    if pres_days <= 0:
        pres_days = 1

    for row in json_rows:
        current_medicine_set = row["MedicineSet"]
        if current_medicine_set != medicine_set:
            continue

        medicine_type = string_utils.xstr(row["MedicineType"])

        if medicine_set == 1:
            if treatment is None and medicine_type in ["穴道", "處置", "檢驗"]:
                continue

            if treatment is not None and medicine_type not in ["穴道", "處置", "檢驗"]:
                continue

        if string_utils.xstr(row["MedicineName"]) in ["", "優待"]:
            continue

        sequence += 1

        dosage = number_utils.get_float(row["Dosage"])
        single_day_dosage += dosage

        if dosage is None or dosage == 0.00:
            dosage_str = ""
        else:
            if dosage_mode in ["日劑量", "總量"]:
                dosage_str = f"{dosage:.1f}"
            elif dosage_mode in ["次劑量"]:
                dosage_str = f"{dosage:.2f}"
            else:
                dosage_str = string_utils.xstr(dosage)

            total_dosage += dosage

        unit = string_utils.xstr(row["Unit"])
        instruction = string_utils.xstr(row["Instruction"])
        try:
            amount = number_utils.get_float(row["Amount"])
        except Exception:
            amount = 0

        total_amount += amount

        if medicine_set >= 2:
            font_color = "color: navy"
        else:
            font_color = ""

        medicine_name = string_utils.xstr(row["MedicineName"])
        prescript_data += f"""
            <tr>
                <td align="center" style="padding-right: 8px; {font_color}">{sequence}</td>
                <td style="padding-left: 8px; {font_color}">{medicine_name}</td>
                <td align="right" style="padding-right: 8px; {font_color}">{dosage_str} {unit}</td>
                <td style="padding-left: 8px; {font_color}">{instruction}</td>
            </tr>
        """

    total_fee = number_utils.round_up(total_amount * pres_days)
    return prescript_data, round(total_dosage, 3), total_fee, single_day_dosage


def get_pres_days_from_json(database, backup_records_key, medicine_set=1):
    sql = f"""
        SELECT * FROM backup_records
        WHERE
            TableName = "dosage" AND
            KeyField = "BackupRecordsKey" AND
            KeyValue = {backup_records_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return 0

    json_rows = json.loads(rows[0]["JSON"])
    pres_days = 0
    for row in json_rows:
        if row["MedicineSet"] == medicine_set:
            pres_days = number_utils.get_integer(row["Days"])
            break

    return pres_days


def get_packages_from_json(database, backup_records_key, medicine_set=1):
    sql = f"""
        SELECT * FROM backup_records
        WHERE
            TableName = "dosage" AND
            KeyField = "BackupRecordsKey" AND
            KeyValue = {backup_records_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return 0

    json_rows = json.loads(rows[0]["JSON"])
    packages = 0
    for row in json_rows:
        if row["MedicineSet"] == medicine_set:
            packages = number_utils.get_integer(row["Packages"])
            break

    return packages


def get_instruction_from_json(database, backup_records_key, medicine_set=1):
    sql = f"""
        SELECT * FROM backup_records
        WHERE
            TableName = "dosage" AND
            KeyField = "BackupRecordsKey" AND
            KeyValue = {backup_records_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return 0

    json_rows = json.loads(rows[0]["JSON"])
    instruction = ""
    for row in json_rows:
        if row["MedicineSet"] == medicine_set:
            instruction = string_utils.xstr(row["Instruction"])
            break

    return instruction


def get_discount_rate_from_json(database, backup_records_key, medicine_set):
    sql = f"""
        SELECT * FROM backup_records
        WHERE
            TableName = "dosage" AND
            KeyField = "BackupRecordsKey" AND
            KeyValue = {backup_records_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return 100

    json_rows = json.loads(rows[0]["JSON"])

    discount_rate = 100
    for row in json_rows:
        if row["MedicineSet"] == medicine_set:
            discount_rate = number_utils.get_integer(row["DiscountRate"])
            break

    return discount_rate


def get_ins_prescript_treat_record_from_json(
    database, backup_records_key, json_rows, dosage_mode, json_medical_record
):
    prescript_html = ""

    treatment = string_utils.xstr(json_medical_record["Treatment"])

    if treatment == "":
        return prescript_html

    treatment_data = f"""
        <tr>
            <td align="center" style="padding-right: 8px;">*</td>
            <td style="padding-left: 8px;">{treatment}</td>
            <td align="right" style="padding-right: 8px">1 次</td>
            <td style="padding-left: 8px;"></td>
        </tr>
    """
    prescript_data, _, _, _ = get_prescript_html_data_from_json(
        database, backup_records_key, json_rows, dosage_mode, 1, True
    )

    prescript_html = f"""
        <table align=center cellpadding="2" cellspacing="0" width="98%"
         style="border-width: 1px; border-style: solid;">
            <thead>
                <tr bgcolor="LightGray">
                    <th style="text-align: center; padding-left: 8px" width="10%">序</th>
                    <th style="padding-left: 8px" width="50%" align="left">健保處置</th>
                    <th style="padding-right: 8px" align="right" width="25%">次數</th>
                    <th style="padding-left: 8px" align="left" width="15%">備註</th>
                </tr>
            </thead>
            <tbody>
                {treatment_data}
                {prescript_data}
            </tbody>
        </table>
        <br>
    """

    return prescript_html


def get_max_medicine_set_from_json(json_rows):
    max_medicine_set = None

    for row in json_rows:
        medicine_set = row["MedicineSet"]
        if medicine_set > number_utils.get_integer(max_medicine_set):
            max_medicine_set = medicine_set

    return max_medicine_set


def get_self_prescript_medicine_record_from_json(
    database, system_settings, backup_records_key, json_rows, dosage_mode
):
    prescript_html = ""

    max_medicine_set = get_max_medicine_set_from_json(json_rows)
    if max_medicine_set is None:
        return prescript_html

    for medicine_set in range(2, max_medicine_set + 1):
        prescript_html = get_prescript_medicine_record_from_json(
            database,
            system_settings,
            backup_records_key,
            json_rows,
            dosage_mode,
            medicine_set,
        )
    return prescript_html


def get_regist_type_sql(regist_type):
    if regist_type == "全部":
        sql = ""
    elif regist_type == "院內門診":
        nhi_regist_type = set(nhi_utils.REG_TYPE).difference(
            nhi_utils.LONG_TERM_CARE + nhi_utils.TOUR_TYPE
        )
        sql = f"""
            AND (cases.RegistType IN {tuple(nhi_regist_type)} OR
                 cases.RegistType IS NULL OR
                 LENGTH(RegistType) = 0
                )
        """
    elif regist_type == "院外出診":
        nhi_regist_type = nhi_utils.LONG_TERM_CARE + nhi_utils.TOUR_TYPE
        sql = f"AND cases.RegistType IN {tuple(nhi_regist_type)}"
    else:
        sql = f'AND cases.RegistType = "{regist_type}"'

    return sql


# 2024.02.05 更新
def get_last_highly_complicated_massage_date(
    database,
    case_date,
    patient_key,
    disease_code1,
    disease_code2=None,
    disease_code3=None,
    disease_code4=None,
):
    case_end_date = f"{case_date.date()} 00:00:00"

    days_list = [90, 180]
    last_date = None
    for i in range(2):
        days = days_list[i]
        case_start_date = f"{case_date.date() - datetime.timedelta(days)} 00:00:00"
        sql = f'''
            SELECT CaseDate, DiseaseCode1, DiseaseCode2, DiseaseCode3, DiseaseCode4 FROM cases
            WHERE
                PatientKey = {patient_key} AND
                CaseDate BETWEEN "{case_start_date}" AND "{case_end_date}" AND
                Treatment IN (
                    "高度複雜性傷科",
                    "一般針灸合併高度傷科起始次", "電針合併高度傷科起始次",
                    "中度針灸合併高度傷科起始次", "高度針灸合併高度傷科起始次",
                    "中度複雜性傷科合併特殊疾病",
                    "一般針灸合併高度傷科", "中度針灸合併高度傷科", "高度針灸合併高度傷科"
                    "一般針灸合併中度傷科合併特殊疾病起始次",
                    "一般針灸合併中度傷科合併特殊疾病後續治療",
                    "中度針灸合併中度傷科合併特殊疾病起始次",
                    "中度針灸合併中度傷科合併特殊疾病後續治療",
                    "高度針灸合併中度傷科合併特殊疾病起始次",
                    "高度針灸合併中度傷科合併特殊疾病後續治療"
                )
            ORDER BY CaseDate LIMIT 1
        '''
        rows = database.select_record(sql)  # 三個月不同病名或六個月同病名
        if len(rows) > 0:
            row = rows[0]

            if (
                disease_code1 == string_utils.xstr(row["DiseaseCode1"]) and days == 180
            ) or days == 90:
                last_date = row["CaseDate"].date()
                break

        # if len(rows) > 0:
        #     row = rows[0]
        #     disease_list = []
        #     if string_utils.xstr(row['DiseaseCode1']) != '':
        #         disease_list.append(string_utils.xstr(row['DiseaseCode1']))
        #     if string_utils.xstr(row['DiseaseCode2']) != '':
        #         disease_list.append(string_utils.xstr(row['DiseaseCode2']))
        #     if string_utils.xstr(row['DiseaseCode3']) != '':
        #         disease_list.append(string_utils.xstr(row['DiseaseCode3']))
        #     if string_utils.xstr(row['DiseaseCode4']) != '':
        #         disease_list.append(string_utils.xstr(row['DiseaseCode4']))

        #     if disease_code1 != '' and disease_code1 in disease_list or \
        #             disease_code2 != '' and disease_code2 in disease_list or \
        #             disease_code3 != '' and disease_code3 in disease_list or \
        #             disease_code4 != '' and disease_code4 in disease_list:
        #         last_date = row['CaseDate'].date()
        #         break

    return last_date


# 取得病歷html格式
def get_medical_record_json_html(database, system_settings, extension_json_key):
    sql = f"""
        SELECT * FROM extension_json
        WHERE
            ExtensionJSONKey = {extension_json_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]

    medical_record_row = json.loads(row["JSON"])["diagnostic"]
    case_date = string_utils.xstr(row["TimeStamp"].date())
    medical_record = f"<b>日期</b>: {case_date}<br>"

    symptom = string_utils.get_str(medical_record_row["symptom"], "utf8")
    tongue = string_utils.get_str(medical_record_row["tongue"], "utf8")
    pulse = string_utils.get_str(medical_record_row["pulse"], "utf8")
    distincts = string_utils.get_str(medical_record_row["distinguish"], "utf8")
    cure = string_utils.get_str(medical_record_row["cure"], "utf8")
    remark = string_utils.get_str(medical_record_row["remark"], "utf8")

    disease_code1 = string_utils.xstr(medical_record_row["disease_code1"])
    disease_name1 = case_utils.get_disease_name(database, disease_code1)
    disease_code2 = string_utils.xstr(medical_record_row["disease_code2"])
    disease_name2 = case_utils.get_disease_name(database, disease_code2)
    disease_code3 = string_utils.xstr(medical_record_row["disease_code3"])
    disease_name3 = case_utils.get_disease_name(database, disease_code3)

    try:
        disease_code4 = string_utils.xstr(medical_record_row["disease_code4"])
        disease_name4 = case_utils.get_disease_name(database, disease_code4)
    except Exception:
        disease_code4 = ""
        disease_name4 = ""

    if symptom != "":
        medical_record += f"<b>主訴</b>: {symptom}<hr>"
    if tongue != "":
        medical_record += f"<b>舌診</b>: {tongue}<hr>"
    if pulse != "":
        medical_record += f"<b>脈象</b>: {pulse}<hr>"
    if distincts != "":
        medical_record += f"<b>辨證</b>: {distincts}<hr>"
    if cure != "":
        medical_record += f"<b>治則</b>: {cure}<hr>"
    if remark != "":
        medical_record += f"<b>備註</b>: {remark}<hr>"
    if disease_code1 != "":
        medical_record += f"<b>主診斷</b>: {disease_code1} {disease_name1}<br>"
    if disease_code2 != "":
        medical_record += f"<b>次診斷1</b>: {disease_code2} {disease_name2}<br>"
    if disease_code3 != "":
        medical_record += f"<b>次診斷2</b>: {disease_code3} {disease_name3}<br>"
    if disease_code4 != "":
        medical_record += f"<b>次診斷3</b>: {disease_code4} {disease_name4}<br>"

    medical_record = f"""
        <div style="width: 95%;">
            {medical_record}
        </div>
    """

    prescript_record = get_prescript_json_record(database, system_settings, row)

    html = f"""
        <html>
            <head>
                <meta charset="UTF-8">
            </head>
            <body>
                {medical_record}
                {prescript_record}
            </body>
        </html>
    """

    return html


def get_prescript_json_record(database, system_settings, row):
    prescript_rows = json.loads(row["JSON"])["prescript"]
    if len(prescript_rows) <= 0:
        return "<br><br><br><center>無開立處方</center><br>"

    html = get_prescript_medicine_json_record(database, system_settings, row, 1)
    html += get_ins_prescript_treat_json_record(database, system_settings, row)
    # html += get_self_prescript_medicine_record(database, system_settings, case_key)

    return html


def get_prescript_medicine_json_record(database, system_settings, row, medicine_set):
    prescript_data, total_dosage, total_fee = get_prescript_json_html_data(
        database, system_settings, row, medicine_set
    )

    if prescript_data == "":
        return ""

    prescript_data += get_dosage_json_html(
        database, row, medicine_set, total_dosage, total_fee
    )
    if medicine_set == 1:
        prescript_heading = "健保處方"
    else:
        prescript_heading = f"自費處方{medicine_set - 1}"

    prescript_html = f"""
        <table align=center cellpadding="2" cellspacing="0" width="98%"
         style="border-width: 1px; border-style: solid;">
            <thead>
                <tr bgcolor="LightGray">
                    <th style="text-align: center; padding-left: 8px" width="10%">序</th>
                    <th style="padding-left: 8px" width="50%" align="left">{prescript_heading}</th>
                    <th style="padding-right: 8px" align="right" width="25%">劑量</th>
                    <th style="padding-left: 8px" align="left" width="15%">指示</th>
                </tr>
            </thead>
            <tbody>
                {prescript_data}
            </tbody>
        </table>
        <br>
    """

    return prescript_html


def get_json_pres_days(database, row, medicine_set=1):
    dosage_rows = json.loads(row["JSON"])["dosage"]

    pres_days = 0
    if len(dosage_rows) <= 0:
        return 0

    for dosage_row in dosage_rows:
        if number_utils.get_integer(dosage_row["medicine_set"]) == medicine_set:
            pres_days = number_utils.get_integer(dosage_row["presdays"])
            break

    return pres_days


def get_json_packages(database, row, medicine_set=1):
    dosage_rows = json.loads(row["JSON"])["dosage"]

    package = 0
    if len(dosage_rows) <= 0:
        return 0

    for dosage_row in dosage_rows:
        if number_utils.get_integer(dosage_row["medicine_set"]) == medicine_set:
            package = number_utils.get_integer(dosage_row["package"])
            break

    return package


def get_json_instruction(database, row, medicine_set=1):
    dosage_rows = json.loads(row["JSON"])["dosage"]

    instruction = None
    if len(dosage_rows) <= 0:
        return None

    for dosage_row in dosage_rows:
        if number_utils.get_integer(dosage_row["medicine_set"]) == medicine_set:
            instruction = string_utils.xstr(dosage_row["instruction"])
            break

    return instruction


def get_prescript_json_html_data(
    database, system_settings, row, medicine_set, treatment=None
):
    prescript_data = ""
    total_dosage = 0.0
    total_fee = 0.0

    prescript_rows = json.loads(row["JSON"])["prescript"]
    if len(prescript_rows) <= 0:
        return prescript_data, total_dosage, total_fee

    sequence = 0
    total_amount = 0.0
    pres_days = get_json_pres_days(database, row, medicine_set)
    if pres_days <= 0:
        pres_days = 1

    for row in prescript_rows:
        medicine_name = string_utils.xstr(row["medicine_name"])
        medicine_type = string_utils.xstr(row["medicine_type"])
        if medicine_name in ["", "優待"]:
            continue

        if treatment is not None and medicine_type not in ["穴道", "處置"]:
            continue
        elif treatment is None and medicine_type in ["穴道", "處置"]:
            continue

        sequence += 1

        dosage = number_utils.get_float(row["dosage"])

        if dosage is None or dosage == 0.00:
            dosage_str = ""
        else:
            if system_settings.field("劑量模式") in ["日劑量", "總量"]:
                dosage_str = f"{dosage:.1f}"
            elif system_settings.field("劑量模式") in ["次劑量"]:
                dosage_str = f"{dosage:.2f}"
            else:
                dosage_str = string_utils.xstr(dosage)

            total_dosage += dosage

        unit = string_utils.xstr(row["unit"])
        instruction = ""

        # try:
        #     amount = number_utils.get_float(row['Amount'])
        # except Exception:
        #     amount = 0
        amount = 0

        total_amount += amount

        if medicine_set >= 2:
            font_color = "color: navy"
        else:
            font_color = ""

        prescript_data += f"""
            <tr>
                <td align="center" style="padding-right: 8px; {font_color}">{sequence}</td>
                <td style="padding-left: 8px; {font_color}">{medicine_name}</td>
                <td align="right" style="padding-right: 8px; {font_color}">{dosage_str} {unit}</td>
                <td style="padding-left: 8px; {font_color}">{instruction}</td>
            </tr>
        """

    total_fee = number_utils.round_up(total_amount * pres_days)
    return prescript_data, round(total_dosage, 3), total_fee


def get_dosage_json_html(database, row, medicine_set, total_dosage, total_fee):
    dosage_data = ""

    dosage_rows = json.loads(row["JSON"])["dosage"]

    packages = 0
    pres_days = 0
    instruction = ""

    if len(dosage_rows) <= 0:
        return dosage_data

    for dosage_row in dosage_rows:
        if number_utils.get_integer(dosage_row["medicine_set"]) == medicine_set:
            packages = number_utils.get_integer(dosage_row["package"])
            pres_days = number_utils.get_integer(dosage_row["presdays"])
            instruction = string_utils.xstr(dosage_row["instruction"])
            break

    dosage_data = f"""
        <tr>
            <td style="text-align: left; padding-left: 30px;" colspan="4">
                用法: {packages}包 {pres_days}日份 {instruction}服用 總量: {total_dosage}
            </td>
        </tr>
    """

    return dosage_data


def get_ins_prescript_treat_json_record(database, system_settings, row):
    prescript_html = ""

    medical_record_row = json.loads(row["JSON"])["diagnostic"]
    treatment = string_utils.xstr(medical_record_row["treatment"])

    if treatment == "":
        return prescript_html

    treatment_data = f"""
        <tr>
            <td align="center" style="padding-right: 8px;">*</td>
            <td style="padding-left: 8px;">{treatment}</td>
            <td align="right" style="padding-right: 8px">1 次</td>
            <td style="padding-left: 8px;"></td>
        </tr>
    """
    prescript_data, _, _ = get_prescript_json_html_data(
        database, system_settings, row, 1, treatment
    )

    prescript_html = f"""
        <table align=center cellpadding="2" cellspacing="0" width="98%"
         style="border-width: 1px; border-style: solid;">
            <thead>
                <tr bgcolor="LightGray">
                    <th style="text-align: center; padding-left: 8px" width="10%">序</th>
                    <th style="padding-left: 8px" width="50%" align="left">健保處置</th>
                    <th style="padding-right: 8px" align="right" width="25%">次數</th>
                    <th style="padding-left: 8px" align="left" width="15%">備註</th>
                </tr>
            </thead>
            <tbody>
                {treatment_data}
                {prescript_data}
            </tbody>
        </table>
        <br>
    """

    return prescript_html


# 拷貝自訂參考病歷
def copy_medical_record_json(
    database,
    system_settings,
    medical_record,
    extension_json_key,
    copy_diagnostic,
    copy_remark,
    copy_disease,
    copy_ins_prescript,
    copy_ins_prescript_to,
    copy_ins_treat,
    copy_self_prescript,
    not_overwrite=False,
):

    sql = f"""
        SELECT * FROM extension_json
        WHERE
            ExtensionJSONKey = {extension_json_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    json_row = rows[0]

    medical_record_row = json.loads(json_row["JSON"])["diagnostic"]
    try:
        case_key = medical_record_row["case_key"]
    except Exception:
        case_key = None

    ui = medical_record.ui
    if copy_diagnostic:
        symptom = string_utils.get_str(medical_record_row["symptom"], "utf8")
        tongue = string_utils.get_str(medical_record_row["tongue"], "utf8")
        pulse = string_utils.get_str(medical_record_row["pulse"], "utf8")
        distinguish = string_utils.get_str(medical_record_row["distinguish"], "utf8")
        cure = string_utils.get_str(medical_record_row["cure"], "utf8")

        ui.textEdit_symptom.setText(symptom)
        ui.textEdit_tongue.setText(tongue)
        ui.textEdit_pulse.setText(pulse)
        ui.lineEdit_distinguish.setText(distinguish)
        ui.lineEdit_cure.setText(cure)

    if copy_remark:
        remark = string_utils.get_str(medical_record_row["remark"], "utf8")
        ui.textEdit_remark.setText(remark)

    if copy_disease:
        disease_code1 = string_utils.xstr(medical_record_row["disease_code1"])
        disease_code2 = string_utils.xstr(medical_record_row["disease_code2"])
        disease_code3 = string_utils.xstr(medical_record_row["disease_code3"])
        disease_code4 = string_utils.xstr(medical_record_row["disease_code4"])
        disease_name1 = case_utils.get_disease_name(database, disease_code1)
        disease_name2 = case_utils.get_disease_name(database, disease_code2)
        disease_name3 = case_utils.get_disease_name(database, disease_code3)
        disease_name4 = case_utils.get_disease_name(database, disease_code4)
        disease_list = [
            [disease_code1, disease_name1],
            [disease_code2, disease_name2],
            [disease_code3, disease_name3],
            [disease_code4, disease_name4],
        ]

        line_edit_disease = [
            [ui.lineEdit_disease_code1, ui.lineEdit_disease_name1],
            [ui.lineEdit_disease_code2, ui.lineEdit_disease_name2],
            [ui.lineEdit_disease_code3, ui.lineEdit_disease_name3],
            [ui.lineEdit_disease_code4, ui.lineEdit_disease_name4],
        ]

        for i in range(len(line_edit_disease)):
            disease_code = disease_list[i][0]
            disease_name = disease_list[i][1]

            if disease_code.isdigit():
                disease_code = icd9_to_icd10(database, disease_code)

            line_edit_disease[i][0].setText(disease_code)
            line_edit_disease[i][1].setText(disease_name)

    if copy_ins_prescript:
        if copy_ins_prescript_to == "健保處方":
            if medical_record.tab_list[0] is not None:
                medical_record.tab_list[0].copy_prescript_json(extension_json_key)
                medical_record.tab_list[0].append_null_medicine()
        else:
            if medical_record.tab_list[1] is None:
                medical_record.add_prescript_tab(2)

            medical_record.tab_list[1].copy_prescript_json(extension_json_key, 1)
            medical_record.tab_list[1].append_null_medicine()

    if copy_ins_treat:
        if medical_record.tab_list[0] is not None:
            medical_record.tab_list[0].copy_past_treat(case_key, "病歷拷貝")
            medical_record.tab_list[0].append_null_treat()
        elif medical_record.ins_type == "自費":
            medical_record.tab_list[1].copy_past_treat(case_key)
            medical_record.tab_list[1].append_null_medicine()

    if copy_self_prescript:
        if not_overwrite:
            pass
        else:
            medical_record.close_all_self_prescript_tabs()  # 本來已經拿掉，後來會造成重複拷貝的狀況，2021.02.10 恢復

        sql = f"""
            SELECT MedicineSet FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2
            GROUP BY MedicineSet ORDER BY MedicineSet
        """
        rows = database.select_record(sql)

        for json_row in rows:
            medicine_set = json_row["MedicineSet"]

            if medicine_set == 11:
                continue

            tab_index = medicine_set - 1
            if (
                medical_record.tab_list[tab_index] is None
                or medical_record.tab_list[tab_index].tableWidget_prescript.item(
                    0, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
                )
                is None
            ):
                medical_record.add_prescript_tab(medicine_set)
            else:
                if (
                    medical_record.tab_list[tab_index].tableWidget_prescript.rowCount()
                    > 0
                ):  # 原本的自費處方已被拷貝佔用
                    medical_record.add_prescript_tab(medicine_set + 1)
                    tab_index += 1

            medical_record.tab_list[tab_index].copy_past_prescript(
                case_key, medicine_set
            )
            medical_record.tab_list[tab_index].append_null_medicine()

    if system_settings.field("健保自費分開") == "Y":
        pass
    elif (
        medical_record.tab_list[1] is None
    ):  # 2019.04.27 拷貝完, 清除所有自費處方後, 自動新增自費處方1
        medical_record.add_prescript_tab()
        medical_record.tab_list[1].append_null_medicine()
        medical_record.ui.tabWidget_prescript.setCurrentIndex(0)


def get_ic_card_type(database, case_key):
    ic_card_type = get_case_extend(database, case_key, "健保卡種類")
    if ic_card_type is None:
        ic_card_type = "一般卡"

    return ic_card_type


def get_regist_type_exclude_sql(option, exclude=True):
    regist_condition = [""]

    if "資源不足" in option:
        regist_condition.append(
            f" {tuple(nhi_utils.TOUR_FAR + nhi_utils.AT_LACK_AREA + nhi_utils.GOTO_LACK_AREA)} "
        )

    if "巡迴醫療" in option:
        regist_condition.append(f" {tuple(nhi_utils.TOUR_MOUNTAIN_ISLAND)} ")

    if "法定傳染病" in option:
        regist_condition.append(
            f" {tuple(nhi_utils.INFECTIOUS_TYPE + nhi_utils.INFECTIOUS_TYPE)} "
        )

    if "視訊門診" in option:
        regist_condition.append(f" {tuple(nhi_utils.TELECOM_TYPE)} ")

    if "照護機構" in option:
        regist_condition.append(
            f" {tuple(nhi_utils.LONG_TERM_CARE + nhi_utils.LONG_TERM_CARE)} "
        )

    if exclude:
        regist_condition = " AND RegistType NOT IN ".join(regist_condition)
    else:
        regist_condition = " AND RegistType IN ".join(regist_condition)

    return regist_condition


# 取得星期過濾條件
def get_weekday_list_sql(weekday_list):
    weekday_condition = ""

    if len(weekday_list) > 0:
        weekday_condition = f" AND WEEKDAY(CaseDate) IN({','.join(weekday_list)})"

    return weekday_condition


def set_disease_tool_tip(
    database, disease_code, disease_name, complicated_treat_list=None
):
    icd_code = disease_code.text().strip()

    if icd_code == "":
        return

    sql = f'''
        SELECT ChineseName, EnglishName FROM icd10
        WHERE
            ICDCode = "{icd_code}"
        LIMIT 1
    '''
    try:
        rows = database.select_record(sql)
    except Exception:
        return

    if len(rows) <= 0:
        return

    row = rows[0]
    chinese_name = string_utils.xstr(row["ChineseName"])
    english_name = string_utils.xstr(row["EnglishName"])
    html = f"{chinese_name}<hr>{english_name}"

    moderate_complicated_acupuncture_list = complicated_treat_list[0]
    highly_complicated_acupuncture_list = complicated_treat_list[1]
    moderate_complicated_massage_list = complicated_treat_list[2]
    highly_complicated_massage_list = complicated_treat_list[3]
    special_disease_list = complicated_treat_list[4]
    dislocate_list = complicated_treat_list[5]
    fracture_list = complicated_treat_list[6]

    if icd_code in moderate_complicated_acupuncture_list:
        html += "<hr>符合中度複雜性針灸適應症"
    if icd_code in highly_complicated_acupuncture_list:
        html += "<hr>符合高度複雜性針灸適應症"
    if icd_code in moderate_complicated_massage_list:
        html += "<hr>符合中度複雜性傷科適應症"
    if icd_code in highly_complicated_massage_list:
        html += "<hr>符合高度複雜性傷科適應症"
    if icd_code in special_disease_list:
        html += "<hr>符合特殊疾病適應症"
    if icd_code in dislocate_list:
        html += "<hr>符合脫臼整復復位適應症"
    if icd_code in fracture_list:
        html += "<hr>符合骨折復位適應症"

    disease_code.setToolTip(html)
    disease_name.setToolTip(html)

    return html


def get_drug_no(database, system_settings, case_date):
    try:
        drug_no = number_utils.get_integer(system_settings.field("領藥起始號"))
    except Exception:
        drug_no = 1

    if drug_no == 0:
        drug_no = 1

    case_date = case_date.strftime("%Y-%m-%d")
    sql = f'''
        SELECT DrugNo FROM cases
        WHERE
            DATE(CaseDate) = "{case_date}" AND
            DrugNo > 0
        ORDER BY DrugNo DESC LIMIT 1
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return drug_no

    row = rows[0]
    drug_no = number_utils.get_integer(row["DrugNo"]) + 1

    return drug_no


def get_case_field_value(database, case_key, field_name):
    if case_key in ["", None]:
        return None

    sql = f"""
        SELECT {field_name} FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        field_value = None
    else:
        field_value = rows[0][field_name]

    return field_value


# 取得慢性病代碼
def get_chronic_code(database, icd_code):
    chronic_code = None

    if icd_code in ["", None]:
        return chronic_code

    sql = f'''
        SELECT SpecialCode FROM icd10
        WHERE
            ICDCode = "{icd_code}"
    '''
    rows = database.select_record(sql)

    if len(rows) > 0:
        chronic_code = rows[0]["SpecialCode"]

    return chronic_code


def is_duplicate_patient(database, row):
    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    patient_key = string_utils.xstr(row["PatientKey"])

    sql = f'''
        SELECT CaseKey FROM cases
        WHERE
            DATE(CaseDate) = "{case_date}" AND
            PatientKey = {patient_key}
    '''
    rows = database.select_record(sql)
    if len(rows) >= 2:
        return True

    return False


def is_duplicate_ins_patient(database, row):
    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    patient_key = string_utils.xstr(row["PatientKey"])

    sql = f'''
        SELECT CaseKey FROM cases
        WHERE
            DATE(CaseDate) = "{case_date}" AND
            PatientKey = {patient_key} AND
            InsType = "健保"
    '''
    rows = database.select_record(sql)
    if len(rows) >= 1:
        return True

    return False


def extract_treatment(treatment):
    if treatment in ["", None]:
        return None, None

    if treatment in [
        "中度針灸合併高度傷科",
        "高度針灸合併高度傷科",
    ]:  # 轉先前舊的高度傷科
        treatment += "起始次"
    elif treatment in [
        "中度針灸合併高度傷科療程2-6次",
        "高度針灸合併高度傷科療程2-6次",
    ]:
        treatment = treatment.replace("療程2-6次", "") + "後續治療"

    if treatment not in nhi_utils.ACUPUNCTURE_MERGE_TREAT:  # 非針灸合併傷科治療
        return treatment, None

    for primary_treatment in nhi_utils.PRIMARY_ACUPUNCTURE_TREAT:
        if primary_treatment in treatment:
            if primary_treatment == "中度針灸":
                primary_treatment = "中度複雜性針灸"
            elif primary_treatment == "高度針灸":
                primary_treatment = "高度複雜性針灸"

            break

    for secondary_treatment in nhi_utils.SECONDARY_MASSAGE_TREAT:
        if secondary_treatment in treatment:
            if secondary_treatment == "中度傷科":
                secondary_treatment = "中度複雜性傷科"
            elif secondary_treatment == "高度傷科":
                secondary_treatment = "高度複雜性傷科"
            elif secondary_treatment == "中度傷科合併特殊疾病":
                secondary_treatment = "中度複雜性傷科合併特殊疾病"

            break

    return primary_treatment, secondary_treatment


def exclude_xx_card():
    sql = """
        (cases.Card IS NULL OR
            cases.Card NOT IN ("XX1", "XX2", "XX3", "XX4", "XX5", "XX6", "XX7", "XX8", "XX9"))
    """

    return sql


def get_disease_name_all(row):
    disease_name_list = []
    if string_utils.xstr(row["DiseaseName1"]) != "":
        disease_name_list.append("①" + string_utils.xstr(row["DiseaseName1"]))
    if string_utils.xstr(row["DiseaseName2"]) != "":
        disease_name_list.append("②" + string_utils.xstr(row["DiseaseName2"]))
    if string_utils.xstr(row["DiseaseName3"]) != "":
        disease_name_list.append("③" + string_utils.xstr(row["DiseaseName3"]))

    disease_name = ", ".join(disease_name_list)

    return disease_name


def get_case_times_this_month(database, patient_key):
    start_date = datetime.datetime.now().strftime("%Y-%m-01 00:00:00")
    sql = f'''
        SELECT CaseKey FROM cases
        WHERE
            PatientKey = {patient_key} AND
            InsType = "健保" AND
            CaseDate >= "{start_date}"
    '''
    rows = database.select_record(sql)

    return len(rows)


def get_case_times(database, patient_key, case_date):
    # last_day = calendar.monthrange(case_date.year, case_date.month)[1]
    # end_date = f'{case_date.year}-{case_date.month}-{last_day} 23:59:59'

    start_date = f"{case_date.year}-{case_date.month}-01 00:00:00"
    end_date = f"{case_date.year}-{case_date.month}-{case_date.day} 23:59:59"
    sql = f'''
        SELECT CaseKey FROM cases
        WHERE
            PatientKey = {patient_key} AND
            InsType = "健保" AND
            CaseDate BETWEEN "{start_date}" AND "{end_date}"
    '''
    rows = database.select_record(sql)

    return len(rows)


# 拷貝參考處方
def copy_reference_prescript(
    database,
    system_settings,
    medical_record,
    reference_key,
    copy_diagnostic,
    copy_prescript,
):
    sql = f"""
        SELECT * FROM reference
        WHERE
            Referencekey = {reference_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]
    ui = medical_record.ui
    if copy_diagnostic:
        ui.textEdit_symptom.setText(string_utils.get_str(row["RefSymptom"], "utf8"))
        ui.textEdit_tongue.setText(string_utils.get_str(row["RefTongue"], "utf8"))
        ui.textEdit_pulse.setText(string_utils.get_str(row["RefPulse"], "utf8"))

    if not copy_prescript:
        return

    sql = f"""
        SELECT * FROM refprescript
        WHERE
            Referencekey = {reference_key}
    """
    rows = database.select_record(sql)
    for row in rows:
        medicine_key = row["MedicineKey"]
        if medicine_key in ["", None]:
            continue

        sql = f"""
            SELECT * FROM medicine
            WHERE
                MedicineKey = {medicine_key}
        """
        medicine_rows = database.select_record(sql)
        if len(medicine_rows) <= 0:
            continue

        medicine_row = medicine_rows[0]
        quantity = number_utils.get_float(row["Quantity"])
        if quantity > 0:
            medical_record.tab_list[0].append_prescript(medicine_row, dosage=quantity)
        else:
            medical_record.tab_list[0].append_prescript(medicine_row)

        medical_record.tab_list[0].append_null_medicine()


def get_medical_record_qr_code_data(database, system_settings, case_key):
    qr_code1 = get_medical_record_code_data(database, system_settings, case_key)
    qr_code2 = get_prescript_code_data(database, case_key)

    return f"{qr_code1}{qr_code2}"


def get_medical_record_code_data(database, system_settings, case_key):
    sql = f"""
        SELECT
            cases.CaseKey, cases.Name, cases.CaseDate, cases.Card, cases.Share, cases.Injury,
            cases.TreatType, cases.Continuance, cases.SpecialCode, cases.RegistType, cases.Treatment,
            DiseaseCode1, DiseaseCode2, DiseaseCode3, cases.Doctor,
            cases.DiagFee, cases.InsTotalFee,
            patient.ID, patient.Gender, patient.Birthday
        FROM cases
            LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    row = rows[0]
    clinic_id = system_settings.field("院所代號")
    patient_id = string_utils.xstr(row["ID"])
    name = string_utils.xstr(row["Name"])
    gender_code = patient_utils.get_gender_code(string_utils.xstr(row["Gender"]))
    birth_date = row["Birthday"].strftime("%Y%m%d")

    doctor = string_utils.xstr(row["Doctor"])
    case_date = row["CaseDate"].strftime("%Y%m%d")
    doctor_id = personnel_utils.get_person_field_value(database, doctor, "ID")
    doctor_id = doctor_id[:2] + "****" + doctor_id[6:10]

    hosp_class = "60"
    card = string_utils.xstr(row["Card"])
    identifier = case_utils.get_identifier(database, case_key, "就醫識別碼")
    pres_days = get_pres_days(database, case_key)

    injury = string_utils.xstr(row["Injury"])
    if injury == "職業傷害":
        injury_code = "1"
    elif injury == "職業病":
        injury_code = "2"
    elif injury == "普通傷害":
        injury_code = "3"
    elif injury == "普通疾病":
        injury_code = "4"
    elif injury == "天然災害":
        injury_code = "8"
    else:
        injury_code = "4"

    share_type = string_utils.xstr(row["Share"])
    if share_type == "重大傷病":
        share_code = "001"
    elif share_type == "低收入戶":
        share_code = "003"
    elif share_type == "榮民":
        share_code = "004"
    elif share_type == "職業傷害":
        share_code = "006"
    elif share_type == "山地離島":
        share_code = "007"
    elif share_type == "三歲兒童":
        share_code = "902"
    elif share_type == "替代役男":
        share_code = "906"
    else:
        share_code = "S10"

    diag_fee = number_utils.get_integer(row["DiagFee"])
    ins_total_fee = number_utils.get_integer(row["InsTotalFee"])

    case_type = nhi_utils.get_case_type(
        database, system_settings, row, diag_fee, ins_total_fee
    )
    disease_code = string_utils.xstr(row["DiseaseCode1"])
    pharmacy_times = 1
    pres_type = "A"  # A: 一般處方箋, B: 慢性病處方箋 C: 慢性病連續處方箋

    qr_code = (
        f"{clinic_id}|{patient_id}|{name}|{gender_code}|{birth_date}|{doctor_id}|"
        + f"{doctor}|{case_date}|{hosp_class}|{card}|{identifier}|{pres_days}|{injury_code}|"
        + f"{share_code}|{case_type}|{disease_code}|{pharmacy_times}|{pres_type}"
    )

    return qr_code


def get_prescript_code_data(database, case_key):
    sql = f"""
        SELECT * FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = 1
        ORDER BY PrescriptKey
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    pres_days = get_pres_days(database, case_key)
    packages = get_packages(database, case_key)
    instruction = get_instruction(database, case_key)

    try:
        frequency = nhi_utils.FREQUENCY[packages]
    except Exception:
        frequency = "TID"

    usage = "PO"

    qr_code = ""

    for row_no, row in enumerate(rows):
        order_type = "1"
        order_seq = row_no + 1
        ins_code = string_utils.xstr(row["InsCode"])
        medicine_name = string_utils.xstr(row["MedicineName"])
        ingredient = medicine_name
        medicine_mode = "科學中藥"
        dosage = round(number_utils.get_float(row["Dosage"]), 2)
        unit = string_utils.xstr(row["Unit"])
        total_dosage = round(packages * pres_days, 2)
        replacement = "Y"

        qr_code += (
            f"|{order_type}|{order_seq}|{ins_code}|{medicine_name}|{ingredient}|"
            + f"{dosage}|{medicine_mode}|{dosage}|{unit}|{frequency}|{pres_days}|{total_dosage}|"
            + f"{usage}|{replacement}"
        )

    return qr_code


def get_security_data(security, field_name):
    try:
        data = extract_security_xml(security, field_name)
    except Exception:
        data = None

    return data


def get_identifier(database, case_key, field_name):
    security = get_case_field_value(database, case_key, "Security")
    if security is None:
        return None

    identifier = extract_security_xml(security, field_name)

    return identifier


def get_integrate_case_time(database, case_key):
    start_time = "0000"
    end_time = "0000"

    sql = f"""
        SELECT Symptom FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    if len(rows) > 0:
        row = rows[0]
        symptom = string_utils.get_str(row["Symptom"], "utf8")
        # 抓出所有的 start_time 和 end_time 配對
        matches = re.findall(r"診療及衛教時間: 從(\d{2}:\d{2})至(\d{2}:\d{2})", symptom)

        # 取得最新一筆（最後一筆）
        if matches:
            start_time, end_time = matches[0]
            start_time = start_time.replace(":", "")
            end_time = end_time.replace(":", "")

    return start_time, end_time


def get_last_share_type(database, patient_key):
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    sql = f'''
        SELECT Share FROM cases
        WHERE
            PatientKey = {patient_key} AND
            InsType = "健保" AND
            (Continuance IS NULL OR Continuance < 1) AND
            DATE(CaseDate) < "{today}"
        ORDER BY CaseDate DESC LIMIT 1
    '''

    rows = database.select_record(sql)
    if not rows:
        return None

    row = rows[0]
    share_type = string_utils.xstr(row["Share"])

    return share_type


def get_prescript_order(database, case_key, medicine_set):
    if medicine_set == 1:
        ins_type = "健保:"
    elif medicine_set >= 2:
        ins_type = f"自費{medicine_set - 1}:"
    else:
        ins_type = ""

    if ins_type != "":
        keyword = f' AND Content LIKE "%{ins_type}%"'
    else:
        keyword = ""

    sql = f"""
        SELECT Content FROM caseextend
        WHERE
            CaseKey = {case_key} AND
            ExtendType = "醫囑"
            {keyword}
        ORDER BY CaseExtendKey
    """
    rows = database.select_record(sql)

    if not rows:
        return None

    order_list = []
    for row in rows:
        content = string_utils.xstr(row["Content"])
        content = content.replace(ins_type, "")
        order_list.append(content)

    return ", ".join(order_list)


def calculate_discount_rate(database, case_key):
    discount_fee = number_utils.get_integer(
        case_utils.get_case_field_value(database, case_key, "DiscountFee")
    )

    if discount_fee <= 0:
        return 100

    self_total_fee = number_utils.get_integer(
        case_utils.get_case_field_value(database, case_key, "SelfTotalFee")
    )

    if self_total_fee <= 0:
        return 100

    discount_rate = 100 - int(round(discount_fee / self_total_fee * 100, 1))

    return discount_rate
