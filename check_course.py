
# -*- coding: UTF-8 -*-


from PyQt5 import QtWidgets, QtGui, QtCore
import datetime

from libs import class_utils

from libs import ui_utils
from libs import date_utils
from libs import number_utils
from libs import string_utils
from libs import system_utils
from libs import nhi_utils
from libs import case_utils


# 療程檢查 2018.01.31
class CheckCourse(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(CheckCourse, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = int(args[2])
        self.apply_month = int(args[3])
        self.apply_type = args[4]
        self.check_two_months = args[5]
        self.ui = None
        self.errors = 0
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_CHECK_COURSE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self._set_table_widget()

    def _set_table_widget(self):
        self.table_widget_errors = class_utils.get_table_widget(self.ui.tableWidget_errors, self.database)
        self.table_widget_errors.set_column_hidden([0])
        width = [
            100, 130, 60, 80, 90, 100, 80, 40, 100, 350, 100, 50,
            90, 80, 250,
        ]
        self.table_widget_errors.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_errors.doubleClicked.connect(self.open_medical_record)
        self.ui.toolButton_find_error.clicked.connect(self._find_error)

    def _find_error(self):
        self.table_widget_errors.find_error(14)

    def open_medical_record(self):
        case_key = self.table_widget_errors.field_value(0)
        self.parent.open_medical_record(case_key)

    def read_data(self):
        month = int(self.apply_month)
        if month > 1:
            year = self.apply_year
            month -= 1
        else:
            year = self.apply_year - 1
            month = 12

        last_start_date = date_utils.get_start_date_by_year_month(
            str(year), str(month))  # 雙月檢查
        start_date = date_utils.get_start_date_by_year_month(
            self.apply_year, self.apply_month)
        end_date = date_utils.get_end_date_by_year_month(
            self.apply_year, self.apply_month)

        apply_type_sql = nhi_utils.get_apply_type_sql(self.apply_type)

        sql = f'''
            SELECT
                CaseKey, CaseDate,
                Period, PatientKey, Name, Share, Card, Continuance,
                DiseaseCode1, DiseaseName1, Treatment, Doctor,
                AcupunctureFee, MassageFee, DislocateFee
            FROM cases
            WHERE
                (CaseDate BETWEEN "{last_start_date}" AND "{end_date}") AND
                (cases.InsType = "健保") AND
                (cases.Card != "欠卡") AND
                (Continuance >= 1) AND
                ({apply_type_sql})
            ORDER BY PatientKey, CaseDate
        '''
        self.rows = self.database.select_record(sql)

    def row_count(self):
        return len(self.rows)

    def start_check(self):
        self.read_data()

        self.ui.tableWidget_errors.setRowCount(0)
        for row in self.rows:
            self._insert_record(row)

        self._remove_useless_record()
        self._set_last_month_color()
        self.ui.tableWidget_errors.setAlternatingRowColors(True)

        self._check_course()
        if self.errors <= 0:
            self.ui.toolButton_find_error.setEnabled(False)
        else:
            self.ui.toolButton_find_error.setEnabled(True)

        self.ui.tableWidget_errors.resizeRowsToContents()

    def _check_no_first_course(self, row_no):
        course = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no, 7).text())
        if course == 1:
            return

        patient_key = self.ui.tableWidget_errors.item(row_no, 3).text()
        card = self.ui.tableWidget_errors.item(row_no, 6).text()

        error_message = []
        previous_patient_key = self.ui.tableWidget_errors.item(row_no-1, 3)

        if previous_patient_key is None and course >= 2:  # 第一筆
            error_message.append('療程未見首次')
        elif patient_key != previous_patient_key.text() and course >= 2:  # 換人
            error_message.append('療程未見首次')
        else:  # 同人
            previous_card = self.ui.tableWidget_errors.item(row_no-1, 6).text()
            if card == previous_card:
                return
            elif course >= 2:
                case_date = self.ui.tableWidget_errors.item(row_no, 1).text()
                previous_case_date = date_utils.str_to_date(case_date) - datetime.timedelta(days=30)
                sql = f'''
                    SELECT CaseKey FROM cases
                    WHERE
                        PatientKey = {patient_key} AND
                        DATE(CaseDate) >= "{previous_case_date}" AND DATE(CaseDate) < "{case_date}" AND
                        Card = "{card}" AND
                        Continuance < {course}
                '''
                rows = self.database.select_record(sql)
                if len(rows) <= 0:
                    error_message.append('療程未見首次')

        if len(error_message) > 0:
            self.errors += 1
            self._set_row_error_message(row_no, 14, error_message)

    def _check_last_course_not_full(self, row_no):
        course = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no, 7).text())
        if course != 1:
            return

        case_key = self.ui.tableWidget_errors.item(row_no, 0).text()
        patient_key = self.ui.tableWidget_errors.item(row_no, 3).text()
        case_date = self.ui.tableWidget_errors.item(row_no, 1).text()

        error_message = []
        previous_patient_key = self.ui.tableWidget_errors.item(row_no-1, 3)
        if previous_patient_key is None or previous_patient_key.text() != patient_key:
            return

        previous_case_date = self.ui.tableWidget_errors.item(row_no-1, 1).text()
        previous_card = self.ui.tableWidget_errors.item(row_no-1, 6).text()
        previous_course = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no-1, 7).text())

        if previous_course == 1:
            delta = date_utils.str_to_date(case_date) - date_utils.str_to_date(previous_case_date)
            regist_type = case_utils.get_case_field_value(self.database, case_key, 'RegistType')
            card = self.ui.tableWidget_errors.item(row_no, 6).text()
            if delta.days < 30 and regist_type not in ['照護機構中醫照護'] and \
                    card[:4] != nhi_utils.OCCUPATIONAL_INJURY_CARD:  # 職災不檢查
                error_message.append('上次療程僅首次且未滿30日開新療程')
        elif previous_course <= 5:
            delta = nhi_utils.get_first_course_delta(
                self.ui.tableWidget_errors, row_no,
                patient_key, previous_card, previous_course, case_date,
            )
            if delta is not None and 0 < delta.days < 30:
                error_message.append('上次療程30日內未滿6次')

        if len(error_message) > 0:
            self.errors += 1
            self._set_row_error_message(row_no, 14, error_message)

    def _check_complicated_treat_level(self, row_no):
        course = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no, 7).text())
        if course == 1:
            return

        patient_key = self.ui.tableWidget_errors.item(row_no, 3).text()
        previous_patient_key = self.ui.tableWidget_errors.item(row_no-1, 3)
        if previous_patient_key is None or previous_patient_key.text() != patient_key:
            return

        card = self.ui.tableWidget_errors.item(row_no, 6).text()
        previous_card = self.ui.tableWidget_errors.item(row_no-1, 6).text()
        if card != previous_card:
            return
        
        current_treat = string_utils.xstr(self.ui.tableWidget_errors.item(row_no, 10).text())
        previous_treat = string_utils.xstr(self.ui.tableWidget_errors.item(row_no-1, 10).text())

        error_message = []
        if previous_treat in nhi_utils.GENERAL_ACUPUNCTURE_TREAT + nhi_utils.GENERAL_MASSAGE_TREAT:
            if current_treat in nhi_utils.COMPLICATED_ACUPUNCTURE_TREAT:
                error_message.append('針傷複雜度不可高於上次')
        elif previous_treat in \
                nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST + nhi_utils.MODERATE_COMPLICATED_MASSAGE_TREAT:
            if current_treat in \
                    nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST + nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT:
                error_message.append('針傷複雜度不可高於上次')

        if current_treat in \
                nhi_utils.MODERATE_COMPLICATED_MASSAGE_TREAT + nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT and \
                course >= 2:
            error_message.append('療程2-6次不能執行中度或高度複雜性傷科')

        if len(error_message) > 0:
            self.errors += 1
            self._set_row_error_message(row_no, 14, error_message)

    def _check_course_over_30days(self, row_no):
        course = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no, 7).text())
        if course == 1:
            return

        patient_key = self.ui.tableWidget_errors.item(row_no, 3).text()
        previous_patient_key = self.ui.tableWidget_errors.item(row_no-1, 3)
        if previous_patient_key is None or previous_patient_key.text() != patient_key:
            return

        card = self.ui.tableWidget_errors.item(row_no, 6).text()
        previous_card = self.ui.tableWidget_errors.item(row_no-1, 6).text()
        if card != previous_card:
            return
        
        previous_course = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no-1, 7).text())
        case_date = self.ui.tableWidget_errors.item(row_no, 1).text()

        error_message = []
        delta = nhi_utils.get_first_course_delta(
            self.ui.tableWidget_errors, row_no,
            patient_key, previous_card, previous_course, case_date,
        )
        if delta is not None and delta.days > 30:
            error_message.append('療程超過30日')

        if len(error_message) > 0:
            self.errors += 1
            self._set_row_error_message(row_no, 14, error_message)

    def _check_pres_days_over_28days(self, row_no):
        patient_key = self.ui.tableWidget_errors.item(row_no, 3).text()
        card = self.ui.tableWidget_errors.item(row_no, 6).text()
        total_pres_days = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no, 11).text())

        for i in range(6, 0, -1):
            previous_patient_key = self.ui.tableWidget_errors.item(row_no-i, 3)
            if previous_patient_key is None or previous_patient_key.text() != patient_key:
                continue

            previous_card = self.ui.tableWidget_errors.item(row_no-i, 6).text()
            if card != previous_card:
                continue

            pres_days = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no-i, 11).text())
            if pres_days > 0:
                total_pres_days += pres_days

        error_message = []

        # if total_pres_days > 28:
        #     error_message.append('療程總藥日超過28日(非錯誤，可不理會)')

        if len(error_message) > 0:
            self.errors += 1
            self._set_row_error_message(row_no, 14, error_message)

    def _check_null_value(self, row_no):
        error_message = []

        treatment = self.ui.tableWidget_errors.item(row_no, 10).text()
        if treatment == '':
            error_message.append('無處置醫令')

        if len(error_message) > 0:
            self.errors += 1
            self._set_row_error_message(row_no, 14, error_message)

    def _check_course_treat(self, row_no):
        error_message = []

        treatment = self.ui.tableWidget_errors.item(row_no, 10).text()
        course = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no, 7).text())

        if course >= 2:
            if '中度傷科' in treatment:
                error_message.append('療程2-6次不可申報中度傷科')
            elif '高度傷科' in treatment:
                error_message.append('療程2-6次不可申報高度傷科')
            elif '合併中度傷科' in treatment:
                error_message.append('療程2-6次針傷合併不可申報中度傷科')
            elif '合併高度傷科' in treatment:
                error_message.append('療程2-6次針傷合併不可申報高度傷科')

        if len(error_message) > 0:
            self.errors += 1
            self._set_row_error_message(row_no, 14, error_message)

    def _check_previous_course(self, row_no):
        patient_key = self.ui.tableWidget_errors.item(row_no, 3).text()
        previous_patient_key = self.ui.tableWidget_errors.item(row_no-1, 3)
        if previous_patient_key is None or previous_patient_key.text() != patient_key:  # 不同人
            return

        card = self.ui.tableWidget_errors.item(row_no, 6).text()
        previous_card = self.ui.tableWidget_errors.item(row_no-1, 6).text()
        if card != previous_card:  # 不同卡
            return

        error_message = []

        disease_code = self.ui.tableWidget_errors.item(row_no, 8).text()[:6].strip()
        previous_disease_code = self.ui.tableWidget_errors.item(row_no-1, 8).text()[:6].strip()

        if disease_code[:6] != previous_disease_code[:6]:
            error_message.append('療程診斷碼不一致')

        if len(error_message) > 0:
            self.errors += 1
            self._set_row_error_message(row_no, 14, error_message)

    def _check_same_course(self, row_no):
        patient_key = self.ui.tableWidget_errors.item(row_no, 3).text()
        next_patient_key = self.ui.tableWidget_errors.item(row_no+1, 3)
        if next_patient_key is None or next_patient_key.text() != patient_key:  # 不同人
            return

        card = self.ui.tableWidget_errors.item(row_no, 6).text()
        next_card = self.ui.tableWidget_errors.item(row_no+1, 6).text()
        if card != next_card:  # 不同卡
            return

        error_message = []

        case_date = self.ui.tableWidget_errors.item(row_no, 1).text()
        share_type = self.ui.tableWidget_errors.item(row_no, 5).text()
        course = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no, 7).text())
        disease_code1 = self.ui.tableWidget_errors.item(row_no, 8).text()
        treatment = self.ui.tableWidget_errors.item(row_no, 10).text()

        next_case_date = self.ui.tableWidget_errors.item(row_no+1, 1).text()
        next_share_type = self.ui.tableWidget_errors.item(row_no+1, 5).text()
        next_course = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no+1, 7).text())
        next_disease_code1 = self.ui.tableWidget_errors.item(row_no+1, 8).text()
        next_treatment = self.ui.tableWidget_errors.item(row_no+1, 10).text()

        if next_course > 6:
            error_message.append('療程超過6次')
        if next_course == course:
            error_message.append('療程重複')
        if next_course - course != 1:
            error_message.append('療程不連續')
        if case_date >= next_case_date:
            error_message.append('門診日期未照順序')

        if share_type != next_share_type:
            error_message.append('負擔類別不一致')

        if disease_code1[:6] != next_disease_code1[:6]:
            error_message.append('療程主診斷碼不一致')

        # if treatment != next_treatment:
        #     if treatment in ['一般針灸', '一般傷科'] and course == 1:
        #         if '中度' in next_treatment or '高度' in next_treatment:
        #             error_message.append('複雜性針傷療程首次為一般針傷 (有行政核扣之虞)')
        #     else:
        #         error_message.append('處置不一致')

        if len(error_message) > 0:
            self.errors += 1
            self._set_row_error_message(row_no, 14, error_message)

    # 2021-11-30 重新改寫
    def _check_course(self):
        row_count = self.ui.tableWidget_errors.rowCount()
        if row_count <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            '正在執行療程檢查中, 請稍後...', '取消', 0, row_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for row_no in range(row_count):
            case_date = self.ui.tableWidget_errors.item(row_no, 1).text()
            if date_utils.str_to_date(case_date).month != self.apply_month:  # 上月不檢查
                progress_dialog.setValue(row_no)
                continue

            share_type = self.ui.tableWidget_errors.item(row_no, 5).text()   # 山地離島每次都是新療程
            if share_type in ['山地離島']:
                progress_dialog.setValue(row_no)
                continue

            self._check_no_first_course(row_no)                 # 療程未見首次
            self._check_last_course_not_full(row_no)            # 30日內療程未滿6次
            self._check_previous_course(row_no)                 # 上次療程
            self._check_complicated_treat_level(row_no)         # 療程複雜度
            self._check_course_over_30days(row_no)              # 療程超過30日
            self._check_pres_days_over_28days(row_no)           # 療程開藥超過28日
            self._check_null_value(row_no)                      # 檢查必填欄位庫白
            self._check_same_course(row_no)                     # 同療程檢查
            self._check_course_treat(row_no)                    # 同療程檢查
            self._check_highly_massage_duration(row_no)         # 高傷是符合時間
            self._check_highly_massage_course(row_no)           # 高傷療程2-6次不能執行複雜性針灸

            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()

    def _set_row_error_message(self, row_no, col_no, error_message):
        self.ui.tableWidget_errors.setItem(
            row_no, col_no,
            QtWidgets.QTableWidgetItem(
                ', '.join(error_message)
            )
        )
        self._set_row_color(row_no, 'red')

    def _set_row_color(self, row_no, color):
        for column_no in range(self.ui.tableWidget_errors.columnCount()):
            self.ui.tableWidget_errors.item(row_no, column_no).setForeground(QtGui.QColor(color))

    def error_count(self):
        return self.errors

    def _remove_useless_record(self):
        self._remove_full_course()
        if not self.check_two_months:
            self._remove_last_month_single_course()

    def _remove_full_course(self):
        for row_no in range(self.ui.tableWidget_errors.rowCount()):
            case_date = self.ui.tableWidget_errors.item(row_no, 1).text()
            patient_key = self.ui.tableWidget_errors.item(row_no, 3).text()
            card = self.ui.tableWidget_errors.item(row_no, 6).text()
            course = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no, 7).text())
            last_case_date = case_date

            if date_utils.str_to_date(case_date).month != self.apply_month:
                last_course = course
                last_case_date = case_date
                for i in range(1, 7):
                    next_patient_key_item = self.ui.tableWidget_errors.item(row_no+i, 3)
                    if next_patient_key_item is None:
                        break

                    next_patient_key = next_patient_key_item.text()
                    next_case_date = self.ui.tableWidget_errors.item(row_no+i, 1).text()
                    next_card = self.ui.tableWidget_errors.item(row_no+i, 6).text()
                    next_course = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no+i, 7).text())
                    if patient_key == next_patient_key and card == next_card and next_course > course:
                        last_course = next_course
                        last_case_date = next_case_date

            if date_utils.str_to_date(last_case_date).month != self.apply_month and last_course == 6:  # 上月療程有做滿6次
                self._set_row_error_message(row_no, 14, '!')

        for row_no in reversed(range(self.ui.tableWidget_errors.rowCount())):
            remove_flag = self.ui.tableWidget_errors.item(row_no, 14)
            if remove_flag is not None and remove_flag.text() == '!':
                self.ui.tableWidget_errors.removeRow(row_no)

    def _remove_last_month_single_course(self):
        for row_no in range(self.ui.tableWidget_errors.rowCount()):
            current_case_date = self.ui.tableWidget_errors.item(row_no, 1).text()
            current_patient_key = self.ui.tableWidget_errors.item(row_no, 3).text()

            at_this_month = False
            i = 1
            while True:
                next_patient_key_item = self.ui.tableWidget_errors.item(row_no+i, 3)
                if next_patient_key_item is None:
                    if date_utils.str_to_date(current_case_date).month == self.apply_month:
                        at_this_month = True

                    break

                next_patient_key = next_patient_key_item.text()
                if current_patient_key != next_patient_key:
                    if date_utils.str_to_date(current_case_date).month == self.apply_month:
                        at_this_month = True

                    break

                next_case_date = self.ui.tableWidget_errors.item(row_no+i, 1).text()
                if date_utils.str_to_date(next_case_date).month == self.apply_month:
                    at_this_month = True
                    break

                current_patient_key = next_patient_key
                current_case_date = next_case_date
                i += 1

            if not at_this_month:
                self._set_row_error_message(row_no, 14, '!')

        for row_no in reversed(range(self.ui.tableWidget_errors.rowCount())):
            remove_flag = self.ui.tableWidget_errors.item(row_no, 14)
            if remove_flag is not None and remove_flag.text() == '!':
                self.ui.tableWidget_errors.removeRow(row_no)

    # def _remove_useless_record(self):
    #     for row_no in range(self.ui.tableWidget_errors.rowCount()):
    #         case_date = self.ui.tableWidget_errors.item(row_no, 1).text()
    #         patient_key = self.ui.tableWidget_errors.item(row_no, 3).text()
    #         card = self.ui.tableWidget_errors.item(row_no, 6).text()
    #         course = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no, 7).text())

    #         if date_utils.str_to_date(case_date).month != self.apply_month:
    #             last_case_date = case_date
    #             for i in range(1, 7):
    #                 next_case_date = self.ui.tableWidget_errors.item(row_no+i, 1)
    #                 if next_case_date is None:
    #                     continue

    #                 next_case_date = next_case_date.text()
    #                 next_patient_key = self.ui.tableWidget_errors.item(row_no+i, 3).text()
    #                 next_card = self.ui.tableWidget_errors.item(row_no+i, 6).text()
    #                 next_course = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no+i, 7).text())
    #                 if patient_key == next_patient_key and card == next_card and next_course > course:
    #                     last_case_date = next_case_date

    #             if date_utils.str_to_date(last_case_date).month != self.apply_month:
    #                 self._set_row_error_message(row_no, 13, '!')

    #     for row_no in reversed(range(self.ui.tableWidget_errors.rowCount())):
    #         remove_flag = self.ui.tableWidget_errors.item(row_no, 13)
    #         if remove_flag is not None and remove_flag.text() == '!':
    #             self.ui.tableWidget_errors.removeRow(row_no)

    def _check_remove_need(self, row_no):
        start_date = date_utils.get_start_date_by_year_month(
            self.apply_year, self.apply_month)
        patient_key = self.ui.tableWidget_errors.item(row_no, 3).text()
        card = self.ui.tableWidget_errors.item(row_no, 6).text()
        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                PatientKey = {patient_key} AND
                Card = "{card}" AND
                CaseDate >= "{start_date}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self.ui.tableWidget_errors.removeRow(row_no)

    def _set_last_month_color(self):
        for row_no in range(self.ui.tableWidget_errors.rowCount()):
            case_date = self.ui.tableWidget_errors.item(row_no, 1).text()
            start_date = date_utils.get_start_date_by_year_month(
                self.apply_year, self.apply_month)
            if (datetime.datetime.strptime(case_date, '%Y-%m-%d') <
                    datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')):
                for column in range(0, self.ui.tableWidget_errors.columnCount()):
                    self.ui.tableWidget_errors.item(row_no, column).setForeground(
                        QtGui.QColor('darkGray'))

    def _insert_record(self, row, row_no=None):
        if row_no is None:
            row_no = self.ui.tableWidget_errors.rowCount()
            self.ui.tableWidget_errors.setRowCount(row_no + 1)

        case_key = row['CaseKey']
        year = row['CaseDate'].year
        month = row['CaseDate'].month
        day = row['CaseDate'].day
        pres_days = case_utils.get_pres_days(self.database, case_key)
        if pres_days <= 0:
            pres_days = None

        error_row = [
            case_key,
            f'{year}-{month:0>2}-{day:0>2}',
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Share']),
            string_utils.xstr(row['Card']),
            string_utils.xstr(row['Continuance']),
            string_utils.xstr(row['DiseaseCode1']),
            string_utils.xstr(row['DiseaseName1']),
            string_utils.xstr(row['Treatment']),
            pres_days,
            string_utils.xstr(row['Doctor']),
            string_utils.xstr(
                number_utils.get_integer(row['AcupunctureFee']) +
                number_utils.get_integer(row['MassageFee']) +
                number_utils.get_integer(row['DislocateFee'])
            ),
            None,
        ]
        for col_no in range(len(error_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, error_row[col_no])
            self.ui.tableWidget_errors.setItem(
                row_no, col_no, item
            )

            if col_no in [7]:
                self.ui.tableWidget_errors.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            elif col_no in [3, 11, 13]:
                self.ui.tableWidget_errors.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    # 重新顯示資料 call from ins_check
    def refresh_medical_record(self):
        case_key = self.table_widget_errors.field_value(0)
        if case_key is None:
            return

        sql = f'''
            SELECT
                CaseKey, CaseDate,
                Period, PatientKey, Name, Share, Card, Continuance,
                DiseaseCode1, DiseaseName1, Treatment, Doctor,
                AcupunctureFee, MassageFee, DislocateFee
            FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        current_row_no = self.ui.tableWidget_errors.currentRow()
        self._insert_record(row, current_row_no)

    def _check_highly_massage_duration(self, row_no):
        current_treat = string_utils.xstr(self.ui.tableWidget_errors.item(row_no, 10).text())
        if current_treat not in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT:
            return True

        patient_key = self.ui.tableWidget_errors.item(row_no, 3).text()
        case_date = self.ui.tableWidget_errors.item(row_no, 1).text()
        case_date = datetime.datetime.strptime(case_date, '%Y-%m-%d') 
        disease_code1 = self.ui.tableWidget_errors.item(row_no, 8).text()[:6].strip()

        last_highly_complicated_massage_date = case_utils.get_last_highly_complicated_massage_date(
            self.database, case_date, patient_key, disease_code1
        )

        error_message = []
        if last_highly_complicated_massage_date is not None:
            error_message.append(
                f'已在{last_highly_complicated_massage_date}執行過高度複雜性傷科, 請更改治療方式'
            )

        if len(error_message) > 0:
            self.errors += 1
            self._set_row_error_message(row_no, 14, error_message)

    def _check_highly_massage_course(self, row_no):
        current_treat = string_utils.xstr(self.ui.tableWidget_errors.item(row_no, 10).text())
        if current_treat in nhi_utils.GENERAL_ACUPUNCTURE_TREAT + nhi_utils.GENERAL_MASSAGE_TREAT:  # 一般針灸 or 一般傷科
            return True

        course = number_utils.get_integer(self.ui.tableWidget_errors.item(row_no, 7).text())
        if course <= 1:  # 療程2-6次才檢查
            return True

        patient_key = self.ui.tableWidget_errors.item(row_no, 3).text()
        card = self.ui.tableWidget_errors.item(row_no, 6).text()

        first_treat = nhi_utils.get_first_course_treat(
            self.ui.tableWidget_errors, row_no, patient_key, card, course,
        )

        error_message = []
        if first_treat in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT:
            error_message.append(
                f'高度傷科療程2-6次不能執行複雜性針傷'
            )

        if len(error_message) > 0:
            self.errors += 1
            self._set_row_error_message(row_no, 14, error_message)
