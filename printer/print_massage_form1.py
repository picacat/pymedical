# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter

from libs import date_utils, printer_utils, string_utils, system_utils


# 民俗調理單1 3"空白人形掛號單
# 2022.08.13
class PrintMassageForm1:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None

        self.printer = printer_utils.get_printer(
            self.system_settings, "民俗調理單印表機"
        )
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        self.current_print = None

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
        font = system_utils.get_font(self.system_settings)
        self.font = QtGui.QFont(font, 16, QtGui.QFont.PreferQuality)

    def _set_signal(self):
        pass

    def print(self, print_option=None):
        self.print_painter(True)

    def preview(self, print_option=None):
        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        self.preview_dialog.paintRequested.connect(self.print_painter)
        self.preview_dialog.resize(
            geometry.width(), geometry.height()
        )  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def print_painter(self, printing=None):
        row = self._get_case_row(self.case_key)

        patient_name = string_utils.xstr(row["Name"])
        birthday = string_utils.xstr(row["Birthday"])
        registration_no = string_utils.xstr(row["RegistNo"])
        case_date = string_utils.xstr(row["CaseDate"].date())
        case_time = string_utils.xstr(row["CaseDate"].time())[:5]

        self.current_print = self.print_painter
        self.printer.setPaperSize(QtCore.QSizeF(4.5, 3), QPrinter.Inch)

        painter = QtGui.QPainter()
        painter.begin(self.printer)
        font = QtGui.QFont(system_utils.get_font(), 16, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(10, 50, f"姓名: {patient_name}")
        painter.drawText(10, 80, f"生日: {date_utils.date_to_zh_tw_date(birthday)}")
        painter.drawText(10, 110, f"日期: {date_utils.date_to_zh_tw_date(case_date)}")
        painter.drawText(10, 140, f"時間: {case_time}")
        painter.drawText(10, 170, f"序號: {registration_no}")
        font = QtGui.QFont(system_utils.get_font(), 10, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(10, 200, self.system_settings.field("民俗調理單地址"))
        painter.drawText(10, 230, self.system_settings.field("民俗調理單備註"))

        pixmap = QtGui.QPixmap("./images/physical.jpg")
        painter.drawPixmap(
            QtCore.QPoint(190, 20), pixmap.scaled(240, 240, QtCore.Qt.KeepAspectRatio)
        )

        painter.end()

    def _get_case_row(self, case_key):
        sql = f"""
            SELECT cases.*, patient.Birthday FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                CaseKey = {case_key}
        """
        row = self.database.select_record(sql)[0]

        if string_utils.xstr(row["TreatType"]) != "民俗調理":
            sql = f'''
                SELECT cases.*, patient.Birthday FROM cases
                    LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
                WHERE
                    Position1 = "{case_key}"
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                return

            row = rows[0]

        return row
