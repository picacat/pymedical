
# 資料庫修復 2019.07.15
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
import configparser

from libs import class_utils
from libs import ui_utils
from libs import system_utils


# 資料庫修復
class DialogDatabaseRepair(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogDatabaseRepair, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_DATABASE_REPAIR, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('關閉')
        self.table_widget_tables = class_utils.get_table_widget(
            self.ui.tableWidget_tables, self.database)
        self._set_table_width()

    def _set_table_width(self):
        width = [400, 200]
        self.table_widget_tables.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.pushButton_repair_tables.clicked.connect(self._repair_tables)
        pass

    def accepted_button_clicked(self):
        self._repair_tables()

    def _repair_tables(self):
        config = configparser.ConfigParser()
        config.read(self.database.CONFIG_FILE)
        database_name = config['db']['database']

        sql = f'''
            SELECT
                concat('repair table ', table_name, ';') AS repair_script
            FROM information_schema.tables
            WHERE
                table_schema = '{database_name}'
            ORDER BY repair_script
        '''
        rows = self.database.select_record(sql)
        self.ui.tableWidget_tables.setRowCount(len(rows))

        for row_no, row in enumerate(rows):
            repair_script = row['repair_script']
            results = self.database.select_record(repair_script)
            QtCore.QCoreApplication.processEvents()

            for result in results:
                result_row = [result['Table'].split('.')[1], result['Msg_text']]
                for col_no in range(len(result_row)):
                    self.ui.tableWidget_tables.setItem(
                        row_no, col_no,
                        QtWidgets.QTableWidgetItem(result_row[col_no])
                    )
