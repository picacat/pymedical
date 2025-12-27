
from PyQt5.QtWidgets import QMessageBox, QPushButton

try:
    import pyodbc
except Exception:
    pass

from libs import string_utils
from libs import patient_utils
from libs import number_utils
from libs import date_utils


# 國泰轉檔 2018.05.09
class CvtKThis():
    def __init__(self, parent, *args):
        self.parent = parent
        self.product_type = parent.ui.comboBox_utec_product.currentText()
        self.database = parent.database
        self.source_db = parent.source_db
        self.progress_bar = parent.ui.progressBar

        sql = 'SELECT TID_ID, TID_NAME FROM typeid ORDER BY TID_ID'
        self.typeid = self.source_db.select_record(sql)

        sql = 'SELECT USR_ID, USR_NAME FROM users ORDER BY USR_ID'
        self.users = self.source_db.select_record(sql)

        sql = 'SELECT UNT_ID, UNT_NAME FROM unit ORDER BY UNT_ID'
        self.unit = self.source_db.select_record(sql)

        sql = 'SELECT ETW_ID, ETW_NAME FROM eatway ORDER BY ETW_ID'
        self.eat_way = self.source_db.select_record(sql)

        sql = '''
            SELECT ALM_ID, ALM_TYPE, ALM_NAME, ALM_LICNO, ALM_SELL FROM allmenu
            WHERE
                ALM_TYPE != '01'
            ORDER BY ALM_ID
        '''
        self.medicine = self.source_db.select_record(sql)

    # 開始轉檔
    def convert(self):
        if self.parent.ui.label_connection_status_kt.text() == '未連線':
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('尚未開啟連線')
            msg_box.setText("<font size='4' color='Red'><b>尚未執行連線測試, 請執行連線測試後再執行轉檔作業.</b></font>")
            msg_box.setInformativeText("連線尚未開啟, 無法執行轉檔作業.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        if self.parent.ui.checkBox_patient_kt.isChecked():
            self._cvt_patient()
            self._cvt_nr('patient', 'PatientKey', 'Remark')
        if self.parent.ui.checkBox_medical_record_kt.isChecked():
            self._cvt_medical_record()
        if self.parent.ui.checkBox_symptom_kt.isChecked():
            self._cvt_symptom()
        if self.parent.ui.checkBox_medicine_kt.isChecked():
            self._cvt_medicine()
        if self.parent.ui.checkBox_disease_kt.isChecked():
            self._cvt_disease()
        if self.parent.ui.checkBox_users_kt.isChecked():
            self._cvt_users()

    @staticmethod
    def _get_date(in_date):
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
    def _get_share(share_code):
        share_type = '基層醫療'

        if share_code == '33':
            share_type = '低收入戶'
        elif share_code == '35':
            share_type = '榮民'

        return share_type

    def _get_patient_remark(self, patient_key):
        sql = f'''
            SELECT PAT_GRAPH FROM patientg
            WHERE
                PAT_SERIAL = "9999" AND
                PAT_ID = "{patient_key}"
        '''
        rows = self.source_db.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]

        return row['PAT_GRAPH']

    def _get_patient_key(self, field_value):
        patient_key = field_value

        try:
            if string_utils.xstr(patient_key)[0] == '6':
                patient_key = -number_utils.get_integer(patient_key[1:])
        except Exception:
            patient_key = 0

        return patient_key

    def _get_case_key(self, field_value):
        case_key = field_value

        try:
            if string_utils.xstr(case_key)[0] == '6':
                case_key = -number_utils.get_integer(case_key[1:])
        except Exception:
            pass

        return case_key

    def _cvt_patient(self):
        self.parent.ui.label_progress.setText('病患基本資料檔轉檔')
        sql = '''
            SELECT * FROM patient
            ORDER BY PAT_ID'''
        rows = self.source_db.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        sql = 'TRUNCATE patient'
        self.database.exec_sql(sql)
        fields = [
            'PatientKey', 'ChartNo', 'Name', 'Birthday', 'ID',
            'Telephone', 'Cellphone', 'InitDate', 'InsType', 'DiscountType',
            'Gender', 'Address', 'Nationality', 'Remark',
        ]

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            birthday = self._get_date(row['PAT_BDAY'])

            try:
                init_date = self._get_date(row['PAT_FDATE']) + ' 09:00'
            except Exception:
                init_date = None

            ins_type = self._get_share(row['PAT_ISTYPE'])
            discount_type = self._get_discount_type(row['PAT_IDTYPE'])
            if discount_type in ['一般']:
                discount_type = None

            if row['PAT_SEX'] == '0':
                gender = '女'
            elif row['PAT_SEX'] == '1':
                gender = '男'
            else:
                gender = None

            patient_id = string_utils.xstr(row['PAT_BNO'])
            nationality = '本國'
            if len(patient_id) > 1:
                nationality = patient_utils.get_nationality(patient_id[1])
                if gender is None:
                    if patient_id[1] == '1':
                        gender = '男'
                    elif patient_id[1] == '2':
                        gender = '女'

            try:
                remark = self._get_patient_remark(row['PAT_ID'])
            except Exception:
                remark = None

            patient_key = self._get_patient_key(row['PAT_ID'])

            data = [
                patient_key,
                None,
                row['PAT_NAME'],
                birthday,
                patient_id,
                row['PAT_TEL1'],
                row['PAT_TEL2'],
                init_date,
                ins_type,
                discount_type,
                gender,
                row['PAT_ADDR1'],
                nationality,
                remark,
            ]
            try:
                self.database.insert_record('patient', fields, data)
            except Exception:
                pass

    def _get_disease(self, disease_code):
        if disease_code in [None, '']:
            return None, None, None

        sql = f'''
            SELECT ALM_NAME, ALM_ICD9, ALM_SPCURE FROM allmenu
            WHERE
                ALM_TYPE = "01" AND
                ALM_ID = "{disease_code}"
        '''
        rows = self.source_db.select_record(sql)
        if len(rows) <= 0:
            return None, None, None

        row = rows[0]
        disease_code = row['ALM_ICD9']
        disease_name = row['ALM_NAME']
        special_code = row['ALM_SPCURE']

        return disease_code, disease_name, special_code

    def _get_discount_type(self, id_type):
        discount_type = None
        for row in self.typeid:
            if id_type == row['TID_ID']:
                discount_type = row['TID_NAME']
                break

        if discount_type in ['一般', '自費患者']:
            return None

        return discount_type

    def _get_user(self, user_id):
        user_name = None
        for row in self.users:
            if user_id == row['USR_ID']:
                user_name = row['USR_NAME']
                break

        return user_name

    def _get_unit(self, unit_code):
        unit_name = None
        for row in self.unit:
            if unit_code == row['UNT_ID']:
                unit_name = row['UNT_NAME']
                break

        return unit_name

    def _get_instruction(self, instruction_code):
        instruction = None
        for row in self.eat_way:
            if instruction_code == row['ETW_ID']:
                instruction = row['ETW_NAME']
                break

        return instruction

    def _get_medicine(self, medicine_code):
        medicine_type, medicine_name, ins_code, price = None, None, None, None
        for row in self.medicine:
            if medicine_code == row['ALM_ID']:
                medicine_type = self._get_medicine_type(row['ALM_TYPE'])
                medicine_name = row['ALM_NAME']
                ins_code = row['ALM_LICNO']
                price = row['ALM_SELL']
                break

        return medicine_type, medicine_name, ins_code, number_utils.get_float(price)

    def _get_symptom(self, case_key):
        sql = f'''
            SELECT HIS_DOC FROM hisopdd
            WHERE
                HIS_ID = "{case_key}" AND
                HIS_GRPNO = "01"
           ORDER BY HIS_SERNO
        '''
        rows = self.source_db.select_record(sql)

        symptom = ''
        for row in rows:
            symptom += string_utils.xstr(row['HIS_DOC'])

        return symptom

    def _get_tongue(self, case_key):
        sql = f'''
            SELECT HIS_DOC FROM hisopdd
            WHERE
                HIS_ID = "{case_key}" AND
                HIS_GRPNO = "05"
        '''
        rows = self.source_db.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]

        return row['HIS_DOC']

    def _get_ins_case_key(self, case_date, patient_key):
        case_date = case_date.split(' ')[0]

        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                DATE(CaseDate) = "{case_date}" AND
                PatientKey = {patient_key}
        '''

        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return rows[0]['CaseKey']

    def _cvt_medical_record(self):
        self.parent.ui.label_progress.setText('病歷資料檔轉檔')
        sql = 'SELECT * FROM history ORDER BY HIS_ID'
        rows = self.source_db.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        sql = 'TRUNCATE cases'
        self.database.exec_sql(sql)
        sql = 'TRUNCATE dosage'
        self.database.exec_sql(sql)
        sql = 'TRUNCATE prescript'
        self.database.exec_sql(sql)

        fields = [
            'CaseKey', 'PatientKey', 'Name', 'CaseDate', 'DoctorDate', 'ChargeDate',
            'Period', 'ChargePeriod', 'Visit', 'RegistType', 'TreatType', 'Injury',
            'InsType', 'Share', 'ApplyType', 'PharmacyType',
            'Card', 'Continuance', 'Room', 'RegistNo', 'Doctor', 'Register',
            'Symptom', 'Tongue', 'Pulse', 'Distincts', 'Cure',
            'SpecialCode',
            'DiseaseCode1', 'DiseaseName1',
            'DiseaseCode2', 'DiseaseName2',
            'DiseaseCode3', 'DiseaseName3',
            'RegistFee', 'SDiagShareFee',
            'DoctorDone', 'ChargeDone',
        ]

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            if row['HIS_LOOKDATE'] is None:
                continue

            reg_time = ''
            doctor_time = ''
            charge_time = ''

            if row['HIS_REG_TIME'] is not None:
                reg_time = row['HIS_REG_TIME']

            if row['HIS_LOOKTIME'] is not None:
                if reg_time == '':
                    reg_time = row['HIS_LOOKTIME']

                doctor_time = row['HIS_LOOKTIME']

            if row['HIS_SAVETIME'] is not None:
                charge_time = row['HIS_SAVETIME']

            his_date = self._get_date(row['HIS_LOOKDATE'])
            case_date = f'{his_date} {reg_time}'.strip()
            doctor_date = f'{his_date} {doctor_time}'.strip()
            charge_date = f'{his_date} {charge_time}'.strip()

            patient_key = self._get_patient_key(row['HIS_PAT_ID'])

            if row['HIS_TIS_ID'] == '00':
                ins_type = '自費'
                case_key = self._get_ins_case_key(case_date, patient_key)
                if case_key is not None:
                    self._cvt_prescript(row['HIS_ID'], case_date, ins_type, None, new_case_key=case_key)
                    self._cvt_dosage(
                        row['HIS_ID'], ins_type, row['HIS_PACK'], row['HIS_DAY'], row['HIS_EATWAY'],
                        new_case_key=case_key
                    )
                    self._cvt_fees(row['HIS_ID'], ins_type, new_case_key=case_key)

                    continue
            else:
                ins_type = '健保'

            period = None
            if row['HIS_REG_SECTION'] == '1':
                period = '早班'
            elif row['HIS_REG_SECTION'] == '2':
                period = '午班'
            elif row['HIS_REG_SECTION'] == '3':
                period = '晚班'

            visit = None
            if row['HIS_FIRSTORNOT'] == '0':
                visit = '複診'
            elif row['HIS_FIRSTORNOT'] == '1':
                visit = '初診'

            share_type = self._get_share(row['HIS_TIS_ID'])
            card = string_utils.xstr(row['HIS_CARD'])[2:6].strip()
            if card in ['-', '']:
                if ins_type == '自費':
                    card = '免卡'
                else:
                    card = '欠卡'

            if row['HIS_REP_LNO'] == '網路' and card == '欠卡':
                continue

            continuance = None
            if ins_type == '健保' and row['HIS_CARD'] is not None and len(row['HIS_CARD']) >= 8:
                continuance = string_utils.xstr(row['HIS_CARD'])[7].strip()
                if continuance in ['-', '', '1']:
                    continuance = None

            injury = '普通疾病'
            if card == 'IC06':
                share_type = '職業傷害'
                injury = '職業傷害'

            try:
                room = int(row['HIS_ROOM1'])
            except (TypeError, ValueError):
                room = 1

            try:
                regist_no = int(row['HIS_REG_REGNO'])
            except (TypeError, ValueError):
                regist_no = None

            doctor = self._get_user(row['HIS_DRID1'])
            registrar = self._get_user(row['HIS_REG_USRID'])

            symptom = self._get_symptom(row['HIS_ID'])
            tongue = self._get_tongue(row['HIS_ID'])

            disease_code1, disease_name1, special_code = self._get_disease(
                string_utils.xstr(row['HIS_SICK1']).strip()
            )
            disease_code2, disease_name2, _ = self._get_disease(
                string_utils.xstr(row['HIS_SICK2']).strip()
            )
            disease_code3, disease_name3, _ = self._get_disease(
                string_utils.xstr(row['HIS_SICK3']).strip()
            )

            case_key = self._get_case_key(row['HIS_ID'])
            data = [
                case_key,
                patient_key,
                row['HIS_PAT_NAME'],
                case_date,
                doctor_date,
                charge_date,
                period,
                period,
                visit,
                '一般門診',
                '內科',
                injury,
                ins_type,
                share_type,
                '申報',
                '申報',
                card,
                continuance,
                room,
                regist_no,
                doctor,
                registrar,
                symptom,
                tongue,
                row['HIS_MINE'],
                row['HIS_LOOKTYPE'],
                row['HIS_DWAY'],
                special_code,
                disease_code1, disease_name1,
                disease_code2, disease_name2,
                disease_code3, disease_name3,
                row['HIS_REG_REGPAY'],
                row['HIS_REG_SELFPAY'],
                'True', 'True',
            ]

            try:
                new_case_key = self.database.insert_record('cases', fields, data)
                self._cvt_prescript(row['HIS_ID'], case_date, ins_type, continuance)
                self._cvt_dosage(row['HIS_ID'], ins_type, row['HIS_PACK'], row['HIS_DAY'], row['HIS_EATWAY'])
                self._cvt_fees(row['HIS_ID'], ins_type, new_case_key)

                self._update_treat_type(new_case_key)
            except Exception:
                pass

    # 設定就醫類別及療程
    def _update_treat_type(self, case_key):
        pass

    def _cvt_dosage(self, his_id, ins_type, package, pres_days, instruction_code, new_case_key=None):
        if package in [None, '0'] and pres_days in [None, '0']:
            return

        instruction = self._get_instruction(instruction_code)

        fields = [
            'CaseKey', 'MedicineSet', 'Packages', 'Days', 'Instruction'
        ]

        if new_case_key is not None:
            case_key = new_case_key
        else:
            case_key = self._get_case_key(his_id)

        if ins_type == '健保':
            medicine_set = 1
        else:
            medicine_set = self._get_self_medicine_set(case_key)

        data = [
            case_key,
            medicine_set,
            package,
            pres_days,
            instruction,
        ]
        self.database.insert_record('dosage', fields, data)

    def _get_self_medicine_set(self, case_key):
        sql = f'''
            SELECT MedicineSet FROM prescript
            WHERE
                CaseKey = {case_key}
            GROUP BY MedicineSet
            ORDER BY MedicineSet DESC
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            medicine_set = 2
        else:
            medicine_set = rows[0]['MedicineSet'] + 1

        return medicine_set

    def _cvt_prescript(self, his_id, case_date, ins_type, continuance, new_case_key=None):
        sql = f'''
            SELECT * FROM hisopdo
            WHERE
                HIS_ID = "{his_id}"
            ORDER BY HIS_SERNO
        '''
        rows = self.source_db.select_record(sql)

        fields = [
            'CaseKey', 'CaseDate', 'MedicineSet', 'MedicineType',
            'InsCode', 'MedicineName', 'DosageMode', 'Dosage',
            'Unit', 'Price', 'Amount',
        ]

        if new_case_key is not None:
            case_key = new_case_key
        else:
            case_key = self._get_case_key(his_id)

        if ins_type == '健保':
            medicine_set = 1
        else:
            medicine_set = self._get_self_medicine_set(case_key)

        for row in rows:
            medicine_type, medicine_name, ins_code, price = self._get_medicine(row['HIS_CODE'])
            if medicine_name is None:
                continue

            if '[部]' in medicine_name:
                continue

            if ins_type == '健保' and medicine_name in [
                    '針灸處理', '傷科處理', '中度複雜性針灸', '高度複雜性針灸',
                    '中度複雜性傷科', '高度複雜性傷科(多部位)', '高度複雜性傷科(脫臼)', '高度複雜性傷科(骨折)']:
                self._rewrite_cases(his_id, case_date, medicine_name, continuance)
                continue

            dosage = number_utils.get_float(row['HIS_NUM'])
            unit = self._get_unit(row['HIS_UNIT'])
            amount = dosage * price

            data = [
                case_key,
                case_date,
                medicine_set,
                medicine_type,
                ins_code,
                medicine_name,
                '日劑量',
                dosage,
                unit,
                price,
                amount
            ]
            self.database.insert_record('prescript', fields, data)

            self._set_treat_type(case_key, medicine_name)

    def _set_treat_type(self, case_key, medicine_name):
        if '兒童過敏性鼻炎' in medicine_name:
            field, treat_type = 'TreatType', '兒童鼻炎'
        elif '中醫慢性腎臟病門診加強照護' in medicine_name:
            field, treat_type = 'TreatType', '慢性腎病照護'
        elif '小兒氣喘' in medicine_name:
            field, treat_type = 'TreatType', '小兒氣喘'
        elif '小兒腦性麻痺' in medicine_name:
            field, treat_type = 'TreatType', '小兒腦性麻痺'
        elif '腦血管疾病' in medicine_name:
            field, treat_type = 'TreatType', '腦血管疾病'
        elif '電話問診' in medicine_name:
            field, treat_type = 'RegistType', '電話門診'
        elif '視訊問診' in medicine_name:
            field, treat_type = 'RegistType', '視訊門診'
        elif '長期臥床行動不便(代領' in medicine_name:
            field, treat_type = 'RegistType', '行動不便代領'
        elif '出海遠洋漁船作業(代領' in medicine_name:
            field, treat_type = 'RegistType', '遠洋漁船船員代領'
        elif '出海國際航線船舶作業(代領' in medicine_name:
            field, treat_type = 'RegistType', '國際航線船員代領'
        elif '保險人認定特殊情形(代領' in medicine_name:
            field, treat_type = 'RegistType', '特殊情形代領'
        elif '中醫助孕照護' in medicine_name:
            field, treat_type = 'TreatType', '助孕照護'
        elif '中醫保胎照護' in medicine_name:
            field, treat_type = 'TreatType', '保胎照護'
        elif '特定癌症門診加強照護' in medicine_name:
            field, treat_type = 'TreatType', '保胎照護'
        elif '居家醫療' in medicine_name:
            field, treat_type = 'TreatType', '居家醫療'
        else:
            return

        sql = f'''
            UPDATE cases
            SET
                {field} = "{treat_type}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

        if '中醫慢性腎臟病門診加強照護' in medicine_name:
            self._set_kidney(case_key)
        elif '腦血管疾病' in medicine_name:
            self._rewrite_cases_treatment(case_key, '一般針灸')

    def _set_kidney(self, case_key):
        self._rewrite_cases_treatment(case_key, '一般針灸')
        self._insert_ins_care(case_key, )

    def _rewrite_cases_treatment(self, case_key, treatment):
        sql = f'''
            UPDATE cases
            SET
                Treatment = "{treatment}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

    def _insert_ins_care(self, case_key, treat_code):
        sql = f'''
            SELECT * FROM charge_settings
            WHERE
                InsCode = "{treat_code}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        charge_row = rows[0]

        fields = [
            'MedicineSet', 'CaseKey', 'MecicineType', 'MedicineKey',
            'MedicineName', 'InsCode', 'Price', 'Dosage', 'Unit', 'Amount'
        ]
        data = [
            11,
            case_key,
            '照護',
            charge_row['ChargeSettingsKey'],
            string_utils.xstr(charge_row['ItemName']),
            treat_code,
            number_utils.get_integer(charge_row['Amount']),
            1,
            '次'
        ]
        self.database.insert_record('prescript', fields, data)

    def _rewrite_cases(self, case_key, case_date, treat_name, continuance):
        sql = f'''
            SELECT TreatType, RegistType FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            treat_type = string_utils.xstr(row['TreatType'])
            regist_type = string_utils.xstr(row['RegistType'])
            if treat_type in [
               '兒童鼻炎',
               '慢性腎病照護',
               '小兒氣喘',
               '小兒腦性麻痺',
               '腦血管疾病',
               '助孕照護',
               '保胎照護',
               '保胎照護',
               '居家醫療']:
                return

            if regist_type in [
               '電話門診'
               '視訊門診'
               '行動不便代領'
               '遠洋漁船船員代領'
               '國際航線船員代領'
               '特殊情形代領']:
                return

        treatment = None

        if treat_name == '針灸處理':
            treatment = '一般針灸'
        elif treat_name == '一般傷科':
            treatment = '傷科治療'
        elif treat_name in ['中度複雜性針灸', '高度複雜性針灸', '中度複雜性傷科']:
            treatment = treat_name
        elif '高度複雜性傷科' in treat_name:
            treatment = '高度複雜性傷科'

        treat_type = treatment

        if continuance is None:
            continuance = 1

        sql = f'''
            UPDATE cases
            SET
                TreatType = "{treat_type}",
                Treatment = "{treatment}",
                Continuance = {continuance}
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

    def _cvt_fees(self, his_id, ins_type, new_case_key):
        sql = f'''
            SELECT HIS_CODE, HIS_COST FROM hisopdc
            WHERE
                HIS_ID = "{his_id}"
        '''
        rows = self.source_db.select_record(sql)
        if len(rows) <= 0:
            return

        s_drug_fee = 0
        s_expensive_fee = 0
        s_acupuncture_fee = 0
        s_material_fee = 0

        fields = [
            'SDrugFee', 'SExpensiveFee', 'SAcupunctureFee', 'SMaterialFee',
            'SelfTotalFee', 'TotalFee', 'ReceiptFee',
        ]
        for row in rows:
            fee_code = row['HIS_CODE']
            fee = number_utils.get_integer(row['HIS_COST'])

            if fee_code == '2002':
                s_drug_fee += fee
            elif fee_code == '1020':
                s_expensive_fee += fee
            elif fee_code == '2003':
                s_acupuncture_fee += fee
            elif fee_code in ['2004', '2005', '2007']:
                s_material_fee += fee
            else:
                s_drug_fee += fee

        self_total_fee = s_drug_fee + s_expensive_fee + s_acupuncture_fee + s_material_fee

        data = [
            s_drug_fee,
            s_expensive_fee,
            s_acupuncture_fee,
            s_material_fee,
            self_total_fee,
            self_total_fee,
            self_total_fee,
        ]

        if new_case_key is not None:
            case_key = new_case_key
        else:
            case_key = his_id

        self.database.update_record('cases', fields, 'CaseKey', case_key, data)

    @staticmethod
    def _get_medicine_type(medicine_type_code):
        medicine_type = '複方'

        if medicine_type_code == '02':
            medicine_type = '複方'
        elif medicine_type_code == '03':
            medicine_type = '單方'
        elif medicine_type_code == '04':
            medicine_type = '水藥'
        elif medicine_type_code == '05':
            medicine_type = '處置'
        elif medicine_type_code == '08':
            medicine_type = '穴道'

        return medicine_type

    def _check_symptom_groups(self):
        dict_groups_type = '主訴類別'
        dict_groups_name = '國泰'
        sql = f'''
            SELECT DictGroupsKey FROM dict_groups
            WHERE
                DictGroupsType = "{dict_groups_type}" AND
                DictGroupsName = "{dict_groups_name}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return

        fields = [
            'DictGroupsType', 'DictGroupsName',
        ]
        data = [
            dict_groups_type,
            dict_groups_name,
        ]
        self.database.insert_record('dict_groups', fields, data)

    def _cvt_symptom(self):
        self.parent.ui.label_progress.setText('主訴詞庫檔轉檔')
        sql = '''
            SELECT * FROM allmenu
            WHERE
                ALM_TYPE = "07"
        '''
        rows = self.source_db.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        self._check_symptom_groups()
        fields = [
            'ClinicType', 'ClinicCode', 'InputCode', 'ClinicName', 'Groups',
        ]

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            clinic_code = string_utils.xstr(row['ALM_ID'])[-5:]
            clinic_name = row['ALM_NAME']
            groups_name = row['ALM_KIND1']
            sql = f'''
                SELECT ClinicKey FROM clinic
                WHERE
                    ClinicType = "主訴" AND
                    ClinicCode = "{clinic_code}" AND
                    ClinicName = "{clinic_name}" AND
                    Groups = "{groups_name}"
            '''
            clinic_rows = self.database.select_record(sql)
            if len(clinic_rows) > 0:
                self.database.delete_record('clinic', 'ClinicKey', clinic_rows[0]['ClinicKey'])

            input_code = string_utils.phonetic_to_str(string_utils.xstr(row['ALM_PHONE']))[:5]
            data = [
                '主訴',
                clinic_code,
                input_code,
                clinic_name,
                groups_name,
            ]
            self.database.insert_record('clinic', fields, data)

            self._insert_dict_groups(groups_name)

    def _insert_dict_groups(self, groups_name):
        dict_groups_type = '主訴'
        dict_groups_top_level = "國泰"
        sql = f'''
            SELECT DictGroupsName FROM dict_groups
            WHERE
                DictGroupsType = "{dict_groups_type}" AND
                DictGroupsTopLevel = "{dict_groups_top_level}" AND
                DictGroupsName = "{groups_name}"
        '''
        dict_groups_rows = self.database.select_record(sql)
        if len(dict_groups_rows) > 0:
            return

        fields = [
            'DictGroupsType', 'DictGroupsTopLevel', 'DictGroupsName',
        ]
        data = [
            dict_groups_type,
            dict_groups_top_level,
            groups_name,
        ]
        self.database.insert_record('dict_groups', fields, data)

    def _clear_medicine(self):
        self.database.exec_sql('TRUNCATE medicine')
        self.database.exec_sql('TRUNCATE refcompound')

    def _cvt_medicine(self):
        self._clear_medicine()

        self._cvt_medicine_type('複方')
        self._cvt_medicine_type('單方')
        self._cvt_medicine_type('水藥')
        self._cvt_medicine_type('穴道')
        self._cvt_medicine_type('其他')
        self._cvt_medicine_type('成方')
        self._cvt_medicine_expensive()
        self._cvt_medicine_massage()
        self._cvt_exam()

    def _cvt_medicine_type(self, medicine_type):
        medicine_type_code = '02'
        if medicine_type == '複方':
            medicine_type_code = '02'
        elif medicine_type == '單方':
            medicine_type_code = '03'
        elif medicine_type == '水藥':
            medicine_type_code = '04'
        elif medicine_type == '其他':
            medicine_type_code = '05'
        elif medicine_type == '穴道':
            medicine_type_code = '08'
        elif medicine_type == '成方':
            medicine_type_code = '09'

        self.parent.ui.label_progress.setText(f'{medicine_type}詞庫檔轉檔')

        sql = f'''
            SELECT * FROM allmenu
            WHERE
                ALM_TYPE = "{medicine_type_code}"
        '''
        rows = self.source_db.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        fields = [
            'MedicineType', 'MedicineMode', 'MedicineCode', 'InputCode', 'InsCode', 'MedicineName',
            'Unit', 'SalePrice', 'InPrice', 'Description',
        ]

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            location = string_utils.xstr(row['ALM_LOCATE']).strip()
            if medicine_type in ['單方', '複方'] and location == '':
                continue

            alm_id = row['ALM_ID']
            if '#' in alm_id:
                continue

            alm_name = string_utils.xstr(row['ALM_NAME'])
            if alm_name == '':
                continue

            input_code = string_utils.phonetic_to_str(string_utils.xstr(row['ALM_PHONE']))[:5]
            unit = self._get_unit(row['ALM_UNIT'])
            description = self._get_medicine_description(alm_id)

            data = [
                medicine_type,
                row['ALM_KIND2'],
                alm_id,
                input_code,
                row['ALM_LICNO'],
                alm_name,
                unit,
                number_utils.get_float(row['ALM_SELL']),
                row['ALM_COST'],
                description,
            ]
            compound_key = self.database.insert_record('medicine', fields, data)

            if medicine_type == '成方':
                self._convert_compound(compound_key, alm_id)

    def _convert_compound(self, compound_key, alm_id):
        sql = f'''
            SELECT * FROM allmenuw
            WHERE
                ALM_ID = "{alm_id}"
            ORDER BY ALM_SERIAL
        '''
        rows = self.source_db.select_record(sql)
        if len(rows) <= 0:
            return

        field = ['CompoundKey', 'MedicineKey', 'Quantity', 'Unit']
        for row in rows:
            medicine_code = string_utils.xstr(row['ALM_ID2'])
            if medicine_code == '':
                continue

            medicine_key, unit = self._get_medicine_key(medicine_code)
            if medicine_key is None:
                continue

            quantity = row['ALN_NUM']
            data = [compound_key, medicine_key, quantity, unit]
            try:
                self.database.insert_record('refcompound', field, data)
            except Exception:
                pass

    def _get_medicine_key(self, medicine_code):
        sql = f'''
            SELECT MedicineKey, Unit FROM medicine
            WHERE
                MedicineCode = "{medicine_code}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None, None

        row = rows[0]
        return row['MedicineKey'], string_utils.xstr(row['Unit'])

    def _get_medicine_description(self, alm_id):
        sql = f'''
            SELECT BOK_TEXT FROM bookchp
            WHERE
                BOK_CHPID = "{alm_id}"
        '''
        rows = self.source_db.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]
        description = string_utils.get_str(row['BOK_TEXT'], 'utf8')
        description = description.replace('rn', '\n')

        return description

    def _cvt_medicine_expensive(self):
        medicine_type_code = '05'
        medicine_type = '高貴'

        self.parent.ui.label_progress.setText(f'{medicine_type}詞庫檔轉檔')
        self.database.exec_sql(f'''
            DELETE FROM medicine
            WHERE
                MedicineType = "{medicine_type}"
        ''')

        sql = f'''
            SELECT * FROM allmenu
            WHERE
                ALM_TYPE = "{medicine_type_code}" AND
                ALM_NAME IS NOT NULL AND
                (ALM_KIND1 LIKE "%診所自費%")
        '''
        rows = self.source_db.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        fields = [
            'MedicineType', 'MedicineMode', 'MedicineCode', 'InputCode', 'InsCode', 'MedicineName',
            'Unit', 'SalePrice', 'InPrice'
        ]

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            input_code = string_utils.phonetic_to_str(string_utils.xstr(row['ALM_PHONE']))[:5]
            unit = self._get_unit(row['ALM_UNIT'])

            sale_price = row['ALM_SELL']
            if number_utils.get_float(sale_price) == 0.0:
                sale_price = row['ALM_COST']

            data = [
                medicine_type,
                row['ALM_KIND2'],
                row['ALM_ID'],
                input_code,
                row['ALM_LICNO'],
                row['ALM_NAME'],
                unit,
                sale_price,
                row['ALM_COST'],
            ]
            self.database.insert_record('medicine', fields, data)

    def _cvt_medicine_massage(self):
        medicine_type_code = '05'
        medicine_type = '處置'

        self.parent.ui.label_progress.setText(f'{medicine_type}詞庫檔轉檔')
        sql = f'''
            SELECT * FROM allmenu
            WHERE
                ALM_TYPE = "{medicine_type_code}" AND
                (ALM_KIND1 LIKE "%傷科處置%" OR
                 ALM_KIND1 LIKE "%理筋手法%")
        '''
        rows = self.source_db.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        fields = [
            'MedicineType', 'MedicineMode', 'MedicineCode', 'InputCode', 'InsCode', 'MedicineName',
            'Unit', 'SalePrice', 'InPrice'
        ]

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            input_code = string_utils.phonetic_to_str(string_utils.xstr(row['ALM_PHONE']))[:5]
            unit = self._get_unit(row['ALM_UNIT'])

            sale_price = row['ALM_SELL']
            if number_utils.get_float(sale_price) == 0.0:
                sale_price = row['ALM_COST']

            data = [
                medicine_type,
                row['ALM_KIND2'],
                row['ALM_ID'],
                input_code,
                row['ALM_LICNO'],
                row['ALM_NAME'],
                unit,
                sale_price,
                row['ALM_COST'],
            ]
            self.database.insert_record('medicine', fields, data)

    def _cvt_disease(self):
        self.parent.ui.label_progress.setText('病名詞庫檔轉檔')

        sql = 'SELECT * FROM icd10 ORDER BY ICDCode'
        rows = self.database.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            icd_code = string_utils.xstr(row['ICDCode'])
            sql = f'''
                SELECT ALM_SPCURE, ALM_PHONE from allmenu
                WHERE
                    ALM_TYPE = "01" AND
                    ALM_ICD9 = "{icd_code}"
            '''
            all_menu_rows = self.source_db.select_record(sql)
            if len(all_menu_rows) <= 0:
                continue

            all_menu_row = all_menu_rows[0]
            input_code = string_utils.phonetic_to_str(string_utils.xstr(all_menu_row['ALM_PHONE']))[:5]
            try:
                special_code = all_menu_row['ALM_SPCURE'][:2]
            except Exception:
                special_code = None

            if special_code is None:
                sql = f'''
                    UPDATE icd10
                    SET
                        InputCode = "{input_code}"
                    WHERE
                        ICDCode = "{icd_code}"
                '''
            else:
                sql = f'''
                    UPDATE icd10
                    SET
                        InputCode = "{input_code}",
                        SpecialCode = "{special_code}"
                    WHERE
                        ICDCode = "{icd_code}"
                '''
            self.database.exec_sql(sql)

    def _cvt_users(self):
        self.parent.ui.label_progress.setText('使用者資料轉檔')

        sql = '''
            SELECT users.* FROM users
            ORDER BY USR_ID
        '''
        rows = self.source_db.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        sql = 'TRUNCATE person'
        self.database.exec_sql(sql)

        fields = [
            'Name', 'Birthday', 'ID', 'Gender', 'Address',
            'Telephone', 'Cellphone', 'Email', 'Fulltime',
        ]
        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            try:
                birthday = date_utils.date_to_west_date.xstr(row['USR_BDAY'])
            except Exception:
                birthday = None

            if row['USR_SEX'] == '2':
                gender = '女'
            elif row['USR_SEX'] == '1':
                gender = '男'
            else:
                gender = None

            if row['USR_PARTTIME'] == '2':
                parttime = '兼職'
            elif row['USR_PARTTIME'] == '1':
                parttime = '全職'
            else:
                parttime = None

            data = [
                row['USR_NAME'],
                birthday,
                row['USR_BNO'],
                gender,
                row['USR_ADDR'],
                row['USR_TEL'],
                row['USR_MOB'],
                row['USR_EMAIL'],
                parttime,
            ]

            self.database.insert_record('person', fields, data)

    def _cvt_exam(self):
        self.database.exec_sql('DELETE FROM medicine WHERE MedicineType = "檢驗"')

        self.parent.ui.label_progress.setText(f'檢驗詞庫檔轉檔')

        sql = f'''
            SELECT * FROM allmenu
            WHERE
                ALM_TYPE = "05" AND
                ALM_ID BETWEEN "E20000" AND "E20999"
            ORDER BY ALM_ID
        '''
        rows = self.source_db.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        fields = [
            'MedicineType', 'MedicineMode', 'MedicineCode', 'InputCode', 'InsCode', 'MedicineName',
            'Unit', 'SalePrice', 'InPrice', 'Description',
        ]

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            alm_id = row['ALM_ID']
            if '#' in alm_id:
                continue

            alm_name = string_utils.xstr(row['ALM_NAME'])
            if alm_name == '':
                continue

            input_code = string_utils.phonetic_to_str(string_utils.xstr(row['ALM_PHONE']))[:5]
            unit = self._get_unit(row['ALM_UNIT'])
            description = self._get_medicine_description(alm_id)

            data = [
                '檢驗',
                row['ALM_KIND2'],
                alm_id,
                input_code,
                row['ALM_LICNO'],
                alm_name,
                unit,
                number_utils.get_float(row['ALM_SELL']),
                row['ALM_COST'],
                description,
            ]
            self.database.insert_record('medicine', fields, data)

    def _cvt_nr(self, table_name, primary_key, field):
        sql = f'SELECT {primary_key}, {field} FROM {table_name} WHERE {field} LIKE "%rn%"'
        rows = self.database.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        for row in rows:
            key_value = row[primary_key]
            field_value = string_utils.get_str(row[field], 'utf8')
            new_field_value = field_value.replace('rn', '\r\n')
            self.database.exec_sql(
                f'UPDATE {table_name} SET {field} = "{new_field_value}" WHERE {primary_key} = {key_value}'
            )
