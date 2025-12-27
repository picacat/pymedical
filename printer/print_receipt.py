# -*- coding: UTF-8 -*-

from libs import printer_utils
from libs import number_utils
from libs import case_utils
from libs import string_utils


# 列印費用收據 2018.02.26
class PrintReceipt:
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

        try:
            self.print_dosage = args[4]
        except IndexError:
            self.print_dosage = True

        try:
            self.print_only_medicine_set2 = args[5]
        except IndexError:
            self.print_only_medicine_set2 = False

        if self.system_settings.field('費用收據不印處方') == 'Y':
            self.print_only_medicine_set2 = True

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
        if self.print_option == '健保收據':  # medical_record_list 列印註記健保費用收據
            printer_utils.print_ins_receipt(
                self, self.database, self.system_settings,
                self.case_key, print_type, self.print_option,
                print_dosage=self.print_dosage,
            )
            return

        selected_items = printer_utils.get_medicine_set_items(
            self.parent, self.database, self.system_settings, self.case_key, '收據', self.print_option)

        if not selected_items:
            return

        if self.print_option == '自費收據':  # medical_record_list 列印註記自費費用收據
            try:
                selected_items.remove('健保收據')
            except Exception:
                pass

        for item in selected_items:
            if item == '健保收據':
                rows = case_utils.get_dosage_row(self.database, self.case_key, 1)
                if len(rows) > 0 and \
                        self.print_option == '系統設定' and \
                        '本頁不印' in string_utils.xstr(rows[0]['Remark']):
                    continue
                
                note = case_utils.get_case_extend(self.database, self.case_key, '掛號費用')
                if note not in ['', None]:
                    print_note = True
                else:
                    print_note = False

                printer_utils.print_ins_receipt(
                    self, self.database, self.system_settings, self.case_key, print_type, self.print_option,
                    print_dosage=self.print_dosage, print_note=print_note
                )
            else:
                medicine_set = number_utils.get_integer(item.split('自費收據')[1]) + 1
                if self.print_only_medicine_set2 and medicine_set != 2:
                    continue
                
                rows = case_utils.get_dosage_row(self.database, self.case_key, medicine_set)
                if len(rows) > 0 and '本頁不印' in string_utils.xstr(rows[0]['Remark']):
                    continue

                printer_utils.print_self_receipt(
                    self, self.database, self.system_settings,
                    self.case_key, medicine_set, print_type, self.print_option,
                    print_dosage=self.print_dosage,
                )
