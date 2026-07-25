# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtWidgets

from libs import class_utils, nhi_utils, string_utils, system_utils, ui_utils


# 主視窗
class DialogInsCare(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInsCare, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.treat_type = args[2]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INS_CARE, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("存檔")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")
        self.ui.tableWidget_ins_care.setFocus()
        self.table_widget_ins_care = class_utils.get_table_widget(
            self.ui.tableWidget_ins_care, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [100, 270, 90]
        self.table_widget_ins_care.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_ins_care.doubleClicked.connect(self._table_double_clicked)

    def _table_double_clicked(self):
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).animateClick()

    def accepted_button_clicked(self):
        self.ins_code = self.table_widget_ins_care.field_value(0)
        self.close()

    def _read_data(self):
        if self.treat_type in nhi_utils.CANCER_CARE_TREAT:
            sql = """
                SELECT * FROM charge_settings
                WHERE
                    InsCode IN ('P56006', 'P56007')
                ORDER BY InsCode
            """
        elif self.treat_type in ["小兒氣喘"]:
            sql = """
                SELECT * FROM charge_settings
                WHERE
                    InsCode IN ('C01', 'C02')
                ORDER BY InsCode
            """
        elif self.treat_type in ["小兒腦性麻痺"]:
            sql = """
                SELECT * FROM charge_settings
                WHERE
                    InsCode IN ('C03', 'C04')
                ORDER BY InsCode
            """
        elif self.treat_type in ["慢性腎病照護"]:
            ins_code = [
                # "P64001",
                # "P64002",
                # "P64003",
                # "P64004",
                # "P64005",
                # "P64006",
                # "P64007",
                # "P64008",
                # "P64009",
                # "P640010",
                "P64011",
                "P64012",
                "P64013",
                "P64014",
                "09006C",
                "09015C",
                "09044C",
            ]
            sql = f"""
                SELECT * FROM charge_settings
                WHERE
                    InsCode IN {tuple(ins_code)}
                ORDER BY InsCode
            """
        elif self.treat_type in ["癌症中醫門診延長照護"]:
            ins_code = [
                "P59011",
                "P59051",
                "P59052",
                "P59061",
                "P59062",
                "P59063",
            ]
            sql = f"""
                SELECT * FROM charge_settings
                WHERE
                    InsCode IN {tuple(ins_code)}
                ORDER BY InsCode
            """
        else:
            return

        self.table_widget_ins_care.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        ins_care_row = [
            string_utils.xstr(row["InsCode"]),
            string_utils.xstr(row["ItemName"]),
            string_utils.xstr(row["Amount"]),
        ]

        for column in range(len(ins_care_row)):
            self.ui.tableWidget_ins_care.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(ins_care_row[column])
            )

            if column in [2]:
                self.ui.tableWidget_ins_care.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
