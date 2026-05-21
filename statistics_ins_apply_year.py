# -*- coding: UTF-8 -*-

import os

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtChart import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QValueAxis,
)
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (
    class_utils,
    dialog_utils,
    export_utils,
    number_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 健保申報分列項目表 2025-05-14
class StatisticsInsApplyYear(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsInsApplyYear, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.sql = None

        self._set_ui()
        self._set_signal()

        self.dialog_setting = {
            "dialog_executed": False,
            "year": None,
        }

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_INS_APPLY_YEAR, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_ins_apply = class_utils.get_table_widget(
            self.ui.tableWidget_ins_apply, self.database
        )
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.action_requery.triggered.connect(self.open_dialog)
        self.ui.action_close.triggered.connect(self.close_form)
        self.ui.action_export_to_excel.triggered.connect(self._export_to_excel)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 100, 110, 110, 90, 110, 110, 110, 110]
        self.table_widget_ins_apply.set_table_heading_width(width)

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_date_picker(
            self, self.database, self.system_settings, "by_year"
        )

        if self.dialog_setting["dialog_executed"]:
            dialog.ui.comboBox_year.setCurrentText(self.dialog_setting["year"])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        year = dialog.ui.comboBox_year.currentText()

        self.dialog_setting["dialog_executed"] = True
        self.dialog_setting["year"] = year

        dialog.deleteLater()

        self._start_calculate()
        self._create_bar_chart()

    def _start_calculate(self):
        # self.ui.tableWidget_ins_apply.setRowCount(0)
        # year = int(self.dialog_setting['year']) - 1911
        # apply_date_list = [f'{year-1}12']
        # for i in range(1, 12):
        #     apply_date_list.append(f'{year}{i:02}')

        self.ui.tableWidget_ins_apply.setRowCount(0)
        year = int(self.dialog_setting["year"]) - 1911

        # 直接產生今年 01 到 12 月的字串列表
        apply_date_list = [f"{year}{i:02}" for i in range(1, 13)]

        for apply_date in apply_date_list:
            self._set_ins_apply_data(apply_date)

        self._calculate_total()

    def _set_ins_apply_data(self, apply_date):
        sql = f'''
            SELECT
                COUNT(*) AS record_count,
                COUNT(CASE WHEN DiagFee > 0 THEN 1 END) AS total_diag_count,
                SUM(DiagFee) AS total_diag_fee,
                SUM(DrugFee) AS total_drug_fee,
                SUM(PharmacyFee) AS total_pharmacy_fee,
                SUM(TreatFee) AS total_treat_fee,
                SUM(InsTotalFee) AS total_ins_total_fee,
                SUM(ShareFee) AS total_share_fee,
                SUM(InsApplyFee) AS total_ins_apply_fee
            FROM
                insapply
            WHERE
                ApplyDate = "{apply_date}"
        '''
        row = self.database.select_record(sql)[0]
        if row["record_count"] == 0:
            return

        ins_apply_data = [
            apply_date,
            row["total_diag_count"],
            row["total_diag_fee"],
            row["total_drug_fee"],
            row["total_pharmacy_fee"],
            row["total_treat_fee"],
            row["total_ins_total_fee"],
            row["total_share_fee"],
            row["total_ins_apply_fee"],
        ]
        self._set_table_data(ins_apply_data)

    def _set_table_data(self, ins_apply_data):
        row_no = self.ui.tableWidget_ins_apply.rowCount()
        self.ui.tableWidget_ins_apply.setRowCount(
            self.ui.tableWidget_ins_apply.rowCount() + 1
        )
        for col_no in range(len(ins_apply_data)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, string_utils.xstr(ins_apply_data[col_no]))
            self.ui.tableWidget_ins_apply.setItem(row_no, col_no, item)
            if col_no in [0]:
                self.ui.tableWidget_ins_apply.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            else:
                self.ui.tableWidget_ins_apply.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _calculate_total(self):
        total_diag_count, diag_fee, drug_fee, pharmacy_fee, treat_fee = 0, 0, 0, 0, 0
        ins_apply_total, share_fee, ins_apply_fee = 0, 0, 0

        for row_no in range(self.ui.tableWidget_ins_apply.rowCount()):
            total_diag_count += number_utils.get_integer(
                self.ui.tableWidget_ins_apply.item(row_no, 1).text()
            )
            diag_fee += number_utils.get_integer(
                self.ui.tableWidget_ins_apply.item(row_no, 2).text()
            )
            drug_fee += number_utils.get_integer(
                self.ui.tableWidget_ins_apply.item(row_no, 3).text()
            )
            pharmacy_fee += number_utils.get_integer(
                self.ui.tableWidget_ins_apply.item(row_no, 4).text()
            )
            treat_fee += number_utils.get_integer(
                self.ui.tableWidget_ins_apply.item(row_no, 5).text()
            )
            ins_apply_total += number_utils.get_integer(
                self.ui.tableWidget_ins_apply.item(row_no, 6).text()
            )
            share_fee += number_utils.get_integer(
                self.ui.tableWidget_ins_apply.item(row_no, 7).text()
            )
            ins_apply_fee += number_utils.get_integer(
                self.ui.tableWidget_ins_apply.item(row_no, 8).text()
            )

        total_row = [
            "合計",
            total_diag_count,
            diag_fee,
            drug_fee,
            pharmacy_fee,
            treat_fee,
            ins_apply_total,
            share_fee,
            ins_apply_fee,
        ]
        self._set_table_data(total_row)

    def _create_bar_chart(self):
        if self.ui.tableWidget_ins_apply.rowCount() <= 1:
            return

        # 清除舊圖表
        for i in reversed(range(self.ui.horizontalLayout_age_group.count())):
            item = self.ui.horizontalLayout_age_group.itemAt(i)
            widget = item.widget()
            if widget and widget != self.ui.tableWidget_ins_apply:
                widget.setParent(None)

        # 取得 tableWidget_ins_apply 的資料
        data_rows = []
        row_count = self.ui.tableWidget_ins_apply.rowCount()
        for row in range(row_count - 1):  # 最後一列是「合計」，不統計
            month = self.ui.tableWidget_ins_apply.item(row, 0).text()  # 申報年月
            item_text = (
                self.ui.tableWidget_ins_apply.item(row, 8)
                .text()
                .replace(",", "")
                .strip()
            )
            apply_fee = int(item_text) if item_text.isdigit() else 0
            data_rows.append({"month": month, "fee": apply_fee})

        # 建立 BarSet：健保申請
        fee_set = QBarSet("健保申請")
        months = []
        for row in data_rows:
            months.append(row["month"])
            fee_set << row["fee"]

        # 建立 BarSeries 並加入資料
        series = QBarSeries()
        series.append(fee_set)
        series.setLabelsVisible(True)

        # 建立 Chart
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("健保申請統計")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        # X 軸：分類軸（申報年月）
        axis_x = QBarCategoryAxis()
        axis_x.append(months)
        chart.setAxisX(axis_x, series)

        # Y 軸：數值軸
        max_y = max(row["fee"] for row in data_rows)
        axis_y = QValueAxis()
        axis_y.setRange(0, max_y * 1.1)
        axis_y.setTitleText("健保申請金額")
        chart.setAxisY(axis_y, series)

        # 建立 Chart View 並設定寬度
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setFixedWidth(700)

        # 加入到 layout
        self.ui.horizontalLayout_age_group.addWidget(chart_view)

    def _export_to_excel(self):
        last_dir = system_utils.get_last_directory("健保申報分列項目表")
        options = QFileDialog.Options()
        excel_filename = os.path.join(
            last_dir, f"{self.dialog_setting['year']}年度健保申報分項表.xlsx"
        )
        excel_filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出分項表",
            excel_filename,
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_filename:
            return

        export_utils.export_table_widget_to_excel(
            excel_filename,
            self.ui.tableWidget_ins_apply,
            None,
            [1, 2, 3, 4, 5, 6, 7, 8],
            f"{self.dialog_setting['year']}健保申報年度分列項目表",
        )
        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>{excel_filename}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )
