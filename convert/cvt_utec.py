
from PyQt5.QtWidgets import QMessageBox, QPushButton, QFileDialog
from convert import cvt_groups
import re
import json
import os
from os import listdir

from libs import string_utils
from libs import number_utils
from libs import nhi_utils
from libs import date_utils
from libs import case_utils

import check_database


# 友杏轉檔 2018.05.09
class CvtUtec():
    def __init__(self, parent, *args):
        self.parent = parent
        self.product_type = parent.ui.comboBox_utec_product.currentText()
        self.database = parent.database
        self.source_db = parent.source_db
        self.utec_db = parent.utec_db
        self.progress_bar = parent.ui.progressBar

    # 開始轉檔
    def convert(self):
        if self.parent.ui.label_connection_status.text() == '未連線':
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('尚未開啟連線')
            msg_box.setText("<font size='4' color='Red'><b>尚未執行連線測試, 請執行連線測試後再執行轉檔作業.</b></font>")
            msg_box.setInformativeText("連線尚未開啟, 無法執行轉檔作業.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        if self.product_type == 'Med2000':
            self._convert_med2000()
        else:
            self._convert_medical()

        if self.parent.ui.checkBox_address_list.isChecked():
            self._cvt_address_list()
        if self.parent.ui.checkBox_certificate.isChecked():
            self._cvt_certificate()
        if self.parent.ui.checkBox_self_drug.isChecked():
            self._cvt_self_drug()
        if self.parent.ui.checkBox_users.isChecked():
            self._cvt_users()
        if self.parent.ui.checkBox_pathologic.isChecked():
            self._cvt_pathologic()
        if self.parent.ui.checkBox_case_extend.isChecked():
            self._cvt_case_extend()

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle('轉檔完成')
        msg_box.setText("<font size='4' color='Blue'><b>恭喜！轉檔完成!</b></font>")
        msg_box.setInformativeText("請繼續轉檔作業.")
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

    def _convert_med2000(self):
        if self.parent.ui.checkBox_groups.isChecked():
            self._cvt_groups()
        if self.parent.ui.checkBox_disease_common.isChecked():
            self._cvt_disease_common()
        if self.parent.ui.checkBox_disease_treat.isChecked():
            self._cvt_disease_treat()
        if self.parent.ui.checkBox_dosage.isChecked():
            self._cvt_med2000_dosage()
        if self.parent.ui.checkBox_medical_record.isChecked():
            self._cvt_med2000_cases()
        if self.parent.ui.checkBox_treatment.isChecked():
            self._cvt_treatment()
        if self.parent.ui.checkBox_tour_area.isChecked():
            self._cvt_tour_area()
        if self.parent.ui.checkBox_infectious.isChecked():
            self._cvt_infectious()

    def _convert_medical(self):
        if self.parent.ui.checkBox_database.isChecked():
            self._cvt_database()
        if self.parent.ui.checkBox_groups.isChecked():
            self._cvt_groups()
        if self.parent.ui.checkBox_disease_common.isChecked():
            self._cvt_disease_common()
        if self.parent.ui.checkBox_disease_treat.isChecked():
            self._cvt_disease_treat()
        if self.parent.ui.checkBox_dosage.isChecked():
            self._cvt_medical_dosage()
        if self.parent.ui.checkBox_patient.isChecked():
            self._cvt_medical_patient()
        if self.parent.ui.checkBox_reserve.isChecked():
            self._cvt_medical_reserve()
        if self.parent.ui.checkBox_medical_record.isChecked():
            self._cvt_medical_cases()
            self._cvt_med2000_cases()
        if self.parent.ui.checkBox_treatment.isChecked():
            self._cvt_treatment()
        if self.parent.ui.checkBox_tour_area.isChecked():
            self._cvt_tour_area()
        if self.parent.ui.checkBox_infectious.isChecked():
            self._cvt_infectious()
        if self.parent.ui.checkBox_commission.isChecked():
            self._cvt_medical_commission()
        if self.parent.ui.checkBox_project.isChecked():
            self._cvt_medical_project()

    def _cvt_database(self):
        self.parent.ui.label_progress.setText('基礎資料庫轉檔')
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        check_db = check_database.CheckDatabase(
            self.parent, self.database, self.parent.system_settings, 'cvt_utec')
        check_db.check_database()
        del check_db

        self.progress_bar.setValue(100)

    def _cvt_groups(self):
        self.parent.ui.label_progress.setText('詞庫類別轉檔')
        cvt_groups.cvt_pymedical_groups(self.database)
        cvt_groups.cvt_groups_name(self.database, self.source_db, self.product_type, self.progress_bar)
        cvt_groups.cvt_tongue_groups(self.database, self.source_db, self.progress_bar)
        cvt_groups.cvt_pulse_groups(self.source_db)
        cvt_groups.cvt_remark_groups(self.source_db)
        cvt_groups.cvt_pymedical_disease_groups(self.database)
        cvt_groups.cvt_pymedical_other_groups(self.source_db)

    def _cvt_med2000_dosage(self):
        sql = 'TRUNCATE dosage'
        self.database.exec_sql(sql)

        sql = '''
            SELECT CaseKey,
                Package1, Package2, Package3, Package4, Package5, Package6,
                PresDays1, PresDays2, PresDays3, PresDays4, PresDays5, PresDays6,
                Instruction1, Instruction2, Instruction3, Instruction4, Instruction5, Instruction6
             FROM cases ORDER BY CaseKey
        '''
        rows = self.source_db.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)
        fields = ['CaseKey', 'MedicineSet', 'Packages', 'Days', 'Instruction']
        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)
            for i in range(1, 7):
                if row[f'Package{i}'] is not None or row[f'PresDays{i}'] is not None:
                    data = [
                        row['CaseKey'],
                        i,
                        row[f'Package{i}'],
                        row[f'PresDays{i}'],
                        row[f'Instruction{i}']
                    ]
                    self.database.insert_record('dosage', fields, data)

    def _cvt_med2000_cases(self):
        self.parent.ui.label_progress.setText('Med2000病歷檔轉檔')
        self.progress_bar.setMaximum(23)
        self.progress_bar.setValue(0)

        sql = '''
            UPDATE cases
            SET
                RegistType = "一般門診"
            WHERE
                RegistType IN ("一般", "中度複針", "高度複針", "中度複傷", "高度複傷")
        '''
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET Position1 = NULL, Position2 = NULL'
        self.database.exec_sql(sql)

        sql = 'UPDATE cases SET TreatType = "居家醫療", RegistType = "一般門診" WHERE RegistType IN ("居家整合")'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET PharmacyType = "不申報" WHERE ApplyType = "調劑不報"'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET PharmacyType = "申報" WHERE PharmacyType IS NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET ApplyType = "申報" WHERE ApplyType != "不申報"'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "內科" WHERE TreatType IN ("一般", "一般+民俗")'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "針灸治療" WHERE Treatment = "針灸治療" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "一般針灸" WHERE Treatment = "一般針灸" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "電針", Treatment = "電針" WHERE Treatment = "電針治療" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "複雜針灸" WHERE Treatment = "複雜針灸" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "中度複雜性針灸", RegistType = "一般門診" WHERE TreatType = "中度複針" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "高度複雜性針灸", RegistType = "一般門診" WHERE TreatType = "高度複針" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "中度複雜性針灸", Treatment = "中度複雜性針灸" WHERE Treatment = "中度複針" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "高度複雜性針灸", Treatment = "高度複雜性針灸" WHERE Treatment = "高度複針" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "傷科治療" WHERE Treatment = "傷科治療" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "一般傷科" WHERE Treatment = "一般傷科" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "複雜傷科" WHERE Treatment = "複雜傷科" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "中度複雜性傷科", Treatment = "中度複雜性傷科" WHERE Treatment = "中度複傷" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "高度複雜性傷科", Treatment = "高度複雜性傷科" WHERE Treatment = "多部位損傷" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = '''
            UPDATE cases
            SET
                TreatType = "中度複雜性傷科合併特殊疾病", Treatment = "中度複雜性傷科合併特殊疾病"
            WHERE
                Treatment = "中度併特疾"
        '''
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "脫臼整復" WHERE Treatment = "脫臼整復" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "骨折復位" WHERE Treatment = "骨折復位" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        dosage_mode = self.parent.ui.comboBox_dosage_mode.currentText()
        sql = f'UPDATE prescript SET DosageMode = "{dosage_mode}"'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE prescript SET Amount = Price * Dosage WHERE Amount = 0 AND Price > 0 AND MedicineSet >= 2'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

    def _cvt_tour_area(self):
        self.parent.ui.label_progress.setText('資源缺乏地區轉檔')
        self.progress_bar.setMaximum(5)
        self.progress_bar.setValue(0)

        sql = 'UPDATE cases SET RegistType = "矯正機關內門診" WHERE RegistType = "矯正醫療" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET RegistType = "前往資源不足地區" WHERE RegistType = "巡迴偏遠" '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        tour_area = self.parent.ui.comboBox_tour_area.currentText()
        sql = f'UPDATE cases SET TourArea = "{tour_area}" WHERE RegistType IN("巡迴山地", "巡迴偏遠", "巡迴離島") '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        lack_area = self.parent.ui.comboBox_lack_area.currentText()
        sql = f'UPDATE cases SET TourArea = "{lack_area}" WHERE RegistType IN("前往資源不足地區") '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        correction_area = self.parent.ui.comboBox_correction_area.currentText()
        sql = f'UPDATE cases SET TourArea = "{correction_area}" WHERE RegistType IN("矯正機關內門診", "戒護就醫") '
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

    def _cvt_infectious(self):
        self.parent.ui.label_progress.setText('法定傳染病及視訊門診轉檔')
        self.progress_bar.setMaximum(3)
        self.progress_bar.setValue(0)

        sql = '''
            UPDATE cases SET
                RegistType = "視訊門診"
            WHERE
                Pulse LIKE "視訊%" AND
                DiseaseCode1 != "U071"
        '''
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = '''
            UPDATE cases SET
                RegistType = "法定傳染病通報隔離",
                Share = "法定傳染病通報隔離",
                Injury = "法定傳染病通報隔離"
            WHERE
                DiseaseCode1 = "U071"
        '''
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = '''
            SELECT CaseKey, Symptom FROM cases
            WHERE
                RegistType = "法定傳染病通報隔離" AND
                Symptom LIKE "%隔離日期%"
        '''
        rows = self.database.select_record(sql)

        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        for row in rows:
            symptom = row['Symptom']
            try:
                start_pos = symptom.find('隔離日期')
                infectious_date = symptom[start_pos+6:start_pos+15].strip()
                infectious_date = date_utils.date_to_west_date(infectious_date)
                case_utils.set_case_extend(
                    self.database, row['CaseKey'], '確診日期',
                    f'{infectious_date} 00:00:00'
                )
            except Exception:
                continue

            self.progress_bar.setValue(self.progress_bar.value() + 1)

    # 病歷處置檔
    def _cvt_treatment(self):
        self.parent.ui.label_progress.setText('病歷處置檔轉檔')
        sql = '''
            SELECT CaseKey, CaseDate, Symptom, Position1, Position2 FROM cases
            WHERE
                Symptom LIKE "%治療時間%" AND
                Symptom LIKE "%輔助治療%"
        '''
        rows = self.database.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        for row in rows:
            if row['Symptom'] is None:
                continue

            self._set_treat_position(row)
            self._set_treat_time(row)
            self._set_auxiliary_treat(row)

            self.progress_bar.setValue(self.progress_bar.value() + 1)

    # 病歷處置
    def _cvt_case_extend(self):
        self.parent.ui.label_progress.setText('病歷處置轉檔')
        sql = '''
            SELECT cases.CaseKey, cases.Treatment, cases.Continuance, caseextend.Content FROM cases
                LEFT JOIN caseextend ON caseextend.CaseKey = cases.CaseKey
            WHERE
                ExtendType = "針傷合併"
        '''
        rows = self.database.select_record(sql)
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        for row in rows:
            primary_treatment = string_utils.xstr(row['Treatment'])
            primary_treatment = primary_treatment.split('合併')[0]
            second_treatment = string_utils.xstr(row['Content'])
            course = number_utils.get_integer(row['Continuance'])
            case_key = row['CaseKey']

            if primary_treatment == '中度複雜性針灸':
                primary_treatment = '中度針灸'
            elif primary_treatment == '高度複雜性針灸':
                primary_treatment = '高度針灸'
            elif primary_treatment == '中度複雜性針灸合併特殊疾病':
                primary_treatment = '中度針灸合併特殊疾病'

            if second_treatment == '中度複傷':
                second_treatment = '中度傷科'
            elif second_treatment in ['多部位損傷', '高度複傷']:
                second_treatment = '高度傷科'
            elif second_treatment == '中度併特疾':
                second_treatment = '中度傷科合併特殊疾病'

            new_treatment = f'{primary_treatment}合併{second_treatment}'
            treat_type = f'{primary_treatment}合併{second_treatment}'

            if second_treatment in ['中度傷科'] and course >= 2:
                new_treatment += '療程2-6次'
            elif second_treatment in ['高度傷科', '中度傷科合併特殊疾病', '脫臼整復復位', '骨折復位']:
                if course <= 1:
                    new_treatment += '起始次'
                else:
                    new_treatment += '後續治療'

            sql = f'''
                UPDATE cases
                SET
                    TreatType = "{treat_type}", Treatment = "{new_treatment}"
                WHERE
                    CaseKey = {case_key}
            '''
            self.database.exec_sql(sql)

            self.progress_bar.setValue(self.progress_bar.value() + 1)

    def _set_treat_time(self, row):
        fields = ['CaseKey', 'CaseDate', 'MedicineSet', 'MedicineType', 'MedicineName']
        medicine_type = '穴道'
        symptom = row['Symptom']
        start_time = None
        end_time = None
        treat_time = None

        if '治療開始時間' in symptom:
            try:
                start_pos = symptom.find('治療開始時間')
                start_time = symptom[start_pos+8:start_pos+13]
                if '上午 ' in start_time:
                    start_time = symptom[start_pos+8:start_pos+16].replace('上午 ', '')
                elif '下午 ' in start_time:
                    start_time = symptom[start_pos+8:start_pos+16].replace('下午 ', '')
            except Exception:
                pass

            time_re = re.compile("(24:00|2[0-3]:[0-5][0-9]|[0-1][0-9]:[0-5][0-9])")
            if time_re.match(start_time):
                start_time = f'治療開始:{start_time}'
            else:
                start_time = None

        if '結束時間' in symptom:
            try:
                start_pos = symptom.find('結束時間')
                end_time = symptom[start_pos+6:start_pos+11]
                if '上午 ' in end_time:
                    end_time = symptom[start_pos+6:start_pos+14].replace('上午 ', '')
                elif '下午 ' in end_time:
                    end_time = symptom[start_pos+6:start_pos+14].replace('下午 ', '')
            except Exception:
                pass

            time_re = re.compile("(24:00|2[0-3]:[0-5][0-9]|[0-1][0-9]:[0-5][0-9])")
            if time_re.match(end_time):
                end_time = f'治療結束:{end_time}'
            else:
                end_time = None

        if '治療時間' in symptom:
            try:
                start_pos = symptom.find('治療時間')
                treat_time = symptom[start_pos:start_pos+10]
                treat_time = treat_time.replace(' ', '')
            except Exception:
                pass

        if start_time is not None:
            self.database.exec_sql(f'''
                DELETE FROM prescript
                WHERE
                    CaseKey = {row["CaseKey"]} AND
                    MedicineSet = 1 AND
                    MedicineType = "{medicine_type}" AND
                    MedicineName LIKE "治療開始:%"
            ''')
            data = [row['CaseKey'], row['CaseDate'], 1, medicine_type, start_time]
            self.database.insert_record('prescript', fields, data)

        if end_time is not None:
            self.database.exec_sql(f'''
                DELETE FROM prescript
                WHERE
                    CaseKey = {row["CaseKey"]} AND
                    MedicineSet = 1 AND
                    MedicineType = "{medicine_type}" AND
                    MedicineName LIKE "治療結束:%"
            ''')
            data = [row['CaseKey'], row['CaseDate'], 1, medicine_type, end_time]
            self.database.insert_record('prescript', fields, data)

        if treat_time is not None:
            self.database.exec_sql(f'''
                DELETE FROM prescript
                WHERE
                    CaseKey = {row["CaseKey"]} AND
                    MedicineSet = 1 AND
                    MedicineType = "{medicine_type}" AND
                    MedicineName LIKE "治療時間:%"
            ''')
            data = [row['CaseKey'], row['CaseDate'], 1, medicine_type, treat_time]
            self.database.insert_record('prescript', fields, data)

    def _set_auxiliary_treat(self, row):
        auxiliary_treat_list = []
        symptom = row['Symptom']

        if '輔助' in symptom and '拔罐' in symptom:
            auxiliary_treat_list.append('輔助治療:拔罐治療')
        if '輔助' in symptom and '刮痧' in symptom:
            auxiliary_treat_list.append('輔助治療:刮痧治療')
        if '輔助' in symptom and '熱療' in symptom:
            auxiliary_treat_list.append('輔助治療:熱療 (含紅外線治療)')
        if '輔助' in symptom and '熱敷' in symptom:
            auxiliary_treat_list.append('輔助治療:熱療 (含紅外線治療)')
        if '輔助' in symptom and '電療' in symptom:
            auxiliary_treat_list.append('輔助治療:電療')
        if '輔助' in symptom and '放血' in symptom:
            auxiliary_treat_list.append('輔助治療:放血')
        if '輔助' in symptom and '艾灸' in symptom:
            auxiliary_treat_list.append('輔助治療:艾灸治療')
        if '輔助' in symptom and '藥薰' in symptom:
            auxiliary_treat_list.append('輔助治療:藥薰治療')
        if '輔助' in symptom and '膏布' in symptom:
            auxiliary_treat_list.append('輔助治療:膏布治療')
        if '輔助' in symptom and '夾板' in symptom:
            auxiliary_treat_list.append('輔助治療:夾板固定治療')

        if len(auxiliary_treat_list) == 0:
            return

        fields = [
            'CaseKey', 'CaseDate', 'MedicineSet', 'MedicineType', 'MedicineName',
        ]
        self.database.exec_sql(f'''
            DELETE FROM prescript
            WHERE
                CaseKey = {row["CaseKey"]} AND
                MedicineSet = 1 AND
                MedicineType = "處置" AND
                MedicineName LIKE "輔助治療:%"
        ''')
        for auxiliary_treat in auxiliary_treat_list:
            data = [row['CaseKey'], row['CaseDate'], 1, '處置', auxiliary_treat]
            self.database.insert_record('prescript', fields, data)

    def _get_extra_position_list(self, symptom):
        extra_position_list = []

        if '右上肢' in symptom:
            extra_position_list.append('CO')
        if '左上肢' in symptom:
            extra_position_list.append('CH')
        if '右下肢' in symptom:
            extra_position_list.append('C1')
        if '左下肢' in symptom:
            extra_position_list.append('CV')
        if '頭部' in symptom:
            extra_position_list.append('CA')
        if '腰部' in symptom:
            extra_position_list.append('CF')
        if '上肢' in symptom:
            extra_position_list.append('CO')
            extra_position_list.append('CH')
        if '下肢' in symptom:
            extra_position_list.append('C1')
            extra_position_list.append('CV')

        if '小腿' in symptom:
            extra_position_list.append('C0')
            extra_position_list.append('C6')

        if '大腿' in symptom:
            extra_position_list.append('CZ')
            extra_position_list.append('C5')

        if '四肢' in symptom:
            extra_position_list.append('CO')
            extra_position_list.append('CH')
            extra_position_list.append('C1')
            extra_position_list.append('CV')

        if '前軀幹' in symptom:
            extra_position_list.append('CC')

        if '後軀幹' in symptom:
            extra_position_list.append('CD')

        if '右前臂' in symptom:
            extra_position_list.append('CS')
        if '左前臂' in symptom:
            extra_position_list.append('CL')
        if '兩前臂' in symptom:
            extra_position_list.append('CS')
            extra_position_list.append('CL')

        if '右肩' in symptom:
            extra_position_list.append('CU')
        if '左肩' in symptom:
            extra_position_list.append('CN')
        if '兩肩' in symptom:
            extra_position_list.append('CU')
            extra_position_list.append('CN')

        if '右膝' in symptom:
            extra_position_list.append('C4')
        if '左膝' in symptom:
            extra_position_list.append('CY')
        if '兩膝' in symptom:
            extra_position_list.append('C4')
            extra_position_list.append('CY')

        if '髖關節' in symptom or '臗關節' in symptom:
            extra_position_list.append('CG')

        if '頸椎' in symptom:
            extra_position_list.append('CB')

        if '部位' in symptom and '頭' in symptom:
            extra_position_list.append('CA')

        return extra_position_list

    def _set_treat_position(self, row):
        position_list = []
        position1 = string_utils.xstr(row['Position1']).split(' ')[0][:2].strip()
        position2 = string_utils.xstr(row['Position2']).split(' ')[0][:2].strip()

        if position1 != '9':
            position_list.append(position1)
        if position2 != '9':
            position_list.append(position2)

        extra_position_list = self._get_extra_position_list(row['Symptom'])
        position_list += extra_position_list

        if len(position_list) == 0:
            return

        fields = [
            'CaseKey', 'CaseDate', 'MedicineSet', 'MedicineType', 'MedicineName',
        ]
        self.database.exec_sql(f'''
            DELETE FROM prescript
            WHERE
                CaseKey = {row["CaseKey"]} AND
                MedicineSet = 1 AND
                MedicineType = "處置" AND
                MedicineName LIKE "治療部位:%"
        ''')
        for position in position_list:
            if position in ['', None]:
                continue

            try:
                position = nhi_utils.POSTION_NAME_DICT[position]
            except Exception:
                try:
                    position = nhi_utils.OLD_POSITION_NAME_DICT[position]
                except Exception:
                    return
                    
            position = f'治療部位:{position}'
            data = [row['CaseKey'], row['CaseDate'], 1, '處置', position]
            self.database.insert_record('prescript', fields, data)

    def _cvt_medical_patient(self):
        self.parent.ui.label_progress.setText('病患基本資料檔轉檔')
        self.progress_bar.setMaximum(4)
        self.progress_bar.setValue(0)

        sql = 'UPDATE patient SET Gender = Sex WHERE Sex IS NOT NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE patient SET Allergy = Alergy WHERE Alergy IS NOT NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE patient SET InsType = "基層醫療" WHERE InsType = "健保"'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE patient SET Nationality = "本國" WHERE SUBSTRING(ID, 2, 1) IN ("1", "2") AND Nationality IS NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = '''
            UPDATE patient
            SET
                Nationality = "外國"
            WHERE
                SUBSTRING(ID, 2, 1) NOT IN ("1", "2") AND Nationality IS NULL
        '''
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

    def _cvt_medical_cases(self):
        self.parent.ui.label_progress.setText('Medical病歷檔轉檔')
        self.progress_bar.setMaximum(7)
        self.progress_bar.setValue(0)

        sql = 'UPDATE cases SET SDiagShareFee = ReceiptShare WHERE ReceiptShare IS NOT NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET Cashier = Casher WHERE Casher IS NOT NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET DiagShareFee = TreatShare WHERE TreatShare IS NOT NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET DrugShareFee = DrugShare WHERE DrugShare IS NOT NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET RefundFee = Refund WHERE Refund IS NOT NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET SMaterialFee = SMaterial WHERE SMaterial IS NOT NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "內科" WHERE TreatType IS NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = '''
            UPDATE cases
            SET
                ChargeDone = "True", ChargeDate = DoctorDate, ChargePeriod = Period
            WHERE
                DoctorDone = "True"
        '''
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

    def _cvt_medical_dosage(self):
        self.parent.ui.label_progress.setText('處方用藥轉檔')
        sql = 'TRUNCATE dosage'
        self.database.exec_sql(sql)

        self._cvt_medical_dosage_by_cases()
        self._cvt_medical_dosage_by_caseextend()

    def _cvt_medical_case_duration(self, start_date, end_date):
        self.parent.ui.label_progress.setText('Medical病歷檔轉檔')
        self.progress_bar.setMaximum(7)
        self.progress_bar.setValue(0)

        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}"
                ORDER BY CaseKey
        '''
        rows = self.utec_db.select_record(sql)
        for row in rows:
            print(row)

        sql = f'''
            UPDATE cases SET
                SDiagShareFee = ReceiptShare
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                ReceiptShare IS NOT NULL
        '''
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = f'''
            UPDATE cases
            SET
                Cashier = Casher
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                Casher IS NOT NULL
        '''
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = f'''
            UPDATE cases SET
                DiagShareFee = TreatShare
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                TreatShare IS NOT NULL
        '''
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = '''
            UPDATE cases SET DrugShareFee = DrugShare WHERE DrugShare IS NOT NULL'''
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET RefundFee = Refund WHERE Refund IS NOT NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET SMaterialFee = SMaterial WHERE SMaterial IS NOT NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'UPDATE cases SET TreatType = "內科" WHERE TreatType IS NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = '''
            UPDATE cases
            SET
                ChargeDone = "True", ChargeDate = DoctorDate, ChargePeriod = Period
            WHERE
                DoctorDone = "True"
        '''
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

    def _cvt_medical_dosage_by_cases(self):
        sql = '''
            SELECT
                CaseKey,
                Package1, Package2, Package3,
                PresDays1, PresDays2, PresDays3,
                Instruction1, Instruction2, Instruction3
             FROM cases
             ORDER BY CaseKey
        '''

        rows = self.source_db.select_record(sql)

        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)
        fields = ['CaseKey', 'MedicineSet', 'Packages', 'Days', 'Instruction']
        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)
            for i in range(1, 4):
                if row[f'Package{i}'] is not None or row[f'PresDays{i}'] is not None:
                    data = [
                        row['CaseKey'],
                        i,
                        row[f'Package{i}'],
                        row[f'PresDays{i}'],
                        row[f'Instruction{i}']
                    ]
                    self.database.insert_record('dosage', fields, data)

    def _cvt_medical_dosage_by_caseextend(self):
        sql = '''
            SELECT *
             FROM caseextend
             WHERE
                ExtendType IN ("藥日4", "藥日5", "藥日6", "藥包4", "藥包5", "藥包6", "指示4", "指示5", "指示6") AND
                (Content IS NOT NULL AND LENGTH(Content) > 0) AND
                Content NOT LIKE "ComboBox%"
             ORDER BY CaseKey
        '''

        rows = self.source_db.select_record(sql)
        if len(rows) <= 0:
            return

        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)
        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            if string_utils.xstr(row['ExtendType'])[:2] == '藥日':
                field = 'Days'
            elif string_utils.xstr(row['ExtendType'])[:2] == '藥包':
                field = 'Packages'
            elif string_utils.xstr(row['ExtendType'])[:2] == '指示':
                field = 'Instruction'
            else:
                continue

            medicine_set = string_utils.xstr(row['ExtendType'])[2]

            case_key = row['CaseKey']
            sql = f'''
                SELECT * FROM dosage
                WHERE
                    CaseKey = {case_key} AND
                    MedicineSet = {medicine_set}
            '''
            dosage_rows = self.database.select_record(sql)
            value = string_utils.xstr(row['Content'])
            if field in ['Days', 'Packages'] and not value.isdigit():
                value = 0

            if len(dosage_rows) > 0:
                dosage_key = dosage_rows[0]['DosageKey']
                self.database.exec_sql(f'''
                    UPDATE dosage
                    SET
                        {field} = "{value}"
                    WHERE
                        DosageKey = {dosage_key}
                ''')
            else:
                fields = ['CaseKey', 'MedicineSet', field]
                data = [
                    row['CaseKey'], medicine_set, value,
                ]
                self.database.insert_record('dosage', fields, data)

    def _cvt_medical_reserve(self):
        self.parent.ui.label_progress.setText('預約掛號檔轉檔')
        self.progress_bar.setMaximum(2)
        self.progress_bar.setValue(0)

        sql = 'UPDATE reserve SET ReserveNo = Sequence WHERE Sequence IS NOT NULL'
        self.database.exec_sql(sql)
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        sql = 'SELECT Name, Room FROM person WHERE Position IN ("醫師", "支援醫師") AND Room IS NOT NULL'
        rows = self.database.select_record(sql)
        for row in rows:
            room = row['Room']
            doctor = string_utils.xstr(row['Name'])
            sql = f'UPDATE reserve SET Doctor = "{doctor}" WHERE Room  = {room}'
            self.database.exec_sql(sql)

        self.progress_bar.setValue(self.progress_bar.value() + 1)

    def _cvt_address_list(self):
        self.parent.ui.label_progress.setText('地址郵遞區號轉檔')
        self.progress_bar.setMaximum(61034)
        self.progress_bar.setValue(0)

        self.database.exec_sql('truncate address_list')

        fields = ['ZipCode', 'City', 'District', 'Street', 'MailRange']
        import csv
        f = open('zip_code.csv', 'r', encoding='utf8')
        for row in csv.DictReader(f):
            try:
                data = [row['郵遞區號'], row['縣市名稱'], row['鄉鎮市區'], row['原始路名'], row['投遞範圍']]
                self.database.insert_record('address_list', fields, data)
            except Exception:
                pass

            self.progress_bar.setValue(self.progress_bar.value() + 1)

    def _cvt_certificate(self):
        rows = self.database.select_record('SELECT * FROM proof ORDER BY ProofKey')
        row_count = len(rows)

        self.parent.ui.label_progress.setText('診斷及收費證明轉檔')
        self.progress_bar.setMaximum(row_count)
        self.progress_bar.setValue(0)

        self.database.exec_sql('truncate certificate')

        fields = [
            'CertificateKey', 'CaseKey', 'PatientKey', 'Name', 'CertificateDate', 'CertificateType',
            'InsType', 'StartDate', 'EndDate', 'Doctor', 'Diagnosis', 'DoctorComment',

        ]
        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)
            patient_key = row['PatientKey']
            start_date = row['StartDate']
            start_date = f'{start_date} 00:00:00'
            end_date = row['StopDate']
            end_date = f'{end_date} 23:59:59'
            sql = f'''
                SELECT CaseKey, Doctor FROM cases
                WHERE
                    CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                    PatientKey = {patient_key}
            '''
            case_rows = self.database.select_record(sql)
            if len(case_rows) <= 0:
                case_key = 0
                doctor = None
            else:
                case_key = case_rows[0]['CaseKey']
                doctor = string_utils.xstr(case_rows[0]['Doctor'])

            data = [
                row['ProofKey'],
                case_key,
                row['PatientKey'],
                row['Name'],
                row['ProofDate'],
                row['ProofType'],
                row['InsType'],
                row['StartDate'],
                row['StopDate'],
                doctor,
                string_utils.get_str(row['Disease'], 'utf8'),
                string_utils.get_str(row['Diagnosis'], 'utf8'),
            ]

            self.database.insert_record('certificate', fields, data)

    def _cvt_disease_common(self):
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.parent.ui.label_progress.setText('病名詞庫常用類別轉檔')
        cvt_groups.cvt_disease_common(self.database)
        self.progress_bar.setValue(100)

    def _cvt_disease_treat(self):
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.parent.ui.label_progress.setText('病名詞庫傷骨科類別轉檔')
        cvt_groups.cvt_disease_treat(self.database)
        self.progress_bar.setValue(100)

    def _cvt_medical_commission(self):
        sql = '''
            SELECT * FROM medextend
            WHERE
                ExtendType = "抽成比例"
            ORDER BY MedicineKey
        '''

        rows = self.source_db.select_record(sql)

        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)
            medicine_key = row['MedicineKey']
            commission = row['Description']
            if medicine_key is None or commission is None:
                continue

            commission = f'{commission}%'
            self.database.exec_sql(f'''
                UPDATE medicine
                SET
                    Commission = "{commission}"
                WHERE
                    MedicineKey = {medicine_key}
            ''')

        self.progress_bar.setValue(len(rows))

    def _cvt_medical_project(self):
        sql = '''
            SELECT * FROM medextend
            WHERE
                ExtendType = "專案"
            ORDER BY MedicineKey
        '''

        rows = self.source_db.select_record(sql)

        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)
            medicine_key = row['MedicineKey']
            project = row['Description']
            if medicine_key is None or project is None:
                continue

            self.database.exec_sql(f'''
                UPDATE medicine
                SET
                    Project = "{project}"
                WHERE
                    MedicineKey = {medicine_key}
            ''')

        self.progress_bar.setValue(len(rows))

    def _cvt_self_drug_type(self):
        rows = self.database.select_record('SELECT DrugType FROM drugtype ORDER BY DrugTypeKey')
        fields = ['DictGroupsType', 'DictGroupsName']
        for row in rows:
            drug_type = string_utils.xstr(row['DrugType'])
            dict_rows = self.database.select_record(
                f'SELECT DictGroupsKey FROM dict_groups WHERE DictGroupsName = "{drug_type}"'
            )
            if len(dict_rows) > 0:
                continue

            data = ['藥品類別', drug_type]
            self.database.insert_record('dict_groups', fields, data)

    def _cvt_self_drug(self):
        self._cvt_self_drug_type()

        rows = self.database.select_record('SELECT * FROM selfdrug ORDER BY DrugKey')
        row_count = len(rows)

        self.parent.ui.label_progress.setText('自費系統處方檔')
        self.progress_bar.setMaximum(row_count)
        self.progress_bar.setValue(0)

        fields = [
            'MedicineType', 'MedicineCode', 'InputCode', 'MedicineName', 'Unit', 'Location',
            'SalePrice', 'InPrice', 'Quantity', 'SafeQuantity', 'Description', 'Commission',
        ]
        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)

            bonus = number_utils.get_integer(row['Bonus1'])
            ratio = number_utils.get_integer(row['Ratio1'])
            if ratio > 0:
                commission = f"{ratio}%"
            elif bonus > 0:
                commission = bonus
            else:
                commission = None

            data = [
                row['DrugType'],
                row['DrugCode'],
                row['InputCode'],
                row['DrugName'],
                row['Unit'],
                row['Location'],
                row['SalePrice'],
                row['InPrice'],
                row['Quantity'],
                row['SafeQuantity'],
                row['Description'],
                commission,
            ]
            medicine_key = self.database.insert_record('medicine', fields, data)

            ratio2 = number_utils.get_integer(row['Ratio2'])
            bonus2 = number_utils.get_integer(row['Bonus2'])
            if ratio2 > 0:
                self._convert_commission(medicine_key, '推拿師父', ratio2, '%')
                self._convert_commission(medicine_key, '櫃台', ratio2, '%')
            elif bonus2 > 0:
                self._convert_commission(medicine_key, '推拿師父', bonus2)
                self._convert_commission(medicine_key, '櫃台', bonus2)

            ratio3 = number_utils.get_integer(row['Ratio3'])
            ratio4 = number_utils.get_integer(row['Ratio4'])
            if ratio3 > 0:
                self._convert_commission(medicine_key, '醫師分成', ratio3, '%')
            if ratio4 > 0:
                self._convert_commission(medicine_key, '推拿師父分成', ratio4, '%')
                self._convert_commission(medicine_key, '櫃台分成', ratio4, '%')

            ratio5 = number_utils.get_integer(row['Ratio5'])
            ratio6 = number_utils.get_integer(row['Ratio6'])
            if ratio5 > 0:
                self._convert_commission(medicine_key, '廠房', ratio5, '%')
            elif ratio6 > 0:
                self._convert_commission(medicine_key, '廠房', ratio5)

    def _convert_commission(self, medicine_key, name, commission, commission_type=''):
        if commission is None:
            commission = 0

        if commission_type == '%':
            commission = f'{commission}%'

        fields = ['MedicineKey', 'Name', 'Commission']
        data = [medicine_key, name, commission]
        self.database.insert_record('commission', fields, data)

    def _cvt_users(self):
        self.parent.ui.label_progress.setText('使用者資料轉檔')
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        self.database.exec_sql('''
            UPDATE person
            SET
                Position = "推拿師父"
            WHERE
                Position = "理療師"
        ''')

        self.progress_bar.setValue(100)

    def _cvt_pathologic(self):
        self.parent.ui.label_progress.setText('診前檢查資料轉檔')

        extension_type = '診前檢查'

        rows = self.database.select_record('SELECT * FROM pathologic')
        self.progress_bar.setMaximum(len(rows))
        self.progress_bar.setValue(0)

        fields = [
            'CaseKey', 'ExtensionType', 'Content',
        ]
        for row in rows:
            self.progress_bar.setValue(self.progress_bar.value() + 1)
            case_key = row['CaseKey']
            self.database.exec_sql(f'''
                DELETE FROM case_extension
                WHERE
                    CaseKey = {case_key} AND
                    ExtensionType = "{extension_type}"
            ''')

            exam_precheck_dict = {
                'height': string_utils.xstr(row['Height']),
                'weight': string_utils.xstr(row['Weight']),
                'heartbeat': string_utils.xstr(row['HeartBeat']),
                'bph': string_utils.xstr(row['BPHigh']),
                'bpl': string_utils.xstr(row['BPLow']),
            }
            exam_precheck_json = json.dumps(exam_precheck_dict, indent=4)

            data = [case_key, extension_type, exam_precheck_json]
            self.database.insert_record('case_extension', fields, data)

        self.progress_bar.setValue(100)

    def convert_images(self):
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory(
            self.parent, "選擇影像資料路徑", '', options=options
        )
        if not directory:
            return

        source_files = [
            f for f in listdir(directory)
            if os.path.isfile(os.path.join(directory, f))
        ]

        i = 1
        fields = ['CaseKey', 'PatientKey', 'FileName']
        self.parent.ui.label_progress.setText('影像資料轉檔')
        self.progress_bar.setMaximum(len(source_files))
        self.progress_bar.setValue(0)
        for filename in source_files:
            try:
                if 'P' in filename:
                    continue
                elif 'C' in filename:
                    case_key = filename.split('C')[1].split('.')[0]
                    case_key = number_utils.get_integer(case_key)
                    patient_key = 0
                    sequence = 1
                else:
                    case_key = filename.split('病歷鍵')[1].split('-')[0]
                    case_key = number_utils.get_integer(case_key)
                    patient_key = int(filename.split('系統號')[1].split('病歷鍵')[0])
                    sequence = filename.split('病歷鍵')[1].split('-')[1]
                    sequence = sequence.split('.')[0]
            except IndexError:
                continue

            new_filename = f'{case_key}-{int(sequence)}.jpg'

            data = [case_key, patient_key, new_filename]
            self.database.insert_record('images', fields, data)

            source_filename = os.path.join(directory, filename)
            dest_filename = os.path.join(directory, new_filename)
            os.rename(source_filename, dest_filename)
            self.progress_bar.setValue(self.progress_bar.value() + 1)
