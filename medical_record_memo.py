# -*- coding: utf-8 -*-

from PyQt5 import QtWidgets

from libs import (case_utils, personnel_utils, string_utils, system_utils,
                  ui_utils)


# 病歷資料-記事 2023.05.31 琥珀
class MedicalRecordMemo(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(MedicalRecordMemo, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.patient_key = args[3]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_memo()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_MEDICAL_RECORD_MEMO, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

    # 設定信號
    def _set_signal(self):
        pass

    def _read_memo(self):
        if self.system_settings.field('備忘錄以病患鍵為主') == 'Y':
            sql = f'''
                SELECT * FROM patient_extension
                WHERE
                    PatientKey = {self.patient_key} AND
                    ExtensionType = "Memo"
                ORDER BY PatientExtensionKey DESC LIMIT 1
            '''
        else:
            sql = f'''
                SELECT * FROM case_extension
                WHERE
                    CaseKey = {self.case_key} AND
                    ExtensionType = "Memo"
            '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        memo = string_utils.xstr(row['Content'])
        self.ui.textEdit_memo.setPlainText(memo)

    def save_memo(self):
        memo = self.ui.textEdit_memo.toPlainText()
        if memo.strip() == '':
            self._delete_memo()
            return

        if self.system_settings.field('備忘錄以病患鍵為主') == 'Y':
            sql = f'''
                SELECT PatientExtensionKey FROM patient_extension
                WHERE
                    ExtensionType = "Memo" AND
                    PatientKey = {self.patient_key}
                ORDER BY PatientExtensionKey DESC LIMIT 1
            '''
            rows = self.database.select_record(sql)
            if not rows:
                fields = ['PatientKey', 'ExtensionType', 'Content']
                data = [self.patient_key, 'Memo', memo]
                self.database.insert_record('patient_extension', fields, data)
                return

            patient_extension_key = rows[0]['PatientExtensionKey']
            self.database.exec_sql(f'''
                UPDATE patient_extension
                SET
                    Content = "{memo}"
                WHERE
                    PatientExtensionKey = {patient_extension_key}
            ''')
                
        else:
            print('case_key')            
            fields = ['CaseKey', 'ExtensionType', 'Content']
            data = [self.case_key, 'Memo', memo]
            self.database.insert_record('case_extension', fields, data)

    def _delete_memo(self):
        if self.system_settings.field('備忘錄以病患鍵為主') == 'Y':
            sql = f'''
                DELETE FROM patient_extension
                WHERE
                    PatientKey = {self.patient_key} AND
                    ExtensionType = "Memo"
            '''
        else:
            sql = f'''
                DELETE FROM case_extension
                WHERE
                    CaseKey = {self.case_key} AND
                    ExtensionType = "Memo"
            '''
        self.database.exec_sql(sql)

