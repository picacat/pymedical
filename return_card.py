import datetime

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QPushButton

from libs import (
    class_utils,
    date_utils,
    dialog_utils,
    export_utils,
    number_utils,
    personnel_utils,
    printer_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 欠還卡作業
#
# 修正重點:
#   1. 權限只在開啟作業時查一次(原本每換一次選取列就打 4 次資料庫)
#   2. _get_previous_deposit_date 改以「今天」判斷申報月界, 並正確算出上個月1日
#   3. 紅字只標尚未還卡且超過10天的資料(原本已還卡的也會標紅)
#   4. 尚未還卡的資料擋掉「更改還卡日期 / 更改還卡班別 / 列印還卡收據」
#   5. 所有動作先確認有選取列, 避免空表格時組出壞掉的 SQL
#   6. _locate_patient / _locate_previous_card 找不到時不再把游標留在錯的列
#   7. 還原成欠卡時一併還原 wait.Card, 並移除多餘的第一次 refresh
#   8. 寫入動作改為參數化
#
# 註: 本檔案的寫入動作使用 database.exec_sql(sql, params) 的參數化形式.
class ReturnCard(QtWidgets.QMainWindow):
    program_name = "健保卡欠還卡"

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.permission = {}

        self._read_permission()
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
        self.table_widget_return_card = class_utils.get_table_widget(
            self.ui.tableWidget_return_card, self.database
        )
        self.table_widget_return_card.set_column_hidden([0, 1])
        # self._set_table_width()
        self._set_date()
        self.ui.statusbar.showMessage("紅色字體代表尚未還卡且欠卡日期超過10天")

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
        self.ui.action_print_registration_form.triggered.connect(
            self._print_registration_form
        )
        self.ui.action_print_return_registration_form.triggered.connect(
            self._print_return_registration_form
        )
        self.ui.action_modify_deposit_fee.triggered.connect(self._modify_deposit_fee)
        self.ui.action_change_return_date.triggered.connect(self._change_return_date)
        self.ui.action_change_return_period.triggered.connect(
            self._change_return_period
        )
        self.ui.action_export_to_excel.triggered.connect(self._export_to_excel)
        self.ui.tableWidget_return_card.doubleClicked.connect(self.open_medical_record)
        self.ui.tableWidget_return_card.itemSelectionChanged.connect(
            self._return_card_item_changed
        )
        self.ui.dateEdit_start_date.dateChanged.connect(self.read_return_card)
        self.ui.dateEdit_end_date.dateChanged.connect(self.read_return_card)
        self.ui.radioButton_deposit.clicked.connect(self.read_return_card)
        self.ui.radioButton_return.clicked.connect(self.read_return_card)
        self.ui.radioButton_all.clicked.connect(self.read_return_card)

    # 權限只在開啟作業時查一次, 不要每次換選取列都打資料庫
    def _read_permission(self):
        self.permission = {
            "健保還卡": True,
            "調閱病歷": True,
            "還原欠卡": True,
            "匯出": True,
        }

        if self.user_name == "超級使用者":
            return

        self.permission["健保還卡"] = (
            personnel_utils.get_permission(
                self.database, self.program_name, "健保還卡", self.user_name
            )
            == "Y"
        )
        self.permission["調閱病歷"] = (
            personnel_utils.get_permission(
                self.database, self.program_name, "調閱病歷", self.user_name
            )
            == "Y"
        )
        self.permission["還原欠卡"] = (
            personnel_utils.get_permission(
                self.database, self.program_name, "還原欠卡", self.user_name
            )
            == "Y"
        )
        self.permission["匯出"] = (
            personnel_utils.get_permission(
                self.database, "系統作業", "關閉匯出功能", self.user_name
            )
            != "Y"
        )

    # 套用權限: 只會把按鈕關掉, 不會打開
    def _set_permission(self):
        if not self.permission.get("健保還卡", True):
            self.ui.action_return_card.setEnabled(False)

        if not self.permission.get("調閱病歷", True):
            self.ui.action_open_medical_record.setEnabled(False)

        if not self.permission.get("還原欠卡", True):
            self.ui.action_undo.setEnabled(False)

        if not self.permission.get("匯出", True):
            self.ui.action_export_to_excel.setEnabled(False)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [
            80,
            90,
            100,
            90,
            90,
            130,
            130,
            150,
            180,
            80,
            180,
            80,
            70,
            50,
            100,
            90,
            60,
            50,
        ]
        self.table_widget_return_card.set_table_heading_width(width)

    # 目前有沒有選到資料
    def _has_current_row(self):
        if self.ui.tableWidget_return_card.rowCount() <= 0:
            return False

        return self.ui.tableWidget_return_card.currentRow() >= 0

    # 這筆是否已經還卡
    def _is_returned(self):
        return string_utils.xstr(self.table_widget_return_card.field_value(10)) != ""

    # 尚未還卡就擋下來
    def _check_returned(self):
        if self._is_returned():
            return True

        system_utils.show_message_box(
            QMessageBox.Warning,
            "尚未還卡",
            '<font size="5" color="red"><b>這筆資料還沒有還卡, 無法執行此項作業.</b></font>',
            "請先執行還卡作業, 取得健保卡序之後再更改還卡日期或班別.",
        )

        return False

    # 列印欠卡收據
    def _print_registration_form(self):
        if not self._has_current_row():
            return

        case_key = self.table_widget_return_card.field_value(1)
        self.print_registration_form("直接列印", case_key)

    # 列印還卡收據
    def _print_return_registration_form(self):
        if not self._has_current_row() or not self._check_returned():
            return

        case_key = self.table_widget_return_card.field_value(1)
        self.print_registration_form("還卡收據", case_key)

    # 列印掛號收據
    def print_registration_form(self, printable, case_key=False):
        if not case_key:
            case_key = self.table_widget_return_card.field_value(1)

        printer_utils.print_regist_form(
            self, self.database, self.system_settings, case_key, printable
        )

    # 讀取欠卡資料
    def read_return_card(self):
        start_date = self.ui.dateEdit_start_date.date().toString("yyyy-MM-dd 00:00:00")
        end_date = self.ui.dateEdit_end_date.date().toString("yyyy-MM-dd 23:59:59")

        return_condition = f'''
            (DepositDate BETWEEN "{start_date}" AND "{end_date}" OR
             ReturnDate BETWEEN "{start_date}" AND "{end_date}")
        '''
        if self.ui.radioButton_deposit.isChecked():
            return_condition += """
                AND ReturnDate IS NULL
            """
        elif self.ui.radioButton_return.isChecked():
            return_condition += """
                AND ReturnDate IS NOT NULL
            """

        sql = f"""
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
        """

        self.table_widget_return_card.set_db_data(sql, self._set_deposit_data)
        self._set_tool_buttons()
        self._return_card_item_changed()

        if self.patient_key is not None:
            self._locate_patient(self.patient_key)
            self.patient_key = None  # 只在第一次進入時定位, 之後改查詢條件不要再被拉走

    def _set_tool_buttons(self):
        enabled = self.ui.tableWidget_return_card.rowCount() > 0

        self.ui.action_open_medical_record.setEnabled(enabled)
        self.ui.action_return_card.setEnabled(enabled)
        self.ui.action_undo.setEnabled(enabled)
        self.ui.action_remove_deposit.setEnabled(enabled)
        self.ui.action_modify_deposit_fee.setEnabled(enabled)
        self.ui.action_print_registration_form.setEnabled(enabled)

        self._set_permission()

    def _set_deposit_data(self, row_no, row):
        if string_utils.xstr(row["DoctorDone"]) == "True":
            doctor_done = "是"
        else:
            doctor_done = "否"

        deposit_date = row["DepositDate"]
        if deposit_date is None:
            deposit_date_text = ""
            delta_days = 0
        else:
            deposit_date_text = deposit_date.strftime("%Y-%m-%d %H:%M")
            delta_days = (datetime.date.today() - deposit_date.date()).days

        return_date = row["ReturnDate"]
        if return_date is None:
            return_date_text = ""
        else:
            return_date_text = return_date.strftime("%Y-%m-%d %H:%M")

        return_card_data = [
            string_utils.xstr(row["DepositKey"]),
            string_utils.xstr(row["CaseKey"]),
            string_utils.xstr(row["RegistType"])[:6],
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["Birthday"]),
            string_utils.xstr(row["ID"]),
            string_utils.xstr(row["CardNo"]),
            deposit_date_text,
            string_utils.xstr(row["CasePeriod"]),
            return_date_text,
            string_utils.xstr(row["Period"]),
            string_utils.xstr(row["Card"]),
            string_utils.xstr(row["Continuance"]),
            string_utils.xstr(row["Register"]),
            string_utils.xstr(row["Refunder"]),
            string_utils.xstr(row["Fee"]),
            doctor_done,
        ]

        # 已經還卡的就不必再標紅字了
        overdue = return_date is None and delta_days > 10

        for column in range(len(return_card_data)):
            self.ui.tableWidget_return_card.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(return_card_data[column])
            )
            if column in [3, 16]:
                self.ui.tableWidget_return_card.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif column in [9, 11, 13, 17]:
                self.ui.tableWidget_return_card.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if overdue:
                self.ui.tableWidget_return_card.item(row_no, column).setForeground(
                    QtGui.QColor("red")
                )

    def refresh_record(self):
        if not self._has_current_row():
            return

        deposit_key = number_utils.get_integer(
            self.table_widget_return_card.field_value(0)
        )
        sql = f"""
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
        """
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            self._set_deposit_data(
                self.ui.tableWidget_return_card.currentRow(), rows[0]
            )

        self._return_card_item_changed()
        self.ui.tableWidget_return_card.resizeColumnsToContents()

    # 找出這個病人在本筆之前、還沒還卡而且還來得及補還的最早一筆
    def _get_previous_deposit_date(self, deposit_date, patient_key):
        deposit_date = date_utils.str_to_date(deposit_date)
        end_date = deposit_date - datetime.timedelta(days=1)

        # 申報的月界要以「今天」為準, 不是欠卡那天:
        # 本月20日以前, 上個月可能還沒申報, 上個月的欠卡還可以還;
        # 20日以後已經申報完了, 只能還這個月的.
        today = datetime.date.today()
        if today.day <= 20:
            start_date = (today.replace(day=1) - datetime.timedelta(days=1)).replace(
                day=1
            )
        else:
            start_date = today.replace(day=1)

        if start_date > end_date:  # 本筆本身就在可補還區間之前, 不必再往前找
            return None

        sql = f'''
            SELECT CaseDate FROM cases
            WHERE
                CaseDate BETWEEN "{start_date} 00:00:00" AND "{end_date} 23:59:59" AND
                PatientKey = {patient_key} AND
                Card = "欠卡"
            ORDER BY CaseDate LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return rows[0]["CaseDate"].strftime("%Y-%m-%d")

    def _locate_previous_card(self, deposit_date, patient_key):
        for row_no in range(self.ui.tableWidget_return_card.rowCount()):
            patient_item = self.ui.tableWidget_return_card.item(row_no, 3)
            deposit_item = self.ui.tableWidget_return_card.item(row_no, 8)
            if patient_item is None or deposit_item is None:
                continue

            if patient_item.text() != patient_key:
                continue

            if deposit_item.text()[:10] == deposit_date:
                self.ui.tableWidget_return_card.setCurrentCell(row_no, 0)
                return

        # 前次欠卡不在目前的查詢範圍內
        system_utils.show_message_box(
            QMessageBox.Information,
            "不在查詢範圍內",
            f'<font size="5" color="red"><b>{deposit_date}的欠卡不在目前的查詢範圍內.</b></font>',
            "請把查詢的起始日期往前調整後, 再執行還卡作業.",
        )

    # 還卡
    def return_card(self):
        if not self._has_current_row():
            return

        deposit_date = string_utils.xstr(self.table_widget_return_card.field_value(8))[
            :10
        ]
        patient_key = self.table_widget_return_card.field_value(3)
        previous_deposit_date = self._get_previous_deposit_date(
            deposit_date, patient_key
        )
        if previous_deposit_date is not None:
            msg_box = dialog_utils.get_message_box(
                "請先還卡之前的欠卡",
                QMessageBox.Warning,
                f"""
                    <font size="5" color="red"><b>此筆病歷在{previous_deposit_date}尚有欠卡,
                    請先執行前次的還卡作業.</b></font>
                """,
                "請依照還卡日期順序還卡.",
                ok_button="繼續還卡",
                cancel_button=f"我要先還{previous_deposit_date}的欠卡",
            )
            continue_return_card = msg_box.exec_()
            if not continue_return_card:
                self._locate_previous_card(previous_deposit_date, patient_key)
                return

        if self.table_widget_return_card.field_value(12) != "欠卡":
            system_utils.show_message_box(
                QMessageBox.Critical,
                "不需還卡",
                '<font size="5" color="red"><b>此筆病歷的卡序不是"欠卡", 不需執行還卡作業.</b></font>',
                "請確定此人是否已經還卡.",
            )
            return

        case_key = self.table_widget_return_card.field_value(1)
        sql = f"SELECT InProgress FROM wait WHERE CaseKey = {case_key}"
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            if string_utils.xstr(row["InProgress"]) == "Y":
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "暫時無法還卡",
                    '<font size="5" color="red"><b>此筆病歷正在看診中, 暫時不執行還卡作業.</b></font>',
                    "請確定此人看診完畢後, 再執行還卡作業, 已利系統進行健保卡病歷及處方寫入的程序.",
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
            self,
            self.database,
            self.system_settings,
            self.table_widget_return_card.field_value(0),
            case_key,
            patient_key,
        )
        if dialog.exec_():
            self.refresh_record()

        dialog.deleteLater()

    def open_medical_record(self):
        if not self.permission.get("調閱病歷", True):
            return

        if not self._has_current_row():
            return

        case_key = self.table_widget_return_card.field_value(1)
        self.parent.open_medical_record(case_key, "欠還卡作業")

    def _undo_return_card(self):
        if not self._has_current_row():
            return

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("還原成欠卡")
        msg_box.setText(
            """
            <font size="5" color="red">
              <b>將已還卡資料還原成欠卡狀態?<br>
            </font>
            """
        )
        msg_box.setInformativeText("若已經執行IC卡還卡，則會產生新的健保卡序!")
        msg_box.addButton(QPushButton("還原"), QMessageBox.YesRole)
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        cancel = msg_box.exec_()
        if cancel:
            return

        deposit_key = number_utils.get_integer(
            self.table_widget_return_card.field_value(0)
        )
        case_key = number_utils.get_integer(
            self.table_widget_return_card.field_value(1)
        )

        self.database.exec_sql(
            """
                UPDATE deposit
                SET ReturnDate = NULL, Period = NULL, Refunder = NULL
                WHERE DepositKey = %s
            """,
            (deposit_key,),
        )
        self.database.exec_sql(
            'UPDATE cases SET Card = "欠卡" WHERE CaseKey = %s', (case_key,)
        )
        # wait 沒有一起還原的話, 候診名單與病歷的卡序會不一致
        self.database.exec_sql(
            'UPDATE wait SET Card = "欠卡" WHERE CaseKey = %s', (case_key,)
        )

        self.refresh_record()

    def _return_card_item_changed(self):
        if not self._has_current_row():
            self.ui.action_return_card.setEnabled(False)
            self.ui.action_undo.setEnabled(False)
            self.ui.action_change_return_date.setEnabled(False)
            self.ui.action_change_return_period.setEnabled(False)
            self.ui.action_print_return_registration_form.setEnabled(False)
            self._set_permission()
            return

        returned = self._is_returned()

        self.ui.action_return_card.setEnabled(not returned)
        self.ui.action_undo.setEnabled(returned)
        # 還沒還卡就沒有還卡日期/班別可以改, 也沒有還卡收據可以印
        self.ui.action_change_return_date.setEnabled(returned)
        self.ui.action_change_return_period.setEnabled(returned)
        self.ui.action_print_return_registration_form.setEnabled(returned)

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
        if not self._has_current_row():
            return

        name = self.table_widget_return_card.field_value(4)
        msg_box = dialog_utils.get_message_box(
            "刪除欠卡資料",
            QMessageBox.Warning,
            f"""
                <font size="5" color="red">
                    <b>確定刪除{name}的欠卡資料?</b>
                </font>
            """,
            "注意！資料刪除後, 將無法回復!\n"
            "病歷的卡序仍然會維持「欠卡」, 需要的話請另外到病歷修改.",
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_return_card.field_value(0)
        self.database.delete_record("deposit", "DepositKey", key)
        self.ui.tableWidget_return_card.removeRow(
            self.ui.tableWidget_return_card.currentRow()
        )
        self._set_tool_buttons()
        self._return_card_item_changed()

    def _locate_patient(self, patient_key):
        patient_key = string_utils.xstr(patient_key)

        for row_no in range(self.ui.tableWidget_return_card.rowCount()):
            item = self.ui.tableWidget_return_card.item(row_no, 3)
            if item is None:
                continue

            if item.text() == patient_key:  # 先比對再定位, 找不到就不要移動游標
                self.ui.tableWidget_return_card.setCurrentCell(row_no, 3)
                return

    def _modify_deposit_fee(self):
        if not self._has_current_row():
            return

        deposit_fee = number_utils.get_integer(
            self.table_widget_return_card.field_value(16)
        )

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")
        deposit_fee, ok = input_dialog.getInt(
            self, "更改欠卡費", "請輸入新的欠卡費", deposit_fee, 0, 10000, 100
        )
        if not ok:
            return

        deposit_key = number_utils.get_integer(
            self.table_widget_return_card.field_value(0)
        )
        case_key = number_utils.get_integer(
            self.table_widget_return_card.field_value(1)
        )

        self.database.exec_sql(
            "UPDATE deposit SET Fee = %s WHERE DepositKey = %s",
            (deposit_fee, deposit_key),
        )
        self.database.exec_sql(
            "UPDATE cases SET DepositFee = %s WHERE CaseKey = %s",
            (deposit_fee, case_key),
        )

        self.refresh_record()

    def _change_return_date(self):
        if not self._has_current_row() or not self._check_returned():
            return

        return_date = date_utils.get_dialog_date(
            self, self.database, self.system_settings, call_from=self.program_name
        )
        if return_date is None:
            return

        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        return_date = f"{return_date} {current_time}"

        deposit_key = number_utils.get_integer(
            self.table_widget_return_card.field_value(0)
        )
        self.database.exec_sql(
            "UPDATE deposit SET ReturnDate = %s WHERE DepositKey = %s",
            (return_date, deposit_key),
        )
        self.refresh_record()

    def _change_return_period(self):
        if not self._has_current_row() or not self._check_returned():
            return

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")
        items = ("早班", "午班", "晚班")
        period, ok = input_dialog.getItem(
            self, "選擇班別", "請選擇還卡班別", items, 0, False
        )
        if not ok or not period:
            return

        deposit_key = number_utils.get_integer(
            self.table_widget_return_card.field_value(0)
        )
        self.database.exec_sql(
            "UPDATE deposit SET Period = %s WHERE DepositKey = %s",
            (period, deposit_key),
        )
        self.refresh_record()

    def _export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出欠還卡名單",
            "欠還卡名單.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_return_card,
            [0, 1],
            [3, 16],
            "欠還卡名單",
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )
