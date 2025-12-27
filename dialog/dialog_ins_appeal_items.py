
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from libs import ui_utils
from libs import system_utils
from libs import string_utils


# 輸入申復資料 2022.11.08
class DialogInsAppealItems(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInsAppealItems, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_date = args[2]
        self.ins_appeal_items_key = args[3]
        self.ins_appeal_key = args[4]

        self.ui = None
        self.clinic_id = self.system_settings.field('院所代號')

        self._set_ui()
        self._set_signal()
        self._set_sample()

        if self.ins_appeal_items_key is not None:
            self._edit_ins_appeal_items()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INS_APPEAL_ITEMS, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('存檔')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)

    def _set_sample(self):
        sql = f'''
            SELECT Sample FROM insappeal
            WHERE
                InsAppealKey = {self.ins_appeal_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.ui.radioButton_1.setEnabled(True)
        self.ui.radioButton_2.setEnabled(True)

        sample = rows[0]['Sample']
        if sample == '統扣':
            self.ui.radioButton_2.setChecked(True)
            self.ui.radioButton_1.setEnabled(False)
        else:
            self.ui.radioButton_1.setChecked(True)
            self.ui.radioButton_2.setEnabled(False)

    def accepted_button_clicked(self):
        self._save_ins_appeal_items()

        self.close()

    def rejected_button_clicked(self):
        self.close()

    def _edit_ins_appeal_items(self):
        sql = f'''
            SELECT * FROM insappeal_items
            WHERE
                InsAppealItemsKey = {self.ins_appeal_items_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]
        if string_utils.xstr(row['ItemType']) == '申復醫令段':
            self.ui.radioButton_1.setChecked(True)
        else:
            self.ui.radioButton_2.setChecked(True)

        self.ui.lineEdit_item_seq.setText(string_utils.xstr(row['OrderSeq']))
        self.ui.lineEdit_ins_code.setText(string_utils.xstr(row['InsCode']))
        self.ui.lineEdit_reject_code.setText(string_utils.xstr(row['RejectCode']))
        self.ui.lineEdit_percent.setText(string_utils.xstr(row['Percent']))
        self.ui.lineEdit_quantity.setText(string_utils.xstr(row['Quantity']))
        self.ui.lineEdit_point.setText(string_utils.xstr(row['Point']))
        self.ui.textEdit_reason.setText(
            string_utils.xstr(row['Reason1']) + string_utils.xstr(row['Reason2']))

    def _save_ins_appeal_items(self):
        if self.ui.radioButton_1.isChecked():
            item_type = '申復醫令段'
        else:
            item_type = '統扣明細段'

        order_seq = self.ui.lineEdit_item_seq.text()
        ins_code = self.ui.lineEdit_ins_code.text()
        reject_code = self.ui.lineEdit_reject_code.text()
        percent = self.ui.lineEdit_percent.text()
        quantity = self.ui.lineEdit_quantity.text()
        point = self.ui.lineEdit_point.text()

        if self.ui.checkBox_file_link.isChecked():
            file_link = '是'
        else:
            file_link = '否'

        reason1 = self.ui.textEdit_reason.toPlainText()
        reason2 = None
        if len(reason1) > 1000:
            reason1 = reason1[:1000]
            reason2 = reason1[1000:2000]

        fields = [
            'InsAppealKey', 'ItemType', 'OrderSeq', 'InsCode', 'RejectCode',
            'Percent', 'Quantity', 'Point', 'FileLink', 'Reason1', 'Reason2']
        data = [
            self.ins_appeal_key, item_type, order_seq, ins_code, reject_code,
            percent, quantity, point, file_link, reason1, reason2]

        if self.ins_appeal_items_key is not None:
            self.database.update_record(
                'insappeal_items', fields, 'InsAppealItemsKey', self.ins_appeal_items_key, data)
        else:
            self.database.insert_record('insappeal_items', fields, data)
