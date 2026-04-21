# -*- coding: utf-8 -*-
import datetime
import os

from pyexcel_ods3 import get_data
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QInputDialog, QMessageBox, QProgressBar, QPushButton

from libs import (
    class_utils,
    db_utils,
    dropbox_utils,
    nhi_utils,
    prescript_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 健保藥品更新 2026.04.20
class DictInsDrug(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DictInsDrug, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.col_no = {
            "medicine_key": 0,
            "medicine_type": 1,
            "medicine_name": 2,
            "drug_name": 3,
            "ins_code": 4,
            "valid_date": 5,
            "clear_ins_code": 6,
            "error_message": 7,
        }

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
        width = [100, 50, 160, 120, 100, 130, 50, 200]
        self.table_widget_medicine.set_table_heading_width(width)

        width = [100, 100, 180, 110, 120, 130, 50]
        self.table_widget_drug.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.action_sync_drug.triggered.connect(self._sync_drug)
        self.ui.action_update_drug.triggered.connect(self._update_ins_drug)
        self.ui.action_close.triggered.connect(self._close_ins_drug)
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
        self.ui.action_export_drug_json.triggered.connect(self._export_dict_drug_json)

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
                MedicineName IS NOT NULL AND
                LENGTH(MedicineName) > 0 AND
                medicine.MedicineType IN ({medicine_type})
                {medicine_name_script}
            ORDER BY FIELD(medicine.MedicineType, {medicine_type}),
                     LENGTH(MedicineName), CAST(CONVERT(`MedicineName` using big5) AS BINARY)
        """
        self.table_widget_medicine.set_db_data(sql, self._set_medicine_data)
        self._check_medicine_name()

    def _set_medicine_data(self, row_no, row):
        error_message = []

        medicine_key = string_utils.xstr(row["MedicineKey"])
        medicine_name = string_utils.xstr(row["MedicineName"])
        drug_name = string_utils.xstr(row["DrugName"])
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
            medicine_name,
            drug_name,
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
                self.col_no["clear_ins_code"],
                gtk_apply,
                "medicine_key",
                medicine_key,
                self._clear_ins_code,
            )

    def _clear_ins_code(self, show_warning=True):
        medicine_name = self.table_widget_medicine.field_value(
            self.col_no["medicine_name"]
        )
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

        medicine_key = self.table_widget_medicine.field_value(
            self.col_no["medicine_key"]
        )
        sql = f"""
            UPDATE medicine
            SET
                InsCode = NULL
            WHERE
                MedicineKey = {medicine_key}
        """
        self.database.exec_sql(sql)

        row_no = self.ui.tableWidget_medicine.currentRow()

        for column in range(self.col_no["ins_code"], self.col_no["clear_ins_code"]):
            self.ui.tableWidget_medicine.setItem(
                row_no, column, QtWidgets.QTableWidgetItem("")
            )
        self.ui.tableWidget_medicine.setCellWidget(
            row_no, self.col_no["clear_ins_code"], None
        )

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
            self.table_widget_medicine.field_value(self.col_no["medicine_name"])
        )
        ins_code = self.table_widget_medicine.field_value(self.col_no["ins_code"])
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
        drug_name = self.table_widget_drug.field_value(2)
        valid_date = self.table_widget_drug.field_value(5)
        medicine_key = self.table_widget_medicine.field_value(0)
        sql = f'''
            UPDATE medicine
            SET
                InsCode = "{drug_code}",
                DrugName = "{drug_name}"
            WHERE
                MedicineKey = {medicine_key}
        '''
        self.database.exec_sql(sql)

        self.ui.tableWidget_medicine.setItem(
            self.ui.tableWidget_medicine.currentRow(),
            self.col_no["drug_name"],
            QtWidgets.QTableWidgetItem(string_utils.xstr(drug_name)),
        )
        self.ui.tableWidget_medicine.setItem(
            self.ui.tableWidget_medicine.currentRow(),
            self.col_no["ins_code"],
            QtWidgets.QTableWidgetItem(string_utils.xstr(drug_code)),
        )
        self.ui.tableWidget_medicine.setItem(
            self.ui.tableWidget_medicine.currentRow(),
            self.col_no["valid_date"],
            QtWidgets.QTableWidgetItem(string_utils.xstr(valid_date)),
        )

        gtk_apply = "./icons/gtk-clear.svg"
        ui_utils.set_table_widget_field_icon(
            self.ui.tableWidget_medicine,
            self.ui.tableWidget_medicine.currentRow(),
            self.col_no["clear_ins_code"],
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
            error_item = self.ui.tableWidget_medicine.item(
                row_no, self.col_no["error_message"]
            )
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

            self.ui.tableWidget_medicine.setCurrentCell(
                row_no, self.col_no["medicine_name"]
            )
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

    def _convert_valid_date(self, valid_date):
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

        return valid_date

    def _update_drug_file1(self):
        medicine_type = "單方"
        url = f"https://raw.githubusercontent.com/picacat/medical-announcements/main/{medicine_type}.ods"
        drug_file = os.path.join(self.base_path, f"{medicine_type}.ods")
        if not system_utils.download_file_from_github(url, drug_file):
            system_utils.show_message_box(
                QMessageBox.Critical,
                "線上更新健保碼失敗",
                '<font size="5" color="red"><b>無法下載最新版本的單方健保碼資料.</b></font>',
                "請檢查是否可以連上網際網路",
            )
            return

        try:
            data_dict = get_data(drug_file)
            # 取出字典裡所有的 values，並轉成 list 抓第一個 [0]
            rows = list(data_dict.values())[0]
        except Exception as e:
            print(f"讀取分頁失敗: {e}")

        progress_bar = QProgressBar()
        progress_bar.setMaximum(len(rows))
        progress_bar.setValue(0)
        self.ui.statusbar.addWidget(progress_bar)
        self._write_ins_drug_file1(medicine_type, rows, progress_bar)
        self.ui.statusbar.removeWidget(progress_bar)

    def _write_ins_drug_file1(self, medicine_type, rows, progress_bar):
        ins_code_no = self._get_field_number(rows[0], "藥品代碼")
        drug_name_no = self._get_field_number(rows[0], "藥品名稱")

        drug_type_no = self._get_field_number(rows[0], "劑型")
        supplier_no = self._get_field_number(rows[0], "製造廠名稱")
        invalid_date_no = self._get_field_number(rows[0], "不再收載日")

        sql = f'''
            DELETE FROM drug
            WHERE
                MedicineType = "{medicine_type}" OR
                MedicineType IS NULL
        '''
        self.database.exec_sql(sql)

        for row_no, row in enumerate(rows):
            if row is None:
                continue

            progress_bar.setValue(row_no + 1)
            if row_no == 0:  # data heading 不轉檔
                continue

            if len(row) == 0:
                continue

            valid_date = "2099-12-31"
            try:
                # 先檢查 row 的長度是否足以包含 invalid_date_no
                if invalid_date_no is not None and len(row) > invalid_date_no:
                    invalid_date = string_utils.xstr(row[invalid_date_no]).strip()
                else:
                    invalid_date = ""  # 如果欄位不存在，視為空白

                if invalid_date != "":
                    valid_date = self._convert_valid_date(invalid_date)
            except Exception:
                pass

            try:
                ins_code = row[ins_code_no]
                drug_name = row[drug_name_no]
                drug_type = row[drug_type_no]
                supplier = row[supplier_no]
            except Exception:
                continue

            drug_name = prescript_utils.clean_drug_name(drug_name, medicine_type="單方")

            field = [
                "InsCode",
                "DrugName",
                "MedicineType",
                "Unit",
                "Supplier",
                "ValidDate",
            ]

            data = [
                ins_code.strip(),
                drug_name.strip(),
                medicine_type,
                drug_type,
                supplier[:5].strip(),
                valid_date,
            ]

            self.database.insert_record("drug", field, data)

    def _update_drug_file2(self):
        medicine_type = "複方"
        url = f"https://raw.githubusercontent.com/picacat/medical-announcements/main/{medicine_type}.ods"
        drug_file = os.path.join(self.base_path, f"{medicine_type}.ods")
        if not system_utils.download_file_from_github(url, drug_file):
            system_utils.show_message_box(
                QMessageBox.Critical,
                "線上更新健保碼失敗",
                f'<font size="5" color="red"><b>無法下載最新版本的{medicine_type}健保碼資料.</b></font>',
                "請檢查是否可以連上網際網路",
            )
            return

        try:
            data_dict = get_data(drug_file)
            # 取出字典裡所有的 values，並轉成 list 抓第一個 [0]
            rows = list(data_dict.values())[0]
        except Exception as e:
            print(f"讀取分頁失敗: {e}")

        progress_bar = QProgressBar()
        progress_bar.setMaximum(len(rows))
        progress_bar.setValue(0)
        self.ui.statusbar.addWidget(progress_bar)
        self._write_ins_drug_file2(medicine_type, rows, progress_bar)
        self.ui.statusbar.removeWidget(progress_bar)

    def _write_ins_drug_file2(self, medicine_type, rows, progress_bar):
        ins_code_no = self._get_field_number(rows[0], "藥品代碼")
        drug_name_no = self._get_field_number(rows[0], "方名")

        drug_type_no = self._get_field_number(rows[0], "劑型")
        supplier_no = self._get_field_number(rows[0], "製造廠名稱")
        invalid_date_no = self._get_field_number(rows[0], "不再收載日期")

        sql = f'''
            DELETE FROM drug
            WHERE
                MedicineType = "{medicine_type}" OR
                MedicineType IS NULL
        '''
        self.database.exec_sql(sql)

        for row_no, row in enumerate(rows):
            if row is None:
                continue

            progress_bar.setValue(row_no + 1)
            if row_no == 0:  # data heading 不轉檔
                continue

            if len(row) == 0:
                continue

            valid_date = "2099-12-31"
            try:
                # 先檢查 row 的長度是否足以包含 invalid_date_no
                if invalid_date_no is not None and len(row) > invalid_date_no:
                    invalid_date = string_utils.xstr(row[invalid_date_no]).strip()
                else:
                    invalid_date = ""  # 如果欄位不存在，視為空白

                if invalid_date != "":
                    valid_date = self._convert_valid_date(invalid_date)
            except Exception:
                pass

            try:
                ins_code = row[ins_code_no]
                drug_name = row[drug_name_no]
                drug_type = row[drug_type_no]
                supplier = row[supplier_no]
            except Exception:
                continue

            drug_name = prescript_utils.clean_drug_name(drug_name, medicine_type="複方")

            field = [
                "InsCode",
                "DrugName",
                "MedicineType",
                "Unit",
                "Supplier",
                "ValidDate",
            ]

            data = [
                ins_code.strip(),
                drug_name.strip(),
                medicine_type,
                drug_type,
                supplier[:5].strip(),
                valid_date,
            ]

            self.database.insert_record("drug", field, data)

    def _update_ins_drug(self):
        self._update_drug_file1()
        self._update_drug_file2()

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

        valid_year = self.ui.spinBox_valid_year.value()
        valid_month = self.ui.spinBox_valid_month.value()
        start_date = f"{valid_year}-{valid_month:0>2}-01 00:00:00"

        for row_no in range(record_count):
            progress_dialog.setValue(row_no)
            if progress_dialog.wasCanceled():
                break

            ins_code = self.ui.tableWidget_medicine.item(
                row_no, self.col_no["ins_code"]
            )
            if ins_code is not None:
                ins_code = ins_code.text()

            if ins_code in [None, ""]:
                ins_code = "NULL"

            medicine_key = self.ui.tableWidget_medicine.item(
                row_no, self.col_no["medicine_key"]
            )
            if medicine_key is not None:
                medicine_key = medicine_key.text()
            else:
                continue

            medicine_type = self.ui.tableWidget_medicine.item(
                row_no, self.col_no["medicine_type"]
            )
            if medicine_type is not None:
                medicine_type = medicine_type.text()
            else:
                continue

            medicine_name = self.ui.tableWidget_medicine.item(
                row_no, self.col_no["medicine_name"]
            )
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

            sql = f'''
                UPDATE prescript
                SET
                    {update_condition}
                WHERE
                    CaseDate >= "{start_date}" AND
                    MedicineSet = 1 AND
                    (MedicineKey = {medicine_key} AND MedicineName = "{medicine_name}") AND
                    {check_condition}
            '''
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
            self.ui.tableWidget_medicine.setCurrentCell(
                row_no, self.col_no["medicine_name"]
            )
            medicine_name = self.ui.tableWidget_medicine.item(
                row_no, self.col_no["medicine_name"]
            ).text()
            self._set_factory(factory, medicine_name)

            progress_dialog.setValue(row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()

        system_utils.show_message_box(
            QMessageBox.Information,
            "轉入完成",
            "<h3>指定藥廠的健保藥品碼轉入完成.</h3>",
            "請自行檢視是否正確.",
        )

    # 指定藥廠.
    def _set_factory(self, factory, medicine_name):
        row_count = self.ui.tableWidget_drug.rowCount()
        for row_no in range(row_count):
            self.ui.tableWidget_drug.setCurrentCell(row_no, 0)
            current_drug = self.ui.tableWidget_drug.item(row_no, 2).text()
            current_factory = self.ui.tableWidget_drug.item(row_no, 4).text()
            if factory in current_factory and medicine_name == current_drug:
                self._set_ins_drug()

    def _check_medicine_name(self):
        self.ui.tableWidget_medicine.blockSignals(True)
        for row_no in range(self.ui.tableWidget_medicine.rowCount()):
            self.ui.tableWidget_medicine.setCurrentCell(row_no, 0)
            ins_code = self.ui.tableWidget_medicine.item(
                row_no, self.col_no["ins_code"]
            ).text()
            medicine_name = self.ui.tableWidget_medicine.item(
                row_no, self.col_no["medicine_name"]
            ).text()
            try:
                ins_drug_name = self.ui.tableWidget_medicine.item(
                    row_no, self.col_no["drug_name"]
                ).text()
            except Exception:
                ins_drug_name = None

            if ins_drug_name not in [None, ""]:
                medicine_name = ins_drug_name

            drug_row = self._get_drug_row(ins_code)
            if drug_row is None:
                continue

            drug_name = string_utils.xstr(drug_row["DrugName"])
            if not prescript_utils.is_same_medicine(medicine_name, drug_name):
                message_item = self.ui.tableWidget_medicine.item(
                    row_no, self.col_no["error_message"]
                )
                error_message = []
                if message_item is not None:
                    error_message.append(message_item.text())

                error_message.append(f"藥名不符:{drug_name}")

                self.ui.tableWidget_medicine.setItem(
                    row_no,
                    self.col_no["error_message"],
                    QtWidgets.QTableWidgetItem(", ".join(error_message)),
                )
                for col_no in range(self.ui.tableWidget_medicine.columnCount()):
                    self.ui.tableWidget_medicine.item(row_no, col_no).setForeground(
                        QtGui.QColor("red")
                    )

        self.ui.tableWidget_medicine.setCurrentCell(0, 0)
        self.ui.tableWidget_medicine.blockSignals(False)

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

    def _export_dict_drug_json(self):
        options = QtWidgets.QFileDialog.Options()
        json_file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.parent,
            "匯出健保藥品JSON檔案",
            "drug.json",
            "json檔案 (*.json)",
            options=options,
        )
        if not json_file_name:
            return

        sql = """
            SELECT * FROM drug
        """
        rows = self.database.select_record(sql)

        json_data = db_utils.mysql_to_json(rows)
        text_file = open(json_file_name, "w", encoding="utf8")
        text_file.write(str(json_data))
        text_file.close()

        system_utils.show_message_box(
            QMessageBox.Information,
            "JSON資料匯出完成",
            f"<h3>{json_file_name}匯出完成.</h3>",
            "JSON 檔案格式.",
        )
