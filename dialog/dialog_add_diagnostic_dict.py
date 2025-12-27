
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import string_utils


# 新增主訴詞庫 2019.08.27
class DialogAddDiagnosticDict(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogAddDiagnosticDict, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.dict_type = args[2]
        self.dict_name = args[3]

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_ADD_DIAGNOSTIC_DICT, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.textEdit_dict_name.setText(self.dict_name)
        self.ui.lineEdit_input_code.setFocus()
        self._set_combo_box()

    def _set_combo_box(self):
        sql = f'''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = "{self.dict_type}"
            GROUP BY DictGroupsTopLevel
            ORDER BY DictGroupsKey
        '''
        rows = self.database.select_record(sql)

        groups_type_list = []
        for row in rows:
            groups_type_list.append(string_utils.xstr(row['DictGroupsTopLevel']))

        ui_utils.set_combo_box(self.ui.comboBox_groups_type, groups_type_list, None)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.comboBox_groups_type.currentTextChanged.connect(self._groups_type_changed)

    def accepted_button_clicked(self):
        self._insert_diagnostic()
        self.close()

    # 寫入主訴
    def _insert_diagnostic(self):
        fields = [
            'ClinicType', 'InputCode', 'ClinicName', 'Groups'
        ]

        data = [
            self.dict_type,
            self.ui.lineEdit_input_code.text(),
            self.ui.textEdit_dict_name.toPlainText(),
            self.ui.comboBox_sub_groups.currentText(),
        ]

        self.database.insert_record('clinic', fields, data)

    def _groups_type_changed(self):
        self.ui.comboBox_sub_groups.clear()

        groups_type = self.ui.comboBox_groups_type.currentText()
        if groups_type == '':
            return

        sql = f'''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = "{self.dict_type}" AND
                DictGroupsTopLevel = "{groups_type}"
            GROUP BY DictGroupsName
            ORDER BY DictGroupsName
        '''
        rows = self.database.select_record(sql)

        sub_groups_list = []
        for row in rows:
            sub_groups_list.append(string_utils.xstr(row['DictGroupsName']))

        ui_utils.set_combo_box(self.ui.comboBox_sub_groups, sub_groups_list, None)
