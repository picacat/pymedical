
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QSettings, QSize, QPoint

from libs import ui_utils
from libs import system_utils
from libs import string_utils


# 主視窗
class DialogPatientMemo(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPatientMemo, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]  # rich_text, plain_text, html
        self.text_format = 'rich_text'

        self.ui = None
        self.settings = QSettings('__settings.ini', QSettings.IniFormat)

        self._set_ui()
        self._set_signal()
        if self.patient_key not in [0, None]:
            self._read_patient_memo()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def show_patient_memo(self):
        self.show()

    # 關閉
    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.settings.setValue("dialog_patient_memo_size", self.size())
        self.settings.setValue("dialog_patient_memo_pos", self.pos())


    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PATIENT_MEMO, self)
        self.ui.resize(self.settings.value("dialog_patient_memo_size", QSize(858, 769)))

        screen_width = QtWidgets.QDesktopWidget().screenGeometry().width()

        pos = self.settings.value("dialog_patient_memo_pos")
        if pos is not None and pos.x() < screen_width:
            self.ui.move(self.settings.value("dialog_patient_memo_pos", QPoint(1054, 225)))

        # self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')

    def _read_patient_memo(self):
        sql = f'''
            SELECT PatientKey, Name, Description FROM patient
            WHERE
                PatientKey = {self.patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            text = rows[0]['Description']
            name = string_utils.xstr(rows[0]['Name'])
            patient_key = string_utils.xstr(rows[0]['PatientKey'])
            self.ui.label_patient.setText(f'病歷號碼: {patient_key} {name}')
        else:
            text = ''
            self.ui.label_patient.setText(None)

        try:
            if self.text_format == 'rich_text':
                self.ui.textEdit_rich_text.setText(text)
            elif self.text_format == 'plain_text':
                self.ui.textEdit_rich_text.setPlainText(text)
            elif self.text_format == 'html':
                self.ui.textEdit_rich_text.setHtml(text)
        except TypeError:
            self.ui.textEdit_rich_text.setText('內有亂碼, 無法顯示')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self._accepted_button_clicked)

    def _accepted_button_clicked(self):
        self._save_description()
        self.settings.setValue("dialog_patient_memo_size", self.size())
        self.settings.setValue("dialog_patient_memo_pos", self.pos())

        self.close()

    def _save_description(self):
        description = self.ui.textEdit_rich_text.toPlainText()
        description = string_utils.remove_quote_characters(description)

        sql = f'''
            UPDATE patient
                SET Description = "{description}"
            WHERE
                PatientKey = {self.patient_key}
        '''
        self.database.exec_sql(sql)
