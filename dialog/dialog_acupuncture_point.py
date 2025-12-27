
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore

from libs import class_utils
from libs import system_utils
from libs import ui_utils


# 針灸穴位圖
class DialogAcupuncturePoint(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogAcupuncturePoint, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.acupuncture_point_list = []

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_ACUPUNCTURE_POINT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('匯入病歷')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_medicine = class_utils.get_table_widget(
            self.ui.tableWidget_medicine, self.database
        )
        self._set_table_width()
        self._set_image_list()
        self.ui.tabWidget_physical.setCurrentIndex(0)
        self.ui.tabWidget_head.setCurrentIndex(0)
        self.ui.tabWidget_trunk.setCurrentIndex(0)
        self.ui.tabWidget_upper_limb.setCurrentIndex(0)
        self.ui.tabWidget_lower_limb.setCurrentIndex(0)

        for push_button in self.findChildren(QtWidgets.QPushButton):
            push_button.move(push_button.geometry().x(), push_button.geometry().y()-8)

    def _set_table_width(self):
        width = [200, 60]
        self.table_widget_medicine.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        for button in self.findChildren(QtWidgets.QPushButton):
            button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            button.clicked.connect(self._button_clicked)

    def _set_image_list(self):
        image_list = [
            [self.ui.widget_face, './images/face.jpg'],
            [self.ui.widget_face_side, './images/face_side.jpg'],
            [self.ui.widget_head_back, './images/head_back.jpg'],
            [self.ui.widget_head_top, './images/head_top.jpg'],
            [self.ui.widget_eye, './images/eye.jpg'],
            [self.ui.widget_ear_back, './images/ear_back.jpg'],
            [self.ui.widget_neck, './images/neck.jpg'],
            [self.ui.widget_oral, './images/oral.jpg'],

            [self.ui.widget_trunk_top, './images/trunk_top.jpg'],
            [self.ui.widget_trunk_bottom, './images/trunk_bottom.jpg'],
            [self.ui.widget_back_top, './images/back_top.jpg'],
            [self.ui.widget_back_bottom, './images/back_bottom.jpg'],
            [self.ui.widget_trunk_top_side, './images/trunk_top_side.jpg'],
            [self.ui.widget_trunk_bottom_side, './images/trunk_bottom_side.jpg'],
            [self.ui.widget_perineum, './images/perineum.jpg'],

            [self.ui.widget_upper_limb, './images/upper_limb.jpg'],
            [self.ui.widget_arm, './images/arm.jpg'],
            [self.ui.widget_palm, './images/palm.jpg'],
            [self.ui.widget_armpit, './images/armpit.jpg'],

            [self.ui.widget_lower_limb, './images/lower_limb.jpg'],
            [self.ui.widget_leg, './images/leg.jpg'],
            [self.ui.widget_leg_back, './images/leg_back.jpg'],
            [self.ui.widget_calf, './images/calf.jpg'],
            [self.ui.widget_calf_back, './images/calf_back.jpg'],
            [self.ui.widget_sole, './images/sole.jpg'],
            [self.ui.widget_caudal_vertebra, './images/caudal_vertebra.jpg'],
        ]
        for image in image_list:
            system_utils.set_widget_image(image[0], image[1])

    def _button_clicked(self):
        acupuncture_point = self.sender().text()
        row_count = self.ui.tableWidget_medicine.rowCount()
        for row_no in range(row_count):
            item_name = self.ui.tableWidget_medicine.item(row_no, 0)
            if item_name is None:
                self.ui.tableWidget_medicine.removeRow(row_no)
                return

            item_name = item_name.text()
            if acupuncture_point == item_name:
                return

        self.ui.tableWidget_medicine.setRowCount(row_count + 1)
        self.ui.tableWidget_medicine.setItem(
            row_count, 0,
            QtWidgets.QTableWidgetItem(acupuncture_point)
        )
        button = QtWidgets.QPushButton(self.ui.tableWidget_medicine)
        button.setIcon(QtGui.QIcon('./icons/gtk-cancel.svg'))
        button.setFlat(True)

        button.clicked.connect(self._remove_medicine_row)
        self.ui.tableWidget_medicine.setCellWidget(row_count, 1, button)

    def _remove_medicine_row(self):
        current_row = self.ui.tableWidget_medicine.currentRow()
        self.ui.tableWidget_medicine.removeRow(current_row)

    def accepted_button_clicked(self):
        self.acupuncture_point_list = []
        for row_no in range(self.ui.tableWidget_medicine.rowCount()):
            self.acupuncture_point_list.append(self.ui.tableWidget_medicine.item(row_no, 0).text())
