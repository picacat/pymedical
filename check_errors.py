# -*- coding: UTF-8 -*-
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (case_utils, charge_utils, class_utils, date_utils, nhi_utils,
                  number_utils, personnel_utils, prescript_utils, string_utils,
                  system_utils, ui_utils, validator_utils)


# 欄位錯誤檢查 2018.01.31
class CheckErrors(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(CheckErrors, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = int(args[2])
        self.apply_month = int(args[3])
        self.apply_type = args[4]
        self.start_date = args[5]
        self.end_date = args[6]
        self.check_empty_symptom = args[7]
        self.ui = None
        self.doctor_list = personnel_utils.get_person(self.database, '醫師')
        self.check_chronic_pres_days = self.system_settings.field('慢性病開藥檢查')
        self.no_massage = self.system_settings.field('不申報傷科治療')

        self.rows = None

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_CHECK_ERRORS, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self._set_table_widget()

    def _set_table_widget(self):
        self.table_widget_errors = class_utils.get_table_widget(self.ui.tableWidget_errors, self.database)
        self.table_widget_errors.set_column_hidden([0])
        width = [
            100, 130, 60, 90, 90, 130, 150, 100, 80, 100,
            90, 70, 60, 70, 70, 90, 90, 90, 400,
        ]
        self.table_widget_errors.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_errors.doubleClicked.connect(self.open_medical_record)
        self.ui.toolButton_calculate_ins_fee.clicked.connect(self._calculate_ins_fee)
        self.ui.toolButton_correct_error.clicked.connect(self._correct_errors)
        # database.ui.action_close.triggered.connect(database.close_app)

    def open_medical_record(self):
        case_key = self.table_widget_errors.field_value(0)
        self.parent.open_medical_record(case_key)

    def read_data(self):
        if self.start_date is not None:
            start_date = self.start_date
        else:
            start_date = date_utils.get_start_date_by_year_month(
                self.apply_year, self.apply_month)

        if self.end_date is not None:
            end_date = self.end_date
        else:
            end_date = date_utils.get_end_date_by_year_month(
                self.apply_year, self.apply_month)

        apply_type_sql = nhi_utils.get_apply_type_sql(self.apply_type)

        sql = f'''
            SELECT
                CaseKey, CaseDate, Period, cases.PatientKey, cases.Name, RegistType, Card, Continuance, Doctor,
                cases.InsType, TreatType, Treatment, ApplyType, cases.Share, Injury, TourArea, Symptom,
                DiseaseCode1, DiseaseCode2, DiseaseCode3, DiseaseCode4,
                DiseaseName1, DiseaseName2, DiseaseName3, DiseaseName4,
                RegistFee, InterDrugFee, DiagFee, PharmacyFee,  AcupunctureFee, MassageFee, DislocateFee, ExamFee,
                InsTotalFee, InsApplyFee, AgentFee, DiagShareFee, DrugShareFee,
                PharmacyType, SpecialCode,
                patient.Birthday, patient.ID, patient.InsType AS PatientInsType
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
                (cases.InsType = "健保") AND
                (({apply_type_sql}) OR (ApplyType IS NULL) OR (LENGTH(ApplyType) <= 0))
            ORDER BY CaseDate
        '''
        self.rows = self.database.select_record(sql)

    def row_count(self):
        return len(self.rows)

    def start_check(self):
        self.read_data()

        if self.row_count() <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            '正在執行欄位錯誤檢查中, 請稍後...', '取消', 0, self.row_count(), self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        self.ui.tableWidget_errors.setRowCount(0)
        for row_no, row in enumerate(self.rows):
            error_messages = []
            error_messages += self._check_patient(row)
            error_messages += self._check_medical_record(row)
            error_messages += self._check_prescript(row)
            error_messages += self._check_charge(row)
            error_messages += self._check_care(row)
            error_messages += self._check_highly_complicated_massage_duration(row)
            error_messages += self._check_invalid_gender_disease(row)
            error_messages += self._check_duplicate_treat(row)

            if len(error_messages) > 0:
                self._insert_error_record(row, error_messages)

            progress_dialog.setValue(row_no)

        progress_dialog.setValue(len(self.rows))

        self.ui.tableWidget_errors.setAlternatingRowColors(True)

        if self.error_count() <= 0:
            self.ui.toolButton_calculate_ins_fee.setEnabled(False)
        else:
            self.ui.toolButton_calculate_ins_fee.setEnabled(True)

        self.ui.tableWidget_errors.resizeRowsToContents()

    def error_count(self):
        return self.ui.tableWidget_errors.rowCount()

    def _insert_error_record(self, row, error_messages):
        row_no = self.ui.tableWidget_errors.rowCount()
        self.ui.tableWidget_errors.setRowCount(row_no + 1)
        card = string_utils.xstr(row['Card']) \
            if string_utils.xstr(row['Continuance']) == '' \
            else string_utils.xstr(row['Card']) + '-' + string_utils.xstr(row['Continuance'])
        year = row['CaseDate'].year
        month = row['CaseDate'].month
        day = row['CaseDate'].day
        error_record = [
            string_utils.xstr(row['CaseKey']),
            f'{year}-{month:0>2}-{day:0>2}',
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Birthday']),
            string_utils.xstr(row['ID']),
            string_utils.xstr(row['Share']),
            card,
            string_utils.xstr(row['DiseaseCode1']),
            string_utils.xstr(row['Doctor']),
            string_utils.xstr(row['DiagFee']),
            string_utils.xstr(row['InterDrugFee']),
            string_utils.xstr(row['PharmacyFee']),
            string_utils.xstr(
                number_utils.get_integer(row['AcupunctureFee']) +
                number_utils.get_integer(row['MassageFee']) +
                number_utils.get_integer(row['DislocateFee'])
            ),
            string_utils.xstr(row['DiagShareFee']),
            string_utils.xstr(row['DrugShareFee']),
            string_utils.xstr(row['InsApplyFee']),
            ', '.join(error_messages),
        ]
        for column_no in range(len(error_record)):
            self.ui.tableWidget_errors.setItem(
                row_no, column_no,
                QtWidgets.QTableWidgetItem(error_record[column_no])
            )
            if column_no in [3, 11, 12, 13, 14, 15, 16, 17]:
                self.ui.tableWidget_errors.item(
                    row_no, column_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
        color = QtGui.QColor('red')
        self.ui.tableWidget_errors.item(row_no, 18).setForeground(color)

    def _check_patient(self, row):
        error_messages = []

        if self._check_patient_error_exists(row['PatientKey']):
            return error_messages

        rows = self.database.select_record(
            f"SELECT PatientKey FROM patient WHERE PatientKey = {row['PatientKey']}"
        )
        if len(rows) <= 0:
            error_messages.append('病患資料不存在')
            return error_messages

        if string_utils.xstr(row['Name']) == '':
            error_messages.append('姓名空白')

        try:
            if row['Birthday'].year <= 1900:
                error_messages.append('生日不合理')
            elif row['Birthday'] > row['CaseDate'].date():
                error_messages.append('生日不合理')
            else:
                share = string_utils.xstr(row['Share'])
                age_year, _ = date_utils.get_age(row['Birthday'], row['CaseDate'])
                if age_year < 3 and share == '基層醫療' and share != '三歲兒童':
                    error_messages.append('應申報三歲以下兒童')
                elif age_year >= 3 and share == '三歲兒童':
                    error_messages.append('不得申報三歲以下兒童')
        except Exception:
            if string_utils.xstr(row['Birthday']) == '':
                error_messages.append('生日空白')

        if string_utils.xstr(row['ID']) == '':
            error_messages.append('身分證空白')
        elif len(row['ID']) != 10:
            error_messages.append('身分證長度有誤')
        elif not validator_utils.verify_id(string_utils.xstr(row['ID'])):
            error_messages.append('身份證編碼錯誤')

        if string_utils.xstr(row['InsType']) == '':
            error_messages.append('保險類別空白')

        return error_messages

    def _check_patient_error_exists(self, patient_key):
        for row_no in range(self.ui.tableWidget_errors.rowCount()):
            if self.ui.tableWidget_errors.item(row_no, 3).text() == string_utils.xstr(patient_key):
                return True

        return False

    def _check_treatment(self, row):
        error_message = None

        case_key = row['CaseKey']
        treat_type = string_utils.xstr(row['TreatType'])
        treatment = string_utils.xstr(row['Treatment'])
        correct_treat_type = self._get_treat_type(case_key)

        sql = f'''
            SELECT PrescriptKey FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                MedicineType IN ("穴道", "處置")
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if treatment == '' and len(rows) > 0:
            error_message = '有處置方式無健保處置醫令'
        elif treatment != '' and len(rows) <= 0:
            error_message = '有健保處置醫令無處置方式'

        # if treat_type != correct_treat_type:
        #     error_message = '就醫類別錯誤'

        return error_message

    def _check_medical_record(self, row):
        error_messages = []

        case_key = row['CaseKey']
        patient_key = string_utils.xstr(row['PatientKey'])
        name = string_utils.xstr(row['Name'])
        period = string_utils.xstr(row['Period'])
        card = string_utils.xstr(row['Card'])
        course = number_utils.get_integer(row['Continuance'])
        treatment = string_utils.xstr(row['Treatment'])
        # patient_share_type = string_utils.xstr(row['PatientInsType'])
        share_type = string_utils.xstr(row['Share'])
        injury_type = string_utils.xstr(row['Injury'])
        regist_type = string_utils.xstr(row['RegistType'])
        treat_type = string_utils.xstr(row['TreatType'])
        tour_area = string_utils.xstr(row['TourArea'])
        case_date = row['CaseDate']
        # seq_number = case_utils.extract_security_xml(row['Security'], '健保卡序')
        treatment_message = self._check_treatment(row)

        if treatment_message is not None:
            error_messages.append(treatment_message)

        if '傷科' in treat_type and self.no_massage == 'Y':
            error_messages.append('不申報傷科治療')
        if '合併中度傷科' in treat_type and '中度傷科' not in treatment:
            error_messages.append('治療處置缺少中度傷科')
        if '合併高度傷科' in treat_type and '高度傷科' not in treatment:
            error_messages.append('治療處置缺少高度傷科')

        if row['ApplyType'] not in nhi_utils.APPLY_TYPE:
            error_messages.append('申報類別有誤')
        elif row['ApplyType'] is None:
            error_messages.append('申報類別空白')

        if case_utils.get_case_extend(self.database, case_key, '整合醫療照護') == 'Y':
            if course >= 2:
                error_messages.append('療程2-6次不可申報整合醫療照護')

            symptom = string_utils.get_str(row['Symptom'], 'utf-8') 
            check_list = ['診療及衛教時間', '衛教方式', '衛教內容']
            error_list = []
            for keyword in check_list:
                if keyword not in symptom:
                    error_list.append(keyword)
                    
            if len(error_list) > 0:
                error_messages.append(f"整合醫療照護缺少{', '.join(error_list)}")

        if row['RegistType'] in nhi_utils.TOUR_FAR and row['TourArea'] is None:
            error_messages.append('巡迴醫療無巡迴地區')

        if treat_type == '醫療諮詢':
            error_messages.append('問診')
        if treat_type == '內科' and treatment not in ['', None]:
            error_messages.append('就醫類別錯誤')

        # if patient_share_type == '重大傷病' and patient_share_type != share_type:
        #     error_messages.append('重大傷病負擔類別不一致')

        if string_utils.xstr(row['Share']) == '其他免部份負擔':
            error_messages.append('負擔類別錯誤')

        if card != '欠卡' and len(card) < 4:
            error_messages.append('卡序長度不足4碼')

        if injury_type == '':
            error_messages.append('無傷病類別')

        if regist_type in nhi_utils.TOUR_TYPE_WITH_GOTO_LACK_AREA and tour_area == '':
            error_messages.append('無巡迴或資源不足地區')

        if case_date.strftime('%Y-%m-%d') >= '2023-03-20' and card == 'HVIT':
            error_messages.append('2023-03-20以後禁用HVIT')

        if '\n' in name:
            error_messages.append('姓名內含換行字元')

        if course >= 1:
            start_date = case_utils.get_course_start_date(self.database, patient_key, row['CaseDate'], card, course)
            if start_date < nhi_utils.INS_TREAT_2021_DATE and \
                    treatment in nhi_utils.ACUPUNCTURE_TREAT_2021 + \
                    nhi_utils.MASSAGE_TREAT_2021 + \
                    nhi_utils.DISLOCATE_TREAT_2021:
                error_messages.append('處置錯誤:應申報舊版處置')
            elif start_date >= nhi_utils.INS_TREAT_2021_DATE and \
                    treatment in nhi_utils.ACUPUNCTURE_TREAT_2020 + \
                    nhi_utils.MASSAGE_TREAT_2020 + \
                    nhi_utils.DISLOCATE_TREAT_2020:
                error_messages.append('處置錯誤:應申報新版處置')
            if course >= 2:
                if treatment in [
                    '中度複雜性傷科', '中度針灸合併中度傷科', '高度針灸合併中度傷科'
                    '高度複雜性傷科', '中度針灸合併高度傷科起始次', '高度針灸合併高度傷科起始次'
                ]:
                    error_messages.append('療程2-6次不得申報中度複雜性傷科首次或高度複雜性傷科起始次')
            else:
                if treatment in [
                    '中度針灸合併中度傷科療程2-6次', '高度針灸合併中度傷科療程2-6次'
                ]:
                    error_messages.append('療程首次不得申報中度複雜性傷科療程2-6次')

            if treatment in [
                '中度針灸合併高度傷科療程2-6次',
            ]:
                error_messages.append('請改為中度針灸合併高度傷科後續治療')
            elif treatment in [
                '高度針灸合併高度傷科療程2-6次'
            ]:
                error_messages.append('請改為高度針灸合併高度傷科後續治療')
            elif treatment in [
                '中度針灸合併高度傷科'
            ]:
                error_messages.append('請改為中度針灸合併高度傷科起始次')
            elif treatment in [
                '高度針灸合併高度傷科'
            ]:
                error_messages.append('請改為高度針灸合併高度傷科起始次')

        # if course == 1 and share_type != '山地離島' and case_utils.is_last_month_course_duplicated(
        #     self.database, string_utils.xstr(row['PatientKey']), case_date, card
        # ):
        #     error_messages.append('療程錯誤:應續上月療程')

        if period not in ['早班', '午班', '晚班']:
            error_messages.append('班別有誤')

        if card == '':
            error_messages.append('卡序空白')
        elif card == '欠卡':
            error_messages.append('欠卡未還')
        elif len(card) >= 6:
            error_messages.append('卡序過長')
        elif not card.isnumeric():
            card = card[:4]
            available_card = (
                nhi_utils.ABNORMAL_CARD +
                [nhi_utils.OCCUPATIONAL_INJURY_CARD] +
                [nhi_utils.INFECTIOUS_INJURY_CARD]
            )
            if card[0] in ['M', 'V', 'W']:  # 居家醫療、虛擬健保卡
                pass
            elif card not in available_card:
                error_messages.append('卡序錯誤')
        # elif seq_number is not None and seq_number != '' and card != seq_number and course <= 0:
        #     error_messages.append('卡序與健保卡就醫序號不一致')

        if card == 'Z000' and (share_type in nhi_utils.INFECTIOUS_TYPE or injury_type in nhi_utils.INFECTIOUS_TYPE):
            error_messages.append('請將卡序改為HVIT')

        if string_utils.xstr(row['Doctor']) == '':
            error_messages.append('無醫師')
        elif string_utils.xstr(row['Doctor']) not in self.doctor_list:
            error_messages.append('非醫師')

        if (treatment in nhi_utils.INS_TREAT and
                string_utils.xstr(row['TreatType']) in nhi_utils.INS_TREAT and
                number_utils.get_integer(row['Continuance']) < 1):
            error_messages.append('無療程序號')

        if (number_utils.get_integer(row['Continuance']) >= 1 and
                treatment not in nhi_utils.INS_TREAT):
            error_messages.append('療程內無處置')

        if (string_utils.xstr(row['TreatType']) in nhi_utils.TREAT_DICT and
                string_utils.xstr(row['Treatment']) not in nhi_utils.INS_TREAT):
            error_messages.append('就醫類別錯誤')

        if string_utils.xstr(row['DiseaseCode1']) == '':
            error_messages.append('無主診斷碼')
        else:
            pres_days = case_utils.get_pres_days(self.database, row['CaseKey'])
            treat_type = string_utils.xstr(row['TreatType'])

            disease_list = [
                string_utils.xstr(row['DiseaseCode1']),
                string_utils.xstr(row['DiseaseCode2']),
                string_utils.xstr(row['DiseaseCode3']),
                string_utils.xstr(row['DiseaseCode4']),
            ]
            special_code = ''
            for i in range(len(disease_list)):
                disease_code = disease_list[i]
                special_code = case_utils.get_disease_special_code(
                    self.database, disease_code,
                )
                if special_code != '':
                    break

            # if case_utils.get_case_extend(self.database, case_key, '不申報慢性病') == 'Y':
            #     pass
            # elif special_code != '' and string_utils.xstr(row['SpecialCode']).strip() == '':
            #     error_messages.append('診斷碼為慢性病但病歷無慢性病代碼')

            # if special_code == '' and treat_type == '內科' and \
            #    share_type not in nhi_utils.INFECTIOUS_INJURY_TYPE and pres_days > 7:
            #     error_messages.append('診斷碼非慢性病但內科開藥超過七日')

            if case_utils.get_case_extend(self.database, case_key, '不申報慢性病') == 'Y':
                pass
            elif self.check_chronic_pres_days == 'Y' and \
                    special_code != '' and treat_type == '內科' and 1 <= pres_days <= 7:
                error_messages.append('診斷碼為慢性病但內科開藥少於八日')

            for i in range(1, nhi_utils.MAX_DISEASE_CODE + 1):
                disease_code = string_utils.xstr(row[f'DiseaseCode{i}'])
                disease_name = string_utils.xstr(row[f'DiseaseName{i}'])
                if disease_name == '白帶' and disease_code == '12':
                    disease_code = 'N899'
                    self.database.exec_sql(
                        f'''UPDATE cases
                            SET
                                DiseaseCode{i} = "{disease_code}"
                            WHERE
                                CaseKey = {case_key} AND
                                DiseaseCode{i} = "12"
                    ''')

                if disease_code != '' and disease_code[0] in [str(i) for i in range(10)]:
                    if i == 1:
                        disease_name = '主診斷碼'
                    else:
                        disease_name = f'次診斷{i-1}'

                    error_messages.append(f'{disease_name}非ICD10碼')

                # if disease_code[:1] in ['W', 'X', 'Y', 'Z']:
                #     if i == 1:
                #         disease_name = '主診斷碼'
                #     else:
                #         disease_name = f'次診斷{i-1}'

                #     error_messages.append(f'{disease_name}不可申報')

                if disease_code != '' and not case_utils.is_disease_code_exist(self.database, disease_code):
                    disease_code = self._correct_invalid_disease(case_key, i)
                    if disease_code is None:
                        error_messages.append(f'診斷碼 {disease_code} 無效')

                if disease_code != '' and disease_name == '':
                    error_messages.append(f'診斷碼 {disease_code} 不完整')

        if (injury_type in nhi_utils.INFECTIOUS_TYPE or share_type in nhi_utils.INFECTIOUS_TYPE):
            if string_utils.xstr(row['DiseaseCode1']) != 'U071':
                error_messages.append('非COVID-19確診病名部份負擔類別不得申報法定傳染病隔離通報')

            infectious_date = case_utils.get_case_extend(self.database, row['CaseKey'], '確診日期')
            if infectious_date is None:
                error_messages.append('請輸入確診日期')
            else:
                try:
                    infectious_date = date_utils.str_to_date(infectious_date[:10])
                    if infectious_date > row['CaseDate'].date():
                        error_messages.append('確診日期不合理')
                except Exception:
                    error_messages.append('請輸入確診日期')

        if not case_utils.check_treatment_disease(
            self.parent.parent.moderate_complicated_acupuncture_list,
            self.parent.parent.highly_complicated_acupuncture_list,
            self.parent.parent.moderate_complicated_massage_list,
            self.parent.parent.highly_complicated_massage_list,
            self.parent.parent.dislocate_list,
            self.parent.parent.fracture_list,
            self.parent.parent.special_disease_list,
            row
        ):
            treatment = string_utils.xstr(row['Treatment'])
            error_messages.append(f'診斷碼非{treatment}適應症')

        if self.check_empty_symptom and string_utils.get_str(row['Symptom'], 'utf-8') == '':
            error_messages.append('主訴空白')

        for i in range(1, 5):
            disease_code = string_utils.xstr(row[f'DiseaseCode{i}'])
            if disease_code == '':
                continue

            if not case_utils.is_disease_code_neat(self.database, disease_code):
                disease_code = case_utils.correct_neat_disease(self.database, case_key, i)
                if disease_code is None:
                    error_messages.append(f'病名{i}非最細碼')
                else:
                    if not case_utils.is_disease_code_neat(self.database, disease_code):
                        error_messages.append(f'病名{i}非最細碼')

        return error_messages

    def _check_prescript(self, row):
        error_messages = []

        case_key = row['CaseKey']
        sql = f'''
            SELECT MedicineType, MedicineName, InsCode, Dosage FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1
        '''
        prescript_rows = self.database.select_record(sql)
        if len(prescript_rows) <= 0 and string_utils.xstr(row['TreatType']) != '醫療諮詢':
            return ['無開立處方']

        pres_days = case_utils.get_pres_days(self.database, case_key)
        packages = case_utils.get_packages(self.database, case_key)
        instruction = case_utils.get_instruction(self.database, case_key)

        if packages > 8:
            return ['給藥包數超過8包']

        acupuncture_treat = 0
        massage_treat = 0

        total_ins_medicine = 0
        treatment = string_utils.xstr(row['Treatment'])
        if treatment in \
                nhi_utils.COMPLICATED_ACUPUNCTURE_TREAT + \
                nhi_utils.COMPLICATED_MASSAGE_TREAT + \
                nhi_utils.COMPLICATED_MERGE_TREAT_LIST:
            require_treat_times = True
        else:
            require_treat_times = False

        treat_start_times, treat_end_times, treat_times = None, None, None
        treat_position_count, auxiliary_treat_count = 0, 0
        use_infectious_drug = False
        for prescript_row in prescript_rows:
            ins_code = string_utils.xstr(prescript_row['InsCode'])

            dosage = prescript_row['Dosage']
            if ins_code in [
                '1100015686',
                '1100015903',
                '1101800237',
                '1100022217',
                '1100028044',
                '1100028108',
                '1100030654',
                '1100034528',
                '1110019135',
            ]:
                total_ins_medicine += 1
                use_infectious_drug = True
                continue

            medicine_type = string_utils.xstr(prescript_row['MedicineType'])
            medicine_name = string_utils.xstr(prescript_row['MedicineName'])
            if medicine_type in ['', None]:
                total_ins_medicine += 1
                error_messages.append('無處方類別')
                continue
            elif medicine_name in ['', None]:
                total_ins_medicine += 1
                error_messages.append('無處方名稱')
                continue

            sql = f'''
                SELECT PrescriptKey FROM prescript
                WHERE
                    CaseKey = {case_key} AND
                    MedicineSet = 1 AND
                    MedicineType = "{medicine_type}" AND
                    MedicineType NOT IN ("穴道", "處置") AND
                    MedicineName = "{medicine_name}"
            '''
            try:
                rows = self.database.select_record(sql)
            except Exception:
                if ins_code in [None, '']:
                    pass
                else:
                    total_ins_medicine += 1
                    error_messages.append(f'{medicine_name}處方名稱錯誤(不可以使用雙引號)')

                continue

            if len(rows) >= 2:
                error = f'{medicine_name}重複開立'
                if error not in error_messages:
                    error_messages.append(error)

            if '清冠一號' in medicine_name:
                if '順天' in medicine_name and dosage != 20:
                    error_messages.append(f'{medicine_name}成人基本量為20克(兒童除外)')
                elif dosage != 30:
                    error_messages.append(f'{medicine_name}成人基本量為30克(兒童除外)')

            if '輔助治療' in medicine_name:
                auxiliary_treat_count += 1
            if '治療部位' in medicine_name:
                treat_position_count += 1

            if '治療時間' in medicine_name:
                treat_times = medicine_name.strip()
                # treat_times = treat_times.removeprefix('治療時間:')  # removeprefix support in python 3.9
                # treat_times = treat_times.removesuffix('分鐘')

                if '分鐘以上' in medicine_name:
                    treat_times = string_utils.removeprefix(treat_times, '治療時間')
                    treat_times = string_utils.removesuffix(treat_times, '分鐘以上')
                else:
                    treat_times = string_utils.removeprefix(treat_times, '治療時間:')
                    treat_times = string_utils.removesuffix(treat_times, '分鐘')

            if '治療開始:' in medicine_name:
                try:
                    treat_start_times = datetime.datetime.strptime(medicine_name.replace('治療開始:', ''), '%H:%M')
                except Exception:
                    pass

            elif '治療結束:' in medicine_name:
                treat_end_times = medicine_name

            if string_utils.xstr(prescript_row['MedicineType']) == '穴道':
                acupuncture_treat += 1
            elif string_utils.xstr(prescript_row['MedicineType']) == '處置':
                massage_treat += 1

            if ins_code != '':
                total_ins_medicine += 1

            if medicine_type not in ['', '穴道', '處置']:
                if ins_code not in [None, ''] and dosage in [None, 0, '']:
                    error_messages.append(f'{medicine_name}劑量空白')
                if medicine_name in [None, '']:
                    error_messages.append('處方名稱空白')

            if medicine_type in ['單方', '複方'] and '清冠一號' not in medicine_name:
                if ins_code != '' and ins_code[0] != 'A':
                    error_messages.append(f'''健保碼非中藥:{medicine_name}({ins_code})''')

        if use_infectious_drug and pres_days > 5:
            error_messages.append('開立清冠一號不得超過5天')

        if require_treat_times:
            if auxiliary_treat_count == 0:
                error_messages.append('無輔助治療')

            if treat_position_count == 0:
                error_messages.append('無治療部位')
            elif treatment in nhi_utils.COMPLICATED_ACUPUNCTURE_TREAT and treat_position_count < 2:
                error_messages.append('針刺部位不足兩個')

            try:
                if treat_times is None:
                    error_messages.append('無治療時間')
                elif treatment in [
                     '中度複雜性針灸', '中度複雜性傷科',
                ] and number_utils.get_integer(treat_times) < 10:
                    error_messages.append('治療時間不足10分鐘')
                elif treatment in [
                    '中度針灸合併中度傷科', '中度針灸合併中度傷科療程2-6次',
                    '高度複雜性針灸', '高度複雜性傷科',
                ] and number_utils.get_integer(treat_times) < 20:
                    error_messages.append('治療時間不足20分鐘')
                elif treatment in [
                    '中度針灸合併高度傷科起始次', '中度針灸合併高度傷科後續治療',
                ] and number_utils.get_integer(treat_times) < 30:
                    error_messages.append('治療時間不足30分鐘')
                elif treatment in [
                    '高度針灸合併高度傷科起始次', '高度針灸合併高度傷科後續治療',
                ] and number_utils.get_integer(treat_times) < 40:
                    error_messages.append('治療時間不足40分鐘')
            except ValueError:
                error_messages.append('治療時間有誤')

            if treat_start_times is None:
                error_messages.append('無治療開始時間')
            if treat_end_times is None:
                error_messages.append('無治療結束時間')

            if treat_start_times is not None and treat_end_times is not None and treat_times is not None:
                try:
                    minutes = number_utils.get_integer(treat_times.strip())
                except Exception:
                    print(row['CaseKey'], treat_times)

                correct_time = treat_start_times + datetime.timedelta(minutes=minutes)
                correct_time_str = f'治療結束:{correct_time.strftime("%H:%M")}'
                if treat_end_times != correct_time_str:
                    correct_time = treat_start_times + datetime.timedelta(minutes=minutes+1)  # 有一分鐘的誤差 (友杏)
                    correct_time_str = f'治療結束:{correct_time.strftime("%H:%M")}'
                    if treat_end_times != correct_time_str:
                        error_messages.append('治療結束時間錯誤')

        if string_utils.xstr(row['Treatment']) in nhi_utils.ACUPUNCTURE_TREAT and acupuncture_treat <= 0:
            error_messages.append('針灸治療無穴位記錄')
        elif string_utils.xstr(row['Treatment']) in nhi_utils.MASSAGE_TREAT and massage_treat <= 0:
            error_messages.append('傷科治療無治療手法記錄')

        if pres_days > 0 and total_ins_medicine <= 0:
            error_messages.append('無健保碼藥品')

        if packages > 8:
            error_messages.append('給藥包數超過8包')

        if total_ins_medicine > 0:
            if (row['Share'] not in nhi_utils.INFECTIOUS_TYPE and
               row['Injury'] not in nhi_utils.INFECTIOUS_TYPE) and pres_days >= 1 and pres_days < 2:
                error_messages.append('給藥天數不足2日')

                if instruction in [None, '']:
                    error_messages.append('服藥方式空白')

        return error_messages

    def _get_minutes(self, rows, treatment):
        default_moderate_acupuncture_time, default_highly_acupuncture_time = \
            prescript_utils.get_default_complicated_acupuncture_time(self.system_settings)

        if treatment in ['中度複雜性針灸', '中度複雜性傷科', '中度針灸合併中度傷科', '中度針灸合併中度傷科療程2-6次']:
            minutes = default_moderate_acupuncture_time
        else:
            minutes = default_highly_acupuncture_time

        try:
            for row in rows:
                medicine_name = string_utils.xstr(row['MedicineName'])
                if '治療時間' in medicine_name:
                    medicine_name = medicine_name.removeprefix('治療時間:')
                    medicine_name = medicine_name.removesuffix('分鐘')
                    minutes = number_utils.get_integer(medicine_name.strip())
                    break
        except Exception:
            pass

        return minutes

    def _check_charge(self, row):
        error_messages = []

        diag_fee = number_utils.get_integer(row['DiagFee'])
        inter_drug_fee = number_utils.get_integer(row['InterDrugFee'])
        pharmacy_fee = number_utils.get_integer(row['PharmacyFee'])
        acupuncture_fee = number_utils.get_integer(row['AcupunctureFee'])
        massage_fee = number_utils.get_integer(row['MassageFee'])
        dislocate_fee = number_utils.get_integer(row['DislocateFee'])
        exam_fee = number_utils.get_integer(row['ExamFee'])
        total_fee = number_utils.get_integer(row['InsTotalFee'])
        apply_fee = number_utils.get_integer(row['InsApplyFee'])
        agent_fee = number_utils.get_integer(row['AgentFee'])
        diag_share_fee = number_utils.get_integer(row['DiagShareFee'])
        drug_share_fee = number_utils.get_integer(row['DrugShareFee'])

        treat_type = string_utils.xstr(row['TreatType'])
        infectious_drug = prescript_utils.get_infectious_drug(self.database, row['CaseKey'])
        isolation_position = case_utils.get_case_extend(self.database, row['CaseKey'], '隔離處所')

        ins_fee = charge_utils.get_ins_fee(
            self.database, self.system_settings,
            case_key=row['CaseKey'],
            reg_type=string_utils.xstr(row['RegistType']),
            treat_type=treat_type,
            share=string_utils.xstr(row['Share']),
            course=number_utils.get_integer(row['Continuance']),
            pres_days=case_utils.get_pres_days(self.database, row['CaseKey']),
            pharmacy_type=string_utils.xstr(row['PharmacyType']),
            treatment=string_utils.xstr(row['Treatment']),
            infectious_drug=infectious_drug,
            isolation_position=isolation_position,
        )

        if diag_fee != ins_fee['diag_fee']:
            error_messages.append('診察費金額有誤')
        if inter_drug_fee != ins_fee['drug_fee']:
            error_messages.append('藥費有誤')
        if pharmacy_fee != ins_fee['pharmacy_fee']:
            error_messages.append('調劑費有誤')
        if acupuncture_fee != ins_fee['acupuncture_fee']:
            error_messages.append('針灸費有誤')
        if massage_fee != ins_fee['massage_fee']:
            error_messages.append('傷科費有誤')
        if dislocate_fee != ins_fee['dislocate_fee']:
            error_messages.append('照護費有誤')
        if exam_fee != ins_fee['exam_fee']:
            error_messages.append('加計費有誤')
        if diag_share_fee != ins_fee['diag_share_fee']:
            error_messages.append('門診負擔有誤')
        if drug_share_fee != ins_fee['drug_share_fee']:
            error_messages.append('藥品負擔有誤')
        if total_fee != ins_fee['ins_total_fee']:
            error_messages.append('合計金額有誤')
        if apply_fee != ins_fee['ins_apply_fee']:
            error_messages.append('申報金額有誤')
        if agent_fee != ins_fee['agent_fee']:
            error_messages.append('代辦費有誤')
        if treat_type == '居家醫療' and pharmacy_fee > 0:
            error_messages.append('居家醫療不得申報調劑費')

        return error_messages

    # 重新批價
    def _calculate_ins_fee(self):
        row_count = self.ui.tableWidget_errors.rowCount()

        self.ui.tableWidget_errors.setFocus(True)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在重新批價中, 請稍後...', '取消', 0, row_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for row_no in range(row_count):
            progress_dialog.setValue(row_no)

            self.ui.tableWidget_errors.setCurrentCell(row_no, 0)
            case_key = self.ui.tableWidget_errors.item(row_no, 0).text()
            charge_utils.calculate_ins_fee(self.database, self.system_settings, case_key)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()
        self.parent._check_ins_data()

    def _correct_errors(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('自動更新錯誤')
        msg_box.setText(
            """
                <font size='4' color='red'><b>確定自動更正以下的錯誤?</b></font><br>
                1. 更正針灸傷科療程空白 (應為療程1)<br>
                2. 更正病名為慢性病但病歷無慢性病代碼<br>
                3. 重新更新無健保碼藥品<br>
                4. 非中藥的健保碼<br>
                5. 新舊版處置轉換<br>
                6. 正確的治療時間<br>
                7. 正確的治療開始及結束時間<br>
                8. 中度針灸或高度針灸合併高度傷科首次與療程轉換<br>
                9. 姓名內含換行字元<br>
                10. 居家醫療NA卡序<br>
            """
        )
        msg_box.setInformativeText("注意！ 其他錯誤請自行更正")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        correct_errors = msg_box.exec_()
        if not correct_errors:
            return

        for row_no in range(self.ui.tableWidget_errors.rowCount()):
            self.ui.tableWidget_errors.setCurrentCell(row_no, 1)
            case_key = self.table_widget_errors.field_value(0)
            if case_key is None:
                continue

            error_message = self.table_widget_errors.field_value(18)
            if '無健保碼藥品' in error_message:
                self._refresh_ins_code(case_key)
            elif '健保碼非中藥' in error_message:
                self._correct_ins_code(case_key)

            if '就醫類別錯誤' in error_message:
                self._correct_treat_type(case_key)
            if '處置錯誤' in error_message:
                self._correct_treatment(case_key)
            if '無治療時間' in error_message:
                self._correct_times(case_key)
            if '治療時間不足20分鐘' in error_message:
                self._correct_insufficent_times(case_key)
            if '治療結束時間錯誤' in error_message:
                self._correct_treatment_times(case_key)

            if '療程2-6次不得申報中度複雜性傷科首次或高度複雜性傷科起始次' in error_message:
                self._correct_treatment_course_2_6(case_key)
            if '療程首次不得申報中度複雜性傷科療程2-6次' in error_message:
                self._correct_treatment_course_1(case_key)

            if '請改為後續治療' in error_message:
                self._correct_complicated_treatment_first(case_key)
            if '請改為中度針灸合併高度傷科起始次' in error_message or \
               '請改為中度針灸合併高度傷科後續治療' in error_message or \
               '請改為高度針灸合併高度傷科起始次' in error_message or \
               '請改為高度針灸合併高度傷科後續治療' in error_message:
                self._correct_complicated_treatment_name(case_key)
            if '姓名內含換行字元' in error_message:
                self._correct_name_character(case_key)
            if '卡序長度不足4碼' in error_message:
                self._correct_home_care_card(case_key)
            if '病名1非最細碼' in error_message:
                case_utils.correct_neat_disease(self.database, case_key, 1)
            if '病名2非最細碼' in error_message:
                case_utils.correct_neat_disease(self.database, case_key, 2)
            if '病名3非最細碼' in error_message:
                case_utils.correct_neat_disease(self.database, case_key, 3)
            if '病名4非最細碼' in error_message:
                case_utils.correct_neat_disease(self.database, case_key, 4)

            sql = f'''
                SELECT
                    CaseKey, TreatType, Treatment, Continuance,
                    DiseaseCode1, DiseaseCode2, DiseaseCode3, DiseaseCode4, SpecialCode
                FROM cases
                WHERE
                    CaseKey = {case_key}
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                continue

            row = rows[0]

            fields = []
            data = []

            if (string_utils.xstr(row['Treatment']) in nhi_utils.INS_TREAT and
                    string_utils.xstr(row['TreatType']) in nhi_utils.INS_TREAT and
                    number_utils.get_integer(row['Continuance']) < 1):
                fields.append('Continuance')
                data.append(1)

            disease_list = [
                string_utils.xstr(row['DiseaseCode1']),
                string_utils.xstr(row['DiseaseCode2']),
                string_utils.xstr(row['DiseaseCode3']),
                string_utils.xstr(row['DiseaseCode4']),
            ]
            special_code = ''
            for i in range(len(disease_list)):
                disease_code = disease_list[i]
                special_code = case_utils.get_disease_special_code(
                    self.database, disease_code,
                )
                if special_code != '':
                    break

            if special_code != '' and string_utils.xstr(row['SpecialCode']).strip() == '':
                fields.append('SpecialCode')
                data.append(special_code)

            if len(fields) <= 0:
                continue

            self.database.update_record('cases', fields, 'CaseKey', case_key, data)

        self._calculate_ins_fee()
        self.start_check()

    def _refresh_ins_code(self, case_key):
        sql = f'''
            SELECT PrescriptKey, MedicineType, MedicineName FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                MedicineType IN ("單方", "複方") AND
                (InsCode IS NULL OR LENGTH(InsCode) <= 0)
        '''
        rows = self.database.select_record(sql)

        for row in rows:
            medicine_type = string_utils.xstr(row['MedicineType'])
            medicine_name = string_utils.xstr(row['MedicineName'])

            medicine_rows = self._get_medicine_row(medicine_type, medicine_name)
            if len(medicine_rows) <= 0:
                medicine_name = medicine_name.split('(')[0]  # 去掉()
                if string_utils.xstr(medicine_name) == '':
                    continue

                medicine_rows = self._get_medicine_row(medicine_type, medicine_name)
                if len(medicine_rows) <= 0:
                    continue

            ins_code = string_utils.xstr(medicine_rows[0]['InsCode'])
            prescript_key = string_utils.xstr(row['PrescriptKey'])
            self.database.exec_sql(f'''
                UPDATE prescript
                SET
                    InsCode = "{ins_code}"
                WHERE
                    PrescriptKey = {prescript_key}
            ''')

    def _correct_ins_code(self, case_key):
        sql = f'''
            SELECT PrescriptKey, MedicineType, MedicineName, InsCode FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                MedicineType IN ("單方", "複方") AND
                (InsCode IS NOT NULL AND LENGTH(InsCode) > 0)
        '''
        rows = self.database.select_record(sql)

        for row in rows:
            ins_code = string_utils.xstr(row['InsCode'])
            if ins_code[0] == 'A':
                continue

            medicine_name = string_utils.xstr(row['MedicineName'])
            medicine_type = string_utils.xstr(row['MedicineType'])

            medicine_rows = self._get_medicine_row(medicine_type, medicine_name)
            if len(medicine_rows) <= 0:
                medicine_name = medicine_name.split('(')[0]  # 去掉()
                if string_utils.xstr(medicine_name) == '':
                    continue

                medicine_rows = self._get_medicine_row(medicine_type, medicine_name)
                if len(medicine_rows) <= 0:
                    continue

            ins_code = string_utils.xstr(medicine_rows[0]['InsCode'])
            prescript_key = string_utils.xstr(row['PrescriptKey'])
            self.database.exec_sql(f'''
                UPDATE prescript
                SET
                    InsCode = "{ins_code}"
                WHERE
                    PrescriptKey = {prescript_key}
            ''')

    def _get_medicine_row(self, medicine_type, medicine_name):
        sql = f'''
            SELECT InsCode FROM medicine
            WHERE
                MedicineType = "{medicine_type}" AND
                MedicineName LIKE "{medicine_name}%" AND
                InsCode IS NOT NULL AND
                LENGTH(InsCode) > 0
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_treat_type(self, case_key):
        sql = f'''
            SELECT Treatment, Continuance FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            treat_type = '內科'
        else:
            row = rows[0]
            treatment = string_utils.xstr(row['Treatment'])
            primary_treatment, secondary_treatment = case_utils.extract_treatment(treatment)
            course = number_utils.get_integer(row['Continuance'])
            treatment = nhi_utils.get_treatment(
                self.database, case_key, primary_treatment, secondary_treatment, course)
            treat_type = prescript_utils.truncate_treatment(treatment)

        return treat_type

    # 修正錯誤
    def _correct_treat_type(self, case_key):
        treat_type = self._get_treat_type(case_key)

        sql = f'''
            UPDATE cases
            SET
                TreatType = "{treat_type}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

    def _correct_treatment(self, case_key):
        sql = f'''
            SELECT Treatment FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        treatment = string_utils.xstr(row['Treatment'])
        if treatment == '一般針灸':
            correct_treatment = '針灸治療'
        elif treatment == '針灸治療':
            correct_treatment = '一般針灸'
        elif treatment == '一般傷科':
            correct_treatment = '傷科治療'
        elif treatment == '傷科治療':
            correct_treatment = '一般傷科'
        else:
            return

        sql = f'''
            UPDATE cases
            SET
                Treatment = "{correct_treatment}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

    def _correct_times(self, case_key):
        sql = f'''
            SELECT CaseDate, Treatment FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        treatment = string_utils.xstr(row['Treatment'])
        if treatment in ['中度複雜性針灸', '中度複雜性傷科', '中度針灸合併中度傷科', '中度針灸合併中度傷科療程2-6次']:
            treat_times = '治療時間: 10分鐘'
        elif treatment in ['高度複雜性針灸', '高度複雜性傷科',
                           '中度針灸合併高度傷科起始次', '中度針灸合併高度傷科後續治療',
                           '高度針灸合併高度傷科起始次', '高度針灸合併高度傷科後續治療']:
            treat_times = '治療時間: 20分鐘'
        else:
            return

        fields = [
            'CaseKey', 'CaseDate', 'MedicineSet', 'MedicineType', 'MedicineName'
        ]
        data = [
            case_key, row['CaseDate'], 1, '穴道', treat_times,
        ]

        self.database.insert_record('prescript', fields, data)

    def _correct_insufficent_times(self, case_key):
        sql = f'''
            UPDATE prescript
                SET MedicineName = "治療時間:20分鐘"
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                MedicineName != "治療時間:20分鐘" AND
                MedicineType IN ("穴道", "處置") AND
                MedicineName LIKE "治療時間:%"
        '''
        self.database.exec_sql(sql)

    def _set_end_time(self, case_key, end_time):
        sql = f'''
            UPDATE prescript
                SET MedicineName = "{end_time}"
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                MedicineType IN ("穴道", "處置") AND
                MedicineName LIKE "治療結束:%"
        '''
        self.database.exec_sql(sql)

    def _correct_treatment_times(self, case_key):
        minutes = self._get_treat_times(case_key)
        if minutes is None:
            return

        start_time = self._get_treat_start_time(case_key)
        if start_time is None:
            return

        treat_start_times = datetime.datetime.strptime(start_time, '%H:%M')
        end_time = treat_start_times + datetime.timedelta(minutes=minutes)
        treat_end_time = f'治療結束:{end_time.strftime("%H:%M")}'

        self._set_end_time(case_key, treat_end_time)

    def _get_treat_times(self, case_key):
        sql = f'''
            SELECT MedicineName FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                MedicineType IN ("穴道", "處置") AND
                MedicineName LIKE "治療時間:%"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]
        medicine_name = string_utils.xstr(row['MedicineName'])
        medicine_name = string_utils.removeprefix(medicine_name, '治療時間:')
        medicine_name = string_utils.removesuffix(medicine_name, '分鐘')

        minutes = number_utils.get_integer(medicine_name)

        return minutes

    def _get_treat_start_time(self, case_key):
        sql = f'''
            SELECT MedicineName FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                MedicineType IN ("穴道", "處置") AND
                MedicineName LIKE "治療開始:%"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]
        medicine_name = string_utils.xstr(row['MedicineName'])
        start_time = string_utils.removeprefix(medicine_name, '治療開始:')

        return start_time

    def _correct_treatment_course_2_6(self, case_key):
        sql = f'''
            SELECT CaseDate, Continuance, Treatment FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        course = number_utils.get_integer(row['Continuance'])
        treatment = string_utils.xstr(row['Treatment'])

        if course <= 1:
            return

        if treatment in ['中度針灸合併中度傷科', '高度針灸合併中度傷科']:
            treatment += '療程2-6次'
        elif treatment in ['中度針灸合併高度傷科起始次', '高度針灸合併高度度傷科起始次']:
            treatment = treatment.replace('起始次', '後續治療')
        else:
            return

        self.database.exec_sql(
            f'''UPDATE cases SET Treatment = "{treatment}", TreatType = "{treatment}" WHERE CaseKey = {case_key}''')

    def _correct_treatment_course_1(self, case_key):
        sql = f'''
            SELECT CaseDate, Continuance, Treatment FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        course = number_utils.get_integer(row['Continuance'])
        treatment = string_utils.xstr(row['Treatment'])

        if course >= 2:
            return

        if treatment in ['中度針灸合併中度傷科療程2-6次', '高度針灸合併中度傷科療程2-6次']:
            treatment = treatment.replace('療程2-6次', '')
        else:
            return

        self.database.exec_sql(f'UPDATE cases SET Treatment = "{treatment}" WHERE CaseKey = {case_key}')

    def _correct_complicated_treatment_first(self, case_key):
        sql = f'''
            SELECT CaseDate, Continuance, Treatment FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        course = number_utils.get_integer(row['Continuance'])
        treatment = string_utils.xstr(row['Treatment'])

        if course >= 2:
            return

        if treatment in ['中度針灸合併高度傷科起始次', '高度針灸合併高度傷科起始次']:
            treatment = treatment.replace('起始次', '後續治療')
        else:
            return

        self.database.exec_sql(f'UPDATE cases SET Treatment = "{treatment}" WHERE CaseKey = {case_key}')

    def _correct_complicated_treatment_name(self, case_key):
        sql = f'''
            SELECT CaseDate, Continuance, Treatment FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        treatment = string_utils.xstr(row['Treatment'])

        if treatment in ['中度針灸合併高度傷科', '高度針灸合併高度傷科']:
            treatment += '起始次'
        elif treatment in ['中度針灸合併高度傷科療程2-6次', '高度針灸合併高度傷科療程2-6次']:
            treatment = treatment.replace('療程2-6次', '後續治療')
        else:
            return

        self.database.exec_sql(f'UPDATE cases SET Treatment = "{treatment}" WHERE CaseKey = {case_key}')

    def _correct_name_character(self, case_key):
        sql = f'''
            SELECT Name FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        name = string_utils.xstr(row['Name'])
        name = string_utils.remove_illegal_characters(name)

        self.database.exec_sql(f'UPDATE cases SET Name = "{name}" WHERE CaseKey = {case_key}')

    def _delete_existing_times(self, case_key):
        sql = f'''
            DELETE FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                MedicineType IN ("穴道", "處置") AND
                (MedicineName LIKE "治療開始%" OR MedicineName LIKE "治療結束%")
        '''
        self.database.exec_sql(sql)

    def _check_care(self, row):
        error_messages = []
        treat_type = string_utils.xstr(row['TreatType'])
        if treat_type not in ['小兒氣喘', '小兒腦性麻痺'] + nhi_utils.IMPROVE_CARE_TREAT:
            return error_messages

        case_key = row['CaseKey']
        sql = f'''
            SELECT * FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 11
        '''
        prescript_rows = self.database.select_record(sql)
        if len(prescript_rows) <= 0:
            error_messages.append(f'{treat_type}無加強照護處置項目')

        return error_messages

    def _check_highly_complicated_massage_duration(self, row):
        error_messages = []
        treatment = string_utils.xstr(row['Treatment'])
        if treatment not in ['中度針灸合併高度傷科起始次', '高度針灸合併高度傷科起始次']:
            return error_messages

        patient_key = row['PatientKey']
        case_date = row['CaseDate']
        disease_code1 = string_utils.xstr(row['DiseaseCode1'])
        disease_code2 = string_utils.xstr(row['DiseaseCode2'])
        disease_code3 = string_utils.xstr(row['DiseaseCode3'])
        disease_code4 = string_utils.xstr(row['DiseaseCode4'])

        last_highly_complicated_massage_date = case_utils.get_last_highly_complicated_massage_date(
            self.database, case_date, patient_key,
            disease_code1, disease_code2, disease_code3, disease_code4,
        )

        if last_highly_complicated_massage_date is not None:
            error_messages.append(
                f'已在{last_highly_complicated_massage_date}執行過{treatment}, 請改為後續治療'
            )

        return error_messages

    def _check_invalid_gender_disease(self, row):
        error_messages = []

        rows = self.database.select_record(
            f"SELECT Gender FROM patient WHERE PatientKey = {row['PatientKey']}"
        )
        if len(rows) <= 0:
            return error_messages

        gender = string_utils.xstr(rows[0]['Gender'])
        if gender not in ['男', '女']:
            return error_messages

        disease_list = [
            string_utils.xstr(row['DiseaseCode1']),
            string_utils.xstr(row['DiseaseCode2']),
            string_utils.xstr(row['DiseaseCode3']),
            string_utils.xstr(row['DiseaseCode4']),
        ]
        for i in range(len(disease_list)):
            disease_code = disease_list[i]
            if disease_code == '':
                continue

            if gender == '男' and ('N7' <= disease_code[:2] <= 'P9'):
                error_messages.append(f'男性病患輸入女性病患診斷碼: {disease_code}')
            elif gender == '女' and ('N4' <= disease_code[:2] <= 'N5'):
                error_messages.append(f'女性病患輸入男性病患診斷碼: {disease_code}')

        return error_messages

    def _check_duplicate_treat(self, row):
        error_messages = []

        case_key = row['CaseKey']

        sql = f'''
            SELECT PrescriptKey FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                MedicineType IN ("穴道", "處置") AND
                MedicineName LIKE "治療時間%"
        '''
        rows = self.database.select_record(sql)
        if len(rows) >= 2:
            error_messages.append('治療時間重複')

        sql = f'''
            SELECT PrescriptKey FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                MedicineType IN ("穴道", "處置") AND
                MedicineName LIKE "治療開始%"
        '''
        rows = self.database.select_record(sql)
        if len(rows) >= 2:
            error_messages.append('治療開始時間重複')

        sql = f'''
            SELECT PrescriptKey FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                MedicineType IN ("穴道", "處置") AND
                MedicineName LIKE "治療結束%"
        '''
        rows = self.database.select_record(sql)
        if len(rows) >= 2:
            error_messages.append('治療結束時間重複')

        return error_messages

    def _correct_home_care_card(self, case_key):
        sql = f'''
            SELECT CaseDate, PatientKey, TreatType FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        treat_type = string_utils.xstr(row['TreatType'])
        if treat_type != '居家醫療':
            return

        patient_key = string_utils.xstr(row['PatientKey'])
        year = row['CaseDate'].year
        month = row['CaseDate'].month
        start_date = date_utils.get_start_date_by_year_month(
            str(year), str(month))  # 雙月檢查
        end_date = row['CaseDate'].strftime('%Y-%m-%d 00:00:00')
        sql = f'''
            SELECT Card FROM cases
            WHERE
                PatientKey = {patient_key} AND
                TreatType = "居家醫療" AND
                CaseDate BETWEEN "{start_date}" AND "{end_date}"
            ORDER BY CaseDate DESC LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        card = string_utils.xstr(rows[0]['Card'])
        if len(card) == 4:
            correct_card = f'{card}1'
        elif len(card) == 5:
            card1 = card[:4]
            card2 = number_utils.get_integer(card[4])
            correct_card = f'{card1}{card2+1}'

        self.database.exec_sql(f'UPDATE cases SET Card = "{correct_card}" WHERE CaseKey = {case_key}')

    def _correct_invalid_disease(self, case_key, index):
        new_icd_10 = {
            'H4011X0': 'H401194',
            'H4011X3': 'H401194',
            'H4011X4': 'H401193',
            'H8141': 'H814',
            'H8142': 'H814',
            'H8143': 'H814',
            'H8149': 'H814',
            'T670XXA': 'T6701XA',
        }

        disease_name_field = 'DiseaseName' + str(index)
        disease_code_field = 'DiseaseCode' + str(index)
        sql = f'''
            SELECT {disease_code_field}, {disease_name_field} FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]
        disease_code = string_utils.xstr(row[disease_code_field])
        if disease_code in new_icd_10:
            sql = f'''
                UPDATE cases SET {disease_code_field} = "{new_icd_10[disease_code]}" WHERE CaseKey = {case_key}
            '''
            self.database.exec_sql(sql)
            return new_icd_10[disease_code]
        else:
            return None
