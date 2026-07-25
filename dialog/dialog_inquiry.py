
# 主訴舌診脈象詞庫 2019.07.19
# -*- coding: UTF-8 -*-

from libs import dialog_utils, system_utils, ui_utils
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QPoint, QSettings, QSize


# 主訴舌診脈象詞庫
class DialogInquiry(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInquiry, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.dialog_type = args[2]
        self.text_edit = args[3]

        self.settings = QSettings('__settings.ini', QSettings.IniFormat)
        self.ui = None

        self._set_ui()
        self._set_signal()
        self.read_dictionary()

        system_utils.set_keyboard_layout('英文')

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def done(self, r: int) -> None:        
        ui_utils.save_settings(self, 'dialog_inquiry')
        super().done(r)
        

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INQUIRY, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.set_theme(self.ui, self.system_settings)

        if self.system_settings.field('詞庫視窗顯示方式') == '彈出式視窗':
            self.ui.setWindowFlags(QtCore.Qt.Popup)

        ui_utils.restore_settings(
            self, 'dialog_inquiry', QSize(858, 769), QPoint(846, 215))
            
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('關閉')
        self.ui.lineEdit_query.setFocus()

    def _tab_changed(self, i):
        visible = True

        tab_name = self.ui.tabWidget_inquiry.tabText(i)
        if tab_name in ['舌苔', '舌質', '脈象表']:
            visible = False

        self.ui.label_query.setVisible(visible)
        self.ui.lineEdit_query.setVisible(visible)

        self.ui.lineEdit_query.setFocus()

    # 設定信號
    def _set_signal(self):
        self.ui.lineEdit_query.textChanged.connect(self._query_diagnostic)
        self.ui.tabWidget_inquiry.currentChanged.connect(self._tab_changed)                   # 切換分頁
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)

    def accepted_button_clicked(self):
        self.accept()
        
    def rejected_button_clicked(self):
        self.reject()

    def read_dictionary(self):
        if self.dialog_type == '主訴':
            sql = 'SELECT * FROM dict_groups WHERE DictGroupsType = "主訴類別" ORDER BY DictGroupsKey'
            rows = self.database.select_record(sql)
            for row in rows:
                groups_name = row['DictGroupsName']
                dialog = dialog_utils.get_dialog_symptom(
                    self, self.database, self.system_settings, groups_name, self.text_edit)
                self.ui.tabWidget_inquiry.addTab(dialog, groups_name)
        elif self.dialog_type == '舌診':
            sql = 'SELECT * FROM dict_groups WHERE DictGroupsType = "舌診類別" ORDER BY DictGroupsKey'
            rows = self.database.select_record(sql)
            for row in rows:
                groups_name = row['DictGroupsName']
                if groups_name in ['', None]:
                    continue

                dialog = dialog_utils.get_dialog_tongue_list(
                    self, self.database, self.system_settings, groups_name, self.text_edit)
                self.ui.tabWidget_inquiry.addTab(dialog, groups_name)
            dialog_tongue1 = dialog_utils.get_dialog_tongue(
                self, self.database, self.system_settings, '舌質', self.text_edit)
            dialog_tongue2 = dialog_utils.get_dialog_tongue(
                self, self.database, self.system_settings, '舌苔', self.text_edit)

            self.ui.tabWidget_inquiry.addTab(dialog_tongue1, '舌質總覽')
            self.ui.tabWidget_inquiry.addTab(dialog_tongue2, '舌苔總覽')
        elif self.dialog_type == '脈象':
            dialog_picker = dialog_utils.get_dialog_pulse_picker(
                self, self.database, self.system_settings, self.text_edit)
            self.ui.tabWidget_inquiry.addTab(dialog_picker, '脈象表')

            sql = 'SELECT * FROM dict_groups WHERE DictGroupsType = "脈象類別" ORDER BY DictGroupsKey'
            rows = self.database.select_record(sql)
            for row in rows:
                groups_name = row['DictGroupsName']
                dialog = dialog_utils.get_dialog_pulse(
                    self, self.database, self.system_settings, groups_name, self.text_edit)
                self.ui.tabWidget_inquiry.addTab(dialog, '脈象詞庫')
        elif self.dialog_type in ['病史', '備註']:
            sql = 'SELECT * FROM dict_groups WHERE DictGroupsType = "備註類別" ORDER BY DictGroupsKey'
            rows = self.database.select_record(sql)
            for row in rows:
                groups_name = row['DictGroupsName']
                dialog = dialog_utils.get_dialog_remark(
                    self, self.database, self.system_settings, groups_name, self.text_edit)
                self.ui.tabWidget_inquiry.addTab(dialog, groups_name)

    def _query_diagnostic(self):
        keyword = self.ui.lineEdit_query.text()
        if keyword == '':
            return

        tab = self.ui.tabWidget_inquiry.currentWidget()
        dialog = None
        if self.dialog_type == '主訴':
            dialog = [tab.table_widget_symptom, 'ClinicName']
        elif self.dialog_type == '舌診':
            dialog = [tab.table_widget_tongue, tab._set_tongue_data]
        elif self.dialog_type == '脈象':
            dialog = [tab.table_widget_pulse, tab._set_pulse_data]
        elif self.dialog_type in ['病史', '備註']:
            dialog = [tab.table_widget_remark, tab._set_remark_data]

        if dialog is None:
            return

        order_type = '''
            ORDER BY LENGTH(ClinicName), CAST(CONVERT(`ClinicName` using big5) AS BINARY)
        '''
        if self.system_settings.field('詞庫排序') == '點擊率':
            order_type = 'ORDER BY HitRate DESC'
        elif self.system_settings.field('詞庫排序') == '最後點擊時戳':
            order_type = 'ORDER BY TimeStamp DESC'

        clinic_type = self.dialog_type
        if clinic_type == '病史':
            clinic_type = '備註'

        sql = f'''
            SELECT * FROM clinic
            WHERE
                ClinicType = "{clinic_type}" AND
                (InputCode LIKE "{keyword}%" OR ClinicName LIKE "%{keyword}%")
            GROUP BY ClinicName
            {order_type}
        '''
        if self.dialog_type == '主訴':
            dialog[0].set_db_data_without_heading(sql, dialog[1])
        else:
            dialog[0].set_db_data(sql, dialog[1])

        self.ui.lineEdit_query.setFocus()
        self.ui.lineEdit_query.setCursorPosition(len(keyword))

    def reset_query(self):
        self.ui.lineEdit_query.setText(None)
        self.ui.lineEdit_query.setFocus()
