
# -*- coding: UTF-8 -*-

import csv

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import dialog_utils
from libs import dropbox_utils


#  其他資料 2019.07.11
class DictHosp(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DictHosp, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_hosp()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DICT_HOSP, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_dict_hosp = class_utils.get_table_widget(
            self.ui.tableWidget_dict_hosp, self.database
        )
        self.table_widget_dict_hosp.set_column_hidden([0])
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_add_hosp.clicked.connect(self._add_hosp)
        self.ui.toolButton_remove_hosp.clicked.connect(self._remove_hosp)
        self.ui.toolButton_import.clicked.connect(self._import_hosp)
        self.ui.toolButton_download.clicked.connect(self._update_hosp)
        self.ui.lineEdit_query.textChanged.connect(self._query_hosp)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 150, 500, 200, 740]
        self.table_widget_dict_hosp.set_table_heading_width(width)

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def _read_hosp(self, sql=None):
        if sql is None:
            sql = '''
                SELECT * FROM hospid
                ORDER BY HospID
            '''

        self.table_widget_dict_hosp.set_db_data(sql, self._set_dict_hosp_data)

    def _set_dict_hosp_data(self, row_no, row):
        dict_hosp_row = [
            string_utils.xstr(row['HospKey']),
            string_utils.xstr(row['HospID']),
            string_utils.xstr(row['HospName']),
            string_utils.xstr(row['Telephone']),
            string_utils.xstr(row['Address']),
        ]

        for column in range(len(dict_hosp_row)):
            self.ui.tableWidget_dict_hosp.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(dict_hosp_row[column])
            )

    def _query_hosp(self):
        keywords = self.ui.lineEdit_query.text().split()
        if len(keywords) <= 0:
            self._read_hosp()
            self.ui.lineEdit_query.setFocus(True)
            return

        condition = []
        for keyword in keywords:
            condition.append(f'''
                (HospID LIKE "{keyword}%" OR
                 HospName LIKE "%{keyword}%" OR
                 Telephone LIKE "%{keyword}%" OR
                 Address LIKE "%{keyword}%")
            ''')

        condition = ' AND '.join(condition)
        sql = f'''
            SELECT * FROM hospid
            WHERE
                {condition}
            ORDER BY HospID
        '''
        self._read_hosp(sql)
        self.ui.lineEdit_query.setFocus(True)
        self.ui.lineEdit_query.setCursorPosition(len(self.ui.lineEdit_query.text()))

    # 新增院所資料
    def _add_hosp(self):
        pass

    # 移除院所資料
    def _remove_hosp(self):
        clinic_name = self.table_widget_dict_hosp.field_value(2)
        msg_box = dialog_utils.get_message_box(
            '刪除資料',
            QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定刪除院所資料 "{clinic_name}"?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_dict_hosp.field_value(0)
        self.database.delete_record('hosp', 'HospKey', key)
        self.ui.tableWidget_dict_hosp.removeRow(self.ui.tableWidget_dict_hosp.currentRow())

    def _update_hosp(self):
        title = '下載健保特約醫師機構名冊檔'
        message = '<font size="5" color="red"><b>正在下載健保健保特約醫事機構名冊檔, 請稍後...</b></font>'
        hint = '正在與更新檔資料庫連線, 會花費一些時間.'
        filename = 'hospbsc.txt'
        url = 'https://www.dropbox.com/s/i7326uv1l8lo2zs/hospbsc.txt?dl=1'
        dropbox_utils.download_dropbox_file(filename, url, title, message, hint)

        self._import_hosp_file(filename)
        system_utils.show_message_box(
            QMessageBox.Information,
            '線上更新醫事機構名冊',
            '<font size="5" color="blue"><b>最新版本的醫事機構名冊已更新完成.</b></font>',
            '恭喜您! 現在已經是最新的醫事機構名冊資料檔'
        )

    def _import_hosp(self):
        options = QFileDialog.Options()

        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(
            self, "匯入院所資料",
            'hospbsc.txt',
            "所有檔案 (*);;txt檔 (*.txt)", options=options
        )
        if not file_name:
            return

        self._import_hosp_file(file_name)

    def _import_hosp_file(self, file_name):
        with open(file_name, encoding='utf16', newline='') as f:
            for i, l in enumerate(f):
                pass

        row_count = i + 1
        progress_dialog = QtWidgets.QProgressDialog(
            '正在轉入院所資料檔中, 請稍後...', '取消', 0, row_count, self
        )

        self.database.exec_sql('TRUNCATE hospid')
        fields = [
            'HospID', 'HospName', 'Telephone', 'Address'
        ]

        with open(file_name, encoding='utf16', newline='') as csv_file:
            rows = csv.DictReader(csv_file)

            progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
            row_no = 0
            for row in rows:
                progress_dialog.setValue(row_no)
                if progress_dialog.wasCanceled():
                    break

                row_no += 1
                try:
                    self._insert_hosp_row(fields, row)
                except Exception:
                    pass

            progress_dialog.setValue(row_count)
            progress_dialog.deleteLater()

        self._read_hosp()

    def _insert_hosp_row(self, fields, row):
        if string_utils.xstr(row['機構地址']) == '' and string_utils.xstr(row['電話號碼']) == '':
            return

        try:
            area_code = row['電話區域號碼 ']
            telephone = row['電話號碼']
            telephone = f'{area_code}-{telephone}'
        except KeyError:
            telephone = row['電話號碼']

        data = [
            row['醫事機構代碼'],
            row['醫事機構名稱'],
            telephone,
            row['機構地址'],
        ]

        self.database.insert_record('hospid', fields, data)
