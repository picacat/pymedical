
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from libs import ui_utils
from libs import system_utils


# 建立廠商通訊錄資料 2022.09.06
class DialogInputSupplier(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInputSupplier, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        try:
            self.supplier_key = args[2]
        except IndexError:
            self.supplier_key = None

        self.ui = None

        self._set_ui()
        self._set_signal()
        if self.supplier_key is not None:
            self._edit_supplier()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INPUT_SUPPLIER, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('存檔')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.lineEdit_supplier_name.setFocus()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def _edit_supplier(self):
        sql = f'''
            SELECT * FROM supplier
            WHERE
                SupplierKey = {self.supplier_key}
        '''
        row = self.database.select_record(sql)[0]
        self.ui.lineEdit_supplier_code.setText(row['Code'])
        self.ui.lineEdit_supplier_name.setText(row['Name'])
        self.ui.lineEdit_telephone.setText(row['Telephone'])
        self.ui.lineEdit_cellphone.setText(row['Cellphone'])
        self.ui.lineEdit_address.setText(row['Address'])
        self.ui.plainTextEdit_remark.setPlainText(row['Remark'])

    def accepted_button_clicked(self):
        fields = ['Code', 'Name', 'Telephone', 'Cellphone', 'Address', 'Remark']
        data = [
            self.ui.lineEdit_supplier_code.text(),
            self.ui.lineEdit_supplier_name.text(),
            self.ui.lineEdit_telephone.text(),
            self.ui.lineEdit_cellphone.text(),
            self.ui.lineEdit_address.text(),
            self.ui.plainTextEdit_remark.toPlainText(),
        ]

        if self.supplier_key is None:
            self.database.insert_record('supplier', fields, data)
        else:
            self.database.update_record('supplier', fields, 'SupplierKey', self.supplier_key, data)
