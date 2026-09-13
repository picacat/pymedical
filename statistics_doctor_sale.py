# -*- coding: UTF-8 -*-
import gc
import logging

from PyQt5 import QtChart, QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

import mysql
from libs import (
    case_utils,
    charge_utils,
    class_utils,
    export_utils,
    number_utils,
    string_utils,
    system_utils,
    ui_utils,
)

# 進度對話框固定更新約 N 次, 與資料量無關
PROGRESS_UPDATE_COUNT = 100
# IN (...) 子句一次帶入的 key 數量上限
CHUNK_SIZE = 1000
# 明細列數上限: 超過此數量即使不爆記憶體, QTableWidget 也吃不消
# 32 位元 Python 行程位址空間僅約 2GB, 這道守門是必要的
MAX_ROW_COUNT = 200000
# 圓餅圖取前 N 名
CHART_TOP_COUNT = 10

# 顯示列種類
ROW_SALE = 0  # 自費銷售明細 (含折扣, 差額)
ROW_RETURN = 1  # 退貨
ROW_TOTAL = 2  # 總計

# 文字顏色
COLOR_NONE = None
COLOR_RED = "red"
COLOR_DARK_GREEN = "darkgreen"

# 靠右 / 置中的欄位
SALE_RIGHT_COLUMNS = (2, 5, 6, 8, 9, 10, 11)
SALE_CENTER_COLUMNS = (7,)
RETURN_RIGHT_COLUMNS = (2, 6, 9)

# 明細表欄位索引
COL_CASE_KEY = 0
COL_CASE_DATE = 1
COL_MEDICINE_NAME = 4
COL_QUANTITY = 6
COL_AMOUNT = 9
COL_COMMISSION = 11

# 不列入品項小計的列
SUMMARY_EXCLUDE_NAMES = ("折扣", "總計", "差額")


# 醫師自費銷售統計 2019.08.27
class StatisticsDoctorSale(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.doctor = args[5]
        self.option = args[6]
        self.weekday_list = args[7]
        self.ui = None
        self.clinic_name = self.system_settings.field("院所名稱")
        self.progress_dialog = None
        self.chart_view = None

        # ------- 效能快取 (每次 start_calculate 會重設) -------
        self.pres_days_cache = {}  # (CaseKey, MedicineSet) -> Days
        self.commission_cache = {}  # (MedicineKey, Doctor) -> 抽成率

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DOCTOR_SALE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_doctor_sale = class_utils.get_table_widget(
            self.ui.tableWidget_doctor_sale, self.database
        )
        self.table_widget_sale_summary = class_utils.get_table_widget(
            self.ui.tableWidget_sale_summary, self.database
        )
        self.table_widget_doctor_sale.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        width = [100, 130, 70, 85, 200, 50, 50, 50, 60, 100, 70, 70, 85]
        self.table_widget_doctor_sale.set_table_heading_width(width)
        width = [270, 70, 120, 80]
        self.table_widget_sale_summary.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_doctor_sale.doubleClicked.connect(self._open_medical_record)
        self.ui.toolButton_export_to_excel.clicked.connect(self._export_to_excel)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    # 改版重點 (2026-09):
    #   1. 主查詢只執行一次. 原版先 select_record 取 row_count, 再用同一句 SQL 跑
    #      set_db_data, 兩份完整結果集同時存在記憶體, 32 位元行程直接 MemoryError.
    #   2. 不再 SELECT prescript.*, 只取實際用得到的欄位.
    #   3. 折扣/差額/退貨/總計改為在 Python 端組成完整的顯示列清單後,
    #      setRowCount 一次配置再循序填表, 全程不呼叫 insertRow (原版是 O(n^2)).
    #   4. cases 的預載快取移除: DiscountFee 併入主查詢即可, 其餘欄位本來就在主查詢裡.
    #   5. 品項小計改用 dict 累加, 取代原版每列線性掃描小計表.
    # ------------------------------------------------------------------
    def start_calculate(self):
        self._reset_caches()
        self._clear_tables()

        try:
            display_rows = self._read_data()
            if display_rows is None:  # 取消, 或資料量超過上限
                return

            self._merge_return_goods(display_rows)
            self._append_total_row(display_rows)

            self._fill_table(display_rows)
            summary_rows = self._build_sale_summary(display_rows)
            display_rows = None  # 表格已填完, 立刻釋放
        finally:
            self._close_progress_dialog()
            self._reset_caches()
            gc.collect()

        self._list_sales_summary(summary_rows)
        self._append_summary_total_row(summary_rows)
        self._plot_chart(summary_rows)

    def _clear_tables(self):
        self.ui.tableWidget_doctor_sale.clearContents()
        self.ui.tableWidget_doctor_sale.setRowCount(0)
        self.ui.tableWidget_sale_summary.clearContents()
        self.ui.tableWidget_sale_summary.setRowCount(0)

    # ------------------------------------------------------------------
    # 快取
    # ------------------------------------------------------------------
    def _reset_caches(self):
        self.pres_days_cache = {}
        self.commission_cache = {}

    @staticmethod
    def _chunked(items, size=CHUNK_SIZE):
        for i in range(0, len(items), size):
            yield items[i : i + size]

    def _preload_pres_days(self, rows):
        """由主查詢結果取出所有 CaseKey, 一次把 dosage 的給藥日數撈進記憶體."""
        case_keys = []
        seen = set()
        for row in rows:
            case_key = row["CaseKey"]
            if case_key is None or case_key in seen:
                continue
            seen.add(case_key)
            case_keys.append(case_key)

        for chunk in self._chunked(case_keys):
            key_list = ",".join(str(number_utils.get_integer(k)) for k in chunk)
            sql = f"""
                SELECT CaseKey, MedicineSet, Days
                FROM dosage
                WHERE CaseKey IN ({key_list})
            """
            try:
                dosage_rows = self.database.select_record(sql)
            except Exception as e:
                logging.error(f"預載給藥日數失敗: {e}")
                return
            for row in dosage_rows:
                key = (
                    number_utils.get_integer(row["CaseKey"]),
                    number_utils.get_integer(row["MedicineSet"]),
                )
                # 對應原本 get_pres_days 的 LIMIT 1: 同一組只取第一筆
                if key not in self.pres_days_cache:
                    self.pres_days_cache[key] = number_utils.get_integer(row["Days"])

    def _get_pres_days(self, case_key, medicine_set):
        """取代 case_utils.get_pres_days, 純記憶體查表."""
        if medicine_set is None:
            return 0
        key = (
            number_utils.get_integer(case_key),
            number_utils.get_integer(medicine_set),
        )
        return self.pres_days_cache.get(key, 0)

    def _get_commission_rate(self, medicine_key, doctor):
        """charge_utils.get_commission_rate 一次要跑 3~4 個查詢, 這裡以
        (MedicineKey, Doctor) 為 key 記憶結果, 相同組合只查一次."""
        key = (medicine_key, doctor)
        if key not in self.commission_cache:
            self.commission_cache[key] = charge_utils.get_commission_rate(
                self.database, medicine_key, doctor
            )
        return self.commission_cache[key]

    def _cell_text(self, row_no, col_no):
        item = self.ui.tableWidget_doctor_sale.item(row_no, col_no)
        if item is None:
            return ""
        return item.text()

    # ------------------------------------------------------------------
    # 進度對話框
    # ------------------------------------------------------------------
    def _create_progress_dialog(self, message, maximum):
        # 註: minimumDuration 預設 4000ms, 估不到 4 秒就整個不顯示,
        #     改成 0 並主動 show() + processEvents() 讓對話框立刻出現.
        #     若 ui_utils.get_progress_dialog() 已抽成共用函式, 可直接改用它.
        dialog = QtWidgets.QProgressDialog(message, "取消", 0, maximum, self)
        dialog.setWindowModality(QtCore.Qt.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setValue(0)
        dialog.show()
        QtWidgets.QApplication.processEvents()
        return dialog

    def _close_progress_dialog(self):
        if self.progress_dialog is None:
            return
        self.progress_dialog.close()
        self.progress_dialog.deleteLater()
        self.progress_dialog = None

    @staticmethod
    def _progress_step(record_count):
        return max(1, record_count // PROGRESS_UPDATE_COUNT)

    # ------------------------------------------------------------------
    # 讀取資料
    # ------------------------------------------------------------------
    def _get_condition(self):
        period_condition = ""
        if self.period != "全部":
            period_condition = f' AND Period = "{self.period}"'

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(cases.CaseDate) IN({','.join(self.weekday_list)})"
            )

        doctor_condition = ""
        if self.doctor != "全部":
            doctor_condition = f' AND cases.Doctor = "{self.doctor}"'

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option)

        # 註: 原本的 LEFT JOIN 因 WHERE 帶有 cases.CaseDate 條件, 語意上等同 INNER JOIN,
        #     改成 INNER JOIN 可確保優化器以 cases 為驅動表.
        #     原本的 GROUP BY prescript.PrescriptKey 是多餘的 (PrescriptKey 為 PRIMARY KEY).
        return f'''
            FROM
                prescript
            INNER JOIN cases
                ON prescript.CaseKey = cases.CaseKey
            WHERE
                prescript.MedicineSet >= 2 AND
                prescript.MedicineSet != 11 AND
                MedicineName IS NOT NULL AND
                cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}"
                {period_condition}
                {weekday_condition}
                {regist_condition}
                {doctor_condition}
        '''

    def _get_row_count(self, from_sql):
        sql = f"SELECT COUNT(*) AS RowCount {from_sql}"
        try:
            rows = self.database.select_record(sql)
        except mysql.connector.Error as e:
            logging.error(f"計算資料筆數失敗: {e.errno} {e.msg}")
            return -1
        if not rows:
            return 0
        return number_utils.get_integer(rows[0]["RowCount"])

    def _read_data(self):
        """回傳顯示列清單 [(kind, color, values), ...];
        使用者取消或資料量超過上限時回傳 None."""
        from_sql = self._get_condition()

        row_count = self._get_row_count(from_sql)
        if row_count < 0:
            return None
        if row_count == 0:
            return []
        if row_count > MAX_ROW_COUNT:
            system_utils.show_message_box(
                QMessageBox.Warning,
                "資料量過大",
                f"<h3>符合條件的自費處方共 {row_count:,} 列, 超過可處理的上限.</h3>",
                "請縮小查詢的日期範圍, 或指定單一醫師後再查詢一次.",
            )
            return None

        # 只取用得到的欄位. 原版的 prescript.* 會把 Instruction / Remark 等
        # 完全沒用到的欄位一起撈回來, 在 32 位元行程裡是主要的記憶體來源之一.
        # cases.CaseKey 不重複選取 (與 prescript.CaseKey 同名會互相覆蓋).
        sql = f"""
            SELECT
                prescript.CaseKey, prescript.MedicineSet, prescript.MedicineKey,
                prescript.MedicineName, prescript.Dosage, prescript.Unit,
                prescript.Price, prescript.Amount,
                cases.PatientKey, cases.Name, cases.CaseDate, cases.Doctor,
                cases.DiscountFee, cases.TotalFee
            {from_sql}
            ORDER BY cases.CaseKey, prescript.PrescriptKey
        """

        try:
            rows = self.database.select_record(sql)
        except mysql.connector.Error as e:
            logging.error(f"讀取自費處方失敗: {e.errno} {e.msg}")
            return None
        except MemoryError:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "記憶體不足",
                "<h3>資料量過大, 無法完成統計.</h3>",
                "請縮小查詢的日期範圍, 或指定單一醫師後再查詢一次.",
            )
            return None

        if not rows:
            return []

        self._preload_pres_days(rows)

        self.progress_dialog = self._create_progress_dialog(
            "自費銷售統計中, 請稍後...", len(rows)
        )
        display_rows = self._build_display_rows(rows)
        rows = None

        return display_rows

    def _build_display_rows(self, rows):
        """走訪主查詢結果, 逐份病歷產生明細列, 並在每份病歷結束時補上折扣與差額列.

        註 1: 原版以 PatientKey 換人作為折扣的分組界線, 但折扣是掛在病歷 (CaseKey) 上,
              同一位病患相鄰的兩份病歷 (同日重複掛號) 前一份的折扣會被跳過, 最後由
              差額補上 -- 金額正確但名稱與顏色錯誤. 這裡一律以 CaseKey 分組.
        註 2: rows 反轉後由尾端 pop, 已處理的列即時釋放, 讓 rows 與 display_rows
              不會整份同時佔用記憶體.
        """
        display_rows = []
        progress_step = self._progress_step(len(rows))
        processed = 0

        rows.reverse()
        current_case_key = None
        current_case_row = None
        current_amount = 0.0

        while rows:
            row = rows.pop()
            case_key = string_utils.xstr(row["CaseKey"])
            if case_key != current_case_key:
                if current_case_row is not None:
                    current_amount = self._close_case_group(
                        display_rows, current_case_row, current_amount
                    )
                current_case_key = case_key
                current_case_row = row
                current_amount = 0.0

            values, color = self._build_sale_row(row)
            display_rows.append((ROW_SALE, color, values))
            current_amount += number_utils.get_float(values[COL_AMOUNT])

            processed += 1
            if processed % progress_step == 0:
                self.progress_dialog.setValue(processed)
                if self.progress_dialog.wasCanceled():
                    return None

        if current_case_row is not None:
            self._close_case_group(display_rows, current_case_row, current_amount)

        return display_rows

    def _close_case_group(self, display_rows, case_row, case_amount):
        """一份病歷結束: 先補折扣列, 再補差額列 (與原版的插入順序相同)."""
        discount_fee = number_utils.get_integer(case_row["DiscountFee"])
        if discount_fee > 0:
            values, color = self._build_sale_row(
                self._make_virtual_row(case_row, "折扣", -discount_fee)
            )
            display_rows.append((ROW_SALE, color, values))
            case_amount += number_utils.get_float(values[COL_AMOUNT])

        total_fee = number_utils.get_float(case_row["TotalFee"])
        if case_amount != total_fee:
            balance = case_amount - total_fee
            values, color = self._build_sale_row(
                self._make_virtual_row(case_row, "差額", -balance)
            )
            display_rows.append((ROW_SALE, color, values))
            case_amount += number_utils.get_float(values[COL_AMOUNT])

        return case_amount

    @staticmethod
    def _make_virtual_row(case_row, medicine_name, amount):
        """組出折扣 / 差額這類沒有對應 prescript 的虛擬列."""
        return {
            "CaseKey": case_row["CaseKey"],
            "CaseDate": case_row["CaseDate"],
            "PatientKey": case_row["PatientKey"],
            "Name": case_row["Name"],
            "MedicineName": medicine_name,
            "MedicineSet": 0,
            "Dosage": 1,
            "Unit": "次",
            "Price": amount,
            "Amount": amount,
            "MedicineKey": None,
            "Doctor": case_row["Doctor"],
            "TotalFee": amount,
        }

    def _build_sale_row(self, row):
        """純計算, 不碰 Qt: 由一列資料算出表格要顯示的 13 個欄位與文字顏色."""
        case_key = row["CaseKey"]
        medicine_key = row["MedicineKey"]
        medicine_set = row["MedicineSet"]
        medicine_name = row["MedicineName"]

        pres_days = self._get_pres_days(case_key, medicine_set)
        if pres_days == 0:
            pres_days = 1

        doctor = string_utils.xstr(row["Doctor"])
        quantity = number_utils.get_float(row["Dosage"])
        price = number_utils.get_float(row["Price"])

        if (
            self.clinic_name == "專嘉中醫診所"
            and medicine_name is not None
            and medicine_name == "自費粉藥"
        ):
            pres_days = 1

        amount = number_utils.round_up(
            charge_utils.get_subtotal_fee(
                number_utils.get_float(row["Amount"]), pres_days
            )
        )
        if number_utils.get_integer(row["TotalFee"]) == 0:
            amount = 0

        commission_rate = self._get_commission_rate(medicine_key, doctor)
        commission = charge_utils.calc_commission(quantity, amount, commission_rate)
        if commission_rate != "" and "%" not in commission_rate:
            commission_rate = f"${commission_rate}"

        values = (
            string_utils.xstr(case_key),
            string_utils.xstr(row["CaseDate"].date()),
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            medicine_name,
            pres_days,
            quantity,
            string_utils.xstr(row["Unit"]),
            price,
            amount,
            commission_rate,
            commission,
            doctor,
        )

        color = COLOR_NONE
        if price < 0:
            color = COLOR_RED
        if medicine_name == "差額":
            color = COLOR_DARK_GREEN

        return values, color

    # ------------------------------------------------------------------
    # 退貨
    # ------------------------------------------------------------------
    def _read_return_goods_rows(self):
        period_condition = ""
        if self.period != "全部":
            period_condition = f' AND Period = "{self.period}"'

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(ReturnGoodsDate) IN({','.join(self.weekday_list)})"
            )

        sql = f"""
            SELECT ReturnGoodsDate, PatientKey, Name, ItemName, Quantity, Amount
            FROM returngoods
            WHERE ReturnGoodsDate BETWEEN %s AND %s
            {period_condition}
            {weekday_condition}
            ORDER BY ReturnGoodsDate DESC, ReturnGoodsKey DESC
        """
        params = (self.start_date, self.end_date)
        try:
            return self.database.select_record(sql, params)
        except mysql.connector.Error as e:
            logging.error(f"讀取退貨資料失敗: {e.errno} {e.msg}")
            return None

    def _merge_return_goods(self, display_rows):
        if self.doctor != "全部":  # 退貨無醫師欄位, 個別醫師統計不列退貨
            return

        rows = self._read_return_goods_rows()
        if not rows:
            return

        # SQL 已按日期由晚到早排序, 先插後面的列不會影響前面的插入位置
        for row in rows:
            return_date = row["ReturnGoodsDate"].strftime("%Y-%m-%d")
            item_name = string_utils.xstr(row["ItemName"])
            amount = number_utils.get_integer(row["Amount"])
            values = (
                "",
                return_date,
                string_utils.xstr(row["PatientKey"]),
                string_utils.xstr(row["Name"]),
                f"{item_name}(退貨)",
                "",
                number_utils.get_float(row["Quantity"]),
                "",
                "",
                -amount,
                "",
                "",
                "",
            )
            position = self._get_return_goods_position(display_rows, return_date)
            display_rows.insert(position, (ROW_RETURN, COLOR_RED, values))

    @staticmethod
    def _get_return_goods_position(display_rows, return_date):
        """找到第一筆日期大於退貨日的列, 退貨列插在該日所有銷售之後.
        註: 明細是按 CaseKey 排序而非日期, 這個定位方式沿用原版 (CaseKey 大致依時序遞增)."""
        for index, (_kind, _color, values) in enumerate(display_rows):
            if values[COL_CASE_DATE] > return_date:
                return index
        return len(display_rows)

    # ------------------------------------------------------------------
    # 總計
    # ------------------------------------------------------------------
    @staticmethod
    def _append_total_row(display_rows):
        total_amount = 0.0
        total_commission = 0.0
        for _kind, _color, values in display_rows:
            total_amount += number_utils.get_float(values[COL_AMOUNT])
            total_commission += number_utils.get_float(values[COL_COMMISSION])

        values = [""] * 13
        values[COL_MEDICINE_NAME] = "總計"
        values[COL_AMOUNT] = string_utils.xstr(round(total_amount))
        values[COL_COMMISSION] = string_utils.xstr(
            number_utils.round_up(total_commission)
        )
        display_rows.append((ROW_TOTAL, COLOR_NONE, tuple(values)))

    # ------------------------------------------------------------------
    # 填表
    # ------------------------------------------------------------------
    def _fill_table(self, display_rows):
        table = self.ui.tableWidget_doctor_sale
        row_count = len(display_rows)
        progress_step = self._progress_step(row_count)

        if self.progress_dialog is not None:
            self.progress_dialog.setLabelText("產生報表中, 請稍後...")
            self.progress_dialog.setRange(0, row_count)
            self.progress_dialog.setValue(0)

        table.setSortingEnabled(False)
        table.setUpdatesEnabled(False)
        table.blockSignals(True)
        try:
            table.setRowCount(row_count)
            for row_no, (kind, color, values) in enumerate(display_rows):
                if kind == ROW_TOTAL:
                    self._fill_total_row(row_no, values)
                else:
                    self._fill_row(row_no, kind, color, values)

                if self.progress_dialog is not None and row_no % progress_step == 0:
                    self.progress_dialog.setValue(row_no)
                    if self.progress_dialog.wasCanceled():
                        break
        finally:
            table.blockSignals(False)
            table.setUpdatesEnabled(True)

        if self.progress_dialog is not None:
            self.progress_dialog.setValue(row_count)

    def _fill_row(self, row_no, kind, color, values):
        table = self.ui.tableWidget_doctor_sale
        brush = QtGui.QBrush(QtGui.QColor(color)) if color is not None else None

        for col_no, value in enumerate(values):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, value)

            if kind == ROW_RETURN:
                if col_no in RETURN_RIGHT_COLUMNS:
                    align = QtCore.Qt.AlignRight
                else:
                    align = QtCore.Qt.AlignLeft
            elif col_no in SALE_RIGHT_COLUMNS:
                align = QtCore.Qt.AlignRight
            elif col_no in SALE_CENTER_COLUMNS:
                align = QtCore.Qt.AlignCenter
            else:
                align = QtCore.Qt.AlignLeft
            item.setTextAlignment(align | QtCore.Qt.AlignVCenter)

            if brush is not None:
                item.setForeground(brush)

            table.setItem(row_no, col_no, item)

    def _fill_total_row(self, row_no, values):
        table = self.ui.tableWidget_doctor_sale
        for col_no in (COL_MEDICINE_NAME, COL_AMOUNT, COL_COMMISSION):
            item = QtWidgets.QTableWidgetItem(values[col_no])
            if col_no != COL_MEDICINE_NAME:
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            table.setItem(row_no, col_no, item)

    # ------------------------------------------------------------------
    # 品項小計
    # ------------------------------------------------------------------
    @staticmethod
    def _build_sale_summary(display_rows):
        """以 dict 累加取代原版每列線性掃描小計表 (原本是 明細列數 x 品項數)."""
        summary = {}
        for kind, _color, values in display_rows:
            if kind != ROW_SALE:
                continue

            medicine_name = values[COL_MEDICINE_NAME]
            if medicine_name is None:
                continue
            if medicine_name in SUMMARY_EXCLUDE_NAMES:
                continue
            if medicine_name.endswith("(退貨)"):
                continue

            data = summary.setdefault(medicine_name, [0.0, 0.0, 0.0])
            data[0] += number_utils.get_float(values[COL_QUANTITY])
            data[1] += number_utils.get_float(values[COL_AMOUNT])
            data[2] += number_utils.get_float(values[COL_COMMISSION])

        # 依金額由大到小, 取代原版的 sortItems
        return sorted(summary.items(), key=lambda item: item[1][1], reverse=True)

    def _list_sales_summary(self, summary_rows):
        table = self.ui.tableWidget_sale_summary
        table.setSortingEnabled(False)
        table.setUpdatesEnabled(False)
        try:
            table.setRowCount(len(summary_rows))
            for row_no, (medicine_name, data) in enumerate(summary_rows):
                quantity, amount, commission = data
                summary_row = [
                    medicine_name,
                    quantity,
                    number_utils.get_integer(amount),
                    commission,
                ]
                for col_no, value in enumerate(summary_row):
                    item = QtWidgets.QTableWidgetItem()
                    item.setData(QtCore.Qt.EditRole, value)
                    if col_no in (1, 2, 3):
                        item.setTextAlignment(
                            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                        )
                    if amount < 0:
                        item.setForeground(QtGui.QBrush(QtGui.QColor(COLOR_RED)))
                    table.setItem(row_no, col_no, item)
        finally:
            table.setUpdatesEnabled(True)

    def _append_summary_total_row(self, summary_rows):
        total_amount = 0.0
        total_commission = 0.0
        for _medicine_name, data in summary_rows:
            total_amount += data[1]
            total_commission += data[2]

        table = self.ui.tableWidget_sale_summary
        row_count = table.rowCount()
        table.insertRow(row_count)
        table.setItem(row_count, 0, QtWidgets.QTableWidgetItem("總計"))

        item = QtWidgets.QTableWidgetItem(string_utils.xstr(round(total_amount)))
        item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        table.setItem(row_count, 2, item)

        item = QtWidgets.QTableWidgetItem(string_utils.xstr(total_commission))
        item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        table.setItem(row_count, 3, item)

    # ------------------------------------------------------------------
    # 圓餅圖
    # ------------------------------------------------------------------
    def _plot_chart(self, summary_rows):
        """原版由小計表回讀資料, 走訪到「總計」列時已先把總金額從 total_amount 扣掉
        才 break, 導致「其他」變成負數. 這裡直接用 summary_rows 計算."""
        self._remove_chart_view()

        series = QtChart.QPieSeries()
        for medicine_name, data in summary_rows[:CHART_TOP_COUNT]:
            series.append(medicine_name, data[1])

        if len(summary_rows) > CHART_TOP_COUNT:
            others = sum(data[1] for _name, data in summary_rows[CHART_TOP_COUNT:])
            if others > 0:
                series.append("其他", others)

        for pie_slice in series.slices():
            pie_slice.setExploded()
            pie_slice.setLabelVisible()

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle(f"{self.doctor}醫師自費銷售排行榜Top{CHART_TOP_COUNT}")
        chart.legend().hide()
        chart.setAnimationOptions(QtChart.QChart.AllAnimations)

        self.chart_view = QtChart.QChartView(chart)
        self.chart_view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.chart_view.setFixedHeight(400)
        self.ui.verticalLayout_chart.addWidget(self.chart_view)

    def _remove_chart_view(self):
        """重新統計時把舊的圖表移除, 否則會一張一張往下疊."""
        if self.chart_view is None:
            return
        self.ui.verticalLayout_chart.removeWidget(self.chart_view)
        self.chart_view.setParent(None)
        self.chart_view.deleteLater()
        self.chart_view = None

    # ------------------------------------------------------------------
    # 匯出 / 開啟病歷
    # ------------------------------------------------------------------
    def _export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]

        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f"{start_date}至{end_date}{self.doctor}醫師自費銷售統計表.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_doctor_sale, [0], [2, 5, 6, 8, 9, 11]
        )
        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>醫師自費銷售統計檔{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def _open_medical_record(self):
        # 不再經過 set_db_data, 直接由表格第 0 欄 (隱藏的 CaseKey) 取值
        row_no = self.ui.tableWidget_doctor_sale.currentRow()
        if row_no < 0:
            return

        case_key = self._cell_text(row_no, COL_CASE_KEY)
        if case_key == "":  # 退貨列與總計列沒有病歷
            return

        self.parent.parent.open_medical_record(case_key)
