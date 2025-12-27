
# 列印選擇器
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import case_utils


# 主視窗
class DialogSelectMedicineSet(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogSelectMedicineSet, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.form_type = args[3]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._set_option_items()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_SELECT_MEDICINE_SET, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.checkBox_select_all.clicked.connect(self._selected_all_options)

    def accepted_button_clicked(self):
        pass

    def _set_option_items(self):
        sql = f'''
            SELECT MedicineSet FROM prescript
            WHERE
                CaseKey = {self.case_key}
            GROUP BY MedicineSet
            ORDER BY MedicineSet
        '''
        rows = self.database.select_record(sql)
        sql = f'''
            SELECT TreatType FROM cases
            WHERE
                CaseKey = {self.case_key} AND
                TreatType = "醫療諮詢"
        '''
        case_rows = self.database.select_record(sql)
        if len(case_rows) > 0:
            rows.insert(0, {'MedicineSet': 1})

        self.check_box_list = []
        for row in rows:
            medicine_set = row['MedicineSet']
            if medicine_set == 1:
                item_name = f'健保{self.form_type}'
            else:
                item_name = f'自費{self.form_type}{medicine_set-1}'

            check_box = QtWidgets.QCheckBox()
            check_box.setText(item_name)
            check_box.clicked.connect(self._check_selected_options)

            rows = case_utils.get_dosage_row(self.database, self.case_key, medicine_set)
            if len(rows) > 0 and '本頁不印' in string_utils.xstr(rows[0]['Remark']):
                check_box.setEnabled(False)

            self.check_box_list.append(check_box)

        for item in self.check_box_list:
            self.ui.verticalLayout_options.addWidget(item)

        vertical_spacer = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.ui.verticalLayout_options.addItem(vertical_spacer)

    def _check_selected_options(self):
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        for check_box in self.check_box_list:
            if check_box.isChecked():
                self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
                return

    def get_selected_options(self):
        selected_items = []
        for check_box in self.check_box_list:
            if check_box.isChecked():
                selected_items.append(check_box.text())

        return selected_items

    def get_all_options(self):
        selected_items = []
        for check_box in self.check_box_list:
            selected_items.append(check_box.text())

        return selected_items

    def _selected_all_options(self):
        if self.ui.checkBox_select_all.isChecked():
            checked = True
        else:
            checked = False

        for check_box in self.check_box_list:
            if check_box.isEnabled():
                check_box.setChecked(checked)

        self._check_selected_options()
