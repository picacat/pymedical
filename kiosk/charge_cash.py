# -*- coding: UTF-8 -*-

import time
import json

from PyQt5 import QtWidgets, QtGui, QtCore
from threading import Thread
from queue import Queue

from libs import class_utils
from libs import ui_utils
from libs import number_utils
from libs import cshis_utils
from libs import printer_utils


# 掛號機 2022.01.31
class ChargeCash(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(ChargeCash, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.socket_client = class_utils.get_socket_client()

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_CHARGE_CASH, self)
        style = '''
            QMainWindow#WindowCharge
            {background-image: url(./images/home.jpg);}
        '''
        self.ui.setStyleSheet(style)

        self.ui.label_message.setStyleSheet("QLabel {color : white; }")
        effect = QtWidgets.QGraphicsDropShadowEffect()
        effect.setBlurRadius(0)
        effect.setColor(QtGui.QColor('black'))
        effect.setOffset(1, 2)
        self.ui.label_message.setGraphicsEffect(effect)

        self.ui.label_cash_in.setStyleSheet("QLabel {color : white; }")
        effect2 = QtWidgets.QGraphicsDropShadowEffect()
        effect2.setBlurRadius(0)
        effect2.setColor(QtGui.QColor('black'))
        effect2.setOffset(1, 2)
        self.ui.label_cash_in.setGraphicsEffect(effect2)

    # 設定信號
    def _set_signal(self):
        pass

    def set_charge_cash_data(self, charge_type, case_key, fees):
        self.charge_type = charge_type

        charge_list = []
        self.total_fee = 0
        for fee in fees:
            item = fee[0]
            charge_fee = fee[1]
            self.total_fee += charge_fee
            charge_list.append(
                '{item}: {charge_fee}'.format(
                    item=item,
                    charge_fee=number_utils.get_integer(charge_fee),
                )
            )
        charge_detail = '以下是您的繳費明細:<br>'
        charge_detail += '<br>'.join(charge_list)
        charge_detail += '<br><font color="yellow">合計金額: {total_fee}</font>'.format(
            total_fee=self.total_fee,
        )

        self.ui.label_message.setText(charge_detail)
        self.parent.pay_machine.set_fee(self.total_fee)
        self.ready_to_pay(case_key, fees)

    # 準備付款
    def ready_to_pay(self, case_key, fees):
        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()

        t = Thread(target=self.get_machine_state_thread, args=(msg_queue,))
        t.start()
        status = msg_queue.get()

        if status == 'finish':
            if self.charge_type == '門診掛號':
                self._write_regist_fee(case_key, fees)
                self._print_registration(case_key)
            else:
                self._write_cashier_fee(case_key, fees)
                self._print_receipt(case_key)
                if self.system_settings.field('產生醫令簽章位置') == '批價':
                    self._write_ic_card(case_key)

            self.parent.open_show_message('謝謝您的使用.')

    def _write_ic_card(self, case_key):
        self.parent.ic_card.write_ic_medical_record(case_key, cshis_utils.NORMAL_CARD)

    # 列印掛號收據
    def _print_registration(self, case_key):
        printer_utils.print_regist_form(
            self, self.database, self.system_settings, case_key, '直接列印')

    # 列印醫療收據
    def _print_receipt(self, case_key):
        printer_utils.print_receipt_form(
            self, self.database, self.system_settings, case_key, '系統設定')

    def get_machine_state_thread(self, out_queue):
        status = None
        QtCore.QCoreApplication.processEvents()
        while True:
            state = self.parent.pay_machine.machine_state()
            QtCore.QCoreApplication.processEvents()
            time.sleep(0.2)
            if state is not None:
                parameter = json.loads(state)['parmeter']
                status = parameter['emsg']
                paid = parameter['paid']
                QtCore.QCoreApplication.processEvents()
                self.ui.label_cash_in.setText(
                    '<font color="yellow">投入金額: {0}元</font>'.format(paid)
                )
                self.ui.label_cash_in.repaint()
                self.ui.update()

            if status == 'finish':
                break

        out_queue.put(status)

    def _write_regist_fee(self, case_key, fees):
        regist_fee = fees[0][1]
        diag_share_fee = fees[1][1]

        fields = ['RegistFee', 'SDiagShareFee']
        data = [regist_fee, diag_share_fee]
        self.database.update_record('cases', fields, 'CaseKey', case_key, data)

    def _write_cashier_fee(self, case_key, fees):
        drug_share_fee = fees[0][1]
        total_fee = fees[1][1]

        fields = ['SDrugShareFee', 'ReceiptFee', 'Cashier', 'ChargeDone']
        data = [drug_share_fee, total_fee, '掛號機', 'True']
        self.database.update_record('cases', fields, 'CaseKey', case_key, data)
        self.database.exec_sql('UPDATE wait SET ChargeDone = "True" WHERE CaseKey = {0}'.format(case_key))
        self.socket_client.send_data('批價完成')

    def _back_home(self):
        self.parent.open_home()
