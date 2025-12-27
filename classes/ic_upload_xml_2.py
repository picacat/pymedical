# -*- coding: utf-8 -*-

import json

from libs import (case_utils, cshis_utils, date_utils, nhi_utils, number_utils,
                  personnel_utils, prescript_utils, string_utils, system_utils)
from lxml import etree as ET
from PyQt5.QtWidgets import QFileDialog, QMessageBox


# 上傳格式2.0 2023-09-07 第二版 2024-11-01 更新2023-ICD-10
class ICUploadXML2:
    def __init__(self, parent, database, system_settings, tableWidget_medical_record, upload_type):
        self.parent = parent
        self.database = database
        self.system_settings = system_settings
        self.tableWidget_medical_record = tableWidget_medical_record
        self.upload_type = upload_type
        self.case_count = 0
        self.prescript_count = 0

        file_path = nhi_utils.get_dir(self.system_settings, '申報路徑')
        upload_date = date_utils.date_to_str()
        self._xml_file_name = f'{file_path}/IC-{self.upload_type}-{upload_date}.xml'
        self._file_created = True
        try:
            with open('2023_ICD_MAP.json', 'r', encoding='utf-8') as f:
                self.dict_icd_map = json.load(f)
        except Exception:
            self.dict_icd_map = None

    def __del__(self):
        pass

    def is_file_created(self):
        return self._file_created

    def xml_file_name(self):
        return self._xml_file_name

    def create_xml_file(self, assign_path=False):
        if assign_path:
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(
                self.parent,
                "ic卡就醫資料上傳檔",
                self._xml_file_name,
                "xml檔案 (*.xml);;XML Files (*.xml)", options=options
            )
            if file_name:
                self._xml_file_name = file_name

        tree = self._get_xml_tree()

        tree.write(
            self._xml_file_name, pretty_print=True,
            xml_declaration=False,
            doctype='<?xml version="1.0" encoding="Big5"?>',
            encoding="Big5"
        )

    def get_xml(self, encoding='utf-8'):
        tree = self._get_xml_tree()
        xml = ET.tostring(
            tree,
            xml_declaration=False,
            doctype=f'<?xml version="1.0" encoding="{encoding}"?>',
            encoding=encoding,
        )

        return xml.decode(encoding)

    def get_case_count(self):
        return self.case_count

    def get_prescript_count(self):
        return self.prescript_count

    def _get_xml_tree(self):
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

            self.case_count += 1

        tree = ET.ElementTree(root)

        return tree

    def get_upload_type(self, medical_record):
        upload_type = case_utils.extract_security_xml(medical_record['Security'], '資料格式')

        if upload_type in ['', '1', '3']:  # 舊版轉換
            upload_type = 'A'
        elif upload_type in ['2', '4']:
            upload_type = 'B'

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

        h00 = ET.SubElement(msh, 'H00')
        h00.text = '1'
        h01 = ET.SubElement(msh, 'H01')
        h01.text = string_utils.xstr(upload_type)

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
        case_key = medical_record['CaseKey']
        pres_days = case_utils.get_pres_days(self.database, case_key)

        sql = f'SELECT * FROM patient WHERE PatientKey = {patient_key}'
        patient_record = self.database.select_record(sql)[0]

        if upload_type in ['A']:
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

        xcard = string_utils.xstr(medical_record['XCard'])
        if xcard != '':
            card = xcard

        card = string_utils.xstr(card)[:4]

        treat_after_check = case_utils.extract_security_xml(medical_record['Security'], '補卡註記')
        if treat_after_check in ['', None]:
            treat_after_check = '1'

        treat_item = cshis_utils.get_treat_item(medical_record['Continuance'], medical_record['Share'])
        if card in ['', None] and treat_item == '03' and medical_record['TreatType'] in nhi_utils.HOME_CARE:
            treat_item = 'AH'
            
        if upload_type in ['A'] and treat_item in ['AA', 'AD']:  # 正常上傳療程及職傷不要放就醫序號
            card = ''

            
        disease_code1 = string_utils.xstr(medical_record['DiseaseCode1'])
        disease_code2 = string_utils.xstr(medical_record['DiseaseCode2'])
        disease_code3 = string_utils.xstr(medical_record['DiseaseCode3'])
        disease_code4 = string_utils.xstr(medical_record['DiseaseCode4'])

        if medical_record['CaseDate'].strftime('%Y-%m-%d') <= '2024-12-31' and self.dict_icd_map is not None:
            if disease_code1 != '':
                try:
                    disease_code1 = self.dict_icd_map[disease_code1]  # 申報月份2025年以前只能申報2014年版本ICD-10
                except Exception:
                    pass
            if disease_code2 != '':
                try:
                    disease_code2 = self.dict_icd_map[disease_code2]  # 申報月份2025年以前只能申報2014年版本ICD-10
                except Exception:
                    pass
            if disease_code3 != '':
                try:
                    disease_code3 = self.dict_icd_map[disease_code3]  # 申報月份2025年以前只能申報2014年版本ICD-10
                except Exception:
                    pass
            if disease_code4 != '':
                try:
                    disease_code4 = self.dict_icd_map[disease_code4]  # 申報月份2025年以前只能申報2014年版本ICD-10
                except Exception:
                    pass

        ins_total_fee = number_utils.get_integer(medical_record['InsTotalFee'])
        share_fee = (
                number_utils.get_integer(medical_record['DiagShareFee']) +
                number_utils.get_integer(medical_record['DrugShareFee'])
        )

        if upload_type in ['A']:
            sam_id = case_utils.extract_security_xml(medical_record['Security'], '安全模組')
            m01 = ET.SubElement(mb1, 'M01')
            m01.text = string_utils.xstr(sam_id)

            m02 = ET.SubElement(mb1, 'M02')
            m02.text = string_utils.xstr(patient_record['CardNo'])

        m03 = ET.SubElement(mb1, 'M03')
        m03.text = string_utils.xstr(string_utils.xstr(patient_record['ID']))
        m04 = ET.SubElement(mb1, 'M04')
        m04.text = string_utils.xstr(date_utils.west_date_to_nhi_date(patient_record['Birthday']))
        m05 = ET.SubElement(mb1, 'M05')
        m05.text = string_utils.xstr(clinic_id)
        m06 = ET.SubElement(mb1, 'M06')
        m06.text = string_utils.xstr(personnel_utils.get_person_field_value(
            self.database, string_utils.xstr(medical_record['Doctor']), 'ID')
        )
        m07 = ET.SubElement(mb1, 'M07')
        m07.text = string_utils.xstr(treat_item)

        m11 = ET.SubElement(mb1, 'M11')
        m11.text = string_utils.xstr(registered_date)
        m12 = ET.SubElement(mb1, 'M12')
        m12.text = string_utils.xstr(treat_after_check)  # 補卡註記 1: 正常 2: 補卡
        if card != '':
            m13 = ET.SubElement(mb1, 'M13')
            m13.text = string_utils.xstr(card)

        '''
        1. 當A01為(1、3正常卡序)且A23就醫類別為(01-08內科或首次)時，A18必須為數字欄位且不可空白，若大於1500退件。
        2. 當A01為(1、3)且A23非(01-08、AC療程)時，A18需為空值
        3. 當A01為(2、4)，A18必須符合左列的內容
        4. 當A23值非01 - 08，則A18可接受空值
        5. 當A23為AC且A01 = (1、3)，A18必須足4碼且為IC開頭ICxx
        6. 當A01為(1、3) 但A23不等於(01~08, AC)， 則A18可以等於"IC08"
        '''

        security_signature = case_utils.extract_security_xml(medical_record['Security'], '安全簽章')
        if security_signature not in ['', None]:
            m14 = ET.SubElement(mb1, 'M14')
            m14.text = string_utils.xstr(security_signature)

        identification = case_utils.extract_security_xml(medical_record['Security'], '就醫識別碼')
        if identification not in ['', None]:
            m15 = ET.SubElement(mb1, 'M15')
            m15.text = string_utils.xstr(identification)

        if treat_item in ['AA', 'AH']:  # 連續療程
            original_card = string_utils.xstr(medical_record['Card'])

            original_security = case_utils.get_first_course_field(
                self.database,
                medical_record['CaseDate'],
                medical_record['PatientKey'],
                original_card,
                'Security',
                treat_item=treat_item,
            )
            if original_security is None:
                # original_identification = '99999999999999999999'  # 新舊交接期間使用
                original_identification = 'MISS0000000000000000'  # 新舊交接期間使用
                original_registered_date = registered_date
            else:
                original_identification = case_utils.extract_security_xml(original_security, '就醫識別碼')
                original_registered_date = date_utils.west_datetime_to_nhi_datetime(
                    case_utils.extract_security_xml(original_security, '寫卡時間')
                )

            m16 = ET.SubElement(mb1, 'M16')
            m16.text = string_utils.xstr(original_identification)
            m17 = ET.SubElement(mb1, 'M17')
            m17.text = string_utils.xstr(clinic_id)
            m18 = ET.SubElement(mb1, 'M18')
            m18.text = string_utils.xstr(original_card)
            m19 = ET.SubElement(mb1, 'M19')
            m19.text = string_utils.xstr(original_registered_date)

        m20 = ET.SubElement(mb1, 'M20')
        m20.text = string_utils.xstr(pres_days)

        pharmacy_type = '2'  # 未開處方
        available_pharmacy_time = ''
        if pres_days > 0:
            pharmacy_type = '0'  # 自行調劑
            # available_pharmacy_time = '1'  # 可調劑次數
            if upload_type in ['A']:
                medicine_order_count = nhi_utils.get_medicine_order_count(self.database, case_key)
                if medicine_order_count > 0:
                    available_pharmacy_time = '1'  # 可調劑次數

        m23 = ET.SubElement(mb1, 'M23')
        m23.text = string_utils.xstr(pharmacy_type)

        if available_pharmacy_time != '':
            m24 = ET.SubElement(mb1, 'M24')
            m24.text = string_utils.xstr(available_pharmacy_time)

        course = number_utils.get_integer(medical_record['Continuance'])
        if course >= 2:
            m30 = ET.SubElement(mb1, 'M30')
            m30.text = string_utils.xstr(course)

        m35 = ET.SubElement(mb1, 'M35')
        m35.text = string_utils.xstr(disease_code1)

        if disease_code2 != '':
            m36 = ET.SubElement(mb1, 'M36')
            m36.text = string_utils.xstr(disease_code2)

        if disease_code3 != '':
            m37 = ET.SubElement(mb1, 'M37')
            m37.text = string_utils.xstr(disease_code3)

        if disease_code4 != '':
            m38 = ET.SubElement(mb1, 'M38')
            m38.text = string_utils.xstr(disease_code4)

        m44 = ET.SubElement(mb1, 'M44')
        m44.text = string_utils.xstr(ins_total_fee)
        m45 = ET.SubElement(mb1, 'M45')
        m45.text = string_utils.xstr(share_fee)

        if treat_after_check == '2':
            m49 = ET.SubElement(mb1, 'M49')

            registered_date = case_utils.get_case_extend(self.database, case_key, '實際就醫日期')
            if registered_date in ['', None]:
                try:
                    registered_date = date_utils.west_datetime_to_nhi_datetime(medical_record['CaseDate'])
                except Exception:
                    pass

            m49.text = registered_date

        injury_code = nhi_utils.INJURY_DICT[string_utils.xstr(medical_record['Injury'])]
        m51 = ET.SubElement(mb1, 'M51')
        m51.text = string_utils.xstr(injury_code)

        if treat_after_check == '2':
            identification = case_utils.get_case_extend(self.database, case_key, '原就醫識別碼')
            if identification in [None, '']:
                identification = 'MISS0000000000000000'

            m52 = ET.SubElement(mb1, 'M52')
            m52.text = string_utils.xstr(identification)

        diag_share_fee = number_utils.get_integer(medical_record['DiagShareFee'])
        if diag_share_fee > 0:
            m53 = ET.SubElement(mb1, 'M53')
            m53.text = string_utils.xstr(diag_share_fee)

        drug_share_fee = number_utils.get_integer(medical_record['DrugShareFee'])
        if diag_share_fee > 0:
            m54 = ET.SubElement(mb1, 'M54')
            m54.text = string_utils.xstr(drug_share_fee)

        m56 = ET.SubElement(mb1, 'M56')
        m56.text = '14'  # 門診中醫

        return True

    # 醫療專區
    def add_mb2(self, mb, medical_record, upload_type):
        self.order_no = 0

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

    def _add_correction_area_order(self, mb, medical_record, upload_type, correction_area_code):
        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['A']:
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

        d01 = ET.SubElement(mb2, 'D01')
        d01.text = string_utils.xstr(registered_date)
        d02 = ET.SubElement(mb2, 'D02')
        d02.text = string_utils.xstr(prescript_type)

        self.order_no += 1
        d03 = ET.SubElement(mb2, 'D03')
        d03.text = f'{self.order_no:0>3}'  # 醫令序號: 001 ~ 999
        # d05 = ET.SubElement(mb2, 'D05')
        # d05.text = '0'  # 調劑方式: 0-自行調劑、檢驗或物理治療

        d06 = ET.SubElement(mb2, 'D06')
        d06.text = ins_code
        d10 = ET.SubElement(mb2, 'D10')
        d10.text = f'{dosage:07.1f}'

        return True

    def add_treat(self, mb, medical_record, upload_type):
        treatment = string_utils.xstr(medical_record['Treatment'])
        if treatment == '':
            return True

        case_key = medical_record['CaseKey']
        dosage = 1

        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['A']:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                case_utils.extract_security_xml(medical_record['Security'], '寫卡時間')
            )
        else:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                medical_record['CaseDate']
            )

        d01 = ET.SubElement(mb2, 'D01')
        d01.text = string_utils.xstr(registered_date)
        d02 = ET.SubElement(mb2, 'D02')
        d02.text = '2'  # 醫令類別: 2-支付標準(診療)

        self.order_no += 1
        d03 = ET.SubElement(mb2, 'D03')
        d03.text = f'{self.order_no:0>3}'  # 醫令序號: 001 ~ 999

        d05 = ET.SubElement(mb2, 'D05')
        d05.text = '0'  # 調劑方式: 0-自行調劑、檢驗或物理治療
        d06 = ET.SubElement(mb2, 'D06')
        d06.text = string_utils.xstr(nhi_utils.TREAT_DICT[treatment])
        d10 = ET.SubElement(mb2, 'D10')
        d10.text = f'{dosage:07.1f}'

        if upload_type in ['A']:
            sql = f'''
            SELECT Content AS PrescriptSign FROM presextend
            WHERE
                PrescriptKey = {case_key} AND
                ExtendType = "處置簽章"
            '''
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                prescript_sign = string_utils.xstr(rows[0]['PrescriptSign'])
                d11 = ET.SubElement(mb2, 'D11')
                d11.text = string_utils.xstr(prescript_sign)

        self.prescript_count += 1

        return True

    def add_medicine(self, mb, medical_record, upload_type):
        case_key = string_utils.xstr(medical_record['CaseKey'])

        if upload_type in ['A']:  # 正常卡序
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

        if (string_utils.xstr(medical_record['RegistType']) in nhi_utils.TELECOM_TYPE or
           string_utils.xstr(medical_record['RegistType']) in nhi_utils.INFECTIOUS_INJURY_TYPE or
           string_utils.xstr(medical_record['Share']) in nhi_utils.INFECTIOUS_INJURY_TYPE or
           string_utils.xstr(medical_record['Injury']) in nhi_utils.INFECTIOUS_INJURY_TYPE):
            self._add_covid19(mb, medical_record, upload_type)
            infectious_drug = prescript_utils.get_infectious_drug(self.database, case_key)
            if infectious_drug in ['台灣清冠一號', '台灣清冠一號及科學中藥']:
                self._add_infectious_drug(mb, medical_record, upload_type)
                self._add_infectious_virtual_code(mb, medical_record, upload_type)

        for prescript_row in rows:
            if not self.add_medicine_rows(
                    mb, medical_record, prescript_row, dosage_row, case_key, upload_type):
                return False

        return True

    def _add_virtual_order(self, mb, medical_record, upload_type):
        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['A']:
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

        d01 = ET.SubElement(mb2, 'D01')
        d01.text = string_utils.xstr(registered_date)
        d02 = ET.SubElement(mb2, 'D02')
        d02.text = string_utils.xstr(prescript_type)

        self.order_no += 1
        d03 = ET.SubElement(mb2, 'D03')
        d03.text = f'{self.order_no:0>3}'  # 醫令序號: 001 ~ 999

        d06 = ET.SubElement(mb2, 'D06')
        d06.text = ins_code
        d10 = ET.SubElement(mb2, 'D10')
        d10.text = string_utils.xstr(dosage)

        self.prescript_count += 1

        return True

    # 虛擬健保卡
    def _add_vhc_ic_card(self, mb, medical_record, upload_type):
        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['A']:
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

        d01 = ET.SubElement(mb2, 'D01')
        d01.text = string_utils.xstr(registered_date)
        d02 = ET.SubElement(mb2, 'D02')
        d02.text = string_utils.xstr(prescript_type)

        self.order_no += 1
        d03 = ET.SubElement(mb2, 'D03')
        d03.text = f'{self.order_no:0>3}'  # 醫令序號: 001 ~ 999

        d06 = ET.SubElement(mb2, 'D06')
        d06.text = ins_code
        d10 = ET.SubElement(mb2, 'D10')
        d10.text = string_utils.xstr(dosage)

        self.prescript_count += 1

        return True

    def _add_covid19(self, mb, medical_record, upload_type):
        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['A']:
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

        d01 = ET.SubElement(mb2, 'D01')
        d01.text = string_utils.xstr(registered_date)
        d02 = ET.SubElement(mb2, 'D02')
        d02.text = string_utils.xstr(prescript_type)

        self.order_no += 1
        d03 = ET.SubElement(mb2, 'D03')
        d03.text = f'{self.order_no:0>3}'  # 醫令序號: 001 ~ 999

        d06 = ET.SubElement(mb2, 'D06')
        d06.text = ins_code
        d10 = ET.SubElement(mb2, 'D10')
        d10.text = string_utils.xstr(dosage)

        self.prescript_count += 1

        return True

    def add_medicine_rows(self, mb, medical_record, prescript_row, dosage_row, case_key, upload_type):
        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['A']:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                case_utils.extract_security_xml(medical_record['Security'], '寫卡時間')
            )
        else:
            registered_date = date_utils.west_datetime_to_nhi_datetime(
                medical_record['CaseDate']
            )

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
                    f'''<font size="5" color="red"><b>
                            {name}的處方內容({prescript_row["MedicineName"]})有誤, 請確認處方名稱或劑量是否空白.
                       </b></font>
                    ''',
                    '請進入病歷內查看並更正此錯誤後再上傳.'
                )
                return False
        else:
            frequency = ''
            days = 0
            dosage = 0

        d01 = ET.SubElement(mb2, 'D01')
        d01.text = string_utils.xstr(registered_date)
        d02 = ET.SubElement(mb2, 'D02')
        d02.text = '1'  # 醫令類別: 1-藥品主檔

        self.order_no += 1
        d03 = ET.SubElement(mb2, 'D03')
        d03.text = f'{self.order_no:0>3}'  # 醫令序號: 001 ~ 999

        d04 = ET.SubElement(mb2, 'D04')
        d04.text = 'A'  # 處方種類: A-一般處方箋
        d05 = ET.SubElement(mb2, 'D05')
        d05.text = '0'  # 調劑方式: 0-自行調劑、檢驗或物理治療
        d06 = ET.SubElement(mb2, 'D06')
        d06.text = string_utils.xstr(prescript_row['InsCode'])
        d08 = ET.SubElement(mb2, 'D08')
        d08.text = string_utils.xstr(frequency)
        d09 = ET.SubElement(mb2, 'D09')
        d09.text = f'{days:0>2}'
        d10 = ET.SubElement(mb2, 'D10')
        d10.text = f'{dosage:07.1f}'

        if upload_type in ['A']:
            prescript_sign = string_utils.xstr(prescript_row['PrescriptSign'])
            if prescript_sign != '':
                d11 = ET.SubElement(mb2, 'D11')
                d11.text = string_utils.xstr(prescript_sign)

        d14 = ET.SubElement(mb2, 'D14')
        d14.text = 'PO'  # 給藥途徑: PO-口服

        self.prescript_count += 1

        return True

    def _add_infectious_drug(self, mb, medical_record, upload_type):
        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['A']:
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

        d01 = ET.SubElement(mb2, 'D01')
        d01.text = string_utils.xstr(registered_date)
        d02 = ET.SubElement(mb2, 'D02')
        d02.text = string_utils.xstr(prescript_type)

        self.order_no += 1
        d03 = ET.SubElement(mb2, 'D03')
        d03.text = f'{self.order_no:0>3}'  # 醫令序號: 001 ~ 999

        d04 = ET.SubElement(mb2, 'D04')
        d04.text = 'A'  # 處方種類: A-一般處方箋
        d05 = ET.SubElement(mb2, 'D05')
        d05.text = '0'  # 調劑方式: 0-自行調劑、檢驗或物理治療
        d06 = ET.SubElement(mb2, 'D06')
        d06.text = string_utils.xstr(ins_code)
        d09 = ET.SubElement(mb2, 'D09')
        d09.text = f'{days:0>2}'
        d10 = ET.SubElement(mb2, 'D10')
        d10.text = f'{dosage:07.1f}'

        if upload_type in ['A']:
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
                    d11 = ET.SubElement(mb2, 'D11')
                    d11.text = string_utils.xstr(prescript_sign)

        d14 = ET.SubElement(mb2, 'D14')
        d14.text = 'PO'  # 給藥途徑: PO-口服

        return True

    def _add_infectious_virtual_code(self, mb, medical_record, upload_type):
        mb2 = ET.SubElement(mb, 'MB2')

        if upload_type in ['A']:
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

        d01 = ET.SubElement(mb2, 'D01')
        d01.text = string_utils.xstr(registered_date)
        d02 = ET.SubElement(mb2, 'D02')
        d02.text = string_utils.xstr(prescript_type)

        self.order_no += 1
        d03 = ET.SubElement(mb2, 'D03')
        d03.text = f'{self.order_no:0>3}'  # 醫令序號: 001 ~ 999

        d06 = ET.SubElement(mb2, 'D06')
        d06.text = ins_code
        d10 = ET.SubElement(mb2, 'D10')
        d10.text = string_utils.xstr(dosage)

        self.prescript_count += 1

        return True
