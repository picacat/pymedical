
# -*- coding: UTF-8 -*-

import datetime
import enum

from libs import (class_utils, nhi_utils, number_utils, prescript_utils,
                  string_utils, system_utils, ui_utils)
from PyQt5 import QtCore, QtWidgets

INS_DRUG_DICT = {
    'A005541': {
        '勝昌': 'A038807',
        '莊松榮': 'A031399',
        '科達': 'A057512',
        '順天堂': 'A031152',
        '天明': 'A030832',
    },
    'A014478': {
        '勝昌': 'A028833',
        '莊松榮': 'A044695',
        '科達': 'A042563',
        '順天堂': 'A023247',
        '天明': 'A035021',
    },
    'A015127': {
        '勝昌': 'A028433',
        '莊松榮': 'A031610',
        '科達': 'A029891',
        '順天堂': 'A030497',
        '天明': 'A046708',
    },
    'A033317': {
        '勝昌': 'A036139',
        '莊松榮': 'A038345',
        '科達': 'A035904',
        '順天堂': 'A038658',
        '天明': 'A042790',
    },
    'A038028': {
        '勝昌': 'A039097',
        '莊松榮': 'A038105',
        '科達': 'A038360',
        '順天堂': 'A042164',
        '天明': 'A042833',
    },
    'A035340': {
        '勝昌': 'A006880',
        '莊松榮': 'A058453',
        '科達': 'A031478',
        '順天堂': 'A006880',
        '天明': 'A055152',
    },
    'A039447': {
        '勝昌': 'A039071',
        '莊松榮': 'A044728',
        '科達': 'A035347',
        '順天堂': 'A042167',
        '天明': 'A036828',
    },
    'A031916': {
        '勝昌': 'A006888',
        '莊松榮': 'A039459',
        '科達': 'A036716',
        '順天堂': 'A046774',
        '天明': 'A039834',
    },
    'A033842': {
        '勝昌': 'A007929',
        '莊松榮': 'A033712',
        '科達': 'A055822',
        '順天堂': 'A017268',
        '天明': 'A055141',
    },
    'A033818': {
        '勝昌': 'A016569',
        '莊松榮': 'A061211',
        '科達': 'A040318',
        '順天堂': 'A010552',
        '天明': 'A047096',
    },
    'A033843': {
        '勝昌': 'A004023',
        '莊松榮': 'A033727',
        '科達': 'A032909',
        '順天堂': 'A046784',
        '天明': 'A040329',
    },
    'A038582': {
        '勝昌': 'A011641',
        '莊松榮': 'A055212',
        '科達': 'A056399',
        '順天堂': 'A001282',
        '天明': 'A057005',
    },
    'A038742': {
        '勝昌': 'A040235',
        '莊松榮': 'A040031',
        '科達': 'A041305',
        '順天堂': 'A002880',
        '天明': 'A046379',
    },
    'A039933': {
        '勝昌': 'A009001',
        '莊松榮': 'A040954',
        '科達': 'A041306',
        '順天堂': 'A010556',
        '天明': 'A055393',
    },
    'A040942': {
        '勝昌': 'A005152',
        '莊松榮': 'A045767',
        '科達': 'A055396',
        '順天堂': 'A017273',
        '天明': 'A058505',
    },
    'A008178': {
        '勝昌': '',
        '莊松榮': '',
        '科達': '',
        '順天堂': '',
        '天明': '',
    },
}

        
# 檢查港香蘭無效健保碼 2025-09-24
class DialogInvalidInsDrug(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInvalidInsDrug, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INVALID_INS_DRUG, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('自動更新健保藥碼')
 
        self.table_widget_ins_drug = class_utils.get_table_widget(
            self.ui.tableWidget_ins_drug, self.database
        )
        self.table_widget_ins_drug.set_column_hidden([0, 1])
        self._set_table_width()

    def _set_table_width(self):
        width = [100, 120, 110, 80, 200, 120, 250]
        self.table_widget_ins_drug.set_table_heading_width(width)

    def start_check(self):
        sql = f'''
            SELECT PrescriptKey, prescript.MedicineType, prescript.InsCode, prescript. MedicineName,
                cases.Name, cases.CaseDate,
                drug.Supplier
            FROM prescript
                LEFT JOIN cases ON cases.CaseKey = prescript.CaseKey
                LEFT JOIN drug ON drug.InsCode = prescript.InsCode
            WHERE
                prescript.InsCode IN {tuple(nhi_utils.INVALID_INS_CODE_LIST)} AND
                DATE(cases.CaseDate) >= "2025-09-01"
            ORDER BY prescript.InsCode
        '''
        
        rows = self.database.select_record(sql)
        if not rows:
            # system_utils.show_message_box(
            #     QtWidgets.QMessageBox.Information,
            #     '健保碼檢查完成',
            #     '<h3>經查本院並無使用港香蘭16項無效藥品，請放心！</h3>',
            #     '檢查日期: 2025-09-01開始檢查.'
            # )
            
            return

        self.setModal(True)
        self.show()
        self._set_table_data(rows)

    def _set_table_data(self, rows):
        self.ui.tableWidget_ins_drug.setRowCount(len(rows))
        for row_no, row in enumerate(rows):
            prescript_row = [
                string_utils.xstr(row['PrescriptKey']),
                string_utils.xstr(row['CaseDate'].date()),
                string_utils.xstr(row['Name']),
                string_utils.xstr(row['MedicineType']),                
                string_utils.xstr(row['MedicineName']),
                string_utils.xstr(row['InsCode']),
                string_utils.xstr(row['Supplier']),
            ]
            for col_no in range(len(prescript_row)):
                self.ui.tableWidget_ins_drug.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem(prescript_row[col_no])
                )
            
    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        self._correct_ins_drug()

    def _correct_ins_drug(self):
        for row_no in range(self.ui.tableWidget_ins_drug.rowCount()):
            prescript_key = self.ui.tableWidget_ins_drug.item(row_no, 0)
            
            if prescript_key is None:
                continue
            
            prescript_key = prescript_key.text()
            ins_code = self.ui.tableWidget_ins_drug.item(row_no, 5).text()            
            self._update_prescript_ins_code(prescript_key, ins_code)

    def _get_supplier(self):
        radio_button_list = [
            self.ui.radioButton1,
            self.ui.radioButton2,
            self.ui.radioButton3,
            self.ui.radioButton4,
            self.ui.radioButton5,
        ]

        for radio_button in radio_button_list:
            if radio_button.isChecked():
                supplier = radio_button.text()
                break

        return supplier
        
    def _update_prescript_ins_code(self, prescript_key, ins_code):
        supplier = self._get_supplier()
        try:
            correct_ins_code = INS_DRUG_DICT[ins_code][supplier]            
        except Exception:
            return

        if correct_ins_code == '':
            sql = f'UPDATE prescript SET InsCode = NULL WHERE PrescriptKey = {prescript_key}'
        else:
            sql = f'UPDATE prescript SET InsCode = "{correct_ins_code}" WHERE PrescriptKey = {prescript_key}'

        self.database.exec_sql(sql)


