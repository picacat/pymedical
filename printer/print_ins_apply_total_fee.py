
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtPrintSupport import QPrinter
import os

from libs import printer_utils
from libs import system_utils
from libs import nhi_utils


# 列印申請總表
# 2018.07.09
class PrintInsApplyTotalFee:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ins_total_fee = args[2]
        self.ui = None

        self.ins_apply_path = nhi_utils.get_dir(self.system_settings, '申報路徑')
        self.printer = printer_utils.get_printer(self.system_settings, '報表印表機')
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
        self.font = QtGui.QFont(font, 10, QtGui.QFont.PreferQuality)

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
        apply_year = self.ins_total_fee['apply_year'] - 1911
        apply_month = self.ins_total_fee['apply_month']
        apply_date = f'{apply_year:0>3}年{apply_month:0>2}月'

        export_dir = f'{self.ins_apply_path}/申請總表'
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        pdf_file_name = f'{export_dir}/申請總表{apply_date}.pdf'
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self.parent, "匯出申請總表pdf",
            pdf_file_name,
            "所有檔案 (*);;pdf檔 (*.pdf)", options=options
        )
        if not file_name:
            return

        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(file_name)
        self.print_html(True)
        system_utils.show_message_box(
            QMessageBox.Information,
            '匯出完成',
            '<font size="5" color="red"><b>申請總表pdf檔案已匯出完成</b></font>',
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
        document.setHtml(self._get_html(self.ins_total_fee))
        if printing:
            document.print(self.printer)

    def _get_html(self, ins_total_fee):
        apply_year = ins_total_fee['apply_year'] - 1911
        apply_month = ins_total_fee['apply_month']
        apply_period = ins_total_fee['apply_period']
        apply_date = f'{apply_year:0>3}年{apply_month:0>2}月 {apply_period}'

        if ins_total_fee['apply_type'] == '1':
            apply_type_name = '1送核'
        else:
            apply_type_name = '2補報'

        ins_generate_year = ins_total_fee['ins_generate_date'].year() - 1911
        ins_generate_month = ins_total_fee['ins_generate_date'].month()
        ins_generate_day = ins_total_fee['ins_generate_date'].day()
        generate_date = f'{ins_generate_year:0>3}年{ins_generate_month:0>2}月{ins_generate_day:0>2}日'

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
        clinic_address = self.system_settings.field('院所地址')
        clinic_telephone = self.system_settings.field('院所電話')
        general_count = ins_total_fee['general_count']
        general_amount = ins_total_fee['general_amount']
        special_count = ins_total_fee['special_count']
        special_amount = ins_total_fee['special_amount']
        tcm_count = ins_total_fee['tcm_count']
        tcm_amount = ins_total_fee['tcm_amount']
        chronical_count = ins_total_fee['chronical_count']
        chronical_amount = ins_total_fee['chronical_amount']
        total_count = ins_total_fee['total_count']
        total_amount = ins_total_fee['total_amount']
        share_count = ins_total_fee['share_count']
        share_amount = ins_total_fee['share_amount']

        html = f'''
            <html>
                <body>
                    <div>
                        <table align=center cellpadding="1" cellspacing="0" width="95%">
                            <tbody>
                                <tr>
                                    <td width="90%" style="text-align: center;">
                                        <h3>特約醫事服務機構門診醫療服務點數申報總表</h3>
                                    </td>
                                    <td width="10%" style="text-align: right;">
                                        <h3>中醫</h3>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                        <br>
                        <table align=center cellpadding="1" cellspacing="0" width="95%"
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
                        <table align=center cellpadding="1" cellspacing="0" width="95%"
                         style="border-width: 1px; border-style: solid;">
                        <tbody>
                            <tr>
                                <td width="15%" style="text-align: center;" colspan="2">類別</td>
                                <td width="20%" style="text-align: center;" colspan="2">件數</td>
                                <td width="20%" style="text-align: center;" colspan="2">申請點數</td>
                                <td style="padding-left: 20%; text-align: left;" rowspan="20">
                                    <br>
                                    負責醫師姓名: {owner}<br>
                                    <br>
                                    醫事服務機構地址: {clinic_address}<br>
                                    <br>
                                    電話: {clinic_telephone}<br>
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
                            <tr>
                                <td style="text-align: center;"><br><br><br>注<br>意<br>事<br>項<br></td>
                                <td colspan="5" rowspan="10">
                                    一、使用本表免另行辦函，請填送一式兩份。<br>
                                    二、書面申報醫療費用者，應檢附本表及醫療服務點數清單暨醫令清單。<br>
                                    三、媒體申報醫療費用者，僅需填本表及送媒體(磁片或磁帶)。<br>
                                    四、連線申報醫療費用者，僅需填寫本表。<br>
                                    五、
                                    <ul>
                                        <li>一般案件係指特約診所之日劑藥費申報案件（即案件分類：01、11、21）。</li>
                                        <li>西醫專案案件範圍請參閱媒體申報格式之填表說明。</li>
                                    </ul>
                                    六、本表各欄位請按照媒體申報格式之填表說明填寫。
                                </td>
                            </tr>
                        </tbody>
                        </table>
                    </div>
                </body>
            </html>
        '''

        return html
