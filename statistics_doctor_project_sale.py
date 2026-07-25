
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils
from libs import case_utils
from libs import nhi_utils
from libs import charge_utils
from libs import export_utils


# 醫師專案銷售業績統計 2019.11.04
class StatisticsDoctorProjectSale(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDoctorProjectSale, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.ins_type = args[5]
        self.doctor = args[6]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DOCTOR_PROJECT_SALE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_self_prescript = class_utils.get_table_widget(
            self.ui.tableWidget_self_prescript, self.database
        )
        self.table_widget_self_prescript.set_column_hidden([0])
        self._set_table_width()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [
            100,
            120, 50, 50, 70, 80, 50, 50,
            250, 50, 50, 90, 50, 90, 90,
            60, 90, 80, 110, 110,
            100,
        ]
        self.table_widget_self_prescript.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_self_prescript.doubleClicked.connect(self._open_medical_record)
        self.ui.toolButton_export_to_excel.clicked.connect(self._export_to_excel)

    def _open_medical_record(self):
        case_key = self.table_widget_self_prescript.field_value(0)
        if case_key is None:
            return

        self.parent.parent.open_medical_record(case_key)

    def start_calculate(self):
        self._read_medical_record()

    def _read_medical_record(self):
        sql = '''
            SELECT * FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                (TotalFee > 0 OR DiscountFee > 0)
        '''.format(
            start_date=self.start_date,
            end_date=self.end_date,
        )
        if self.period != '全部':
            sql += ' AND cases.ChargePeriod = "{0}"'.format(self.period)
        if self.ins_type != '全部':
            sql += ' AND cases.InsType = "{0}"'.format(self.ins_type)
        if self.doctor != '全部':
            sql += ' AND cases.Doctor = "{0}"'.format(self.doctor)

        sql += ' ORDER BY cases.CaseDate, FIELD(cases.Period, {0})'.format(
            string_utils.xstr(nhi_utils.PERIOD)[1:-1])

        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self._set_medical_record(rows)

    def _get_prescript_row_count(self, case_key):
        sql = '''
            SELECT * FROM prescript
                LEFT JOIN medicine ON prescript.MedicineKey = medicine.MedicineKey
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2 AND
                (prescript.Price > 0 OR prescript.Amount > 0) AND
                Project IS NOT NULL
            ORDER BY MedicineSet, PrescriptKey
        '''.format(
            case_key=case_key,
        )

        rows = self.database.select_record(sql)

        return len(rows)

    def _set_medical_record(self, rows):

        row_count = len(rows)
        self.progress_dialog = QtWidgets.QProgressDialog(
            '門診專案銷售資料統計中, 請稍後...', '取消', 0, row_count, self
        )

        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        self.progress_dialog.setValue(0)
        self.ui.tableWidget_self_prescript.setRowCount(0)
        row_no = 0
        for index, row in enumerate(rows):
            self.progress_dialog.setValue(index)

            case_key = row['CaseKey']
            doctor = string_utils.xstr(row['Doctor'])

            project_count = self._get_prescript_row_count(case_key)
            if project_count <= 0:
                continue

            self.ui.tableWidget_self_prescript.setRowCount(
                self.ui.tableWidget_self_prescript.rowCount() + 1
            )

            medical_record = [
                case_key,
                row['CaseDate'].strftime('%Y-%m-%d'),
                string_utils.xstr(row['Period']),
                row['Room'],
                row['PatientKey'],
                string_utils.xstr(row['Name']),
                string_utils.xstr(row['InsType']),
                None, None, None, None, None, None,
                None,
                None, None, None, None,
                doctor,
                string_utils.xstr(row['Cashier']),
            ]
            for col_no in range(len(medical_record)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, medical_record[col_no])
                self.ui.tableWidget_self_prescript.setItem(
                    row_no, col_no, item,
                )
                if col_no in [4, 13]:
                    self.ui.tableWidget_self_prescript.item(
                        row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                    )
                elif col_no in [2, 3, 6]:
                    self.ui.tableWidget_self_prescript.item(
                        row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                    )
                self.ui.tableWidget_self_prescript.item(
                    row_no, col_no).setBackground(
                    QtGui.QColor('lightgray')
                )
            row_no += self._read_prescript(case_key, row_no, doctor)
            row_no += 1

        self.progress_dialog.setValue(row_count)
        self.progress_dialog.deleteLater()

    '''
        醫師自費抽成算法
        1.折扣90%以上
          專案1成
          自費2成
          藥丸3成

        2.折扣80%~89%
          專案0.5成
          自費1成
          藥丸1.5成

        3.折扣79%~60%
          不抽成

        4.折扣59%以下
          醫師個人負擔成本

        5.折扣0%
          醫師個人負擔成本50%
    '''
    def _read_prescript(self, case_key, row_no, doctor):
        sql = '''
            SELECT * FROM prescript
                LEFT JOIN medicine ON prescript.MedicineKey = medicine.MedicineKey
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2 AND
                (prescript.Price > 0 OR prescript.Amount > 0) AND
                Project IS NOT NULL
            ORDER BY MedicineSet, PrescriptKey
        '''.format(
            case_key=case_key,
        )

        rows = self.database.select_record(sql)

        prescript_row_no = 0
        row_count = 0
        for row in rows:
            medicine_set = row['MedicineSet']
            pres_days = case_utils.get_pres_days(self.database, case_key, medicine_set)
            if pres_days <= 0:
                pres_days = 1

            dosage = number_utils.get_float(row['Dosage'])
            if dosage <= 0:
                dosage = 1

            price = number_utils.get_float(row['Price'])
            amount = number_utils.get_float(row['Amount'])
            if amount <= 0:
                amount = price * dosage

            subtotal = charge_utils.get_subtotal_fee(amount, pres_days)

            prescript_row_no += 1
            self.ui.tableWidget_self_prescript.setRowCount(
                self.ui.tableWidget_self_prescript.rowCount() + 1
            )

            discount_rate = case_utils.get_discount_rate(self.database, case_key, medicine_set)
            medicine_commission_rate = charge_utils.get_commission_rate(self.database, row['MedicineKey'], doctor)
            if discount_rate >= 90:
                commission_rate = 100
            elif 80 <= discount_rate < 90:
                commission_rate = 50
            elif 60 <= discount_rate < 80:
                commission_rate = 0
            else:
                commission_rate = discount_rate - 50

            if commission_rate > 0:
                medicine_rate = number_utils.get_integer(medicine_commission_rate.split('%')[0])
                commission_rate = commission_rate * medicine_rate / 100

            commission = number_utils.round_up(subtotal * commission_rate / 100)

            prescript_record = [
                case_key,
                None, None, None, None, None, None,
                medicine_set,
                string_utils.xstr(row['MedicineName']),
                dosage,
                string_utils.xstr(row['Unit']),
                '{0:.1f}'.format(price),
                pres_days,
                '{0:.1f}'.format(subtotal),
                medicine_commission_rate,
                '{0}%'.format(discount_rate),
                '{0}%'.format(commission_rate),
                commission,
                None, None,
            ]
            for col_no in range(len(prescript_record)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, prescript_record[col_no])
                self.ui.tableWidget_self_prescript.setItem(
                    row_no+prescript_row_no, col_no, item,
                )
                cell_item = self.ui.tableWidget_self_prescript.item(row_no + prescript_row_no, col_no)
                if col_no in [9, 11, 12, 13, 14, 15, 16, 17]:
                    if cell_item is not None:
                        cell_item.setTextAlignment(
                            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                        )
                elif col_no in [7, 10]:
                    if cell_item is not None:
                        cell_item.setTextAlignment(
                            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                        )
            row_count += 1

        return row_count

    def _export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{start_date}至{end_date}{self.doctor}專案產品銷售抽成統計表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_self_prescript, [0], [9, 11, 12, 13, 17]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>專案產品銷售抽成統計檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )
