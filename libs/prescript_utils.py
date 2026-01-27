
import csv
import datetime
import os

from lxml import etree as ET
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QAbstractItemView, QInputDialog, QMessageBox

from libs import (case_utils, date_utils, dialog_utils, medicine_utils,
                  nhi_utils, number_utils, patient_utils, registration_utils,
                  string_utils, system_utils)

PRESCRIPT_COL_NO = {
    'PrescriptKey': 0,
    'PrescriptNo': 1,
    'CaseKey': 2,
    'CaseDate': 3,
    'MedicineSet': 4,
    'MedicineType': 5,
    'MedicineKey': 6,
    'InsCode': 7,
    'DosageMode': 8,
}


INS_PRESCRIPT_COL_NO = {
    **PRESCRIPT_COL_NO,
    'BackupMedicineName': 9,
    'MedicineName': 10,
    'Dosage': 11,
    'Unit': 12,
    'Instruction': 13,
    'Info': 14,
}


SELF_PRESCRIPT_COL_NO = {
    **PRESCRIPT_COL_NO,
    'BackupMedicineName': 9,
    'MedicineName': 10,
    'Dosage': 11,
    'Unit': 12,
    'Instruction': 13,
    'Price': 14,
    'Amount': 15,
    'Info': 16,
}

INS_TREAT_COL_NO = {
    'PrescriptKey': 0,
    'CaseKey': 1,
    'CaseDate': 2,
    'MedicineSet': 3,
    'MedicineType': 4,
    'MedicineKey': 5,
    'InsCode': 6,
    'BackupMedicineName': 7,
    'MedicineName': 8,
}

INS_CARE_COL_NO = {
    'PrescriptKey': 0,
    'PrescriptNo': 1,
    'CaseKey': 2,
    'CaseDate': 3,
    'MedicineSet': 4,
    'MedicineType': 5,
    'MedicineKey': 6,
    'MedicineName': 7,
    'InsCode': 8,
    'Price': 9,
    'Dosage': 10,
    'Unit': 11,
    'Amount': 12,
}

PRESCRIPT_TREAT = ['穴道', '處置']


# 取得服藥頻率代碼
def get_usage_code(package):
    usage_dict = {
        0: None,
        1: 'QD',
        2: 'BID',
        3: 'TID',
        4: 'QID',
    }

    return usage_dict[package]


# 取得服藥方式代碼
def get_instruction_code(instruction):
    if instruction is None:
        return 'PC'

    if instruction.find('飯前') >= 0:
        instruction_code = 'AC'
    elif instruction.find('飯後') >= 0:
        instruction_code = 'PC'
    else:
        instruction_code = ''

    return instruction_code


# 檢查是否重複開立處方
def check_prescript_duplicates(in_table_widget, medicine_type, col_no, check_value, duplicate_warning=True):
    exists = False

    if check_value == '':  # 特殊處方或處置不檢查 (波形, 頻率, 時間)
        return exists

    row_count = in_table_widget.rowCount()
    field_value = None
    in_table_widget.blockSignals(True)                
    for row_no in range(row_count):
        field = in_table_widget.item(row_no, col_no)
        if field is not None:
            field_value = field.text()

        if check_value == field_value:
            row_no = in_table_widget.currentRow()

            if medicine_type in PRESCRIPT_TREAT:
                backup_medicine_name = INS_TREAT_COL_NO['BackupMedicineName']
                medicine_name = INS_TREAT_COL_NO['MedicineName']
            else:
                backup_medicine_name = INS_PRESCRIPT_COL_NO['BackupMedicineName']
                medicine_name = INS_PRESCRIPT_COL_NO['MedicineName']

            previous_medicine_item = in_table_widget.item(row_no, backup_medicine_name)

            in_table_widget.setItem(
                row_no, medicine_name,
                QtWidgets.QTableWidgetItem(previous_medicine_item)
            )

            if duplicate_warning:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    '重複處方或處置',
                    '<font size="5" color="red"><b>處方或處置重複開立, 請檢查.</b></font>',
                    '處方或處置重複輸入.'
                )

            exists = True
            break
 
    in_table_widget.blockSignals(False)
 
    return exists


# 新增加強照護醫令
def insert_ins_care_item(database, case_key, case_date, ins_code):
    sql = f'''
        SELECT * FROM prescript
        WHERE
            (CaseKey = {case_key}) AND (MedicineSet = 11) AND
            (MedicineType IN ("照護"))
        ORDER BY PrescriptNo, PrescriptKey
    '''
    rows = database.select_record(sql)

    if len(rows) > 0:
        return

    sql = f'''
        SELECT * FROM charge_settings
        WHERE
            ChargeType = "照護費" AND
            InsCode = "{ins_code}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return

    row = rows[0]

    fields = [
        'PrescriptNo', 'CaseKey', 'CaseDate', 'MedicineSet', 'MedicineType',
        'MedicineKey', 'MedicineName', 'InsCode', 'Price', 'Dosage', 'Unit', 'Amount',
    ]
    data = [
        '1',
        string_utils.xstr(case_key),
        string_utils.xstr(case_date),
        '11',
        '照護',
        string_utils.xstr(row['ChargeSettingsKey']),
        string_utils.xstr(row['ItemName']),
        string_utils.xstr(row['InsCode']),
        string_utils.xstr(row['Amount']),
        '1',
        '次',
        string_utils.xstr(row['Amount']),
    ]

    database.insert_record('prescript', fields, data)


def extract_ins_compound(database, prescript_row, table_widget_prescript, table_widget_treat=None):
    medicine_key = prescript_row[6][1]
    sql = f'''
        SELECT * FROM refcompound
        WHERE
            CompoundKey = {medicine_key}
        ORDER BY RefCompoundKey
    '''

    compound_rows = database.select_record(sql)
    if len(compound_rows) <= 0:
        return

    for compound_row in compound_rows:
        medicine_key = string_utils.xstr(compound_row['MedicineKey'])
        if medicine_key == '':
            return


def extract_compound(prescript_tab, database, system_settings, medicine_key, table_widget_medicine=None):
    sql = f'''
        SELECT * FROM medicine
        WHERE
            MedicineKey = {medicine_key}
    '''
    rows = database.select_record(sql)
    row = rows[0]
    is_unit_price = False
    compound_single = medicine_utils.get_medicine_extend(database, medicine_key, '成方單項')
    compound_title = medicine_utils.get_medicine_extend(database, medicine_key, '成方抬頭')
    if prescript_tab.objectName() == 'SelfPrescript' and (compound_title == 'Y' or compound_single == 'Y'):
        price = number_utils.get_integer(row['SalePrice'])
        if price > 0:
            is_unit_price = True

        medicine_name = string_utils.xstr(row['MedicineName'])
        unit = string_utils.xstr(row['Unit'])
        row = {
            'MedicineType': '成方表頭',
            'MedicineKey': medicine_key,
            'InsCode': None,
            'MedicineName': f'成方: {medicine_name}',
            'Unit': unit,
            'Quantity': 1,
            'Price': price,
            'Amount': price,
        }
        add_medicine(prescript_tab, table_widget_medicine, row)

    if compound_single == 'Y' and compound_title != 'Y':  # 單項true 抬頭false 不匯入成方內容
        return

    sql = f'''
        SELECT
            refcompound.*,
            medicine.MedicineKey, medicine.MedicineType, medicine.InsCode,
            medicine.MedicineName, medicine.Unit, medicine.SalePrice
        FROM refcompound
            LEFT JOIN medicine ON refcompound.MedicineKey = medicine.MedicineKey
        WHERE
            CompoundKey = {medicine_key}
        ORDER BY RefCompoundKey
    '''

    compound_rows = database.select_record(sql)
    if len(compound_rows) <= 0:
        return

    for compound_row in compound_rows:
        if is_unit_price:
            price = 0
            amount = 0
        else:
            quantity = number_utils.get_float(compound_row['Quantity'])
            price = number_utils.get_float(compound_row['SalePrice'])
            amount = round(quantity * price, 2)

        row = {
            'MedicineType': string_utils.xstr(compound_row['MedicineType']),
            'MedicineKey': string_utils.xstr(compound_row['MedicineKey']),
            'InsCode': string_utils.xstr(compound_row['InsCode']),
            'MedicineName': string_utils.xstr(compound_row['MedicineName']),
            'Unit': string_utils.xstr(compound_row['Unit']),
            'Quantity': string_utils.xstr(compound_row['Quantity']),
            'Price': string_utils.xstr(price),
            'Amount': string_utils.xstr(amount),
        }

        medicine_type = row['MedicineType']
        if medicine_type in ['穴道', '處置'] and number_utils.get_integer(prescript_tab.medicine_set) <= 1:
            add_treat(prescript_tab, table_widget_medicine, row)

            current_row = prescript_tab.tableWidget_prescript.currentRow()
            medicine_key = prescript_tab.tableWidget_prescript.item(current_row, INS_PRESCRIPT_COL_NO['MedicineKey'])
            medicine_name = prescript_tab.tableWidget_prescript.item(current_row, INS_PRESCRIPT_COL_NO['MedicineName'])
            if medicine_key is None and medicine_name is not None:
                prescript_tab.tableWidget_prescript.removeRow(current_row)
                prescript_tab.append_null_medicine()
        elif medicine_type in ['自費科中'] and number_utils.get_integer(prescript_tab.medicine_set) <= 1:  # 2025-03-14 頤光中正
            add_medicine(prescript_tab.parent.tab_list[1], table_widget_medicine, row)
        else:
            add_medicine(prescript_tab, table_widget_medicine, row)


def set_treatment(medicine_type, combobox_treatment):
    if combobox_treatment.currentText() != '':
        return

    medicine_type_dict = {'穴道': '一般針灸', '處置': '一般傷科'}
    treatment = medicine_type_dict[medicine_type]

    combobox_treatment.setCurrentText(treatment)


# 輸入處置
def add_treat(prescript_tab, table_widget_medicine, row=None):
    if row is None:
        row = get_medicine_row(table_widget_medicine)

    medicine_type = row['MedicineType']
    set_treatment(medicine_type, prescript_tab.comboBox_treatment)

    prescript_tab.append_treat(row)
    current_row = prescript_tab.tableWidget_treat.currentRow()
    if current_row == prescript_tab.tableWidget_treat.rowCount() - 1:
        prescript_tab.append_null_treat()
    else:
        prescript_tab.tableWidget_treat.setCurrentCell(
            current_row + 1, INS_TREAT_COL_NO['MedicineName'],
        )


# 輸入藥品
def add_medicine(prescript_tab, table_widget_medicine, row=None, dosage=None):
    if row is None:
        row = get_medicine_row(table_widget_medicine)

    if dosage is not None:
        quantity = dosage
    else:
        quantity = row['Quantity']
        if quantity in ['', None]:
            quantity = None

    if not prescript_tab.append_prescript(row, quantity):
        return

    current_row = prescript_tab.tableWidget_prescript.currentRow()
    if current_row == prescript_tab.tableWidget_prescript.rowCount() - 1:
        prescript_tab.append_null_medicine()
    else:
        prescript_tab.tableWidget_prescript.setCurrentCell(
            current_row+1, INS_PRESCRIPT_COL_NO['MedicineName'],
        )


# 輸入藥品
def add_inventory_item(prescript_tab, table_widget_medicine, row=None):
    if row is None:
        row = get_medicine_row(table_widget_medicine)

    prescript_tab.append_prescript(row, row['Quantity'])

    current_row = prescript_tab.tableWidget_prescript.currentRow()
    if current_row == prescript_tab.tableWidget_prescript.rowCount() - 1:
        prescript_tab.append_null_medicine()
    else:
        prescript_tab.tableWidget_prescript.setCurrentCell(
            current_row+1, INS_PRESCRIPT_COL_NO['MedicineName'],
        )


def get_medicine_row(table_widget_medicine):
    row = {
        'MedicineKey': table_widget_medicine.field_value(0),
        'MedicineType': table_widget_medicine.field_value(1),
        'MedicineName': table_widget_medicine.field_value(2),
        'Unit': table_widget_medicine.field_value(3),
        'Price': table_widget_medicine.field_value(4),
        'InsCode': table_widget_medicine.field_value(5),
        'Quantity': table_widget_medicine.field_value(6),
        'Amount': None
    }

    return row


def get_medicine_description(database, medicine_key):
    if medicine_key == '':
        return None

    sql = f'''
        SELECT Description FROM medicine
        WHERE
            MedicineKey = {medicine_key}
    '''
    medicine_row = database.select_record(sql)

    if len(medicine_row) <= 0:
        return None

    try:
        description = string_utils.get_str(medicine_row[0]['Description'], 'utf8')
    except TypeError:
        return None

    if description is not None and description.strip() == '':
        return None

    return description


def get_costs_html(database, table_widget, pres_days, prescript_col_dict):
    prescript_record = ''
    sequence = 0
    day_cost = 0
    for row_no in range(table_widget.rowCount()):
        item = table_widget.item(row_no, prescript_col_dict['MedicineName'])
        if item is None:
            continue

        medicine_name = item.text()

        item = table_widget.item(row_no, prescript_col_dict['Dosage'])
        if item is None:
            continue

        dosage = number_utils.get_float(item.text())

        item = table_widget.item(row_no, prescript_col_dict['MedicineKey'])
        if item is None:
            medicine_key = item
        else:
            medicine_key = item.text()

        item = table_widget.item(row_no, prescript_col_dict['Unit'])
        if item is not None:
            unit = item.text()
        else:
            unit = ''

        cost = 0
        if medicine_key not in [None, '']:
            sql = f'''
                SELECT InPrice FROM medicine
                WHERE
                    MedicineKey = {medicine_key}
            '''
            rows = database.select_record(sql)
            if len(rows) > 0:
                cost = number_utils.get_float(rows[0]['InPrice'])

        sequence += 1

        subtotal_cost = dosage * cost
        prescript_record += f'''
            <tr>
                <td align="center" style="padding-right: 8px;">{sequence}</td>
                <td style="padding-left: 8px;">{medicine_name}</td>
                <td align="right" style="padding-right: 8px">{cost}</td>
                <td align="right" style="padding-right: 8px">{dosage} {unit}</td>
                <td align="right" style="padding-right: 8px">{subtotal_cost:.1f}</td>
            </tr>
        '''

        day_cost += subtotal_cost

    total_cost = round(day_cost, 1) * pres_days
    prescript_record += f'''
        <tr>
            <td align="center" style="padding-right: 8px;"></td>
            <td style="padding-left: 8px;">單日成本</td>
            <td align="right" style="padding-right: 8px"></td>
            <td align="right" style="padding-right: 8px"></td>
            <td align="right" style="padding-right: 8px">{day_cost:.1f}</td>
        </tr>
        <tr>
            <td align="center" style="padding-right: 8px;"></td>
            <td style="padding-left: 8px;">{pres_days}日藥總成本</td>
            <td align="right" style="padding-right: 8px"></td>
            <td align="right" style="padding-right: 8px"></td>
            <td align="right" style="padding-right: 8px">{total_cost:.1f}</td>
        </tr>
    '''

    prescript_data = f'''
        <table align=center cellpadding="2" cellspacing="0" width="98%"
         style="border-width: 1px; border-style: solid;">
            <thead>
                <tr bgcolor="LightGray">
                    <th style="text-align: center; padding-left: 8px" width="5%">序</th>
                    <th style="padding-left: 8px" width="50%" align="left">藥品名稱</th>
                    <th style="padding-right: 8px" align="right" width="15%">進價</th>
                    <th style="padding-right: 8px" align="right" width="15%">數量</th>
                    <th style="padding-right: 8px" align="right" width="15%">成本小計</th>
                </tr>
            </thead>
            <tbody>
                {prescript_record}
            </tbody>
        </table>
        <br>
    '''

    html = f'''
        <html>
            <head>
                <meta charset="UTF-8">
            </head>
            <body>
                <center><h4>用藥成本</h4></center>
                {prescript_data}
            </body>
        </html>
    '''

    return html


def get_max_medicine_set(database, case_key):
    max_medicine_set = 1

    sql = f'''
        SELECT MedicineSet FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet >= 2
        GROUP BY MedicineSet
        ORDER BY MedicineSet DESC LIMIT 1
    '''
    rows = database.select_record(sql)

    if len(rows) > 0:
        max_medicine_set = number_utils.get_integer(rows[0]['MedicineSet'])

    return max_medicine_set


def get_medicine_field(database, medicine_key, field_name):
    if medicine_key in [None, '']:
        return None

    sql = f'''
        SELECT {field_name} FROM medicine
        WHERE
            MedicineKey = {medicine_key}
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    return rows[0][field_name]


def get_total_dosage(table_widget_prescript, database=None, medicine_set=None):
    total_dosage = 0.0
    infectious_drug = False
    for row_no in range(table_widget_prescript.rowCount()):
        item = table_widget_prescript.item(row_no, INS_PRESCRIPT_COL_NO['MedicineName'])
        if item is None:
            continue

        medicine_name = item.text()
        if '清冠一號' in medicine_name:  # 清冠一號不檢查
            infectious_drug = True
            continue

        
        try:
            item = table_widget_prescript.item(row_no, INS_PRESCRIPT_COL_NO['MedicineKey'])
            if item is not None and item.text() != '' and \
               database is not None and medicine_set is None:
                medicine_key = item.text()
                sql = f'''
                    SELECT NoDosage FROM medicine
                    WHERE
                        MedicineKey = {medicine_key}
                '''
                rows = database.select_record(sql)
                if len(rows) > 0:
                    row = rows[0]
                    if string_utils.xstr(row['NoDosage']) == 'Y':
                        continue
        except Exception:
            pass

        item = table_widget_prescript.item(row_no, INS_PRESCRIPT_COL_NO['Dosage'])
        if item is None:
            continue

        try:
            dosage = round(number_utils.get_float(item.text()), 1)
        except (ValueError, TypeError):
            item.setText(None)
            continue

        total_dosage += dosage

    return total_dosage, infectious_drug


def is_folk_massage(database, system_settings, case_key):
    folk_massage_name = system_settings.field('民俗調理項目名稱')

    sql = f'''
        SELECT PrescriptKey FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = 2 AND
            MedicineType = "處置" AND
            MedicineName = "{folk_massage_name}"
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        return True
    else:
        return False


def get_folk_massage_name(system_settings):
    folk_massage_name = system_settings.field('民俗調理項目名稱')
    if folk_massage_name in ['', None]:
        folk_massage_name = '民俗調理'

    return folk_massage_name


def open_prescript_dialog(parent, database, system_settings, table_widget_prescript, ins_type):
    row_no = table_widget_prescript.currentRow()
    col_no = table_widget_prescript.currentColumn()

    if ins_type == '健保':
        medicine_name_col_no = INS_PRESCRIPT_COL_NO['MedicineName']
        dosage_col_no = INS_PRESCRIPT_COL_NO['Dosage']
        unit_col_no = INS_PRESCRIPT_COL_NO['Unit']
        instruction_col_no = INS_PRESCRIPT_COL_NO['Instruction']
    else:
        medicine_name_col_no = SELF_PRESCRIPT_COL_NO['MedicineName']
        dosage_col_no = SELF_PRESCRIPT_COL_NO['Dosage']
        unit_col_no = SELF_PRESCRIPT_COL_NO['Unit']
        instruction_col_no = SELF_PRESCRIPT_COL_NO['Instruction']

    medicine_name_item = table_widget_prescript.item(row_no, medicine_name_col_no)
    if medicine_name_item is None:
        return

    if col_no not in [medicine_name_col_no, dosage_col_no, unit_col_no, instruction_col_no]:
        return

    if col_no == dosage_col_no:
        table_widget_prescript.setEditTriggers(  # 取消編輯模式
            QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed
        )

        dialog = dialog_utils.get_dialog_dosage(
            parent, database, system_settings, table_widget_prescript, ins_type
        )
        dialog.show_dosage()
    elif col_no == unit_col_no:
        table_widget_prescript.setEditTriggers(  # 取消編輯模式
            QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed
        )

        dialog = dialog_utils.get_dialog_unit(
            parent, database, system_settings, table_widget_prescript, ins_type
        )
        dialog.show_unit()
    elif col_no == instruction_col_no:
        table_widget_prescript.setEditTriggers(  # 取消編輯模式
            QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed
        )

        dialog = dialog_utils.get_dialog_prescript_instruction(
            parent, database, system_settings, table_widget_prescript, ins_type
        )
        dialog.show_prescript_instruction()
    else:
        parent.open_medicine_dictionary()

    # dialog.exec_()
    # dialog.deleteLater()


def append_null_medicine(parent):
    tab = None

    if parent.ins_type == '健保':
        tab = parent.tab_list[0]
    else:
        tab = parent.tab_list[1]

    if tab is not None:
        tab.append_null_medicine()


def get_pres_extend_value(database, prescript_key, extend_type):
    sql = f'''
        SELECT * FROM presextend
        WHERE
            PrescriptKey = {prescript_key} AND
            ExtendType = "{extend_type}"
        ORDER BY PresExtendKey
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    return string_utils.xstr(rows[0]['Content'])


def insert_pres_extend_row(database, prescript_key, extend_type, content):
    fields = ['PrescriptKey', 'ExtendType', 'Content']
    data = [prescript_key, extend_type, content]

    database.insert_record('presextend', fields, data)


def remove_pres_extend_row(database, prescript_key, extend_type):
    sql = f'''
        DELETE FROM presextend
        WHERE
            PrescriptKey = {prescript_key} AND
            ExtendType = "{extend_type}"
    '''
    database.exec_sql(sql)


def get_no_discount_status(database, medicine_key):
    sql = f'SELECT Charged FROM medicine WHERE MedicineKey = {medicine_key}'
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    row = rows[0]

    return string_utils.xstr(row['Charged'])


def get_infectious_drug(database, case_key):
    is_infectious_drug = False
    is_ins_drug = False

    sql = f'''
        SELECT * FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = 1
    '''
    rows = database.select_record(sql)

    for row in rows:
        medicine_name = string_utils.xstr(row['MedicineName'])
        ins_code = string_utils.xstr(row['InsCode'])

        if '清冠一號' in medicine_name:
            is_infectious_drug = True
        elif ins_code != '':
            is_ins_drug = True

    if is_infectious_drug and is_ins_drug:
        infectious_drug = '台灣清冠一號及科學中藥'
    elif is_infectious_drug:
        infectious_drug = '台灣清冠一號'
    elif is_ins_drug:
        infectious_drug = '科學中藥'
    else:
        infectious_drug = '未開藥'

    return infectious_drug


def get_infectious_drug_code(database, case_key):
    sql = f'''
        SELECT * FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = 1 AND
            MedicineType IN ("單方", "複方") AND
            MedicineName LIKE "%清冠一號%"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return None

    row = rows[0]
    infectious_drug_name = string_utils.xstr(row['MedicineName'])
    ins_code, _, _ = get_infectious_drug_factory(infectious_drug_name)

    return ins_code


def get_infectious_drug_factory(infectious_drug):
    ins_code, medicine_name, dosage = None, None, None

    if '順天堂' in infectious_drug:
        ins_code, medicine_name, dosage = ['1100015686', '(順天堂)台灣清冠一號濃縮顆粒', 20]
    elif '莊松榮' in infectious_drug:
        ins_code, medicine_name, dosage = ['1100015903', '(莊松榮)台灣清冠一號濃縮顆粒', 30]
    elif '康福' in infectious_drug:
        ins_code, medicine_name, dosage = ['1101800237', '(康福)台灣清冠一號濃縮顆粒', 30]
    elif '勸奉堂' in infectious_drug:
        ins_code, medicine_name, dosage = ['1100022217', '(勸奉堂)台灣清冠一號濃縮顆粒', 30]
    elif '勝昌' in infectious_drug:
        ins_code, medicine_name, dosage = ['1100028044', '(勝昌)台灣清冠一號濃縮顆粒', 30]
    elif '華佗' in infectious_drug:
        ins_code, medicine_name, dosage = ['1100028108', '(華陀)台灣清冠一號濃縮顆粒', 30]
    elif '華陀' in infectious_drug:
        ins_code, medicine_name, dosage = ['1100028108', '(華陀)台灣清冠一號濃縮顆粒', 30]
    elif '漢聖' in infectious_drug:
        ins_code, medicine_name, dosage = ['1100030654', '(漢聖)台灣清冠一號濃縮顆粒', 30]
    elif '天一' in infectious_drug:
        ins_code, medicine_name, dosage = ['1100034528', '(天一)台灣清冠一號濃縮顆粒', 30]
    elif '天明' in infectious_drug:
        ins_code, medicine_name, dosage = ['1110019135', '(天明)台灣清冠一號濃縮顆粒', 30]
    elif '科達' in infectious_drug:
        ins_code, medicine_name, dosage = ['1110020553', '(科達)台灣清冠一號濃縮顆粒', 30]
    elif '富田' in infectious_drug:
        ins_code, medicine_name, dosage = ['1110022062', '(富田)台灣清冠一號濃縮顆粒', 30]

    return ins_code, medicine_name, dosage


def get_treat_time(database, case_key, field_value):
    treat_time = '0000'

    sql = f'''
        SELECT MedicineName FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = 1 AND
            MedicineName LIKE "{field_value}%"
        LIMIT 1
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        row = rows[0]
        treat_time = string_utils.xstr(row['MedicineName'])
        try:
            treat_time = treat_time.split(field_value)[1].replace(':', '').strip()
        except Exception:
            pass
    else:
        sql = f'''
            SELECT CaseDate, DoctorDate FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            try:
                if '治療開始' in field_value:
                    treat_time = row['DoctorDate'].strftime('%H%M')
                else:
                    treat_time = row['DoctorDate'] + datetime.timedelta(minutes=20)
                    treat_time = treat_time.strftime('%H%M')
            except Exception:
                pass

    return treat_time


def get_treat_position(database, case_key, field_value):
    treat_position_code = ''

    sql = f'''
        SELECT MedicineName FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = 1 AND
            MedicineName LIKE "{field_value}%"
        ORDER BY PrescriptKey
    '''
    rows = database.select_record(sql)

    for row in rows:
        treat_position = string_utils.xstr(row['MedicineName'])
        try:
            treat_position = treat_position.split(field_value)[1].strip()
        except Exception:
            continue

        try:
            treat_position_code += nhi_utils.POSITION_DICT[treat_position]
        except Exception:
            pass

    return treat_position_code


def get_auxiliary_list(database, case_key, field_value):
    auxiliary_list = []

    sql = f'''
        SELECT MedicineName FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = 1 AND
            MedicineName LIKE "{field_value}%"
        ORDER BY PrescriptKey
    '''
    rows = database.select_record(sql)

    for row in rows:
        auxiliary_treat = string_utils.xstr(row['MedicineName'])
        try:
            auxiliary_treat = auxiliary_treat.split(field_value)[1].strip()
        except Exception:
            continue

        try:
            auxiliary_list.append(nhi_utils.AUXILIARY_TREAT_DICT[auxiliary_treat])
        except Exception:
            pass

    return auxiliary_list


# 預設複雜性針灸治療時間
def get_default_complicated_acupuncture_time(system_settings):
    moderate_time = system_settings.field('預設中度複雜性針灸治療時間')
    if moderate_time is None:
        moderate_time = 10

    highly_time = system_settings.field('預設高度複雜性針灸治療時間')
    if highly_time is None:
        highly_time = 20

    return number_utils.get_integer(moderate_time), number_utils.get_integer(highly_time)


# 預設複雜性傷科治療時間
def get_default_complicated_massage_time(system_settings):
    moderate_time = system_settings.field('預設中度複雜性傷科治療時間')
    if moderate_time is None:
        moderate_time = 10

    highly_time = system_settings.field('預設高度複雜性傷科治療時間')
    if highly_time is None:
        highly_time = 20

    return number_utils.get_integer(moderate_time), number_utils.get_integer(highly_time)


def save_electrical_prescript(database, system_settings, case_key):
    file_path = os.path.join(system_settings.field('電子處方箋路徑'))
    if not os.path.exists(file_path):
        system_utils.show_message_box(
            QMessageBox.Critical,
            '無法連線到包藥機',
            '<h3>找不到包藥機的資料路徑, 請確定電子處方箋路徑是否正確</h3>',
            '請確認資料路徑是否存在'
        )
        return

    if case_utils.get_electrical_prescript_status(database, case_key) == 'Y':
        msg_box = dialog_utils.get_message_box(
            '電子調劑', QMessageBox.Warning,
            '''<font color="red"><b>
                    此病歷已經產生過電子調劑處方箋了, 是否重新產生新的電子調劑處方箋?
                </b></font>
            ''',
            '重新產生電子處方箋，藥局調劑電腦會出現新的調劑處方箋.'
        )
        save_record = msg_box.exec_()
        if not save_record:
            return

    if system_settings.field('電子處方箋格式') == '格式2':
        save_electric_prescript2(database, system_settings, case_key)
    else:
        save_electric_prescript1(database, system_settings, case_key)


# 電子處方箋格式1
def save_electric_prescript1(database, system_settings, case_key):
    sql = f'''
        SELECT CaseDate, Name, PatientKey FROM cases
        WHERE
            CaseKey = {case_key}
    '''
    case_rows = database.select_record(sql)
    if len(case_rows) <= 0:
        return

    case_row = case_rows[0]

    sql = f'''
        SELECT prescript.*, dosage.Days, dosage.Packages, dosage.Instruction AS instruction
        FROM prescript
            LEFT JOIN dosage ON dosage.CaseKey = prescript.CaseKey
        WHERE
            prescript.CaseKey = {case_key} AND
            MedicineType NOT IN ("穴道", "處置")
        GROUP BY prescript.PrescriptKey
        ORDER BY prescript.MedicineSet, PrescriptKey
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    name = case_row['Name']
    patient_key = case_row['PatientKey']
    case_date = case_row['CaseDate'].date()
    drug_no = registration_utils.get_electric_drug_no(
        database, system_settings, case_date, case_key
    )
    drug_no = f'{drug_no:0>3}'

    filename = f'{case_date.strftime("%Y%m%d")}_{drug_no}.csv'
    csv_file = os.path.join(system_settings.field('電子處方箋路徑'), filename)
    with open(csv_file, 'w', newline='', encoding='utf8') as csvfile:
        writer = csv.writer(csvfile)
        for row in rows:
            dosage1 = number_utils.get_float(row['Dosage'])
            if dosage1 == 0:
                continue

            days = number_utils.get_integer(row['Days'])
            if days == 0:
                days = 1

            total_dosage = dosage1 * days

            packages = number_utils.get_integer(row['Packages'])
            if packages == 0:
                packages = 1

            dosage2 = dosage1 / packages

            if number_utils.get_integer(row['MedicineSet']) == 1:
                is_ins = 'Y'
            else:
                is_ins = 'N'

            location = string_utils.xstr(row['Unit'])
            if location == '':
                location = 'n/a'

            csv_line = [
                drug_no,
                string_utils.xstr(row['MedicineKey']),
                string_utils.xstr(row['MedicineName']),
                f'{total_dosage:.1f}',
                days,
                f'{dosage2:.2f}',
                string_utils.xstr(row['instruction']),
                'N',
                is_ins,
                patient_key,
                name,
                packages,
                string_utils.xstr(row['Unit']),
            ]
            writer.writerow(csv_line)

    case_utils.set_electrical_prescript_status(database, case_key)


# 電子處方箋格式2
def save_electric_prescript2(database, system_settings, case_key):
    '''太初專用.'''
    sql = f'''
        SELECT
            cases.CaseKey, cases.CaseDate, cases.DoctorDate, cases.Name, cases.PatientKey, cases.Doctor,
            patient.Gender, patient.Birthday, patient.Remark
        FROM cases
            LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
        WHERE
            CaseKey = {case_key}
    '''
    case_rows = database.select_record(sql)
    if len(case_rows) <= 0:
        return

    case_row = case_rows[0]

    max_medicine_set = get_max_medicine_set(database, case_key)
    for i in range(max_medicine_set):
        medicine_set = i + 1
        save_electric_prescript2_xml(database, system_settings, case_row, medicine_set)


def get_prescript_remark_rows(database, case_key, medicine_set, prefix):
    sql = f'''
        SELECT MedicineName from prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set} AND
            MedicineType = "備註" AND
            MedicineName LIKE "{prefix}%"
    '''
    rows = database.select_record(sql)

    return rows


def get_prescript_remark(database, case_key, medicine_set):
    prefix = '備註:'
    rows = get_prescript_remark_rows(database, case_key, medicine_set, prefix)
    if len(rows) <= 0:
        return ''

    prescript_remark = ''
    for row in rows:
        remark = string_utils.xstr(row['MedicineName']).split(prefix)[1]
        prescript_remark += remark

    return prescript_remark


def save_electric_prescript2_xml(database, system_settings, case_row, medicine_set):
    '''太初專用.'''
    case_key = case_row['CaseKey']
    patient_key = case_row['PatientKey']
    patient_remark = string_utils.get_str(case_row['Remark'], 'utf8')
    
    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)

    sql = f'''
        SELECT prescript.*, dosage.Days, dosage.Packages, dosage.Instruction AS instruction
        FROM prescript
            LEFT JOIN dosage ON dosage.CaseKey = prescript.CaseKey
        WHERE
            prescript.CaseKey = {case_key} AND
            prescript.MedicineSet = {medicine_set} AND
            MedicineType NOT IN ("穴道", "處置")
        GROUP BY prescript.PrescriptKey
        ORDER BY prescript.MedicineSet, PrescriptKey
    '''
    rows = database.select_record(sql)
    if pres_days <= 0 or len(rows) <= 0:  # 未開藥或處置不包
        return

    generate_xml_file = False
    if medicine_set == 1:
        generate_xml_file = True  # 健保一定要包
    else:
        for row in rows:
            medicine_name = string_utils.xstr(row['MedicineName'])
            # if '健保合包' in medicine_name:
            #     generate_xml_file = False  # 健保合包要跟健保藥包在一起，不要產生包藥檔
            #     break

            if '自費另包' in medicine_name:
                generate_xml_file = True  # 自費科中要送到包藥機
                break

    if not generate_xml_file:
        return

    name = string_utils.xstr(case_row['Name'])
    medicine_bag_name_mask = patient_utils.get_patient_extension_settings(database, patient_key, '藥包姓名遮蔽')
    if medicine_bag_name_mask == '1':
        name = string_utils.get_mask_name(name)

    medicine_bag_no_name = patient_utils.get_patient_extension_settings(database, patient_key, '藥包姓名不印')
    if medicine_bag_no_name == '1':    
        name = ''
    
    doctor = string_utils.xstr(case_row['Doctor'])
    gender = string_utils.xstr(case_row['Gender'])
    patient_key = case_row['PatientKey']
    case_date = case_row['CaseDate'].date()
    doctor_done_time = case_row['DoctorDate'].time().strftime('%H:%M:%S')
    drug_no = registration_utils.get_electric_drug_no(
        database, system_settings, case_date, case_key
    )
    prescript_remark = get_prescript_remark(database, case_key, medicine_set)

    filename = f'{case_key:0>10}-{medicine_set:0>2}.xml'
    xml_filename = os.path.join(system_settings.field('電子處方箋路徑'), filename)

    root = ET.Element('d_clinic001_export_xml')
    xml_row = ET.SubElement(root, 'd_clinic001_export_xml_row')

    his_name = ET.SubElement(xml_row, 'his_name')
    his_name.text = name

    his_date = ET.SubElement(xml_row, 'his_date')
    his_date.text = case_date.strftime('%Y-%m-%d')

    his_use = ET.SubElement(xml_row, 'his_use')
    his_use.text = f'每日{packages}次'

    his_num = ET.SubElement(xml_row, 'his_num')
    his_num.text = string_utils.xstr(packages * pres_days)

    numeric_list = [
        'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
    ]
    for digit in numeric_list:
        num = ET.SubElement(xml_row, digit)
        num.text = '0'

    history = ET.SubElement(xml_row, 'history')
    history.text = f'{case_key:0>10}'

    dr = ET.SubElement(xml_row, 'dr')
    dr.text = doctor

    get_no = ET.SubElement(xml_row, 'get_no')
    get_no.text = drug_no

    age_year, _ = date_utils.get_age(case_row['Birthday'], case_row['CaseDate'])
    age = ET.SubElement(xml_row, 'age')
    age.text = string_utils.xstr(age_year)

    deal_sex = ET.SubElement(xml_row, 'deal_sex')
    deal_sex.text = gender

    subject = ET.SubElement(xml_row, 'subject')
    subject.text = '中醫'

    pcname = ET.SubElement(xml_row, 'pcname')
    pcname.text = ''

    eatdays = ET.SubElement(xml_row, 'eatdays')
    eatdays.text = string_utils.xstr(pres_days)

    drdate = ET.SubElement(xml_row, 'drdate')
    drdate.text = doctor_done_time

    if medicine_set == 1:
        package_name = '健保'
    else:
        package_name = f'自費{medicine_set-1}'

    his_id = ET.SubElement(xml_row, 'his_id')
    his_id.text = f'{patient_key:0>6}-{package_name}'

    notes = ET.SubElement(xml_row, 'Notes')
    notes.text = prescript_remark

    tree = ET.ElementTree(root)
    tree.write(
        xml_filename, pretty_print=True,
        xml_declaration=False,
        doctype='<?xml version="1.0" encoding="BIG5"?>',
        encoding="Big5"
    )

    case_utils.set_electrical_prescript_status(database, case_key)


def get_medicine_set_list(database, case_key):
    medicine_set_list = []

    sql = f'''
        SELECT MedicineSet FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet >= 2
        GROUP BY MedicineSet
        ORDER BY MedicineSet
    '''
    rows = database.select_record(sql)

    for row in rows:
        medicine_set_list.append(row['MedicineSet'])

    return medicine_set_list


def get_prescript_remark_items(database, prefix):
    sql = f'''
        SELECT MedicineName from prescript
        WHERE
            MedicineType = "備註" AND
            MedicineName LIKE "{prefix}%"
        GROUP BY MedicineName
        ORDER BY MedicineName
    '''
    rows = database.select_record(sql)

    return rows


def get_prescript_remark_row(parent, database, case_key):
    prefix = '備註:'
    rows = get_prescript_remark_items(database, prefix)

    items = [None]
    for row in rows:
        prescript_remark = string_utils.xstr(row['MedicineName'])
        items.append(prescript_remark.split(prefix)[1])

    input_dialog = QInputDialog()
    input_dialog.setOkButtonText('確定')
    input_dialog.setCancelButtonText('取消')
    prescript_remark, ok = input_dialog.getItem(
        parent, '設定處方備註', '請輸入處方備註', items, 0, True)

    if not ok or not prescript_remark:
        return None

    row = {}
    row['MedicineKey'] = None
    row['MedicineType'] = '備註'
    row['Price'] = None
    row['Amount'] = None
    row['InsCode'] = None
    row['MedicineName'] = f'備註:{prescript_remark}'
    row['Unit'] = None

    return row


def get_medicine_name_remark(parent):
    items = [None, '水揮', '生粉', '特']

    input_dialog = QInputDialog()
    input_dialog.setOkButtonText('確定')
    input_dialog.setCancelButtonText('取消')
    medicine_name_remark, ok = input_dialog.getItem(
        parent, '設定處方加註名稱', '請選擇處方加註名稱', items, 0, True)

    if not ok or not medicine_name_remark:
        return None
    else:
        return medicine_name_remark


def is_prescript_exists(table_widget, col_no, in_medicine_name):
    medicine_name_exists = False
    for row_no in range(table_widget.rowCount()):
        item = table_widget.item(row_no, col_no)
        if item is None:
            continue

        medicine_name = item.text()
        if in_medicine_name in medicine_name:
            medicine_name_exists = True
            break

    return medicine_name_exists


def check_extend_ins_drug(ins_tab, self_tab):
    if ins_tab is None or self_tab is None:
        return

    extend_ins_drug = is_prescript_exists(
        self_tab.tableWidget_prescript, SELF_PRESCRIPT_COL_NO['MedicineName'], '健保合包')

    if not extend_ins_drug:
        return

    packages = ins_tab.comboBox_package.currentText()
    pres_days = ins_tab.comboBox_pres_days.currentText()
    instruction = ins_tab.comboBox_instruction.currentText()

    if self_tab.comboBox_package.currentText() != packages:
        self_tab.comboBox_package.setCurrentText(packages)
    if self_tab.comboBox_pres_days.currentText() != pres_days:
        self_tab.comboBox_pres_days.setCurrentText(pres_days)
    if self_tab.comboBox_instruction.currentText() != instruction:
        self_tab.comboBox_instruction.setCurrentText(instruction)


def truncate_treatment(treatment):
    if treatment is None:
        treatment = '內科'
    elif '療程2-6次' in treatment:
        treatment = treatment.replace('療程2-6次', '')
    if '起始次' in treatment:
        treatment = treatment.replace('起始次', '')
    if '後續治療' in treatment:
        treatment = treatment.replace('後續治療', '')

    return treatment


# 藥品是否停用
def get_medicine_deactivate(database, medicine_key):
    if medicine_key in ['', None]:
        return None

    sql = f'''
        SELECT Deactivate FROM medicine
        WHERE
            MedicineKey = {medicine_key}
    '''
    rows = database.select_record(sql)

    if len(rows) > 0:
        return rows[0]['Deactivate']
    else:
        return None


# 藥品是含動物性成份 2026-01-27
def is_animal_derived(database, medicine_key):
    if medicine_key in ['', None]:
        return False

    sql = f'''
        SELECT AnimalDerived FROM medicine
        WHERE
            MedicineKey = {medicine_key}

    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return False

    row = rows[0]
    if row['AnimalDerived'] == 1:
        return True
    else:
        return False


def get_medicine_record(database, medicine_key):
    sql = f'''
        SELECT * FROM medicine
        WHERE
            MedicineKey = {medicine_key}
    '''
    rows = database.select_record(sql)

    if len(rows) > 0:
        return rows[0]
    else:
        return None

def get_ins_prescript_rows(database, case_key, medicine_set):
    sql = f'''
        SELECT PrescriptKey FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set} AND
            prescript.MedicineType IN ("單方", "複方", "科中", "科學中藥", "自費科中")
    '''
    rows = database.select_record(sql)

    return rows


def refresh_medicine_type(database, medicine_name):
    sql = f'''
        SELECT MedicineType FROM medicine
        WHERE
            MedicineName Like "{medicine_name}%" AND
            MedicineType NOT IN ("單方", "複方")
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        return rows[0]['MedicineType']
    else:
        return None


def refresh_location(database, medicine_type, medicine_name, unit):
    sql = f'''
        SELECT Location FROM medicine        
        WHERE
            MedicineType = "{medicine_type}" AND
            MedicineName = "{medicine_name}" AND
            Unit = "{unit}"    
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        location = rows[0]['Location']
        return location

    return None


# 使否有代煎水藥
def is_herbal_decocation_service(table_widget_prescript):
    '''使否有代煎水藥'''
    
    herbal_decocation_service = False
    
    for row_no in range(table_widget_prescript.rowCount()):
        item = table_widget_prescript.item(
            row_no, SELF_PRESCRIPT_COL_NO['MedicineName'])
        if item is None:
            continue

        medicine_name = item.text()
        if '代煎' in medicine_name:
            herbal_decocation_service = True
            break

    return herbal_decocation_service


# 取得自費水藥淨重
def get_herbal_net_weight(is_herbal_decocation_service, table_widget_prescript):
    '''取得自費水藥淨重: 去掉自費水藥, 代煎費, 有單價的高貴藥費'''
    
    net_weight = 0
    
    for row_no in range(table_widget_prescript.rowCount()):
        item = table_widget_prescript.item(
            row_no, SELF_PRESCRIPT_COL_NO['MedicineName'])
        if item is None:
            continue

        medicine_name = item.text()
        if medicine_name in ['自費水藥']:
            continue
        
        if '代煎' in medicine_name:
            continue

        if not is_herbal_decocation_service and '生薑' in medicine_name:  # 自煎 (無代煎)要扣掉生薑的重量
            continue

        item = table_widget_prescript.item(row_no, SELF_PRESCRIPT_COL_NO['Price'])
        if item is not None and number_utils.get_float(item.text()) > 0:  # 有高貴藥費
            continue

        item = table_widget_prescript.item(row_no, SELF_PRESCRIPT_COL_NO['Dosage'])
        if item is None:
            continue

        try:
            current_weight = number_utils.get_float(item.text())
        except ValueError:
            continue

        net_weight += current_weight

    return net_weight



def duplicate_table_widget(src_table, dst_table):
    def table_to_list(table):
        rows = table.rowCount()
        cols = table.columnCount()
        data = []
        for r in range(rows):
            row_data = []
            for c in range(cols):
                it = table.item(r, c)

                if c in [
                        SELF_PRESCRIPT_COL_NO['PrescriptKey'],                        
                    ]:
                    row_data.append(("-1", None))
                    continue
                elif c in [
                        SELF_PRESCRIPT_COL_NO['MedicineSet'],
                    ]:
                    row_data.append(("", None))   # 不拷貝 → 填空 (或填 None)
                    continue
            
                if it is None:
                    row_data.append(("", None))   # 空白格也是一筆
                else:
                    txt = it.text()
                    align = it.data(QtCore.Qt.TextAlignmentRole)
                    row_data.append((txt, align))
                    
            data.append(row_data)
            
        return data

    def list_to_table(table, data):
        table.blockSignals(True)
        was_sort = table.isSortingEnabled()
        table.setSortingEnabled(False)
        table.setUpdatesEnabled(False)

        rows = len(data)
        cols = len(data[0]) if rows else 0
        table.setRowCount(rows)
        table.setColumnCount(cols)

        for r in range(rows):
            for c in range(cols):
                txt, align = data[r][c]
                it = table.item(r, c)
                if it is None:
                    it = QtWidgets.QTableWidgetItem()
                    table.setItem(r, c, it)

                it.setText(txt)
                if align is not None:
                    it.setData(QtCore.Qt.TextAlignmentRole, align)

        table.setUpdatesEnabled(True)
        table.setSortingEnabled(was_sort)
        table.blockSignals(False)

    data = table_to_list(src_table)
    list_to_table(dst_table, data)


def duplicate_ins_table_widget(database, src_table, dst_table):
    def table_to_list(table, dst_table):
        rows = table.rowCount()
        cols = dst_table.columnCount()
        data = []
        for r in range(rows):
            row_data = []
            medicine_key = None
            price = 0
            dosage = 0
            for c in range(cols):
                it = table.item(r, c)

                if c == INS_PRESCRIPT_COL_NO['MedicineKey'] and it is not None:
                    medicine_key = it.text()
                if c == INS_PRESCRIPT_COL_NO['Dosage'] and it is not None:
                    dosage = number_utils.get_float(it.text())
                    
                if c in [
                        INS_PRESCRIPT_COL_NO['PrescriptKey'],                        
                    ]:
                    row_data.append(("-1", None))
                    continue
                elif c in [
                        INS_PRESCRIPT_COL_NO['MedicineSet'],
                    ]:
                    row_data.append(("", None))   # 不拷貝 → 填空 (或填 None)
                    continue
                elif c in [
                        SELF_PRESCRIPT_COL_NO['Price'],
                    ]:
                    if medicine_key is not None:
                        price = number_utils.get_float(get_medicine_field(database, medicine_key, 'SalePrice'))

                    row_data.append(
                        (f'{price:.2f}', (QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)))
                    continue
                elif c in [
                        SELF_PRESCRIPT_COL_NO['Amount'],
                    ]:
                    if price is not None and dosage is not None:
                        amount = price * dosage

                        row_data.append(
                            (f'{amount:.2f}', (QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)))
                        continue
            
                if it is None:
                    row_data.append(("", None))   # 空白格也是一筆
                else:
                    txt = it.text()
                    align = it.data(QtCore.Qt.TextAlignmentRole)
                    row_data.append((txt, align))

            data.append(row_data)
            
        return data

    def list_to_table(table, data):
        table.blockSignals(True)
        was_sort = table.isSortingEnabled()
        table.setSortingEnabled(False)
        table.setUpdatesEnabled(False)

        rows = len(data)
        cols = len(data[0]) if rows else 0
        table.setRowCount(rows)
        table.setColumnCount(cols)

        for r in range(rows):
            for c in range(cols):
                txt, align = data[r][c]
                it = table.item(r, c)
                if it is None:
                    it = QtWidgets.QTableWidgetItem()
                    table.setItem(r, c, it)

                it.setText(txt)
                if align is not None:
                    it.setData(QtCore.Qt.TextAlignmentRole, align)

        table.setUpdatesEnabled(True)
        table.setSortingEnabled(was_sort)
        table.blockSignals(False)

    data = table_to_list(src_table, dst_table)
    list_to_table(dst_table, data)

    
