
# -*- coding: UTF-8 -*-

from libs import case_utils
from libs import printer_utils


# 列印藥袋 2023.02.19
class PrintPrescriptionBag:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        try:
            self.print_option = args[3]
        except IndexError:
            self.print_option = None

        self.ui = None

        self._set_ui()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        pass

    def print(self):
        self._ready_to_print('print')

    def preview(self):
        self._ready_to_print('preview')

    def _ready_to_print(self, print_type):
        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        for medicine_set in range(1, 3):
            pres_days = case_utils.get_pres_days(self.database, row['CaseKey'], medicine_set=medicine_set)
            if pres_days > 0:
                printer_utils.print_prescript_bag(
                    self, self.database, self.system_settings,
                    self.case_key, print_type, medicine_set, self.print_option
                )
