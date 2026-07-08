# -*- coding: UTF-8 -*-

import datetime

from PyQt5 import QtWidgets

from libs import string_utils, system_utils, ui_utils


# 三高加強照護 202
class Patient3H(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(Patient3H, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_3H_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PATIENT_3H, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.dateEdit_case_date.setDate(datetime.date.today())

    # 設定信號
    def _set_signal(self):
        pass

    def _read_3H_data(self):
        sql = """
            SELECT * FROM patient
            WHERE
                PatientKey = %s
        """
        params = (self.patient_key,)
        rows = self.database.select_record(sql, params)
        if not rows:
            return

        row = rows[0]

        self.ui.label_name.setText(
            f"姓名: {string_utils.xstr(row['Name'])} ({string_utils.xstr(row['Gender'])})"
        )
        self.ui.label_birthday.setText(f"生日: {row['Birthday'].strftime('%Y-%m-%d')}")
        self.ui.label_ID.setText(f"身份證: {string_utils.xstr(row['ID'])}")
        phone = string_utils.xstr(row["Cellphone"]) or string_utils.xstr(
            row["Telephone"]
        )
        self.ui.label_telephone.setText(f"電話: {phone}")
        self.ui.label_address.setText(f"地址: {string_utils.xstr(row['Address'])}")
