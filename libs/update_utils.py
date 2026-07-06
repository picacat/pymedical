# 自動更新 2023-02-27
# -*- coding: UTF-8 -*-
import json

from PyQt5 import QtCore, QtWidgets

from libs import case_utils, dropbox_utils, number_utils, string_utils


def update_database(parent, database):
    if case_utils.get_case_extend(database, 0, "202607-001") != "Y":
        update_nhi_payment(database)
        case_utils.set_case_extend(database, 0, "202607-001", "Y")

    # if case_utils.get_case_extend(database, 0, '202505-002') != 'Y':
    #     update_nhi_payment(database)
    #     case_utils.set_case_extend(database, 0, '202505-002', 'Y')

    # if case_utils.get_case_extend(database, 0, '202505-001') != 'Y':
    #     update_nhi_payment(database)
    #     case_utils.set_case_extend(database, 0, '202505-001', 'Y')

    # if case_utils.get_case_extend(database, 0, '202303-001') != 'Y':
    #     update_utils.update_nhi_payment(database)
    #     case_utils.set_case_extend(database, 0, '202303-001', 'Y')

    # if case_utils.get_case_extend(database, 0, '202303-002') != 'Y':
    #     update_utils.update_chronic_condition(parent, database)
    #     case_utils.set_case_extend(database, 0, '202303-002', 'Y')


"""
    更新記錄:
        202303-001 2023-03-01 支付標準更新
        202303-002 2023-03-05 慢性病代碼更新
        202303-002 2023-03-05 取消慢性病代碼更新, 許多醫師用不習慣
"""


# 雲端藥歷
def update_nhi_payment(database):
    filename = "nhi_payment.json"
    url = "https://www.dropbox.com/s/8w42p1zovzzz8uc/nhi_payment.json?dl=1"

    title = "下載健保支付標準檔"
    message = (
        '<font size="5" color="red"><b>正在下載健保支付標準檔, 請稍後...</b></font>'
    )
    hint = "正在與更新檔資料庫連線, 會花費一些時間."

    download_file = dropbox_utils.download_dropbox_file(
        filename, url, title, message, hint
    )
    if download_file is None:
        return

    update_list = []
    with open(filename, encoding="utf8") as json_file:
        rows = json.load(json_file)
        for row_no, row in enumerate(rows):
            new_ins_code = row["InsCode"]
            new_amount = number_utils.get_integer(row["Amount"])
            sql = f'''
                SELECT * FROM charge_settings
                WHERE
                    InsCode = "{new_ins_code}"
            '''
            charge_row = database.select_record(sql)
            if len(charge_row) <= 0:
                update_list.append(["無", row])
            elif number_utils.get_integer(charge_row[0]["Amount"]) != new_amount:
                update_list.append([charge_row[0]["Amount"], row])

    if len(update_list) <= 0:
        return

    for row in update_list:
        json_row = row[1]
        ins_code = json_row["InsCode"]
        sql = f'''
            SELECT * FROM charge_settings
            WHERE
                InsCode = "{ins_code}"
        '''
        rows = database.select_record(sql)

        if len(rows) > 0:
            amount = number_utils.get_integer(json_row["Amount"])
            remark = string_utils.xstr(json_row["Remark"])
            ins_code = string_utils.xstr(json_row["InsCode"])
            sql = f"""
                UPDATE charge_settings
                SET
                    Amount = {amount}, Remark = '{remark}'
                WHERE
                    InsCode = '{ins_code}'
            """
            database.exec_sql(sql)
        else:
            fields = [
                "ChargeType",
                "ItemName",
                "InsCode",
                "Amount",
                "Remark",
            ]

            data = [
                string_utils.xstr(json_row["ChargeType"]),
                string_utils.xstr(json_row["ItemName"]),
                string_utils.xstr(json_row["InsCode"]),
                number_utils.get_integer(json_row["Amount"]),
                string_utils.xstr(json_row["Remark"]),
            ]

            database.insert_record("charge_settings", fields, data)


def update_chronic_condition(parent, database):
    f = open("chronic_condition.json")
    json_data = json.load(f)
    max_progress = len(json_data)

    progress_dialog = QtWidgets.QProgressDialog(
        "正在轉入慢性病代碼資料中, 請稍後...", "取消", 0, max_progress, parent
    )

    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
    progress_dialog.setValue(0)
    for i, key in enumerate(json_data):
        progress_dialog.setValue(i + 1)
        icd_code = key
        chronic_code = json_data[key]
        database.exec_sql(
            f'UPDATE icd10 SET SpecialCode = "{chronic_code}" WHERE ICDCode = "{icd_code}"'
        )

    progress_dialog.setValue(max_progress)
    progress_dialog.deleteLater()


def update_2023_icd10(parent, database):
    f = open("2023_ICD10.json", "r", encoding="utf-8")
    json_data = json.load(f)
    max_progress = len(json_data)

    progress_dialog = QtWidgets.QProgressDialog(
        "正在轉入2023資料中, 請稍後...", "取消", 0, max_progress, parent
    )

    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
    progress_dialog.setValue(0)
    fields = [
        "ICDCode",
        "ChineseName",
        "EnglishName",
    ]
    for i, item in enumerate(json_data):
        progress_dialog.setValue(i + 1)
        icd_code = item["ICDCode"]
        icd_code = icd_code.replace(".", "")

        chinese_name = item["ChineseName"][:100]
        english_name = item["EnglishName"][:100]
        rows = database.select_record(
            f'SELECT ICD10Key FROM icd10 WHERE ICDCode = "{icd_code}"'
        )
        if len(rows) > 0:
            database.exec_sql(f'''
                UPDATE icd10 SET
                    ChineseName = "{chinese_name}",
                    EnglishName = "{english_name}"
                WHERE ICDCode = "{icd_code}"
            ''')
        else:
            data = [
                icd_code,
                chinese_name,
                english_name,
            ]
            database.insert_record("icd10", fields, data)

    progress_dialog.setValue(max_progress)
    progress_dialog.deleteLater()


def delete_2023_icd10(parent, database):
    f = open("2023_ICD10_disable.json", "r", encoding="utf-8")
    json_data = json.load(f)
    max_progress = len(json_data)

    progress_dialog = QtWidgets.QProgressDialog(
        "正在移除2023作廢資料中, 請稍後...", "取消", 0, max_progress, parent
    )

    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
    progress_dialog.setValue(0)
    for i, item in enumerate(json_data):
        progress_dialog.setValue(i + 1)
        icd_code = item["ICDCode"]
        icd_code = icd_code.replace(".", "")
        database.exec_sql(f'''
            DELETE FROM icd10 WHERE ICDCode = "{icd_code}"
        ''')

    progress_dialog.setValue(max_progress)
    progress_dialog.deleteLater()


def update_2023_icd10_input_code(parent, database):
    sql = "SELECT ICDCode, InputCode, SpecialCode FROM icd10 WHERE InputCode IS NOT NULL AND LENGTH(InputCode) > 0"
    rows = database.select_record(sql)

    max_progress = len(rows)
    progress_dialog = QtWidgets.QProgressDialog(
        "正在轉入2023資料中, 請稍後...", "取消", 0, max_progress, parent
    )

    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
    progress_dialog.setValue(0)

    for i, row in enumerate(rows):
        progress_dialog.setValue(i + 1)
        icd_code = string_utils.xstr(row["ICDCode"])
        input_code = string_utils.xstr(row["InputCode"])
        special_code = string_utils.xstr(row["SpecialCode"])

        sql = f'''
            SELECT ICD10Key FROM icd10
            WHERE
                ICDCode LIKE "{icd_code}%" AND
                (InputCode IS NULL OR LENGTH(InputCode) = 0)'''
        icd_rows = database.select_record(sql)
        for icd_row in icd_rows:
            icd10_key = string_utils.xstr(icd_row["ICD10Key"])
            database.exec_sql(f'''
                UPDATE icd10
                SET
                    InputCode = "{input_code}",
                    SpecialCode = "{special_code}"
                WHERE
                    ICD10Key = {icd10_key}
            ''')

    progress_dialog.setValue(max_progress)
    progress_dialog.deleteLater()
