
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
import datetime
import os

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import nhi_utils
from libs import date_utils
from libs import patient_utils


# 初診照護病歷 A4
# 2020.10.07
class PrintPatientNewCare:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]
        self.case_key = args[3]
        self.apply_date = args[4]
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
        # 14: 中醫 A:病歷本文 案件類別 流水號6碼
        export_dir = f'{self.ins_apply_path}/emr{self.apply_date}'
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        pdf_file_name = f'{export_dir}/patient_new_care_{self.patient_key:0>6}.pdf'
        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(pdf_file_name)
        self.print_html(True)

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
        self.printer.setOrientation(QPrinter.Portrait)
        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_html(self):
        patient_html = self._get_patient_html()
        history_html = self._get_history_html()
        diagnosis_html = self._get_diagnosis_html()
        html = f'''
            <html>
                <body>
                    <h2 style="text-align: center">{self.system_settings.field('院所名稱')} 中醫門診初診患者照護專案病歷</h2>
                    {patient_html}<br>
                    {history_html}
                    {diagnosis_html}
                </body>
            </html>
        '''

        return html

    def _get_patient_html(self):
        sql = f'''
            SELECT * FROM patient
            WHERE
                PatientKey = {self.patient_key}
        '''
        row = self.database.select_record(sql)[0]

        if self.case_key is not None:
            sql = f'''
                SELECT CaseDate FROM cases
                WHERE
                    CaseKey = {self.case_key}
            '''
            case_rows = self.database.select_record(sql)
            try:
                case_date = case_rows[0]['CaseDate']
                first_date = self._get_first_date(case_date)
            except Exception:
                first_date = ''
        else:
            first_date = ''

        name = string_utils.xstr(row['Name'])
        gender = string_utils.xstr(row['Gender'])
        age_year, _ = date_utils.get_age(row['Birthday'], datetime.datetime.now())
        occupation = string_utils.xstr(row['Occupation'])
        marriage = string_utils.xstr(row['Marriage'])
        first_date_type = self._get_first_date_type()

        patient_html = f'''
            <table align=center cellpadding="0" cellspacing="0" width="95%">
                <tbody>
                    <tr>
                        <td>姓名: {name}</td>
                        <td>性別: {gender}</td>
                        <td>年齡: {age_year}</td>
                        <td>{first_date}</td>
                    </tr>
                    <tr>
                        <td>病歷號碼: {self.patient_key:0>6}</td>
                        <td>職業: {occupation}</td>
                        <td>婚姻: {marriage}</td>
                        <td>{first_date_type}</td>
                    </tr>
                </tbody>
            </table>
        '''

        return patient_html

    def _get_history_html(self):
        html = f'''
            <table align=center cellpadding="0" cellspacing="0" width="95%">
                <tbody>
                    <tr>
                        <td>
                            <b>一、主訴:</b>{self._get_field_value('主訴', 90)}
                        </td>
                    </tr>
                    <tr>
                        <td>
                            <b>二、現病史:</b>{self._get_field_value('現病史', 90)}
                        </td>
                    </tr>
                </tbody>
            </table>
            <table align=center cellpadding="0" cellspacing="0" width="95%">
                <tbody>
                    <tr>
                        <td colspan="3">
                            <b>三、過去病史:</b>
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td colspan="2">
                            {self._set_check_box_field('過去病史-糖尿病', '糖尿病')}
                            {self._set_check_box_field('過去病史-高血壓', '高血壓')}
                            {self._set_check_box_field('過去病史-冠心病', '冠心病')}
                            {self._set_check_box_field('過去病史-慢性阻塞性肺病', '慢性阻塞性肺病')}
                            {self._set_check_box_field('過去病史-肺結核', '肺結核')}
                            {self._set_check_box_field('過去病史-腦中風', '腦中風')}
                            {self._set_check_box_field('過去病史-癌症', '癌症')}<br>
                            其他傷病史: {self._get_field_value('其他傷病史', 40)}
                        </td>
                    </tr>
                    <tr>
                        <td colspan="3"><b>四、個人史:</b></td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%"><b>飲食習慣:</b></td>
                        <td>
                            {self._set_check_box_field('飲食習慣-素食', '素食')}
                            {self._set_check_box_field('飲食習慣-葷食', '葷食')}
                            {self._set_check_box_field('飲食習慣-辛辣', '辛辣')}
                            {self._set_check_box_field('飲食習慣-冷飲', '冷飲')}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%"><b>過敏:</b></td>
                        <td>
                            {self._set_check_box_field('過敏-無', '無')}
                            {self._set_check_box_field('過敏-藥物', '藥物')}: {self._get_field_value('過敏藥物', 20)}
                            {self._set_check_box_field('過敏-食物', '食物')}: {self._get_field_value('過敏食物', 20)}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%"><b>抽煙:</b></td>
                        <td>
                            {self._set_check_box_field('抽煙-無', '無')}
                            {self._set_check_box_field('抽煙-有', '有')} {self._get_field_value('抽煙頻率', 10)} 包/天
                            喝酒: {self._set_check_box_field('喝酒-無', '無')}
                            {self._set_check_box_field('喝酒-有', '有')} {self._get_field_value('喝酒頻率', 10)} 瓶/天
                            (酒類: {self._get_field_value('酒類', 10)})
                        </td>
                    </tr>
                    <tr>
                        <td colspan="3"><b>五、家族病史:</b></td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td colspan="2">
                            {self._set_check_box_field('家族病史-糖尿病', '糖尿病')}
                            {self._set_check_box_field('家族病史-高血壓', '高血壓')}
                            {self._set_check_box_field('家族病史-冠心病', '冠心病')}
                            {self._set_check_box_field('家族病史-腦中風', '腦中風')}
                            {self._set_check_box_field('家族病史-癌症', '癌症')}
                            種類: {self._get_field_value('癌症', 20)}<br>
                            {self._set_check_box_field('家族病史-氣喘', '氣喘')}
                            {self._set_check_box_field('家族病史-鼻過敏', '鼻過敏')}
                            {self._set_check_box_field('家族病史-異位性皮膚炎', '異位性皮膚炎')}
                            其他疾病: {self._get_field_value('其他家族病史', 30)}
                        </td>
                    </tr>
                </tbody>
            </table>
        '''

        return html

    def _get_diagnosis_html(self):
        html = f'''
            <table align=center cellpadding="1" cellspacing="0" width="95%">
                <tbody>
                    <tr>
                        <td colspan="3"><b>六、中醫四診及理學檢查:</b></td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td colspan="2">
                            血壓: {self._get_field_value('收縮壓', 10)} / {self._get_field_value('舒張壓', 10)} mmHg
                            脈率: {self._get_field_value('脈搏', 10)} /min
                            體溫: {self._get_field_value('體溫', 10)} °C
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td colspan="2"><b>(一)望診:</b></td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%" align="right"><b>意識</b></td>
                        <td>
                            {self._set_check_box_field('意識-清醒', '清醒')}
                            {self._set_check_box_field('意識-嗜睡', '嗜睡')}
                            {self._set_check_box_field('意識-木僵', '木僵')}
                            {self._set_check_box_field('意識-半昏迷', '半昏迷')}
                            {self._set_check_box_field('意識-昏迷', '昏迷')}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%" align="right"><b>體格</b></td>
                        <td>
                            {self._set_check_box_field('體格-肥胖', '肥胖')}
                            {self._set_check_box_field('體格-略胖', '略胖')}
                            {self._set_check_box_field('體格-中等', '中等')}
                            {self._set_check_box_field('體格-略瘦', '略瘦')}
                            {self._set_check_box_field('體格-消瘦', '消瘦')}
                            {self._set_check_box_field('體格-壯', '壯')}
                            {self._set_check_box_field('體格-弱', '弱')}<br>
                            舌診: {self._get_field_value('舌診', 60)}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td colspan="2"><b>(二)聞診:</b></td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%" align="right"><b>嗅氣味</b></td>
                        <td>
                            {self._set_check_box_field('氣味-無異狀', '無異狀')}
                            {self._set_check_box_field('氣味-臭', '臭')}
                            {self._set_check_box_field('氣味-特殊氣味', '特殊氣味')}: {self._get_field_value('特殊氣味', 20)}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%" align="right"><b>聽聲音</b></td>
                        <td>
                            {self._set_check_box_field('聲音-無異狀', '無異狀')}
                            {self._set_check_box_field('聲音-沙啞', '沙啞')}
                            {self._set_check_box_field('聲音-高亢', '高亢')}
                            {self._set_check_box_field('聲音-低微', '低微')}
                            {self._set_check_box_field('聲音-氣短', '氣短')}
                            {self._set_check_box_field('聲音-其他', '其他')} {self._get_field_value('其他聲音', 20)}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td colspan="2"><b>(三)問診:</b></td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%" align="right"><b>情志</b></td>
                        <td>
                            {self._set_check_box_field('情志-平常', '平常')}
                            {self._set_check_box_field('情志-煩躁', '煩躁')}
                            {self._set_check_box_field('情志-易怒', '易怒')}
                            {self._set_check_box_field('情志-健忘', '健忘')}
                            {self._set_check_box_field('情志-善喜', '善喜')}
                            {self._set_check_box_field('情志-憂慮', '憂慮')}
                            {self._set_check_box_field('情志-工作壓力', '工作壓力')}
                            {self._set_check_box_field('情志-恐懼', '恐懼')}
                            {self._set_check_box_field('情志-易緊張', '易緊張')}<br>
                            {self._set_check_box_field('情志-其他', '其他')}: {self._get_field_value('其他情志', 16)}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%" align="right"><b>睡眠</b></td>
                        <td>
                            {self._set_check_box_field('睡眠-平常', '平常')}
                            {self._set_check_box_field('睡眠-不易入睡', '不易入睡')}
                            {self._set_check_box_field('睡眠-淺眠', '淺眠')}
                            {self._set_check_box_field('睡眠-多夢', '多夢')}
                            {self._set_check_box_field('睡眠-易醒', '易醒')}
                            {self._set_check_box_field('睡眠-早醒', '早醒')}
                            {self._set_check_box_field('睡眠-徹夜不眠', '徹夜不眠')}
                            {self._set_check_box_field('睡眠-多寐', '徹夜多寐')}<br>
                            {self._set_check_box_field('睡眠-其他', '其他')}: {self._get_field_value('其他睡眠', 16)}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%" align="right"><b>五官耳鼻喉</b></td>
                        <td>
                            {self._set_check_box_field('五官-無不適', '無不適')}
                            不適症狀說明: {self._get_field_value('其他五官', 40)}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%" align="right"><b>胸部</b></td>
                        <td>
                            {self._set_check_box_field('胸部-無不適', '無不適')}
                            {self._set_check_box_field('胸部-胸悶', '胸悶')}
                            {self._set_check_box_field('胸部-胸痛', '胸痛')}
                            (胸部部位: {self._get_field_value('胸部部位', 10)}
                            性質: {self._set_check_box_field('胸部-悶痛', '悶痛')}
                                 {self._set_check_box_field('胸部-脹痛', '脹痛')}
                                 {self._set_check_box_field('胸部-刺痛', '刺痛')})<br>
                            {self._set_check_box_field('胸部-咳嗽', '咳嗽')}
                            (時間: {self._get_field_value('咳嗽時間', 10)}
                             性質: {self._get_field_value('咳嗽性質', 10)})
                            {self._set_check_box_field('胸部-咳血', '咳血')}
                             痰色質量描述: {self._get_field_value('痰色', 10)}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%" align="right"><b>腹部</b></td>
                        <td>
                            {self._set_check_box_field('腹部-無不適', '無不適')}
                            {self._set_check_box_field('腹部-食慾', '食慾')}
                            ({self._set_check_box_field('腹部-亢進', '亢進')}
                             {self._set_check_box_field('腹部-正常', '正常')}
                             {self._set_check_box_field('腹部-不佳', '不佳')})
                            {self._set_check_box_field('腹部-泛酸', '泛酸')}
                            {self._set_check_box_field('腹部-噯氣', '噯氣')}
                            {self._set_check_box_field('腹部-呃逆', '呃逆')}
                            {self._set_check_box_field('腹部-噁心', '噁心')}
                            {self._set_check_box_field('腹部-乾嘔', '乾嘔')}<br>
                            {self._set_check_box_field('腹部-腹痛', '腹痛')}
                             部位: {self._get_field_value('腹部部位', 10)}
                             性質: {self._set_check_box_field('腹部-悶痛', '悶痛')}
                                  {self._set_check_box_field('腹部-脹痛', '脹痛')}
                                  {self._set_check_box_field('腹部-絞痛', '絞痛')}
                                  {self._set_check_box_field('腹部-刺痛', '刺痛')}
                                  {self._set_check_box_field('腹部-喜按', '喜按')}
                                  {self._set_check_box_field('腹部-拒按', '拒按')}
                                  {self._set_check_box_field('腹部-喜熱敷', '喜熱敷')}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%" align="right"><b>二便</b></td>
                        <td>
                            {self._set_check_box_field('二便-大便正常', '大便正常')}
                            {self._set_check_box_field('二便-質硬', '質硬')}
                            {self._set_check_box_field('二便-顆粒', '顆粒')}
                            {self._set_check_box_field('二便-軟散', '軟散')}
                            {self._set_check_box_field('二便-便溏', '便溏')}
                            {self._set_check_box_field('二便-水瀉', '水瀉')}
                            {self._set_check_box_field('二便-排不淨感', '排不淨感')}<br>
                            {self._set_check_box_field('二便-小便正常', '小便正常')}
                            {self._set_check_box_field('二便-小便頻數', '小便頻數')}
                            {self._set_check_box_field('二便-小便不利', '小便不利(量少排出困難)')}
                            {self._set_check_box_field('二便-小便疼痛', '小便疼痛')}
                            {self._set_check_box_field('二便-尿急', '尿急')}
                            {self._set_check_box_field('二便-餘尿感', '餘尿感')}<br>
                            {self._set_check_box_field('二便-小便失禁', '小便失禁')}
                            {self._set_check_box_field('二便-夜尿', '夜尿')}
                            {self._set_check_box_field('二便-遺尿', '遺尿')}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%" align="right"><b>腰背</b></td>
                        <td>
                            {self._set_check_box_field('腰背-無不適', '無不適')}
                            {self._set_check_box_field('腰背-背痛', '背痛')}
                            {self._set_check_box_field('腰背-腰痠', '腰痠')}
                            {self._set_check_box_field('腰背-腰冷', '腰冷')}
                            {self._set_check_box_field('腰背-腰重著', '腰重著')}
                            {self._set_check_box_field('腰背-腰痛', '腰痛')}
                            {self._set_check_box_field('腰背-腰膝無力', '腰膝無力')}
                            {self._set_check_box_field('腰背-尾椎痛', '尾椎痛')}<br>
                            {self._set_check_box_field('腰背-其他', '其他')} {self._get_field_value('其他腰背', 10)}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td width="10%" align="right"><b>四肢</b></td>
                        <td>
                            {self._set_check_box_field('四肢-無不適', '無不適')}
                            {self._set_check_box_field('四肢-疼痛', '疼痛')}
                            {self._set_check_box_field('四肢-麻木', '麻木')}
                            {self._set_check_box_field('四肢-無力', '無力')}
                            {self._set_check_box_field('四肢-瘦削', '瘦削')}
                            {self._set_check_box_field('四肢-腫脹', '腫脹')}
                            (部位: {self._get_field_value('四肢部位', 20)})<br>
                            {self._set_check_box_field('四肢-僵硬', '僵硬')}
                            {self._set_check_box_field('四肢-抽搐', '抽搐')}
                            {self._set_check_box_field('四肢-震顫', '震顫')}
                            {self._set_check_box_field('四肢-手足厥冷', '手足厥冷')}
                            {self._set_check_box_field('四肢-手足心熱', '手足心熱')}
                            {self._set_check_box_field('四肢-其他', '其他')}
                            {self._get_field_value('其他四肢', 20)}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td colspan="2">
                            <b>(四)切診: 脈象:</b>{self._get_field_value('脈象', 60)}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td colspan="2"><b>(五)相關理學檢查:</b>
                            {self._get_field_value('理學檢查', 60)}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td colspan="2"><b>(六)相關實驗室數據:</b>
                            {self._get_field_value('實驗室數據', 60)}
                        </td>
                    </tr>
                    <tr>
                        <td width="12%"></td>
                        <td colspan="2"><b>(七)其他補充說明:</b>
                            {self._get_field_value('其他補充說明', 60)}
                        </td>
                    </tr>
                    <tr>
                        <td colspan="3">
                            <b>七、診斷:</b>
                            {self._get_field_value('診斷', 80)}
                        </td>
                    </tr>
                    <tr>
                        <td colspan="3">
                            <b>八、自我照護指導:</b>
                            {self._get_field_value('自我照護', 70)}
                        </td>
                    </tr>
                    <tr>
                        <td colspan="3">
                            <b>九、飲食宜忌指導:</b>
                            {self._get_field_value('飲食指導', 70)}
                        </td>
                    </tr>
                </tbody>
            </table>
        '''

        return html

    def _set_check_box_field(self, field_name, caption):
        check_box = string_utils.get_check_box(
            patient_utils.read_patient_new_care(self.database, self.patient_key, field_name)
        )

        return f'{check_box}{caption}'

    def _get_field_value(self, field_name, underline_count=None):
        value = patient_utils.read_patient_new_care(self.database, self.patient_key, field_name)
        if value is None and underline_count is not None:
            value = '_' * underline_count

        return f'{string_utils.xstr(value)}'

    def _get_first_date(self, first_date):
        if first_date is None:
            return '☐初診日期:'

        year = first_date.year - 1911
        month = first_date.month
        day = first_date.day
        first_date = f'{year} 年 {month:0>2} 月 {day:0>2} 日'

        check_box = string_utils.get_check_box(not self._is_two_years_not_visit())

        return f'{check_box}初診日期: {first_date}'

    def _get_first_date_type(self):
        check_box = string_utils.get_check_box(self._is_two_years_not_visit())

        return f'{check_box}二年以上未至本院看診'

    def _is_two_years_not_visit(self):
        if self.case_key is None:
            case_date = datetime.datetime.now()
        else:
            sql = f'''
                SELECT CaseDate FROM cases
                WHERE
                    CaseKey = {self.case_key}
            '''
            rows = self.database.select_record(sql)
            try:
                case_date = rows[0]['CaseDate']
            except Exception:
                case_date = datetime.datetime.now()

        two_years_ago = f'{case_date.replace(year=case_date.year - 2).date()} 00:00:00'
        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                PatientKey = {self.patient_key} AND
                CaseDate < "{two_years_ago}"
            LIMIT 1
        '''
        rows = self.database.select_record(sql)

        if len(rows) > 0:
            return True
        else:
            return False
