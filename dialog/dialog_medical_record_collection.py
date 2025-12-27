
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import class_utils

from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import case_utils


# 主視窗
class DialogMedicalRecordCollection(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMedicalRecordCollection, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_date = args[2]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_collection()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MEDICAL_RECORD_COLLECTION, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('匯入病歷')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_collection_type1 = class_utils.get_table_widget(
            self.ui.tableWidget_collection_type1, self.database
        )
        self.table_widget_collection_type2 = class_utils.get_table_widget(
            self.ui.tableWidget_collection_type2, self.database
        )
        self.table_widget_collection_name = class_utils.get_table_widget(
            self.ui.tableWidget_collection_name, self.database
        )

    # 設定欄位寬度
    def _set_table_width(self):
        pass

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_collection_type1.itemSelectionChanged.connect(self._collection_type1_changed)
        self.ui.tableWidget_collection_type2.itemSelectionChanged.connect(self._collection_type2_changed)
        self.ui.tableWidget_collection_name.itemSelectionChanged.connect(self._collection_name_changed)

    def accepted_button_clicked(self):
        case_utils.copy_collection(
            self.database, self.parent, self.case_date, self.row,
            self.ui.checkBox_diagnostic.isChecked(),
            self.ui.checkBox_disease.isChecked(),
            self.ui.checkBox_prescript.isChecked(),
        )

    def _read_collection(self):
        sql = '''
            SELECT CollectionType1 FROM collection
            WHERE
                CollectionType1 IS NOT NULL
            GROUP BY CollectionType1
            ORDER BY CollectionType1
        '''
        try:
            self.table_widget_collection_type1.set_db_data_without_heading(sql, 'CollectionType1')
        except Exception:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

    def _collection_type1_changed(self):
        if not self.ui.tableWidget_collection_type1.selectedItems():
            return

        collection_type1 = self.ui.tableWidget_collection_type1.selectedItems()[0].text()
        sql = f'''
            SELECT CollectionType2 FROM collection
            WHERE
                CollectionType1 = "{collection_type1}" AND
                CollectionType2 IS NOT NULL
            GROUP BY CollectionType2
            ORDER BY CollectionType2
        '''
        self.table_widget_collection_type2.set_db_data_without_heading(sql, 'CollectionType2')

    def _collection_type2_changed(self):
        if not self.ui.tableWidget_collection_type2.selectedItems():
            return

        collection_type1 = self.ui.tableWidget_collection_type1.selectedItems()[0].text()
        collection_type2 = self.ui.tableWidget_collection_type2.selectedItems()[0].text()
        sql = f'''
            SELECT CollectionName FROM collection
            WHERE
                CollectionType1 = "{collection_type1}" AND
                CollectionType2 = "{collection_type2}" AND
                CollectionName IS NOT NULL
            ORDER BY CollectionName
        '''
        self.table_widget_collection_name.set_db_data_without_heading(sql, 'CollectionName')

    def _collection_name_changed(self):
        if not self.ui.tableWidget_collection_name.selectedItems():
            return

        collection_type1 = self.ui.tableWidget_collection_type1.selectedItems()[0].text()
        collection_type2 = self.ui.tableWidget_collection_type2.selectedItems()[0].text()
        collection_name = self.ui.tableWidget_collection_name.selectedItems()[0].text()
        self._show_collection_content(collection_type1, collection_type2, collection_name)

    def _show_collection_content(self, collection_type1, collection_type2, collection_name):
        self.ui.textEdit_collection.clear()

        sql = f'''
            SELECT * FROM collection
            WHERE
                CollectionType1 = "{collection_type1}" AND
                CollectionType2 = "{collection_type2}" AND
                CollectionName = "{collection_name}"
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        self.row = rows[0]
        self._set_collection_html(self.row)

    def _set_collection_html(self, row):
        medical_record = ''
        symptom = string_utils.get_str(row['Symptom'], 'utf8')
        tongue = string_utils.get_str(row['Tongue'], 'utf8')
        pulse = string_utils.get_str(row['Pulse'], 'utf8')
        distincts = string_utils.get_str(row['Distincts'], 'utf8')
        cure = string_utils.get_str(row['Cure'], 'utf8')

        if symptom != '':
            medical_record += f'<b>主訴</b>: {symptom}<hr>'
        if tongue != '':
            medical_record += f'<b>舌診</b>: {tongue}<hr>'
        if pulse != '':
            medical_record += f'<b>脈象</b>: {pulse}<hr>'
        if distincts != '':
            medical_record += f'<b>辨證</b>: {distincts}<hr>'
        if cure != '':
            medical_record += f'<b>治則</b>: {cure}<hr>'

        disease_list = []
        for i in range(3):
            icd9_code = string_utils.xstr(row[f'ICDCode{i+1}'])
            if icd9_code == '':
                continue

            icd10_code, icd10_name = case_utils.convert_icd9_to_icd10(self.database, icd9_code)
            if icd10_name is not None:
                disease_list.append([icd10_code, icd10_name])

        icd_label = ['主診斷', '次診斷1', '次診斷2']
        for item_no, item in enumerate(disease_list):
            icd_label = icd_label[item_no]
            icd_code = item[0]
            icd_name = item[1]
            medical_record += f'<b>{icd_label}</b>: {icd_code} {icd_name}<br>'

        medical_record = f'''
            <div style="width: 95%;">
                {medical_record}
            </div>
        '''

        try:
            prescript_record = self._get_prescript_record(row['CollectionKey'])
        except Exception:
            prescript_record = '無處方內容'

        html = f'''
            <html>
                <head>
                    <meta charset="UTF-8">
                </head>
                <body>
                    {medical_record}
                    {prescript_record}
                </body>
            </html>
        '''
        self.ui.textEdit_collection.setHtml(html)

    def _get_prescript_record(self, collection_key):
        sql = f'''
            SELECT * FROM collitems
            WHERE
                CollectionKey = {collection_key}
            ORDER BY CollectionSetKey
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return ''

        prescript_data = ''
        sequence = 0
        for row in rows:
            if string_utils.xstr(row['MedicineName']) == '':
                continue

            sequence += 1
            medicine_name = string_utils.xstr(row['MedicineName'])
            dosage = string_utils.xstr(row['Dosage'])
            unit = string_utils.xstr(row['Unit'])
            prescript_data += f'''
                <tr>
                    <td align="center" style="padding-right: 8px;">{sequence}</td>
                    <td style="padding-left: 8px">{medicine_name}</td>
                    <td align="right" style="padding-right: 8px">{dosage} {unit}</td>
                    <td style="padding-left: 8px"></td>
                </tr>
            '''

        prescript_html = f'''
            <table align=center cellpadding="2" cellspacing="0" width="98%"
             style="border-width: 1px; border-style: solid;">
                <thead>
                    <tr bgcolor="LightGray">
                        <th style="text-align: center; padding-left: 8px" width="10%">序</th>
                        <th style="padding-left: 8px" width="50%" align="left">健保處置</th>
                        <th style="padding-right: 8px" align="right" width="15%">次數</th>
                        <th style="padding-left: 8px" align="left" width="25%">備註</th>
                    </tr>
                </thead>
                <tbody>
                    {prescript_data}
                </tbody>
            </table>
            <br>
        '''

        return prescript_html
