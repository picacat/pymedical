
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime

from libs import system_utils
from libs import ui_utils
from libs import nhi_utils
from libs import personnel_utils
from libs import registration_utils
from libs import string_utils


# 新增盤點記錄
class DialogAddInventory(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogAddInventory, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.stock_inventory_key = args[2]

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_ADD_INVENTORY, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        ui_utils.set_combo_box(
            self.ui.comboBox_inspector,
            personnel_utils.get_person(self.database, '職員'),
        )
        self.ui.dateEdit_inventory_date.setDate(datetime.datetime.today())

        if self.stock_inventory_key is not None:
            self._set_stock_inventory_data()

    def _set_stock_inventory_data(self):
        sql = f'''
            SELECT * FROM stockinventory
            WHERE
                StockInventoryKey = {self.stock_inventory_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self.ui.dateEdit_inventory_date.setDate(row['StockInventoryDate'])
        self.ui.comboBox_inspector.setCurrentText(string_utils.xstr(row['Inspector']))
        self.ui.lineEdit_remark.setText(string_utils.xstr(row['Remark']))

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        if self.stock_inventory_key is None:
            self._insert_inventory()
        else:
            self._update_inventory()

    def _insert_inventory(self):
        fields = [
            'StockInventoryDate', 'Inspector', 'Remark',
        ]
        data = [
            self.ui.dateEdit_inventory_date.date().toString('yyyy-MM-dd'),
            self.ui.comboBox_inspector.currentText(),
            self.ui.lineEdit_remark.text(),
        ]
        self.stock_inventory_key = self.database.insert_record('stockinventory', fields, data)

    def _update_inventory(self):
        fields = [
            'StockInventoryDate', 'Inspector', 'Remark',
        ]
        data = [
            self.ui.dateEdit_inventory_date.date().toString('yyyy-MM-dd'),
            self.ui.comboBox_inspector.currentText(),
            self.ui.lineEdit_remark.text(),
        ]
        self.database.update_record('stockinventory', fields, 'StockInventoryKey', self.stock_inventory_key, data)
