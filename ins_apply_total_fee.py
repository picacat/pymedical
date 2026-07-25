# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import nhi_utils
from libs import number_utils
from libs import printer_utils


# 申請總表 2018.10.01
class InsApplyTotalFee(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(InsApplyTotalFee, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = args[2]
        self.apply_month = args[3]
        self.start_date = args[4]
        self.end_date = args[5]
        self.period = args[6]
        self.apply_type = args[7]
        self.clinic_id = args[8]
        self.ins_generate_date = args[9]
        self.ins_calculated_table = args[10]
        self.ui = None

        self.apply_date = nhi_utils.get_apply_date(self.apply_year, self.apply_month)
        self.apply_type_code = nhi_utils.APPLY_TYPE_CODE[self.apply_type]

        self.ins_total_fee = {
            'apply_year': self.apply_year,
            'apply_month': self.apply_month,
            'apply_period': self.period,
            'apply_type': self.apply_type_code,
            'apply_date': self.apply_date,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'clinic_id': self.clinic_id,
            'period': self.period,
            'ins_generate_date': self.ins_generate_date,
        }
        self._set_ui()
        self._set_signal()
        self._display_total_fee()

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INS_APPLY_TOTAL_FEE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_print.clicked.connect(self._print_total_fee)
        self.ui.toolButton_export_pdf.clicked.connect(self._export_pdf)

    def _calculate_total_fee(self):
        (general_count, general_amount, special_count, special_amount, chronical_count, chronical_amount,
         share_count, diag_share_amount, drug_share_amount, share_amount) = self._calculate_fees()

        tcm_count = general_count + special_count
        tcm_amount = general_amount + special_amount

        total_count = general_count + special_count + chronical_count
        total_amount = general_amount + special_amount + chronical_amount

        self.ins_total_fee['general_count'] = general_count
        self.ins_total_fee['general_amount'] = general_amount
        self.ins_total_fee['special_count'] = special_count
        self.ins_total_fee['special_amount'] = special_amount
        self.ins_total_fee['chronical_count'] = chronical_count
        self.ins_total_fee['chronical_amount'] = chronical_amount

        self.ins_total_fee['tcm_count'] = tcm_count
        self.ins_total_fee['tcm_amount'] = tcm_amount
        self.ins_total_fee['total_count'] = total_count
        self.ins_total_fee['total_amount'] = total_amount

        self.ins_total_fee['share_count'] = share_count
        self.ins_total_fee['diag_share_amount'] = diag_share_amount
        self.ins_total_fee['drug_share_amount'] = drug_share_amount
        self.ins_total_fee['share_amount'] = share_amount

    def _display_total_fee(self):
        self._calculate_total_fee()

        html = self._get_html(self.ins_total_fee, '18px')
        self.ui.textEdit_total_fee.setHtml(html)

    def _get_html(self, ins_total_fee, font_size):
        apply_year = ins_total_fee['apply_year'] - 1911
        apply_month = ins_total_fee['apply_month']
        apply_period = ins_total_fee['apply_period']
        apply_date = f'{apply_year:0>3}年{apply_month:0>2}月 {apply_period}'
        if ins_total_fee['apply_type'] == '1':
            apply_type_name = '1送核'
        else:
            apply_type_name = '2補報'

        ins_year = ins_total_fee['ins_generate_date'].year() - 1911
        ins_month = ins_total_fee['ins_generate_date'].month()
        ins_day = ins_total_fee['ins_generate_date'].day()
        generate_date = f'{ins_year:0>3}年{ins_month:0>2}月{ins_day:0>2}日'

        start_year = ins_total_fee['start_date'].year() - 1911
        start_month = ins_total_fee['start_date'].month()
        start_day = ins_total_fee['start_date'].day()
        start_date = f'{start_year:0>3}年{start_month:0>2}月{start_day:0>2}日'

        end_year = ins_total_fee['end_date'].year() - 1911
        end_month = ins_total_fee['end_date'].month()
        end_day = ins_total_fee['end_date'].day()
        end_date = f'{end_year:0>3}年{end_month:0>2}月{end_day:0>2}日'

        clinic_id = self.ins_total_fee['clinic_id']
        clinic_name = self.system_settings.field('院所名稱')
        owner = self.system_settings.field('負責醫師')
        address = self.system_settings.field('院所地址')
        telephone = self.system_settings.field('院所電話')
        general_count = ins_total_fee['general_count']
        general_amount = ins_total_fee['general_amount']
        special_count = ins_total_fee['special_count']
        special_amount = ins_total_fee['special_amount']
        chronical_count = ins_total_fee['chronical_count']
        chronical_amount = ins_total_fee['chronical_amount']

        tcm_count = ins_total_fee['tcm_count']
        tcm_amount = ins_total_fee['tcm_amount']
        total_count = ins_total_fee['total_count']
        total_amount = ins_total_fee['total_amount']

        share_count = ins_total_fee['share_count']
        share_amount = ins_total_fee['share_amount']

        html = f'''
            <html>
            <body>
                <div>
                    <h3 style="text-align: center;">特約醫事服務機構門診醫療服務點數申報總表</h3>
                </div>
                <div>
                    <table align=center cellpadding="2" cellspacing="0" width="85%"
                     style="border-width: 1px; border-style: solid;">
                        <tbody>
                            <tr>
                                <td style="text-align: center;" colspan="2">t1資料格式</td>
                                <td style="text-align: center;" colspan="2">t2服務機構</td>
                                <td style="text-align: center;">t3費用年月</td>
                                <td style="text-align: center;">t4申報方式</td>
                                <td style="text-align: center;">t5申報類別</td>
                                <td style="text-align: center;">t6申報日期</td>
                                <td style="text-align: center;">收文日期</td>
                            </tr>
                            <tr>
                                <td style="text-align: center;">10</td>
                                <td style="text-align: center;">門診申報總表</td>
                                <td style="text-align: center;">{clinic_id}</td>
                                <td style="text-align: center;">{clinic_name}</td>
                                <td style="text-align: center;">{apply_date}</td>
                                <td style="text-align: center;">3網路</td>
                                <td style="text-align: center;">{apply_type_name}</td>
                                <td style="text-align: center;">{generate_date}</td>
                                <td></td>
                            </tr>
                        </tbody>
                    </table>
                    <br>
                    <table align=center cellpadding="1" cellspacing="0" width="85%"
                     style="border-width: 1px; border-style: solid;">
                    <tbody>
                        <tr>
                            <td width="15%" style="text-align: center;" colspan="2">類別</td>
                            <td width="22%" style="text-align: center;" colspan="2">件數</td>
                            <td width="22%" style="text-align: center;" colspan="2">申請點數</td>
                            <td style="padding-left: 20%; text-align: left;" rowspan="20">
                                <br>
                                負責醫師姓名: {owner}<br>
                                <br>
                                醫事服務機構地址: {address}<br>
                                <br>
                                電話: {telephone}<br>
                                <br>
                                印信:
                            </td>
                        </tr>
                        <tr>
                            <td rowspan="5" style="text-align: center;"><br><br>西<br><br>醫</td>
                            <td style="text-align: center;">一般案件</td>
                            <td style="text-align: center;">t7</td>
                            <td style="text-align: center;"></td>
                            <td style="text-align: center;">t8</td>
                            <td style="text-align: center;"></td>
                        </tr>
                        <tr>
                            <td style="text-align: center;">專案案件</td>
                            <td style="text-align: center;">t9</td>
                            <td style="text-align: center;"></td>
                            <td style="text-align: center;">t10</td>
                            <td style="text-align: center;"></td>
                        </tr>
                        <tr>
                            <td style="text-align: center;">洗腎</td>
                            <td style="text-align: center;">t11</td>
                            <td style="text-align: center;"></td>
                            <td style="text-align: center;">t12</td>
                            <td style="text-align: center;"></td>
                        </tr>
                        <tr>
                            <td style="text-align: center;">結核病</td>
                            <td style="text-align: center;">t15</td>
                            <td style="text-align: center;"></td>
                            <td style="text-align: center;">t16</td>
                            <td style="text-align: center;"></td>
                        </tr>
                        <tr>
                            <td style="text-align: center;">小計</td>
                            <td style="text-align: center;">t17</td>
                            <td style="text-align: center;"></td>
                            <td style="text-align: center;">t18</td>
                            <td style="text-align: center;"></td>
                        </tr>
                        <tr>
                            <td rowspan="3" style="text-align: center;"><br>牙<br>醫</td>
                            <td style="text-align: center;">一般案件</td>
                            <td style="text-align: center;">t19</td>
                            <td style="text-align: center;"></td>
                            <td style="text-align: center;">t20</td>
                            <td style="text-align: center;"></td>
                        </tr>
                        <tr>
                            <td style="text-align: center;">專案案件</td>
                            <td style="text-align: center;">t21</td>
                            <td style="text-align: center;"></td>
                            <td style="text-align: center;">t22</td>
                            <td style="text-align: center;"></td>
                        </tr>
                        <tr>
                            <td style="text-align: center;">小計</td>
                            <td style="text-align: center;">t23</td>
                            <td style="text-align: center;"></td>
                            <td style="text-align: center;">t24</td>
                            <td style="text-align: center;"></td>
                        </tr>
                        <tr>
                            <td rowspan="3" style="text-align: center;"><br>中<br>醫</td>
                            <td style="text-align: center;">一般案件</td>
                            <td style="text-align: center;">t25</td>
                            <td style="text-align: right;">{general_count:,}</td>
                            <td style="text-align: center;">t26</td>
                            <td style="text-align: right;">{general_amount:,}</td>
                        </tr>
                        <tr>
                            <td style="text-align: center;">專案案件</td>
                            <td style="text-align: center;">t27</td>
                            <td style="text-align: right;">{special_count:,}</td>
                            <td style="text-align: center;">t28</td>
                            <td style="text-align: right;">{special_amount:,}</td>
                        </tr>
                        <tr>
                            <td style="text-align: center;">小計</td>
                            <td style="text-align: center;">t29</td>
                            <td style="text-align: right;">{tcm_count:,}</td>
                            <td style="text-align: center;">t30</td>
                            <td style="text-align: right;">{tcm_amount:,}</td>
                        </tr>
                        <tr>
                            <td style="text-align: center;" colspan="2">預防保健</td>
                            <td style="text-align: center;">t31</td>
                            <td style="text-align: center;"></td>
                            <td style="text-align: center;">t32</td>
                            <td style="text-align: center;"></td>
                        </tr>
                        <tr>
                            <td style="text-align: center;" colspan="2">慢性病連續處方箋調劑</td>
                            <td style="text-align: center;">t33</td>
                            <td style="text-align: right;">{chronical_count:,}</td>
                            <td style="text-align: center;">t34</td>
                            <td style="text-align: right;">{chronical_amount:,}</td>
                        </tr>
                        <tr>
                            <td style="text-align: center;" colspan="2">居家照護</td>
                            <td style="text-align: center;">t35</td>
                            <td style="text-align: center;"></td>
                            <td style="text-align: center;">t36</td>
                            <td style="text-align: center;"></td>
                        </tr>
                        <tr>
                            <td style="text-align: center;" colspan="2">精神疾病社區復健</td>
                            <td style="text-align: center;">t13</td>
                            <td style="text-align: center;"></td>
                            <td style="text-align: center;">t14</td>
                            <td style="text-align: center;"></td>
                        </tr>
                        <tr>
                            <td style="text-align: center;" colspan="2">總計</td>
                            <td style="text-align: center;">t37</td>
                            <td style="text-align: right;">{total_count:,}</td>
                            <td style="text-align: center;">t38</td>
                            <td style="text-align: right;">{total_amount:,}</td>
                        </tr>
                        <tr>
                            <td style="text-align: center;" colspan="2">部份負擔</td>
                            <td style="text-align: center;">t39</td>
                            <td style="text-align: right;">{share_count:,}</td>
                            <td style="text-align: center;">t40</td>
                            <td style="text-align: right;">{share_amount:,}</td>
                        </tr>
                        <tr>
                            <td style="text-align: center;" colspan="2">本次連線申報起迄日期</td>
                            <td style="text-align: center;">t41</td>
                            <td style="text-align: center;">{start_date}</td>
                            <td style="text-align: center;">t42</td>
                            <td style="text-align: center;">{end_date}</td>
                        </tr>
                    </tbody>
                    </table>
                </div>
            </body>
            </html>
        '''
        return html

    def _calculate_fees(self):
        sql = f'''
            SELECT CaseType, InsApplyFee, DiagShareFee, DrugShareFee, ShareFee
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}"
                ORDER BY CaseType, Sequence
        '''
        rows = self.database.select_record(sql)

        general_count = 0
        general_amount = 0
        special_count = 0
        special_amount = 0
        chronical_count = 0
        chronical_amount = 0

        share_count = 0
        diag_share_amount = 0
        drug_share_amount = 0
        share_amount = 0
        for row in rows:
            if row['CaseType'] == '21':
                general_count += 1
                general_amount += number_utils.get_integer(row['InsApplyFee'])
            elif row['CaseType'] == '28':
                chronical_count += 1
                chronical_amount += number_utils.get_integer(row['InsApplyFee'])
            else:
                special_count += 1
                special_amount += number_utils.get_integer(row['InsApplyFee'])

            diag_share_fee = number_utils.get_integer(row['DiagShareFee'])
            drug_share_fee = number_utils.get_integer(row['DrugShareFee'])
            share_fee = number_utils.get_integer(row['ShareFee'])
            if share_fee > 0:
                share_count += 1

            diag_share_amount += diag_share_fee
            drug_share_amount += drug_share_fee
            share_amount += share_fee

        return (general_count, general_amount, special_count, special_amount, chronical_count, chronical_amount,
                share_count, diag_share_amount, drug_share_amount, share_amount)

    # 列印申請總表
    def _print_total_fee(self):
        self._calculate_total_fee()

        printer_utils.print_form_ins_apply_total_fee(
            self, self.database, self.system_settings,
            self.ins_total_fee,
        )

    # 列印申請總表PDF
    def _export_pdf(self):
        self._calculate_total_fee()

        printer_utils.print_form_ins_apply_total_fee(
            self, self.database, self.system_settings,
            self.ins_total_fee, 'pdf'
        )
