# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from libs import ui_utils
from libs import string_utils
from libs import system_utils
from libs import case_utils
from libs import personnel_utils


# 病歷資料 2018.01.31
class MedicalRecordRecentlyHistory(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(MedicalRecordRecentlyHistory, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.patient_key = args[3]
        self.call_from = args[4]
        self.medical_record = None
        self.patient_data = None
        self.ui = None

        self.no_separator = self.system_settings.field('最近病歷不顯示分隔線')
        self.past_history = {
            'index': 0,
            'row_count': 0,
            'data': None,
        }
        self._set_ui()
        self._set_signal()
        self._read_data()
        self._display_past_record()

        self.user_name = system_utils.get_user_name(self.system_settings)
        self._set_permission()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_MEDICAL_RECORD_RECENTLY_HISTORY, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_check.clicked.connect(self.set_check_box)
        self.ui.toolButton_first.clicked.connect(self.first_past_record)
        self.ui.toolButton_previous.clicked.connect(self.prev_past_record)
        self.ui.toolButton_next.clicked.connect(self.next_past_record)
        self.ui.toolButton_last.clicked.connect(self.last_past_record)
        self.ui.toolButton_copy.clicked.connect(self.copy_past_medical_record_button_clicked)

    def _test(self, url):
        print(url)

    def _set_permission(self):
        # if self.call_from == '醫師看診作業':
        #     return

        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(self.database, '醫師看診作業', '病歷登錄', self.user_name) == 'Y':
            return

        if personnel_utils.get_permission(self.database, '病歷資料', '病歷修正', self.user_name) == 'Y':
            return

        self.ui.toolButton_copy.setEnabled(False)
        self.ui.toolButton_check.setEnabled(False)
        self.ui.checkBox_diagnostic.setEnabled(False)
        self.ui.checkBox_disease.setEnabled(False)
        self.ui.checkBox_remark.setEnabled(False)
        self.ui.checkBox_ins_prescript.setEnabled(False)
        self.ui.checkBox_ins_treat.setEnabled(False)
        self.ui.checkBox_copy_to_self.setEnabled(False)
        self.ui.checkBox_self_prescript.setEnabled(False)

    def _read_data(self):
        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        try:
            self.medical_record = self.database.select_record(sql)[0]
        except Exception:
            pass

        sql = f'''
            SELECT * FROM patient
            WHERE
                PatientKey = {self.patient_key}
        '''
        try:
            self.patient_data = self.database.select_record(sql)[0]
        except Exception:
            pass

        self._read_past_history()

    # 讀取過去病歷名單
    def _read_past_history(self):
        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                CaseKey != {self.case_key} AND
                PatientKey = {self.patient_key} AND
                TreatType NOT IN ("民俗調理")
            ORDER BY CaseDate DESC
        '''
        try:
            rows = self.database.select_record(sql)
        except Exception:
            rows = []

        if len(rows) <= 0:
            self.ui.toolButton_copy.setEnabled(False)
            return

        history_list = []
        for row in rows:
            history_list.append(row['CaseKey'])

        self.past_history = {
            'index': 0,
            'row_count': len(history_list),
            'data': history_list
        }

    # 顯示最近病歷
    def _display_past_record(self):
        self.first_past_record()

    # 設定最近病歷參數 (目前沒用到, 留作範例)
    def _set_past_values(self, row):
        self.ui.textEdit_past.setProperty('medical_record', row['CaseKey'])
        self.ui.textEdit_past.setProperty('primary_key', row['PatientKey'])
        self.ui.textEdit_past.setProperty('case_date', row['CaseDate'])

    def _get_past_history_case_key(self):
        if self.past_history['data'] is None:
            case_key = None
        else:
            index = self.past_history['index']
            case_key = self.past_history['data'][index]

        return case_key

    # 最近一筆
    def first_past_record(self):
        if self.past_history['data'] is None:
            self.ui.toolButton_first.setEnabled(False)
            self.ui.toolButton_previous.setEnabled(False)
            self.ui.toolButton_next.setEnabled(False)
            self.ui.toolButton_last.setEnabled(False)
            html = '<br><br><br><br><br><center>無過去病歷</center><br>'
            self.ui.textEdit_past.setHtml(html)
            return

        self.past_history['index'] = 0
        case_key = self._get_past_history_case_key()

        self._set_past_record(case_key)
        self.ui.toolButton_first.setEnabled(False)
        self.ui.toolButton_previous.setEnabled(False)
        self.ui.toolButton_next.setEnabled(True)
        self.ui.toolButton_last.setEnabled(True)

    # 上一筆
    def prev_past_record(self):
        self.past_history['index'] -= 1
        if self.past_history['index'] <= 0:  # 到頂
            self.past_history['index'] = 0
            self.ui.toolButton_first.setEnabled(False)
            self.ui.toolButton_previous.setEnabled(False)

        self.ui.toolButton_next.setEnabled(True)
        self.ui.toolButton_last.setEnabled(True)
        case_key = self._get_past_history_case_key()
        self._set_past_record(case_key)

    # 下一筆
    def next_past_record(self):
        self.past_history['index'] += 1
        if self.past_history['index'] >= self.past_history['row_count'] - 1:  # 到底
            self.past_history['index'] = self.past_history['row_count'] - 1
            self.ui.toolButton_next.setEnabled(False)
            self.ui.toolButton_last.setEnabled(False)

        self.ui.toolButton_first.setEnabled(True)
        self.ui.toolButton_previous.setEnabled(True)
        case_key = self._get_past_history_case_key()
        self._set_past_record(case_key)

    # 最後一筆
    def last_past_record(self):
        self.past_history['index'] = self.past_history['row_count'] - 1
        case_key = self._get_past_history_case_key()

        self._set_past_record(case_key)
        self.ui.toolButton_first.setEnabled(True)
        self.ui.toolButton_previous.setEnabled(True)
        self.ui.toolButton_next.setEnabled(False)
        self.ui.toolButton_last.setEnabled(False)

    # 讀取最近病歷
    def _set_past_record(self, case_key):
        sql = f'''
            SELECT CaseKey, InsType, Treatment FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        ins_type = string_utils.xstr(row['InsType'])
        treatment = string_utils.xstr(row['Treatment'])

        if self.no_separator == 'Y':
            show_separator = False
        else:
            show_separator = True

        html = case_utils.get_medical_record_html(
            self.database, self.system_settings, case_key, show_separator=show_separator)

        self.ui.textEdit_past.setHtml(html)

        self.ui.checkBox_ins_prescript.setChecked(False)  # 健保療程2-6次預設不拷貝藥品
        self.ui.checkBox_ins_prescript.setEnabled(False)  # 健保療程2-6次預設不拷貝藥品

        self.ui.checkBox_copy_to_self.setEnabled(False)

        self.ui.checkBox_ins_treat.setChecked(False)
        self.ui.checkBox_ins_treat.setEnabled(False)

        if ins_type == '健保':
            if treatment != '':
                self.ui.checkBox_ins_treat.setEnabled(True)
                self.ui.checkBox_ins_treat.setChecked(True)
            sql = f'''
                SELECT PrescriptKey FROM prescript
                WHERE
                    CaseKey = {case_key} AND
                    MedicineSet = 1
            '''
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                self.ui.checkBox_ins_prescript.setEnabled(True)
                self.ui.checkBox_copy_to_self.setEnabled(True)
                if treatment == '':
                    self.ui.checkBox_ins_prescript.setChecked(True)  # 預設非療程才拷貝藥品

                if self.medical_record['InsType'] == '自費':
                    self.ui.checkBox_copy_to_self.setChecked(True)
        # if self.system_settings.field('健保自費分開') == 'Y':
        #     sql = f'''
        #         SELECT InsType FROM cases
        #         WHERE
        #             CaseKey = {self.case_key}
        #     '''
        #     rows = self.database.select_record(sql)
        #     if len(rows) >= 0 and string_utils.xstr(rows[0]['InsType']) == '健保':
        #         self.ui.checkBox_self_prescript.setEnabled(False)
        #         self.ui.checkBox_copy_to_self.setEnabled(False)
        #         return

        sql = f'''
            SELECT MedicineSet FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            copy_self_prescript = True
        else:
            copy_self_prescript = False

        self.ui.checkBox_self_prescript.setEnabled(copy_self_prescript)
        self.ui.checkBox_self_prescript.setChecked(copy_self_prescript)

        if copy_self_prescript:
            if self.system_settings.field('預設拷貝自費處方') == 'Y':
                self.ui.checkBox_self_prescript.setChecked(True)
            else:
                self.ui.checkBox_self_prescript.setChecked(False)

        if (self.parent.ins_type == '自費' or self.call_from == '新增自費病歷') and ins_type == '自費':
            self.ui.checkBox_copy_to_self.setChecked(False)
            sql = f'''
                SELECT PrescriptKey FROM prescript
                WHERE
                    CaseKey = {case_key} AND
                    MedicineSet >= 2
            '''
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                self.ui.checkBox_self_prescript.setChecked(True)

    # 拷貝病歷
    def copy_past_medical_record_button_clicked(self):
        if self.ui.checkBox_copy_to_self.isChecked():
            copy_to = '自費處方'
        else:
            copy_to = '健保處方'

        case_key = self._get_past_history_case_key()

        case_utils.copy_past_medical_record(
            self.database, self.system_settings, self.parent, case_key,
            self.ui.checkBox_diagnostic.isChecked(),
            self.ui.checkBox_remark.isChecked(),
            self.ui.checkBox_disease.isChecked(),
            self.ui.checkBox_ins_prescript.isChecked(),
            copy_to,
            self.ui.checkBox_ins_treat.isChecked(),
            self.ui.checkBox_self_prescript.isChecked(),
            False,
            self.ui.checkBox_not_overwrite.isChecked(),
        )

    # 設定核取方塊
    def set_check_box(self):
        enabled = not self.ui.checkBox_diagnostic.isChecked()

        self.ui.checkBox_diagnostic.setChecked(enabled)
        self.ui.checkBox_disease.setChecked(enabled)
        self.ui.checkBox_remark.setChecked(enabled)
        if self.ui.checkBox_ins_prescript.isEnabled():
            self.ui.checkBox_ins_prescript.setChecked(enabled)
        if self.ui.checkBox_ins_treat.isEnabled():
            self.ui.checkBox_ins_treat.setChecked(enabled)
        if self.ui.checkBox_self_prescript.isEnabled():
            self.ui.checkBox_self_prescript.setChecked(enabled)
