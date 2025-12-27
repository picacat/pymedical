# 自費管理系統函式庫 2021.10.04
# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets

from libs import (case_utils, charge_utils, class_utils, medicine_utils,
                  number_utils, prescript_utils, string_utils)

PURCHASE_COL_NO = {
    'prescript_key': 0,
    'case_key': 1,
    'medicine_set': 2,
    'medicine_type': 3,
    'medicine_key': 4,
    'case_date': 5,
    'return_date': 6,
    'period': 7,
    'patient_key': 8,
    'name': 9,
    'ins_type': 10,
    'invoice_no': 11,
    'promotion': 12,
    'medicine_name': 13,
    'quantity': 14,
    'unit': 15,
    'pres_days': 16,
    'total_dosage': 17,
    'price': 18,
    'discount': 19,
    'total_fee': 20,
    'receipt_fee': 21,
    'debt': 22,
    'repayment': 23,
    'repayment_date': 24,
    'return_fee': 25,
    'doctor': 26,
    'doctor_commission_rate': 27,
    'doctor_commission': 28,
    'massage_assistant': 29,
    'massager_commission_rate': 30,
    'massager_commission': 31,
    'nursing_assistant': 32,
    'cashier_commission_rate': 33,
    'cashier_commission': 34,
    'dealer': 35,
    'remark': 36,
}

PRESCRIPT_COL_NO = {
    'MedicineKey': 0,
    'MedicineType': 1,
    'Promotion': 2,
    'MedicineName': 3,
    'Unit': 4,
    'Quantity': 5,
    'Price': 6,
    'Amount': 7,
    'DiscountFee': 8,
    'Debt': 9,
    'Course': 10,
    'Remove': 11,
}


def set_purchase_list_table(database, in_table_widget):
    table_widget_purchase_list = class_utils.get_table_widget(
        in_table_widget, database
    )
    table_widget_purchase_list.set_column_hidden([
        PURCHASE_COL_NO['prescript_key'],
        PURCHASE_COL_NO['case_key'],
        PURCHASE_COL_NO['medicine_set'],
        PURCHASE_COL_NO['medicine_type'],
        PURCHASE_COL_NO['medicine_key'],
    ])

    width = [
        100, 100, 100, 100, 100,  # invisible fileds
        130, 130, 50, 70, 90, 50,
        120, 50, 250, 50, 75, 50, 50, 70,
        70, 90, 90, 70, 70, 160, 90,
        90, 70, 70,
        90, 70, 70,
        90, 70, 70, 90,
        250,
    ]
    table_widget_purchase_list.set_table_heading_width(width)


def is_herb_or_powder(database, case_key):
    sql = f'''
        SELECT * FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineName IN ("自費水藥", "自費粉藥")
        LIMIT 1
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        return True

    return False


def check_single_compound(database, case_key, medicine_type):
    if medicine_type == '成方表頭':
        return False

    if case_key in ['', None]:
        return False

    sql = f'''
        SELECT MedicineKey FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineType = "成方表頭"
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return False

    row = rows[0]
    medicine_key = row['MedicineKey']
    single_compound = medicine_utils.get_medicine_extend(database, medicine_key, '成方單項')
    title_compound = medicine_utils.get_medicine_extend(database, medicine_key, '成方抬頭')
    if single_compound == 'Y' and title_compound == 'Y':
        return True

    return False


def set_purchase_list_data(
        database, table_widget, row, row_no, refresh_record=False,
        query_start_date=None, query_end_date=None):
    if row is None:
        return False

    case_key = row['CaseKey']
    if case_key is None:
        return False

    price = number_utils.get_float(row['Price'])
    # if price <= 0:
    #     return False

    medicine_type = string_utils.xstr(row['MedicineType'])
    if price <= 0 and medicine_type in ['單方', '複方', '水藥', '穴道', '處置']:
        return False

    if medicine_type == '成方表頭' and is_herb_or_powder(database, case_key):
        return False

    # if check_single_compound(database, case_key, medicine_type):
    #     return False

    prescript_key = string_utils.xstr(row['PrescriptKey'])
    medicine_set = row['MedicineSet']
    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    treat_type = string_utils.xstr(row['TreatType'])

    if row['DiscountFee'] is None:
        try:
            discount_fee = _get_discount_fee(database, row, case_key, medicine_set)
        except Exception:
            discount_fee = 0
    else:
        discount_fee = number_utils.get_integer(row['DiscountFee'])

    if pres_days <= 0:
        pres_days = 1

    dosage = number_utils.get_float(row['Dosage'])
    if dosage == 0:
        dosage = 1

    medicine_key = string_utils.xstr(row['MedicineKey'])
    medicine_name = string_utils.xstr(row['MedicineName'])
    medicine_type = string_utils.xstr(row['MedicineType'])
    remark = string_utils.xstr(row['Remark'])

    try:
        sale_date = row['SaleDate'].strftime('%Y-%m-%d')
    except Exception:
        sale_date = None

    if '(退貨)' in medicine_name or '(換貨)' in medicine_name:
        try:
            case_date = row['CaseDate'].strftime('%Y-%m-%d')
        except Exception:
            case_date = None

        # pres_days = 1

        if '(退貨)' in medicine_name and \
                ('自費水藥' in medicine_name or '自費粉藥' in medicine_name or medicine_name in '代煎水藥'):
            pres_days = dosage
            dosage = 1
    else:
        case_date = None

    doctor = string_utils.xstr(row['Doctor'])

    massage_referrer = prescript_utils.get_pres_extend_value(database, prescript_key, '傷助推薦')
    if massage_referrer in [None, '']:
        massage_referrer = string_utils.xstr(row['MassageReferrer'])

    nursing_assistant = prescript_utils.get_pres_extend_value(database, prescript_key, '護佐')
    if nursing_assistant in [None, '']:
        nursing_assistant = string_utils.xstr(row['NursingAssistant'])

    price = number_utils.get_float(row['Price'])
    amount = number_utils.get_float(row['Amount'])
    if amount <= 0:
        amount = price * dosage

    if price <= 0:
        discount_fee = 0

    debt = number_utils.get_integer(row['Debt'])
    total_amount = number_utils.get_integer(amount * pres_days) - discount_fee
    receipt_fee = total_amount - debt

    if debt > 0:
        repayment_date, repayment = get_repayment(database, prescript_key)
        if repayment >= debt:
            repayment = debt

        if query_start_date is not None and query_end_date is not None and repayment_date is not None and \
           (repayment_date[:10] < query_start_date or repayment_date[:10] > query_end_date):
            repayment_date, repayment = None, None
    else:
        repayment_date, repayment = None, None

    if '(退貨)' in medicine_name:
        receipt_fee = total_amount + debt
        return_fee = abs(receipt_fee)
        debt = -debt
    else:
        return_fee = 0

    if debt > 0 and debt - number_utils.get_integer(repayment) > 0:  # 欠款不得抽成
        doctor_commission_rate = None
        massager_commission_rate = None
        cashier_commission_rate = None
    else:
        doctor_commission_rate = get_commission_rate(
            database, medicine_key, medicine_name, '醫師',
            doctor, massage_referrer, nursing_assistant, amount, pres_days, discount_fee,
            treat_type, remark,
        )
        massager_commission_rate = get_commission_rate(
            database, medicine_key, medicine_name, '推拿師父',
            doctor, massage_referrer, nursing_assistant, amount, pres_days, discount_fee,
            treat_type, remark,
        )
        cashier_commission_rate = get_commission_rate(
            database, medicine_key, medicine_name, '櫃台',
            doctor, massage_referrer, nursing_assistant, amount, pres_days, discount_fee,
            treat_type, remark,
        )

    if '(退貨)' in medicine_name or '(換貨)' in medicine_name:
        doctor_commission_rate = get_commission_rate(
            database, medicine_key, medicine_name, '醫師',
            doctor, massage_referrer, nursing_assistant, abs(amount), pres_days, abs(discount_fee),
            treat_type, remark,
        )
        massager_commission_rate = get_commission_rate(
            database, medicine_key, medicine_name, '推拿師父',
            doctor, massage_referrer, nursing_assistant, abs(amount), pres_days, abs(discount_fee),
            treat_type, remark,
        )
        cashier_commission_rate = get_commission_rate(
            database, medicine_key, medicine_name, '櫃台',
            doctor, massage_referrer, nursing_assistant, abs(amount), pres_days, abs(discount_fee),
            treat_type, remark,
        )

    if treat_type in ['療程實現', '療程實現贈送']:
        unit_price = _get_unit_price(database, medicine_key)
        doctor_commission = get_commission(doctor_commission_rate, unit_price) * dosage
        massager_commission = get_commission(massager_commission_rate, unit_price) * dosage
        cashier_commission = get_commission(cashier_commission_rate, unit_price) * dosage
    else:
        if repayment is not None:
            commision_receipt = receipt_fee + number_utils.get_integer(repayment)
        else:
            commision_receipt = receipt_fee

        doctor_commission = get_commission(doctor_commission_rate, commision_receipt)
        massager_commission = get_commission(massager_commission_rate, commision_receipt)
        cashier_commission = get_commission(cashier_commission_rate, commision_receipt)

    if '(退貨)' in medicine_name or '(換貨)' in medicine_name:
        if query_start_date is not None and query_end_date is not None and \
           sale_date != case_date and (case_date < query_start_date or case_date > query_end_date):
            return
        
        if doctor_commission > 0:
            doctor_commission = -doctor_commission

        if massager_commission > 0:
            massager_commission = -massager_commission

        if cashier_commission > 0:
            cashier_commission = -cashier_commission

    total_dosage = dosage * pres_days
    
    if not refresh_record:
        table_widget.setRowCount(table_widget.rowCount() + 1)

    prescript_record = [
        prescript_key,
        case_key,
        string_utils.xstr(row['MedicineSet']),
        medicine_type,
        string_utils.xstr(row['MedicineKey']),
        sale_date,
        case_date,
        string_utils.xstr(row['Period']),
        row['PatientKey'],
        string_utils.xstr(row['Name']),
        string_utils.xstr(row['InsType']),
        string_utils.xstr(row['InvoiceNo']),
        string_utils.xstr(row['Promotion']),
        medicine_name,
        dosage,
        string_utils.xstr(row['Unit']),
        pres_days,
        total_dosage,
        number_utils.get_integer(price),
        discount_fee,
        total_amount,
        receipt_fee,
        debt,
        repayment,
        repayment_date,
        return_fee,
        doctor,
        doctor_commission_rate,
        doctor_commission,
        massage_referrer,
        massager_commission_rate,
        massager_commission,
        nursing_assistant,
        cashier_commission_rate,
        cashier_commission,
        string_utils.xstr(row['Dealer']),
        string_utils.get_str(row['Remark'], 'utf8'),
    ]

    for col_no in range(len(prescript_record)):
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, prescript_record[col_no])
        table_widget.setItem(row_no, col_no, item)
        cell_item = table_widget.item(row_no, col_no)
        if col_no in [
            PURCHASE_COL_NO['patient_key'],
            PURCHASE_COL_NO['quantity'],
            PURCHASE_COL_NO['pres_days'],
            PURCHASE_COL_NO['total_dosage'],
            PURCHASE_COL_NO['price'],
            PURCHASE_COL_NO['total_fee'],
            PURCHASE_COL_NO['discount'],
            PURCHASE_COL_NO['debt'],
            PURCHASE_COL_NO['repayment'],
            PURCHASE_COL_NO['return_fee'],
            PURCHASE_COL_NO['receipt_fee'],
            PURCHASE_COL_NO['doctor_commission_rate'],
            PURCHASE_COL_NO['doctor_commission'],
            PURCHASE_COL_NO['massager_commission_rate'],
            PURCHASE_COL_NO['massager_commission'],
            PURCHASE_COL_NO['cashier_commission_rate'],
            PURCHASE_COL_NO['cashier_commission'],
        ]:
            if cell_item is not None:
                cell_item.setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
        elif col_no in [
            PURCHASE_COL_NO['promotion'],
            PURCHASE_COL_NO['unit'],
        ]:
            if cell_item is not None:
                cell_item.setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

        if cell_item is not None and '(退貨)' in medicine_name:
            cell_item.setForeground(QtGui.QColor('blue'))
        elif cell_item is not None and '(換貨)' in medicine_name:
            cell_item.setForeground(QtGui.QColor('magenta'))
        elif cell_item is not None and debt > 0:
            if debt - number_utils.get_integer(repayment) > 0:
                cell_item.setForeground(QtGui.QColor('red'))
            else:
                cell_item.setForeground(QtGui.QColor('darkGreen'))

        if discount_fee > 0 and col_no == PURCHASE_COL_NO['discount']:
            cell_item.setForeground(QtGui.QColor('brown'))

        if (discount_fee > doctor_commission or
            discount_fee > massager_commission or
            discount_fee > cashier_commission) and \
           col_no == PURCHASE_COL_NO['discount']:
            cell_item.setForeground(QtGui.QColor('red'))

        if '湯包' in medicine_type and '(贈)' in medicine_name and \
           dosage > 1 and \
           col_no in [PURCHASE_COL_NO['medicine_name'], PURCHASE_COL_NO['quantity']]:
            cell_item.setForeground(QtGui.QColor('green'))

    return True


def _get_discount_fee(database, row, case_key, medicine_set):
    medicine_name = string_utils.xstr(row['MedicineName'])
    if medicine_name in ['代煎水藥']:
        return 0

    discount_fee = number_utils.get_integer(row['DiscountFee'])
    if discount_fee <= 0:
        discount_fee = case_utils.get_discount_fee(database, case_key, medicine_set)

    if number_utils.get_integer(discount_fee) <= 0:
        sql = f'''
            SELECT DiscountFee FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            discount_fee = number_utils.get_integer(row['DiscountFee'])

    if '(退貨)' in medicine_name or '(換貨)' in medicine_name:
        discount_fee = -discount_fee

    return discount_fee


def _get_unit_price(database, medicine_key):
    sql = f'''
        SELECT Dosage, SalePrice FROM medicine
        WHERE
            MedicineKey = {medicine_key}
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return 0

    row = rows[0]

    dosage = number_utils.get_integer(row['Dosage'])
    if dosage <= 0:
        return 0

    sale_price = number_utils.get_integer(row['SalePrice'])

    unit_price = sale_price / dosage

    return unit_price


def get_repayment(database, prescript_key):
    if prescript_key == '':
        return None, 0

    sql = f'''
        SELECT * FROM debt
        WHERE
            PrescriptKey = {prescript_key}
    '''

    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None, 0

    row = rows[0]
    if row['ReturnDate1'] is not None:
        return_date = f"{row['ReturnDate1'].strftime('%Y-%m-%d')} {string_utils.xstr(row['Period1'])}"
    else:
        return_date = None

    return return_date, number_utils.get_integer(row['TotalReturn'])


def get_commission_rate(
        database, medicine_key, medicine_name, position,
        doctor, massage_referrer, nursing_assistant, total_fee, pres_days, discount_fee, treat_type, remark=''):
    if (position == '醫師' and doctor == '') or \
            (position == '推拿師父' and massage_referrer == '') or \
            (position == '櫃台' and nursing_assistant == ''):
        return None

    if medicine_key in ['', None]:
        if medicine_name in ['自費水藥', '自費粉藥']:
            commission_rate = '20%'

            if position == '醫師':
                if massage_referrer not in ['', None] or nursing_assistant not in ['', None]:
                    commission_type = '分成率'
                else:
                    commission_type = '抽成率'
            elif position in ['推拿師父', '傷助推薦']:
                if doctor not in ['', None] or nursing_assistant not in ['', None]:
                    commission_type = '分成率'
                else:
                    commission_type = '抽成率'
            elif position in ['櫃台', '護佐']:
                if doctor not in ['', None] or massage_referrer not in ['', None]:
                    commission_type = '分成率'
                else:
                    commission_type = '抽成率'

            sql = f'''
                SELECT Amount FROM charge_settings
                WHERE
                    ItemName = "{medicine_name}{position}{commission_type}"
            '''
            rows = database.select_record(sql)
            if len(rows) > 0:
                row = rows[0]
                commission_rate = f'{string_utils.xstr(row["Amount"])}%'

            if discount_fee > 0 and '%' in commission_rate:
                total_fee *= pres_days
                max_discount_fee = total_fee - (total_fee * 80 / 100)  # 折扣超過2成不得抽成
                if discount_fee >= max_discount_fee:
                    commission_rate = 0
                else:
                    commission_rate = number_utils.get_integer(commission_rate.split('%')[0])
                    commission_rate /= 2

                commission_rate = f'{commission_rate}%'
        else:
            commission_rate = None

        return commission_rate

    commission_rate = None
    sql = f'''
        SELECT * FROM medicine
        WHERE
            MedicineKey = {medicine_key}
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return commission_rate

    row = rows[0]

    if position == '醫師':
        if '無介紹人' in remark:
            commission_rate = charge_utils.get_commission_rate(
                database, medicine_key, '醫師', treat_type, medicine_name=medicine_name)
        elif '介紹人' in remark:  # 要在後，不然關鍵字會誤判
            commission_rate = charge_utils.get_commission_rate(
                database, medicine_key, '醫師分成', treat_type, medicine_name=medicine_name)
        elif massage_referrer not in [None, ''] or nursing_assistant not in [None, '']:
            commission_rate = charge_utils.get_commission_rate(
                database, medicine_key, '醫師分成', treat_type, medicine_name=medicine_name)
        else:
            commission_rate = charge_utils.get_commission_rate(
                database, medicine_key, '醫師', treat_type, doctor=doctor, medicine_name=medicine_name)
    elif position in ['推拿師父', '傷助推薦']:
        if doctor != '' or nursing_assistant != '' or '介紹人' in remark:
            commission_rate = charge_utils.get_commission_rate(
                database, medicine_key, '推拿師父分成', treat_type, medicine_name=medicine_name)
        elif doctor == '' and nursing_assistant == '':
            commission_rate = charge_utils.get_commission_rate(
                database, medicine_key, '推拿師父', treat_type, medicine_name=medicine_name)

        if commission_rate == '':
            commission_rate = charge_utils.get_commission_rate(
                database, medicine_key, '推拿師父分成', treat_type, medicine_name=medicine_name)

    elif position in ['櫃台', '護佐']:
        if doctor != '' or massage_referrer != '' or '介紹人' in remark:
            commission_rate = charge_utils.get_commission_rate(
                database, medicine_key, '櫃台分成', treat_type, medicine_name=medicine_name)
        elif doctor == '' and massage_referrer == '':
            commission_rate = charge_utils.get_commission_rate(
                database, medicine_key, '櫃台', treat_type, medicine_name=medicine_name)

        if commission_rate == '':
            commission_rate = charge_utils.get_commission_rate(
                database, medicine_key, '櫃台分成', treat_type, medicine_name=medicine_name)

    if discount_fee > 0 and '%' in commission_rate:
        max_discount_fee = total_fee - (total_fee * 80 / 100)  # 折扣超過2成不得抽成
        if discount_fee >= max_discount_fee:
            commission_rate = 0
        else:
            commission_rate = number_utils.get_integer(commission_rate.split('%')[0])
            commission_rate /= 2

        commission_rate = f'{commission_rate}%'

    if commission_rate in [None, '']:
        medicine_type = string_utils.xstr(row['MedicineType'])
        sql = f'''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = "藥品類別" AND
                DictGroupsName = "{medicine_type}"
        '''
        rows = database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            commission_rate = string_utils.xstr(row['DictGroupsLevel2'])
            if commission_rate != '':
                commission_rate += '%'

    if '%' not in string_utils.xstr(commission_rate) and \
            number_utils.get_float(commission_rate) < 1:
        commission_rate = number_utils.get_float(commission_rate) * 100
        commission_rate = f'{number_utils.get_integer(commission_rate)}%'

    return commission_rate


def get_commission(commission_rate, amount):
    commission = 0

    if commission_rate in ['', None]:
        return 0

    if '%' not in commission_rate:
        return number_utils.get_integer(commission_rate)

    commission_rate = number_utils.get_float(commission_rate.split('%')[0])

    commission = amount * commission_rate / 100

    return number_utils.get_float(commission)


def calculate_purchase_list_total(table_widget, start_date=None, end_date=None):
    total_discount, total_fee, total_receipt, total_debt, total_repayment, total_return = 0, 0, 0, 0, 0, 0
    total_dosage = 0
    total_doctor_commission, total_massager_commission, total_cashier_commission = 0, 0, 0

    check_date = None  # check_date 是否為單日銷售日期(單日結帳用)
    if start_date is not None and start_date == end_date:
        check_date = start_date

    for row_no in range(table_widget.rowCount()):
        medicine_name_item = table_widget.item(row_no, PURCHASE_COL_NO['medicine_name'])
        if medicine_name_item is None or medicine_name_item.text() == '合計':
            continue

        case_date = table_widget.item(row_no, PURCHASE_COL_NO['case_date']).text()  # 銷售日期
        return_date = table_widget.item(row_no, PURCHASE_COL_NO['return_date']).text()  # 退換貨日期

        total_discount += number_utils.get_integer(
            table_widget.item(row_no, PURCHASE_COL_NO['discount']).text()
        )

        if check_date is None or \
                (check_date is not None and (case_date == check_date or return_date == check_date)):
            total_fee += number_utils.get_integer(
                table_widget.item(row_no, PURCHASE_COL_NO['total_fee']).text()
            )

            total_receipt += number_utils.get_integer(
                table_widget.item(row_no, PURCHASE_COL_NO['receipt_fee']).text()
            )
            total_debt += number_utils.get_integer(
                table_widget.item(row_no, PURCHASE_COL_NO['debt']).text()
            )

        total_dosage += number_utils.get_integer(
            table_widget.item(row_no, PURCHASE_COL_NO['total_dosage']).text()
        )
        total_repayment += number_utils.get_integer(
            table_widget.item(row_no, PURCHASE_COL_NO['repayment']).text()
        )
        total_return += number_utils.get_integer(
            table_widget.item(row_no, PURCHASE_COL_NO['return_fee']).text()
        )
        total_doctor_commission += number_utils.get_integer(
            table_widget.item(row_no, PURCHASE_COL_NO['doctor_commission']).text()
        )
        total_massager_commission += number_utils.get_integer(
            table_widget.item(row_no, PURCHASE_COL_NO['massager_commission']).text()
        )
        total_cashier_commission += number_utils.get_integer(
            table_widget.item(row_no, PURCHASE_COL_NO['cashier_commission']).text()
        )

    total_list = [
        ['合計', PURCHASE_COL_NO['medicine_name']],
        [total_dosage, PURCHASE_COL_NO['total_dosage']],
        [total_discount, PURCHASE_COL_NO['discount']],
        [total_fee, PURCHASE_COL_NO['total_fee']],
        [total_receipt, PURCHASE_COL_NO['receipt_fee']],
        [total_debt, PURCHASE_COL_NO['debt']],
        [total_repayment, PURCHASE_COL_NO['repayment']],
        [total_return, PURCHASE_COL_NO['return_fee']],
        [total_doctor_commission, PURCHASE_COL_NO['doctor_commission']],
        [total_massager_commission, PURCHASE_COL_NO['massager_commission']],
        [total_cashier_commission, PURCHASE_COL_NO['cashier_commission']],
    ]

    font = QtGui.QFont()
    font.setBold(True)

    row_no = get_subtotal_row_no(table_widget)
    if row_no is None:
        row_no = table_widget.rowCount()
        table_widget.setRowCount(row_no+1)

    for data in total_list:
        value = data[0]
        col_no = data[1]
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, value)
        table_widget.setItem(row_no, col_no, item)
        table_widget.item(row_no, col_no).setFont(font)
        if isinstance(value, int):
            table_widget.item(row_no, col_no).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )


def get_subtotal_row_no(table_widget):
    for row_no in range(table_widget.rowCount()):
        item = table_widget.item(row_no, PURCHASE_COL_NO['medicine_name'])
        if item is None:
            continue

        if item.text() == '合計':
            return row_no

    return None


def _check_prescript_exists(tableWidget_prescript, medicine_row):
    exists = False
    in_medicine_key = string_utils.xstr(medicine_row['MedicineKey'])
    row_count = tableWidget_prescript.rowCount()

    for row_no in range(row_count):
        medicine_key = tableWidget_prescript.item(row_no, PRESCRIPT_COL_NO['MedicineKey'])
        if medicine_key is None:
            continue

        if in_medicine_key == medicine_key.text():
            quantity = tableWidget_prescript.item(row_no, PRESCRIPT_COL_NO['Quantity'])
            if quantity is not None:
                quantity = number_utils.get_float(quantity.text())
            else:
                quantity = 0

            tableWidget_prescript.setItem(
                row_no, PRESCRIPT_COL_NO['Quantity'],
                QtWidgets.QTableWidgetItem(string_utils.xstr(quantity + 1))
            )
            tableWidget_prescript.item(
                row_no, PRESCRIPT_COL_NO['Quantity']).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )
            exists = True
            break

    return exists


def insert_prescript_row(
        database, tableWidget_prescript, medicine_key,
        extra_process=None, cancel_button=False, discount_permission=True):
    sql = f'''
        SELECT * FROM medicine
        WHERE
            MedicineKey = {medicine_key}
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    row = rows[0]
    if _check_prescript_exists(tableWidget_prescript, row):
        return

    medicine_key = row['MedicineKey']

    row_no = tableWidget_prescript.rowCount()
    tableWidget_prescript.setFocus(True)
    tableWidget_prescript.insertRow(row_no)
    tableWidget_prescript.setCurrentCell(row_no, PRESCRIPT_COL_NO['Quantity'])

    if cancel_button:
        course_count = None
    else:
        bonus = medicine_utils.get_medicine_extend(database, medicine_key, '療程實現贈送')
        course_count = number_utils.get_integer(row['Dosage']) + number_utils.get_integer(bonus)

    prescript_row = [
        medicine_key,
        row['MedicineType'],
        None,
        row['MedicineName'],
        row['Unit'],
        1.0,
        number_utils.get_float(row['SalePrice']),
        number_utils.get_float(row['SalePrice']),
        0.0,
        0.0,
        course_count,
    ]
    for col_no in range(len(prescript_row)):
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, prescript_row[col_no])
        tableWidget_prescript.setItem(row_no, col_no, item)

        if col_no in [PRESCRIPT_COL_NO['Unit']]:
            tableWidget_prescript.item(
                row_no, col_no).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
            )
        elif col_no in [
            PRESCRIPT_COL_NO['Quantity'],
            PRESCRIPT_COL_NO['Price'],
            PRESCRIPT_COL_NO['Amount'],
            PRESCRIPT_COL_NO['DiscountFee'],
            PRESCRIPT_COL_NO['Debt'],
            PRESCRIPT_COL_NO['Course'],
        ]:
            item = tableWidget_prescript.item(row_no, col_no)
            if item is not None:
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        if col_no not in [
            PRESCRIPT_COL_NO['Quantity'],
            PRESCRIPT_COL_NO['Price'],
            PRESCRIPT_COL_NO['DiscountFee'],
            PRESCRIPT_COL_NO['Debt'],
            PRESCRIPT_COL_NO['Course'],
        ]:
            item = tableWidget_prescript.item(row_no, col_no)
            if item is not None:
                item.setFlags(QtCore.Qt.ItemIsEnabled)

    if not discount_permission:
        item = tableWidget_prescript.item(row_no, PRESCRIPT_COL_NO['DiscountFee'])
        if item is not None:
            item.setFlags(QtCore.Qt.ItemIsEnabled)

    check_box = QtWidgets.QCheckBox(tableWidget_prescript)
    check_box.setChecked(False)
    tableWidget_prescript.setCellWidget(row_no, PRESCRIPT_COL_NO['Promotion'], check_box)

    button = QtWidgets.QPushButton(tableWidget_prescript)
    button.setIcon(QtGui.QIcon('./icons/cancel.svg'))
    button.setFlat(True)
    button.clicked.connect(lambda: remove_prescript_row(tableWidget_prescript, extra_process))
    if cancel_button:
        remove_col = 9
    else:
        remove_col = PRESCRIPT_COL_NO['Remove']

    tableWidget_prescript.setCellWidget(row_no, remove_col, button)


def remove_prescript_row(tableWidget_prescript, extra_process):
    current_row = tableWidget_prescript.currentRow()
    tableWidget_prescript.removeRow(current_row)
    if extra_process is not None:
        for process in extra_process:
            process()


def prescript_item_changed(tableWidget_prescript, item):
    if item is None:
        return

    row_no = item.row()
    col_no = item.column()
    if col_no not in [
        PRESCRIPT_COL_NO['Quantity'],
        PRESCRIPT_COL_NO['Price'],
        PRESCRIPT_COL_NO['DiscountFee'],
        PRESCRIPT_COL_NO['Debt'],
        PRESCRIPT_COL_NO['Course'],
    ]:
        return

    sale_price = tableWidget_prescript.item(row_no, PRESCRIPT_COL_NO['Price'])
    if sale_price is None:
        return

    quantity = tableWidget_prescript.item(row_no, PRESCRIPT_COL_NO['Quantity'])
    if quantity is None:
        return

    sale_price = sale_price.text()
    quantity = quantity.text()
    subtotal = number_utils.get_float(quantity) * number_utils.get_float(sale_price)

    tableWidget_prescript.setItem(
        row_no, PRESCRIPT_COL_NO['Amount'],
        QtWidgets.QTableWidgetItem(string_utils.xstr(subtotal))
    )
    tableWidget_prescript.item(
        row_no, PRESCRIPT_COL_NO['Amount']).setTextAlignment(
        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
    )
    tableWidget_prescript.item(row_no, PRESCRIPT_COL_NO['Amount']).setFlags(
        QtCore.Qt.ItemIsEnabled
    )


def is_returned_goods(database, tableWidget_prescript, row_no):
    medicine_key = tableWidget_prescript.item(row_no, PURCHASE_COL_NO['medicine_key']).text()
    if medicine_key == '':
        return False

    is_returned = False
    case_key = tableWidget_prescript.item(row_no, PURCHASE_COL_NO['case_key']).text()

    sql = f'''
        SELECT * FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineKey = {medicine_key} AND
            MedicineName LIKE "%(退貨)%"
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        is_returned = True

    return is_returned
