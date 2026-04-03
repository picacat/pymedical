# -*- coding: UTF-8 -*-

import datetime

from libs import case_utils, number_utils

PAYMENT_TYPE_LIST = ["現金", "轉帳", "月結", "未付款"]


# 雲端藥歷
def get_supplier_list(database):
    sql = "SELECT Name FROM supplier ORDER BY Name"
    rows = database.select_record(sql)

    supplier_list = []
    for row in rows:
        supplier_list.append(row["Name"])

    return supplier_list


def set_medicine_in_price(database, medicine_key, unit_quantity, unit_price):
    try:
        in_price = round(unit_price / unit_quantity, 2)
    except Exception:
        return

    if in_price <= 0:
        return

    sql = f"""
        UPDATE medicine
        SET
            InPrice = {in_price}
        WHERE
            MedicineKey = {medicine_key}
    """
    database.exec_sql(sql)


def add_medicine_quantity(database, medicine_key, stock_quantity):
    sql = f"""
        SELECT Quantity FROM medicine
        WHERE
            MedicineKey = {medicine_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]
    original_stock_quantity = number_utils.get_float(row["Quantity"])
    total_quantity = original_stock_quantity + number_utils.get_float(stock_quantity)

    sql = f"""
        UPDATE medicine
        SET
            Quantity = {total_quantity}
        WHERE
            MedicineKey = {medicine_key}
    """
    database.exec_sql(sql)


def subtract_medicine_quantity(database, medicine_key, stock_quantity):
    sql = f"""
        SELECT Quantity FROM medicine
        WHERE
            MedicineKey = {medicine_key}
    """
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]
    original_stock_quantity = number_utils.get_float(row["Quantity"])
    # if original_stock_quantity <= 0:  # 庫存量=0 不扣庫存
    #     return

    total_quantity = round(original_stock_quantity - stock_quantity, 1)

    sql = f"""
        UPDATE medicine
        SET
            Quantity = {total_quantity}
        WHERE
            MedicineKey = {medicine_key}
    """
    database.exec_sql(sql)


def set_restore_date(database, stock_in_key):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    sql = f'''
        UPDATE stockin
        SET
            StoreDate = "{today}"
        WHERE
            StockInKey = {stock_in_key}
    '''
    database.exec_sql(sql)


def set_adjust_date(database, stock_out_key):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    sql = f'''
        UPDATE stockout
        SET
            AdjustDate = "{today}"
        WHERE
            StockOutKey = {stock_out_key}
    '''
    database.exec_sql(sql)


def adjust_stock_quantity(database, system_settings, stock_in_key):
    sql = f"""
        SELECT * FROM stockinitems
        WHERE
            StockInKey = {stock_in_key}
    """
    rows = database.select_record(sql)

    for row in rows:
        medicine_key = row["MedicineKey"]
        unit_quantity = number_utils.get_integer(row["UnitQuantity"])
        unit_price = number_utils.get_integer(row["UnitPrice"])
        quantity = number_utils.get_integer(row["Quantity"])

        if unit_quantity > 0:
            stock_quantity = unit_quantity * quantity
        else:
            stock_quantity = quantity

        try:
            add_medicine_quantity(database, medicine_key, stock_quantity)
        except Exception:
            pass

        try:
            if system_settings.field("輸入進貨資料同步更新藥品進價") == "Y":
                set_medicine_in_price(database, medicine_key, unit_quantity, unit_price)
        except Exception:
            pass

    set_restore_date(database, stock_in_key)


def restore_stock_quantity(database, stock_in_key):
    sql = f"""
        SELECT * FROM stockinitems
        WHERE
            StockInKey = {stock_in_key}
    """
    rows = database.select_record(sql)

    for row in rows:
        medicine_key = row["MedicineKey"]
        if medicine_key is None:
            continue

        unit_quantity = number_utils.get_integer(row["UnitQuantity"])
        quantity = number_utils.get_integer(row["Quantity"])
        stock_quantity = unit_quantity * quantity

        subtract_medicine_quantity(database, medicine_key, stock_quantity)

    set_restore_date(database, stock_in_key)


def adjust_stock_out_quantity(database, stock_out_key):
    sql = f"""
        SELECT * FROM stockoutitems
        WHERE
            StockOutKey = {stock_out_key}
    """
    rows = database.select_record(sql)

    for row in rows:
        medicine_key = row["MedicineKey"]
        unit_quantity = number_utils.get_integer(row["UnitQuantity"])
        quantity = number_utils.get_integer(row["Quantity"])
        stock_quantity = unit_quantity * quantity

        try:
            subtract_medicine_quantity(database, medicine_key, stock_quantity)
        except Exception:
            pass

    set_adjust_date(database, stock_out_key)


def adjust_ins_prescript(database, case_key):
    if case_utils.get_doctor_done(database, case_key):  # 完診就不再調整庫存
        return

    medicine_set = 1
    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    if pres_days == 0:
        return

    sql = f"""
        SELECT MedicineKey, Dosage FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set}
    """
    rows = database.select_record(sql)

    for row in rows:
        medicine_key = row["MedicineKey"]
        if medicine_key is None:
            continue

        total_dosage = number_utils.get_integer(row["Dosage"]) * pres_days

        subtract_medicine_quantity(database, medicine_key, total_dosage)


def adjust_self_prescript(database, case_key, medicine_set, adjust_stock=True):
    if not adjust_stock:
        return

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    if pres_days == 0:
        pres_days = 1

    sql = f"""
        SELECT MedicineKey, Dosage FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set}
    """
    rows = database.select_record(sql)

    for row in rows:
        medicine_key = row["MedicineKey"]
        if medicine_key is None:
            continue

        total_dosage = number_utils.get_float(row["Dosage"]) * pres_days
        subtract_medicine_quantity(database, medicine_key, total_dosage)


def restore_prescript_quantity(database, case_key):
    if case_key in [None, ""]:
        return

    sql = f"""
        SELECT MedicineSet, MedicineKey, Dosage FROM prescript
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    for row in rows:
        medicine_key = row["MedicineKey"]
        medicine_set = row["MedicineSet"]
        pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
        if pres_days == 0:
            pres_days = 1

        total_dosage = number_utils.get_integer(row["Dosage"]) * pres_days

        add_medicine_quantity(database, medicine_key, total_dosage)
