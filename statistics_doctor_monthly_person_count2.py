# -*- coding: UTF-8 -*-

import calendar
import datetime

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (
    case_utils,
    class_utils,
    date_utils,
    export_utils,
    nhi_utils,
    number_utils,
    string_utils,
    system_utils,
    ui_utils,
)

SELF_FEE_COLUMN = {
    "科中": 26,
    "外用": 27,
    "針灸": 28,
    "飲片": 29,
    "其他": 30,
}

# 明細合計與 cases.TotalFee 有差額時, 把差額補到哪一欄 (科中)
# 與 statistics_business_income_list.py 的對帳邏輯一致
RECONCILE_COLUMN = SELF_FEE_COLUMN["科中"]


# 醫師月報表 2022.05.12
class StatisticsDoctorMonthlyPersonCount2(QtWidgets.QMainWindow):
    # 明細合計與 cases.TotalFee 對帳 (偷懶病歷: 處方沒填價但 TotalFee 有值)
    # 設為 False 則只採計處方明細算得出來的金額
    RECONCILE_WITH_CASE_TOTAL = True

    # True : 自費金額與人次分開統計 (有自費的健保病歷仍計入針灸/傷科/內科人次)
    # False: 維持原本行為 (TotalFee > 0 就不計人次) -- 僅供比對舊報表用

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.year = args[2]
        self.month = args[3]
        self.doctor = args[4]
        self.ui = None

        self.last_day = calendar.monthrange(int(self.year), int(self.month))[1]
        self.start_date = f"{self.year}-{self.month}-01 00:00:00"
        self.end_date = f"{self.year}-{self.month}-{self.last_day} 23:59:59"
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
        self.ui = ui_utils.load_ui_file(
            ui_utils.UI_STATISTICS_DOCTOR_MONTHLY_COUNT, self
        )
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_doctor_monthly = class_utils.get_table_widget(
            self.ui.tableWidget_doctor_monthly, self.database
        )

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_to_excel.clicked.connect(self._export_to_excel)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_doctor_monthly.setRowCount(0)
        self._set_statistics_table_heading()
        self._calculate_data()
        # self._calculate_subtotal()
        self._calculate_total()

    def _set_heading(self, title, submenu):
        start_col_no = self.ui.tableWidget_doctor_monthly.columnCount()

        self.ui.tableWidget_doctor_monthly.setColumnCount(
            self.ui.tableWidget_doctor_monthly.columnCount() + len(submenu)
        )
        self.ui.tableWidget_doctor_monthly.setItem(
            0, start_col_no, QtWidgets.QTableWidgetItem(title)
        )
        self.ui.tableWidget_doctor_monthly.setSpan(0, start_col_no, 1, len(submenu))
        self.ui.tableWidget_doctor_monthly.item(0, start_col_no).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )
        for col_no, menu in enumerate(submenu):
            self.ui.tableWidget_doctor_monthly.setItem(
                1, col_no + start_col_no, QtWidgets.QTableWidgetItem(menu)
            )
            self.ui.tableWidget_doctor_monthly.item(
                1, col_no + start_col_no
            ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    def _set_statistics_table_heading(self):
        v_heading_height = 2
        self.ui.tableWidget_doctor_monthly.clearSpans()
        self.ui.tableWidget_doctor_monthly.clear()

        self.ui.tableWidget_doctor_monthly.setColumnCount(1)
        self.ui.tableWidget_doctor_monthly.setRowCount(v_heading_height)

        self.ui.tableWidget_doctor_monthly.setItem(
            0, 0, QtWidgets.QTableWidgetItem("項目")
        )
        self.ui.tableWidget_doctor_monthly.setSpan(0, 0, 2, 1)
        self.ui.tableWidget_doctor_monthly.item(0, 0).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

        self._set_heading("內科", ["人數"])
        self._set_heading("一般針灸給藥", ["首次", "2-6次"])
        self._set_heading("中度複針給藥", ["首次", "2-6次"])
        self._set_heading("高度複針給藥", ["首次", "2-6次"])
        self._set_heading("一般傷科給藥", ["首次", "2-6次"])
        self._set_heading("中度複傷給藥", ["首次", "2-6次"])
        self._set_heading("高度複傷給藥", ["首次", "2-6次"])
        self._set_heading("一般針灸", ["首次", "2-6次"])
        self._set_heading("中度複針", ["首次", "2-6次"])
        self._set_heading("高度複針", ["首次", "2-6次"])
        self._set_heading("一般傷科", ["首次", "2-6次"])
        self._set_heading("中度複傷", ["首次", "2-6次"])
        self._set_heading("高度複傷", ["首次", "2-6次"])
        self._set_heading("自費金額", ["科中", "外用", "針灸", "飲片", "其他"])

        self._set_calendar_heading(v_heading_height)

    def _set_calendar_heading(self, v_heading_height):
        start_date = datetime.datetime.strptime(
            self.start_date, "%Y-%m-%d %H:%M:%S"
        ).date()
        end_date = datetime.datetime.strptime(self.end_date, "%Y-%m-%d %H:%M:%S").date()
        day_count = (end_date - start_date).days + 1

        calendar_list = []
        for date in (start_date + datetime.timedelta(n) for n in range(day_count)):
            try:
                week_day_name = date_utils.get_weekday_name(date.weekday(), "zh_TW")
                case_date = date.strftime(f"%m/%d ({week_day_name[2]})")
            except Exception:
                case_date = date.strftime("%m/%d")

            if case_date not in calendar_list:
                calendar_list.append(case_date)

        row_count = len(calendar_list)
        self.ui.tableWidget_doctor_monthly.setRowCount(row_count + 1 + v_heading_height)

        for row_no, case_date in enumerate(calendar_list):
            self.ui.tableWidget_doctor_monthly.setItem(
                row_no + v_heading_height, 0, QtWidgets.QTableWidgetItem(case_date)
            )
            self.ui.tableWidget_doctor_monthly.item(
                row_no + v_heading_height, 0
            ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        self.ui.tableWidget_doctor_monthly.setItem(
            row_count + v_heading_height, 0, QtWidgets.QTableWidgetItem("總計")
        )
        self.ui.tableWidget_doctor_monthly.item(
            row_count + v_heading_height, 0
        ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        for row_no in range(
            v_heading_height, self.ui.tableWidget_doctor_monthly.rowCount()
        ):
            for col_no in range(1, self.ui.tableWidget_doctor_monthly.columnCount()):
                self.ui.tableWidget_doctor_monthly.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem("0")
                )
                self.ui.tableWidget_doctor_monthly.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _read_data(self):
        params = [self.start_date, self.end_date]

        doctor_condition = ""
        if self.doctor != "全部":
            doctor_condition = " AND cases.Doctor = %s"
            params.append(self.doctor)

        sql = f"""
            SELECT
                CaseKey, CaseDate, InsType, Treatment, Continuance, TotalFee
            FROM cases
            WHERE
                CaseDate BETWEEN %s AND %s
                {doctor_condition}
            ORDER BY CaseDate
        """
        rows = self.database.select_record(sql, params=tuple(params))

        return rows

    def _get_row_no(self, case_date):
        for row_no in range(self.ui.tableWidget_doctor_monthly.rowCount()):
            case_date_item = self.ui.tableWidget_doctor_monthly.item(row_no, 0)
            if case_date_item is None:
                continue

            if case_date in case_date_item.text():
                return row_no

        return None

    def _calculate_data(self):
        rows = self._read_data()
        row_count = len(rows)
        if row_count <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            "門診資料統計中, 請稍後...", "取消", 0, row_count, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for i, row in enumerate(rows):
            if progress_dialog.wasCanceled():
                break

            case_date = row["CaseDate"].strftime("%m/%d")
            progress_dialog.setValue(i)
            row_no = self._get_row_no(case_date)
            if row_no is None:
                continue

            case_key = row["CaseKey"]
            ins_type = string_utils.xstr(row["InsType"])
            treatment = string_utils.xstr(row["Treatment"])
            course = number_utils.get_integer(row["Continuance"])
            case_total_fee = number_utils.get_integer(row["TotalFee"])

            if ins_type == "健保":
                pres_days = case_utils.get_pres_days(self.database, case_key)
                self._calculate_case_count(row_no, treatment, course, pres_days)

            # 自費金額: 與人次分開計算
            # 一筆健保病歷可能既是針灸案件, 又有自費藥品, 兩邊都要算
            if case_total_fee > 0:
                self._calculate_self_fees(row_no, case_key, case_total_fee)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()

    # 人次統計 (由 _calculate_data 拆出, 邏輯未變動)
    def _calculate_case_count(self, row_no, treatment, course, pres_days):
        if treatment in nhi_utils.ACUPUNCTURE_TREAT:
            if pres_days > 0:
                if treatment in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST:
                    self._set_value(row_no, course, 4, 5)
                elif treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST:
                    self._set_value(row_no, course, 6, 7)
                else:
                    self._set_value(row_no, course, 2, 3)
            else:
                if treatment in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST:
                    self._set_value(row_no, course, 16, 17)
                elif treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST:
                    self._set_value(row_no, course, 18, 19)
                else:
                    self._set_value(row_no, course, 14, 15)
        elif treatment in nhi_utils.MASSAGE_TREAT:
            if pres_days > 0:
                if treatment in nhi_utils.MODERATE_COMPLICATED_MASSAGE_TREAT:
                    self._set_value(row_no, course, 10, 11)
                elif treatment in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT:
                    self._set_value(row_no, course, 12, 13)
                else:
                    self._set_value(row_no, course, 8, 9)
            else:
                if treatment in nhi_utils.MODERATE_COMPLICATED_MASSAGE_TREAT:
                    self._set_value(row_no, course, 22, 23)
                elif treatment in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT:
                    self._set_value(row_no, course, 24, 25)
                else:
                    self._set_value(row_no, course, 20, 21)
        else:  # 內科
            self._set_internal_cases(row_no)

    # -----------------------------------------------------------------
    # 自費金額統計
    #
    # 金額口徑與 statistics_business_income_list.py 一致:
    #   1. 以 medicine_set 為單位取金額, 不是逐筆處方
    #   2. dosage.TotalFee 優先, 沒有才用 prescript.Amount 加總
    #   3. 扣掉該 set 的 dosage.DiscountFee (折讓)
    #   4. 不乘 PresDays (dosage.TotalFee 本身已含天數)
    #   5. 與 cases.TotalFee 對帳, 差額補到科中
    # -----------------------------------------------------------------

    def _calculate_self_fees(self, row_no, case_key, case_total_fee=0):
        medicine_sets = self._get_medicine_sets(case_key)
        set_total = 0

        for medicine_set in medicine_sets:
            ms = number_utils.get_integer(medicine_set["MedicineSet"])
            net = self._get_set_total_fee(case_key, ms)
            if net <= 0:
                continue

            for medicine_type, amount in self._split_set_amount(case_key, ms, net):
                col_no = SELF_FEE_COLUMN.get(medicine_type, SELF_FEE_COLUMN["其他"])
                self._set_amount(row_no, col_no, amount)

            set_total += net

        # 明細合計與 cases.TotalFee 對帳
        # 偷懶病歷 (處方完全沒填價) 的金額才不會憑空消失
        if self.RECONCILE_WITH_CASE_TOTAL and medicine_sets:
            diff = case_total_fee - set_total
            if diff != 0:
                self._set_amount(row_no, RECONCILE_COLUMN, diff)

    # 該病歷的所有自費處方組別
    def _get_medicine_sets(self, case_key):
        sql = """
            SELECT
                MedicineSet
            FROM
                prescript
            WHERE
                CaseKey = %s AND
                MedicineSet >= 2
            GROUP BY MedicineSet
        """
        rows = self.database.select_record(sql, params=(case_key,))

        return rows

    # 單一 medicine_set 的實收金額
    #
    #   實收 = 登錄金額 - 該 set 的 DiscountFee
    #   登錄金額: dosage.TotalFee 有值優先, 否則加總 prescript.Amount
    #
    # 注意 (口徑確認點):
    #   此寫法假設 dosage.TotalFee 是「折讓前」的登錄金額。
    #   若實際上 dosage.TotalFee 已是折讓後實收, 則第一層不可再扣
    #   DiscountFee (會扣兩次), 只有 fallback 到 prescript.Amount 時才需要扣。
    def _get_set_total_fee(self, case_key, medicine_set):
        sql = """
            SELECT
                SUM(TotalFee) AS TotalFee,
                SUM(DiscountFee) AS DiscountFee
            FROM
                dosage
            WHERE
                CaseKey = %s AND
                MedicineSet = %s
        """
        rows = self.database.select_record(sql, params=(case_key, medicine_set))

        dosage_total = 0
        discount_fee = 0
        if rows:
            dosage_total = number_utils.get_integer(rows[0]["TotalFee"])
            discount_fee = number_utils.get_integer(rows[0]["DiscountFee"])

        if dosage_total > 0:
            base = dosage_total
        else:
            # 處置類等沒有 dosage 金額的 set: 用 prescript 明細加總
            sql = """
                SELECT
                    SUM(Amount) AS Amount
                FROM
                    prescript
                WHERE
                    CaseKey = %s AND
                    MedicineSet = %s
            """
            prescript_rows = self.database.select_record(
                sql, params=(case_key, medicine_set)
            )
            base = 0
            if prescript_rows and prescript_rows[0]["Amount"] is not None:
                base = number_utils.get_integer(prescript_rows[0]["Amount"])

        net = base - discount_fee
        net = max(net, 0)  # 折讓大於登錄金額屬資料異常, 不讓負數污染統計

        return net

    # 一組 set 內若混了不同藥品類別, 依 prescript.Amount 比例分攤該 set 的實收金額
    # 最後一項吸收進位誤差, 確保分攤加總 == net
    def _split_set_amount(self, case_key, medicine_set, net):
        sql = """
            SELECT
                MedicineName, MedicineType, Unit, Amount
            FROM
                prescript
            WHERE
                CaseKey = %s AND
                MedicineSet = %s
        """
        rows = self.database.select_record(sql, params=(case_key, medicine_set))
        if not rows:
            return [("其他", net)]

        subtotal = {}
        for row in rows:
            medicine_type = self._get_medicine_type(row)
            subtotal[medicine_type] = subtotal.get(
                medicine_type, 0
            ) + number_utils.get_integer(row["Amount"])

        items = [(key, value) for key, value in subtotal.items() if value > 0]
        base = sum(value for _, value in items)
        if base <= 0:
            # 明細完全沒填價的 set: 整筆歸第一列的類別
            return [(self._get_medicine_type(rows[0]), net)]

        result = []
        remaining = net
        for i, (medicine_type, amount) in enumerate(items):
            if i == len(items) - 1:
                value = remaining
            else:
                value = round(amount * net / base)
                remaining -= value
            result.append((medicine_type, value))

        return result

    def _get_medicine_type(self, row):
        medicine_type = string_utils.xstr(row["MedicineType"])
        medicine_name = string_utils.xstr(row["MedicineName"])
        unit = string_utils.xstr(row["Unit"])

        if (
            medicine_type in ["單方", "複方"]
            or "粉藥" in medicine_name
            or "科中" in medicine_name
            or "克" in unit
        ):
            medicine_type = "科中"
        elif (
            medicine_type in ["外用"]
            or "藥布" in medicine_name
            or "藥膏" in medicine_name
            or "膏藥" in medicine_name
        ):
            medicine_type = "外用"
        elif (
            medicine_type in ["穴道"] or "針" in medicine_name or "針" in medicine_type
        ):
            medicine_type = "針灸"
        elif (
            medicine_type in ["水藥"]
            or "水藥" in medicine_name
            or "飲片" in medicine_name
            or "錢" in unit
        ):
            medicine_type = "飲片"
        else:
            medicine_type = "其他"

        return medicine_type

    # -----------------------------------------------------------------
    # tableWidget 存取
    # -----------------------------------------------------------------

    def _set_value(self, row_no, course, col_no1, col_no2):
        if course <= 1:
            col_no = col_no1
        else:
            col_no = col_no2

        case_count = self._get_cell_value(row_no, col_no) + 1
        self._set_item_data(row_no, col_no, case_count)

    def _set_amount(self, row_no, col_no, amount):
        amount += self._get_cell_value(row_no, col_no)
        self._set_item_data(row_no, col_no, amount)

    def _set_internal_cases(self, row_no):
        col_no = 1

        case_count = self._get_cell_value(row_no, col_no) + 1
        self._set_item_data(row_no, col_no, case_count)

    def _get_cell_value(self, row_no, col_no):
        item = self.ui.tableWidget_doctor_monthly.item(row_no, col_no)
        if item is None:
            return 0

        return number_utils.get_integer(item.text())

    def _set_item_data(self, row_no, col_no, value):
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, value)
        self.ui.tableWidget_doctor_monthly.setItem(row_no, col_no, item)
        self.ui.tableWidget_doctor_monthly.item(row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "資料匯出",
            f"{start_date}至{end_date}{self.doctor}門診收入一覽表.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_doctor_monthly,
            None,
            [],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>門診收入一覽檔{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def _calculate_subtotal(self):
        col_count = self.ui.tableWidget_doctor_monthly.columnCount()
        row_count = self.ui.tableWidget_doctor_monthly.rowCount()

        self.ui.tableWidget_doctor_monthly.setColumnCount(col_count + 2)
        case_col_no = col_count
        fee_col_no = col_count + 1
        self.ui.tableWidget_doctor_monthly.setItem(
            0, case_col_no, QtWidgets.QTableWidgetItem("合計")
        )
        self.ui.tableWidget_doctor_monthly.setSpan(0, case_col_no, 1, 2)
        self.ui.tableWidget_doctor_monthly.item(0, case_col_no).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

        self.ui.tableWidget_doctor_monthly.setItem(
            1, case_col_no, QtWidgets.QTableWidgetItem("人數")
        )
        self.ui.tableWidget_doctor_monthly.item(1, case_col_no).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )
        self.ui.tableWidget_doctor_monthly.setItem(
            1, fee_col_no, QtWidgets.QTableWidgetItem("申報金額")
        )
        self.ui.tableWidget_doctor_monthly.item(1, fee_col_no).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

        for row_no in range(2, row_count - 1):
            total_case_count = 0
            total_fee = 0
            for col_no in range(
                1, self.ui.tableWidget_doctor_monthly.columnCount() - 2
            ):
                heading_item = self.ui.tableWidget_doctor_monthly.item(1, col_no)
                if heading_item is None:
                    continue

                heading = heading_item.text()
                if heading == "金額":
                    total_fee += self._get_cell_value(row_no, col_no)
                elif heading == "人數":
                    total_case_count += self._get_cell_value(row_no, col_no)

            self._set_item_data(row_no, case_col_no, total_case_count)
            self._set_item_data(row_no, fee_col_no, total_fee)

    def _calculate_total(self):
        row_count = self.ui.tableWidget_doctor_monthly.rowCount()
        total_field_row_no = row_count - 1

        for col_no in range(1, self.ui.tableWidget_doctor_monthly.columnCount()):
            total_fee = 0
            for row_no in range(2, row_count - 1):
                total_fee += self._get_cell_value(row_no, col_no)

            self._set_item_data(total_field_row_no, col_no, total_fee)
