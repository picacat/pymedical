# 2021.12.27
# -*- coding: UTF-8 -*-

from libs import string_utils


def set_medicine_extend(database, medicine_key, extend_type, description):
    sql = f'''
        SELECT MedicineKey FROM medextend
        WHERE
            MedicineKey = {medicine_key} AND
            ExtendType = "{extend_type}"
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        remove_medicine_extend(database, medicine_key, extend_type)

    fields = ['MedicineKey', 'ExtendType', 'Description']
    data = [
        medicine_key,
        extend_type,
        description,
    ]
    database.insert_record('medextend', fields, data)


def get_medicine_extend(database, medicine_key, extend_type):
    description = None

    sql = f'''
        SELECT Description FROM medextend
        WHERE
            MedicineKey = {medicine_key} AND
            ExtendType = "{extend_type}"
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        row = rows[0]
        description = string_utils.xstr(row['Description'])

    return description


def remove_medicine_extend(database, medicine_key, extend_type):
    sql = f'''
        DELETE FROM medextend
        WHERE
            MedicineKey = {medicine_key} AND
            ExtendType = "{extend_type}"
    '''
    database.exec_sql(sql)
