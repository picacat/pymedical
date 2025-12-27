
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
import os
import sys

from libs import class_utils

from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import case_utils
from libs import db_utils


# 主視窗
class DialogMedicalRecordHosts(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMedicalRecordHosts, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_id = args[2]

        self.ui = None
        self.copy_medical_record = True
        self.data_base_list = {}

        self._set_ui()
        self._set_signal()
        self._read_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MEDICAL_RECORD_HOSTS, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('拷貝病歷')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_medical_records = class_utils.get_table_widget(
            self.ui.tableWidget_medical_records, self.database
        )
        self.table_widget_medical_records.set_column_hidden([0])
        self.table_widget_image_history = class_utils.get_table_widget(
            self.ui.tableWidget_image_history, self.database
        )
        self._set_table_width()
        self.ui.tabWidget_hosts.setCurrentIndex(0)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 170, 125, 50, 80, 60, 50, 200, 40, 80, 80]
        self.table_widget_medical_records.set_table_heading_width(width)

        width = [330, 330, 330, 330, 330]
        self.table_widget_image_history.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_medical_records.itemSelectionChanged.connect(self._medical_record_changed)
        self.ui.tableWidget_image_history.doubleClicked.connect(self._open_image_file)

        self.ui.pushButton_top.clicked.connect(self._top_record)
        self.ui.pushButton_next.clicked.connect(self._next_record)
        self.ui.pushButton_prev.clicked.connect(self._prev_record)
        self.ui.pushButton_bottom.clicked.connect(self._bottom_record)

    def _top_record(self):
        self.current_page = 1

        self._read_medical_records(self.current_page)
        self._set_page_button()

    def _prev_record(self):
        if self.current_page > 1:
            self.current_page -= 1

        self._read_medical_records(self.current_page)
        self._set_page_button()

    def _next_record(self):
        if self.current_page < self.total_pages:
            self.current_page += 1

        self._read_medical_records(self.current_page)
        self._set_page_button()

    def _bottom_record(self):
        self.current_page = self.total_pages

        self._read_medical_records(self.current_page)
        self._set_page_button()

    def accepted_button_clicked(self):
        if not self.copy_medical_record:
            return

        case_key = self.table_widget_medical_records.field_value(0)
        clinic_name = self.table_widget_medical_records.field_value(1)
        database = self.database_list[clinic_name]['database']

        if self.ui.radioButton_ins_prescript.isChecked():
            copy_ins_prescript_to = '健保處方'
        else:
            copy_ins_prescript_to = '自費處方'

        case_utils.copy_host_medical_record(
            database, self.parent, case_key,
            self.ui.checkBox_diagnostic.isChecked(),
            self.ui.checkBox_remark.isChecked(),
            self.ui.checkBox_disease.isChecked(),
            self.ui.checkBox_ins_prescript.isChecked(),
            copy_ins_prescript_to,
            self.ui.checkBox_ins_treat.isChecked(),
            self.ui.checkBox_self_prescript.isChecked(),
        )

    def _read_data(self):
        self.current_page = 1
        self.count_per_page = number_utils.get_integer(self.system_settings.field('過去病歷一頁筆數'))
        if self.count_per_page <= 0:  # 預設值
            self.count_per_page = 30

        self._set_total_page()
        self._read_medical_records(self.current_page)
        try:
            self._read_images()
        except Exception:
            pass

    def _set_total_page(self):
        self.database_list = db_utils.get_host_database_dict(self.database, '顯示分院病歷')
        row_count = 0
        for clinic_name in self.database_list.keys():
            database = self.database_list[clinic_name]['database']
            row_count += self._get_medical_record_count(database)

        self.total_pages = int(row_count / self.count_per_page)
        if row_count % self.count_per_page > 0:
            self.total_pages += 1

        self.ui.label_total_pages.setText(f'共{self.total_pages}頁')
        self._set_page_button()

    def _set_page_button(self):
        self.ui.label_current_page.setText(f'第{self.current_page}頁')

    def _get_medical_record_count(self, database_hosts):
        sql = f'''
            SELECT PatientKey FROM patient
            WHERE
                ID = "{self.patient_id}"
        '''
        rows = database_hosts.select_record(sql)

        if len(rows) <= 0:
            return 0

        self.patient_key = rows[0]['PatientKey']
        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                PatientKey = {self.patient_key}
        '''
        rows = database_hosts.select_record(sql)

        return len(rows)

    def _read_medical_records(self, page=1):
        medical_records = []
        self.database_list = db_utils.get_host_database_dict(self.database, '顯示分院病歷')
        for clinic_name in self.database_list.keys():
            database = self.database_list[clinic_name]['database']
            HIS_version = self.database_list[clinic_name]['HISVersion']

            medical_records += self._get_medical_records(database, clinic_name, HIS_version, page)

        if len(medical_records) <= 0:
            br = '<br>' * 12
            html = f'''
                {br}
                <center><b>無分院病歷</b></center>
            '''
            self.ui.textEdit_medical_record.setHtml(html)
            self.ui.groupBox_copy_option.setEnabled(False)
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

            return

        self._set_group_box_title(medical_records[0])
        self._set_table_data(medical_records)

    def _get_medical_records(self, database_hosts, clinic_name, HIS_version, page=1):
        if HIS_version == 'Medical':
            gender = 'Sex'
            treat_type = 'RegistType'
        else:
            gender = 'Gender'
            treat_type = 'TreatType'

        medical_records = []
        sql = f'''
            SELECT PatientKey, {gender}, Birthday FROM patient
            WHERE
                ID = "{self.patient_id}"
        '''
        rows = database_hosts.select_record(sql)

        if len(rows) <= 0:
            return medical_records

        self.patient_key = rows[0]['PatientKey']
        gender = rows[0][gender]
        birthday = rows[0]['Birthday']

        start_index = ((page-1) * self.count_per_page)
        sql = f'''
            SELECT
                CaseKey, PatientKey, Name, CaseDate, InsType, {treat_type},
                Card, Continuance, PresDays1, PresDays2,
                DiseaseName1, Doctor, TotalFee
            FROM cases
            WHERE
                PatientKey = {self.patient_key}
            ORDER BY CaseDate DESC
            LIMIT {start_index}, {self.count_per_page}
        '''
        rows = database_hosts.select_record(sql)

        if len(rows) <= 0:
            return medical_records

        for row in rows:
            case_key = row['CaseKey']

            pres_days1 = case_utils.get_pres_days(self.database, case_key, medicine_set=1)
            pres_days2 = case_utils.get_pres_days(self.database, case_key, medicine_set=2)

            medical_records.append(
                {
                    'CaseKey': case_key,
                    'ClinicName': clinic_name,
                    'PatientKey': row['PatientKey'],
                    'Name': row['Name'],
                    'Gender': gender,
                    'Birthday': birthday,
                    'CaseDate': row['CaseDate'],
                    'InsType': row['InsType'],
                    'TreatType': row[treat_type],
                    'Card': row['Card'],
                    'Continuance': row['Continuance'],
                    'PresDays1': pres_days1,
                    'PresDays2': pres_days2,
                    'DiseaseName1': row['DiseaseName1'],
                    'Doctor': row['Doctor'],
                    'TotalFee': row['TotalFee'],
                    'HISVersion': HIS_version,
                }
            )

        return medical_records

    def _set_table_data(self, medical_records):
        record_count = len(medical_records)

        self.ui.tableWidget_medical_records.setRowCount(record_count)
        for row_no, row in zip(range(record_count), medical_records):
            self._set_row_data(row_no, row)

        self.ui.tableWidget_medical_records.setAlternatingRowColors(True)
        self.ui.tableWidget_medical_records.resizeRowsToContents()
        self.ui.tableWidget_medical_records.sortItems(2, QtCore.Qt.DescendingOrder)
        self.ui.tableWidget_medical_records.setCurrentCell(0, 1)

    def _set_row_data(self, row_no, row):
        case_key = row['CaseKey']
        if row['InsType'] == '健保':
            medicine_set = 1
        else:
            medicine_set = 2

        HIS_version = string_utils.xstr(row['HISVersion'])

        clinic_name = string_utils.xstr(row['ClinicName'])
        database = self.database_list[clinic_name]['database']
        pres_days = row[f'PresDays{medicine_set}']
        pres_days = case_utils.get_pres_days(database, case_key, medicine_set)

        if pres_days == 0:
            pres_days = ''

        total_fee = number_utils.get_integer(row['TotalFee'])
        medical_record_data = [
            string_utils.xstr(case_key),
            clinic_name,
            string_utils.xstr(row['CaseDate'].date()),
            string_utils.xstr(row['InsType']),
            string_utils.xstr(row['TreatType']),
            string_utils.xstr(row['Card']),
            string_utils.xstr(row['Continuance']),
            string_utils.xstr(row['DiseaseName1']),
            string_utils.xstr(pres_days),
            string_utils.xstr(row['Doctor']),
            f'{total_fee:,}',
        ]

        for column in range(len(medical_record_data)):
            self.ui.tableWidget_medical_records.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(medical_record_data[column])
            )
            if column in [0, 8, 10]:
                self.ui.tableWidget_medical_records.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif column in [6]:
                self.ui.tableWidget_medical_records.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if row['InsType'] == '自費' or number_utils.get_integer(row['TotalFee']) > 0:
                self.ui.tableWidget_medical_records.item(
                    row_no, column).setForeground(
                    QtGui.QColor('blue')
                )

            if row['Continuance'] == 1:
                self.ui.tableWidget_medical_records.item(
                    row_no, column).setForeground(
                    QtGui.QColor('darkred')
                )

    def _set_group_box_title(self, row):
        name = string_utils.xstr(row['Name'])
        gender = string_utils.xstr(row['Gender'])
        birthday = string_utils.xstr(row['Birthday'])
        self.ui.groupBox_medical_record.setTitle(f'{name}({gender}) 出生日期: {birthday}  病歷內容')

    def _medical_record_changed(self):
        case_key = self.table_widget_medical_records.field_value(0)
        clinic_name = self.table_widget_medical_records.field_value(1)

        self._set_copy_prescript_check_box()
        html = case_utils.get_medical_record_html(
            self.database_list[clinic_name]['database'], self.system_settings, case_key
        )
        self.ui.textEdit_medical_record.setHtml(html)

    def _set_copy_prescript_check_box(self):
        case_key = self.table_widget_medical_records.field_value(0)
        clinic_name = self.table_widget_medical_records.field_value(1)
        ins_type = self.table_widget_medical_records.field_value(3)
        database = self.database_list[clinic_name]['database']

        self.ui.checkBox_ins_prescript.setChecked(False)  # 健保療程2-6次預設不拷貝藥品
        self.ui.checkBox_ins_prescript.setEnabled(False)  # 健保療程2-6次預設不拷貝藥品

        self.ui.radioButton_ins_prescript.setEnabled(False)
        self.ui.radioButton_self_prescript.setEnabled(False)

        self.ui.checkBox_ins_treat.setChecked(False)
        self.ui.checkBox_ins_treat.setEnabled(False)

        if ins_type == '健保':
            sql = f'''
                SELECT Treatment FROM cases
                WHERE
                    CaseKey = {case_key}
            '''
            rows = database.select_record(sql)
            treatment = string_utils.xstr(rows[0]['Treatment'])

            if treatment != '':
                self.ui.checkBox_ins_treat.setEnabled(True)
                self.ui.checkBox_ins_treat.setChecked(True)

            sql = f'''
                SELECT PrescriptKey FROM prescript
                WHERE
                    CaseKey = {case_key} AND
                    MedicineSet = 1
            '''
            rows = database.select_record(sql)
            if len(rows) > 0:
                self.ui.checkBox_ins_prescript.setEnabled(True)
                self.ui.radioButton_ins_prescript.setEnabled(True)
                self.ui.radioButton_self_prescript.setEnabled(True)
                if treatment == '':
                    self.ui.checkBox_ins_prescript.setChecked(True)  # 預設非療程才拷貝藥品

        sql = f'''
            SELECT MedicineSet FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2
        '''
        rows = database.select_record(sql)
        if len(rows) > 0:
            copy_self_prescript = True
        else:
            copy_self_prescript = False

        self.ui.checkBox_self_prescript.setEnabled(copy_self_prescript)
        self.ui.checkBox_self_prescript.setChecked(copy_self_prescript)
        if copy_self_prescript:
            self.ui.checkBox_self_prescript.setChecked(False)  # 預設不要拷貝

    def _read_images(self):
        image_database_list = db_utils.get_host_database_dict(self.database, '顯示分院病歷')
        image_list = []
        for clinic_name in image_database_list.keys():
            database = image_database_list[clinic_name]['database']
            image_dir = image_database_list[clinic_name]['image_dir']

            image_list += self._get_images(database, clinic_name, image_dir)

        self._fit_images_list_to_table_widget(image_list)

    def _get_images(self, database, clinic_name, image_dir):
        sql = f'''
            SELECT PatientKey FROM patient
            WHERE
                ID = "{self.patient_id}"
        '''
        rows = database.select_record(sql)

        if len(rows) <= 0:
            return []

        patient_key = rows[0]['PatientKey']
        sql = f'''
            SELECT images.*, cases.CaseDate FROM images
                LEFT JOIN cases ON cases.CaseKey = images.CaseKey
            WHERE
                images.PatientKey = {patient_key}
            ORDER BY Filename DESC
        '''

        rows = database.select_record(sql)
        if len(rows) <= 0:
            return []

        image_list = []
        for row in rows:
            filename = string_utils.xstr(row['Filename'])
            full_filename = os.path.join(image_dir, filename)
            try:
                image_date = row['CaseDate'].date()
            except Exception:
                image_date = row['TimeStamp'].date()

            image_file = full_filename
            filename = os.path.basename(full_filename)
            image_label = QtWidgets.QLabel(self.ui.tableWidget_image_history)
            image_label.setTextFormat(QtCore.Qt.RichText)
            image_label.setText(f'''
                {clinic_name} {image_date}<br>
                <img src="{image_file}" width="320" height="180" align=middle><br>
                {full_filename}
            ''')
            image_list.append(image_label)

        return image_list

    def _fit_images_list_to_table_widget(self, image_list):
        image_count = len(image_list)
        column_count = self.ui.tableWidget_image_history.columnCount()

        row_count = int(image_count / column_count)
        if image_count % column_count > 0:
            row_count += 1

        self.ui.tableWidget_image_history.setRowCount(row_count)
        for row_no in range(row_count):
            for col_no in range(column_count):
                index = (row_no * column_count) + col_no
                if index >= image_count:
                    break

                image_label = image_list[index]
                self.ui.tableWidget_image_history.setCellWidget(row_no, col_no, image_label)

        self.ui.tableWidget_image_history.resizeRowsToContents()
        self.ui.tableWidget_image_history.setCurrentCell(0, 0)

    def _open_image_file(self):
        row_no = self.ui.tableWidget_image_history.currentRow()
        col_no = self.ui.tableWidget_image_history.currentColumn()

        label_image = self.ui.tableWidget_image_history.cellWidget(row_no, col_no)
        filename = label_image.text().split('<br>')[2].strip()

        if sys.platform == 'win32':
            os.system(f'start "" "{filename}"')
        else:
            desktop_session = os.environ.get("DESKTOP_SESSION")
            if desktop_session is not None:
                desktop_session = desktop_session.lower()

            if desktop_session == 'plasma':  # kde
                os.system(f'gwenview {filename}')
            else:
                os.system(f'viewnior {filename}')