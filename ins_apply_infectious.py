
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import calendar

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import nhi_utils
from libs import printer_utils
from libs import string_utils
from libs import case_utils
from libs import charge_utils
from libs import export_utils
from libs import prescript_utils
from libs import dialog_utils
from libs import personnel_utils


# 清冠一號補助報表 2022.05.25
class InsApplyInfectious(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(InsApplyInfectious, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = args[2]
        self.apply_month = args[3]
        self.period = args[4]
        self.apply_type = args[5]
        self.clinic_id = args[6]

        self.ui = None
        self.infectious_apply_count = 0

        self.dialog_setting = {
            "dialog_executed": False,
            "year": None,
            "month": None,
        }

        self.clinic_name = self.system_settings.field('院所名稱')
        self.clinic_id = self.system_settings.field('院所代號')
        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()

        if self.apply_year is not None and self.apply_month is not None:
            self.apply_date = nhi_utils.get_apply_date(self.apply_year, self.apply_month)
        else:
            self.open_dialog()

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INS_APPLY_INFECTIOUS, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_infectious = class_utils.get_table_widget(
            self.ui.tableWidget_infectious, self.database)
        self.table_widget_infectious.set_column_hidden([0])
        self._set_table_width()
        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.toolButton_export_excel.setEnabled(False)
            self.ui.toolButton_export_pdf.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_print_list.clicked.connect(self._print_infectious)
        self.ui.toolButton_export_pdf.clicked.connect(self._export_to_pdf)
        self.ui.toolButton_export_excel.clicked.connect(self._export_to_excel)
        self.ui.tableWidget_infectious.doubleClicked.connect(self._open_medical_record)

    def _set_table_width(self):
        width = [100, 120, 200, 90, 90, 90, 120, 230, 130, 80, 100, 140, 140, 120]
        self.table_widget_infectious.set_table_heading_width(width)

    def _open_medical_record(self):
        case_key = self.table_widget_infectious.field_value(0)
        try:
            self.parent.parent.open_medical_record(case_key, '健保申報')
        except AttributeError:
            self.parent.open_medical_record(case_key, '健保申報')

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_date_picker(self, self.database, self.system_settings, None)

        if self.dialog_setting['dialog_executed']:
            dialog.ui.comboBox_year.setCurrentText(self.dialog_setting['year'])
            dialog.ui.comboBox_month.setCurrentText(self.dialog_setting['month'])

        if not dialog.exec_():
            dialog.deleteLater()
            self.apply_date = None
            return

        year = dialog.ui.comboBox_year.currentText()
        month = dialog.ui.comboBox_month.currentText()

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['year'] = year
        self.dialog_setting['month'] = month

        dialog.deleteLater()
        self._calculate_by_medical_record(year, month)

    def calculate_by_ins_apply(self):
        apply_type_code = nhi_utils.APPLY_TYPE_CODE[self.apply_type]

        sql = f'''
            SELECT * FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType = "C5"
            GROUP BY CaseKey1
            ORDER BY Sequence
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.set_table_data(rows)

    def _calculate_by_medical_record(self, year, month):
        last_day = calendar.monthrange(int(year), int(month))[1]
        start_date = f'{year}-{month}-1 00:00:00'
        end_date = f'{year}-{month}-{last_day} 23:59:59'
        self.apply_date = f'{int(year)-1911:0>3}{month:0>2}'

        sql = f'''
            SELECT cases.*, cases.Share AS ShareCode, patient.Birthday FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
                LEFT JOIN prescript ON prescript.CaseKey = cases.CaseKey
            WHERE
                cases.CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                cases.InsType = "健保" AND
                Card != "欠卡" AND
                (cases.Share = "{nhi_utils.INFECTIOUS_INJURY_TYPE[0]}" OR
                 cases.Injury = "{nhi_utils.INFECTIOUS_INJURY_TYPE[0]}" OR
                 prescript.MedicineName LIKE "%台灣清冠一號%")
            GROUP BY CaseKey ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.set_table_data(rows)

    def set_table_data(self, rows):
        self.ui.tableWidget_infectious.setRowCount(0)  # 歸零
        for row in rows:
            try:
                case_key = row['CaseKey1']
            except KeyError:
                case_key = row['CaseKey']

            if case_key is None:
                continue

            infectious_drug = prescript_utils.get_infectious_drug(self.database, case_key)
            if infectious_drug not in ['台灣清冠一號', '台灣清冠一號及科學中藥']:
                continue

            self._set_infectious_row(row, case_key)
            self.infectious_apply_count += 1

    def _get_infectious_drug(self, case_key):
        infectious_drug_name = '台灣清冠一號濃縮顆粒'
        ins_code = None
        dosage = 0
        unit = None

        sql = f'''
            SELECT prescript.MedicineName, InsCode, Dosage, Unit FROM prescript
                LEFT JOIN cases ON cases.CaseKey = prescript.CaseKey
            WHERE
                prescript.CaseKey = {case_key} AND
                MedicineSet = 1 AND
                MedicineName LIKE "%清冠一號%"
            LIMIT 1
        '''
        rows = self.database.select_record(sql)

        if len(rows) > 0:
            infectious_drug_name = string_utils.xstr(rows[0]['MedicineName'])
            ins_code = rows[0]['InsCode']
            dosage = rows[0]['Dosage']
            unit = rows[0]['Unit']

        infectious_drug_name = self._get_formal_drug_name(infectious_drug_name, ins_code)

        return infectious_drug_name, dosage, unit

    def _get_formal_drug_name(self, infectious_drug_name, ins_code):
        if '順' in infectious_drug_name:
            infectious_drug_name = '“順天堂”RespireAid臺灣清冠一號濃縮顆粒'
        elif '莊' in infectious_drug_name:
            infectious_drug_name = '“莊松榮”臺灣清冠一號濃縮顆粒'
        elif '康' in infectious_drug_name:
            infectious_drug_name = '康福顆粒(臺灣清冠一號)'
        elif '勸' in infectious_drug_name:
            infectious_drug_name = '“勸奉堂”臺灣清冠一號濃縮顆粒'
        elif '勝' in infectious_drug_name:
            infectious_drug_name = '“勝昌”臺灣清冠一號濃縮顆粒'
        elif '華' in infectious_drug_name:
            infectious_drug_name = '“華佗”臺灣清冠一號濃縮顆粒'
        elif '漢' in infectious_drug_name:
            infectious_drug_name = '“漢聖”臺灣清冠一號濃縮顆粒'
        elif '天明' in infectious_drug_name:
            infectious_drug_name = '“天明”臺灣清冠一號濃縮顆粒'
        elif '天' in infectious_drug_name:
            infectious_drug_name = '“天一”臺灣清冠一號濃縮顆粒'
        elif '科' in infectious_drug_name:
            infectious_drug_name = '“科達”臺灣清冠一號濃縮顆粒'
        elif '富' in infectious_drug_name:
            infectious_drug_name = '“富田”臺灣清冠一號濃縮顆粒'
        else:
            infectious_drug_name = '臺灣清冠一號濃縮顆粒'

        return infectious_drug_name

    def _get_weight(self, infectious_drug_name):
        if '順' in infectious_drug_name:
            weight = 5
        elif '莊' in infectious_drug_name:
            weight = 10
        elif '康' in infectious_drug_name:
            weight = 10
        elif '勸' in infectious_drug_name:
            weight = 10
        elif '勝' in infectious_drug_name:
            weight = 5
        elif '華' in infectious_drug_name:
            weight = 5
        elif '漢' in infectious_drug_name:
            weight = 5
        elif '天明' in infectious_drug_name:
            weight = 10
        elif '天' in infectious_drug_name:
            weight = 5
        else:
            weight = None

        return weight

    def _set_infectious_row(self, row, case_key):
        row_no = self.ui.tableWidget_infectious.rowCount()
        self.ui.tableWidget_infectious.setRowCount(row_no+1)

        infectious_drug_name, dosage, unit = self._get_infectious_drug(case_key)
        case_date, _ = case_utils.get_case_date(self.database, case_key)
        infectious_drug_fee = charge_utils.get_ins_fee_from_ins_code(self.database, 'E5012C', case_date=case_date)
        packages = case_utils.get_packages(self.database, case_key)
        pres_days = case_utils.get_pres_days(self.database, case_key)
        try:
            if dosage == 1:
                total_dosage = packages * pres_days
            else:
                total_dosage = dosage * pres_days
        except Exception:
            total_dosage = 0

        if unit == '包':
            weight = self._get_weight(infectious_drug_name)
            if weight is not None:
                total_dosage *= weight
                unit = '克'

        is_infectious_case = '☑'
        # if row['ShareCode'] in ['914'] + nhi_utils.INFECTIOUS_INJURY_TYPE:
        #     is_infectious_case = '☑'
        # else:
        #     is_infectious_case = '☐'

        try:
            birthday = row['Birthday'].strftime('%Y/%m/%d')
        except Exception:
            birthday = None

        isolation_position = case_utils.get_case_extend(self.database, case_key, '隔離處所')
        if isolation_position in ['', None]:
            isolation_position = '居家'

        infectious_row = [
            string_utils.xstr(case_key),
            self.clinic_id,
            self.clinic_name,
            self.apply_date,
            string_utils.xstr(infectious_drug_fee * pres_days),
            string_utils.xstr(row['Name']),
            birthday,
            infectious_drug_name,
            row['CaseDate'].strftime('%Y/%m/%d'),
            string_utils.xstr(pres_days),
            string_utils.xstr(int(total_dosage)),
            is_infectious_case,
            '☑',
            isolation_position,
        ]

        for col_no in range(len(infectious_row)):
            self.ui.tableWidget_infectious.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(infectious_row[col_no]))
            if col_no in [4, 9, 10]:
                self.ui.tableWidget_infectious.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [3, 6, 8, 11, 12, 13]:
                self.ui.tableWidget_infectious.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _get_html(self):
        body = self._get_html_body()

        html = f'''
            <html>
            <body>
                <div>
                    <h3 style="text-align: center;">醫療機構「公費清冠一號藥品費用」申請補助清冊</h3>
                </div>
                <div>
                    <table align=center cellpadding="2" cellspacing="0" width="98%"
                     style="border-width: 1px; border-style: solid;">
                        <thead>
                            <tr>
                                <th style="text-align: center; vertical-align: middle" rowspan="2">序號</th>
                                <th style="text-align: center" colspan="4">院所資訊</th>
                                <th style="text-align: center" colspan="2">個案資訊</th>
                                <th style="text-align: center" colspan="4">藥品資訊</th>
                                <th style="text-align: center" colspan="3">院所查檢欄位</th>
                            </tr>
                            <tr>
                                <th style="text-align: center; vertical-align: middle">醫事機構代碼</th>
                                <th style="text-align: center; vertical-align: middle">醫療機構名稱</th>
                                <th style="text-align: center; vertical-align: middle">費用年月</th>
                                <th style="text-align: center; vertical-align: middle">申請費用</th>
                                <th style="text-align: center; vertical-align: middle">姓名</th>
                                <th style="text-align: center; vertical-align: middle">出生日期</th>
                                <th style="text-align: center; vertical-align: middle">藥品品名</th>
                                <th style="text-align: center; vertical-align: middle">用藥起始日</th>
                                <th style="text-align: center; vertical-align: middle">用藥天數</th>
                                <th style="text-align: center; vertical-align: middle">開立總克數</th>
                                <th style="text-align: center; vertical-align: middle">COVID-19確診</th>
                                <th style="text-align: center; vertical-align: middle">個案簽署同意書</th>
                                <th style="text-align: center; vertical-align: middle">個案收治處所</th>
                            </tr>
                        </thead>
                        <tbody>
                            {body}
                        </tbody>
                    </table>
                </div>
            </body>
            </html>
        '''

        return html

    def _get_html_body(self):
        html = ''
        for row_no in range(self.ui.tableWidget_infectious.rowCount()):
            clinic_id = self.ui.tableWidget_infectious.item(row_no, 1).text()
            clinic_name = self.ui.tableWidget_infectious.item(row_no, 2).text()
            apply_date = self.ui.tableWidget_infectious.item(row_no, 3).text()
            apply_fee = self.ui.tableWidget_infectious.item(row_no, 4).text()
            name = self.ui.tableWidget_infectious.item(row_no, 5).text()
            birthday = self.ui.tableWidget_infectious.item(row_no, 6).text()
            medicine_name = self.ui.tableWidget_infectious.item(row_no, 7).text()
            case_date = self.ui.tableWidget_infectious.item(row_no, 8).text()
            pres_days = self.ui.tableWidget_infectious.item(row_no, 9).text()
            total_dosage = self.ui.tableWidget_infectious.item(row_no, 10).text()
            is_infectious_case = self.ui.tableWidget_infectious.item(row_no, 11).text()
            agreement = self.ui.tableWidget_infectious.item(row_no, 12).text()
            position = self.ui.tableWidget_infectious.item(row_no, 13).text()

            html += f'''
                <tr>
                    <td style="text-align:center; vertical-align: middle">{row_no+1}</td>
                    <td style="text-align:center; vertical-align: middle">{clinic_id}</td>
                    <td style="text-align:center; vertical-align: middle">{clinic_name}</td>
                    <td style="text-align:center; vertical-align: middle">{apply_date}</td>
                    <td style="text-align:center; vertical-align: middle">{apply_fee}</td>
                    <td style="text-align:center; vertical-align: middle">{name}</td>
                    <td style="text-align:center; vertical-align: middle">{birthday}</td>
                    <td style="text-align:center; vertical-align: middle">{medicine_name}</td>
                    <td style="text-align:center; vertical-align: middle">{case_date}</td>
                    <td style="text-align:center; vertical-align: middle">{pres_days}</td>
                    <td style="text-align:center; vertical-align: middle">{total_dosage}</td>
                    <td style="text-align:center; vertical-align: middle">{is_infectious_case}</td>
                    <td style="text-align:center; vertical-align: middle">{agreement}</td>
                    <td style="text-align:center; vertical-align: middle">{position}</td>
                </tr>
            '''

        return html

    # 列印費用申請表
    def _print_infectious(self):
        html = self._get_html()
        printer_utils.print_form_html(
            self, self.database, self.system_settings, html, 'landscape'
        )

    def _export_to_pdf(self):
        if self.ui.tableWidget_infectious.rowCount() == 0:
            return

        filename = f'{self.clinic_name}{self.apply_date}清冠一號藥品補助清冊.pdf'
        html = self._get_html()
        printer_utils.print_form_html(
            self, self.database, self.system_settings, html,
            orientation='landscape',  print_type='pdf', filename=filename,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>{filename}匯出完成.</h3>',
            'PDF 格式.'
        )

    def _export_to_excel(self):
        if self.ui.tableWidget_infectious.rowCount() == 0:
            return

        filename = f'{self.clinic_name}{self.apply_date}清冠一號藥品補助清冊.xlsx'

        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "清冠一號藥品補助清冊",
            filename,
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_infectious_list(self.system_settings, excel_file_name, self.ui.tableWidget_infectious)

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>專案銷售明細表{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )
