# -*- coding: UTF-8 -*-

from PyQt5.QtWidgets import QMessageBox, QFileDialog
from lxml import etree as ET

from libs import string_utils
from libs import number_utils
from libs import date_utils
from libs import case_utils
from libs import personnel_utils
from libs import nhi_utils
from libs import system_utils
from libs import cshis_utils
from libs import prescript_utils


class ICUploadXML1:
    def __init__(self, parent, database, system_settings, tableWidget_medical_record, upload_type):
        self.parent = parent
        self.database = database
        self.system_settings = system_settings
        self.tableWidget_medical_record = tableWidget_medical_record
        self.upload_type = upload_type

        file_path = nhi_utils.get_dir(self.system_settings, '申報路徑')
        upload_date = date_utils.date_to_str()
        self._xml_filename = f'{file_path}/IC-{self.upload_type}-{upload_date}.xml'
        self._file_created = True

    def __del__(self):
        pass

    def is_file_created(self):
        return self._file_created

    def xml_file_name(self):
        return self._xml_filename

    def create_xml_file(self, assign_path=False, filename=None):
        if filename:
            self._xml_filename = filename

        if assign_path:
            options = QFileDialog.Options()
            selected_filename, _ = QFileDialog.getSaveFileName(
                self.parent,
                "ic卡就醫資料上傳檔",
                self._xml_filename,
                "xml檔案 (*.xml);;XML Files (*.xml)", options=options
            )
            if selected_filename:
                self._xml_filename = selected_filename
            else:
                return None

        root = ET.Element('RECS')
        for row_no in range(self.tableWidget_medical_record.rowCount()):
            self.tableWidget_medical_record.setCurrentCell(row_no, 0)
            check_box = self.tableWidget_medical_record.cellWidget(row_no, 1)
            if check_box is None or not check_box.isChecked():
                continue

            case_key = self.tableWidget_medical_record.item(row_no, 0).text()
            medical_record = self.database.select_record(f'''
                SELECT * FROM cases
                WHERE
                    CaseKey = {case_key}
            ''')[0]
            upload_type = self.get_upload_type(medical_record)
            if not self.add_rec(root, medical_record, upload_type):
                self._file_created = False
                return

            if not self._file_created:
                self._file_created = True

        tree = ET.ElementTree(root)
        tree.write(
            self._xml_filename, pretty_print=True,
            xml_declaration=False,
            doctype='<?xml version="1.0" encoding="Big5"?>',
            encoding="Big5"
        )

    def get_upload_type(self, medical_record):
        upload_type = case_utils.extract_security_xml(medical_record['Security'], '資料格式')
        if upload_type == '':
            upload_type = '1'

        if upload_type == '1' and medical_record['Card'] in nhi_utils.INFECTIOUS_CARD:
            upload_type = '2'

        if self.upload_type == '2':  # 補正上傳
            upload_type = string_utils.xstr(int(upload_type) + 2)  # 轉換成補正上傳 1->3, 2->4

        return upload_type

    # 每一筆資料上傳內容
    def add_rec(self, root, medical_record, upload_type):
        rec = ET.SubElement(root, 'REC')

        self.add_msh(rec, upload_type)  # 表頭
        if not self.add_mb(rec, medical_record, upload_type):   # 資料本體
            return False

        return True

    # 表頭內容
    def add_msh(self, rec, upload_type):
        msh = ET.SubElement(rec, 'MSH')

        a00 = ET.SubElement(msh, 'A00')
        a00.text = '1'
        a01 = ET.SubElement(msh, 'A01')
        a01.text = string_utils.xstr(upload_type)
        a02 = ET.SubElement(msh, 'A02')
        a02.text = '1.0'

    # 每一筆資料本體
    def add_mb(self, rec, medical_record, upload_type):
        mb = ET.SubElement(rec, 'MB')

        if not self.add_mb1(mb, medical_record, upload_type):
            return False

        if not self.add_mb2(mb, medical_record, upload_type):
            return False

        return True

    # 健保資料段
    def add_mb1(self, mb, medical_record, upload_type):
        mb1 = ET.SubElement(mb, 'MB1')

        patient_key = string_utils.xstr(medical_record['PatientKey'])
        sql = f'SELECT * FROM patient WHERE PatientKey = {patient_key}'
        patient_record = self.database.select_record(sql)[0]

        if upload_type in ['1', '3']:
            clinic_id = case_utils.extract_security_xml(medical_record['Security'], '院所代號')
            card = case_utils.extract_security_xml(medical_record['Security'], '健保卡序')
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                case_utils.extract_security_xml(medical_record['Security'], '寫卡時間')
            )
        else:
            clinic_id = self.system_settings.field('院所代號')
            card = string_utils.xstr(medical_record['Card'])
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                medical_record['CaseDate']
            )

        if clinic_id in ['', None]:
            clinic_id = self.system_settings.field('院所代號')

        if card in ['', None]:
            card = string_utils.xstr(medical_record['Card'])

        if registered_date in ['', None]:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                medical_record['CaseDate']
            )

        xcard = string_utils.xstr(medical_record['XCard'])
        if xcard != '':
            card = xcard

        card = string_utils.xstr(card)[:4]

        treat_after_check = case_utils.extract_security_xml(medical_record['Security'], '補卡註記')
        treat_item = cshis_utils.get_treat_item(medical_record['Continuance'], medical_record['Share'])
        if upload_type in ['1', '3'] and treat_item in ['AA', 'AD']:  # 正常上傳療程及職傷不要放就醫序號
            card = ''

        if treat_after_check in ['', None]:
            treat_after_check = 1

        disease_code1 = string_utils.xstr(medical_record['DiseaseCode1'])
        disease_code2 = string_utils.xstr(medical_record['DiseaseCode2'])
        disease_code3 = string_utils.xstr(medical_record['DiseaseCode3'])
        disease_code4 = string_utils.xstr(medical_record['DiseaseCode4'])
        ins_total_fee = number_utils.get_integer(medical_record['InsTotalFee'])
        share_fee = (
                number_utils.get_integer(medical_record['DiagShareFee']) +
                number_utils.get_integer(medical_record['DrugShareFee'])
        )

        if upload_type in ['1', '3']:
            a11 = ET.SubElement(mb1, 'A11')
            a11.text = string_utils.xstr(patient_record['CardNo'])

        a12 = ET.SubElement(mb1, 'A12')
        a12.text = string_utils.xstr(string_utils.xstr(patient_record['ID']))
        a13 = ET.SubElement(mb1, 'A13')
        a13.text = string_utils.xstr(date_utils.west_date_to_nhi_date(patient_record['Birthday']))
        a14 = ET.SubElement(mb1, 'A14')
        a14.text = string_utils.xstr(clinic_id)
        a15 = ET.SubElement(mb1, 'A15')
        a15.text = string_utils.xstr(personnel_utils.get_person_field_value(
            self.database, string_utils.xstr(medical_record['Doctor']), 'ID')
        )

        if upload_type in ['1', '3']:
            sam_id = case_utils.extract_security_xml(medical_record['Security'], '安全模組')
            a16 = ET.SubElement(mb1, 'A16')
            a16.text = string_utils.xstr(sam_id)

        a17 = ET.SubElement(mb1, 'A17')
        a17.text = string_utils.xstr(registered_date)
        if card != '':
            a18 = ET.SubElement(mb1, 'A18')
            a18.text = string_utils.xstr(card)

        '''
        1. 當A01為(1、3正常卡序)且A23就醫類別為(01-08內科或首次)時，A18必須為數字欄位且不可空白，若大於1500退件。
        2. 當A01為(1、3)且A23非(01-08、AC療程)時，A18需為空值
        3. 當A01為(2、4)，A18必須符合左列的內容
        4. 當A23值非01 - 08，則A18可接受空值
        5. 當A23為AC且A01 = (1、3)，A18必須足4碼且為IC開頭ICxx
        6. 當A01為(1、3) 但A23不等於(01~08, AC)， 則A18可以等於"IC08"
        '''

        a19 = ET.SubElement(mb1, 'A19')
        a19.text = string_utils.xstr(treat_after_check)

        if upload_type in ['1', '3']:
            security_signature = case_utils.extract_security_xml(medical_record['Security'], '安全簽章')
            a22 = ET.SubElement(mb1, 'A22')
            a22.text = string_utils.xstr(security_signature)

        a23 = ET.SubElement(mb1, 'A23')
        a23.text = string_utils.xstr(treat_item)
        a25 = ET.SubElement(mb1, 'A25')
        a25.text = string_utils.xstr(disease_code1)

        if disease_code2 != '':
            a26 = ET.SubElement(mb1, 'A26')
            a26.text = string_utils.xstr(disease_code2)

        if disease_code3 != '':
            a27 = ET.SubElement(mb1, 'A27')
            a27.text = string_utils.xstr(disease_code3)

        if disease_code4 != '':
            a27 = ET.SubElement(mb1, 'A28')
            a27.text = string_utils.xstr(disease_code4)

        a31 = ET.SubElement(mb1, 'A31')
        a31.text = string_utils.xstr(ins_total_fee)
        a32 = ET.SubElement(mb1, 'A32')
        a32.text = string_utils.xstr(share_fee)

        if treat_after_check == '2':
            a54 = ET.SubElement(mb1, 'A54')

            try:
                a54.text = date_utils.west_datetime_to_nhi_datetime(medical_record['CaseDate'])[:7]
            except Exception:
                pass

        injury_code = nhi_utils.INJURY_DICT[string_utils.xstr(medical_record['Injury'])]
        a55 = ET.SubElement(mb1, 'A55')
        a55.text = string_utils.xstr(injury_code)

        return True

    # 醫療專區
    def add_mb2(self, mb, medical_record, upload_type):
        tour_area = medical_record['TourArea']
        if tour_area is not None:
            correction_area_code = nhi_utils.get_correction_area_code(self.system_settings, tour_area)  # 矯正機關代號
            if correction_area_code is not None:
                self._add_correction_area_order(mb, medical_record, upload_type, correction_area_code)

        if not self.add_treat(mb, medical_record, upload_type):
            return False

        if not self.add_medicine(mb, medical_record, upload_type):
            return False

        return True

    def add_treat(self, mb, medical_record, upload_type):
        treatment = string_utils.xstr(medical_record['Treatment'])
        if treatment == '':
            return True

        case_key = medical_record['CaseKey']
        prescript_type = '3'  # 3-診療
        days = 0
        dosage = 1
        pharmacy_type = '03'  # 物理治療

        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['1', '3']:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                case_utils.extract_security_xml(medical_record['Security'], '寫卡時間')
            )
        else:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                medical_record['CaseDate']
            )

        a71 = ET.SubElement(mb2, 'A71')
        a71.text = string_utils.xstr(registered_date)
        a72 = ET.SubElement(mb2, 'A72')
        a72.text = string_utils.xstr(prescript_type)
        a73 = ET.SubElement(mb2, 'A73')
        a73.text = string_utils.xstr(nhi_utils.TREAT_DICT[treatment])
        a76 = ET.SubElement(mb2, 'A76')
        a76.text = f'{days:0>2}'
        a77 = ET.SubElement(mb2, 'A77')
        a77.text = f'{dosage:07.1f}'
        a78 = ET.SubElement(mb2, 'A78')
        a78.text = string_utils.xstr(pharmacy_type)

        if upload_type in ['1', '3']:
            sql = f'''
            SELECT Content AS PrescriptSign FROM presextend
            WHERE
                PrescriptKey = {case_key} AND
                ExtendType = "處置簽章"
            '''
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                prescript_sign = string_utils.xstr(rows[0]['PrescriptSign'])
                a79 = ET.SubElement(mb2, 'A79')
                a79.text = string_utils.xstr(prescript_sign)

        return True

    def add_medicine(self, mb, medical_record, upload_type):
        case_key = string_utils.xstr(medical_record['CaseKey'])

        if upload_type in ['1', '3']:  # 正常卡序
            sql = f'''
                SELECT
                    prescript.MedicineName, prescript.InsCode, prescript.Dosage,
                    presextend.ExtendType, presextend.Content AS PrescriptSign
                FROM prescript
                    LEFT JOIN presextend ON presextend.PrescriptKey = prescript.PrescriptKey
                WHERE
                    prescript.CaseKey = {case_key} AND
                    prescript.MedicineSet = 1 AND
                    prescript.MedicineName NOT LIKE "%清冠一號%" AND
                    prescript.InsCode IS NOT NULL AND
                    presextend.ExtendType = "處方簽章" AND
                    presextend.Content IS NOT NULL
                ORDER BY prescript.PrescriptNo, prescript.PrescriptKey
            '''
        else:  # 異常卡序
            sql = f'''
                SELECT  *
                FROM prescript
                WHERE
                    CaseKey = {case_key} AND
                    MedicineSet = 1 AND
                    MedicineName NOT LIKE "%清冠一號%" AND
                    InsCode IS NOT NULL
                ORDER BY PrescriptNo, PrescriptKey
            '''
        rows = self.database.select_record(sql)

        sql = f'''
            SELECT * FROM dosage
            WHERE
                CaseKey = {case_key}
        '''
        dosage_row = self.database.select_record(sql)

        if 'G000' in string_utils.xstr(medical_record) and len(rows) > 0:  # 新特約院所開藥增加虛擬碼 R005, 避免雲端用藥重複被核扣
            self._add_virtual_order(mb, medical_record, upload_type)

        ic_card_type = case_utils.get_ic_card_type(self.database, case_key)
        if number_utils.get_integer(medical_record['Continuance']) >= 2 and ic_card_type == '虛擬健保卡':
            self._add_vhc_ic_card(mb, medical_record, upload_type)

        infectious_drug = prescript_utils.get_infectious_drug(self.database, case_key)
        if infectious_drug in ['台灣清冠一號', '台灣清冠一號及科學中藥']:
            self._add_covid19(mb, medical_record, upload_type)
            self._add_infectious_drug(mb, medical_record, upload_type)
            self._add_infectious_virtual_code(mb, medical_record, upload_type)

        for prescript_row in rows:
            if not self.add_medicine_rows(
                    mb, medical_record, prescript_row, dosage_row, case_key, upload_type):
                return False

        return True

    def _add_correction_area_order(self, mb, medical_record, upload_type, correction_area_code):
        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['1', '3']:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                case_utils.extract_security_xml(medical_record['Security'], '寫卡時間')
            )
        else:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                medical_record['CaseDate']
            )

        prescript_type = 'J'  # G-虛擬醫令
        ins_code = correction_area_code  # 矯正機關代號
        dosage = 1

        a71 = ET.SubElement(mb2, 'A71')
        a71.text = string_utils.xstr(registered_date)
        a72 = ET.SubElement(mb2, 'A72')
        a72.text = string_utils.xstr(prescript_type)
        a73 = ET.SubElement(mb2, 'A73')
        a73.text = ins_code
        a77 = ET.SubElement(mb2, 'A77')
        a77.text = f'{dosage:07.1f}'

        return True

    def _add_virtual_order(self, mb, medical_record, upload_type):
        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['1', '3']:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                case_utils.extract_security_xml(medical_record['Security'], '寫卡時間')
            )
        else:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                medical_record['CaseDate']
            )

        prescript_type = 'G'  # G-虛擬醫令
        ins_code = 'R005'  # 新特約院所
        dosage = 0

        a71 = ET.SubElement(mb2, 'A71')
        a71.text = string_utils.xstr(registered_date)
        a72 = ET.SubElement(mb2, 'A72')
        a72.text = string_utils.xstr(prescript_type)
        a73 = ET.SubElement(mb2, 'A73')
        a73.text = ins_code
        a77 = ET.SubElement(mb2, 'A77')
        a77.text = f'{dosage:07.1f}'

        return True

    # 虛擬健保卡
    def _add_vhc_ic_card(self, mb, medical_record, upload_type):
        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['1', '3']:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                case_utils.extract_security_xml(medical_record['Security'], '寫卡時間')
            )
        else:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                medical_record['CaseDate']
            )

        prescript_type = 'G'  # G-虛擬醫令
        ins_code = 'V000'

        dosage = 0

        a71 = ET.SubElement(mb2, 'A71')
        a71.text = string_utils.xstr(registered_date)
        a72 = ET.SubElement(mb2, 'A72')
        a72.text = string_utils.xstr(prescript_type)
        a73 = ET.SubElement(mb2, 'A73')
        a73.text = ins_code
        a77 = ET.SubElement(mb2, 'A77')
        a77.text = f'{dosage:07.1f}'

        return True

    def _add_covid19(self, mb, medical_record, upload_type):
        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['1', '3']:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                case_utils.extract_security_xml(medical_record['Security'], '寫卡時間')
            )
        else:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                medical_record['CaseDate']
            )

        prescript_type = 'G'  # G-虛擬醫令
        if string_utils.xstr(medical_record['RegistType']) in ['視訊門診'] + nhi_utils.INFECTIOUS_INJURY_TYPE:
            ins_code = 'ViT-COVID19'
        elif string_utils.xstr(medical_record['Injury']) in nhi_utils.INFECTIOUS_INJURY_TYPE:
            ins_code = 'ViT-COVID19'
        elif string_utils.xstr(medical_record['Share']) in nhi_utils.INFECTIOUS_INJURY_TYPE:
            ins_code = 'ViT-COVID19'
        elif string_utils.xstr(medical_record['RegistType']) in ['電話門診']:
            ins_code = 'PhT-COVID19'  # 新特約院所
        else:
            return False

        dosage = 0

        a71 = ET.SubElement(mb2, 'A71')
        a71.text = string_utils.xstr(registered_date)
        a72 = ET.SubElement(mb2, 'A72')
        a72.text = string_utils.xstr(prescript_type)
        a73 = ET.SubElement(mb2, 'A73')
        a73.text = ins_code
        a77 = ET.SubElement(mb2, 'A77')
        a77.text = f'{dosage:07.1f}'

        return True

    def _add_infectious_drug(self, mb, medical_record, upload_type):
        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['1', '3']:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                case_utils.extract_security_xml(medical_record['Security'], '寫卡時間')
            )
        else:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                medical_record['CaseDate']
            )

        case_key = string_utils.xstr(medical_record['CaseKey'])
        prescript_type = '3'  # 診療
        ins_code = 'E5012C'
        days = 0
        dosage = case_utils.get_pres_days(self.database, case_key)

        a71 = ET.SubElement(mb2, 'A71')
        a71.text = string_utils.xstr(registered_date)
        a72 = ET.SubElement(mb2, 'A72')
        a72.text = string_utils.xstr(prescript_type)
        a73 = ET.SubElement(mb2, 'A73')
        a73.text = ins_code
        a76 = ET.SubElement(mb2, 'A76')
        a76.text = string_utils.xstr(days)
        a77 = ET.SubElement(mb2, 'A77')
        a77.text = f'{dosage:07.1f}'

        if upload_type in ['1', '3']:
            sql = f'''
            SELECT PrescriptKey FROM prescript
            WHERE
                CaseKey = {case_key} AND
                InsCode = "E5012C"
            '''
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                prescript_key = rows[0]['PrescriptKey']
                sql = f'''
                SELECT Content AS PrescriptSign FROM presextend
                WHERE
                    PrescriptKey = {prescript_key}
                '''
                rows = self.database.select_record(sql)
                if len(rows) > 0:
                    prescript_sign = string_utils.xstr(rows[0]['PrescriptSign'])
                    a79 = ET.SubElement(mb2, 'A79')
                    a79.text = string_utils.xstr(prescript_sign)

        return True

    def _add_infectious_virtual_code(self, mb, medical_record, upload_type):
        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['1', '3']:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                case_utils.extract_security_xml(medical_record['Security'], '寫卡時間')
            )
        else:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                medical_record['CaseDate']
            )

        prescript_type = 'G'  # G-虛擬醫令
        ins_code = 'NND000'
        dosage = 0

        a71 = ET.SubElement(mb2, 'A71')
        a71.text = string_utils.xstr(registered_date)
        a72 = ET.SubElement(mb2, 'A72')
        a72.text = string_utils.xstr(prescript_type)
        a73 = ET.SubElement(mb2, 'A73')
        a73.text = ins_code
        a77 = ET.SubElement(mb2, 'A77')
        a77.text = f'{dosage:07.1f}'

        return True

    def add_medicine_rows(self, mb, medical_record, prescript_row, dosage_row, case_key, upload_type):
        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['1', '3']:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                case_utils.extract_security_xml(medical_record['Security'], '寫卡時間')
            )
        else:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                medical_record['CaseDate']
            )
        prescript_type = '1'  # 1-長期藥品
        if len(dosage_row) > 0:
            try:
                frequency = nhi_utils.FREQUENCY[dosage_row[0]['Packages']]
            except KeyError:
                frequency = ''

            days = number_utils.get_integer(dosage_row[0]['Days'])
            try:
                dosage = prescript_row['Dosage'] * days
            except Exception:
                name = string_utils.xstr(medical_record['Name'])
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    '資料錯誤',
                    f'<font size="5" color="red"><b>{name}的處方內容有誤, 請確認處方名稱或劑量是否空白.</b></font>',
                    '請進入病歷內查看並更正此錯誤後再上傳.'
                )
                return False
        else:
            frequency = ''
            days = 0
            dosage = 0

        pharmacy_type = '01'  # 自行調劑

        a71 = ET.SubElement(mb2, 'A71')
        a71.text = string_utils.xstr(registered_date)
        a72 = ET.SubElement(mb2, 'A72')
        a72.text = string_utils.xstr(prescript_type)
        a73 = ET.SubElement(mb2, 'A73')
        a73.text = string_utils.xstr(prescript_row['InsCode'])
        a75 = ET.SubElement(mb2, 'A75')
        a75.text = string_utils.xstr(frequency)
        a76 = ET.SubElement(mb2, 'A76')
        a76.text = f'{days:0>2}'
        a77 = ET.SubElement(mb2, 'A77')
        a77.text = f'{dosage:07.1f}'
        a78 = ET.SubElement(mb2, 'A78')
        a78.text = string_utils.xstr(pharmacy_type)

        if upload_type in ['1', '3']:
            prescript_sign = string_utils.xstr(prescript_row['PrescriptSign'])
            if prescript_sign != '':
                a79 = ET.SubElement(mb2, 'A79')
                a79.text = string_utils.xstr(prescript_sign)

        return True
