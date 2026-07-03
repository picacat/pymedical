# -*- coding: UTF-8 -*-

import os.path

from lxml import etree as ET
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QTableWidgetItem

from libs import (
    class_utils,
    date_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    personnel_utils,
    string_utils,
    system_utils,
    ui_utils,
    xml_utils,
)


# 申報金額核對 2026.07.03
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
        self.dict_treat_count = {}

        self._set_ui()
        self._set_signal()
        self._check_ins_apply_fee()
        # self.print_highly_acupuncture_list()

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
        self.table_widget_treat_count = class_utils.get_table_widget(
            self.ui.tableWidget_treat_count, self.database
        )
        self.table_widget_error_message = class_utils.get_table_widget(
            self.ui.tableWidget_error_message, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [100, 100, 100, 100, 100, 100, 100, 100]
        self.table_widget_treat_count.set_table_heading_width(width)
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
        self._set_treat_data()

        for row in range(self.ui.tableWidget_xml.rowCount()):
            for column in range(1, self.ui.tableWidget_xml.columnCount()):
                item = self.ui.tableWidget_xml.item(row, column)
                if item is not None:
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _get_treat_categories(self, ins_code):
        """回傳這個代碼命中的所有分類（可能不只一個）"""
        categories = []

        # 針傷合併：F01~F68 全部，獨立計算，不影響其他判斷
        if ins_code in nhi_utils.MERGE_TREAT_CODE:  # F01~F68
            categories.append("針傷合併")

        # 針灸複雜性（各自獨立判斷，彼此互斥）
        if ins_code in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_CODE:  # D07,D08,F52-F68
            categories.append("高度複針")
        elif (
            ins_code in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_CODE
        ):  # D05,D06,F35-F51
            categories.append("中度複針")
        elif ins_code in ("D01", "D02"):
            categories.append("一般針灸")

        # 傷科複雜性（需要自訂清單，nhi_utils現有的清單不夠完整）
        HIGHLY_COMPLICATED_MASSAGE_FULL = nhi_utils.HIGHLY_COMPLICATED_MASSAGE_CODE + [
            "F06",
            "F09",
            "F12",
            "F15",
            "F23",
            "F26",
            "F29",
            "F32",
            "F40",
            "F43",
            "F46",
            "F49",
            "F57",
            "F60",
            "F63",
            "F66",
        ]
        MODERATE_COMPLICATED_MASSAGE_FULL = (
            nhi_utils.MODERATE_COMPLICATED_MASSAGE_CODE
            + [
                "F03",
                "F20",
                "F37",
                "F54",
            ]
        )

        if ins_code in HIGHLY_COMPLICATED_MASSAGE_FULL:
            categories.append("高度複傷")
        elif ins_code in MODERATE_COMPLICATED_MASSAGE_FULL:
            categories.append("中度複傷")
        elif ins_code in ("E01", "E02"):
            categories.append("一般傷科")

        return categories

    def _set_treat_data(self):
        column_map = {
            "一般針灸": 1,
            "中度複針": 2,
            "高度複針": 3,
            "一般傷科": 4,
            "中度複傷": 5,
            "高度複傷": 6,
            "針傷合併": 7,
        }

        table_widget = self.ui.tableWidget_treat_count
        doctor_count = len(self.dict_treat_count)
        table_widget.setRowCount(doctor_count + 1)

        grand_totals = {key: 0 for key in column_map}

        for row_no, (doctor_id, ins_counts) in enumerate(self.dict_treat_count.items()):
            doctor = personnel_utils.person_id_to_name(self.database, doctor_id)
            table_widget.setItem(row_no, 0, QTableWidgetItem(doctor))

            category_totals = {key: 0 for key in column_map}

            for ins_code, count in ins_counts.items():
                categories = self._get_treat_categories(
                    ins_code
                )  # 拿清單，可能不只一個
                for category in categories:
                    category_totals[category] += count

            for category, col_no in column_map.items():
                value = category_totals[category]
                grand_totals[category] += value

                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                table_widget.setItem(row_no, col_no, item)

        # ---- 合計列 ----
        total_row_no = doctor_count
        total_label_item = QTableWidgetItem("合計")
        total_label_item.setTextAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        total_label_item.setFont(font)
        table_widget.setItem(total_row_no, 0, total_label_item)

        for category, col_no in column_map.items():
            item = QTableWidgetItem(str(grand_totals[category]))
            item.setTextAlignment(Qt.AlignCenter)
            item.setFont(font)
            table_widget.setItem(total_row_no, col_no, item)

    def _parse_ins_calculated_data(self):
        row_no = 0
        self.ui.tableWidget_xml.setItem(
            row_no, 0, QtWidgets.QTableWidgetItem(string_utils.xstr("申報檔案"))
        )
        self.ui.tableWidget_xml.setItem(
            row_no,
            1,
            QtWidgets.QTableWidgetItem(
                string_utils.xstr(self.ins_total_fee["total_count"])
            ),
        )
        self.ui.tableWidget_xml.setItem(
            row_no,
            7,
            QtWidgets.QTableWidgetItem(
                string_utils.xstr(self.ins_total_fee["diag_share_amount"])
            ),
        )
        self.ui.tableWidget_xml.setItem(
            row_no,
            8,
            QtWidgets.QTableWidgetItem(
                string_utils.xstr(self.ins_total_fee["drug_share_amount"])
            ),
        )
        self.ui.tableWidget_xml.setItem(
            row_no,
            9,
            QtWidgets.QTableWidgetItem(
                string_utils.xstr(self.ins_total_fee["share_amount"])
            ),
        )
        self.ui.tableWidget_xml.setItem(
            row_no,
            10,
            QtWidgets.QTableWidgetItem(
                string_utils.xstr(self.ins_total_fee["total_amount"])
            ),
        )

    def _parse_tdata(self, root):
        tdata = root.xpath("//outpatient/tdata")[0]

        tdata = xml_utils.convert_node_to_dict(tdata)
        total_count = number_utils.get_integer(tdata["t37"])
        total_fee = number_utils.get_integer(tdata["t38"])
        total_share_fee = number_utils.get_integer(tdata["t40"])

        row_no = 1
        self.ui.tableWidget_xml.setItem(
            row_no, 0, QtWidgets.QTableWidgetItem(string_utils.xstr("總表段"))
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

        dbody = root.xpath("//outpatient/ddata/dbody")

        ddata_fee = {
            "case_type": None,
            "sequence": None,
            "name": None,
            "total_count": 0,
            "diag_fee": 0,
            "drug_fee": 0,
            "pharmacy_fee": 0,
            "treat_fee": 0,
            "total_fee": 0,
            "diag_share_fee": 0,
            "drug_share_fee": 0,
            "share_fee": 0,
            "apply_fee": 0,
            "agent_fee": 0,
        }
        pdata_fee = {
            "total_count": 0,
            "diag_fee": 0,
            "drug_fee": 0,
            "pharmacy_fee": 0,
            "treat_fee": 0,
            "total_fee": 0,
            "diag_share_fee": 0,
            "drug_share_fee": 0,
            "share_fee": 0,
            "apply_fee": 0,
            "agent_fee": 0,
        }

        record_count = len(dbody)
        progress_dialog = QtWidgets.QProgressDialog(
            "正在執行申報檔金額平衡檢查中, 請稍後...", "取消", 0, record_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for row_no, ddata in enumerate(dbody):
            progress_dialog.setValue(row_no)

            dhead = root.xpath("//outpatient/ddata/dhead")[row_no]
            dhead_data = xml_utils.convert_node_to_dict(dhead)

            ddata_fee["case_type"] = dhead_data["d1"]
            ddata_fee["sequence"] = dhead_data["d2"]
            ddata_fee["total_count"] += 1

            xdata = xml_utils.convert_node_to_dict(ddata)
            ddata_fee["name"] = xdata["d49"]

            try:
                diag_fee = number_utils.get_integer(xdata["d36"])
            except KeyError:
                diag_fee = 0

            ddata_fee["diag_fee"] += diag_fee

            try:
                drug_fee = number_utils.get_integer(xdata["d32"])
            except KeyError:
                drug_fee = 0

            ddata_fee["drug_fee"] += drug_fee

            try:
                pharmacy_fee = number_utils.get_integer(xdata["d38"])
            except KeyError:
                pharmacy_fee = 0

            ddata_fee["pharmacy_fee"] += pharmacy_fee

            try:
                treat_fee = number_utils.get_integer(xdata["d33"])
            except KeyError:
                treat_fee = 0

            ddata_fee["treat_fee"] += treat_fee

            try:
                total_fee = number_utils.get_integer(xdata["d39"])
            except KeyError:
                total_fee = 0

            ddata_fee["total_fee"] += total_fee

            try:
                diag_share_fee = number_utils.get_integer(xdata["d57"])
            except KeyError:
                diag_share_fee = 0

            ddata_fee["diag_share_fee"] += diag_share_fee

            try:
                drug_share_fee = number_utils.get_integer(xdata["d58"])
            except KeyError:
                drug_share_fee = 0

            ddata_fee["drug_share_fee"] += drug_share_fee

            try:
                share_fee = number_utils.get_integer(xdata["d40"])
            except KeyError:
                share_fee = 0

            ddata_fee["share_fee"] += share_fee

            try:
                apply_fee = number_utils.get_integer(xdata["d41"])
            except KeyError:
                apply_fee = 0

            ddata_fee["apply_fee"] += apply_fee

            try:
                ddata_fee["agent_fee"] += number_utils.get_integer(xdata["d43"])
            except KeyError:
                pass

            error_message = []
            if (diag_fee + drug_fee + pharmacy_fee + treat_fee) != total_fee:
                error_message.append("申報合計不平衡: 自身加總有誤")
            if (total_fee - share_fee) != apply_fee:
                error_message.append("申報金額不平衡: 自身加總有誤")
            if (diag_share_fee + drug_share_fee) != share_fee:
                error_message.append("申報金額不平衡: 負擔金額自身加總有誤")

            if apply_fee <= 0:
                error_message.append("無申報金額")

            result = self._parse_pdata(ddata, dhead_data["d1"])
            if result["diag_fee"] != diag_fee:
                error_message.append(
                    f"診察費不平衡, 清單段: {diag_fee}, 醫令段: {result['diag_fee']}"
                )
            if result["drug_fee"] != drug_fee:
                error_message.append(
                    f"藥費不平衡, 清單段: {drug_fee}, 醫令段: {result['drug_fee']}"
                )
            if result["treat_fee"] != treat_fee:
                error_message.append(
                    f"處置費不平衡, 清單段: {treat_fee}, 醫令段: {result['treat_fee']}"
                )
            if result["pharmacy_fee"] != pharmacy_fee:
                error_message.append(
                    f"調劑費不平衡, 清單段: {pharmacy_fee}, 醫令段: {result['pharmacy_fee']}"
                )
            if (
                result["treat_fee"] > 0
                and result["treat_fee"] != result["total_treat_fee"]
            ):
                error_message.append(
                    f"自身處置費金額不平衡, 處置費: {result['treat_fee']}, 合計: {result['total_treat_fee']}"
                )

            if len(error_message) > 0:
                self.ui.tableWidget_error_message.setRowCount(
                    self.ui.tableWidget_error_message.rowCount() + 1
                )
                data = [
                    ddata_fee["case_type"],
                    ddata_fee["sequence"],
                    ddata_fee["name"],
                    ", ".join(error_message),
                ]

                row_no = self.ui.tableWidget_error_message.rowCount() - 1
                for i in range(len(data)):
                    self.ui.tableWidget_error_message.setItem(
                        row_no,
                        i,
                        QtWidgets.QTableWidgetItem(string_utils.xstr(data[i])),
                    )

            pdata_fee["total_count"] += result["total_count"]
            pdata_fee["diag_fee"] += result["diag_fee"]
            pdata_fee["drug_fee"] += result["drug_fee"]
            pdata_fee["pharmacy_fee"] += result["pharmacy_fee"]
            pdata_fee["treat_fee"] += result["treat_fee"]
            pdata_fee["total_fee"] += result["total_fee"]
            pdata_fee["diag_share_fee"] += result["diag_share_fee"]
            pdata_fee["drug_share_fee"] += result["drug_share_fee"]
            pdata_fee["share_fee"] += result["share_fee"]
            pdata_fee["apply_fee"] += result["apply_fee"]
            pdata_fee["agent_fee"] += result["agent_fee"]

        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()

        data = [
            "清單段",
            ddata_fee["total_count"],
            ddata_fee["diag_fee"],
            ddata_fee["drug_fee"],
            ddata_fee["pharmacy_fee"],
            ddata_fee["treat_fee"],
            ddata_fee["total_fee"],
            ddata_fee["diag_share_fee"],
            ddata_fee["drug_share_fee"],
            ddata_fee["share_fee"],
            ddata_fee["apply_fee"],
            ddata_fee["agent_fee"],
        ]

        row_no = 2
        for i in range(len(data)):
            self.ui.tableWidget_xml.setItem(
                row_no, i, QtWidgets.QTableWidgetItem(string_utils.xstr(data[i]))
            )

        data = [
            "醫令段",
            pdata_fee["total_count"],
            pdata_fee["diag_fee"],
            pdata_fee["drug_fee"],
            pdata_fee["pharmacy_fee"],
            pdata_fee["treat_fee"],
            pdata_fee["total_fee"],
            pdata_fee["diag_share_fee"],
            pdata_fee["drug_share_fee"],
            pdata_fee["share_fee"],
            pdata_fee["apply_fee"],
            pdata_fee["agent_fee"],
        ]

        row_no = 3
        for i in range(len(data)):
            self.ui.tableWidget_xml.setItem(
                row_no, i, QtWidgets.QTableWidgetItem(string_utils.xstr(data[i]))
            )

    def _parse_pdata(self, ddata, case_type=None):
        pdata = ddata.xpath("./pdata")

        pdata_fee = {
            "total_count": 0,
            "diag_fee": 0,
            "drug_fee": 0,
            "pharmacy_fee": 0,
            "treat_fee": 0,
            "total_treat_fee": 0,
            "total_fee": 0,
            "diag_share_fee": 0,
            "drug_share_fee": 0,
            "share_fee": 0,
            "apply_fee": 0,
            "agent_fee": 0,
        }
        for row in pdata:
            pdata_fee["total_count"] += 1

            xdata = xml_utils.convert_node_to_dict(row)

            try:
                percent = number_utils.get_integer(xdata["p8"])
            except Exception:
                percent = 100

            try:
                unit_price = number_utils.round_up(
                    number_utils.get_integer(xdata["p11"]) * percent / 100
                )
            except Exception:
                unit_price = 0

            try:
                total_dosage = number_utils.get_integer(xdata["p10"])
            except Exception:
                total_dosage = 1

            try:
                total_fee = number_utils.get_integer(xdata["p12"])
            except Exception:
                total_fee = 0

            if string_utils.xstr(xdata["p3"]) == "0":
                pdata_fee["diag_fee"] += total_fee
            elif string_utils.xstr(xdata["p3"]) == "1":
                pdata_fee["drug_fee"] += total_fee
            elif string_utils.xstr(xdata["p3"]) == "2":
                pdata_fee["treat_fee"] += unit_price * total_dosage
                pdata_fee["total_treat_fee"] += total_fee
            elif string_utils.xstr(xdata["p3"]) == "9":
                pdata_fee["pharmacy_fee"] += total_fee

            ins_code = string_utils.xstr(xdata["p4"])
            if case_type == "29" and ins_code in nhi_utils.TREAT_ALL_CODE:
                doctor_id = string_utils.xstr(xdata["p16"])
                self.dict_treat_count.setdefault(doctor_id, {})
                self.dict_treat_count[doctor_id][ins_code] = (
                    self.dict_treat_count[doctor_id].get(ins_code, 0) + 1
                )

        return pdata_fee

    def print_highly_acupuncture_list(self):
        patients = self.list_highly_acupuncture_patients()
        i = 0
        for p in patients:
            if p["case_type"] != "29":
                continue

            i += 1
            case_date = date_utils.nhi_date_to_west_date(p["case_date"])
            patient_key = patient_utils.get_patient_key_by_id(
                self.database, p["patient_id"]
            )
            sql = f'''
                select DATE(CaseDate) as CaseDate, PatientKey, Name, Treatment from cases
                where
                    DATE(CaseDate) = "{case_date}" and
                    PatientKey = {patient_key} and
                    InsType = "健保"
            '''
            rows = self.database.select_record(sql)
            if not rows:
                continue

            row = rows[0]
            print(i, row["CaseDate"], row["PatientKey"], row["Name"], row["Treatment"])

    def list_highly_acupuncture_patients(self):
        """
        解析XML，列出所有屬於高度複針(D07,D08,F52-F68)的病人清單
        回傳 list of dict: [{id, name, doctor_id, ins_code, case_type, case_date}, ...]
        """
        xml_file_name = nhi_utils.get_ins_xml_file_name(
            self.system_settings, self.apply_type_code, self.apply_date
        )
        if not os.path.isfile(xml_file_name):
            return []

        tree = ET.parse(xml_file_name)
        root = tree.getroot()

        dbody_list = root.xpath("//outpatient/ddata/dbody")
        dhead_list = root.xpath("//outpatient/ddata/dhead")

        result = []

        for row_no, ddata in enumerate(dbody_list):
            dhead_data = xml_utils.convert_node_to_dict(dhead_list[row_no])
            case_type = dhead_data["d1"]

            xdata = xml_utils.convert_node_to_dict(ddata)
            patient_id = string_utils.xstr(xdata.get("d3"))  # 病人身份證

            pdata_list = ddata.xpath("./pdata")
            for pdata in pdata_list:
                p_xdata = xml_utils.convert_node_to_dict(pdata)
                ins_code = string_utils.xstr(p_xdata.get("p4"))

                if ins_code in ("D07", "D08") or (
                    ins_code.startswith("F")
                    and ins_code[1:].isdigit()
                    and 52 <= int(ins_code[1:]) <= 68
                ):
                    doctor_id = string_utils.xstr(p_xdata.get("p16"))
                    # 查病人姓名
                    sql = f'''
                            SELECT Name FROM patient
                            WHERE ID = "{patient_id}"
                            LIMIT 1
                        '''
                    rows = self.database.select_record(sql)
                    patient_name = (
                        string_utils.xstr(rows[0]["Name"])
                        if len(rows) > 0
                        else "(查無此人)"
                    )

                    # 查醫師姓名
                    doctor_name = personnel_utils.person_id_to_name(
                        self.database, doctor_id
                    )
                    case_date = string_utils.xstr(p_xdata.get("p14"))[
                        :7
                    ]  # 就醫日期(民國年格式)

                    result.append(
                        {
                            "case_type": case_type,
                            "patient_id": patient_id,
                            "patient_name": patient_name,
                            "doctor_id": doctor_id,
                            "doctor_name": doctor_name,
                            "ins_code": ins_code,
                            "case_date": case_date,
                        }
                    )

        return result
