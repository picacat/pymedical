# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox, QPushButton
import os.path
import webbrowser

from libs import ui_utils
from libs import class_utils
from libs import string_utils
from libs import nhi_utils
from libs import number_utils
from libs import system_utils
from libs import log_utils
from libs import dialog_utils
from libs import module_utils


# 07-231-8122
# 健保申復 2023.05.01
class InsAppeal(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(InsAppeal, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.apply_date = None
        self.clinic_id = self.system_settings.field('院所代號')

        self.apply_year = None
        self.apply_month = None
        self.apply_date = None
        self.apply_upload_date = None
        self.apply_type = None
        self.clinic_id = None
        self.apply_period = '全月'

        self._set_ui()
        self._set_signal()
        # database.read_wait()   # activate by pymedical.py->tab_changed

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INS_APPEAL, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        self.table_widget_appeal = class_utils.get_table_widget(self.ui.tableWidget_appeal, self.database)
        self.table_widget_appeal.set_column_hidden([0, 1])
        self.table_widget_appeal_items = class_utils.get_table_widget(self.ui.tableWidget_appeal_items, self.database)
        self.table_widget_appeal_items.set_column_hidden([0])
        self._set_table_width()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 100, 90, 80, 90, 90, 90, 120, 120, 120]
        self.table_widget_appeal.set_table_heading_width(width)
        width = [100, 700]
        self.table_widget_appeal_items.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.action_reapply.triggered.connect(self.open_dialog)
        self.ui.action_open_nhi_vpn.triggered.connect(self._open_nhi_vpn)
        self.ui.action_upload.triggered.connect(self._upload_data)
        self.ui.action_close.triggered.connect(self.close_app)

        self.ui.toolButton_add_appeal.clicked.connect(self._add_ins_appeal)
        self.ui.toolButton_remove_appeal.clicked.connect(self._remove_ins_appeal)
        self.ui.toolButton_edit_appeal.clicked.connect(self._edit_ins_appeal)

        self.ui.toolButton_add_items.clicked.connect(self._add_ins_appeal_items)
        self.ui.tableWidget_appeal.doubleClicked.connect(self._edit_ins_appeal)

        self.ui.tableWidget_appeal.itemSelectionChanged.connect(self._ins_appeal_changed)

    def open_medical_record(self, case_key):
        self.parent.open_medical_record(case_key, '健保申報')

    def open_dialog(self):
        if self.system_settings.field('院所代號') in ['', None]:
            system_utils.show_message_box(
                QMessageBox.Critical,
                '系統設定有誤',
                '<font color="red"><h3>尚未設定院所代號, 請至「系統設定」輸入院所代號.</h3></font>',
                '請至系統設定->院所設定頁面檢視院所代號的設定值.'
            )
            return

        xml_dir = self.system_settings.field('資料路徑')
        if xml_dir in ['', None] or not os.path.exists(xml_dir):
            system_utils.show_message_box(
                QMessageBox.Critical,
                '申報路徑有誤',
                '<font color="red"><h3>申報路徑設定有誤, 請檢視申報路徑是否空白或正確.</h3></font>',
                '請至系統設定->其他頁面檢視申報及備份路徑的設定值.'
            )
            return

        dialog = dialog_utils.get_dialog_ins_judge(self.ui, self.database, self.system_settings)
        if self.apply_year is not None:
            dialog.ui.comboBox_year.setCurrentText(string_utils.xstr(self.apply_year))
            dialog.ui.comboBox_month.setCurrentText(string_utils.xstr(self.apply_month))
            dialog.ui.lineEdit_clinic_id.setText(self.clinic_id)
            dialog.ui.comboBox_period.setCurrentText(self.apply_period)
            dialog.ui.dateEdit_apply.setDate(self.apply_upload_date)
            if self.apply_type == '申報':
                dialog.ui.radioButton_apply.setChecked(True)
            else:
                dialog.ui.radioButton_reapply.setChecked(True)

        if dialog.exec_():
            self.apply_year = number_utils.get_integer(dialog.ui.comboBox_year.currentText())
            self.apply_month = number_utils.get_integer(dialog.ui.comboBox_month.currentText())
            self.clinic_id = dialog.ui.lineEdit_clinic_id.text()
            self.apply_period = dialog.ui.comboBox_period.currentText()

            if dialog.ui.radioButton_apply.isChecked():
                self.apply_type = '申報'  # 申報
            else:
                self.apply_type = '補報'  # 補報

            self.apply_type_code = nhi_utils.APPLY_TYPE_CODE[self.apply_type]

            self.apply_date = f'{self.apply_year-1911:0>3}{self.apply_month:0>2}'
            self.apply_upload_date = dialog.ui.dateEdit_apply.date()
        else:
            self.apply_type_code = None

        dialog.close_all()
        dialog.deleteLater()

        if not self._check_apply_data_exists():
            self.ui.label_year.setText(f'{self.apply_year}年{self.apply_month}月 申報資料不存在')
            self.ui.label_1.setVisible(False)
            self.ui.label_2.setVisible(False)
            self.ui.label_month.setVisible(False)
            return

        self.ui.label_year.setText(str(self.apply_year))
        self.ui.label_1.setVisible(True)
        self.ui.label_month.setText(str(self.apply_month))
        self.ui.label_month.setVisible(True)
        self.ui.label_2.setVisible(True)

        self._read_ins_appeal()

    def _read_ins_appeal(self):
        sql = f'''
            SELECT insappeal.*, insapply.Name FROM insappeal
                LEFT JOIN insapply ON insapply.InsApplyKey = insappeal.InsApplyKey
            WHERE
                insappeal.ApplyDate = "{self.apply_date}" AND
                insappeal.ApplyType = "{self.apply_type_code}" AND
                insappeal.ApplyPeriod = "{self.apply_period}" AND
                insappeal.ClinicID = "{self.clinic_id}"
            ORDER BY insappeal.CaseType, insappeal.Sequence
        '''
        self.table_widget_appeal.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        ins_appeal_row = [
            row['InsAppealKey'],
            row['InsApplyKey'],
            string_utils.xstr(row['CaseType']),
            row['Sequence'],
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Sample']),
            string_utils.xstr(row['Reject']),
            row['Point1'],
            row['Point2'],
            row['Point3'],
        ]

        for column in range(len(ins_appeal_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, ins_appeal_row[column])
            self.ui.tableWidget_appeal.setItem(row_no, column, item)
            if column in [2, 5, 6]:
                self.ui.tableWidget_appeal.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            elif column in [3, 7, 8, 9]:
                self.ui.tableWidget_appeal.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _check_apply_data_exists(self):
        sql = f'''
            SELECT * FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.apply_period}" AND
                ClinicID = "{self.clinic_id}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            apply_data_exists = True
        else:
            apply_data_exists = False

        return apply_data_exists

    def _open_dialog_appeal(self, ins_appeal_key=None):
        dialog = dialog_utils.get_dialog_ins_appeal(
            self, self.database, self.system_settings,
            self.apply_date, self.apply_period, self.apply_type_code, ins_appeal_key)
        if dialog.exec_():
            self._read_ins_appeal()

        dialog.deleteLater()

    def _add_ins_appeal(self):
        self._open_dialog_appeal()

    def _remove_ins_appeal(self):
        ins_appeal_key = self._get_ins_appeal_key()
        if ins_appeal_key is None:
            return

        msg_box = dialog_utils.get_message_box(
            '刪除申復資料', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除此筆申復資料?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        row_no = self.ui.tableWidget_appeal.currentRow()
        self.ui.tableWidget_appeal.removeRow(row_no)
        self.database.exec_sql(f'DELETE FROM insappeal WHERE InsAppealKey = {ins_appeal_key}')
        self.database.exec_sql(f'DELETE FROM insappeal_items WHERE InsAppealKey = {ins_appeal_key}')

    def _get_ins_appeal_key(self):
        row_no = self.ui.tableWidget_appeal.currentRow()
        ins_appeal_key = self.ui.tableWidget_appeal.item(row_no, 0)
        if ins_appeal_key is None:
            return None
        else:
            return ins_appeal_key.text()

    def _get_ins_appeal_sample(self):
        row_no = self.ui.tableWidget_appeal.currentRow()
        sample = self.ui.tableWidget_appeal.item(row_no, 4)
        if sample is None:
            return None
        else:
            return sample.text()

    def _get_ins_appeal_items_key(self):
        row_no = self.ui.tableWidget_appeal_items.currentRow()
        ins_appeal_items_key = self.ui.tableWidget_appeal_items.item(row_no, 0)
        if ins_appeal_items_key is None:
            return None
        else:
            return ins_appeal_items_key.text()

    def _edit_ins_appeal(self):
        ins_appeal_key = self._get_ins_appeal_key()
        if ins_appeal_key is None:
            return

        self._open_dialog_appeal(ins_appeal_key)

    def _save_ins_appeal_reason(self):
        row_no = self.ui.tableWidget_appeal.currentRow()
        ins_appeal_key = self.ui.tableWidget_appeal.item(row_no, 0)
        if ins_appeal_key is None:
            return

        ins_appeal_key = ins_appeal_key.text()

        order_seq = self.ui.lineEdit_order_seq.text()
        ins_code = self.ui.lineEdit_ins_code.text()
        change_seq = self.ui.lineEdit_change_seq.text()
        percent = self.ui.lineEdit_percent.text()
        quantity = self.ui.lineEdit_quantity.text()
        point = self.ui.lineEdit_point.text()
        reason1 = self.ui.textEdit_reason1.toPlainText()

        reply_seq = self.ui.lineEdit_reply_seq.text()
        reply_ins_code = self.ui.lineEdit_reply_ins_code.text()
        reject_code = self.ui.lineEdit_reject_code.text()
        reply_percent = self.ui.lineEdit_reply_percent.text()
        reply_quantity = self.ui.lineEdit_reply_quantity.text()
        reply_point = self.ui.lineEdit_reply_point.text()
        reply_reason1 = self.ui.textEdit_reply_reason1.toPlainText()

        fields = [
            'OrderSeq', 'InsCode', 'ChangeSeq', 'Percent', 'Quantity','Point','Reason1',
            'ReplySeq', 'ReplyInsCode', 'RejectCode', 'ReplyPercent', 'ReplyQuantity', 'ReplyPoint', 'ReplyReason1',
        ]
        data = [
            order_seq, ins_code, change_seq, percent, quantity, point, reason1,
            reply_seq, reply_ins_code, reject_code, reply_percent, reply_quantity, reply_point, reply_reason1,
        ]
        self.database.update_record('insappeal', fields, 'InsAppealKey', ins_appeal_key, data)

        system_utils.show_message_box(
            QMessageBox.Information,
            '存檔完成',
            '<font size="5" color="blue"><b>資料已存檔完成</b></font>',
            '存檔成功.'
        )

    def _ins_appeal_changed(self):
        ins_appeal_key = self._get_ins_appeal_key()
        self._read_ins_appeal_items(ins_appeal_key)

    def _read_ins_appeal_items(self, ins_appeal_key):
        sql = f'''
            SELECT * FROM insappeal_items
            WHERE
                InsAppealKey = {ins_appeal_key}
            ORDER BY InsAppealItemsKey
        '''
        self.table_widget_appeal_items.set_db_data(sql, self._set_appeal_items_data)

        for row_no in range(0, self.ui.tableWidget_appeal_items.rowCount()):
            self.ui.tableWidget_appeal_items.setRowHeight(row_no, 300)

    def _set_appeal_items_data(self, row_no, row):
        ins_appeal_items_key = string_utils.xstr(row['InsAppealItemsKey'])

        items_type = string_utils.xstr(row['ItemType'])
        order_seq = string_utils.xstr(row['OrderSeq'])
        ins_code = string_utils.xstr(row['InsCode'])
        reject_code = string_utils.xstr(row['RejectCode'])
        percent = string_utils.xstr(row['Percent'])
        quantity = string_utils.xstr(row['Quantity'])
        point = string_utils.xstr(row['Point'])
        reason = string_utils.xstr(row['Reason1']) + string_utils.xstr(row['Reason2'])

        html = f'''
            <table align=center cellpadding="2" cellspacing="0" width="98%"
             style="border-width: 1px; border-style: solid;">
                <tr>
                    <td bgcolor="lightGray"><b>申復醫令類別</b></td><td colspan="3">{items_type}</td>
                </tr>
                <tr>
                    <td bgcolor="lightGray"><b>醫令序號</b></td><td>{order_seq}</td>
                    <td bgcolor="lightGray"><b>醫令代碼</b></td><td>{ins_code}</td>
                </tr>
                <tr>
                    <td bgcolor="lightGray"><b>改支/核減</b></td><td>{reject_code}</td>
                    <td bgcolor="lightGray"><b>成數受理</b></td><td>{percent}</td>
                </tr>
                <tr>
                    <td bgcolor="lightGray"><b>數量受理</b></td><td>{quantity}</td>
                    <td bgcolor="lightGray"><b>點數受理</b></td><td>{point}</td>
                </tr>
                <tr>
                    <td bgcolor="lightGray"><b>申復理由</b></td>
                    <td colspan="3">{reason}</td>
                </tr>
            </table>
        '''
        text_edit = QtWidgets.QTextEdit(self.ui.tableWidget_appeal_items)
        text_edit.setReadOnly(True)
        text_edit.setHtml(html)

        button_delete = QtWidgets.QPushButton(self.ui.tableWidget_appeal_items)
        button_delete.setIcon(QtGui.QIcon('./icons/edit-delete.png'))
        # button_delete.setFlat(True)
        button_delete.setText('刪除')
        button_delete.clicked.connect(lambda: self._remove_appeal_items(ins_appeal_items_key))

        button_edit = QtWidgets.QPushButton(self.ui.tableWidget_appeal_items)
        button_edit.setIcon(QtGui.QIcon('./icons/gtk-edit.svg'))
        # button_edit.setFlat(True)
        button_edit.setText('修改')
        button_edit.clicked.connect(lambda: self._edit_appeal_items(ins_appeal_items_key))

        vertical_spacer = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)

        v_layout = QtWidgets.QVBoxLayout()
        v_layout.setSpacing(10)
        v_layout.addWidget(button_edit)
        v_layout.addWidget(button_delete)
        v_layout.addItem(vertical_spacer)

        widget = QtWidgets.QWidget()
        widget.setLayout(v_layout)

        self.ui.tableWidget_appeal_items.setCellWidget(row_no, 1, text_edit)
        self.ui.tableWidget_appeal_items.setCellWidget(row_no, 2, widget)

    def _open_nhi_vpn(self):
        med_vpn_addr = 'https://medvpn.nhi.gov.tw/iwse0000/IWSE0020S01.aspx'
        webbrowser.open(med_vpn_addr, new=0)  # 0: open in existing tab, 2: new tab

    @staticmethod
    def _message_box(title, message, hint):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setInformativeText(hint)
        msg_box.setStandardButtons(QMessageBox.NoButton)

        return msg_box

    def _upload_data(self):
        ins_xml_file = module_utils.get_ins_appeal_xml(
            self, self.database, self.system_settings, self.apply_year, self.apply_month,
            self.apply_date, self.apply_period, self.apply_type_code, self.clinic_id,
            self.apply_upload_date,
        )
        ins_xml_file.create_xml_file()
        xml_file = ins_xml_file.get_xml_file_name()
        zip_file = xml_file.replace('xml', 'zip')

        if not os.path.isfile(zip_file):
            system_utils.show_message_box(
                QMessageBox.Information,
                '無申復檔案',
                '<font size="5" color="red"><b>找不到申復檔案, 請確定是否已輸入申復資料.</b></font>',
                '請重新執行申復上傳作業.'
            )
            return

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('上傳申復檔')
        msg_box.setText(f"<font size='4' color='red'><b>確定上傳健保申復檔案?<br>申報檔名: {zip_file}</b></font>")
        msg_box.setInformativeText("注意！資料上傳前, 請檢查申復資料是否正確!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        upload_xml_file = msg_box.exec_()
        if not upload_xml_file:
            return

        type_code = '07'  # 醫療費用電子申復
        nhi_utils.NHI_SendB(self.system_settings, type_code, zip_file)

        try:
            self._write_log()
        except Exception:
            pass

    def _write_log(self):
        log_type = '申復日期'
        apply_date = f'{self.apply_year}-{self.apply_month:0>2}'
        generate_date = self.ins_generate_date.toString('yyyy-MM-dd')

        self.database.exec_sql(f'''
            DELETE FROM system_log
            WHERE
                LogType = "{log_type}" AND
                LogName = "{apply_date}"
        ''')
        log_utils.write_system_log(self.database, '申復日期', apply_date, generate_date)

    def _add_ins_appeal_items(self):
        ins_appeal_key = self._get_ins_appeal_key()
        if ins_appeal_key is None:
            return

        self._open_dialog_appeal_items(ins_appeal_key)

    def _edit_appeal_items(self, ins_appeal_items_key):
        ins_appeal_key = self._get_ins_appeal_key()
        if ins_appeal_key is None:
            return

        self._open_dialog_appeal_items(ins_appeal_key, ins_appeal_items_key)

    def _remove_appeal_items(self, ins_appeal_items_key):
        msg_box = dialog_utils.get_message_box(
            '刪除申復醫令資料', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除此筆申復醫令資料?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        self.database.exec_sql(f'DELETE FROM insappeal_items WHERE InsAppealItemsKey = {ins_appeal_items_key}')
        self._refresh_appeal_items()

    def _open_dialog_appeal_items(self, ins_appeal_key, ins_appeal_items_key=None):
        dialog = dialog_utils.get_dialog_ins_appeal_items(
            self, self.database, self.system_settings, self.apply_date, ins_appeal_items_key, ins_appeal_key)

        if dialog.exec_():
            self._refresh_appeal_items()

        dialog.deleteLater()

    def _refresh_appeal_items(self):
        ins_appeal_key = self._get_ins_appeal_key()
        self._read_ins_appeal_items(ins_appeal_key)
