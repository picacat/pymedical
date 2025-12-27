
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
import os.path
from lxml import etree as ET

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import nhi_utils
from libs import number_utils
from libs import xml_utils


# 申報金額核對 2018.12.17
class InsCheckApplyFee(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(InsCheckApplyFee, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = args[2]
        self.apply_month = args[3]
        self.start_date = args[4]
        self.end_date = args[5]
        self.period = args[6]
        self.apply_type = args[7]
        self.clinic_id = args[8]
        self.ins_generate_date = args[9]
        self.ins_total_fee = args[10]
        self.ui = None

        self.apply_date = nhi_utils.get_apply_date(self.apply_year, self.apply_month)
        self.apply_type_code = nhi_utils.APPLY_TYPE_CODE[self.apply_type]

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INS_CHECK_APPLY_FEE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.tableWidget_xml.setAlternatingRowColors(True)
        self.table_widget_error_message = class_utils.get_table_widget(
            self.ui.tableWidget_error_message, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [100, 100, 120, 800]
        self.table_widget_error_message.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        pass

    def _check_ins_apply_fee(self):
        self.ui.tableWidget_error_message.setRowCount(0)
        self.ui.tableWidget_xml.setRowCount(4)

        self._parse_ins_calculated_data()

        xml_file_name = nhi_utils.get_ins_xml_file_name(
            self.system_settings, self.apply_type_code, self.apply_date
        )
        if not os.path.isfile(xml_file_name):
            return

        tree = ET.parse(xml_file_name)

        root = tree.getroot()
        self._parse_tdata(root)
        self._parse_ddata(root)

        for row in range(self.ui.tableWidget_xml.rowCount()):
            for column in range(1, self.ui.tableWidget_xml.columnCount()):
                item = self.ui.tableWidget_xml.item(row, column)
                if item is not None:
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _parse_ins_calculated_data(self):
        row_no = 0
        self.ui.tableWidget_xml.setItem(
            row_no, 0, QtWidgets.QTableWidgetItem(string_utils.xstr('申報檔案'))
        )
        self.ui.tableWidget_xml.setItem(
            row_no, 1, QtWidgets.QTableWidgetItem(string_utils.xstr(
                self.ins_total_fee['total_count']))
        )
        self.ui.tableWidget_xml.setItem(
            row_no, 7, QtWidgets.QTableWidgetItem(string_utils.xstr(
                self.ins_total_fee['diag_share_amount']))
        )
        self.ui.tableWidget_xml.setItem(
            row_no, 8, QtWidgets.QTableWidgetItem(string_utils.xstr(
                self.ins_total_fee['drug_share_amount']))
        )
        self.ui.tableWidget_xml.setItem(
            row_no, 9, QtWidgets.QTableWidgetItem(string_utils.xstr(
                self.ins_total_fee['share_amount']))
        )
        self.ui.tableWidget_xml.setItem(
            row_no, 10, QtWidgets.QTableWidgetItem(string_utils.xstr(
                self.ins_total_fee['total_amount']))
        )

    def _parse_tdata(self, root):
        tdata = root.xpath('//outpatient/tdata')[0]

        tdata = xml_utils.convert_node_to_dict(tdata)
        total_count = number_utils.get_integer(tdata['t37'])
        total_fee = number_utils.get_integer(tdata['t38'])
        total_share_fee = number_utils.get_integer(tdata['t40'])

        row_no = 1
        self.ui.tableWidget_xml.setItem(
            row_no, 0, QtWidgets.QTableWidgetItem(string_utils.xstr('總表段'))
        )
        self.ui.tableWidget_xml.setItem(
            row_no, 1, QtWidgets.QTableWidgetItem(string_utils.xstr(total_count))
        )
        self.ui.tableWidget_xml.setItem(
            row_no, 9, QtWidgets.QTableWidgetItem(string_utils.xstr(total_share_fee))
        )
        self.ui.tableWidget_xml.setItem(
            row_no, 10, QtWidgets.QTableWidgetItem(string_utils.xstr(total_fee))
        )

    def _parse_ddata(self, root):

        dbody = root.xpath('//outpatient/ddata/dbody')

        ddata_fee = {
            'case_type': None,
            'sequence': None,
            'name': None,
            'total_count': 0,
            'diag_fee': 0,
            'drug_fee': 0,
            'pharmacy_fee': 0,
            'treat_fee': 0,
            'total_fee': 0,
            'diag_share_fee': 0,
            'drug_share_fee': 0,
            'share_fee': 0,
            'apply_fee': 0,
            'agent_fee': 0,
        }
        pdata_fee = {
            'total_count': 0,
            'diag_fee': 0,
            'drug_fee': 0,
            'pharmacy_fee': 0,
            'treat_fee': 0,
            'total_fee': 0,
            'diag_share_fee': 0,
            'drug_share_fee': 0,
            'share_fee': 0,
            'apply_fee': 0,
            'agent_fee': 0,
        }

        record_count = len(dbody)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在執行申報檔金額平衡檢查中, 請稍後...', '取消', 0, record_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for row_no, ddata in enumerate(dbody):
            progress_dialog.setValue(row_no)

            dhead = root.xpath('//outpatient/ddata/dhead')[row_no]
            dhead_data = xml_utils.convert_node_to_dict(dhead)

            ddata_fee['case_type'] = dhead_data['d1']
            ddata_fee['sequence'] = dhead_data['d2']
            ddata_fee['total_count'] += 1

            xdata = xml_utils.convert_node_to_dict(ddata)
            ddata_fee['name'] = xdata['d49']

            try:
                diag_fee = number_utils.get_integer(xdata['d36'])
            except KeyError:
                diag_fee = 0

            ddata_fee['diag_fee'] += diag_fee

            try:
                drug_fee = number_utils.get_integer(xdata['d32'])
            except KeyError:
                drug_fee = 0

            ddata_fee['drug_fee'] += drug_fee

            try:
                pharmacy_fee = number_utils.get_integer(xdata['d38'])
            except KeyError:
                pharmacy_fee = 0

            ddata_fee['pharmacy_fee'] += pharmacy_fee

            try:
                treat_fee = number_utils.get_integer(xdata['d33'])
            except KeyError:
                treat_fee = 0

            ddata_fee['treat_fee'] += treat_fee

            try:
                total_fee = number_utils.get_integer(xdata['d39'])
            except KeyError:
                total_fee = 0

            ddata_fee['total_fee'] += total_fee

            try:
                diag_share_fee = number_utils.get_integer(xdata['d57'])
            except KeyError:
                diag_share_fee = 0

            ddata_fee['diag_share_fee'] += diag_share_fee

            try:
                drug_share_fee = number_utils.get_integer(xdata['d58'])
            except KeyError:
                drug_share_fee = 0

            ddata_fee['drug_share_fee'] += drug_share_fee

            try:
                share_fee = number_utils.get_integer(xdata['d40'])
            except KeyError:
                share_fee = 0

            ddata_fee['share_fee'] += share_fee

            try:
                apply_fee = number_utils.get_integer(xdata['d41'])
            except KeyError:
                apply_fee = 0

            ddata_fee['apply_fee'] += apply_fee

            try:
                ddata_fee['agent_fee'] += number_utils.get_integer(xdata['d43'])
            except KeyError:
                pass

            error_message = []
            if (diag_fee + drug_fee + pharmacy_fee + treat_fee) != total_fee:
                error_message.append('申報合計不平衡: 自身加總有誤')
            if (total_fee - share_fee) != apply_fee:
                error_message.append('申報金額不平衡: 自身加總有誤')
            if (diag_share_fee + drug_share_fee) != share_fee:
                error_message.append('申報金額不平衡: 負擔金額自身加總有誤')

            if apply_fee <= 0:
                error_message.append('無申報金額')

            result = self._parse_pdata(ddata)
            if result['diag_fee'] != diag_fee:
                error_message.append(f"診察費不平衡, 清單段: {diag_fee}, 醫令段: {result['diag_fee']}")
            if result['drug_fee'] != drug_fee:
                error_message.append(f"藥費不平衡, 清單段: {drug_fee}, 醫令段: {result['drug_fee']}")
            if result['treat_fee'] != treat_fee:
                error_message.append(f"處置費不平衡, 清單段: {treat_fee}, 醫令段: {result['treat_fee']}")
            if result['pharmacy_fee'] != pharmacy_fee:
                error_message.append(f"調劑費不平衡, 清單段: {pharmacy_fee}, 醫令段: {result['pharmacy_fee']}")
            if result['treat_fee'] > 0 and result['treat_fee'] != result['total_treat_fee']:
                error_message.append(f"自身處置費金額不平衡, 處置費: {result['treat_fee']}, 合計: {result['total_treat_fee']}")

            if len(error_message) > 0:
                self.ui.tableWidget_error_message.setRowCount(self.ui.tableWidget_error_message.rowCount() + 1)
                data = [
                    ddata_fee['case_type'],
                    ddata_fee['sequence'],
                    ddata_fee['name'],
                    ', '.join(error_message),
                ]

                row_no = self.ui.tableWidget_error_message.rowCount() - 1
                for i in range(len(data)):
                    self.ui.tableWidget_error_message.setItem(
                        row_no, i, QtWidgets.QTableWidgetItem(string_utils.xstr(data[i]))
                    )

            pdata_fee['total_count'] += result['total_count']
            pdata_fee['diag_fee'] += result['diag_fee']
            pdata_fee['drug_fee'] += result['drug_fee']
            pdata_fee['pharmacy_fee'] += result['pharmacy_fee']
            pdata_fee['treat_fee'] += result['treat_fee']
            pdata_fee['total_fee'] += result['total_fee']
            pdata_fee['diag_share_fee'] += result['diag_share_fee']
            pdata_fee['drug_share_fee'] += result['drug_share_fee']
            pdata_fee['share_fee'] += result['share_fee']
            pdata_fee['apply_fee'] += result['apply_fee']
            pdata_fee['agent_fee'] += result['agent_fee']

        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()

        data = [
            '清單段',
            ddata_fee['total_count'],
            ddata_fee['diag_fee'],
            ddata_fee['drug_fee'],
            ddata_fee['pharmacy_fee'],
            ddata_fee['treat_fee'],
            ddata_fee['total_fee'],
            ddata_fee['diag_share_fee'],
            ddata_fee['drug_share_fee'],
            ddata_fee['share_fee'],
            ddata_fee['apply_fee'],
            ddata_fee['agent_fee'],
        ]

        row_no = 2
        for i in range(len(data)):
            self.ui.tableWidget_xml.setItem(
                row_no, i, QtWidgets.QTableWidgetItem(string_utils.xstr(data[i]))
            )

        data = [
            '醫令段',
            pdata_fee['total_count'],
            pdata_fee['diag_fee'],
            pdata_fee['drug_fee'],
            pdata_fee['pharmacy_fee'],
            pdata_fee['treat_fee'],
            pdata_fee['total_fee'],
            pdata_fee['diag_share_fee'],
            pdata_fee['drug_share_fee'],
            pdata_fee['share_fee'],
            pdata_fee['apply_fee'],
            pdata_fee['agent_fee'],
        ]

        row_no = 3
        for i in range(len(data)):
            self.ui.tableWidget_xml.setItem(
                row_no, i, QtWidgets.QTableWidgetItem(string_utils.xstr(data[i]))
            )

    def _parse_pdata(self, ddata):
        pdata = ddata.xpath('./pdata')

        pdata_fee = {
            'total_count': 0,
            'diag_fee': 0,
            'drug_fee': 0,
            'pharmacy_fee': 0,
            'treat_fee': 0,
            'total_treat_fee': 0,
            'total_fee': 0,
            'diag_share_fee': 0,
            'drug_share_fee': 0,
            'share_fee': 0,
            'apply_fee': 0,
            'agent_fee': 0,
        }
        for row in pdata:
            pdata_fee['total_count'] += 1

            xdata = xml_utils.convert_node_to_dict(row)

            try:
                percent = number_utils.get_integer(xdata['p8'])
            except Exception:
                percent = 100

            try:
                unit_price = number_utils.round_up(number_utils.get_integer(xdata['p11']) * percent / 100)
            except Exception:
                unit_price = 0

            try:
                total_dosage = number_utils.get_integer(xdata['p10'])
            except Exception:
                total_dosage = 1

            try:
                total_fee = number_utils.get_integer(xdata['p12'])
            except Exception:
                total_fee = 0

            if string_utils.xstr(xdata['p3']) == '0':
                pdata_fee['diag_fee'] += total_fee
            elif string_utils.xstr(xdata['p3']) == '1':
                pdata_fee['drug_fee'] += total_fee
            elif string_utils.xstr(xdata['p3']) == '2':
                pdata_fee['treat_fee'] += unit_price * total_dosage
                pdata_fee['total_treat_fee'] += total_fee
            elif string_utils.xstr(xdata['p3']) == '9':
                pdata_fee['pharmacy_fee'] += total_fee

        return pdata_fee
