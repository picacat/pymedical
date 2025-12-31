
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox, QFileDialog
import csv

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import charge_utils
from libs import export_utils
from libs import system_utils
from libs import date_utils
from libs import nhi_utils
from libs import printer_utils


# 掛號費優待統計 2020.02.10
class StatisticsInsDiscountRegistFee(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsInsDiscountRegistFee, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.doctor = args[4]
        self.first_course = args[5]
        self.only_discount = args[6]
        self.basic_regist_fee_discount = args[7]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_INS_DISCOUNT_REGIST_FEE, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_medical_record.set_column_hidden([0])

        self.table_widget_regist_fee_list = class_utils.get_table_widget(
            self.ui.tableWidget_regist_fee_list, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [
            100, 100, 120, 800,
        ]
        self.table_widget_regist_fee_list.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_medical_record.doubleClicked.connect(self.open_medical_record)
        self.ui.toolButton_export_to_csv.clicked.connect(self.export_to_csv)

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
        self._list_regist_fee()

    def _calculate_data(self):
        self._read_data()
        self._trim_null_rows()
        self._calculate_total()

    def _trim_null_rows(self):
        for row_no in range(self.ui.tableWidget_medical_record.rowCount(), -1, -1):
            item = self.ui.tableWidget_medical_record.item(row_no, 0)
            if item is None:
                self.ui.tableWidget_medical_record.removeRow(row_no)

    def _read_data(self):
        self.basic_regist_fee = number_utils.get_integer(charge_utils._get_basic_regist_fee(self.database, '健保'))
        old_man_age = self.system_settings.field('老人優待年齡')
        if old_man_age is None:
            old_man_age = 65

        doctor_condition = ''
        if self.doctor != '全部':
            doctor_condition = f' AND Doctor = "{self.doctor}"'

        course_condition = ''
        if self.first_course:
            course_condition = ' AND (Continuance IS NULL OR Continuance <= 1)'

        basic_regist_fee_condition = ''
        if self.basic_regist_fee_discount:
            basic_regist_fee_condition = f' OR (cases.Share = "基層醫療" AND RegistFee < {self.basic_regist_fee})'

        discount_condition = f''' AND
            ((patient.DiscountType IS NOT NULL AND LENGTH(patient.DiscountType) > 0) OR
            ((DATEDIFF(cases.CaseDate, patient.Birthday) / 365.25 >= {old_man_age}) AND
             (cases.Share = "基層醫療")) OR
            (patient.InsType IN ("榮民", "低收入戶"))
            {basic_regist_fee_condition}
            )
        '''
        # discount_condition = ''
        # if self.only_discount:
        #     discount_condition = f''' AND
        #         ((patient.DiscountType IS NOT NULL AND LENGTH(patient.DiscountType) > 0) OR
        #          ((DATEDIFF(cases.CaseDate, patient.Birthday) / 365.25 >= {old_man_age}) AND
        #           (cases.Share = "基層醫療")) OR
        #         (cases.Share IN ("榮民", "低收入戶") AND RegistFee < {self.basic_regist_fee}))
        #     '''

        sql = f'''
            SELECT
                CaseKey, CaseDate, Period, cases.Card, cases.Continuance, cases.InsType, cases.Share,
                TreatType, Doctor, Continuance, RegistFee,
                patient.PatientKey, patient.Name, patient.ID, patient.Birthday,
                patient.InsType,
                patient.Telephone, patient.Cellphone, patient.Address, patient.DiscountType
            FROM cases
                LEFT JOIN patient ON cases.PatientKey = patient.PatientKey
            WHERE
                DATE(cases.CaseDate) BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                cases.InsType = "健保"
                {course_condition}
                {discount_condition}
                {doctor_condition}
            ORDER BY CaseDate
        '''
        self.table_widget_medical_record.set_db_data(sql, self._set_table_data)

    def _get_basic_regist_fee(self, row):
        basic_regist_fee = self.basic_regist_fee

        # if self.basic_regist_fee_discount:
        #     return basic_regist_fee

        ins_type = string_utils.xstr(row['InsType'])
        share_type = string_utils.xstr(row['Share'])
        treat_type = string_utils.xstr(row['TreatType'])
        course_type = nhi_utils.get_course_type(number_utils.get_integer(row['Continuance']))

        sql = f'''
            SELECT * FROM charge_settings
            WHERE
                ChargeType = "掛號費" AND
                InsType = "{ins_type}" AND
                ShareType = "{share_type}"
        '''

        if '針' in treat_type:
            treat_type = '針灸治療'
        elif '傷科' in treat_type:
            treat_type = '傷科治療'
        elif '脫臼' in treat_type:
            treat_type = '傷科治療'
        elif '骨折' in treat_type:
            treat_type = '傷科治療'

        if ins_type == '健保':
            sql += f'''
                AND
                TreatType = "{treat_type}" AND
                Course = "{course_type}"
            '''

        rows = self.database.select_record(sql)
        if len(rows) > 0:
            amount_row = rows[0]
            basic_regist_fee = number_utils.get_integer(amount_row['Amount'])

        return basic_regist_fee

    def _set_table_data(self, row_no, row):
        basic_regist_fee = self._get_basic_regist_fee(row)
        # basic_regist_fee = charge_utils.get_regist_fee(
        #     self.database, self.system_settings,
        #     row['Birthday'],
        #     string_utils.xstr(row['DiscountType']),
        #     string_utils.xstr(row['InsType']),
        #     string_utils.xstr(row['Share']),
        #     string_utils.xstr(row['TreatType']),
        #     string_utils.xstr(row['Continuance']),
        # )

        regist_fee = number_utils.get_integer(row['RegistFee'])
        if basic_regist_fee - regist_fee <= 0:
            return

        if self.basic_regist_fee_discount:  # 2023-10-02 御漢堂
            if basic_regist_fee - regist_fee >= 150:
                basic_regist_fee = self.basic_regist_fee

        share = string_utils.xstr(row['Share'])
        discount_type = string_utils.xstr(row['DiscountType'])
        if discount_type == '':
            if share in ['榮民', '低收入戶']:
                discount_type = share
            else:
                age_year, _ = date_utils.get_age(row['Birthday'], row['CaseDate'])
                old_man_age = number_utils.get_integer(self.system_settings.field('老人優待年齡'))
                if number_utils.get_integer(age_year) >= old_man_age:
                    discount_type = '年長病患'

        case_date = date_utils.date_to_zh_tw_date(row['CaseDate'].date().strftime('%Y-%m-%d'))
        try:
            birthday = date_utils.date_to_zh_tw_date(row['Birthday'].strftime('%Y-%m-%d'))
        except Exception:
            birthday = None

        card = string_utils.xstr(row['Card'])
        course = number_utils.get_integer(row['Continuance'])
        if course >= 1:
            card = f'{card}-{course}'

        medical_record = [
            string_utils.xstr(row['CaseKey']),
            case_date,
            string_utils.xstr(row['Period']),
            discount_type,
            share,
            string_utils.xstr(row['TreatType']),
            card,
            basic_regist_fee,
            regist_fee,
            basic_regist_fee - regist_fee,
            string_utils.xstr(row['Doctor']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            birthday,
            string_utils.xstr(row['ID']),
            string_utils.xstr(row['Telephone']),
            string_utils.xstr(row['Cellphone']),
            string_utils.xstr(row['Address'])
        ]

        for col_no in range(len(medical_record)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medical_record[col_no])
            self.ui.tableWidget_medical_record.setItem(row_no, col_no, item)

            if col_no in [7, 8, 9, 11]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [2]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _calculate_total(self):
        regist_fee, receipt_regist_fee, discount_fee = 0, 0, 0
        total_case_count = 0

        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            total_case_count += 1
            regist_fee += number_utils.get_integer(
                self.ui.tableWidget_medical_record.item(row_no, 7).text()
            )
            receipt_regist_fee += number_utils.get_integer(
                self.ui.tableWidget_medical_record.item(row_no, 8).text()
            )
            discount_fee += number_utils.get_integer(
                self.ui.tableWidget_medical_record.item(row_no, 9).text()
            )

        self.ui.tableWidget_medical_record.setRowCount(total_case_count+1)
        row = [
            [5, f'合計{total_case_count}人次'],
            [6, '總計'],
            [7, regist_fee],
            [8, receipt_regist_fee],
            [9, discount_fee],
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

    def export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{start_date}至{end_date}{self.doctor}醫師掛號費優待統計表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_medical_record, [0],
            [7, 8, 9], title='掛號費優待統計表',
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>掛號費優待統計檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def export_to_csv(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        csv_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{start_date}至{end_date}優免掛號費優統計表.csv',
            "csv檔案 (*.csv)", options=options
        )
        if not csv_file_name:
            return

        # with open(csv_file_name, 'w', newline='', encoding='big5') as csv_file:
        with open(csv_file_name, 'w', newline='', encoding='utf-8-sig') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([
                '序號', '看診日期', '健保卡卡號', '姓名', '生日', '身分證字號', '住址', '電話', '優免原因', '優免金額'])

            i = 0
            for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
                try:
                    case_date = self.ui.tableWidget_medical_record.item(row_no, 1).text()
                    case_date = case_date.replace('-', '')
                except Exception:
                    continue

                i += 1
                card = ''

                try:
                    name = self.ui.tableWidget_medical_record.item(row_no, 12).text()
                except Exception:
                    name = ''

                try:
                    birthday = self.ui.tableWidget_medical_record.item(row_no, 13).text()
                    birthday = birthday.replace('-', '')
                except Exception:
                    birthday = ''

                try:
                    patient_id = self.ui.tableWidget_medical_record.item(row_no, 14).text()
                except Exception:
                    patient_id = ''

                try:
                    address = self.ui.tableWidget_medical_record.item(row_no, 17).text()
                except Exception:
                    address = ''

                try:
                    telephone = self.ui.tableWidget_medical_record.item(row_no, 15).text()
                except Exception:
                    telephone = ''

                if telephone == '':
                    try:
                        telephone = self.ui.tableWidget_medical_record.item(row_no, 16).text()
                    except Exception:
                        telephone = ''

                try:
                    discount_type = self.ui.tableWidget_medical_record.item(row_no, 3).text()
                except Exception:
                    discount_type = ''

                try:
                    discount_fee = self.ui.tableWidget_medical_record.item(row_no, 9).text()
                except Exception:
                    discount_fee = ''

                row = [
                    i, case_date, card, name, birthday, patient_id,
                    address, telephone, discount_type, discount_fee]

                try:
                    writer.writerow(row)
                except UnicodeEncodeError:
                    try:
                        xname = list(name)
                        xname[1] = '*'
                        xname = ''.join(xname)
                        row = [
                            i, case_date, card, xname, birthday, patient_id,
                            address, telephone, discount_type, discount_fee]
                        writer.writerow(row)
                    except UnicodeEncodeError:
                        try:
                            xname = list(name)
                            xname[2] = '*'
                            xname = ''.join(xname)
                            row = [
                                i, case_date, card, xname, birthday, patient_id,
                                address, telephone, discount_type, discount_fee]
                            writer.writerow(row)
                        except UnicodeEncodeError:
                            continue

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>優免掛號費統計檔{csv_file_name}匯出完成.</h3>',
            'CSV 格式.'
        )

    def print_list(self):
        printer_utils.print_regist_fee_discount(
            self.parent, self.database, self.system_settings,
            self.start_date, self.end_date, self.ui.tableWidget_medical_record)

    def _list_regist_fee(self):
        sql = f'''
            SELECT
                RegistFee
            FROM cases
            WHERE
                DATE(cases.CaseDate) BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                cases.InsType = "健保"
            GROUP BY RegistFee ORDER BY RegistFee
        '''
        rows = self.database.select_record(sql)

        self.ui.tableWidget_regist_fee_list.setRowCount(len(rows)+1)
        for row_no, row in enumerate(rows):
            regist_fee = number_utils.get_integer(row['RegistFee'])
            person_count, total_regist_Fee, discount_type = self._get_regist_fee_count(regist_fee)

            cell = [regist_fee, person_count, total_regist_Fee, discount_type]

            for col_no in range(len(cell)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, cell[col_no])
                self.ui.tableWidget_regist_fee_list.setItem(row_no, col_no, item)
                if col_no in [0, 1, 2]:
                    self.ui.tableWidget_regist_fee_list.item(row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                    )

    def _get_regist_fee_count(self, regist_fee):
        sql = f'''
            SELECT
                COUNT(CaseKey), SUM(RegistFee)
            FROM cases
            WHERE
                DATE(cases.CaseDate) BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                cases.InsType = "健保" AND
                RegistFee = {regist_fee}
            LIMIT 1
        '''

        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None, None

        row = rows[0]

        count = number_utils.get_integer(row['COUNT(CaseKey)'])
        amount = number_utils.get_integer(row['SUM(RegistFee)'])

        basic_regist_fee = number_utils.get_integer(charge_utils._get_basic_regist_fee(self.database, '健保'))

        if regist_fee >= basic_regist_fee:
            discount_list = '一般民眾'
        else:
            sql = f'SELECT ItemName FROM charge_settings WHERE ChargeType = "掛號費優待" AND Amount = {regist_fee}'
            rows = self.database.select_record(sql)

            discount_list = []
            for row in rows:
                discount_list.append(string_utils.xstr(row['ItemName']))

            discount_list = ', '.join(discount_list)

        if discount_list == '':
            discount_list = '一般民眾'

        return count, amount, discount_list
