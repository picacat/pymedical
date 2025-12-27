
from PyQt5.QtWidgets import QMessageBox, QPushButton

try:
    import pyodbc
except Exception:
    pass

from libs import string_utils
from libs import patient_utils
from libs import number_utils
from libs import date_utils
from libs import nhi_utils


# 巨騰轉檔 2023.04.01
class CvtGP():
    def __init__(self, parent, *args):
        self.parent = parent
        self.product_type = parent.ui.comboBox_utec_product.currentText()
        self.database = parent.database
        self.source_db = parent.source_db
        self.progress_bar = parent.ui.progressBar

        self.conn = pyodbc.connect(f'DSN={self.parent.lineEdit_dsn_gp.text()};UID="";PWD=""')
        self.cursor = self.conn.cursor()

    # 開始轉檔
    def convert(self):
        if self.parent.ui.label_connection_status_gp == '未連線':
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('尚未開啟連線')
            msg_box.setText("<font size='4' color='Red'><b>尚未執行連線測試, 請執行連線測試後再執行轉檔作業.</b></font>")
            msg_box.setInformativeText("連線尚未開啟, 無法執行轉檔作業.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        if self.parent.ui.checkBox_medicine_gp.isChecked():
            self._cvt_medicine()
        if self.parent.ui.checkBox_compound_gp.isChecked():
            self._cvt_compound()
        if self.parent.ui.checkBox_user_gp.isChecked():
            self._cvt_user()
        if self.parent.ui.checkBox_patient_gp.isChecked():
            self._cvt_patient()
        if self.parent.ui.checkBox_medical_record_gp.isChecked():
            self._cvt_medical_record()
        if self.parent.ui.checkBox_symptom_gp.isChecked():
            self._cvt_symptom()
        if self.parent.ui.checkBox_disease_gp.isChecked():
            self._cvt_disease()

    @staticmethod
    def _get_date(in_date):
        if in_date is None:
            return None

        try:
            year, month, day = in_date.split('/')
        except ValueError:
            return

        if year.strip() == '':
            out_date = None
        else:
            year = int(year) + 1911
            out_date = f'{year}-{month}-{day}'

        return out_date

    @staticmethod
    def _get_share(share_type):
        share_type = share_type.strip()
        share = '基層醫療'

        if share_type == '福保':
            share = '低收入戶'
        elif share_type.strip() in ['榮民', '重大傷病']:
            share = share_type

        return share

    def _get_share_type(self, patient_key):
        sql = f'''
            SELECT InsType FROM patient
            WHERE
                PatientKey = {patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return string_utils.xstr(rows[0]['InsType'])

    def _get_field_value(self, field_value):
        if field_value is not None:
            result = string_utils.xstr(field_value).strip()
        else:
            result = None

        if result == '':
            result = None

        return result

    def _cvt_patient(self):
        self.parent.ui.label_progress.setText('病患基本資料檔轉檔')
        sql = """
            SELECT * FROM patient
            ORDER BY pid
        """
        rows = self._exec_sql(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        sql = 'TRUNCATE patient'
        self.database.exec_sql(sql)
        fields = [
            'PatientKey', 'Name', 'Birthday', 'ID',
            'Telephone', 'Cellphone', 'InitDate', 'InsType', 'DiscountType',
            'Gender', 'Address', 'Nationality', 'Remark',
            'ZipCode', 'CardNo', 'Marriage', 'History', 'Allergy',
        ]

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            name = self._get_field_value(row['chn_name'])
            card_no = self._get_field_value(row['IcCardNo'])
            telephone = self._get_field_value(row['Tele'])
            cellphone = self._get_field_value(row['Mobile_Tele'])
            address = self._get_field_value(row['Address'])
            zip_code = self._get_field_value(row['Post_Code'])
            marriage = self._get_field_value(row['Marry'])
            history = self._get_field_value(row['Sick_History'])
            allergy = self._get_field_value(row['Sen_sitive'])
            remark = self._get_field_value(row['Pat_Memo'])
            birthday = self._get_date(row['Birthday'])

            try:
                init_date = self._get_date(row['First_Diag'])
            except Exception:
                init_date = None

            ins_type = self._get_share(string_utils.xstr(row['Identity_Type']))
            # discount_type = self._get_discount_type(string_utils.xstr(row['Identity_Type']))
            discount_type = None

            try:
                patient_id = self._get_field_value(row['identity_card']).strip()
            except Exception:
                patient_id = None

            nationality = '本國'
            if patient_id is not None and len(patient_id) > 1:
                nationality = patient_utils.get_nationality(patient_id[1])
                if patient_id[1] == '1':
                    gender = '男'
                elif patient_id[1] == '2':
                    gender = '女'

            data = [
                row['pid'],
                name,
                birthday,
                patient_id,
                telephone,
                cellphone,
                init_date,
                ins_type,
                discount_type,
                gender,
                address,
                nationality,
                remark,
                zip_code,
                card_no,
                marriage,
                history,
                allergy,
            ]
            try:
                self.database.insert_record('patient', fields, data)
            except Exception:
                pass

    def _get_discount_type(self, id_type):
        discount_type = None
        id_type = id_type.strip()

        if id_type not in ['一般', '榮民', '福保', '重大傷病']:
            discount_type = id_type

        return discount_type

    def _cvt_medical_record(self):
        start_date = self.parent.ui.lineEdit_start_date_gp.text()
        end_date = self.parent.ui.lineEdit_end_date_gp.text()

        self.parent.ui.label_progress.setText('病歷資料檔')

        sql = f"""
            SELECT * FROM GT_DM
            WHERE
                REG_DATE BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY DIAG_ID
        """
        try:
            rows = self._exec_sql(sql)
        except Exception:
            return

        self._truncate_medical_record(start_date, end_date)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            if row['DELETE_FLAG'] == 'Y':  # 已刪除資料
                continue

            medical_record_row = {}
            self._convert_registration(row, medical_record_row)
            self._convert_type(row, medical_record_row)
            self._convert_diag(row, medical_record_row)
            case_key = self._insert_medical_record(medical_record_row)
            self._convert_prescript(case_key, medical_record_row['CaseDate'], row)
            self._convert_dosage(case_key, medical_record_row['CaseDate'], row)
            self._convert_treat_type(case_key)
            self._convert_fees(case_key, row)

    def _convert_registration(self, row, medical_record_row):
        ins_type_dict = {
            '0': '自費',
            '1': '健保',
            'Y': '健保',
        }
        injury_dict = {
            '1': '職業傷害',
            '2': '職業病',
            '3': '普通傷害',
            '4': '普通疾病',
        }
        period_dict = {
            'A': '早班',
            'B': '午班',
            'C': '晚班',
        }

        year, month, day = string_utils.xstr(row['REG_DATE']).split('/')
        case_date = f'{int(year)+1911}-{int(month):0>2}-{int(day):0>2} {string_utils.xstr(row["REG_TIME"])}:00'
        medical_record_row['CaseDate'] = case_date
        medical_record_row['RegistNo'] = row['WAIT_NO']
        medical_record_row['Room'] = row['ROOM_NO']
        medical_record_row['PatientKey'] = row['PID']
        medical_record_row['Share'] = self._get_share_type(medical_record_row['PatientKey'])
        medical_record_row['Name'] = self._get_field_value(row['PAT_CHN_NAME'])
        try:
            medical_record_row['InsType'] = ins_type_dict[row['INS_TYPE']]
        except Exception:
            medical_record_row['InsType'] = '健保'

        try:
            medical_record_row['Injury'] = injury_dict[row['INJURY']]
        except Exception:
            medical_record_row['Injury'] = '普通疾病'

        try:
            medical_record_row['Period'] = period_dict[row['REG_CLASS_CODE']]
        except Exception:
            medical_record_row['Period'] = '早班'

        medical_record_row['Card'] = self._get_field_value(row['INS_CARD'])
        medical_record_row['Continuance'] = number_utils.get_integer(row['CARD_TIMES'])
        medical_record_row['Register'] = self._get_field_value(row['REG_NAME'])
        medical_record_row['Doctor'] = self._get_field_value(row['DOCTOR_NAME'])
        medical_record_row['Cashier'] = self._get_field_value(row['CHG_NAME'])
        medical_record_row['Massager'] = self._get_field_value(row['MASSAGE_NAME'])

    def _convert_type(self, row, medical_record_row):
        medical_record_row['RegistType'] = '一般門診'
        medical_record_row['ApplyType'] = '申報'
        if self._get_field_value(row['TREAT_TYPE']) == '針灸':
            if date_utils.str_to_date(medical_record_row['CaseDate']) >= nhi_utils.INS_TREAT_2021_DATE:
                medical_record_row['Treatment'] = '一般針灸'
            else:
                medical_record_row['Treatment'] = '針灸治療'
        elif self._get_field_value(row['TREAT_TYPE']) == '傷科':
            if date_utils.str_to_date(medical_record_row['CaseDate']) >= nhi_utils.INS_TREAT_2021_DATE:
                medical_record_row['Treatment'] = '一般傷科'
            else:
                medical_record_row['Treatment'] = '傷科治療'
        else:
            medical_record_row['Treatment'] = None

    def _convert_diag(self, row, medical_record_row):
        medical_record_row['DiseaseCode1'] = None
        medical_record_row['DiseaseName1'] = None
        medical_record_row['SpecialCode'] = None
        medical_record_row['DiseaseCode2'] = None
        medical_record_row['DiseaseName2'] = None
        medical_record_row['DiseaseCode3'] = None
        medical_record_row['DiseaseName3'] = None
        medical_record_row['Symptom'] = None
        medical_record_row['Tongue'] = None
        medical_record_row['Pulse'] = None
        medical_record_row['Distincts'] = None
        medical_record_row['Cure'] = None
        medical_record_row['Remark'] = None

        diag_id = self._get_field_value(row['DIAG_ID'])
        if diag_id is None:
            return

        sql = f"""
            SELECT * FROM GT_DS
            WHERE
                Diag_ID = '{diag_id}'
        """
        rows = self._exec_sql(sql)

        if len(rows) <= 0:
            return

        diag_row = rows[0]

        medical_record_row['DiseaseCode1'] = self._get_field_value(row['DISE_STANDARD1'])
        medical_record_row['DiseaseName1'] = self._get_field_value(row['DISE_NAME1'])
        medical_record_row['SpecialCode'] = self._get_field_value(row['DISE_SLOW_CODE_1'])
        medical_record_row['DiseaseCode2'] = self._get_field_value(diag_row['DISE_STANDARD2'])
        medical_record_row['DiseaseName2'] = self._get_field_value(diag_row['DISE_NAME2'])
        medical_record_row['DiseaseCode3'] = self._get_field_value(diag_row['DISE_STANDARD3'])
        medical_record_row['DiseaseName3'] = self._get_field_value(diag_row['DISE_NAME3'])

        try:
            medical_record_row['Symptom'] = self._get_field_value(diag_row['SYMPTOM'])
        except Exception:
            medical_record_row['Symptom'] = self._get_field_value(diag_row['SYMPTOM'])

        medical_record_row['Tongue'] = self._get_field_value(diag_row['TONGUE'])
        left_pulse = self._get_field_value(diag_row['LEFT_PULSE'])
        right_pulse = self._get_field_value(diag_row['RIGHT_PULSE'])

        pulse_list = []
        if left_pulse not in [None, '']:
            pulse_list.append(f'左脈: {left_pulse}')

        if right_pulse not in [None, '']:
            pulse_list.append(f'右脈: {right_pulse}')

        if len(pulse_list) > 0:
            medical_record_row['Pulse'] = ', '.join(pulse_list)
        else:
            medical_record_row['Pulse'] = None

        medical_record_row['Remark'] = self._get_field_value(diag_row['DIAG_MEMO'])
        medical_record_row['Distincts'] = self._get_field_value(diag_row['JUDGE'])
        medical_record_row['Cure'] = self._get_field_value(diag_row['LUNZHI'])

    def _insert_medical_record(self, row):
        fields = [
            'CaseDate', 'RegistNo', 'Room', 'PatientKey', 'Name', 'InsType',
            'DoctorDate', 'ChargeDate', 'ChargePeriod',
            'Share', 'Injury', 'Period', 'Card', 'Continuance',
            'Register', 'Doctor', 'Cashier', 'Massager',
            'DoctorDone', 'ChargeDone', 'DrugDone',
            'DiseaseCode1', 'DiseaseName1',
            'DiseaseCode2', 'DiseaseName2',
            'DiseaseCode3', 'DiseaseName3',
            'SpecialCode',
            'Symptom', 'Tongue', 'Pulse', 'Remark',
            'RegistType', 'ApplyType', 'Treatment',
        ]
        data = [
            row['CaseDate'], row['RegistNo'], row['Room'], row['PatientKey'], row['Name'], row['InsType'],
            row['CaseDate'], row['CaseDate'], row['Period'],
            row['Share'], row['Injury'], row['Period'], row['Card'], row['Continuance'],
            row['Register'], row['Doctor'], row['Cashier'], row['Massager'],
            'True', 'True', 'True',
            row['DiseaseCode1'], row['DiseaseName1'],
            row['DiseaseCode2'], row['DiseaseName2'],
            row['DiseaseCode3'], row['DiseaseName3'],
            row['SpecialCode'],
            row['Symptom'], row['Tongue'], row['Pulse'], row['Remark'],
            row['RegistType'], row['ApplyType'], row['Treatment'],
        ]
        case_key = self.database.insert_record('cases', fields, data)

        return case_key

    def _get_medicine_type(self, code):
        medicine_type_dict = {
            '0': '專案',
            '1': '單方',
            '2': '複方',
            '3': '水藥',
            '4': '外用',
            '5': '高貴',
            '6': '穴道',
            '7': '處置',
            '9': '處置',
            'B': '器材',
            'C': '檢驗',
        }

        try:
            medicine_type = medicine_type_dict[code]
        except Exception:
            medicine_type = '單方'

        return medicine_type

    def _convert_prescript(self, case_key, case_date, dm_row):
        diag_id = self._get_field_value(dm_row['DIAG_ID'])
        if diag_id is None:
            return

        sql = f"""
            SELECT * FROM GT_DDY
            WHERE
                Diag_ID = '{diag_id}'
            ORDER BY DDY_ID
        """
        rows = self._exec_sql(sql)

        fields = [
            'CaseKey', 'CaseDate', 'MedicineSet',
            'MedicineType', 'MedicineKey', 'InsCode',
            'MedicineName', 'Unit', 'DosageMode', 'Dosage',
            'Price', 'Amount',
        ]
        for row in rows:
            try:
                dosage = number_utils.get_float(row['QUANT_HURTNO'])
            except Exception:
                dosage = None

            medicine_name = self._get_field_value(row['DRUG_NAME'])
            medicine_type = self._get_medicine_type(self._get_field_value(row['DRUG_TYPE']))
            if '中度複雜性針灸' in medicine_name or '高度複雜性針灸' in medicine_name:
                medicine_type = '穴道'
            elif '中度複雜性傷科' in medicine_name or '高度複雜性傷科' in medicine_name:
                medicine_type = '處置'

            medicine_key, price = self._get_medicine_key(self._get_field_value(row['DRUG_ID']))
            try:
                amount = price * dosage
            except Exception:
                amount = None

            data = [
                case_key,
                case_date,
                row['INS_SELF_FLAG'],
                medicine_type,
                medicine_key,
                self._get_field_value(row['DRUG_STD_CODE']),
                medicine_name,
                self._get_field_value(row['UNIT_NAME']),
                '日劑量',
                dosage,
                price,
                amount,
            ]
            self.database.insert_record('prescript', fields, data)

            if '中度複雜性針灸' in medicine_name:
                self._update_cases(case_key, 'Treatment', '中度複雜性針灸')
            elif '高度複雜性針灸' in medicine_name:
                self._update_cases(case_key, 'Treatment', '高度複雜性針灸')
            elif '中度複雜性傷科' in medicine_name:
                if number_utils.get_integer(dm_row['CARD_TIMES']) >= 2:
                    treatment = '一般傷科'
                else:
                    treatment = '中度複雜性傷科'

                self._update_cases(case_key, 'Treatment', treatment)
            elif '高度複雜性傷科' in medicine_name:
                if number_utils.get_integer(dm_row['CARD_TIMES']) >= 2:
                    treatment = '一般傷科'
                else:
                    treatment = '高度複雜性傷科'

                self._update_cases(case_key, 'Treatment', treatment)

    def _get_medicine_key(self, drug_id):
        sql = f'''
            SELECT MedicineKey, SalePrice FROM medicine
            WHERE
                MedicineMode = "{drug_id}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None, None

        row = rows[0]
        medicine_key = row['MedicineKey']
        sale_price = number_utils.get_float(row['SalePrice'])

        return medicine_key, sale_price

    # 設定就醫類別及療程
    def _convert_treat_type(self, case_key):
        sql = f'''
            SELECT Treatment, Continuance FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        case_row = self.database.select_record(sql)[0]

        treatment = case_row['Treatment']
        course = number_utils.get_integer(case_row['Continuance'])
        if treatment in nhi_utils.INS_TREAT:
            treat_type = treatment

            if course is None or course <= 0:
                self._update_cases(case_key, 'Continuance', 1)
        elif treatment in ['', None]:
            treat_type = '內科'
            if course >= 1:
                sql = f'''
                    UPDATE cases
                    SET
                        Continuance = NULL
                    WHERE
                        CaseKey = {case_key}
                '''
                self.database.exec_sql(sql)

        self._update_cases(case_key, 'TreatType', treat_type)

    def _convert_fees(self, case_key, dm_row):
        diag_id = self._get_field_value(dm_row['DIAG_ID'])
        if diag_id is None:
            return

        sql = f"""
            SELECT * FROM GT_CTY
            WHERE
                Diag_ID = '{diag_id}'
        """
        rows = self._exec_sql(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        
        regist_fee = number_utils.get_integer(row['REG_INS'])
        diag_fee = number_utils.get_integer(row['EXAM_INS'])
        inter_drug_fee = number_utils.get_integer(row['MED_INS'])
        pharmacy_fee = number_utils.get_integer(row['MED_MIX_INS'])
        acupuncture_fee = number_utils.get_integer(row['ACUP_INS'])
        massage_fee = number_utils.get_integer(row['MASSAGE_INS'])
        diag_share_fee = number_utils.get_integer(row['REG_INS_PART']) + number_utils.get_integer(row['HURT_INS_PART'])
        drug_share_fee = number_utils.get_integer(row['MED_INS_PART'])
        ins_total_fee = number_utils.get_integer(row['INS_TOTAL'])
        ins_apply_fee = number_utils.get_integer(row['INS_REQUEST_TOTAL'])
        s_diag_fee = number_utils.get_integer(row['EXAM_SELF'])
        s_drug_fee = number_utils.get_integer(row['INN_MED_SELF']) + number_utils.get_integer(row['HEAL_MED_SELF'])
        s_herb_fee = number_utils.get_integer(row['DRINK_MED_SELF'])
        s_massage_fee = number_utils.get_integer(row['MASSAGE_SELF'])
        s_material_fee = number_utils.get_integer(row['MATERIAL_SELF']) + number_utils.get_integer(row['OTHER_SELF'])
        discount_fee = number_utils.get_integer(row['SELF_DISCOUNT'])
        self_total_fee = number_utils.get_integer(row['SELF_TOTAL'])

        if pharmacy_fee > 0:
            pharmacy_type = '申報'
        else:
            pharmacy_type = '不申報'

        fields = [
            'RegistFee', 'DiagFee', 'InterDrugFee',
            'PharmacyFee', 'PharmacyType',
            'AcupunctureFee', 'MassageFee',
            'DiagShareFee', 'SDiagShareFee',
            'DrugShareFee', 'SDrugShareFee',
            'InsTotalFee', 'InsApplyFee',
            'SDiagFee', 'SDrugFee', 'SHerbFee',
            'SMassageFee', 'SMaterialFee',
            'DiscountFee', 'SelfTotalFee',
            'TotalFee', 'ReceiptFee',
        ]
        data = [
            regist_fee, diag_fee, inter_drug_fee,
            pharmacy_fee, pharmacy_type,
            acupuncture_fee, massage_fee,
            diag_share_fee, drug_share_fee,
            diag_share_fee, drug_share_fee,
            ins_total_fee, ins_apply_fee,
            s_diag_fee, s_drug_fee, s_herb_fee,
            s_massage_fee, s_material_fee,
            discount_fee, self_total_fee,
            self_total_fee, self_total_fee,
        ]
        self.database.update_record('cases', fields, 'CaseKey', case_key, data)

    def _update_cases(self, case_key, field_name, value):
        sql = f'''
            UPDATE cases
            SET
                {field_name} = "{value}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

    def _convert_dosage(self, case_key, case_date, row):
        diag_id = self._get_field_value(row['DIAG_ID'])
        if diag_id is None:
            return

        sql = f"""
            SELECT * FROM GT_BDT
            WHERE
                Diag_ID = '{diag_id}'
        """
        rows = self._exec_sql(sql)

        fields = [
            'CaseKey', 'MedicineSet',
            'Packages', 'Days', 'Instruction',
        ]
        for row in rows:
            data = [
                case_key,
                row['INS_SELF_FLAG'],
                self._get_field_value(row['BOXES']),
                self._get_field_value(row['DAYS']),
                self._get_field_value(row['TAKEWAY']),
            ]

            self.database.insert_record('dosage', fields, data)

    def _truncate_medical_record(self, start_date, end_date):
        start_year = int(start_date.split('/')[0]) + 1911
        start_month = int(start_date.split('/')[1])
        start_day = int(start_date.split('/')[2])

        end_year = int(end_date.split('/')[0]) + 1911
        end_month = int(end_date.split('/')[1])
        end_day = int(end_date.split('/')[2])

        start_date = f'{start_year}-{start_month:0>2}-{start_day:0>2} 00:00:00'
        end_date = f'{end_year}-{end_month:0>2}-{end_day:0>2} 23:59:59'
        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        case_key_list = []
        for row in rows:
            case_key_list.append(row['CaseKey'])

        self._delete_table_by_case_key_list('cases', case_key_list)
        self._delete_table_by_case_key_list('prescript', case_key_list)
        self._delete_table_by_case_key_list('dosage', case_key_list)

    def _delete_table_by_case_key_list(self, table_name, case_key_list):
        if len(case_key_list) <= 0:
            return
        elif len(case_key_list) == 1:
            sql = f'''
                DELETE FROM {table_name}
                WHERE
                    CaseKey = {case_key_list[0]}
            '''
        else:
            sql = f'''
                DELETE FROM {table_name}
                WHERE
                    CaseKey IN {tuple(case_key_list)}
            '''

        self.database.exec_sql(sql)

    def _cvt_dosage(self, case_key, ins_type, package, pres_days, instruction_code):
        if package in [None, '0'] and pres_days in [None, '0']:
            return

        if ins_type == '健保':
            medicine_set = 1
        else:
            medicine_set = 2

        instruction = self._get_instruction(instruction_code)

        fields = [
            'CaseKey', 'MedicineSet', 'Packages', 'Days', 'Instruction'
        ]
        data = [
            case_key,
            medicine_set,
            package,
            pres_days,
            instruction,
        ]
        self.database.insert_record('dosage', fields, data)

    def _cvt_medicine(self):
        self.parent.ui.label_progress.setText('處方資料檔轉檔')
        sql = """
            SELECT * FROM Drug_DB
            ORDER BY Drug_Id
        """
        rows = self._exec_sql(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        sql = 'TRUNCATE medicine'
        self.database.exec_sql(sql)
        fields = [
            'MedicineType', 'MedicineMode', 'MedicineCode', 'InputCode',
            'InsCode', 'MedicineName', 'MedicineAlias', 'Unit', 'Dosage',
            'Location', 'SalePrice', 'InPrice',
            'SafeQuantity', 'Description',
        ]

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            use_flag = self._get_field_value(row['Use_Flag'])
            if string_utils.xstr(use_flag) == '不用':
                continue

            medicine_type = self._get_medicine_type(row['Drug_Type'])
            medicine_code = self._get_field_value(row['Self_Code'])
            medicine_mode = self._get_field_value(row['Drug_Id'])
            input_code = self._get_field_value(row['ZY_Code'])
            ins_code = self._get_field_value(row['Standard_Code'])
            medicine_name = self._get_field_value(row['Drug_Name'])
            medicine_alias = None
            unit = self._get_field_value(row['unit_name'])
            dosage = None
            location = None

            sale_price = number_utils.get_float(row['Diag_Price'])
            sale_price = round(sale_price, 2)
            in_price = number_utils.get_float(row['Purchase_Price'])
            in_price = round(in_price, 2)
            safe_quantity = None
            description = row['Drug_Memo']

            data = [
                medicine_type,
                medicine_mode,
                medicine_code,
                input_code[:5],
                ins_code,
                medicine_name[:40],
                medicine_alias,
                unit,
                dosage,
                location,
                sale_price,
                in_price,
                safe_quantity,
                description,
            ]

            self.database.insert_record('medicine', fields, data)

    def _get_medicine_row(self, drug_id):
        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineMode = "{drug_id}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return rows[0]

    def _get_drug_slip_rows(self, drug_id):
        sql = f"""
            SELECT * FROM drug_slip
            WHERE
                CDrugId = '{drug_id}'
        """
        rows = self._exec_sql(sql)
        if len(rows) <= 0:
            return None

        return rows

    def _cvt_compound_title(self):
        sql = """
            SELECT CDrugid FROM drug_slip
            GROUP BY CDrugid
            ORDER BY CDrugid
        """
        rows = self._exec_sql(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        sql = 'DELETE FROM medicine WHERE MedicineType = "成方"'
        self.database.exec_sql(sql)

        fields = [
            'MedicineType', 'MedicineMode', 'InputCode', 'MedicineName', 'Unit'
        ]

        for row in rows:
            drug_id = self._get_field_value(row['CDrugid'])
            medicine_row = self._get_medicine_row(drug_id)
            if medicine_row is None:
                continue

            medicine_type = '成方'
            input_code = string_utils.xstr(medicine_row['InputCode'])
            medicine_name = string_utils.xstr(medicine_row['MedicineName'])
            unit = string_utils.xstr(medicine_row['Unit'])

            data = [
                medicine_type,
                drug_id,
                input_code,
                medicine_name,
                unit,
            ]

            self.database.insert_record('medicine', fields, data)

    def _cvt_compound(self):
        self._cvt_compound_title()

        self.parent.ui.label_progress.setText('成方資料檔轉檔')
        sql = """
            SELECT * FROM medicine
            WHERE
                MedicineType = "成方"
            ORDER BY MedicineKey
        """
        rows = self.database.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        fields = [
            'CompoundKey', 'MedicineKey', 'Quantity', 'Unit',
        ]

        sql = 'TRUNCATE refcompound'
        self.database.exec_sql(sql)

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            drug_id = string_utils.xstr(row['MedicineMode'])
            drug_slip_rows = self._get_drug_slip_rows(drug_id)
            if drug_slip_rows is None:
                continue

            compound_key = row['MedicineKey']
            for drug_slip_row in drug_slip_rows:
                medicine_row = self._get_medicine_row(self._get_field_value(drug_slip_row['Slip_Drug_Id']))
                if medicine_row is None:
                    continue

                medicine_key = medicine_row['MedicineKey']
                unit = self._get_field_value(drug_slip_row['unit_name'])
                try:
                    quantity = number_utils.get_float(drug_slip_row['quantity'])
                except Exception:
                    quantity = None

                data = [
                    compound_key,
                    medicine_key,
                    quantity,
                    unit,
                ]

                self.database.insert_record('refcompound', fields, data)

    def _cvt_user(self):
        position_dict = {
            '專任醫師': '醫師',
            '支援醫師': '支援醫師',
            '掛號員': '職員',
            '行政': '職員',
            '推拿師': '推拿師父',
        }

        self.parent.ui.label_progress.setText('使用者資料檔轉檔')
        sql = """
            SELECT * FROM UserDoc
            ORDER BY uid
        """
        rows = self._exec_sql(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        sql = 'TRUNCATE person'
        self.database.exec_sql(sql)
        fields = [
            'Code', 'Name', 'Birthday',
            'ID', 'Gender',
            'Address', 'Telephone',
            'Email', 'Position',
            'InitDate', 'QuitDate',
            # 'Password',
            'Certificate',
        ]

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            use_flag = self._get_field_value(row['UseFlag'])
            if string_utils.xstr(use_flag) == 'N':
                continue

            code = self._get_field_value(row['uid'])
            name = self._get_field_value(row['uchnname'])
            birthday = self._get_date(row['ubirthday'])
            id = self._get_field_value(row['uiccard'])
            gender = self._get_field_value(row['usex'])
            address = self._get_field_value(row['uaddress'])
            telephone = self._get_field_value(row['utele'])
            email = self._get_field_value(row['uemail'])
            # password = self._get_field_value(row['upwd'])
            # password = self._translate_pwd(password)

            try:
                position = position_dict[self._get_field_value(row['UPosition'])]
            except Exception:
                position = None

            init_date = self._get_date(row['uenterdate'])
            quit_date = self._get_date(row['uleavedate'])
            certificate = self._get_field_value(row['ZhongYiZheng'])

            data = [
                code, name, birthday,
                id, gender,
                address, telephone,
                email, position,
                init_date, quit_date,
                # password,
                certificate,
            ]
            self.database.insert_record('person', fields, data)

    def _translate_pwd(self, pwd):
        if pwd is None:
            return None

        pwd_symbol = {
            ",": '0',
            "-": '1',
            ".": '2',
            "/": '3',
            "(": '4',
            ")": '5',
            "*": '6',
            "+": '7',
            "$": '8',
            "%": '9',
        }

        password = ''
        for i in pwd:
            password += pwd_symbol[i]

        return password[:6]

    def _cvt_disease(self):
        self.parent.ui.label_progress.setText('病名資料檔轉檔')
        sql = """
            SELECT ICD10CM, ICD10ZYCODE, 慢性 AS SpecialCode FROM disease
            ORDER BY ID
        """
        rows = self._exec_sql(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)
            icd10 = string_utils.xstr(row['ICD10CM']).strip()
            input_code = string_utils.xstr(row['ICD10ZYCODE'])[:5]
            special_code = string_utils.xstr(row['SpecialCode']).strip()

            self._update_disease(icd10, input_code, special_code)

    def _update_disease(self, icd10, input_code, special_code):
        if special_code == '':
            sql = f'''
                UPDATE icd10
                SET
                    InputCode = "{input_code}"
                WHERE
                    ICDCode = "{icd10}"
            '''
        else:
            sql = f'''
                UPDATE icd10
                SET
                    InputCode = "{input_code}", SpecialCode = "{special_code}"
                WHERE
                    ICDCode = "{icd10}"
            '''

        self.database.exec_sql(sql)

    def _exec_sql(self, sql):
        self.cursor.execute(sql)
        columns = [column[0] for column in self.cursor.description]
        rows = []
        results = self.cursor.fetchall()
        for row in results:
            rows.append(dict(zip(columns, row)))

        return rows
