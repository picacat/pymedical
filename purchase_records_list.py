import datetime

from PyQt5 import QtWidgets
from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from libs import (
    charge_utils,
    date_utils,
    db_utils,
    dialog_utils,
    export_utils,
    medicine_utils,
    number_utils,
    personnel_utils,
    prescript_utils,
    printer_utils,
    purchase_utils,
    system_utils,
    ui_utils,
)

# 作用中表格的外框
# 直接設在表格自己的 stylesheet 上, 優先權最高, 不會被 .ui 或 set_css 的樣式蓋掉
ACTIVE_TABLE_CSS = """
    QTableWidget {
        border: 4px solid #FF8C00;
    }
"""


# 自費銷售記錄 2021.10.01
class PurchaseRecordList(QtWidgets.QMainWindow):
    """自費銷售記錄"""

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.dialog = args[2]
        self.no_zero_bonus = args[3]
        self.ui = None
        self.tables = ()
        self.active_table = None

        self.start_date = self.dialog.ui.dateEdit_start_date.date().toString(
            "yyyy-MM-dd 00:00:00"
        )
        self.end_date = self.dialog.ui.dateEdit_end_date.date().toString(
            "yyyy-MM-dd 23:59:59"
        )
        if self.dialog.ui.radioButton_period1.isChecked():
            self.period = "早班"
        elif self.dialog.ui.radioButton_period2.isChecked():
            self.period = "午班"
        elif self.dialog.ui.radioButton_period3.isChecked():
            self.period = "晚班"
        else:
            self.period = "全部"

        self.programe_name = "自費銷售記錄"
        self.user_name = system_utils.get_user_name(self.system_settings)

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PURCHASE_RECORDS_LIST, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        self.tables = (
            self.ui.tableWidget_self_prescript,
            self.ui.tableWidget_self_prescript_agent,
        )
        # 記住各表格原本的 stylesheet, 切換時在它後面加上/拿掉外框
        self._table_base_css = {table: table.styleSheet() for table in self.tables}
        for table in self.tables:
            purchase_utils.set_purchase_list_table(self.database, table)
            table.installEventFilter(self)  # 鍵盤 Tab 進入
            table.viewport().installEventFilter(self)  # 滑鼠點擊

        # 代收的設定欠款已併入「設定欠款」按鈕 (依作用中表格處理)
        self.ui.toolButton_set_agent_debt.hide()

        self._set_text_edit_remark()
        if (
            personnel_utils.get_permission(
                self.database, "系統作業", "關閉匯出功能", self.user_name
            )
            == "Y"
        ):
            self.ui.toolButton_export_agent.setEnabled(False)

        self._set_active_table(self.ui.tableWidget_self_prescript)

    def _set_text_edit_remark(self):
        html = """
            <html>
                <head>
                    <meta charset="UTF-8">
                </head>
                <body>
                    注意事項
                    <ol>
                        <li>
                            <font color="red">
                                若折扣金額低於售價8折，則沒有抽成； 8折以上，抽成減半。
                            </font>
                        </li>
                        <li>換貨時，須注意金額是否沖銷平衡</li>
                        <li>未付清品項不得換貨</li>
                        <li>產品名稱若包含「代收」關鍵字，該筆記錄不會列在銷售記錄內，而是列在代收費用。</li>
                        <li>上方按鈕作用於<font color="#FF8C00"><b>橘色外框</b></font>的表格，點選表格即可切換。</li>
                    </ol>
                </body>
            </html>
        """
        self.ui.textEdit_remark.setHtml(html)

    # 設定信號
    def _set_signal(self):
        for table in self.tables:
            table.doubleClicked.connect(self._open_medical_record)
            table.itemSelectionChanged.connect(self._prescript_item_changed)

        self.ui.toolButton_return.clicked.connect(self._return_button_pressed)
        self.ui.toolButton_return_course.clicked.connect(self._return_course)
        self.ui.toolButton_set_discount.clicked.connect(self._set_discount)
        self.ui.toolButton_exchange.clicked.connect(self._exchange_button_pressed)
        self.ui.toolButton_delete.clicked.connect(self._delete_prescript)
        self.ui.toolButton_set_person.clicked.connect(self._set_person)
        self.ui.toolButton_set_single_person.clicked.connect(self._set_single_person)
        self.ui.toolButton_set_debt.clicked.connect(self._set_debt)
        self.ui.toolButton_repayment.clicked.connect(self._set_repayment)

        self.ui.toolButton_export_agent.clicked.connect(self._export_agent)

    # ------------------------------------------------------------------
    # 作用中表格
    # ------------------------------------------------------------------
    def eventFilter(self, obj, event):
        if event.type() in (QEvent.FocusIn, QEvent.MouseButtonPress):
            for table in self.tables:
                if obj is table or obj is table.viewport():
                    if table is not self.active_table:
                        self._set_active_table(table)
                    break

        return super().eventFilter(obj, event)

    def _set_active_table(self, table):
        self.active_table = table
        for t in self.tables:
            is_active = t is table
            base_css = self._table_base_css.get(t, "")
            t.setStyleSheet(base_css + ACTIVE_TABLE_CSS if is_active else base_css)
            if not is_active:
                t.setCurrentCell(-1, -1)
                t.clearSelection()

        self._prescript_item_changed()

    def _cell(self, table, row_no, col_name):
        if row_no < 0:
            return ""

        item = table.item(row_no, purchase_utils.PURCHASE_COL_NO[col_name])
        if item is None:
            return ""

        return item.text()

    def _get_current_row(self, show_message=True):
        """回傳 (作用中表格, 列號)；沒選到資料列時列號為 None"""
        table = self.active_table
        row_no = table.currentRow()
        if row_no < 0 or self._cell(table, row_no, "prescript_key") == "":
            if show_message:
                system_utils.show_message_box(
                    QMessageBox.Information,
                    "注意",
                    '<font size="5" color="red"><b>請選擇銷售資料.</b></font>',
                    "未選擇任何資料.",
                )
            return table, None

        return table, row_no

    def _calculate_total(self, table):
        if table is self.ui.tableWidget_self_prescript:
            no_zero_bonus = self.no_zero_bonus
        else:
            no_zero_bonus = False

        purchase_utils.calculate_purchase_list_total(
            table,
            self.start_date[:10],
            self.end_date[:10],
            no_zero_bonus=no_zero_bonus,
        )

    # ------------------------------------------------------------------
    # 讀取資料
    # ------------------------------------------------------------------
    def _open_medical_record(self):
        table = self.active_table
        case_key = self._cell(table, table.currentRow(), "case_key")
        if case_key == "":
            return

        self.parent.parent.open_medical_record(case_key)

    def start_calculate(self):
        rows = self._read_prescript()
        self._set_prescript_table(rows)

        agent_rows = self._read_agent_prescript()
        self._set_agent_prescript_table(agent_rows)

    def _get_advance_sql(self):
        conditions = []
        patient_key = self.dialog.lineEdit_patient_key.text().strip()
        doctor = self.dialog.comboBox_doctor.currentText()
        massage_referrer = self.dialog.comboBox_massage_referrer.currentText()
        nursing_assistant = self.dialog.comboBox_nursing_assistant.currentText()
        medicine_name = self.dialog.lineEdit_medicine_name.text().strip()

        if patient_key != "":
            conditions.append(f"cases.PatientKey = {patient_key}")
        if doctor != "":
            conditions.append(f'cases.Doctor = "{doctor}"')
        if massage_referrer != "":
            conditions.append(f'cases.MassageReferrer = "{massage_referrer}"')
        if nursing_assistant != "":
            conditions.append(f'cases.NursingAssistant = "{nursing_assistant}"')
        if medicine_name != "":
            safe_name = medicine_name.replace('"', '""')
            conditions.append(f'MedicineName LIKE "%{safe_name}%"')

        if not conditions:
            return ""

        return " AND " + " AND ".join(conditions)

    def _get_sql_condition(self):
        sql_condition = """
            (prescript.MedicineSet >= 2 AND
             prescript.MedicineSet != 11 AND
             MedicineName != "民俗調理"
             AND MedicineName NOT LIKE "%代收%")
        """

        if self.dialog.ui.radioButton_date.isChecked():  # 日期查詢
            if self.period != "全部":
                sql_condition += f'''
                    AND (
                        (cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                            cases.Period = "{self.period}") OR
                        (prescript.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                            cases.Period = "{self.period}") OR
                        (debt.ReturnDate1 BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                            debt.Period1 = "{self.period}" AND debt.PrescriptKey > 0)
                    )
                '''
            else:
                sql_condition += f'''
                    AND (
                        (cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") OR
                        prescript.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" OR
                        (debt.ReturnDate1 BETWEEN "{self.start_date}" AND "{self.end_date}" AND debt.PrescriptKey > 0)
                    )
                '''

            if self.dialog.checkBox_debt.isChecked():
                sql_condition += " AND cases.TotalFee > ReceiptFee"

            if self.dialog.ui.groupBox_advance.isChecked():
                sql_condition += self._get_advance_sql()
        elif self.dialog.ui.radioButton_invoice_no.isChecked():  # 單據號碼
            invoice_no = self.dialog.ui.lineEdit_invoice_no.text().strip()
            invoice_no_2 = self.dialog.ui.lineEdit_invoice_no_2.text().strip()
            if invoice_no_2 != "":
                sql_condition += (
                    f' AND cases.InvoiceNo BETWEEN "{invoice_no}" AND "{invoice_no_2}"'
                )
            else:
                sql_condition += f' AND cases.InvoiceNo = "{invoice_no}"'

        return sql_condition

    def _read_prescript(self, prescript_key=None):
        """給 prescript_key 時讀單筆 (兩個表格共用)，否則依查詢條件讀銷售記錄"""
        if prescript_key is not None:
            sql_condition = f"prescript.PrescriptKey = {prescript_key}"
        else:
            sql_condition = self._get_sql_condition()

        sql = f"""
            SELECT
                prescript.*,
                cases.CaseKey, cases.CaseDate AS SaleDate, cases.Period, cases.PatientKey, cases.Name, cases.InsType,
                cases.Doctor, cases.MassageReferrer, cases.NursingAssistant,
                cases.InvoiceNo, cases.TreatType
            FROM prescript
                LEFT JOIN cases ON prescript.CaseKey = cases.CaseKey
                LEFT JOIN debt ON debt.CaseKey = prescript.CaseKey
            WHERE
                {sql_condition}
            GROUP BY prescript.PrescriptKey
            ORDER BY prescript.CaseKey, prescript.PrescriptNo, PrescriptKey
        """

        return self.database.select_record(sql)

    def _is_herb_or_powder(self, case_key):
        sql = f"""
            SELECT * FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineName IN ("自費水藥", "自費粉藥")
            LIMIT 1
        """
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return True

        return False

    def _check_single_compound(self, case_key, medicine_type):
        if medicine_type == "成方表頭":
            return False

        sql = f"""
            SELECT MedicineKey FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineType = "成方表頭"
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return False

        row = rows[0]
        medicine_key = row["MedicineKey"]
        single_compound = medicine_utils.get_medicine_extend(
            self.database, medicine_key, "成方單項"
        )
        title_compound = medicine_utils.get_medicine_extend(
            self.database, medicine_key, "成方抬頭"
        )
        if single_compound == "Y" and title_compound == "Y":
            return True

        return False

    def _set_prescript_table(self, rows):
        table = self.ui.tableWidget_self_prescript
        table.setRowCount(0)
        row_no = 0
        for row in rows:
            if not purchase_utils.set_purchase_list_data(
                self.database,
                table,
                row,
                row_no,
                query_start_date=self.start_date[:10],
                query_end_date=self.end_date[:10],
            ):
                continue

            row_no += 1

        if self.no_zero_bonus:
            self._filter_zero_bonus()

        self._calculate_total(table)

    def _filter_zero_bonus(self):
        table = self.ui.tableWidget_self_prescript
        for row_no in range(table.rowCount() - 1, -1, -1):
            bonus = table.item(
                row_no, purchase_utils.PURCHASE_COL_NO["doctor_commission"]
            )
            if bonus is None or number_utils.get_integer(bonus.text()) == 0:
                table.hideRow(row_no)

    # ------------------------------------------------------------------
    # 退貨
    # ------------------------------------------------------------------
    def _get_return_quantity(self, table, row_no):
        medicine_name = self._cell(table, row_no, "medicine_name")
        quantity = number_utils.get_integer(self._cell(table, row_no, "quantity"))

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")
        quantity, ok = input_dialog.getInt(
            self,
            "退貨",
            f'請輸入<font color="blue"><b>「{medicine_name}」</font>退貨數量',
            1,
            1,
            quantity,
            1,
        )
        if not ok:
            return None

        return quantity

    def _get_return_dealer(self):
        input_dialog = QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")

        items = personnel_utils.get_person(self.database, "全部")
        dealer, ok = input_dialog.getItem(
            self, "經手人", "請選擇經手人", items, 0, False
        )

        if not ok:
            return None

        return dealer

    def _return_button_pressed(self):
        table, row_no = self._get_current_row()
        if row_no is None:
            return

        case_key = self._cell(table, row_no, "case_key")
        medicine_key = self._cell(table, row_no, "medicine_key")
        medicine_name = self._cell(table, row_no, "medicine_name")
        invoice_no = self._cell(table, row_no, "invoice_no")

        dialog = dialog_utils.get_dialog_return_goods(
            self,
            self.database,
            self.system_settings,
            case_key,
            medicine_key,
            medicine_name,
            invoice_no,
        )
        if not dialog.exec_():
            dialog.deleteLater()
            return

        return_date = dialog.ui.dateEdit_return_date.date().toString("yyyy-MM-dd")
        quantity = dialog.ui.spinBox_quantity.value()
        dealer = dialog.ui.comboBox_dealer.currentText()

        self._return_goods(table, row_no, return_date, quantity, dealer)

        system_utils.show_message_box(
            QMessageBox.Information,
            "退貨完成",
            '<font size="5" color="blue"><b>已完成退貨作業.</b></font>',
            "退貨成功.",
        )
        dialog.deleteLater()

    def _get_start_row_no(self, table, row_no, invoice_no):
        for i in range(row_no, -1, -1):
            row_no = i

            item = table.item(i - 1, purchase_utils.PURCHASE_COL_NO["invoice_no"])
            if item is None:
                break

            if item.text() != invoice_no:
                break

        return row_no

    def _get_end_row_no(self, table, row_no, invoice_no):
        for i in range(row_no, table.rowCount()):
            row_no = i

            item = table.item(i + 1, purchase_utils.PURCHASE_COL_NO["invoice_no"])
            if item is None:
                break

            if item.text() != invoice_no:
                break

        return row_no

    def _return_course(self):
        table, row_no = self._get_current_row()
        if row_no is None:
            return

        invoice_no = self._cell(table, row_no, "invoice_no")
        if invoice_no == "":
            return

        start_row_no = self._get_start_row_no(table, row_no, invoice_no)
        end_row_no = self._get_end_row_no(table, row_no, invoice_no)

        dialog = dialog_utils.get_dialog_calendar(
            self, self.database, self.system_settings, "自費銷售記錄"
        )
        today = datetime.datetime.today()

        dialog.ui.calendarWidget.setSelectedDate(today)
        dialog.ui.groupBox_calendar.setTitle("請選擇退貨日期")

        if not dialog.exec_():
            dialog.deleteLater()
            return

        return_date = dialog.ui.calendarWidget.selectedDate().toString("yyyy-MM-dd")
        dealer = self.system_settings.field("使用者")
        current_row_no = start_row_no
        for _ in range(start_row_no, end_row_no + 1):
            quantity = number_utils.get_integer(
                self._cell(table, current_row_no, "quantity")
            )
            self._return_goods(table, current_row_no, return_date, quantity, dealer)
            current_row_no += 2  # 每退一筆會在下方插入一列退貨記錄

        dialog.deleteLater()

    def _return_goods(self, table, row_no, return_date, quantity, dealer):
        prescript_key = self._cell(table, row_no, "prescript_key")
        db_utils.update_timestamp(
            self.database, "prescript", "PrescriptKey", prescript_key
        )

        case_key = self._cell(table, row_no, "case_key")
        medicine_set = self._cell(table, row_no, "medicine_set")
        medicine_type = self._cell(table, row_no, "medicine_type")
        medicine_key = self._cell(table, row_no, "medicine_key")
        medicine_name = self._cell(table, row_no, "medicine_name")
        unit = self._cell(table, row_no, "unit")
        price = self._cell(table, row_no, "price")
        discount = self._cell(table, row_no, "discount")
        promotion = self._cell(table, row_no, "promotion")
        remark = self._cell(table, row_no, "remark")
        debt = self._cell(table, row_no, "debt")

        price = number_utils.get_integer(price)
        discount = -number_utils.get_integer(discount)
        quantity = -number_utils.get_integer(quantity)
        amount = price * quantity

        medicine_name += " (退貨)"

        fields = [
            "CaseKey",
            "CaseDate",
            "MedicineSet",
            "MedicineType",
            "MedicineKey",
            "MedicineName",
            "Dosage",
            "Unit",
            "Price",
            "DiscountFee",
            "Amount",
            "Promotion",
            "Dealer",
            "Remark",
            "debt",
        ]
        data = [
            case_key,
            return_date,
            medicine_set,
            medicine_type,
            medicine_key,
            medicine_name,
            quantity,
            unit,
            price,
            discount,
            amount,
            promotion,
            dealer,
            remark,
            debt,
        ]
        new_prescript_key = self.database.insert_record("prescript", fields, data)
        self._insert_row(table, new_prescript_key, row_no + 1)
        self._update_self_fees(case_key, medicine_type, amount)
        self._calculate_total(table)

    def _update_self_fees(self, case_key, medicine_type, amount):
        field = charge_utils.get_medicine_type_charge_field(
            self.database, medicine_type
        )
        charge_field = charge_utils.get_charge_field(field, medicine_type)
        charge_field = {
            "diag_fee": "SDiagFee",
            "drug_fee": "SDrugFee",
            "herb_fee": "SHerbFee",
            "expensive_fee": "SExpensiveFee",
            "acupuncture_fee": "SAcupunctureFee",
            "massage_fee": "SMassageFee",
            "material_fee": "SMaterialFee",
            "exam_fee": "SExamFee",
        }.get(charge_field, "SDrugFee")

        sql = f"""
            UPDATE cases SET
                {charge_field} = {charge_field} + {amount},
                SelfTotalFee = SelfTotalFee + {amount},
                TotalFee = TotalFee + {amount},
                ReceiptFee = TotalFee
            WHERE
                CaseKey = {case_key}
        """
        self.database.exec_sql(sql)

    def _insert_row(self, table, prescript_key, row_no):
        rows = self._read_prescript(prescript_key=prescript_key)
        if len(rows) <= 0:
            return

        table.insertRow(row_no)
        # insertRow 已經加了一列, 所以用 refresh_record=True 避免再多加一列空白列
        if not purchase_utils.set_purchase_list_data(
            self.database, table, rows[0], row_no, refresh_record=True
        ):
            table.removeRow(row_no)

    def _delete_prescript(self):
        table, row_no = self._get_current_row()
        if row_no is None:
            return

        msg_box = dialog_utils.get_message_box(
            "退貨刪除",
            QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除退貨的資料嗎?</b></font>',
            "注意！資料刪除後, 將無法回復!",
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        prescript_key = self._cell(table, row_no, "prescript_key")
        case_key = self._cell(table, row_no, "case_key")
        medicine_type = self._cell(table, row_no, "medicine_type")
        amount = abs(number_utils.get_integer(self._cell(table, row_no, "total_fee")))

        self.database.exec_sql(
            f"DELETE FROM prescript WHERE PrescriptKey = {prescript_key}"
        )
        table.removeRow(row_no)
        self._update_self_fees(case_key, medicine_type, amount)
        self._calculate_total(table)

    # ------------------------------------------------------------------
    # 按鈕狀態
    # ------------------------------------------------------------------
    def _set_all_buttons_enabled(self, enabled):
        for button in (
            self.ui.toolButton_return,
            self.ui.toolButton_return_course,
            self.ui.toolButton_set_discount,
            self.ui.toolButton_exchange,
            self.ui.toolButton_set_person,
            self.ui.toolButton_set_single_person,
            self.ui.toolButton_delete,
            self.ui.toolButton_set_debt,
            self.ui.toolButton_repayment,
        ):
            button.setEnabled(enabled)

    def _prescript_item_changed(self):
        table = self.active_table
        if table is None:
            return

        row_no = table.currentRow()
        medicine_name = self._cell(table, row_no, "medicine_name")
        if row_no < 0 or medicine_name == "":  # 沒選到任何資料列
            self._set_all_buttons_enabled(False)
            return

        is_total_row = "合計" in medicine_name
        enabled = True
        course_enabled = self._cell(table, row_no, "invoice_no") != ""

        if (
            is_total_row
            or "(退貨)" in medicine_name
            or "(換貨)" in medicine_name
            or purchase_utils.is_returned_goods(self.database, table, row_no)
        ):
            enabled = False

        self.ui.toolButton_return.setEnabled(enabled)
        self.ui.toolButton_return_course.setEnabled(course_enabled and not is_total_row)
        self.ui.toolButton_set_discount.setEnabled(enabled)
        self.ui.toolButton_exchange.setEnabled(enabled)
        self.ui.toolButton_set_person.setEnabled(enabled)
        self.ui.toolButton_set_single_person.setEnabled(enabled)
        self.ui.toolButton_set_debt.setEnabled(not is_total_row)
        self.ui.toolButton_delete.setEnabled(not enabled and not is_total_row)

        debt = number_utils.get_integer(self._cell(table, row_no, "debt"))
        if debt > 0:
            self.ui.toolButton_exchange.setEnabled(False)

        self.ui.toolButton_repayment.setEnabled(debt > 0 and not is_total_row)

    # ------------------------------------------------------------------
    # 換貨
    # ------------------------------------------------------------------
    def _exchange_button_pressed(self):
        table, row_no = self._get_current_row()
        if row_no is None:
            return

        case_key = self._cell(table, row_no, "case_key")
        medicine_key = self._cell(table, row_no, "medicine_key")
        medicine_set = self._cell(table, row_no, "medicine_set")
        medicine_name = self._cell(table, row_no, "medicine_name")
        quantity = number_utils.get_integer(self._cell(table, row_no, "quantity"))
        invoice_no = self._cell(table, row_no, "invoice_no")
        receipt_fee = self._cell(table, row_no, "receipt_fee")

        dialog = dialog_utils.get_dialog_exchange_goods(
            self,
            self.database,
            self.system_settings,
            case_key,
            medicine_key,
            medicine_set,
            medicine_name,
            quantity,
            invoice_no,
            receipt_fee,
        )

        if not dialog.exec_():
            dialog.deleteLater()
            return

        exchange_date = dialog.ui.dateEdit_exchange_date.date().toString("yyyy-MM-dd")
        quantity = dialog.ui.spinBox_quantity.value()
        dealer = dialog.ui.comboBox_dealer.currentText()
        self._return_goods(table, row_no, exchange_date, quantity, dealer)

        col = purchase_utils.PRESCRIPT_COL_NO
        exchange_table = dialog.ui.tableWidget_prescript
        for i in range(exchange_table.rowCount()):
            check_box = exchange_table.cellWidget(i, col["Promotion"])
            promotion = (
                "是" if check_box is not None and check_box.isChecked() else None
            )

            medicine_row = {
                "medicine_key": exchange_table.item(i, col["MedicineKey"]).text(),
                "medicine_type": exchange_table.item(i, col["MedicineType"]).text(),
                "medicine_name": exchange_table.item(i, col["MedicineName"]).text(),
                "unit": exchange_table.item(i, col["Unit"]).text(),
                "quantity": exchange_table.item(i, col["Quantity"]).text(),
                "price": exchange_table.item(i, col["Price"]).text(),
                "amount": exchange_table.item(i, col["Amount"]).text(),
                "discount_fee": exchange_table.item(i, col["DiscountFee"]).text(),
                "promotion": promotion,
            }
            self._exchange_goods(table, row_no, exchange_date, medicine_row, dealer)

        dialog.deleteLater()

    def _exchange_goods(self, table, row_no, exchange_date, medicine_row, dealer):
        prescript_key = self._cell(table, row_no, "prescript_key")
        db_utils.update_timestamp(
            self.database, "prescript", "PrescriptKey", prescript_key
        )

        case_key = self._cell(table, row_no, "case_key")
        medicine_set = self._cell(table, row_no, "medicine_set")

        medicine_key = medicine_row["medicine_key"]
        medicine_type = medicine_row["medicine_type"]
        medicine_name = medicine_row["medicine_name"]
        unit = medicine_row["unit"]
        try:
            quantity = number_utils.get_float(medicine_row["quantity"])
        except Exception:
            quantity = None

        price = medicine_row["price"]
        amount = medicine_row["amount"]
        discount_fee = medicine_row["discount_fee"]
        promotion = "是" if medicine_row["promotion"] else None

        medicine_name += " (換貨)"

        fields = [
            "CaseKey",
            "CaseDate",
            "MedicineSet",
            "MedicineType",
            "MedicineKey",
            "MedicineName",
            "Dosage",
            "Unit",
            "Price",
            "Amount",
            "Promotion",
            "DiscountFee",
            "Dealer",
        ]
        data = [
            case_key,
            exchange_date,
            medicine_set,
            medicine_type,
            medicine_key,
            medicine_name,
            quantity,
            unit,
            price,
            amount,
            promotion,
            discount_fee,
            dealer,
        ]
        new_prescript_key = self.database.insert_record("prescript", fields, data)
        self._insert_row(table, new_prescript_key, row_no + 2)
        self._update_self_fees(case_key, medicine_type, amount)
        self._calculate_total(table)

    # ------------------------------------------------------------------
    # 匯出 / 列印
    # ------------------------------------------------------------------
    def _get_export_columns(self):
        col = purchase_utils.PURCHASE_COL_NO
        hidden_columns = [
            col["prescript_key"],
            col["case_key"],
            col["medicine_set"],
            col["medicine_type"],
            col["medicine_key"],
        ]
        number_columns = [
            col["patient_key"],
            col["quantity"],
            col["price"],
            col["pres_days"],
            col["discount"],
            col["total_fee"],
            col["receipt_fee"],
            col["debt"],
            col["repayment"],
            col["return_fee"],
            col["doctor_commission"],
            col["massager_commission"],
            col["cashier_commission"],
        ]
        return hidden_columns, number_columns

    def export_prescript(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f"{self.start_date[:10]}至{self.end_date[:10]}自費銷售抽成明細.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        hidden_columns, number_columns = self._get_export_columns()
        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_self_prescript,
            hidden_columns,
            number_columns,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>自費銷售業績明細檔{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def print_purchase_list(self):
        printer_utils.print_purchase_list(
            self,
            self.database,
            self.system_settings,
            self.start_date[:10],
            self.end_date[:10],
            self.ui.tableWidget_self_prescript,
            self.ui.tableWidget_self_prescript_agent,
            no_zero_bonus=self.no_zero_bonus,
        )

    # ------------------------------------------------------------------
    # 銷售設定
    # ------------------------------------------------------------------
    def _set_person(self):
        table, row_no = self._get_current_row()
        if row_no is None:
            return

        case_key = self._cell(table, row_no, "case_key")
        prescript_key = self._cell(table, row_no, "prescript_key")

        dialog = dialog_utils.get_dialog_set_person(
            self,
            self.database,
            self.system_settings,
            case_key,
            prescript_key,
            "銷售設定",
        )

        if not dialog.exec_():
            dialog.deleteLater()
            return

        fields = ["InvoiceNo", "MassageReferrer", "NursingAssistant"]
        data = [
            dialog.ui.lineEdit_invoice_no.text(),
            dialog.ui.comboBox_massage_referrer.currentText(),
            dialog.ui.comboBox_nursing_assistant.currentText(),
        ]
        self.database.update_record("cases", fields, "CaseKey", case_key, data)

        if dialog.ui.checkBox_promotion.isChecked():
            promotion_script = ',Promotion = "Y"'
        else:
            promotion_script = ",Promotion = NULL"

        sql = f'''
            UPDATE prescript
            SET
                Dealer = "{dialog.ui.comboBox_dealer.currentText()}",
                Remark = "{dialog.ui.textEdit_remark.toPlainText()}"
                {promotion_script}
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2
        '''
        self.database.exec_sql(sql)

        dialog.deleteLater()

        # 同一張單可能同時出現在兩個表格, 兩邊都刷新
        for t in self.tables:
            self._refresh_by_cases(t, case_key)

    def _set_single_person(self):
        table, row_no = self._get_current_row()
        if row_no is None:
            return

        case_key = self._cell(table, row_no, "case_key")
        prescript_key = self._cell(table, row_no, "prescript_key")

        dialog = dialog_utils.get_dialog_set_person(
            self,
            self.database,
            self.system_settings,
            case_key,
            prescript_key,
            "單一品項銷售設定",
        )

        if not dialog.exec_():
            dialog.deleteLater()
            return

        fields = ["InvoiceNo"]
        data = [
            dialog.ui.lineEdit_invoice_no.text(),
        ]
        self.database.update_record("cases", fields, "CaseKey", case_key, data)

        massage_referrer = dialog.ui.comboBox_massage_referrer.currentText()
        nursing_assistant = dialog.ui.comboBox_nursing_assistant.currentText()

        prescript_utils.remove_pres_extend_row(self.database, prescript_key, "傷助推薦")
        prescript_utils.remove_pres_extend_row(self.database, prescript_key, "護佐")

        if massage_referrer != "":
            prescript_utils.insert_pres_extend_row(
                self.database, prescript_key, "傷助推薦", massage_referrer
            )

        if nursing_assistant != "":
            prescript_utils.insert_pres_extend_row(
                self.database, prescript_key, "護佐", nursing_assistant
            )

        if dialog.ui.checkBox_promotion.isChecked():
            promotion_script = ',Promotion = "Y"'
        else:
            promotion_script = ",Promotion = NULL"

        sql = f'''
            UPDATE prescript
            SET
                Dealer = "{dialog.ui.comboBox_dealer.currentText()}",
                Remark = "{dialog.ui.textEdit_remark.toPlainText()}"
                {promotion_script}
            WHERE
                PrescriptKey = {prescript_key}
        '''
        self.database.exec_sql(sql)

        dialog.deleteLater()

        self._refresh_by_prescript(table, row_no, prescript_key)

    def _refresh_by_cases(self, table, in_case_key):
        for row_no in range(table.rowCount()):
            if self._cell(table, row_no, "case_key") != in_case_key:
                continue

            prescript_key = self._cell(table, row_no, "prescript_key")
            rows = self._read_prescript(prescript_key=prescript_key)
            if len(rows) <= 0:
                continue

            purchase_utils.set_purchase_list_data(
                self.database,
                table,
                rows[0],
                row_no,
                refresh_record=True,
            )

        self._calculate_total(table)

    def _refresh_by_prescript(self, table, row_no, in_prescript_key):
        rows = self._read_prescript(prescript_key=in_prescript_key)
        if len(rows) <= 0:
            return

        purchase_utils.set_purchase_list_data(
            self.database,
            table,
            rows[0],
            row_no,
            refresh_record=True,
        )
        self._calculate_total(table)

    # ------------------------------------------------------------------
    # 欠款 / 還款 (兩個表格共用)
    # ------------------------------------------------------------------
    def _set_debt(self):
        table, row_no = self._get_current_row()
        if row_no is None:
            return

        prescript_key = self._cell(table, row_no, "prescript_key")
        rows = self.database.select_record(
            f"SELECT Amount, Debt FROM prescript WHERE PrescriptKey = {prescript_key}"
        )
        if len(rows) <= 0:
            return

        debt = number_utils.get_integer(rows[0]["Debt"])

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")
        debt, ok = input_dialog.getInt(
            self, "設定欠款", "請輸入欠款", debt, 0, 99999999, 1
        )
        if not ok:
            return

        self.database.exec_sql(
            f"UPDATE prescript SET Debt = {debt} WHERE PrescriptKey = {prescript_key}"
        )

        self._insert_debt(table, row_no, prescript_key, debt)
        self._refresh_by_prescript(table, row_no, prescript_key)
        self._prescript_item_changed()

    def _insert_debt(self, table, row_no, prescript_key, debt_fee):
        case_key = self._cell(table, row_no, "case_key")
        case_date = self._cell(table, row_no, "case_date")
        period = self._cell(table, row_no, "period")
        patient_key = self._cell(table, row_no, "patient_key")
        name = self._cell(table, row_no, "name")
        doctor = self._cell(table, row_no, "doctor")

        self.database.exec_sql(
            f"DELETE FROM debt WHERE PrescriptKey = {prescript_key}"
        )  # 清除原有的欠款
        self.database.exec_sql(
            f"UPDATE cases SET DebtFee = {debt_fee} WHERE CaseKey = {case_key}"
        )

        if debt_fee <= 0:
            return

        fields = [
            "CaseKey",
            "PrescriptKey",
            "PatientKey",
            "DebtType",
            "Name",
            "CaseDate",
            "Period",
            "Doctor",
            "Fee",
        ]
        data = [
            case_key,
            prescript_key,
            patient_key,
            "批價欠款",
            name,
            case_date,
            period,
            doctor,
            debt_fee,
        ]
        self.database.insert_record("debt", fields, data)

    def _set_repayment(self):
        table, row_no = self._get_current_row()
        if row_no is None:
            return

        repayment_date = date_utils.get_dialog_date(
            self, self.database, self.system_settings, call_from=self.programe_name
        )
        if repayment_date is None:
            return

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")
        items = ("早班", "午班", "晚班")
        period, ok = input_dialog.getItem(
            self, "選擇班別", "請選擇還款班別", items, 0, False
        )
        if not ok or not period:
            return

        prescript_key = self._cell(table, row_no, "prescript_key")
        rows = self.database.select_record(
            f"SELECT Debt FROM prescript WHERE PrescriptKey = {prescript_key}"
        )
        if len(rows) <= 0:
            return

        debt = number_utils.get_integer(rows[0]["Debt"])

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")
        repayment, ok = input_dialog.getInt(
            self, "輸入還款金額", "請輸入還款金額", debt, 0, 10000000, 100
        )
        if not ok:
            return

        rows = self.database.select_record(
            f"SELECT * FROM debt WHERE PrescriptKey = {prescript_key}"
        )
        if len(rows) <= 0:
            self._insert_debt(table, row_no, prescript_key, debt)

        sql = f'''
            UPDATE debt
            SET
                ReturnDate1 = "{repayment_date}",
                Period1 = "{period}",
                Fee1 = {repayment},
                TotalReturn = {repayment}
            WHERE
                PrescriptKey = {prescript_key}
        '''
        self.database.exec_sql(sql)
        self._refresh_by_prescript(table, row_no, prescript_key)
        self._prescript_item_changed()

    # ------------------------------------------------------------------
    # 代收費用
    # ------------------------------------------------------------------
    def _get_agent_sql_condition(self):
        sql_condition = """
            (prescript.MedicineSet >= 2 AND
             prescript.MedicineSet != 11 AND
             MedicineName != "民俗調理"
             AND MedicineName LIKE "%代收%")
        """

        if self.dialog.ui.radioButton_date.isChecked():  # 日期查詢
            sql_condition += f'''
                AND (
                    cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" OR
                    prescript.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" OR
                    (debt.ReturnDate1 BETWEEN "{self.start_date}" AND "{self.end_date}" AND debt.PrescriptKey > 0)
                )
            '''
            if self.period != "全部":
                sql_condition += f' AND cases.Period = "{self.period}"'

            if self.dialog.checkBox_debt.isChecked():
                sql_condition += " AND cases.TotalFee > ReceiptFee"

            if self.dialog.ui.groupBox_advance.isChecked():
                sql_condition += self._get_advance_sql()
        elif self.dialog.ui.radioButton_invoice_no.isChecked():  # 單據號碼
            invoice_no = self.dialog.ui.lineEdit_invoice_no.text().strip()
            invoice_no_2 = self.dialog.ui.lineEdit_invoice_no_2.text().strip()
            if invoice_no_2 != "":
                sql_condition += (
                    f' AND cases.InvoiceNo BETWEEN "{invoice_no}" AND "{invoice_no_2}"'
                )
            else:
                sql_condition += f' AND cases.InvoiceNo = "{invoice_no}"'

        return sql_condition

    def _read_agent_prescript(self):
        sql = f"""
            SELECT
                prescript.*,
                cases.CaseKey, cases.CaseDate AS SaleDate, cases.Period, cases.PatientKey, cases.Name, cases.InsType,
                cases.Doctor, cases.MassageReferrer, cases.NursingAssistant,
                cases.InvoiceNo, cases.TreatType
            FROM prescript
                LEFT JOIN cases ON prescript.CaseKey = cases.CaseKey
                LEFT JOIN debt ON debt.CaseKey = prescript.CaseKey
            WHERE
                {self._get_agent_sql_condition()}
            ORDER BY prescript.CaseKey, prescript.PrescriptNo, PrescriptKey
        """

        return self.database.select_record(sql)

    def _set_agent_prescript_table(self, rows):
        table = self.ui.tableWidget_self_prescript_agent
        table.setRowCount(0)
        row_no = 0
        for row in rows:
            if not purchase_utils.set_purchase_list_data(
                self.database, table, row, row_no
            ):
                continue

            row_no += 1

        self._calculate_total(table)

    def _export_agent(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f"{self.start_date[:10]}至{self.end_date[:10]}代收自費銷售明細.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        hidden_columns, number_columns = self._get_export_columns()
        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_self_prescript_agent,
            hidden_columns,
            number_columns,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>代收自費銷售明細檔{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    # ------------------------------------------------------------------
    # 折扣
    # ------------------------------------------------------------------
    def _set_discount(self):
        table, row_no = self._get_current_row()
        if row_no is None:
            return

        max_discount_fee = number_utils.get_integer(
            self._cell(table, row_no, "total_fee")
        )
        if max_discount_fee <= 0:
            max_discount_fee = 100000

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")
        discount_fee, ok = input_dialog.getInt(
            self, "折扣", "請輸入折扣金額", 0, 0, max_discount_fee, 1
        )
        if not ok:
            return

        prescript_key = self._cell(table, row_no, "prescript_key")
        self.database.update_record(
            "prescript", ["DiscountFee"], "PrescriptKey", prescript_key, [discount_fee]
        )
        self._refresh_by_prescript(table, row_no, prescript_key)
