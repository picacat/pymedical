
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from libs import ui_utils
from libs import system_utils
from libs import class_utils


# 主視窗
class DialogPulsePicker(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPulsePicker, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.text_edit = args[2]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_pulse()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PULSE_PICKER, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_pulse = class_utils.get_table_widget(self.ui.tableWidget_pulse, self.database)

    # 設定信號
    def _set_signal(self):
        for tool_button in self.findChildren(QtWidgets.QToolButton):
            tool_button.clicked.connect(self._tool_button_clicked)

        self.ui.tableWidget_pulse.clicked.connect(self._add_pulse)
        self.ui.tableWidget_pulse.keyPressEvent = self._table_widget_key_press

    def _table_widget_key_press(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.parent.close()

        return QtWidgets.QTableWidget.keyPressEvent(self.ui.tableWidget_pulse, event)

    def _tool_button_clicked(self):
        pulse_name = self.sender().text()
        if pulse_name in ['左脈', '右脈']:
            if self.text_edit.toPlainText() == '':
                pulse_name += ': '
            else:
                pulse_name = '; ' + pulse_name + ': '

        self.parent.parent.insert_text(self.text_edit, pulse_name, '', insert_comma=False)

    def _read_pulse(self):
        order_type = 'ORDER BY LENGTH(ClinicName), CAST(CONVERT(`ClinicName` using big5) AS BINARY)'
        # if self.system_settings.field('詞庫排序') == '點擊率':
        #     order_type = 'ORDER BY HitRate DESC'
        # elif self.system_settings.field('詞庫排序') == '最後點擊時戳':
        #     order_type = 'ORDER BY TimeStamp DESC'

        sql = f'''
            SELECT ClinicName FROM clinic
            WHERE
                ClinicType = "脈象"
            {order_type}
        '''
        self.table_widget_pulse.set_db_data_without_heading(sql, 'ClinicName')

    def _add_pulse(self):
        if not self.ui.tableWidget_pulse.selectedItems():
            return

        pulse_name = self.ui.tableWidget_pulse.selectedItems()[0].text()
        self.parent.parent.insert_text(self.text_edit, pulse_name, '', insert_comma=False)
