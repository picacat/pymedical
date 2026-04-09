# -*- coding: UTF-8 -*-

from PyQt5 import QtChart, QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (
    class_utils,
    export_utils,
    number_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 推拿業績明細 2020.11.04
class StatisticsMassagerList(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsMassagerList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.massager = args[5]
        self.only_traditional_massage = args[6]
        self.ui = None

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_MASSAGER_LIST, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_massager_list = class_utils.get_table_widget(
            self.ui.tableWidget_massager_list, self.database
        )
        self.table_widget_massager_list.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        width = [100, 130, 70, 90, 50, 150, 90, 50, 90, 100]
        self.table_widget_massager_list.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_massager_list.doubleClicked.connect(
            self._open_medical_record
        )
        self.ui.toolButton_export_to_excel.clicked.connect(self._export_to_excel)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_massager_list.setRowCount(0)
        self._read_data()
        self._calculate_total()
        # self._plot_chart()

    def _read_data(self):
        only_traditional_massage_condition = ""
        if self.only_traditional_massage:
            only_traditional_massage_condition = ' AND TreatType = "民俗調理"'

        period_condition = ""
        if self.period != "全部":
            period_condition = f' AND Period = "{self.period}"'

        massager_condition = ""
        if self.massager != "全部":
            massager_condition = (
                f' AND Massager = "{self.massager}" AND LENGTH(Massager) > 0'
            )

        massage_fee_condition = ""
        if self.system_settings.field("院所名稱") == "耀康中醫診所":
            massage_fee_condition = " AND SMassageFee > 50"

        sql = f'''
            SELECT
               CaseKey, PatientKey, Name, CaseDate, InsType, TreatType, Card, Continuance, Massager, SMassageFee
            FROM
                cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                Massager IS NOT NULL AND LENGTH(Massager) > 0
                {massage_fee_condition}
                {only_traditional_massage_condition}
                {period_condition}
                {massager_condition}
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows)
        if row_count <= 0:
            return

        self.progress_dialog = QtWidgets.QProgressDialog(
            "推拿資料統計中, 請稍後...", "取消", 0, row_count, self
        )

        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        self.progress_dialog.setValue(0)

        self.table_widget_massager_list.set_db_data(sql, self._set_table_data)
        self.progress_dialog.setValue(row_count)
        self.progress_dialog.deleteLater()

    def _set_table_data(self, row_no, row):
        self.progress_dialog.setValue(row_no)
        case_key = row["CaseKey"]
        ins_type = string_utils.xstr(row["InsType"])
        treat_type = string_utils.xstr(row["TreatType"])
        massage_fee = number_utils.get_integer(row["SMassageFee"])

        massager_row = [
            string_utils.xstr(case_key),
            string_utils.xstr(row["CaseDate"].date()),
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            ins_type,
            string_utils.xstr(row["TreatType"]),
            string_utils.xstr(row["Card"]),
            string_utils.xstr(row["Continuance"]),
            string_utils.xstr(row["Massager"]),
            massage_fee,
        ]

        for col_no in range(len(massager_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, massager_row[col_no])
            self.ui.tableWidget_massager_list.setItem(row_no, col_no, item)

            if col_no in [2, 9]:
                align = QtCore.Qt.AlignRight
            elif col_no in [4, 7]:
                align = QtCore.Qt.AlignCenter
            else:
                align = QtCore.Qt.AlignLeft

            self.ui.tableWidget_massager_list.item(row_no, col_no).setTextAlignment(
                align | QtCore.Qt.AlignVCenter
            )

            if treat_type in ["自購"]:
                self.ui.tableWidget_massager_list.item(row_no, col_no).setForeground(
                    QtGui.QColor("darkgreen")
                )
            elif ins_type in ["自費"]:
                self.ui.tableWidget_massager_list.item(row_no, col_no).setForeground(
                    QtGui.QColor("blue")
                )

    def export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f"{start_date}至{end_date}{self.massager}醫師自費銷售統計表.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_massager_list, [0], [2, 5, 6, 8, 9, 11]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>醫師自費銷售統計檔{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def _calculate_total(self):
        total_amount = 0

        row_count = self.ui.tableWidget_massager_list.rowCount()
        for row_no in range(row_count):
            amount = self.ui.tableWidget_massager_list.item(row_no, 9)
            if amount is not None:
                total_amount += number_utils.get_float(amount.text())

        self.ui.tableWidget_massager_list.insertRow(row_count)
        self.ui.tableWidget_massager_list.setItem(
            row_count, 1, QtWidgets.QTableWidgetItem("總計")
        )
        total_amount = round(total_amount)
        self.ui.tableWidget_massager_list.setItem(
            row_count, 9, QtWidgets.QTableWidgetItem(string_utils.xstr(total_amount))
        )
        self.ui.tableWidget_massager_list.item(row_count, 9).setTextAlignment(
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
        chart.setTitle(f"{self.massager}醫師自費銷售排行榜Top10")
        chart.legend().hide()
        chart.setAnimationOptions(QtChart.QChart.AllAnimations)

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedHeight(400)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def _open_medical_record(self):
        case_key = self.table_widget_massager_list.field_value(0)
        if case_key is None:
            return

        self.parent.parent.open_medical_record(case_key)

    # 匯出Excel 耀康
    def _export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "資料匯出",
            "推拿業績明細.xlsx",
            "excel檔案 (*.xlsx)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_massager_list, [0]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )
