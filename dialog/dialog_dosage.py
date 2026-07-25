
# 處方詞庫-滑鼠輸入 2014.09.22
# -*- coding: UTF-8 -*-

from libs import prescript_utils, system_utils, ui_utils
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QPoint, QSettings, QSize


# 劑量詞庫
class DialogDosage(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogDosage, self).__init__(parent)
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
        self.settings.setValue("dialog_dosage_size", self.size())
        self.settings.setValue("dialog_dosage_pos", self.pos())

    def show_dosage(self):
        self.show()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_DOSAGE, self)
        system_utils.set_css(self, self.system_settings)

        self.ui.resize(self.settings.value("dialog_dosage_size", QSize(460, 270)))
        screen_width = QtWidgets.QDesktopWidget().screenGeometry().width()
        width = self.settings.value("dialog_dosage_pos")
        if width is not None and width.x() < screen_width:
            self.ui.move(self.settings.value("dialog_dosage_pos", QPoint(226, 147)))

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)

        for tool_button in self.findChildren(QtWidgets.QToolButton):
            tool_button.clicked.connect(self._dosage_button_clicked)

    def accepted_button_clicked(self):
        self.close()

    def rejected_button_clicked(self):
        self.close()

    def reject(self):
        self.close()

    def _dosage_button_clicked(self):
        row_no = self.table_widget_prescript.currentRow()
        if self.ins_type == '健保':
            col_no = prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']
            medicine_name_col_no = prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']
        else:
            col_no = prescript_utils.SELF_PRESCRIPT_COL_NO['Dosage']
            medicine_name_col_no = prescript_utils.SELF_PRESCRIPT_COL_NO['MedicineName']

        medicine_name_item = self.table_widget_prescript.item(row_no, medicine_name_col_no)
        if medicine_name_item is None or medicine_name_item.text() == '':
            return

        dosage = self.sender().text()
        self.table_widget_prescript.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(dosage)
        )
        self.table_widget_prescript.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        if self.ins_type == '健保':
            # self.parent.check_total_dosage(row_no)
            self.parent.check_total_costs(row_no)

        self.table_widget_prescript.setCurrentCell(row_no+1, col_no)
        medicine_name_item = self.table_widget_prescript.item(row_no+1, medicine_name_col_no)
        if medicine_name_item is None or medicine_name_item.text() == '':
            self.table_widget_prescript.setCurrentCell(row_no+1, medicine_name_col_no)
            
            self.close()
