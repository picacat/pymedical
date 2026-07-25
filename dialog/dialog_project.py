
# 專案詞庫-2022.03.01
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QSettings, QSize, QPoint
from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils
from libs import prescript_utils


# 專案詞庫
class DialogProject(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogProject, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.table_widget_prescript = args[2]
        self.medicine_set = args[3]

        self.settings = QSettings('__settings.ini', QSettings.IniFormat)
        self.ui = None
        self.set_medicine = True

        self._set_ui()
        self._set_signal()
        self._read_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.settings.setValue("dialog_project_size", self.size())
        self.settings.setValue("dialog_project_pos", self.pos())

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PROJECT, self)
        system_utils.set_css(self, self.system_settings)

        self.ui.resize(self.settings.value("dialog_project_size", QSize(867, 593)))
        screen_width = QtWidgets.QDesktopWidget().screenGeometry().width()
        width = self.settings.value("dialog_project_pos")
        if width is not None and width.x() < screen_width:
            self.ui.move(self.settings.value("dialog_project_pos", QPoint(226, 147)))

        self.table_widget_dict_groups = class_utils.get_table_widget(self.ui.tableWidget_dict_groups, self.database)
        self.table_widget_medicine = class_utils.get_table_widget(self.ui.tableWidget_medicine, self.database)

        self.table_widget_dict_groups.set_column_hidden([0])
        self.table_widget_medicine.set_column_hidden([0])

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('匯入')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Close).setText('關閉')
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_dict_groups.itemSelectionChanged.connect(self.dict_groups_changed)
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)
        self.ui.tableWidget_medicine.horizontalHeader().sectionClicked.connect(self._header_clicked)

    # 設定欄位寬度
    def _set_table_width(self):
        dict_groups_width = [100, 250]
        self.table_widget_dict_groups.set_table_heading_width(dict_groups_width)

        medicine_width = [100, 20, 250, 60, 50, 70]
        self.table_widget_medicine.set_table_heading_width(medicine_width)

    def accepted_button_clicked(self):
        self._extract_compound()
        self.close()

    def rejected_button_clicked(self):
        self.set_medicine = False
        self.close()

    def reject(self):
        self.close()

    def _header_clicked(self, col_no):
        if col_no != 1:
            return

        for row_no in range(self.ui.tableWidget_medicine.rowCount()):
            check_box = self.ui.tableWidget_medicine.cellWidget(row_no, 1)
            check_box.setChecked(not check_box.isChecked())

    def _extract_compound(self):
        for row_no in range(self.ui.tableWidget_medicine.rowCount()):
            check_box = self.ui.tableWidget_medicine.cellWidget(row_no, 1)
            if check_box is None or not check_box.isChecked():
                continue

            medicine_key = self.ui.tableWidget_medicine.item(row_no, 0).text()
            sql = f'''
                SELECT * FROM medicine
                WHERE
                    MedicineKey = {medicine_key}
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                continue

            compound_row = rows[0]

            quantity = number_utils.get_float(self.ui.tableWidget_medicine.item(row_no, 4).text())
            price = number_utils.get_float(compound_row['SalePrice'])
            amount = round(quantity * price, 2)
            row = {
                'MedicineType': string_utils.xstr(compound_row['MedicineType']),
                'MedicineKey': string_utils.xstr(medicine_key),
                'InsCode': string_utils.xstr(compound_row['InsCode']),
                'MedicineName': string_utils.xstr(compound_row['MedicineName']),
                'Unit': string_utils.xstr(compound_row['Unit']),
                'Quantity': string_utils.xstr(quantity),
                'Price': string_utils.xstr(price),
                'Amount': string_utils.xstr(amount),
            }

            prescript_utils.add_medicine(self.parent, self.table_widget_medicine, row)

    def _read_data(self):
        self._read_dict_groups()

    # 健保藥品, 藥品, 處置
    def _read_dict_groups(self):
        sql = '''
            SELECT MedicineKey, MedicineName FROM medicine
            WHERE
                MedicineType = "成方" AND
                Project IS NOT NULL AND LENGTH(Project) > 0
            ORDER BY MedicineCode, MedicineKey
        '''
        self.table_widget_dict_groups.set_db_data(sql, self._set_dict_groups_data)

    def _set_dict_groups_data(self, row_no, row):
        dict_groups_row = [
            string_utils.xstr(row['MedicineKey']),
            string_utils.xstr(row['MedicineName']),
        ]

        for col_no in range(len(dict_groups_row)):
            self.ui.tableWidget_dict_groups.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(dict_groups_row[col_no])
            )

    def dict_groups_changed(self):
        compound_key = self.table_widget_dict_groups.field_value(0)
        self._read_ref_compound(compound_key)

    def _read_ref_compound(self, compound_key):
        sql = f'''
            SELECT * FROM refcompound
            WHERE
                CompoundKey = {compound_key} AND
                MedicineKey IS NOT NULL
            ORDER BY RefCompoundKey
        '''
        self.table_widget_medicine.set_db_data(sql, self._set_medicine_data)

    def _set_medicine_data(self, row_no, row):
        medicine_key = row['MedicineKey']
        if medicine_key is None:
            return

        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineKey = {medicine_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        medicine_row = rows[0]

        dict_medicine_row = [
            string_utils.xstr(medicine_key),
            None,
            string_utils.xstr(medicine_row['MedicineName']),
            string_utils.xstr(medicine_row['Unit']),
            string_utils.xstr(row['Quantity']),
            string_utils.xstr(number_utils.get_float(medicine_row['SalePrice'])),
        ]

        for col_no in range(len(dict_medicine_row)):
            self.ui.tableWidget_medicine.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(dict_medicine_row[col_no])
            )
            if col_no in [3]:
                self.ui.tableWidget_medicine.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            elif col_no in [4, 5]:
                self.ui.tableWidget_medicine.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

        self._set_check_box(row_no, True)

    def _set_check_box(self, row_no, check):
        check_box = QtWidgets.QCheckBox()
        check_box.setStyleSheet('padding-left: 20px')
        check_box.setChecked(check)
        col_no = 1

        self.ui.tableWidget_medicine.setCellWidget(
            row_no, col_no, check_box)
        self.ui.tableWidget_medicine.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _add_compound_medicine(self):
        row = prescript_utils.get_medicine_row(self.table_widget_medicine)
        self.parent.add_ref_compound(row)
        self.ui.lineEdit_input_code.setText(None)

    def get_medicine(self):
        if not self.set_medicine:
            medicine_row = None
        else:
            medicine_row = {
                'medicine_key': self.table_widget_medicine.field_value(0),
                'medicine_type': self.table_widget_medicine.field_value(1),
            }

        return medicine_row
