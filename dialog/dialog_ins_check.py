
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime
import calendar

from libs import system_utils
from libs import ui_utils
from libs import nhi_utils
from libs import date_utils


# 主視窗
class DialogInsCheck(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInsCheck, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INS_CHECK, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self._set_combo_box()

        max_treat = nhi_utils.MAX_TREAT
        if self.system_settings.field('健保業務') in ['台北業務組', '北區業務組']:
            max_treat = nhi_utils.MAX_TREAT_TAIPEI

        self.ui.spinBox_diag_limit.setValue(nhi_utils.MAX_DIAG)
        self.ui.spinBox_treat_limit.setValue(max_treat)
        self.ui.spinBox_merge_limit.setValue(nhi_utils.MAX_MERGE_TREAT)

        self.ui.spinBox_moderate_acupuncture_limit.setValue(nhi_utils.MAX_MODERATE_COMPLICATED_ACUPUNCTURE)
        self.ui.spinBox_highly_acupuncture_limit.setValue(nhi_utils.MAX_HIGHLY_COMPLICATED_ACUPUNCTURE)
        self.ui.spinBox_treat_drug_limit.setValue(nhi_utils.MAX_TREAT_DRUG)

        self._set_ins_check_date()

        for combo_box in self.findChildren(QtWidgets.QComboBox):
            combo_box.setView(QtWidgets.QListView())

    def _set_ins_check_date(self):
        self._set_date_duration(True)

        # current_year = int(self.ui.comboBox_year.currentText())
        # current_month = int(self.ui.comboBox_month.currentText())
        # last_day = calendar.monthrange(current_year, current_month)[1]
        # start_date = f'{current_year}-{current_month}-01 00:00:00'
        # end_date = f'{current_year}-{current_month}-{last_day} 23:59:59'

        # self.ui.dateEdit_start_date.setDate(date_utils.str_to_date(start_date))
        # self.ui.dateEdit_end_date.setDate(date_utils.str_to_date(end_date))

        default_date = date_utils.get_default_date(self.system_settings)
        self.ui.dateEdit_start_date.setDate(default_date)
        self.ui.dateEdit_end_date.setDate(default_date)

        self._set_date_duration(False)

    def _set_date_duration(self, enabled):
        self.ui.label_from.setEnabled(enabled)
        self.ui.label_to.setEnabled(enabled)
        self.ui.dateEdit_start_date.setEnabled(enabled)
        self.ui.dateEdit_end_date.setEnabled(enabled)

    def _set_combo_box(self):
        year_list = []
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month
        for i in range(current_year, current_year - 10, -1):
            year_list.append(str(i))

        if current_month > 1:
            current_month -= 1
        else:
            current_month = 12
            current_year -= 1

        ui_utils.set_combo_box(self.ui.comboBox_year, year_list)
        ui_utils.set_combo_box(
            self.ui.comboBox_month,
            [str(x) for x in range(1, 13)]
        )
        self.ui.comboBox_year.setCurrentText(str(current_year))
        self.ui.comboBox_month.setCurrentText(str(current_month))

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.toolButton_select_all.clicked.connect(self._select_all_check_box)
        self.ui.checkBox_date_duration.clicked.connect(lambda: self._set_date_duration(
            self.ui.checkBox_date_duration.isChecked()
        ))
        self.ui.comboBox_year.currentTextChanged.connect(self._set_ins_check_date)
        self.ui.comboBox_month.currentTextChanged.connect(self._set_ins_check_date)

    def accepted_button_clicked(self):
        pass

    def _select_all_check_box(self):
        check_box_list = [
            self.ui.checkBox_check_errors,
            self.ui.checkBox_check_course,
            self.ui.checkBox_check_card,
            self.ui.checkBox_check_medical_record_count,
            self.ui.checkBox_check_prescript_days,
            self.ui.checkBox_check_ins_drug,
            self.ui.checkBox_check_ins_treat,
        ]

        for check_box in check_box_list:
            check_box.setChecked(not check_box.isChecked())
