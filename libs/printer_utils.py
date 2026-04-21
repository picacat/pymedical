# -*- coding: utf-8 -*-

import html
import importlib
import json
import sys

from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter, QPrinterInfo
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (
    case_utils,
    date_utils,
    dialog_utils,
    nhi_utils,
    number_utils,
    prescript_utils,
    string_utils,
)

PRINT_MODE = ["不印", "列印", "藥品", "詢問", "預覽"]
PRINT_MODE2 = ["不印", "列印", "藥品", "詢問", "預覽", "健保", "自費"]
PAPER_SIZE = ["A4", "Letter"]

PRINT_REGISTRATION_FORM = [
    "01-熱感紙掛號單",
    '02-11"中二刀空白掛號單',
    '03-3"套表掛號單',
    '04-2.5x3"熱感掛號單',
    '05-3"套表掛號單',
    '06-3"套表掛號單',
    '07-3"套表掛號單',
    '08-3"空白掛號單',
    '09-3"空白簡易掛號單',
    '10-3"套表掛號單',
    '11-3"套表掛號單',
    '12-2.5"套表掛號單',
    '13-3"套表掛號單',
    '14-3"套表掛號單',
    '15-4"空白掛號單',
    '16-3"空白簡易掛號單',
    '17-5.5"套表掛號單',
    '18-2.5"套表掛號單',
    "19-80mm熱感掛號單(含人形圖)",
    "20-80mm熱感掛號單(二維碼)",
    "21-80mm熱感掛號單2(二維碼)",
    "22-60mm熱感繳費證明單",
]

PRINT_MASSAGE_FORM = [
    '01-3"空白人形民俗調理單',
    "03-80mm熱感民俗調理單",
    '08-3"空白民俗調理單',
    '09-3"空白簡易民俗單',
    '10-3"套表民俗調理單',
    '12-2.5"套表民俗調理單',
    '13-3"套表民俗調理單',
    '14-3"套表民俗調理單',
    '18-2.5"套表民俗調理單',
]

PRINT_PRESCRIPTION_INS_FORM = [
    '01-11"中二刀健保處方箋',
    '02-2"健保處方箋',
    '03-3"健保處方箋',
    '04-4"健保處方箋',
    '05-2.5"健保處方箋',
    "06-A6健保處方箋",
    '07-3x4"健保處方箋',
    '08-3"友杏格式健保處方箋',
    "09-80mm熱感紙健保處方箋",
]

PRINT_PRESCRIPTION_SELF_FORM = [
    '01-11"中二刀自費處方箋',
    '02-2"自費處方箋',
    '03-3"自費處方箋',
    '04-4"自費處方箋',
    '05-2.5"自費處方箋',
    "06-A6健保處方箋",
    "09-80mm熱感紙自費處方箋",
]

PRINT_RECEIPT_INS_FORM = [
    '01-11"中二刀健保醫療收據',
    '02-2"健保醫療收據',
    '03-3"健保醫療收據',
    '04-4"健保醫療收據',
    '05-2.5"健保醫療收據',
    '06-3"友杏格式健保醫療收據',
    "07-A6健保醫療收據",
    '08-4x3"友杏格式健保醫療收據',
    '09-3"8號字友杏格式健保醫療收據',
    '10-2.5"健保醫療收據',
    '12-2.5"健保醫療收據',
    "13-熱感批價證明單",
    '14-3"友杏格式處方字體可變健保醫療收據',
    '15-3"友杏格式單行健保醫療收據',
    "16-熱感掛號機繳費證明單",
    "17-80mm熱感紙健保醫療收據",
    '18-11"中二刀左收據右處方健保醫療收據',
    '19-3"左收據右處方健保醫療收據',
    '20-5.5"健保醫療收據',
    '21-2"健保醫療收據',
    "22-A6健保醫療收據",
    "23-80mm熱感紙健保醫療收據(有框)",
    "24-80mm熱感紙健保醫療收據(客制)",
    "25-60mm熱感繳費證明",
    "26-60mm熱感紙健保醫療收據(有框)",
    "27-A5健保醫療收據",
    "28-80mm熱感紙健保醫療收據(橫印)",
    "29-80mm熱感紙健保醫療收據(橫印)",
]

PRINT_RECEIPT_SELF_FORM = [
    '01-11"中二刀自費醫療收據',
    '02-2"自費醫療收據',
    '03-3"自費醫療收據',
    '04-4"自費醫療收據',
    '05-2.5"自費醫療收據',
    '06-3"友杏格式自費醫療收據',
    "07-A6自費醫療收據",
    '08-4x3"友杏格式自費醫療收據',
    '09-3"官制格式自費醫療收據',
    '10-3"8號字友杏格式自費醫療收據',
    '11-2.5"自費醫療收據',
    '12-2.5"自費醫療收據',
    '14-3"友杏格式處方字體可變自費醫療收據',
    '15-3"友杏格式單行健保醫療收據',
    "17-80mm熱感紙自費醫療收據",
    '18-11"中二刀左收據右處方自費醫療收據',
    "22-A6自費醫療收據",
    "23-80mm熱感紙自費醫療收據(有框)",
    "24-80mm熱感紙自費醫療收據(客制)",
    "27-A5自費醫療收據",
    "29-80mm熱感紙自費醫療收據(橫印)",
]

PRINT_MISC_FORM = [
    '01-3"自費同意書',
    '02-4"自費同意書',
    '03-3"醫囑單',
    '04-3"健保格式醫療費用收據',
    '05-2.5"醫療費用收據',
    '06-2.5"健保格式醫療費用收據',
    "07-A5健保格式醫療費用收據",
    "08-A6健保格式醫療費用收據",
    '09-3"藥袋標示',
    '10-3"自費印花稅總繳收據',
    '11-3"自費格式醫療費用收據',
    '12-3"自費費用收據',
    "13-80mm熱感紙醫療費用收據",
    "14-80mm健保格式醫療費用收據",
    "15-60mm自費同意書",
    "16-80mm自費同意書",
    '17-3"健保及自費印花稅總繳收據',
    '21-3"二維條碼處方箋',
    "30-80mm熱感領藥單",
]

PRINT_PRESCRIPTION_BAG_FORM = [
    '01-10"套表藥袋',
    '02-10"套表藥袋',
    '03-10"套表藥袋',  # 脈悅
    "04-A4套表藥袋",
    '05-10"套表藥袋',
    "06-40x20mm藥包標籤",
    '07-10"套表藥袋',  # 仙岩頤光
    '08-10"公版套表藥袋',  # 脈蘊
]


PRINT_RESERVATION_FORM = [
    '03-3"預約單',
    '04-2"預約單',
    '05-2.5"預約單',
    '06-3"預約單',
    '07-4"預約單',
    "08-熱感預約單",
]


# 取得印表機列表
def get_printer_list():
    printer_info = QPrinterInfo()
    printer_list = printer_info.availablePrinterNames()

    return printer_list


# 取得 text document 邊界
def get_document_margin():
    if sys.platform == "win32":
        return 0
    else:
        return 0  # EPSON LQ-310 (driver: EPSON 24-pin series, resolution 360 * 180, paper size: US Letter


# 取得 text document
def get_document(printer, font):
    paper_size = QtCore.QSizeF()
    paper_size.setWidth(printer.width())
    paper_size.setHeight(printer.height())

    document = QtGui.QTextDocument()
    document.setDefaultFont(font)
    document.setPageSize(paper_size)
    document.documentLayout().setPaintDevice(printer)

    return document


# 自訂健保醫療收據紙張大小邊界
# def set_paper_size(printer, system_settings, width, length, size_unit, print_type):
#     printer.setPaperSize(QtCore.QSizeF(width, length), size_unit)
#     if system_settings.field(f'自訂{print_type}尺寸邊界') == 'Y':
#         set_printer_size_margins(printer, system_settings, print_type)


def set_paper_size(
    printer,
    system_settings,
    width_or_enum,
    length=None,
    size_unit=None,
    print_type=None,
):
    if isinstance(width_or_enum, QPrinter.PageSize):
        printer.setPaperSize(width_or_enum)
    else:
        printer.setPaperSize(QtCore.QSizeF(width_or_enum, length), size_unit)

    if system_settings.field(f"自訂{print_type}尺寸邊界") == "Y":
        set_printer_size_margins(printer, system_settings, print_type)


# 自訂紙張大小邊界
def set_printer_size_margins(printer, system_settings, print_type):
    paper_width = number_utils.get_float(system_settings.field(f"{print_type}寬度"))
    paper_length = number_utils.get_float(system_settings.field(f"{print_type}長度"))
    if system_settings.field(f"{print_type}尺寸單位") == "英吋":
        paper_size_unit = QPrinter.Inch
    else:
        paper_size_unit = QPrinter.Millimeter

    printer.setPaperSize(QtCore.QSizeF(paper_width, paper_length), paper_size_unit)

    left_margin = number_utils.get_float(system_settings.field("醫療收據左邊界"))
    top_margin = number_utils.get_float(system_settings.field("醫療收據上邊界"))
    if system_settings.field("醫療收據邊界單位") == "英吋":
        paper_margin_unit = QPrinter.Inch
    else:
        paper_margin_unit = QPrinter.Millimeter

    # printer.setFullPage(True)
    printer.setPageMargins(left_margin, top_margin, 0, 0, paper_margin_unit)
    # printer.setPageMargins(QtCore.QMarginsF(0, 0, 0, 0))


# 取得印表機
def get_printer(system_settings, printer_name):
    printer = QPrinter(QPrinter.ScreenResolution)
    printer.setResolution(96)
    printer.setPrinterName(system_settings.field(printer_name))
    printer.setPageMargins(
        0.08, 0.08, 0.08, 0.08, QPrinter.Inch
    )  # left, right, top, bottom

    return printer


# 取得印表機
def get_painter_printer(system_settings, printer_name):
    printer = QPrinter(QPrinter.HighResolution)
    printer.setResolution(96)
    printer.setPrinterName(system_settings.field(printer_name))
    printer.setPageMargins(
        0.08, 0.08, 0.08, 0.08, QPrinter.Inch
    )  # left, right, top, bottom

    return printer


# 取得印表機
def get_paper_size(system_settings):
    paper_size = QPrinter.A4

    paper_size_setting = system_settings.field("報表印表機紙張大小")
    if paper_size_setting == "A4":
        paper_size = QPrinter.A4
    elif paper_size_setting == "Letter":
        paper_size = QPrinter.Letter

    return paper_size


def get_print_registration_form(form):
    if form == "01-熱感紙掛號單":
        from printer import print_registration_form1

        module = importlib.reload(print_registration_form1)
        print_form = module.PrintRegistrationForm1
    elif form == '02-11"中二刀空白掛號單':
        from printer import print_registration_form2

        module = importlib.reload(print_registration_form2)
        print_form = module.PrintRegistrationForm2
    elif form == '03-3"套表掛號單':
        from printer import print_registration_form3

        module = importlib.reload(print_registration_form3)
        print_form = module.PrintRegistrationForm3
    elif form == '04-2.5x3"熱感掛號單':
        from printer import print_registration_form4

        module = importlib.reload(print_registration_form4)
        print_form = module.PrintRegistrationForm4
    elif form == '05-3"套表掛號單':
        from printer import print_registration_form5

        module = importlib.reload(print_registration_form5)
        print_form = module.PrintRegistrationForm5
    elif form == '06-3"套表掛號單':
        from printer import print_registration_form6

        module = importlib.reload(print_registration_form6)
        print_form = module.PrintRegistrationForm6
    elif form == '07-3"套表掛號單':
        from printer import print_registration_form7

        module = importlib.reload(print_registration_form7)
        print_form = module.PrintRegistrationForm7
    elif form == '08-3"空白掛號單':
        from printer import print_registration_form8

        module = importlib.reload(print_registration_form8)
        print_form = module.PrintRegistrationForm8
    elif form == '09-3"空白簡易掛號單':
        from printer import print_registration_form9

        module = importlib.reload(print_registration_form9)
        print_form = module.PrintRegistrationForm9
    elif form == '10-3"套表掛號單':
        from printer import print_registration_form10

        module = importlib.reload(print_registration_form10)
        print_form = module.PrintRegistrationForm10
    elif form == '11-3"套表掛號單':
        from printer import print_registration_form11

        module = importlib.reload(print_registration_form11)
        print_form = module.PrintRegistrationForm11
    elif form == '12-2.5"套表掛號單':
        from printer import print_registration_form12

        module = importlib.reload(print_registration_form12)
        print_form = module.PrintRegistrationForm12
    elif form == '13-3"套表掛號單':
        from printer import print_registration_form13

        module = importlib.reload(print_registration_form13)
        print_form = module.PrintRegistrationForm13
    elif form == '14-3"套表掛號單':
        from printer import print_registration_form14

        module = importlib.reload(print_registration_form14)
        print_form = module.PrintRegistrationForm14
    elif form == '15-4"空白掛號單':
        from printer import print_registration_form15

        module = importlib.reload(print_registration_form15)
        print_form = module.PrintRegistrationForm15
    elif form == '16-3"空白簡易掛號單':
        from printer import print_registration_form16

        module = importlib.reload(print_registration_form16)
        print_form = module.PrintRegistrationForm16
    elif form == '17-5.5"套表掛號單':
        from printer import print_registration_form17

        module = importlib.reload(print_registration_form17)
        print_form = module.PrintRegistrationForm17
    elif form == '18-2.5"套表掛號單':
        from printer import print_registration_form18

        module = importlib.reload(print_registration_form18)
        print_form = module.PrintRegistrationForm18
    elif form == "19-80mm熱感掛號單(含人形圖)":
        from printer import print_registration_form19

        module = importlib.reload(print_registration_form19)
        print_form = module.PrintRegistrationForm19
    elif form == "20-80mm熱感掛號單(二維碼)":
        from printer import print_registration_form20

        module = importlib.reload(print_registration_form20)
        print_form = module.PrintRegistrationForm20
    elif form == "21-80mm熱感掛號單2(二維碼)":
        from printer import print_registration_form21

        module = importlib.reload(print_registration_form21)
        print_form = module.PrintRegistrationForm21
    elif form == "22-60mm熱感繳費證明單":
        from printer import print_registration_form22

        module = importlib.reload(print_registration_form22)
        print_form = module.PrintRegistrationForm22
    else:
        print_form = None

    return print_form


def get_print_massage_form(form):
    if form == '01-3"空白人形民俗調理單':
        from printer import print_massage_form1

        module = importlib.reload(print_massage_form1)
        print_form = module.PrintMassageForm1
    if form == "03-80mm熱感民俗調理單":
        from printer import print_massage_form3

        module = importlib.reload(print_massage_form3)
        print_form = module.PrintMassageForm3
    elif form == '08-3"空白民俗調理單':
        from printer import print_massage_form8

        module = importlib.reload(print_massage_form8)
        print_form = module.PrintMassageForm8
    elif form == '09-3"空白簡易民俗單':
        from printer import print_massage_form9

        module = importlib.reload(print_massage_form9)
        print_form = module.PrintMassageForm9
    elif form == '10-3"套表民俗調理單':
        from printer import print_massage_form10

        module = importlib.reload(print_massage_form10)
        print_form = module.PrintMassageForm10
    elif form == '12-2.5"套表民俗調理單':
        from printer import print_massage_form12

        module = importlib.reload(print_massage_form12)
        print_form = module.PrintMassageForm12
    elif form == '13-3"套表民俗調理單':
        from printer import print_massage_form13

        module = importlib.reload(print_massage_form13)
        print_form = module.PrintMassageForm13
    elif form == '14-3"套表民俗調理單':
        from printer import print_massage_form14

        module = importlib.reload(print_massage_form14)
        print_form = module.PrintMassageForm14
    elif form == '18-2.5"套表民俗調理單':
        from printer import print_massage_form18

        module = importlib.reload(print_massage_form18)
        print_form = module.PrintMassageForm18
    else:
        print_form = None

    return print_form


def get_print_prescription_ins_form(form):
    if form == '01-11"中二刀健保處方箋':
        from printer import print_prescription_ins_form1

        module = importlib.reload(print_prescription_ins_form1)
        print_form = module.PrintPrescriptionInsForm1
    elif form == '02-2"健保處方箋':
        from printer import print_prescription_ins_form2

        module = importlib.reload(print_prescription_ins_form2)
        print_form = module.PrintPrescriptionInsForm2
    elif form == '03-3"健保處方箋':
        from printer import print_prescription_ins_form3

        module = importlib.reload(print_prescription_ins_form3)
        print_form = module.PrintPrescriptionInsForm3
    elif form == '04-4"健保處方箋':
        from printer import print_prescription_ins_form4

        module = importlib.reload(print_prescription_ins_form4)
        print_form = module.PrintPrescriptionInsForm4
    elif form == '05-2.5"健保處方箋':
        from printer import print_prescription_ins_form5

        module = importlib.reload(print_prescription_ins_form5)
        print_form = module.PrintPrescriptionInsForm5
    elif form == "06-A6健保處方箋":
        from printer import print_prescription_ins_form6

        module = importlib.reload(print_prescription_ins_form6)
        print_form = module.PrintPrescriptionInsForm6
    elif form == '07-3x4"健保處方箋':
        from printer import print_prescription_ins_form7

        module = importlib.reload(print_prescription_ins_form7)
        print_form = module.PrintPrescriptionInsForm7
    elif form == '08-3"友杏格式健保處方箋':
        from printer import print_prescription_ins_form8

        module = importlib.reload(print_prescription_ins_form8)
        print_form = module.PrintPrescriptionInsForm8
    elif form == "09-80mm熱感紙健保處方箋":
        from printer import print_prescription_ins_form9

        module = importlib.reload(print_prescription_ins_form9)
        print_form = module.PrintPrescriptionInsForm9
    else:
        print_form = None

    return print_form


def get_print_prescription_self_form(form):
    if form == '01-11"中二刀自費處方箋':
        from printer import print_prescription_self_form1

        module = importlib.reload(print_prescription_self_form1)
        print_form = module.PrintPrescriptionSelfForm1
    elif form == '02-2"自費處方箋':
        from printer import print_prescription_self_form2

        module = importlib.reload(print_prescription_self_form2)
        print_form = module.PrintPrescriptionSelfForm2
    elif form == '03-3"自費處方箋':
        from printer import print_prescription_self_form3

        module = importlib.reload(print_prescription_self_form3)
        print_form = module.PrintPrescriptionSelfForm3
    elif form == '04-4"自費處方箋':
        from printer import print_prescription_self_form4

        module = importlib.reload(print_prescription_self_form4)
        print_form = module.PrintPrescriptionSelfForm4
    elif form == '05-2.5"自費處方箋':
        from printer import print_prescription_self_form5

        module = importlib.reload(print_prescription_self_form5)
        print_form = module.PrintPrescriptionSelfForm5
    elif form == "06-A6健保處方箋":
        from printer import print_prescription_self_form6

        module = importlib.reload(print_prescription_self_form6)
        print_form = module.PrintPrescriptionSelfForm6
    elif form == "09-80mm熱感紙自費處方箋":
        from printer import print_prescription_self_form9

        module = importlib.reload(print_prescription_self_form9)
        print_form = module.PrintPrescriptionSelfForm9
    else:
        print_form = None

    return print_form


def get_print_receipt_ins_form(form):
    if form == '01-11"中二刀健保醫療收據':
        from printer import print_receipt_ins_form1

        module = importlib.reload(print_receipt_ins_form1)
        print_form = module.PrintReceiptInsForm1
    elif form == '02-2"健保醫療收據':
        from printer import print_receipt_ins_form2

        module = importlib.reload(print_receipt_ins_form2)
        print_form = module.PrintReceiptInsForm2
    elif form == '03-3"健保醫療收據':
        from printer import print_receipt_ins_form3

        module = importlib.reload(print_receipt_ins_form3)
        print_form = module.PrintReceiptInsForm3
    elif form == '04-4"健保醫療收據':
        from printer import print_receipt_ins_form4

        module = importlib.reload(print_receipt_ins_form4)
        print_form = module.PrintReceiptInsForm4
    elif form == '05-2.5"健保醫療收據':
        from printer import print_receipt_ins_form5

        module = importlib.reload(print_receipt_ins_form5)
        print_form = module.PrintReceiptInsForm5
    elif form == '06-3"友杏格式健保醫療收據':
        from printer import print_receipt_ins_form6

        module = importlib.reload(print_receipt_ins_form6)
        print_form = module.PrintReceiptInsForm6
    elif form == "07-A6健保醫療收據":
        from printer import print_receipt_ins_form7

        module = importlib.reload(print_receipt_ins_form7)
        print_form = module.PrintReceiptInsForm7
    elif form == '08-4x3"友杏格式健保醫療收據':
        from printer import print_receipt_ins_form8

        module = importlib.reload(print_receipt_ins_form8)
        print_form = module.PrintReceiptInsForm8
    elif form == '09-3"8號字友杏格式健保醫療收據':
        from printer import print_receipt_ins_form9

        module = importlib.reload(print_receipt_ins_form9)
        print_form = module.PrintReceiptInsForm9
    elif form == '10-2.5"健保醫療收據':
        from printer import print_receipt_ins_form10

        module = importlib.reload(print_receipt_ins_form10)
        print_form = module.PrintReceiptInsForm10
    elif form == '12-2.5"健保醫療收據':
        from printer import print_receipt_ins_form12

        module = importlib.reload(print_receipt_ins_form12)
        print_form = module.PrintReceiptInsForm12
    elif form == "13-熱感批價證明單":
        from printer import print_receipt_ins_form13

        module = importlib.reload(print_receipt_ins_form13)
        print_form = module.PrintReceiptInsForm13
    elif form == '14-3"友杏格式處方字體可變健保醫療收據':
        from printer import print_receipt_ins_form14

        module = importlib.reload(print_receipt_ins_form14)
        print_form = module.PrintReceiptInsForm14
    elif form == '15-3"友杏格式單行健保醫療收據':
        from printer import print_receipt_ins_form15

        module = importlib.reload(print_receipt_ins_form15)
        print_form = module.PrintReceiptInsForm15
    elif form == "16-熱感掛號機繳費證明單":
        from printer import print_receipt_ins_form16

        module = importlib.reload(print_receipt_ins_form16)
        print_form = module.PrintReceiptInsForm16
    elif form == "17-80mm熱感紙健保醫療收據":
        from printer import print_receipt_ins_form17

        module = importlib.reload(print_receipt_ins_form17)
        print_form = module.PrintReceiptInsForm17
    elif form == '18-11"中二刀左收據右處方健保醫療收據':
        from printer import print_receipt_ins_form18

        module = importlib.reload(print_receipt_ins_form18)
        print_form = module.PrintReceiptInsForm18
    elif form == '19-3"左收據右處方健保醫療收據':
        from printer import print_receipt_ins_form19

        module = importlib.reload(print_receipt_ins_form19)
        print_form = module.PrintReceiptInsForm18
    elif form == '20-5.5"健保醫療收據':
        from printer import print_receipt_ins_form20

        module = importlib.reload(print_receipt_ins_form20)
        print_form = module.PrintReceiptInsForm20
    elif form == '21-2"健保醫療收據':
        from printer import print_receipt_ins_form21

        module = importlib.reload(print_receipt_ins_form21)
        print_form = module.PrintReceiptInsForm21
    elif form == "22-A6健保醫療收據":
        from printer import print_receipt_ins_form22

        module = importlib.reload(print_receipt_ins_form22)
        print_form = module.PrintReceiptInsForm22
    elif form == "23-80mm熱感紙健保醫療收據(有框)":
        from printer import print_receipt_ins_form23

        module = importlib.reload(print_receipt_ins_form23)
        print_form = module.PrintReceiptInsForm23
    elif form == "24-80mm熱感紙健保醫療收據(客制)":
        from printer import print_receipt_ins_form24

        module = importlib.reload(print_receipt_ins_form24)
        print_form = module.PrintReceiptInsForm24
    elif form == "25-60mm熱感繳費證明":
        from printer import print_receipt_ins_form25

        module = importlib.reload(print_receipt_ins_form25)
        print_form = module.PrintReceiptInsForm25
    elif form == "26-60mm熱感紙健保醫療收據(有框)":
        from printer import print_receipt_ins_form26

        module = importlib.reload(print_receipt_ins_form26)
        print_form = module.PrintReceiptInsForm26
    elif form == "27-A5健保醫療收據":
        from printer import print_receipt_ins_form27

        module = importlib.reload(print_receipt_ins_form27)
        print_form = module.PrintReceiptInsForm27
    elif form == "28-80mm熱感紙健保醫療收據(橫印)":
        from printer import print_receipt_ins_form28

        module = importlib.reload(print_receipt_ins_form28)
        print_form = module.PrintReceiptInsForm28
    elif form == "29-80mm熱感紙健保醫療收據(橫印)":
        from printer import print_receipt_ins_form29

        module = importlib.reload(print_receipt_ins_form29)
        print_form = module.PrintReceiptInsForm29
    else:
        print_form = None

    return print_form


def get_print_receipt_self_form(form):
    if form == '01-11"中二刀自費醫療收據':
        from printer import print_receipt_self_form1

        module = importlib.reload(print_receipt_self_form1)
        print_form = module.PrintReceiptSelfForm1
    elif form == '02-2"自費醫療收據':
        from printer import print_receipt_self_form2

        module = importlib.reload(print_receipt_self_form2)
        print_form = module.PrintReceiptSelfForm2
    elif form == '03-3"自費醫療收據':
        from printer import print_receipt_self_form3

        module = importlib.reload(print_receipt_self_form3)
        print_form = module.PrintReceiptSelfForm3
    elif form == '04-4"自費醫療收據':
        from printer import print_receipt_self_form4

        module = importlib.reload(print_receipt_self_form4)
        print_form = module.PrintReceiptSelfForm4
    elif form == '05-2.5"自費醫療收據':
        from printer import print_receipt_self_form5

        module = importlib.reload(print_receipt_self_form5)
        print_form = module.PrintReceiptSelfForm5
    elif form == '06-3"友杏格式自費醫療收據':
        from printer import print_receipt_self_form6

        module = importlib.reload(print_receipt_self_form6)
        print_form = module.PrintReceiptSelfForm6
    elif form == "07-A6自費醫療收據":
        from printer import print_receipt_self_form7

        module = importlib.reload(print_receipt_self_form7)
        print_form = module.PrintReceiptSelfForm7
    elif form == '08-4x3"友杏格式自費醫療收據':
        from printer import print_receipt_self_form8

        module = importlib.reload(print_receipt_self_form8)
        print_form = module.PrintReceiptSelfForm8
    elif form == '09-3"官制格式自費醫療收據':
        from printer import print_receipt_self_form9

        module = importlib.reload(print_receipt_self_form9)
        print_form = module.PrintReceiptSelfForm9
    elif form == '10-3"8號字友杏格式自費醫療收據':
        from printer import print_receipt_self_form10

        module = importlib.reload(print_receipt_self_form10)
        print_form = module.PrintReceiptSelfForm10
    elif form == '11-2.5"自費醫療收據':
        from printer import print_receipt_self_form11

        module = importlib.reload(print_receipt_self_form11)
        print_form = module.PrintReceiptSelfForm11
    elif form == '12-2.5"自費醫療收據':
        from printer import print_receipt_self_form12

        module = importlib.reload(print_receipt_self_form12)
        print_form = module.PrintReceiptSelfForm12
    elif form == '14-3"友杏格式處方字體可變自費醫療收據':
        from printer import print_receipt_self_form14

        module = importlib.reload(print_receipt_self_form14)
        print_form = module.PrintReceiptSelfForm14
    elif form == '15-3"友杏格式單行健保醫療收據':
        from printer import print_receipt_self_form15

        module = importlib.reload(print_receipt_self_form15)
        print_form = module.PrintReceiptSelfForm15
    elif form == "17-80mm熱感紙自費醫療收據":
        from printer import print_receipt_self_form17

        module = importlib.reload(print_receipt_self_form17)
        print_form = module.PrintReceiptSelfForm17
    elif form == '18-11"中二刀左收據右處方自費醫療收據':
        from printer import print_receipt_self_form18

        module = importlib.reload(print_receipt_self_form18)
        print_form = module.PrintReceiptSelfForm18
    elif form == "22-A6自費醫療收據":
        from printer import print_receipt_self_form22

        module = importlib.reload(print_receipt_self_form22)
        print_form = module.PrintReceiptSelfForm22
    elif form == "23-80mm熱感紙自費醫療收據(有框)":
        from printer import print_receipt_self_form23

        module = importlib.reload(print_receipt_self_form23)
        print_form = module.PrintReceiptSelfForm23
    elif form == "24-80mm熱感紙自費醫療收據(客制)":
        from printer import print_receipt_self_form24

        module = importlib.reload(print_receipt_self_form24)
        print_form = module.PrintReceiptSelfForm24
    elif form == "27-A5自費醫療收據":
        from printer import print_receipt_self_form27

        module = importlib.reload(print_receipt_self_form27)
        print_form = module.PrintReceiptSelfForm27
    elif form == "29-80mm熱感紙自費醫療收據(橫印)":
        from printer import print_receipt_self_form29

        module = importlib.reload(print_receipt_self_form29)
        print_form = module.PrintReceiptSelfForm29
    else:
        print_form = None

    return print_form


def get_print_misc_form(form):
    if form == '01-3"自費同意書':
        from printer import print_misc_form1

        module = importlib.reload(print_misc_form1)
        print_form = module.PrintMiscForm1
    elif form == '02-4"自費同意書':
        from printer import print_misc_form2

        module = importlib.reload(print_misc_form2)
        print_form = module.PrintMiscForm2
    elif form == '03-3"醫囑單':
        from printer import print_misc_form3

        module = importlib.reload(print_misc_form3)
        print_form = module.PrintMiscForm3
    elif form == '04-3"健保格式醫療費用收據':
        from printer import print_misc_form4

        module = importlib.reload(print_misc_form4)
        print_form = module.PrintMiscForm4
    elif form == '05-2.5"醫療費用收據':
        from printer import print_misc_form5

        module = importlib.reload(print_misc_form5)
        print_form = module.PrintMiscForm5
    elif form == '06-2.5"健保格式醫療費用收據':
        from printer import print_misc_form6

        module = importlib.reload(print_misc_form6)
        print_form = module.PrintMiscForm6
    elif form == "07-A5健保格式醫療費用收據":
        from printer import print_misc_form7

        module = importlib.reload(print_misc_form7)
        print_form = module.PrintMiscForm7
    elif form == "08-A6健保格式醫療費用收據":
        from printer import print_misc_form8

        module = importlib.reload(print_misc_form8)
        print_form = module.PrintMiscForm8
    elif form == '09-3"藥袋標示':
        from printer import print_misc_form9

        module = importlib.reload(print_misc_form9)
        print_form = module.PrintMiscForm9
    elif form == '10-3"自費印花稅總繳收據':
        from printer import print_misc_form10

        module = importlib.reload(print_misc_form10)
        print_form = module.PrintMiscForm10
    elif form == '11-3"自費格式醫療費用收據':
        from printer import print_misc_form11

        module = importlib.reload(print_misc_form11)
        print_form = module.PrintMiscForm11
    elif form == '12-3"自費費用收據':
        from printer import print_misc_form12

        module = importlib.reload(print_misc_form12)
        print_form = module.PrintMiscForm12
    elif form == "13-80mm熱感紙醫療費用收據":
        from printer import print_misc_form13

        module = importlib.reload(print_misc_form13)
        print_form = module.PrintMiscForm13
    elif form == "14-80mm健保格式醫療費用收據":
        from printer import print_misc_form14

        module = importlib.reload(print_misc_form14)
        print_form = module.PrintMiscForm14
    elif form == "15-60mm自費同意書":
        from printer import print_misc_form15

        module = importlib.reload(print_misc_form15)
        print_form = module.PrintMiscForm15
    elif form == "16-80mm自費同意書":
        from printer import print_misc_form16

        module = importlib.reload(print_misc_form16)
        print_form = module.PrintMiscForm16
    elif form == '17-3"健保及自費印花稅總繳收據':
        from printer import print_misc_form17

        module = importlib.reload(print_misc_form17)
        print_form = module.PrintMiscForm17
    elif form == '21-3"二維條碼處方箋':
        from printer import print_misc_form21

        module = importlib.reload(print_misc_form21)
        print_form = module.PrintMiscForm21
    elif form == "22-60mm熱感繳費證明單":
        from printer import print_misc_form22

        module = importlib.reload(print_misc_form22)
        print_form = module.PrintMiscForm22
    elif form == "30-80mm熱感領藥單":
        from printer import print_misc_form30

        module = importlib.reload(print_misc_form30)
        print_form = module.PrintMiscForm30
    else:
        print_form = None

    return print_form


def get_print_prescription_bag_form(form):
    if form == '01-10"套表藥袋':
        from printer import print_prescription_bag_form1

        module = importlib.reload(print_prescription_bag_form1)
        print_form = module.PrintPrescriptionBagForm1
    elif form == '02-10"套表藥袋':
        from printer import print_prescription_bag_form2

        module = importlib.reload(print_prescription_bag_form2)
        print_form = module.PrintPrescriptionBagForm2
    elif form == '03-10"套表藥袋':
        from printer import print_prescription_bag_form3

        module = importlib.reload(print_prescription_bag_form3)
        print_form = module.PrintPrescriptionBagForm3
    elif form == "04-A4套表藥袋":
        from printer import print_prescription_bag_form4

        module = importlib.reload(print_prescription_bag_form4)
        print_form = module.PrintPrescriptionBagForm4
    elif form == '05-10"套表藥袋':
        from printer import print_prescription_bag_form5

        module = importlib.reload(print_prescription_bag_form5)
        print_form = module.PrintPrescriptionBagForm5
    elif form == "06-40x20mm藥包標籤":
        from printer import print_prescription_bag_form6

        module = importlib.reload(print_prescription_bag_form6)
        print_form = module.PrintPrescriptionBagForm6
    elif form == '07-10"套表藥袋':
        from printer import print_prescription_bag_form7

        module = importlib.reload(print_prescription_bag_form7)
        print_form = module.PrintPrescriptionBagForm7
    elif form == '08-10"公版套表藥袋':
        from printer import print_prescription_bag_form8

        module = importlib.reload(print_prescription_bag_form8)
        print_form = module.PrintPrescriptionBagForm8
    else:
        print_form = None

    return print_form


def get_print_reservation_form(form):
    if form == '03-3"預約單':
        from printer import print_reservation_form3

        module = importlib.reload(print_reservation_form3)
        print_form = module.PrintReservationForm3
    elif form == '04-2"預約單':
        from printer import print_reservation_form4

        module = importlib.reload(print_reservation_form4)
        print_form = module.PrintReservationForm4
    elif form == '05-2.5"預約單':
        from printer import print_reservation_form5

        module = importlib.reload(print_reservation_form5)
        print_form = module.PrintReservationForm5
    elif form == '06-3"預約單':
        from printer import print_reservation_form6

        module = importlib.reload(print_reservation_form6)
        print_form = module.PrintReservationForm6
    elif form == '07-4"預約單':
        from printer import print_reservation_form7

        module = importlib.reload(print_reservation_form7)
        print_form = module.PrintReservationForm7
    elif form == "08-熱感預約單":
        from printer import print_reservation_form8

        module = importlib.reload(print_reservation_form8)
        print_form = module.PrintReservationForm8
    else:
        print_form = None

    return print_form


# 自費處方箋格式3使用 專用
def get_case_html(
    database,
    case_key,
    ins_type,
    background_color=None,
    birthday_mask=True,
    tw_date=False,
    id_mask=True,
    medicine_set=None,
):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    # age = ''
    if birthday is not None:
        if birthday_mask:
            birthday = birthday.strftime("%Y-*-*")
        elif tw_date:
            birthday = string_utils.xstr(
                date_utils.west_date_to_nhi_date(row["Birthday"], "-")
            )

    id = row["ID"]
    if id_mask and id is not None:
        id = id[:6] + "****"

    if background_color is not None:
        color = f' style="background-color: {background_color}"'
    else:
        color = ""

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    if tw_date:
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"], "-")

    patient_key = get_patient_key(row)
    name = string_utils.xstr(row["Name"])
    birthday_str = string_utils.xstr(birthday)

    ins_type_label = get_ins_type_label(ins_type, medicine_set)

    html = f"""
        <tr>
          <td width="30%">病歷號:{patient_key}</td>
          <td width="30%">姓名:{name}</td>
          <td>身分證:{id}</td>
        </tr>
        <tr>
          <td{color} width="30%">就醫日:{case_date}</td>
          <td>保險:{ins_type_label}</td>
          <td width="40%">出生日:{birthday_str}</td>
        </td>
    """

    return html


# 處方箋格式1,2使用
def get_case_html_1(
    database, case_key, ins_type, background_color=None, print_time_label=False
):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    age = ""
    if birthday is not None:
        birthday = birthday.strftime("%Y****")
        age_year, age_month = date_utils.get_age(row["Birthday"], row["CaseDate"])
        if age_year is None:
            age = ""
        else:
            age = f"年齡:{age_year}歲"

    id = row["ID"]
    if id is not None:
        id = id[:6] + "****"

    if background_color is not None:
        color = f' style="background-color: {background_color}"'
    else:
        color = ""

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    patient_key = get_patient_key(row)
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    patient_id = string_utils.xstr(id)
    birthday_str = string_utils.xstr(birthday)
    share_type = string_utils.xstr(row["Share"])
    regist_no = string_utils.xstr(row["RegistNo"])
    print_time = date_utils.now_to_str()[11:16]

    if print_time_label:  # 明醫專用
        print_time_td = f"時間:{print_time}"
    else:
        print_time_td = ""

    html = f"""
        <tr>
          <td width="19%" {color}>日期:{case_date}</td>
          <td width="15%" >病號:{patient_key}</td>
          <td width="18%">姓名:{name} ({gender})</td>
          <td width="20%">證號:{patient_id}</td>
          <td width="25%" colspan="2">生日:{birthday_str} {age}</td>
        </tr>
    """
    if ins_type == "健保":
        html += f"""
            <tr>
              <td>保險:{ins_type}</td>
              <td>負擔:{share_type}</td>
              <td>卡序:{card}</td>
              <td>診號:{regist_no}</td>
              <td>{print_time_td}</td>
            </tr>
        """
    elif ins_type == "全部":
        pass
    else:
        html += f"""
            <tr>
              <td>保險:{ins_type}</td>
              <td>診號:{regist_no}</td>
              <td colspan="2">{print_time_td}</td>
            </tr>
        """

    return html


# 處方箋格式3使用
def get_case_html_2(
    database,
    case_key,
    ins_type,
    background_color=None,
    birthday_mask=True,
    tw_date=False,
    id_mask=True,
    medicine_set=None,
):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    # age = ''
    if birthday is not None:
        if birthday_mask:
            birthday = birthday.strftime("%Y-%m-%d")
        elif tw_date:
            birthday = string_utils.xstr(
                date_utils.west_date_to_nhi_date(row["Birthday"], "-")
            )

    id = row["ID"]
    if id_mask and id is not None:
        id = id[:6] + "****"

    if background_color is not None:
        color = f' style="background-color: {background_color}"'
    else:
        color = ""

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    if tw_date:
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"], "-")

    patient_key = get_patient_key(row)
    patient_key_header = get_patient_key_header(row, "病號")
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    birthday_str = string_utils.xstr(birthday)
    html = f"""
        <tr>
          <td{color} width="30%">診日:{case_date}</td>
          <td width="19%">{patient_key_header}:{patient_key}</td>
          <td width="23%">姓名:{name}</td>
          <td width="27%">生日:{birthday_str}</td>
        </tr>
    """

    share_type = string_utils.xstr(row["Share"])
    ins_type_label = get_ins_type_label(ins_type, medicine_set)

    if ins_type == "健保":
        html += f"""
            <tr>
              <td>身證:{id}</td>
              <td>保險:{ins_type_label}</td>
              <td>負擔:{share_type}</td>
              <td>卡序:{card}</td>
            </tr>
        """
    else:
        html += f"""
            <tr>
              <td>身分證:{id}</td>
              <td>保險:{ins_type_label}</td>
            </tr>
        """

    return html


# 處方箋格式3使用
def get_case_html_utec(
    database,
    case_key,
    ins_type,
    background_color=None,
    birthday_mask=True,
    tw_date=False,
    id_mask=True,
    medicine_set=None,
):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    # age = ''
    if birthday is not None:
        if birthday_mask:
            birthday = birthday.strftime("%Y-%m-%d")
        elif tw_date:
            birthday = string_utils.xstr(
                date_utils.west_date_to_nhi_date(row["Birthday"], "-")
            )

    id = row["ID"]
    if id_mask and id is not None:
        id = id[:6] + "****"

    if background_color is not None:
        color = f' style="background-color: {background_color}"'
    else:
        color = ""

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    if tw_date:
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"], "-")

    patient_key = get_patient_key(row)
    patient_key_header = get_patient_key_header(row, "病號")
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    birthday_str = string_utils.xstr(birthday)
    html = f"""
        <tr>
          <td width="30%">系統號:{patient_key}</td>
          <td width="30%">姓名:{name}</td>
          <td width="40%">身份證:{id} {gender}</td>
        </tr>
    """

    share_type = string_utils.xstr(row["Share"])
    ins_type_label = get_ins_type_label(ins_type, medicine_set)

    if ins_type == "健保":
        html += f"""
            <tr>
              <td width="30%">就醫日:{case_date}</td>
              <td>保險:{ins_type_label} {card}</td>
              <td>生日:{birthday_str}</td>
            </tr>
        """
    else:
        html += f"""
            <tr>
              <td>身分證:{id}</td>
              <td>保險:{ins_type_label}</td>
            </tr>
        """

    return html


# 其他收據80mm熱感紙
def get_case_html_13(
    database, case_key, ins_type, background_color=None, print_time_label=False
):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    age = ""
    if birthday is not None:
        birthday = birthday.strftime("%Y/**/**")
        age_year, age_month = date_utils.get_age(row["Birthday"], row["CaseDate"])
        if age_year is None:
            age = ""
        else:
            age = f"年齡:{age_year}歲"

    id = row["ID"]
    if id is not None:
        id = id[:6] + "****"

    if background_color is not None:
        color = f' style="background-color: {background_color}"'
    else:
        color = ""

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    patient_key = get_patient_key(row)
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    patient_id = string_utils.xstr(id)
    birthday_str = string_utils.xstr(birthday)
    share_type = string_utils.xstr(row["Share"])
    regist_no = string_utils.xstr(row["RegistNo"])
    print_time = date_utils.now_to_str()[11:16]

    if print_time_label:  # 明醫專用
        print_time_td = f"時間:{print_time}"
    else:
        print_time_td = ""

    html = f"""
        <tr>
          <td width="50%" {color}>日期:{case_date}</td>
          <td>病號:{patient_key}</td>
        </tr>
        <tr>
          <td>姓名:{name} ({gender})</td>
          <td>證號:{patient_id}</td>
        </tr>
        <tr>
          <td>生日:{birthday_str}</td>
          <td>{age}</td>
        </tr>
    """
    if ins_type == "健保":
        html += f"""
            <tr>
              <td>保險:{ins_type}</td>
              <td>負擔:{share_type}</td>
            </tr>
            <tr>
              <td>卡序:{card}</td>
              <td>診號:{regist_no}</td>
            </tr>
              <td>{print_time_td}</td>
            </tr>
        """
    elif ins_type == "全部":
        pass
    else:
        html += f"""
            <tr>
              <td>保險:{ins_type}</td>
              <td>診號:{regist_no}</td>
            </tr>
            <tr>
              <td colspan="2">{print_time_td}</td>
            </tr>
        """

    return html


def get_ins_type_label(ins_type, medicine_set):
    ins_type_label = ins_type
    medicine_set = number_utils.get_integer(medicine_set)
    if medicine_set >= 2:
        ins_type_label = f"{ins_type}({medicine_set - 1})"

    return ins_type_label


# 處方箋格式3使用
def get_case_html_2_1(
    database,
    case_key,
    ins_type,
    background_color=None,
    birthday_mask=True,
    tw_date=False,
    id_mask=True,
):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    # age = ''
    if birthday is not None:
        if birthday_mask:
            birthday = birthday.strftime("%Y-*-*")
        elif tw_date:
            birthday = string_utils.xstr(
                date_utils.west_date_to_nhi_date(row["Birthday"], "-")
            )

    id = row["ID"]
    if id_mask and id is not None:
        id = id[:6] + "****"

    if background_color is not None:
        color = f' style="background-color: {background_color}"'
    else:
        color = ""

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    if tw_date:
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"], "-")

    patient_key = get_patient_key(row)
    patient_key_header = get_patient_key_header(row, "病歷號")
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    birthday_str = string_utils.xstr(birthday)
    html = f"""
        <tr>
          <td{color} width="50%">就診日:{case_date}</td>
          <td width="40%">{patient_key_header}:{patient_key}</td>
        </tr>
        <tr>
            <td>姓名:{name}({gender})</td>
            <td>生日:{birthday_str}</td>
        </tr>
        <tr>
            <td>身證:{id}</td>
            <td>保險:{ins_type}</td>
        </tr>
    """

    share_type = string_utils.xstr(row["Share"])
    if ins_type == "健保":
        html += f"""
            <tr>
              <td>負擔:{share_type}</td>
              <td>卡序:{card}</td>
            </tr>
        """

    return html


# 處方箋格式5使用
def get_case_html_3(database, case_key, ins_type, medicine_set, background_color=None):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    if birthday is not None:
        birthday = birthday.strftime("%Y-*-*")
    else:
        birthday = ""

    patient_id = row["ID"]
    if patient_id is not None:
        patient_id = patient_id[:6] + "****"

    # if background_color is not None:
    #     color = f' style="background-color: {background_color}"'
    # else:
    #     color = ''

    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    birthday_str = string_utils.xstr(birthday)
    patient_key = get_patient_key(row)
    case_date = row["CaseDate"].strftime("%Y-%m-%d")

    if ins_type == "健保":
        html = f"""
            <tr>
              <td width="33%">姓名:{name} ({gender})</td>
              <td width="34%">出生日:{birthday_str}</td>
              <td width="33%">健保卡序:{card}</td>
            </tr>
        """
    else:
        if medicine_set is None:
            medicine_set = 2

        html = f"""
            <tr>
              <td width="33%">姓名:{name} ({gender})</td>
              <td width="34%">出生日:{birthday_str}</td>
              <td width="33%">保險別:{ins_type} ({medicine_set - 1})</td>
            </tr>
        """

    html += f"""
        <tr>
          <td width="30%">病歷號:{patient_key}</td>
          <td width="30%">身分證:{patient_id}</td>
          <td width="40%">就診日:{case_date}</td>
        </tr>
    """

    return html


# 其他收據格式6使用
def get_case_html_4(database, case_key, ins_type, background_color=None):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    # age = ''
    if birthday is not None:
        birthday = birthday.strftime("%Y-**-**")
        age_year, age_month = date_utils.get_age(row["Birthday"], row["CaseDate"])
        # if age_year is None:
        #     age = ''
        # else:
        #     age = f'{age_year}歲'

    id = row["ID"]
    if id is not None:
        id = id[:6] + "****"

    # if background_color is not None:
    #     color = f' style="background-color: {background_color}"'
    # else:
    #     color = ''

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    patient_key = get_patient_key(row)
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    patient_id = string_utils.xstr(id)
    birthday_str = string_utils.xstr(birthday)
    share_type = string_utils.xstr(row["Share"])
    room = string_utils.xstr(row["Room"])
    treat_type = string_utils.xstr(row["TreatType"])
    ins_type = string_utils.xstr(row["InsType"])
    # doctor = string_utils.xstr(row['Doctor'])
    # print_time = date_utils.now_to_str()[:16]

    html = f"""
        <tr>
          <td>病患姓名:{name}</td>
          <td>身分證號:{patient_id}</td>
          <td>出生日期:{birthday_str}</td>
          <td>病歷號碼:{patient_key}</td>
          <td>就醫科別:{room}診-{treat_type}</td>
        </tr>
        <tr>
          <td>性別:{gender}</td>
          <td>就診日期:{case_date}</td>
          <td>保險類別:{ins_type}</td>
          <td>就醫身份別:{share_type}</td>
          <td>健保卡就醫序號:{card}</td>
        </tr>
    """

    return html


# 其他收據格式4使用
def get_case_html_5(database, case_key, ins_type, tw_date=True, background_color=None):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    # age = ''
    if birthday is not None:
        birthday = birthday.strftime("***-%m-%d")
        # age_year, age_month = date_utils.get_age(row['Birthday'], row['CaseDate'])
        # if age_year is None:
        #     age = ''
        # else:
        #     age = f'{age_year}歲'

    id = row["ID"]
    if id is not None:
        id = id[:6] + "****"

    # if background_color is not None:
    #     color = f' style="background-color: {background_color}"'
    # else:
    #     color = ''

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    if tw_date:
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"], "-")

    patient_key = get_patient_key(row)
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    patient_id = string_utils.xstr(id)
    birthday_str = string_utils.xstr(birthday)
    share_type = string_utils.xstr(row["Share"])[:4]
    room = string_utils.xstr(row["Room"])
    treat_type = string_utils.xstr(row["TreatType"])
    ins_type = string_utils.xstr(row["InsType"])
    doctor = string_utils.xstr(row["Doctor"])
    # print_time = date_utils.now_to_str()[:16]

    html = f"""
        <tr>
          <td>姓名:{name} ({gender})</td>
          <td>身分證:{patient_id}</td>
          <td>生日:{birthday_str}</td>
        </tr>
        <tr>
          <td>病歷號:{patient_key}</td>
          <td>就診日:{case_date}</td>
          <td>保險:{ins_type}</td>
        </tr>
        <tr>
          <td>身份別:{share_type}</td>
          <td>科別:{treat_type}</td>
          <td>健保卡序:{card}</td>
        </tr>
        <tr>
          <td>診別:{room}診</td>
          <td>醫師:{doctor}</td>
          <td></td>
        </tr>
    """

    return html


# 處方箋格式7使用
def get_case_html_9(
    database,
    case_key,
    ins_type,
    background_color=None,
    birthday_mask=True,
    tw_date=False,
    id_mask=True,
):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    # age = ''
    if birthday is not None:
        if birthday_mask:
            birthday = birthday.strftime("%Y-*-*")
        elif tw_date:
            birthday = string_utils.xstr(
                date_utils.west_date_to_nhi_date(row["Birthday"], "-")
            )

    id = row["ID"]
    if id_mask and id is not None:
        id = id[:6] + "****"

    if background_color is not None:
        color = f' style="background-color: {background_color}"'
    else:
        color = ""

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    if tw_date:
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"], "-")

    patient_key = get_patient_key(row)
    patient_key_header = get_patient_key_header(row, "病號")
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    birthday_str = string_utils.xstr(birthday)
    html = f"""
        <tr>
          <td{color} width="28%">診日:{case_date}</td>
          <td width="20%">{patient_key_header}:{patient_key}</td>
          <td width="24%">姓名:{name}
          <td width="27%">生日:{birthday_str}</td>
        </tr>
    """

    share_type = string_utils.xstr(row["Share"])
    if ins_type == "健保":
        html += f"""
            <tr>
              <td>身證:{id}</td>
              <td>保險:{ins_type}</td>
              <td>負擔:{share_type}</td>
              <td>卡序:{card}</td>
            </tr>
        """
    else:
        html += f"""
            <tr>
              <td>身分證:{id}</td>
              <td>保險:{ins_type}</td>
            </tr>
        """

    return html


# 處方箋格式21使用
def get_case_html_21(database, case_key, ins_type, medicine_set, background_color=None):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    if birthday is not None:
        birthday = birthday.strftime("%Y-*-*")
    else:
        birthday = ""

    patient_id = row["ID"]
    if patient_id is not None:
        patient_id = patient_id[:6] + "****"

    # if background_color is not None:
    #     color = f' style="background-color: {background_color}"'
    # else:
    #     color = ''

    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    regist_no = string_utils.xstr(row["RegistNo"])
    birthday_str = string_utils.xstr(birthday)
    patient_key = get_patient_key(row)
    case_date = row["CaseDate"].strftime("%Y-%m-%d")

    if ins_type == "健保":
        html = f"""
            <tr>
              <td width="25%">姓名:{name} ({gender})</td>
              <td width="25%">生日:{birthday_str}</td>
              <td width="25%">性別:{gender}</td>
              <td width="25%">健保卡序:{card}</td>
            </tr>
        """
    else:
        if medicine_set is None:
            medicine_set = 2

        html = f"""
            <tr>
              <td width="25%">姓名:{name} ({gender})</td>
              <td width="25%">生日:{birthday_str}</td>
              <td width="25%">保險:{ins_type} ({medicine_set - 1})</td>
              <td width="25%"></td>
            </tr>
        """

    html += f"""
        <tr>
          <td width="25%">病歷號:{patient_key}</td>
          <td width="25%">身分證:{patient_id}</td>
          <td width="25%">就診日:{case_date}</td>
          <td width="25%">診號:{regist_no} - {ins_type}</td>
        </tr>
    """

    return html


# 收據格式21使用
def get_case_html_21_2(database, case_key, ins_type):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    case_date = row["CaseDate"].strftime("%Y/%m/%d")
    case_date = date_utils.west_date_to_nhi_date(row["CaseDate"], "/")
    birthday = row["Birthday"]
    if birthday is not None:
        birthday = string_utils.xstr(
            date_utils.west_date_to_nhi_date(row["Birthday"], "/")
        )
    else:
        birthday = ""

    patient_key = get_patient_key(row)
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    patient_id = row["ID"]
    if patient_id is not None:
        patient_id = patient_id[:6] + "****"
    else:
        patient_id = ""

    html = f"""
        <tr>
            <td>就醫日:{case_date}</td>
            <td>病歷號:{patient_key}</td>
            <td>姓名:{name}({gender})</td>
            <td>生日:{birthday}</td>
            <td>身份證:{patient_id}</td>
            <td>保險:{ins_type}</td>
        </tr>
    """

    return html


def get_case_row(database, case_key):
    sql = f"""
        SELECT cases.*, patient.Birthday, patient.ID, patient.Gender, patient.ChartNo FROM cases
            LEFT JOIN patient on patient.PatientKey = cases.PatientKey
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    return rows


def get_patient_key(row):
    patient_key = string_utils.xstr(row["PatientKey"])

    if string_utils.xstr(row["RegistType"]) in nhi_utils.CORRECTION_REG_TYPE:
        chart_no = string_utils.xstr(row["ChartNo"])
        if chart_no not in ["", None]:
            patient_key = chart_no

    return patient_key


def get_patient_key_header(row, patient_key_header="病號"):
    if string_utils.xstr(row["RegistType"]) in nhi_utils.CORRECTION_REG_TYPE:
        patient_key_header = "呼號"

    return patient_key_header


# 一般格式使用
def get_case_html_6(
    database,
    case_key,
    ins_type,
    medicine_set,
    birthday_mask=True,
    id_mask=True,
    tw_date=True,
    background_color=None,
):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    if birthday is not None:
        if birthday_mask:
            birthday = string_utils.xstr(
                date_utils.west_date_to_nhi_date(row["Birthday"], "-")
            )
            birthday = birthday[:7] + "**"
        elif tw_date:
            birthday = string_utils.xstr(
                date_utils.west_date_to_nhi_date(row["Birthday"], "-")
            )

    patient_id = row["ID"]
    if patient_id is not None and id_mask:
        patient_id = patient_id[:6] + "****"

    # if background_color is not None:
    #     color = f' style="background-color: {background_color}"'
    # else:
    #     color = ''

    patient_key = get_patient_key(row)
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    birthday_str = string_utils.xstr(birthday)
    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    if tw_date:
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"], "-")

    patient_key_header = get_patient_key_header(row, "病號")
    share_type = string_utils.xstr(row["Share"])[:2]

    if ins_type == "健保":
        html = f"""
            <tr>
              <td width="33%">姓名:{name}({gender})</td>
              <td width="33%">生日:{birthday_str}</td>
              <td width="34%">卡序:{card}({share_type})</td>
            </tr>
        """
    else:
        if medicine_set is None:
            medicine_set = ""
        else:
            medicine_set = f"({medicine_set - 1})"

        html = f"""
            <tr>
              <td width="33%">姓名:{name}({gender})</td>
              <td width="34%">生日:{birthday_str}</td>
              <td width="33%">保險:{ins_type} {medicine_set}</td>
            </tr>
        """

    html += f"""
        <tr>
          <td width="30%">{patient_key_header}:{patient_key}</td>
          <td width="30%">證號:{patient_id}</td>
          <td width="40%">診日:{case_date}</td>
        </tr>
    """

    return html


# 自費收據格式9使用
def get_case_html_7(database, case_key, ins_type, background_color=None):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    # age = ''
    if birthday is not None:
        birthday = birthday.strftime("%Y-**-**")
        age_year, age_month = date_utils.get_age(row["Birthday"], row["CaseDate"])
        # if age_year is None:
        #     age = ''
        # else:
        #     age = f'{age_year}歲'

    id = row["ID"]
    if id is not None:
        id = id[:6] + "****"

    # if background_color is not None:
    #     color = f' style="background-color: {background_color}"'
    # else:
    #     color = ''

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    patient_key = get_patient_key(row)
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    patient_id = string_utils.xstr(id)
    birthday_str = string_utils.xstr(birthday)
    share_type = string_utils.xstr(row["Share"])
    room = string_utils.xstr(row["Room"])
    treat_type = string_utils.xstr(row["TreatType"])
    # doctor = string_utils.xstr(row['Doctor'])
    # print_time = date_utils.now_to_str()[:16]

    html = f"""
        <tr>
          <td>姓名:{name} ({gender})</td>
          <td>身分證:{patient_id}</td>
          <td>生日:{birthday_str}</td>
        </tr>
        <tr>
          <td>病歷號:{patient_key}</td>
          <td>就診日:{case_date}</td>
          <td>保險:{ins_type}</td>
        </tr>
        <tr>
          <td>身份別:{share_type}</td>
          <td>科別:{room}診-{treat_type}</td>
        </tr>
    """

    return html


# 其他收據格式9藥袋標示使用
def get_case_html_8(
    database, case_key, ins_type, background_color=None, mask_name=False
):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    # age = ''
    if birthday is not None:
        birthday = birthday.strftime("%Y-**-**")
        age_year, age_month = date_utils.get_age(row["Birthday"], row["CaseDate"])
        # if age_year is None:
        #     age = ''
        # else:
        #     age = f'{age_year}歲'

    id = row["ID"]
    if id is not None:
        id = id[:6] + "****"

    # if background_color is not None:
    #     color = f' style="background-color: {background_color}"'
    # else:
    #     color = ''

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    # patient_key = get_patient_key(row)
    name = string_utils.xstr(row["Name"])

    if mask_name:
        name = string_utils.get_mask_name(name)

    gender = string_utils.xstr(row["Gender"])
    patient_id = string_utils.xstr(id)
    # birthday_str = string_utils.xstr(birthday)
    # share_type = string_utils.xstr(row['Share'])
    # room = string_utils.xstr(row['Room'])
    # treat_type = string_utils.xstr(row['TreatType'])
    # ins_type = string_utils.xstr(row['InsType'])
    # doctor = string_utils.xstr(row['Doctor'])
    # print_time = date_utils.now_to_str()[:16]

    html = f"""
        <tr>
          <td>姓名:{name} ({gender})</td>
          <td>身分證:{patient_id}</td>
          <td>就診日:{case_date}</td>
        </tr>
    """

    return html


# 處方箋格式(主訴)1
def get_symptom_html(database, system_settings, case_key, colspan=1):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    symptom = ""
    if string_utils.xstr(row["Symptom"]) != "":
        symptom += "主訴:" + string_utils.get_str(row["Symptom"], "utf8")
    if string_utils.xstr(row["Tongue"]) != "":
        symptom += " 舌診:" + string_utils.get_str(row["Tongue"], "utf8")
    if string_utils.xstr(row["Pulse"]) != "":
        symptom += " 脈象:" + string_utils.get_str(row["Pulse"], "utf8")
    if string_utils.xstr(row["Distincts"]) != "":
        symptom += " 辨證:" + string_utils.get_str(row["Distincts"], "utf8")
    if string_utils.xstr(row["Cure"]) != "":
        symptom += " 治則:" + string_utils.get_str(row["Cure"], "utf8")

    html_str = f'''
        <tr>
          <td colspan="{colspan}">
            {html.escape(symptom)}
          </td>
        </tr>
    '''

    if system_settings.field("列印主訴字數限制") == "Y":
        try:
            max_length = number_utils.get_integer(system_settings.field("列印主訴字數"))
        except ValueError:
            max_length = 600

        if len(html_str) > max_length:
            html_str = html_str[:max_length] + "..."

    return html_str


# 處方箋格式(診斷碼)1
def get_disease(database, case_key):
    try:
        with open("2023_ICD_MAP.json", "r", encoding="utf-8") as f:
            dict_icd_map = json.load(f)
    except Exception:
        dict_icd_map = None

    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    case_date = row["CaseDate"]
    disease_code1 = string_utils.xstr(row["DiseaseCode1"])
    disease_name1 = string_utils.xstr(row["DiseaseName1"])
    disease_code2 = string_utils.xstr(row["DiseaseCode2"])
    disease_name2 = string_utils.xstr(row["DiseaseName2"])
    disease_code3 = string_utils.xstr(row["DiseaseCode3"])
    disease_name3 = string_utils.xstr(row["DiseaseName3"])

    try:
        disease_code4 = string_utils.xstr(row["DiseaseCode4"])
        disease_name4 = string_utils.xstr(row["DiseaseName4"])
    except Exception:
        disease_code4 = ""
        disease_name4 = ""

    if case_date.year <= 2024 and dict_icd_map is not None:  # 2023年版ICD預檢 更新
        try:
            disease_code1 = dict_icd_map[
                disease_code1
            ]  # 申報月份2025年以前只能申報2014年版本ICD-10
        except Exception:
            pass

        try:
            disease_code2 = dict_icd_map[disease_code2]
        except Exception:
            pass

        try:
            disease_code3 = dict_icd_map[disease_code3]
        except Exception:
            pass

        try:
            disease_code4 = dict_icd_map[disease_code4]
        except Exception:
            pass

    disease = ""
    if string_utils.xstr(row["DiseaseCode1"]) != "":
        disease += f"主診斷: {disease_code1} {disease_name1}"
    if string_utils.xstr(row["DiseaseCode2"]) != "":
        disease += f" / 次診斷1: {disease_code2} {disease_name2}"
    if string_utils.xstr(row["DiseaseCode3"]) != "":
        disease += f" / 次診斷2: {disease_code3} {disease_name3}"
    try:
        if string_utils.xstr(row["DiseaseCode4"]) != "":
            disease += f" / 次診斷3: {disease_code4} {disease_name4}"
    except Exception:
        pass

    return disease


# 處方箋格式(診斷碼)1
def get_disease_name(database, system_settings, case_key):
    indication = system_settings.field("自訂適應症")
    if indication not in ["", None]:
        return indication

    sql = f"""
        SELECT DiseaseName1, DiseaseName2, DiseaseName3, DiseaseName4 FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    disease_name1 = string_utils.xstr(row["DiseaseName1"])
    disease_name2 = string_utils.xstr(row["DiseaseName2"])
    disease_name3 = string_utils.xstr(row["DiseaseName3"])
    disease_name4 = string_utils.xstr(row["DiseaseName4"])

    disease_name = disease_name1
    if disease_name2 != "":
        disease_name += f"/{disease_name2}"
    if disease_name3 != "":
        disease_name += f"/{disease_name3}"
    if disease_name4 != "":
        disease_name += f"/{disease_name4}"

    return disease_name


# 處方箋格式(適應症)
def get_disease2(database, system_settings, case_key):
    indication = system_settings.field("自訂適應症")
    if indication not in ["", None]:
        return indication

    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    disease_name1 = string_utils.xstr(row["DiseaseName1"])
    disease_name2 = string_utils.xstr(row["DiseaseName2"])
    disease_name3 = string_utils.xstr(row["DiseaseName3"])
    disease_name4 = string_utils.xstr(row["DiseaseName4"])

    disease_list = []
    if disease_name1 != "":
        disease_list.append(disease_name1)
    if disease_name2 != "":
        disease_list.append(disease_name2)
    if disease_name3 != "":
        disease_list.append(disease_name3)
    if disease_name4 != "":
        disease_list.append(disease_name4)

    return ", ".join(disease_list)


def get_self_prescript_html(database, system_setting, case_key):
    sql = f"""
        SELECT * FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet >= 2
        ORDER BY MedicineSet, PrescriptNo, PrescriptKey
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    prescript_line = ""
    for row in rows:
        price = row["Price"]
        dosage = row["Dosage"]
        amount = row["Amount"]

        try:
            unit_price = f"{price:.1f}"
        except Exception:
            unit_price = "0.0"

        try:
            dosage = f"{dosage:.1f}"
        except Exception:
            dosage = "0.0"

        try:
            total_amount = f"{amount:.1f}"
        except Exception:
            total_amount = "0.0"

        medicine_name = string_utils.xstr(row["MedicineName"])
        unit = string_utils.xstr(row["Unit"])
        prescript_line += f"""
            <tr>
                <td align="left" width="40%">{medicine_name}</td>
                <td align="right" width="10%">{unit_price}</td>
                <td align="right" width="10%">{dosage}{unit}</td>
                <td align="right" width="10%">{total_amount}</td>
                <td width="20%"></td>
            </tr>
        """

    prescript = f"""
        <tr>
            <th align="left">處方名稱</th>
            <th align="right">單價</th>
            <th align="right">數量</th>
            <th align="right">金額</th>
        </tr>
        {prescript_line}
    """

    return prescript


def get_instruction_condition(
    database, system_settings, case_key, medicine_set, instruction=None
):
    instruction_condition = ""
    if medicine_set is None or system_settings.field("比例法劑量") == "Y":
        return instruction_condition

    if medicine_set == 1:
        sql = f"""
            SELECT * FROM dosage
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = {medicine_set}
        """
        rows = database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            total_dosage = number_utils.get_float(row["TotalDosage"])
            if total_dosage > 0:
                return instruction_condition

        instruction_condition = """
            AND (
                prescript.Instruction IS NULL OR
                TRIM(prescript.Instruction) NOT IN("+", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10")
            )
        """
        if instruction == "健保另包":
            instruction_condition = """
                AND (
                    prescript.Instruction IS NOT NULL AND
                    TRIM(prescript.Instruction) = "+"
                )
            """

    elif medicine_set >= 2:
        instruction_condition = f'''
            OR (
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                TRIM(prescript.Instruction) = "{medicine_set - 1}"
            )
        '''

    return instruction_condition


def is_additional_prescript(database, case_key):
    sql = f"""
        SELECT PrescriptKey FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = 1 AND
            Instruction = "+"
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        return True
    else:
        return False


def is_examination(database, case_key, medicine_set):
    if case_key is None or medicine_set is None:
        return False

    sql = f"""
        SELECT PrescriptKey FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set} AND
            MedicineType = "檢驗"
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        return True
    else:
        return False


def is_ins_examination(database, case_key):
    sql = f"""
        SELECT PrescriptKey FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet > 1 AND
            MedicineType = "檢驗" AND
            InsCode IS NOT NULL AND
            LENGTH(InsCode) > 0
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        return True
    else:
        return False


def is_self_examination(database, case_key, medicine_set):
    sql = f"""
        SELECT PrescriptKey FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set} AND
            MedicineType = "檢驗" AND
            Price > 0
    """
    rows = database.select_record(sql)

    if len(rows) > 0:
        return True
    else:
        return False


def get_prescript_html(
    database,
    system_setting,
    case_key,
    medicine_set,
    print_type,
    blocks,
    max_length=None,
    instruction=None,
    print_total_dosage=None,
    print_treat_item=True,
):
    prescript = """
        <tr>
            <td>無處方</td>
        </tr>
        <hr>
    """

    if medicine_set is None:
        return prescript

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    if pres_days <= 0 and instruction == "健保另包":
        return ""

    sql = f"""
        SELECT Treatment, TreatType FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    if not rows:
        return prescript

    treatment = rows[0]["Treatment"]
    treat_type = rows[0]["TreatType"]

    treat_condition = ""
    if (
        print_type == "費用收據"
        and system_setting.field("列印穴道處置") == "N"
        and medicine_set == 1
    ) or (print_type == "過去病歷" and not print_treat_item):
        treat_condition = ' AND (prescript.MedicineType NOT IN ("穴道", "處置")) '

    medicine_set_condition = f" AND (MedicineSet = {medicine_set}) "
    medicine_type_condition = ""
    if instruction == "健保檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NOT NULL) AND
            (LENGTH(prescript.InsCode) > 0)
        """
    elif instruction == "自費檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NULL OR prescript.InsCode = "" OR LENGTH(prescript.InsCode) = 0)
        """

    instruction_condition = get_instruction_condition(
        database, system_setting, case_key, medicine_set, instruction
    )
    sql = f"""
        SELECT prescript.*, medicine.Location, medicine.MedicineAlias FROM prescript
            LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
        WHERE
            CaseKey = {case_key} AND
            (prescript.MedicineName IS NOT NULL AND LENGTH(prescript.MedicineName) > 0)
            {medicine_set_condition}
            {medicine_type_condition}
            {treat_condition}
            {instruction_condition}
        ORDER BY PrescriptNo, PrescriptKey
    """
    rows = database.select_record(sql)

    if (
        medicine_set == 1
        and treatment in nhi_utils.INS_TREAT
        and instruction not in ["健保另包", "健保檢驗", "自費檢驗"]
    ):
        if treatment in nhi_utils.ACUPUNCTURE_TREAT:
            medicine_type = "穴道"
        else:
            medicine_type = "處置"

        rows.insert(
            0,
            {
                "MedicineName": treatment,
                "MedicineAlias": treatment,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Instruction": "",
                "Unit": "次",
                "Location": "",
            },
        )

    if medicine_set == 1 and treat_type == "醫療諮詢":
        medicine_type = "單方"
        rows.insert(
            0,
            {
                "MedicineName": treat_type,
                "MedicineAlias": treat_type,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Instruction": "",
                "Unit": "次",
                "Location": "",
            },
        )

    if len(rows) <= 0:
        return ""

    if pres_days is None or pres_days <= 0:
        pres_days = 1

    if print_total_dosage is None:
        print_total_dosage = system_setting.field("處方箋列印總量")

    print_alias = system_setting.field("列印處方別名")
    if print_type == "處方箋":
        print_alias = "N"

    print_location = system_setting.field("列印藥品存放位置")
    print_location_before_medicine = system_setting.field(
        "列印藥品存放位置在處方名稱前面"
    )

    if print_total_dosage == "Y":
        block_width = {
            3: {
                "medicine_name_width": 19,
                "dosage_width": 6,
                "total_dosage_width": 5,
                "separator_width": 1,
            },
            2: {
                "medicine_name_width": 30,
                "dosage_width": 10,
                "total_dosage_width": 9,
                "separator_width": 1,
            },
            1: {
                "medicine_name_width": 50,
                "dosage_width": 30,
                "total_dosage_width": 20,
                "separator_width": 0,
            },
        }
    else:
        block_width = {
            3: {
                "medicine_name_width": 24,
                "dosage_width": 8,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
            2: {
                "medicine_name_width": 39,
                "dosage_width": 10,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
            1: {
                "medicine_name_width": 50,
                "dosage_width": 30,
                "total_dosage_width": 20,
                "separator_width": 0,
            },
        }

    if system_setting.field("處方列印方向") == "垂直列印":
        rows = set_vertical_direction(rows)

    prescript = ""
    row_count = int((len(rows) - 1) / blocks) + 1
    for row_no in range(1, row_count + 1):
        separator = ""
        prescript_line = ""
        for i in range(blocks):
            prescript_block = get_medicine_detail(
                medicine_set,
                rows,
                (row_no - 1) * blocks + i,
                pres_days,
                packages,
                print_alias,
            )

            medicine_name = string_utils.xstr(prescript_block[0])

            if instruction == "健保檢驗":
                ins_code = string_utils.xstr(prescript_block[5])
                medicine_name = f"{medicine_name} ({ins_code})"

            location = string_utils.xstr(prescript_block[1])
            if print_location != "Y":
                location = ""

            if print_location_before_medicine == "Y":
                medicine_name = location + medicine_name
            else:
                medicine_name += location

            dosage = string_utils.xstr(prescript_block[2])
            total_dosage = string_utils.xstr(prescript_block[4])
            unit = string_utils.xstr(prescript_block[3])
            medicine_name_width = block_width[blocks]["medicine_name_width"]
            dosage_width = block_width[blocks]["dosage_width"]
            total_dosage_width = block_width[blocks]["total_dosage_width"]
            separator_width = block_width[blocks]["separator_width"]

            if medicine_name in ["優待", "健保檢驗", "自費檢驗"]:
                total_dosage = ""

            if instruction == "無劑量":
                dosage = ""
                unit = ""
                total_dosage = ""

            if print_total_dosage != "Y":
                prescript_line += f'''
                    <td align="left" width="{medicine_name_width}%">{medicine_name}</td>
                    <td align="right" width="{dosage_width}%">{dosage}{unit}</td>
                    <td width="{separator_width}%">{separator}</td>
                '''
            else:
                prescript_line += f'''
                    <td align="left" width="{medicine_name_width}%">{medicine_name}</td>
                    <td align="right" width="{dosage_width}%">{dosage}{unit}</td>
                    <td align="right" width="{total_dosage_width}%">{total_dosage}</td>
                '''
                if separator_width > 0:
                    prescript_line += f'''
                    <td width="{separator_width}%">{separator}</td>
                '''

        prescript += f"""
            <tr>
              {prescript_line}
            </tr>
        """

    return prescript


def get_prescript_html2(
    database,
    system_setting,
    case_key,
    medicine_set,
    print_type,
    blocks,
    instruction=None,
    max_line=6,
    wide_dosage=False,
    is_print_dosage=True,
):
    clinic_name = system_setting.field("院所名稱")
    special_clinic = [
        "鵲杏中醫診所",
        "青埔悅兒親子中醫診所",
        "悅兒親子中醫診所",
        "大安悅兒親子中醫診所",
    ]
    print_location = system_setting.field("列印藥品存放位置")
    print_location_before_medicine = system_setting.field(
        "列印藥品存放位置在處方名稱前面"
    )

    print_dosage = system_setting.field("收費收據列印劑量")
    if print_dosage in ["", None]:
        print_dosage = "總量"

    self_daily_dosage = system_setting.field("自費收據列印日量")
    print_alias = system_setting.field("列印處方別名")

    max_length = None
    if system_setting.field("列印處方字數限制") == "Y":
        try:
            max_length = number_utils.get_integer(system_setting.field("列印處方字數"))
        except ValueError:
            pass

    try:
        pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    except Exception:
        pres_days = None

    try:
        packages = case_utils.get_packages(database, case_key, medicine_set)
    except Exception:
        packages = None

    sql = f"""
        SELECT Treatment, TreatType FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    treatment = rows[0]["Treatment"]
    treat_type = rows[0]["TreatType"]

    treat_condition = ""
    if (
        print_type == "費用收據"
        and system_setting.field("列印穴道處置") == "N"
        and medicine_set == 1
    ):  # 健保才過濾
        treat_condition = ' AND (prescript.MedicineType NOT IN ("穴道", "處置")) '

    if medicine_set is None:
        medicine_set_condition = "AND prescript.Amount > 0"
    else:
        medicine_set_condition = f"AND MedicineSet = {medicine_set}"

    medicine_type_condition = ""
    if instruction == "健保檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NOT NULL) AND
            (LENGTH(prescript.InsCode) > 0)
        """
    elif instruction == "自費檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NULL OR prescript.InsCode = "" OR LENGTH(prescript.InsCode) = 0)
        """

    instruction_condition = get_instruction_condition(
        database, system_setting, case_key, medicine_set, instruction
    )

    order_script = "ORDER BY PrescriptNo, PrescriptKey"
    if system_setting.field("列印處方依照存放位置排序") == "Y":
        order_script = """
            ORDER BY
                SUBSTRING(medicine.Location, 1, 1), 
                LENGTH(SUBSTRING(medicine.Location, 2)),
                SUBSTRING(medicine.Location, 2)
        """

    sql = f"""
        SELECT prescript.*, medicine.Location, medicine.MedicineAlias FROM prescript
            LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
        WHERE
            CaseKey = {case_key} AND
            (prescript.MedicineName IS NOT NULL AND LENGTH(prescript.MedicineName) > 0)
            {medicine_set_condition}
            {medicine_type_condition}
            {treat_condition}
            {instruction_condition}
            {order_script}
    """
    rows = database.select_record(sql)

    if pres_days <= 0 or system_setting.field("列印針傷處置名稱") == "Y":
        if (
            medicine_set == 1
            and treatment not in ["", None]
            and instruction not in ["健保另包", "健保檢驗", "自費檢驗"]
        ):
            if treatment in nhi_utils.ACUPUNCTURE_TREAT:
                medicine_type = "穴道"
            else:
                medicine_type = "處置"

            rows.insert(
                0,
                {
                    "MedicineName": treatment,
                    "MedicineAlias": treatment,
                    "MedicineType": medicine_type,
                    "InsCode": "",
                    "Dosage": 1,
                    "Unit": "次",
                    "Location": "",
                },
            )

    if medicine_set == 1 and treat_type == "醫療諮詢":
        medicine_type = "單方"
        rows.insert(
            0,
            {
                "MedicineName": treat_type,
                "MedicineAlias": treat_type,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Unit": "次",
                "Location": "",
            },
        )

    if len(rows) <= 0:
        return "<br>" * blocks

    if pres_days is None or pres_days <= 0:
        pres_days = 1

    if medicine_set is None:  # 列印印花稅收據用
        medicine_set = 2

    if print_dosage in ["總量", "日量"] or (
        medicine_set >= 2 and self_daily_dosage in ["Y"]
    ):
        block_width = {
            3: {
                "medicine_name_width": 34,
                "dosage_width": 15,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
            2: {
                "medicine_name_width": 34,
                "dosage_width": 15,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
            1: {
                "medicine_name_width": 70,
                "dosage_width": 15,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
        }
    else:
        block_width = {
            3: {
                "medicine_name_width": 29,
                "dosage_width": 11,
                "total_dosage_width": 10,
                "separator_width": 1,
            },
            2: {
                "medicine_name_width": 29,
                "dosage_width": 11,
                "total_dosage_width": 10,
                "separator_width": 1,
            },
            1: {
                "medicine_name_width": 70,
                "dosage_width": 15,
                "total_dosage_width": 15,
                "separator_width": 1,
            },
        }

    if wide_dosage:
        block_width = {
            3: {
                "medicine_name_width": 29,
                "dosage_width": 11,
                "total_dosage_width": 10,
                "separator_width": 1,
            },
            2: {
                "medicine_name_width": 29,
                "dosage_width": 11,
                "total_dosage_width": 10,
                "separator_width": 1,
            },
            1: {
                "medicine_name_width": 70,
                "dosage_width": 15,
                "total_dosage_width": 15,
                "separator_width": 1,
            },
        }

    if system_setting.field("處方列印方向") == "垂直列印":
        rows = set_vertical_direction(rows)

    prescript = ""
    row_count = int((len(rows) - 1) / blocks) + 1
    for row_no in range(1, row_count + 1):
        prescript_line = ""
        for i in range(blocks):
            prescript_block = get_medicine_detail(
                medicine_set,
                rows,
                (row_no - 1) * blocks + i,
                pres_days,
                packages,
                print_alias,
            )

            medicine_name = string_utils.xstr(prescript_block[0])
            if print_location == "Y":
                location = string_utils.xstr(prescript_block[1])

                if print_location_before_medicine == "Y":
                    medicine_name = location + medicine_name
                else:
                    medicine_name += location

            medicine_name_width = block_width[blocks]["medicine_name_width"]
            dosage_width = block_width[blocks]["dosage_width"]
            total_dosage_width = block_width[blocks]["total_dosage_width"]
            separator_width = block_width[blocks]["separator_width"]
            dosage = string_utils.xstr(prescript_block[2])
            total_dosage = string_utils.xstr(prescript_block[4])

            unit = string_utils.xstr(prescript_block[3])

            try:
                # dosage_mode = string_utils.xstr(rows[row_no]["DosageMode"])
                dosage_mode = string_utils.xstr(prescript_block[8])
            except Exception:
                dosage_mode = None

            if medicine_set >= 2 and dosage_mode == "次劑量":  # 悅兒親子 2024-08-23
                is_special_clinic_weight_loss = (
                    clinic_name in special_clinic and "減重" in medicine_name
                )
                is_tablet_unit = clinic_name not in special_clinic and unit in [
                    "顆",
                    "錠",
                ]
                if is_special_clinic_weight_loss or is_tablet_unit:
                    total_dosage = number_utils.get_float(
                        dosage
                    ) * number_utils.get_integer(pres_days)

            if total_dosage == "0.0":
                dosage = ""
                total_dosage = ""
                unit = ""

            if not is_print_dosage:
                dosage = ""
                total_dosage = ""
                unit = ""

            if max_length is not None:
                medicine_name = medicine_name[:max_length]

            prescript_instruction = string_utils.xstr(prescript_block[6])
            if prescript_instruction not in ["", None]:
                medicine_name += f"-{prescript_instruction}"

            if medicine_set is None:  # 列印印花稅收據用
                medicine_set = 2

            if instruction in ["健保檢驗", "自費檢驗"]:
                prescript_line += f'''
                    <td align="left" width="{medicine_name_width}%">{medicine_name}</td>
                    <td align="right" width="{dosage_width}%">{dosage}{unit}</td>
                '''
            elif print_dosage in ["總量", "日量"] or (
                medicine_set >= 2 and self_daily_dosage == "Y"
            ):
                dosage_str = total_dosage  # 預設列印總量
                if print_dosage in ["日量"] or (
                    medicine_set >= 2 and self_daily_dosage == "Y"
                ):
                    dosage_str = dosage

                prescript_line += f'''
                    <td align="left" width="{medicine_name_width}%">{medicine_name}</td>
                    <td align="right" width="{dosage_width}%">{dosage_str}{unit}</td>
                '''
            else:
                prescript_line += f'''
                    <td align="left" width="{medicine_name_width}%">{medicine_name}</td>
                    <td align="right" width="{dosage_width}%">{dosage}{unit}</td>
                    <td align="right" width="{total_dosage_width}%">{total_dosage}</td>
                '''

            if blocks >= 2:
                prescript_line += f'''
                    <td width="{separator_width}%"></td>
                '''

        prescript += f"""
            <tr>
              {prescript_line}
            </tr>
        """

    lines = int(len(rows) / blocks)
    if blocks >= 2 and len(rows) % blocks > 0:
        lines += 1

    br_lines = max_line - lines
    if br_lines > 0:
        prescript += "<br>" * br_lines

    return prescript


def set_vertical_direction(rows):
    row_count = len(rows)
    if row_count <= 2:
        return rows

    block_height_count = number_utils.get_integer(row_count / 2)
    if row_count % 2 == 1:
        block_height_count += 1

    new_rows = []
    for row_no in range(block_height_count):
        new_rows.append(rows[row_no])

        if row_no + block_height_count <= row_count - 1:
            new_rows.append(rows[row_no + block_height_count])

    return new_rows


# def split_rows_into_blocks(rows, max_length=10):
#     half = max_length // 2  # ← 整數除法

#     block1_rows = rows[:half]
#     block2_rows = rows[half:max_length]

#     empty_row = {"MedicineName": "", "Dosage": 0.0, "Unit": ""}

#     while len(block1_rows) < half:
#         block1_rows.append(empty_row.copy())

#     while len(block2_rows) < half:
#         block2_rows.append(empty_row.copy())

#     return block1_rows, block2_rows


def split_rows_into_blocks(rows, num_blocks=2, block_size=10):
    blocks = []
    total_needed = num_blocks * block_size
    padded_rows = rows[:total_needed]  # 最多只取需要的筆數

    # 補足不夠的部分
    empty_row = {
        "MedicineName": "",
        "MedicineType": "",
        "Dosage": 0.0,
        "DosageMode": "",
        "Unit": "",
        "Location": "",
    }

    while len(padded_rows) < total_needed:
        padded_rows.append(empty_row.copy())

    # 分割成 N 個區塊
    for i in range(num_blocks):
        start = i * block_size
        end = start + block_size
        blocks.append(padded_rows[start:end])

    return blocks


# 明醫
def get_prescript_block3_html(
    database,
    system_setting,
    case_key,
    medicine_set,
    print_type,
    print_alias,
    blocks=3,
    instruction=None,
):
    if medicine_set is None:
        prescript = """
            <tr>
              <td>無處方</td>
            </tr>
            <hr>
        """
        return prescript

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)

    sql = f"""
        SELECT Treatment, TreatType FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    treatment = rows[0]["Treatment"]
    treat_type = rows[0]["TreatType"]

    treat_condition = ""
    if print_type == "費用收據" and system_setting.field("列印穴道處置") == "N":
        treat_condition = ' AND (prescript.MedicineType NOT IN ("穴道", "處置")) '

    instruction_condition = get_instruction_condition(
        database, system_setting, case_key, medicine_set, instruction
    )
    sql = f"""
        SELECT prescript.*, medicine.Location, medicine.MedicineAlias FROM prescript
            LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
        WHERE
            CaseKey = {case_key} AND
            MedicineSet = {medicine_set} AND
            (prescript.MedicineName IS NOT NULL AND LENGTH(prescript.MedicineName) > 0)
            {treat_condition}
            {instruction_condition}
        ORDER BY PrescriptNo, PrescriptKey
    """
    rows = database.select_record(sql)

    if (
        medicine_set == 1
        and treatment in nhi_utils.INS_TREAT
        and instruction != "健保另包"
    ):
        if treatment in nhi_utils.ACUPUNCTURE_TREAT:
            medicine_type = "穴道"
        else:
            medicine_type = "處置"

        rows.insert(
            0,
            {
                "MedicineName": treatment,
                "MedicineAlias": treatment,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Unit": "次",
                "Location": "",
            },
        )

    if medicine_set == 1 and treat_type == "醫療諮詢":
        medicine_type = "單方"
        rows.insert(
            0,
            {
                "MedicineName": treat_type,
                "MedicineAlias": treat_type,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Unit": "次",
                "Location": "",
            },
        )

    if len(rows) <= 0:
        return ""

    if pres_days is None or pres_days <= 0:
        pres_days = 1

    block_width = {
        3: {
            "medicine_name_width": 20,
            "dosage_width": 7,
            "total_dosage_width": 5,
            "separator_width": 1,
        },
        2: {
            "medicine_name_width": 30,
            "dosage_width": 10,
            "total_dosage_width": 8,
            "separator_width": 1,
        },
    }

    print_total_dosage = system_setting.field("列印藥品總量")
    prescript = ""
    row_count = int((len(rows) - 1) / blocks) + 1
    for row_no in range(1, row_count + 1):
        separator = ""
        prescript_line = ""
        for i in range(blocks):
            prescript_block = get_medicine_detail(
                medicine_set,
                rows,
                (row_no - 1) * blocks + i,
                pres_days,
                packages,
                print_alias,
            )

            location = string_utils.xstr(prescript_block[1])
            if system_setting.field("列印藥品存放位置") != "Y":
                location = ""

            total_dosage = string_utils.xstr(prescript_block[4])
            if print_total_dosage != "Y" or not print_total_dosage:
                total_dosage = ""

            medicine_name = string_utils.xstr(prescript_block[0])[:10]
            dosage = string_utils.xstr(prescript_block[2])
            unit = string_utils.xstr(prescript_block[3])
            medicine_name_width = block_width[blocks]["medicine_name_width"]
            dosage_width = block_width[blocks]["dosage_width"]
            total_dosage_width = block_width[blocks]["total_dosage_width"]
            separator_width = block_width[blocks]["separator_width"]

            prescript_line += f'''
                <td align="left" width="{medicine_name_width}%"><b>{medicine_name} {location}</b></td>
                <td align="right" width="{dosage_width}%"><b>{dosage}{unit}</b></td>
                <td align="right" width="{total_dosage_width}%">{total_dosage}</td>
                <td width="{separator_width}%">{separator}</td>
            '''

        prescript += f"""
            <tr>
              {prescript_line}
            </tr>
        """

    return prescript


# 健保費用
def get_ins_fees_html(database, case_key):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    regist_fee = string_utils.xstr(number_utils.get_integer(row["RegistFee"]))
    diag_share_fee = string_utils.xstr(number_utils.get_integer(row["SDiagShareFee"]))
    drug_share_fee = string_utils.xstr(number_utils.get_integer(row["SDrugShareFee"]))
    # total_share_fee = string_utils.xstr(
    #     number_utils.get_integer(row['SDiagShareFee']) +
    #     number_utils.get_integer(row['SDrugShareFee'])
    # )
    deposit_fee = string_utils.xstr(number_utils.get_integer(row["DepositFee"]))
    total_fee = string_utils.xstr(
        number_utils.get_integer(row["RegistFee"])
        + number_utils.get_integer(row["SDiagShareFee"])
        + number_utils.get_integer(row["SDrugShareFee"])
        + number_utils.get_integer(row["DepositFee"])
    )
    diag_fee = string_utils.xstr(number_utils.get_integer(row["DiagFee"]))
    drug_fee = string_utils.xstr(number_utils.get_integer(row["InterDrugFee"]))
    pharmacy_fee = string_utils.xstr(number_utils.get_integer(row["PharmacyFee"]))
    treat_fee = string_utils.xstr(
        number_utils.get_integer(row["AcupunctureFee"])
        + number_utils.get_integer(row["MassageFee"])
        + number_utils.get_integer(row["DislocateFee"])
    )
    # ins_total_fee = string_utils.xstr(number_utils.get_integer(row['InsTotalFee']))
    ins_apply_fee = string_utils.xstr(number_utils.get_integer(row["InsApplyFee"]))
    html = f"""
        <tr>
          <td>掛號費:</td><td align="right">{regist_fee}</td>
          <td width="1%"></td>
          <td>門診負擔:</td><td align="right">{diag_share_fee}</td>
          <td width="1%"></td>
          <td>藥品負擔:</td><td align="right">{drug_share_fee}</td>
          <td width="1%"></td>
          <td>欠卡費:</td><td align="right">{deposit_fee}</td>
          <td width="1%"></td>
          <td>健保實收:</td><td align="right">{total_fee}</td>
        </tr>
        <tr>
          <td>診察費:</td><td align="right">{diag_fee}</td>
          <td width="1%"></td>
          <td>藥費:</td><td align="right">{drug_fee}</td>
          <td width="1%"></td>
          <td>調劑費:</td><td align="right">{pharmacy_fee}</td>
          <td width="1%"></td>
          <td>處置費:</td><td align="right">{treat_fee}</td>
          <td width="1%"></td>
          <td>健保申請:</td><td align="right">{ins_apply_fee}</td>
        </tr>
    """

    return html


# 自費費用
def get_self_fees_html(database, case_key):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    regist_fee = number_utils.get_integer(row["RegistFee"])
    ins_type = string_utils.xstr(row["InsType"])
    if ins_type == "健保":
        regist_fee = 0

    diag_fee = number_utils.get_integer(row["SDiagFee"])
    drug_fee = number_utils.get_integer(row["SDrugFee"])
    herb_fee = number_utils.get_integer(row["SHerbFee"])
    expensive_fee = number_utils.get_integer(row["SExpensiveFee"])
    material_fee = number_utils.get_integer(row["SMaterialFee"])

    acupuncture_fee = number_utils.get_integer(row["SAcupunctureFee"])
    massage_fee = number_utils.get_integer(row["SMassageFee"])
    self_total_fee = number_utils.get_integer(row["SelfTotalFee"]) + regist_fee
    discount_fee = number_utils.get_integer(row["DiscountFee"])
    total_fee = number_utils.get_integer(row["TotalFee"]) + regist_fee
    receipt_fee = number_utils.get_integer(row["ReceiptFee"]) + regist_fee

    html = f"""
        <tr>
          <td>掛號費:</td><td align="right">{regist_fee}</td>
          <td width="5%"></td>
          <td>診察費:</td><td align="right">{diag_fee}</td>
          <td width="5%"></td>
          <td>藥費:</td><td align="right">{drug_fee}</td>
          <td width="5%"></td>
          <td>水藥費:</td><td align="right">{herb_fee}</td>
        </tr>
        <tr>
          <td>針灸費:</td><td align="right">{acupuncture_fee}</td>
          <td width="5%"></td>
          <td>傷科費:</td><td align="right">{massage_fee}</td>
          <td width="5%"></td>
          <td>材料費:</td><td align="right">{material_fee}</td>
          <td width="5%"></td>
          <td>高貴藥:</td><td align="right">{expensive_fee}</td>
        </tr>
        <tr>
          <td>合計金額:</td><td align="right">{self_total_fee}</td>
          <td width="5%"></td>
          <td>折扣金額:</td><td align="right">{discount_fee}</td>
          <td width="5%"></td>
          <td>應收金額:</td><td align="right">{total_fee}</td>
          <td width="5%"></td>
          <td>實收金額:</td><td align="right">{receipt_fee}</td>
        </tr>
    """

    return html


# 健保費用
def get_ins_fees_html_2(database, case_key):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    regist_fee = string_utils.xstr(number_utils.get_integer(row["RegistFee"]))
    diag_share_fee = string_utils.xstr(number_utils.get_integer(row["SDiagShareFee"]))
    drug_share_fee = string_utils.xstr(number_utils.get_integer(row["SDrugShareFee"]))
    # total_share_fee = string_utils.xstr(
    #     number_utils.get_integer(row['SDiagShareFee']) +
    #     number_utils.get_integer(row['SDrugShareFee'])
    # )
    deposit_fee = string_utils.xstr(number_utils.get_integer(row["DepositFee"]))
    total_fee = string_utils.xstr(
        number_utils.get_integer(row["RegistFee"])
        + number_utils.get_integer(row["SDiagShareFee"])
        + number_utils.get_integer(row["SDrugShareFee"])
        + number_utils.get_integer(row["DepositFee"])
    )
    diag_fee = string_utils.xstr(number_utils.get_integer(row["DiagFee"]))
    drug_fee = string_utils.xstr(number_utils.get_integer(row["InterDrugFee"]))
    pharmacy_fee = string_utils.xstr(number_utils.get_integer(row["PharmacyFee"]))
    treat_fee = string_utils.xstr(
        number_utils.get_integer(row["AcupunctureFee"])
        + number_utils.get_integer(row["MassageFee"])
        + number_utils.get_integer(row["DislocateFee"])
    )
    # ins_total_fee = string_utils.xstr(number_utils.get_integer(row['InsTotalFee']))
    ins_total_fee = string_utils.xstr(number_utils.get_integer(row["InsTotalFee"]))
    ins_apply_fee = string_utils.xstr(number_utils.get_integer(row["InsApplyFee"]))
    html = f"""
        <tr>
          <td>診察費:</td><td align=right>{diag_fee}</td>
          <td width="3%"></td>
          <td>內服藥費:</td><td align=right>{drug_fee}</td>
          <td width="3%"></td>
          <td>調劑費用:</td><td align=right>{pharmacy_fee}</td>
        </tr>
        <tr>
          <td>處置費:</td><td align=right>{treat_fee}</td>
          <td width="3%"></td>
          <td>健保合計:</td><td align=right>{ins_total_fee}</td>
          <td width="3%"></td>
          <td>健保申請:</td><td align=right>{ins_apply_fee}</td>
        </tr>
        <tr>
          <td>掛號費:</td><td align=right>{regist_fee}</td>
          <td width="3%"></td>
          <td>門診負擔:</td><td align=right>{diag_share_fee}</td>
          <td width="3%"></td>
          <td>藥品負擔:</td><td align=right>{drug_share_fee}</td>
        </tr>
        <tr>
          <td>欠卡費:</td><td align=right>{deposit_fee}</td>
          <td width="3%"></td>
          <td>健保實收:</td><td align=right>{total_fee}</td>
          <td width="3%"></td>
          <td></td><td></td>
        </tr>
    """

    return html


# 自費費用
def get_self_fees_html_2(database, case_key, width=15):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    regist_fee = number_utils.get_integer(row["RegistFee"])
    ins_type = string_utils.xstr(row["InsType"])
    if ins_type == "健保":
        regist_fee = 0

    diag_fee = number_utils.get_integer(row["SDiagFee"])
    drug_fee = number_utils.get_integer(row["SDrugFee"])
    herb_fee = number_utils.get_integer(row["SHerbFee"])
    expensive_fee = number_utils.get_integer(row["SExpensiveFee"])
    material_fee = number_utils.get_integer(row["SMaterialFee"])

    acupuncture_fee = number_utils.get_integer(row["SAcupunctureFee"])
    massage_fee = number_utils.get_integer(row["SMassageFee"])
    self_total_fee = number_utils.get_integer(row["SelfTotalFee"]) + regist_fee
    discount_fee = number_utils.get_integer(row["DiscountFee"])
    if discount_fee < 0:
        if drug_fee > 0:
            drug_fee += -discount_fee
        elif herb_fee > 0:
            herb_fee += -discount_fee
        elif expensive_fee > 0:
            expensive_fee += -discount_fee
        elif material_fee > 0:
            material_fee += -discount_fee
        elif acupuncture_fee > 0:
            acupuncture_fee += -discount_fee
        elif massage_fee > 0:
            massage_fee += -discount_fee

        self_total_fee += -discount_fee
        discount_fee = 0

    total_fee = number_utils.get_integer(row["TotalFee"]) + regist_fee
    receipt_fee = number_utils.get_integer(row["ReceiptFee"]) + regist_fee

    html = f'''
        <tr>
          <td>掛號費:</td><td align=right>{regist_fee}</td>
          <td width="{width}%"></td>
          <td>診察費:</td><td align=right>{diag_fee}</td>
          <td width="{width}%"></td>
          <td>藥費:</td><td align=right>{drug_fee}</td>
        </tr>
        <tr>
          <td>水藥費:</td><td align=right>{herb_fee}</td>
          <td width="{width}%"></td>
          <td>高貴藥:</td><td align=right>{expensive_fee}</td>
          <td width="{width}%"></td>
          <td>治療費:</td><td align=right>{acupuncture_fee}</td>
        </tr>
        <tr>
          <td>處置費:</td><td align=right>{massage_fee}</td>
          <td width="{width}%"></td>
          <td>材料費:</td><td align=right>{material_fee}</td>
          <td width="{width}%"></td>
          <td>合計:</td><td align=right>{self_total_fee}</td>
        </tr>
        <tr>
          <td>折扣:</td><td align=right>{discount_fee}</td>
          <td width="{width}%"></td>
          <td>應收:</td><td align=right>{total_fee}</td>
          <td width="{width}%"></td>
          <td>實收:</td><td align=right>{receipt_fee}</td>
        </tr>
    '''

    return html


# 自費費用2
def get_self_fees_html2(database, case_key):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """

    rows = database.select_record(sql)
    if len(rows) <= 0:
        return ""

    row = rows[0]
    # regist_fee = number_utils.get_integer(row['RegistFee'])
    # ins_type = string_utils.xstr(row['InsType'])
    # if ins_type == '健保':
    #     regist_fee = 0

    # diag_fee = string_utils.xstr(number_utils.get_integer(row['SDiagFee']))
    # drug_fee = string_utils.xstr(number_utils.get_integer(row['SDrugFee']))
    # herb_fee = string_utils.xstr(number_utils.get_integer(row['SHerbFee']))
    # expensive_fee = string_utils.xstr(number_utils.get_integer(row['SExpensiveFee']))
    # material_fee = string_utils.xstr(number_utils.get_integer(row['SMaterialFee']))

    # acupuncture_fee = string_utils.xstr(number_utils.get_integer(row['SAcupunctureFee']))
    # massage_fee = string_utils.xstr(number_utils.get_integer(row['SMassageFee']))
    self_total_fee = string_utils.xstr(number_utils.get_integer(row["SelfTotalFee"]))
    discount_fee = string_utils.xstr(number_utils.get_integer(row["DiscountFee"]))
    total_fee = string_utils.xstr(number_utils.get_integer(row["TotalFee"]))
    receipt_fee = string_utils.xstr(number_utils.get_integer(row["ReceiptFee"]))

    html = f"""
        <tr>
          <td>自費金額:{self_total_fee}</td>
          <td>折扣金額:{discount_fee}</td>
          <td>應收金額:{total_fee}</td>
          <td>實收金額:{receipt_fee}</td>
        </tr>
    """
    return html


# 自費費用
def get_fees_html(database, case_key):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    ins_receipt_fee = (
        number_utils.get_integer(row["RegistFee"])
        + number_utils.get_integer(row["SDiagShareFee"])
        + number_utils.get_integer(row["SDrugShareFee"])
        + number_utils.get_integer(row["DepositFee"])
    )

    regist_fee = string_utils.xstr(number_utils.get_integer(row["RegistFee"]))
    diag_share_fee = string_utils.xstr(number_utils.get_integer(row["SDiagShareFee"]))
    drug_share_fee = string_utils.xstr(number_utils.get_integer(row["SDrugShareFee"]))
    # total_share_fee = string_utils.xstr(
    #     number_utils.get_integer(row['SDiagShareFee']) +
    #     number_utils.get_integer(row['SDrugShareFee'])
    # )
    deposit_fee = string_utils.xstr(number_utils.get_integer(row["DepositFee"]))
    diag_fee = string_utils.xstr(number_utils.get_integer(row["DiagFee"]))
    drug_fee = string_utils.xstr(number_utils.get_integer(row["InterDrugFee"]))
    pharmacy_fee = string_utils.xstr(number_utils.get_integer(row["PharmacyFee"]))
    treat_fee = string_utils.xstr(
        number_utils.get_integer(row["AcupunctureFee"])
        + number_utils.get_integer(row["MassageFee"])
        + number_utils.get_integer(row["DislocateFee"])
    )
    # ins_total_fee = string_utils.xstr(number_utils.get_integer(row['InsTotalFee']))
    ins_apply_fee = string_utils.xstr(number_utils.get_integer(row["InsApplyFee"]))
    s_diag_fee = string_utils.xstr(number_utils.get_integer(row["SDiagFee"]))
    s_drug_fee = string_utils.xstr(number_utils.get_integer(row["SDrugFee"]))
    herb_fee = string_utils.xstr(number_utils.get_integer(row["SHerbFee"]))
    expensive_fee = string_utils.xstr(number_utils.get_integer(row["SExpensiveFee"]))
    material_fee = string_utils.xstr(number_utils.get_integer(row["SMaterialFee"]))

    acupuncture_fee = string_utils.xstr(
        number_utils.get_integer(row["SAcupunctureFee"])
    )
    massage_fee = string_utils.xstr(number_utils.get_integer(row["SMassageFee"]))
    self_total_fee = string_utils.xstr(number_utils.get_integer(row["SelfTotalFee"]))
    discount_fee = string_utils.xstr(number_utils.get_integer(row["DiscountFee"]))
    total_fee = string_utils.xstr(number_utils.get_integer(row["TotalFee"]))
    receipt_fee = string_utils.xstr(number_utils.get_integer(row["ReceiptFee"]))
    total_receipt_fee = string_utils.xstr(
        ins_receipt_fee + number_utils.get_integer(row["ReceiptFee"])
    )

    html = f"""
        <tr>
          <td>掛號費:{regist_fee}</td>
          <td>門診負擔:{diag_share_fee}</td>
          <td>藥品負擔:{drug_share_fee}</td>
          <td>欠卡費:{deposit_fee}</td>
          <td>健保實收:{ins_receipt_fee}</td>
        </tr>
        <tr>
          <td>診察費:{diag_fee}</td>
          <td>藥費:{drug_fee}</td>
          <td>調劑費:{pharmacy_fee}</td>
          <td>處置費:{treat_fee}</td>
          <td>健保申請:{ins_apply_fee}</td>
        </tr>
        <tr>
          <td>自費診察費:{s_diag_fee}</td>
          <td>一般藥費:{s_drug_fee}</td>
          <td>水煎藥費:{herb_fee}</td>
          <td>高貴藥費:{expensive_fee}</td>
          <td>自費材料費:{material_fee}</td>
        </tr>
        <tr>
          <td>自費針灸費:{acupuncture_fee}</td>
          <td>傷科處置費:{massage_fee}</td>
        </tr>
        <tr>
          <td>合計金額:{self_total_fee}</td>
          <td>折扣金額:{discount_fee}</td>
          <td>自費應收:{total_fee}</td>
          <td>自費實收:{receipt_fee}</td>
          <td>合計實收:{total_receipt_fee}</td>
        </tr>
    """

    return html


# 健保局費用格式
def get_fees_html2(database, case_key, ins_type="健保"):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    registrar = string_utils.xstr(row["Register"])
    # ins_receipt_fee = (number_utils.get_integer(row['RegistFee']) +
    #                    number_utils.get_integer(row['SDiagShareFee']) +
    #                    number_utils.get_integer(row['SDrugShareFee']) +
    #                    number_utils.get_integer(row['DepositFee']))

    regist_fee = number_utils.get_integer(row["RegistFee"])
    diag_share_fee = number_utils.get_integer(row["SDiagShareFee"])
    drug_share_fee = number_utils.get_integer(row["SDrugShareFee"])
    total_share_fee = diag_share_fee + drug_share_fee

    diag_fee = number_utils.get_integer(row["DiagFee"])
    drug_fee = number_utils.get_integer(row["InterDrugFee"])
    pharmacy_fee = number_utils.get_integer(row["PharmacyFee"])
    exam_fee = number_utils.get_integer(row["ExamFee"])
    treat_fee = (
        number_utils.get_integer(row["AcupunctureFee"])
        + number_utils.get_integer(row["MassageFee"])
        + number_utils.get_integer(row["DislocateFee"])
    )
    ins_total_fee = number_utils.get_integer(row["InsTotalFee"])
    s_drug_fee = number_utils.get_integer(row["SDrugFee"])
    herb_fee = number_utils.get_integer(row["SHerbFee"])
    expensive_fee = number_utils.get_integer(row["SExpensiveFee"])
    s_exam_fee = number_utils.get_integer(row["SExamFee"])
    material_fee = number_utils.get_integer(row["SMaterialFee"])

    s_acupuncture_fee = number_utils.get_integer(row["SAcupunctureFee"])
    s_massage_fee = number_utils.get_integer(row["SMassageFee"])
    s_treat_fee = s_acupuncture_fee + s_massage_fee
    discount_fee = number_utils.get_integer(row["DiscountFee"])
    total_fee = number_utils.get_integer(row["TotalFee"])

    if ins_type == "自費":
        regist_fee = 0
        diag_share_fee = 0
        drug_share_fee = 0
        total_share_fee = diag_share_fee + drug_share_fee

        diag_fee = 0
        drug_fee = 0
        pharmacy_fee = 0
        exam_fee = 0
        treat_fee = 0
        ins_total_fee = 0

    self_drug_fee = s_drug_fee + herb_fee + expensive_fee - discount_fee
    self_treat_fee = s_exam_fee + s_treat_fee

    total_cash = regist_fee + total_share_fee + total_fee

    html = f"""
        <tr>
          <td style="padding-left: 5px">診察費</td>
          <td align=right style="padding-right: 40%">{diag_fee}</td>
          <td style="padding-left: 5px">掛號費</td>
          <td align=right style="padding-right: 40%">{regist_fee}</td>
        </tr>
        <tr>
          <td style="padding-left: 5px">藥費</td>
          <td align=right style="padding-right: 40%">{drug_fee}</td>
          <td style="padding-left: 5px">基本部分負擔</td>
          <td align=right style="padding-right: 40%">{diag_share_fee}</td>
        </tr>
        <tr>
          <td style="padding-left: 5px">藥事服務費</td>
          <td align=right style="padding-right: 40%">{pharmacy_fee}</td>
          <td style="padding-left: 5px">藥品部分負擔</td>
          <td align=right style="padding-right: 40%">{drug_share_fee}</td>
        </tr>
        <tr>
          <td style="padding-left: 5px">檢驗費</td>
          <td align=right style="padding-right: 40%">{exam_fee}</td>
          <td style="padding-left: 5px">檢驗處置費</td>
          <td align=right style="padding-right: 40%">{self_treat_fee}</td>
        </tr>
        <tr>
          <td style="padding-left: 5px">處置手術費</td>
          <td align=right style="padding-right: 40%">{treat_fee}</td>
          <td style="padding-left: 5px">藥品(自費)</td>
          <td align=right style="padding-right: 40%">{self_drug_fee}</td>
        </tr>
        <tr>
          <td style="padding-left: 5px">材料費</td>
          <td align=right style="padding-right: 40%">0</td>
          <td style="padding-left: 5px">衛材(自費)</td>
          <td align=right style="padding-right: 40%">{material_fee}</td>
        </tr>
        <tr>
          <td align=center colspan=2>小計: 健保申報 {ins_total_fee}點<br>(健保申報點數非一點一元給付)</td>
          <td align=center colspan=2>小計: 部份負擔金額 {total_share_fee}元<br>其他自費金額: {total_fee}</td>
        </tr>
        <tr>
          <td align=center colspan=2>應繳金額: {total_cash}元</td>
          <td align=center colspan=2>經手人: {registrar}</td>
        </tr>
    """

    return html


# 健保局自費費用格式
def get_fees_html3(database, case_key):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    cashier = string_utils.xstr(row["Cashier"])

    if string_utils.xstr(row["InsType"]) == "自費":
        regist_fee = number_utils.get_integer(row["RegistFee"])
    else:
        regist_fee = 0

    # diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
    # drug_share_fee = number_utils.get_integer(row['SDrugShareFee'])
    # total_share_fee = diag_share_fee + drug_share_fee

    s_diag_fee = number_utils.get_integer(row["SDiagFee"])
    s_drug_fee = number_utils.get_integer(row["SDrugFee"])
    s_acupuncture_fee = number_utils.get_integer(row["SAcupunctureFee"])
    s_massage_fee = number_utils.get_integer(row["SMassageFee"])

    s_herb_fee = number_utils.get_integer(row["SHerbFee"])
    s_expensive_fee = number_utils.get_integer(row["SExpensiveFee"])
    s_exam_fee = number_utils.get_integer(row["SExamFee"])
    s_material_fee = number_utils.get_integer(row["SMaterialFee"])

    discount_fee = number_utils.get_integer(row["DiscountFee"])
    total_fee = number_utils.get_integer(row["TotalFee"])

    total_cash = regist_fee + total_fee

    html = f"""
        <tr>
          <td style="padding-left: 5px">自費診察費</td>
          <td align=right style="padding-right: 40%">{s_diag_fee}</td>
          <td style="padding-left: 5px">掛號費</td>
          <td align=right style="padding-right: 40%">{regist_fee}</td>
        </tr>
        <tr>
          <td style="padding-left: 5px">自費藥費</td>
          <td align=right style="padding-right: 40%">{s_drug_fee}</td>
          <td style="padding-left: 5px">自費針灸費</td>
          <td align=right style="padding-right: 40%">{s_acupuncture_fee}</td>
        </tr>
        <tr>
          <td style="padding-left: 5px">水藥費</td>
          <td align=right style="padding-right: 40%">{s_herb_fee}</td>
          <td style="padding-left: 5px">民俗調理費</td>
          <td align=right style="padding-right: 40%">{s_massage_fee}</td>
        </tr>
        <tr>
          <td style="padding-left: 5px">高貴藥費</td>
          <td align=right style="padding-right: 40%">{s_expensive_fee}</td>
          <td style="padding-left: 5px">自費檢驗費</td>
          <td align=right style="padding-right: 40%">{s_exam_fee}</td>
        </tr>
        <tr>
          <td style="padding-left: 5px">自費材料費</td>
          <td align=right style="padding-right: 40%">{s_material_fee}</td>
          <td style="padding-left: 5px">折扣</td>
          <td align=right style="padding-right: 40%">{-discount_fee}</td>
        </tr>
        <tr>
          <td align=center colspan=2>應繳金額: {total_cash}元</td>
          <td align=center colspan=2>收款人: {cashier}</td>
        </tr>
    """

    return html


# 自費費用
def get_fees_html13(database, case_key):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    ins_receipt_fee = (
        number_utils.get_integer(row["RegistFee"])
        + number_utils.get_integer(row["SDiagShareFee"])
        + number_utils.get_integer(row["SDrugShareFee"])
        + number_utils.get_integer(row["DepositFee"])
    )

    regist_fee = string_utils.xstr(number_utils.get_integer(row["RegistFee"]))
    diag_share_fee = string_utils.xstr(number_utils.get_integer(row["SDiagShareFee"]))
    drug_share_fee = string_utils.xstr(number_utils.get_integer(row["SDrugShareFee"]))
    # total_share_fee = string_utils.xstr(
    #     number_utils.get_integer(row['SDiagShareFee']) +
    #     number_utils.get_integer(row['SDrugShareFee'])
    # )
    deposit_fee = string_utils.xstr(number_utils.get_integer(row["DepositFee"]))
    diag_fee = string_utils.xstr(number_utils.get_integer(row["DiagFee"]))
    drug_fee = string_utils.xstr(number_utils.get_integer(row["InterDrugFee"]))
    pharmacy_fee = string_utils.xstr(number_utils.get_integer(row["PharmacyFee"]))
    treat_fee = string_utils.xstr(
        number_utils.get_integer(row["AcupunctureFee"])
        + number_utils.get_integer(row["MassageFee"])
        + number_utils.get_integer(row["DislocateFee"])
    )
    # ins_total_fee = string_utils.xstr(number_utils.get_integer(row['InsTotalFee']))
    ins_apply_fee = string_utils.xstr(number_utils.get_integer(row["InsApplyFee"]))
    s_diag_fee = string_utils.xstr(number_utils.get_integer(row["SDiagFee"]))
    s_drug_fee = string_utils.xstr(number_utils.get_integer(row["SDrugFee"]))
    herb_fee = string_utils.xstr(number_utils.get_integer(row["SHerbFee"]))
    expensive_fee = string_utils.xstr(number_utils.get_integer(row["SExpensiveFee"]))
    material_fee = string_utils.xstr(number_utils.get_integer(row["SMaterialFee"]))

    acupuncture_fee = string_utils.xstr(
        number_utils.get_integer(row["SAcupunctureFee"])
    )
    massage_fee = string_utils.xstr(number_utils.get_integer(row["SMassageFee"]))
    self_total_fee = string_utils.xstr(number_utils.get_integer(row["SelfTotalFee"]))
    discount_fee = string_utils.xstr(number_utils.get_integer(row["DiscountFee"]))
    total_fee = string_utils.xstr(number_utils.get_integer(row["TotalFee"]))
    receipt_fee = string_utils.xstr(number_utils.get_integer(row["ReceiptFee"]))
    total_receipt_fee = string_utils.xstr(
        ins_receipt_fee + number_utils.get_integer(row["ReceiptFee"])
    )

    html = f"""
        <tr>
          <td>自費診察費:{s_diag_fee}</td>
          <td>一般藥費:{s_drug_fee}</td>
        </tr>
        <tr>
          <td>水煎藥費:{herb_fee}</td>
          <td>高貴藥費:{expensive_fee}</td>
        </tr>
        <tr>
          <td>自費材料費:{material_fee}</td>
          <td>自費針灸費:{acupuncture_fee}</td>
        </tr>
        <tr>
          <td>傷科處置費:{massage_fee}</td>
          <td>合計金額:{self_total_fee}</td>
        </tr>
        <tr>
          <td>自費應收:{total_fee}</td>
          <td>自費實收:{receipt_fee}</td>
        </tr>
    """

    return html


# 健保費用
def get_ins_fees_html_22(database, case_key):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    regist_fee = string_utils.xstr(number_utils.get_integer(row["RegistFee"]))
    diag_share_fee = string_utils.xstr(number_utils.get_integer(row["SDiagShareFee"]))
    drug_share_fee = string_utils.xstr(number_utils.get_integer(row["SDrugShareFee"]))
    # total_share_fee = string_utils.xstr(
    #     number_utils.get_integer(row['SDiagShareFee']) +
    #     number_utils.get_integer(row['SDrugShareFee'])
    # )
    deposit_fee = string_utils.xstr(number_utils.get_integer(row["DepositFee"]))
    total_fee = string_utils.xstr(
        number_utils.get_integer(row["RegistFee"])
        + number_utils.get_integer(row["SDiagShareFee"])
        + number_utils.get_integer(row["SDrugShareFee"])
        + number_utils.get_integer(row["DepositFee"])
    )
    diag_fee = string_utils.xstr(number_utils.get_integer(row["DiagFee"]))
    drug_fee = string_utils.xstr(number_utils.get_integer(row["InterDrugFee"]))
    pharmacy_fee = string_utils.xstr(number_utils.get_integer(row["PharmacyFee"]))
    treat_fee = string_utils.xstr(
        number_utils.get_integer(row["AcupunctureFee"])
        + number_utils.get_integer(row["MassageFee"])
        + number_utils.get_integer(row["DislocateFee"])
    )
    # ins_total_fee = string_utils.xstr(number_utils.get_integer(row['InsTotalFee']))
    ins_total_fee = string_utils.xstr(number_utils.get_integer(row["InsTotalFee"]))
    ins_apply_fee = string_utils.xstr(number_utils.get_integer(row["InsApplyFee"]))

    html = f"""
        <table width="98%" cellspacing="0">
            <tr>
                <td>診察費:</td><td align=right>{diag_fee}</td>
                <td width="15%"></td>
                <td>內服藥費:</td><td align=right>{drug_fee}</td>
                <td width="15%"></td>
                <td>調劑費用:</td><td align=right>{pharmacy_fee}</td>
            </tr>
            <tr>
                <td>處置費:</td><td align=right>{treat_fee}</td>
                <td width="15%"></td>
                <td>健保合計:</td><td align=right>{ins_total_fee}</td>
                <td width="15%"></td>
                <td>健保申請:</td><td align=right>{ins_apply_fee}</td>
            </tr>
        </table>
        <hr>
        <table width="98%" cellspacing="0">
            <tr>
                <td>掛號費:</td><td align=right>{regist_fee}</td>
                <td width="15%"></td>
                <td>門診負擔:</td><td align=right>{diag_share_fee}</td>
                <td width="15%"></td>
                <td>藥品負擔:</td><td align=right>{drug_share_fee}</td>
            </tr>
            <tr>
                <td>欠卡費:</td><td align=right>{deposit_fee}</td>
                <td width="15%"></td>
                <td>健保實收:</td><td align=right>{total_fee}</td>
                <td width="15%"></td>
                <td></td><td></td>
            </tr>
        </table>
    """

    return html


def get_medicine_detail(
    medicine_set, rows, row_no, pres_days, packages, print_alias="N", by_packages=False
):
    try:
        medicine_type = string_utils.xstr(rows[row_no]["MedicineType"])
        medicine_name = string_utils.xstr(rows[row_no]["MedicineName"])
        medicine_alias = string_utils.xstr(rows[row_no]["MedicineAlias"])
        try:
            dosage_mode = string_utils.xstr(rows[row_no]["DosageMode"])
        except Exception:
            dosage_mode = None

        ins_code = string_utils.xstr(rows[row_no]["InsCode"])

        if medicine_type == "檢驗" and ins_code != "":
            medicine_name = medicine_alias + " " + medicine_name

        if print_alias == "Y" and medicine_alias != "":
            medicine_name = medicine_alias

        unit = string_utils.xstr(rows[row_no]["Unit"])
        location = string_utils.xstr(rows[row_no]["Location"])
    except (IndexError, TypeError):
        medicine_name, dosage_mode, ins_code, medicine_type, unit, location = (
            "",
            "",
            "",
            "",
            "",
            "",
        )

    try:
        if medicine_set == 1 and medicine_type in ["穴道", "處置"]:
            dosage, instruction, unit, total_dosage = "", "", "", ""
        else:
            if packages is None or packages == 0:
                packages = 1

            dosage = rows[row_no]["Dosage"]
            instruction = rows[row_no]["Instruction"]
            total_dosage = dosage * pres_days  # 日量

            if dosage_mode == "次劑量":
                total_dosage *= packages
            elif dosage_mode == "總量":
                total_dosage = dosage
            elif (
                by_packages
                and medicine_set >= 2
                and unit not in ["克", "錢", "帖", "次"]
            ):  # 2025-02-06 耀康 非科中或水藥要乘以包數
                total_dosage *= packages

            if medicine_type in ["檢驗"]:
                dosage = number_utils.get_integer(dosage)
            else:
                dosage = f"{dosage:.1f}"

            total_dosage = f"{total_dosage:.1f}"
    except Exception:
        dosage, instruction, total_dosage = "", "", ""  # ascii 0->null 填補

    return (
        medicine_name,
        location,
        dosage,
        unit,
        total_dosage,
        ins_code,
        instruction,
        medicine_type,
        dosage_mode,
    )


def get_instruction_html_one_line(
    database, system_settings, case_key, medicine_set, additional=None
):
    sql = f"""
        SELECT CaseDate, Doctor, DrugShareFee, TotalFee FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    doctor = string_utils.xstr(row["Doctor"])
    if medicine_set is None:
        if doctor != "":
            html = f"醫師: {doctor}"
        else:
            html = ""

        return html

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    instruction = case_utils.get_instruction(database, case_key, medicine_set)
    total_fee = case_utils.get_total_fee(database, case_key, medicine_set)
    drug_share_fee = number_utils.get_integer(row["DrugShareFee"])
    dosage_mode = case_utils.get_dosage_mode(database, case_key, medicine_set)

    additional_label = ""
    if additional not in ["", None]:
        additional_label = f"<b>「{additional}」</b>"

    if pres_days > 0 and additional is None:
        if packages is None or packages == 0:
            packages = 1

        _, total_dosage, _, _ = case_utils.get_prescript_html_data(
            database, system_settings, case_key, medicine_set
        )

        case_date = row["CaseDate"].date()
        html = f"""
              指示:一日{packages}包, {pres_days}日份, 共{packages * pres_days}包
              服法:{instruction}服用 總量:{total_dosage:.1f}
              醫師/調劑者:{doctor} 調劑日:{case_date}
        """

        # if medicine_set == 1 and drug_share_fee > 0:
        #     html += f'藥品負擔: {drug_share_fee}'
        # elif medicine_set >= 2 and total_fee > 0:
        #     html += f'自費金額: {total_fee}'
    else:
        if doctor != "":
            html = f"醫師: {doctor}"
        else:
            html = ""

        # if medicine_set >= 2 and total_fee > 0:
        #     html += f'  自費金額: {total_fee}'

    return html


def get_instruction_html_0(
    database, system_settings, case_key, medicine_set, additional=None
):
    sql = f"""
        SELECT CaseDate, Doctor, DrugShareFee, TotalFee FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    doctor = string_utils.xstr(row["Doctor"])
    if medicine_set is None:
        if doctor != "":
            html = f"醫師: {doctor}"
        else:
            html = ""

        return html

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    instruction = case_utils.get_instruction(database, case_key, medicine_set)
    dosage_mode = case_utils.get_dosage_mode(database, case_key, medicine_set)

    total_fee = case_utils.get_total_fee(database, case_key, medicine_set)
    drug_share_fee = number_utils.get_integer(row["DrugShareFee"])

    if pres_days > 0 and additional is None:
        if packages is None or packages == 0:
            packages = 1

        _, total_dosage, _, single_day_dosage = case_utils.get_prescript_html_data(
            database, system_settings, case_key, medicine_set
        )

        total_dosage = f"{total_dosage:.1f}"

        case_date = row["CaseDate"].date()
        html = f"""
              指示:一日{packages}包, {pres_days}日份, 共{packages * pres_days}包<br>
              服法:{instruction}服用 總量:{total_dosage}<br>
              醫師/調劑者:{doctor}<br>
              調劑日:{case_date}
        """

        # if medicine_set == 1 and drug_share_fee > 0:
        #     html += f'藥品負擔: {drug_share_fee}'
        # elif medicine_set >= 2 and total_fee > 0:
        #     html += f'自費金額: {total_fee}'
    else:
        html = ""
        if instruction not in ["", None]:
            html = f" 使用方式: {instruction}<br>"

        if doctor != "":
            html += f"醫師: {doctor}"

    return html


def get_instruction_html7(
    database,
    system_settings,
    case_key,
    medicine_set,
    additional=None,
):
    sql = f"""
        SELECT CaseDate, Doctor, DrugShareFee, TotalFee FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    doctor = string_utils.xstr(row["Doctor"])
    if medicine_set is None:
        if doctor != "":
            html = f"醫師: {doctor}"
        else:
            html = ""

        return html

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    instruction = case_utils.get_instruction(database, case_key, medicine_set)
    dosage_mode = case_utils.get_dosage_mode(database, case_key, medicine_set)

    prescript_total_fee = number_utils.get_integer(
        case_utils.get_total_fee(database, case_key, medicine_set)
    )
    drug_share_fee = number_utils.get_integer(row["DrugShareFee"])
    total_fee = number_utils.get_integer(row["TotalFee"])
    if total_fee <= 0:
        prescript_total_fee = total_fee

    if pres_days > 0 and additional is None:
        _, total_dosage, _, single_day_dosage = case_utils.get_prescript_html_data(
            database, system_settings, case_key, medicine_set
        )

        total_dosage = f"{total_dosage:.1f}"
        case_date = row["CaseDate"].date()
        line1 = f"""
            醫師: {doctor} 調劑者: {doctor} 調劑日: {case_date}
        """

        line2 = f"""
            指示: 一日<font size="5"><b>{packages}</b></font>包, 共<font size="5"><b>{pres_days}</b></font>日份
            <font size="5"><b>{instruction}</b></font> 服用
        """
        line3 = f"""
            日量: {single_day_dosage} 總量: {total_dosage}
        """
        if medicine_set == 1 and drug_share_fee > 0:
            line3 += f" 藥品負擔: {drug_share_fee}"
        elif medicine_set >= 2 and prescript_total_fee > 0:
            line3 += f" 自費金額: {prescript_total_fee}"

        html = f"""
            <table width="100%">
                <tr>
                    <td style="padding-bottom: 8px;">{line1}</td>
                </tr>
                <tr>
                    <td>{line2}</td>
                </tr>
                <tr>
                    <td>{line3}</td>
                </tr>
            </table>
        """
    else:
        if doctor != "":
            html = f"醫師: {doctor}"
        else:
            html = ""

        if number_utils.get_integer(medicine_set) >= 2 and prescript_total_fee > 0:
            html += f"<br>自費金額: {prescript_total_fee}"

    return html


def get_instruction_html(
    database,
    system_settings,
    case_key,
    medicine_set,
    additional=None,
    resize_instruction=False,
):
    sql = f"""
        SELECT CaseDate, Doctor, DrugShareFee, TotalFee FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    doctor = string_utils.xstr(row["Doctor"])
    if medicine_set is None:
        if doctor != "":
            html = f"醫師: {doctor}"
        else:
            html = ""

        return html

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    instruction = case_utils.get_instruction(database, case_key, medicine_set)
    dosage_mode = case_utils.get_dosage_mode(database, case_key, medicine_set)

    prescript_total_fee = number_utils.get_integer(
        case_utils.get_total_fee(database, case_key, medicine_set)
    )
    drug_share_fee = number_utils.get_integer(row["DrugShareFee"])
    total_fee = number_utils.get_integer(row["TotalFee"])
    if total_fee <= 0:
        prescript_total_fee = total_fee

    if pres_days > 0 and additional is None:
        _, total_dosage, _, single_day_dosage = case_utils.get_prescript_html_data(
            database, system_settings, case_key, medicine_set
        )

        total_dosage = f"{total_dosage:.1f}"
        case_date = row["CaseDate"].date()
        if resize_instruction:
            html = f"""
                醫師: {doctor} 調劑者: {doctor} 調劑日: {case_date}
                 指示: 一日<font size="5"><b>{packages}</b></font>包, 共<font size="5"><b>{pres_days}</b></font>日份
                <font size="5"><b>{instruction}</b></font> 服用 日量: {single_day_dosage} 總量: {total_dosage}
            """
        else:
            html = f"""
                醫師: {doctor} 調劑者: {doctor} 調劑日: {case_date}
                 指示: 一日{packages}包, 共{pres_days}日份 {instruction}服用 日量: {single_day_dosage} 總量: {total_dosage}
            """

        if medicine_set == 1 and drug_share_fee > 0:
            html += f"<br>藥品負擔: {drug_share_fee}"
        elif medicine_set >= 2 and prescript_total_fee > 0:
            html += f"<br>自費金額: {prescript_total_fee}"
    else:
        if doctor != "":
            html = f"醫師: {doctor}"
        else:
            html = ""

        if number_utils.get_integer(medicine_set) >= 2 and prescript_total_fee > 0:
            html += f"<br>自費金額: {prescript_total_fee}"

    return html


def get_instruction_html1(
    database,
    system_settings,
    case_key,
    medicine_set,
    additional=None,
    print_total_fee=True,
    print_pharmacy_date=False,
):
    sql = f"""
        SELECT CaseDate, RegistNo, Doctor, RegistFee, SDiagShareFee, SDrugShareFee, TotalFee FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    doctor = string_utils.xstr(row["Doctor"])
    if medicine_set is None:
        if doctor != "":
            html = f"醫師: {doctor}"
        else:
            html = ""

        return html

    regist_no = number_utils.get_integer(row["RegistNo"])
    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    instruction = case_utils.get_instruction(database, case_key, medicine_set)

    if medicine_set == 1:
        regist_fee = number_utils.get_integer(row["RegistFee"])
        diag_share_fee = number_utils.get_integer(row["SDiagShareFee"])
        drug_share_fee = number_utils.get_integer(row["SDrugShareFee"])
        total_fee = regist_fee + diag_share_fee + drug_share_fee
    else:
        total_fee = case_utils.get_total_fee(database, case_key, medicine_set)

    pres_days = number_utils.get_integer(pres_days)
    packages = number_utils.get_integer(packages)

    if pres_days <= 0:
        html = f"醫師: {doctor}"
        return html

    if packages == 0:
        packages = 1

    total_packages = pres_days * packages

    _, total_dosage, _, single_day_dosage = case_utils.get_prescript_html_data(
        database, system_settings, case_key, medicine_set
    )

    html = f"""
            醫師/調劑者: {doctor} {packages}包 * {pres_days}天 共{total_packages}包
            {instruction} 總量: {total_dosage} 診號: {regist_no}
    """
    if print_pharmacy_date:
        case_date = string_utils.xstr(row["CaseDate"].date())
        html += f"&nbsp;&nbsp;&nbsp;&nbsp;調劑日: {case_date}"

    if print_total_fee:
        html += f"<br>總價: {total_fee}"

    return html


def get_instruction_html_utec(
    database,
    system_settings,
    case_key,
    medicine_set,
    additional=None,
    print_total_fee=True,
):
    sql = f"""
        SELECT CaseDate, RegistNo, Doctor, RegistFee, SDiagShareFee, SDrugShareFee, TotalFee FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    doctor = string_utils.xstr(row["Doctor"])
    if medicine_set is None:
        if doctor != "":
            html = f"醫師: {doctor}"
        else:
            html = ""

        return html

    regist_no = number_utils.get_integer(row["RegistNo"])
    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    instruction = case_utils.get_instruction(database, case_key, medicine_set)

    if medicine_set == 1:
        regist_fee = number_utils.get_integer(row["RegistFee"])
        diag_share_fee = number_utils.get_integer(row["SDiagShareFee"])
        drug_share_fee = number_utils.get_integer(row["SDrugShareFee"])
        total_fee = regist_fee + diag_share_fee + drug_share_fee
    else:
        total_fee = case_utils.get_total_fee(database, case_key, medicine_set)

    pres_days = number_utils.get_integer(pres_days)
    packages = number_utils.get_integer(packages)

    if pres_days <= 0:
        html = f"醫師: {doctor}"
        return html

    if packages == 0:
        packages = 1

    total_packages = pres_days * packages

    _, total_dosage, _, single_day_dosage = case_utils.get_prescript_html_data(
        database, system_settings, case_key, medicine_set
    )

    html = f"""
            醫師: {doctor} {packages}包 * {pres_days}天
            服法: {instruction} 藥負: {drug_share_fee} 總量: {total_dosage} 診號: {regist_no}
    """

    return html


def get_instruction_html1_1(
    database, system_settings, case_key, medicine_set, additional=None
):
    sql = f"""
        SELECT CaseDate, RegistNo, Doctor, TotalFee FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    doctor = string_utils.xstr(row["Doctor"])
    if medicine_set is None:
        if doctor != "":
            html = f"醫師: {doctor}"
        else:
            html = ""

        return html

    regist_no = number_utils.get_integer(row["RegistNo"])
    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    # total_fee = case_utils.get_total_fee(database, case_key, medicine_set)
    total_fee = number_utils.get_integer(row["TotalFee"])
    if system_settings.field("列印所有收費收據各自金額") == "Y":
        total_fee = number_utils.get_integer(
            case_utils.get_total_fee(database, case_key, medicine_set)
        )

    pres_days = number_utils.get_integer(pres_days)
    if pres_days == 0:
        pres_days = 1

    packages = number_utils.get_integer(packages)
    if packages == 0:
        packages = 1

    instruction = case_utils.get_instruction(database, case_key, medicine_set)
    total_packages = pres_days * packages

    _, total_dosage, _, single_day_dosage = case_utils.get_prescript_html_data(
        database, system_settings, case_key, medicine_set
    )
    total_dosage = f"{total_dosage:.1f}"

    html = f"""
            醫師: {doctor} {packages}包 * {pres_days}天 共{total_packages}包
            {instruction} 總量: {total_dosage} 診號: {regist_no}<br>
            總價: {total_fee}
    """

    return html


def get_fee_html(database, case_key, medicine_set):
    if medicine_set is None:
        return ""

    self_total_fee = case_utils.get_self_total_fee(database, case_key, medicine_set)
    discount_fee = case_utils.get_discount_fee(database, case_key, medicine_set)
    total_fee = case_utils.get_total_fee(database, case_key, medicine_set)

    html = f"""
        自費合計: {self_total_fee} 折扣: {discount_fee} 應收金額: {total_fee}
    """

    return html


def get_instruction_html2(
    database, system_settings, case_key, medicine_set, additional=None, ins_exam=False
):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    doctor = string_utils.xstr(row["Doctor"])
    case_date = row["CaseDate"].date()

    if medicine_set is None:
        html = f"""
              醫師: {doctor}
        """
        return html

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    instruction = case_utils.get_instruction(database, case_key, medicine_set)
    total_fee = case_utils.get_total_fee(database, case_key, medicine_set)
    dosage_mode = case_utils.get_dosage_mode(database, case_key, medicine_set)
    if dosage_mode in ["次劑量"]:
        package_label = "包"
    else:
        package_label = "日"

    additional_label = ""
    if additional not in ["", None]:
        additional_label = f"<b>「{additional}」</b>"

    if pres_days > 0 or instruction not in ["", None]:
        clinic_name = system_settings.field("院所名稱")

        _, total_dosage, _, single_day_dosage = case_utils.get_prescript_html_data(
            database, system_settings, case_key, medicine_set
        )

        if ins_exam:
            html = f"""
                主治醫師: {doctor}
            """
        elif pres_days <= 0:
            html = ""

            if packages > 0:
                html += f"每{package_label}{packages}次, {instruction}"
            else:
                html += instruction

            html += f"<br>醫師: {doctor} 調劑者: {doctor} 調劑日: {case_date}<br>"
        else:
            if clinic_name in ["鵲杏中醫診所"]:
                html = f"""
                    藥日: {packages}包 * {pres_days}天 共{packages * pres_days}包 {instruction}服用
                    每{package_label}{single_day_dosage:.1f} 總量: {total_dosage:.1f} {additional_label}<br>
                    醫師: {doctor} 調劑者: {doctor} 調劑日: {case_date}<br>
                """
            else:
                html = f"""
                    藥日: {packages}包 * {pres_days}天 共{packages * pres_days}包 {instruction}服用
                    總量: {total_dosage:.1f} {additional_label}<br>
                    醫師: {doctor} 調劑者: {doctor} 調劑日: {case_date}<br>
                """
    else:
        html = f"""
              主治醫師: {doctor}<br>
        """

    return html


def get_instruction_html3(
    database, system_settings, case_key, medicine_set, additional=None
):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    doctor = string_utils.xstr(row["Doctor"])

    if medicine_set is None:
        html = f"""
              醫師: {doctor}
        """
        return html

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    instruction = case_utils.get_instruction(database, case_key, medicine_set)
    total_fee = case_utils.get_total_fee(database, case_key, medicine_set)

    additional_label = ""
    if additional is not None:
        additional_label = f"<b>「{additional}」</b>"

    if pres_days > 0:
        _, total_dosage, _, single_day_dosage = case_utils.get_prescript_html_data(
            database, system_settings, case_key, medicine_set
        )
        total_dosage = f"{total_dosage:.1f}"

        html = f"""
            藥日: {packages}包 * {pres_days}天 {instruction} {additional_label} 醫師: {doctor} 調劑者: {doctor}<br>
        """
    else:
        html = f"""
              主治醫師: {doctor}<br>
        """

    return html


def get_instruction_html4(
    database, system_settings, case_key, medicine_set, additional=None
):
    sql = f"""
        SELECT CaseDate, Doctor, DrugShareFee, TotalFee FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    doctor = string_utils.xstr(row["Doctor"])
    if medicine_set is None:
        if doctor != "":
            html = f"醫師: {doctor}"
        else:
            html = ""

        return html

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    instruction = case_utils.get_instruction(database, case_key, medicine_set)

    prescript_total_fee = number_utils.get_integer(
        case_utils.get_total_fee(database, case_key, medicine_set)
    )
    drug_share_fee = number_utils.get_integer(row["DrugShareFee"])
    total_fee = number_utils.get_integer(row["TotalFee"])
    if total_fee <= 0:
        prescript_total_fee = total_fee

    if pres_days > 0 and additional is None:
        _, total_dosage, _, single_day_dosage = case_utils.get_prescript_html_data(
            database, system_settings, case_key, medicine_set
        )
        total_dosage = f"{total_dosage:.1f}"

        case_date = row["CaseDate"].date()
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"], "-")
        html = f"""
            <table width="98%">
              <tbody>
                <tr>
                    <td>醫師: {doctor}</td>
                    <td>調劑者: {doctor}</td>
                    <td>調劑日: {case_date}</td>
                </tr>
                <tr>
                    <td colspan="3">指示: 一日{packages}包, 共{pres_days}日份 {instruction}服用</td>
                </tr>
              </tbody>
            </table>
        """
    else:
        if doctor != "":
            html = f"醫師: {doctor}"
        else:
            html = ""

    return html


# 取得列印健保或自費處方dialog
def get_medicine_set_items(
    parent, database, system_settings, case_key, form_type, print_type="選擇列印"
):
    if case_key in ["", None]:
        return

    sql = f"""
        SELECT MedicineSet FROM prescript
        WHERE
            CaseKey = {case_key}
        GROUP BY MedicineSet
        ORDER BY MedicineSet
    """
    rows = database.select_record(sql)
    row_count = len(rows)

    sql = f"""
        SELECT TreatType FROM cases
        WHERE
            CaseKey = {case_key} AND
            TreatType = "醫療諮詢"
    """
    case_rows = database.select_record(sql)
    if len(case_rows) > 0:
        row_count += 1

    if row_count <= 0:
        items = None
    elif row_count == 1:
        try:
            medicine_set = number_utils.get_integer(rows[0]["MedicineSet"])
        except Exception:
            medicine_set = 1

        if medicine_set == 1:
            items = [f"健保{form_type}"]
        else:
            items = [f"自費{form_type}{medicine_set - 1}"]
    else:
        dialog = dialog_utils.get_dialog_select_medicine_set(
            parent, database, system_settings, case_key, form_type
        )
        if print_type == "選擇列印":
            if not dialog.exec_():
                items = None
            else:
                items = dialog.get_selected_options()
        else:
            items = dialog.get_all_options()

        dialog.deleteLater()

    return items


# 列印門診掛號單
def print_regist_form(
    parent, database, system_settings, case_key, print_option="系統設定"
):
    form = system_settings.field("門診掛號單格式")
    if form is None:
        return

    printable = system_settings.field("列印門診掛號單")
    print_type = "print"

    if print_option != "系統設定" and printable == "不印":
        printable = "列印"

    if printable == "不印":
        return
    elif system_settings.field("列印門診掛號單") == "詢問":
        print_type = "print"

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("列印掛號收據")
        msg_box.setText("<font size='4' color='red'><b>是否列印掛號收據?</b></font>")
        msg_box.setInformativeText(
            "<font size='4'>注意！掛號收據將會列印至系統設定的印表機.</font>"
        )
        msg_box.addButton(QPushButton("否"), QMessageBox.NoRole)  # 0
        msg_box.addButton(QPushButton("是"), QMessageBox.AcceptRole)  # 1

        printing = msg_box.exec_()
        if not printing:
            return
    elif system_settings.field("列印門診掛號單") == "預覽":
        print_type = "preview"
    elif system_settings.field("列印門診掛號單") == "列印":
        print_type = "print"
    elif printable == "列印":
        print_type = "print"

    print_registration_form = get_print_registration_form(form)
    if print_registration_form is None:
        return

    print_form = print_registration_form(parent, database, system_settings, case_key)

    if print_type == "print":
        print_form.print(print_option)
    else:
        print_form.preview(print_option)

    del print_form


# 列印民俗調理單
def print_massage_form(
    parent, database, system_settings, case_key, print_option="系統設定"
):
    form = system_settings.field("民俗調理單格式")
    if form is None:
        return

    printable = system_settings.field("列印民俗調理單")

    sql = f"""
        SELECT InsType FROM cases
        WHERE
            Position1 = {case_key}
    """
    rows = database.select_record(sql)
    if printable == "自費" and len(rows) >= 1:  # 只印自費民俗調理, 健保+民俗調理不印
        return

    print_type = "print"

    if print_option != "系統設定" and printable == "不印":
        printable = "列印"

    if printable == "不印":
        return
    elif system_settings.field("列印民俗調理單") == "詢問":
        print_type = "print"

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("列印民俗調理單")
        msg_box.setText("<font size='4' color='red'><b>是否列印民俗調理單?</b></font>")
        msg_box.setInformativeText(
            "<font size='4'>注意！民俗調理單將會列印至系統設定的印表機.</font>"
        )
        msg_box.addButton(QPushButton("否"), QMessageBox.NoRole)  # 0
        msg_box.addButton(QPushButton("是"), QMessageBox.AcceptRole)  # 1

        printing = msg_box.exec_()
        if not printing:
            return

    elif system_settings.field("列印民俗調理單") == "預覽":
        print_type = "preview"
    elif system_settings.field("列印民俗調理單") == "列印":
        print_type = "print"

    print_massage_form_func = get_print_massage_form(form)
    if print_massage_form_func is None:
        return

    print_form = print_massage_form_func(parent, database, system_settings, case_key)
    print_form2 = None

    if system_settings.field("民俗調理單印表機2") not in ["", None]:
        printer2 = get_printer(system_settings, "民俗調理單印表機2")
        print_form2 = print_massage_form_func(
            parent, database, system_settings, case_key, printer2
        )

    if print_type == "print":
        print_form.print(print_option)
        if print_form2 is not None:
            print_form2.print(print_option)
    else:
        print_form.preview(print_option)
        if print_form2 is not None:
            print_form2.preview(print_option)

    del print_form


# 列印處方箋
def get_print_prescription(parent, database, system_settings, case_key, print_mode):
    from printer import print_prescription

    module = importlib.reload(print_prescription)
    print_module = module.PrintPrescription(
        parent, database, system_settings, case_key, print_mode
    )

    return print_module


# 列印處方箋
def print_prescription_form(parent, database, system_settings, case_key, print_option):
    print_form = get_print_prescription(
        parent, database, system_settings, case_key, print_option
    )
    print_form.print()

    del print_form


# 列印費用收據
def get_print_receipt(
    parent,
    database,
    system_settings,
    case_key,
    print_mode,
    print_dosage=True,
    print_only_medicine_set2=False,
):
    from printer import print_receipt

    module = importlib.reload(print_receipt)
    print_module = module.PrintReceipt(
        parent,
        database,
        system_settings,
        case_key,
        print_mode,
        print_dosage,
        print_only_medicine_set2,
    )

    return print_module


# 列印費用收據
def print_receipt_form(
    parent,
    database,
    system_settings,
    case_key,
    print_option,
    print_dosage=True,
    print_only_medicine_set2=False,
):
    print_form = get_print_receipt(
        parent,
        database,
        system_settings,
        case_key,
        print_option,
        print_dosage,
        print_only_medicine_set2=print_only_medicine_set2,
    )
    print_form.print()

    del print_form


# 列印其他收據1
def get_print_misc(parent, database, system_settings, case_key, print_mode):
    from printer import print_misc

    module = importlib.reload(print_misc)
    print_module = module.PrintMisc(
        parent, database, system_settings, case_key, print_mode
    )

    return print_module


# 列印其他收據1
def print_misc_form(parent, database, system_settings, case_key, print_type):
    print_form = get_print_misc(parent, database, system_settings, case_key, print_type)
    print_form.print()

    del print_form


# 列印其他收據2
def get_print_misc2(parent, database, system_settings, case_key, print_mode):
    from printer import print_misc2

    module = importlib.reload(print_misc2)
    print_module = module.PrintMisc2(
        parent, database, system_settings, case_key, print_mode
    )

    return print_module


# 列印其他收據2
def print_misc_form2(parent, database, system_settings, case_key, print_type):
    print_form = get_print_misc2(
        parent, database, system_settings, case_key, print_type
    )
    print_form.print()

    del print_form


# 列印其他收據3
def get_print_misc3(parent, database, system_settings, case_key, print_mode):
    from printer import print_misc3

    module = importlib.reload(print_misc3)
    print_module = module.PrintMisc3(
        parent, database, system_settings, case_key, print_mode
    )

    return print_module


# 列印其他收據3
def print_misc_form3(parent, database, system_settings, case_key, print_type):
    print_form = get_print_misc3(
        parent, database, system_settings, case_key, print_type
    )
    print_form.print()

    del print_form


# 列印藥袋
def get_print_prescription_bag(parent, database, system_settings, case_key, print_mode):
    from printer import print_prescription_bag

    module = importlib.reload(print_prescription_bag)
    print_module = module.PrintPrescriptionBag(
        parent, database, system_settings, case_key, print_mode
    )

    return print_module


# 列印藥袋
def print_prescription_bag_form(
    parent, database, system_settings, case_key, print_option
):
    print_form = get_print_prescription_bag(
        parent, database, system_settings, case_key, print_option
    )
    print_form.print()

    del print_form


# 列印健保處方箋
def print_ins_prescript(
    parent, database, system_settings, case_key, print_type, print_option="系統設定"
):
    form = system_settings.field("健保處方箋格式")
    if form is None:
        return

    printable = system_settings.field("列印健保處方箋")
    print_type = "print"

    if print_option != "系統設定" and printable == "不印":
        printable = "列印"

    prescript_count = get_prescript_count(database, case_key, medicine_set=1)

    if printable == "不印":
        return
    elif print_option == "系統設定" and printable == "藥品" and prescript_count <= 0:
        return
    elif printable == "詢問":
        print_type = "print"

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("列印健保處方箋")
        msg_box.setText("<font size='4' color='red'><b>是否列印健保處方箋?</b></font>")
        msg_box.setInformativeText(
            "<font size='4'>注意！處方箋將會列印至系統設定的印表機.</font>"
        )
        msg_box.addButton(QPushButton("否"), QMessageBox.NoRole)  # 0
        msg_box.addButton(QPushButton("是"), QMessageBox.AcceptRole)  # 1

        printing = msg_box.exec_()
        if not printing:
            return

    elif printable == "預覽":
        print_type = "preview"
    elif printable == "列印":
        print_type = "print"

    print_prescription_ins_form = get_print_prescription_ins_form(form)
    if print_prescription_ins_form is None:
        return

    print_form = print_prescription_ins_form(
        parent, database, system_settings, case_key
    )

    if print_type == "print":
        print_form.print()
        print_form.print("健保另包")
    else:
        print_form.preview()
        print_form.preview("健保另包")

    del print_form


# 列印自費處方箋
def print_self_prescript(
    parent,
    database,
    system_settings,
    case_key,
    medicine_set,
    print_type,
    print_option="系統設定",
):
    form = system_settings.field("自費處方箋格式")
    if form is None:
        return

    printable = system_settings.field("列印自費處方箋")
    print_type = "print"

    if print_option != "系統設定" and printable == "不印":
        printable = "列印"

    prescript_count = get_prescript_count(
        database, case_key, medicine_set=0
    )  # medicine_set = 0 全部自費

    if printable == "不印":
        return
    elif print_option == "系統設定" and printable == "藥品" and prescript_count <= 0:
        return
    elif printable == "詢問":
        print_type = "print"

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("列印自費處方箋")
        msg_box.setText("<font size='4' color='red'><b>是否列印自費處方箋?</b></font>")
        msg_box.setInformativeText(
            "<font size='4'>注意！處方箋將會列印至系統設定的印表機.</font>"
        )
        msg_box.addButton(QPushButton("否"), QMessageBox.NoRole)  # 0
        msg_box.addButton(QPushButton("是"), QMessageBox.AcceptRole)  # 1

        printing = msg_box.exec_()
        if not printing:
            return

    elif printable == "預覽":
        print_type = "preview"
    elif printable == "列印":
        print_type = "print"

    print_prescription_self_form = get_print_prescription_self_form(form)

    if print_prescription_self_form is None:
        return

    print_form = print_prescription_self_form(
        parent, database, system_settings, case_key, medicine_set
    )
    if print_type == "print":
        print_form.print()
    else:
        print_form.preview()

    del print_form


# 列印健保醫療收據
def print_ins_receipt(
    parent,
    database,
    system_settings,
    case_key,
    print_type,
    print_option="系統設定",
    print_dosage=True,
    print_note=False,
):
    form = system_settings.field("健保醫療收據格式")
    if form is None:
        return

    printable = system_settings.field("列印健保醫療收據")
    print_type = "print"
    prescript_count = get_prescript_count(database, case_key, medicine_set=1)

    if print_option != "系統設定" and printable == "不印":
        printable = "列印"

    if printable == "不印":
        return
    elif print_option == "系統設定" and printable == "藥品" and prescript_count <= 0:
        return
    elif printable == "詢問":
        print_type = "print"

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("列印健保醫療收據")
        msg_box.setText(
            "<font size='4' color='red'><b>是否列印健保醫療收據?</b></font>"
        )
        msg_box.setInformativeText(
            "<font size='4'>注意！醫療收據將會列印至系統設定的印表機.</font>"
        )
        msg_box.addButton(QPushButton("否"), QMessageBox.NoRole)  # 0
        msg_box.addButton(QPushButton("是"), QMessageBox.AcceptRole)  # 1

        printing = msg_box.exec_()
        if not printing:
            return

    elif printable == "預覽":
        print_type = "preview"
    elif printable == "列印":
        print_type = "print"

    print_receipt_ins_form = get_print_receipt_ins_form(form)
    if print_receipt_ins_form is None:
        return

    print_form = print_receipt_ins_form(
        parent, database, system_settings, case_key, print_dosage
    )

    if print_type == "print":
        print_form.print()
        print_form.print("健保另包")
        if print_note:
            print_form.print("補退掛號費用")

        if form[:2] in ["05", "06"]:
            for i in range(2):  # 列印兩張
                print_form.print("健保檢驗")
    else:
        print_form.preview()
        print_form.preview("健保另包")
        if print_note:
            print_form.preview("補退掛號費用")
        if form[:2] in ["05", "06"]:
            for i in range(2):  # 列印兩張
                print_form.preview("健保檢驗")

    del print_form


# 列印自費醫療收據
def print_self_receipt(
    parent,
    database,
    system_settings,
    case_key,
    medicine_set,
    print_type,
    print_option="系統設定",
    print_dosage=True,
):
    form = system_settings.field("自費醫療收據格式")
    if form is None:
        return

    printable = system_settings.field("列印自費醫療收據")
    print_type = "print"
    prescript_count = get_prescript_count(database, case_key, medicine_set=0)

    if print_option != "系統設定" and printable == "不印":
        printable = "列印"

    if printable == "不印":
        return
    elif print_option == "系統設定" and printable == "藥品" and prescript_count <= 0:
        return
    elif printable == "詢問":
        print_type = "print"

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("列印自費醫療收據")
        msg_box.setText(
            "<font size='4' color='red'><b>是否列印自費醫療收據?</b></font>"
        )
        msg_box.setInformativeText(
            "<font size='4'>注意！醫療收據將會列印至系統設定的印表機.</font>"
        )
        msg_box.addButton(QPushButton("否"), QMessageBox.NoRole)  # 0
        msg_box.addButton(QPushButton("是"), QMessageBox.AcceptRole)  # 1

        printing = msg_box.exec_()
        if not printing:
            return

    elif printable == "預覽":
        print_type = "preview"
    elif printable == "pdf":
        print_type = "print_to_pdf"
    elif printable == "列印":
        print_type = "print"

    if print_option == "pdf":
        print_type = "print_to_pdf"

    print_receipt_self_form = get_print_receipt_self_form(form)
    if print_receipt_self_form is None:
        return

    if (
        print_option == "系統設定" and form[:2] in ["09"] and medicine_set >= 3
    ):  # 格式09 只印自費1(已經包含全部自費金額), 其他不印
        return

    if (
        print_option == "系統設定"
        and medicine_set == 2
        and prescript_utils.is_folk_massage(database, system_settings, case_key)
        and system_settings.field("列印民俗調理") != "Y"
    ):  # 民俗調理是否列印收據
        return

    print_form = print_receipt_self_form(
        parent, database, system_settings, case_key, medicine_set, print_dosage
    )

    if print_type == "print":
        print_form.print()
        if system_settings.field("自費加印無劑量收據") == "Y":
            print_form.print("無劑量")
        if form[:2] in ["05"]:
            for i in range(2):  # 列印兩張
                print_form.print("自費檢驗")
    elif print_type == "print_to_pdf":
        try:
            print_form.print_to_pdf()
        except Exception:
            pass
    else:
        print_form.preview()
        if system_settings.field("自費加印無劑量收據") == "Y":
            try:
                print_form.preview("無劑量")
            except Exception:
                pass
        if form[:2] in ["05"]:
            for i in range(2):  # 列印兩張
                print_form.preview("自費檢驗")

    del print_form


# 列印藥袋
def print_prescript_bag(
    parent,
    database,
    system_settings,
    case_key,
    print_type,
    medicine_set,
    print_option="系統設定",
):
    form = system_settings.field("藥袋格式")
    if form is None:
        return

    printable = system_settings.field("列印藥袋")
    print_type = "print"

    if print_option != "系統設定" and printable == "不印":
        printable = "列印"

    prescript_count = get_prescript_count(database, case_key, medicine_set=medicine_set)

    if printable == "不印":
        return
    elif printable == "藥品" and prescript_count <= 0:
        return
    elif printable == "詢問":
        print_type = "print"

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("列印藥袋")
        msg_box.setText("<font size='4' color='red'><b>是否列印藥袋?</b></font>")
        msg_box.setInformativeText(
            "<font size='4'>注意！藥袋將會列印至系統設定的印表機.</font>"
        )
        msg_box.addButton(QPushButton("否"), QMessageBox.NoRole)  # 0
        msg_box.addButton(QPushButton("是"), QMessageBox.AcceptRole)  # 1

        printing = msg_box.exec_()
        if not printing:
            return

    elif printable == "預覽":
        print_type = "preview"
    elif printable == "列印":
        print_type = "print"

    if (
        form[:2] not in ["05", "07", "08"] and medicine_set >= 2
    ):  # 自費2只印藥袋5, 7, 8 其他不印
        return

    pres_days1 = case_utils.get_pres_days(database, case_key, medicine_set=1)
    current_ins_prescript_rows = prescript_utils.get_ins_prescript_rows(
        database, case_key, medicine_set
    )
    if form[:2] in ["07", "08"] and medicine_set >= 2:
        if pres_days1 > 0:  # 已經跟健保科中合併
            return

        if len(current_ins_prescript_rows) <= 0:  # 未開科中
            return

    print_prescription_bag_form = get_print_prescription_bag_form(form)
    if print_prescription_bag_form is None:
        return

    print_form = print_prescription_bag_form(
        parent, database, system_settings, case_key, medicine_set
    )

    if print_type == "print":
        print_form.print()
    else:
        print_form.preview()

    del print_form


# 檢查特定格式有記錄才印
def check_record_count(database, case_key, form):
    if form is None:
        return True

    form_no = form.split("-")[0]
    if form_no not in ["03"]:
        return True

    sql = f"""
        SELECT Content FROM caseextend
        WHERE
            CaseKey = {case_key} AND
            ExtendType = "醫囑"
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return False
    else:
        return True


# 檢查特定格式有自費金額才印
def check_total_fee(database, case_key, form):
    if form is None:
        return True

    form_no = form.split("-")[0]
    if form_no not in ["01", "02", "10"]:
        return True

    sql = f"""
        SELECT TotalFee FROM cases
        WHERE
            CaseKey = {case_key}
    """

    rows = database.select_record(sql)
    if len(rows) <= 0:
        return True

    row = rows[0]
    total_fee = number_utils.get_integer(row["TotalFee"])

    if form_no in ["10"] and total_fee < 250:  # 印花稅收據
        return False
    elif total_fee > 0:
        return True
    else:
        return False


# 檢查特定格式有藥才印
def check_pres_days(database, case_key, medicine_set, form):
    if form is None:
        return True

    form_no = form.split("-")[0]
    if form_no not in ["09"]:
        return True

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    if pres_days > 0:
        return True
    else:
        return False


# 列印其他收據
def print_misc(
    parent, database, system_settings, case_key, print_type, print_option="系統設定"
):
    form = system_settings.field("其他收據格式")
    if form is None:
        return

    printable = system_settings.field("列印其他收據")
    print_type = "print"

    form_no = string_utils.xstr(form.split("-")[0])
    if form_no in ["30"]:  # Form30: 領藥單
        sql = f"""
            SELECT DrugNo FROM cases
            WHERE
                CaseKey = {case_key} AND
                DrugNo > 0
        """
        rows = database.select_record(sql)
        if len(rows) <= 0:
            return
    elif form_no in [
        "1",
        "2",
        "10",
        "11",
        "12",
        "13",
        "15",
        "16",
    ]:  # Form12, 13 自費費用收據
        total_fee = 0
        sql = f"""
            SELECT TotalFee FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            total_fee = number_utils.get_integer(row["TotalFee"])

        if total_fee <= 0:
            return

    if form_no in [17, 30]:  # 健保及自費印花稅收據, 領藥單不要檢查
        pass
    else:
        if not check_record_count(database, case_key, form):
            return

        if not check_total_fee(database, case_key, form):
            return

        if not check_pres_days(database, case_key, 1, form):  # 檢查是否有健保開藥
            return

    if print_option != "系統設定" and printable == "不印":
        printable = "列印"

    if printable == "不印":
        return
    elif printable == "詢問":
        print_type = "print"

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle(f"列印{form}")
        msg_box.setText(f"<font size='4' color='red'><b>是否列印 {form}?</b></font>")
        msg_box.setInformativeText(
            f"<font size='4'>注意！{form}將會列印至系統設定的印表機.</font>"
        )
        msg_box.addButton(QPushButton("否"), QMessageBox.NoRole)  # 0
        msg_box.addButton(QPushButton("是"), QMessageBox.AcceptRole)  # 1

        printing = msg_box.exec_()
        if not printing:
            return

    elif printable == "預覽":
        print_type = "preview"
    elif printable == "列印":
        print_type = "print"

    print_misc_form = get_print_misc_form(form)
    if print_misc_form is None:
        return

    printer = get_printer(system_settings, "其他收據印表機")
    print_form = print_misc_form(parent, database, system_settings, case_key, printer)

    if print_type == "print":
        print_form.print()
    else:
        print_form.preview()

    del print_form


# 列印其他收據2
def print_misc2(
    parent, database, system_settings, case_key, print_type, print_option="系統設定"
):
    form = system_settings.field("其他收據2格式")
    if form is None:
        return

    printable = system_settings.field("列印其他收據2")
    print_type = "print"

    if form.split("-")[0] == "12":  # Form12 自費費用收據
        total_fee = 0
        sql = f"""
            SELECT TotalFee FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            total_fee = number_utils.get_integer(row["TotalFee"])

        if total_fee <= 0:
            return

    if not check_record_count(database, case_key, form):
        return

    if not check_total_fee(database, case_key, form):
        return

    if not check_pres_days(database, case_key, 1, form):  # 檢查是否有健保開藥
        return

    if print_option != "系統設定" and printable == "不印":
        printable = "列印"

    if printable == "不印":
        return
    elif printable == "詢問":
        print_type = "print"

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle(f"列印{form}")
        msg_box.setText(f"<font size='4' color='red'><b>是否列印 {form}?</b></font>")
        msg_box.setInformativeText(
            f"<font size='4'>注意！{form}將會列印至系統設定的印表機.</font>"
        )
        msg_box.addButton(QPushButton("否"), QMessageBox.NoRole)  # 0
        msg_box.addButton(QPushButton("是"), QMessageBox.AcceptRole)  # 1

        printing = msg_box.exec_()
        if not printing:
            return

    elif printable == "預覽":
        print_type = "preview"
    elif printable == "列印":
        print_type = "print"

    print_misc_form = get_print_misc_form(form)
    if print_misc_form is None:
        return

    printer = get_printer(system_settings, "其他收據2印表機")
    print_form = print_misc_form(parent, database, system_settings, case_key, printer)

    if print_type == "print":
        print_form.print()
    else:
        print_form.preview()

    del print_form


# 列印其他收據
def print_misc3(
    parent, database, system_settings, case_key, print_type, print_option="系統設定"
):
    form = system_settings.field("其他收據3格式")
    if form is None:
        return

    printable = system_settings.field("列印其他收據3")
    print_type = "print"

    if form.split("-")[0] == "12":  # Form12 自費費用收據
        total_fee = 0
        sql = f"""
            SELECT TotalFee FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            total_fee = number_utils.get_integer(row["TotalFee"])

        if total_fee <= 0:
            return

    if not check_record_count(database, case_key, form):
        return

    if not check_total_fee(database, case_key, form):
        return

    if not check_pres_days(database, case_key, 1, form):  # 檢查是否有健保開藥
        return

    if print_option != "系統設定" and printable == "不印":
        printable = "列印"

    if printable == "不印":
        return
    elif printable == "詢問":
        print_type = "print"

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle(f"列印{form}")
        msg_box.setText(f"<font size='4' color='red'><b>是否列印 {form}?</b></font>")
        msg_box.setInformativeText(
            f"<font size='4'>注意！{form}將會列印至系統設定的印表機.</font>"
        )
        msg_box.addButton(QPushButton("否"), QMessageBox.NoRole)  # 0
        msg_box.addButton(QPushButton("是"), QMessageBox.AcceptRole)  # 1

        printing = msg_box.exec_()
        if not printing:
            return

    elif printable == "預覽":
        print_type = "preview"
    elif printable == "列印":
        print_type = "print"

    print_misc_form = get_print_misc_form(form)
    if print_misc_form is None:
        return

    printer = get_printer(system_settings, "其他收據3印表機")
    print_form = print_misc_form(parent, database, system_settings, case_key, printer)

    if print_type == "print":
        print_form.print()
    else:
        print_form.preview()

    del print_form


# 列印預約單
def print_reservation(
    parent,
    database,
    system_settings,
    reservation_key,
    print_type,
    print_option="系統設定",
):
    form = system_settings.field("預約掛號單格式")
    if form is None:
        return

    printable = system_settings.field("列印預約掛號單")
    print_type = "print"
    if print_option != "系統設定" and printable == "不印":
        printable = "列印"

    if printable == "不印":
        return
    elif printable == "詢問":
        dialog = QtPrintSupport.QPrintDialog()
        if dialog.exec() == QtWidgets.QDialog.Rejected:
            return
    elif printable == "預覽":
        print_type = "preview"
    elif printable == "列印":
        print_type = "print"

    print_reservation_form = get_print_reservation_form(form)
    if print_reservation_form is None:
        return

    print_form = print_reservation_form(
        parent, database, system_settings, reservation_key
    )

    if print_type == "print":
        print_form.print()
    else:
        print_form.preview()

    del print_form


def get_print_ins_apply_total_fee(parent, database, system_settings, ins_total_fee):
    from printer import print_ins_apply_total_fee

    module = importlib.reload(print_ins_apply_total_fee)
    print_module = module.PrintInsApplyTotalFee(
        parent, database, system_settings, ins_total_fee
    )

    return print_module


# 列印申請總表
def print_form_ins_apply_total_fee(
    parent, database, system_settings, ins_total_fee, print_type="print"
):
    if print_type == "pdf":
        pass
    elif system_settings.field("列印報表") == "詢問":
        dialog = QtPrintSupport.QPrintDialog()
        if dialog.exec() == QtWidgets.QDialog.Rejected:
            return
    elif system_settings.field("列印報表") == "預覽":
        print_type = "preview"
    elif system_settings.field("列印報表") == "列印":
        print_type = "print"

    print_form = get_print_ins_apply_total_fee(
        parent, database, system_settings, ins_total_fee
    )

    if print_type == "print":
        print_form.print()
    elif print_type == "preview":
        print_form.preview()
    elif print_type == "pdf":
        print_form.save_to_pdf()

    del print_form


def get_print_html(parent, database, system_settings, html, orientation):
    from printer import print_html

    module = importlib.reload(print_html)
    print_module = module.PrintHtml(
        parent, database, system_settings, html, orientation
    )

    return print_module


# 列印html
def print_form_html(
    parent,
    database,
    system_settings,
    html,
    orientation="portrait",
    print_type="print",
    filename=None,
):
    if print_type == "print":
        if system_settings.field("列印報表") == "詢問":
            dialog = QtPrintSupport.QPrintDialog()
            if dialog.exec() == QtWidgets.QDialog.Rejected:
                return
        elif system_settings.field("列印報表") == "預覽":
            print_type = "preview"
        elif system_settings.field("列印報表") == "列印":
            print_type = "print"

    print_form = get_print_html(parent, database, system_settings, html, orientation)

    if print_type == "print":
        print_form.print()
    elif print_type == "pdf":
        print_form.save_to_pdf(filename)
    else:
        print_form.preview()

    del print_form


def get_print_ins_apply_schedule_table(
    parent, database, system_settings, html, apply_date
):
    from printer import print_ins_apply_schedule_table

    module = importlib.reload(print_ins_apply_schedule_table)
    print_module = module.PrintInsApplyScheduleTable(
        parent, database, system_settings, html, apply_date
    )

    return print_module


# 列印排班表
def print_form_ins_apply_schedule_table(
    parent, database, system_settings, html, apply_date, print_type="print"
):
    if print_type == "pdf":
        pass
    elif system_settings.field("列印報表") == "詢問":
        dialog = QtPrintSupport.QPrintDialog()
        if dialog.exec() == QtWidgets.QDialog.Rejected:
            return
    elif system_settings.field("列印報表") == "預覽":
        print_type = "preview"
    elif system_settings.field("列印報表") == "列印":
        print_type = "print"

    print_form = get_print_ins_apply_schedule_table(
        parent, database, system_settings, html, apply_date
    )

    if print_type == "print":
        print_form.print()
    elif print_type == "preview":
        print_form.preview()
    elif print_type == "pdf":
        print_form.save_to_pdf()

    del print_form


def print_form(system_settings, function_name, print_type=None, form_type=None):
    if print_type is None:  # 如果未指定列印方式，以系統設定為主
        if system_settings.field("列印報表") == "不印":
            return
        elif system_settings.field("列印報表") == "詢問":
            dialog = QtPrintSupport.QPrintDialog()
            if dialog.exec() == QtWidgets.QDialog.Rejected:
                return
        elif system_settings.field("列印報表") == "預覽":
            print_type = "preview"
        elif system_settings.field("列印報表") == "列印":
            print_type = "print"

    if print_type == "print":
        function_name.print()
    elif print_type == "preview":
        function_name.preview()
    elif print_type == "pdf":
        function_name.save_to_pdf()
    elif print_type == "pdf_by_dialog":
        function_name.save_to_pdf_by_dialog()

    del function_name


def get_print_ins_apply_order(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    apply_type,
    ins_apply_key,
):
    from printer import print_ins_apply_order

    module = importlib.reload(print_ins_apply_order)
    print_module = module.PrintInsApplyOrder(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        apply_type,
        ins_apply_key,
    )

    return print_module


# 列印醫令明細
def print_form_ins_apply_order(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    apply_type,
    ins_apply_key,
    print_type=None,
):
    print_ins_apply_order = get_print_ins_apply_order(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        apply_type,
        ins_apply_key,
    )
    print_form(system_settings, print_ins_apply_order, print_type)


def get_print_medical_records(
    parent,
    database,
    system_settings,
    patient_key,
    sql,
    start_date,
    end_date,
    print_self_prescript=False,
    print_treat_item=True,
):
    from printer import print_medical_records

    module = importlib.reload(print_medical_records)
    print_module = module.PrintMedicalRecords(
        parent,
        database,
        system_settings,
        patient_key,
        sql,
        start_date,
        end_date,
        print_self_prescript,
        print_treat_item,
    )

    return print_module


# 列印實體病歷
def print_form_medical_records(
    parent,
    database,
    system_settings,
    patient_key,
    sql,
    start_date,
    end_date,
    print_type=None,
    print_self_prescript=False,
    print_treat_item=True,
):
    print_medical_records = get_print_medical_records(
        parent,
        database,
        system_settings,
        patient_key,
        sql,
        start_date,
        end_date,
        print_self_prescript,
        print_treat_item,
    )
    print_form(system_settings, print_medical_records, print_type)


def get_print_referral_form(parent, database, system_settings, patient_key, case_key):
    from printer import print_referral_form

    module = importlib.reload(print_referral_form)
    print_module = module.PrintReferralForm(
        parent, database, system_settings, patient_key, case_key
    )

    return print_module


# 列印轉診單
def print_referral_form(
    parent, database, system_settings, patient_key, case_key, print_type
):
    print_referral = get_print_referral_form(
        parent, database, system_settings, patient_key, case_key
    )
    print_form(system_settings, print_referral, print_type)


def get_print_medical_fees(parent, database, system_settings, patient_key, sql):
    from printer import print_medical_fees

    module = importlib.reload(print_medical_fees)
    print_module = module.PrintMedicalFees(
        parent,
        database,
        system_settings,
        patient_key,
        sql,
    )

    return print_module


def get_print_medical_certificate(parent, database, system_settings, case_key):
    from printer import print_medical_certificate

    module = importlib.reload(print_medical_certificate)
    print_module = module.PrintMedicalFees(parent, database, system_settings, case_key)

    return print_module


# 列印收費明細
def print_form_medical_fees(
    parent, database, system_settings, patient_key, sql, print_type=None
):
    print_medical_fees = get_print_medical_fees(
        parent,
        database,
        system_settings,
        patient_key,
        sql,
    )
    print_form(system_settings, print_medical_fees, print_type)


def get_print_medical_chart(parent, database, system_settings, patient_key, apply_date):
    from printer import print_medical_chart

    module = importlib.reload(print_medical_chart)
    print_module = module.PrintMedicalChart(
        parent,
        database,
        system_settings,
        patient_key,
        apply_date,
    )

    return print_module


# 列印就醫證明
def print_form_medical_certificate(
    parent, database, system_settings, case_key, print_type=None
):
    print_medical_certificate = get_print_medical_certificate(
        parent,
        database,
        system_settings,
        case_key,
    )
    print_form(system_settings, print_medical_certificate, print_type)


# 列印雙月病歷首頁
def print_form_medical_chart(
    parent, database, system_settings, patient_key, apply_date, print_type=None
):
    print_medical_chart = get_print_medical_chart(
        parent,
        database,
        system_settings,
        patient_key,
        apply_date,
    )
    print_form(system_settings, print_medical_chart, print_type)


def get_print_simple_medical_chart(parent, database, system_settings, patient_key):
    from printer import print_simple_medical_chart

    module = importlib.reload(print_simple_medical_chart)
    print_module = module.PrintSimpleMedicalChart(
        parent, database, system_settings, patient_key
    )

    return print_module


# 列印簡易病歷首頁
def print_form_simple_medical_chart(
    parent, database, system_settings, patient_key, print_type=None
):
    print_simple_medical_chart = get_print_simple_medical_chart(
        parent, database, system_settings, patient_key
    )
    print_form(system_settings, print_simple_medical_chart, print_type)


def get_print_patient_new_care(
    parent, database, system_settings, patient_key, case_key, apply_date
):
    from printer import print_patient_new_care

    module = importlib.reload(print_patient_new_care)
    print_module = module.PrintPatientNewCare(
        parent,
        database,
        system_settings,
        patient_key,
        case_key,
        apply_date,
    )

    return print_module


# 列印初診照護病歷
def print_form_patient_new_care(
    parent,
    database,
    system_settings,
    patient_key,
    case_key,
    apply_date,
    print_type=None,
):
    print_patient_new_care = get_print_patient_new_care(
        parent,
        database,
        system_settings,
        patient_key,
        case_key,
        apply_date,
    )
    print_form(system_settings, print_patient_new_care, print_type)


def get_print_diagnosis_proof(
    parent, database, system_settings, certificate_key, title
):
    from printer import print_diagnosis_proof

    module = importlib.reload(print_diagnosis_proof)
    print_module = module.PrintDiagnosisProof(
        parent, database, system_settings, certificate_key, title
    )

    return print_module


# 列印就醫證明書
def print_form_diagnosis_proof(
    parent, database, system_settings, certificate_key, title, print_type=None
):
    print_diagnosis_proof = get_print_diagnosis_proof(
        parent, database, system_settings, certificate_key, title
    )
    print_form(system_settings, print_diagnosis_proof, print_type)


def get_print_certificate_diagnosis(
    parent, database, system_settings, certificate_key, title
):
    from printer import print_certificate_diagnosis

    module = importlib.reload(print_certificate_diagnosis)
    print_module = module.PrintCertificateDiagnosis(
        parent, database, system_settings, certificate_key, title
    )

    return print_module


# 列印診斷證明書
def print_form_certificate_diagnosis(
    parent, database, system_settings, certificate_key, title, print_type=None
):
    print_certificate_diagnosis = get_print_certificate_diagnosis(
        parent, database, system_settings, certificate_key, title
    )
    print_form(system_settings, print_certificate_diagnosis, print_type)


def get_print_certificate_payment(
    parent, database, system_settings, certificate_key, show_tax_declare
):
    from printer import print_certificate_payment

    module = importlib.reload(print_certificate_payment)
    print_module = module.PrintCertificatePayment(
        parent,
        database,
        system_settings,
        certificate_key,
        show_tax_declare,
    )

    return print_module


# 列印醫療費用證明書明細
def print_form_certificate_payment(
    parent,
    database,
    system_settings,
    certificate_key,
    show_tax_declare,
    print_type=None,
):
    print_certificate_payment = get_print_certificate_payment(
        parent, database, system_settings, certificate_key, show_tax_declare
    )
    print_form(system_settings, print_certificate_payment, print_type)


def get_print_certificate_cash_payment(
    parent, database, system_settings, certificate_key
):
    from printer import print_certificate_cash_payment

    module = importlib.reload(print_certificate_cash_payment)
    print_module = module.PrintCertificateCashPayment(
        parent, database, system_settings, certificate_key
    )

    return print_module


def get_print_certificate_cash_payment2(
    parent, database, system_settings, certificate_key, form_type=None
):
    from printer import print_certificate_cash_payment2

    module = importlib.reload(print_certificate_cash_payment2)
    print_module = module.PrintCertificateCashPayment2(
        parent, database, system_settings, certificate_key, form_type
    )

    return print_module


def get_print_certificate_ins_fee(parent, database, system_settings, certificate_key):
    from printer import print_certificate_ins_fee

    module = importlib.reload(print_certificate_ins_fee)
    print_module = module.PrintCertificateInsFee(
        parent, database, system_settings, certificate_key
    )

    return print_module


# 列印健保醫療費用證明書明細
def print_form_certificate_ins_fee(
    parent, database, system_settings, certificate_key, print_type=None
):
    print_certificate_payment = get_print_certificate_ins_fee(
        parent, database, system_settings, certificate_key
    )
    print_form(system_settings, print_certificate_payment, print_type)


# 列印醫療費用證明書明細
def print_form_certificate_cash_payment(
    parent, database, system_settings, certificate_key, print_type=None
):
    print_certificate_cash_payment = get_print_certificate_cash_payment(
        parent, database, system_settings, certificate_key
    )
    print_form(system_settings, print_certificate_cash_payment, print_type)


# 列印醫療費用證明書明細2
def print_form_certificate_cash_payment2(
    parent, database, system_settings, certificate_key, print_type=None, form_type=None
):
    print_certificate_cash_payment2 = get_print_certificate_cash_payment2(
        parent, database, system_settings, certificate_key, form_type
    )
    print_form(system_settings, print_certificate_cash_payment2, print_type)


def get_print_certificate_payment_total(
    parent, database, system_settings, certificate_key, print_ins_fee
):
    from printer import print_certificate_payment_total

    module = importlib.reload(print_certificate_payment_total)
    print_module = module.PrintCertificatePaymentTotal(
        parent, database, system_settings, certificate_key, print_ins_fee
    )

    return print_module


# 列印醫療費用證明書總表
def print_form_certificate_total(
    parent,
    database,
    system_settings,
    certificate_key,
    print_type=None,
    print_ins_fee=True,
):
    print_certificate_payment_total = get_print_certificate_payment_total(
        parent, database, system_settings, certificate_key, print_ins_fee
    )
    print_form(system_settings, print_certificate_payment_total, print_type)


def get_print_certificate_payment_receipt(
    parent, database, system_settings, certificate_key
):
    from printer import print_certificate_payment_receipt

    module = importlib.reload(print_certificate_payment_receipt)
    print_module = module.PrintCertificatePaymentReceipt(
        parent, database, system_settings, certificate_key
    )

    return print_module


# 列印醫療費用收據 2022.09.05 星光
def print_form_certificate_receipt(
    parent,
    database,
    system_settings,
    certificate_key,
    print_type=None,
    print_ins_fee=True,
):
    print_certificate_payment_receipt = get_print_certificate_payment_receipt(
        parent, database, system_settings, certificate_key
    )
    print_form(system_settings, print_certificate_payment_receipt, print_type)


def get_print_certificate_payment_prescript(
    parent, database, system_settings, certificate_key, form_type
):
    from printer import print_certificate_payment_prescript

    module = importlib.reload(print_certificate_payment_prescript)
    print_module = module.PrintCertificatePaymentPrescript(
        parent, database, system_settings, certificate_key, form_type
    )

    return print_module


# 列印醫療費用證明書處方明細
def print_form_certificate_prescript(
    parent, database, system_settings, certificate_key, form_type=None
):
    print_certificate_payment_prescript = get_print_certificate_payment_prescript(
        parent,
        database,
        system_settings,
        certificate_key,
        form_type,
    )
    print_form(
        system_settings, print_certificate_payment_prescript, form_type=form_type
    )


def get_print_certificate_payment_self_prescript(
    parent, database, system_settings, certificate_key
):
    from printer import print_certificate_payment_self_prescript

    module = importlib.reload(print_certificate_payment_self_prescript)
    print_module = module.PrintCertificatePaymentSelfPrescript(
        parent, database, system_settings, certificate_key
    )

    return print_module


# 列印醫療費用證明書自費處方明細
def print_form_certificate_self_prescript(
    parent, database, system_settings, certificate_key, print_type=None
):
    print_certificate_payment_self_prescript = (
        get_print_certificate_payment_self_prescript(
            parent,
            database,
            system_settings,
            certificate_key,
        )
    )
    print_form(system_settings, print_certificate_payment_self_prescript, print_type)


def get_prescript_count(database, case_key, medicine_set):
    if medicine_set == 1:
        medicine_type_script = (
            'MedicineSet = 1 AND MedicineType NOT IN ("穴道", "處置", "檢驗") '
        )
    else:
        medicine_type_script = (
            'MedicineSet >= 2 AND MedicineType NOT IN ("穴道", "處置", "檢驗") '
        )

    sql = f"""
        SELECT PrescriptKey FROM prescript
        WHERE
            CaseKey = {case_key} AND
            {medicine_type_script}
    """

    try:
        rows = database.select_record(sql)
        prescript_count = len(rows)
    except Exception:
        prescript_count = 0

    return prescript_count


def get_additional_label(additional):
    if additional is None:
        additional_label = ""
    else:
        additional_label = f"<br><b>「{additional}」</b>"

    return additional_label


def get_case_key_barcode(case_key):
    case_key_str = f"{case_key:0>8}"
    case_key_barcode = f"{string_utils.barcode_128a(case_key_str)}"

    return case_key_barcode


def get_barcode(barcode_string):
    barcode = f"{string_utils.barcode_128a(barcode_string)}"

    return barcode


def set_document_line_height(document, height):
    it = document.begin()
    while it != document.end():
        it = it.next()
        cursor = QtGui.QTextCursor(it)
        tbf = it.blockFormat()

        tbf.setLineHeight(height, QtGui.QTextBlockFormat.FixedHeight)
        cursor.setBlockFormat(tbf)


def get_print_correction_area_income_list(
    parent, database, system_settings, table_widget_medical_record_list, column_name
):
    from printer import print_correction_area_income_list

    module = importlib.reload(print_correction_area_income_list)
    print_module = module.PrintCorrectionAreaReservationList(
        parent, database, system_settings, table_widget_medical_record_list, column_name
    )

    return print_module


def print_correction_reg_income(
    parent,
    database,
    system_settings,
    table_widget_medical_record_list,
    column_name,
    print_type=None,
):
    print_correction_area_incom_list = get_print_correction_area_income_list(
        parent, database, system_settings, table_widget_medical_record_list, column_name
    )
    print_form(system_settings, print_correction_area_incom_list, print_type)


def get_print_ins_regist_fee_discount(
    parent, database, system_settings, start_date, end_date, table_widget_medical_record
):
    from printer import print_ins_regist_fee_discount

    module = importlib.reload(print_ins_regist_fee_discount)
    print_module = module.PrintInsRegistFeeDiscount(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        table_widget_medical_record,
    )

    return print_module


# 列印門診優惠名單
def print_regist_fee_discount(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    table_widget_medical_record,
    print_type=None,
):
    print_ins_regist_fee_discount = get_print_ins_regist_fee_discount(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        table_widget_medical_record,
    )
    print_form(system_settings, print_ins_regist_fee_discount)


def get_print_income(
    parent,
    database,
    system_settings,
    orientation,
    income_date,
    income_period,
    tableWidget_income,
    tableWidget_total,
    income_list_columns,
):
    from printer import print_income

    module = importlib.reload(print_income)
    print_module = module.PrintIncome(
        parent,
        database,
        system_settings,
        orientation,
        income_date,
        income_period,
        tableWidget_income,
        tableWidget_total,
        income_list_columns,
    )

    return print_module


# 掛號櫃台結帳直式日報表1
def print_income(
    parent,
    database,
    system_settings,
    orientation,
    income_date,
    income_period,
    tableWidget_income,
    tableWidget_total,
    income_list_columns,
    print_type=None,
):
    print_income = get_print_income(
        parent,
        database,
        system_settings,
        orientation,
        income_date,
        income_period,
        tableWidget_income,
        tableWidget_total,
        income_list_columns,
    )
    print_form(system_settings, print_income, print_type)


def get_print_income2(
    parent,
    database,
    system_settings,
    orientation,
    tab_income_cash_flow,
    tab_income_list,
    income_list_columns,
):
    from printer import print_income2

    module = importlib.reload(print_income2)
    print_module = module.PrintIncome2(
        parent,
        database,
        system_settings,
        orientation,
        tab_income_cash_flow,
        tab_income_list,
        income_list_columns,
    )

    return print_module


# 掛號櫃台結帳直式日報表1
def print_income2(
    parent,
    database,
    system_settings,
    orientation,
    tab_income_cash_flow,
    tab_income_list,
    income_list_columns,
    print_type=None,
):
    print_income2 = get_print_income2(
        parent,
        database,
        system_settings,
        orientation,
        tab_income_cash_flow,
        tab_income_list,
        income_list_columns,
    )
    print_form(system_settings, print_income2, print_type)


def get_print_income_ins_list(
    parent,
    database,
    system_settings,
    start_date,
    period,
    tableWidget_income,
    tableWidget_free_count,
    tableWidget_summary,
):
    from printer import print_income_ins_list

    module = importlib.reload(print_income_ins_list)
    print_module = module.PrintIncomeInsList(
        parent,
        database,
        system_settings,
        start_date,
        period,
        tableWidget_income,
        tableWidget_free_count,
        tableWidget_summary,
    )

    return print_module


# 掛號櫃台健保收費明細
def print_income_ins_list(
    parent,
    database,
    system_settings,
    start_date,
    period,
    tableWidget_income,
    tableWidget_free_count,
    tableWidget_summary,
    print_type=None,
):
    print_income_ins_list = get_print_income_ins_list(
        parent,
        database,
        system_settings,
        start_date,
        period,
        tableWidget_income,
        tableWidget_free_count,
        tableWidget_summary,
    )
    print_form(system_settings, print_income_ins_list, print_type)


# 列印預約名單
def get_print_reservation_list(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    doctor,
    tableWidget_reservation_list,
):
    from printer import print_reservation_list

    module = importlib.reload(print_reservation_list)
    print_module = module.PrintReservationList(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        doctor,
        tableWidget_reservation_list,
    )

    return print_module


# 列印預約名單
def print_reservation_list(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    doctor,
    tableWidget_reservation_list,
    print_type=None,
):
    print_reserve_list = get_print_reservation_list(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        doctor,
        tableWidget_reservation_list,
    )
    print_form(system_settings, print_reserve_list, print_type)


# 列印矯正機關內門診預約名單
def get_print_correction_area_reservation_list(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    doctor,
    tableWidget_reservation_list,
):
    from printer import print_correction_area_reservation_list

    module = importlib.reload(print_correction_area_reservation_list)
    print_module = module.PrintCorrectionAreaReservationList(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        doctor,
        tableWidget_reservation_list,
    )

    return print_module


# 列印矯正機關內門診預約名單
def print_correction_area_reservation_list(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    doctor,
    tableWidget_reservation_list,
    print_type=None,
):
    print_correction_reservation_list = get_print_correction_area_reservation_list(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        doctor,
        tableWidget_reservation_list,
    )
    print_form(system_settings, print_correction_reservation_list, print_type)


# 自費管理-自費銷售記錄-列印自費銷售記錄
def get_print_purchase_list(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    tableWidget_self_prescript,
    tableWidget_self_prescript_agent,
    no_zero_bonus,
):
    from printer import print_purchase_list

    module = importlib.reload(print_purchase_list)
    print_module = module.PrintPurchaseList(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        tableWidget_self_prescript,
        tableWidget_self_prescript_agent,
        no_zero_bonus,
    )

    return print_module


# 自費管理-自費銷售記錄-列印自費銷售記錄
def print_purchase_list(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    tableWidget_self_prescript,
    tableWidget_self_prescript_agent=None,
    print_type=None,
    no_zero_bonus=False,
):
    print_list = get_print_purchase_list(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        tableWidget_self_prescript,
        tableWidget_self_prescript_agent,
        no_zero_bonus,
    )
    print_form(system_settings, print_list, print_type)


# 自費管理-自費銷售記錄-列印自費銷售總表
def get_print_seller(
    parent, database, system_settings, start_date, end_date, tableWidget_seller
):
    from printer import print_seller

    module = importlib.reload(print_seller)
    print_module = module.PrintSeller(
        parent, database, system_settings, start_date, end_date, tableWidget_seller
    )

    return print_module


# 自費管理-自費銷售記錄-列印自費銷售總表
def print_seller(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    tableWidget_seller,
    print_type=None,
):
    print_seller = get_print_seller(
        parent, database, system_settings, start_date, end_date, tableWidget_seller
    )
    print_form(system_settings, print_seller, print_type)


# 自費管理-自費銷售抽成總表-列印
def get_print_doctor_sale_summary(
    parent, database, system_settings, start_date, end_date, tableWidget_prescript
):
    from printer import print_doctor_sale_summary

    module = importlib.reload(print_doctor_sale_summary)
    print_module = module.PrintDoctorSaleSummary(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        tableWidget_prescript,
    )

    return print_module


# 自費管理-自費銷售抽成總表-列印
def print_doctor_sale_summary(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    tableWidget_prescript,
    print_type=None,
):
    print_list = get_print_doctor_sale_summary(
        parent, database, system_settings, start_date, end_date, tableWidget_prescript
    )
    print_form(system_settings, print_list, print_type)


# 醫師統計-門診收入總覽-列印
def get_print_doctor_summary(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    doctor,
    tableWidget_doctor_summary,
):
    from printer import print_doctor_summary

    module = importlib.reload(print_doctor_summary)
    print_module = module.PrintDoctorSummary(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        doctor,
        tableWidget_doctor_summary,
    )

    return print_module


# 醫師統計-門診收入總覽-列印
def print_doctor_summary(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    doctor,
    tableWidget_doctor_summary,
    print_type=None,
):
    print_list = get_print_doctor_summary(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        doctor,
        tableWidget_doctor_summary,
    )
    print_form(system_settings, print_list, print_type)


# 醫師月報表-收入統計-列印
def get_print_doctor_monthly_income(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    doctor,
    tableWidget_doctor_monthly,
):
    from printer import print_doctor_monthly_income

    module = importlib.reload(print_doctor_monthly_income)
    print_module = module.PrintDoctorMonthlyIncome(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        doctor,
        tableWidget_doctor_monthly,
    )

    return print_module


# 醫師月報表-收入統計-列印
def print_doctor_monthly_income(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    doctor,
    tableWidget_doctor_monthly,
    print_type=None,
):
    print_list = get_print_doctor_monthly_income(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        doctor,
        tableWidget_doctor_monthly,
    )
    print_form(system_settings, print_list, print_type)


# 列印業績成長-年度收入統計
def get_print_growth_income(parent, database, system_settings, tableWidget_income_list):
    from printer import print_growth_income

    module = importlib.reload(print_growth_income)
    print_module = module.PrintGrowthIncome(
        parent, database, system_settings, tableWidget_income_list
    )

    return print_module


# 列印業績成長-年度收入統計
def print_growth_income(
    parent, database, system_settings, tableWidget_income_list, print_type=None
):
    print_income = get_print_growth_income(
        parent, database, system_settings, tableWidget_income_list
    )
    print_form(system_settings, print_income, print_type)


# 天地精進格式使用
def get_case_html_10(
    database,
    case_key,
    ins_type,
    medicine_set,
    birthday_mask=True,
    id_mask=True,
    tw_date=True,
    background_color=None,
):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    if birthday is not None:
        if birthday_mask:
            birthday = string_utils.xstr(
                date_utils.west_date_to_nhi_date(row["Birthday"], "-")
            )
            birthday = birthday[:7] + "**"
        elif tw_date:
            birthday = string_utils.xstr(
                date_utils.west_date_to_nhi_date(row["Birthday"], "-")
            )

    patient_id = row["ID"]
    if patient_id is not None and id_mask:
        patient_id = patient_id[:6] + "****"

    # if background_color is not None:
    #     color = f' style="background-color: {background_color}"'
    # else:
    #     color = ''

    patient_key = get_patient_key(row)
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    birthday_str = string_utils.xstr(birthday)
    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    if tw_date:
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"], "-")

    patient_key_header = get_patient_key_header(row, "病號")
    share_type = string_utils.xstr(row["Share"])[:4]

    html = f"""
        <tr>
            <td>姓名:{name}({gender})</td>
            <td>生日:{birthday_str}</td>
        </tr>
    """
    if ins_type == "健保":
        medicine_set = ""
        html += f"""
            <tr>
              <td>證號:{patient_id}</td>
              <td>卡序:{card}</td>
            </tr>
        """
    else:
        medicine_set = f"({medicine_set - 1})"
        share_type = ""

    html += f"""
        <tr>
          <td>保險:{ins_type} {medicine_set} {share_type}</td>
          <td>診日:{case_date}</td>
        </tr>
    """

    return html


def get_prescript_html23(
    database,
    system_setting,
    case_key,
    medicine_set,
    print_type,
    blocks,
    max_length=None,
    instruction=None,
    print_total_dosage=None,
    print_treat_item=True,
    print_dosage=True,
):
    if medicine_set is None:
        prescript = """
            <tr>
              <td>無處方</td>
            </tr>
            <hr>
        """
        return prescript

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    if pres_days <= 0 and instruction == "健保另包":
        return ""

    treatment, treat_type = None, None
    sql = f"""
        SELECT Treatment, TreatType FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)
    if rows:
        treatment = rows[0]["Treatment"]
        treat_type = rows[0]["TreatType"]

    treat_condition = ""
    if (
        print_type == "費用收據"
        and system_setting.field("列印穴道處置") == "N"
        and medicine_set == 1
    ) or (print_type == "過去病歷" and not print_treat_item):
        treat_condition = ' AND (prescript.MedicineType NOT IN ("穴道", "處置")) '

    medicine_set_condition = f" AND (MedicineSet = {medicine_set}) "
    medicine_type_condition = ""
    if instruction == "健保檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NOT NULL) AND
            (LENGTH(prescript.InsCode) > 0)
        """
    elif instruction == "自費檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NULL OR prescript.InsCode = "" OR LENGTH(prescript.InsCode) = 0)
        """

    instruction_condition = get_instruction_condition(
        database, system_setting, case_key, medicine_set, instruction
    )
    order_script = "ORDER BY PrescriptNo, PrescriptKey"

    if system_setting.field("列印處方依照存放位置排序") == "Y":
        if system_setting.field("列印科中處方依照存放位置排序") == "Y":
            order_script = """
                ORDER BY
                    -- 第一階段：判斷是否為「單方」或「複方」並套用 Location 排序邏輯
                    CASE 
                        WHEN medicine.MedicineType IN ('單方', '複方') THEN SUBSTRING(medicine.Location, 1, 1)
                        ELSE '0' -- 非目標類型的第一排序權重設為相同
                    END,
                    CASE 
                        WHEN medicine.MedicineType IN ('單方', '複方') THEN LENGTH(SUBSTRING(medicine.Location, 2))
                        ELSE 0
                    END,
                    CASE 
                        WHEN medicine.MedicineType IN ('單方', '複方') THEN SUBSTRING(medicine.Location, 2)
                        ELSE ''
                    END,

                    -- 第二階段：如果第一階段權重相同（即非單方、複方），則依照 PrescriptKey 排序
                    PrescriptKey ASC
            """
        else:
            order_script = """
                ORDER BY
                    SUBSTRING(medicine.Location, 1, 1),
                    LENGTH(SUBSTRING(medicine.Location, 2)),
                    SUBSTRING(medicine.Location, 2)
            """

    sql = f"""
        SELECT prescript.*, medicine.Location, medicine.MedicineAlias FROM prescript
            LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
        WHERE
            CaseKey = {case_key} AND
            (prescript.MedicineName IS NOT NULL AND LENGTH(prescript.MedicineName) > 0)
            {medicine_set_condition}
            {medicine_type_condition}
            {treat_condition}
            {instruction_condition}
            {order_script}
            """
    rows = database.select_record(sql)

    if (
        medicine_set == 1
        and treatment in nhi_utils.INS_TREAT
        and instruction not in ["健保另包", "健保檢驗", "自費檢驗"]
    ):
        if treatment in nhi_utils.ACUPUNCTURE_TREAT:
            medicine_type = "穴道"
        else:
            medicine_type = "處置"

        rows.insert(
            0,
            {
                "MedicineName": treatment,
                "MedicineAlias": treatment,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Instruction": "",
                "Unit": "次",
                "Location": "",
            },
        )

    if medicine_set == 1 and treat_type == "醫療諮詢":
        medicine_type = "單方"
        rows.insert(
            0,
            {
                "MedicineName": treat_type,
                "MedicineAlias": treat_type,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Instruction": "",
                "Unit": "次",
                "Location": "",
            },
        )

    if len(rows) <= 0:
        return ""

    if pres_days is None or pres_days <= 0:
        pres_days = 1

    if print_total_dosage is None:
        print_total_dosage = system_setting.field("處方箋列印總量")

    print_alias = system_setting.field("列印處方別名")
    if print_type == "處方箋":
        print_alias = "N"

    print_location = system_setting.field("列印藥品存放位置")
    print_location_before_medicine = system_setting.field(
        "列印藥品存放位置在處方名稱前面"
    )

    if print_total_dosage == "Y":
        block_width = {
            3: {
                "medicine_name_width": 15,
                "dosage_width": 6,
                "total_dosage_width": 5,
                "separator_width": 1,
            },
            2: {
                "medicine_name_width": 26,
                "dosage_width": 10,
                "total_dosage_width": 9,
                "separator_width": 1,
            },
            1: {
                "medicine_name_width": 55,
                "dosage_width": 20,
                "total_dosage_width": 20,
                "separator_width": 4,
            },
        }
    else:
        block_width = {
            3: {
                "medicine_name_width": 20,
                "dosage_width": 8,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
            2: {
                "medicine_name_width": 35,
                "dosage_width": 10,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
            1: {
                "medicine_name_width": 55,
                "dosage_width": 20,
                "total_dosage_width": 20,
                "separator_width": 4,
            },
        }

    if system_setting.field("處方列印方向") == "垂直列印":
        rows = set_vertical_direction(rows)

    prescript = ""
    row_count = int((len(rows) - 1) / blocks) + 1
    sequence = 0
    print_package = system_setting.field("自費處方次劑量")
    if print_package == "Y":
        by_packages = True
    else:
        by_packages = False

    for row_no in range(1, row_count + 1):
        separator = ""
        prescript_line = ""
        for i in range(blocks):
            prescript_block = get_medicine_detail(
                medicine_set,
                rows,
                (row_no - 1) * blocks + i,
                pres_days,
                packages,
                print_alias,
                by_packages=by_packages,
            )

            medicine_name = string_utils.xstr(prescript_block[0])
            unit = string_utils.xstr(prescript_block[3])
            medicine_type = string_utils.xstr(prescript_block[7])

            if instruction == "健保檢驗":
                ins_code = string_utils.xstr(prescript_block[5])
                medicine_name = f"{medicine_name} ({ins_code})"

            if print_location != "Y":
                location = ""
            else:
                location = string_utils.xstr(prescript_block[1])

                try:
                    if medicine_type in ["單方", "複方"]:
                        current_location = prescript_utils.refresh_location(
                            database, medicine_type, medicine_name, unit
                        )
                        if (
                            current_location not in ["", None]
                            and location != current_location
                        ):
                            location = current_location
                except Exception:
                    pass

            if print_location_before_medicine == "Y":
                medicine_name = location + medicine_name
            else:
                medicine_name += location

            dosage = string_utils.xstr(prescript_block[2])
            total_dosage = string_utils.xstr(prescript_block[4])
            unit = string_utils.xstr(prescript_block[3])
            medicine_name_width = block_width[blocks]["medicine_name_width"]
            dosage_width = block_width[blocks]["dosage_width"]
            total_dosage_width = block_width[blocks]["total_dosage_width"]
            separator_width = block_width[blocks]["separator_width"]

            if medicine_name in ["優待", "健保檢驗", "自費檢驗"]:
                total_dosage = ""

            if instruction == "無劑量":
                dosage = ""
                unit = ""
                total_dosage = ""

            seq_str = ""
            if dosage != "":
                sequence += 1
                seq_str = str(sequence)

            if not print_dosage:
                prescript_line += f"""
                    <td align="center" width="10%">{seq_str}</td>
                    <td align="left" width="90%">{medicine_name}</td>
                """
            elif print_total_dosage != "Y":
                prescript_line += f"""
                    <td align="center" width="10%">{seq_str}</td>
                    <td align="left" width="60%">{medicine_name}</td>
                    <td align="right" width="30%">{dosage}{unit}</td>
                """
            else:
                prescript_line += f"""
                    <td align="center" width="10%">{seq_str}</td>
                    <td align="left" width="55%">{medicine_name}</td>
                    <td align="right" width="18%">{dosage}{unit}</td>
                    <td align="right" width="20%">{total_dosage}</td>
                """

        prescript += f"""
            <tr>
              {prescript_line}
            </tr>
        """

    return prescript


def get_prescript_html27(
    database,
    system_setting,
    case_key,
    medicine_set,
    print_type,
    blocks,
    max_length=None,
    instruction=None,
    print_total_dosage=None,
    print_treat_item=True,
):
    if medicine_set is None:
        prescript = """
            <tr>
              <td>無處方</td>
            </tr>
            <hr>
        """
        return prescript

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    if pres_days <= 0 and instruction == "健保另包":
        return ""

    sql = f"""
        SELECT Treatment, TreatType FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    treatment = rows[0]["Treatment"]
    treat_type = rows[0]["TreatType"]

    treat_condition = ""
    if (
        print_type == "費用收據"
        and system_setting.field("列印穴道處置") == "N"
        and medicine_set == 1
    ) or (print_type == "過去病歷" and not print_treat_item):
        treat_condition = ' AND (prescript.MedicineType NOT IN ("穴道", "處置")) '

    medicine_set_condition = f" AND (MedicineSet = {medicine_set}) "
    medicine_type_condition = ""
    if instruction == "健保檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NOT NULL) AND
            (LENGTH(prescript.InsCode) > 0)
        """
    elif instruction == "自費檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NULL OR prescript.InsCode = "" OR LENGTH(prescript.InsCode) = 0)
        """

    instruction_condition = get_instruction_condition(
        database, system_setting, case_key, medicine_set, instruction
    )
    sql = f"""
        SELECT prescript.*, medicine.Location, medicine.MedicineAlias FROM prescript
            LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
        WHERE
            CaseKey = {case_key} AND
            (prescript.MedicineName IS NOT NULL AND LENGTH(prescript.MedicineName) > 0)
            {medicine_set_condition}
            {medicine_type_condition}
            {treat_condition}
            {instruction_condition}
        ORDER BY PrescriptNo, PrescriptKey
    """
    rows = database.select_record(sql)

    if (
        medicine_set == 1
        and treatment in nhi_utils.INS_TREAT
        and instruction not in ["健保另包", "健保檢驗", "自費檢驗"]
    ):
        if treatment in nhi_utils.ACUPUNCTURE_TREAT:
            medicine_type = "穴道"
        else:
            medicine_type = "處置"

        rows.insert(
            0,
            {
                "MedicineName": treatment,
                "MedicineAlias": treatment,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Instruction": "",
                "Unit": "次",
                "Location": "",
            },
        )

    if medicine_set == 1 and treat_type == "醫療諮詢":
        medicine_type = "單方"
        rows.insert(
            0,
            {
                "MedicineName": treat_type,
                "MedicineAlias": treat_type,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Instruction": "",
                "Unit": "次",
                "Location": "",
            },
        )

    if len(rows) <= 0:
        return ""

    if pres_days is None or pres_days <= 0:
        pres_days = 1

    if packages is None or packages <= 0:
        packages = 1

    if print_total_dosage is None:
        print_total_dosage = system_setting.field("處方箋列印總量")

    block1_rows, block2_rows = split_rows_into_blocks(
        rows, num_blocks=blocks, block_size=max_length
    )
    print_location = system_setting.field("列印藥品存放位置")
    print_location_before_medicine = system_setting.field(
        "列印藥品存放位置在處方名稱前面"
    )

    prescript = ""
    for row_no in range(max_length):
        medicine_name_block1 = string_utils.xstr(block1_rows[row_no]["MedicineName"])
        medicine_name_block2 = string_utils.xstr(block2_rows[row_no]["MedicineName"])

        if print_location == "Y":
            if print_location_before_medicine == "Y":
                medicine_name_block1 = (
                    string_utils.xstr(block1_rows[row_no]["Location"])
                    + medicine_name_block1
                )
                medicine_name_block2 = (
                    string_utils.xstr(block2_rows[row_no]["Location"])
                    + medicine_name_block2
                )
            else:
                medicine_name_block1 += string_utils.xstr(
                    block1_rows[row_no]["Location"]
                )
                medicine_name_block2 += string_utils.xstr(
                    block2_rows[row_no]["Location"]
                )

        sequence_block1, dosage_block1, unit_block1, total_dosage_block1 = (
            "",
            "",
            "",
            "",
        )
        dosage1 = block1_rows[row_no]["Dosage"]
        dosage_mode1 = block1_rows[row_no]["DosageMode"]
        medicine_type1 = block1_rows[row_no]["MedicineType"]
        if medicine_name_block1 not in ["", None]:
            sequence_block1 = row_no + 1

        if dosage1 is not None and dosage1 > 0:
            dosage_block1 = number_utils.get_float(block1_rows[row_no]["Dosage"])
            unit_block1 = string_utils.xstr(block1_rows[row_no]["Unit"])
            if medicine_type1 in ["穴道", "處置"]:
                total_dosage_block1 = 1.0
            else:
                total_dosage = block1_rows[row_no]["Dosage"] * pres_days
                if dosage_mode1 == "次劑量":
                    total_dosage *= packages

                total_dosage_block1 = f"{total_dosage:.1f}"

        sequence_block2, dosage_block2, unit_block2, total_dosage_block2 = (
            "",
            "",
            "",
            "",
        )
        dosage2 = block2_rows[row_no]["Dosage"]
        dosage_mode2 = block2_rows[row_no]["DosageMode"]
        medicine_type2 = block2_rows[row_no]["MedicineType"]
        if medicine_name_block2 not in ["", None]:
            sequence_block2 = row_no + max_length + 1

        if dosage2 is not None and dosage2 > 0:
            dosage_block2 = number_utils.get_float(block2_rows[row_no]["Dosage"])
            unit_block2 = string_utils.xstr(block2_rows[row_no]["Unit"])
            if medicine_type2 in ["穴道", "處置"]:
                total_dosage_block2 = 1.0
            else:
                total_dosage = block2_rows[row_no]["Dosage"] * pres_days
                if dosage_mode2 == "次劑量":
                    total_dosage *= packages

                total_dosage_block2 = f"{total_dosage:.1f}"

        if unit_block1 not in ["", None]:
            medicine_name_block1 += f" ({unit_block1})"
        if unit_block2 not in ["", None]:
            medicine_name_block2 += f" ({unit_block2})"

        prescript_line = f"""
            <td align="center" width="5%">{sequence_block1}</td>
            <td align="left" width="32%">{medicine_name_block1}</td>
            <td align="right" width="6%">{dosage_block1}</td>
            <td align="right" width="7%">{total_dosage_block1}</td>
            <td align="center" width="5%">{sequence_block2}</td>
            <td align="left" width="32%">{medicine_name_block2}</td>
            <td align="right" width="6%">{dosage_block2}</td>
            <td align="right" width="7%">{total_dosage_block2}</td>
        """

        prescript += f"""
            <tr>
              {prescript_line}
            </tr>
        """

    return prescript


def get_clinic_name(system_settings):
    if system_settings.field("列印院所名稱") != "Y":
        return ""

    clinic_name = system_settings.field("院所名稱")
    custom_clinic_name = system_settings.field("自訂院所名稱")

    if custom_clinic_name not in ["", None]:
        clinic_name = custom_clinic_name

    return clinic_name


# 健保費用
def get_ins_fees_html_23(database, case_key):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    treat_type = string_utils.xstr(row["TreatType"])

    regist_fee = string_utils.xstr(number_utils.get_integer(row["RegistFee"]))
    diag_share_fee = string_utils.xstr(number_utils.get_integer(row["SDiagShareFee"]))
    drug_share_fee = string_utils.xstr(number_utils.get_integer(row["SDrugShareFee"]))
    # total_share_fee = string_utils.xstr(
    #     number_utils.get_integer(row['SDiagShareFee']) +
    #     number_utils.get_integer(row['SDrugShareFee'])
    # )
    deposit_fee = string_utils.xstr(number_utils.get_integer(row["DepositFee"]))
    total_fee = string_utils.xstr(
        number_utils.get_integer(row["RegistFee"])
        + number_utils.get_integer(row["SDiagShareFee"])
        + number_utils.get_integer(row["SDrugShareFee"])
        + number_utils.get_integer(row["DepositFee"])
    )
    diag_fee = string_utils.xstr(number_utils.get_integer(row["DiagFee"]))
    drug_fee = string_utils.xstr(number_utils.get_integer(row["InterDrugFee"]))
    pharmacy_fee = string_utils.xstr(number_utils.get_integer(row["PharmacyFee"]))
    treat_fee = string_utils.xstr(
        number_utils.get_integer(row["AcupunctureFee"])
        + number_utils.get_integer(row["MassageFee"])
        + number_utils.get_integer(row["DislocateFee"])
    )
    # ins_total_fee = string_utils.xstr(number_utils.get_integer(row['InsTotalFee']))
    ins_total_fee = string_utils.xstr(number_utils.get_integer(row["InsTotalFee"]))
    ins_apply_fee = string_utils.xstr(number_utils.get_integer(row["InsApplyFee"]))

    massage_fee = number_utils.get_integer(row["SMassageFee"])

    if treat_type in nhi_utils.HOME_CARE and massage_fee > 0:
        label_traffic_allowanc = "代收費"
        traffic_allowance_fee = string_utils.xstr(massage_fee)
        total_fee = string_utils.xstr(number_utils.get_integer(total_fee) + massage_fee)
    else:
        label_traffic_allowanc = ""
        traffic_allowance_fee = ""

    html = f"""
        <tr>
          <td>診察費</td><td align=right>{diag_fee}</td>
          <td width="1%"></td>
          <td>內服藥</td><td align=right>{drug_fee}</td>
          <td width="1%"></td>
          <td>調劑費</td><td align=right>{pharmacy_fee}</td>
        </tr>
        <tr>
          <td>處置費</td><td align=right>{treat_fee}</td>
          <td width="1%"></td>
          <td>健保額</td><td align=right>{ins_total_fee}</td>
          <td width="1%"></td>
          <td>申請額</td><td align=right>{ins_apply_fee}</td>
        </tr>
        <tr>
          <td>掛號費</td><td align=right>{regist_fee}</td>
          <td width="1%"></td>
          <td>診負擔</td><td align=right>{diag_share_fee}</td>
          <td width="1%"></td>
          <td>藥負擔</td><td align=right>{drug_share_fee}</td>
        </tr>
        <tr>
          <td>欠卡費</td><td align=right>{deposit_fee}</td>
          <td width="1%"></td>
          <td>實收額</td><td align=right>{total_fee}</td>
          <td width="1%"></td>
          <td>{label_traffic_allowanc}</td><td align=right>{traffic_allowance_fee}</td>
        </tr>
    """

    return html


# 處方箋格式27使用
def get_case_html_27(
    database,
    case_key,
    medicine_set,
    ins_type,
    background_color=None,
    birthday_mask=False,
    tw_date=False,
    id_mask=True,
):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    # age = ''
    if birthday is not None:
        if birthday_mask:
            birthday = birthday.strftime("%Y-*-*")
        elif tw_date:
            birthday = string_utils.xstr(
                date_utils.west_date_to_nhi_date(row["Birthday"], "-")
            )

    id = row["ID"]
    if id_mask and id is not None:
        id = id[:6] + "****"

    if background_color is not None:
        color = f' style="background-color: {background_color}"'
    else:
        color = ""

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    if tw_date:
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"], "-")

    patient_key = get_patient_key(row)
    patient_key_header = get_patient_key_header(row, "病號")
    name = string_utils.xstr(row["Name"])
    share_type = string_utils.xstr(row["Share"])
    gender = string_utils.xstr(row["Gender"])
    birthday_str = string_utils.xstr(birthday)
    room = string_utils.xstr(row["Room"])
    doctor = string_utils.xstr(row["Doctor"])

    case_start_date = nhi_utils.get_start_date(database, row)
    share_code = nhi_utils.get_share_code(  # 內含2020.10 新制
        database,
        case_start_date,
        string_utils.xstr(row["Share"]),
        string_utils.xstr(row["Treatment"]),
        number_utils.get_integer(row["Continuance"]),
        number_utils.get_integer(row["InterDrugFee"]),
        number_utils.get_integer(row["DiagShareFee"]),
        number_utils.get_integer(row["DrugShareFee"]),
        row,
    )

    if share_type == "基層醫療":
        share_type = "一般民眾"

    if ins_type == "健保":
        html_str = f"""
            <tr>
                <td>病患姓名:{name}</td>
                <td>身份證號:{id}</td>
                <td>病患生日:{birthday_str}</td>
            </tr>
            <tr>
                <td>性別:{gender}</td>
                <td>就醫日期:{case_date}</td>
                <td>就醫身份別:{share_type}</td>
            </tr>
            <tr>
                <td>健保卡就醫序號:{card}</td>
                <td>主治醫師:{doctor}</td>
                <td>病歷號碼:{patient_key:0>9}</td>
            </tr>
        """
    else:
        html_str = f"""
            <tr>
                <td>病患姓名:{name}</td>
                <td>身份證號:{id}</td>
                <td>病患生日:{birthday_str}</td>
            </tr>
            <tr>
                <td>性別:{gender}</td>
                <td>就醫日期:{case_date}</td>
                <td>就醫身份別:{ins_type}</td>
            </tr>
            <tr>
                <td>保險類別:{ins_type}({medicine_set - 1})</td>
                <td>主治醫師:{doctor}</td>
                <td>病歷號碼:{patient_key:0>9}</td>
            </tr>
        """

    return html_str


# 處方箋格式3使用
def get_case_html_23(
    database,
    case_key,
    ins_type,
    background_color=None,
    birthday_mask=True,
    tw_date=False,
    id_mask=True,
):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    # age = ''
    if birthday is not None:
        if birthday_mask:
            birthday = birthday.strftime("%Y-*-*")
        elif tw_date:
            birthday = string_utils.xstr(
                date_utils.west_date_to_nhi_date(row["Birthday"], "-")
            )

    id = row["ID"]
    if id_mask and id is not None:
        id = id[:6] + "****"

    if background_color is not None:
        color = f' style="background-color: {background_color}"'
    else:
        color = ""

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    if tw_date:
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"], "-")

    patient_key = get_patient_key(row)
    patient_key_header = get_patient_key_header(row, "病號")
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    birthday_str = string_utils.xstr(birthday)
    html = f"""
        <tr>
          <td{color} width="50%">診日:{case_date}</td>
          <td width="40%">{patient_key_header}:{patient_key}</td>
        </tr>
        <tr>
            <td>姓名:{name}({gender})</td>
            <td>生日:{birthday_str}</td>
        </tr>
        <tr>
            <td>身證:{id}</td>
            <td>保險:{ins_type}</td>
        </tr>
    """

    share_type = string_utils.xstr(row["Share"])
    if ins_type == "健保":
        html += f"""
            <tr>
              <td>負擔:{share_type}</td>
              <td>卡序:{card}</td>
            </tr>
        """

    return html


# 自費費用
def get_self_fees_html_dynamic(
    database, system_settings, case_key, medicine_set, width=15
):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    regist_fee = number_utils.get_integer(row["RegistFee"])
    ins_type = string_utils.xstr(row["InsType"])
    if ins_type == "健保":
        regist_fee = 0

    diag_fee = number_utils.get_integer(row["SDiagFee"])
    drug_fee = number_utils.get_integer(row["SDrugFee"])
    herb_fee = number_utils.get_integer(row["SHerbFee"])
    expensive_fee = number_utils.get_integer(row["SExpensiveFee"])
    material_fee = number_utils.get_integer(row["SMaterialFee"])

    acupuncture_fee = number_utils.get_integer(row["SAcupunctureFee"])
    massage_fee = number_utils.get_integer(row["SMassageFee"])
    self_total_fee = number_utils.get_integer(row["SelfTotalFee"]) + regist_fee
    discount_fee = number_utils.get_integer(row["DiscountFee"])
    total_fee = number_utils.get_integer(row["TotalFee"]) + regist_fee
    receipt_fee = number_utils.get_integer(row["ReceiptFee"]) + regist_fee

    if (
        system_settings.field("列印所有收費收據費用明細") == "Y"
        and system_settings.field("列印所有收費收據各自金額") == "Y"
    ):
        self_total_fee = number_utils.get_integer(
            case_utils.get_self_total_fee(database, case_key, medicine_set)
        )
        discount_fee = number_utils.get_integer(
            case_utils.get_discount_fee(database, case_key, medicine_set)
        )
        total_fee = number_utils.get_integer(
            case_utils.get_total_fee(database, case_key, medicine_set)
        )

        total_medicine_set = get_total_medicine_set(database, case_key)

        if (
            medicine_set == 2 and total_medicine_set >= 2
        ):  # 自費有兩帖以上, 而且各帖的自費折扣加總不等於總折扣
            this_discount_fee = 0
            for i in range(total_medicine_set):
                current_discount_fee = number_utils.get_integer(
                    case_utils.get_discount_fee(database, case_key, i + 2)
                )
                this_discount_fee += current_discount_fee

            all_discount_fee = number_utils.get_integer(row["DiscountFee"])
            if this_discount_fee != all_discount_fee:
                discount_fee = all_discount_fee - this_discount_fee
                total_fee -= discount_fee

        #     fee1 = number_utils.get_integer(row['SelfTotalFee'])
        #     for i, this_fee in enumerate(fee_list):
        #         if i == 0:
        #             continue

        #         fee1 -= this_fee

        #     if self_total_fee != fee1:
        #         remain = fee1 - self_total_fee
        #         self_total_fee += remain
        #         total_fee += remain

        if (
            total_fee == 0 and total_medicine_set == 1
        ):  # 只開自費1沒有批價，列印自費總批價
            pass
        else:
            diag_fee = 0
            drug_fee = self_total_fee
            herb_fee = 0
            expensive_fee = 0
            acupuncture_fee = 0
            massage_fee = 0
            dislocate_fee = 0
            material_fee = 0
            exam_fee = 0
            receipt_fee = total_fee

        if system_settings.field("不印折扣") == "Y" or discount_fee < 0:
            self_total_fee -= discount_fee

            discount_fee = 0
            diag_fee = 0
            drug_fee = self_total_fee
            herb_fee = 0
            expensive_fee = 0
            acupuncture_fee = 0
            massage_fee = 0
            dislocate_fee = 0
            material_fee = 0
            exam_fee = 0
            receipt_fee = self_total_fee
            total_fee = self_total_fee

        if medicine_set == 2:
            total_fee += regist_fee
            receipt_fee += regist_fee

    fee_list = []

    if (
        system_settings.field("列印所有收費收據費用明細") == "Y"
        and system_settings.field("列印所有收費收據各自金額") == "Y"
        and medicine_set >= 3
    ):  # 自費2 以後都不印
        pass
    elif regist_fee > 0:
        fee_list.append(f"<td>掛號費:</td><td align=right>{regist_fee}</td>")

    if diag_fee > 0:
        fee_list.append(f"<td>診察費:</td><td align=right>{diag_fee}</td>")
    if drug_fee > 0:
        fee_list.append(f"<td>一般藥費:</td><td align=right>{drug_fee}</td>")
    if herb_fee > 0:
        fee_list.append(f"<td>水藥費:</td><td align=right>{herb_fee}</td>")
    if expensive_fee > 0:
        fee_list.append(f"<td>高貴藥費:</td><td align=right>{expensive_fee}</td>")
    if acupuncture_fee > 0:
        fee_list.append(f"<td>針灸費:</td><td align=right>{acupuncture_fee}</td>")
    if massage_fee > 0:
        fee_list.append(f"<td>處置費:</td><td align=right>{massage_fee}</td>")
    if material_fee > 0:
        fee_list.append(f"<td>材料費:</td><td align=right>{material_fee}</td>")

    fee_list.append(f"<td>自費合計:</td><td align=right>{self_total_fee}</td>")

    if discount_fee > 0:
        fee_list.append(f"<td>折扣:</td><td align=right>{discount_fee}</td>")

    fee_list.append(f"<td>應收金額:</td><td align=right>{total_fee}</td>")
    fee_list.append(f"<td>實收金額:</td><td align=right>{receipt_fee}</td>")

    html = ""
    for i, fee in enumerate(fee_list):
        i += 1
        if i % 2 == 1:
            html += "<tr>"

        html += fee
        html += f'<td width="{width}%"></td>'

        if i % 2 == 0:
            html += "</tr>"

    return html


# 自費費用
def get_self_fees_html_dynamic29(
    database, system_settings, case_key, medicine_set, print_cash_fees=False, width=15
):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    regist_fee = number_utils.get_integer(row["RegistFee"])
    diag_share_fee = number_utils.get_integer(row["SDiagShareFee"])
    drug_share_fee = number_utils.get_integer(row["SDrugShareFee"])
    ins_type = string_utils.xstr(row["InsType"])
    if ins_type == "健保" and not print_cash_fees:
        regist_fee = 0

    diag_fee = number_utils.get_integer(row["SDiagFee"])
    drug_fee = number_utils.get_integer(row["SDrugFee"])
    herb_fee = number_utils.get_integer(row["SHerbFee"])
    expensive_fee = number_utils.get_integer(row["SExpensiveFee"])
    material_fee = number_utils.get_integer(row["SMaterialFee"])

    acupuncture_fee = number_utils.get_integer(row["SAcupunctureFee"])
    massage_fee = number_utils.get_integer(row["SMassageFee"])
    self_total_fee = number_utils.get_integer(row["SelfTotalFee"]) + regist_fee
    discount_fee = number_utils.get_integer(row["DiscountFee"])
    total_fee = number_utils.get_integer(row["TotalFee"]) + regist_fee
    receipt_fee = number_utils.get_integer(row["ReceiptFee"]) + regist_fee

    if (
        system_settings.field("列印所有收費收據費用明細") == "Y"
        and system_settings.field("列印所有收費收據各自金額") == "Y"
    ):
        self_total_fee = number_utils.get_integer(
            case_utils.get_self_total_fee(database, case_key, medicine_set)
        )
        discount_fee = number_utils.get_integer(
            case_utils.get_discount_fee(database, case_key, medicine_set)
        )
        total_fee = number_utils.get_integer(
            case_utils.get_total_fee(database, case_key, medicine_set)
        )

        total_medicine_set = get_total_medicine_set(database, case_key)

        if (
            medicine_set == 2 and total_medicine_set >= 2
        ):  # 自費有兩帖以上, 而且各帖的自費折扣加總不等於總折扣
            this_discount_fee = 0
            for i in range(total_medicine_set):
                current_discount_fee = number_utils.get_integer(
                    case_utils.get_discount_fee(database, case_key, i + 2)
                )
                this_discount_fee += current_discount_fee

            all_discount_fee = number_utils.get_integer(row["DiscountFee"])
            if this_discount_fee != all_discount_fee:
                discount_fee = all_discount_fee - this_discount_fee
                total_fee -= discount_fee

        #     fee1 = number_utils.get_integer(row['SelfTotalFee'])
        #     for i, this_fee in enumerate(fee_list):
        #         if i == 0:
        #             continue

        #         fee1 -= this_fee

        #     if self_total_fee != fee1:
        #         remain = fee1 - self_total_fee
        #         self_total_fee += remain
        #         total_fee += remain

        if (
            total_fee == 0 and total_medicine_set == 1
        ):  # 只開自費1沒有批價，列印自費總批價
            pass
        else:
            diag_fee = 0
            drug_fee = self_total_fee
            herb_fee = 0
            expensive_fee = 0
            acupuncture_fee = 0
            massage_fee = 0
            dislocate_fee = 0
            material_fee = 0
            exam_fee = 0
            receipt_fee = total_fee

        if medicine_set == 2:
            total_fee += regist_fee
            receipt_fee += regist_fee

        if system_settings.field("不印折扣") == "Y" or discount_fee < 0:
            self_total_fee -= discount_fee

            discount_fee = 0
            diag_fee = 0
            drug_fee = self_total_fee
            herb_fee = 0
            expensive_fee = 0
            acupuncture_fee = 0
            massage_fee = 0
            dislocate_fee = 0
            material_fee = 0
            exam_fee = 0
            receipt_fee = self_total_fee
            total_fee = self_total_fee

    fee_list = []

    if (
        system_settings.field("列印所有收費收據費用明細") == "Y"
        and system_settings.field("列印所有收費收據各自金額") == "Y"
        and medicine_set >= 3
    ):  # 自費2 以後都不印
        pass
    elif regist_fee > 0:
        fee_list.append(f"<td>掛號費:</td><td align=right>{regist_fee}</td>")

    if diag_fee > 0:
        fee_list.append(f"<td>診察費:</td><td align=right>{diag_fee}</td>")
    if drug_fee > 0:
        fee_list.append(f"<td>一般藥費:</td><td align=right>{drug_fee}</td>")
    if herb_fee > 0:
        fee_list.append(f"<td>水藥費:</td><td align=right>{herb_fee}</td>")
    if expensive_fee > 0:
        fee_list.append(f"<td>高貴藥費:</td><td align=right>{expensive_fee}</td>")
    if acupuncture_fee > 0:
        fee_list.append(f"<td>針灸費:</td><td align=right>{acupuncture_fee}</td>")
    if massage_fee > 0:
        fee_list.append(f"<td>處置費:</td><td align=right>{massage_fee}</td>")
    if material_fee > 0:
        fee_list.append(f"<td>材料費:</td><td align=right>{material_fee}</td>")

    fee_list.append(f"<td>合計:</td><td align=right>{self_total_fee}</td>")

    if discount_fee > 0:
        fee_list.append(f"<td>折扣:</td><td align=right>{discount_fee}</td>")

    fee_list.append(f"<td>應收金額:</td><td align=right>{total_fee}</td>")
    fee_list.append(f"<td>實收金額:</td><td align=right>{receipt_fee}</td>")

    if print_cash_fees:
        fee_list = []
        if regist_fee > 0:
            fee_list.append(f"<td>掛號費:</td><td align=right>{regist_fee}</td>")
        if diag_share_fee > 0:
            fee_list.append(f"<td>門診負擔:</td><td align=right>{diag_share_fee}</td>")
        if drug_share_fee > 0:
            fee_list.append(f"<td>藥品負擔:</td><td align=right>{drug_share_fee}</td>")

        total_fee = number_utils.get_integer(row["TotalFee"])
        if total_fee > 0:
            fee_list.append(f"<td>自費金額:</td><td align=right>{total_fee}</td>")

        cash_total = regist_fee + diag_share_fee + drug_share_fee + total_fee
        fee_list.append(f"<td>合計金額:</td><td align=right>{cash_total}</td>")

    html = "<table>"
    for i, fee in enumerate(fee_list):
        i += 1
        if i % 2 == 1:
            html += "<tr>"

        html += fee
        html += f'<td width="{width}%"></td>'

        if i % 2 == 0:
            html += "</tr>"

    html += "</table>"

    return html


def get_title_image(
    clinic_name, clinic_id, clinic_telephone, clinic_address, title="醫療費用收據"
):
    import os

    base_dir = os.path.abspath(os.path.join(os.path.dirname("__file__")))
    image_file = f"{base_dir}/images/{clinic_name}.jpg"
    if os.path.exists(image_file):
        if title == "門診掛號單":
            br_line = ""
        elif clinic_name in [
            "帖人中醫診所",
            "仲明堂中醫診所",
            "青田中醫診所",
            "明醫中醫診所",
        ]:
            br_line = "<br><br><br><br><br>"
        elif clinic_name in [
            "木林中醫診所",
        ]:
            br_line = "<br><br><br><br><br><br><br><br><br><br><br>"
        elif clinic_name in ["澄美中醫診所", "澄馨中醫診所"]:
            br_line = "<br><br>"
        else:
            br_line = "<br><br><br><br>"

        title_image = f'''
            {br_line}
            <div>
                <center>
                    <img src="{image_file}">
                    <br>
                    代號:{clinic_id}<br>
                    電話:{clinic_telephone}<br>
                    {clinic_address}<br><br>
                    <b><u>{title}</u></b><br>
                </center>
            </div>
        '''
    else:
        title_image = f"""
            <br>
            <div>
                <center>
                    <h3>{clinic_name}</h3>
                    <br>
                    代號:{clinic_id}<br>
                    電話:{clinic_telephone}<br>
                    {clinic_address}<br><br>
                    <b><u>醫療費用收據</u></b><br>
                </center>
            </div>
        """

    return title_image


# 其他收據格式14使用
def get_case_html_14(database, case_key, ins_type, tw_date=True, background_color=None):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]

    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    # age = ''
    if birthday is not None:
        birthday = birthday.strftime("***-%m-%d")
        # age_year, age_month = date_utils.get_age(row['Birthday'], row['CaseDate'])
        # if age_year is None:
        #     age = ''
        # else:
        #     age = f'{age_year}歲'

    id = row["ID"]
    if id is not None:
        id = id[:6] + "****"

    # if background_color is not None:
    #     color = f' style="background-color: {background_color}"'
    # else:
    #     color = ''

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    if tw_date:
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"], "-")

    patient_key = get_patient_key(row)
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    patient_id = string_utils.xstr(id)
    birthday_str = string_utils.xstr(birthday)
    share_type = string_utils.xstr(row["Share"])[:4]
    room = string_utils.xstr(row["Room"])
    treat_type = string_utils.xstr(row["TreatType"])
    ins_type = string_utils.xstr(row["InsType"])
    doctor = string_utils.xstr(row["Doctor"])
    # print_time = date_utils.now_to_str()[:16]

    html = f"""
        <tr>
          <td width="50%">姓名:{name} ({gender})</td>
          <td width="50%">身分證:{patient_id}</td>
        </tr>
        <tr>
          <td>病歷號:{patient_key}</td>
          <td>生日:{birthday_str}</td>
        </tr>
        <tr>
          <td>就診日:{case_date}</td>
          <td>保險:{ins_type}</td>
        </tr>
        <tr>
          <td>身份別:{share_type}</td>
          <td>科別:{treat_type}</td>
        </tr>
        <tr>
          <td>健保卡序:{card}</td>
          <td>診別:{room}診</td>
        </tr>
        <tr>
          <td>醫師:{doctor}</td>
          <td></td>
        </tr>
    """

    return html


# 健保局費用格式
def get_fees_html14(database, case_key, ins_type="健保"):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    registrar = string_utils.xstr(row["Register"])
    # ins_receipt_fee = (number_utils.get_integer(row['RegistFee']) +
    #                    number_utils.get_integer(row['SDiagShareFee']) +
    #                    number_utils.get_integer(row['SDrugShareFee']) +
    #                    number_utils.get_integer(row['DepositFee']))

    regist_fee = number_utils.get_integer(row["RegistFee"])
    diag_share_fee = number_utils.get_integer(row["SDiagShareFee"])
    drug_share_fee = number_utils.get_integer(row["SDrugShareFee"])
    total_share_fee = diag_share_fee + drug_share_fee

    diag_fee = number_utils.get_integer(row["DiagFee"])
    drug_fee = number_utils.get_integer(row["InterDrugFee"])
    pharmacy_fee = number_utils.get_integer(row["PharmacyFee"])
    exam_fee = number_utils.get_integer(row["ExamFee"])
    treat_fee = (
        number_utils.get_integer(row["AcupunctureFee"])
        + number_utils.get_integer(row["MassageFee"])
        + number_utils.get_integer(row["DislocateFee"])
    )
    ins_total_fee = number_utils.get_integer(row["InsTotalFee"])
    s_drug_fee = number_utils.get_integer(row["SDrugFee"])
    herb_fee = number_utils.get_integer(row["SHerbFee"])
    expensive_fee = number_utils.get_integer(row["SExpensiveFee"])
    s_exam_fee = number_utils.get_integer(row["SExamFee"])
    material_fee = number_utils.get_integer(row["SMaterialFee"])

    s_acupuncture_fee = number_utils.get_integer(row["SAcupunctureFee"])
    s_massage_fee = number_utils.get_integer(row["SMassageFee"])
    s_treat_fee = s_acupuncture_fee + s_massage_fee
    discount_fee = number_utils.get_integer(row["DiscountFee"])
    total_fee = number_utils.get_integer(row["TotalFee"])

    if ins_type == "自費":
        regist_fee = 0
        diag_share_fee = 0
        drug_share_fee = 0
        total_share_fee = diag_share_fee + drug_share_fee

        diag_fee = 0
        drug_fee = 0
        pharmacy_fee = 0
        exam_fee = 0
        treat_fee = 0
        ins_total_fee = 0

    self_drug_fee = s_drug_fee + herb_fee + expensive_fee - discount_fee
    self_treat_fee = s_exam_fee + s_treat_fee

    total_cash = regist_fee + total_share_fee + total_fee

    html = f"""
        <tr>
          <td width="32%">診察費</td>
          <td width="18%" align=right>{diag_fee}</td>
          <td width="32%">掛號費</td>
          <td width="18%" align=right>{regist_fee}</td>
        </tr>
        <tr>
          <td>藥費</td>
          <td align=right>{drug_fee}</td>
          <td>基本部分負擔</td>
          <td align=right>{diag_share_fee}</td>
        </tr>
        <tr>
          <td>藥事服務費</td>
          <td align=right>{pharmacy_fee}</td>
          <td>藥品部分負擔</td>
          <td align=right>{drug_share_fee}</td>
        </tr>
        <tr>
          <td>檢驗費</td>
          <td align=right>{exam_fee}</td>
          <td>檢驗處置費</td>
          <td align=right>{self_treat_fee}</td>
        </tr>
        <tr>
          <td>處置手術費</td>
          <td align=right>{treat_fee}</td>
          <td>藥品(自費)</td>
          <td align=right>{self_drug_fee}</td>
        </tr>
        <tr>
          <td>材料費</td>
          <td align=right>0</td>
          <td>衛材(自費)</td>
          <td align=right>{material_fee}</td>
        </tr>
        <tr>
          <td colspan="2">小計: 健保申報 {ins_total_fee}點<br>(健保申報點數非一點一元給付)</td>
          <td colspan="2">小計: 部份負擔金額 {total_share_fee}元<br>其他自費金額: {total_fee}</td>
        </tr>
        <tr>
          <td align="center" colspan="2">應繳金額: {total_cash}元</td>
          <td align=center colspan="2">經手人: {registrar}</td>
        </tr>
    """

    return html


def get_total_medicine_set(database, case_key):
    sql = f"""
        SELECT MedicineSet FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet >= 2
        GROUP BY MedicineSet
    """
    rows = database.select_record(sql)

    return len(rows)


def get_self_prescript_receipt_html(database, system_setting, case_key):
    sql = f"""
        SELECT * FROM prescript
        WHERE
            CaseKey = {case_key} AND
            MedicineSet >= 2 AND
            Price > 0
        ORDER BY MedicineSet, PrescriptNo, PrescriptKey
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    prescript_line = ""
    for row in rows:
        medicine_set = number_utils.get_integer(row["MedicineSet"])
        pres_days = case_utils.get_pres_days(database, case_key, medicine_set)

        dosage = round(number_utils.get_float(row["Dosage"]), 1)
        price = round(number_utils.get_float(row["Price"]), 1)
        amount = dosage * price

        try:
            instruction = int(row["Instruction"])
        except Exception:
            instruction = None

        if pres_days <= 0:
            pres_days = 1

        if instruction is None:
            total_amount = amount * pres_days
        else:
            total_amount = amount * instruction

        medicine_name = string_utils.xstr(row["MedicineName"])
        unit = string_utils.xstr(row["Unit"])
        prescript_line += f"""
            <tr>
                <td align="left" width="50%">{medicine_name}</td>
                <td align="right" width="25%">{dosage}{unit}</td>
                <td align="right" width="25%">{total_amount}</td>
            </tr>
        """

    prescript = f"""
        <tr>
            <th align="left">自費項目</th>
            <th align="right">數量</th>
            <th align="right">金額</th>
        </tr>
        {prescript_line}
    """

    return prescript


def get_location(database, medicine_type, medicine_name, unit):
    sql = f'''
        SELECT Location FROM medicine
        WHERE
            MedicineType = "{medicine_type}" AND
            MedicineName = "{medicine_name}" AND
            Unit = "{unit}"
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        if medicine_type == "單方":
            sql = f'''
                SELECT Location FROM medicine
                WHERE
                    MedicineType = "複方" AND
                    MedicineName = "{medicine_name}"
            '''
            rows = database.select_record(sql)
            if len(rows) <= 0:
                return ""
        elif medicine_type == "複方":
            sql = f'''
                SELECT Location FROM medicine
                WHERE
                    MedicineType = "單方" AND
                    MedicineName = "{medicine_name}"
            '''
            rows = database.select_record(sql)
            if len(rows) <= 0:
                return ""
        else:
            return ""

    row = rows[0]
    location = string_utils.xstr(row["Location"])

    return location


def rotate_document(printer, document, paper_width, paper_length):
    printer.setPaperSize(QtCore.QSizeF(paper_width, paper_length), QPrinter.Millimeter)

    # 使用 QPainter 旋轉
    painter = QtGui.QPainter(printer)
    page_rect = printer.pageRect()
    painter.translate(page_rect.right(), page_rect.top())
    painter.rotate(90)

    text_rect = QtCore.QRectF(
        0,
        0,
        page_rect.height(),  # 寬度 ← 旋轉後的 page 高度
        page_rect.width(),  # 高度 ← 旋轉後的 page 寬度
    )

    document.setPageSize(text_rect.size())
    document.drawContents(painter, text_rect)

    painter.end()


# 橫式列印專用 2025-07-04 專嘉
def get_case_html_24(
    database,
    system_settings,
    case_key,
    ins_type,
    background_color=None,
    birthday_mask=True,
    tw_date=False,
    id_mask=True,
):
    rows = get_case_row(database, case_key)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    card = string_utils.xstr(row["Card"])
    if number_utils.get_integer(row["Continuance"]) >= 1:
        card += "-" + string_utils.xstr(row["Continuance"])

    birthday = row["Birthday"]
    # age = ''
    if birthday is not None:
        if birthday_mask:
            birthday = birthday.strftime("%Y-*-*")
        elif tw_date:
            birthday = string_utils.xstr(
                date_utils.west_date_to_nhi_date(row["Birthday"], "-")
            )

    id = row["ID"]
    if id_mask and id is not None:
        id = id[:6] + "****"

    if background_color is not None:
        color = f' style="background-color: {background_color}"'
    else:
        color = ""

    case_date = row["CaseDate"].strftime("%Y-%m-%d")
    if tw_date:
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"], "-")

    clinic_name = system_settings.field("院所名稱")
    clinic_id = system_settings.field("院所代號")
    patient_key = row["PatientKey"]
    name = string_utils.xstr(row["Name"])
    gender = string_utils.xstr(row["Gender"])
    birthday_str = string_utils.xstr(birthday)
    share_type = string_utils.xstr(row["Share"])

    html = f"""
      <table>
        <tr>
          <td colspan="2" style="font-size: 16px;">{clinic_name} ({clinic_id}) 醫療費用收據</td>
        </tr>
        <tr>
          <td{color} width="50%">就診日:{case_date}</td>
          <td width="40%">病歷號:{patient_key}</td>
        </tr>
        <tr>
            <td>姓名:{name}({gender})</td>
            <td>生日:{birthday_str}</td>
        </tr>
        <tr>
            <td>身份證:{id}</td>
            <td>保險:{ins_type}</td>
        </tr>
        <tr>
          <td>負擔:{share_type}</td>
          <td>卡序:{card}</td>
        </tr>
      </table>
    """

    return html


# 健保費用
def get_ins_fees_html_24(database, case_key):
    sql = f"""
        SELECT * FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return ""

    row = rows[0]
    treat_type = string_utils.xstr(row["TreatType"])

    regist_fee = string_utils.xstr(number_utils.get_integer(row["RegistFee"]))
    diag_share_fee = string_utils.xstr(number_utils.get_integer(row["SDiagShareFee"]))
    drug_share_fee = string_utils.xstr(number_utils.get_integer(row["SDrugShareFee"]))
    # total_share_fee = string_utils.xstr(
    #     number_utils.get_integer(row['SDiagShareFee']) +
    #     number_utils.get_integer(row['SDrugShareFee'])
    # )
    deposit_fee = string_utils.xstr(number_utils.get_integer(row["DepositFee"]))
    total_fee = string_utils.xstr(
        number_utils.get_integer(row["RegistFee"])
        + number_utils.get_integer(row["SDiagShareFee"])
        + number_utils.get_integer(row["SDrugShareFee"])
        + number_utils.get_integer(row["DepositFee"])
    )
    diag_fee = string_utils.xstr(number_utils.get_integer(row["DiagFee"]))
    drug_fee = string_utils.xstr(number_utils.get_integer(row["InterDrugFee"]))
    pharmacy_fee = string_utils.xstr(number_utils.get_integer(row["PharmacyFee"]))
    treat_fee = string_utils.xstr(
        number_utils.get_integer(row["AcupunctureFee"])
        + number_utils.get_integer(row["MassageFee"])
        + number_utils.get_integer(row["DislocateFee"])
    )
    # ins_total_fee = string_utils.xstr(number_utils.get_integer(row['InsTotalFee']))
    ins_total_fee = string_utils.xstr(number_utils.get_integer(row["InsTotalFee"]))
    ins_apply_fee = string_utils.xstr(number_utils.get_integer(row["InsApplyFee"]))

    massage_fee = number_utils.get_integer(row["SMassageFee"])

    if treat_type in nhi_utils.HOME_CARE and massage_fee > 0:
        label_traffic_allowanc = "代收費"
        traffic_allowance_fee = string_utils.xstr(massage_fee)
        total_fee = string_utils.xstr(number_utils.get_integer(total_fee) + massage_fee)
    else:
        label_traffic_allowanc = ""
        traffic_allowance_fee = ""

    html = f"""
    <table width="98%" cellspacing="0">
      <tbody>
        <tr>
          <td>診察費</td><td align=right>{diag_fee}</td>
          <td width="1%"></td>
          <td>內服藥</td><td align=right>{drug_fee}</td>
          <td width="1%"></td>
          <td>調劑費</td><td align=right>{pharmacy_fee}</td>
        </tr>
        <tr>
          <td>處置費</td><td align=right>{treat_fee}</td>
          <td width="1%"></td>
          <td>健保額</td><td align=right>{ins_total_fee}</td>
          <td width="1%"></td>
          <td>申請額</td><td align=right>{ins_apply_fee}</td>
        </tr>
        <tr>
          <td>掛號費</td><td align=right>{regist_fee}</td>
          <td width="1%"></td>
          <td>診負擔</td><td align=right>{diag_share_fee}</td>
          <td width="1%"></td>
          <td>藥負擔</td><td align=right>{drug_share_fee}</td>
        </tr>
        <tr>
          <td>欠卡費</td><td align=right>{deposit_fee}</td>
          <td width="1%"></td>
          <td>實收額</td><td align=right>{total_fee}</td>
          <td width="1%"></td>
          <td>{label_traffic_allowanc}</td><td align=right>{traffic_allowance_fee}</td>
        </tr>
      </tbody>
    </table>
    """

    return html


def get_prescript_html24(
    database,
    system_setting,
    case_key,
    medicine_set,
    print_type,
    blocks,
    max_length=None,
    instruction=None,
    print_total_dosage=None,
    print_treat_item=True,
    td_width=250,
    border=1,
    block_len=10,
    header=True,
    print_sequence=True,
):
    if medicine_set is None:
        prescript_td = """
            <tr>
              <td>無處方</td>
            </tr>
            <hr>
        """
        return prescript_td

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    if pres_days <= 0 and instruction == "健保另包":
        return ""

    sql = f"""
        SELECT Treatment, TreatType FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    treatment = rows[0]["Treatment"]
    treat_type = rows[0]["TreatType"]

    treat_condition = ""
    if (
        print_type == "費用收據"
        and system_setting.field("列印穴道處置") == "N"
        and medicine_set == 1
    ) or (print_type == "過去病歷" and not print_treat_item):
        treat_condition = ' AND (prescript.MedicineType NOT IN ("穴道", "處置")) '

    medicine_set_condition = f" AND (MedicineSet = {medicine_set}) "
    medicine_type_condition = ""
    if instruction == "健保檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NOT NULL) AND
            (LENGTH(prescript.InsCode) > 0)
        """
    elif instruction == "自費檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NULL OR prescript.InsCode = "" OR LENGTH(prescript.InsCode) = 0)
        """

    instruction_condition = get_instruction_condition(
        database, system_setting, case_key, medicine_set, instruction
    )
    order_script = "ORDER BY PrescriptNo, PrescriptKey"
    if system_setting.field("列印處方依照存放位置排序") == "Y":
        order_script = """
            ORDER BY
                SUBSTRING(medicine.Location, 1, 1),
                LENGTH(SUBSTRING(medicine.Location, 2)),
                SUBSTRING(medicine.Location, 2)
        """

    sql = f"""
        SELECT prescript.*, medicine.Location, medicine.MedicineAlias FROM prescript
            LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
        WHERE
            CaseKey = {case_key} AND
            (prescript.MedicineName IS NOT NULL AND LENGTH(prescript.MedicineName) > 0)
            {medicine_set_condition}
            {medicine_type_condition}
            {treat_condition}
            {instruction_condition}
            {order_script}
            """
    rows = database.select_record(sql)

    if (
        medicine_set == 1
        and treatment in nhi_utils.INS_TREAT
        and instruction not in ["健保另包", "健保檢驗", "自費檢驗"]
    ):
        if treatment in nhi_utils.ACUPUNCTURE_TREAT:
            medicine_type = "穴道"
        else:
            medicine_type = "處置"

        rows.insert(
            0,
            {
                "MedicineName": treatment,
                "MedicineAlias": treatment,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Instruction": "",
                "Unit": "次",
                "Location": "",
            },
        )

    if medicine_set == 1 and treat_type == "醫療諮詢":
        medicine_type = "單方"
        rows.insert(
            0,
            {
                "MedicineName": treat_type,
                "MedicineAlias": treat_type,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Instruction": "",
                "Unit": "次",
                "Location": "",
            },
        )

    if len(rows) <= 0:
        return ""

    if pres_days is None or pres_days <= 0:
        pres_days = 1

    if print_total_dosage is None:
        print_total_dosage = system_setting.field("處方箋列印總量")

    print_alias = system_setting.field("列印處方別名")
    if print_type == "處方箋":
        print_alias = "N"

    print_location = system_setting.field("列印藥品存放位置")
    print_location_before_medicine = system_setting.field(
        "列印藥品存放位置在處方名稱前面"
    )

    if print_total_dosage == "Y":
        block_width = {
            3: {
                "medicine_name_width": 15,
                "dosage_width": 6,
                "total_dosage_width": 5,
                "separator_width": 1,
            },
            2: {
                "medicine_name_width": 26,
                "dosage_width": 10,
                "total_dosage_width": 9,
                "separator_width": 1,
            },
            1: {
                "medicine_name_width": 55,
                "dosage_width": 20,
                "total_dosage_width": 20,
                "separator_width": 4,
            },
        }
    else:
        block_width = {
            3: {
                "medicine_name_width": 20,
                "dosage_width": 8,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
            2: {
                "medicine_name_width": 35,
                "dosage_width": 10,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
            1: {
                "medicine_name_width": 55,
                "dosage_width": 20,
                "total_dosage_width": 20,
                "separator_width": 4,
            },
        }

    if system_setting.field("處方列印方向") == "垂直列印":
        rows = set_vertical_direction(rows)

    prescript_td = ""
    row_count = int((len(rows) - 1) / blocks) + 1
    sequence = 0
    print_package = system_setting.field("自費處方次劑量")
    if print_package == "Y":
        by_packages = True
    else:
        by_packages = False

    prescript_line = []
    for row_no in range(1, row_count + 1):
        for i in range(blocks):
            prescript_block = get_medicine_detail(
                medicine_set,
                rows,
                (row_no - 1) * blocks + i,
                pres_days,
                packages,
                print_alias,
                by_packages=by_packages,
            )

            medicine_name = string_utils.xstr(prescript_block[0])

            if instruction == "健保檢驗":
                ins_code = string_utils.xstr(prescript_block[5])
                medicine_name = f"{medicine_name} ({ins_code})"

            location = string_utils.xstr(prescript_block[1])
            if print_location != "Y":
                location = ""

            if print_location_before_medicine == "Y":
                medicine_name = location + medicine_name
            else:
                medicine_name += location

            dosage = string_utils.xstr(prescript_block[2])
            total_dosage = string_utils.xstr(prescript_block[4])
            unit = string_utils.xstr(prescript_block[3])
            medicine_name_width = block_width[blocks]["medicine_name_width"]
            dosage_width = block_width[blocks]["dosage_width"]
            total_dosage_width = block_width[blocks]["total_dosage_width"]
            separator_width = block_width[blocks]["separator_width"]

            if medicine_name in ["優待", "健保檢驗", "自費檢驗"]:
                total_dosage = ""

            if instruction == "無劑量":
                dosage = ""
                unit = ""
                total_dosage = ""

            seq_str = ""
            if dosage != "":
                sequence += 1
                seq_str = str(sequence)

            if print_total_dosage != "Y":
                current_line = f"""
                    <td align="left" width="60%">{medicine_name}</td>
                    <td align="right" width="35%">{dosage}{unit}</td>
                """
            else:
                current_line = f"""
                    <td align="left" width="60%">{medicine_name}</td>
                    <td align="right" width="20%">{dosage}{unit}</td>
                    <td align="right" width="15%">{total_dosage}</td>
                """

            if print_sequence:
                current_line = (
                    f'<td align="center" width="15%">{seq_str}</td>' + current_line
                )

            prescript_line.append(current_line)

    td_block = len(prescript_line) // block_len
    remain = len(prescript_line) % block_len
    if remain > 0:
        td_block += 1

    html = ""
    header_html = ""
    if header:
        if print_sequence:
            header_html = """
                <thead>
                <tr>
                    <th align="center">序</th>
                    <th align="left">處方名稱</th>
                    <th align="right">劑量</th>
                    <th align="right">總量</th>
                </tr>
                </thead>
            """
        else:
            header_html = """
                <thead>
                <tr>
                    <th align="left">處方名稱</th>
                    <th align="right">劑量</th>
                    <th align="right">總量</th>
                </tr>
                </thead>
            """

    for td in range(td_block):
        prescript_td = ""
        for i in range(block_len):
            index = i + (block_len * td)
            if index < len(prescript_line):
                prescript_td += f"""
                    <tr>
                        {prescript_line[index]}
                    </tr>
                """
        html += f'''
            <td width="{td_width}">
                <table style="border-collapse: collapse; border:1px #cccccc solid;" cellpadding="0" border="{border}">
                    {header_html}
                    <tbody>
                        {prescript_td}
                    </tbody>
                </table>
            </td>
        '''

    return html, len(prescript_line)


def get_prescript_html29(
    database,
    system_setting,
    case_key,
    medicine_set,
    print_type,
    blocks,
    max_length=None,
    instruction=None,
    print_total_dosage=None,
    print_treat_item=True,
    td_width=250,
    border=1,
    block_len=10,
    header=True,
    print_sequence=True,
):
    if medicine_set is None:
        prescript_td = """
            <tr>
              <td>無處方</td>
            </tr>
            <hr>
        """
        return prescript_td

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    if pres_days <= 0 and instruction == "健保另包":
        return ""

    sql = f"""
        SELECT Treatment, TreatType FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    treatment = rows[0]["Treatment"]
    treat_type = rows[0]["TreatType"]

    treat_condition = ""
    if (
        print_type == "費用收據"
        and system_setting.field("列印穴道處置") == "N"
        and medicine_set == 1
    ) or (print_type == "過去病歷" and not print_treat_item):
        treat_condition = ' AND (prescript.MedicineType NOT IN ("穴道", "處置")) '

    medicine_set_condition = f" AND (MedicineSet = {medicine_set}) "
    medicine_type_condition = ""
    if instruction == "健保檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NOT NULL) AND
            (LENGTH(prescript.InsCode) > 0)
        """
    elif instruction == "自費檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NULL OR prescript.InsCode = "" OR LENGTH(prescript.InsCode) = 0)
        """

    instruction_condition = get_instruction_condition(
        database, system_setting, case_key, medicine_set, instruction
    )
    order_script = "ORDER BY PrescriptNo, PrescriptKey"
    if system_setting.field("列印處方依照存放位置排序") == "Y":
        order_script = """
            ORDER BY
                SUBSTRING(medicine.Location, 1, 1), 
                LENGTH(SUBSTRING(medicine.Location, 2)),
                SUBSTRING(medicine.Location, 2)
        """

    sql = f"""
        SELECT prescript.*, medicine.Location, medicine.MedicineAlias FROM prescript
            LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
        WHERE
            CaseKey = {case_key} AND
            (prescript.MedicineName IS NOT NULL AND LENGTH(prescript.MedicineName) > 0)
            {medicine_set_condition}
            {medicine_type_condition}
            {treat_condition}
            {instruction_condition}
            {order_script}
            """
    rows = database.select_record(sql)

    if (
        medicine_set == 1
        and treatment in nhi_utils.INS_TREAT
        and instruction not in ["健保另包", "健保檢驗", "自費檢驗"]
    ):
        if treatment in nhi_utils.ACUPUNCTURE_TREAT:
            medicine_type = "穴道"
        else:
            medicine_type = "處置"

        rows.insert(
            0,
            {
                "MedicineName": treatment,
                "MedicineAlias": treatment,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Instruction": "",
                "Unit": "次",
                "Location": "",
            },
        )

    if medicine_set == 1 and treat_type == "醫療諮詢":
        medicine_type = "單方"
        rows.insert(
            0,
            {
                "MedicineName": treat_type,
                "MedicineAlias": treat_type,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Instruction": "",
                "Unit": "次",
                "Location": "",
            },
        )

    if len(rows) <= 0:
        return ""

    if pres_days is None or pres_days <= 0:
        pres_days = 1

    if print_total_dosage is None:
        print_total_dosage = system_setting.field("處方箋列印總量")

    print_alias = system_setting.field("列印處方別名")
    if print_type == "處方箋":
        print_alias = "N"

    print_location = system_setting.field("列印藥品存放位置")
    print_location_before_medicine = system_setting.field(
        "列印藥品存放位置在處方名稱前面"
    )

    if print_total_dosage == "Y":
        block_width = {
            3: {
                "medicine_name_width": 15,
                "dosage_width": 6,
                "total_dosage_width": 5,
                "separator_width": 1,
            },
            2: {
                "medicine_name_width": 26,
                "dosage_width": 10,
                "total_dosage_width": 9,
                "separator_width": 1,
            },
            1: {
                "medicine_name_width": 55,
                "dosage_width": 20,
                "total_dosage_width": 20,
                "separator_width": 4,
            },
        }
    else:
        block_width = {
            3: {
                "medicine_name_width": 20,
                "dosage_width": 8,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
            2: {
                "medicine_name_width": 35,
                "dosage_width": 10,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
            1: {
                "medicine_name_width": 55,
                "dosage_width": 20,
                "total_dosage_width": 20,
                "separator_width": 4,
            },
        }

    if system_setting.field("處方列印方向") == "垂直列印":
        rows = set_vertical_direction(rows)

    prescript_td = ""
    row_count = int((len(rows) - 1) / blocks) + 1
    sequence = 0
    print_package = system_setting.field("自費處方次劑量")
    if print_package == "Y":
        by_packages = True
    else:
        by_packages = False

    prescript_line = []
    for row_no in range(1, row_count + 1):
        for i in range(blocks):
            prescript_block = get_medicine_detail(
                medicine_set,
                rows,
                (row_no - 1) * blocks + i,
                pres_days,
                packages,
                print_alias,
                by_packages=by_packages,
            )

            medicine_name = string_utils.xstr(prescript_block[0])

            if instruction == "健保檢驗":
                ins_code = string_utils.xstr(prescript_block[5])
                medicine_name = f"{medicine_name} ({ins_code})"

            location = string_utils.xstr(prescript_block[1])
            if print_location != "Y":
                location = ""

            if print_location_before_medicine == "Y":
                medicine_name = location + medicine_name
            else:
                medicine_name += location

            dosage = string_utils.xstr(prescript_block[2])
            total_dosage = string_utils.xstr(prescript_block[4])
            unit = string_utils.xstr(prescript_block[3])
            medicine_name_width = block_width[blocks]["medicine_name_width"]
            dosage_width = block_width[blocks]["dosage_width"]
            total_dosage_width = block_width[blocks]["total_dosage_width"]
            separator_width = block_width[blocks]["separator_width"]

            if medicine_name in ["優待", "健保檢驗", "自費檢驗"]:
                total_dosage = ""

            if instruction == "無劑量":
                dosage = ""
                unit = ""
                total_dosage = ""

            seq_str = ""
            if dosage != "":
                sequence += 1
                seq_str = str(sequence)

            if print_total_dosage != "Y":
                current_line = f"""
                    <td align="left" width="65%">{medicine_name}</td>
                    <td align="right" width="30%">{dosage}{unit}</td>
                """
            else:
                current_line = f"""
                    <td align="left" width="65%">{medicine_name}</td>
                    <td align="right" width="30%">{total_dosage}{unit}</td>
                """

            if print_sequence:
                current_line = (
                    f'<td align="center" width="15%">{seq_str}</td>' + current_line
                )

            prescript_line.append(current_line)

    td_block = len(prescript_line) // block_len
    remain = len(prescript_line) % block_len
    if remain > 0:
        td_block += 1

    html = ""
    header_html = ""
    if header:
        if print_sequence:
            header_html = """
                <thead>
                <tr>
                    <th align="center">序</th>
                    <th align="left">處方名稱</th>
                    <th align="right">總量</th>
                </tr>
                </thead>
            """
        else:
            header_html = """
                <thead>
                <tr>
                    <th align="left">處方名稱</th>
                    <th align="right">劑量</th>
                    <th align="right">總量</th>
                </tr>
                </thead>
            """

    for td in range(td_block):
        prescript_td = ""
        for i in range(block_len):
            index = i + (block_len * td)
            if index < len(prescript_line):
                prescript_td += f"""
                    <tr>
                        {prescript_line[index]}
                    </tr>
                """
        html += f'''
            <td width="{td_width}">
                <table style="border-collapse: collapse; border:1px #cccccc solid;" cellpadding="0" border="{border}">
                    {header_html}
                    <tbody>
                        {prescript_td}
                    </tbody>
                </table>
            </td>
        '''

    return html, len(prescript_line)


# 雲濤
def get_prescript_html7(
    database,
    system_setting,
    case_key,
    medicine_set,
    print_type,
    blocks,
    max_length=None,
    instruction=None,
    print_total_dosage=None,
):
    if medicine_set is None:
        prescript = """
            <tr>
              <td>無處方</td>
            </tr>
            <hr>
        """
        return prescript

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    if pres_days <= 0 and instruction == "健保另包":
        return ""

    sql = f"""
        SELECT Treatment, TreatType FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    treatment = rows[0]["Treatment"]
    treat_type = rows[0]["TreatType"]

    treat_condition = ""
    if (
        print_type == "費用收據"
        and system_setting.field("列印穴道處置") == "N"
        and medicine_set == 1
    ):  # 健保才過濾
        treat_condition = ' AND (prescript.MedicineType NOT IN ("穴道", "處置")) '

    medicine_set_condition = f" AND (MedicineSet = {medicine_set}) "
    medicine_type_condition = ""
    if instruction == "健保檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NOT NULL) AND
            (LENGTH(prescript.InsCode) > 0)
        """
    elif instruction == "自費檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NULL OR prescript.InsCode = "" OR LENGTH(prescript.InsCode) = 0)
        """

    instruction_condition = get_instruction_condition(
        database, system_setting, case_key, medicine_set, instruction
    )
    order_script = "ORDER BY PrescriptKey"
    if system_setting.field("列印處方依照存放位置排序") == "Y":
        order_script = """
            ORDER BY 
                -- 1. 先排純字母部分 (例如 A, B, AA)
                REGEXP_SUBSTR(medicine.Location, '^[A-Za-z]+'),
                
                -- 2. 排字母後的第一組數字 (例如 A3 中的 3, B5-10 中的 5)
                -- 先抓出數字部分，轉為數值排序
                CAST(REGEXP_SUBSTR(medicine.Location, '[0-9]+') AS UNSIGNED),
                
                -- 3. 排槓號後的第二組數字 (處理 A3-1, A3-10)
                -- 如果沒有槓號，這層會是 0，不影響排序
                CAST(SUBSTRING_INDEX(CONCAT(medicine.Location, '-0'), '-', -2) AS UNSIGNED)
        """

    sql = f"""
        SELECT prescript.*, medicine.Location, medicine.MedicineAlias FROM prescript
            LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
        WHERE
            CaseKey = {case_key} AND
            (prescript.MedicineName IS NOT NULL AND LENGTH(prescript.MedicineName) > 0)
            {medicine_set_condition}
            {medicine_type_condition}
            {treat_condition}
            {instruction_condition}
        {order_script}
    """
    rows = database.select_record(sql)

    if (
        medicine_set == 1
        and treatment in nhi_utils.INS_TREAT
        and instruction not in ["健保另包", "健保檢驗", "自費檢驗"]
    ):
        if treatment in nhi_utils.ACUPUNCTURE_TREAT:
            medicine_type = "穴道"
        else:
            medicine_type = "處置"

        rows.insert(
            0,
            {
                "MedicineName": treatment,
                "MedicineAlias": treatment,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Instruction": "",
                "Unit": "次",
                "Location": "",
            },
        )

    if medicine_set == 1 and treat_type == "醫療諮詢":
        medicine_type = "單方"
        rows.insert(
            0,
            {
                "MedicineName": treat_type,
                "MedicineAlias": treat_type,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Instruction": "",
                "Unit": "次",
                "Location": "",
            },
        )

    if len(rows) <= 0:
        return ""

    if pres_days is None or pres_days <= 0:
        pres_days = 1

    if print_total_dosage is None:
        print_total_dosage = system_setting.field("處方箋列印總量")

    print_alias = system_setting.field("列印處方別名")
    if print_type == "處方箋":
        print_alias = "N"

    if print_total_dosage == "Y":
        block_width = {
            3: {
                "location_width": 10,
                "medicine_name_width": 19,
                "dosage_width": 6,
                "total_dosage_width": 5,
                "separator_width": 1,
            },
            2: {
                "location_width": 15,
                "medicine_name_width": 30,
                "dosage_width": 10,
                "total_dosage_width": 9,
                "separator_width": 1,
            },
            1: {
                "location_width": 10,
                "medicine_name_width": 40,
                "dosage_width": 20,
                "total_dosage_width": 20,
                "instruction_width": 10,
            },
        }
    else:
        block_width = {
            3: {
                "location_width": 10,
                "medicine_name_width": 24,
                "dosage_width": 8,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
            2: {
                "location_width": 10,
                "medicine_name_width": 39,
                "dosage_width": 10,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
            1: {
                "location_width": 10,
                "medicine_name_width": 40,
                "dosage_width": 20,
                "total_dosage_width": 20,
                "instruction_width": 10,
            },
        }

    prescript = ""
    row_count = int((len(rows) - 1) / blocks) + 1
    for row_no in range(1, row_count + 1):
        separator = ""
        prescript_line = ""
        for i in range(blocks):
            prescript_block = get_medicine_detail(
                medicine_set,
                rows,
                (row_no - 1) * blocks + i,
                pres_days,
                packages,
                print_alias,
            )

            medicine_name = string_utils.xstr(prescript_block[0])
            unit = string_utils.xstr(prescript_block[3])
            medicine_type = string_utils.xstr(prescript_block[7])

            if instruction == "健保檢驗":
                ins_code = string_utils.xstr(prescript_block[5])
                medicine_name = f"{medicine_name} ({ins_code})"

            if medicine_set == 1:
                location = get_location(database, medicine_type, medicine_name, unit)
                if location == "":
                    location = string_utils.xstr(prescript_block[1])
            else:
                location = string_utils.xstr(prescript_block[1])

            dosage = string_utils.xstr(prescript_block[2])
            total_dosage = string_utils.xstr(prescript_block[4])
            unit = string_utils.xstr(prescript_block[3])
            instruction = string_utils.xstr(prescript_block[6])

            location_width = block_width[blocks]["location_width"]
            medicine_name_width = block_width[blocks]["medicine_name_width"]
            dosage_width = block_width[blocks]["dosage_width"]
            total_dosage_width = block_width[blocks]["total_dosage_width"]
            instruction_width = block_width[blocks]["instruction_width"]

            if medicine_name in ["優待", "健保檢驗", "自費檢驗"]:
                total_dosage = ""

            if instruction == "無劑量":
                dosage = ""
                unit = ""
                total_dosage = ""

            if print_total_dosage != "Y":
                prescript_line += f'''
                    <td align="left" width="{location_width}%">{location}</td>
                    <td align="left" width="{medicine_name_width}%">{medicine_name}</td>
                    <td align="right" width="{dosage_width}%">{dosage}{unit}</td>
                    <td align="left" style="padding-left: 10px" width="{instruction_width}%">{instruction}</td>
                '''
            else:
                prescript_line += f'''
                    <td align="left" width="{location_width}%">{location}</td>
                    <td align="left" width="{medicine_name_width}%">{medicine_name}</td>
                    <td align="right" width="{dosage_width}%">{dosage}{unit}</td>
                    <td align="right" width="{total_dosage_width}%">{total_dosage}</td>
                    <td align="left" style="padding-left: 10px" width="{instruction_width}%">{instruction}</td>
                '''

        prescript += f"""
            <tr>
              {prescript_line}
            </tr>
        """

    return prescript


# 天地精進
def get_prescript_html22(
    database,
    system_setting,
    case_key,
    medicine_set,
    print_type,
    blocks,
    max_length=None,
    instruction=None,
    print_total_dosage=None,
):
    if medicine_set is None:
        prescript = """
            <tr>
              <td>無處方</td>
            </tr>
            <hr>
        """
        return prescript

    pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
    packages = case_utils.get_packages(database, case_key, medicine_set)
    if pres_days <= 0 and instruction == "健保另包":
        return ""

    sql = f"""
        SELECT Treatment, TreatType FROM cases
        WHERE
            CaseKey = {case_key}
    """
    rows = database.select_record(sql)

    treatment = rows[0]["Treatment"]
    treat_type = rows[0]["TreatType"]

    treat_condition = ""
    if (
        print_type == "費用收據"
        and system_setting.field("列印穴道處置") == "N"
        and medicine_set == 1
    ):  # 健保才過濾
        treat_condition = ' AND (prescript.MedicineType NOT IN ("穴道", "處置")) '

    medicine_set_condition = f" AND (MedicineSet = {medicine_set}) "
    medicine_type_condition = ""
    if instruction == "健保檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NOT NULL) AND
            (LENGTH(prescript.InsCode) > 0)
        """
    elif instruction == "自費檢驗":
        treat_condition = ""
        medicine_set_condition = " AND (MedicineSet > 1) "
        medicine_type_condition = """ AND
            (prescript.MedicineType = "檢驗") AND
            (prescript.InsCode IS NULL OR prescript.InsCode = "" OR LENGTH(prescript.InsCode) = 0)
        """

    instruction_condition = get_instruction_condition(
        database, system_setting, case_key, medicine_set, instruction
    )
    order_script = "ORDER BY PrescriptNo, PrescriptKey"
    # if system_setting.field("列印處方依照存放位置排序") == "Y":
    #     order_script = """
    #         ORDER BY
    #             SUBSTRING(medicine.Location, 1, 1),
    #             LENGTH(SUBSTRING(medicine.Location, 2)),
    #             SUBSTRING(medicine.Location, 2)
    #     """
    if system_setting.field("列印處方依照存放位置排序") == "Y":
        order_script = """
            ORDER BY 
                -- 1. 先排純字母部分 (例如 A, B, AA)
                REGEXP_SUBSTR(medicine.Location, '^[A-Za-z]+'),
                
                -- 2. 排字母後的第一組數字 (例如 A3 中的 3, B5-10 中的 5)
                -- 先抓出數字部分，轉為數值排序
                CAST(REGEXP_SUBSTR(medicine.Location, '[0-9]+') AS UNSIGNED),
                
                -- 3. 排槓號後的第二組數字 (處理 A3-1, A3-10)
                -- 如果沒有槓號，這層會是 0，不影響排序
                CAST(SUBSTRING_INDEX(CONCAT(medicine.Location, '-0'), '-', -2) AS UNSIGNED)
        """

    sql = f"""
        SELECT prescript.*, medicine.Location, medicine.MedicineAlias FROM prescript
            LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
        WHERE
            CaseKey = {case_key} AND
            (prescript.MedicineName IS NOT NULL AND LENGTH(prescript.MedicineName) > 0)
            {medicine_set_condition}
            {medicine_type_condition}
            {treat_condition}
            {instruction_condition}
        {order_script}
    """
    rows = database.select_record(sql)

    if (
        medicine_set == 1
        and treatment in nhi_utils.INS_TREAT
        and instruction not in ["健保另包", "健保檢驗", "自費檢驗"]
    ):
        if treatment in nhi_utils.ACUPUNCTURE_TREAT:
            medicine_type = "穴道"
        else:
            medicine_type = "處置"

        rows.insert(
            0,
            {
                "MedicineName": treatment,
                "MedicineAlias": treatment,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Instruction": "",
                "Unit": "次",
                "Location": "",
            },
        )

    if medicine_set == 1 and treat_type == "醫療諮詢":
        medicine_type = "單方"
        rows.insert(
            0,
            {
                "MedicineName": treat_type,
                "MedicineAlias": treat_type,
                "MedicineType": medicine_type,
                "InsCode": "",
                "Dosage": 1,
                "Instruction": "",
                "Unit": "次",
                "Location": "",
            },
        )

    if len(rows) <= 0:
        return ""

    if pres_days is None or pres_days <= 0:
        pres_days = 1

    if print_total_dosage is None:
        print_total_dosage = system_setting.field("處方箋列印總量")

    print_alias = system_setting.field("列印處方別名")
    if print_type == "處方箋":
        print_alias = "N"

    if print_total_dosage == "Y":
        block_width = {
            3: {
                "location_width": 10,
                "medicine_name_width": 19,
                "dosage_width": 6,
                "total_dosage_width": 5,
                "separator_width": 1,
            },
            2: {
                "location_width": 15,
                "medicine_name_width": 30,
                "dosage_width": 10,
                "total_dosage_width": 9,
                "separator_width": 1,
            },
            1: {
                "location_width": 15,
                "medicine_name_width": 40,
                "dosage_width": 25,
                "total_dosage_width": 20,
                "separator_width": 4,
            },
        }
    else:
        block_width = {
            3: {
                "location_width": 10,
                "medicine_name_width": 24,
                "dosage_width": 8,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
            2: {
                "location_width": 10,
                "medicine_name_width": 39,
                "dosage_width": 10,
                "total_dosage_width": 0,
                "separator_width": 1,
            },
            1: {
                "location_width": 15,
                "medicine_name_width": 40,
                "dosage_width": 25,
                "total_dosage_width": 20,
                "separator_width": 4,
            },
        }

    if system_setting.field("處方列印方向") == "垂直列印":
        rows = set_vertical_direction(rows)

    prescript = ""
    row_count = int((len(rows) - 1) / blocks) + 1
    for row_no in range(1, row_count + 1):
        separator = ""
        prescript_line = ""
        for i in range(blocks):
            prescript_block = get_medicine_detail(
                medicine_set,
                rows,
                (row_no - 1) * blocks + i,
                pres_days,
                packages,
                print_alias,
            )

            medicine_name = string_utils.xstr(prescript_block[0])
            unit = string_utils.xstr(prescript_block[3])
            medicine_type = string_utils.xstr(prescript_block[7])

            if instruction == "健保檢驗":
                ins_code = string_utils.xstr(prescript_block[5])
                medicine_name = f"{medicine_name} ({ins_code})"

            if medicine_set == 1:
                location = get_location(database, medicine_type, medicine_name, unit)
                if location == "":
                    location = string_utils.xstr(prescript_block[1])
            else:
                location = string_utils.xstr(prescript_block[1])

            dosage = string_utils.xstr(prescript_block[2])
            total_dosage = string_utils.xstr(prescript_block[4])
            unit = string_utils.xstr(prescript_block[3])
            location_width = block_width[blocks]["location_width"]
            medicine_name_width = block_width[blocks]["medicine_name_width"]
            dosage_width = block_width[blocks]["dosage_width"]
            total_dosage_width = block_width[blocks]["total_dosage_width"]
            separator_width = block_width[blocks]["separator_width"]

            if medicine_name in ["優待", "健保檢驗", "自費檢驗"]:
                total_dosage = ""

            if instruction == "無劑量":
                dosage = ""
                unit = ""
                total_dosage = ""

            if print_total_dosage != "Y":
                prescript_line += f'''
                    <td align="left" width="{location_width}%">{location}</td>
                    <td align="left" width="{medicine_name_width}%">{medicine_name}</td>
                    <td align="right" width="{dosage_width}%">{dosage}{unit}</td>
                '''
            else:
                prescript_line += f'''
                    <td align="left" width="{location_width}%">{location}</td>
                    <td align="left" width="{medicine_name_width}%">{medicine_name}</td>
                    <td align="right" width="{dosage_width}%">{dosage}{unit}</td>
                    <td align="right" width="{total_dosage_width}%">{total_dosage}</td>
                '''

        prescript += f"""
            <tr>
              {prescript_line}
            </tr>
        """

    return prescript
