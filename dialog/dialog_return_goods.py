
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime

from libs import system_utils
from libs import ui_utils
from libs import personnel_utils
from libs import dialog_utils


# 主視窗
class DialogReturnGoods(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogReturnGoods, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.medicine_key = args[3]
        self.medicine_name = args[4]
        self.invoice_no = args[5]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_RETURN_GOODS, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        self.ui.lineEdit_medicine_name.setText(self.medicine_name)
        self.dateEdit_return_date.setDate(datetime.datetime.now())
        self._set_combo_box()
        if self.invoice_no in ['', None]:
            self.ui.pushButton_course.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.pushButton_course.clicked.connect(self._open_purchase_course_list)

    def _set_combo_box(self):
        items = personnel_utils.get_person(self.database, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_dealer, items)
        self.ui.comboBox_dealer.setCurrentText(self.user_name)

    def accepted_button_clicked(self):
        pass

    def _open_purchase_course_list(self):
        dialog = dialog_utils.get_dialog_purchase_course_list(
            self, self.database, self.system_settings, self.case_key, self.medicine_key, self.invoice_no)
        dialog.exec_()
        dialog.deleteLater()
