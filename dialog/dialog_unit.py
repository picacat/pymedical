
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QSettings, QSize, QPoint
from libs import ui_utils
from libs import system_utils
from libs import prescript_utils


# 單位詞庫 2023.12.27
class DialogUnit(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogUnit, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.table_widget_prescript = args[2]
        self.ins_type = args[3]

        self.settings = QSettings('__settings.ini', QSettings.IniFormat)
        self.ui = None

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.settings.setValue("dialog_unit_size", self.size())
        self.settings.setValue("dialog_unit_pos", self.pos())

    def show_unit(self):
        self.show()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_UNIT, self)
        system_utils.set_css(self, self.system_settings)

        self.ui.resize(self.settings.value("dialog_unit_size", QSize(460, 270)))
        screen_width = QtWidgets.QDesktopWidget().screenGeometry().width()
        width = self.settings.value("dialog_unit_pos")
        if width is not None and width.x() < screen_width:
            self.ui.move(self.settings.value("dialog_unit_pos", QPoint(226, 147)))

        sql = '''
                SELECT Unit, COUNT(*) AS count FROM medicine
                GROUP BY Unit ORDER BY count DESC;
        '''
        rows = self.database.select_record(sql)
        unit_list = ['克']
        for row in rows:
            if row['Unit'] is None or str(row['Unit']).strip() == '' or row['Unit'] == '克':
                continue

            unit_list.append(str(row['Unit']).strip())

        tool_button_list = [
            self.ui.toolButton_1,
            self.ui.toolButton_2,
            self.ui.toolButton_3,
            self.ui.toolButton_4,
            self.ui.toolButton_5,
            self.ui.toolButton_6,
            self.ui.toolButton_7,
            self.ui.toolButton_8,
            self.ui.toolButton_9,
            self.ui.toolButton_10,
            self.ui.toolButton_11,
            self.ui.toolButton_12,
            self.ui.toolButton_13,
            self.ui.toolButton_14,
            self.ui.toolButton_15,
            self.ui.toolButton_16,
            self.ui.toolButton_17,
            self.ui.toolButton_18,
            self.ui.toolButton_19,
            self.ui.toolButton_20,
            self.ui.toolButton_21,
            self.ui.toolButton_22,
            self.ui.toolButton_23,
            self.ui.toolButton_24,
            self.ui.toolButton_25,
            self.ui.toolButton_26,
            self.ui.toolButton_27,
            self.ui.toolButton_28,
            self.ui.toolButton_29,
            self.ui.toolButton_30,
            self.ui.toolButton_31,
            self.ui.toolButton_32,
            self.ui.toolButton_33,
            self.ui.toolButton_34,
            self.ui.toolButton_35,
            self.ui.toolButton_36,
            self.ui.toolButton_37,
            self.ui.toolButton_38,
            self.ui.toolButton_39,
            self.ui.toolButton_40,
            self.ui.toolButton_41,
            self.ui.toolButton_42,
            self.ui.toolButton_43,
            self.ui.toolButton_44,
            self.ui.toolButton_45,
            self.ui.toolButton_46,
            self.ui.toolButton_47,
            self.ui.toolButton_48,
            self.ui.toolButton_49,
            self.ui.toolButton_50,
        ]
        for i, tool_button in enumerate(tool_button_list):
            try:
                tool_button.setText(unit_list[i])
            except Exception:
                tool_button.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)

        for tool_button in self.findChildren(QtWidgets.QToolButton):
            tool_button.clicked.connect(self._unit_button_clicked)

    def accepted_button_clicked(self):
        self.close()

    def rejected_button_clicked(self):
        self.close()

    def reject(self):
        self.close()

    def _unit_button_clicked(self):
        row_no = self.table_widget_prescript.currentRow()
        if self.ins_type == '健保':
            col_no = prescript_utils.INS_PRESCRIPT_COL_NO['Unit']
            medicine_name_col_no = prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']
        else:
            col_no = prescript_utils.SELF_PRESCRIPT_COL_NO['Unit']
            medicine_name_col_no = prescript_utils.SELF_PRESCRIPT_COL_NO['MedicineName']

        medicine_name_item = self.table_widget_prescript.item(row_no, medicine_name_col_no)
        if medicine_name_item is None or medicine_name_item.text() == '':
            return

        unit = self.sender().text()
        self.table_widget_prescript.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(unit)
        )
        self.table_widget_prescript.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

        self.table_widget_prescript.setCurrentCell(row_no+1, col_no)
        medicine_name_item = self.table_widget_prescript.item(row_no+1, medicine_name_col_no)
        if medicine_name_item is None or medicine_name_item.text() == '':
            self.table_widget_prescript.setCurrentCell(row_no+1, medicine_name_col_no)
            self.close()
