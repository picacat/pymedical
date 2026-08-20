# -*- coding: UTF-8 -*-

import datetime
import sys

from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter

from libs import (
    case_utils,
    date_utils,
    nhi_utils,
    number_utils,
    printer_utils,
    string_utils,
    system_utils,
)


# 掛號收據格式7 3"套表掛號單 (厚德堂櫃台)
# 2020.12.28
class PrintRegistrationForm10:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None

        self.printer = printer_utils.get_printer(
            self.system_settings, "門診掛號單印表機"
        )
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        self.return_card = None

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
        self.font_name = system_utils.get_font()
        self.font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)

    def _set_signal(self):
        pass

    def print(self, return_card=None):
        self.return_card = return_card
        self.print_painter()

    def preview(self, return_card=None):
        self.return_card = return_card
        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        self.preview_dialog.paintRequested.connect(self.print_painter)
        self.preview_dialog.resize(
            geometry.width(), geometry.height()
        )  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def _get_medical_record(self):
        sql = f"""
        SELECT
            cases.CaseKey, cases.PatientKey, cases.Name, cases.CaseDate, cases.RegistNo, cases.Room,
            cases.InsType, cases.Share, cases.TreatType, cases.RegistFee, cases.SDiagShareFee,
            cases.DepositFee, cases.Card, cases.Continuance, cases.Visit, cases.Register,
            cases.Doctor as CaseDoctor, wait.Doctor,
            patient.DiscountType, patient.Gender, patient.Birthday
        FROM cases
            LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            LEFT JOIN wait ON wait.CasEKey = cases.CaseKey
        WHERE
            cases.CaseKey = {self.case_key}
        """
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return None

        row = rows[0]
        clinic_name = printer_utils.get_clinic_name(self.system_settings)

        case_date = string_utils.xstr(row["CaseDate"].date())
        case_date = date_utils.west_date_to_nhi_date(case_date)
        case_date = f"{case_date[:3]}.{case_date[3:5]}.{case_date[5:]}"
        case_time = string_utils.xstr(row["CaseDate"].time())[:5]

        try:
            birth_date = string_utils.xstr(row["Birthday"])
            birth_date = date_utils.west_date_to_nhi_date(birth_date)
            birth_date = f"{birth_date[:3]}.{birth_date[3:5]}.**"
        except Exception:
            birth_date = ""

        card = string_utils.xstr(row["Card"])
        if number_utils.get_integer(row["Continuance"]) >= 1:
            card += "-" + string_utils.xstr(row["Continuance"])

        regist_fee = number_utils.get_integer(row["RegistFee"])
        diag_share_fee = number_utils.get_integer(row["SDiagShareFee"])
        deposit_fee = number_utils.get_integer(row["DepositFee"])
        return_card_note = ""

        if self.return_card == "還卡收據":
            return_date = case_utils.get_return_date(self.database, row["CaseKey"])
            if return_date is None:
                case_date = datetime.datetime.today()
                case_time = datetime.datetime.now().time().strftime("%H:%M")
            else:
                case_date = string_utils.xstr(return_date.date())
                case_time = string_utils.xstr(return_date.time())[:5]

            case_date = date_utils.west_date_to_nhi_date(case_date)
            case_date = f"{case_date[:3]}.{case_date[3:5]}.{case_date[5:]}"
            regist_fee = 0
            diag_share_fee = 0
            deposit_fee = -number_utils.get_integer(row["DepositFee"])
            return_card_note = "還卡"

        total_fee = (string_utils.xstr(regist_fee + diag_share_fee + deposit_fee),)

        room = string_utils.xstr(row["Room"])
        doctor = string_utils.xstr(row["InsType"])
        registrar = string_utils.xstr(row["Register"])

        if clinic_name == "啟新中醫診所":
            room = ""
            doctor = ""
            registrar = ""

        medical_record = dict()
        medical_record["patient_key"] = string_utils.xstr(row["PatientKey"])
        medical_record["gender"] = string_utils.xstr(row["Gender"])
        medical_record["birthday"] = birth_date
        medical_record["patient_name"] = string_utils.get_mask_name(
            string_utils.xstr(row["Name"]), mask_character="＊"
        )
        medical_record["registration_no"] = string_utils.xstr(row["RegistNo"])
        medical_record["share"] = string_utils.xstr(row["Share"])
        medical_record["room"] = room
        medical_record["massager"] = string_utils.xstr(row["Doctor"])
        medical_record["visit"] = string_utils.xstr(row["Visit"])
        medical_record["ins_type"] = doctor
        medical_record["treat_type"] = string_utils.xstr(row["TreatType"])
        medical_record["discount_type"] = string_utils.xstr(row["DiscountType"])
        medical_record["registrar"] = registrar

        medical_record["clinic_name"] = clinic_name
        medical_record["case_date"] = case_date
        medical_record["case_time"] = case_time
        medical_record["card"] = card
        medical_record["regist_fee"] = regist_fee
        medical_record["diag_share_fee"] = diag_share_fee
        medical_record["deposit_fee"] = deposit_fee
        medical_record["total_fee"] = total_fee
        medical_record["return_card_note"] = return_card_note

        if medical_record["massager"] == "":
            medical_record["massager"] = string_utils.xstr(row["CaseDoctor"])

        return row, medical_record

    def _get_traditional_health_care_fee(self):
        sql = f'''
            SELECT TotalFee FROM cases
            WHERE
                InsType = "自費" AND
                Position1 = "{self.case_key}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            traditional_health_care_fee = number_utils.get_integer(rows[0]["TotalFee"])
        else:
            traditional_health_care_fee = 0

        return traditional_health_care_fee

    def print_painter(self):
        row, medical_record = self._get_medical_record()
        if medical_record is None:
            return

        self.printer.setPaperSize(QtCore.QSizeF(5, 3), QPrinter.Inch)

        if sys.platform == "win32":
            lines = [20, 110, 170, 230]
        else:
            lines = [0, 95, 155, 215]

        tradtional_health_care_fee = self._get_traditional_health_care_fee()
        if tradtional_health_care_fee > 0:
            remark = f"自費: {tradtional_health_care_fee}"
        else:
            remark = medical_record["treat_type"]
            if remark in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST:
                remark = "中度複針"
            elif remark in nhi_utils.MODERATE_COMPLICATED_MASSAGE_TREAT:
                remark = "中度複傷"
            elif remark in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST:
                remark = "高度複針"
            elif remark in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT:
                remark = "高度複傷"
            else:
                remark = remark[:4]

        painter = QtGui.QPainter()

        painter.begin(self.printer)

        font = QtGui.QFont(self.font_name, 14, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(20, 50, medical_record["clinic_name"])

        font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(40, lines[1], medical_record["patient_key"])
        painter.drawText(
            120,
            lines[1],
            medical_record["patient_name"] + f"({medical_record['gender']})",
        )

        font = QtGui.QFont(self.font_name, 10, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(120, lines[1] + 14, medical_record["birthday"])

        font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(250, lines[1], medical_record["visit"])
        painter.drawText(350, lines[1], medical_record["registration_no"])

        try:
            case_count = case_utils.get_case_times(
                self.database, medical_record["patient_key"], row["CaseDate"]
            )
            font = QtGui.QFont(self.font_name, 9, QtGui.QFont.PreferQuality)
            painter.setFont(font)
            painter.drawText(230, lines[1] + 14, f"本月門診{case_count:0>2}次")
        except Exception:
            pass

        painter.drawText(40, lines[2] - 5, f"{medical_record['room']}診")
        painter.drawText(15, lines[2] + 10, f"{medical_record['massager']}醫師")
        painter.drawText(120, lines[2], medical_record["ins_type"])
        painter.drawText(210, lines[2], string_utils.xstr(medical_record["regist_fee"]))
        painter.drawText(
            290, lines[2], string_utils.xstr(medical_record["diag_share_fee"])
        )
        painter.drawText(
            360, lines[2], string_utils.xstr(medical_record["deposit_fee"])
        )

        font = QtGui.QFont(self.font_name, 10, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(30, lines[3], medical_record["case_date"])

        font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(110, lines[3], medical_record["case_time"])

        painter.drawText(190, lines[3], medical_record["card"])
        painter.drawText(250, lines[3], remark)
        painter.drawText(340, lines[3], medical_record["registrar"])

        painter.end()
