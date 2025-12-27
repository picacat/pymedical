
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import string_utils


# 主視窗
class DialogRichText(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogRichText, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.text_format = args[2]  # rich_text, plain_text, html
        self.medicine_key = args[3]
        self.text = args[4]

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_RICH_TEXT, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        if self.medicine_key is not None:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('儲存編輯')
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Close).setText('關閉')
        else:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setVisible(False)
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Close).setText('關閉')

        self._set_text()
        if self.medicine_key is None:
            self.ui.textEdit_rich_text.setReadOnly(True)

    def _set_text(self):
        text = self.text

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
        self.ui.buttonBox.rejected.connect(self._rejected_button_clicked)

    def _rejected_button_clicked(self):
        self.close()

    def _accepted_button_clicked(self):
        if self.medicine_key is not None and self.ui.textEdit_rich_text.document().isModified():
            self._save_description()

        self.close()

    def _save_description(self):
        description = self.ui.textEdit_rich_text.toPlainText()
        description = string_utils.remove_quote_characters(description)

        sql = f'''
            UPDATE medicine
                SET Description = "{description}"
            WHERE
                MedicineKey = {self.medicine_key}
        '''
        self.database.exec_sql(sql)
