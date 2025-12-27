
# -*- coding: UTF-8 -*-

import calendar

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (case_utils, class_utils, date_utils, export_utils, nhi_utils,
                  number_utils, printer_utils, string_utils, system_utils,
                  ui_utils)


# 照護機構院民資料日報表 2023.03.16
class StatisticsNursingHomeDailyData(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsNursingHomeDailyData, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.year = args[2]
        self.month = args[3]
        self.ui = None
        self.case_count = 0

        self.year = int(self.year)
        self.month = int(self.month)
        self.apply_date = nhi_utils.get_apply_date(self.year, self.month)
        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_NURSING_HOME_DAILY_DATA, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_daily_list = class_utils.get_table_widget(
            self.ui.tableWidget_daily_list, self.database)
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_print_list.clicked.connect(self._print_daily_list)
        self.ui.toolButton_export_list.clicked.connect(self._export_daily_list)

    def _set_table_width(self):
        width = [1650]
        self.table_widget_daily_list.set_table_heading_width(width)

    def read_data(self):
        self._display_daily_list()
        # self._display_ins_tour_apply()

    def _display_daily_list(self):
        last_day = calendar.monthrange(self.year, self.month)[1]
        start_date = f'{self.year}-{self.month:0>2}-01'
        end_date = f'{self.year}-{self.month:0>2}-{last_day:0>2}'

        sql = f'''
            SELECT * FROM cases
            WHERE
                DATE(CaseDate) BETWEEN "{start_date}" AND "{end_date}" AND
                RegistType = "照護機構中醫照護" AND
                InsType = "健保" AND
                ApplyType = "申報" AND
                Card != "欠卡"
            GROUP BY DATE(CaseDate)
        '''
        rows = self.database.select_record(sql)
        self.case_count = len(rows)
        if self.case_count <= 0:
            return

        self._get_list(rows)
        self.ui.tableWidget_daily_list.resizeRowsToContents()

    def _get_list(self, rows):
        row_count = len(rows)
        self.ui.tableWidget_daily_list.setRowCount(0)  # 歸零
        self.ui.tableWidget_daily_list.setRowCount(row_count)
        for row_no, row in enumerate(rows):
            html = self._get_daily_html(row['CaseKey'], row['CaseDate'], '10px')
            text_edit = QtWidgets.QTextEdit(self.ui.tableWidget_daily_list)
            text_edit.setHtml(html)
            self.ui.tableWidget_daily_list.setCellWidget(row_no, 0, text_edit)

    def _get_daily_html(self, case_key, case_date, font_size='12px'):
        sql = f'''
            SELECT TourArea FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            tour_area = string_utils.xstr(rows[0]['TourArea'])
        else:
            tour_area = ''

        daily_list = self._get_daily_list(case_date, font_size)
        branch_name = self.system_settings.field('健保業務').split('業務組')[0]
        branch = f'中保會{branch_name}分會'
        tour_area = tour_area
        apply_year = self.year - 1911
        case_date = date_utils.west_date_to_nhi_date(case_date, '-')
        case_time = '08:00 - 12:00'
        clinic_id = self.system_settings.field('院所代號')

        apply_date = f"{self.year}-{self.month}-01"
        treat_head = '''
            <td style="text-align: center;"></td>
            <td style="text-align: center;"></td>
            <td style="text-align: center;"></td>
            <td style="text-align: center;"></td>
            <td style="text-align: center;"></td>
            <td style="text-align: center;"></td>
        '''

        html = f'''
            <html>
            <body>
                <table width="100%" cellspacing="0">
                  <tbody>
                    <tr>
                      <td width="80%">
                        <br>
                        <h3 style="text-align: center;">全民健康保險中醫門診總額照護機構中醫醫療照護方案門診日報表</h3>
                      </td>
                      <td style="font-size: 14px" width="20%">
                        所屬分會: {branch}<br>
                        承辦單位: <br>
                        醫事服務機構代碼: {clinic_id}<br>
                        服務地點: {tour_area}<br>
                        核准代碼: <br>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <table align=center cellpadding="0" cellspacing="0" width="98%"
                 style="border-width: 1px; border-style: solid;">
                    <tbody>
                        <tr style="font-size: {font_size}">
                            <td style="text-align: center; vertical-align: middle" colspan="2">日期</td>
                            <td style="text-align: center; vertical-align: middle">{case_date}</td>
                            <td style="text-align: center; vertical-align: middle" colspan="2">時間</td>
                            <td style="text-align: center; vertical-align: middle">{case_time}</td>
                            <td colspan="18"></td>
                        </tr>
                        <tr style="font-size: {font_size}">
                            <td style="text-align: center; vertical-align: middle" rowspan="2">編號</td>
                            <td style="text-align: center; vertical-align: middle" rowspan="2">姓名</td>
                            <td style="text-align: center; vertical-align: middle" rowspan="2">身份證號</td>
                            <td style="text-align: center; vertical-align: middle" rowspan="2">出生日期</td>
                            <td style="text-align: center; vertical-align: middle" rowspan="2">性別</td>
                            <td style="text-align: center; vertical-align: middle" rowspan="2">住址</td>
                            <td style="text-align: center; vertical-align: middle" rowspan="2">電話</td>
                            <td style="text-align: center; vertical-align: middle" rowspan="2">診察費</td>
                            <td style="text-align: center; vertical-align: middle" rowspan="2">藥費<br>(天)</td>
                            <td style="text-align: center; vertical-align: middle" colspan="2">調劑費</td>
                            <td style="text-align: center; vertical-align: middle" colspan="6" rowspan="2">治療處置</td>
                            <td style="text-align: center; vertical-align: middle" colspan="2">當地居民</td>
                            <td style="text-align: center; vertical-align: middle" rowspan="2">醫療費用</td>
                            <td style="text-align: center; vertical-align: middle" rowspan="2">部份負擔</td>
                            <td style="text-align: center; vertical-align: middle" rowspan="2">申請費用</td>
                            <td style="text-align: center; vertical-align: middle" rowspan="2">身份別</td>
                            <td style="text-align: center; vertical-align: middle" rowspan="2">備註</td>
                        </tr>
                        <tr style="font-size: {font_size}">
                            <td style="text-align: center;">A31</td>
                            <td style="text-align: center;">A32</td>
                            <td style="text-align: center;">是</td>
                            <td style="text-align: center;">否</td>
                        </tr>
                        {daily_list}
                    </tbody>
                </table>
            </body>
            </html>
        '''

        return html

    def _get_ins_apply_row(self, case_key):
        sql = f'''
            SELECT DiagCode, InsApplyFee, InsTotalFee FROM insapply
            WHERE
                CaseKey1 = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
        else:
            row = None

        return row

    def _get_daily_list(self, case_date, font_size):
        tour_area = None
        sql = f'''
            SELECT cases.*,
                patient.Birthday, patient.Gender, patient.Address, patient.Telephone, patient.ID
            FROM cases
                LEFT JOIN patient ON cases.PatientKey = patient.PatientKey
            WHERE
                DATE(CaseDate) = "{case_date.date()}" AND
                RegistType = "照護機構中醫照護" AND
                cases.InsType = "健保" AND
                ApplyType = "申報" AND
                Card != "欠卡"
            ORDER BY CaseKey
        '''
        rows = self.database.select_record(sql)

        html = ''
        for row_no, row in enumerate(rows):
            if tour_area is None and string_utils.xstr(row['TourArea']) != '':
                tour_area = string_utils.xstr(row['TourArea'])

            if string_utils.xstr(row['Gender']) == '男':
                gender_code = '1'
            elif string_utils.xstr(row['Gender']) == '女':
                gender_code = '0'
            else:
                gender_code = ''

            address = string_utils.xstr(row['Address'])

            pres_days = case_utils.get_pres_days(self.database, row['CaseKey'])
            if string_utils.xstr(row['PharmacyType']) == '申報':
                pharmacy_code = 'A31'
            else:
                pharmacy_code = ''

            pharmacy_cell = self._get_pharmacy_cell(pharmacy_code)
            treat_cell = self._get_treat_cell(string_utils.xstr(row['CaseKey']))
            native_cell = self._get_native_cell(address, tour_area)
            share_code = nhi_utils.get_share_code(  # 內含2020.10 新制
                self.database,
                row['CaseDate'].date(),
                string_utils.xstr(row['Share']),
                string_utils.xstr(row['Treatment']),
                number_utils.get_integer(row['Continuance']),
                number_utils.get_integer(row['InterDrugFee']),
                number_utils.get_integer(row['DiagShareFee']),
                number_utils.get_integer(row['DrugShareFee']),
                row
            )
            if share_code in ['S10', 'S20']:
                share_code = ''

            sequence = row_no + 1
            name = string_utils.xstr(row['Name'])
            patient_id = string_utils.xstr(row['ID'])
            birthday = string_utils.xstr(date_utils.west_date_to_nhi_date(row['Birthday'], '-'))
            telephone = string_utils.xstr(row['Telephone'])
            ins_apply_row = self._get_ins_apply_row(row['CaseKey'])
            if ins_apply_row is not None:
                diag_code = string_utils.xstr(ins_apply_row['DiagCode'])
                ins_apply_fee = string_utils.xstr(ins_apply_row['InsApplyFee'])
                ins_total_fee = string_utils.xstr(ins_apply_row['InsTotalFee'])
            else:
                diag_code = nhi_utils.get_diag_code(
                    self.database,
                    self.system_settings,
                    string_utils.xstr(row['Doctor']),
                    string_utils.xstr(row['RegistType']),
                    string_utils.xstr(row['TreatType']),
                    number_utils.get_integer(row['DiagFee']),
                )
                ins_apply_fee = string_utils.xstr(row['InsApplyFee'])
                ins_total_fee = string_utils.xstr(row['InsTotalFee'])

            share_fee = number_utils.get_integer(row['DiagShareFee']) + number_utils.get_integer(row['DrugShareFee'])

            html += f'''
                <tr style="font-size: {font_size}">
                    <td style="text-align: center; vertical-align: middle">{sequence}</td>
                    <td style="text-align: center; vertical-align: middle">{name}</td>
                    <td style="text-align: center; vertical-align: middle">{patient_id}</td>
                    <td style="text-align: center; vertical-align: middle">{birthday}</td>
                    <td style="text-align: center; vertical-align: middle">{gender_code}</td>
                    <td style="text-align: center; vertical-align: middle">{address}</td>
                    <td style="text-align: center; vertical-align: middle">{telephone}</td>
                    <td style="text-align: center; vertical-align: middle">{diag_code}</td>
                    <td style="text-align: center; vertical-align: middle">{pres_days}</td>
                    {pharmacy_cell}
                    {treat_cell}
                    {native_cell}
                    <td style="text-align: center; vertical-align: middle">{ins_total_fee}</td>
                    <td style="text-align: center; vertical-align: middle">{share_fee}</td>
                    <td style="text-align: center; vertical-align: middle">{ins_apply_fee}</td>
                    <td style="text-align: center; vertical-align: middle">{share_code}</td>
                </tr>
            '''

        return html

    @staticmethod
    def _get_pharmacy_cell(pharmacy_code):
        pharmacy_cell_list = [
            '<td style="text-align: center; vertical-align: middle"></td>',
            '<td style="text-align: center; vertical-align: middle"></td>',
        ]
        if pharmacy_code == '':
            return ''.join(pharmacy_cell_list)

        pharmacy_cell_dict = {
            'A31': 0, 'A32': 1,
        }
        pharmacy_cell_list[pharmacy_cell_dict[pharmacy_code]] = \
            '<td style="text-align: center; vertical-align: middle">V</td>'

        return ''.join(pharmacy_cell_list)

    def _get_treat_cell(self, case_key):
        treat_code = nhi_utils.get_treat_code(self.database, case_key)
        if treat_code in ['', None]:
            treat_code = ''

        treat_cell_list = [
            f'<td style="text-align: center; vertical-align: middle">{treat_code}</td>',
            '<td style="text-align: center; vertical-align: middle"></td>',
            '<td style="text-align: center; vertical-align: middle"></td>',
            '<td style="text-align: center; vertical-align: middle"></td>',
            '<td style="text-align: center; vertical-align: middle"></td>',
            '<td style="text-align: center; vertical-align: middle"></td>',
        ]

        return ''.join(treat_cell_list)

    @staticmethod
    def _get_native_cell(address, tour_area):
        native_cell_list = [
            '<td style="text-align: center; vertical-align: middle"></td>',
            '<td style="text-align: center; vertical-align: middle"></td>',
        ]

        # try:
        #     if address == '' or tour_area in address:
        #         index = 0
        #     else:
        #         index = 1
        # except TypeError:
        #     index = 0

        index = 0  # 全部設定為當地居民
        native_cell_list[index] = '<td style="text-align: center; vertical-align: middle">V</td>'

        return ''.join(native_cell_list)

    def _display_ins_tour_apply(self):
        sql = f'''
            SELECT *, cases.TourArea FROM insapply
                LEFT JOIN cases ON insapply.CaseKey1 = cases.CaseKey
            WHERE
                ApplyDate = "{self.apply_date}" AND
                insapply.ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType = "25" AND
                SpecialCode1 = "C6"
            GROUP BY insapply.CaseDate
        '''
        rows = self.database.select_record(sql)
        tour_apply_html = self._get_tour_apply_html(rows, '12px')
        self.ui.textEdit_tour_apply.setHtml(tour_apply_html)

    def _get_tour_apply_html(self, rows, font_size='12px'):
        doctor_list = self._get_doctor_list(rows, font_size)
        apply_list = self._get_apply_list(rows, font_size)
        apply_year = self.year - 1911
        apply_month = self.month
        clinic_id = self.system_settings.field('院所代號')
        clinic_name = self.system_settings.field('院所名稱')
        owner = self.system_settings.field('負責醫師')
        address = self.system_settings.field('院所地址')
        telephone = self.system_settings.field('院所電話')

        html = f'''
            <html>
            <body>
                <h3 style="text-align: center;">全民健康保險中醫門診總額醫療資源不足地區醫療服務計畫論次費用申請表</h3>
                <h4 style="text-align: right; margin-right: 30px">
                    {apply_year} 年 {apply_month} 月, 第 1 頁共 1 頁
                </h4>
                <table align=center cellpadding="0" cellspacing="0" width="98%"
                 style="border-width: 1px; border-style: solid;">
                    <tbody>
                        <tr style="font-size: {font_size}">
                            <td style="text-align: center; vertical-align: middle" colspan="2">受理日期</td>
                            <td colspan="2"></td>
                            <td style="text-align: center; vertical-align: middle" colspan="6">受理編號</td>
                            <td colspan="2"></td>
                        </tr>
                        <tr style="font-size: {font_size}">
                            <td style="text-align: center; vertical-align: middle" colspan="2">醫事服務機構名稱</td>
                            <td style="text-align: center; vertical-align: middle" colspan="2">{clinic_name}</td>
                            <td style="text-align: center; vertical-align: middle" colspan="6">醫事服務機構代號</td>
                            <td style="text-align: center; vertical-align: middle" colspan="2">{clinic_id}</td>
                        </tr>
                        <tr style="font-size: {font_size}">
                            <td style="text-align: center; vertical-align: middle">編號</td>
                            <td style="text-align: center; vertical-align: middle">醫事人員姓名</td>
                            <td style="text-align: center; vertical-align: middle">醫事人員身份證號</td>
                            <td style="text-align: center; vertical-align: middle">支付別</td>
                            <td style="text-align: center; vertical-align: middle">日期</td>
                            <td style="text-align: center; vertical-align: middle">鄉(鎮)名</td>
                            <td style="text-align: center; vertical-align: middle">村(里)名</td>
                            <td style="text-align: center; vertical-align: middle">地點</td>
                            <td style="text-align: center; vertical-align: middle">診療人次</td>
                            <td style="text-align: center; vertical-align: middle">申請金額</td>
                            <td style="text-align: center; vertical-align: middle">核減額</td>
                            <td style="text-align: center; vertical-align: middle">核定額</td>
                        </tr>
                        {doctor_list}
                        <tr style="font-size: {font_size}">
                            <td style="text-align: center; vertical-align: middle;" rowspan="9">
                                <br><br>總<br><br><br>表<br><br>
                            </td>
                            <td style="text-align: center; vertical-align: middle">支付別/項目</td>
                            <td style="text-align: center; vertical-align: middle">申請次數</td>
                            <td style="text-align: center; vertical-align: middle">診療人次</td>
                            <td style="text-align: center; vertical-align: middle">每次申請金額</td>
                            <td style="text-align: center; vertical-align: middle">申請金額總數</td>
                            <td style="text-align: center; vertical-align: middle" colspan="2">核減次數</td>
                            <td style="text-align: center; vertical-align: middle" colspan="2">核減金額</td>
                            <td style="text-align: center; vertical-align: middle">核定次數</td>
                            <td style="text-align: center; vertical-align: middle">核定金額</td>
                        </tr>
                        {apply_list}
                    </tbody>
                </table>
                <table align=center cellpadding="0" cellspacing="0" width="98%"
                 style="border-width: 1px; border-style: solid;">
                    <tbody>
                        <tr style="font-size: {font_size}">
                            <td style="padding-left: 20%" width="35%">
                                <br>
                                負責醫師姓名: {owner}<br><br>
                                醫事服務機構地址: {address}<br><br>
                                電話: {telephone}<br><br>
                                印信: <br><br><br>
                            </td>
                            <td style="padding-left: 10%" width="65%">
                                一、本項巡迴醫療應經當地衛生主管機關許可，並報經保險人分區業務組同意始得給支付。<br>
                                二、編號：每月填送均自1號起編。總表欄 : 於最後一頁填寫；診療人次：填寫當次診療之人次。<br>
                                三、支付別：中醫：中醫門診巡迴醫療服務計畫：論次費用「次」計填寫。<br>
                                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                P23064 中醫資源不足地區中醫師巡迴醫療費用（次）。<br>
                                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                P23007 一級偏遠地區中醫師巡迴醫療費用（次）。<br>
                                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                P23063 二級偏遠地區中醫師巡迴醫療費用（次）。<br>
                                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                P23008 山地地區中醫師巡迴醫療費用（次）。<br>
                                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                P23009 一級離島中醫師巡迴醫療費用（次）。<br>
                                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                P23010 二級離島中醫師巡迴醫療費用（次）。<br>
                                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                P23011 三級離島中醫師巡迴醫療費用（次）。<br>
                                四、填寫時請依同一醫事人員姓名、同一「支付別」集中申報。<br>
                                五、本申請表應於次月20日前連同門診費用申報寄保險人分區業務組，惟請另置於信封內，
                                並於信封上註明中醫門診巡迴醫療服務計畫（論次費用）。<br>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </body>
            </html>
        '''

        return html

    def _get_doctor_list(self, rows, font_size):
        row_count = len(rows)

        html = ''
        total_case_count = 0
        total_tour_fee = 0
        self.tour_ins_code_list = []
        for row_no, row in enumerate(rows):
            if row['CaseDate'] is None:
                continue

            sequence = row_no + 1
            tour_area = string_utils.xstr(row['TourArea'])
            case_date = date_utils.west_date_to_nhi_date(row['CaseDate'], '-')
            case_count = self._get_case_count(row['CaseDate'])
            total_case_count += case_count
            if tour_area != '':
                tour_area_code = nhi_utils.TOUR_AREA_DICT[tour_area]
                tour_ins_code = nhi_utils.TOUR_INS_CODE_DICT[tour_area_code]
                tour_apply_fee = nhi_utils.TOUR_INS_FEE_DICT[tour_ins_code]
                total_tour_fee += tour_apply_fee
                self.tour_ins_code_list.append([tour_ins_code, case_count])
            else:
                tour_ins_code = ''
                tour_apply_fee = ''

            doctor_name = string_utils.xstr(row['DoctorName'])
            doctor_id = string_utils.xstr(row['DoctorID'])

            html += f'''
                <tr style="font-size: {font_size}">
                    <td style="text-align: center; vertical-align: middle">{sequence}</td>
                    <td style="text-align: center; vertical-align: middle">{doctor_name}</td>
                    <td style="text-align: center; vertical-align: middle">{doctor_id}</td>
                    <td style="text-align: center; vertical-align: middle">{tour_ins_code}</td>
                    <td style="text-align: center; vertical-align: middle">{case_date}</td>
                    <td style="text-align: center; vertical-align: middle">{tour_area}</td>
                    <td style="text-align: center; vertical-align: middle"></td>
                    <td style="text-align: center; vertical-align: middle"></td>
                    <td style="text-align: center; vertical-align: middle">{case_count}</td>
                    <td style="text-align: center; vertical-align: middle">{tour_apply_fee}</td>
                </tr>
            '''

        total_row = 6
        if row_count < total_row:
            for i in range(total_row-row_count):
                html += '''
                    <tr>
                        <td style="text-align: center; vertical-align: middle"></td>
                        <td style="text-align: center; vertical-align: middle"></td>
                        <td style="text-align: center; vertical-align: middle"></td>
                        <td style="text-align: center; vertical-align: middle"></td>
                        <td style="text-align: center; vertical-align: middle"></td>
                        <td style="text-align: center; vertical-align: middle"></td>
                        <td style="text-align: center; vertical-align: middle"></td>
                        <td style="text-align: center; vertical-align: middle"></td>
                        <td style="text-align: center; vertical-align: middle"></td>
                        <td style="text-align: center; vertical-align: middle"></td>
                        <td style="text-align: center; vertical-align: middle"></td>
                        <td style="text-align: center; vertical-align: middle"></td>
                    </tr>
                '''

        html += f'''
            <tr style="font-size: {font_size}">
                <td style="text-align: center; vertical-align: middle" colspan="2">本頁小計</td>
                <td style="text-align: center; vertical-align: middle"></td>
                <td style="text-align: center; vertical-align: middle"></td>
                <td style="text-align: center; vertical-align: middle"></td>
                <td style="text-align: center; vertical-align: middle"></td>
                <td style="text-align: center; vertical-align: middle"></td>
                <td style="text-align: center; vertical-align: middle"></td>
                <td style="text-align: center; vertical-align: middle">{total_case_count}</td>
                <td style="text-align: center; vertical-align: middle">{total_tour_fee}</td>
                <td style="text-align: center; vertical-align: middle"></td>
                <td style="text-align: center; vertical-align: middle"></td>
            </tr>
        '''

        return html

    def _get_apply_list(self, rows, font_size):
        html = ''
        col_no = 0
        total_ins_code_count = 0
        total_case_count = 0
        total_fee = 0
        for ins_code in list(nhi_utils.TOUR_INS_FEE_DICT.keys()):
            col_no += 1
            ins_code_count = 0
            case_count = 0
            for item in self.tour_ins_code_list:
                if ins_code == item[0]:
                    ins_code_count += 1
                    case_count += item[1]

            tour_apply_fee = nhi_utils.TOUR_INS_FEE_DICT[ins_code]
            total_ins_code_count += ins_code_count
            total_case_count += case_count
            total_apply_fee = ins_code_count * tour_apply_fee
            total_fee += total_apply_fee
            html += f'''
                <tr style="font-size: {font_size}">
                    <td style="text-align: center; vertical-align: middle;">{ins_code}</td>
                    <td style="text-align: center; vertical-align: middle;">{ins_code_count}</td>
                    <td style="text-align: center; vertical-align: middle;">{case_count}</td>
                    <td style="text-align: center; vertical-align: middle;">{tour_apply_fee}</td>
                    <td style="text-align: center; vertical-align: middle;">{total_apply_fee}</td>
                    <td style="text-align: center; vertical-align: middle;" colspan="2"></td>
                    <td style="text-align: center; vertical-align: middle;" colspan="2"></td>
                </tr>
            '''

        html += f'''
            <tr style="font-size: {font_size}">
                <td style="text-align: center; vertical-align: middle;">總計</td>
                <td style="text-align: center; vertical-align: middle;">{total_ins_code_count}</td>
                <td style="text-align: center; vertical-align: middle;">{total_case_count}</td>
                <td style="text-align: center; vertical-align: middle;"></td>
                <td style="text-align: center; vertical-align: middle;">{total_fee}</td>
                <td style="text-align: center; vertical-align: middle;" colspan="2"></td>
                <td style="text-align: center; vertical-align: middle;" colspan="2"></td>
            </tr>
        '''

        return html

    def _get_case_count(self, case_date):
        sql = f'''
            SELECT CaseDate FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                insapply.ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType = "25" AND
                CaseDate = "{case_date.date()}"
        '''
        rows = self.database.select_record(sql)

        return len(rows)

    # 列印日報表
    def _print_daily_list(self):
        for row_no in range(self.ui.tableWidget_daily_list.rowCount()):
            text_edit = self.ui.tableWidget_daily_list.cellWidget(row_no, 0)
            html = text_edit.toHtml()
            printer_utils.print_form_html(
                self, self.database, self.system_settings, html, 'landscape'
            )

    # 列印費用申請表
    def _print_tour_apply(self):
        html = self.ui.textEdit_tour_apply.toHtml()
        printer_utils.print_form_html(
            self, self.database, self.system_settings, html, 'landscape'
        )

    def _export_daily_list(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{self.year}年{self.month}月照護機構中醫照護方案門診日報表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        clinic_id = self.system_settings.field('院所代號')
        export_utils.export_nursing_home_list_to_excel(
            self.database, self.system_settings, excel_file_name, self.year, self.month, clinic_id,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )
