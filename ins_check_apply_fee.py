# -*- coding: UTF-8 -*-
import datetime
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

# ---------------------------------------------------------------------------
# 常數表：改用 frozenset 並在模組載入時建立一次
# 原本寫在函式內，每次呼叫都重新組 list，而且 list 的 in 是線性搜尋
# ---------------------------------------------------------------------------
TREAT_ALL_CODE_SET = frozenset(nhi_utils.TREAT_ALL_CODE)
MERGE_TREAT_CODE_SET = frozenset(nhi_utils.MERGE_TREAT_CODE)

HIGHLY_COMPLICATED_ACUPUNCTURE_SET = frozenset(
    nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_CODE
)
MODERATE_COMPLICATED_ACUPUNCTURE_SET = frozenset(
    nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_CODE
)

# 傷科複雜性：nhi_utils 現有清單不夠完整，補上針傷合併碼中屬於複雜傷科的部分
HIGHLY_COMPLICATED_MASSAGE_SET = frozenset(
    list(nhi_utils.HIGHLY_COMPLICATED_MASSAGE_CODE)
    + [
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
)
MODERATE_COMPLICATED_MASSAGE_SET = frozenset(
    list(nhi_utils.MODERATE_COMPLICATED_MASSAGE_CODE)
    + [
        "F03",
        "F20",
        "F37",
        "F54",
    ]
)

GENERAL_ACUPUNCTURE_SET = frozenset(["D01", "D02"])
GENERAL_MASSAGE_SET = frozenset(["E01", "E02"])

# 高度複針（D07, D08, F52~F68）
HIGHLY_ACUPUNCTURE_LIST_SET = frozenset(
    ["D07", "D08"] + [f"F{i}" for i in range(52, 69)]
)

# 進度對話盒總共更新幾次（與資料筆數無關，成本固定）
# 每一列都更新會強制事件迴圈與重繪，資料量大時會明顯拖慢
PROGRESS_UPDATES = 100

# 進度對話盒延遲顯示的毫秒數
# Qt 預設是 4000：估計作業不到 4 秒就整個不顯示，速度變快後會看起來像沒反應
# 0 = 一定顯示；若不想讓小月份閃一下，可改成 500
PROGRESS_MINIMUM_DURATION = 0


# 申報金額核對 2026.07.03
class InsCheckApplyFee(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
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

        # 快取：避免同一個代碼/人員重複計算或重複查資料庫
        self._category_cache = {}
        self._person_name_cache = {}

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

    # -----------------------------------------------------------------------
    # XML 取值小工具：直接取直接子節點，不做整棵子樹的 dict 轉換
    # -----------------------------------------------------------------------
    @staticmethod
    def _text_of(node, tag):
        return node.findtext(tag, "") or ""

    @staticmethod
    def _int_of(node, tag, default=0):
        text = node.findtext(tag, "") or ""
        if text.strip() == "":
            return default

        return number_utils.get_integer(text)

    def _person_id_to_name(self, person_id):
        if person_id in self._person_name_cache:
            return self._person_name_cache[person_id]

        name = personnel_utils.person_id_to_name(self.database, person_id)
        self._person_name_cache[person_id] = name

        return name

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
        cached = self._category_cache.get(ins_code)
        if cached is not None:
            return cached

        categories = []

        # 針傷合併：F01~F68 全部，獨立計算，不影響其他判斷
        if ins_code in MERGE_TREAT_CODE_SET:
            categories.append("針傷合併")

        # 針灸複雜性（各自獨立判斷，彼此互斥）
        if ins_code in HIGHLY_COMPLICATED_ACUPUNCTURE_SET:  # D07, D08, F52~F68
            categories.append("高度複針")
        elif ins_code in MODERATE_COMPLICATED_ACUPUNCTURE_SET:  # D05, D06, F35~F51
            categories.append("中度複針")
        elif ins_code in GENERAL_ACUPUNCTURE_SET:  # D01, D02
            categories.append("一般針灸")

        # 傷科複雜性
        if ins_code in HIGHLY_COMPLICATED_MASSAGE_SET:
            categories.append("高度複傷")
        elif ins_code in MODERATE_COMPLICATED_MASSAGE_SET:
            categories.append("中度複傷")
        elif ins_code in GENERAL_MASSAGE_SET:  # E01, E02
            categories.append("一般傷科")

        self._category_cache[ins_code] = categories

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

        table_widget.setUpdatesEnabled(False)
        try:
            table_widget.setRowCount(doctor_count + 1)

            grand_totals = {key: 0 for key in column_map}
            bold_font = QFont()
            bold_font.setBold(True)

            for row_no, (doctor_id, ins_counts) in enumerate(
                self.dict_treat_count.items()
            ):
                doctor = self._person_id_to_name(doctor_id)
                table_widget.setItem(row_no, 0, QTableWidgetItem(doctor))

                category_totals = {key: 0 for key in column_map}
                for ins_code, count in ins_counts.items():
                    for category in self._get_treat_categories(ins_code):
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
            total_label_item.setFont(bold_font)
            table_widget.setItem(total_row_no, 0, total_label_item)

            for category, col_no in column_map.items():
                item = QTableWidgetItem(str(grand_totals[category]))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFont(bold_font)
                table_widget.setItem(total_row_no, col_no, item)
        finally:
            table_widget.setUpdatesEnabled(True)

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
        # 這兩個 xpath 原本寫在迴圈裡，每一列都會重新掃描整份 XML（O(N^2)）
        # 改成迴圈外各做一次
        dbody_list = root.xpath("//outpatient/ddata/dbody")
        dhead_list = root.xpath("//outpatient/ddata/dhead")

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
        error_rows = []

        record_count = len(dbody_list)
        progress_dialog, progress_step = ui_utils.get_progress_dialog(
            self, "正在執行申報檔金額平衡檢查中, 請稍後...", record_count
        )

        try:
            for row_no, ddata in enumerate(dbody_list):
                if row_no % progress_step == 0:
                    progress_dialog.setValue(row_no)
                    if progress_dialog.wasCanceled():
                        break

                if row_no >= len(dhead_list):
                    break

                dhead = dhead_list[row_no]
                case_type = self._text_of(dhead, "d1")

                ddata_fee["case_type"] = case_type
                ddata_fee["sequence"] = self._text_of(dhead, "d2")
                ddata_fee["total_count"] += 1
                ddata_fee["name"] = self._text_of(ddata, "d49")

                diag_fee = self._int_of(ddata, "d36")
                drug_fee = self._int_of(ddata, "d32")
                pharmacy_fee = self._int_of(ddata, "d38")
                treat_fee = self._int_of(ddata, "d33")
                total_fee = self._int_of(ddata, "d39")
                diag_share_fee = self._int_of(ddata, "d57")
                drug_share_fee = self._int_of(ddata, "d58")
                share_fee = self._int_of(ddata, "d40")
                apply_fee = self._int_of(ddata, "d41")
                agent_fee = self._int_of(ddata, "d43")

                ddata_fee["diag_fee"] += diag_fee
                ddata_fee["drug_fee"] += drug_fee
                ddata_fee["pharmacy_fee"] += pharmacy_fee
                ddata_fee["treat_fee"] += treat_fee
                ddata_fee["total_fee"] += total_fee
                ddata_fee["diag_share_fee"] += diag_share_fee
                ddata_fee["drug_share_fee"] += drug_share_fee
                ddata_fee["share_fee"] += share_fee
                ddata_fee["apply_fee"] += apply_fee
                ddata_fee["agent_fee"] += agent_fee

                error_message = []
                if (diag_fee + drug_fee + pharmacy_fee + treat_fee) != total_fee:
                    error_message.append("申報合計不平衡: 自身加總有誤")

                if (total_fee - share_fee) != apply_fee:
                    error_message.append("申報金額不平衡: 自身加總有誤")

                if (diag_share_fee + drug_share_fee) != share_fee:
                    error_message.append("申報金額不平衡: 負擔金額自身加總有誤")

                if apply_fee <= 0:
                    error_message.append("無申報金額")

                result = self._parse_pdata(ddata, case_type)

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
                        f"調劑費不平衡, 清單段: {pharmacy_fee}, "
                        f"醫令段: {result['pharmacy_fee']}"
                    )

                if (
                    result["treat_fee"] > 0
                    and result["treat_fee"] != result["total_treat_fee"]
                ):
                    error_message.append(
                        f"自身處置費金額不平衡, 處置費: {result['treat_fee']}, "
                        f"合計: {result['total_treat_fee']}"
                    )

                if len(error_message) > 0:
                    error_rows.append(
                        [
                            ddata_fee["case_type"],
                            ddata_fee["sequence"],
                            ddata_fee["name"],
                            ", ".join(error_message),
                        ]
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
        finally:  # 中途出錯時對話盒也要收掉, 否則會留在畫面上關不掉
            progress_dialog.deleteLater()

        self._set_error_message(error_rows)

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

    def _set_error_message(self, error_rows):
        """錯誤清單一次填入，避免逐列 setRowCount 重新配置"""
        table_widget = self.ui.tableWidget_error_message

        table_widget.setUpdatesEnabled(False)
        try:
            table_widget.setRowCount(len(error_rows))
            for row_no, row_data in enumerate(error_rows):
                for col_no, value in enumerate(row_data):
                    table_widget.setItem(
                        row_no,
                        col_no,
                        QtWidgets.QTableWidgetItem(string_utils.xstr(value)),
                    )
        finally:
            table_widget.setUpdatesEnabled(True)

    def _parse_pdata(self, ddata, case_type=None):
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

        count_treat = case_type == "29"

        for row in ddata.findall("pdata"):
            pdata_fee["total_count"] += 1

            percent = self._int_of(row, "p8", 100)
            unit_price = number_utils.round_up(self._int_of(row, "p11") * percent / 100)
            total_dosage = self._int_of(row, "p10", 1)
            total_fee = self._int_of(row, "p12")
            pay_type = self._text_of(row, "p3")

            if pay_type == "0":
                pdata_fee["diag_fee"] += total_fee
            elif pay_type == "1":
                pdata_fee["drug_fee"] += total_fee
            elif pay_type == "2":
                pdata_fee["treat_fee"] += unit_price * total_dosage
                pdata_fee["total_treat_fee"] += total_fee
            elif pay_type == "9":
                pdata_fee["pharmacy_fee"] += total_fee

            if count_treat:
                ins_code = self._text_of(row, "p4")
                if ins_code in TREAT_ALL_CODE_SET:
                    doctor_id = self._text_of(row, "p16")
                    doctor_counts = self.dict_treat_count.setdefault(doctor_id, {})
                    doctor_counts[ins_code] = doctor_counts.get(ins_code, 0) + 1

        return pdata_fee

    def print_highly_acupuncture_list(self):
        patients = self.list_highly_acupuncture_patients()

        i = 0
        for p in patients:
            if p["case_type"] != "29":
                continue

            i += 1
            case_date = date_utils.nhi_date_to_west_date(p["case_date"])
            case_date = self._to_date(case_date)
            if case_date is None:
                continue

            next_date = case_date + datetime.timedelta(days=1)
            patient_key = patient_utils.get_patient_key_by_id(
                self.database, p["patient_id"]
            )

            # 原本用 DATE(CaseDate) = "..."，欄位包在函式裡會讓索引失效
            # 改為半開區間
            sql = f'''
                SELECT DATE(CaseDate) AS CaseDate, PatientKey, Name, Treatment
                FROM cases
                WHERE
                    CaseDate >= "{case_date}" AND
                    CaseDate < "{next_date}" AND
                    PatientKey = {patient_key} AND
                    InsType = "健保"
            '''
            rows = self.database.select_record(sql)
            if not rows:
                continue

            row = rows[0]
            print(i, row["CaseDate"], row["PatientKey"], row["Name"], row["Treatment"])

    @staticmethod
    def _to_date(value):
        if value is None:
            return None

        if isinstance(value, datetime.datetime):
            return value.date()

        if isinstance(value, datetime.date):
            return value

        text = string_utils.xstr(value)[:10]
        try:
            return datetime.datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None

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
        patient_id_set = set()

        for row_no, ddata in enumerate(dbody_list):
            if row_no >= len(dhead_list):
                break

            case_type = self._text_of(dhead_list[row_no], "d1")
            patient_id = self._text_of(ddata, "d3")  # 病人身份證

            for pdata in ddata.findall("pdata"):
                ins_code = self._text_of(pdata, "p4")
                if ins_code not in HIGHLY_ACUPUNCTURE_LIST_SET:
                    continue

                doctor_id = self._text_of(pdata, "p16")
                case_date = self._text_of(pdata, "p14")[:7]  # 就醫日期(民國年格式)

                patient_id_set.add(patient_id)
                result.append(
                    {
                        "case_type": case_type,
                        "patient_id": patient_id,
                        "patient_name": None,
                        "doctor_id": doctor_id,
                        "doctor_name": None,
                        "ins_code": ins_code,
                        "case_date": case_date,
                    }
                )

        # 病人姓名一次查回來，取代原本每一筆各查一次（N+1）
        patient_names = self._get_patient_names(patient_id_set)
        for item in result:
            item["patient_name"] = patient_names.get(item["patient_id"], "(查無此人)")
            item["doctor_name"] = self._person_id_to_name(item["doctor_id"])

        return result

    def _get_patient_names(self, patient_id_set):
        patient_names = {}
        id_list = [pid for pid in patient_id_set if pid]
        if not id_list:
            return patient_names

        # 分批查詢，避免 SQL 過長
        batch_size = 500
        for start in range(0, len(id_list), batch_size):
            batch = id_list[start : start + batch_size]
            in_values = ", ".join([f'"{pid}"' for pid in batch])
            sql = f"""
                SELECT ID, Name FROM patient
                WHERE ID IN ({in_values})
            """
            rows = self.database.select_record(sql)
            for row in rows:
                patient_names[string_utils.xstr(row["ID"])] = string_utils.xstr(
                    row["Name"]
                )

        return patient_names
