# 孕產照護 2021-09-21
# -*- coding: UTF-8 -*-

from PyQt5.QtWidgets import QInputDialog
from libs import string_utils


def set_case_label(row, label_case_date):
    try:
        case_date = row['CaseDate'].date()
    except Exception:
        case_date = ''

    name = string_utils.xstr(row['Name'])
    doctor = string_utils.xstr(row['Doctor'])
    label_case_date.setText(f"<b>門診日期: {case_date}  姓名: {name}  主治醫師: {doctor}</b>")


def copy_pregnant_data(parent, table_widget_past_pregnant, process_data):
    current_case_date = table_widget_past_pregnant.item(table_widget_past_pregnant.currentRow(), 2).text()

    items = []
    past_data = {}
    for row_no in range(table_widget_past_pregnant.rowCount()):
        case_date_item = table_widget_past_pregnant.item(row_no, 2)
        if case_date_item is None:
            continue

        case_date = case_date_item.text()
        if case_date == current_case_date:
            continue

        case_key = table_widget_past_pregnant.item(row_no, 1).text()
        past_data[case_date] = [case_key, case_date]
        items.append(past_data[case_date][1])

    case_date, copy = QInputDialog.getItem(parent, "拷貝過去資料", "請選擇拷貝哪一天的資料", items, 0, False)

    if not copy:
        return

    case_key = past_data[case_date][0]
    process_data(case_key, display_case_date_label=False)
