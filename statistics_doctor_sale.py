# -*- coding: UTF-8 -*-

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


# 醫師自費銷售統計 2019.05.28
class StatisticsDoctorSale(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDoctorSale, self).__init__(parent)
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

    def start_calculate(self):
        self.ui.tableWidget_doctor_sale.setRowCount(0)
        self._read_data()
        self._insert_return_goods()

        self._calculate_total()
        self._list_sales_summary()
        self._calculate_summary_total()
        self._plot_chart()

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
        if self.doctor != "全部":
            doctor_condition = f' AND cases.Doctor = "{self.doctor}"'

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option)

        sql = f'''
            SELECT
                prescript.*,
                cases.CaseKey, cases.PatientKey, cases.Name, cases.CaseDate, cases.Doctor, cases.TotalFee
            FROM
                prescript
            LEFT JOIN cases
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
            GROUP BY prescript.PrescriptKey
            ORDER BY cases.CaseKey, prescript.PrescriptKey
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows)
        if row_count <= 0:
            return

        self.progress_dialog = QtWidgets.QProgressDialog(
            "自費銷售統計中, 請稍後...", "取消", 0, row_count, self
        )

        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        self.progress_dialog.setValue(0)

        self.table_widget_doctor_sale.set_db_data(sql, self._set_table_data)
        self._insert_discount()
        self._insert_balance()
        self.progress_dialog.setValue(row_count)
        self.progress_dialog.deleteLater()

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

    def _insert_return_goods(self):
        if self.doctor != "全部":  # 退貨無醫師欄位, 個別醫師統計不列退貨
            return

        rows = self._read_return_goods_rows()
        if rows is None:
            return

        # SQL 已按日期由晚到早排序, 先插後面的列不會影響前面的插入位置
        for row in rows:
            return_date = row["ReturnGoodsDate"].strftime("%Y-%m-%d")
            row_no = self._get_return_goods_row_no(return_date)
            self._insert_return_goods_row(row_no, return_date, row)

    def _insert_return_goods_row(self, row_no, return_date, row):
        self.ui.tableWidget_doctor_sale.insertRow(row_no)

        item_name = string_utils.xstr(row["ItemName"])
        amount = number_utils.get_integer(row["Amount"])

        row_data = [
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
        ]
        for col_no in range(len(row_data)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, row_data[col_no])
            self.ui.tableWidget_doctor_sale.setItem(row_no, col_no, item)

            if col_no in [2, 6, 9]:
                align = QtCore.Qt.AlignRight
            else:
                align = QtCore.Qt.AlignLeft

            item.setTextAlignment(align | QtCore.Qt.AlignVCenter)
            item.setForeground(QtGui.QColor("red"))

    def _get_return_goods_row_no(self, return_date):
        # 找到第一筆日期大於退貨日的列, 退貨列插在該日所有銷售之後
        for row_no in range(self.ui.tableWidget_doctor_sale.rowCount()):
            case_date_item = self.ui.tableWidget_doctor_sale.item(row_no, 1)
            if case_date_item is None:
                continue

            if case_date_item.text() > return_date:
                return row_no

        return self.ui.tableWidget_doctor_sale.rowCount()

    def _set_table_data(self, row_no, row):
        self.progress_dialog.setValue(row_no)

        case_key = row["CaseKey"]
        medicine_key = row["MedicineKey"]
        medicine_set = row["MedicineSet"]
        medicine_name = row["MedicineName"]

        pres_days = case_utils.get_pres_days(self.database, case_key, medicine_set)
        if pres_days == 0:
            pres_days = 1

        doctor = string_utils.xstr(row["Doctor"])
        quantity = number_utils.get_float(row["Dosage"])
        price = number_utils.get_float(row["Price"])
        # amount = number_utils.round_up(number_utils.get_float(row['Amount'])) * pres_days

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

        commission_rate = charge_utils.get_commission_rate(
            self.database, medicine_key, doctor
        )
        commission = charge_utils.calc_commission(quantity, amount, commission_rate)

        if commission_rate != "" and "%" not in commission_rate:
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
            doctor,
        ]

        for col_no in range(len(sale_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, sale_row[col_no])
            self.ui.tableWidget_doctor_sale.setItem(row_no, col_no, item)

            if col_no in [2, 5, 6, 8, 9, 10, 11]:
                align = QtCore.Qt.AlignRight
            elif col_no in [7]:
                align = QtCore.Qt.AlignCenter
            else:
                align = QtCore.Qt.AlignLeft

            self.ui.tableWidget_doctor_sale.item(row_no, col_no).setTextAlignment(
                align | QtCore.Qt.AlignVCenter
            )
            if price < 0:
                self.ui.tableWidget_doctor_sale.item(row_no, col_no).setForeground(
                    QtGui.QColor("red")
                )

            if medicine_name == "差額":
                self.ui.tableWidget_doctor_sale.item(row_no, col_no).setForeground(
                    QtGui.QColor("darkgreen")
                )

    def _insert_balance(self):
        row_count = self.ui.tableWidget_doctor_sale.rowCount()
        if row_count <= 0:
            return

        # 第一階段：純讀取，收集每個 case 的 amount 和插入位置
        case_data = {}  # case_key -> {'amount': float, 'insert_row': int}
        last_case_key = self.ui.tableWidget_doctor_sale.item(0, 0).text()

        for row_no in range(row_count):
            case_key_item = self.ui.tableWidget_doctor_sale.item(row_no, 0)
            case_key = case_key_item.text() if case_key_item is not None else ""

            medicine_item = self.ui.tableWidget_doctor_sale.item(row_no, 4)
            medicine_name = medicine_item.text() if medicine_item is not None else ""

            if case_key != "" and case_key != last_case_key:
                # 記錄上一個 case 的插入位置（在它最後一行的下一行）
                case_data[last_case_key]["insert_row"] = row_no
                last_case_key = case_key
                case_data[case_key] = {"amount": 0, "insert_row": row_no}

            if last_case_key not in case_data:
                case_data[last_case_key] = {"amount": 0, "insert_row": 0}

            if medicine_name != "差額":
                amount_item = self.ui.tableWidget_doctor_sale.item(row_no, 9)
                if amount_item is not None:
                    case_data[last_case_key]["amount"] += number_utils.get_float(
                        amount_item.text()
                    )

        # 最後一個 case
        case_data[last_case_key]["insert_row"] = row_count

        # 第二階段：從後往前插入，避免 index 錯位
        for case_key in reversed(list(case_data.keys())):
            data = case_data[case_key]
            self._check_balance_row(data["insert_row"], case_key, data["amount"])

    def _check_balance_row(self, row_no, case_key, amount):
        sql = f"""
            SELECT CaseKey, CaseDate, PatientKey, Name, Doctor, TotalFee FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        total_fee = number_utils.get_float(rows[0]["TotalFee"])
        if amount != total_fee:
            balance = amount - total_fee
            self._insert_balance_row(row_no, row, balance)

    def _insert_balance_row(self, row_no, row, balance):
        self.ui.tableWidget_doctor_sale.insertRow(row_no)
        discount_row = {
            "CaseKey": row["CaseKey"],
            "CaseDate": row["CaseDate"],
            "PatientKey": row["PatientKey"],
            "Name": row["Name"],
            "MedicineName": "差額",
            "MedicineSet": 0,
            "PresDays": 1,
            "Dosage": 1,
            "Unit": "次",
            "Price": -balance,
            "Amount": -balance,
            "MedicineKey": None,
            "Doctor": row["Doctor"],
            "TotalFee": -balance,
        }
        self._set_table_data(row_no, discount_row)

    def _insert_discount(self):
        row_count = (
            self.ui.tableWidget_doctor_sale.rowCount() + self._get_discount_count()
        )
        if row_count <= 0:
            return

        last_patient_key = self.ui.tableWidget_doctor_sale.item(0, 2).text()
        last_case_key = self.ui.tableWidget_doctor_sale.item(0, 0).text()

        for row_no in range(row_count):
            if self.ui.tableWidget_doctor_sale.item(row_no, 2) is None:
                patient_key = 0
            else:
                patient_key = self.ui.tableWidget_doctor_sale.item(row_no, 2).text()

            if patient_key != last_patient_key:
                self._check_discount_row(row_no, last_case_key)

            last_patient_key = patient_key
            last_case_key = self.ui.tableWidget_doctor_sale.item(row_no, 0)
            if last_case_key is not None:
                last_case_key = last_case_key.text()

    # 計算要插入的折扣rows
    def _get_discount_count(self):
        discount_count = 0
        discount_list = []
        for row_no in range(
            self.ui.tableWidget_doctor_sale.rowCount()
        ):  # 計算要插入的折扣rows count
            case_key = self.ui.tableWidget_doctor_sale.item(row_no, 0)
            if case_key is None:
                continue

            sql = f"""
                SELECT CaseKey, DiscountFee, TotalFee FROM cases
                WHERE
                    CaseKey = {case_key.text()} and
                    DiscountFee > 0
            """
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                case_key = rows[0]["CaseKey"]
                if case_key not in discount_list:
                    discount_list.append(case_key)
                    discount_count += 1

        return discount_count

    def _check_discount_row(self, row_no, case_key):
        sql = f"""
            SELECT CaseKey, PatientKey, CaseDate, Name, Doctor, DiscountFee, TotalFee FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        discount_fee = number_utils.get_integer(rows[0]["DiscountFee"])
        if discount_fee > 0:  # 有折扣
            self._insert_discount_row(row_no, rows[0], discount_fee)

    def _insert_discount_row(self, row_no, row, discount_fee):
        self.ui.tableWidget_doctor_sale.insertRow(row_no)
        discount_row = {
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
            "TotalFee": -discount_fee,
        }
        self._set_table_data(row_no, discount_row)

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

    def _calculate_total(self):
        total_amount = 0
        total_commission = 0

        row_count = self.ui.tableWidget_doctor_sale.rowCount()
        for row_no in range(row_count):
            amount = self.ui.tableWidget_doctor_sale.item(row_no, 9)
            if amount is not None:
                total_amount += number_utils.get_float(amount.text())

            commission = self.ui.tableWidget_doctor_sale.item(row_no, 11)
            if commission is not None:
                total_commission += number_utils.get_float(commission.text())

        self.ui.tableWidget_doctor_sale.insertRow(row_count)
        self.ui.tableWidget_doctor_sale.setItem(
            row_count, 4, QtWidgets.QTableWidgetItem("總計")
        )
        total_amount = round(total_amount)
        self.ui.tableWidget_doctor_sale.setItem(
            row_count, 9, QtWidgets.QTableWidgetItem(string_utils.xstr(total_amount))
        )
        self.ui.tableWidget_doctor_sale.item(row_count, 9).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        self.ui.tableWidget_doctor_sale.setItem(
            row_count,
            11,
            QtWidgets.QTableWidgetItem(
                string_utils.xstr(number_utils.round_up(total_commission))
            ),
        )
        self.ui.tableWidget_doctor_sale.item(row_count, 11).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _list_sales_summary(self):
        row_count = self.ui.tableWidget_doctor_sale.rowCount()
        for row_no in range(row_count):
            medicine_name = self.ui.tableWidget_doctor_sale.item(row_no, 4)
            if medicine_name is None:
                continue

            medicine_name = medicine_name.text()
            if medicine_name in ["折扣", "總計", "差額"] or medicine_name.endswith(
                "(退貨)"
            ):
                continue

            quantity = self.ui.tableWidget_doctor_sale.item(row_no, 6)
            if quantity is None:
                quantity = 0
            else:
                quantity = number_utils.get_float(quantity.text())

            amount = self.ui.tableWidget_doctor_sale.item(row_no, 9)
            if amount is None:
                amount = 0
            else:
                amount = number_utils.get_float(amount.text())

            commission = self.ui.tableWidget_doctor_sale.item(row_no, 11)
            if commission is None:
                commission = 0
            else:
                commission = number_utils.get_float(commission.text())

            self._set_to_sale_summary(medicine_name, quantity, amount, commission)

        self.ui.tableWidget_sale_summary.sortItems(2, QtCore.Qt.DescendingOrder)

    def _set_to_sale_summary(self, medicine_name, quantity, amount, commission):
        row_count = self.ui.tableWidget_sale_summary.rowCount()
        medicine_exists = False
        for row_no in range(row_count):
            if medicine_name != self.ui.tableWidget_sale_summary.item(row_no, 0).text():
                continue

            total_quantity = quantity + number_utils.get_integer(
                self.ui.tableWidget_sale_summary.item(row_no, 1).text()
            )
            total_amount = amount + number_utils.get_integer(
                self.ui.tableWidget_sale_summary.item(row_no, 2).text()
            )
            total_commission = commission + number_utils.get_float(
                self.ui.tableWidget_sale_summary.item(row_no, 3).text()
            )

            summary_row = [
                medicine_name,
                number_utils.get_integer(total_quantity),
                number_utils.get_integer(total_amount),
                total_commission,
            ]
            for col_no in range(len(summary_row)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, summary_row[col_no])
                self.ui.tableWidget_sale_summary.setItem(row_no, col_no, item)
                if col_no in [1, 2, 3]:
                    self.ui.tableWidget_sale_summary.item(
                        row_no, col_no
                    ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                if total_amount < 0:
                    self.ui.tableWidget_sale_summary.item(row_no, col_no).setForeground(
                        QtGui.QColor("red")
                    )

            medicine_exists = True
            break

        if not medicine_exists:
            summary_row = [medicine_name, quantity, amount, commission]
            self.ui.tableWidget_sale_summary.insertRow(row_count)

            for col_no in range(len(summary_row)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, summary_row[col_no])
                self.ui.tableWidget_sale_summary.setItem(row_count, col_no, item)
                if col_no in [1, 2, 3]:
                    self.ui.tableWidget_sale_summary.item(
                        row_count, col_no
                    ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _calculate_summary_total(self):
        total_amount = 0
        total_commission = 0

        row_count = self.ui.tableWidget_sale_summary.rowCount()
        for row_no in range(row_count):
            amount = self.ui.tableWidget_sale_summary.item(row_no, 2)
            if amount is not None:
                total_amount += number_utils.get_float(amount.text())

            commission = self.ui.tableWidget_sale_summary.item(row_no, 3)
            if commission is not None:
                total_commission += number_utils.get_float(commission.text())

        self.ui.tableWidget_sale_summary.insertRow(row_count)
        self.ui.tableWidget_sale_summary.setItem(
            row_count, 0, QtWidgets.QTableWidgetItem("總計")
        )
        total_amount = round(total_amount)
        self.ui.tableWidget_sale_summary.setItem(
            row_count, 2, QtWidgets.QTableWidgetItem(string_utils.xstr(total_amount))
        )
        self.ui.tableWidget_sale_summary.item(row_count, 2).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        self.ui.tableWidget_sale_summary.setItem(
            row_count,
            3,
            QtWidgets.QTableWidgetItem(string_utils.xstr(total_commission)),
        )
        self.ui.tableWidget_sale_summary.item(row_count, 3).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
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
        chart.setTitle(f"{self.doctor}醫師自費銷售排行榜Top10")
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
