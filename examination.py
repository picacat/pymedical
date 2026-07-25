# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
import datetime

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils
from libs import dialog_utils
from libs import examination_util


# 檢驗作業 2019.08.11
class Examination(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(Examination, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.examination_key = args[2]
        self.patient_key = args[3]
        self.examination_date = args[4]
        self.ui = None
        self._set_ui()
        self._set_signal()

        if self.examination_key is not None:
            self._read_examination()

        if self.patient_key is not None:
            self._preset_patient()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_EXAMINATION, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_examination_item = class_utils.get_table_widget(
            self.ui.tableWidget_examination_item, self.database
        )
        self.table_widget_examination_item.set_column_hidden([0])
        self.ui.dateEdit_examination_date.setDate(datetime.datetime.today())
        self.ui.action_save.setEnabled(False)
        self._set_table_width()
        self._set_combo_box_laboratory()
        self._set_examination_items()

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_examination)
        self.ui.action_save.triggered.connect(self._save_examination)
        self.ui.toolButton_select_patient.clicked.connect(lambda: self._select_patient(None))
        self.ui.lineEdit_patient_key.textChanged.connect(self._patient_key_changed)
        self.ui.comboBox_laboratory.currentTextChanged.connect(self._set_combo_box_MLS)
        self.ui.tableWidget_examination_item.itemChanged.connect(self._examination_item_changed)

    def close_examination(self):
        self.close_all()
        self.close_tab()

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 120, 250, 200, 100, 200, 150, 600]
        self.table_widget_examination_item.set_table_heading_width(width)

    def _set_combo_box_laboratory(self):
        sql = '''
            SELECT Laboratory FROM examination
            WHERE
                Laboratory IS NOT NULL
            GROUP BY Laboratory
        '''
        rows = self.database.select_record(sql)
        laboratory_list = []
        for row in rows:
            laboratory_list.append(string_utils.xstr(row['Laboratory']))

        ui_utils.set_combo_box(self.ui.comboBox_laboratory, laboratory_list, '本院')

    def _set_combo_box_MLS(self):
        self.ui.comboBox_MLS.clear()

        laboratory = self.ui.comboBox_laboratory.currentText()
        if laboratory == '':
            return

        sql = f'''
            SELECT MLS FROM examination
            WHERE
                Laboratory = "{laboratory}" AND
                MLS IS NOT NULL
            GROUP BY MLS
        '''
        rows = self.database.select_record(sql)
        MLS_list = []
        for row in rows:
            MLS_list.append(string_utils.xstr(row['MLS']))

        ui_utils.set_combo_box(self.ui.comboBox_MLS, MLS_list, None)

    def _set_examination_items(self):
        examination_item_list = examination_util.EXAMINATION_LIST
        record_count = len(examination_item_list)

        self.ui.tableWidget_examination_item.setRowCount(record_count)
        for row_no in range(record_count):
            low = examination_item_list[row_no][3]
            high = examination_item_list[row_no][4]
            if low is None and high is None:
                operator = None
            elif low is None and high is not None:
                operator = '<'
            elif low is not None and high is None:
                operator = '>'
            elif low is not None and high is not None and low == high:
                operator = '='
            else:
                operator = '-'

            low = string_utils.xstr(examination_item_list[row_no][3])
            high = string_utils.xstr(examination_item_list[row_no][4])
            normal_range = f'{low}{operator}{high}'
            if operator == '=':
                normal_range = low
            elif operator is None:
                normal_range = None

            examination_item = [
                None,
                examination_item_list[row_no][0],
                examination_item_list[row_no][1],
                examination_item_list[row_no][2],
                '',
                normal_range,
                examination_item_list[row_no][5],
                examination_item_list[row_no][6],
            ]
            for col_no in range(len(examination_item)):
                self.ui.tableWidget_examination_item.setItem(
                    row_no, col_no,
                    QtWidgets.QTableWidgetItem(examination_item[col_no])
                )
                if col_no not in [4]:
                    self.ui.tableWidget_examination_item.item(row_no, col_no).setFlags(
                        QtCore.Qt.ItemIsEnabled
                    )

        self.ui.tableWidget_examination_item.resizeRowsToContents()

    def _patient_key_changed(self):
        patient_key = self.ui.lineEdit_patient_key.text()
        if patient_key.strip() == '':
            self.ui.lineEdit_name.setText(None)
            self.ui.action_save.setEnabled(False)
            return

        sql = f'''
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        '''

        try:
            rows = self.database.select_record(sql)
        except Exception:
            self.ui.lineEdit_patient_key.setText(None)
            return

        if len(rows) <= 0:
            return

        row = rows[0]
        self.ui.lineEdit_name.setText(string_utils.xstr(row['Name']))
        self.ui.action_save.setEnabled(True)

    def _select_patient(self, keyword=None):
        dialog = dialog_utils.get_dialog_select_patient(
            self, self.database, self.system_settings, 'patient', 'PatientKey', keyword
        )
        if not dialog.exec_():
            return

        patient_key = dialog.get_primary_key()
        name = dialog.get_name()

        self.ui.lineEdit_patient_key.setText(patient_key)
        self.ui.lineEdit_name.setText(name)

        dialog.deleteLater()

    def _read_examination(self):
        sql = f'''
            SELECT * from examination
            WHERE
                ExaminationKey = {self.examination_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]

        self.ui.lineEdit_patient_key.setText(string_utils.xstr(row['PatientKey']))
        self.ui.dateEdit_examination_date.setDate(row['ExaminationDate'])
        self.ui.comboBox_laboratory.setCurrentText(string_utils.xstr(row['Laboratory']))
        self.ui.comboBox_MLS.setCurrentText(string_utils.xstr(row['MLS']))

        self._read_examination_item(self.examination_key)

    def _read_examination_item(self, examination_key):
        sql = f'''
            SELECT * FROM examination_item
            WHERE
                ExaminationKey = {examination_key}
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            item_name = string_utils.xstr(row['ExaminationItem'])
            row_no = self._get_item_row_no(item_name)
            if row_no is None:
                continue

            self.ui.tableWidget_examination_item.setItem(
                row_no, 4,
                QtWidgets.QTableWidgetItem(string_utils.xstr(row['TestResult']))
            )

    def _get_item_row_no(self, item_name):
        current_row_no = None
        for row_no in range(self.ui.tableWidget_examination_item.rowCount()):
            if self.ui.tableWidget_examination_item.item(row_no, 3).text() == item_name:
                current_row_no = row_no
                break

        return current_row_no

    def _save_examination(self):
        fields = [
            'PatientKey', 'Name', 'ExaminationDate', 'Laboratory', 'MLS',
        ]

        data = [
            self.ui.lineEdit_patient_key.text(),
            self.ui.lineEdit_name.text(),
            self.ui.dateEdit_examination_date.date().toString('yyyy-MM-dd'),
            self.comboBox_laboratory.currentText(),
            self.comboBox_MLS.currentText(),
        ]

        if self.examination_key is not None:
            examination_key = self.examination_key
            self.database.update_record('examination', fields, 'ExaminationKey', examination_key, data)
        else:
            examination_key = self.database.insert_record('examination', fields, data)

        self._save_examination_item(examination_key)
        self._clear_examination()
        if self.examination_key is not None or self.patient_key is not None:
            self.close_examination()

    def _save_examination_item(self, examination_key):
        self.database.delete_record('examination_item', 'ExaminationKey', examination_key)

        fields = [
            'ExaminationKey', 'PatientKey', 'Name', 'ExaminationDate', 'ExaminationItem', 'TestResult',
        ]

        for row_no in range(self.ui.tableWidget_examination_item.rowCount()):
            test_result = self.ui.tableWidget_examination_item.item(row_no, 4).text()
            if test_result in [None, '']:
                continue

            data = [
                examination_key,
                self.ui.lineEdit_patient_key.text(),
                self.ui.lineEdit_name.text(),
                self.ui.dateEdit_examination_date.date().toString('yyyy-MM-dd'),
                self.ui.tableWidget_examination_item.item(row_no, 3).text(),
                test_result,
            ]

            self.database.insert_record('examination_item', fields, data)

    def _clear_examination(self):
        self.ui.lineEdit_patient_key.setText(None)
        self.ui.lineEdit_name.setText(None)
        self.ui.dateEdit_examination_date.setDate(datetime.datetime.today())
        self.ui.comboBox_laboratory.setCurrentText(None)
        self.ui.comboBox_MLS.setCurrentText(None)

        self._set_examination_items()

    def _examination_item_changed(self, item):
        height, weight, bmi = None, None, None

        for row_no in range(self.ui.tableWidget_examination_item.rowCount()):
            item = self.ui.tableWidget_examination_item.item(row_no, 3)
            test_result = self.ui.tableWidget_examination_item.item(row_no, 4)
            if item.text() == '身高' and test_result is not None:
                height = test_result.text()
            elif item.text() == '體重' and test_result is not None:
                weight = test_result.text()

        try:
            height = number_utils.get_float(height) / 100
        except Exception:
            height = None

        try:
            weight = number_utils.get_float(weight)
        except Exception:
            weight = None

        if height is None or height == 0 or weight is None or weight == 0 or bmi == 0:
            bmi = None
        else:
            bmi = round(weight / (height * height), 2)

        self._set_bmi(bmi)

    def _set_bmi(self, bmi):
        self.ui.tableWidget_examination_item.itemChanged.disconnect()

        for row_no in range(self.ui.tableWidget_examination_item.rowCount()):
            item = self.ui.tableWidget_examination_item.item(row_no, 3)
            if item.text() == '身體質量指數':
                self.ui.tableWidget_examination_item.setItem(
                    row_no, 4,
                    QtWidgets.QTableWidgetItem(string_utils.xstr(bmi))
                )
                break

        self.ui.tableWidget_examination_item.itemChanged.connect(self._examination_item_changed)

    def _preset_patient(self):
        self.ui.lineEdit_patient_key.setText(string_utils.xstr(self.patient_key))
        if self.examination_date is not None:
            self.ui.dateEdit_examination_date.setDate(self.examination_date)

        self.ui.tableWidget_examination_item.setCurrentCell(0, 4)
        self.ui.tableWidget_examination_item.setFocus()
