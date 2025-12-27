# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui, QtChart
from PyQt5.QtWidgets import QFileDialog, QMessageBox

import os.path
from lxml import etree as ET

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import nhi_utils
from libs import number_utils
from libs import personnel_utils
from libs import export_utils
from libs import xml_utils
from libs import charge_utils


# 醫師申報金額業績 2019.08.01
class InsApplyFeePerformance(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(InsApplyFeePerformance, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = args[2]
        self.apply_month = args[3]
        self.doctor = args[4]
        self.start_date = args[5]
        self.end_date = args[6]
        self.period = args[7]
        self.apply_type = args[8]
        self.exclude_c5 = args[9]
        self.ui = None
        self.user_name = system_utils.get_user_name(self.system_settings)

        self.apply_date = nhi_utils.get_apply_date(self.apply_year, self.apply_month)
        self.apply_type_code = nhi_utils.APPLY_TYPE_CODE[self.apply_type]

        self.doctor_id = personnel_utils.get_person_field_value(
            self.database, self.doctor, 'ID')

        self._set_ui()
        self._set_signal()
        self._check_ins_apply_fee()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INS_APPLY_FEE_PERFORMANCE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.tableWidget_doctor_xml.setAlternatingRowColors(True)
        self.table_widget_doctor_xml = class_utils.get_table_widget(self.ui.tableWidget_doctor_xml, self.database)
        self.table_widget_case_xml = class_utils.get_table_widget(self.ui.tableWidget_case_xml, self.database)
        self.table_widget_nurse_list = class_utils.get_table_widget(self.ui.tableWidget_nurse_list, self.database)
        self.table_widget_special_fee = class_utils.get_table_widget(self.ui.tableWidget_special_fee, self.database)
        self._set_table_width()
        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.toolButton_export_doctor_excel.setEnabled(False)
            self.ui.toolButton_export_case_type_excel.setEnabled(False)

    def _set_table_width(self):
        width = [
            130, 100, 100, 100, 100, 100, 100, 100, 100, 150, 150
        ]
        self.table_widget_doctor_xml.set_table_heading_width(width)
        self.table_widget_case_xml.set_table_heading_width(width)
        self.table_widget_nurse_list.set_table_heading_width([130, 120, 120])
        self.table_widget_special_fee.set_table_heading_width([220, 120, 120])

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_doctor_excel.clicked.connect(self.export_doctor_to_excel)
        self.ui.toolButton_export_case_type_excel.clicked.connect(self.export_case_to_excel)

    def _check_ins_apply_fee(self):
        self._check_ins_apply_fee_doctor()
        if self.doctor == '全部':
            self._check_ins_apply_fee_case_type()
            self._check_ins_apply_fee_nurse()
            try:
                self._check_ins_apply_fee_special()
            except Exception:
                pass

        try:
            self._list_summary()
        except AttributeError:
            self.ui.tableWidget_summary.setVisible(False)

        self._plot_chart()

    def _check_ins_apply_fee_doctor(self):
        self.ui.tableWidget_doctor_xml.setRowCount(0)

        xml_file_name = nhi_utils.get_ins_xml_file_name(
            self.system_settings, self.apply_type_code, self.apply_date
        )
        if not os.path.isfile(xml_file_name):
            return

        tree = ET.parse(xml_file_name)

        root = tree.getroot()
        self._parse_doctor_ddata(root)
        self._calculate_ins_apply_fee_doctor()
        self.ui.tableWidget_doctor_xml.sortItems(7, QtCore.Qt.DescendingOrder)
        self._calculate_total(self.ui.tableWidget_doctor_xml)

        for row_no in range(self.ui.tableWidget_doctor_xml.rowCount()):
            for col_no in range(1, self.ui.tableWidget_doctor_xml.columnCount()):
                item = self.ui.tableWidget_doctor_xml.item(row_no, col_no)
                if item is not None:
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self._filter_doctor_data()

    def _filter_doctor_data(self):
        for row_no in range(self.ui.tableWidget_doctor_xml.rowCount()-1, -1, -1):
            current_doctor = self.ui.tableWidget_doctor_xml.item(row_no, 0).text()
            if self.doctor != '全部' and (current_doctor != self.doctor or current_doctor == '合計'):
                self.ui.tableWidget_doctor_xml.removeRow(row_no)

    def _calculate_ins_apply_fee_doctor(self):
        for row_no in range(self.ui.tableWidget_doctor_xml.rowCount()):
            doctor_item = self.ui.tableWidget_doctor_xml.item(row_no, 0)
            if doctor_item is None:
                doctor_name = '空白'
                total_fee, share_fee, ins_apply_fee = 0, 0, 0
            else:
                doctor_name = personnel_utils.person_id_to_name(self.database, doctor_item.text())

                total_fee = number_utils.get_integer(self.ui.tableWidget_doctor_xml.item(row_no, 6).text())
                share_fee = number_utils.get_integer(self.ui.tableWidget_doctor_xml.item(row_no, 7).text())
                ins_apply_fee = total_fee - share_fee

            data = [
                [0, doctor_name],
                [8, ins_apply_fee],
            ]

            for col_no in range(len(data)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, data[col_no][1])
                self.ui.tableWidget_doctor_xml.setItem(
                    row_no, data[col_no][0], item,
                )

    def _calculate_total(self, table_widget):
        row_count = table_widget.rowCount()

        table_widget.setRowCount(row_count+1)

        total_count = 0
        total_diag_fee = 0
        total_drug_fee = 0
        total_pharmacy_fee = 0
        total_treat_fee = 0
        total_ins_total_fee = 0
        total_share_fee = 0
        total_ins_apply_fee = 0
        for row_no in range(row_count):
            ord_item = table_widget.item(row_no, 1)
            if ord_item is None:
                continue

            ord_count = number_utils.get_integer(ord_item.text())
            diag_fee = number_utils.get_integer(table_widget.item(row_no, 2).text())
            drug_fee = number_utils.get_integer(table_widget.item(row_no, 3).text())
            pharmacy_fee = number_utils.get_integer(table_widget.item(row_no, 4).text())
            treat_fee = number_utils.get_integer(table_widget.item(row_no, 5).text())
            ins_total_fee = number_utils.get_integer(table_widget.item(row_no, 6).text())
            share_fee = number_utils.get_integer(table_widget.item(row_no, 7).text())
            ins_apply_fee = number_utils.get_integer(table_widget.item(row_no, 8).text())

            total_count += ord_count
            total_diag_fee += diag_fee
            total_drug_fee += drug_fee
            total_pharmacy_fee += pharmacy_fee
            total_treat_fee += treat_fee
            total_ins_total_fee += ins_total_fee
            total_share_fee += share_fee
            total_ins_apply_fee += ins_apply_fee

        data = [
            '合計',
            total_count,
            total_diag_fee,
            total_drug_fee,
            total_pharmacy_fee,
            total_treat_fee,
            total_ins_total_fee,
            total_share_fee,
            total_ins_apply_fee,
        ]

        for col_no in range(len(data)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, data[col_no])
            table_widget.setItem(row_count, col_no, item)

    def _get_cell_value(self, table_widget, row_no, col_no):
        item = table_widget.item(row_no, col_no)
        if item is None:
            return 0

        return number_utils.get_integer(item.text())

    def _parse_doctor_ddata(self, root):
        dhead = root.xpath('//outpatient/ddata/dhead')
        dbody = root.xpath('//outpatient/ddata/dbody')

        record_count = len(dbody)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在統計醫師申報業績, 請稍後...', '取消', 0, record_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for xml_row_no, hdata, ddata in zip(range(record_count), dhead, dbody):
            progress_dialog.setValue(xml_row_no)

            xhdata = xml_utils.convert_node_to_dict(hdata)
            case_type = xhdata['d1']
            if self.exclude_c5 and case_type == 'C5':
                continue

            self._parse_pdata(ddata, self.ui.tableWidget_doctor_xml)

            xdata = xml_utils.convert_node_to_dict(ddata)
            doctor_id = xdata['d30']

            table_widget_row_no = None
            for i in range(self.ui.tableWidget_doctor_xml.rowCount()):
                item = self.ui.tableWidget_doctor_xml.item(i, 0)
                if item is None:
                    break

                if item.text() == doctor_id:
                    table_widget_row_no = i
                    break

            if table_widget_row_no is None:
                table_widget_row_no = self.ui.tableWidget_doctor_xml.rowCount()
                self.ui.tableWidget_doctor_xml.setRowCount(table_widget_row_no+1)

            last_share_fee = self._get_cell_value(self.ui.tableWidget_doctor_xml, table_widget_row_no, 7)
            share_fee = number_utils.get_integer(xdata['d40']) + last_share_fee

            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, share_fee)
            self.ui.tableWidget_doctor_xml.setItem(
                table_widget_row_no, 7, item,
            )

        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()

    def _parse_pdata(self, ddata, table_widget):
        pdata = ddata.xpath('./pdata')

        for row in pdata:
            xdata = xml_utils.convert_node_to_dict(row)
            doctor_id = xdata['p16']

            table_widget_row_no = None
            for i in range(table_widget.rowCount()):
                item = table_widget.item(i, 0)
                if item is None:
                    break

                if item.text() == doctor_id:
                    table_widget_row_no = i
                    break

            if table_widget_row_no is None:
                table_widget_row_no = table_widget.rowCount()
                table_widget.setRowCount(table_widget_row_no+1)

            last_total_count = self._get_cell_value(table_widget, table_widget_row_no, 1)
            last_diag_fee = self._get_cell_value(table_widget, table_widget_row_no, 2)
            last_drug_fee = self._get_cell_value(table_widget, table_widget_row_no, 3)
            last_pharmacy_fee = self._get_cell_value(table_widget, table_widget_row_no, 4)
            last_treat_fee = self._get_cell_value(table_widget, table_widget_row_no, 5)
            last_total_fee = self._get_cell_value(table_widget, table_widget_row_no, 6)
            last_share_fee = self._get_cell_value(table_widget, table_widget_row_no, 7)
            last_apply_fee = self._get_cell_value(table_widget, table_widget_row_no, 8)
            last_new_patient_count = self._get_cell_value(table_widget, table_widget_row_no, 9)
            last_integrate_count = self._get_cell_value(table_widget, table_widget_row_no, 10)

            pdata_fee = {
                'total_count': last_total_count,
                'diag_fee': last_diag_fee,
                'drug_fee': last_drug_fee,
                'pharmacy_fee': last_pharmacy_fee,
                'treat_fee': last_treat_fee,
                'total_fee': last_total_fee,
                'share_fee': last_share_fee,
                'apply_fee': last_apply_fee,
                'new_patient_count': last_new_patient_count,
                'integrate_count': last_integrate_count,
            }
            try:
                price = number_utils.get_integer(xdata['p12'])
            except Exception:
                price = 0

            pdata_fee['total_count'] = last_total_count + 1
            if string_utils.xstr(xdata['p3']) == '0':
                pdata_fee['diag_fee'] = price + last_diag_fee
            elif string_utils.xstr(xdata['p3']) == '1':
                pdata_fee['drug_fee'] = price + last_drug_fee
            elif string_utils.xstr(xdata['p3']) == '2':
                pdata_fee['treat_fee'] = price + last_treat_fee
            elif string_utils.xstr(xdata['p3']) == '9':
                pdata_fee['pharmacy_fee'] = price + last_pharmacy_fee

            if string_utils.xstr(xdata['p4']) == 'A90':
                pdata_fee['new_patient_count'] = last_new_patient_count + 1
            elif string_utils.xstr(xdata['p4']) == 'A91':
                pdata_fee['integrate_count'] = last_integrate_count + 1

            pdata_fee['total_fee'] = (
                pdata_fee['diag_fee'] +
                pdata_fee['drug_fee'] +
                pdata_fee['treat_fee'] +
                pdata_fee['pharmacy_fee']
            )

            data = [
                doctor_id,
                pdata_fee['total_count'],
                pdata_fee['diag_fee'],
                pdata_fee['drug_fee'],
                pdata_fee['pharmacy_fee'],
                pdata_fee['treat_fee'],
                pdata_fee['total_fee'],
                pdata_fee['share_fee'],
                pdata_fee['apply_fee'],
                pdata_fee['new_patient_count'],
                pdata_fee['integrate_count'],
            ]

            for col_no in range(len(data)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, data[col_no])
                table_widget.setItem(
                    table_widget_row_no, col_no, item,
                )

    def _check_ins_apply_fee_case_type(self):
        self.ui.tableWidget_case_xml.setRowCount(0)

        xml_file_name = nhi_utils.get_ins_xml_file_name(
            self.system_settings, self.apply_type_code, self.apply_date
        )
        if not os.path.isfile(xml_file_name):
            return

        tree = ET.parse(xml_file_name)

        root = tree.getroot()
        self._parse_case_ddata(root)
        self._calculate_ins_apply_fee_case_type()
        self._calculate_total(self.ui.tableWidget_case_xml)

        for row in range(self.ui.tableWidget_case_xml.rowCount()):
            for column in range(1, self.ui.tableWidget_case_xml.columnCount()):
                item = self.ui.tableWidget_case_xml.item(row, column)
                if item is not None:
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _list_summary(self):
        patient_count = self._get_ins_apply_patient_count()
        period_count = self._get_period_count()
        try:
            period_patient_count = patient_count // period_count
        except ZeroDivisionError:
            period_patient_count = 0

        days = self._get_days()
        case_count = self._get_case_count()
        diag_count = self._get_ins_apply_diag_count()
        ins_apply_fee = self._get_ins_apply_fee()
        try:
            day_apply_fee = ins_apply_fee // days
        except ZeroDivisionError:
            day_apply_fee = 0

        row_data = [
            patient_count,
            period_count,
            period_patient_count,
            days,
            case_count,
            diag_count,
            ins_apply_fee,
            day_apply_fee,
        ]

        self.ui.tableWidget_summary.setRowCount(1)
        for col_no in range(len(row_data)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, row_data[col_no])

            self.ui.tableWidget_summary.setItem(0, col_no, item)
            self.ui.tableWidget_summary.item(
                0, col_no).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )

    def _get_total_row_no(self):
        table_widget_apply = self.parent.tab_ins_apply_calculated_data.tableWidget_ins_apply_data

        current_row_no = None
        for row_no in range(table_widget_apply.rowCount()):
            item = table_widget_apply.item(row_no, 0)
            if item is None:
                continue

            if item.text() == '合計':
                current_row_no = row_no
                break

        if current_row_no is None:
            return 0

        return current_row_no

    def _get_ins_apply_patient_count(self):
        current_row_no = self._get_total_row_no()
        if current_row_no is None:
            return 0

        table_widget_apply = self.parent.tab_ins_apply_calculated_data.tableWidget_ins_apply_data
        item = table_widget_apply.item(current_row_no, 4)
        try:
            patient_count = number_utils.get_integer(item.text())
        except AttributeError:
            patient_count = 0

        return patient_count

    def _get_ins_apply_diag_count(self):
        current_row_no = self._get_total_row_no()
        if current_row_no is None:
            return 0

        table_widget_apply = self.parent.tab_ins_apply_calculated_data.tableWidget_ins_apply_data
        item = table_widget_apply.item(current_row_no, 5)
        try:
            diag_count = number_utils.get_integer(item.text())
        except AttributeError:
            diag_count = 0

        return diag_count

    def _get_period_count(self):
        start_date = self.start_date.toString('yyyy-MM-dd 00:00:00')
        end_date = self.end_date.toString('yyyy-MM-dd 23:59:59')
        sql = f'''
            SELECT CaseKey, CaseDate, DATE(CaseDate) as case_date FROM cases
                LEFT JOIN person ON cases.Doctor = person.Name
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                InsType = "健保" AND
                ApplyType = "申報" AND
                Doctor IS NOT NULL AND LENGTH(Doctor) > 0 AND
                person.ID IS NOT NULL
            GROUP BY case_date, Period, Doctor
        '''
        rows = self.database.select_record(sql)

        return len(rows)

    def _get_days(self):
        start_date = self.start_date.toString('yyyy-MM-dd 00:00:00')
        end_date = self.end_date.toString('yyyy-MM-dd 23:59:59')
        sql = f'''
            SELECT CaseKey, DATE(CaseDate) as case_date FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                InsType = "健保" AND
                ApplyType = "申報"
            GROUP BY case_date
        '''
        rows = self.database.select_record(sql)

        return len(rows)

    def _get_case_count(self):
        table_widget_apply = self.ui.tableWidget_case_xml
        item = table_widget_apply.item(table_widget_apply.rowCount()-1, 1)
        try:
            case_count = number_utils.get_integer(item.text())
        except AttributeError:
            case_count = 0

        return case_count

    def _get_ins_apply_fee(self):
        table_widget_apply = self.ui.tableWidget_case_xml
        item = table_widget_apply.item(table_widget_apply.rowCount()-1, 8)
        try:
            ins_apply_fee = number_utils.get_integer(item.text())
        except AttributeError:
            ins_apply_fee = 0

        return ins_apply_fee

    def _parse_case_ddata(self, root):
        dhead = root.xpath('//outpatient/ddata/dhead')
        dbody = root.xpath('//outpatient/ddata/dbody')

        record_count = len(dbody)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在統計案件分類申報業績, 請稍後...', '取消', 0, record_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for xml_row_no, hdata, ddata in zip(range(record_count), dhead, dbody):
            progress_dialog.setValue(xml_row_no)

            xdata = xml_utils.convert_node_to_dict(ddata)
            xhdata = xml_utils.convert_node_to_dict(hdata)
            case_type = xhdata['d1']
            # if self.exclude_c5 and case_type == 'C5':
            #     continue

            if self.doctor != '全部':
                doctor_id = xdata['d30']
                if doctor_id != self.doctor_id:
                    continue

            self._parse_ddata(xdata, self.ui.tableWidget_case_xml, case_type)

        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()

    def _parse_ddata(self, ddata, table_widget, case_type):
        row_no = None
        for i in range(table_widget.rowCount()):
            item = table_widget.item(i, 0)
            if item is None:
                break

            if item.text() == case_type:
                row_no = i
                break

        if row_no is None:
            row_no = table_widget.rowCount()
            table_widget.setRowCount(row_no+1)

        last_total_count = self._get_cell_value(table_widget, row_no, 1)
        last_diag_fee = self._get_cell_value(table_widget, row_no, 2)
        last_drug_fee = self._get_cell_value(table_widget, row_no, 3)
        last_pharmacy_fee = self._get_cell_value(table_widget, row_no, 4)
        last_treat_fee = self._get_cell_value(table_widget, row_no, 5)
        last_total_fee = self._get_cell_value(table_widget, row_no, 6)
        last_share_fee = self._get_cell_value(table_widget, row_no, 7)
        last_apply_fee = self._get_cell_value(table_widget, row_no, 8)

        ddata_fee = {
            'total_count': last_total_count,
            'diag_fee': last_diag_fee,
            'drug_fee': last_drug_fee,
            'pharmacy_fee': last_pharmacy_fee,
            'treat_fee': last_treat_fee,
            'total_fee': last_total_fee,
            'share_fee': last_share_fee,
            'apply_fee': last_apply_fee,
        }

        ddata_fee['total_count'] += 1

        try:
            ddata_fee['diag_fee'] += number_utils.get_integer(ddata['d36'])
        except Exception:
            pass

        try:
            ddata_fee['drug_fee'] += number_utils.get_integer(ddata['d32'])
        except Exception:
            pass

        try:
            ddata_fee['pharmacy_fee'] += number_utils.get_integer(ddata['d38'])
        except Exception:
            pass

        try:
            ddata_fee['treat_fee'] += number_utils.get_integer(ddata['d33'])
        except Exception:
            pass

        try:
            ddata_fee['total_fee'] += number_utils.get_integer(ddata['d39'])
        except Exception:
            pass

        try:
            ddata_fee['share_fee'] += number_utils.get_integer(ddata['d40'])
        except Exception:
            pass

        try:
            ddata_fee['apply_fee'] += number_utils.get_integer(ddata['d41'])
        except Exception:
            pass

        data = [
            case_type,
            ddata_fee['total_count'],
            ddata_fee['diag_fee'],
            ddata_fee['drug_fee'],
            ddata_fee['pharmacy_fee'],
            ddata_fee['treat_fee'],
            ddata_fee['total_fee'],
            ddata_fee['share_fee'],
            ddata_fee['apply_fee'],
        ]

        for col_no in range(len(data)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, data[col_no])
            table_widget.setItem(
                row_no, col_no, item,
            )

    def _calculate_ins_apply_fee_case_type(self):
        for row_no in range(self.ui.tableWidget_case_xml.rowCount()):
            case_type_item = self.ui.tableWidget_case_xml.item(row_no, 0)
            if case_type_item is None:
                continue

            case_type_item = case_type_item.text()
            total_fee = number_utils.get_integer(self.ui.tableWidget_case_xml.item(row_no, 6).text())
            share_fee = number_utils.get_integer(self.ui.tableWidget_case_xml.item(row_no, 7).text())
            ins_apply_fee = total_fee - share_fee

            data = [
                [0, case_type_item],
                [8, ins_apply_fee],
            ]

            for col_no in range(len(data)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, data[col_no][1])
                self.ui.tableWidget_case_xml.setItem(
                    row_no, data[col_no][0], item,
                )

    def _get_period(self, case_key):
        sql = f'''
            SELECT Period FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return string_utils.xstr(rows[0]['Period'])

    def _get_nurse_fee(self, diag_code, case_date=None):
        if diag_code == 'A01':
            no_diag_code = 'A02'
        elif diag_code == 'A03':
            no_diag_code = 'A04'
        elif diag_code == 'A05':
            no_diag_code = 'A06'
        elif diag_code == 'A09':
            no_diag_code = 'A10'
        else:
            return 0

        diag_fee = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(self.database, diag_code, case_date=case_date)
        )
        no_diag_fee = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(self.database, no_diag_code, case_date=case_date)
        )

        return diag_fee - no_diag_fee

    def _check_ins_apply_fee_nurse(self):
        try:
            clinic_id = self.parent.clinic_id
        except AttributeError:
            clinic_id = self.system_settings.field('院所代號')

        sql = f'''
            SELECT * FROM insapply
            WHERE
                ClinicID = "{clinic_id}" AND
                ApplyDate = "{self.apply_date}" AND
                ApplyPeriod = "{self.period}" AND
                ApplyType = "{self.apply_type_code}" AND
                DiagCode IN ("A01", "A03", "A05", "A09")
        '''
        rows = self.database.select_record(sql)
        record_count = len(rows)
        if record_count <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            '正在統計跟診護理人員申報業績, 請稍後...', '取消', 0, record_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        nurse_dict = {}
        for row_no, row in enumerate(rows):
            progress_dialog.setValue(row_no)
            period = self._get_period(row['CaseKey1'])
            if period is None:
                continue

            case_date = row['CaseDate'].strftime('%Y-%m-%d')
            doctor_id = string_utils.xstr(row['DoctorID'])
            diag_code = string_utils.xstr(row['DiagCode'])
            doctor_name = personnel_utils.person_id_to_name(self.database, doctor_id)

            sql = f'''
                SELECT * FROM nurse_schedule
                WHERE
                    ScheduleDate = "{case_date}" AND
                    Doctor = "{doctor_name}"
            '''
            nurse_rows = self.database.select_record(sql)
            if len(nurse_rows) <= 0:
                continue

            nurse_row = nurse_rows[0]
            if period == '早班':
                nurse_field = 'Nurse1'
            elif period == '午班':
                nurse_field = 'Nurse2'
            elif period == '晚班':
                nurse_field = 'Nurse3'
            else:
                continue

            nurse = string_utils.xstr(nurse_row[nurse_field])
            if nurse not in nurse_dict:
                nurse_dict[nurse] = {}
                nurse_dict[nurse]['count'] = 0
                nurse_dict[nurse]['points'] = 0

            nurse_dict[nurse]['count'] += 1
            nurse_dict[nurse]['points'] += self._get_nurse_fee(diag_code, case_date=row['CaseDate'])

        self.ui.tableWidget_nurse_list.setRowCount(0)
        for row_no, nurse in enumerate(nurse_dict.keys()):
            self.ui.tableWidget_nurse_list.setRowCount(self.ui.tableWidget_nurse_list.rowCount()+1)

            nurse_data = [nurse, nurse_dict[nurse]['count'], nurse_dict[nurse]['points']]
            for col_no in range(len(nurse_data)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, nurse_data[col_no])
                self.ui.tableWidget_nurse_list.setItem(row_no, col_no, item)
                if col_no in [1, 2]:
                    self.ui.tableWidget_nurse_list.item(
                        row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                    )

        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()

    def _check_ins_apply_fee_special(self):
        treat_type_list = [
            '視訊門診', '法定傳染病通報隔離',
            '巡迴山地', '巡迴偏遠', '巡迴離島',
            '前往資源不足地區', '照護機構中醫照護',
            '矯正機關內門診',
        ]

        self.ui.tableWidget_special_fee.setRowCount(0)
        for treat_type in treat_type_list:
            self._check_special_ins_apply_fee(treat_type)

    def _check_special_ins_apply_fee(self, in_treat_type):
        try:
            clinic_id = self.parent.clinic_id
        except AttributeError:
            clinic_id = self.system_settings.field('院所代號')

        sql = f'''
            SELECT insapply.*, cases.RegistType, cases.TreatType FROM insapply
                LEFT JOIN cases ON insapply.CaseKey1 = cases.CaseKey
            WHERE
                ClinicID = "{clinic_id}" AND
                ApplyDate = "{self.apply_date}" AND
                ApplyPeriod = "{self.period}" AND
                insapply.ApplyType = "{self.apply_type_code}" AND
                CaseKey1 IS NOT NULL AND
                (RegistType = "{in_treat_type}" OR TreatType = "{in_treat_type}")
        '''
        rows = self.database.select_record(sql)
        record_count = len(rows)
        if record_count <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            '正在統計專案申報業績, 請稍後...', '取消', 0, record_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        count, points = 0, 0
        for row_no, row in enumerate(rows):
            progress_dialog.setValue(row_no)

            count += 1
            points += number_utils.get_integer(row['InsApplyFee'])

        current_row_no = self.ui.tableWidget_special_fee.rowCount()
        self.ui.tableWidget_special_fee.setRowCount(current_row_no + 1)

        row = [in_treat_type, count, points]
        for col_no in range(len(row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, row[col_no])
            self.ui.tableWidget_special_fee.setItem(current_row_no, col_no, item)
            if col_no in [1, 2]:
                self.ui.tableWidget_special_fee.item(current_row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()

    def export_doctor_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出醫師申報業績表",
            f'{self.apply_year}年{self.apply_month}月醫師申報業績表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        clinic_name = self.system_settings.field('院所名稱')
        year = self.apply_year
        month = self.apply_month
        title = f'{clinic_name} {year}年{month}月份醫師申報業績表'

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_doctor_xml, None, [1, 2, 3, 4, 5, 6, 7, 8], title
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>醫師申報業績表{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def export_case_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出案件分類申報業績表",
            f'{self.apply_year}年{self.apply_month}月案件分類申報業績表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        clinic_name = self.system_settings.field('院所名稱')
        year = self.apply_year
        month = self.apply_month
        title = f'{clinic_name} {year}年{month}月份案件分類申報業績表'

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_case_xml, None, [1, 2, 3, 4, 5, 6, 7, 8], title
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>案件分類申報業績表{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _plot_chart(self):
        self._plot_doctor_chart()
        self._plot_case_type_chart()

    def _plot_doctor_chart(self):
        series = QtChart.QPieSeries()
        for row_no in range(self.ui.tableWidget_doctor_xml.rowCount()-1):
            doctor_item = self.ui.tableWidget_doctor_xml.item(row_no, 0)
            if doctor_item is None:
                doctor_name = '空白'
                ins_apply_fee = 0
            else:
                doctor_name = doctor_item.text()
                ins_apply_fee = number_utils.get_integer(self.ui.tableWidget_doctor_xml.item(row_no, 8).text())

            series.append(doctor_name, ins_apply_fee)

            try:
                slice = series.slices()[row_no]
            except IndexError:
                return

            slice.setExploded()
            slice.setLabelVisible()

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle('醫師申報業績')
        chart.legend().hide()
        chart.setAnimationOptions(QtChart.QChart.AllAnimations)

        chartView = QtChart.QChartView(chart)
        chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        chartView.setFixedWidth(700)
        chartView.setFixedHeight(450)
        self.ui.verticalLayout_chart.addWidget(chartView)

    def _plot_case_type_chart(self):
        case_type_list = []
        bar_set = []
        series = QtChart.QBarSeries()
        for row_no in range(self.ui.tableWidget_case_xml.rowCount()-1):
            case_type = self.ui.tableWidget_case_xml.item(row_no, 0).text()
            ins_apply_fee = number_utils.get_integer(self.ui.tableWidget_case_xml.item(row_no, 8).text())

            case_type_list.append(case_type)
            bar_set.append(QtChart.QBarSet(case_type))
            bar_set[row_no] << ins_apply_fee
            series.append(bar_set[row_no])

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle('案件分類申報統計表')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ['申報金額']

        axis = QtChart.QBarCategoryAxis()
        axis.append(categories)
        chart.createDefaultAxes()
        chart.setAxisX(axis, series)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(QtCore.Qt.AlignBottom)

        chartView = QtChart.QChartView(chart)
        chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        chartView.setFixedWidth(700)
        self.ui.verticalLayout_chart.addWidget(chartView)
