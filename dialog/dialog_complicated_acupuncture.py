
# 複雜性針灸選取視窗 2021.02.24
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import prescript_utils


# 主視窗
class DialogComplicatedAcupuncture(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogComplicatedAcupuncture, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.treatment = args[2]
        self.second_treatment = args[3]
        self.disease_code = args[4]
        self.diag_time = args[5]
        self.table_widget_treat = args[6]

        if self.diag_time is None:
            self.diag_time = datetime.datetime.now()

        self.ui = None
        self.accept_treats = False
        self.position_keyword = '治療部位:'
        self.auxiliary_keyword = '輔助治療:'

        self.default_moderate_acupuncture_time, self.default_highly_acupuncture_time = \
            prescript_utils.get_default_complicated_acupuncture_time(self.system_settings)

        self._set_ui()
        self._set_signal()

        self._set_selected_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_COMPLICATED_ACUPUNCTURE, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.setWindowTitle(self.treatment)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        if self.treatment in ['針灸治療', '一般針灸']:
            self.ui.label_position.hide()
            self.ui.label_treat_time.hide()
            self.ui.label_cure.hide()
        else:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        if self.treatment in [
            '一般針灸', '電針', '中度複雜性針灸', '一般傷科', '中度複雜性傷科'
        ] and self.second_treatment in [None, '']:
            minutes = 10
        elif self.treatment in [
            '高度複雜性針灸', '高度複雜性傷科', '中度複雜性傷科合併特殊疾病', '脫臼整復復位', '骨折復位'
        ] and self.second_treatment in [None, '']:
            minutes = 20
        elif '一般' in self.treatment and '一般' in self.second_treatment:
            minutes = 10
        elif '一般' in self.treatment and '中度' in self.second_treatment:
            minutes = 10
        elif '一般' in self.treatment and '高度' in self.second_treatment:
            minutes = 20
        elif '中度' in self.treatment and '一般' in self.second_treatment:
            minutes = 10
        elif '中度' in self.treatment and '中度' in self.second_treatment:
            minutes = 20
        elif '中度' in self.treatment and '高度' in self.second_treatment:
            minutes = 30
        elif '高度' in self.treatment and '一般' in self.second_treatment:
            minutes = 20
        elif '高度' in self.treatment and '中度' in self.second_treatment:
            minutes = 30
        elif '高度' in self.treatment and '高度' in self.second_treatment:
            minutes = 40
        else:
            minutes = 20

        if minutes == 10 and self.default_moderate_acupuncture_time > minutes:
            minutes = self.default_moderate_acupuncture_time
        elif minutes == 20 and self.default_highly_acupuncture_time > minutes:
            minutes = self.default_highly_acupuncture_time

        self.ui.label_treat_time.setText(f'至少{minutes}分鐘')
        self.ui.spinBox_time.setMinimum(minutes)
        self.ui.spinBox_time.setValue(minutes)

        self.ui.timeEdit_start_time.setTime(self.diag_time.time())
        self.ui.timeEdit_end_time.setTime(
            self.ui.timeEdit_start_time.time().addSecs(minutes * 60)
        )
        self.ui.timeEdit_start_time.setCurrentSection(QtWidgets.QDateTimeEdit.MinuteSection)
        self.ui.timeEdit_end_time.setCurrentSection(QtWidgets.QDateTimeEdit.MinuteSection)

        if self.system_settings.field('院所名稱') == '信望愛中醫診所':
            self.ui.checkBox_1.setChecked(True)
            self.ui.checkBox_3.setChecked(True)
            self.ui.checkBox_4.setChecked(True)
            # self.ui.spinBox_time.setValue(20)  # 改回正常預設值

        self.table_widget_acupuncture_point = class_utils.get_table_widget(
            self.ui.tableWidget_acupuncture_point, self.database
        )
        self.ui.tableWidget_acupuncture_point.setAlternatingRowColors(True)
        if self.disease_code not in [None, '']:
            self._set_frequently_acupuncture_point()

        if self.second_treatment in ['', None]:
            self.ui.groupBox_massage.setVisible(False)

            self.ui.checkBox_8.setEnabled(False)
            self.ui.checkBox_9.setEnabled(False)
            self.ui.checkBox_10.setEnabled(False)

        self.treat_position1_list = [
            self.ui.checkBox_c1,
            self.ui.checkBox_c2,
        ]

        self.treat_position2_list = [
            self.ui.checkBox_c3,
            self.ui.checkBox_c4,
            self.ui.checkBox_c5,
            self.ui.checkBox_c6,
            self.ui.checkBox_c7,
        ]

        self.treat_position3_list = [
            self.ui.checkBox_lu1,
            self.ui.checkBox_lu2,
            self.ui.checkBox_lu3,
            self.ui.checkBox_lu4,
            self.ui.checkBox_lu5,
            self.ui.checkBox_lu6,
            self.ui.checkBox_lu7,
        ]

        self.treat_position4_list = [
            self.ui.checkBox_lb1,
            self.ui.checkBox_lb2,
            self.ui.checkBox_lb3,
            self.ui.checkBox_lb4,
            self.ui.checkBox_lb5,
            self.ui.checkBox_lb6,
        ]
        self.treat_position5_list = [
            self.ui.checkBox_ru1,
            self.ui.checkBox_ru2,
            self.ui.checkBox_ru3,
            self.ui.checkBox_ru4,
            self.ui.checkBox_ru5,
            self.ui.checkBox_ru6,
            self.ui.checkBox_ru7,
        ]
        self.treat_position6_list = [
            self.ui.checkBox_rb1,
            self.ui.checkBox_rb2,
            self.ui.checkBox_rb3,
            self.ui.checkBox_rb4,
            self.ui.checkBox_rb5,
            self.ui.checkBox_rb6,
        ]

        self.treat_position_list = \
            self.treat_position1_list + \
            self.treat_position2_list + \
            self.treat_position3_list + \
            self.treat_position4_list + \
            self.treat_position5_list + \
            self.treat_position6_list

        self.treat_auxiliary_list = [
            self.ui.checkBox_1,
            self.ui.checkBox_2,
            self.ui.checkBox_3,
            self.ui.checkBox_4,
            self.ui.checkBox_5,
            self.ui.checkBox_6,
            self.ui.checkBox_7,
            self.ui.checkBox_8,
            self.ui.checkBox_9,
            self.ui.checkBox_10,
        ]

        self.treat_massage_list = [
            self.ui.checkBox_massage1,
            self.ui.checkBox_massage2,
            self.ui.checkBox_massage3,
            self.ui.checkBox_massage4,
            self.ui.checkBox_massage5,
            self.ui.checkBox_massage6,
            self.ui.checkBox_massage7,
            self.ui.checkBox_massage8,
            self.ui.checkBox_massage9,
            self.ui.checkBox_massage10,
            self.ui.checkBox_massage11,
            self.ui.checkBox_massage12,
            self.ui.checkBox_massage13,
            self.ui.checkBox_massage14,
            self.ui.checkBox_massage15,
            self.ui.checkBox_massage16,
            self.ui.checkBox_massage17,
            self.ui.checkBox_massage18,
            self.ui.checkBox_massage19,
        ]

    def _set_treat_time(self):
        self.ui.timeEdit_end_time.setTime(
            self.ui.timeEdit_start_time.time().addSecs(self.ui.spinBox_time.value() * 60)
        )

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

        self.ui.timeEdit_start_time.timeChanged.connect(self._set_treat_time)
        self.ui.timeEdit_end_time.timeChanged.connect(self._set_treat_time)
        self.ui.spinBox_time.valueChanged.connect(self._set_treat_time)

        for check_box in self.treat_position_list + self.treat_auxiliary_list + self.treat_massage_list:
            check_box.clicked.connect(self._check_available)

    def _set_selected_data(self):
        self._set_selected_position()
        self._set_selected_auxiliary()
        self._set_selected_acupuncture_point()
        self._set_selected_massage()

        self._check_available()

    def _set_selected_position(self):
        for row_no in range(self.table_widget_treat.rowCount()):
            item = self.table_widget_treat.item(row_no, prescript_utils.INS_TREAT_COL_NO['MedicineName'])
            if item is None:
                continue

            medicine_name = item.text()
            if self.position_keyword not in medicine_name:
                continue

            position = medicine_name.replace(self.position_keyword, '').strip()
            for check_box in self.treat_position_list:
                if check_box.text() == position:
                    check_box.setChecked(True)

    def _set_selected_auxiliary(self):
        for row_no in range(self.table_widget_treat.rowCount()):
            item = self.table_widget_treat.item(row_no, prescript_utils.INS_TREAT_COL_NO['MedicineName'])
            if item is None:
                continue

            medicine_name = item.text()
            if self.auxiliary_keyword not in medicine_name:
                continue

            auxiliary_treat = medicine_name.replace(self.auxiliary_keyword, '').strip()
            for check_box in self.treat_auxiliary_list:
                if check_box.text() in ['藥薰治療', '膏布治療', '夾板固定治療']:
                    continue

                if check_box.text() == auxiliary_treat:
                    check_box.setChecked(True)

    def _set_selected_acupuncture_point(self):
        for row_no in range(self.table_widget_treat.rowCount()):
            item = self.table_widget_treat.item(row_no, prescript_utils.INS_TREAT_COL_NO['MedicineName'])
            if item is None:
                continue

            medicine_name = item.text()
            self._set_table_widget_acupuncture_point(medicine_name)

    def _set_selected_massage(self):
        for row_no in range(self.table_widget_treat.rowCount()):
            item = self.table_widget_treat.item(row_no, prescript_utils.INS_TREAT_COL_NO['MedicineName'])
            if item is None:
                continue

            medicine_name = item.text()
            for check_box in self.treat_massage_list:
                if check_box.text() == medicine_name:
                    check_box.setChecked(True)

    def _set_table_widget_acupuncture_point(self, medicine_name):
        for row_no in range(self.ui.tableWidget_acupuncture_point.rowCount()):
            for col_no in range(self.ui.tableWidget_acupuncture_point.columnCount()):
                check_box = self.ui.tableWidget_acupuncture_point.cellWidget(row_no, col_no)
                if check_box is None:
                    continue

                if check_box.text() == medicine_name:
                    check_box.setChecked(True)
                    check_box.setStyleSheet('padding-left: 5px; color:blue; font-weight:bold')

    def _check_available(self):
        position_count = 0

        treat_position_list = [
            [self.treat_position1_list, 0],
            [self.treat_position2_list, 0],
            [self.treat_position3_list, 0],
            [self.treat_position4_list, 0],
            [self.treat_position5_list, 0],
            [self.treat_position6_list, 0],
        ]
        for treat_position_item in treat_position_list:
            for check_box in treat_position_item[0]:
                if check_box.isChecked():
                    check_box.setStyleSheet('color:blue; font-weight:bold')
                    # treat_position_item[1] = 1
                    treat_position_item[1] += 1  # 2023.01.19  # 改為任兩個部位，不分區域
                else:
                    check_box.setStyleSheet(None)

        for item in treat_position_list:
            position_count += item[1]

        self.label_position_count.setText(f'合計部位: {position_count}個')

        treatment_count = 0
        for check_box in self.treat_auxiliary_list:
            if check_box.isChecked():
                check_box.setStyleSheet('color:blue; font-weight:bold')
                treatment_count += 1
            else:
                check_box.setStyleSheet(None)

        for check_box in self.treat_massage_list:
            if check_box.isChecked():
                check_box.setStyleSheet('color:blue; font-weight:bold')
                treatment_count += 1
            else:
                check_box.setStyleSheet(None)

        if self.treatment in ['針灸治療', '一般針灸']:
            return

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        if position_count >= 2 and treatment_count >= 1:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    def accepted_button_clicked(self):
        self.accept_treats = True

    def _set_frequently_acupuncture_point(self):
        self.ui.tableWidget_acupuncture_point.clear()
        self.ui.tableWidget_acupuncture_point.setRowCount(0)
        
        start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d')

        sql = f'''
            SELECT prescript.MedicineName, medicine.MedicineKey FROM prescript
                LEFT JOIN cases ON prescript.CaseKey = cases.CaseKey
                LEFT JOIN medicine on prescript.MedicineKey = medicine.MedicineKey
            WHERE
                DATE(cases.CaseDate) >= "{start_date}" AND
                prescript.MedicineType = '穴道' AND
                DiseaseCode1 LIKE '{self.disease_code}%' AND
                prescript.MedicineName IS NOT NULL AND
                LENGTH(prescript.MedicineName) > 0 AND
                prescript.MedicineName NOT LIKE "%針灸%" AND
                prescript.MedicineName NOT LIKE "時間%" AND
                prescript.MedicineName NOT LIKE "頻率%" AND
                prescript.MedicineName NOT LIKE "%波" AND
                prescript.MedicineName NOT LIKE "輔助%" AND
                prescript.MedicineName NOT LIKE "治療%" AND
                prescript.MedicineName NOT LIKE "%複雜%" AND
                prescript.MedicineName NOT LIKE "建議%"
            GROUP BY prescript.MedicineName
            ORDER BY prescript.CaseKey, PrescriptKey
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        column_count = 5
        x = divmod(len(rows), column_count)
        row_count = x[0]
        if x[1] > 0:
            row_count += 1

        self.ui.tableWidget_acupuncture_point.setRowCount(row_count)
        self.ui.tableWidget_acupuncture_point.setColumnCount(column_count)

        for row_no in range(row_count):
            for col_no in range(column_count):
                rec_no = row_no * column_count + col_no
                if rec_no >= len(rows):
                    break

                medicine_name = string_utils.xstr(rows[rec_no]['MedicineName'])
                check_box = QtWidgets.QCheckBox()
                check_box.setStyleSheet('padding-left: 5px')
                check_box.setText(medicine_name)
                check_box.clicked.connect(self._set_cell_widget_check_box)

                self.ui.tableWidget_acupuncture_point.setCellWidget(row_no, col_no, check_box)

        self.ui.tableWidget_acupuncture_point.resizeRowsToContents()
        self.ui.tableWidget_acupuncture_point.setCurrentCell(0, 0)

    def _set_cell_widget_check_box(self):
        for row_no in range(self.ui.tableWidget_acupuncture_point.rowCount()):
            for col_no in range(self.ui.tableWidget_acupuncture_point.columnCount()):
                check_box = self.ui.tableWidget_acupuncture_point.cellWidget(row_no, col_no)
                if check_box is None:
                    continue

                if check_box.isChecked():
                    check_box.setStyleSheet('padding-left: 5px; color:blue; font-weight:bold')
                else:
                    check_box.setStyleSheet('padding-left: 5px')
