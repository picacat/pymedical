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


# 醫師月報表 2022.05.12
class StatisticsDoctorMonthlyPersonCount2(QtWidgets.QMainWindow):
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
        # self._set_heading(
        #     "傷科類給藥", ["<=3天", "4-7天", "8-14天", ">=15天", "人數", "金額"]
        # )
        # self._set_heading("一般針灸", ["首次", "2-6次", "人數", "金額"])
        # self._set_heading("中度複雜性針灸", ["首次", "2-6次", "人數", "金額"])
        # self._set_heading("高度複雜性針灸", ["起始次", "後續治療", "人數", "金額"])
        # self._set_heading("一般傷科", ["首次", "2-6次", "人數", "金額"])
        # self._set_heading("中度複雜性傷科", ["人數", "金額"])
        # self._set_heading("高度複雜性傷科", ["人數", "金額"])

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
        doctor_condition = ""
        if self.doctor != "全部":
            doctor_condition = f' AND cases.Doctor = "{self.doctor}"'

        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                InsType = "健保" AND
                (Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
                (Share NOT IN ("山地離島")) AND
                (Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡")
                {doctor_condition}
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

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
            case_date = row["CaseDate"].strftime("%m/%d")
            progress_dialog.setValue(i)
            row_no = self._get_row_no(case_date)
            if row_no is None:
                continue

            treatment = string_utils.xstr(row["Treatment"])
            course = number_utils.get_integer(row["Continuance"])
            pres_days = case_utils.get_pres_days(self.database, row["CaseKey"])

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

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()

    def _set_value(self, row_no, course, col_no1, col_no2):
        if course <= 1:
            col_no = col_no1
        else:
            col_no = col_no2

        case_count = (
            number_utils.get_integer(
                self.ui.tableWidget_doctor_monthly.item(row_no, col_no).text()
            )
            + 1
        )
        self._set_item_data(row_no, col_no, case_count)

    def _set_internal_cases(self, row_no):
        col_no = 1

        case_count = (
            number_utils.get_integer(
                self.ui.tableWidget_doctor_monthly.item(row_no, col_no).text()
            )
            + 1
        )
        self._set_item_data(row_no, col_no, case_count)

    def _set_item_data(self, row_no, col_no, value):
        item = self.ui.tableWidget_doctor_monthly.item(row_no, col_no)
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
                heading = self.ui.tableWidget_doctor_monthly.item(1, col_no).text()
                if heading == "金額":
                    fee = number_utils.get_integer(
                        self.ui.tableWidget_doctor_monthly.item(row_no, col_no).text()
                    )
                    total_fee += fee
                elif heading == "人數":
                    case_count = number_utils.get_integer(
                        self.ui.tableWidget_doctor_monthly.item(row_no, col_no).text()
                    )
                    total_case_count += case_count

            self._set_item_data(row_no, case_col_no, total_case_count)
            self._set_item_data(row_no, fee_col_no, total_fee)

    def _calculate_total(self):
        row_count = self.ui.tableWidget_doctor_monthly.rowCount()
        total_field_row_no = row_count - 1

        for col_no in range(1, self.ui.tableWidget_doctor_monthly.columnCount()):
            total_fee = 0
            for row_no in range(2, row_count - 1):
                value = number_utils.get_integer(
                    self.ui.tableWidget_doctor_monthly.item(row_no, col_no).text()
                )
                total_fee += value

            self._set_item_data(total_field_row_no, col_no, total_fee)
