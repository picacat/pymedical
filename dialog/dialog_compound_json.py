
# 處方詞庫-滑鼠輸入 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QSettings, QSize, QPoint
import json

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils
from libs import prescript_utils


# 方劑詞庫
class DialogCompoundJson(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogCompoundJson, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.medicine_set = args[2]
        self.table_widget_prescript = args[3]

        self.settings = QSettings('__settings.ini', QSettings.IniFormat)
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_compound_json()
        self._set_focus()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.settings.setValue("dialog_full_compound_size", self.size())
        self.settings.setValue("dialog_full_compound_pos", self.pos())

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_COMPOUND_JSON, self)
        system_utils.set_css(self, self.system_settings)

        if self.system_settings.field('詞庫視窗顯示方式') == '彈出式視窗':
            self.ui.setWindowFlags(QtCore.Qt.Popup)

        default_width = 850
        default_height = 930
        dialog_size = self.settings.value("dialog_full_compound_size", QSize(635, 930))
        if dialog_size.width() >= default_width:
            dialog_size.setWidth(default_width)
        if dialog_size.height() >= default_height:
            dialog_size.setHeight(default_height)

        self.ui.resize(dialog_size)
        # self.ui.resize(self.settings.value("dialog_full_medicine_size", QSize(635, 802)))

        screen_width = QtWidgets.QDesktopWidget().screenGeometry().width()
        width = self.settings.value("dialog_full_compound_pos")
        if width is not None and width.x() < screen_width:
            self.ui.move(self.settings.value("dialog_full_compound_pos", QPoint(226, 147)))

        self.table_widget_compound = class_utils.get_table_widget(self.ui.tableWidget_compound, self.database)

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('匯入')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Close).setText('關閉')
        self._set_table_width()

    def _set_focus(self):
        self.ui.tableWidget_compound.setCurrentCell(0, 1)
        self.lineEdit_input_code.setFocus(True)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_compound.clicked.connect(self._show_compound)
        self.ui.lineEdit_input_code.textChanged.connect(self.input_code_changed)
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)
        self.ui.pushButton_show_all.clicked.connect(self._show_all)

        self.ui.radioButton_powder.clicked.connect(lambda: self._read_compound_json())
        self.ui.radioButton_herb.clicked.connect(lambda: self._read_compound_json())

        self.ui.toolButton_backspace.clicked.connect(self._input_code_backspace)

        for tool_button in self.findChildren(QtWidgets.QToolButton):
            if tool_button is self.ui.toolButton_backspace:
                continue

            tool_button.clicked.connect(self.phonetic_button_clicked)

    def _tab_changed(self, i):
        tab_name = self.ui.tabWidget_keyboard.tabText(i)
        if tab_name == '經絡分類':
            self._groups_changed()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [220]
        self.table_widget_compound.set_table_heading_width(width)

    def accepted_button_clicked(self):
        json_compound = self._get_current_compound()
        if json_compound is None:
            self.ui.tableWidget_compound.setCurrentCell(0, 0)
            json_compound = self._get_current_compound()

        if json_compound is not None:
            self._add_compound(json_compound)

        self.close()

    def rejected_button_clicked(self):
        self.set_medicine = False
        self.close()

    def reject(self):
        self.close()

    def _read_compound_json(self, input_code=''):
        self.compound_list = []
        with open('compound.json', 'r', encoding='utf8') as json_file:
            rows = json.load(json_file)
            for row in rows:
                if input_code != '':
                    json_input_code = str(row['輸入碼']).lower()
                    if json_input_code[:len(input_code)] != input_code:
                        continue

                compound = []
                for item in row['處方']:
                    compound.append({
                        'medicine_name': item['藥名'],
                        'dosage': item['劑量']
                    })

                self.compound_list.append({
                    'compound_name': row['方名'],
                    'source': row['出典'],
                    'function': row['效能'],
                    'indication': row['適應症'],
                    'notice': row['注意事項'],
                    'medicine': compound,
                })

        self.ui.tableWidget_compound.setRowCount(0)
        for row_no, item in enumerate(self.compound_list):
            compound_name = item['compound_name']

            self.ui.tableWidget_compound.setRowCount(self.ui.tableWidget_compound.rowCount()+1)
            self.ui.tableWidget_compound.setItem(
                row_no, 0,
                QtWidgets.QTableWidgetItem(compound_name)
            )

        self.ui.tableWidget_compound.setCurrentCell(0, 0)
        self.ui.tableWidget_compound.setFocus()

        self._show_compound()

    def phonetic_button_clicked(self):
        input_code = str(self.ui.lineEdit_input_code.text()).strip()
        input_code += self.sender().text()
        self.ui.lineEdit_input_code.setText(input_code)

    def _show_all(self):
        self._read_compound_json()
        self._set_focus()

    def input_code_changed(self):
        input_code = str(self.ui.lineEdit_input_code.text()).strip()
        if input_code == '':
            self._read_compound_json()
            self.ui.lineEdit_input_code.setFocus(True)
            return

        input_code = string_utils.phonetic_to_str(input_code)
        self._read_compound_json(input_code=input_code)
        if len(self.compound_list) <= 0:
            self.ui.lineEdit_input_code.setText(self.ui.lineEdit_input_code.text()[:-1])

        self.ui.lineEdit_input_code.setFocus(True)
        self.ui.lineEdit_input_code.setCursorPosition(len(input_code))

    def _get_medicine_row(self, medicine_name):
        medicine_type = self._get_medicine_type()

        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineType = "{medicine_type}" AND
                MedicineName LIKE "%{medicine_name}%"
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return None

        return rows[0]

    def _add_compound(self, json_compound):
        for item in json_compound['medicine']:
            medicine_name = item['medicine_name']
            dosage = number_utils.get_float(item['dosage'])

            medicine_row = self._get_medicine_row(medicine_name)
            if medicine_row is not None:
                if string_utils.xstr(medicine_row['Unit']) == '錢':
                    dosage /= 3.75
                    dosage = round(dosage, 1)

                self._add_prescript(medicine_row, dosage)

    def _add_prescript(self, medicine_row, dosage):
        deactivate = string_utils.xstr(medicine_row['Deactivate'])
        medicine_name = string_utils.xstr(medicine_row['MedicineName'])
        if deactivate != '':
            if deactivate == '庫存量不足':
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
                    f'<font color="red"><h3>{medicine_name}已經停用<br>停用原因: {deactivate}</h3></font>',
                    '請開立其他藥品',
                )
                return

        self._add_medicine(medicine_row, dosage)

    def _add_medicine(self, medicine_row, dosage):
        if self.table_widget_prescript is None:
            self.close()
            return

        try:
            tab_prescript = self.parent.parent.tab_list[self.medicine_set-1]   # call by ins_prescript/self_prescript
        except AttributeError:
            return

        prescript_utils.add_medicine(tab_prescript, None, medicine_row, dosage)

        self.ui.lineEdit_input_code.setText(None)
        self.ui.lineEdit_input_code.setFocus()

    def _input_code_backspace(self):
        input_code = self.ui.lineEdit_input_code.text().strip()
        if input_code == '':
            return

        input_code = input_code[:len(input_code)-1]
        self.ui.lineEdit_input_code.setText(input_code)

    def _get_current_compound(self):
        row_no = self.ui.tableWidget_compound.currentRow()

        item = self.ui.tableWidget_compound.item(row_no, 0)
        if item is None:
            return None

        current_compound_name = item.text()
        json_compound = None
        for row_no, item in enumerate(self.compound_list):
            compound_name = item['compound_name']
            if current_compound_name == compound_name:
                json_compound = {
                    'compound_name': compound_name,
                    'source': item['source'],
                    'function': item['function'],
                    'indication': item['indication'],
                    'notice': item['notice'],
                    'medicine': item['medicine'],
                }

        return json_compound

    def _get_medicine_type(self):
        if self.ui.radioButton_powder.isChecked():
            medicine_type = '單方'
        else:
            medicine_type = '水藥'

        return medicine_type

    def _show_compound(self):
        self.ui.textEdit_compound.setPlainText(None)

        json_compound = self._get_current_compound()
        if json_compound is None:
            return

        medicine_type = self._get_medicine_type()
        if medicine_type == '單方':
            unit = '克'
        else:
            unit = '錢'

        medicine_tr = ''
        i = 0
        for item in json_compound['medicine']:
            i += 1
            dosage = number_utils.get_float(item['dosage'])
            if unit == '錢':
                dosage /= 3.75

            medicine_tr += f'''
                <tr>
                    <td width="10%" align="center">{i}</td>
                    <td>{item['medicine_name']}</td>
                    <td width="20%" align="right">{dosage:.1f}</td>
                    <td width="10%" align="center">{unit}</td>
                </tr>
            '''

        medicine_html = f'''
            <table align=center cellpadding="2" cellspacing="0" width="98%"
            style="border-width: 1px; border-style: solid;">
                <thead>
                    <tr>
                        <th bgcolor="LightGray">序</th>
                        <th bgcolor="LightGray">藥品名稱</th>
                        <th bgcolor="LightGray">劑量</th>
                        <th bgcolor="LightGray">單位</th>
                    </tr>
                </thead>
                <tbody>
                    {medicine_tr}
                </tbody>
            </table>
        '''

        compound_html = f'''
            <table align=center cellpadding="2" cellspacing="0" width="98%"
            style="border-width: 1px; border-style: solid;">
                <tbody>
                    <tr>
                        <th width="20%" style="vertical-align: middle" bgcolor="LightGray">方名</th>
                        <td>{json_compound['compound_name']}</td>
                    </tr>
                    <tr>
                        <th style="vertical-align: middle" bgcolor="LightGray">出典</th>
                        <td>{json_compound['source']}</td>
                    </tr>
                    <tr>
                        <th style="vertical-align: middle" bgcolor="LightGray">效能</th>
                        <td>{json_compound['function']}</td>
                    </tr>
                    <tr>
                        <th style="vertical-align: middle" bgcolor="LightGray">適應症</th>
                        <td>{json_compound['indication']}</td>
                    </tr>
                    <tr>
                        <th style="vertical-align: middle" bgcolor="LightGray">組成</th>
                        <td>
                            {medicine_html}
                        </td>
                    </tr>
                    <tr>
                        <th style="vertical-align: middle" bgcolor="LightGray">注意事項</th>
                        <td>{json_compound['notice']}</td>
                    </tr>
                </tbody>
            </table>
        '''

        html = f'''
            <html>
                <head>
                    <meta charset="UTF-8">
                </head>
                <body>
                    {compound_html}
                </body>
            </html>
        '''
        self.ui.textEdit_compound.setHtml(html)
