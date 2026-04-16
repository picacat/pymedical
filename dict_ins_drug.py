# -*- coding: utf-8 -*-

import datetime
import re

from pyexcel_ods3 import get_data
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QInputDialog, QMessageBox, QProgressBar, QPushButton

from libs import (
    class_utils,
    dropbox_utils,
    nhi_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 健保藥品 2019.03.13
class DictInsDrug(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DictInsDrug, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_medicine()

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DICT_INS_DRUG, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_medicine = class_utils.get_table_widget(
            self.ui.tableWidget_medicine, self.database
        )
        self.table_widget_drug = class_utils.get_table_widget(
            self.ui.tableWidget_drug, self.database
        )
        self.table_widget_drug.set_column_hidden([0])
        self.table_widget_medicine.set_column_hidden([0])
        self._set_table_width()
        self._set_combo_box_supplier()
        self._set_spin_box_valid_date()

        self.ui.action_update_valid_date.setEnabled(False)

    def _set_combo_box_supplier(self):
        sql = """
            SELECT Supplier FROM drug
            WHERE
                Supplier IS NOT NULL AND
                LENGTH(Supplier) > 0
            GROUP BY Supplier
            ORDER BY LENGTH(Supplier), CAST(CONVERT(`Supplier` using big5) AS BINARY)
        """
        rows = self.database.select_record(sql)
        supplier_list = []
        for row in rows:
            supplier_list.append(string_utils.xstr(row["Supplier"]))

        ui_utils.set_combo_box(self.ui.comboBox_supplier, supplier_list, "全部")

    def _set_spin_box_valid_date(self):
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month

        self.ui.spinBox_valid_year.setValue(current_year)
        self.ui.spinBox_valid_month.setValue(current_month)

        self.ui.spinBox_valid_year.setMinimum(current_year - 1)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 50, 180, 100, 130, 50, 180]
        self.table_widget_medicine.set_table_heading_width(width)

        width = [100, 100, 250, 100, 280, 130, 50]
        self.table_widget_drug.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.action_sync_drug.triggered.connect(self._sync_drug)
        self.ui.action_update_drug.triggered.connect(self._update_ins_drug)
        self.ui.action_close.triggered.connect(self._close_ins_drug)
        self.ui.action_check_medicine_name.triggered.connect(self._check_medicine_name)
        self.ui.action_update_valid_date.triggered.connect(self._update_valid_date)
        self.ui.action_update_prescript.triggered.connect(self._update_prescript)
        self.ui.action_assign_ins_code.triggered.connect(self._assign_ins_code)
        self.ui.tableWidget_medicine.itemSelectionChanged.connect(
            self._medicine_item_selection_changed
        )
        self.ui.pushButton_medicine_query.clicked.connect(self._medicine_name_query)
        self.ui.pushButton_drug_query.clicked.connect(self._drug_name_query)
        self.ui.radioButton_all.clicked.connect(self._filter_medicine)
        self.ui.radioButton_errors.clicked.connect(self._filter_medicine)
        self.ui.spinBox_valid_year.valueChanged.connect(self._valid_date_changed)
        self.ui.spinBox_valid_month.valueChanged.connect(self._valid_date_changed)

    def _read_medicine(self, medicine_name=None):
        medicine_name_script = ""
        if medicine_name is not None and medicine_name != "":
            medicine_name_script = (
                f' AND medicine.MedicineName LIKE "%{medicine_name}%"'
            )

        medicine_type = str(nhi_utils.INS_MEDICINE_TYPE)[1:-1]
        sql = f"""
            SELECT medicine.*, drug.ValidDate FROM medicine
                LEFT JOIN drug ON medicine.InsCode = drug.InsCode
            WHERE
                medicine.MedicineType IN ({medicine_type})
                {medicine_name_script}
            ORDER BY FIELD(medicine.MedicineType, {medicine_type}),
                     LENGTH(MedicineName), CAST(CONVERT(`MedicineName` using big5) AS BINARY)
        """
        self.table_widget_medicine.set_db_data(sql, self._set_medicine_data)

    def _set_medicine_data(self, row_no, row):
        error_message = []

        medicine_key = string_utils.xstr(row["MedicineKey"])
        medicine_name = string_utils.xstr(row["MedicineName"])
        ins_code = string_utils.xstr(row["InsCode"]).strip()
        valid_date = string_utils.xstr(row["ValidDate"])
        year = valid_date[:4]
        month = valid_date[4:6]
        day = valid_date[6:8]
        if valid_date != "" and "-" not in valid_date:
            valid_date = f"{year}-{month:0>2}-{day:0>2}"

        valid_year = self.ui.spinBox_valid_year.value()
        valid_month = self.ui.spinBox_valid_month.value()
        expire_date = f"{valid_year}-{valid_month:0>2}-01"

        if ins_code != "" and "清冠一號" not in medicine_name:
            if valid_date == "":
                error_message.append("健保碼無效")
            elif valid_date < expire_date:
                error_message.append("健保碼過期")

            if ins_code in nhi_utils.INVALID_INS_CODE_LIST:
                error_message.append("港香蘭無效健保碼")
            elif ins_code in nhi_utils.INVALID_WKP_INS_CODE_LIST:
                error_message.append("萬國信宏無效健保碼")

        medicine_row = [
            medicine_key,
            string_utils.xstr(row["MedicineType"]),
            string_utils.xstr(row["MedicineName"]),
            ins_code,
            valid_date,
            None,
            ", ".join(error_message),
        ]

        for column in range(len(medicine_row)):
            self.ui.tableWidget_medicine.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(medicine_row[column])
            )
            if len(error_message) > 0:
                self.ui.tableWidget_medicine.item(row_no, column).setForeground(
                    QtGui.QColor("red")
                )

        gtk_apply = "./icons/gtk-clear.svg"
        if ins_code != "":
            ui_utils.set_table_widget_field_icon(
                self.ui.tableWidget_medicine,
                row_no,
                5,
                gtk_apply,
                "medicine_key",
                medicine_key,
                self._clear_ins_code,
            )

    def _clear_ins_code(self, show_warning=True):
        medicine_name = self.table_widget_medicine.field_value(2)
        if show_warning:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("清除健保碼")
            msg_box.setText(f"""
                <font size="5" color="red">
                <b>確定清除{medicine_name}的健保藥碼?<br>
                </font>
            """)
            msg_box.setInformativeText(
                "健保碼清除後, 若想反悔, 可以至右邊的健保藥品詞庫點選新的健保藥品資料."
            )
            msg_box.addButton(QPushButton("確定清除"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            cancel = msg_box.exec_()
            if cancel:
                return

        medicine_key = self.table_widget_medicine.field_value(0)
        sql = f"""
            UPDATE medicine
            SET
                InsCode = NULL
            WHERE
                MedicineKey = {medicine_key}
        """
        self.database.exec_sql(sql)

        row_no = self.ui.tableWidget_medicine.currentRow()

        for column in range(3, 5):
            self.ui.tableWidget_medicine.setItem(
                row_no, column, QtWidgets.QTableWidgetItem("")
            )
        self.ui.tableWidget_medicine.setCellWidget(row_no, 5, None)

    def _sync_drug(self):
        self._update_drug(
            "單方",
            "./drug1.ods",
        )
        self._update_drug(
            "複方",
            "./drug2.ods",
        )

        self._read_medicine()

        system_utils.show_message_box(
            QMessageBox.Information,
            "本機更新健保碼",
            '<font size="5" color="blue"><b>最新版本的健保碼更新已完成.</b></font>',
            "恭喜您! 現在已經是最新的健保藥品",
        )

    def _write_ins_drug(self, medicine_type, rows, progress_bar):
        ins_code_no = self._get_field_number(rows[0], "藥品代碼")
        drug_name_no = self._get_field_number(rows[0], "基準方名")
        if drug_name_no is None:
            drug_name_no = self._get_field_number(rows[0], "藥品名稱")

        drug_type_no = self._get_field_number(rows[0], "劑型")
        supplier_no = self._get_field_number(rows[0], "製造廠名稱")
        valid_date_no = self._get_field_number(rows[0], "有效期間")

        for row_no, row in enumerate(rows):
            progress_bar.setValue(row_no + 1)
            if row_no == 0:  # data heading 不轉檔
                continue

            try:
                ins_code = row[ins_code_no]
                drug_name = row[drug_name_no]
                drug_type = row[drug_type_no]
                supplier = row[supplier_no]
                valid_date = string_utils.xstr(row[valid_date_no])
                if len(valid_date) == 7:
                    year = valid_date[:3]
                    year = int(year) + 1911
                    month = valid_date[3:5]
                    day = valid_date[5:7]
                else:
                    year = valid_date[:4]
                    month = valid_date[4:6]
                    day = valid_date[6:8]

                valid_date = f"{year}-{month}-{day}"
            except IndexError:
                continue

            field = [
                "InsCode",
                "DrugName",
                "MedicineType",
                "Unit",
                "Supplier",
                "ValidDate",
            ]

            data = [
                ins_code,
                drug_name,
                medicine_type,
                drug_type,
                supplier,
                valid_date,
            ]

            self.database.insert_record("drug", field, data)

    def _get_field_number(self, row, field_name):
        for col_no, col_name in enumerate(row):
            if col_name == field_name:
                return col_no

        return None

    def _close_ins_drug(self):
        self.close_all()
        self.close_tab()

    def _medicine_item_selection_changed(self):
        medicine_type = self.table_widget_medicine.field_value(1)
        medicine_name = string_utils.strip_string(
            self.table_widget_medicine.field_value(2)
        )
        ins_code = self.table_widget_medicine.field_value(3)
        self._read_drug(medicine_name, medicine_type)

        for row_no in range(self.ui.tableWidget_drug.rowCount()):
            current_ins_code = self.ui.tableWidget_drug.item(row_no, 1).text()
            if ins_code == current_ins_code:
                for col_no in range(self.ui.tableWidget_drug.columnCount()):
                    item = self.ui.tableWidget_drug.item(row_no, col_no)
                    if item is not None:
                        item.setForeground(QtGui.QColor("blue"))

    def _read_drug(self, drug_name, medicine_type=None):
        if drug_name == "":
            self.ui.tableWidget_drug.setRowCount(0)
            return

        supplier = self.ui.comboBox_supplier.currentText()
        if supplier == "全部":
            supplier_script = ""
        else:
            supplier_script = f' AND Supplier LIKE "%{supplier}%"'

        if medicine_type is None:
            medicine_type_condition = ""
        else:
            medicine_type_condition = f' (MedicineType = "{medicine_type}") AND'

        sql = f'''
            SELECT * FROM drug
            WHERE
                {medicine_type_condition}
                (DrugName LIKE "%{drug_name}%" OR InsCode = "{drug_name}")
                {supplier_script}
            ORDER BY ValidDate DESC, LENGTH(DrugName), CAST(CONVERT(`DrugName` using big5) AS BINARY)
        '''
        self.table_widget_drug.set_db_data(sql, self._set_drug_data)
        self.ui.tableWidget_medicine.setFocus(True)

    def _set_drug_data(self, row_no, row):
        drug_row = [
            string_utils.xstr(row["DrugKey"]),
            string_utils.xstr(row["InsCode"]),
            string_utils.xstr(row["DrugName"]),
            string_utils.xstr(row["Unit"]),
            string_utils.xstr(row["Supplier"]),
            string_utils.xstr(row["ValidDate"]),
        ]

        for column in range(len(drug_row)):
            self.ui.tableWidget_drug.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(drug_row[column])
            )
            if string_utils.xstr(
                row["InsCode"]
            ) == self.table_widget_medicine.field_value(3):
                self.ui.tableWidget_drug.item(row_no, column).setForeground(
                    QtGui.QColor("blue")
                )

        gtk_apply = "./icons/gtk-edit.svg"
        drug_key = self.table_widget_drug.field_value(0)
        ui_utils.set_table_widget_field_icon(
            self.ui.tableWidget_drug,
            row_no,
            6,
            gtk_apply,
            "drug_key",
            drug_key,
            self._set_ins_drug,
        )

    def _set_ins_drug(self):
        drug_code = self.table_widget_drug.field_value(1)
        valid_date = self.table_widget_drug.field_value(5)
        medicine_key = self.table_widget_medicine.field_value(0)
        sql = f'''
            UPDATE medicine
            SET
                InsCode = "{drug_code}"
            WHERE
                MedicineKey = {medicine_key}
        '''
        self.database.exec_sql(sql)

        self.ui.tableWidget_medicine.setItem(
            self.ui.tableWidget_medicine.currentRow(),
            3,
            QtWidgets.QTableWidgetItem(string_utils.xstr(drug_code)),
        )
        self.ui.tableWidget_medicine.setItem(
            self.ui.tableWidget_medicine.currentRow(),
            4,
            QtWidgets.QTableWidgetItem(string_utils.xstr(valid_date)),
        )

        gtk_apply = "./icons/gtk-clear.svg"
        ui_utils.set_table_widget_field_icon(
            self.ui.tableWidget_medicine,
            self.ui.tableWidget_medicine.currentRow(),
            5,
            gtk_apply,
            "medicine_key",
            medicine_key,
            self._clear_ins_code,
        )

    def _locate_drug(self, ins_code):
        ins_code_found = False
        for row_no in range(self.ui.tableWidget_drug.rowCount()):
            self.ui.tableWidget_drug.setCurrentCell(row_no, 1)
            drug_code = self.table_widget_drug.field_value(1)
            if ins_code == drug_code:
                ins_code_found = True

        if not ins_code_found:
            self.ui.tableWidget_drug.setCurrentCell(0, 1)

    def _medicine_name_query(self):
        medicine_name = self.ui.lineEdit_medicine_query.text()
        self._read_medicine(medicine_name)
        self._medicine_item_selection_changed()
        self.ui.lineEdit_medicine_query.setFocus(True)
        self.ui.lineEdit_medicine_query.setCursorPosition(len(medicine_name))

    def _filter_medicine(self):
        self.ui.action_update_valid_date.setEnabled(True)

        if self.ui.radioButton_all.isChecked():
            self.ui.action_update_valid_date.setEnabled(False)
            self._read_medicine()
            return

        for row_no in range(self.ui.tableWidget_medicine.rowCount() - 1, -1, -1):
            error_item = self.ui.tableWidget_medicine.item(row_no, 6)
            if error_item is None or error_item.text() == "":
                self.ui.tableWidget_medicine.removeRow(row_no)

    def _drug_name_query(self):
        drug_name = self.ui.lineEdit_drug_query.text()
        self._read_drug(drug_name)
        self.ui.lineEdit_drug_query.setFocus(True)
        self.ui.lineEdit_drug_query.setCursorPosition(len(drug_name))

    def _valid_date_changed(self):
        self._read_medicine()
        self._filter_medicine()

    def _update_valid_date(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("更新有效期限")
        msg_box.setText(
            "<font size='4' color='blue'><b>確定更新過期藥品的有效期限?</b></font>"
        )
        msg_box.setInformativeText("注意！有效期限只會更新健保藥品第一欄的資料!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        update_record = msg_box.exec_()
        if not update_record:
            return

        record_count = self.ui.tableWidget_medicine.rowCount()

        progress_dialog = QtWidgets.QProgressDialog(
            "正在更新健保藥品有效期限中, 請稍後...", "取消", 0, record_count, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for row_no in range(record_count):
            progress_dialog.setValue(row_no)
            if progress_dialog.wasCanceled():
                break

            self.ui.tableWidget_medicine.setCurrentCell(row_no, 1)
            if self.ui.tableWidget_drug.rowCount() > 0:
                self.ui.tableWidget_drug.setCurrentCell(0, 0)
                self._set_ins_drug()
            else:
                self._clear_ins_code(show_warning=False)

        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()
        self._read_medicine()
        self._filter_medicine()

    def _update_drug(self, medicine_type, file_name, url=None):
        title = "下載健保藥品更新檔"
        message = (
            '<font size="5" color="red"><b>正在下載健保藥品更新檔, 請稍後...</b></font>'
        )
        hint = "正在與更新檔資料庫連線, 會花費一些時間."
        if url is not None:
            file_name = dropbox_utils.download_dropbox_file(
                file_name, url, title, message, hint
            )

        sql = f'''
            DELETE FROM drug
            WHERE
                MedicineType = "{medicine_type}" OR
                MedicineType IS NULL
        '''
        self.database.exec_sql(sql)

        if medicine_type == "單方":
            tab_sheet_name = "中藥單方"
        else:
            tab_sheet_name = "中藥複方"

        try:
            rows = get_data(file_name)[tab_sheet_name]
        except Exception:
            tab_sheet_name += "_"
            rows = get_data(file_name)[tab_sheet_name]  # 2023-06-05 與之前不同

        progress_bar = QProgressBar()
        progress_bar.setMaximum(len(rows))
        progress_bar.setValue(0)
        self.ui.statusbar.addWidget(progress_bar)
        self._write_ins_drug(medicine_type, rows, progress_bar)
        self.ui.statusbar.removeWidget(progress_bar)

    def _update_ins_drug(self):
        self._update_drug(
            "單方",
            "drug1.ods",
            "https://www.dropbox.com/scl/fi/xh5nmj1xdo01rk6eg4a1f/drug1.ods?rlkey=avtcu3o6f62h3fnarjoqumdl5&dl=1",
        )
        self._update_drug(
            "複方",
            "drug2.ods",
            "https://www.dropbox.com/scl/fi/dl11wmvo0ae09p854x006/drug2.ods?rlkey=hv50kjm1bwqx93njf5d9dbrsr&dl=1",
        )

        self._read_medicine()

        system_utils.show_message_box(
            QMessageBox.Information,
            "線上更新健保碼",
            '<font size="5" color="blue"><b>最新版本的健保碼更新已完成.</b></font>',
            "恭喜您! 現在已經是最新的健保藥品",
        )

    def _update_prescript(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("更新病歷處方資料")
        msg_box.setText(
            "<font size='4' color='blue'><b>確定更新病歷內的處方健保碼資料?</b></font>"
        )
        msg_box.setInformativeText("注意！沒有健保碼的藥品會將病歷處方的藥品碼請除!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        update_record = msg_box.exec_()
        if not update_record:
            return

        record_count = self.ui.tableWidget_medicine.rowCount()

        progress_dialog = QtWidgets.QProgressDialog(
            "正在更新病歷處方健保藥品碼中, 請稍後...", "取消", 0, record_count, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for row_no in range(record_count):
            progress_dialog.setValue(row_no)
            if progress_dialog.wasCanceled():
                break

            ins_code = self.ui.tableWidget_medicine.item(row_no, 3)
            if ins_code is not None:
                ins_code = ins_code.text()

            if ins_code in [None, ""]:
                ins_code = "NULL"

            medicine_key = self.ui.tableWidget_medicine.item(row_no, 0)
            if medicine_key is not None:
                medicine_key = medicine_key.text()
            else:
                continue

            medicine_type = self.ui.tableWidget_medicine.item(row_no, 1)
            if medicine_type is not None:
                medicine_type = medicine_type.text()
            else:
                continue

            medicine_name = self.ui.tableWidget_medicine.item(row_no, 2)
            if medicine_name is not None:
                medicine_name = medicine_name.text()
            else:
                continue

            if ins_code == "NULL":
                update_condition = "InsCode = NULL"
                check_condition = "InsCode IS NOT NULL"
            else:
                update_condition = f'InsCode = "{ins_code}"'
                check_condition = f'InsCode != "{ins_code}"'

            valid_year = self.ui.spinBox_valid_year.value()
            valid_month = self.ui.spinBox_valid_month.value()
            start_date = f"{valid_year}-{valid_month:0>2}-01"

            sql = f'''
                UPDATE prescript
                SET
                    {update_condition}
                WHERE
                    DATE(CaseDate) >= "{start_date}" AND
                    ((MedicineKey = {medicine_key} AND MedicineName = "{medicine_name}") OR
                     (MedicineType = "{medicine_type}" AND MedicineName = "{medicine_name}")) AND
                    {check_condition}
            '''
            if row_no <= 10:
                print(sql)

            self.database.exec_sql(sql)

        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("病歷處方健保碼更新完成")
        msg_box.setText("<font size='4'><b>所有的病歷處方均已完成更新.</b></font>")
        msg_box.setInformativeText("請按確定鍵結束.")
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

    # 選擇藥廠名稱
    def _get_factory(self):
        sql = """
            SELECT LEFT(Supplier, 4) AS Factory FROM drug
            WHERE
                Supplier IS NOT NULL AND
                LENGTH(Supplier) >= 2
            GROUP BY LEFT(Supplier, 2)
            ORDER BY CAST(CONVERT(`Supplier` using big5) AS BINARY)
        """

        rows = self.database.select_record(sql)

        items = []
        for row in rows:
            items.append(string_utils.xstr(row["Factory"]))

        item, ok = QInputDialog.getItem(self, "藥廠名稱", "請選擇藥廠", items, 0, False)

        if not ok or not item:
            return None

        factory = item[:2]

        return factory

    # 指定藥廠健保藥品碼
    def _assign_ins_code(self):
        factory = self._get_factory()
        if factory is None:
            return

        row_count = self.ui.tableWidget_medicine.rowCount()
        progress_dialog = QtWidgets.QProgressDialog(
            "正在轉入指定的藥廠藥品碼中, 請稍後...", "取消", 0, row_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for row_no in range(row_count):
            self.ui.tableWidget_medicine.setCurrentCell(row_no, 0)
            self._set_factory(factory)

            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()

        system_utils.show_message_box(
            QMessageBox.Information,
            "轉入完成",
            "<h3>指定藥廠的健保藥品碼轉入完成.</h3>",
            "請自行檢視是否正確.",
        )

    def _set_factory(self, factory):
        row_count = self.ui.tableWidget_drug.rowCount()
        for row_no in range(row_count):
            self.ui.tableWidget_drug.setCurrentCell(row_no, 0)
            current_factory = self.ui.tableWidget_drug.item(row_no, 4).text()
            if factory in current_factory:
                self._set_ins_drug()

    def _check_medicine_name(self):
        row_count = self.ui.tableWidget_medicine.rowCount()
        progress_dialog = QtWidgets.QProgressDialog(
            "正在檢查處方名稱是否相符, 請稍後...", "取消", 0, row_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        self.ui.tableWidget_medicine.blockSignals(True)

        for row_no in range(self.ui.tableWidget_medicine.rowCount()):
            progress_dialog.setValue(row_no)

            self.ui.tableWidget_medicine.setCurrentCell(row_no, 0)
            ins_code = self.ui.tableWidget_medicine.item(row_no, 3).text()
            medicine_name = self.ui.tableWidget_medicine.item(row_no, 2).text()
            drug_row = self._get_drug_row(ins_code)
            if drug_row is None:
                continue

            drug_name = string_utils.xstr(drug_row["DrugName"])
            supplier = string_utils.xstr(drug_row["Supplier"])
            if not self._is_same_medicine(medicine_name, drug_name, supplier):
                self.ui.tableWidget_medicine.setItem(
                    row_no,
                    6,
                    QtWidgets.QTableWidgetItem(f"名稱不符:{drug_name}"),
                )

        progress_dialog.setValue(row_count)
        self.ui.tableWidget_medicine.blockSignals(False)
        self.ui.tableWidget_medicine.resizeColumnsToContents()

    def _get_drug_row(self, ins_code):
        sql = f'''
            SELECT * FROM drug
            WHERE
                InsCode = "{ins_code}"
        '''
        rows = self.database.select_record(sql)
        if not rows:
            return None

        return rows[0]

    # 檢查處方名稱是否相符的關鍵邏輯
    def _is_same_medicine(self, med_name, drug_name, supplier):
        # 1. 基本清理
        noise_pattern = r'[“"”]|濃縮(細粒|顆粒|散|粉|膠囊|膜衣錠|丸)|(去.*)'
        clean_drug = re.sub(noise_pattern, "", drug_name)

        # 2. 移除廠商名
        supplier_short = supplier[:2]
        clean_drug = clean_drug.replace(supplier_short, "").strip()

        # 3. 處理括號（如：複方丹參片）
        # 有些藥名核心在括號內，例如：行氣活血...(複方丹參片)
        extra_info = re.search(r"\((.*?)\)", clean_drug)
        if extra_info:
            if med_name in extra_info.group(1):
                return True

        # 4. 關鍵判定邏輯：處理「大棗」問題
        # 如果處方名稱完全等於清理後的藥名，那絕對沒問題
        if med_name == clean_drug:
            return True

        # 如果處方名是藥名的一部分 (例如: "大棗" in "甘麥大棗湯")
        if med_name in clean_drug:
            # 檢查 clean_drug 是否為複方格式 (以湯/散/丸/飲結尾)
            formula_suffixes = ("湯", "散", "丸", "飲", "丹", "膏", "方")
            med_is_formula = med_name.endswith(formula_suffixes)
            drug_is_formula = clean_drug.endswith(formula_suffixes)

            # 如果處方是單味藥(大棗)，藥庫是複方(大棗湯)，則判定不符
            if not med_is_formula and drug_is_formula:
                return False

            return True  # 其他情況（如縮寫符合）可視為 True 或進入人工覆核

        return False
