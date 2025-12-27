
# -*- coding: UTF-8 -*-

import calendar
import csv

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QPushButton

from libs import (class_utils, date_utils, nhi_utils, string_utils,
                  system_utils, ui_utils)


# 照護機構院民資料 2022-05-20
class StatisticsNursingHomeData(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsNursingHomeData, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.year = args[2]
        self.month = args[3]
        self.ui = None

        last_day = calendar.monthrange(int(self.year), int(self.month))[1]
        self.start_date = f'{self.year}-{self.month}-1'
        self.end_date = f'{self.year}-{self.month}-{last_day}'
        self.clinic_name = self.system_settings.field('院所名稱')
        self.clinic_id = self.system_settings.field('院所代號')

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_NURSING_HOME_DATA, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_patient = class_utils.get_table_widget(
            self.ui.tableWidget_patient, self.database
        )
        self.table_widget_patient.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        width = [
            100,
            100, 300, 300, 120, 120, 200, 200, 120
        ]
        self.table_widget_patient.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_patient.doubleClicked.connect(self.open_patient_record)
        self.ui.pushButton_export_csv.clicked.connect(self._export_to_csv)
        self.ui.pushButton_import_csv.clicked.connect(self._import_from_csv)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def open_patient_record(self):
        patient_key = self.table_widget_patient.field_value(0)
        self.parent.parent.open_patient_record(patient_key, '照護機構院民資料報表')

    def refresh_patient_record(self):
        patient_key = self.table_widget_patient.field_value(0)

        if patient_key in ['', None]:
            return

        sql = f'SELECT * FROM patient WHERE PatientKey = {patient_key}'
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]
        row_no = self.ui.tableWidget_patient.currentRow()
        self._set_table_data(row_no, row)

    def read_data(self):
        sql = f'''
            SELECT
                cases.CaseKey, patient.*
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                DATE(CaseDate) BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                cases.InsType = "健保" AND
                cases.RegistType = "{nhi_utils.LONG_TERM_CARE[0]}"
            GROUP BY PatientKey
            ORDER BY CaseDate
        '''
        self.table_widget_patient.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        apply_date = f'{int(self.year)-1911:0>3}{self.month:0>2}'
        nursing_home = string_utils.xstr(row['NursingHome'])
        nursing_home_id = string_utils.xstr(row['NursingHomeID'])
        patient_name = string_utils.xstr(row['Name'])
        patient_id = string_utils.xstr(row['ID'])
        birthday = date_utils.west_date_to_nhi_date(row['Birthday'])
        try:
            nursing_home_in_date = date_utils.west_date_to_nhi_date(row['NursingHomeInDate'])
        except ValueError:
            try:
                nursing_home_date = string_utils.xstr(row['NursingHomeInDate'])
                separator = date_utils.get_date_separator(nursing_home_date)
                year, month, day = nursing_home_date.split(separator)
                nursing_home_in_date = f'{year}{month}{day}'
            except Exception:
                nursing_home_in_date = '入院日期不正確'

        nursing_home_out_date = None

        patient_record = [
            string_utils.xstr(row['PatientKey']),
            apply_date,
            f'{self.clinic_id} {self.clinic_name}',
            f'{nursing_home_id} {nursing_home}',
            patient_id,
            birthday,
            nursing_home_in_date,
            nursing_home_out_date,
            patient_name,
        ]

        for col_no in range(len(patient_record)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, patient_record[col_no])
            self.ui.tableWidget_patient.setItem(row_no, col_no, item)

            if col_no in [1]:
                self.ui.tableWidget_patient.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _export_to_csv(self):
        filename = f'care_{self.clinic_id}_{int(self.year)-1911:0>3}{self.month:0>2}.csv'
        options = QFileDialog.Options()

        csv_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出CSV",
            filename,
            "CSV檔案 (*.csv)", options=options
        )
        if not csv_file_name:
            return

        with open(csv_file_name, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for row_no in range(self.ui.tableWidget_patient.rowCount()):
                row = []
                for col_no in range(1, self.ui.tableWidget_patient.columnCount()):
                    try:
                        data = self.ui.tableWidget_patient.item(row_no, col_no).text()
                        if col_no in [2, 3]:
                            data = data.split(' ')[0]

                        row.append(data)
                    except Exception:
                        row.append(None)

                writer.writerow(row)

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>{csv_file_name}匯出完成.</h3>',
            'CSV 格式.'
        )

    def _import_from_csv(self):
        options = QFileDialog.Options()

        options |= QFileDialog.DontUseNativeDialog
        finame, _ = QFileDialog.getOpenFileName(
            self, "匯入院民資料",
            '*.csv',
            "CSV檔案 (*);;csv檔 (*.csv)", options=options
        )
        if not finame:
            return

        self._import_csv_data(finame)

    def _import_csv_data(self, filename):
        with open(filename, encoding='big5', newline='') as csv_file:
            rows = csv.DictReader(csv_file)

            for row in rows:
                patient_id = row['身分證']
                if patient_id in ['', None]:
                    continue

                in_nursing_date = row['入住日期']
                sql = f'''
                    SELECT PatientKey FROM patient
                    WHERE
                        ID = "{patient_id}" AND
                        NursingHomeInDate IS NULL OR
                        LENGTH(NursingHomeInDate) = 0
                '''
                rows = self.database.select_record(sql)
                if len(rows) <= 0:
                    continue

                patient_key = rows[0]['PatientKey']
                sql = f'''
                    UPDATE patient
                    SET
                       NursingHomeInDate = "{in_nursing_date}" 
                    WHERE
                        PatientKey = "{patient_key}"
                '''
                self.database.exec_sql(sql)

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('檔案匯入完成')
        msg_box.setText("<font size='4'><b>院民資料檔匯入完成.</b></font>")
        msg_box.setInformativeText("請按確定鍵結束.")
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

        self.read_data()
