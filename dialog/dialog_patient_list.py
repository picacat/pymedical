
# 病患查詢 2019.03.18
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import re
import calendar
import datetime

from libs import date_utils
from libs import validator_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils


# 病患查詢
class DialogPatientList(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPatientList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PATIENT_LIST, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.label_patient_key.setEnabled(False)
        self.ui.lineEdit_start.setEnabled(False)
        self.ui.label_to.setEnabled(False)
        self.ui.lineEdit_end.setEnabled(False)
        self.ui.dateEdit_start_date.setDate(datetime.datetime.now())
        self.ui.dateEdit_end_date.setDate(datetime.datetime.now())
        ui_utils.set_combo_box(
            self.ui.comboBox_birth_month,
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'], None)
        ui_utils.set_combo_box(
            self.ui.comboBox_operand, ['大於', '大於等於', '等於', '小於等於', '小於'])

        self.ui.lineEdit_keyword.setFocus()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.radioButton_all_range.clicked.connect(self._set_patient)
        self.ui.radioButton_range.clicked.connect(self._set_patient)
        self.ui.lineEdit_start.textChanged.connect(self._range_check)
        self.ui.lineEdit_end.textChanged.connect(self._range_check)

    def get_row_count(self):
        sql = self.get_sql()
        if sql is None:
            return 0

        try:
            rows = self.database.select_record(sql)
        except Exception:
            return 0

        return len(rows)

    def _get_advance_search(self):
        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')
        times = self.ui.spinBox_times.value()

        operand = {
            '大於': '>',
            '大於等於': '>=',
            '等於': '=',
            '小於等於': '<=',
            '小於': '<'
        }.get(self.ui.comboBox_operand.currentText(), '>=')

        # 撈出符合就診次數與日期的病患
        rows = self.database.select_record(f'''
            SELECT PatientKey, Continuance FROM cases
            WHERE (CaseDate BETWEEN "{start_date}" AND "{end_date}")
            GROUP BY PatientKey HAVING COUNT(CaseKey) {operand} {times}
        ''')

        # 篩選課程種類
        patient_list = []
        for row in rows:
            course = number_utils.get_integer(row['Continuance'])
            if self.ui.checkBox_internal.isChecked() and course <= 0 or \
               self.ui.checkBox_course1.isChecked() and course == 1 or \
               self.ui.checkBox_course2.isChecked() and course >= 2:
                patient_list.append(string_utils.xstr(row['PatientKey']))

        if not patient_list:
            return '0'  # 這樣 WHERE 0 永遠不成立，可安全避開查詢

        # 回傳可放入 WHERE 條件的 SQL 字串
        return f'patient.PatientKey IN ({",".join(patient_list)})'

    # 設定 mysql script
    def get_sql(self):
        # 基本 SELECT 與 FROM
        select_clause = '''
            SELECT
                patient.PatientKey, patient.Name, patient.Gender, patient.ID,
                patient.Birthday,
                patient.Nationality, patient.InsType, patient.DiscountType,
                patient.InitDate, patient.Telephone, patient.Cellphone,
                patient.Email, patient.Address, patient.Remark
        '''
        from_clause = 'FROM patient'
        join_clause = ''
        where_conditions = []

        # ▍條件：就診次數與疾病名稱都會用到 cases 表
        if self.ui.checkBox_case_times.isChecked() or self.ui.checkBox_disease_name.isChecked():
            join_clause = 'LEFT JOIN cases ON patient.PatientKey = cases.PatientKey'

        # ▍條件：病患編號範圍
        if self.ui.radioButton_range.isChecked():
            start_key = string_utils.xstr(self.ui.lineEdit_start.text())
            end_key = string_utils.xstr(self.ui.lineEdit_end.text())
            if start_key and end_key:
                where_conditions.append(f'(patient.PatientKey BETWEEN {start_key} AND {end_key})')

        # ▍條件：生日月份
        if self.ui.checkBox_birth_month.isChecked():
            month = self.ui.comboBox_birth_month.currentText()
            if month:
                where_conditions.append(f'(MONTH(Birthday) = {month})')

        # ▍條件：疾病名稱包含關鍵字（多組 OR，再組成 AND）
        if self.ui.checkBox_disease_name.isChecked():
            disease_keywords = self.ui.lineEdit_disease_name.text().split()
            if disease_keywords:
                disease_clauses = []
                for word in disease_keywords:
                    clause = f'''
                        (cases.DiseaseName1 LIKE "%{word}%" OR
                         cases.DiseaseName2 LIKE "%{word}%" OR
                         cases.DiseaseName3 LIKE "%{word}%" OR
                         cases.DiseaseName4 LIKE "%{word}%")
                    '''
                    disease_clauses.append(clause.strip())
                where_conditions.append(' AND '.join(disease_clauses))

        # ▍條件：只找有手機者
        if self.ui.checkBox_only_cellphone.isChecked():
            where_conditions.append('(Cellphone IS NOT NULL AND LENGTH(Cellphone) > 0)')

        # ▍條件：只找有優惠者
        if self.ui.checkBox_only_discount.isChecked():
            where_conditions.append('(DiscountType IS NOT NULL AND LENGTH(DiscountType) > 0)')

        # ▍條件：關鍵字搜尋（會處理數字、生日、中文等）
        keyword = string_utils.xstr(self.ui.lineEdit_keyword.text().strip())
        if self.ui.radioButton_keyword.isChecked() and keyword:
            kw_clause = self._build_keyword_condition(keyword)
            if kw_clause:
                where_conditions.append(kw_clause)

        # ▍條件：就診次數進階搜尋
        if self.ui.checkBox_case_times.isChecked():
            times_clause = self._get_advance_search()
            if times_clause:
                where_conditions.append(times_clause)

        # ▍組合 SQL
        sql = f"{select_clause} {from_clause} {join_clause}"

        if where_conditions:
            sql += "\nWHERE " + '\n  AND '.join(where_conditions)

        # ▍GROUP BY 與 ORDER BY
        sql += '\nGROUP BY PatientKey'

        if self.ui.checkBox_birth_month.isChecked():
            sql += '\nORDER BY DAY(Birthday), Birthday'
        else:
            sql += '\nORDER BY PatientKey'

        return sql
        
    def _build_keyword_condition(self, keyword):
        if keyword.isdigit():
            date_keyword = validator_utils.get_exp_date(keyword)
            return f'''
                (PatientKey = {keyword} OR Birthday = "{date_keyword}" OR ChartNo = "{keyword}" OR
                 Telephone LIKE "{keyword}%" OR Cellphone LIKE "{keyword}%")
            '''

        elif re.match(validator_utils.DATE_REGEXP, keyword):
            query_date = date_utils.date_to_west_date(keyword)
            return f'Birthday = "{query_date}"'

        elif re.match(r'^[0-9]{1,4}[-/.][0-9]{1,2}', keyword):
            sep = date_utils.get_date_separator(keyword)
            try:
                year, month = map(int, keyword.split(sep))
                if year < 1000:
                    year += 1911
                last_day = calendar.monthrange(year, month)[1]
                start_date = f"{year}{sep}{month:02d}{sep}01"
                end_date = f"{year}{sep}{month:02d}{sep}{last_day}"
                return f'(Birthday BETWEEN "{start_date}" AND "{end_date}")'
            except Exception:
                return None

        # 中文或其他一般字串關鍵字
        return f'''
            (patient.Name LIKE "%{keyword}%" OR
             ID LIKE "{keyword}%" OR
             Address LIKE "%{keyword}%" OR
             EMail LIKE "%{keyword}%" OR
             patient.Remark LIKE "%{keyword}%")
        '''

    def accepted_button_clicked(self):
        pass

    def _set_patient(self):
        if self.ui.radioButton_all_range.isChecked():
            self.ui.lineEdit_start.setText('')
            self.ui.lineEdit_end.setText('')
            enabled = False
        else:
            enabled = True

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(not enabled)
        self.ui.label_patient_key.setEnabled(enabled)
        self.ui.lineEdit_start.setEnabled(enabled)
        self.ui.label_to.setEnabled(enabled)
        self.ui.lineEdit_end.setEnabled(enabled)

    def _range_check(self):
        if self.ui.lineEdit_start.text() == '' or self.ui.lineEdit_end.text() == '':
            enabled = False
        else:
            enabled = True

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(enabled)
