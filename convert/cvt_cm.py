
from PyQt5.QtWidgets import QMessageBox, QPushButton
from libs import string_utils
from libs import patient_utils
from libs import number_utils
from libs import case_utils
from libs import nhi_utils


# 精典轉檔 2023.02.16
class CvtCM():
    def __init__(self, parent, *args):
        self.parent = parent
        self.product_type = parent.ui.comboBox_utec_product.currentText()
        self.database = parent.database
        self.source_db = parent.source_db
        self.progress_bar = parent.ui.progressBar

    # 開始轉檔
    def convert(self):
        if self.parent.ui.label_connection_status_cm == '未連線':
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('尚未開啟連線')
            msg_box.setText("<font size='4' color='Red'><b>尚未執行連線測試, 請執行連線測試後再執行轉檔作業.</b></font>")
            msg_box.setInformativeText("連線尚未開啟, 無法執行轉檔作業.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        self._set_person_dict()

        if self.parent.ui.checkBox_medicine_cm.isChecked():
            self._cvt_medicine()
        if self.parent.ui.checkBox_compound_cm.isChecked():
            self._cvt_compound()
        if self.parent.ui.checkBox_user_cm.isChecked():
            self._cvt_user()
        if self.parent.ui.checkBox_patient_cm.isChecked():
            self._cvt_patient()
        if self.parent.ui.checkBox_medical_record_cm.isChecked():
            self._cvt_medical_record()
        if self.parent.ui.checkBox_symptom_cm.isChecked():
            self._cvt_symptom()
        if self.parent.ui.checkBox_disease_cm.isChecked():
            self._cvt_disease()

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle('轉檔完成')
        msg_box.setText("<font size='4' color='Blue'><b>恭喜！轉檔完成!</b></font>")
        msg_box.setInformativeText("請繼續轉檔作業.")
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

    def _set_person_dict(self):
        sql = """
            SELECT * FROM employee
            ORDER BY EmployeeNo
        """
        rows = self.source_db.select_record(sql)

        self.person_dict = dict()

        for row in rows:
            self.person_dict[row['EmployeeID']] = row['EmployeeName']

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

        if share_type == '低收入戶':
            share = '低收入戶'
        elif share_type == '榮民遺眷家戶':
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

    def _get_field_value(self, field_value):
        if field_value is not None:
            result = string_utils.xstr(field_value)
        else:
            result = None

        if result == '':
            result = None

        return result

    def _cvt_patient(self):
        self.parent.ui.label_progress.setText('病患基本資料檔轉檔')
        sql = """
            SELECT * FROM patient
            ORDER BY PatientNo
        """
        rows = self.source_db.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        sql = 'TRUNCATE patient'
        self.database.exec_sql(sql)
        fields = [
            'PatientKey', 'Name', 'Birthday', 'ID',
            'Telephone', 'Cellphone', 'InitDate', 'InsType',
            'Gender', 'Address', 'Nationality', 'Remark',
            'ZipCode',
        ]

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            patient_key = self._get_field_value(row['PatientNo'])
            name = self._get_field_value(row['Name'])
            telephone = self._get_field_value(row['Phone'])
            cellphone = self._get_field_value(row['Mobile'])
            address = self._get_field_value(row['Address'])
            zip_code = self._get_field_value(row['AddressCode'])
            remark = self._get_field_value(row['Nidus1'])
            birthday = row['Birthday']
            init_date = row['FirstDate']

            ins_type = self._get_share(string_utils.xstr(row['BurdenCode']))

            try:
                patient_id = self._get_field_value(row['ID']).strip()
            except Exception:
                patient_id = None

            gender = self._get_field_value(row['Gender'])
            if gender == '1':
                gender = '男'
            elif gender == '2':
                gender = '女'

            nationality = '本國'
            if patient_id is not None and len(patient_id) > 1:
                nationality = patient_utils.get_nationality(patient_id[1])
                if gender in [None, '']:
                    if patient_id[1] == '1':
                        gender = '男'
                    elif patient_id[1] == '2':
                        gender = '女'

            data = [
                patient_key,
                name,
                birthday,
                patient_id,
                telephone,
                cellphone,
                init_date,
                ins_type,
                gender,
                address,
                nationality,
                remark,
                zip_code,
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
        self.parent.ui.label_progress.setText('病歷資料檔轉檔')

        start_date = self.parent.ui.lineEdit_start_date_cm.text()
        end_date = self.parent.ui.lineEdit_end_date_cm.text()

        self.parent.ui.label_progress.setText('病歷資料檔')

        sql = f"""
            SELECT history.*, register.Room FROM history
                LEFT JOIN register ON register.RegisterID = history.RegisterID
            WHERE
                history.RegisterDate BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY HistoryID
        """
        try:
            rows = self.source_db.select_record(sql)
        except Exception:
            return

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
            self._convert_prescript(case_key, medical_record_row['InsType'], medical_record_row['CaseDate'], row)
            self._convert_dosage(case_key, medical_record_row, row)
            self._convert_treat_type(case_key, medical_record_row)
            self._convert_fees(case_key, medical_record_row, row)

    def _convert_registration(self, row, medical_record_row):
        ins_type_dict = {
            '0': '自費',
            '1': '健保',
            'Y': '健保',
        }
        period_dict = {
            '1': '早班',
            '2': '午班',
            '3': '晚班',
        }

        medical_record_row['CaseDate'] = row['RegisterDate']
        medical_record_row['RegistNo'] = row['RegisterNo']
        try:
            medical_record_row['Room'] = row['Room']
        except Exception:
            medical_record_row['Room'] = 1

        if medical_record_row['Room'] in ['', None]:
            medical_record_row['Room'] = 1

        medical_record_row['PatientKey'] = row['PatientNo']
        medical_record_row['Name'] = self._get_field_value(row['Name'])
        try:
            medical_record_row['InsType'] = ins_type_dict[row['RegisterType']]
        except Exception:
            medical_record_row['InsType'] = '健保'

        medical_record_row['Injury'] = '普通疾病'
        medical_record_row['Share'] = '基層醫療'

        if row['BurdenCode'] == 'S10':
            medical_record_row['Share'] = '基層醫療'
        elif row['BurdenCode'] == '003':
            medical_record_row['Share'] = '低收入戶'
        elif row['BurdenCode'] == '004':
            medical_record_row['Share'] = '榮民'
        elif row['BurdenCode'] == '006':
            medical_record_row['Share'] = '職業傷害'
            medical_record_row['Injury'] = '職業傷害'
        elif row['BurdenCode'] == '902':
            medical_record_row['Share'] = '三歲兒童'
        elif row['BurdenCode'] == '906':
            medical_record_row['Share'] = '替代役男'
        elif row['BurdenCode'] == '914':
            medical_record_row['Share'] = '法定傳染病通報隔離'
            medical_record_row['Injury'] = '法定傳染病通報隔離'

        try:
            medical_record_row['Period'] = period_dict[row['Section']]
        except Exception:
            medical_record_row['Period'] = '早班'

        try:
            visit = self._get_visit(medical_record_row)
        except Exception:
            visit = '複診'

        medical_record_row['Visit'] = visit
        medical_record_row['Card'] = self._get_field_value(row['ICCard'])
        medical_record_row['Continuance'] = number_utils.get_integer(row['ICCardSerialNo'])
        if medical_record_row['InsType'] == '自費':
            medical_record_row['Continuance'] = None

        if row['ExceptionCode'] not in ['', None]:
            medical_record_row['Card'] = self._get_field_value(row['ExceptionCode'])

        try:
            medical_record_row['Doctor'] = self.person_dict[row['DoctorID']]
        except Exception:
            medical_record_row['Doctor'] = None

        try:
            medical_record_row['Massager'] = self.person_dict[row['AssistantID']]
        except Exception:
            medical_record_row['Massager'] = None

        try:
            medical_record_row['Register'] = self.person_dict[row['OrderID']]
        except Exception:
            medical_record_row['Register'] = None

        # medical_record_row['Cashier'] = self._get_field_value(row['Chg_Name'])
        # medical_record_row['Massager'] = self._get_field_value(row['Massage_Name'])

    def _get_visit(self, medical_record_row):
        visit = '複診'

        sql = f'''
            SELECT InitDate FROM patient
            WHERE
                PatientKey = {medical_record_row['PatientKey']}
        '''
        try:
            rows = self.database.select_record(sql)
        except Exception:
            return visit

        if len(rows) <= 0:
            return visit

        row = rows[0]
        if medical_record_row['CaseDate'] == row['InitDate'].date():
            visit = '初診'

        return visit

    def _convert_type(self, row, medical_record_row):
        medical_record_row['RegistType'] = '一般門診'
        medical_record_row['ApplyType'] = '申報'

    def _convert_diag(self, row, medical_record_row):
        medical_record_row['Symptom'] = row['Symptom']
        medical_record_row['Tongue'] = row['TongueEvent']
        medical_record_row['Pulse'] = row['Pulsation']
        medical_record_row['DiseaseCode1'] = row['DiseaseCode1']
        medical_record_row['DiseaseName1'] = case_utils.get_disease_name(self.database, row['DiseaseCode1'])
        medical_record_row['DiseaseCode2'] = row['DiseaseCode2']
        medical_record_row['DiseaseName2'] = case_utils.get_disease_name(self.database, row['DiseaseCode2'])
        medical_record_row['DiseaseCode3'] = row['DiseaseCode3']
        medical_record_row['DiseaseName3'] = case_utils.get_disease_name(self.database, row['DiseaseCode3'])
        medical_record_row['Distincts'] = row['DiseaseIdentify']
        medical_record_row['Cure'] = row['TreatIdentify']

    def _insert_medical_record(self, row):
        fields = [
            'CaseDate', 'RegistNo', 'PatientKey', 'Name', 'InsType', 'Visit',
            'Period', 'Card', 'Continuance', 'Room', 'Share', 'Injury',
            'RegistType', 'ApplyType',
            'Doctor', 'Massager', 'Register',
            'DoctorDate', 'ChargeDate', 'ChargePeriod',
            'DoctorDone', 'ChargeDone', 'DrugDone',
            'Symptom', 'Tongue', 'Pulse',
            'DiseaseCode1', 'DiseaseName1',
            'DiseaseCode2', 'DiseaseName2',
            'DiseaseCode3', 'DiseaseName3',
            # 'SpecialCode',
            # 'RegistType', 'ApplyType', 'Treatment',
        ]
        try:
            room = number_utils.get_integer(row['Room'])
        except Exception:
            room = 1

        data = [
            row['CaseDate'], row['RegistNo'], row['PatientKey'], row['Name'], row['InsType'], row['Visit'],
            row['Period'], row['Card'], row['Continuance'], room, row['Share'], row['Injury'],
            row['RegistType'], row['ApplyType'],
            row['Doctor'], row['Massager'], row['Register'],
            row['CaseDate'], row['CaseDate'], row['Period'],
            'True', 'True', 'True',
            row['Symptom'], row['Tongue'], row['Pulse'],
            row['DiseaseCode1'], row['DiseaseName1'],
            row['DiseaseCode2'], row['DiseaseName2'],
            row['DiseaseCode3'], row['DiseaseName3'],
            # row['SpecialCode'],
            # row['RegistType'], row['ApplyType'], row['Treatment'],
        ]
        case_key = self.database.insert_record('cases', fields, data)

        return case_key

    def _get_medicine_type(self, code):
        medicine_type_dict = {
            '10': '複方',
            '20': '水藥',
            '21': '高貴',
            '31': '穴道',
            '32': '處置',
        }

        try:
            medicine_type = medicine_type_dict[code]
        except Exception:
            medicine_type = None

        return medicine_type

    def _get_medicine_row(self, medicine_code):
        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineCode = "{medicine_code}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return rows[0]

    def _convert_prescript(self, case_key, ins_type, case_date, row):
        sql = f"""
            SELECT * FROM treat
            WHERE
                PatientNo = '{row['PatientNo']}' AND
                RegisterDate = '{row['RegisterDate']}'
            ORDER BY TreatID
        """
        treat_rows = self.source_db.select_record(sql)

        fields = [
            'CaseKey', 'CaseDate', 'MedicineSet',
            'MedicineType', 'MedicineKey', 'InsCode',
            'MedicineName', 'Unit', 'DosageMode', 'Dosage',
            'Price', 'Amount',
        ]
        treatment = None
        for treat_row in treat_rows:
            medicine_row = self._get_medicine_row(treat_row['DrugNo'])
            if medicine_row is None:
                continue

            medicine_key = medicine_row['MedicineKey']
            medicine_type = medicine_row['MedicineType']
            medicine_name = medicine_row['MedicineName']
            medicine_set = 1
            if ins_type != '健保':
                medicine_set = 2
            ins_code = medicine_row['InsCode']
            unit = medicine_row['Unit']
            dosage = f'{treat_row["Quantity"]:.1f}'
            price = number_utils.get_integer(treat_row['Price'])
            amount = number_utils.get_float(dosage) * price

            if medicine_type == '穴道':
                treatment = '一般針灸'
            elif medicine_type == '處置':
                treatment = '一般傷科'

            data = [
                case_key,
                case_date,
                medicine_set,
                medicine_type,
                medicine_key,
                ins_code,
                medicine_name,
                unit,
                '日劑量',
                dosage,
                price,
                amount,
            ]
            self.database.insert_record('prescript', fields, data)

        if treatment is not None:
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
    def _convert_treat_type(self, case_key, medical_record_row):
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

        medical_record_row['TreatType'] = treat_type
        self._update_cases(case_key, 'TreatType', treat_type)

    def _convert_fees(self, case_key, medical_record_row, row):
        regist_fee = number_utils.get_integer(row['RegisterFee'])
        if medical_record_row['InsType'] == '健保':
            diag_fee = number_utils.get_integer(row['DiagnosisFee'])
            inter_drug_fee = number_utils.get_integer(row['DrugFee'])
            pharmacy_fee = number_utils.get_integer(row['DrugServiceFee'])

            treat_fee = number_utils.get_integer(row['TreatFee'])
            acupuncture_fee = 0
            massage_fee = 0
            if medical_record_row['TreatType'] == '一般針灸':
                acupuncture_fee = treat_fee
            elif medical_record_row['TreatType'] == '一般傷科':
                massage_fee = treat_fee

            diag_share_fee = number_utils.get_integer(row['NHIPartFee'])
            drug_share_fee = number_utils.get_integer(row['NHIDrugPartFee'])
            ins_total_fee = number_utils.get_integer(row['Total'])
            ins_apply_fee = number_utils.get_integer(row['SubTotal'])
            s_drug_fee = 0
        else:
            diag_fee = 0
            inter_drug_fee = 0
            pharmacy_fee = 0

            treat_fee = 0
            acupuncture_fee = 0
            massage_fee = 0
            acupuncture_fee = 0
            massage_fee = 0

            diag_share_fee = 0
            drug_share_fee = 0
            ins_total_fee = 0
            ins_apply_fee = 0
            s_drug_fee = number_utils.get_integer(row['OwnPayFee'])

        self_total_fee = s_drug_fee

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
            'SDrugFee', 'SelfTotalFee',
            'TotalFee', 'ReceiptFee',
        ]
        data = [
            regist_fee, diag_fee, inter_drug_fee,
            pharmacy_fee, pharmacy_type,
            acupuncture_fee, massage_fee,
            diag_share_fee, drug_share_fee,
            diag_share_fee, drug_share_fee,
            ins_total_fee, ins_apply_fee,
            s_drug_fee, self_total_fee,
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

    def _convert_dosage(self, case_key, medical_record_row, row):
        if medical_record_row['InsType'] == '健保':
            medicine_set = 1
        else:
            medicine_set = 2

        pres_days = self._get_field_value(row['Days'])
        packages = self._get_field_value(row['DayTimes'])
        instruction = self._get_field_value(row['DrugMethod'])

        if pres_days == '0.0':
            pres_days = None
            instruction = None

        if packages == '0.0':
            packages = None

        fields = [
            'CaseKey', 'MedicineSet',
            'Packages', 'Days', 'Instruction',
        ]
        data = [
            case_key,
            medicine_set,
            packages,
            pres_days,
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
            SELECT * FROM drugs
            ORDER BY DrugNo
        """
        rows = self.source_db.select_record(sql)
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

            medicine_type = self._get_medicine_type(row['DrugClass'])
            if medicine_type is None:
                continue

            medicine_code = self._get_field_value(row['DrugNo'])
            medicine_mode = None
            input_code = self._get_field_value(row['DrugHelpKey'])
            if input_code is not None:
                input_code = input_code[:5]

            ins_code = self._get_field_value(row['NHICode'])
            medicine_name = self._get_field_value(row['DrugName'])
            medicine_alias = None
            unit = self._get_field_value(row['Unit'])
            dosage = None
            location = None

            sale_price = number_utils.get_float(row['SalePrice'])
            in_price = number_utils.get_float(row['Price'])
            safe_quantity = None
            description = row['GroupDrugContent']

            if medicine_type == '複方' and '(水)' in medicine_name:
                medicine_type = '水藥'

            data = [
                medicine_type,
                medicine_mode,
                medicine_code,
                input_code,
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

    def _get_drug_slip_rows(self, drug_id):
        sql = f"""
            SELECT * FROM drug_slip
            WHERE
                CDrugId = '{drug_id}'
        """
        rows = self.source_db.select_record(sql)
        if len(rows) <= 0:
            return None

        return rows

    def _cvt_compound_title(self):
        sql = """
            SELECT CDrugid FROM drug_slip
            GROUP BY CDrugid
            ORDER BY CDrugid
        """
        rows = self.source_db.select_record(sql)
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
                unit = self._get_field_value(drug_slip_row['Unit_Name'])
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
            '掛號人員': '職員',
            '行政人員': '職員',
            '助理人員': '推拿師父',
        }

        self.parent.ui.label_progress.setText('使用者資料檔轉檔')
        sql = """
            SELECT * FROM employee
            ORDER BY EmployeeNo
        """
        rows = self.source_db.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        sql = 'TRUNCATE person'
        self.database.exec_sql(sql)
        fields = [
            'Code', 'Name', 'ID', 'Position', 'Password', 'Room',
        ]

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            code = self._get_field_value(row['EmployeeNo'])
            name = self._get_field_value(row['EmployeeName'])
            id = self._get_field_value(row['EmployeeID'])
            password = self._get_field_value(row['PassWord'])

            try:
                position = position_dict[self._get_field_value(row['EmployeeClass'])]
            except Exception:
                position = None

            if position in ['醫師', '支援醫師']:
                room = row['Room']
                if room in ['', None]:
                    room = 1
            else:
                room = None

            data = [
                code, name, id, position, password, room,
            ]
            try:
                self.database.insert_record('person', fields, data)
            except Exception:
                pass

    def _cvt_disease(self):
        self.parent.ui.label_progress.setText('病名資料檔轉檔')
        sql = """
            SELECT
                NewDiseaseCode, DiseaseHelpKey, DiseaseName, SpecialClass
            FROM Disease
            ORDER BY DiseaseID
        """
        rows = self.source_db.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)
            icd10 = string_utils.xstr(row['NewDiseaseCode']).strip()
            input_code = string_utils.xstr(row['DiseaseHelpKey']).strip()[:5]
            special_code = string_utils.xstr(row['SpecialClass']).strip()[:2]

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
