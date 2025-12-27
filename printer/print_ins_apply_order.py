
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
import datetime
import os
import json

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import nhi_utils
from libs import case_utils
from libs import number_utils
from libs import charge_utils
from libs import date_utils
from libs import personnel_utils
from libs import prescript_utils


# 掛號收據格式1 80mm * 80mm 熱感紙
# 2018.07.09
class PrintInsApplyOrder:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = args[2]
        self.apply_month = args[3]
        self.apply_type = args[4]
        self.ins_apply_key = args[5]
        self.ui = None

        self.start_date = date_utils.get_start_date_by_year_month(
            str(self.apply_year), str(self.apply_month))  # 雙月檢查
        self.end_date = date_utils.get_end_date_by_year_month(
            self.apply_year, self.apply_month)
        self.printer = printer_utils.get_printer(self.system_settings, '報表印表機')
        self.ins_apply_path = nhi_utils.get_dir(self.system_settings, '申報路徑')
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        self.current_print = None

        try:
            with open('2023_ICD_MAP.json', 'r', encoding='utf-8') as f:
                self.dict_icd_map = json.load(f)
        except Exception:
            self.dict_icd_map = None

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
        self.font = QtGui.QFont(font, 10, QtGui.QFont.PreferQuality)
        self.font.setLetterSpacing(QtGui.QFont.PercentageSpacing, 94)

    def _set_signal(self):
        pass

    def print(self):
        self.print_html(True)

    def preview(self):
        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        self.preview_dialog.paintRequested.connect(self.print_html)
        self.preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def save_to_pdf(self):
        sql = f'''
            SELECT * FROM insapply
            WHERE
                InsApplyKey = {self.ins_apply_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return None

        row = rows[0]
        # 14: 中醫 A:病歷本文 案件類別 流水號6碼
        export_dir = f'{self.ins_apply_path}/emr{row["ApplyDate"]}'
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        pdf_file_name = f'{export_dir}/ins_order_{row["CaseType"]}{row["Sequence"]:0>6}.pdf'
        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(pdf_file_name)
        self.print_html(True)

    def save_to_pdf_by_dialog(self):
        export_dir = f'{self.ins_apply_path}/pdf'
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        pdf_file_name = f'{export_dir}/健保醫令pdf_{self.ins_apply_key}.pdf'

        options = QtWidgets.QFileDialog.Options()
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.parent, "匯出醫令pdf",
            pdf_file_name,
            "所有檔案 (*);;pdf檔 (*.pdf)", options=options
        )
        if not file_name:
            return

        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(file_name)
        self.print_html(True)
        system_utils.show_message_box(
            QtWidgets.QMessageBox.Information,
            '匯出完成',
            '<font size="5" color="red"><b>醫令明細pdf檔案已匯出完成</b></font>',
            '',
        )

    def print_painter(self):
        self.current_print = self.print_painter
        self.printer.setPaperSize(QtCore.QSizeF(80, 80), QPrinter.Millimeter)

        painter = QtGui.QPainter()
        painter.setFont(self.font)
        painter.begin(self.printer)
        painter.drawText(0, 10, 'print test line1 中文測試')
        painter.drawText(0, 30, 'print test line2 中文測試')
        painter.end()

    def print_html(self, printing):
        self.current_print = self.print_html
        self.printer.setOrientation(QPrinter.Landscape)
        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html(self.ins_apply_key))
        # printer_utils.set_document_line_height(document, 18)
        if printing:
            document.print(self.printer)

    def _get_html(self, ins_apply_key):
        sql = f'''
            SELECT * FROM insapply
            WHERE
                InsApplyKey = {ins_apply_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]
        case_record = self._get_case_record(row)
        prescript_record = self._get_prescript_record(row)
        fees_record = self._get_fees_record(row)

        html = f'''
            <html>
                <body>
                    <center><h3 style="text-align: center">特 約 醫 事 服 務 機 構 門 診 醫 療 服 務 點 數 及 醫 令 清 單</h3></center>
                    <table align=center cellpadding="0" cellspacing="0" width="100%"
                     style="font-color: black; border-width: 1px; border-style: solid;">
                        <tbody>
                            <tr>
                                <td>
                                    {case_record}
                                </td>
                            </tr>
                            <tr>
                                <td>
                                    {prescript_record}
                                </td>
                            </tr>
                            <tr>
                                <td>
                                    {fees_record}
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </body>
            </html>
        '''

        return html

    # 醫令病歷資料
    def _get_case_record(self, row):
        if self.apply_type == '申報':
            apply_type = '送核'
        else:
            apply_type = self.apply_type

        try:
            year = row['StopDate'].year - 1911
            month = row['StopDate'].month
            day = row['StopDate'].day
            stop_date = f'{year:0>3}年{month:0>2}月{day:0>2}日'
        except Exception:
            stop_date = ''

        birthday = row['Birthday']
        if birthday is not None:
            birthday = string_utils.xstr(f'{birthday.year-1911:0>3}年{birthday.month:0>2}月{birthday.day:0>2}日')
        else:
            birthday = ''

        sequence = string_utils.xstr(row['Sequence'])
        clinic_id = self.system_settings.field('院所代號')
        clinic_name = self.system_settings.field('院所名稱')

        if row['StopDate'] not in ['', None]:
            ins_apply_date = row['StopDate']
        else:
            ins_apply_date = row['CaseDate']

        apply_date = f'{ins_apply_date.year-1911:0>3}年{ins_apply_date.month:0>2}月'

        case_type = string_utils.xstr(row['CaseType'])
        special_code1 = string_utils.xstr(row['SpecialCode1'])
        special_code2 = string_utils.xstr(row['SpecialCode2'])
        special_code3 = string_utils.xstr(row['SpecialCode3'])
        special_code4 = string_utils.xstr(row['SpecialCode4'])
        name = string_utils.xstr(row['Name'])
        case_date = string_utils.xstr(
            f'{row["CaseDate"].year-1911:0>3}年{row["CaseDate"].month:0>2}月{row["CaseDate"].day:0>2}日'
        )
        clinic_class = nhi_utils.INS_CLASS
        pres_days = string_utils.xstr(row['PresDays'])
        id = string_utils.xstr(row['ID'])
        card = string_utils.xstr(row['Card'])
        injury = string_utils.xstr(row['Injury'])
        share_code = string_utils.xstr(row['ShareCode'])

        disease_list = [
            string_utils.xstr(row['DiseaseCode1']),
            string_utils.xstr(row['DiseaseCode2']),
            string_utils.xstr(row['DiseaseCode3']),
            string_utils.xstr(row['DiseaseCode4']),
            string_utils.xstr(row['DiseaseCode5'])
        ]
        for i, disease_code in enumerate(disease_list):
            if disease_code == '':
                continue

            if self.apply_year <= 2024 and self.dict_icd_map is not None:  # 2023年版ICD預檢 更新
                try:
                    disease_code = self.dict_icd_map[disease_code]  # 申報月份2025年以前只能申報2014年版本ICD-10
                except Exception:
                    pass

            disease_list[i] = disease_code

        disease_code1 = disease_list[0]
        disease_code2 = disease_list[1] 
        disease_code3 = disease_list[2]
        disease_code4 = disease_list[3]
        disease_code5 = disease_list[4]

        disease_name = case_utils.get_disease_name(self.database, row['DiseaseCode1'])

        pres_type = nhi_utils.PHARMACY_TYPE_DICT[row['PresType']]

        if special_code1 in ['JA', 'JB']:
            correction_area_code = nhi_utils.get_correction_area_code(self.system_settings)
        else:
            correction_area_code = ''

        html = f'''
            <table align=center cellpadding="0" cellspacing="0" width="100%"
             style="border-width: 1px; font-color: black; border-style: solid;">
                <tbody>
                    <tr>
                        <td rowspan=2 style="text-align: center;" colspan="2">d2流水編號<br>{sequence}</td>
                        <td style="text-align: center;">t1資料格式</td>
                        <td style="text-align: center;">t2服務機構</td>
                        <td style="text-align: center;">t3費用年月</td>
                        <td>t5申報類別: {apply_type}</td>
                        <td style="text-align: center;">d1案件分類</td>
                    </tr>
                    <tr>
                        <td style="text-align: center">10門診費用明細</td>
                        <td style="text-align: center">({clinic_id}) {clinic_name}</td>
                        <td style="text-align: center">{apply_date}</td>
                        <td>d12補報原因註記:</td>
                        <td style="text-align: center">{case_type}</td>
                    </tr>
                </tbody>
            </table>
            <table align=center cellpadding="0" cellspacing="0" width="100%"
             style="border-width: 0px; border-style: solid;">
                <tbody>
                    <tr>
                        <td>
                            特定治療項目代號: d4:{special_code1}, d5:{special_code2}, d6:{special_code3}, d7:{special_code4}
                        </td>
                        <td>d49姓名: {name}</td>
                        <td>d9就醫日期: {case_date}</td>
                        <td>d8就醫科別: {clinic_class}</td>
                        <td>d27給藥日份: {pres_days}</td>
                    </tr>
                </tbody>
            </table>
            <table align=center cellpadding="0" cellspacing="0" width="100%"
             style="border-width: 1px; border-style: solid;">
                <tbody>
                    <tr>
                        <td>d11出生年月日:{birthday}</td>
                        <td>d3身分證統一編號:{id}</td>
                        <td>d29就醫序號:{card}</td>
                        <td>d14給付類別:{injury}</td>
                        <td>d15部份負擔代號:{share_code}</td>
                        <td>d10治療結束日期:{stop_date}</td>
                    </tr>
                </tbody>
            </table>
            <table align=center cellpadding="0" cellspacing="0" width="100%"
             style="border-width: 0px; border-style: solid;">
                <tbody>
                    <tr>
                        <td>d42論病歷計酬代碼:</td>
                        <td>d18病患是否轉出: N</td>
                        <td>d45依附就醫新生兒出生日期:</td>
                        <td>d44慢性病連續處方箋有效期間總處方日份:</td>
                    </tr>
                </tbody>
            </table>
            <table align=center cellpadding="0" cellspacing="0" width="100%"
             style="border-width: 1px; border-style: solid;">
                <tbody>
                    <tr>
                        <td>國際疾病分類碼</td>
                        <td>d19: {disease_code1}</td>
                        <td>d20: {disease_code2}</td>
                        <td>d21: {disease_code3}</td>
                        <td>d22: {disease_code4}</td>
                        <td>d23: {disease_code5}</td>
                        <td>d50矯正機關代號: {correction_area_code}</td>
                        <td>d52特定地區醫療服務:</td>
                        <td>d53支援區域:</td>
                    </tr>
                </tbody>
            </table>
            <table align=center cellpadding="0" cellspacing="0" width="100%"
             style="border-width: 0px; border-style: solid;">
                <tbody>
                    <tr>
                        <td>d24主手術(處置)代碼:</td>
                        <td>傷病名稱:{disease_name}</td>
                        <td>d25次手術(處置)代碼(一):</td>
                        <td>d53實際提供醫療服務之醫事服務機構代號:</td>
                    </tr>
                </tbody>
            </table>
            <table align=center cellpadding="0" cellspacing="0" width="100%"
             style="border-width: 1px; border-style: solid;">
                <tbody>
                    <tr>
                        <td>d25次手術(處置)代碼(二):</td>
                        <td>d46急診治療起始時間:</td>
                        <td>d47急診治療結束時間:</td>
                        <td>d48山地離島地區醫療服務計畫代碼:</td>
                        <td>d51依附就醫新生兒胞胎註記:</td>
                    </tr>
                </tbody>
            </table>
            <table align=center cellpadding="0" cellspacing="0" width="100%"
             style="border-width: 0px; border-style: solid;">
                <tbody>
                    <tr>
                        <td>d16轉診(檢),代檢或處方調劑案件註記:</td>
                        <td>d17轉診(檢),代檢或處方調劑案件之服務機構代號:</td>
                        <td>d13整合式照護計畫註記:</td>
                    </tr>
                </tbody>
            </table>
            <table align=center cellpadding="0" cellspacing="0" width="100%"
             style="border-width: 1px; border-style: solid;">
                <tbody>
                    <tr>
                        <td>d28處方調劑方式: {pres_type}</td>
                    </tr>
                </tbody>
            </table>
        '''

        return html

    # 醫令點數資料
    def _get_fees_record(self, row):
        pharmacy_code = nhi_utils.extract_pharmacy_code(row['PharmacyCode'])

        case_rows = self._get_case_row(row['CaseKey1'])
        if len(case_rows) > 0:
            case_row = case_rows[0]
            if string_utils.xstr(case_row['TreatType']) == '癌症中醫門診延長照護':
                pharmacy_code = 'P59031'

        drug_fee = string_utils.xstr(row['DrugFee'])
        treat_fee = string_utils.xstr(row['TreatFee'])
        doctor_id = string_utils.xstr(row['DoctorID'])
        doctor_name = string_utils.xstr(row['DoctorName'])
        pharmacist_id = string_utils.xstr(row['PharmacistID'])
        diag_code = string_utils.xstr(row['DiagCode'])
        diag_fee = string_utils.xstr(row['DiagFee'])
        pharmacy_fee = string_utils.xstr(row['PharmacyFee'])
        agent_fee = string_utils.xstr(row['AgentFee'])
        ins_total_fee = string_utils.xstr(row['InsTotalFee'])
        share_fee = string_utils.xstr(row['ShareFee'])
        ins_apply_fee = string_utils.xstr(row['InsApplyFee'])

        html = f'''
            <table align=center cellpadding="0" cellspacing="0" width="100%"
             style="border-width: 1px; border-style: solid;">
                <tbody>
                    <tr>
                        <td colspan="4">d32用藥明細點數小計: {drug_fee}</td>
                        <td colspan="4">d33診療明細點數小計: {treat_fee}</td>
                        <td colspan="4">d34特殊材料明細點數小計:</td>
                    </tr>
                    <tr>
                        <td colspan="4">d30診治醫事人員代號: {doctor_id}</td>
                        <td colspan="4">d31藥師代號: {pharmacist_id}</td>
                        <td style="text-align: center">項目代號</td>
                        <td style="text-align: center">項目名稱</td>
                        <td style="text-align: center">點數</td>
                        <td style="text-align: center">審查欄</td>
                    </tr>
                    <tr>
                        <td colspan="4" rowspan="6">診療醫師人員簽章: {doctor_name}</td>
                        <td colspan="4" rowspan="6">藥師簽章:</td>
                        <td>d35: {diag_code}</td>
                        <td>診察費</td>
                        <td>d36: {diag_fee}</td>
                        <td></td>
                    </tr>
                    <tr>
                        <td>d37: {pharmacy_code}</td>
                        <td>藥事服務費</td>
                        <td>d38: {pharmacy_fee}</td>
                        <td></td>
                    </tr>
                    <tr>
                        <td></td>
                        <td>行政協助項目部分負擔</td>
                        <td>d43: {agent_fee}</td>
                        <td></td>
                    </tr>
                    <tr>
                        <td colspan="2" style="text-align: center">d39合計點數</td>
                        <td style="text-align: right">{ins_total_fee}</td>
                        <td></td>
                    </tr>
                    <tr>
                        <td colspan="2" style="text-align: center">d40部分負擔點數</td>
                        <td style="text-align: right">{share_fee}</td>
                        <td></td>
                    </tr>
                    <tr>
                        <td colspan="2" style="text-align: center">d41申請點數<br>(扣除部分負擔後淨額)</td>
                        <td style="text-align: right; vertical-align: middle">{ins_apply_fee}</td>
                        <td></td>
                    </tr>
                </tbody>
            </table>
        '''

        return html

    # 取得醫令藥品處置資料
    def _get_prescript_record(self, row):
        prescript_rows = self._get_order_rows(row)

        html = f'''
            <table align=center cellpadding="0" cellspacing="0" width="100%"
             style="font-size: 12px; border-width: 1px; border-style: solid;">
                <thead>
                    <tr>
                        <th style="text-align: center; vertical-align: middle">p13<br>醫令<br>序</th>
                        <th style="text-align: center; vertical-align: middle">p20<br>就醫<br>科別</th>
                        <th style="text-align: center; vertical-align: middle">p17<br>慢性病連續處方箋註記 </th>
                        <th style="text-align: center; vertical-align: middle">p2<br>醫令<br>調劑<br>方式</th>
                        <th style="text-align: center; vertical-align: middle">p3<br>醫令<br>類別</th>
                        <th style="text-align: center; vertical-align: middle">p1<br>藥品<br>給藥<br>日份</th>
                        <th style="text-align: center; vertical-align: middle">p4<br>藥品項目<br>代號</th>
                        <th style="text-align: center; vertical-align: middle">診療項目或<br>藥品材料<br>名稱規格</th>
                        <th style="text-align: center; vertical-align: middle">p21<br>自費<br>特材<br>群組<br>序號</th>
                        <th style="text-align: center; vertical-align: middle">p14<br>執行時<br>間-起</th>
                        <th style="text-align: center; vertical-align: middle">p15<br>執行時<br>間-迄</th>
                        <th style="text-align: center; vertical-align: middle">p16<br>執行醫事<br>人員代號</th>
                        <th style="text-align: center; vertical-align: middle">p19<br>事前<br>審查<br>受理<br>編號</th>
                        <th style="text-align: center; vertical-align: middle">p18<br>影像<br>來源</th>
                        <th style="text-align: center; vertical-align: middle">p5<br>藥品<br>用量<br>p6<br>診療<br>部位</th>
                        <th style="text-align: center; vertical-align: middle">p7<br>藥品使用<br>頻率<br>p8<br>支付成數</th>
                        <th style="text-align: center; vertical-align: middle">p9<br>給藥<br>途徑<br>作用<br>部位</th>
                        <th style="text-align: center; vertical-align: middle">p10<br>總量</th>
                        <th style="text-align: center; vertical-align: middle">p11<br>單價</th>
                        <th style="text-align: center; vertical-align: middle">p12<br>點數</th>
                        <th style="text-align: center; vertical-align: middle">p12<br>審查欄</th>
                    </tr>
                </thead>
                <tbody>
                    {prescript_rows}
                </tbody>
            </table>
        '''

        return html

    def _get_order_rows(self, row):
        self.sequence = 0
        case_type = string_utils.xstr(row['CaseType'])

        if case_type == '30':  # 腦血管疾病, 小兒氣喘, 小兒腦麻
            html = self._set_auxiliary_case(row)
            return html
        elif case_type == 'C5':  # 法定傳染病隔離通報
            html = self._set_infectious(row)
            return html

        html = ''

        max_course = nhi_utils.MAX_COURSE
        if case_type == '31':
            max_course = nhi_utils.MAX_HOME_CARE

        for course in range(1, max_course+1):
            case_key = number_utils.get_integer(row[f'CaseKey{course}'])
            if case_key <= 0:
                continue

            rows = self._get_case_row(case_key)
            if len(rows) <= 0:
                continue

            case_row = rows[0]

            if case_type == '31' or \
               (case_type == '25' and string_utils.xstr(case_row['TreatType']) in nhi_utils.HOME_CARE):
                html += self._set_home_care_treat(row, case_row)

            if course == 1 or case_row['TreatType'] in nhi_utils.HOME_CARE:  # 設定診察費
                html += self._set_diagnosis(row)
                if string_utils.xstr(row['Visit']) == '初診照護':
                    html += self._set_first_visit(row)

                if case_utils.get_case_extend(self.database, case_key, '整合醫療照護') == 'Y':
                    html += self._set_integrate_care(row)

            if string_utils.xstr(case_row['TreatType']) in nhi_utils.CARE_TREAT:
                html += self._set_special_care(row, case_row)

            treat_code = string_utils.xstr(row[f'TreatCode{course}'])
            if treat_code != '':
                html += self._set_treatment(row, case_row, course, treat_code)
                if treat_code in nhi_utils.COMPLICATED_TREAT_CODE:
                    auxiliary_list = prescript_utils.get_auxiliary_list(
                        self.database, case_row['CaseKey'], '輔助治療:')
                    for auxiliary_code in auxiliary_list:
                        html += self._set_auxiliary(row, case_row, auxiliary_code)

            prescript_rows = self._get_prescript_rows(case_key)
            if len(prescript_rows) > 0:
                html += self._set_prescript(row, case_row, prescript_rows, case_key, course)

        return html

    def _set_home_care_treat(self, row, case_row):
        ins_code = nhi_utils.get_home_care_ins_code(self.database, string_utils.xstr(case_row['RegistType']))

        amount = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(self.database, ins_code, case_date=case_row['CaseDate'])
        )
        unit_price = amount

        if unit_price <= 0:
            return

        start_date = date_utils.west_date_to_nhi_date(case_row['CaseDate'])
        end_date = date_utils.west_date_to_nhi_date(case_row['CaseDate'])
        percent = amount / unit_price * 100
        order_name = charge_utils.get_item_name_from_ins_code(self.database, ins_code)

        self.sequence += 1
        order_row = {
            'sequence': string_utils.xstr(self.sequence),
            'clinic_class': string_utils.xstr(row['Class']),
            'course_type': '',
            'pres_type': '',
            'order_type': '2',
            'pres_days': '',
            'ins_code': ins_code,
            'order_name': order_name,
            'start_date': f'{start_date}0000',
            'stop_date': f'{end_date}0000',
            'doctor_id': string_utils.xstr(row['DoctorID']),
            'dosage': '1',
            'percent': f'{percent:05.2f}',
            'usage': '',
            'total_dosage': '1',
            'unit_price': string_utils.xstr(unit_price),
            'amount': string_utils.xstr(amount)
        }

        html = self._get_html_order_row(order_row)

        return html

    def _set_auxiliary_case(self, row):
        if string_utils.xstr(row['TreatCode1']) in ['C01', 'C02', 'C03', 'C04']:  # 小兒氣喘, 小兒腦性麻痺
            sql = f'''
                SELECT * FROM cases
                WHERE
                    CaseKey = {row["CaseKey1"]}
            '''
        else:
            patient_key = row['PatientKey']
            sql = f'''
                SELECT * FROM cases
                WHERE
                    (InsType = "健保") AND
                    (Card != "欠卡") AND
                    (TreatType = "腦血管疾病") AND
                    (PatientKey = {patient_key}) AND
                    (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                    (ApplyType = "{self.apply_type}")
                ORDER BY CaseDate
            '''

        rows = self.database.select_record(sql)
        html = self._get_auxiliary_case(row, rows[0], '2', row['StopDate'])  # 2=診療明細
        for case_row in rows:
            case_key = case_row['CaseKey']

            html += self._get_auxiliary_case(row, case_row, '4', case_row['CaseDate'])  # 不另計價
            treat_code = nhi_utils.get_treat_code(self.database, case_row['CaseKey'])
            html += self._set_treatment(row, case_row, None, treat_code)
            prescript_rows = self._get_prescript_rows(case_key)
            if len(prescript_rows) > 0:
                html += self._set_prescript(row, case_row, prescript_rows, case_key)

        return html

    def _get_auxiliary_case(self, row, case_row, order_type, stop_date):
        treat_code = string_utils.xstr(row['TreatCode1'])
        percent = number_utils.get_integer(row['Percent1'])
        if order_type == '2':
            amount = number_utils.get_integer(row['TreatFee1'])
        else:
            amount = 0

        unit_price = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(self.database, treat_code, case_date=case_row['CaseDate'])
        )

        case_key = case_row['CaseKey']
        pres_days = case_utils.get_pres_days(self.database, case_key)
        if pres_days > 0:
            pres_type = '0'
        else:
            pres_type = '2'

        self.sequence += 1
        start_date = date_utils.west_date_to_nhi_date(case_row['CaseDate'])
        end_date = date_utils.west_date_to_nhi_date(stop_date)

        order_row = {
            'sequence': string_utils.xstr(self.sequence),
            'clinic_class': string_utils.xstr(row['Class']),
            'course_type': '2',
            'pres_type': '0',
            'order_type': order_type,
            'pres_days': pres_type,
            'ins_code': treat_code,
            'order_name': charge_utils.get_item_name_from_ins_code(self.database, treat_code),
            'start_date': f'{start_date}0000',
            'stop_date': f'{end_date}0000',
            'doctor_id': string_utils.xstr(row['DoctorID']),
            'dosage': '1',
            'percent': f'{percent:05.2f}',
            'usage': '',
            'total_dosage': '1',
            'unit_price': string_utils.xstr(unit_price),
            'amount': string_utils.xstr(amount)
        }

        html = self._get_html_order_row(order_row)

        return html

    def _set_diagnosis(self, row):
        case_type = string_utils.xstr(row['CaseType'])
        diag_code = string_utils.xstr(row['DiagCode'])

        unit_price = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(self.database, diag_code, case_date=row['CaseDate'])
        )
        if unit_price <= 0:
            return ''

        amount = number_utils.get_integer(row['DiagFee'])
        if case_type == '31':  # 居家醫療 列出單次金額, 非合併後的金額
            amount = unit_price

        start_date = date_utils.west_date_to_nhi_date(row['CaseDate'])
        end_date = date_utils.west_date_to_nhi_date(row['CaseDate'])

        if string_utils.xstr(row['ShareCode']) == '007':
            percent = 100
            unit_price = amount
        else:
            percent = amount / unit_price * 100

        ins_code = string_utils.xstr(row['DiagCode'])

        order_name = charge_utils.get_item_name_from_ins_code(self.database, ins_code)
        order_name = order_name.replace('<', '&lt;')  # 去掉html的 < >
        order_name = order_name.replace('<', '&gt;')

        self.sequence += 1
        order_row = {
            'sequence': string_utils.xstr(self.sequence),
            'clinic_class': string_utils.xstr(row['Class']),
            'course_type': '',
            'pres_type': '',
            'order_type': '0',
            'pres_days': '',
            'ins_code': ins_code,
            'order_name': order_name,
            'start_date': f'{start_date}0000',
            'stop_date': f'{end_date}0000',
            'doctor_id': string_utils.xstr(row['DoctorID']),
            'dosage': '1',
            'percent': f'{percent:05.2f}',
            'usage': '',
            'total_dosage': '1',
            'unit_price': string_utils.xstr(unit_price),
            'amount': string_utils.xstr(amount)
        }

        html = self._get_html_order_row(order_row)

        return html

    # 初診照護
    def _set_first_visit(self, row):
        ins_code = 'A90'

        amount = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(self.database, ins_code, case_date=row['CaseDate'])
        )
        unit_price = amount

        if unit_price <= 0:
            return

        start_date = date_utils.west_date_to_nhi_date(row['CaseDate'])
        end_date = date_utils.west_date_to_nhi_date(row['CaseDate'])
        percent = amount / unit_price * 100
        order_name = charge_utils.get_item_name_from_ins_code(self.database, ins_code)

        self.sequence += 1
        order_row = {
            'sequence': string_utils.xstr(self.sequence),
            'clinic_class': string_utils.xstr(row['Class']),
            'course_type': '',
            'pres_type': '',
            'order_type': '2',
            'pres_days': '',
            'ins_code': ins_code,
            'order_name': order_name,
            'start_date': f'{start_date}0000',
            'stop_date': f'{end_date}0000',
            'doctor_id': string_utils.xstr(row['DoctorID']),
            'dosage': '1',
            'percent': f'{percent:05.2f}',
            'usage': '',
            'total_dosage': '1',
            'unit_price': string_utils.xstr(unit_price),
            'amount': string_utils.xstr(amount)
        }

        html = self._get_html_order_row(order_row)

        return html

    # 整合醫療照護
    def _set_integrate_care(self, row):
        ins_code = 'A91'

        amount = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(self.database, ins_code, case_date=row['CaseDate'])
        )
        unit_price = amount

        if unit_price <= 0:
            return

        start_date = date_utils.west_date_to_nhi_date(row['CaseDate'])
        end_date = date_utils.west_date_to_nhi_date(row['CaseDate'])
        percent = amount / unit_price * 100
        order_name = charge_utils.get_item_name_from_ins_code(self.database, ins_code)

        self.sequence += 1
        order_row = {
            'sequence': string_utils.xstr(self.sequence),
            'clinic_class': string_utils.xstr(row['Class']),
            'course_type': '',
            'pres_type': '',
            'order_type': '2',
            'pres_days': '',
            'ins_code': ins_code,
            'order_name': order_name,
            'start_date': f'{start_date}0000',
            'stop_date': f'{end_date}0000',
            'doctor_id': string_utils.xstr(row['DoctorID']),
            'dosage': '1',
            'percent': f'{percent:05.2f}',
            'usage': '',
            'total_dosage': '1',
            'unit_price': string_utils.xstr(unit_price),
            'amount': string_utils.xstr(amount)
        }

        html = self._get_html_order_row(order_row)

        return html

    # 加強照護
    def _set_special_care(self, row, case_row):
        case_key = case_row['CaseKey']
        sql = f'''
            SELECT * FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 11 AND
                MedicineType = "照護"
            ORDER BY PrescriptKey
        '''
        rows = self.database.select_record(sql)

        start_date = date_utils.west_date_to_nhi_date(row['CaseDate'])
        end_date = date_utils.west_date_to_nhi_date(row['CaseDate'])

        html = ''
        for care_row in rows:
            self.sequence += 1
            amount = number_utils.get_integer(care_row['Price'])
            percent = 100
            unit_price = number_utils.get_integer(amount / percent * 100)
            ins_code = string_utils.xstr(care_row['InsCode'])

            order_row = {
                'sequence': string_utils.xstr(self.sequence),
                'clinic_class': string_utils.xstr(row['Class']),
                'course_type': '',
                'pres_type': '0',
                'order_type': '2',
                'pres_days': '',
                'ins_code': ins_code,
                'order_name': string_utils.xstr(care_row['MedicineName']),
                'start_date': f'{start_date}0000',
                'stop_date': f'{end_date}0000',
                'doctor_id': string_utils.xstr(row['DoctorID']),
                'dosage': '1',
                'percent': f'{percent:05.2f}',
                'usage': '',
                'total_dosage': '1',
                'unit_price': string_utils.xstr(unit_price),
                'amount': string_utils.xstr(amount)
            }

            html += self._get_html_order_row(order_row)

        return html

    def _set_treatment(self, row, case_row, course, treat_code):
        try:
            amount = number_utils.get_integer(row[f'TreatFee{course}'])
            percent = number_utils.get_integer(row[f'Percent{course}'])
            treat_code = string_utils.xstr(row[f'TreatCode{course}'])
            unit_price = number_utils.get_integer(
                charge_utils.get_ins_fee_from_ins_code(self.database, treat_code, case_date=case_row['CaseDate'])
            )
            if string_utils.xstr(case_row['TreatType']) == '慢性腎病照護':
                amount = 0
        except KeyError:
            amount = 0
            unit_price = 0
            percent = 100

        order_type = '2'
        if amount <= 0:
            order_type = '4'

        start_date = date_utils.west_date_to_nhi_date(case_row['CaseDate'])
        end_date = date_utils.west_date_to_nhi_date(case_row['CaseDate'])

        self.sequence += 1

        if treat_code in nhi_utils.COMPLICATED_TREAT_CODE:
            treat_position = prescript_utils.get_treat_position(self.database, case_row['CaseKey'], '治療部位:')
        else:
            treat_position = '1'

        order_row = {
            'sequence': string_utils.xstr(self.sequence),
            'clinic_class': string_utils.xstr(row['Class']),
            'course_type': '2',
            'pres_type': '0',
            'order_type': order_type, 'pres_days': '',
            'ins_code': treat_code,
            'order_name': nhi_utils.TREAT_NAME_DICT[treat_code],
            'start_date': f'{start_date}0000',
            'stop_date': f'{end_date}0000',
            'doctor_id': personnel_utils.get_person_field_value(
                 self.database, string_utils.xstr(case_row['Doctor']), 'ID'
            ),
            'dosage': treat_position,
            'percent': f'{percent:05.2f}',
            'usage': '',
            'total_dosage': '1',
            'unit_price': string_utils.xstr(unit_price),
            'amount': string_utils.xstr(amount)
        }

        html = self._get_html_order_row(order_row)

        return html

    def _set_auxiliary(self, row, case_row, auxiliary):
        order_type = '4'
        amount = 0
        unit_price = 0
        percent = 100
        start_date = date_utils.west_date_to_nhi_date(case_row['CaseDate'])
        end_date = date_utils.west_date_to_nhi_date(case_row['CaseDate'])

        self.sequence += 1


        order_row = {
            'sequence': string_utils.xstr(self.sequence),
            'clinic_class': string_utils.xstr(row['Class']),
            'course_type': '2',
            'pres_type': '0',
            'order_type': order_type, 'pres_days': '',
            'ins_code': auxiliary,
            'order_name': nhi_utils.get_auxiliary_name_by_code(auxiliary),
            'start_date': f'{start_date}0000',
            'stop_date': f'{end_date}0000',
            'doctor_id': personnel_utils.get_person_field_value(
                 self.database, string_utils.xstr(case_row['Doctor']), 'ID'
            ),
            'dosage': '1.00',
            'percent': f'{percent:05.2f}',
            'usage': '',
            'total_dosage': '1',
            'unit_price': string_utils.xstr(unit_price),
            'amount': string_utils.xstr(amount)
        }

        html = self._get_html_order_row(order_row)

        return html

    def _set_prescript(self, row, case_row, prescript_rows, case_key, course=None):
        html = ''

        pres_days = case_utils.get_pres_days(self.database, case_key)
        packages = case_utils.get_packages(self.database, case_key)
        instruction = case_utils.get_instruction(self.database, case_key)
        if pres_days <= 0:
            return html

        if number_utils.get_integer(row['DrugFee']) > 0:
            order_type = '1'  # 1=用藥明細
        else:
            order_type = '4'  # 4=不另計價

        html += self._set_A21(row, case_row, order_type, pres_days)
        if number_utils.get_integer(row['PharmacyFee']) > 0:
            html += self._set_pharmacy(row, case_row, pres_days, course)

        for prescript_row in prescript_rows:
            html += self._set_medicine(
                row, case_row, prescript_row, pres_days, packages, instruction
            )

        return html

    def _set_A21(self, row, case_row, order_type, pres_days):
        ins_code = 'A21'
        if string_utils.xstr(case_row['TreatType']) == '癌症中醫門診延長照護':
            ins_code = 'P59021'

        percent = 100
        unit_price = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(self.database, ins_code, case_date=case_row['CaseDate'])
        )
        amount = unit_price * pres_days
        if order_type == '4':  # 不另計價
            unit_price = 0
            amount = unit_price

        start_date = date_utils.west_date_to_nhi_date(case_row['CaseDate'])
        end_date = date_utils.west_date_to_nhi_date(
            case_row['CaseDate'].date() + datetime.timedelta(days=pres_days - 1)
        )

        self.sequence += 1
        order_row = {
            'sequence': string_utils.xstr(self.sequence),
            'clinic_class': string_utils.xstr(row['Class']),
            'course_type': '',
            'pres_type': '0',
            'order_type': order_type,
            'pres_days': pres_days,
            'ins_code': ins_code,
            'order_name': charge_utils.get_item_name_from_ins_code(self.database, ins_code),
            'start_date': f'{start_date}0000',
            'stop_date': f'{end_date}0000',
            'doctor_id': personnel_utils.get_person_field_value(
                self.database, string_utils.xstr(case_row['Doctor']), 'ID'
            ),
            'dosage': pres_days,
            'percent': f'{percent:05.2f}',
            'usage': 'PO',
            'total_dosage': pres_days,
            'unit_price': string_utils.xstr(unit_price),
            'amount': string_utils.xstr(amount)
        }

        html = self._get_html_order_row(order_row)

        return html

    def _set_pharmacy(self, row, case_row, pres_days, course):
        html = ''
        if pres_days <= 0:
            return html

        if string_utils.xstr(case_row['PharmacyType']) != '申報':
            return html

        course = number_utils.get_integer(course)
        pharmacy_byte = string_utils.xstr(row['PharmacyCode'])[course-1]
        if pharmacy_byte not in ['1', '2']:
            return html

        _, pharmacist = nhi_utils.pharmacist_schedule_on_duty(self.database, case_row['CaseKey'])
        if pharmacist is not None:
            pharmacy_code = 'A31'
        else:
            pharmacy_code = 'A32'

        if string_utils.xstr(case_row['TreatType']) == '癌症中醫門診延長照護':
            pharmacy_code = 'P59031'

        unit_price = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(self.database, pharmacy_code, case_date=case_row['CaseDate'])
        )
        amount = charge_utils.get_extra_pharmacy_fee(string_utils.xstr(case_row['RegistType']), unit_price)
        percent = round(amount / unit_price * 100, -1)

        start_date = date_utils.west_date_to_nhi_date(case_row['CaseDate'])
        end_date = date_utils.west_date_to_nhi_date(case_row['CaseDate'])

        executor = pharmacist
        if executor is None:
            executor = string_utils.xstr(case_row['Doctor'])

        self.sequence += 1
        order_row = {
            'sequence': string_utils.xstr(self.sequence),
            'clinic_class': string_utils.xstr(row['Class']),
            'course_type': '',
            'pres_type': '0',
            'order_type': '9',
            'pres_days': pres_days,
            'ins_code': pharmacy_code,
            'order_name': charge_utils.get_item_name_from_ins_code(self.database, pharmacy_code),
            'start_date': f'{start_date}0000',
            'stop_date': f'{end_date}0000',
            'doctor_id': personnel_utils.get_person_field_value(self.database, executor, 'ID'),
            'dosage': '1',
            'percent': f'{percent:05.2f}',
            'usage': '',
            'total_dosage': '1',
            'unit_price': string_utils.xstr(unit_price),
            'amount': string_utils.xstr(amount)
        }

        html = self._get_html_order_row(order_row)

        return html

    def _set_medicine(self, row, case_row, prescript_row, pres_days, packages, instruction):
        unit_price = 0
        amount = unit_price
        ins_code = string_utils.xstr(prescript_row['InsCode'])

        # order_name = case_utils.get_drug_name(self.database, ins_code)
        order_name = string_utils.remove_square_square_brackets(prescript_row['MedicineName'])

        if order_name == '':
            order_name = case_utils.get_medicine_name(self.database, 'InsCode', ins_code)

        start_date = date_utils.west_date_to_nhi_date(case_row['CaseDate'])
        end_date = date_utils.west_date_to_nhi_date(
            case_row['CaseDate'].date() + datetime.timedelta(days=pres_days-1)
        )
        dosage = prescript_row['Dosage']  # 2020-05-01 改為日劑量
        dosage_mode = prescript_row['DosageMode']  # 劑量模式
        if dosage_mode == '次劑量':
            dosage *= packages

        try:  # 沒有劑量的藥品跳過
            total_dosage = dosage * pres_days
        except Exception:
            return ''

        packages_code = nhi_utils.FREQUENCY[packages]
        instruction_code = nhi_utils.get_usage(instruction)

        self.sequence += 1
        order_row = {
            'sequence': string_utils.xstr(self.sequence),
            'clinic_class': string_utils.xstr(row['Class']),
            'course_type': '',
            'pres_type': '0',
            'order_type': '4',
            'pres_days': pres_days,
            'ins_code': ins_code,
            'order_name': order_name,
            'start_date': f'{start_date}0000',
            'stop_date': f'{end_date}0000',
            'doctor_id': '',
            'dosage': f'{dosage:7.2f}',
            'percent': f'{packages_code}{instruction_code}',
            'usage': 'PO',
            'total_dosage': f'{total_dosage:7.1f}',
            'unit_price': string_utils.xstr(unit_price),
            'amount': string_utils.xstr(amount)
        }

        html = self._get_html_order_row(order_row)

        return html

    def _get_case_row(self, case_key):
        sql = f'''
            SELECT *
            FROM cases
            WHERE
                CaseKey = "{case_key}"
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_prescript_rows(self, case_key):
        sql = f'''
            SELECT * FROM prescript
            WHERE
                CaseKey = "{case_key}" AND
                MedicineSet = 1 AND
                InsCode IS NOT NULL AND
                MedicineName NOT LIKE "%清冠一號%" AND
                LENGTH(InsCode) > 0
            ORDER BY PrescriptNo, PrescriptKey
        '''
        rows = self.database.select_record(sql)

        return rows

    # 取得醫令列
    @staticmethod
    def _get_html_order_row(row):
        sequence = row['sequence']
        clinic_class = row['clinic_class']
        course_type = row['course_type']
        pres_type = row['pres_type']
        order_type = row['order_type']
        pres_days = row['pres_days']
        ins_code = row['ins_code']
        order_name = row['order_name']
        start_date = row['start_date']
        stop_date = row['stop_date']
        doctor_id = row['doctor_id']
        dosage = row['dosage']
        percent = row['percent']
        usage = row['usage']
        total_dosage = row['total_dosage']
        unit_price = row['unit_price']
        amount = row['amount']

        if ins_code in nhi_utils.COMPLICATED_TREAT_CODE:
            dosage_align = 'left'
        else:
            dosage_align = 'right'

        html = f'''
            <tr>
                <td width="3%" style="text-align: center; vertical-align: middle">{sequence}</td>
                <td width="3%" style="text-align: center; vertical-align: middle">{clinic_class}</td>
                <td width="4%" style="text-align: center; vertical-align: middle">{course_type}</td>
                <td width="3%" style="text-align: center; vertical-align: middle">{pres_type}</td>
                <td width="3%" style="text-align: center; vertical-align: middle">{order_type}</td>
                <td width="3%" style="text-align: right; vertical-align: middle">{pres_days}</td>
                <td width="6%" style="text-align: center; vertical-align: middle">{ins_code}</td>
                <td width="18%" style="text-align: center; vertical-align: middle">{order_name}</td>
                <td width="5%"></td>
                <td width="6%" style="text-align: center; vertical-align: middle; font-size:9px">{start_date}</td>
                <td width="6%" style="text-align: center; vertical-align: middle; font-size:9px">{stop_date}</td>
                <td width="6%" style="text-align: center; vertical-align: middle; font-size:9px">{doctor_id}</td>
                <td width="3%"></td>
                <td width="3%"></td>
                <td width="4%" style="text-align: {dosage_align}; vertical-align: middle">{dosage}</td>
                <td width="5%" style="text-align: right; vertical-align: middle">{percent}</td>
                <td width="3%" style="text-align: center; vertical-align: middle">{usage}</td>
                <td width="4%" style="text-align: right; vertical-align: middle">{total_dosage}</td>
                <td width="4%" style="text-align: right; vertical-align: middle">{unit_price}</td>
                <td width="5%" style="text-align: right; vertical-align: middle">{amount}</td>
                <td></td>
            </tr>
        '''

        return html

    def _set_infectious(self, row):
        course = 1
        case_key = row[f'CaseKey{course}']
        case_rows = self._get_case_row(case_key)
        if len(case_rows) <= 0:
            return None

        case_row = case_rows[0]
        total_dosage = case_utils.get_pres_days(self.database, case_row['CaseKey'])

        remote_diag_fee = charge_utils.get_ins_fee_from_ins_code(self.database, 'E5204C', case_date=row['CaseDate'])  # 遠距診療費

        if row['DiagFee'] > 0:
            html = self._set_diagnosis(row)
            return html

        if row['InsApplyFee'] == remote_diag_fee:
            html = self._set_infectious_treatment(row, case_row, 'E5204C', 1)  # 遠距診療費
            return html

        html = ''
        infectious_drug = prescript_utils.get_infectious_drug(self.database, case_key)
        if infectious_drug in ['台灣清冠一號及科學中藥', '台灣清冠一號']:
            html += self._set_infectious_treatment(row, case_row, 'E5012C', total_dosage)  # 台灣清冠一號補助費
        if infectious_drug in ['台灣清冠一號及科學中藥', '科學中藥']:
            prescript_rows = self._get_prescript_rows(case_key)
            if len(prescript_rows) > 0:
                html += self._set_prescript(row, case_row, prescript_rows, case_key, course)

        return html

    # 法定傳染病通報隔離案件
    def _set_infectious_treatment(self, row, case_row, ins_code, total_dosage):
        order_type = '2'
        unit_price = charge_utils.get_ins_fee_from_ins_code(self.database, ins_code, case_date=case_row['CaseDate'])
        amount = unit_price * total_dosage
        percent = 100
        order_name = charge_utils.get_item_name_from_ins_code(self.database, ins_code)

        start_date = date_utils.west_date_to_nhi_date(case_row['CaseDate'])
        end_date = date_utils.west_date_to_nhi_date(case_row['CaseDate'])

        self.sequence += 1
        order_row = {
            'sequence': string_utils.xstr(self.sequence),
            'clinic_class': string_utils.xstr(row['Class']),
            'course_type': '',
            'pres_type': '0',
            'order_type': order_type,
            'pres_days': '',
            'ins_code': ins_code,
            'order_name': order_name,
            'start_date': f'{start_date}0000',
            'stop_date': f'{end_date}0000',
            'doctor_id': personnel_utils.get_person_field_value(
                 self.database, string_utils.xstr(case_row['Doctor']), 'ID'
            ),
            'dosage': total_dosage,
            'percent': f'{percent:05.2f}',
            'usage': '',
            'total_dosage': total_dosage,
            'unit_price': string_utils.xstr(unit_price),
            'amount': string_utils.xstr(amount)
        }

        html = self._get_html_order_row(order_row)

        return html
