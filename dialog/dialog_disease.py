
# 病歷登錄之病名詞庫 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore
from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import case_utils
from libs import nhi_utils
from libs import icd10_utils
from libs import db_utils


# 病名詞庫 (from 病歷登錄)
class DialogDisease(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogDisease, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.line_edit_icd_code1 = args[3]
        self.line_edit_disease_name1 = args[4]
        self.line_edit_special_code = args[5]
        self.line_edit_icd_code2 = args[6]
        self.line_edit_disease_name2 = args[7]
        self.disease_type = args[8]

        self.ui = None
        self._set_variables()

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def _set_variables(self):
        if self.case_key is None:
            self.start_date = nhi_utils.INS_TREAT_2021_DATE
            return

        sql = f'''
            SELECT CaseDate, PatientKey, Card, Continuance FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self.start_date = nhi_utils.INS_TREAT_2021_DATE
            return

        row = rows[0]

        self.start_date = case_utils.get_course_start_date(
            self.database, row['PatientKey'], row['CaseDate'],
            row['Card'], row['Continuance'],
        )

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_DISEASE, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Save).setText('選取')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Close).setText('關閉')
        self.table_widget_groups = class_utils.get_table_widget(self.ui.tableWidget_groups, self.database)
        self.table_widget_groups_name = class_utils.get_table_widget(self.ui.tableWidget_groups_name, self.database)
        self.table_widget_groups_name.set_column_hidden([0])
        self.table_widget_disease = class_utils.get_table_widget(self.ui.tableWidget_disease, self.database)
        self.table_widget_disease2 = class_utils.get_table_widget(self.ui.tableWidget_disease2, self.database)
        self.table_widget_disease.set_column_hidden([0, 3])
        self.table_widget_disease2.set_column_hidden([0, 3])
        self.ui.label_disease2.setVisible(False)
        self.ui.tableWidget_disease2.setVisible(False)

        self._set_radio_buttons()
        self._set_table_width()
        self._set_groups()

    def _set_radio_buttons(self):
        if self.disease_type == '所有病名':
            self.ui.radioButton_all.setChecked(True)
        elif self.disease_type == '常用病名':
            self.ui.radioButton_common.setChecked(True)
        elif self.disease_type == '自訂病名':
            self.ui.radioButton_custom.setChecked(True)
        elif self.disease_type == '傷骨科':
            self.ui.radioButton_treat.setChecked(True)
        elif self.disease_type == '慢性病':
            self.ui.radioButton_chronic.setChecked(True)
        elif self.disease_type == '複雜性針灸適應症':
            self.ui.radioButton_complicated_acupuncture.setChecked(True)
        elif self.disease_type == '中度複雜性針灸':
            self.ui.radioButton_moderate_complicated_acupuncture.setChecked(True)
        elif self.disease_type == '高度複雜性針灸':
            self.ui.radioButton_highly_complicated_acupuncture.setChecked(True)
        elif self.disease_type == '複雜性傷科適應症':
            self.ui.radioButton_complicated_massage.setChecked(True)
        elif self.disease_type == '中度複雜性傷科':
            self.ui.radioButton_moderate_complicated_massage.setChecked(True)
        elif self.disease_type == '高度複雜性傷科':
            self.ui.radioButton_highly_complicated_massage.setChecked(True)
        elif self.disease_type == '中度複雜性傷科合併特殊疾病':
            self.ui.radioButton_moderate_complicated_massage_with_special_disease.setChecked(True)
        elif self.disease_type == '脫臼整復復位適應症':
            self.ui.radioButton_dislocate.setChecked(True)
        elif self.disease_type == '骨折復位適應症':
            self.ui.radioButton_fracture.setChecked(True)
        elif self.disease_type == '健保專案':
            self.ui.radioButton_ins_care.setChecked(True)

        if self.disease_type == '常用病名':
            if self.system_settings.field('病名詞庫預設類別') == '常用病名':
                self.ui.radioButton_common.setChecked(True)
            elif self.system_settings.field('病名詞庫預設類別') == '所有病名':
                self.ui.radioButton_all.setChecked(True)
            elif self.system_settings.field('病名詞庫預設類別') == '自訂病名':
                self.ui.radioButton_custom.setChecked(True)
            elif self.system_settings.field('病名詞庫預設類別') == '傷骨科':
                self.ui.radioButton_treat.setChecked(True)

        if self.start_date >= nhi_utils.INS_TREAT_2021_DATE:
            self.ui.radioButton_complicated_acupuncture.setVisible(False)
            self.ui.radioButton_complicated_massage.setVisible(False)
        else:
            self.ui.radioButton_moderate_complicated_acupuncture.setVisible(False)
            self.ui.radioButton_highly_complicated_acupuncture.setVisible(False)
            self.ui.radioButton_moderate_complicated_massage.setVisible(False)
            self.ui.radioButton_highly_complicated_massage.setVisible(False)
            self.ui.radioButton_moderate_complicated_massage_with_special_disease.setVisible(False)
            self.ui.radioButton_dislocate.setVisible(False)
            self.ui.radioButton_fracture.setVisible(False)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)
        self.ui.tableWidget_groups.itemSelectionChanged.connect(self.groups_changed)
        self.ui.tableWidget_groups_name.itemSelectionChanged.connect(self.groups_name_changed)
        self.ui.tableWidget_disease.doubleClicked.connect(self.accepted_button_clicked)
        self.ui.radioButton_all.clicked.connect(self._set_groups)
        self.ui.radioButton_common.clicked.connect(self._set_groups)
        self.ui.radioButton_custom.clicked.connect(self._set_groups)
        self.ui.radioButton_chronic.clicked.connect(self._set_groups)
        self.ui.radioButton_treat.clicked.connect(self._set_groups)
        self.ui.radioButton_complicated_acupuncture.clicked.connect(self._set_groups)
        self.ui.radioButton_moderate_complicated_acupuncture.clicked.connect(self._set_groups)
        self.ui.radioButton_highly_complicated_acupuncture.clicked.connect(self._set_groups)
        self.ui.radioButton_complicated_massage.clicked.connect(self._set_groups)
        self.ui.radioButton_moderate_complicated_massage.clicked.connect(self._set_groups)
        self.ui.radioButton_highly_complicated_massage.clicked.connect(self._set_groups)
        self.ui.radioButton_moderate_complicated_massage_with_special_disease.clicked.connect(self._set_groups)
        self.ui.radioButton_ins_care.clicked.connect(self._set_groups)
        self.ui.radioButton_dislocate.clicked.connect(self._set_groups)
        self.ui.radioButton_fracture.clicked.connect(self._set_groups)

        self.ui.radioButton_no_side.clicked.connect(self._set_injury_list)
        self.ui.radioButton_left_side.clicked.connect(self._set_injury_list)
        self.ui.radioButton_right_side.clicked.connect(self._set_injury_list)

        self.ui.radioButton_no_period.clicked.connect(self._set_injury_list)
        self.ui.radioButton_period1.clicked.connect(self._set_injury_list)
        self.ui.radioButton_period2.clicked.connect(self._set_injury_list)
        self.ui.radioButton_period3.clicked.connect(self._set_injury_list)

        self.ui.tableWidget_injury.itemSelectionChanged.connect(self._injury_changed)
        self.ui.lineEdit_keyword.textChanged.connect(self._query_disease)

    # 存檔
    def accepted_button_clicked(self):
        self.line_edit_icd_code1.setText(self.table_widget_disease.field_value(1))
        self.line_edit_disease_name1.setText(self.table_widget_disease.field_value(3))
        self.line_edit_icd_code1.setModified(True)

        icd10_key = self.table_widget_disease.field_value(0)
        db_utils.increment_hit_rate(self.database, 'icd10', 'ICD10Key', icd10_key)

        if self.table_widget_disease2.field_value(1) is not None:
            self.line_edit_icd_code2.setText(self.table_widget_disease2.field_value(1))
            self.line_edit_disease_name2.setText(self.table_widget_disease2.field_value(3))

        if self.line_edit_special_code is not None and \
           self.line_edit_icd_code1 == self.parent.ui.lineEdit_disease_code1:  # 主診斷才設定慢性病代碼
            self.line_edit_special_code.setText(self.table_widget_disease.field_value(2))

        self.close()
        self.parent.check_complicated_treat_disease(self.table_widget_disease.field_value(1))

    # 關閉
    def rejected_button_clicked(self):
        self.close()

    # 設定欄位寬度
    def _set_table_width(self):
        groups_name_width = [100, 450]
        disease_width = [100, 100, 70, 100, 500, 100]
        self.table_widget_disease.set_table_heading_width(disease_width)
        self.table_widget_disease2.set_table_heading_width(disease_width)
        self.table_widget_groups_name.set_table_heading_width(groups_name_width)

    def _set_groups(self):
        self.ui.tableWidget_groups.setVisible(True)

        self.ui.tableWidget_injury.setVisible(False)
        self.ui.groupBox_side.setVisible(False)
        self.ui.groupBox_period.setVisible(False)

        if self.ui.radioButton_chronic.isChecked():
            sql = '''
                SELECT DictGroupsTopLevel as DictGroupsName FROM dict_groups
                    LEFT JOIN icd10 ON icd10.groups = dict_groups.DictGroupsName
                WHERE
                    DictGroupsType = "病名" AND
                    icd10.SpecialCode IS NOT NULL
                GROUP BY DictGroupsTopLevel
                ORDER BY DictGroupsTopLevel
            '''
        elif self.ui.radioButton_custom.isChecked():
            self.ui.tableWidget_groups.setVisible(False)
            self._set_custom_disease()
            return
        elif self.ui.radioButton_treat.isChecked():
            self.ui.tableWidget_injury.setVisible(True)
            self.ui.groupBox_side.setVisible(True)
            self.ui.groupBox_period.setVisible(True)
            sql = '''
                SELECT * FROM dict_groups
                WHERE
                    DictGroupsType = "傷骨科病名類別"
                ORDER BY DictGroupsName
            '''
        elif self.ui.radioButton_complicated_acupuncture.isChecked():
            self.ui.tableWidget_groups.setVisible(False)
            self._set_custom_groups_name(icd10_utils.COMPLICATED_ACUPUNCTURE_DISEASE_DICT)
            self.groups_name_changed()
            return
        elif self.ui.radioButton_moderate_complicated_acupuncture.isChecked():
            self.ui.tableWidget_groups.setVisible(False)
            self._set_custom_groups_name(icd10_utils.MODERATE_COMPLICATED_ACUPUNCTURE_DISEASE_DICT)
            self.groups_name_changed()
            return
        elif self.ui.radioButton_highly_complicated_acupuncture.isChecked():
            self.ui.tableWidget_groups.setVisible(False)
            self._set_custom_groups_name(icd10_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_DISEASE_DICT)
            self.groups_name_changed()
            return
        elif self.ui.radioButton_complicated_massage.isChecked():
            self.ui.tableWidget_groups.setVisible(False)
            self._set_custom_groups_name(icd10_utils.COMPLICATED_MASSAGE_DISEASE_DICT)
            self.groups_name_changed()
            return
        elif self.ui.radioButton_moderate_complicated_massage.isChecked():
            self.ui.tableWidget_groups.setVisible(False)
            self._set_custom_groups_name(icd10_utils.MODERATE_COMPLICATED_MASSAGE_DISEASE_DICT)
            self.groups_name_changed()
            return
        elif self.ui.radioButton_highly_complicated_massage.isChecked():
            self.ui.tableWidget_groups.setVisible(False)
            self._set_custom_groups_name(icd10_utils.HIGHLY_COMPLICATED_MASSAGE_DISEASE_DICT)
            self.groups_name_changed()
            return
        elif self.ui.radioButton_moderate_complicated_massage_with_special_disease.isChecked():
            self.ui.tableWidget_groups.setVisible(False)
            self._set_custom_groups_name(icd10_utils.MODERATE_COMPLICATED_MASSAGE_WITH_SPECIAL_DISEASE_DICT)
            self.groups_name_changed()
            return
        elif self.ui.radioButton_dislocate.isChecked():
            self.ui.tableWidget_groups.setVisible(False)
            self._set_custom_groups_name(icd10_utils.DISLOCATE_DICT)
            self.groups_name_changed()
            return
        elif self.ui.radioButton_fracture.isChecked():
            self.ui.tableWidget_groups.setVisible(False)
            self._set_custom_groups_name(icd10_utils.FRACTURE_DICT)
            self.groups_name_changed()
            return
        elif self.ui.radioButton_ins_care.isChecked():
            self.ui.tableWidget_groups.setVisible(False)
            self._set_custom_groups_name(icd10_utils.INS_SPECIAL_CARE_DICT)
            self.groups_name_changed()
            return
        elif self.ui.radioButton_common.isChecked():
            sql = '''
                SELECT * FROM dict_groups
                WHERE
                    DictGroupsType = "常用病名類別"
                ORDER BY DictGroupsName
            '''
        else:
            sql = '''
                SELECT * FROM dict_groups
                WHERE
                    DictGroupsType = "病名類別"
                ORDER BY DictGroupsName
            '''

        self.table_widget_groups.set_db_data_without_heading(sql, 'DictGroupsName')

        groups = self.ui.tableWidget_groups.selectedItems()
        if len(groups) <= 0:
            return

        groups = groups[0].text()
        self._read_groups_name(groups)
        groups_name = self.table_widget_groups_name.field_value(1)

        # if self.ui.radioButton_treat.isChecked():
        #     return

        self._read_disease(groups_name)
        self.ui.tableWidget_groups.setFocus(True)

        if self.ui.radioButton_common.isChecked() or self.ui.radioButton_treat.isChecked():
            self.groups_name_changed()

        if self.ui.radioButton_treat.isChecked():
            self._injury_changed()

    def groups_changed(self):
        if not self.ui.tableWidget_groups.selectedItems():
            return

        self.ui.lineEdit_keyword.setText(None)
        groups = self.ui.tableWidget_groups.selectedItems()[0].text()
        self._read_groups_name(groups)
        groups_name = self.table_widget_groups_name.field_value(1)

        if self.ui.radioButton_treat.isChecked():
            self._set_injury_list()
        else:
            self._read_disease(groups_name)

        if self.ui.radioButton_common.isChecked():
            self.groups_name_changed()

        self.ui.tableWidget_groups.setFocus(True)

    def _read_groups_name(self, groups):
        if self.ui.radioButton_chronic.isChecked():
            sql = f'''
                SELECT *, icd10.SpecialCode FROM dict_groups
                    LEFT JOIN icd10 ON icd10.groups = dict_groups.DictGroupsName
                WHERE
                    DictGroupsType = "病名" and DictGroupsTopLevel = "{groups}" AND
                    icd10.SpecialCode IS NOT NULL
                GROUP BY DictGroupsName
                ORDER BY DictGroupsName
            '''
        elif self.ui.radioButton_treat.isChecked():
            sql = f'''
                SELECT * FROM dict_groups
                WHERE
                    DictGroupsType = "傷骨科病名" and DictGroupsTopLevel = "{groups}"
                ORDER BY DictGroupsName
            '''
        elif self.ui.radioButton_common.isChecked():
            sql = f'''
                SELECT * FROM dict_groups
                WHERE
                    DictGroupsType = "常用病名" and DictGroupsTopLevel = "{groups}"
                ORDER BY DictGroupsName
            '''
        else:
            sql = f'''
                SELECT * FROM dict_groups
                WHERE
                    DictGroupsType = "病名" and DictGroupsTopLevel = "{groups}"
                ORDER BY DictGroupsName
            '''

        self.table_widget_groups_name.set_db_data(sql, self._set_groups_name_data)

    def _set_groups_name_data(self, row_no, row):
        groups_name_row = [
            string_utils.xstr(row['DictGroupsKey']),
            string_utils.xstr(row['DictGroupsName']),
        ]

        for column in range(len(groups_name_row)):
            self.ui.tableWidget_groups_name.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(groups_name_row[column])
            )

    def _read_disease(self, groups_name):
        sql = f'''
            SELECT ICD10Key, ICDCode, SpecialCode, ChineseName FROM icd10
            WHERE
                Groups = "{groups_name}"
        '''

        if self.ui.radioButton_chronic.isChecked():
            sql += ' AND SpecialCode IS NOT NULL '

        if self.system_settings.field('病名詞庫以病名碼排序') == 'Y':
            sql += ' ORDER BY ICDCode'
        elif self.system_settings.field('詞庫排序') == '點擊率':
            sql += ' ORDER BY HitRate DESC'
        elif self.system_settings.field('詞庫排序') == '最後點擊時戳':
            sql += ' ORDER BY TimeStamp DESC'
        else:
            sql += ' ORDER BY ICDCode'

        self.table_widget_disease.set_db_data(sql, self._set_disease_data)

    def _get_treatment(self, icd_code):
        treatment_list = []

        if icd_code in self.parent.parent.moderate_complicated_acupuncture_list:
            treatment_list.append('中針')
        if icd_code in self.parent.parent.highly_complicated_acupuncture_list:
            treatment_list.append('高針')
        if icd_code in self.parent.parent.moderate_complicated_massage_list:
            treatment_list.append('中傷')
        if icd_code in self.parent.parent.highly_complicated_massage_list:
            treatment_list.append('高傷')
        if icd_code in self.parent.parent.special_disease_list:
            treatment_list.append('中針')

        treatment = ','.join(treatment_list)

        return treatment

    def _set_disease_data(self, row_no, row):
        icd_code = string_utils.xstr(row['ICDCode'])
        treatment = self._get_treatment(icd_code)

        disease_row = [
            string_utils.xstr(row['ICD10Key']),
            icd_code,
            string_utils.xstr(row['SpecialCode']),
            string_utils.xstr(row['ChineseName']),
            string_utils.xstr(row['ChineseName']),
            treatment,
        ]
        for col_no in range(len(disease_row)):
            self.ui.tableWidget_disease.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(disease_row[col_no]))

            if string_utils.xstr(row['SpecialCode']) != '':
                self.ui.tableWidget_disease.item(
                    row_no, col_no).setForeground(
                    QtGui.QColor('red')
                )

        # disease_name = case_utils.get_disease_name_html(row['ChineseName'])
        # self.ui.tableWidget_disease.setCellWidget(
        #     row_no, 4, disease_name
        # )
        self.ui.tableWidget_disease.setCurrentCell(0, 1)

    def _get_side(self):
        side = '不分'

        if self.ui.radioButton_left_side.isChecked():
            side = '左側'
        elif self.ui.radioButton_right_side.isChecked():
            side = '右側'

        return side

    def _get_period(self):
        period = '不分'

        if self.ui.radioButton_period1.isChecked():
            period = '初期照護'
        elif self.ui.radioButton_period2.isChecked():
            period = '後續照護'
        elif self.ui.radioButton_period3.isChecked():
            period = '後遺症'

        return period

    def _set_injury_list(self):
        injury_list = []

        side = self._get_side()
        period = self._get_period()
        groups_name = self.table_widget_groups_name.field_value(1)[2:]

        sql = f'''
            SELECT ICD10Key FROM icd10
            WHERE
                LENGTH(ICDCode) >= 7 AND
                ChineseName LIKE "%{groups_name}%"
        '''

        for injury in case_utils.INJURY_LIST:
            script = sql + f' AND ChineseName LIKE "%{injury}%"'
            if side != '不分':
                script += f' AND ChineseName LIKE "%{side}%"'
            if period != '不分':
                script += f' AND ChineseName LIKE "%{period}%"'

            script += ' LIMIT 1'
            rows = self.database.select_record(script)
            if len(rows) > 0:
                injury_list.append(injury)

        row_count = len(injury_list)
        self.ui.tableWidget_injury.setRowCount(0)

        column_count = self.ui.tableWidget_injury.columnCount()
        total_row = int(row_count / column_count)
        if row_count % column_count > 0:
            total_row += 1

        for row_no in range(0, total_row):
            self.ui.tableWidget_injury.setRowCount(
                self.ui.tableWidget_injury.rowCount() + 1
            )
            for col_no in range(0, column_count):
                index = (row_no * column_count) + col_no
                if index >= row_count:
                    break

                self.ui.tableWidget_injury.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem(injury_list[index])
                )

        self.ui.tableWidget_injury.setCurrentCell(0, 0)

    def _injury_changed(self):
        self._read_injury_disease()

    def _read_injury_disease(self):
        side = self._get_side()
        period = self._get_period()
        groups_name = self.table_widget_groups_name.field_value(1)[2:]

        injury = self.ui.tableWidget_injury.selectedItems()
        if not injury:
            return

        injury = injury[0].text()

        sql = f'''
            SELECT ICD10Key, ICDCode, SpecialCode, ChineseName FROM icd10
            WHERE
                LENGTH(ICDCode) >= 7 AND
                ChineseName LIKE "%{groups_name}%" AND
                ChineseName LIKE "%{injury}%"
        '''

        if side != '不分':
            sql += f' AND ChineseName LIKE "%{side}%"'
        if period != '不分':
            sql += f' AND ChineseName LIKE "%{period}%"'

        sql += ' ORDER BY ICDCode'
        self.table_widget_disease.set_db_data(sql, self._set_disease_data)

    def _set_disease_data2(self, row_no, row):
        icd_code = string_utils.xstr(row['ICDCode'])
        treatment = self._get_treatment(icd_code)
        disease_row = [
            string_utils.xstr(row['ICD10Key']),
            icd_code,
            string_utils.xstr(row['SpecialCode']),
            string_utils.xstr(row['ChineseName']),
            treatment,
        ]
        for column in range(len(disease_row)):
            self.ui.tableWidget_disease2.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(disease_row[column])
            )
            if string_utils.xstr(row['SpecialCode']) != '':
                self.ui.tableWidget_disease2.item(
                    row_no, column).setForeground(
                    QtGui.QColor('red')
                )

        disease_name = case_utils.get_disease_name_html(row['ChineseName'])
        self.ui.tableWidget_disease2.setCellWidget(
            row_no, 4, disease_name
        )

    def _set_custom_disease(self):
        self.ui.tableWidget_groups_name.setCurrentCell(0, 1)

        sql = '''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = "自訂病名"
            ORDER BY DictGroupsTopLevel
        '''
        custom_rows = self.database.select_record(sql)

        rows = []
        for row in custom_rows:
            rows.append(
                {'DictGroupsKey': row['DictGroupsKey'],
                 'DictGroupsName': string_utils.xstr(row['DictGroupsTopLevel'])}
            )

        row_count = len(rows)
        self.ui.tableWidget_groups_name.setRowCount(row_count)
        for row_no in range(row_count):
            self.ui.tableWidget_groups_name.setItem(
                row_no, 1,
                QtWidgets.QTableWidgetItem(rows[row_no]['DictGroupsName'])
            )
        self.ui.tableWidget_groups_name.resizeRowsToContents()
        self._set_custom_icd()

    def _set_custom_groups_name(self, custom_dict):
        self.ui.tableWidget_groups_name.setCurrentCell(0, 1)

        rows = []
        for row in list(custom_dict.keys()):
            rows.append({'DictGroupsKey': None, 'DictGroupsName': string_utils.xstr(row)})

        row_count = len(rows)
        self.ui.tableWidget_groups_name.setRowCount(row_count)
        for row_no in range(row_count):
            self.ui.tableWidget_groups_name.setItem(
                row_no, 1,
                QtWidgets.QTableWidgetItem(rows[row_no]['DictGroupsName'])
            )
        self.ui.tableWidget_groups_name.resizeRowsToContents()

    def groups_name_changed(self):
        self.ui.lineEdit_keyword.setText(None)

        self.ui.label_disease2.setVisible(False)
        self.ui.tableWidget_disease2.setVisible(False)

        groups_name = self.table_widget_groups_name.field_value(1)

        if self.ui.radioButton_common.isChecked():
            self._set_custom_disease_list(icd10_utils.COMMON_DISEASE_DICT, groups_name)
        elif self.ui.radioButton_treat.isChecked():
            self._set_injury_list()
        elif self.ui.radioButton_custom.isChecked():
            self._set_custom_icd()
        elif self.ui.radioButton_complicated_acupuncture.isChecked():
            self._set_custom_disease_list(icd10_utils.COMPLICATED_ACUPUNCTURE_DISEASE_DICT, groups_name)
        elif self.ui.radioButton_moderate_complicated_acupuncture.isChecked():
            self._set_custom_disease_list(icd10_utils.MODERATE_COMPLICATED_ACUPUNCTURE_DISEASE_DICT, groups_name)
        elif self.ui.radioButton_highly_complicated_acupuncture.isChecked():
            self._set_custom_disease_list(icd10_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_DISEASE_DICT, groups_name)
        elif self.ui.radioButton_complicated_massage.isChecked():
            self._set_custom_disease_list(icd10_utils.COMPLICATED_MASSAGE_DISEASE_DICT, groups_name)
        elif self.ui.radioButton_moderate_complicated_massage.isChecked():
            self._set_custom_disease_list(icd10_utils.MODERATE_COMPLICATED_MASSAGE_DISEASE_DICT, groups_name)
        elif self.ui.radioButton_highly_complicated_massage.isChecked():
            self._set_custom_disease_list(icd10_utils.HIGHLY_COMPLICATED_MASSAGE_DISEASE_DICT, groups_name)
        elif self.ui.radioButton_moderate_complicated_massage_with_special_disease.isChecked():
            self._set_custom_disease_list(
                icd10_utils.MODERATE_COMPLICATED_MASSAGE_WITH_SPECIAL_DISEASE_DICT, groups_name
            )
        elif self.ui.radioButton_dislocate.isChecked():
            self._set_custom_disease_list(
                icd10_utils.DISLOCATE_DICT, groups_name
            )
        elif self.ui.radioButton_fracture.isChecked():
            self._set_custom_disease_list(
                icd10_utils.FRACTURE_DICT, groups_name
            )
        elif self.ui.radioButton_ins_care.isChecked():
            self._set_custom_disease_list(icd10_utils.INS_SPECIAL_CARE_DICT, groups_name)
        else:
            self._read_disease(groups_name)

        self.ui.tableWidget_groups_name.setFocus(True)

    def _set_custom_icd(self):
        self.ui.label_disease2.setVisible(False)
        self.ui.tableWidget_disease2.setVisible(False)

        groups_name = self.table_widget_groups_name.field_value(1)
        sql = f'''
            SELECT CustomDiseaseKey, icd10.* FROM custom_disease
                LEFT JOIN icd10 ON icd10.ICDCode = custom_disease.ICDCode
            WHERE
                GroupsName = "{groups_name}"
            ORDER BY icd10.ICDCode
        '''
        rows = self.database.select_record(sql)
        self.ui.tableWidget_disease.setRowCount(len(rows))

        for row_no, row in enumerate(rows):
            row = {
                'ICD10Key': row['ICD10Key'],
                'ICDCode': row['ICDCode'],
                'SpecialCode': row['SpecialCode'],
                'ChineseName': row['ChineseName'],
            }
            self._set_disease_data(row_no, row)

    def _set_custom_disease_list(self, custom_dict, groups_name):
        self.ui.label_disease2.setVisible(False)
        self.ui.tableWidget_disease2.setVisible(False)

        try:
            disease_rows1 = nhi_utils.get_custom_groups_name_rows(
                self.database, custom_dict, groups_name, disease=1
            )
        except KeyError:
            return

        disease_rows2 = nhi_utils.get_custom_groups_name_rows(
            self.database, custom_dict, groups_name, disease=2
        )

        disease_rows_count1 = len(disease_rows1)
        self.ui.tableWidget_disease.setRowCount(disease_rows_count1)
        for row_no in range(disease_rows_count1):
            icd_code = disease_rows1[row_no]
            sql = f'''
                SELECT * FROM icd10
                WHERE
                    ICDCode = "{icd_code}"
            '''
            icd_rows = self.database.select_record(sql)[0]

            row = {
                'ICD10Key': icd_rows['ICD10Key'],
                'ICDCode': icd_code,
                'SpecialCode': icd_rows['SpecialCode'],
                'ChineseName': icd_rows['ChineseName'],
            }
            self._set_disease_data(row_no, row)

        if len(disease_rows2) <= 0:
            return

        self.ui.label_disease2.setVisible(True)
        self.ui.tableWidget_disease2.setVisible(True)

        disease_rows_count2 = len(disease_rows2)
        self.ui.tableWidget_disease2.setRowCount(disease_rows_count2)
        for row_no in range(disease_rows_count2):
            icd_code = disease_rows2[row_no]
            sql = f'''
                SELECT * FROM icd10
                WHERE
                    ICDCode = "{icd_code}"
            '''
            icd_rows = self.database.select_record(sql)[0]

            row = {
                'ICD10Key': icd_rows['ICD10Key'],
                'ICDCode': icd_code,
                'SpecialCode': icd_rows['SpecialCode'],
                'ChineseName': icd_rows['ChineseName'],
            }
            self._set_disease_data2(row_no, row)

        self.ui.tableWidget_disease2.setFocus(True)
        self.ui.tableWidget_disease2.setCurrentCell(0, 1)

    def _query_disease(self):
        keyword = self.ui.lineEdit_keyword.text()
        illegal_characters = ['\\', '"', '\'']
        if any(s in keyword for s in illegal_characters):
            keyword = string_utils.replace_ascii_char(illegal_characters, keyword)
            self.ui.lineEdit_keyword.setText(keyword)
            self.ui.lineEdit_keyword.setCursorPosition(len(keyword))

        if keyword == '':
            self.ui.tableWidget_disease.setRowCount(0)
            return

        if self.system_settings.field('病名詞庫以病名碼排序') == 'Y':
            order_type = 'ORDER BY ICDCode'
        elif self.system_settings.field('詞庫排序') == '點擊率':
            order_type = 'ORDER BY HitRate DESC'
        elif self.system_settings.field('詞庫排序') == '最後點擊時戳':
            order_type = 'ORDER BY TimeStamp DESC'
        else:
            order_type = 'ORDER BY ICDCode'

        sql = f'''
            SELECT * FROM icd10
            WHERE
                ICDCode LIKE "{keyword}%" OR
                ChineseName LIKE "%{keyword}%"
            {order_type}
            LIMIT 100
        '''
        self.table_widget_disease.set_db_data(sql, self._set_disease_data)
        for row_no in range(self.ui.tableWidget_disease.rowCount()-1, -1, -1):
            icd_code = self.ui.tableWidget_disease.item(row_no, 1).text()
            sql = f'''
                SELECT ICDCode FROM icd10
                WHERE
                    ICDCode LIKE "{icd_code}%"
                LIMIT 2
            '''
            temp_rows = self.database.select_record(sql)
            if len(temp_rows) >= 2:
                self.ui.tableWidget_disease.removeRow(row_no)

        self.ui.lineEdit_keyword.setFocus(True)
        self.ui.lineEdit_keyword.setCursorPosition(len(keyword))
