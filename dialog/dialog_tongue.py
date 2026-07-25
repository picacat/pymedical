
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import db_utils


# 主視窗
class DialogTongue(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogTongue, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.groups = args[2]
        self.text_edit = args[3]

        self.ui = None
        self.diagnostic_type = '舌診'
        self.tongue_rows = []

        self._set_ui()
        self._set_signal()
        self._read_tongue_dict()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_TONGUE, self)
        system_utils.set_css(self, self.system_settings)

    # 設定信號
    def _set_signal(self):
        self.ui.textBrowser.anchorClicked.connect(self._set_text)
        self.ui.textBrowser.keyPressEvent = self.text_browser_key_press

    def text_browser_key_press(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.parent.close()

        return QtWidgets.QTextBrowser.keyPressEvent(self.ui.textBrowser, event)

    def _set_text(self, url):
        tongue_name = url.toString()
        self.parent.parent.insert_text(self.text_edit, tongue_name, '')
        self.text_edit.document().setModified(True)

        clinic_key = self._get_clinic_key(tongue_name)
        if clinic_key is not None:
            db_utils.increment_hit_rate(self.database, 'clinic', 'ClinicKey', clinic_key)

    def _get_clinic_key(self, clinic_name):
        clinic_key = None
        for row in self.tongue_rows:
            if clinic_name == string_utils.xstr(row['ClinicName']):
                clinic_key = string_utils.xstr(row['ClinicKey'])
                break

        return clinic_key

    def _read_tongue_dict(self):
        tongue_coating_html = self._get_tongue_coating_html()

        html = f'''
            {tongue_coating_html}
        '''
        self.ui.textBrowser.setHtml(html)

    def _get_tongue_coating_html(self):
        sql = f'''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = "{self.diagnostic_type}" AND
                DictGroupsTopLevel = "{self.groups}" AND
                DictGroupsName IS NOT NULL AND LENGTH(DictGroupsName) > 0
            ORDER BY LENGTH(DictGroupsName), CAST(CONVERT(`DictGroupsName` using big5) AS BINARY)
        '''
        rows = self.database.select_record(sql)

        html = ''
        for row in rows:
            tongue_type = string_utils.xstr(row['DictGroupsName'])
            html += self._get_tongue_row(tongue_type)

        return html

    def _get_tongue_row(self, tongue_type):
        sql = f'''
            SELECT * FROM clinic
            WHERE
                ClinicType = "{self.diagnostic_type}" AND
                ClinicName IS NOT NULL AND LENGTH(ClinicName) > 0 AND
                Groups = "{tongue_type}"
            ORDER BY LENGTH(ClinicName), CAST(CONVERT(`ClinicName` using big5) AS BINARY)
        '''
        rows = self.database.select_record(sql)
        self.tongue_rows += rows

        html = f'''
            <b>{tongue_type}</b>
            <table cellpadding="4">
        '''

        if self.groups == '舌苔':
            col_count = 10
        else:
            col_count = 8

        td = ''
        for row_no, row in enumerate(rows):
            clinic_name = string_utils.xstr(row['ClinicName'])
            td += f'<td><a href="{clinic_name}">{clinic_name}</a></td>'
            if row_no > 1 and row_no % col_count == col_count-1:
                html += f'<tr>{td}</tr>'
                td = ''

        if td != '':
            html += f'<tr>{td}</tr>'

        html += '</table>'

        return html
