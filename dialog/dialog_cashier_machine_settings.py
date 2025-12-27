
# 掛號機零錢箱設定 2022.01.27
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import class_utils
from libs import system_utils
from libs import ui_utils


# 2022.01.27 掛號機零錢箱設定
class DialogCashierMachineSettings(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogCashierMachineSettings, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        try:
            self.coinsys = class_utils.get_coin_sys(self.system_settings)
            self.coinsys.set_current_path(self.system_settings.field('掛號機錢箱路徑'))
        except Exception:
            self.coinsys = None

        self._set_ui()
        self._set_signal()
        self._reload_coin_amount()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_CASHIER_MACHINE_SETTINGS, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        if self.coinsys is not None:
            self._reload_income()

    def _reload_income(self):
        one, five, ten, fifty = self.coinsys.get_coin_amount()
        # nd100, tnv100, tnv500, tnv1000 = self.coinsys.get_banknote_amount()
        nd100, tnv100, tnv1000 = self.coinsys.get_banknote_amount()

        self.ui.spinBox_1.setValue(one)
        self.ui.spinBox_5.setValue(five)
        self.ui.spinBox_10.setValue(ten)
        self.ui.spinBox_50.setValue(fifty)

        self.ui.spinBox_100.setValue(nd100)
        self.ui.spinBox_tnv100.setValue(tnv100)
        # self.ui.spinBox_tnv500.setValue(tnv500)
        self.ui.spinBox_tnv1000.setValue(tnv1000)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.pushButton_reset_coin_box.clicked.connect(self._reset_coin_box)
        self.ui.pushButton_show_income.clicked.connect(self._show_income)

    def accepted_button_clicked(self):
        if self.coinsys is not None:
            self.coinsys.set_coin_amount(
                one_dollar=self.ui.spinBox_1.value(),
                five_dollar=self.ui.spinBox_5.value(),
                ten_dollar=self.ui.spinBox_10.value(),
                fifty_dollar=self.ui.spinBox_50.value(),
            )
            nd100 = self.ui.spinBox_100.value()
            tnv100 = self.ui.spinBox_tnv100.value()
            # tnv500 = self.ui.spinBox_tnv500.value()
            tnv1000 = self.ui.spinBox_tnv1000.value()

            # self.coinsys.set_banknote(nd100, tnv100, tnv500, tnv1000)
            self.coinsys.set_banknote(nd100, tnv100, tnv1000)

    def _reload_coin_amount(self):
        pass

    def _reset_coin_box(self):
        if self.coinsys is not None:
            self.coinsys.reset_coin_box()

    def _show_income(self):
        if self.coinsys is None:
            return

        one, five, ten, fifty = self.coinsys.get_coin_amount()
        # nd100, tnv100, tnv500, tnv1000 = self.coinsys.get_banknote_amount()
        nd100, tnv100, tnv1000 = self.coinsys.get_banknote_amount()

        # total_income = (
        #     tnv1000 * 1000 + tnv500 * 500 + tnv100 * 100 + nd100 * 100 +
        #     fifty * 50 + ten * 10 + five * 5 + one
        # )
        total_income = (
            tnv1000 * 1000 + tnv100 * 100 + nd100 * 100 +
            fifty * 50 + ten * 10 + five * 5 + one
        )

        html = f'''
            <table align=center cellpadding="2" cellspacing="0" width="98%"
             style="font-size: 18px; border-width: 1px; border-style: solid;">
                <thead>
                    <tr bgcolor="LightGray">
                        <th style="padding: 8px">幣值種類</th>
                        <th style="padding: 8px">數量</th>
                        <th style="padding: 8px">金額</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>1元硬幣</td>
                        <td align=right>{one}</td>
                        <td align=right>{one}</td>
                    </tr>
                    <tr>
                        <td>5元硬幣</td>
                        <td align=right>{five}</td>
                        <td align=right>{five * 5}</td>
                    </tr>
                    <tr>
                        <td>10元硬幣</td>
                        <td align=right>{ten}</td>
                        <td align=right>{ten * 10}</td>
                    </tr>
                    <tr>
                        <td>50元硬幣</td>
                        <td align=right>{fifty}</td>
                        <td align=right>{fifty * 50}</td>
                    </tr>
                    <tr>
                        <td>100元紙鈔(找鈔機</td>
                        <td align=right>{nd100}</td>
                        <td align=right>{nd100 * 100}</td>
                    </tr>
                    <tr>
                        <td>100元紙鈔</td>
                        <td align=right>{tnv100}</td>
                        <td align=right>{tnv100 * 100}</td>
                    </tr>
                    <tr>
                        <td>1000元紙鈔</td>
                        <td align=right>{tnv1000}</td>
                        <td align=right>{tnv1000 * 1000}</td>
                    </tr>
                    <tr>
                        <td colspan=2>合計金額</td>
                        <td align=right>{total_income}</td>
                    </tr>
                </tbody>
            </table>
        '''
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle('掛號機錢箱統計')
        msg_box.setText(f'''
            <font color="red"><h3>自動掛號機錢箱數量清點如下:</h3></font>
            {html}
        ''')
        msg_box.setInformativeText('以上資料由掛號機提供')
        msg_box.addButton(QPushButton("確定"), QMessageBox.AcceptRole)
        msg_box.exec_()
