# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox, QFileDialog

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import case_utils
from libs import export_utils
from libs import system_utils


# 免收藥品負擔統計 2020.02.11
class StatisticsInsDiscountDrugShareFee(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsInsDiscountDrugShareFee, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.doctor = args[4]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_INS_DISCOUNT_DRUG_SHARE_FEE, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_medical_record.set_column_hidden([0])
        # self._set_table_width()

    def _set_table_width(self):
        width = [
            100,
            120, 50, 100, 50, 90, 90,
            100, 90, 100, 130, 130, 130, 400,
        ]
        self.table_widget_medical_record.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_medical_record.doubleClicked.connect(self.open_medical_record)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def open_medical_record(self):
        case_key = self.table_widget_medical_record.field_value(0)
        if case_key == '':
            return

        self.parent.parent.open_medical_record(case_key, '病歷查詢')

    def start_calculate(self):
        self._calculate_data()
        self._calculate_total()

    def _calculate_data(self):
        self._read_data()

    def _calculate_total(self):
        drug_share_fee, receipt_drug_share_fee = 0, 0
        total_case_count = 0

        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            total_case_count += 1
            drug_share_fee += number_utils.get_integer(
                self.ui.tableWidget_medical_record.item(row_no, 5).text()
            )
            receipt_drug_share_fee += number_utils.get_integer(
                self.ui.tableWidget_medical_record.item(row_no, 6).text()
            )

        self.ui.tableWidget_medical_record.setRowCount(total_case_count+1)
        row = [
            [3, f'合計{total_case_count}人次'],
            [4, '總計'],
            [5, drug_share_fee],
            [6, receipt_drug_share_fee],
        ]

        for cell in row:
            self._set_item_data(
                total_case_count, cell[0], string_utils.xstr(cell[1])
            )

    def _set_item_data(self, row_no, col_no, data):
        self.ui.tableWidget_medical_record.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(data)
        )
        self.ui.tableWidget_medical_record.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _read_data(self):
        doctor_condition = ''
        if self.doctor != '全部':
            doctor_condition = f' AND Doctor = "{self.doctor}"'

        sql = f'''
            SELECT
                CaseKey, CaseDate, Period, Share, Doctor, Card, Continuance,
                DrugShareFee, SDrugShareFee,
                patient.*
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                DATE(CaseDate) BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                cases.InsType = "健保" AND
                InterDrugFee > 100 AND
                SDrugShareFee <= 0
                {doctor_condition}
            ORDER BY CaseDate
        '''
        self.table_widget_medical_record.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        case_key = row['CaseKey']
        pres_days = case_utils.get_pres_days(self.database, case_key, 1)

        card = string_utils.xstr(row['Card'])
        course = number_utils.get_integer(row['Continuance'])
        if course >= 1:
            card = f'{card}-{course}'

        medical_record = [
            case_key,
            string_utils.xstr(row['CaseDate'].date()),
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['Share']),
            card,
            pres_days,
            number_utils.get_integer(row['DrugShareFee']),
            number_utils.get_integer(row['SDrugShareFee']),
            string_utils.xstr(row['Doctor']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['ID']),
            string_utils.xstr(row['Telephone']),
            string_utils.xstr(row['Cellphone']),
            string_utils.xstr(row['Address'])
        ]

        for col_no in range(len(medical_record)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medical_record[col_no])
            self.ui.tableWidget_medical_record.setItem(row_no, col_no, item)

            if col_no in [5, 6, 7, 9]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [2]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{start_date}至{end_date}{self.doctor}醫師免收藥品負擔統計表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_medical_record, [0],
            [4, 5, 6, 8],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>免收藥品負擔統計檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def print_list(self):
        pass
