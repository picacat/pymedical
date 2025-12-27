# -*- coding: utf-8 -*-

import datetime

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QPushButton

from libs import (class_utils, date_utils, dialog_utils, export_utils,
                  number_utils, personnel_utils, printer_utils, string_utils,
                  system_utils, ui_utils)


# 樣板 2018.01.31
class ReturnCard(QtWidgets.QMainWindow):
    program_name = '健保卡欠還卡'

    # 初始化
    def __init__(self, parent=None, *args):
        super(ReturnCard, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_permission()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_return_card(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_RETURN_CARD, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_return_card = class_utils.get_table_widget(self.ui.tableWidget_return_card, self.database)
        self.table_widget_return_card.set_column_hidden([0, 1])
        # self._set_table_width()
        self._set_date()
        self.ui.statusbar.showMessage('紅色字體代表欠卡日期超過10天')

    def _set_date(self):
        last_month = datetime.date.today().replace(day=1) - datetime.timedelta(days=1)
        self.ui.dateEdit_start_date.setDate(last_month.replace(day=1))
        self.ui.dateEdit_end_date.setDate(datetime.date.today())

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_return_card)
        self.ui.action_return_card.triggered.connect(self.return_card)
        self.ui.action_add_deposit.triggered.connect(self._add_deposit)
        self.ui.action_remove_deposit.triggered.connect(self._remove_deposit)
        self.ui.action_open_medical_record.triggered.connect(self.open_medical_record)
        self.ui.action_undo.triggered.connect(self._undo_return_card)
        self.ui.action_print_registration_form.triggered.connect(self._print_registration_form)
        self.ui.action_print_return_registration_form.triggered.connect(self._print_return_registration_form)
        self.ui.action_modify_deposit_fee.triggered.connect(self._modify_deposit_fee)
        self.ui.action_change_return_date.triggered.connect(self._change_return_date)
        self.ui.action_change_return_period.triggered.connect(self._change_return_period)
        self.ui.action_export_to_excel.triggered.connect(self._export_to_excel)
        self.ui.tableWidget_return_card.doubleClicked.connect(self.open_medical_record)
        self.ui.tableWidget_return_card.itemSelectionChanged.connect(self._return_card_item_changed)
        self.ui.dateEdit_start_date.dateChanged.connect(self.read_return_card)
        self.ui.dateEdit_end_date.dateChanged.connect(self.read_return_card)
        self.ui.radioButton_deposit.clicked.connect(self.read_return_card)
        self.ui.radioButton_return.clicked.connect(self.read_return_card)
        self.ui.radioButton_all.clicked.connect(self.read_return_card)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(self.database, self.program_name, '健保還卡', self.user_name) != 'Y':
            self.ui.action_return_card.setEnabled(False)
        if personnel_utils.get_permission(self.database, self.program_name, '調閱病歷', self.user_name) != 'Y':
            self.ui.action_open_medical_record.setEnabled(False)
        if personnel_utils.get_permission(self.database, self.program_name, '還原欠卡', self.user_name) != 'Y':
            self.ui.action_undo.setEnabled(False)
        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.action_export_to_excel.setEnabled(False)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [80, 90, 100, 90, 90, 130, 130, 150, 180, 80, 180, 80, 70, 50, 100, 90, 60, 50]
        self.table_widget_return_card.set_table_heading_width(width)

    # 列印欠卡收據
    def _print_registration_form(self):
        case_key = self.table_widget_return_card.field_value(1)
        self.print_registration_form('直接列印', case_key)

    # 列印還卡收據
    def _print_return_registration_form(self):
        case_key = self.table_widget_return_card.field_value(1)
        self.print_registration_form('還卡收據', case_key)

    # 列印掛號收據
    def print_registration_form(self, printable, case_key=False):
        if not case_key:
            case_key = self.table_widget_return_card.field_value(1)

        printer_utils.print_regist_form(
            self, self.database, self.system_settings, case_key, printable
        )

    # 讀取欠卡資料
    def read_return_card(self):
        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')

        return_condition = f'''
            (DepositDate BETWEEN "{start_date}" AND "{end_date}" OR
             ReturnDate BETWEEN "{start_date}" AND "{end_date}")
        '''
        if self.ui.radioButton_deposit.isChecked():
            return_condition += '''
                AND ReturnDate IS NULL
            '''
        elif self.ui.radioButton_return.isChecked():
            return_condition += '''
                AND ReturnDate IS NOT NULL
            '''

        sql = f'''
            SELECT
                deposit.*,
                cases.Card, cases.Continuance, cases.DoctorDone, cases.Period AS CasePeriod,
                cases.RegistType,
                patient.Birthday, patient.ID, patient.CardNo
            FROM deposit
                LEFT JOIN cases ON cases.CaseKey = deposit.CaseKey
                LEFT JOIN patient ON patient.PatientKey = deposit.PatientKey
            WHERE
                {return_condition}
            ORDER BY DepositDate DESC
        '''

        self.table_widget_return_card.set_db_data(sql, self._set_deposit_data)
        self._set_tool_buttons()
        self._return_card_item_changed()

        if self.patient_key is not None:
            self._locate_patient(self.patient_key)

    def _set_tool_buttons(self):
        if self.ui.tableWidget_return_card.rowCount() <= 0:
            enabled = False
        else:
            enabled = True

        self.ui.action_open_medical_record.setEnabled(enabled)
        self.ui.action_return_card.setEnabled(enabled)
        self.ui.action_undo.setEnabled(enabled)

        self._set_permission()

    def _set_deposit_data(self, row_no, row):
        if string_utils.xstr(row['DoctorDone']) == 'True':
            doctor_done = '是'
        else:
            doctor_done = '否'

        deposit_date = row['DepositDate'].date()
        present = datetime.datetime.today().date()
        delta = present - deposit_date
        return_date = row['ReturnDate']
        if return_date is not None:
            return_date = return_date.strftime('%Y-%m-%d %H:%M')
        return_card_data = [
            string_utils.xstr(row['DepositKey']),
            string_utils.xstr(row['CaseKey']),
            string_utils.xstr(row['RegistType'])[:6],
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Birthday']),
            string_utils.xstr(row['ID']),
            string_utils.xstr(row['CardNo']),
            row['DepositDate'].strftime('%Y-%m-%d %H:%M'),
            string_utils.xstr(row['CasePeriod']),
            return_date,
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['Card']),
            string_utils.xstr(row['Continuance']),
            string_utils.xstr(row['Register']),
            string_utils.xstr(row['Refunder']),
            string_utils.xstr(row['Fee']),
            doctor_done,
        ]

        for column in range(len(return_card_data)):
            self.ui.tableWidget_return_card.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(return_card_data[column])
            )
            if column in [3, 16]:
                self.ui.tableWidget_return_card.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif column in [9, 11, 13, 17]:
                self.ui.tableWidget_return_card.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if delta.days > 10:
                self.ui.tableWidget_return_card.item(
                    row_no, column).setForeground(
                    QtGui.QColor('red')
                )

    def refresh_record(self):
        deposit_key = self.table_widget_return_card.field_value(0)
        sql = f'''
            SELECT
                deposit.*,
                cases.Card, cases.Continuance, cases.DoctorDone, cases.Period AS CasePeriod,
                cases.RegistType,
                patient.Birthday, patient.ID, patient.CardNo
            FROM deposit
                LEFT JOIN cases ON cases.CaseKey = deposit.CaseKey
                LEFT JOIN patient ON patient.PatientKey = deposit.PatientKey
            WHERE
                DepositKey = {deposit_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            self._set_deposit_data(self.ui.tableWidget_return_card.currentRow(), rows[0])

        self._return_card_item_changed()
        self.ui.tableWidget_return_card.resizeColumnsToContents()

    def _get_previous_deposit_date(self, deposit_date, patient_key):
        previous_deposit_date = None

        deposit_date = date_utils.str_to_date(deposit_date)
        last_day = deposit_date.day
        deposit_date = deposit_date - datetime.timedelta(days=1)

        if last_day <= 20:  # 本月20日以前，上個月可能還沒申報，可以還上個月的欠卡
            last_deposit_date = (deposit_date - datetime.timedelta(days=30-1)).strftime('%Y-%m-01 00:00:00')
        else:
            last_deposit_date = deposit_date.strftime('%Y-%m-01 00:00:00')  # 申報完了，只能還這個月

        sql = f'''
            SELECT CaseDate FROM cases
            WHERE
                CaseDate BETWEEN "{last_deposit_date}" AND "{deposit_date} 23:59:59" AND
                PatientKey = {patient_key} AND
                Card = "欠卡"
            ORDER BY CaseDate LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            previous_deposit_date = rows[0]['CaseDate'].strftime('%Y-%m-%d')

        return previous_deposit_date

    def _locate_previous_card(self, deposit_date, patient_key):
        for row_no in range(self.ui.tableWidget_return_card.rowCount()):
            item = self.ui.tableWidget_return_card.item(row_no, 3)
            if item is None:
                continue

            if item.text() != patient_key:
                continue

            item = self.ui.tableWidget_return_card.item(row_no, 8)
            if item is None:
                continue

            if item.text()[:10] == deposit_date:
                self.ui.tableWidget_return_card.setCurrentCell(row_no, 0)
                break   

    # 還卡
    def return_card(self):
        deposit_date = self.table_widget_return_card.field_value(8)[:10]
        patient_key = self.table_widget_return_card.field_value(3)
        previous_deposit_date = self._get_previous_deposit_date(deposit_date, patient_key)
        if previous_deposit_date is not None:
            msg_box = dialog_utils.get_message_box(
                '請先還卡之前的欠卡', QMessageBox.Warning,
                f'''
                    <font size="5" color="red"><b>此筆病歷在{previous_deposit_date}尚有欠卡,
                    請先執行前次的還卡作業.</b></font>
                ''',
                '請依照還卡日期順序還卡.',
                ok_button='繼續還卡', cancel_button=f'我要先還{previous_deposit_date}的欠卡'
            )
            continue_return_card = msg_box.exec_()
            if not continue_return_card:
                self._locate_previous_card(previous_deposit_date, patient_key)
                return

        if self.table_widget_return_card.field_value(12) != '欠卡':
            system_utils.show_message_box(
                QMessageBox.Critical,
                '不需還卡',
                '<font size="5" color="red"><b>此筆病歷的卡序不是"欠卡", 不需執行還卡作業.</b></font>',
                '請確定此人是否已經還卡.'
            )
            return

        case_key = self.table_widget_return_card.field_value(1)
        sql = f'SELECT InProgress FROM wait WHERE CaseKey = {case_key}'
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            if string_utils.xstr(row['InProgress']) == 'Y':
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    '暫時無法還卡',
                    '<font size="5" color="red"><b>此筆病歷正在看診中, 暫時不執行還卡作業.</b></font>',
                    '請確定此人看診完畢後, 再執行還卡作業, 已利系統進行健保卡病歷及處方寫入的程序.'
                )
                return

        # if self.table_widget_return_card.field_value(17) != '是':  # 有可能還沒看診，可以先還卡
        #     system_utils.show_message_box(
        #         QMessageBox.Critical,
        #         '暫時無法還卡',
        #         '<font size="5" color="red"><b>此筆病歷尚未看診完畢, 暫時不需執行還卡作業.</b></font>',
        #         '請確定此人看診完畢後, 再執行還卡作業, 已利系統進行健保卡病歷及處方寫入的程序.'
        #     )
        #     return

        patient_key = self.table_widget_return_card.field_value(3)
        dialog = dialog_utils.get_dialog_return_card(
            self, self.database, self.system_settings,
            self.table_widget_return_card.field_value(0),
            case_key, patient_key,
        )
        if dialog.exec_():
            self.refresh_record()

        dialog.deleteLater()

    def open_medical_record(self):
        if (self.user_name != '超級使用者' and
                personnel_utils.get_permission(self.database, self.program_name, '調閱病歷', self.user_name) != 'Y'):
            return

        case_key = self.table_widget_return_card.field_value(1)
        self.parent.open_medical_record(case_key, '欠還卡作業')

    def _undo_return_card(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle('還原成欠卡')
        msg_box.setText(
            '''
            <font size="5" color="red">
              <b>將已還卡資料還原成欠卡狀態?<br>
            </font>
            '''
        )
        msg_box.setInformativeText("若已經執行IC卡還卡，則會產生新的健保卡序!")
        msg_box.addButton(QPushButton("還原"), QMessageBox.YesRole)
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        cancel = msg_box.exec_()
        if cancel:
            return

        self.refresh_record()
        deposit_key = self.table_widget_return_card.field_value(0)
        case_key = self.table_widget_return_card.field_value(1)

        sql = f'''
            UPDATE deposit
            SET
                ReturnDate = NULL, Period = NULL, Refunder = NULL
            WHERE
                DepositKey = {deposit_key}
        '''
        self.database.exec_sql(sql)

        sql = f'''
            UPDATE cases
            SET
                Card = "欠卡"
            WHERE
                CaseKey = {case_key}'''
        self.database.exec_sql(sql)

        self.refresh_record()

    def _return_card_item_changed(self):
        return_date = self.table_widget_return_card.field_value(10)

        if return_date == '':
            enabled = False
        else:
            enabled = True

        self.ui.action_return_card.setEnabled(not enabled)
        self.ui.action_undo.setEnabled(enabled)

        self._set_permission()

    # 新增欠卡資料
    def _add_deposit(self):
        dialog = dialog_utils.get_dialog_add_deposit(
            self, self.database, self.system_settings
        )

        if not dialog.exec_():
            dialog.deleteLater()
            return

        self.read_return_card()
        dialog.deleteLater()

    # 刪除欠卡資料
    def _remove_deposit(self):
        name = self.table_widget_return_card.field_value(4)
        msg_box = dialog_utils.get_message_box(
            '刪除欠卡資料', QMessageBox.Warning,
            f'''
                <font size="5" color="red">
                    <b>確定刪除{name}的欠卡資料?</b>
                </font>
            ''',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_return_card.field_value(0)
        self.database.delete_record('deposit', 'DepositKey', key)
        self.ui.tableWidget_return_card.removeRow(self.ui.tableWidget_return_card.currentRow())

    def _locate_patient(self, patient_key):
        patient_key = string_utils.xstr(patient_key)

        for row_no in range(self.ui.tableWidget_return_card.rowCount()):
            self.ui.tableWidget_return_card.setCurrentCell(row_no, 3)
            patient_key_item = self.ui.tableWidget_return_card.item(row_no, 3).text()
            if patient_key == patient_key_item:
                break

    def _modify_deposit_fee(self):
        deposit_fee = number_utils.get_integer(self.table_widget_return_card.field_value(16))

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')
        deposit_fee, ok = input_dialog.getInt(
            self, '更改欠卡費', '請輸入新的欠卡費', deposit_fee, 0, 10000, 100)
        if not ok:
            return

        deposit_key = self.table_widget_return_card.field_value(0)
        case_key = self.table_widget_return_card.field_value(1)

        sql = f'''
            UPDATE deposit
            SET
                Fee = {deposit_fee}
            WHERE
                DepositKey = {deposit_key}
        '''
        self.database.exec_sql(sql)

        sql = f'''
            UPDATE cases
            SET
                DepositFee = {deposit_fee}
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

        self.refresh_record()

    def _change_return_date(self):
        return_date = date_utils.get_dialog_date(
            self, self.database, self.system_settings, call_from=self.program_name)
        if return_date is None:
            return

        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        return_date = f'{return_date} {current_time}'

        deposit_key = self.table_widget_return_card.field_value(0)
        sql = f'''
            UPDATE deposit
            SET
                ReturnDate = "{return_date}"
            WHERE
                DepositKey = {deposit_key}
        '''
        self.database.exec_sql(sql)
        self.refresh_record()

    def _change_return_period(self):
        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')
        items = ('早班', '午班', '晚班')
        period, ok = input_dialog.getItem(
            self, '選擇班別', '請選擇還卡班別', items, 0, False)
        if not ok or not period:
            return

        deposit_key = self.table_widget_return_card.field_value(0)
        sql = f'''
            UPDATE deposit
            SET
                Period = "{period}"
            WHERE
                DepositKey = {deposit_key}
        '''
        self.database.exec_sql(sql)
        self.refresh_record()

    def _export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出欠還卡名單",
            f'欠還卡名單.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_return_card,
            [0, 1], [3, 16], '欠還卡名單',
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )
