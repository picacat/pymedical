# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets

from libs import class_utils, string_utils, system_utils, ui_utils


# 病名詞庫-鍵盤輸入
class DialogDiseasePicker(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.icd_code = args[2]

        self.ui = None

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_DISEASE_PICKER, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        if self.system_settings.field("詞庫視窗顯示方式") == "彈出式視窗":
            self.ui.setWindowFlags(QtCore.Qt.Popup)

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("存檔")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")
        self.table_widget_disease = class_utils.get_table_widget(
            self.ui.tableWidget_disease, self.database
        )
        self._set_table_width()
        self.table_widget_disease.set_column_hidden([0])
        self.ui.tableWidget_disease.setFocus()

    def _set_table_width(self):
        width = [100, 100, 80, 400, 340, 120]
        self.table_widget_disease.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_disease.doubleClicked.connect(self._table_double_clicked)
        self.ui.radioButton_all.clicked.connect(self._read_data)
        self.ui.radioButton_chronic.clicked.connect(self._read_data)

    def _table_double_clicked(self):
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).animateClick()

    def accepted_button_clicked(self):
        self.icd10_key = self.table_widget_disease.field_value(0)
        self.icd_code = self.table_widget_disease.field_value(1)
        self.special_code = self.table_widget_disease.field_value(2)
        self.chinese_name = self.table_widget_disease.field_value(3)
        self.close()

    def _get_sql_script(self):
        self.icd_code = self.icd_code.strip()
        if self.icd_code == "":
            return None

        chronic_script = ""
        if self.ui.radioButton_chronic.isChecked():
            chronic_script = (
                " AND (SpecialCode IS NOT NULL AND LENGTH(SpecialCode) > 0)"
            )

        if self.icd_code.isdigit():
            order_type = "ORDER BY icd10.ICDCode"

            if self.system_settings.field("病名詞庫以病名碼排序") == "Y":
                order_type = "ORDER BY icd10.ICDCode"
            elif self.system_settings.field("詞庫排序") == "點擊率":
                order_type = "ORDER BY icd10.HitRate DESC, icd10.ICDCode"
            elif self.system_settings.field("詞庫排序") == "最後點擊時戳":
                order_type = "ORDER BY icd10.TimeStamp DESC"

            if self.system_settings.field("病名詞庫以病名碼排序") == "Y":
                order_type = "ORDER BY icd10.ICDCode"

            sql = f'''
                SELECT
                    icd10.ICD10Key,
                    icd10.ICDCode,
                    icd10.ChineseName,
                    icd10.EnglishName,
                    icd10.SpecialCode
                FROM icdmap
                    LEFT JOIN icd10 ON icdmap.ICD10Code = icd10.ICDCode
                WHERE
                    ICD9Code LIKE "{self.icd_code}%"
                    {chronic_script}
                {order_type}
            '''
        else:
            order_type = "ORDER BY ICDCode"

            if self.system_settings.field("病名詞庫以病名碼排序") == "Y":
                order_type = "ORDER BY icd10.ICDCode"
            elif self.system_settings.field("詞庫排序") == "點擊率":
                order_type = "ORDER BY HitRate DESC, ICDCode"
            elif self.system_settings.field("詞庫排序") == "最後點擊時戳":
                order_type = "ORDER BY TimeStamp DESC"

            keyword_list = self.icd_code.split()
            chinese_name_script = []
            for keyword in keyword_list:
                chinese_name_script.append(f'ChineseName LIKE "%{keyword}%"')

            if len(chinese_name_script) > 0:
                chinese_name_script = " AND ".join(chinese_name_script)
                chinese_name_script = f"OR ({chinese_name_script})"

            english_name_script = ""
            if len(self.icd_code) >= 5:
                english_name_script = []
                for keyword in keyword_list:
                    english_name_script.append(f'UPPER(EnglishName) LIKE "%{keyword}%"')

                if len(english_name_script) >= 0:
                    english_name_script = " AND ".join(english_name_script)
                    english_name_script = f"OR ({english_name_script})"

            sql = f'''
                SELECT * FROM icd10
                WHERE
                    (ICDCode LIKE "{self.icd_code}%" OR
                    InputCode LIKE "{self.icd_code}%"
                    {chinese_name_script}
                    {english_name_script})
                    {chronic_script}
            '''
            # sql += order_type + ' LIMIT 300'
            sql += order_type + " LIMIT 300"

        return sql

    def _read_data(self):
        sql = self._get_sql_script()
        if sql is None:
            self.ui.tableWidget_disease.setRowCount(0)
            return

        self.table_widget_disease.set_db_data(sql, self._set_table_data)
        for row_no in range(self.ui.tableWidget_disease.rowCount() - 1, -1, -1):
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

    def _get_treatment(self, icd_code):
        treatment_list = []

        if icd_code in self.parent.parent.moderate_complicated_acupuncture_list:
            treatment_list.append("中針")
        if icd_code in self.parent.parent.highly_complicated_acupuncture_list:
            treatment_list.append("高針")
        if icd_code in self.parent.parent.moderate_complicated_massage_list:
            treatment_list.append("中傷")
        if icd_code in self.parent.parent.highly_complicated_massage_list:
            treatment_list.append("高傷")
        if icd_code in self.parent.parent.special_disease_list:
            treatment_list.append("中針")

        treatment = ",".join(treatment_list)

        return treatment

    def _set_table_data(self, row_no, row):
        icd_code = string_utils.xstr(row["ICDCode"])
        treatment = self._get_treatment(icd_code)
        icd_code_row = [
            string_utils.xstr(row["ICD10Key"]),
            icd_code,
            string_utils.xstr(row["SpecialCode"]),
            string_utils.xstr(row["ChineseName"]),
            string_utils.xstr(row["EnglishName"]),
            treatment,
        ]

        for column in range(len(icd_code_row)):
            self.ui.tableWidget_disease.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(icd_code_row[column])
            )
            if icd_code_row[2] != "":
                self.ui.tableWidget_disease.item(row_no, column).setForeground(
                    QtGui.QColor("red")
                )
