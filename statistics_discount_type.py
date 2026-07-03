# -*- coding: UTF-8 -*-

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

from libs import (
    class_utils,
    dialog_utils,
    export_utils,
    personnel_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 病患優待身份統計
class StatisticsDiscountType(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDiscountType, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.sql = None
        self.statistics_start_date = None  # None 表示統計所有日期
        self.statistics_end_date = None

        self._set_ui()
        self._set_signal()

        self.program_name = "病患優待身份統計"
        self.user_name = system_utils.get_user_name(self.system_settings)

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DISCOUNT_TYPE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_discount_type = class_utils.get_table_widget(
            self.ui.tableWidget_discount_type, self.database
        )
        self.table_widget_patient_list = class_utils.get_table_widget(
            self.ui.tableWidget_patient_list, self.database
        )
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.action_requery.triggered.connect(self.open_dialog)
        self.ui.action_close.triggered.connect(self.close_form)
        self.ui.action_export_to_excel.triggered.connect(self._export_to_excel)
        self.ui.tableWidget_patient_list.doubleClicked.connect(self.open_patient_record)
        self.ui.tableWidget_discount_type.itemSelectionChanged.connect(
            self._discount_type_selection_changed
        )

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [200, 100, 100]
        self.table_widget_discount_type.set_table_heading_width(width)

        width = [90, 100, 260]
        self.table_widget_patient_list.set_table_heading_width(width)

    def open_dialog(self):
        dialog = dialog_utils.get_dialog_date_period(
            self, self.database, self.system_settings
        )
        dialog.set_title("請選擇病歷統計日期")
        if not dialog.exec_():
            dialog.deleteLater()
            return

        # 重新填表時先擋掉 selection 信號, 避免途中觸發 _discount_type_selection_changed
        self.ui.tableWidget_discount_type.blockSignals(True)

        if dialog.radioButton_all.isChecked():
            self.statistics_start_date = None
            self.statistics_end_date = None
            self.ui.label_period.setText("統計期間: 所有日期")
            rows = self._calculate_discount_type_all()
        else:
            start_date = dialog.ui.dateEdit_start_date
            end_date = dialog.ui.dateEdit_end_date
            self.statistics_start_date = start_date.date().toString("yyyy-MM-dd")
            self.statistics_end_date = end_date.date().toString("yyyy-MM-dd")
            self.ui.label_period.setText(
                f"統計期間:{self.statistics_start_date} 至 {self.statistics_end_date}"
            )
            rows = self._calculate_discount_type_period(
                start_date.date(), end_date.date()
            )

        self.ui.tableWidget_discount_type.blockSignals(False)

        # 預設選取第一列, 觸發 _discount_type_selection_changed 填入病患門診明細
        self.ui.tableWidget_patient_list.setRowCount(0)
        if len(rows) > 0:
            self.ui.tableWidget_discount_type.selectRow(0)

        try:
            self.create_bar_chart(rows)
        except Exception:
            pass

    # 將統計結果填入 tableWidget_discount_type
    # column[0]: 優待身份  column[1]: 人數  column[2]: 門診次數
    def _set_discount_type_table(self, rows):
        self.ui.tableWidget_discount_type.setRowCount(len(rows))
        for row_no, row in enumerate(rows):
            self.ui.tableWidget_discount_type.setItem(
                row_no,
                0,
                QtWidgets.QTableWidgetItem(string_utils.xstr(row["DiscountType"])),
            )

            item = QtWidgets.QTableWidgetItem(str(row["count"]))
            item.setTextAlignment(QtCore.Qt.AlignRight)
            self.ui.tableWidget_discount_type.setItem(row_no, 1, item)

            item = QtWidgets.QTableWidgetItem(str(row["case_count"]))
            item.setTextAlignment(QtCore.Qt.AlignRight)
            self.ui.tableWidget_discount_type.setItem(row_no, 2, item)

    def _calculate_discount_type_period(self, start_date, end_date):
        sql = f'''
            SELECT
                patient.DiscountType,
                COUNT(DISTINCT cases.PatientKey) AS count,
                COUNT(*) AS case_count
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                DATE(cases.CaseDate) BETWEEN "{start_date.toString("yyyy-MM-dd")}" AND "{end_date.toString("yyyy-MM-dd")}" AND
                patient.DiscountType IS NOT NULL AND LENGTH(patient.DiscountType) > 0
            GROUP BY patient.DiscountType
        '''
        rows = self.database.select_record(sql)
        self._set_discount_type_table(rows)

        return rows

    def _calculate_discount_type_all(self):
        sql = """
            SELECT
                patient.DiscountType,
                COUNT(DISTINCT patient.PatientKey) AS count,
                COUNT(cases.CaseKey) AS case_count
            FROM patient
                LEFT JOIN cases ON cases.PatientKey = patient.PatientKey
            WHERE
                patient.DiscountType IS NOT NULL AND LENGTH(patient.DiscountType) > 0
            GROUP BY patient.DiscountType
        """

        rows = self.database.select_record(sql)
        self._set_discount_type_table(rows)

        return rows

    def create_bar_chart(self, data_rows):
        # 清除舊的 chart（若有）
        # 刪除舊圖表（如果已經有）
        for i in reversed(range(self.ui.horizontalLayout_trace.count())):
            item = self.ui.horizontalLayout_trace.itemAt(i)
            widget = item.widget()
            if widget and widget not in [
                self.ui.tableWidget_discount_type,
                self.ui.tableWidget_patient_list,
            ]:
                widget.setParent(None)

        # 統計總次數
        total = sum([row["count"] for row in data_rows])

        # 建立 QBarSet
        bar_set = QBarSet("人數")
        bar_set_cases = QBarSet("門診次數")
        contents = []
        for row in data_rows:
            contents.append(row["DiscountType"])
            bar_set.append(row["count"])
            bar_set_cases.append(row["case_count"])

        # 建立 QBarSeries 並加進 QBarSet
        series = QBarSeries()
        series.append(bar_set)
        series.append(bar_set_cases)
        series.setLabelsVisible(True)  # 顯示數字
        series.setLabelsPosition(QBarSeries.LabelsOutsideEnd)  # 顯示在條外側

        # 建立 Chart
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("病患優待身份 - 人數/門診次數統計")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        # 分類軸（Y軸）
        axis_y = QBarCategoryAxis()
        axis_y.append(contents)
        chart.setAxisX(axis_y, series)
        axis_y.setLabelsAngle(-30)  # 或 -45 看效果

        # 數值軸（X軸）
        max_value = max(
            max(row["count"] for row in data_rows),
            max(row["case_count"] for row in data_rows),
        )
        axis_x = QValueAxis()
        axis_x.setRange(0, max_value + 1)
        axis_x.setTitleText("次數")
        chart.setAxisY(axis_x, series)

        # 建立 Chart View
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)

        # 加入 layout（在 tableWidget_discount_type 右邊）
        self.ui.horizontalLayout_trace.addWidget(chart_view)

    # tableWidget_discount_type 選取列改變時, 依該優待身份列出病患門診明細
    def _discount_type_selection_changed(self):
        row_no = self.ui.tableWidget_discount_type.currentRow()
        if row_no < 0:
            return

        item = self.ui.tableWidget_discount_type.item(row_no, 0)
        if item is None:
            return

        discount_type = item.text()
        if not discount_type:
            return

        self._set_patient_case_list(discount_type)

    # 列出指定優待身份的病患在統計期間內的每一筆門診
    # column[0]: 病歷號  column[1]: 姓名  column[2]: 門診日期
    def _set_patient_case_list(self, discount_type):
        date_condition = ""
        if self.statistics_start_date is not None:
            date_condition = f'''
                AND DATE(cases.CaseDate)
                    BETWEEN "{self.statistics_start_date}" AND "{self.statistics_end_date}"
            '''

        sql = f'''
            SELECT patient.PatientKey, patient.Name, cases.CaseDate
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                patient.DiscountType = "{discount_type}"
                {date_condition}
            ORDER BY patient.PatientKey, cases.CaseDate
        '''
        rows = self.database.select_record(sql)
        self.ui.tableWidget_patient_list.setRowCount(len(rows))

        for row_no, row in enumerate(rows):
            patient_key = row["PatientKey"]
            name = string_utils.xstr(row["Name"])
            case_date = row["CaseDate"]
            if hasattr(case_date, "strftime"):
                case_date = case_date.strftime("%Y-%m-%d")
            else:
                case_date = string_utils.xstr(case_date)

            self.ui.tableWidget_patient_list.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(string_utils.xstr(patient_key))
            )
            self.ui.tableWidget_patient_list.setItem(
                row_no, 1, QtWidgets.QTableWidgetItem(name)
            )

            item = QtWidgets.QTableWidgetItem(case_date)
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.ui.tableWidget_patient_list.setItem(row_no, 2, item)

        self.ui.tableWidget_patient_list.resizeRowsToContents()

    def _get_row_no(self, patient_key):
        for row_no in range(self.ui.tableWidget_patient_list.rowCount()):
            if self.ui.tableWidget_patient_list.item(
                row_no, 0
            ).text() == string_utils.xstr(patient_key):
                return row_no

        return None

    def open_patient_record(self):
        if (
            self.user_name != "超級使用者"
            and personnel_utils.get_permission(
                self.database, self.program_name, "調閱資料", self.user_name
            )
            != "Y"
        ):
            return

        patient_key = self.table_widget_patient_list.field_value(0)
        self.parent.open_patient_record(patient_key, "病患查詢")

    def _export_to_excel(self):
        options = QtWidgets.QFileDialog.Options()
        excel_file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.parent,
            "資料匯出",
            "病患優待統計.xlsx",
            "excel檔案 (*.xlsx)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_discount_type, numeric_cell=[1, 2]
        )

        system_utils.show_message_box(
            QtWidgets.QMessageBox.Information,
            "資料匯出完成",
            f"<h3>{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )
