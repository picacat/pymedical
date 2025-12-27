from PyQt5 import QtWidgets
from libs import ui_utils
from libs import system_utils
from libs import string_utils


VENDOR_LIST = {
    '友杏': ['Medical', 'Med2000'],
    '國泰': ['kthis'],
}


# 輸入分院資料
class DialogInputHost(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInputHost, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.hosts_key = args[2]
        self.ui = None

        self._set_ui()
        self._set_signal()
        if self.hosts_key is not None:
            self._edit_host()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INPUT_HOST, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('存檔')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self._set_combo_box()
        self.ui.lineEdit_clinic_name.setFocus()

    def _set_combo_box(self):
        ui_utils.set_combo_box(self.ui.comboBox_charset, ['utf8', 'utf8mb4', 'big5'])
        ui_utils.set_combo_box(self.ui.comboBox_vendor, list(VENDOR_LIST.keys()), None)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.comboBox_vendor.currentTextChanged.connect(self._set_HIS_version)

    def _set_HIS_version(self):
        self.ui.comboBox_HIS_version.clear()

        if self.ui.comboBox_vendor.currentText() == '':
            return

        ui_utils.set_combo_box(
            self.ui.comboBox_HIS_version,
            VENDOR_LIST[self.ui.comboBox_vendor.currentText()],
            None
        )

    def _edit_host(self):
        sql = f'''
            SELECT * FROM hosts
            WHERE
                HostsKey = {self.hosts_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self.ui.lineEdit_clinic_name.setText(row['ClinicName'])
        self.ui.lineEdit_host_name.setText(row['Host'])
        self.ui.lineEdit_user_name.setText(row['UserName'])
        self.ui.lineEdit_password.setText(row['Password'])
        self.ui.comboBox_database_name.setCurrentText(string_utils.xstr(row['DatabaseName']))
        self.ui.comboBox_charset.setCurrentText(string_utils.xstr(row['Charset']))
        self.ui.comboBox_vendor.setCurrentText(string_utils.xstr(row['Vendor']))
        self.ui.comboBox_HIS_version.setCurrentText(string_utils.xstr(row['HISVersion']))
        self.ui.lineEdit_image_dir.setText(row['ImageDir'])

        if '顯示分院病歷' in string_utils.xstr(row['Function']):
            self.ui.checkBox_past_history.setChecked(True)
        if '分院統計' in string_utils.xstr(row['Function']):
            self.ui.checkBox_statistic.setChecked(True)

    def accepted_button_clicked(self):
        if self.hosts_key is None:
            self._insert_host()
        else:
            self._update_host()

    def _get_function(self):
        items = []

        if self.ui.checkBox_past_history.isChecked():
            items.append('顯示分院病歷')
        if self.ui.checkBox_statistic.isChecked():
            items.append('分院統計')
        if self.ui.checkBox_massage.isChecked():
            items.append('養生館')

        function = ', '.join(items)
        if function == '':
            function = None

        return function

    def _insert_host(self):
        function = self._get_function()

        fields = [
            'ClinicName', 'Host', 'DatabaseName', 'UserName', 'Password', 'Charset',
            'Vendor', 'HISVersion', 'Function', 'ImageDir',
        ]
        data = [
            self.ui.lineEdit_clinic_name.text(),
            self.ui.lineEdit_host_name.text(),
            self.ui.comboBox_database_name.currentText(),
            self.ui.lineEdit_user_name.text(),
            self.ui.lineEdit_password.text(),
            self.ui.comboBox_charset.currentText(),
            self.ui.comboBox_vendor.currentText(),
            self.ui.comboBox_HIS_version.currentText(),
            function,
            self.ui.lineEdit_image_dir.text(),
        ]
        self.database.insert_record('hosts', fields, data)

    def _update_host(self):
        function = self._get_function()

        fields = [
            'ClinicName', 'Host', 'DatabaseName', 'UserName', 'Password', 'Charset',
            'Vendor', 'HISVersion', 'Function', 'ImageDir',
        ]
        data = [
            self.ui.lineEdit_clinic_name.text(),
            self.ui.lineEdit_host_name.text(),
            self.ui.comboBox_database_name.currentText(),
            self.ui.lineEdit_user_name.text(),
            self.ui.lineEdit_password.text(),
            self.ui.comboBox_charset.currentText(),
            self.ui.comboBox_vendor.currentText(),
            self.ui.comboBox_HIS_version.currentText(),
            function,
            self.ui.lineEdit_image_dir.text(),
        ]

        self.database.update_record(
            'hosts', fields, 'HostsKey', self.hosts_key, data
        )
