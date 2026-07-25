
# 處方詞庫-滑鼠輸入 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QSettings, QSize, QPoint
from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils


# 檢驗詞庫-滑鼠輸入
class DialogExamination(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogExamination, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.table_widget_prescript = args[2]
        self.medicine_set = args[3]

        self.settings = QSettings('__settings.ini', QSettings.IniFormat)
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_data()
        self.lineEdit_input_code.setFocus(True)

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.settings.setValue("dialog_examination_size", self.size())
        self.settings.setValue("dialog_examination_pos", self.pos())

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_EXAMINATION, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        # system_utils.center_window(self)

        self.ui.resize(self.settings.value("dialog_examination_size", QSize(1072, 931)))
        screen_width = QtWidgets.QDesktopWidget().screenGeometry().width()
        width = self.settings.value("dialog_examination_pos")
        if width is not None and width.x() < screen_width:
            self.ui.move(self.settings.value("dialog_examination_pos", QPoint(226, 147)))

        self.table_widget_dict_groups = class_utils.get_table_widget(self.ui.tableWidget_dict_groups, self.database)
        self.table_widget_medicine = class_utils.get_table_widget(self.ui.tableWidget_medicine, self.database)

        self.table_widget_dict_groups.set_column_hidden([0])
        self.table_widget_medicine.set_column_hidden([0])

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Close).setText('關閉')
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_dict_groups.itemSelectionChanged.connect(self.dict_groups_changed)
        self.ui.tableWidget_medicine.clicked.connect(self._add_prescript)
        self.ui.lineEdit_input_code.textChanged.connect(self.input_code_changed)
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)

        for tool_button in self.findChildren(QtWidgets.QToolButton):
            tool_button.clicked.connect(self.phonetic_button_clicked)

    # 設定欄位寬度
    def _set_table_width(self):
        dict_groups_width = [100, 200]
        medicine_width = [100, 250, 200, 90, 70, 80, 120]
        self.table_widget_dict_groups.set_table_heading_width(dict_groups_width)
        self.table_widget_medicine.set_table_heading_width(medicine_width)

    def accepted_button_clicked(self):
        self.close()

    def rejected_button_clicked(self):
        self.close()

    def reject(self):
        self.close()

    def _read_data(self):
        self._read_dict_groups()

    # 檢驗類別
    def _read_dict_groups(self):
        sql = '''
            SELECT MedicineKey, MedicineMode FROM medicine
            WHERE
                MedicineType = "檢驗" AND
                MedicineMode IS NOT NULL AND
                LENGTH(MedicineMode) > 0 AND
                SalePrice > 0
            GROUP BY MedicineMode
            ORDER BY MedicineMode
        '''
        self.table_widget_dict_groups.set_db_data(sql, self._set_dict_groups_data)
        self._insert_ins_examination()

    def _insert_ins_examination(self):
        self.ui.tableWidget_dict_groups.insertRow(0)
        self.ui.tableWidget_dict_groups.setItem(
            0, 1,
            QtWidgets.QTableWidgetItem('健保檢驗')
        )
        self.ui.tableWidget_dict_groups.setCurrentCell(0, 1)

    def _set_dict_groups_data(self, row_no, row):
        dict_groups_row = [
            string_utils.xstr(row['MedicineKey']),
            string_utils.xstr(row['MedicineMode']),
        ]
        for col_no in range(len(dict_groups_row)):
            self.ui.tableWidget_dict_groups.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(dict_groups_row[col_no])
            )

    def dict_groups_changed(self):
        medicine_mode = self.table_widget_dict_groups.field_value(1)
        if medicine_mode == '健保檢驗':
            self._read_ins_examination()
        else:
            self._read_medicine(medicine_mode)

        self.ui.tableWidget_dict_groups.setFocus(True)

    def _read_ins_examination(self):
        order_type = '''
            ORDER BY LENGTH(MedicineName), CAST(CONVERT(`MedicineName` using big5) AS BINARY)
        '''

        sql = f'''
            SELECT * FROM medicine
            WHERE
                (MedicineType = "檢驗") AND
                (InsCode IS NOT NULL) AND
                (LENGTH(InsCode) > 0)
                {order_type}
        '''
        self.table_widget_medicine.set_db_data(sql, self._set_medicine_data)

    def _read_medicine(self, medicine_mode, input_code=None):
        order_type = '''
            ORDER BY LENGTH(MedicineName), CAST(CONVERT(`MedicineName` using big5) AS BINARY)
        '''

        input_code_str = ''
        if input_code is not None:
            input_code_str = f'''
                AND (
                    (MedicineName LIKE "%{input_code}%") OR
                    (MedicineAlias LIKE "%{input_code}%") OR
                    (InputCode LIKE "{input_code}%")
                )
            '''
            if self.system_settings.field('詞庫排序') == '點擊率':
                order_type = 'ORDER BY HitRate DESC'
            elif self.system_settings.field('詞庫排序') == '最後點擊時戳':
                order_type = 'ORDER BY TimeStamp DESC'

        medicine_mode_condition = ''
        if medicine_mode != '':
            medicine_mode_condition = f'AND (MedicineMode = "{medicine_mode}")'

        sql = f'''
            SELECT * FROM medicine
            WHERE
                (MedicineType = "檢驗")
                {medicine_mode_condition}
                {input_code_str}
                {order_type}
        '''
        self.table_widget_medicine.set_db_data(sql, self._set_medicine_data)

    def _set_medicine_data(self, row_no, row):
        price = string_utils.get_formatted_str('單價', row['SalePrice'])
        deactivate = string_utils.xstr(row['Deactivate'])

        medicine_row = [
            string_utils.xstr(row['MedicineKey']),
            string_utils.xstr(row['MedicineName']),
            string_utils.xstr(row['MedicineAlias']),
            string_utils.xstr(row['InsCode']),
            string_utils.xstr(row['Unit']),
            price,
            deactivate,
        ]

        for col_no in range(len(medicine_row)):
            self.ui.tableWidget_medicine.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(medicine_row[col_no])
            )

            align = QtCore.Qt.AlignLeft
            if col_no in [4]:
                align = QtCore.Qt.AlignCenter
            elif col_no in [5]:
                align = QtCore.Qt.AlignRight

            self.ui.tableWidget_medicine.item(row_no, col_no).setTextAlignment(align | QtCore.Qt.AlignVCenter)
            if deactivate != '':
                self.ui.tableWidget_medicine.item(row_no, col_no).setForeground(
                    QtGui.QColor('gray')
                )

    def phonetic_button_clicked(self):
        input_code = str(self.ui.lineEdit_input_code.text()).strip()
        input_code += self.sender().text()
        self.ui.lineEdit_input_code.setText(input_code)

    def input_code_changed(self):
        input_code = str(self.ui.lineEdit_input_code.text()).strip()
        if input_code == '':
            self._read_medicine('', input_code)
            self.ui.lineEdit_input_code.setFocus(True)
            return

        input_code = string_utils.phonetic_to_str(input_code)
        self._read_medicine('', input_code)
        self.ui.lineEdit_input_code.setFocus(True)
        self.ui.lineEdit_input_code.setCursorPosition(len(input_code))

    def _add_prescript(self):
        deactivate = self.table_widget_medicine.field_value(6)
        medicine_name = self.table_widget_medicine.field_value(1)
        if deactivate != '':
            system_utils.show_message_box(
                QMessageBox.Critical,
                '藥品已停用',
                f'''
                    <font color="red">
                        <h3>{medicine_name}已經停用<br>停用原因: {deactivate}</h3>
                    </font>
                ''',
                '請開立其他藥品',
            )
            return

        self._add_drug()

    def _add_drug(self):
        tab_no = self.medicine_set - 1
        self.parent.tab_list[tab_no].append_null_medicine()

        row = self._get_medicine_row()
        self.parent.tab_list[tab_no].append_prescript(row, row['Quantity'])

        self.ui.lineEdit_input_code.setText(None)
        self.ui.lineEdit_input_code.setFocus(True)

    def _get_medicine_row(self):
        row = {
            'MedicineType': '檢驗',
            'MedicineKey': self.table_widget_medicine.field_value(0),
            'InsCode': self.table_widget_medicine.field_value(3),
            'MedicineName': self.table_widget_medicine.field_value(1),
            # 'Unit': self.table_widget_medicine.field_value(4),
            'Unit': '次',
            'Quantity': 1,
            'Price': self.table_widget_medicine.field_value(5),
            'Amount': self.table_widget_medicine.field_value(5),
        }

        return row

    def _add_massage_prescript(self):
        self.table_widget_prescript.setRowCount(
            self.table_widget_prescript.rowCount() + 1
        )
        data = [
            None,
            None,
            self.table_widget_medicine.field_value(0),
            self.table_widget_medicine.field_value(2),
            1,
            self.table_widget_medicine.field_value(4),
            number_utils.get_float(self.table_widget_medicine.field_value(5)),
            number_utils.get_float(self.table_widget_medicine.field_value(5)),
            None,
        ]
        row_no = self.table_widget_prescript.rowCount() - 1
        for col_no in range(len(data)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, data[col_no])
            self.table_widget_prescript.setItem(row_no, col_no, item)
            if col_no in [4, 6, 7]:
                self.table_widget_prescript.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [5]:
                self.table_widget_prescript.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

        self.parent.calculate_total_fee()
