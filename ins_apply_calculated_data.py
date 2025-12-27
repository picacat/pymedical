# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import export_utils
from libs import personnel_utils


# 申報統計 2018.11.01
class InsApplyCalculatedData(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(InsApplyCalculatedData, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ins_calculated_table = args[2]
        self.ui = None
        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_ins_calculated_table()

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INS_APPLY_CALCULATED_DATA, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_ins_apply_data = class_utils.get_table_widget(
            self.ui.tableWidget_ins_apply_data, self.database
        )
        self._set_table_width()
        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.toolButton_export_to_excel.setEnabled(False)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [
            90, 90, 150, 70, 70, 80, 80, 90, 100,
            100, 100, 100, 100, 100, 85, 85, 85, 85, 85, 85, 85,
        ]
        self.table_widget_ins_apply_data.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_to_excel.clicked.connect(self._export_to_excel)

    def _set_ins_calculated_table(self):
        self.ui.tableWidget_ins_apply_data.setRowCount(len(self.ins_calculated_table))
        self.ui.tableWidget_ins_apply_data.setAlternatingRowColors(True)

        infectious_total = 0
        for row_no, row in enumerate(self.ins_calculated_table):
            doctor_type = string_utils.xstr(row['doctor_type'])
            if doctor_type == '醫師':
                doctor_type = '專任醫師'

            fields = [
                doctor_type,
                string_utils.xstr(row['doctor_name']),
                string_utils.xstr(row['doctor_id']),
                row['diag_days'],
                row['total_count'],
                row['total_diag_count'],
                row['diag_count'],
                row['diag_section1'],
                row['diag_section2'],
                row['diag_section3'],
                row['diag_section4'],
                row['diag_section5'],
                row['treat_count'],
                row['treat_section1'],
                row['treat_section2'],
                row['treat_section3'],
                row['internal_drug'],
                row['treat_drug'],
                row['total_drug'],
                row['complicated_massage'],
                row['moderate_complicated_acupuncture'],
                row['highly_complicated_acupuncture'],
                row['infectious_count'],
            ]
            infectious_total += row['infectious_count']

            for col_no in range(len(fields)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, fields[col_no])
                self.ui.tableWidget_ins_apply_data.setItem(row_no, col_no, item)
                if col_no >= 3:
                    self.ui.tableWidget_ins_apply_data.item(
                        row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                    )

        self.ui.tableWidget_ins_apply_data.sortItems(0, QtCore.Qt.AscendingOrder)
        self._calculate_total()

        # if infectious_total > 0:
        #     self._calculate_infectious_total()

    def _calculate_total(self):
        row_count = self.ui.tableWidget_ins_apply_data.rowCount()
        total_days, total_count, total_diag, diag_count = 0, 0, 0, 0
        diag_section1, diag_section2, diag_section3, diag_section4, diag_section5 = 0, 0, 0, 0, 0
        treat_count, treat_section1, treat_section2, treat_section3 = 0, 0, 0, 0
        internal_drug, treat_drug, total_drug = 0, 0, 0
        complicated_massage, moderate_complicated_acupuncture, highly_complicated_acupuncture = 0, 0, 0
        infectious_count = 0

        for row_no in range(row_count):
            total_days += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 3).text())
            total_count += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 4).text())
            total_diag += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 5).text())
            diag_count += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 6).text())
            diag_section1 += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 7).text())
            diag_section2 += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 8).text())
            diag_section3 += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 9).text())
            diag_section4 += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 10).text())
            diag_section5 += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 11).text())
            treat_count += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 12).text())
            treat_section1 += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 13).text())
            treat_section2 += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 14).text())
            treat_section3 += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 15).text())
            internal_drug += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 16).text())
            treat_drug += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 17).text())
            total_drug += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 18).text())
            complicated_massage += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 19).text())
            moderate_complicated_acupuncture += number_utils.get_integer(
                self.ui.tableWidget_ins_apply_data.item(row_no, 20).text()
            )
            highly_complicated_acupuncture += number_utils.get_integer(
                self.ui.tableWidget_ins_apply_data.item(row_no, 21).text()
            )
            infectious_count += number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_no, 22).text())

        total_row = [
            '合計',
            None,
            None,
            total_days,
            total_count,
            total_diag,
            diag_count,
            diag_section1,
            diag_section2,
            diag_section3,
            diag_section4,
            diag_section5,
            treat_count,
            treat_section1,
            treat_section2,
            treat_section3,
            internal_drug,
            treat_drug,
            total_drug,
            complicated_massage,
            moderate_complicated_acupuncture,
            highly_complicated_acupuncture,
            infectious_count,
        ]
        self.ui.tableWidget_ins_apply_data.setRowCount(row_count + 1)
        for col_no in range(len(total_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, total_row[col_no])
            self.ui.tableWidget_ins_apply_data.setItem(row_count, col_no, item)
            if col_no >= 3:
                self.ui.tableWidget_ins_apply_data.item(
                    row_count, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _calculate_infectious_total(self):
        row_count = self.ui.tableWidget_ins_apply_data.rowCount()
        infectious_count = number_utils.get_integer(self.ui.tableWidget_ins_apply_data.item(row_count-1, 22).text())

        total_row = [
            '確診門診',
            None,
            None,
            None,
            infectious_count,
        ]

        self.ui.tableWidget_ins_apply_data.setRowCount(row_count + 1)
        for col_no in range(len(total_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, total_row[col_no])
            self.ui.tableWidget_ins_apply_data.setItem(row_count, col_no, item)
            if col_no in [4]:
                self.ui.tableWidget_ins_apply_data.item(
                    row_count, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _export_to_excel(self):
        clinic_name = self.system_settings.field('院所名稱')
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出診察人次表",
            f'{clinic_name}{self.parent.apply_year}年{self.parent.apply_month}月診察人次表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_ins_apply_data, None,
            [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
            f'{clinic_name}{self.parent.apply_year}年{self.parent.apply_month}月診察人次表',
            calc_total=False,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>診察人次表{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )
