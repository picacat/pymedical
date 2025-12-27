# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox, QFileDialog
import datetime

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import case_utils
from libs import string_utils
from libs import date_utils
from libs import db_utils
from libs import log_utils


# 匯出病歷JSON 2021.07.17
class DialogExportMedicalRecordJSON(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogExportMedicalRecordJSON, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_EXPORT_MEDICAL_RECORD_JSON, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('匯出')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )

        self.table_widget_medical_record.set_column_hidden([0])
        self.ui.dateEdit_start_date.setDate(datetime.datetime.now())
        self.ui.dateEdit_end_date.setDate(datetime.datetime.now())

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.button_accepted)
        self.ui.buttonBox.rejected.connect(self.button_rejected)
        self.ui.pushButton_read_medical_record.clicked.connect(self._read_medical_record)
        self.ui.toolButton_set_bookmark.clicked.connect(self._set_bookmark)
        self.ui.dateEdit_start_date.dateChanged.connect(self._set_date_edit)
        self.ui.tableWidget_medical_record.horizontalHeader().sectionClicked.connect(self._header_clicked)

    def _set_date_edit(self):
        self.ui.dateEdit_end_date.setDate(self.ui.dateEdit_start_date.date())

    def button_accepted(self):
        self._export_json_files()

    def button_rejected(self):
        pass

    def _read_medical_record(self):
        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')
        sql = f'''
            SELECT cases.* FROM cases
                LEFT JOIN deposit ON deposit.CaseKey = cases.CaseKey
            WHERE
                (cases.CaseDate BETWEEN "{start_date}" AND "{end_date}" OR
                 deposit.ReturnDate BETWEEN "{start_date}" AND "{end_date}") AND
                cases.DoctorDone = "True"
            GROUP BY cases.CaseKey
            ORDER BY cases.CaseDate
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        self.table_widget_medical_record.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        if row['InsType'] == '健保':
            medicine_set = 1
        else:
            medicine_set = 2

        case_key = string_utils.xstr(row['CaseKey'])
        pres_days = case_utils.get_pres_days(self.database, case_key, medicine_set)

        full_card = case_utils.get_full_card(row['Card'], row['Continuance'])

        medical_record = [
            string_utils.xstr(row['CaseKey']),
            None,
            string_utils.xstr(row['CaseDate']),
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['InsType']),
            string_utils.xstr(row['Share']),
            string_utils.xstr(row['TreatType']),
            full_card,
            string_utils.int_to_str(pres_days),
            string_utils.xstr(row['Doctor']),
            string_utils.xstr(row['DiseaseName1']),
        ]

        for column in range(len(medical_record)):
            self.ui.tableWidget_medical_record.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(medical_record[column])
            )
            if column in [4, 11]:
                self.ui.tableWidget_medical_record.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif column in [1, 3, 6]:
                self.ui.tableWidget_medical_record.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

        self._set_check_box(row_no, True)

    def _set_check_box(self, row_no, checked):
        check_box = QtWidgets.QCheckBox()
        check_box.setStyleSheet('padding-left: 20px')
        check_box.setChecked(checked)
        check_box.clicked.connect(lambda: self._set_row_color(row_no, check_box.isChecked()))
        col_no = 1

        self.ui.tableWidget_medical_record.setCellWidget(
            row_no, col_no, check_box)
        self.ui.tableWidget_medical_record.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        self._set_row_color(row_no, checked)

    def _set_row_color(self, row_no, checked):
        if checked:
            color = 'black'
        else:
            color = 'darkGray'

        for col_no in range(self.ui.tableWidget_medical_record.columnCount()):
            self.ui.tableWidget_medical_record.item(row_no, col_no).setForeground(QtGui.QColor(color))

    def _export_json_files(self):
        options = QFileDialog.Options()
        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd')
        json_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出JSON檔案",
            f'{start_date}至{end_date}病歷資料.json',
            "json檔案 (*.json)",
            options=options
        )
        if not json_file_name:
            return

        row_count = self.ui.tableWidget_medical_record.rowCount()
        case_key_list = []
        for row_no in range(row_count):
            check_box = self.ui.tableWidget_medical_record.cellWidget(row_no, 1)
            if not check_box.isChecked():
                continue

            case_key = self.ui.tableWidget_medical_record.item(row_no, 0).text()
            case_key_list.append(case_key)

        if len(case_key_list) <= 0:
            return

        db_utils.export_medical_record_to_json(self, self.database, json_file_name, case_key_list)

        system_utils.show_message_box(
            QMessageBox.Information,
            'JSON資料匯出完成',
            f'<h3>病歷資料 {json_file_name}匯出完成.</h3>',
            'JSON 檔案格式.'
        )

        log = f'{date_utils.now_to_str()}匯出JSON檔案, 檔案名稱: {json_file_name}'
        self._write_event_log('JSON資料匯出', log)

    def _write_event_log(self, log_type, log):
        log_utils.write_event_log(
            self.database, self.system_settings.field('使用者'),
            log_type, '匯出病歷JSON', log
        )

    def _set_bookmark(self):
        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            self._header_clicked(1)

    def _header_clicked(self, col_no):
        if col_no != 1:
            return

        row_count = self.ui.tableWidget_medical_record.rowCount()
        for row_no in range(row_count):
            check_box = self.ui.tableWidget_medical_record.cellWidget(row_no, col_no)
            check_box.setChecked(not check_box.isChecked())
            self._set_row_color(row_no, check_box.isChecked())
