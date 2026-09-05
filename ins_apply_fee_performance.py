# -*- coding: UTF-8 -*-

import os.path

from lxml import etree as ET
from PyQt5 import QtChart, QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (
    charge_utils,
    class_utils,
    export_utils,
    nhi_utils,
    number_utils,
    personnel_utils,
    string_utils,
    system_utils,
    ui_utils,
    xml_utils,  # noqa: F401  保留匯入，避免其他模組相依中斷
)

# 進度對話盒最多更新幾次（資料量再大也不會被重繪拖慢）
PROGRESS_UPDATES = 100

# 進度對話盒延遲顯示的毫秒數
# Qt 預設 4000：作業不到 4 秒就整個不顯示，速度變快後看起來像沒反應
# 0 = 一定顯示；若不想讓小月份閃一下，可改成 500
PROGRESS_MINIMUM_DURATION = 0

# IN (...) 一次帶幾個值
CHUNK_SIZE = 500

# 跟診護理費：有護士 / 沒護士的診察費代碼配對
NURSE_DIAG_CODE_PAIR = {
    "A01": "A02",
    "A03": "A04",
    "A05": "A06",
    "A09": "A10",
}

SPECIAL_TREAT_TYPE = [
    "視訊門診",
    "法定傳染病通報隔離",
    "巡迴山地",
    "巡迴偏遠",
    "巡迴離島",
    "前往資源不足地區",
    "照護機構中醫照護",
    "矯正機關內門診",
]


# 醫師申報金額業績 2026-09-05
class InsApplyFeePerformance(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)

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
            self.database, self.doctor, "ID"
        )

        # ---- 快取 ----
        self._xml_loaded = False
        self._xml_root = None
        self._person_name_cache = {}
        self._nurse_fee_cache = {}
        self._clinic_id = None
        # 醫師業績表最後一列是不是「合計」（篩選單一醫師時會被刪掉）
        self._doctor_total_row = False

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

        self.table_widget_doctor_xml = class_utils.get_table_widget(
            self.ui.tableWidget_doctor_xml, self.database
        )
        self.table_widget_case_xml = class_utils.get_table_widget(
            self.ui.tableWidget_case_xml, self.database
        )
        self.table_widget_nurse_list = class_utils.get_table_widget(
            self.ui.tableWidget_nurse_list, self.database
        )
        self.table_widget_special_fee = class_utils.get_table_widget(
            self.ui.tableWidget_special_fee, self.database
        )

        self._set_table_width()

        if (
            personnel_utils.get_permission(
                self.database, "系統作業", "關閉匯出功能", self.user_name
            )
            == "Y"
        ):
            self.ui.toolButton_export_doctor_excel.setEnabled(False)
            self.ui.toolButton_export_case_type_excel.setEnabled(False)

    def _set_table_width(self):
        width = [130, 100, 100, 100, 100, 100, 100, 100, 100, 150, 150]
        self.table_widget_doctor_xml.set_table_heading_width(width)
        self.table_widget_case_xml.set_table_heading_width(width)
        self.table_widget_nurse_list.set_table_heading_width([130, 120, 120])
        self.table_widget_special_fee.set_table_heading_width([220, 120, 120])

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_doctor_excel.clicked.connect(
            self.export_doctor_to_excel
        )
        self.ui.toolButton_export_case_type_excel.clicked.connect(
            self.export_case_to_excel
        )

    # -----------------------------------------------------------------------
    # 共用小工具
    # -----------------------------------------------------------------------
    def _get_progress_dialog(self, message, record_count, cancel_text="取消"):
        """建立進度對話盒，回傳 (dialog, step)。

        step: 每隔幾列才呼叫一次 setValue，讓更新次數固定在 PROGRESS_UPDATES 次
              左右——資料量再大也不會被重繪拖慢，資料量小也還是會動。
        """
        dialog = QtWidgets.QProgressDialog(message, cancel_text, 0, record_count, self)
        dialog.setWindowModality(QtCore.Qt.WindowModal)
        dialog.setMinimumDuration(PROGRESS_MINIMUM_DURATION)
        dialog.setValue(0)
        dialog.show()
        QtWidgets.QApplication.processEvents()

        return dialog, max(1, record_count // PROGRESS_UPDATES)

    @staticmethod
    def _chunks(values, size=CHUNK_SIZE):
        values = list(values)
        for i in range(0, len(values), size):
            yield values[i : i + size]

    @staticmethod
    def _text_of(node, tag):
        """取直接子節點的字串，不做整棵子樹的 dict 轉換。"""
        if node is None:
            return ""

        return node.findtext(tag, "") or ""

    @staticmethod
    def _int_of(node, tag, default=0):
        if node is None:
            return default

        text = node.findtext(tag, "") or ""
        if text.strip() == "":
            return default

        return number_utils.get_integer(text)

    @staticmethod
    def _date_text(value):
        """把 DATE / DATETIME / 字串統一成 yyyy-MM-dd。"""
        if value is None:
            return ""

        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d")

        return string_utils.xstr(value)[:10]

    def _get_clinic_id(self):
        if self._clinic_id is None:
            try:
                self._clinic_id = self.parent.clinic_id
            except AttributeError:
                self._clinic_id = self.system_settings.field("院所代號")

        return self._clinic_id

    def _person_id_to_name(self, person_id):
        if person_id in self._person_name_cache:
            return self._person_name_cache[person_id]

        name = personnel_utils.person_id_to_name(self.database, person_id)
        self._person_name_cache[person_id] = name

        return name

    @staticmethod
    def _set_row(table_widget, row_no, data, start_col=0):
        """一次把一整列寫進表格；data 內為 None 的欄位不建立 item。"""
        for offset, value in enumerate(data):
            if value is None:
                continue

            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, value)
            table_widget.setItem(row_no, start_col + offset, item)

    @staticmethod
    def _align_right(table_widget, first_col=1):
        for row_no in range(table_widget.rowCount()):
            for col_no in range(first_col, table_widget.columnCount()):
                item = table_widget.item(row_no, col_no)
                if item is not None:
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    # -----------------------------------------------------------------------
    # XML：整份檔案只 parse 一次
    # -----------------------------------------------------------------------
    def _load_xml_root(self):
        if self._xml_loaded:
            return self._xml_root

        self._xml_loaded = True

        xml_file_name = nhi_utils.get_ins_xml_file_name(
            self.system_settings, self.apply_type_code, self.apply_date
        )
        if not os.path.isfile(xml_file_name):
            return None

        self._xml_root = ET.parse(xml_file_name).getroot()

        return self._xml_root

    @staticmethod
    def _iter_ddata(root):
        """回傳 [(dhead, dbody), ...]，沒有 dbody 的略過。"""
        # 申報 XML 的根節點就是 <outpatient>，ddata 是它的直接子節點；
        # 萬一外面又包了一層，再退回去用 descendant 找一次
        ddata_nodes = root.findall("ddata")
        if not ddata_nodes:
            ddata_nodes = root.findall(".//outpatient/ddata")

        ddata_list = []
        for ddata in ddata_nodes:
            dbody = ddata.find("dbody")
            if dbody is None:
                continue

            ddata_list.append((ddata.find("dhead"), dbody))

        return ddata_list

    # -----------------------------------------------------------------------
    def _check_ins_apply_fee(self):
        self._check_ins_apply_fee_doctor()

        if self.doctor == "全部":
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

    # -----------------------------------------------------------------------
    # 醫師申報業績
    # -----------------------------------------------------------------------
    def _check_ins_apply_fee_doctor(self):
        table_widget = self.ui.tableWidget_doctor_xml
        table_widget.setRowCount(0)
        self._doctor_total_row = False

        root = self._load_xml_root()
        if root is None:
            return

        doctor_data = self._collect_doctor_data(root)
        self._list_doctor_data(doctor_data)

        table_widget.sortItems(7, QtCore.Qt.DescendingOrder)
        self._calculate_total(table_widget)
        self._doctor_total_row = True

        self._align_right(table_widget)
        self._filter_doctor_data()

    def _collect_doctor_data(self, root):
        """把 XML 一次掃完，累加在 dict 裡（不再拿 QTableWidget 當累加器）。

        口徑與原程式相同：
            醫令（pdata）掛在 p16（執行的醫事人員），
            部分負擔（d40）掛在 d30（診治醫師）。
        """
        ddata_list = self._iter_ddata(root)
        record_count = len(ddata_list)

        doctor_data = {}

        def bucket(doctor_id):
            data = doctor_data.get(doctor_id)
            if data is None:
                data = {
                    "has_pdata": False,
                    "total_count": 0,
                    "diag_fee": 0,
                    "drug_fee": 0,
                    "pharmacy_fee": 0,
                    "treat_fee": 0,
                    "share_fee": 0,
                    "new_patient_count": 0,
                    "integrate_count": 0,
                }
                doctor_data[doctor_id] = data

            return data

        progress_dialog, progress_step = self._get_progress_dialog(
            "正在統計醫師申報業績, 請稍後...", record_count
        )

        try:
            for row_no, (dhead, dbody) in enumerate(ddata_list):
                if row_no % progress_step == 0:
                    progress_dialog.setValue(row_no)
                    if progress_dialog.wasCanceled():
                        break

                case_type = self._text_of(dhead, "d1")
                if self.exclude_c5 and case_type == "C5":
                    continue

                for pdata in dbody.findall("pdata"):
                    data = bucket(self._text_of(pdata, "p16"))
                    data["has_pdata"] = True
                    data["total_count"] += 1

                    price = self._int_of(pdata, "p12")
                    order_type = self._text_of(pdata, "p3")
                    if order_type == "0":
                        data["diag_fee"] += price
                    elif order_type == "1":
                        data["drug_fee"] += price
                    elif order_type == "2":
                        data["treat_fee"] += price
                    elif order_type == "9":
                        data["pharmacy_fee"] += price

                    ins_code = self._text_of(pdata, "p4")
                    if ins_code == "A90":
                        data["new_patient_count"] += 1
                    elif ins_code == "A91":
                        data["integrate_count"] += 1

                bucket(self._text_of(dbody, "d30"))["share_fee"] += self._int_of(
                    dbody, "d40"
                )

            progress_dialog.setValue(record_count)
        finally:
            progress_dialog.deleteLater()

        return doctor_data

    def _list_doctor_data(self, doctor_data):
        """把累加結果一次寫進表格（每位醫師只寫一次）。"""
        table_widget = self.ui.tableWidget_doctor_xml
        table_widget.setRowCount(len(doctor_data))

        for row_no, (doctor_id, data) in enumerate(doctor_data.items()):
            if not data["has_pdata"]:
                # 只出現在 d30、從未出現在任何 p16 的醫事人員：
                # 維持原程式的行為——顯示「空白」、申報金額 0、不計入合計
                self._set_row(table_widget, row_no, ["空白"])
                self._set_row(table_widget, row_no, [data["share_fee"], 0], 7)
                continue

            total_fee = (
                data["diag_fee"]
                + data["drug_fee"]
                + data["treat_fee"]
                + data["pharmacy_fee"]
            )
            self._set_row(
                table_widget,
                row_no,
                [
                    self._person_id_to_name(doctor_id),
                    data["total_count"],
                    data["diag_fee"],
                    data["drug_fee"],
                    data["pharmacy_fee"],
                    data["treat_fee"],
                    total_fee,
                    data["share_fee"],
                    total_fee - data["share_fee"],
                    data["new_patient_count"],
                    data["integrate_count"],
                ],
            )

    def _filter_doctor_data(self):
        if self.doctor == "全部":
            return

        table_widget = self.ui.tableWidget_doctor_xml
        for row_no in range(table_widget.rowCount() - 1, -1, -1):
            item = table_widget.item(row_no, 0)
            current_doctor = "" if item is None else item.text()
            if current_doctor != self.doctor or current_doctor == "合計":
                table_widget.removeRow(row_no)

        # 合計列已經被刪掉了，畫圓餅圖時不能再扣一列
        self._doctor_total_row = False

    def _calculate_total(self, table_widget):
        row_count = table_widget.rowCount()
        table_widget.setRowCount(row_count + 1)

        total = [0] * 8
        for row_no in range(row_count):
            if table_widget.item(row_no, 1) is None:
                continue

            for index in range(8):
                total[index] += self._get_cell_value(table_widget, row_no, index + 1)

        self._set_row(table_widget, row_count, ["合計"] + total)

    def _get_cell_value(self, table_widget, row_no, col_no):
        item = table_widget.item(row_no, col_no)
        if item is None:
            return 0

        return number_utils.get_integer(item.text())

    # -----------------------------------------------------------------------
    # 案件分類申報業績
    # -----------------------------------------------------------------------
    def _check_ins_apply_fee_case_type(self):
        table_widget = self.ui.tableWidget_case_xml
        table_widget.setRowCount(0)

        root = self._load_xml_root()
        if root is None:
            return

        case_type_data = self._collect_case_type_data(root)
        self._list_case_type_data(case_type_data)

        self._calculate_total(table_widget)
        self._align_right(table_widget)

    def _collect_case_type_data(self, root):
        ddata_list = self._iter_ddata(root)
        record_count = len(ddata_list)

        case_type_data = {}
        filter_doctor = self.doctor != "全部"

        progress_dialog, progress_step = self._get_progress_dialog(
            "正在統計案件分類申報業績, 請稍後...", record_count
        )

        try:
            for row_no, (dhead, dbody) in enumerate(ddata_list):
                if row_no % progress_step == 0:
                    progress_dialog.setValue(row_no)
                    if progress_dialog.wasCanceled():
                        break

                # 註：原程式在此並未套用 exclude_c5（該行是註解掉的），維持不變
                if filter_doctor and self._text_of(dbody, "d30") != self.doctor_id:
                    continue

                case_type = self._text_of(dhead, "d1")
                data = case_type_data.get(case_type)
                if data is None:
                    data = {
                        "total_count": 0,
                        "diag_fee": 0,
                        "drug_fee": 0,
                        "pharmacy_fee": 0,
                        "treat_fee": 0,
                        "total_fee": 0,
                        "share_fee": 0,
                    }
                    case_type_data[case_type] = data

                data["total_count"] += 1
                data["diag_fee"] += self._int_of(dbody, "d36")
                data["drug_fee"] += self._int_of(dbody, "d32")
                data["pharmacy_fee"] += self._int_of(dbody, "d38")
                data["treat_fee"] += self._int_of(dbody, "d33")
                data["total_fee"] += self._int_of(dbody, "d39")
                data["share_fee"] += self._int_of(dbody, "d40")

            progress_dialog.setValue(record_count)
        finally:
            progress_dialog.deleteLater()

        return case_type_data

    def _list_case_type_data(self, case_type_data):
        table_widget = self.ui.tableWidget_case_xml
        table_widget.setRowCount(len(case_type_data))

        for row_no, (case_type, data) in enumerate(case_type_data.items()):
            self._set_row(
                table_widget,
                row_no,
                [
                    case_type,
                    data["total_count"],
                    data["diag_fee"],
                    data["drug_fee"],
                    data["pharmacy_fee"],
                    data["treat_fee"],
                    data["total_fee"],
                    data["share_fee"],
                    data["total_fee"] - data["share_fee"],
                ],
            )

    # -----------------------------------------------------------------------
    # 摘要
    # -----------------------------------------------------------------------
    def _list_summary(self):
        total_row_no = self._get_total_row_no()

        patient_count = self._get_apply_data_value(total_row_no, 4)
        diag_count = self._get_apply_data_value(total_row_no, 5)

        period_count = self._get_period_count()
        try:
            period_patient_count = patient_count // period_count
        except ZeroDivisionError:
            period_patient_count = 0

        days = self._get_days()
        case_count = self._get_case_count()
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
        self._set_row(self.ui.tableWidget_summary, 0, row_data)
        self._align_right(self.ui.tableWidget_summary, first_col=0)

    def _get_total_row_no(self):
        table_widget_apply = (
            self.parent.tab_ins_apply_calculated_data.tableWidget_ins_apply_data
        )

        for row_no in range(table_widget_apply.rowCount()):
            item = table_widget_apply.item(row_no, 0)
            if item is None:
                continue

            if item.text() == "合計":
                return row_no

        # 找不到合計列就回 None，不要退回第 0 列（那是某一位醫師的資料）
        return None

    def _get_apply_data_value(self, row_no, col_no):
        if row_no is None:
            return 0

        table_widget_apply = (
            self.parent.tab_ins_apply_calculated_data.tableWidget_ins_apply_data
        )
        item = table_widget_apply.item(row_no, col_no)
        if item is None:
            return 0

        return number_utils.get_integer(item.text())

    def _get_period_count(self):
        start_date = self.start_date.toString("yyyy-MM-dd 00:00:00")
        end_date = self.end_date.toString("yyyy-MM-dd 23:59:59")

        sql = f'''
            SELECT COUNT(*) AS record_count FROM (
                SELECT DATE(CaseDate) AS case_date FROM cases
                    LEFT JOIN person ON cases.Doctor = person.Name
                WHERE
                    CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                    InsType = "健保" AND
                    ApplyType = "申報" AND
                    Doctor IS NOT NULL AND LENGTH(Doctor) > 0 AND
                    person.ID IS NOT NULL
                GROUP BY case_date, Period, Doctor
            ) AS period_list
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return 0

        return number_utils.get_integer(rows[0]["record_count"])

    def _get_days(self):
        start_date = self.start_date.toString("yyyy-MM-dd 00:00:00")
        end_date = self.end_date.toString("yyyy-MM-dd 23:59:59")

        sql = f'''
            SELECT COUNT(DISTINCT DATE(CaseDate)) AS record_count FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                InsType = "健保" AND
                ApplyType = "申報"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return 0

        return number_utils.get_integer(rows[0]["record_count"])

    def _get_case_count(self):
        table_widget = self.ui.tableWidget_case_xml

        return self._get_cell_value(table_widget, table_widget.rowCount() - 1, 1)

    def _get_ins_apply_fee(self):
        table_widget = self.ui.tableWidget_case_xml

        return self._get_cell_value(table_widget, table_widget.rowCount() - 1, 8)

    # -----------------------------------------------------------------------
    # 跟診護理人員
    # -----------------------------------------------------------------------
    def _get_nurse_fee(self, diag_code, case_date=None):
        no_diag_code = NURSE_DIAG_CODE_PAIR.get(diag_code)
        if no_diag_code is None:
            return 0

        cache_key = (diag_code, self._date_text(case_date))
        if cache_key in self._nurse_fee_cache:
            return self._nurse_fee_cache[cache_key]

        diag_fee = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(
                self.database, diag_code, case_date=case_date
            )
        )
        no_diag_fee = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(
                self.database, no_diag_code, case_date=case_date
            )
        )

        nurse_fee = diag_fee - no_diag_fee
        self._nurse_fee_cache[cache_key] = nurse_fee

        return nurse_fee

    def _get_case_period_map(self, case_keys):
        period_map = {}

        keys = sorted(
            {
                number_utils.get_integer(case_key)
                for case_key in case_keys
                if number_utils.get_integer(case_key) > 0
            }
        )
        for chunk in self._chunks(keys):
            in_list = ", ".join(str(key) for key in chunk)
            sql = f"""
                SELECT CaseKey, Period FROM cases
                WHERE
                    CaseKey IN ({in_list})
            """
            for row in self.database.select_record(sql):
                period_map[number_utils.get_integer(row["CaseKey"])] = (
                    string_utils.xstr(row["Period"])
                )

        return period_map

    def _get_nurse_schedule_map(self, case_dates):
        """回傳 {(yyyy-MM-dd, 醫師姓名): nurse_schedule 列}。"""
        schedule_map = {}

        dates = sorted({date_text for date_text in case_dates if date_text})
        for chunk in self._chunks(dates):
            in_list = ", ".join(f'"{date_text}"' for date_text in chunk)
            sql = f"""
                SELECT ScheduleDate, Doctor, Nurse1, Nurse2, Nurse3
                FROM nurse_schedule
                WHERE
                    ScheduleDate IN ({in_list})
            """
            for row in self.database.select_record(sql):
                key = (
                    self._date_text(row["ScheduleDate"]),
                    string_utils.xstr(row["Doctor"]).strip(),
                )
                # 原程式取 rows[0]；同日同醫師有重複列時一樣只取第一筆
                if key not in schedule_map:
                    schedule_map[key] = row

        return schedule_map

    def _check_ins_apply_fee_nurse(self):
        self.ui.tableWidget_nurse_list.setRowCount(0)

        diag_code_list = '", "'.join(NURSE_DIAG_CODE_PAIR.keys())
        sql = f'''
            SELECT CaseKey1, CaseDate, DoctorID, DiagCode FROM insapply
            WHERE
                ClinicID = "{self._get_clinic_id()}" AND
                ApplyDate = "{self.apply_date}" AND
                ApplyPeriod = "{self.period}" AND
                ApplyType = "{self.apply_type_code}" AND
                DiagCode IN ("{diag_code_list}")
        '''
        rows = self.database.select_record(sql)
        record_count = len(rows)
        if record_count <= 0:
            return

        progress_dialog, progress_step = self._get_progress_dialog(
            "正在統計跟診護理人員申報業績, 請稍後...", record_count
        )

        nurse_dict = {}
        nurse_field_dict = {"早班": "Nurse1", "午班": "Nurse2", "晚班": "Nurse3"}

        try:
            # 先把 cases.Period 與 nurse_schedule 整批撈回來，避免每列 5 次查詢
            period_map = self._get_case_period_map(row["CaseKey1"] for row in rows)
            schedule_map = self._get_nurse_schedule_map(
                self._date_text(row["CaseDate"]) for row in rows
            )

            for row_no, row in enumerate(rows):
                if row_no % progress_step == 0:
                    progress_dialog.setValue(row_no)
                    if progress_dialog.wasCanceled():
                        break

                period = period_map.get(number_utils.get_integer(row["CaseKey1"]))
                if period is None:
                    continue

                nurse_field = nurse_field_dict.get(period)
                if nurse_field is None:
                    continue

                case_date = self._date_text(row["CaseDate"])
                doctor_name = self._person_id_to_name(
                    string_utils.xstr(row["DoctorID"])
                )

                nurse_row = schedule_map.get((case_date, doctor_name.strip()))
                if nurse_row is None:
                    continue

                nurse = string_utils.xstr(nurse_row[nurse_field]).strip()
                if nurse == "":
                    # 該時段沒有排跟診護理人員，不要產生一列空白姓名
                    continue

                nurse_data = nurse_dict.get(nurse)
                if nurse_data is None:
                    nurse_data = {"count": 0, "points": 0}
                    nurse_dict[nurse] = nurse_data

                nurse_data["count"] += 1
                nurse_data["points"] += self._get_nurse_fee(
                    string_utils.xstr(row["DiagCode"]), case_date=row["CaseDate"]
                )

            progress_dialog.setValue(record_count)
        finally:
            progress_dialog.deleteLater()

        table_widget = self.ui.tableWidget_nurse_list
        table_widget.setRowCount(len(nurse_dict))
        for row_no, (nurse, nurse_data) in enumerate(nurse_dict.items()):
            self._set_row(
                table_widget,
                row_no,
                [nurse, nurse_data["count"], nurse_data["points"]],
            )

        self._align_right(table_widget)

    # -----------------------------------------------------------------------
    # 專案申報業績
    # -----------------------------------------------------------------------
    def _check_ins_apply_fee_special(self):
        self.ui.tableWidget_special_fee.setRowCount(0)

        treat_type_list = '", "'.join(SPECIAL_TREAT_TYPE)
        sql = f'''
            SELECT insapply.InsApplyFee, cases.RegistType, cases.TreatType
            FROM insapply
                LEFT JOIN cases ON insapply.CaseKey1 = cases.CaseKey
            WHERE
                insapply.ClinicID = "{self._get_clinic_id()}" AND
                insapply.ApplyDate = "{self.apply_date}" AND
                insapply.ApplyPeriod = "{self.period}" AND
                insapply.ApplyType = "{self.apply_type_code}" AND
                insapply.CaseKey1 IS NOT NULL AND
                (
                    cases.RegistType IN ("{treat_type_list}") OR
                    cases.TreatType IN ("{treat_type_list}")
                )
        '''
        rows = self.database.select_record(sql)
        record_count = len(rows)
        if record_count <= 0:
            return

        progress_dialog, progress_step = self._get_progress_dialog(
            "正在統計專案申報業績, 請稍後...", record_count
        )

        special_data = {}

        try:
            for row_no, row in enumerate(rows):
                if row_no % progress_step == 0:
                    progress_dialog.setValue(row_no)
                    if progress_dialog.wasCanceled():
                        break

                ins_apply_fee = number_utils.get_integer(row["InsApplyFee"])
                # 一筆同時符合掛號別與治療別時，兩邊都要計入（與原程式相同）
                for treat_type in {
                    string_utils.xstr(row["RegistType"]),
                    string_utils.xstr(row["TreatType"]),
                }:
                    if treat_type not in SPECIAL_TREAT_TYPE:
                        continue

                    data = special_data.get(treat_type)
                    if data is None:
                        data = {"count": 0, "points": 0}
                        special_data[treat_type] = data

                    data["count"] += 1
                    data["points"] += ins_apply_fee

            progress_dialog.setValue(record_count)
        finally:
            progress_dialog.deleteLater()

        table_widget = self.ui.tableWidget_special_fee
        # 依 SPECIAL_TREAT_TYPE 的順序列出，沒有資料的治療別不列（與原程式相同）
        listed = [
            treat_type
            for treat_type in SPECIAL_TREAT_TYPE
            if treat_type in special_data
        ]
        table_widget.setRowCount(len(listed))
        for row_no, treat_type in enumerate(listed):
            data = special_data[treat_type]
            self._set_row(
                table_widget, row_no, [treat_type, data["count"], data["points"]]
            )

        self._align_right(table_widget)

    # -----------------------------------------------------------------------
    # 匯出
    # -----------------------------------------------------------------------
    def export_doctor_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出醫師申報業績表",
            f"{self.apply_year}年{self.apply_month}月醫師申報業績表.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        clinic_name = self.system_settings.field("院所名稱")
        title = f"{clinic_name} {self.apply_year}年{self.apply_month}月份醫師申報業績表"

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_doctor_xml,
            None,
            [1, 2, 3, 4, 5, 6, 7, 8],
            title,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>醫師申報業績表{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def export_case_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出案件分類申報業績表",
            f"{self.apply_year}年{self.apply_month}月案件分類申報業績表.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        clinic_name = self.system_settings.field("院所名稱")
        title = (
            f"{clinic_name} {self.apply_year}年{self.apply_month}月份案件分類申報業績表"
        )

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_case_xml,
            None,
            [1, 2, 3, 4, 5, 6, 7, 8],
            title,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>案件分類申報業績表{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    # -----------------------------------------------------------------------
    # 圖表
    # -----------------------------------------------------------------------
    def _plot_chart(self):
        self._plot_doctor_chart()
        self._plot_case_type_chart()

    def _plot_doctor_chart(self):
        table_widget = self.ui.tableWidget_doctor_xml
        row_count = table_widget.rowCount()
        if self._doctor_total_row:
            row_count -= 1

        series = QtChart.QPieSeries()
        for row_no in range(row_count):
            doctor_item = table_widget.item(row_no, 0)
            if doctor_item is None:
                doctor_name = "空白"
                ins_apply_fee = 0
            else:
                doctor_name = doctor_item.text()
                ins_apply_fee = self._get_cell_value(table_widget, row_no, 8)

            series.append(doctor_name, ins_apply_fee)
            try:
                pie_slice = series.slices()[row_no]
            except IndexError:
                return

            pie_slice.setExploded()
            pie_slice.setLabelVisible()

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle("醫師申報業績")
        chart.legend().hide()
        chart.setAnimationOptions(QtChart.QChart.AllAnimations)

        chartView = QtChart.QChartView(chart)
        chartView.setRenderHint(QtGui.QPainter.Antialiasing)
        chartView.setFixedWidth(700)
        chartView.setFixedHeight(450)
        self.ui.verticalLayout_chart.addWidget(chartView)

    def _plot_case_type_chart(self):
        table_widget = self.ui.tableWidget_case_xml

        bar_set = []
        series = QtChart.QBarSeries()
        for row_no in range(table_widget.rowCount() - 1):
            item = table_widget.item(row_no, 0)
            if item is None:
                continue

            case_type = item.text()
            bar_set.append(QtChart.QBarSet(case_type))
            bar_set[-1] << self._get_cell_value(table_widget, row_no, 8)
            series.append(bar_set[-1])

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle("案件分類申報統計表")
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ["申報金額"]
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
