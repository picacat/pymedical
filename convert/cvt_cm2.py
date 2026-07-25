
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


# 中醫智庫轉檔 2025.01.02
class CvtCM2():
    def __init__(self, parent, *args):
        self.parent = parent
        self.product_type = parent.ui.comboBox_utec_product.currentText()
        self.database = parent.database
        self.source_db = parent.source_db
        self.progress_bar = parent.ui.progressBar

        self.conn = pyodbc.connect(f'DSN={self.parent.lineEdit_dsn_cm2.text()};UID="";PWD=""')
        self.cursor = self.conn.cursor()

    def disconnect_db(self):
        self.cursor.close()
        self.conn.close()

    # 開始轉檔
    def convert(self):
        if self.parent.ui.label_connection_status_tm == '未連線':
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('尚未開啟連線')
            msg_box.setText("<font size='4' color='Red'><b>尚未執行連線測試, 請執行連線測試後再執行轉檔作業.</b></font>")
            msg_box.setInformativeText("連線尚未開啟, 無法執行轉檔作業.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        if self.parent.ui.checkBox_medicine_cm2.isChecked():
            self._cvt_medicine()
        if self.parent.ui.checkBox_compound_cm2.isChecked():
            self._cvt_compound()
        if self.parent.ui.checkBox_patient_cm2.isChecked():
            self._cvt_patient()
        if self.parent.ui.checkBox_medical_record_cm2.isChecked():
            self._cvt_medical_record()
        if self.parent.ui.checkBox_symptom_cm2.isChecked():
            self._cvt_symptom()

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
    def _get_share_code(share_code):
        share_code = share_code.strip()
        share = '基層醫療'

        if share_code == '003':
            share = '低收入戶'
        elif share_code == '004':
            share = '榮民'

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

    def _get_patient_row(self, patient_key):
        sql = f'''
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return rows[0]
        else:
            return None

    def _get_field_value(self, field_value):
        if field_value is not None:
            result = string_utils.xstr(field_value).strip()
        else:
            result = None

        if result == '':
            result = None

        return result

    def _cvt_patient(self):
        self.database.exec_sql('TRUNCATE patient')

        self.parent.ui.label_progress.setText('病患基本資料檔轉檔')
        sql = """
            SELECT * FROM [中醫門診].[dbo].[患者基本資料]
            ORDER BY 病歷號碼
        """
        rows = self._exec_sql(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        sql = 'TRUNCATE patient'
        self.database.exec_sql(sql)

        fields = [
            'PatientKey', 'Name', 'Birthday', 'ID',
            'Telephone', 'InitDate', 'InsType',
            'Gender', 'Address', 'Nationality',
            'History',
        ]

        for row in rows:
            patient_key =  number_utils.get_integer(row['病歷號碼'])
            if patient_key == 0:
                continue

            self.progress_bar.setValue(self.progress_bar.value() + 1)

            name = self._get_field_value(row['姓名'])
            telephone = self._get_field_value(row['電話'])
            address = self._get_field_value(row['住址'])
            history = self._get_field_value(row['病史'])
            birthday = self._get_field_value(row['出生日期'])

            try:
                init_date = self._get_field_value(row['初診日期'])
            except Exception:
                init_date = None

            ins_type = self._get_share_code(string_utils.xstr(row['負擔代號']))
            gender = self._get_field_value(row['性別'])
            if gender == '1':
                gender = '男'
            elif gender == '2':
                gender = '女'

            try:
                patient_id = self._get_field_value(row['身份證號']).strip()
            except Exception:
                patient_id = None

            nationality = '本國'
            if patient_id is not None and len(patient_id) > 1:
                nationality = patient_utils.get_nationality(patient_id[1])
                if gender == '':
                    if patient_id[1] == '1':
                        gender = '男'
                    elif patient_id[1] == '2':
                        gender = '女'

            data = [
                patient_key,
                name,
                birthday,
                string_utils.xstr(patient_id)[:10],
                string_utils.xstr(telephone)[:15],
                init_date,
                ins_type,
                gender,
                address,
                nationality,
                history,
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
        start_date = self.parent.ui.lineEdit_start_date_cm2.text()
        end_date = self.parent.ui.lineEdit_end_date_cm2.text()
        self.parent.ui.label_progress.setText('病歷資料檔轉檔')

        sql = f"""
            SELECT * FROM [中醫門診].[dbo].[門診]
            WHERE
                [就醫日期] BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
            ORDER BY [就醫日期]
        """

        rows = self._exec_sql(sql)
        self._truncate_medical_record(start_date, end_date)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            medical_record_row = {}
            self._convert_registration(row, medical_record_row)
            self._convert_type(row, medical_record_row)
            self._convert_diag(row, medical_record_row)
            case_key = self._insert_medical_record(medical_record_row)

            if string_utils.xstr(medical_record_row['InsType']) == '健保':
                medicine_set = 1
            else:
                medicine_set = 2

            self._convert_prescript(case_key, medicine_set, row)
            self._convert_dosage(case_key, medicine_set, row)
            self._convert_treat_type(case_key)
            # self._convert_fees(case_key, row)

        self.progress_bar.setValue(len(rows))

    def _convert_registration(self, row, medical_record_row):
        case_date = row['就醫日期']
        medical_record_row['CaseDate'] = case_date
        medical_record_row['Room'] = 1
        medical_record_row['PatientKey'] = number_utils.get_integer(row['病歷號碼'])
        medical_record_row['Name'] = None
        medical_record_row['Share'] = None

        patient_row = self._get_patient_row(medical_record_row['PatientKey'])
        if patient_row is not None:
            medical_record_row['Name'] = string_utils.xstr(patient_row['Name'])
            medical_record_row['Share'] = string_utils.xstr(patient_row['InsType'])

        try:
            if row['保險類別'] == '1':
                medical_record_row['InsType'] =  '健保'
            else:
                medical_record_row['InsType'] =  '自費'
        except Exception:
            medical_record_row['InsType'] = '健保'

        medical_record_row['Injury'] = '普通疾病'

        medical_record_row['Period'] = '午班'
        try:
            medical_record_row['Card'] = self._get_field_value(row['健保卡號'])[:4]
        except Exception:
            medical_record_row['Card'] = None

        try:
            medical_record_row['Continuance'] = self._get_field_value(row['健保卡號'])[4]
        except Exception:
            medical_record_row['Continuance'] = None

    def _convert_type(self, row, medical_record_row):
        medical_record_row['RegistType'] = '一般門診'
        medical_record_row['ApplyType'] = '申報'

    def _convert_diag(self, row, medical_record_row):
        medical_record_row['DiseaseCode1'] = self._get_field_value(row['主病ICD10'])
        medical_record_row['DiseaseCode2'] = self._get_field_value(row['次病ICD10'])
        medical_record_row['DiseaseName1'] = None
        medical_record_row['DiseaseName2'] = None
        if string_utils.xstr(medical_record_row['DiseaseCode1']) != '':
            medical_record_row['DiseaseName1'] = self._get_disease_name(medical_record_row['DiseaseCode1'])
        if string_utils.xstr(medical_record_row['DiseaseCode2']) != '':
            medical_record_row['DiseaseName2'] = self._get_disease_name(medical_record_row['DiseaseCode2'])

        medical_record_row['Symptom'] = self._get_field_value(row['主訴'])

    def _get_disease_name(self, icd_code):
        sql = f'''
            SELECT ChineseName FROM icd10
            WHERE
                ICDCode = "{icd_code}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]
        disease_name = string_utils.xstr(row['ChineseName'])

        return disease_name

    def _insert_medical_record(self, row):
        fields = [
            'CaseDate', 'Room', 'PatientKey', 'Name', 'InsType',
            'DoctorDate', 'ChargeDate', 'ChargePeriod',
            'Share', 'Injury', 'Period', 'Card', 'Continuance',
            'DoctorDone', 'ChargeDone', 'DrugDone',
            'DiseaseCode1', 'DiseaseName1',
            'DiseaseCode2', 'DiseaseName2',
            'Symptom',
            'RegistType', 'ApplyType',
        ]
        data = [
            row['CaseDate'], row['Room'], row['PatientKey'], row['Name'], row['InsType'],
            row['CaseDate'], row['CaseDate'], row['Period'],
            row['Share'], row['Injury'], row['Period'], row['Card'], row['Continuance'],
            'True', 'True', 'True',
            row['DiseaseCode1'], row['DiseaseName1'],
            row['DiseaseCode2'], row['DiseaseName2'],
            row['Symptom'],
            row['RegistType'], row['ApplyType'],
        ]
        case_key = self.database.insert_record('cases', fields, data)

        return case_key

    def _get_medicine_type(self, code):
        code = code[0]
        medicine_type_dict = {
            'A': '複方',
            'B': '單方',
            'C': '穴道',
            'D': '處置',
            'E': '高貴',
            'F': '水藥',
        }

        try:
            medicine_type = medicine_type_dict[code]
        except Exception:
            medicine_type = '單方'

        return medicine_type

    def _get_medicine_row(self, code):
        sql = f"""
            SELECT * FROM [中醫門診].[dbo].[總處方]
            WHERE
                [系統代碼] = '{code}'
        """
        rows = self._exec_sql(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]

        return row

    def _convert_prescript(self, case_key, medicine_set, row):
        patient_key = string_utils.xstr(row['病歷號碼']).strip()
        case_date = row['就醫日期']

        sql = f"""
            SELECT * FROM [中醫門診].[dbo].[門診處方]
            WHERE
                [就醫日期] = '{case_date}' AND
                [病歷號碼] = '{patient_key}'
            ORDER BY [序號]
        """
        rows = self._exec_sql(sql)

        fields = [
            'CaseKey', 'CaseDate', 'MedicineType', 'MedicineSet',
            'MedicineName', 'Unit', 'DosageMode', 'Dosage', 'InsCode',
        ]

        for row in rows:
            medicine_row = self._get_medicine_row(row['系統代碼'])
            if medicine_row is None:
                continue

            try:
                dosage = number_utils.get_float(row['劑量'])
            except Exception:
                dosage = None

            medicine_name = self._get_field_value(medicine_row['名稱'])
            ins_code = self._get_field_value(medicine_row['藥品代碼'])
            medicine_type = self._get_medicine_type(self._get_field_value(row['系統代碼']))

            data = [
                case_key,
                case_date,
                medicine_type,
                medicine_set,
                medicine_name,
                self._get_field_value(row['單位']),
                '日劑量',
                dosage,
                ins_code,
            ]
            self.database.insert_record('prescript', fields, data)

            if '針灸' in medicine_name:
                self._update_cases(case_key, 'Treatment', '一般針灸')
            elif '傷科' in medicine_name:
                self._update_cases(case_key, 'Treatment', '一般傷科')

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
            SELECT TreatType, Treatment, Continuance FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        case_row = self.database.select_record(sql)[0]

        treat_type = string_utils.xstr(case_row['TreatType'])
        if treat_type in nhi_utils.CARE_TREAT + nhi_utils.HOME_CARE:
            return

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
        diag_id = self._get_field_value(dm_row['Diag_ID'])
        if diag_id is None:
            return

        year = string_utils.xstr(dm_row['Reg_Date']).split('/')[0]
        fee_table_name = f'cty{year:0>3}'
        sql = f"""
            SELECT * FROM {fee_table_name}
            WHERE
                Diag_ID = '{diag_id}'
        """
        rows = self._exec_sql(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        
        regist_fee = number_utils.get_integer(row['Reg_Ins'])
        diag_fee = number_utils.get_integer(row['Exam_Ins'])
        inter_drug_fee = number_utils.get_integer(row['Med_Ins'])
        pharmacy_fee = number_utils.get_integer(row['Med_Mix_Ins'])
        acupuncture_fee = number_utils.get_integer(row['Acup_Ins'])
        massage_fee = number_utils.get_integer(row['Massage_Ins'])
        diag_share_fee = number_utils.get_integer(row['Reg_Ins_Part'])
        drug_share_fee = number_utils.get_integer(row['Med_Ins_Part'])
        ins_total_fee = number_utils.get_integer(row['Ins_Total'])
        ins_apply_fee = number_utils.get_integer(row['Ins_Request_Total'])
        s_diag_fee = number_utils.get_integer(row['Exam_Self'])
        s_drug_fee = number_utils.get_integer(row['Inn_Med_Self']) + number_utils.get_integer(row['Heal_Med_Self'])
        s_herb_fee = number_utils.get_integer(row['Drink_Med_Self'])
        s_massage_fee = number_utils.get_integer(row['Massage_Self'])
        s_material_fee = number_utils.get_integer(row['Material_Self']) + number_utils.get_integer(row['Other_Self'])
        discount_fee = number_utils.get_integer(row['Self_Discount'])
        self_total_fee = number_utils.get_integer(row['Self_Total'])

        if pharmacy_fee > 0:
            pharmacy_type = '申報'
        else:
            pharmacy_type = '不申報'

        fields = [
            'RegistFee', 'DiagFee', 'InterDrugFee',
            'PharmacyFee', 'PharmacyType',
            'AcupunctureFee', 'MassageFee',
            'DiagShareFee', 'DrugShareFee',
            'SDiagShareFee', 'SDrugShareFee',
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

    def _convert_dosage(self, case_key, medicine_set, row):
        instruction = string_utils.xstr(row['服藥時間']).strip()
        if instruction == '1':
            instruction = '飯前'
        elif instruction == '2':
            instruction = '飯後'
        elif instruction == '3':
            instruction = '睡前'
        else:
            instruction = None

        fields = [
            'CaseKey', 'MedicineSet',
            'Packages', 'Days', 'Instruction',
        ]
        data = [
            case_key, medicine_set,
            self._get_field_value(row['保險藥包']),
            self._get_field_value(row['保險藥天']),
            instruction,
        ]

        self.database.insert_record('dosage', fields, data)

    def _truncate_medical_record(self, start_date, end_date):
        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                DATE(CaseDate) BETWEEN "{start_date}" AND "{end_date}"
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
            SELECT * FROM drug_db
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
            unit = self._get_field_value(row['Unit_Name'])
            dosage = None
            location = self._get_field_value(row['Store_Code'])

            sale_price = number_utils.get_float(row['Diag_Price'])
            sale_price = round(sale_price, 2)
            in_price = number_utils.get_float(row['Purchase_Price'])
            in_price = round(in_price, 2)
            safe_quantity = None
            description = row['Drug_Memo']
            try:
                input_code = input_code[:5]
            except Exception:
                input_code = None
            try:
                medicine_name = medicine_name[:40]
            except Exception:
                medicine_name = None

            data = [
                medicine_type,
                medicine_mode,
                medicine_code,
                input_code,
                ins_code,
                medicine_name,
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

    def _get_pres_set_link_rows(self, drug_id):
        sql = f"""
            SELECT * FROM Pres_Set_Link
            WHERE
                PS_ID = '{drug_id}'
            ORDER BY PSL_ID
        """
        rows = self._exec_sql(sql)
        if len(rows) <= 0:
            return None

        return rows

    def _cvt_compound_title(self):
        sql = """
            SELECT * FROM Pres_Set
            WHERE
                User_ID != '@' AND
                Type_Flag = '0'
            ORDER BY PS_Code
        """
        rows = self._exec_sql(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        sql = 'DELETE FROM medicine WHERE MedicineType = "成方"'
        self.database.exec_sql(sql)

        fields = [
            'MedicineType', 'MedicineCode', 'MedicineMode', 'InputCode', 'MedicineName', 'Unit'
        ]

        for row in rows:
            medicine_type = '成方'
            drug_id = string_utils.xstr(row['PS_Id'])
            medicine_code = string_utils.xstr(row['PS_Code'])
            input_code = string_utils.xstr(row['ZY_Code'])[:5]
            medicine_name = string_utils.xstr(row['PSName'])
            unit = None

            data = [
                medicine_type,
                medicine_code,
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
            pres_set_link_rows = self._get_pres_set_link_rows(drug_id)
            if pres_set_link_rows is None:
                continue

            compound_key = row['MedicineKey']
            for ps_link_row in pres_set_link_rows:
                medicine_row = self._get_medicine_row(self._get_field_value(ps_link_row['drug_Id']))
                if medicine_row is None:
                    continue

                medicine_key = medicine_row['MedicineKey']
                unit = medicine_row['Unit']
                try:
                    quantity = number_utils.get_float(ps_link_row['Quantity'])
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
            'Password',
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
            password = self._get_field_value(row['upwd'])
            try:
                password = self._translate_pwd(password)
            except Exception:
                pass

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
                password,
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

    def _exec_sql(self, sql):
        self.cursor.execute(sql)
        columns = [column[0] for column in self.cursor.description]
        rows = []
        results = self.cursor.fetchall()
        for row in results:
            rows.append(dict(zip(columns, row)))

        return rows

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
