# 健保卡就醫資料 2023-03-21
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from libs import ui_utils
from libs import system_utils
from libs import class_utils
from libs import registration_utils
from libs import number_utils
from libs import case_utils


# 健保卡就醫資料 2023-03-21
class DialogICCardRecord(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogICCardRecord, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ic_card = args[2]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._set_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_IC_CARD_RECORD, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('關閉')

        self.table_widget_prescript_data = class_utils.get_table_widget(
            self.ui.tableWidget_prescript_data, self.database)
        self._set_table_width()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [580]
        self.table_widget_prescript_data.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        self.close()

    def _set_data(self):
        self.ic_card.read_treatment_no_need_hpc()
        self.treatment_data = self.ic_card.treatment_data

        self.ic_card.read_treatment_need_hpc()
        self.disease_data = self.ic_card.disease_data

        self.ic_card.read_prescript_data()
        self.prescript_data = self.ic_card.prescript_data

        self._set_patient_data()
        for row_no, treatment in enumerate(self.treatment_data['treatments']):
            html = self._get_html(treatment)

            self.ui.tableWidget_prescript_data.setRowCount(self.ui.tableWidget_prescript_data.rowCount()+1)
            self.ui.tableWidget_prescript_data.setRowHeight(row_no, 300)

            text_edit = QtWidgets.QTextEdit(self.ui.tableWidget_prescript_data)
            text_edit.setHtml(html)
            self.ui.tableWidget_prescript_data.setCellWidget(row_no, 0, text_edit)

        # self.ui.tableWidget_prescript_data.resizeRowsToContents()
        # self.ui.tableWidget_prescript_data.setRowHeight(row_no, 300)

    def _set_patient_data(self):
        card_no = self.ic_card.basic_data['card_no']
        name = self.ic_card.basic_data['name']
        patient_id = self.ic_card.basic_data['patient_id']
        birthday = self.ic_card.basic_data['birthday']
        gender = self.ic_card.basic_data['gender']
        card_date = self.ic_card.basic_data['card_date']
        cancel_mark = self.ic_card.basic_data['cancel_mark']
        insured_mark = self.ic_card.basic_data['insured_mark']
        valid_date = self.ic_card.basic_data['card_valid_date']
        available_count = self.ic_card.basic_data['card_available_count']

        html = f'''
            <table align=center cellpadding="2" cellspacing="0" width="98%"
            style="border-width: 1px; border-style: solid;">
                <thead>
                </thead>
                <tbody>
                    <tr>
                        <td bgcolor="lightGray">病患姓名</td>
                        <td>{name}</td>
                        <td bgcolor="lightGray">性別</td>
                        <td>{gender}</td>
                        <td bgcolor="lightGray">身分證號</td>
                        <td>{patient_id}</td>
                        <td bgcolor="lightGray">出生日期</td>
                        <td>{birthday}</td>
                    </tr>
                    <tr>
                        <td bgcolor="lightGray">保險身分</td>
                        <td>{insured_mark}</td>
                        <td bgcolor="lightGray">卡片號碼</td>
                        <td>{card_no}</td>
                        <td bgcolor="lightGray">發卡日期</td>
                        <td>{card_date}</td>
                        <td bgcolor="lightGray">卡片效期</td>
                        <td>{valid_date}</td>
                    </tr>
                    <tr>
                        <td bgcolor="lightGray">卡片註記</td>
                        <td>{cancel_mark}</td>
                        <td bgcolor="lightGray">可用次數</td>
                        <td>{available_count}</td>
                        <td bgcolor="lightGray"></td>
                        <td></td>
                        <td bgcolor="lightGray"></td>
                        <td></td>
                    </tr>
                </tbody>
            </table>
            <br>
        '''

        self.ui.textEdit_patient.setHtml(html)

    def _get_html(self, treatment):
        hosp_id = treatment['treat_hosp_code']
        hosp_name = registration_utils.get_hosp_name(self.database, hosp_id)

        case_time = treatment['treat_date_time']
        case_date_time = f'{case_time[:3]}-{case_time[3:5]}-{case_time[5:7]} {case_time[7:9]}:{case_time[9:11]}'

        card = treatment['card']
        treat_item = treatment['treat_item']
        if treat_item == '03':
            course = '(內科或首次)'
        elif treat_item == 'AA':
            course = '(療程2-6次)'
        elif treat_item == 'AC':
            course = '(職災)'
        else:
            course = ''

        disease_html = self._get_disease_html(case_time)
        prescript_html = self._get_prescript_html(case_time)

        html = f'''
            院所名稱: {hosp_name}<br>
            門診日期: {case_date_time} 卡序: {card} {course}
            {disease_html}
            {prescript_html}
        '''

        return html

    def _get_disease_html(self, case_time):
        disease_data = self._get_disease_data(case_time)

        html = ''
        for disease in disease_data:
            disease1 = disease['disease1']
            disease2 = disease['disease2']
            disease3 = disease['disease3']
            disease4 = disease['disease4']

            if disease1 != '':
                disease_name = case_utils.get_disease_name(self.database, disease1)
                html += f'<br>主診斷: {disease1} {disease_name}'
            if disease2 != '':
                disease_name = case_utils.get_disease_name(self.database, disease2)
                html += f'<br>次診斷1: {disease2} {disease_name}'
            if disease3 != '':
                disease_name = case_utils.get_disease_name(self.database, disease3)
                html += f'<br>次診斷2: {disease3} {disease_name}'
            if disease4 != '':
                disease_name = case_utils.get_disease_name(self.database, disease4)
                html += f'<br>次診斷3: {disease4} {disease_name}'

        return html

    def _get_prescript_html(self, case_time):
        prescript_data = self._get_prescript_data(case_time)

        prescript_row, pres_days, packages, instruction = self._get_prescript_row(prescript_data)
        if pres_days > 0:
            instruction_html = f'''
                <tr>
                    <td style="text-align: left; padding-left: 30px;" colspan="3">
                        用法: {packages}包 {pres_days}日份 {instruction}服用
                    </td>
                </tr>
            '''
        else:
            instruction_html = ''

        prescript_html = f'''
            <table align=center cellpadding="2" cellspacing="0" width="98%"
            style="border-width: 1px; border-style: solid;">
                <thead>
                    <tr bgcolor="LightGray">
                        <th style="text-align: center; padding-left: 8px" width="10%">序</th>
                        <th style="padding-left: 8px" width="70%" align="left">處方名稱</th>
                        <th style="padding-right: 8px" align="right" width="25%">劑量</th>
                    </tr>
                </thead>
                <tbody>
                    {prescript_row}
                    {instruction_html}
                </tbody>
            </table>
            <br>
        '''

        return prescript_html

    def _get_prescript_row(self, prescript_data):
        real_pres_days = 0
        real_packages = 0
        real_instruction = ''

        html = ''
        for row_no, prescript in enumerate(prescript_data):
            prescript_type = prescript['prescript_type']
            if prescript_type == '1':
                medicine_html, packages, pres_days, instruction = self._get_medicine(row_no, prescript)
                html += medicine_html
                if pres_days > real_pres_days:
                    real_pres_days = pres_days
                if packages > real_packages:
                    real_packages = packages
                if instruction != '':
                    real_instruction = instruction
            elif prescript_type == '3':
                html += self._get_treat(row_no, prescript)

        return html, real_pres_days, real_packages, real_instruction

    def _get_medicine(self, row_no, prescript):
        ins_code = prescript['ins_code']
        pres_days = number_utils.get_integer(prescript['pres_days'])
        usage = prescript['usage']
        if 'QD' in usage:
            packages = 1
        elif 'BID' in usage:
            packages = 2
        elif 'TID' in usage:
            packages = 3
        elif 'QID' in usage:
            packages = 4
        else:
            packages = 0

        if 'AC' in usage:
            instruction = '飯前'
        elif 'PC' in usage:
            instruction = '飯後'
        else:
            instruction = ''

        drug_name = case_utils.get_drug_name(self.database, ins_code)
        if drug_name == '':
            drug_name = ins_code

        total_dosage = number_utils.get_float(prescript['total_dosage'])
        try:
            dosage = total_dosage / pres_days
        except Exception:
            dosage = 0

        html = f'''
            <tr>
                <td align=center>{row_no+1}</td>
                <td>{drug_name}</td>
                <td align=right>{dosage:.1f}</td>
            </tr>
        '''

        return html, packages, pres_days, instruction

    def _get_treat(self, row_no, prescript):
        ins_code = prescript['ins_code']
        treat_name = case_utils.get_treat_name(self.database, ins_code)
        if treat_name == '':
            treat_name = ins_code

        html = f'''
            <tr>
                <td align=center>{row_no+1}</td>
                <td>{treat_name}</td>
                <td></td>
            </tr>
        '''

        return html

    def _get_disease_data(self, case_time):
        disease_data = []

        for row in self.disease_data['diseases']:
            if row['case_date'] == case_time:
                disease_data.append(row)

        return disease_data

    def _get_prescript_data(self, case_time):
        prescript_data = []

        for row in self.prescript_data:
            if row['case_date'] == case_time:
                prescript_data.append(row)

        return prescript_data
