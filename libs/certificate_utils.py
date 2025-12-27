# -*- coding: UTF-8 -*-
import datetime

from libs import registration_utils
from libs import number_utils
from libs import string_utils


def insert_certificate(database, **kwargs):
    fields = [
        'CaseKey', 'PatientKey', 'Name', 'CertificateDate', 'CertificateType',
        'InsType', 'Doctor', 'StartDate', 'EndDate', 'CertificateFee',
    ]
    data = [
        0,
        kwargs['patient_key'],
        kwargs['name'],
        datetime.datetime.now().strftime('%Y-%m-%d'),
        kwargs['certificate_type'],
        kwargs['ins_type'],
        kwargs['doctor'],
        kwargs['start_date'],
        kwargs['end_date'],
        kwargs['certificate_fee'],
    ]
    certificate_key = database.insert_record('certificate', fields, data)

    return certificate_key


# 寫入收費證明明細病歷
def insert_certificate_items(database, certificate_key, case_key):
    sql = f'''
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    '''
    row = database.select_record(sql)[0]

    ins_type = string_utils.xstr(row['InsType'])
    treat_type = string_utils.xstr(row['TreatType'])
    if treat_type in ['開立證明']:
        ins_type = treat_type

    fields = [
        'CertificateKey', 'CaseKey', 'CaseDate', 'InsType',
        'RegistFee', 'DiagFee', 'InterDrugFee', 'PharmacyFee',
        'AcupunctureFee', 'MassageFee',
        'SDiagShareFee', 'SDrugShareFee',
        'SDiagFee', 'SDrugFee', 'SHerbFee', 'SExpensiveFee', 'SAcupunctureFee',
        'SMassageFee', 'SDislocateFee', 'SMaterialFee', 'SExamFee',
        'InsApplyFee',
        'SelfTotalFee', 'DiscountFee', 'TotalFee', 'ReceiptFee',
    ]
    data = [
        certificate_key, row['CaseKey'], row['CaseDate'], ins_type,
        row['RegistFee'], row['DiagFee'], row['InterDrugFee'], row['PharmacyFee'],
        row['AcupunctureFee'], row['MassageFee'],
        row['SDiagShareFee'], row['SDrugShareFee'],
        row['SDiagFee'], row['SDrugFee'], row['SHerbFee'], row['SExpensiveFee'], row['SAcupunctureFee'],
        row['SMassageFee'], row['SDislocateFee'], row['SMaterialFee'], row['SExamFee'],
        row['InsApplyFee'],
        row['SelfTotalFee'], row['DiscountFee'], row['TotalFee'], row['ReceiptFee'],
    ]

    database.insert_record('certificate_items', fields, data)


def insert_medical_record(database, system_settings, patient_key, name, certificate_fee):
    charge_date = None
    charge_period = None
    charge_done = 'False'
    receipt_fee = None
    if system_settings.field('自動完成批價作業') == 'Y':
        charge_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        charge_period = registration_utils.get_current_period(system_settings)
        charge_done = 'True'
        receipt_fee = certificate_fee

    fields = [
        'PatientKey', 'Name', 'CaseDate', 'DoctorDate',
        'Period', 'InsType', 'TreatType', 'Register',
        'SMaterialFee', 'SelfTotalFee', 'TotalFee', 'ReceiptFee',
        'DoctorDone', 'ChargeDone', 'ChargeDate', 'ChargePeriod',
    ]
    data = [
        patient_key,
        name,
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        registration_utils.get_current_period(system_settings),
        '自費',
        '開立證明',
        system_settings.field('使用者'),
        certificate_fee,
        certificate_fee,
        certificate_fee,
        receipt_fee,
        'True',
        charge_done,
        charge_date,
        charge_period,
    ]

    case_key = database.insert_record('cases', fields, data)

    return case_key


def insert_prescript(database, case_key, unit_price, quantity):
    certificate_fee = unit_price * quantity

    fields = [
        'PrescriptNo', 'CaseKey', 'CaseDate',
        'MedicineSet', 'MedicineType', 'MedicineKey',
        'MedicineName', 'Dosage', 'Unit',
        'Price', 'Amount',
    ]

    data = [
        1,
        case_key,
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        2,
        '器材',
        0,
        '醫療費用證明書',
        quantity,
        '份',
        unit_price,
        certificate_fee,
    ]

    database.insert_record('prescript', fields, data)


def insert_wait(database, system_settings, case_key, patient_key, name):
    charge_done = 'False'
    if system_settings.field('自動完成批價作業') == 'Y':
        charge_done = 'True'

    fields = [
        'CaseKey', 'CaseDate', 'PatientKey', 'Name', 'Visit', 'RegistType',
        'TreatType', 'InsType', 'Period',
        'Room', 'RegistNo', 'DoctorDone', 'ChargeDone'
    ]
    data = [
        case_key,
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        patient_key,
        name,
        '複診',
        '一般門診',
        '自購',
        '自費',
        registration_utils.get_current_period(system_settings),
        1,
        0,
        'True',
        charge_done,
    ]
    database.insert_record('wait', fields, data)


# 檢查證明書是否重複開立
def check_certificate_duplicate(database, certificate_type, patient_key, start_date, end_date):
    duplicate = False

    sql = f'''
        SELECT CertificateKey FROM certificate
        WHERE
            CertificateType = "{certificate_type}" AND
            PatientKey = {patient_key} AND
            (StartDate BETWEEN "{start_date}" AND "{end_date}" OR
             EndDate BETWEEN "{start_date}" AND "{end_date}")
    '''
    rows = database.select_record(sql)

    if len(rows) > 0:
        duplicate = True

    return duplicate


def get_total_certificate_fees(database, certificate_key):
    sql = f'''
        SELECT certificate_items.*, cases.TreatType FROM certificate_items
            LEFT JOIN cases ON certificate_items.CaseKey = cases.CaseKey
        WHERE
            CertificateKey = {certificate_key}
        ORDER BY CaseDate
    '''
    rows = database.select_record(sql)

    fees_detail = {
        'total_cash_fee': 0,
        'total_regist_fee': 0,
        'total_diag_share_fee': 0,
        'total_drug_share_fee': 0,
        'total_diag_fee': 0,
        'total_drug_fee': 0,
        'total_pharmacy_fee': 0,
        'total_acupuncture_fee': 0,
        'total_massage_fee': 0,
        'total_dislocate_fee': 0,

        'total_self_acupuncture_fee': 0,
        'total_self_massage_fee': 0,
        'total_self_dislocate_fee': 0,

        'total_self_drug_fee': 0,
        'total_self_treat_fee': 0,
        'total_misc_fee': 0,
        'total_certificate_fee': 0,

        'total_total_fee': 0,
        'total_ins_apply_fee': 0,
    }

    for row in rows:
        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
        drug_share_fee = number_utils.get_integer(row['SDrugShareFee'])
        total_fee = number_utils.get_integer(row['TotalFee'])

        diag_fee = number_utils.get_integer(row['DiagFee'])
        drug_fee = number_utils.get_integer(row['InterDrugFee'])
        pharmacy_fee = number_utils.get_integer(row['PharmacyFee'])
        acupuncture_fee = number_utils.get_integer(row['AcupunctureFee'])
        massage_fee = number_utils.get_integer(row['MassageFee'])
        dislocate_fee = number_utils.get_integer(row['DislocateFee'])

        self_diag_fee = number_utils.get_integer(row['SDiagFee'])
        self_acupuncture_fee = number_utils.get_integer(row['SAcupunctureFee'])
        self_massage_fee = number_utils.get_integer(row['SMassageFee'])
        self_dislocate_fee = number_utils.get_integer(row['SDislocateFee'])
        self_treat_fee = self_diag_fee + self_acupuncture_fee + self_massage_fee + self_dislocate_fee

        self_misc_fee = number_utils.get_integer(row['SMaterialFee']) + number_utils.get_integer(row['SExamFee'])
        self_drug_fee = total_fee - self_treat_fee - self_misc_fee
        ins_apply_fee = number_utils.get_integer(row['InsApplyFee'])

        certificate_fee = 0
        if string_utils.xstr(row['TreatType']) == '開立證明':
            certificate_fee = self_misc_fee
            self_misc_fee = 0

        fees_detail['total_regist_fee'] += regist_fee
        fees_detail['total_diag_share_fee'] += diag_share_fee
        fees_detail['total_drug_share_fee'] += drug_share_fee
        fees_detail['total_diag_fee'] += diag_fee
        fees_detail['total_drug_fee'] += drug_fee
        fees_detail['total_pharmacy_fee'] += pharmacy_fee
        fees_detail['total_acupuncture_fee'] += acupuncture_fee
        fees_detail['total_massage_fee'] += massage_fee
        fees_detail['total_dislocate_fee'] += dislocate_fee

        fees_detail['total_self_acupuncture_fee'] += self_acupuncture_fee
        fees_detail['total_self_massage_fee'] += self_massage_fee
        fees_detail['total_self_dislocate_fee'] += self_dislocate_fee

        fees_detail['total_self_drug_fee'] += self_drug_fee
        fees_detail['total_self_treat_fee'] += self_treat_fee
        fees_detail['total_misc_fee'] += self_misc_fee
        fees_detail['total_certificate_fee'] += certificate_fee

        fees_detail['total_total_fee'] += total_fee
        fees_detail['total_cash_fee'] += regist_fee + diag_share_fee + drug_share_fee + total_fee
        fees_detail['total_ins_apply_fee'] += ins_apply_fee

    return fees_detail
