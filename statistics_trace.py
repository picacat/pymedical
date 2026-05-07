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
    personnel_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 何處得知本診所統計
class StatisticsTrace(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsTrace, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.sql = None

        self._set_ui()
        self._set_signal()

        self.program_name = "何處得知本診所統計"
        self.user_name = system_utils.get_user_name(self.system_settings)

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_TRACE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_trace = class_utils.get_table_widget(
            self.ui.tableWidget_trace, self.database
        )
        self.table_widget_patient_list = class_utils.get_table_widget(
            self.ui.tableWidget_patient_list, self.database
        )
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.action_requery.triggered.connect(self.open_dialog)
        self.ui.action_close.triggered.connect(self.close_form)
        self.ui.tableWidget_patient_list.doubleClicked.connect(self.open_patient_record)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [200, 100]
        self.table_widget_trace.set_table_heading_width(width)

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

        if dialog.radioButton_all.isChecked():
            self.ui.label_period.setText("統計期間: 所有日期")
            rows = self._calculate_trace_all()
            self._set_patient_table_all()
        else:
            start_date = dialog.ui.dateEdit_start_date
            end_date = dialog.ui.dateEdit_end_date
            self.ui.label_period.setText(
                f"""統計期間:{start_date.date().toString("yyyy-MM-dd")} 至 {end_date.date().toString("yyyy-MM-dd")}"""
            )
            rows = self._calculate_trace_period(start_date.date(), end_date.date())
            self._set_patient_table_duration(start_date.date(), end_date.date())

        try:
            self.create_bar_chart(rows)
        except Exception:
            pass

    def _calculate_trace_period(self, start_date, end_date):
        sql = f'''
            SELECT CaseDate, PatientKey FROM cases
            WHERE
                DATE(CaseDate) BETWEEN "{start_date.toString("yyyy-MM-dd")}" AND "{end_date.toString("yyyy-MM-dd")}"
            GROUP BY PatientKey ORDER BY PatientKey
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return rows

        patient_list = [[row["CaseDate"], row["PatientKey"]] for row in rows]
        if not patient_list:
            return []

        patient_key_list = [str(row[1]) for row in patient_list]
        if not patient_key_list:
            return []

        patient_keys_sql = f"({', '.join(patient_key_list)})"

        sql = f"""
            SELECT patient.PatientKey, patient.Name, Content, COUNT(*) AS count FROM patient_extension
                LEFT join patient ON patient.PatientKey = patient_extension.PatientKey
            WHERE
                patient_extension.PatientKey IN {patient_keys_sql} AND
                ExtensionType IN ('從何處得知本診所', '從何處得知本診所備註')
            GROUP BY Content ORDER BY count DESC
        """

        rows = self.database.select_record(sql)
        self.ui.tableWidget_trace.setRowCount(len(rows))
        for row_no, row in enumerate(rows):
            self.ui.tableWidget_trace.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(string_utils.xstr(row["Content"]))
            )

            item = QtWidgets.QTableWidgetItem(str(row["count"]))
            item.setTextAlignment(QtCore.Qt.AlignRight)
            self.ui.tableWidget_trace.setItem(row_no, 1, item)

        return rows

    def _calculate_trace_all(self):
        sql = """
            SELECT patient.PatientKey, patient.Name, Content, COUNT(*) AS count FROM patient_extension
                LEFT join patient ON patient.PatientKey = patient_extension.PatientKey
            WHERE
                ExtensionType IN ('從何處得知本診所', '從何處得知本診所備註')
            GROUP BY Content ORDER BY count DESC
        """

        rows = self.database.select_record(sql)

        self.ui.tableWidget_trace.setRowCount(len(rows))
        for row_no, row in enumerate(rows):
            self.ui.tableWidget_trace.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(string_utils.xstr(row["Content"]))
            )

            item = QtWidgets.QTableWidgetItem(str(row["count"]))
            item.setTextAlignment(QtCore.Qt.AlignRight)
            self.ui.tableWidget_trace.setItem(row_no, 1, item)

        return rows

    def create_bar_chart(self, data_rows):
        # 清除舊的 chart（若有）
        # 刪除舊圖表（如果已經有）
        for i in reversed(range(self.ui.horizontalLayout_trace.count())):
            item = self.ui.horizontalLayout_trace.itemAt(i)
            widget = item.widget()
            if widget and widget not in [
                self.ui.tableWidget_trace,
                self.ui.tableWidget_patient_list,
            ]:
                widget.setParent(None)

        # 統計總次數
        total = sum([row["count"] for row in data_rows])

        # 建立 QBarSet
        bar_set = QBarSet("次數")
        contents = []
        for row in data_rows:
            contents.append(row["Content"])
            bar_set.append(row["count"])

        # 建立 QBarSeries 並加進 QBarSet
        series = QBarSeries()
        series.append(bar_set)
        series.setLabelsVisible(True)  # 顯示數字
        series.setLabelsPosition(QBarSeries.LabelsOutsideEnd)  # 顯示在條外側

        # 建立 Chart
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("從何處得知本診所 - 次數統計")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        # 分類軸（Y軸）
        axis_y = QBarCategoryAxis()
        axis_y.append(contents)
        chart.setAxisX(axis_y, series)
        axis_y.setLabelsAngle(-30)  # 或 -45 看效果

        # 數值軸（X軸）
        axis_x = QValueAxis()
        axis_x.setRange(0, max(row["count"] for row in data_rows) + 1)
        axis_x.setTitleText("次數")
        chart.setAxisY(axis_x, series)

        # 建立 Chart View
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)

        # 加入 layout（在 tableWidget_trace 右邊）
        self.ui.horizontalLayout_trace.addWidget(chart_view)

    def _set_patient_table_all(self):
        sql = """
            SELECT patient.PatientKey, patient.Name FROM patient
                LEFT join patient_extension ON patient_extension.PatientKey = patient.PatientKey
            WHERE
                ExtensionType IN ('從何處得知本診所', '從何處得知本診所備註')
            GROUP BY patient.PatientKey ORDER BY patient.PatientKey
        """
        rows = self.database.select_record(sql)
        self.ui.tableWidget_patient_list.setRowCount(len(rows))

        for row_no, row in enumerate(rows):
            patient_key = row["PatientKey"]
            name = string_utils.xstr(row["Name"])
            content = self._get_content(patient_key)

            self.ui.tableWidget_patient_list.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(string_utils.xstr(patient_key))
            )
            self.ui.tableWidget_patient_list.setItem(
                row_no, 1, QtWidgets.QTableWidgetItem(name)
            )
            self.ui.tableWidget_patient_list.setItem(
                row_no, 2, QtWidgets.QTableWidgetItem(content)
            )

        self.ui.tableWidget_patient_list.resizeRowsToContents()

    def _set_patient_table_duration(self, start_date, end_date):
        sql = f'''
            SELECT patient.PatientKey, patient.Name FROM patient
                LEFT join patient_extension ON patient_extension.PatientKey = patient.PatientKey
                LEFT join cases ON cases.PatientKey = patient.PatientKey
            WHERE
                ExtensionType IN ('從何處得知本診所', '從何處得知本診所備註') AND
                DATE(CaseDate) BETWEEN "{start_date.toString("yyyy-MM-dd")}" AND "{end_date.toString("yyyy-MM-dd")}"
            GROUP BY patient.PatientKey ORDER BY patient.PatientKey
        '''
        rows = self.database.select_record(sql)
        self.ui.tableWidget_patient_list.setRowCount(len(rows))

        for row_no, row in enumerate(rows):
            patient_key = row["PatientKey"]
            name = string_utils.xstr(row["Name"])
            content = self._get_content(patient_key)

            self.ui.tableWidget_patient_list.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(string_utils.xstr(patient_key))
            )
            self.ui.tableWidget_patient_list.setItem(
                row_no, 1, QtWidgets.QTableWidgetItem(name)
            )
            self.ui.tableWidget_patient_list.setItem(
                row_no, 2, QtWidgets.QTableWidgetItem(content)
            )

        self.ui.tableWidget_patient_list.resizeRowsToContents()

    def _get_content(self, patient_key):
        sql = f"""
            SELECT Content FROM patient_extension
            WHERE
                PatientKey = {patient_key} AND
                ExtensionType IN ('從何處得知本診所', '從何處得知本診所備註')
            GROUP BY PatientExtensionKey
        """
        rows = self.database.select_record(sql)
        content_list = [string_utils.xstr(row["Content"]) for row in rows]
        content = ", ".join(content_list)

        return content

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
