
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton
import sys
import subprocess

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import case_utils
from libs import dialog_utils
from libs import cshis_utils


# 主視窗
class DialogICCard(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogICCard, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        try:
            self.ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        except NameError:
            self.ic_card = None

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_IC_CARD, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('關閉')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.toolButton_verify_sam.clicked.connect(self.verify_sam)
        self.ui.toolButton_verify_hpc_pin.clicked.connect(self.verify_hpc_pin)
        self.ui.toolButton_set_hpc_pin.clicked.connect(self.set_hpc_pin)
        self.ui.toolButton_unlock_hpc_pin.clicked.connect(self.unlock_hpc_pin)
        self.ui.toolButton_update_ic_card.clicked.connect(self.update_ic_card)
        self.ui.toolButton_verify_ic_card_pin.clicked.connect(self.verify_ic_card_pin)
        self.ui.toolButton_set_ic_card_pin.clicked.connect(self.set_ic_card_pin)
        self.ui.toolButton_disable_ic_card_pin.clicked.connect(self.disable_ic_card_pin)
        self.ui.toolButton_ic_card_info.clicked.connect(self.ic_card_info)
        self.ui.toolButton_ic_card_treat_info.clicked.connect(self.ic_card_prescript_data)
        # self.ui.toolButton_ic_card_record.clicked.connect(self.ic_card_record)
        self.ui.toolButton_reset_reader.clicked.connect(self.reset_reader)

    # 關閉
    def accepted_button_clicked(self):
        self.close()

    # 安全模組卡認證
    def verify_sam(self):
        self.ic_card.verify_sam()

    # 驗證醫事人員卡
    def verify_hpc_pin(self):
        self.ic_card.verify_hpc_pin()

    # 設定醫事人員卡密碼
    def set_hpc_pin(self):
        self.ic_card.input_hpc_pin()

    # 解鎖醫事人員卡密碼
    def unlock_hpc_pin(self):
        if self.system_settings.field('讀卡機控制軟體版本') == 'cshis6':
            card_status = self.ic_card.get_api_status('hpc')['status']
            if card_status == 0:  # 未插入卡片
                cshis_utils.show_ic_card_message(1102, '醫事人員卡密碼驗證')
                return

        self.ic_card.unlock_hpc()

    # 更新病患健保卡內容
    def update_ic_card(self):
        if sys.platform == 'win32':
            self.ic_card.update_hc()
        else:
            self.ic_card.start()

    # 驗證病患健保卡密碼
    def verify_ic_card_pin(self):
        self.ic_card.verify_hc_pin()

    # 設定病患健保卡密碼
    def set_ic_card_pin(self):
        self.ic_card.input_hc_pin()

    # 解除病患健保卡密碼
    def disable_ic_card_pin(self):
        self.ic_card.disable_hc_pin()

    # 讀取健保卡基本資料
    def ic_card_info(self):
        if not self.ic_card.read_register_basic_data():
            return

        self.ic_card.read_critical_illness()
        critical_illness_data = self.ic_card.critical_illness_data

        critical_illness_list = ''
        for i in range(len(critical_illness_data)):
            icd10 = critical_illness_data[i]['CI_CODE'].strip()
            disease_name = case_utils.get_disease_name(self.database, icd10)
            start_date = critical_illness_data[i]['CI_VALIDITY_START']
            end_date = critical_illness_data[i]['CI_VALIDITY_END']
            critical_illness_list += f'''
                <tr>
                    <td align=center>{i+1}</td>
                    <td>{icd10}</td>
                    <td>{disease_name}</td>
                    <td>{start_date}</td>
                    <td>{end_date}</td>
                </tr>
            '''
        html = f'''
            <table align=center cellpadding="2" cellspacing="0" width="98%"
             style="border-width: 1px; border-style: solid;">
                <thead>
                    <tr bgcolor="LightGray">
                        <th style="text-align: center; padding-left: 8px" width="10%">序</th>
                        <th style="padding-left: 8px" width="10%" align="left">ICD-10</th>
                        <th style="padding-left: 8px" width="50%" align="left">重大傷病名稱</th>
                        <th style="padding-right: 8px" align="right" width="20%">有效起日</th>
                        <th style="padding-left: 8px" align="left" width="20%">有效訖日</th>
                    </tr>
                </thead>
                    {critical_illness_list}
                <tbody>
                </tbody>
            </table>
        '''

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

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle('健保卡基本資料')
        msg_box.setText(f'''
            <font size="5" color="red">
              <b>健保IC卡卡片基本資料內容如下:</b><br><br>
            </font>
            <font size="5" color="black">
              <b>卡片號碼</b>: {card_no}<br>
              <b>病患姓名</b>: {name}<br>
              <b>身分證號</b>: {patient_id}<br>
              <b>出生日期</b>: {birthday}<br>
              <b>病患性別</b>: {gender}<br>
              <b>發卡日期</b>: {card_date}<br>
              <b>卡片註記</b>: {cancel_mark}<br>
              <b>保險身分</b>: {insured_mark}<br>
              <b>卡片效期</b>: {valid_date}<br>
              <b>可用次數</b>: {available_count}<br>
            </font>
            {html}
        ''')
        msg_box.setInformativeText('健保IC卡卡片內容讀取完成')
        msg_box.addButton(QPushButton("確定"), QMessageBox.AcceptRole)
        msg_box.exec_()

    # 讀取健保卡就醫資料
    def ic_card_prescript_data(self):
        if self.system_settings.field('讀卡機控制軟體版本') == 'cshis6':
            try:
                card_status = self.ic_card.get_api_status('hpc')['status']
            except Exception:
                cshis_utils.show_ic_card_message(1402, '醫事人員卡密碼驗證')
                return

            if card_status != 3:
                cshis_utils.show_ic_card_message(1402, '醫事人員卡密碼驗證')
                return

        if not self.ic_card.read_register_basic_data():
            return

        dialog = dialog_utils.get_dialog_ic_card_record(self, self.database, self.system_settings, self.ic_card)
        dialog.exec_()
        dialog.deleteLater()

    # 讀取健保卡就醫資料
    def ic_card_record(self):
        self.ic_card.read_treatment_no_need_hpc()
        treatment_data = self.ic_card.treatment_data
        for treatment in treatment_data['treatments']:
            print(treatment)

    # 讀卡機裝置重新啟動
    def reset_reader(self):
        self.ic_card.reset_reader()
