# -*- coding: UTF-8 -*-

import subprocess

from openpyxl import Workbook
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (
    class_utils,
    dialog_utils,
    medicine_utils,
    number_utils,
    personnel_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 成方詞庫 2018.04.14
class DictCompound(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.dict_type = "成方"
        self.user_name = system_utils.get_user_name(self.system_settings)
        self._drag_source_row = None  # 拖曳中的來源列

        self._set_ui()
        self._set_signal()
        self.read_medicine()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DICT_COMPOUND, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        self.table_widget_dict_compound = class_utils.get_table_widget(
            self.ui.tableWidget_dict_compound, self.database
        )
        self.table_widget_dict_compound.set_column_hidden([0])
        self.table_widget_dict_medicine = class_utils.get_table_widget(
            self.ui.tableWidget_dict_medicine, self.database
        )
        self.table_widget_dict_medicine.set_column_hidden([0, 1])
        self._set_table_width()
        self._set_description()
        self._set_drag_drop()

        if (
            personnel_utils.get_permission(
                self.database, "系統作業", "關閉匯出功能", self.user_name
            )
            == "Y"
        ):
            self.ui.toolButton_export_compound.setEnabled(False)

    def _set_description(self):
        html = """
            成方名稱說明
            <ol>
                <li>單項☐ 抬頭☐: 輸入病歷時, 只代入成方內容, 不代入成方名稱</li>
                <li>單項☐ 抬頭☑: 輸入病歷時, 代入成方名稱與成方內容</li>
                <li>單項☑ 抬頭☐: 輸入病歷時, 只代入成方名稱, 不代入成方內容</li>
                <li>單項☑ 抬頭☑: 輸入病歷時, 代入成方名稱與成方內容, 統計時只顯示成方名稱</li>
            </ol>
        """
        self.ui.textEdit_description.setHtml(html)

    # 設定成方內容可整列拖曳排序
    def _set_drag_drop(self):
        table = self.ui.tableWidget_dict_medicine

        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.setDragEnabled(True)
        table.setAcceptDrops(True)
        table.viewport().setAcceptDrops(True)
        table.setDropIndicatorShown(True)
        table.setDragDropOverwriteMode(False)  # 關鍵: 不覆蓋, 用插入的方式
        table.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        table.verticalHeader().setSectionsMovable(False)

        # .ui 載入的 widget 無法 subclass, 用 eventFilter 攔截 drop 事件
        table.viewport().installEventFilter(self)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_dict_compound.itemSelectionChanged.connect(
            self.dict_compound_changed
        )
        self.ui.toolButton_add_dict_compound.clicked.connect(self._add_dict_compound)
        self.ui.toolButton_remove_dict_compound.clicked.connect(
            self._remove_dict_compound
        )
        self.ui.toolButton_insert_null_medicine.clicked.connect(
            self._insert_null_medicine
        )
        self.ui.toolButton_edit_dict_compound.clicked.connect(self._edit_dict_compound)
        self.ui.toolButton_export_compound.clicked.connect(self._export_compound)
        self.ui.tableWidget_dict_compound.doubleClicked.connect(
            self._edit_dict_compound
        )

        self.ui.toolButton_add_dict_medicine.clicked.connect(self._add_dict_medicine)
        self.ui.toolButton_remove_dict_medicine.clicked.connect(
            self._remove_dict_medicine
        )
        self.ui.toolButton_save_dosage.clicked.connect(self._save_dosage)
        self.ui.lineEdit_search_compound.textChanged.connect(self._search_compound)
        self.ui.tableWidget_dict_medicine.itemChanged.connect(
            self._dict_medicine_changed
        )

    # 設定欄位寬度
    def _set_table_width(self):
        dict_compound_width = [100, 120, 80, 240, 50, 70, 90, 50, 50]
        dict_medicine_width = [100, 100, 120, 60, 250, 120, 50, 60, 80]

        self.table_widget_dict_compound.set_table_heading_width(dict_compound_width)
        self.table_widget_dict_medicine.set_table_heading_width(dict_medicine_width)

    def read_medicine(self):
        self._read_dict_compound()

    def _read_dict_compound(self, keyword=None):
        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineType = "{self.dict_type}"
        '''
        if keyword is not None:
            sql += keyword

        sql += " ORDER BY MedicineCode, LENGTH(MedicineName), CAST(CONVERT(`MedicineName` using big5) AS BINARY)"

        self.table_widget_dict_compound.set_db_data(sql, self._set_dict_compound_data)
        self.dict_compound_changed()

    def _set_dict_compound_data(self, row_no, row):
        medicine_key = row["MedicineKey"]

        dict_compound_row = [
            string_utils.xstr(medicine_key),
            string_utils.xstr(row["MedicineCode"]),
            string_utils.xstr(row["InputCode"]),
            string_utils.xstr(row["MedicineName"]),
            string_utils.xstr(row["Unit"]),
            string_utils.xstr(row["SalePrice"]),
            string_utils.xstr(row["Project"]),
            None,
            None,
        ]

        for col_no in range(len(dict_compound_row)):
            self.ui.tableWidget_dict_compound.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(dict_compound_row[col_no])
            )
            if col_no in [5]:
                self.ui.tableWidget_dict_compound.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [4]:
                self.ui.tableWidget_dict_compound.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

        self._set_check_box(row_no, medicine_key)

    def _set_check_box(self, row_no, medicine_key):
        check_box_single = QtWidgets.QCheckBox()
        check_box_single.setStyleSheet("padding-left: 20px")
        check_box_title = QtWidgets.QCheckBox()
        check_box_title.setStyleSheet("padding-left: 20px")

        if (
            medicine_utils.get_medicine_extend(self.database, medicine_key, "成方單項")
            == "Y"
        ):
            check_box_single.setChecked(True)

        if (
            medicine_utils.get_medicine_extend(self.database, medicine_key, "成方抬頭")
            == "Y"
        ):
            check_box_title.setChecked(True)

        check_box_single.clicked.connect(
            lambda: self._update_compound_single(check_box_single, medicine_key)
        )
        check_box_title.clicked.connect(
            lambda: self._update_compound_title(check_box_title, medicine_key)
        )

        self.ui.tableWidget_dict_compound.setCellWidget(row_no, 7, check_box_single)
        self.ui.tableWidget_dict_compound.item(row_no, 7).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        self.ui.tableWidget_dict_compound.setCellWidget(row_no, 8, check_box_title)
        self.ui.tableWidget_dict_compound.item(row_no, 8).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _update_compound_single(self, check_box_single, medicine_key):
        if check_box_single.isChecked():
            medicine_utils.set_medicine_extend(
                self.database, medicine_key, "成方單項", "Y"
            )
        else:
            medicine_utils.remove_medicine_extend(
                self.database, medicine_key, "成方單項"
            )

    def _update_compound_title(self, check_box_title, medicine_key):
        if check_box_title.isChecked():
            medicine_utils.set_medicine_extend(
                self.database, medicine_key, "成方抬頭", "Y"
            )
        else:
            medicine_utils.remove_medicine_extend(
                self.database, medicine_key, "成方抬頭"
            )

    def dict_compound_changed(self):
        compound_key = self.table_widget_dict_compound.field_value(0)
        if compound_key is None:
            return

        self._read_ref_compound(compound_key)
        self.ui.tableWidget_dict_compound.setFocus(True)

    def _read_ref_compound(self, compound_key):
        sql = f"""
            SELECT * FROM refcompound
            WHERE
                CompoundKey = {compound_key}
            ORDER BY RefCompoundKey
        """
        self.table_widget_dict_medicine.set_db_data(sql, self._set_dict_medicine_data)
        self._set_total_dosage(self.ui.tableWidget_dict_medicine)

    def _set_dict_medicine_data(self, row_no, row):
        medicine_key = row["MedicineKey"]
        if medicine_key is None:
            return

        sql = f"""
            SELECT * FROM medicine
            WHERE
                MedicineKey = {medicine_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            medicine_row = {
                "RefCompoundKey": string_utils.xstr(row["RefCompoundKey"]),
                "MedicineKey": string_utils.xstr(medicine_key),
                "MedicineCode": None,
                "MedicineType": None,
                "MedicineName": None,
                "InsCode": None,
                "Unit": string_utils.xstr(row["Unit"]),
                "Quantity": string_utils.xstr(row["Quantity"]),
                "SalePrice": None,
            }
        else:
            medicine_row = rows[0]

        dict_medicine_row = [
            string_utils.xstr(row["RefCompoundKey"]),
            string_utils.xstr(medicine_row["MedicineKey"]),
            string_utils.xstr(medicine_row["MedicineCode"]),
            string_utils.xstr(medicine_row["MedicineType"]),
            string_utils.xstr(medicine_row["MedicineName"]),
            string_utils.xstr(medicine_row["InsCode"]),
            string_utils.xstr(medicine_row["Unit"]),
            string_utils.xstr(row["Quantity"]),
            string_utils.xstr(medicine_row["SalePrice"]),
        ]

        for col_no in range(len(dict_medicine_row)):
            self.ui.tableWidget_dict_medicine.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(dict_medicine_row[col_no])
            )
            if col_no in [7, 8]:
                self.ui.tableWidget_dict_medicine.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [6]:
                self.ui.tableWidget_dict_medicine.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    # ------------------------------------------------------------------
    # 成方內容拖曳排序
    # ------------------------------------------------------------------
    def eventFilter(self, source, event):
        if source is self.ui.tableWidget_dict_medicine.viewport():
            event_type = event.type()
            if event_type == QtCore.QEvent.DragEnter:
                # 只記錄來源列, 不攔截 (讓表格自己畫插入指示線)
                self._drag_source_row = self.ui.tableWidget_dict_medicine.currentRow()
            elif event_type == QtCore.QEvent.Drop:
                if self._medicine_drop_event(event):
                    return True  # 攔截, 不讓表格內建的搬移動作執行

        return super().eventFilter(source, event)

    def _medicine_drop_event(self, event):
        table = self.ui.tableWidget_dict_medicine
        if event.source() is not table:
            return False

        # 關鍵: 不可回傳 MoveAction, 否則 QAbstractItemView 會自動刪除來源列
        event.setDropAction(QtCore.Qt.CopyAction)
        event.accept()

        from_row = self._drag_source_row
        self._drag_source_row = None
        if from_row is None or from_row < 0:
            return True

        drop_index = table.indexAt(event.pos())
        if drop_index.isValid():
            to_row = drop_index.row()
            rect = table.visualRect(drop_index)
            if event.pos().y() > rect.center().y():  # 落在下半部 -> 插在該列之後
                to_row += 1
        else:
            to_row = table.rowCount()  # 拖到空白處 -> 移到最後

        if to_row in [from_row, from_row + 1]:  # 沒有移動
            return True

        key_list = []  # 目前畫面順序的 RefCompoundKey
        for row_no in range(table.rowCount()):
            item = table.item(row_no, 0)
            if item is None or item.text().strip() == "":
                return True
            try:
                key_list.append(int(item.text()))
            except ValueError:
                return True

        if from_row >= len(key_list):
            return True

        ref_compound_key = key_list.pop(from_row)
        if to_row > from_row:
            to_row -= 1
        key_list.insert(to_row, ref_compound_key)

        compound_key = self.table_widget_dict_compound.field_value(0)
        self._save_compound_order(compound_key, key_list)

        # 等拖曳程序完全結束後再重新載入畫面, 避免被 Qt 內建動作干擾
        QtCore.QTimer.singleShot(
            0, lambda: self._reload_ref_compound(compound_key, to_row)
        )

        return True

    def _reload_ref_compound(self, compound_key, current_row=0):
        table = self.ui.tableWidget_dict_medicine
        self._read_ref_compound(compound_key)

        if 0 <= current_row < table.rowCount():
            table.selectRow(current_row)

    # 依指定順序重新排列 refcompound 的資料
    def _save_compound_order(self, compound_key, new_order):
        if compound_key is None or len(new_order) <= 0:
            return

        sql = f"""
            SELECT * FROM refcompound
            WHERE
                CompoundKey = {compound_key}
        """
        records = {}
        for row in self.database.select_record(sql):
            records[int(row["RefCompoundKey"])] = row

        sorted_keys = sorted(records.keys())
        if sorted(new_order) != sorted_keys:  # 資料不一致, 不處理以策安全
            return

        # 把 old_key 的內容寫到 new_key 這個位置
        # (資料已先讀成 records 快照, 不會發生互相覆蓋的問題)
        for new_key, old_key in zip(sorted_keys, new_order):
            if new_key == old_key:
                continue

            record = records[old_key]
            values = []
            for field, value in record.items():
                if field in ["RefCompoundKey", "CompoundKey"]:
                    continue

                if value is None:
                    values.append(f"{field} = NULL")
                else:
                    data = string_utils.xstr(value).replace('"', '""')
                    values.append(f'{field} = "{data}"')

            if len(values) <= 0:
                continue

            sql = f"""
                UPDATE refcompound
                SET
                    {", ".join(values)}
                WHERE
                    RefCompoundKey = {new_key}
            """
            self.database.exec_sql(sql)

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    # 關閉分頁
    def close_charge_settings(self):
        self.close_all()
        self.close_tab()

    # 新增成方
    def _add_dict_compound(self):
        dialog = dialog_utils.get_dialog_input_drug(
            self, self.database, self.system_settings, "成方", None
        )

        if dialog.exec_():
            self._read_dict_compound()

        dialog.close_all()
        dialog.deleteLater()

    # 移除成方
    def _remove_dict_compound(self):
        compound_name = self.table_widget_dict_compound.field_value(3)
        msg_box = dialog_utils.get_message_box(
            f"刪除{self.dict_type}資料",
            QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定刪除{self.dict_type}: "{compound_name}"?</b></font>',
            "注意！資料刪除後, 將無法回復!",
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_dict_compound.field_value(0)
        self.database.delete_record("refcompound", "CompoundKey", key)
        self.database.delete_record("medicine", "MedicineKey", key)
        self.ui.tableWidget_dict_compound.removeRow(
            self.ui.tableWidget_dict_compound.currentRow()
        )

    # 更改成方
    def _edit_dict_compound(self):
        compound_key = self.table_widget_dict_compound.field_value(0)
        dialog = dialog_utils.get_dialog_input_drug(
            self, self.database, self.system_settings, "成方", compound_key
        )
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

        # 重新顯示資料
        sql = f"""
            SELECT * FROM medicine
            WHERE
                MedicineKey = {compound_key}
        """
        row_data = self.database.select_record(sql)[0]
        self._set_dict_compound_data(
            self.ui.tableWidget_dict_compound.currentRow(), row_data
        )

    # 移除成方內容
    def _remove_dict_medicine(self):
        medicine_name = self.table_widget_dict_medicine.field_value(4)
        msg_box = dialog_utils.get_message_box(
            "移除成方內容",
            QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定移除{self.dict_type}內容: "{medicine_name}"?</b></font>',
            "注意！資料移除後, 將無法回復!",
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_dict_medicine.field_value(0)
        self.database.delete_record("refcompound", "RefCompoundKey", key)
        self.ui.tableWidget_dict_medicine.removeRow(
            self.ui.tableWidget_dict_medicine.currentRow()
        )

    # 新增處方
    def _add_dict_medicine(self):
        dialog = dialog_utils.get_dialog_medicine(
            self,
            self.database,
            self.system_settings,
            self.ui.tableWidget_dict_medicine,
            None,
            "成方",
        )
        dialog.exec_()
        dialog.deleteLater()

    def add_ref_compound(self, row):
        compound_key = self.table_widget_dict_compound.field_value(0)

        fields = ["CompoundKey", "MedicineKey"]
        data = [
            compound_key,
            row["MedicineKey"],
        ]
        self.database.insert_record("refcompound", fields, data)
        self._read_ref_compound(compound_key)

    def _save_dosage(self):
        for row_no in range(self.ui.tableWidget_dict_medicine.rowCount()):
            dosage = self.ui.tableWidget_dict_medicine.item(row_no, 7)
            data = "NULL"
            if dosage is not None:
                data = dosage.text()

            if data == "":
                data = "NULL"

            self.ui.tableWidget_dict_medicine.setCurrentCell(row_no, 0)
            compound_key = self.table_widget_dict_medicine.field_value(0)
            sql = f"""
                UPDATE refcompound
                SET
                    Quantity = {data}
                WHERE
                    RefCompoundKey = {compound_key}
            """
            try:
                self.database.exec_sql(sql)
            except Exception:
                pass

        system_utils.show_message_box(
            QMessageBox.Information,
            "存檔完畢",
            "<h3>劑量已全部存檔完成</h3>",
            "資料正確.",
        )

    def _search_compound(self):
        keyword = self.ui.lineEdit_search_compound.text()
        keyword = keyword.strip()

        if keyword == "":
            self._read_dict_compound()
        else:
            script = f''' AND
                (InputCode LIKE "{keyword}%" OR
                 MedicineName LIKE "%{keyword}%")
            '''
            self._read_dict_compound(script)

        self.ui.lineEdit_search_compound.setFocus(True)
        self.ui.lineEdit_search_compound.setCursorPosition(len(keyword))

    def _dict_medicine_changed(self):
        row_no = self.ui.tableWidget_dict_medicine.currentRow()
        if self.ui.tableWidget_dict_medicine.item(row_no, 0) is None:
            return

        ref_compound_key = self.ui.tableWidget_dict_medicine.item(row_no, 0).text()
        quantity = self.ui.tableWidget_dict_medicine.item(row_no, 7)
        if quantity is not None:
            quantity = number_utils.get_float(quantity.text())

        sql = f"""
            UPDATE refcompound
            SET
                Quantity = {quantity}
            WHERE
                RefCompoundKey = {ref_compound_key}
        """
        self.database.exec_sql(sql)
        self._set_total_dosage(self.ui.tableWidget_dict_medicine)

    def _set_total_dosage(self, table_widget_prescript):
        total_dosage = 0.0
        for row_no in range(table_widget_prescript.rowCount()):
            item = table_widget_prescript.item(row_no, 7)
            if item is None:
                continue

            try:
                dosage = round(number_utils.get_float(item.text()), 1)
            except (ValueError, TypeError):
                item.setText(None)
                continue

            total_dosage += dosage

        self.ui.label_total_dosage.setText(f"總量: {total_dosage:.1f}")

    # 匯出成方
    def _export_compound(self):
        options = QFileDialog.Options()
        excel_filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出Excel檔案",
            "compound.xlsx",
            "excel檔案 (*.xlsx)",
            options=options,
        )
        if not excel_filename:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            "正在匯出成方資料中, 請稍後...",
            "取消",
            0,
            self.ui.tableWidget_dict_compound.rowCount(),
            self,
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        wb = Workbook()
        ws = wb.active
        ws.title = "sheet1"

        header_row = [
            "序",
            "成方名稱",
            "單位",
            "金額",
            "類別",
            "藥品名稱",
            "健保碼",
            "單位",
            "劑量",
            "金額",
        ]
        ws.column_dimensions["A"].width = 5
        ws.column_dimensions["B"].width = 30
        ws.column_dimensions["C"].width = 5
        ws.column_dimensions["D"].width = 12
        ws.column_dimensions["E"].width = 10
        ws.column_dimensions["F"].width = 25
        ws.column_dimensions["G"].width = 10
        ws.column_dimensions["H"].width = 5
        ws.column_dimensions["I"].width = 10
        ws.column_dimensions["J"].width = 10

        ws.append(header_row)

        for row_no in range(self.ui.tableWidget_dict_compound.rowCount()):
            row = []
            self.ui.tableWidget_dict_compound.setCurrentCell(row_no, 0)
            row.append(row_no + 1)
            row.append(self.table_widget_dict_compound.field_value(3))
            row.append(self.table_widget_dict_compound.field_value(4))
            row.append(self.table_widget_dict_compound.field_value(5))
            ws.append(row)

            for i in range(self.ui.tableWidget_dict_medicine.rowCount()):
                medicine_row = []
                self.ui.tableWidget_dict_medicine.setCurrentCell(i, 0)
                medicine_row.append("")
                medicine_row.append("")
                medicine_row.append("")
                medicine_row.append("")
                medicine_row.append(self.table_widget_dict_medicine.field_value(3))
                medicine_row.append(self.table_widget_dict_medicine.field_value(4))
                medicine_row.append(self.table_widget_dict_medicine.field_value(5))
                medicine_row.append(self.table_widget_dict_medicine.field_value(6))
                medicine_row.append(self.table_widget_dict_medicine.field_value(7))
                medicine_row.append(self.table_widget_dict_medicine.field_value(8))
                ws.append(medicine_row)

            ws.append([])
            progress_dialog.setValue(row_no)

        wb.save(excel_filename)

        self.ui.tableWidget_dict_compound.setCurrentCell(0, 0)
        progress_dialog.setValue(self.ui.tableWidget_dict_compound.rowCount())
        progress_dialog.deleteLater()

        system_utils.show_message_box(
            QMessageBox.Information,
            "Excel匯出完成",
            f"<h3>{excel_filename}匯出完成.</h3>",
            "Excel 檔案格式.",
        )

        try:
            subprocess.Popen([excel_filename], shell=True)
        except Exception:
            pass

    # 新增遺失的處方
    def _insert_null_medicine(self):
        medicine_key = self.ui.tableWidget_dict_medicine.item(
            self.ui.tableWidget_dict_medicine.currentRow(), 1
        )
        if medicine_key is None:
            return

        medicine_key = medicine_key.text()
        dialog = dialog_utils.get_dialog_input_drug(
            self, self.database, self.system_settings, "水藥", medicine_key
        )

        if dialog.exec_():
            self._read_dict_compound()

        dialog.close_all()
        dialog.deleteLater()
