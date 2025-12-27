
from PyQt5.QtWidgets import QMessageBox, QPushButton
# from dbfread import DBF
try:
    import pyodbc
except Exception:
    pass

import os
import sqlite3

from libs import string_utils
from libs import patient_utils
from libs import number_utils
from libs import date_utils
from libs import nhi_utils
from libs import case_utils
from libs import personnel_utils


# 展望轉檔 2023.09.04
class CvtVIS():
    def __init__(self, parent, *args):
        self.parent = parent
        self.product_type = parent.ui.comboBox_utec_product.currentText()
        self.database = parent.database
        self.source_db = parent.source_db
        self.progress_bar = parent.ui.progressBar

        self.conn = pyodbc.connect(f'DSN={self.parent.ui.lineEdit_vis_odbc.text()};UID="";PWD=""')
        self.cursor = self.conn.cursor()

    def disconnect_db(self):
        self.cursor.close()
        self.conn.close()

    # 開始轉檔
    def convert(self):
        if self.parent.ui.lineEdit_vis_odbc.text() == '':
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('尚未設定Data Source Name')
            msg_box.setText("<font size='4' color='Red'><b>尚未設定ODBC FoxPro Data Source Name, 請設定後再執行轉檔作業.</b></font>")
            msg_box.setInformativeText("連線尚未設定, 無法執行轉檔作業.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        if self.parent.ui.checkBox_patient_vis.isChecked():
            self._cvt_patient()

        if self.parent.ui.checkBox_medical_record_vis.isChecked():
            self._convert_medical_record()

    @staticmethod
    def _get_date(in_date):
        if in_date is None:
            return None

        try:
            year = in_date[:3]
            month = in_date[3:5]
            day = in_date[5:7]
        except ValueError:
            return None

        if year.strip() == '':
            out_date = None
        else:
            year = int(year) + 1911
            out_date = f'{year}-{month}-{day}'

        return out_date

    @staticmethod
    def _get_share(share_type):
        share_type = share_type.strip()

        if share_type == '3':
            share = '低收入戶'
        elif share_type == '4':
            share = '榮民'
        else:
            share = '基層醫療'

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

        start_patient_key = self.parent.ui.lineEdit_start_patient_key.text()
        if start_patient_key != '':
            self.cursor.execute(f'SELECT * FROM CO01M WHERE KCSTMR >= "{start_patient_key:0>7}" ORDER BY KCSTMR')
        else:
            self.cursor.execute('SELECT * FROM CO01M ORDER BY KCSTMR')

        rows = self.cursor.fetchall()

        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        fields = [
            'PatientKey', 'Name', 'Birthday', 'ID',
            'Telephone', 'Cellphone', 'InitDate', 'InsType', 'DiscountType',
            'Gender', 'Address', 'Nationality', 'Remark',
            'ZipCode', 'CardNo', 'Marriage', 'History', 'Allergy',
        ]

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            name = self._get_field_value(row[1])
            card_no = None
            telephone = self._get_field_value(row[7])
            cellphone = self._get_field_value(row[25])
            address = self._get_field_value(row[60])
            zip_code = self._get_field_value(row[59])
            marriage = None
            history = None
            allergy = None
            remark = None
            birthday = self._get_date(row[4])

            try:
                init_date = self._get_date(row[17])
            except Exception:
                init_date = None

            ins_type = self._get_share(string_utils.xstr(row[35]))
            # discount_type = self._get_discount_type(string_utils.xstr(row['Identity_Type']))
            discount_type = None

            try:
                patient_id = self._get_field_value(row[13]).strip()
            except Exception:
                patient_id = None

            nationality = '本國'
            if patient_id is not None and len(patient_id) > 1:
                nationality = patient_utils.get_nationality(patient_id[1])
                if patient_id[1] == '1':
                    gender = '男'
                elif patient_id[1] == '2':
                    gender = '女'

            patient_key = number_utils.get_integer(row[0])
            data = [
                patient_key,
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
                self.database.update_record('patient', fields, 'PatientKey', patient_key, data)

    def _get_discount_type(self, id_type):
        discount_type = None
        id_type = id_type.strip()

        if id_type not in ['一般', '榮民', '福保', '重大傷病']:
            discount_type = id_type

        return discount_type

    def _get_west_date(self, in_date):
        in_year = int(in_date[:3]) + 1911
        in_month = int(in_date[3:5])
        in_day = int(in_date[5:7])

        return f'{in_year}-{in_month:0>2}-{in_day:0>2}'

    def _get_tw_date(self, in_date):
        in_year = int(in_date[:4]) - 1911
        in_month = int(in_date[4:6])
        in_day = int(in_date[6:8])

        return f'{in_year:0>3}{in_month:0>2}{in_day:0>2}'

    def _get_time(self, in_time):
        hour = int(in_time[:2])
        minute = int(in_time[2:4])
        second = int(in_time[4:6])

        return f'{hour:0>2}:{minute:0>2}:{second:0>2}'

    def create_sqlite3(self):
        db_name = os.path.join(self.parent.ui.lineEdit_vis_db_path.text(), 'vis.db')
        con = sqlite3.connect(db_name)

        self.create_medicine(con)
        self.create_symptom(con)
        self.create_cases(con)
        self.create_prescript(con)

        con.close()

    def create_cases(self, con):
        cur = con.cursor()
        try:
            cur.execute('DROP TABLE cases')
        except Exception:
            pass

        cur.execute('''
            CREATE TABLE cases (
                case_date, case_time, patient_key, name, ins_type, card,
                disease_code,disease_name, disease_code2, disease_code3, doctor_id,
                share_type, regist_fee
            )
        ''')

        table_name = os.path.join(self.parent.ui.lineEdit_vis_db_path.text(), 'CO03L.DBF')
        table = DBF(table_name)

        self.parent.ui.label_progress.setText('建立病歷資料檔')
        self.progress_bar.setMaximum(len(table))
        self.progress_bar.setValue(0)
        for row in table:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            case_date = self._get_west_date(row['DATE'])
            case_time = self._get_time(row['TIME'])
            patient_key = int(row['KCSTMR'])
            name = row['LNAME']
            if row['LISRS'].strip() == '':
                card = ''
            else:
                card = '0' + row['LISRS']

            disease_code = row['LABNO']
            disease_code = disease_code.strip()
            disease_name = row['LABDT']
            disease_name = disease_name.strip()

            doctor_id = row['LDTID']
            share_code = row['LHIID']

            ins_type = '健保'
            if row['LPID'].strip() == '':
                ins_type = '自費'

            share_type = '基層醫療'
            if share_code == '003':
                share_type = '低收入戶'
            elif share_code == '004':
                share_type = '榮民'

            disease_code2, disease_code3 = '', ''
            try:
                disease_code_list = row['LACD'].split(',')
                disease_code2 = disease_code_list[0].strip()
                disease_code3 = disease_code_list[1].strip()
            except Exception:
                pass

            regist_fee = number_utils.get_integer(row['A0'])
            
            sql = f'''
                INSERT INTO cases (
                        case_date, case_time, patient_key, name, ins_type, card, disease_code,
                        disease_name, disease_code2, disease_code3, doctor_id,
                        share_type, regist_fee
                    )
                    VALUES(
                        "{case_date}", "{case_time}", "{patient_key}", "{name}", "{ins_type}", "{card}",
                        "{disease_code}", "{disease_name}", "{disease_code2}", "{disease_code3}",
                        "{doctor_id}", "{share_type}", "{regist_fee}"
                    )
            '''
            cur.execute(sql)

        self.progress_bar.setValue(len(table))
        con.commit()

    def create_prescript(self, con):
        cur = con.cursor()
        try:
            cur.execute('DROP TABLE prescript')
        except Exception:
            pass

        cur.execute('''
            CREATE TABLE prescript (
                case_date, case_time, patient_key, medicine_key, dosage, package, presdays
            )
        ''')

        table_name = os.path.join(self.parent.ui.lineEdit_vis_db_path.text(), 'CO02P.DBF')
        table = DBF(table_name)

        self.parent.ui.label_progress.setText('建立病歷處方檔')
        self.progress_bar.setMaximum(len(table))
        self.progress_bar.setValue(0)
        for row in table:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            case_date = self._get_west_date(row['PDATE'])
            case_time = self._get_time(row['PTIME'])
            patient_key = int(row['KCSTMR'])
            medicine_key = row['KDRUG']
            dosage = row['PQTY']
            package = row['PTFQ']
            presdays = row['PTDAY']
            
            sql = f'''
                INSERT INTO prescript (
                        case_date, case_time, patient_key, medicine_key, dosage, package, presdays
                    )
                    VALUES(
                        "{case_date}", "{case_time}", "{patient_key}", "{medicine_key}",
                        "{dosage}", "{package}", "{presdays}"
                    )
            '''
            cur.execute(sql)

        self.progress_bar.setValue(len(table))
        con.commit()

    def create_symptom(self, con):
        cur = con.cursor()
        try:
            cur.execute('DROP TABLE symptom')
        except Exception:
            pass

        cur.execute('''
            CREATE TABLE symptom (
                case_date, case_time, patient_key, symptom
            )
        ''')

        table_name = os.path.join(self.parent.ui.lineEdit_vis_db_path.text(), 'CO02H.DBF')
        table = DBF(table_name, encoding='windows-1252')

        self.parent.ui.label_progress.setText('建立病歷主訴檔')
        self.progress_bar.setMaximum(len(table))
        self.progress_bar.setValue(0)
        for row in table:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            case_date = self._get_west_date(row['SDATE'])
            case_time = self._get_time(row['STIME'])
            patient_key = int(row['KCSTMR'])
            symptom = row['STEXT']
            
            sql = f'''
                INSERT INTO symptom (
                        case_date, case_time, patient_key, symptom
                    )
                    VALUES(
                        "{case_date}", "{case_time}", "{patient_key}", "{symptom}"
                    )
            '''
            cur.execute(sql)

        self.progress_bar.setValue(len(table))

        con.commit()

    def create_medicine(self, con):
        cur = con.cursor()
        try:
            cur.execute('DROP TABLE medicine')
        except Exception:
            pass

        cur.execute('''
            CREATE TABLE medicine (
                medicine_key, input_code, medicine_name, unit, medicine_type, ins_type
            )
        ''')

        table_name = os.path.join(self.parent.ui.lineEdit_vis_db_path.text(), 'CO09D.DBF')
        table = DBF(table_name)

        self.parent.ui.label_progress.setText('建立處方詞庫檔')
        self.progress_bar.setMaximum(len(table))
        self.progress_bar.setValue(0)
        for row in table:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            medicine_key = row['KDRUG']
            input_code = row['KDRUGS']
            medicine_name = row['DDESC']
            unit = row['DUM1']
            medicine_type = row['DGROUP']
            ins_type = row['DNO']
            
            sql = f'''
                INSERT INTO medicine (
                        medicine_key, input_code, medicine_name, unit, medicine_type, ins_type
                    )
                    VALUES(
                        "{medicine_key}", "{input_code}", "{medicine_name}", "{unit}",
                        "{medicine_type}", "{ins_type}"
                    )
            '''
            cur.execute(sql)

        self.progress_bar.setValue(len(table))

        con.commit()

    def _get_symptom(self, kcstmr, sdate, stime):
        sql = f'''
            SELECT STEXT FROM CO02H
            WHERE
                KCSTMR = "{kcstmr}" AND
                SDATE = "{sdate}" AND
                STIME = "{stime}"
        '''
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()

        if len(rows) <= 0:
            return None

        row = rows[0]
        return string_utils.get_str(row[0], 'utf8')

    def _convert_medical_record(self):
        self.parent.ui.label_progress.setText('病歷資料檔')

        start_date = self.parent.ui.dateEdit_start_date_vis.date().toString('yyyy-MM-dd')
        end_date = self.parent.ui.dateEdit_end_date_vis.date().toString('yyyy-MM-dd')

        a_start_date = self.parent.ui.dateEdit_start_date_vis.date().toString('yyyyMMdd')
        a_end_date = self.parent.ui.dateEdit_end_date_vis.date().toString('yyyyMMdd')
        tw_start_date = self._get_tw_date(a_start_date)
        tw_end_date = self._get_tw_date(a_end_date)

        self.cursor.execute(f'SELECT * FROM CO03L WHERE DATE BETWEEN "{tw_start_date}" AND "{tw_end_date}" ORDER BY DATE')
        rows = self.cursor.fetchall()

        sql = f'SELECT CaseKey FROM cases WHERE DATE(CaseDate) BETWEEN "{start_date}" AND "{end_date}"'
        case_rows = self.database.select_record(sql)
        for case_row in case_rows:
            case_key = case_row['CaseKey']
            self.database.exec_sql(f'DELETE FROM prescript WHERE CaseKey = {case_key}')
            self.database.exec_sql(f'DELETE FROM dosage WHERE CaseKey = {case_key}')
            self.database.exec_sql(f'DELETE FROM cases WHERE CaseKey = {case_key}')

        self.parent.ui.label_progress.setText('病歷資料庫轉檔')
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        fields = [
            'CaseDate', 'DoctorDate', 'ChargeDate', 'PatientKey', 'Name', 'InsType', 'Card', 'Continuance',
            'Symptom', 'Tongue', 'Pulse', 'Distincts', 'Cure',
            'DiseaseCode1', 'DiseaseName1',
            'DiseaseCode2', 'DiseaseName2',
            'DiseaseCode3', 'DiseaseName3',
            'Doctor', 'Treatment',
            'Share', 'RegistFee',
            'Visit', 'Period', 'ChargePeriod', 'RegistType', 'Injury', 'TreatType', 'ApplyType', 'PHarmacyType',
            'DoctorDone', 'ChargeDone',
        ]
        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            kcstmr = row[0]
            sdate = row[1]
            stime = row[6]
            symptom_line = self._get_symptom(kcstmr, sdate, stime)
            symptom_line = symptom_line.strip()

            symptom, tongue, pulse, distincts, cure = None, None, None, None, None
            if symptom_line is not None:
                symptom_list = symptom_line.split('\x80')
                for item in symptom_list:
                    if item is None:
                        continue

                    try:
                        if '\n\r' in item:
                            item = item.split('\r\n')[0]

                        if '問診：' in item:
                            symptom = item.split('問診：')[1]
                        elif '望診：' in item:
                            tongue = item.split('望診：')[1]
                        elif '脈診：' in item:
                            pulse = item.split('脈診：')[1]
                        elif '辨證：' in item:
                            distincts = item.split('辨證：')[1]
                        elif '治則：' in item:
                            cure = item.split('治則：')[1]
                    except Exception:
                        symptom = item

            case_date = self._get_west_date(row[1])
            case_time = self._get_time(row[6])
            if case_time >= '18:00:00':
                period = '晚班'
            elif case_time >= '14:00:00':
                period = '午班'
            else:
                period = '早班'

            patient_key = int(row[0])
            name = row[77]

            if row[59].strip() == '':
                card = ''
            else:
                card = '0' + row[59]

            continuance = number_utils.get_integer(row[74])
            if continuance == 0:
                continuance = None

            doctor_id = row[69]
            doctor_name = personnel_utils.person_id_to_name(self.database, doctor_id)
            share_code = row[71]

            if row[7].strip() == '':
                ins_type = '自費'
            else:
                ins_type = '健保'

            if share_code == '003':
                share_type = '低收入戶'
            elif share_code == '004':
                share_type = '榮民'
            else:
                share_type = '基層醫療'

            disease_code1 = row[19]
            disease_name1 = row[20]
            disease_code2, disease_code3 = None, None 
            disease_name2, disease_name3 = None, None 

            disease_code_list = string_utils.xstr(row[60]).strip()
            if disease_code_list != '':
                try:
                    disease_code_list = disease_code_list.split(',')
                    disease_code2 = disease_code_list[0].strip()
                    disease_code3 = disease_code_list[1].strip()
                except Exception:
                    pass

            if disease_code2 is not None:
                disease_name2 = case_utils.get_disease_name(self.database, disease_code2)
            if disease_code3 is not None:
                disease_name3 = case_utils.get_disease_name(self.database, disease_code3)

            reigst_fee = row[21]

            regist_type = '一般門診'
            injury = '普通疾病'

            treat_type = string_utils.xstr(row[14]).strip()
            if '針灸' in treat_type:
                treat_type = '一般針灸'
                treatment = treat_type
            else:
                treat_type = '內科'
                treatment = None

            data = [
                case_date, case_date, case_date, patient_key, name, ins_type, card, continuance,
                symptom, tongue, pulse, distincts, cure,
                disease_code1, disease_name1,
                disease_code2, disease_name2,
                disease_code3, disease_name3,
                doctor_name, treatment,
                share_type, reigst_fee,
                '複診', period, period, regist_type, injury, treat_type, '申報', '不申報',
                'True', 'True',
            ]

            case_key = self.database.insert_record('cases', fields, data)
            self._convert_prescript(case_key, case_date, kcstmr, sdate, stime, ins_type)

        self.progress_bar.setValue(len(rows))

    def _convert_prescript(self, case_key, case_date, kcstmr, sdate, stime, ins_type):
        sql = f"""
            SELECT * FROM CO02P
            WHERE
                 KCSTMR = '{kcstmr}' AND
                 PDATE = '{sdate}' AND
                 PTIME = '{stime}'
        """
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()

        fields = [
            'CaseKey', 'CaseDate', 'MedicineSet',
            'MedicineType', 'MedicineKey', 'InsCode',
            'MedicineName', 'Unit', 'DosageMode', 'Dosage',
        ]
        packages, presdays = None, None
        for row in rows:
            if ins_type == '健保':
                medicine_set = 1
            else:
                medicine_set = 2

            try:
                dosage = row[8]
            except Exception:
                dosage = None

            kdrug = row[6]
            medicine_type, medicine_name, unit, ins_code = self._get_medicine(kdrug)
            packages = row[14]
            presdays = row[17]

            data = [
                case_key,
                case_date,
                medicine_set,
                medicine_type,
                None,
                ins_code,
                medicine_name,
                unit,
                '日劑量',
                dosage
            ]
            self.database.insert_record('prescript', fields, data)

        if packages is not None and presdays is not None:
            try:
                fields = ['CaseKey', 'MedicineSet', 'Packages', 'Days', 'Instruction']
                data = [case_key, medicine_set, packages, presdays, '飯後']
                self.database.insert_record('dosage', fields, data)
            except Exception:
                pass

    def _get_medicine(self, kdrug):
        sql = f'''
            SELECT * from co09d
            WHERE
                KDRUG = "{kdrug}"
        '''
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        if len(rows) <= 0:
            return None, None, None, None

        row = rows[0]

        medicine_type = row[5]
        medicine_name = row[2]
        unit = row[3]
        ins_code = row[7]

        medicine_type = medicine_type.strip()
        medicine_name = medicine_name.strip()
        unit = unit.strip()
        ins_code = ins_code.strip()

        if medicine_type == '單':
            medicine_type = '單方'
        elif medicine_type == '複':
            medicine_type = '複方'
        elif medicine_type == '水':
            medicine_type = '水藥'
        elif medicine_type == '高':
            medicine_type = '高貴'
        elif medicine_type == '針':
            medicine_type = '穴道'
        elif medicine_type == '傷':
            medicine_type = '處置'

        return medicine_type, medicine_name, unit, ins_code

    def _convert_sqlite3_medical_record(self):
        start_date = self.parent.ui.dateEdit_start_date_vis.date().toString('yyyy-MM-dd')
        end_date = self.parent.ui.dateEdit_end_date_vis.date().toString('yyyy-MM-dd')

        db_name = os.path.join(self.parent.ui.lineEdit_vis_db_path.text(), 'vis.db')
        con = sqlite3.connect(db_name)
        cur = con.cursor()
        cur.execute(f'''
            select * from cases where
                case_date between "{start_date}" and "{end_date}"
                order by case_date
        ''')
        rows = cur.fetchall()

        self.parent.ui.label_progress.setText('病歷資料庫轉檔')
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)
        fields = [
            'CaseDate', 'PatientKey', 'Name', 'InsType', 'Card',
            'DiseaseCode1', 'DiseaseName1',
            'DiseaseCode2', 'DiseaseName2',
            'DiseaseCode3', 'DiseaseName3',
            'Doctor',
            'Share', 'RegistFee',
            'Visit', 'Period', 'RegistType', 'ApplyType', 'PHarmacyType',
            'DoctorDone', 'ChargeDone',
        ]
        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)
            case_date = row[0]
            case_time = row[1]
            patient_key = row[2]
            name = row[3]
            ins_type = row[4]
            card = row[5]
            disease_code1 = row[6]
            disease_name1 = row[7]

            disease_code2 = row[8]
            disease_name2 = None
            disease_code3 = row[9]
            disease_name3 = None

            doctor_id = row[10]
            doctor_name = personnel_utils.person_id_to_name(self.database, doctor_id)

            share_type = row[11]
            reigst_fee = row[12]
            if case_time >= '18:00:00':
                period = '晚班'
            elif case_time >= '14:00:00':
                period = '午班'
            else:
                period = '早班'

            if disease_code2 != '':
                disease_name2 = case_utils.get_disease_name(self.database, disease_code2)
            if disease_code3 != '':
                disease_name3 = case_utils.get_disease_name(self.database, disease_code3)

            data = [
                case_date, patient_key, name, ins_type, card,
                disease_code1, disease_name1,
                disease_code2, disease_name2,
                disease_code3, disease_name3,
                doctor_name,
                share_type, reigst_fee,
                '複診', period, '一般門診', '申報', '不申報',
                'True', 'True',
            ]

            case_key = self.database.insert_record('cases', fields, data)
            self._convert_sqlite3_prescript(cur, case_key, case_date, case_time, patient_key, ins_type)

        self.progress_bar.setValue(len(rows))

    def _convert_sqlite3_prescript(self, cur, case_key, case_date, case_time, patient_key, ins_type):
        sql = f"""
            SELECT * FROM prescript
            WHERE
                 case_date = '{case_date}' AND
                 case_time = '{case_time}' AND
                 patient_key = '{patient_key}'
        """
        cur.execute(sql)
        rows = cur.fetchall()

        fields = [
            'CaseKey', 'CaseDate', 'MedicineSet',
            'MedicineType', 'MedicineKey', 'InsCode',
            'MedicineName', 'Unit', 'DosageMode', 'Dosage',
        ]
        packages, presdays = None, None
        for row in rows:
            if ins_type == '健保':
                medicine_set = 1
            else:
                medicine_set = 2

            try:
                dosage = row[4]
            except Exception:
                dosage = None

            kdrug = row[3]
            medicine_type, medicine_name, unit, ins_code = self._get_medicine(kdrug)
            packages = row[5]
            presdays = row[6]

            data = [
                case_key,
                case_date,
                medicine_set,
                medicine_type,
                None,
                ins_code,
                medicine_name,
                unit,
                '日劑量',
                dosage
            ]
            self.database.insert_record('prescript', fields, data)

        if packages is not None and presdays is not None:
            try:
                fields = ['CaseKey', 'MedicineSet', 'Packages', 'Days', 'Instruction']
                data = [case_key, medicine_set, packages, presdays, '飯後']
                self.database.insert_record('dosage', fields, data)
            except Exception:
                pass
