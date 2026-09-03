from PyQt5 import QtChart, QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

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


# 自費銷售抽成統計 2026.08.29
class StatisticsCommissionSale(QtWidgets.QMainWindow):
    PROGRESS_STEP = 100  # 進度條更新間隔(每N列更新一次, 避免頻繁重繪)

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.seller = args[5]
        self.option = args[6]
        self.weekday_list = args[7]

        self.ui = None
        self.clinic_name = self.system_settings.field("院所名稱")

        self.min_discount_rate = None
        self.ignore_discount = None
        self.progress_dialog = None

        # 查詢快取(避免 N+1 query)
        self._pres_days_cache = {}
        self._discount_rate_cache = {}
        self._commission_cache = {}

        # 統計累加器(建表時同步累加, 不再回頭掃描表格)
        self._total_amount = 0.0
        self._total_commission = 0.0
        self._summary = {}

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_COMMISSION_SALE, self)
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
        width = [100, 130, 70, 85, 230, 50, 50, 50, 60, 70, 70, 70, 85]
        self.table_widget_doctor_sale.set_table_heading_width(width)
        width = [200, 100, 100]
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
    def start_calculate(self):
        self.min_discount_rate = charge_utils.get_min_discount_rate(self.database)
        self.ignore_discount = charge_utils.ignore_discount(self.database)

        self._pres_days_cache = {}
        self._discount_rate_cache = {}
        self._commission_cache = {}
        self._total_amount = 0.0
        self._total_commission = 0.0
        self._summary = {}

        self.ui.tableWidget_doctor_sale.setRowCount(0)
        self.ui.tableWidget_sale_summary.setRowCount(0)

        self._read_data()
        self._calculate_total()
        self._list_sales_summary()
        self._calculate_summary_total()
        # self._plot_chart()

    # ------------------------------------------------------------------
    # 快取包裝(同樣的參數只查一次DB)
    # ------------------------------------------------------------------
    def _get_pres_days(self, case_key, medicine_set):
        key = (case_key, medicine_set)
        if key not in self._pres_days_cache:
            pres_days = case_utils.get_pres_days(self.database, case_key, medicine_set)
            if not pres_days:
                pres_days = 1
            self._pres_days_cache[key] = pres_days
        return self._pres_days_cache[key]

    def _get_discount_rate(self, case_key):
        if case_key not in self._discount_rate_cache:
            self._discount_rate_cache[case_key] = case_utils.calculate_discount_rate(
                self.database, case_key
            )
        return self._discount_rate_cache[case_key]

    def _get_commission_rate(self, medicine_key, seller, treat_type=None):
        key = (medicine_key, seller, treat_type)
        if key not in self._commission_cache:
            if treat_type:
                rate = charge_utils.get_commission_rate(
                    self.database,
                    medicine_key,
                    seller,
                    treat_type=treat_type,
                    only_doctor=False,
                )
            else:
                rate = charge_utils.get_commission_rate(
                    self.database, medicine_key, seller, only_doctor=False
                )
            self._commission_cache[key] = rate
        return self._commission_cache[key]

    # ------------------------------------------------------------------
    # 讀取資料
    # ------------------------------------------------------------------
    def _read_data(self):
        period_condition = ""
        if self.period != "全部":
            period_condition = f' AND Period = "{self.period}"'

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(cases.CaseDate) IN({','.join(self.weekday_list)})"
            )

        doctor_condition = ""
        if self.seller != "全部":
            doctor_condition = f'''
                AND (cases.Doctor = "{self.seller}" OR
                    (cases.Doctor IS NULL AND
                     cases.Massager IS NULL AND
                     cases.Cashier = "{self.seller}") OR
                    (cases.Doctor IS NULL AND
                     cases.Massager IS NULL AND
                     cases.NursingAssistant = "{self.seller}") OR
                    (cases.Massager = "{self.seller}"))
            '''

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option)

        sql = f'''
            SELECT
                prescript.*,
                cases.CaseKey, cases.PatientKey, cases.Name, cases.CaseDate,
                cases.Doctor, cases.Cashier, cases.Register, cases.Massager,
                cases.NursingAssistant,
                cases.InsType, cases.TreatType, cases.DiscountFee
            FROM
                prescript
            LEFT JOIN cases
                ON prescript.CaseKey = cases.CaseKey
            WHERE
                prescript.MedicineSet >= 2 AND
                Dosage > 0 AND
                cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}"
                {period_condition}
                {weekday_condition}
                {regist_condition}
                {doctor_condition}
            ORDER BY cases.CaseKey, prescript.PrescriptKey
        '''

        rows = self.database.select_record(sql)
        if not rows:
            return

        # 折扣列直接用已抓回來的資料組出來, 不再另外查DB
        rows = self._merge_discount_rows(rows)
        row_count = len(rows)

        self.progress_dialog = QtWidgets.QProgressDialog(
            "自費銷售統計中, 請稍後...", "取消", 0, row_count, self
        )
        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        self.progress_dialog.setValue(0)

        table = self.ui.tableWidget_doctor_sale
        sorting_enabled = table.isSortingEnabled()
        table.setSortingEnabled(False)
        table.setUpdatesEnabled(False)
        table.blockSignals(True)
        table.setRowCount(row_count)  # 一次配置列數, 不用 insertRow

        filled_count = row_count
        try:
            for row_no, row in enumerate(rows):
                if row_no % self.PROGRESS_STEP == 0:
                    self.progress_dialog.setValue(row_no)
                    if self.progress_dialog.wasCanceled():
                        filled_count = row_no
                        break
                self._set_table_data(row_no, row)
        finally:
            if filled_count != row_count:
                table.setRowCount(filled_count)
            table.blockSignals(False)
            table.setUpdatesEnabled(True)
            table.setSortingEnabled(sorting_enabled)

        self.progress_dialog.setValue(row_count)
        self.progress_dialog.deleteLater()
        self.progress_dialog = None

    # 依病歷分組, 在每個病歷的最後一列後面插入折扣列
    def _merge_discount_rows(self, rows):
        merged = []
        last_row = None
        for row in rows:
            if last_row is not None and row["CaseKey"] != last_row["CaseKey"]:
                self._append_discount_row(merged, last_row)
            merged.append(row)
            last_row = row

        if last_row is not None:
            self._append_discount_row(merged, last_row)

        return merged

    def _append_discount_row(self, merged, row):
        discount_fee = number_utils.get_integer(row["DiscountFee"])
        if discount_fee <= 0:
            return

        merged.append(
            {
                "CaseKey": row["CaseKey"],
                "CaseDate": row["CaseDate"],
                "PatientKey": row["PatientKey"],
                "Name": row["Name"],
                "MedicineName": "折扣",
                "MedicineSet": 0,
                "PresDays": 1,
                "Dosage": 1,
                "Unit": "次",
                "Price": -discount_fee,
                "Amount": -discount_fee,
                "MedicineKey": None,
                "Doctor": row["Doctor"],
                "Massager": row["Massager"],
                "Register": row["Register"],
                "Cashier": row["Cashier"],
                "NursingAssistant": row["NursingAssistant"],
                "DiscountFee": row["DiscountFee"],
            }
        )

    # ------------------------------------------------------------------
    # 填入表格 + 同步累加統計
    # ------------------------------------------------------------------
    def _set_table_data(self, row_no, row):
        case_key = row["CaseKey"]
        medicine_key = row["MedicineKey"]
        medicine_set = row["MedicineSet"]
        medicine_name = string_utils.xstr(row["MedicineName"])

        pres_days = self._get_pres_days(case_key, medicine_set)

        try:
            discount_fee = number_utils.get_integer(row["DiscountFee"])
        except Exception:
            discount_fee = 0

        seller = string_utils.xstr(row["Doctor"])
        if seller in ["", None]:
            seller = string_utils.xstr(row["Massager"])
        if seller in ["", None]:
            seller = string_utils.xstr(row["Cashier"])
        if seller in ["", None]:
            seller = string_utils.xstr(row["Register"])

        seller2 = string_utils.xstr(row["NursingAssistant"])

        quantity = number_utils.get_float(row["Dosage"])
        price = number_utils.get_float(row["Price"])

        if self.clinic_name == "專嘉中醫診所" and medicine_name == "自費粉藥":
            pres_days = 1

        amount = number_utils.round_up(
            charge_utils.get_subtotal_fee(
                number_utils.get_float(row["Amount"]), pres_days
            )
        )

        if medicine_name in ["自費粉藥", "自費水藥"]:
            commission_rate = self._get_commission_rate(
                medicine_key, seller, treat_type=medicine_name
            )
        else:
            commission_rate = self._get_commission_rate(medicine_key, seller)

        if not self.ignore_discount:
            discount_rate = self._get_discount_rate(case_key)
            if discount_fee > 0 and discount_rate <= self.min_discount_rate:
                commission_rate = ""

        commission = charge_utils.calc_commission(quantity, amount, commission_rate)

        if (
            commission_rate is not None
            and commission_rate != ""
            and "%" not in commission_rate
        ):
            commission_rate = f"${commission_rate}"

        sale_row = [
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
            seller,
            seller2,
        ]

        table = self.ui.tableWidget_doctor_sale
        negative = price < 0
        red = QtGui.QColor("red")

        for col_no in range(len(sale_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, sale_row[col_no])

            if col_no in [2, 5, 6, 8, 9, 10, 11]:
                align = QtCore.Qt.AlignRight
            elif col_no in [7]:
                align = QtCore.Qt.AlignCenter
            else:
                align = QtCore.Qt.AlignLeft
            item.setTextAlignment(align | QtCore.Qt.AlignVCenter)

            if negative:
                item.setForeground(red)

            table.setItem(row_no, col_no, item)

        # 同步累加, 省掉之後整表重掃
        amount = number_utils.get_float(amount)
        commission = number_utils.get_float(commission)
        self._total_amount += amount
        self._total_commission += commission

        summary_key = seller
        if seller2 != "":
            summary_key = f"{seller}/{seller2}"
        entry = self._summary.get(summary_key)
        if entry is None:
            self._summary[summary_key] = [amount, commission]
        else:
            entry[0] += amount
            entry[1] += commission

    # ------------------------------------------------------------------
    # 明細總計
    # ------------------------------------------------------------------
    def _calculate_total(self):
        table = self.ui.tableWidget_doctor_sale
        row_count = table.rowCount()
        table.insertRow(row_count)

        table.setItem(row_count, 4, QtWidgets.QTableWidgetItem("總計"))

        item = QtWidgets.QTableWidgetItem(string_utils.xstr(round(self._total_amount)))
        item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        table.setItem(row_count, 9, item)

        item = QtWidgets.QTableWidgetItem(
            string_utils.xstr(number_utils.round_up(self._total_commission))
        )
        item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        table.setItem(row_count, 11, item)

    # ------------------------------------------------------------------
    # 銷售人員小計
    # ------------------------------------------------------------------
    def _list_sales_summary(self):
        # 依抽成金額由大到小排序
        ordered = sorted(
            self._summary.items(), key=lambda entry: entry[1][1], reverse=True
        )

        table = self.ui.tableWidget_sale_summary
        sorting_enabled = table.isSortingEnabled()
        table.setSortingEnabled(False)
        table.setUpdatesEnabled(False)
        table.blockSignals(True)
        table.setRowCount(len(ordered))

        red = QtGui.QColor("red")
        try:
            for row_no, (seller, (amount, commission)) in enumerate(ordered):
                blank_seller = seller in ["", "/"]
                summary_row = [
                    "折扣" if blank_seller else seller,
                    amount,
                    commission,
                ]
                for col_no in range(len(summary_row)):
                    item = QtWidgets.QTableWidgetItem()
                    item.setData(QtCore.Qt.EditRole, summary_row[col_no])
                    if col_no in [1, 2]:
                        item.setTextAlignment(
                            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                        )
                    if amount < 0 or (blank_seller and col_no == 0):
                        item.setForeground(red)
                    table.setItem(row_no, col_no, item)
        finally:
            table.blockSignals(False)
            table.setUpdatesEnabled(True)
            table.setSortingEnabled(sorting_enabled)

    def _calculate_summary_total(self):
        table = self.ui.tableWidget_sale_summary
        row_count = table.rowCount()
        table.insertRow(row_count)

        table.setItem(row_count, 0, QtWidgets.QTableWidgetItem("總計"))

        item = QtWidgets.QTableWidgetItem(string_utils.xstr(round(self._total_amount)))
        item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        table.setItem(row_count, 1, item)

        item = QtWidgets.QTableWidgetItem(
            string_utils.xstr(round(self._total_commission))
        )
        item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        table.setItem(row_count, 2, item)

    # ------------------------------------------------------------------
    # 匯出 / 圖表 / 病歷
    # ------------------------------------------------------------------
    def _export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]

        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f"{start_date}至{end_date}{self.seller}醫師自費銷售統計表.xlsx",
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

    def _plot_chart(self):
        total_amount = number_utils.get_float(
            self.ui.tableWidget_sale_summary.item(
                self.ui.tableWidget_sale_summary.rowCount() - 1, 2
            ).text()
        )

        series = QtChart.QPieSeries()
        for row_no in range(self.ui.tableWidget_sale_summary.rowCount()):
            medicine_name = self.ui.tableWidget_sale_summary.item(row_no, 0).text()
            amount = number_utils.get_float(
                self.ui.tableWidget_sale_summary.item(row_no, 2).text()
            )
            total_amount -= amount
            if row_no >= 10 or medicine_name == "總計":
                break

            series.append(medicine_name, amount)
            slice = series.slices()[row_no]
            slice.setExploded()
            slice.setLabelVisible()

        if self.ui.tableWidget_sale_summary.rowCount() > 10:
            series.append("其他", total_amount)
            slice = series.slices()[10]
            slice.setExploded()
            slice.setLabelVisible()

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle(f"{self.seller}醫師自費銷售排行榜Top10")
        chart.legend().hide()
        chart.setAnimationOptions(QtChart.QChart.AllAnimations)

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)
        self.chartView.setFixedHeight(400)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def _open_medical_record(self):
        case_key = self.table_widget_doctor_sale.field_value(0)
        if case_key is None:
            return

        self.parent.parent.open_medical_record(case_key)
