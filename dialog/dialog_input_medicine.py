
# 處方詞庫-鍵盤輸入 2014.09.22
# -*- coding: UTF-8 -*-

from libs import (class_utils, db_utils, nhi_utils, number_utils,
                  prescript_utils, string_utils, system_utils, ui_utils)
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QPoint, QSettings, QSize, Qt
from PyQt5.QtWidgets import QMessageBox


# 處方詞庫-鍵盤輸入
class DialogInputMedicine(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInputMedicine, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.dict_type = args[2]
        self.medicine_set = args[3]
        self.table_widget_prescript = args[4]
        self.previous_medicine_name = args[5]
        self.input_code = args[6]

        self.settings = QSettings('__settings.ini', QSettings.IniFormat)
        self.ui = None
        self.medicine_key = None

        self._set_ui()
        self._set_signal()
        self._set_table_width()
        self.read_dictionary()
        # self._set_medicine_type_button()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def done(self, r: int) -> None:        
        ui_utils.save_settings(self, 'dialog_medicine')
        super().done(r)
        
        if self.medicine_key is None:
            self.table_widget_prescript.currentItem().setText(self.previous_medicine_name)
        else:
            if self.dict_type == '健保處置':
                self._add_treat()
            else:
                self._add_prescript()

        self.table_widget_prescript.setFocus()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INPUT_MEDICINE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.set_theme(self.ui, self.system_settings)

        if self.system_settings.field('詞庫視窗顯示方式') == '彈出式視窗':
            self.ui.setWindowFlags(QtCore.Qt.Popup)

        ui_utils.restore_settings(
            self, 'dialog_medicine', QSize(635, 930), QPoint(1054, 225))
        

        self.table_widget_medicine = class_utils.get_table_widget(self.ui.tableWidget_medicine, self.database)
        self.table_widget_medicine.set_column_hidden([0])

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Save).setText('選取')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Close).setText('關閉')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)
        self.ui.tableWidget_medicine.clicked.connect(self.accepted_button_clicked)

    # 設定欄位寬度
    def _set_table_width(self):
        medicine_width = [100, 100, 240, 60, 80, 110, 70, 120]
        self.table_widget_medicine.set_table_heading_width(medicine_width)

    def accepted_button_clicked(self):
        deactivate = self.table_widget_medicine.field_value(7)
        medicine_name = self.table_widget_medicine.field_value(2)
        if deactivate != '':
            if deactivate == '庫存量不足':
                if self.system_settings.field('庫存量不足不要提醒') == 'Y':
                    pass
                else:
                    system_utils.show_message_box(
                        QMessageBox.Critical,
                        '庫存量不足',
                        f'''
                            <font color="red">
                                <h3>「{medicine_name}」低於安全庫存量, 庫存量不足</h3>
                            </font>
                        ''',
                        '請盡速補貨',
                    )
            else:
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

        self.medicine_key = self.table_widget_medicine.field_value(0)
        db_utils.increment_hit_rate(self.database, 'medicine', 'MedicineKey', self.medicine_key)

        try:
            self.ui.lineEdit_input_code.setText(None)
        except Exception:
            pass

        self.accept()

    def rejected_button_clicked(self):
        self.medicine_key = None
        self.reject()

    def _get_other_medicine_type_list(self):
        sql = '''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = '藥品類別' AND
                DictGroupsName NOT IN ("單方", "複方", "水藥", "外用", "高貴")
            ORDER BY DictOrderNo
        '''
        rows = self.database.select_record(sql)

        other_medicine_type_list = []
        for row in rows:
            other_medicine_type_list.append(string_utils.xstr(row['DictGroupsName']))

        return other_medicine_type_list

    def read_dictionary(self, medicine_type=None):
        herb_type = None
        if self.system_settings.field('處方詞庫僅列出水藥') == 'Y':
            current_row = self.table_widget_prescript.currentRow()
            if current_row > 0:  # 第一筆不要限制
                herb_type_item = self.table_widget_prescript.item(0, prescript_utils.PRESCRIPT_COL_NO['MedicineType'])
                if herb_type_item is not None:
                    herb_type = herb_type_item.text()

        if herb_type is not None and herb_type == '水藥':
            medicine_type = f'AND (MedicineType IN ("{herb_type}", "成方"))'
        elif medicine_type is not None:
            medicine_type = f'AND (MedicineType = "{medicine_type}")'
        elif self.dict_type == '健保藥品':
            medicine_type = 'AND (MedicineType IN ("單方", "複方", "成方"))'

            if self.system_settings.field('健保處方詞庫只顯示單方複方') == 'Y':
                medicine_type = 'AND (MedicineType IN ("單方", "複方") OR (MedicineType = "成方" AND Unit = "克"))'
            elif self.system_settings.field('健保處方詞庫顯示自訂類別') == 'Y':
                medicine_type = 'AND (MedicineType NOT IN ("水藥", "外用", "高貴", "穴道", "處置", "器材", "檢驗"))'
        # elif self.dict_type == '所有藥品':
        #     medicine_type = 'AND (MedicineType NOT IN ("穴道", "處置", "檢驗"))'
        elif self.dict_type == '健保處置':
            if self.parent.comboBox_treatment.currentText() in nhi_utils.ACUPUNCTURE_TREAT:
                medicine_type = '''
                    AND (MedicineType in ("穴道", "處置", "外用") OR (MedicineType = "成方" AND Unit = "次"))
                '''
            elif self.parent.comboBox_treatment.currentText() in nhi_utils.MASSAGE_TREAT:
                medicine_type = '''
                    AND (MedicineType in ("處置", "穴道", "外用") OR (MedicineType = "成方" AND Unit = "次"))
                '''
            else:
                medicine_type = 'AND (MedicineType in ("穴道", "處置", "外用", "成方"))'
        else:
            medicine_type = 'AND (MedicineType IS NOT NULL AND LENGTH(MedicineType) > 0)'

        if self.dict_type == '健保藥品':
            order_type = '''
                ORDER BY FIELD(MedicineType, "複方", "單方", "成方")
            '''
        elif self.dict_type == '所有藥品':
            order_type = '''
                ORDER BY FIELD(MedicineType, "水藥", "複方", "單方", "高貴", "外用", "穴道", "處置", "器材", "成方")
            '''

            other_medicine_type_list = self._get_other_medicine_type_list()
            if len(other_medicine_type_list) > 0:
                other_medicine_type = ', '.join(f'"{w}"' for w in other_medicine_type_list)
                order_type = f'''
                    ORDER BY FIELD(
                        MedicineType, "水藥", "複方", "單方", "高貴", "外用",
                        "穴道", "處置", "器材", "成方", {other_medicine_type}
                    )
                '''
        elif self.dict_type == '健保處置':
            if self.parent.comboBox_treatment.currentText() in nhi_utils.ACUPUNCTURE_TREAT:
                order_type = '''
                    ORDER BY FIELD(MedicineType, "穴道", "處置", "成方")
                '''
            elif self.parent.comboBox_treatment.currentText() in nhi_utils.MASSAGE_TREAT:
                order_type = '''
                    ORDER BY FIELD(MedicineType, "處置", "穴道", "成方")
                '''
            else:
                order_type = '''
                    ORDER BY FIELD(MedicineType, "穴道", "處置", "成方")
                '''
        else:
            order_type = '''
                ORDER BY FIELD(MedicineType, "單方", "複方", "水藥", "外用", "高貴", "穴道", "處置", "器材", "成方")
            '''

        if self.system_settings.field('處方點擊率依照處方類別排序') == 'Y':
            pass
        elif self.system_settings.field('詞庫排序') == '點擊率':
            order_type = 'ORDER BY HitRate DESC'
        elif self.system_settings.field('詞庫排序') == '最後點擊時戳':
            order_type = 'ORDER BY TimeStamp DESC'

        sql = f'''
            SELECT * FROM medicine
            WHERE
                (MedicineName LIKE "%{self.input_code}%" OR
                 InputCode LIKE "{self.input_code}%" OR
                 MedicineCode = "{self.input_code}" OR
                 InsCode = "{self.input_code}")
            {medicine_type}
            {order_type}
        '''
        self.table_widget_medicine.set_db_data(sql, self._set_medicine_data)

    def _set_medicine_type_button(self):
        MAX_COL = 7

        medicine_type_list = ['全部']
        for row_no in range(self.ui.tableWidget_medicine.rowCount()):
            field = self.ui.tableWidget_medicine.item(row_no, 1)
            if field is None:
                continue

            medicine_type = field.text()
            if medicine_type not in medicine_type_list:
                medicine_type_list.append(medicine_type)

        medicine_type_list.sort(key=len)
        button_list = []
        for medicine_type in medicine_type_list:
            button = QtWidgets.QToolButton()
            button.setText(medicine_type)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            if medicine_type == '全部':
                button.setChecked(True)

            button.clicked.connect(self._medicine_type_button_clicked)
            button_list.append(button)

        row_no, col_no = 0, 0
        for button in button_list:
            self.ui.gridLayout_buttons.addWidget(button, row_no, col_no)
            col_no += 1
            if col_no >= MAX_COL:
                row_no += 1
                col_no = 0

    def _medicine_type_button_clicked(self):
        medicine_type = self.sender().text()
        if medicine_type == '全部':
            self.read_dictionary()
        else:
            self.read_dictionary(medicine_type)

    def _set_medicine_data(self, row_no, row):
        safe_quantity = number_utils.get_integer(row['SafeQuantity'])
        quantity = number_utils.get_integer(row['Quantity'])
        medicine_type = string_utils.xstr(row['MedicineType'])
        ins_code = string_utils.xstr(row['InsCode'])
        deactivate = string_utils.xstr(row['Deactivate'])
        location = string_utils.xstr(row['Location'])
        non_nhi = string_utils.xstr(row['NonNHI'])

        if deactivate == '':
            if safe_quantity > 0 and quantity <= safe_quantity:
                deactivate = '庫存量不足'
            elif self.medicine_set == 1 and non_nhi == 'Y':
                deactivate = '僅用於自費'

        dosage_mode = self.system_settings.field('劑量模式')
        if dosage_mode in [None, '']:
            dosage_mode = '日劑量'

        medicine_row = [
            string_utils.xstr(row['MedicineKey']),
            medicine_type,
            string_utils.xstr(row['MedicineName']),
            string_utils.xstr(row['Unit']),
            string_utils.get_formatted_str('單價', row['SalePrice']),
            ins_code,
            string_utils.get_formatted_str(dosage_mode, row['Dosage']),
            deactivate,
        ]

        for col_no in range(len(medicine_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medicine_row[col_no])
            self.ui.tableWidget_medicine.setItem(
                row_no, col_no, item,
            )
            align = QtCore.Qt.AlignLeft
            if col_no in [3]:
                align = QtCore.Qt.AlignCenter
            elif col_no in [4, 6]:
                align = QtCore.Qt.AlignRight

            cell = self.ui.tableWidget_medicine.item(row_no, col_no)
            cell.setTextAlignment(align | QtCore.Qt.AlignVCenter)

            if medicine_type in ['單方', '複方'] and ins_code == '':
                cell.setForeground(QtGui.QColor('blue'))
            elif medicine_type in ['成方']:
                cell.setForeground(QtGui.QColor('brown'))

            if self.system_settings.field('處方無存放位置淡色顯示') == 'Y' and location in ['', None]:
                cell.setForeground(QtGui.QColor('lightgray'))
            elif deactivate == '庫存量不足':
                cell.setForeground(QtGui.QColor('red'))
            elif deactivate != '':
                cell.setForeground(QtGui.QColor('gray'))

    # 輸入藥品
    def _add_prescript(self):
        medicine_type = self.table_widget_medicine.field_value(1)
        medicine_key = self.table_widget_medicine.field_value(0)
        if medicine_type == '成方':
            prescript_utils.extract_compound(
                self.parent, self.database, self.system_settings, medicine_key, self.table_widget_medicine)
        else:
            prescript_utils.add_medicine(self.parent, self.table_widget_medicine)

    def _add_treat(self):
        medicine_type = self.table_widget_medicine.field_value(1)
        medicine_key = self.table_widget_medicine.field_value(0)
        if medicine_type == '成方':
            prescript_utils.extract_compound(
                self.parent, self.database, self.system_settings, medicine_key, self.table_widget_medicine)
        else:
            prescript_utils.add_treat(self.parent, self.table_widget_medicine)
