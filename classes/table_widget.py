from libs import string_utils, system_utils
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox


# tableWidget 設定 2018.03.29
class TableWidget:
    # 初始化
    def __init__(self, table_widget, database):
        self.table_widget = table_widget
        self.database = database
        self.process_data = None
        self.db_row_count = 0
        self.is_set_heading = False
        self.sort = QtCore.Qt.AscendingOrder
        self.parent = None
        self._set_signal()

        p = self.table_widget.palette()
        p.setBrush(p.Inactive, p.Highlight, p.brush(p.Highlight))
        self.table_widget.setPalette(p)

    # 解構
    def __del__(self):
        pass

    def set_parent(self, parent):
        self.parent = parent

    def _set_signal(self):
        self.table_widget.horizontalHeader().sectionClicked.connect(
            self._table_widget_header_clicked
        )
        self.table_widget.itemSelectionChanged.connect(self._table_widget_item_changed)

    def _table_widget_item_changed(self):
        self._refresh_status_bar()

    def _refresh_status_bar(self):
        if self.parent is None:
            return

        record_count = self.table_widget.rowCount()
        record_index = self.table_widget.currentRow()
        if record_count > 0:
            self.parent.set_record_index(f'記錄: 第{record_index+1}筆, 共{record_count}筆')
        else:
            self.parent.set_record_index('')

    def _table_widget_header_clicked(self, col_no):
        self.table_widget.sortItems(col_no, self.sort)
        if self.sort == QtCore.Qt.AscendingOrder:
            self.sort = QtCore.Qt.DescendingOrder
        else:
            self.sort = QtCore.Qt.AscendingOrder

    # 設定 tableWidget heading width
    def set_table_heading_width(self, width):
        for i in range(0, len(width)):
            if self.table_widget.horizontalHeaderItem(i) is None:
                continue

            self.table_widget.setColumnWidth(i, width[i])
            self.table_widget.horizontalHeaderItem(i).setTextAlignment(Qt.AlignCenter)

        self.is_set_heading = True

    def set_column_hidden(self, hidden_columns=None):
        for i in hidden_columns:
            self.table_widget.setColumnHidden(i, True)

    def set_focus(self):
        self.table_widget.setFocus()

    # 設定資料庫資料
    def set_db_data(
            self, sql=None, process_data=None, rows=None, start_index=0, set_focus=True,
            archive_database=None, resize_rows=True):
        self.process_data = process_data

        if rows is None:
            if archive_database is None:
                rows = self.database.select_record(sql)
            else:
                rows = archive_database.select_record(sql)

        self.db_row_count = len(list(rows)) + start_index
        self.table_widget.setRowCount(self.db_row_count)
        for i, row in zip(range(start_index, self.db_row_count), rows):
            self.process_data(i, row)

        if not self.is_set_heading:
            self.table_widget.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
            self.table_widget.resizeColumnsToContents()

        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.selectRow(0)
        if set_focus:
            self.table_widget.setFocus(True)

        if resize_rows:
            self.table_widget.resizeRowsToContents()

        self._refresh_status_bar()

    # 設定資料庫資料
    def set_db_data_without_heading(self, sql, field, align=None):
        rows = self.database.select_record(sql)

        row_count = len(rows)
        self.table_widget.setRowCount(0)

        column_count = self.table_widget.columnCount()
        total_row = int(row_count / column_count)
        if row_count % column_count > 0:
            total_row += 1

        self.table_widget.setRowCount(total_row)
        for row_no in range(total_row):
            for col_no in range(column_count):
                index = (row_no * column_count) + col_no
                if index >= row_count:
                    break

                self.table_widget.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem(rows[index][field])
                )
                if align is not None:
                    self.table_widget.item(
                        row_no, col_no).setTextAlignment(
                        align | QtCore.Qt.AlignVCenter
                    )

        self.table_widget.resizeRowsToContents()
        self.table_widget.setCurrentCell(0, 0)
        # database.medical_record_rows.setFocus(True)
        
    # 設定資料庫資料
    def set_db_data_by_list(self, data_list, align=None):
        row_count = len(data_list)
        self.table_widget.setRowCount(0)

        column_count = self.table_widget.columnCount()
        total_row = int(row_count / column_count)
        if row_count % column_count > 0:
            total_row += 1

        self.table_widget.setRowCount(total_row)
        for row_no in range(total_row):
            for col_no in range(column_count):
                index = (row_no * column_count) + col_no
                if index >= row_count:
                    break

                self.table_widget.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem(data_list[index])
                )
                if align is not None:
                    self.table_widget.item(
                        row_no, col_no).setTextAlignment(
                        align | QtCore.Qt.AlignVCenter
                    )

        self.table_widget.resizeRowsToContents()
        self.table_widget.setCurrentCell(0, 0)
        # database.medical_record_rows.setFocus(True)

    def row_count(self):
        return self.table_widget.rowCount()

    # 取得欄位內容 by index no
    def field_value(self, field_index, row_no=None):
        if row_no is None:
            row_no = self.table_widget.currentRow()

        try:
            field_value = self.table_widget.item(row_no, field_index).text()
        except AttributeError:
            field_value = None

        return field_value

    def cell_widget(self, field_index):
        row = self.table_widget.currentRow()

        try:
            widget = self.table_widget.cellWidget(row, field_index).text()
        except AttributeError:
            widget = None

        return widget

    def set_cell_text_format(self, row_index, column_index, text_format, variable_type=None):
        item = self.table_widget.item(row_index, column_index)
        if item is None:
            return

        self.table_widget.setCurrentCell(row_index, column_index + 1)
        self.table_widget.setCurrentCell(row_index, column_index)

        try:
            if variable_type == 'float':
                value = float(item.text())
            else:
                value = int(item.text())
        except ValueError:
            self.set_item_text(row_index, column_index, None)
            return

        field_text = f'{value:{text_format}}'
        self.set_item_text(row_index, column_index, field_text)

    def set_item_text(self, row_no, col_no, item_text, align=QtCore.Qt.AlignRight):
        self.table_widget.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(item_text)
        )
        self.table_widget.item(row_no, col_no).setTextAlignment(align | QtCore.Qt.AlignVCenter)

    def set_row_color(self, row_index, color):
        for column in range(self.table_widget.columnCount()):
            self.table_widget.item(
                row_index, column).setForeground(color)

    def set_current_cell(self, row_no, col_no):
        self.table_widget.setCurrentCell(row_no, col_no)

    def current_row(self):
        return self.table_widget.currentRow()

    def find_error(self, field_no):
        self.table_widget.setFocus(True)
        for row_no in range(
                self.table_widget.currentRow()+1, self.table_widget.rowCount()):
            self.table_widget.setCurrentCell(row_no, field_no)
            error_message = string_utils.xstr(
                self.table_widget.item(row_no, field_no).text()
            )
            if error_message != '':
                break

        if (self.table_widget.currentRow() ==
                self.table_widget.rowCount() - 1):
            system_utils.show_message_box(
                QMessageBox.Information,
                '尋找錯誤',
                '<font size="5" color="red"><b>所有的錯誤資料均已瀏覽完畢.</b></font>',
                '請按確定鍵繼續.'
            )
            self.table_widget.setCurrentCell(0, field_no)

            # error_message = string_utils.xstr(
            #     database.table_widget_wait.item(0, field_no).text()
            # )
            #
            # if error_message == '':
            #     database.find_error(field_no)

    def set_dict(self, in_dict):
        self.table_widget.setRowCount(len(in_dict))
        self.table_widget.setAlternatingRowColors(True)

        for row_no, field in enumerate(in_dict):
            self.table_widget.setItem(
                row_no, 0,
                QtWidgets.QTableWidgetItem(string_utils.xstr(field))
            )
            self.table_widget.setItem(
                row_no, 1,
                QtWidgets.QTableWidgetItem(string_utils.xstr(in_dict[field]))
            )

            self.table_widget.item(
                row_no, 1).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )


class TableDragDropSorter(QtCore.QObject):
    def __init__(self, tableWidget):
        super().__init__(tableWidget)
        self.tableWidget = tableWidget
        
        # --- 設定必要的屬性 ---
        self.tableWidget.setDragEnabled(True)
        self.tableWidget.setAcceptDrops(True)
        self.tableWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.tableWidget.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.tableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableWidget.setDragDropOverwriteMode(False)

        # --- 關鍵修改在此 ---
        # 必須先把 viewport 存成 self 的屬性，eventFilter 才能讀得到
        self.viewport = self.tableWidget.viewport()
        self.viewport.installEventFilter(self)

    def eventFilter(self, source, event):
        if (source == self.tableWidget or
            source == self.viewport) and \
                event.type() == QtCore.QEvent.Drop:
            self.handle_drop_logic(self.tableWidget, event)
            return True

        return super().eventFilter(source, event)

    def handle_drop_logic(self, tableWidget, event):
        selection = tableWidget.selectedIndexes()
        if not selection:
            return

        source_row = selection[0].row()

        target_index = tableWidget.indexAt(event.pos())
        target_row = target_index.row()

        if target_row == -1:
            target_row = tableWidget.rowCount()

        if source_row == target_row:
            return

        tableWidget.insertRow(target_row)

        if source_row > target_row:
            real_source_row = source_row + 1
        else:
            real_source_row = source_row

        for col in range(tableWidget.columnCount()):
            item = tableWidget.item(real_source_row, col)
            if item:
                new_item = QtWidgets.QTableWidgetItem(item)
                tableWidget.setItem(target_row, col, new_item)

        tableWidget.removeRow(real_source_row)
        tableWidget.resizeRowsToContents()
