
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import dialog_utils
from libs import module_utils
from libs import personnel_utils


# 自費銷售記錄 2021.10.01
class PurchaseRecords(QtWidgets.QMainWindow):
    program_name = '自費銷售記錄'

    # 初始化
    def __init__(self, parent=None, *args):
        super(PurchaseRecords, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.dialog_setting = {
            "dialog_executed": False,

            "by_date": True,
            "start_date": None,
            "end_date": None,

            "by_invoice_no": False,
            "invoice_no": None,
            "invoice_no_2": None,

            "find_all": False,
            "no_zero_bonus": False,
        }

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_permission()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PURCHASE_RECORDS, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_form)
        self.ui.action_open_dialog.triggered.connect(self.open_dialog)
        self.ui.action_print_purchase_list.triggered.connect(self.print_purchase_list)
        self.ui.action_export_excel.triggered.connect(self.export_purchase_list)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(
                self.database, self.program_name, '匯出自費銷售記錄', self.user_name) != 'Y':
            self.ui.action_export_excel.setEnabled(False)

        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.action_export_excel.setEnabled(False)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_purchase_query(self, self.database, self.system_settings)

        if self.dialog_setting['dialog_executed']:
            dialog.ui.dateEdit_start_date.setDate(self.dialog_setting['start_date'])
            dialog.ui.dateEdit_end_date.setDate(self.dialog_setting['end_date'])
            dialog.ui.checkBox_no_zero_bonus.setChecked(self.dialog_setting['no_zero_bonus'])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['start_date'] = dialog.ui.dateEdit_start_date.date()
        self.dialog_setting['end_date'] = dialog.ui.dateEdit_end_date.date()
        self.dialog_setting['no_zero_bonus'] = dialog.ui.checkBox_no_zero_bonus.isChecked()

        self._set_tab_widget(dialog)
        dialog.deleteLater()

    def _set_tab_widget(self, dialog):
        self.ui.tabWidget_statistics_summary.clear()
        # self.ui.statusbar.showMessage(f' 統計期間: 月')

        self._add_purchase_records_list(dialog)

    # 醫師自費銷售業績統計
    def _add_purchase_records_list(self, dialog):
        self.tab_purchase_records_list = module_utils.get_purchase_records_list(
            self, self.database, self.system_settings, dialog, self.dialog_setting['no_zero_bonus']
        )
        self.tab_purchase_records_list.start_calculate()
        self.ui.tabWidget_statistics_summary.addTab(self.tab_purchase_records_list, '自費銷售記錄')

    def print_purchase_list(self):
        self.tab_purchase_records_list.print_purchase_list()

    def export_purchase_list(self):
        self.tab_purchase_records_list.export_prescript()
