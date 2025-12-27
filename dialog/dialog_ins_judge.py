
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime

from libs import system_utils
from libs import ui_utils
from libs import string_utils


# 主視窗
class DialogInsJudge(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInsJudge, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INS_JUDGE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.lineEdit_clinic_name.setText(self.system_settings.field('院所名稱'))
        self.ui.lineEdit_clinic_id.setText(self.system_settings.field('院所代號'))
        self._set_combo_box()
        self._set_apply_date()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.comboBox_year.currentTextChanged.connect(self._set_apply_date)
        self.ui.comboBox_month.currentTextChanged.connect(self._set_apply_date)

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
        self.ui.comboBox_year.setCurrentText(str(current_year))
        self.ui.comboBox_month.setCurrentText(str(current_month))
        for combo_box in self.findChildren(QtWidgets.QComboBox):
            combo_box.setView(QtWidgets.QListView())

    def _set_apply_date(self):
        year = self.ui.comboBox_year.currentText()
        month = self.ui.comboBox_month.currentText()
        log_name = f'{year}-{month:0>2}'
        sql = f'''
            SELECT * FROM system_log
            WHERE
                LogType = "申報日期" AND
                LogName = "{log_name}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            apply_date = datetime.datetime.strptime(f'{year}-{month}-01', '%Y-%m-%d')
        else:
            apply_date = datetime.datetime.strptime(string_utils.xstr(rows[0]['Log']), '%Y-%m-%d')

        self.ui.dateEdit_apply.setDate(apply_date)

    def accepted_button_clicked(self):
        pass
