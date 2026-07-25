
# -*- coding: UTF-8 -*-

from libs import printer_utils
from libs import number_utils
from libs import case_utils
from libs import string_utils


# 列印處方箋 2018.02.26
class PrintPrescription:
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
        if self.print_option == '健保處方':  # medical_record_list 列印註記健保處方箋
            printer_utils.print_ins_prescript(
                self, self.database, self.system_settings,
                self.case_key, print_type, self.print_option
            )
            return

        selected_items = printer_utils.get_medicine_set_items(
            self.parent, self.database, self.system_settings, self.case_key, '處方', self.print_option)

        if not selected_items:
            return

        if self.print_option == '自費處方':  # medical_record_list 列印註記自費處方箋
            try:
                selected_items.remove('健保處方')
            except Exception:
                pass

        for item in selected_items:
            if item == '健保處方':
                rows = case_utils.get_dosage_row(self.database, self.case_key, 1)
                if len(rows) > 0 and '本頁不印' in string_utils.xstr(rows[0]['Remark']):
                    continue
                else:
                    printer_utils.print_ins_prescript(
                        self, self.database, self.system_settings,
                        self.case_key, print_type, self.print_option
                    )
            else:
                medicine_set = number_utils.get_integer(item.split('自費處方')[1]) + 1

                rows = case_utils.get_dosage_row(self.database, self.case_key, medicine_set)
                if len(rows) > 0 and '本頁不印' in string_utils.xstr(rows[0]['Remark']):
                    continue

                printer_utils.print_self_prescript(
                    self, self.database, self.system_settings,
                    self.case_key, medicine_set, print_type, self.print_option
                )
