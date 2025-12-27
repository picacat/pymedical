
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import module_utils


# 資料回復 2019.06.20
class RestoreRecords(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(RestoreRecords, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()

        self._set_tab_widget()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_RESTORE_RECORDS, self)
        system_utils.set_css(self, self.system_settings)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_form)
        self.ui.action_restore_record.triggered.connect(self._restore_record)
        self.ui.action_view_deleted_record_json.triggered.connect(self._view_deleted_record_json)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def _set_tab_widget(self):
        self.ui.tabWidget_restore_records.clear()
        self._add_tab_restore_medical_records()

    def _add_tab_restore_medical_records(self):
        self.tab_restore_medical_records = module_utils.get_restore_medical_records(
            self, self.database, self.system_settings,
        )
        self.tab_restore_medical_records.read_data()
        self.ui.tabWidget_restore_records.addTab(self.tab_restore_medical_records, '病歷資料')

    # 資料回復
    def _restore_record(self):
        if self.ui.tabWidget_restore_records.currentIndex() == 0:
            self.tab_restore_medical_records.restore_medical_record()

    # 查看刪除內容
    def _view_deleted_record_json(self):
        if self.ui.tabWidget_restore_records.currentIndex() == 0:
            self.tab_restore_medical_records.view_medical_record_json()
