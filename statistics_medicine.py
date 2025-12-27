
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore

from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import export_utils
from libs import dialog_utils
from libs import module_utils
from libs import number_utils


# 用藥統計 2019.08.02
class StatisticsMedicine(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsMedicine, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.dialog_setting = {
            "dialog_executed": False,
            "start_date": None,
            "end_date": None,
            "ins_type": None,
            "therapist": None,
        }

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_MEDICINE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_form)
        self.ui.action_open_dialog.triggered.connect(self.open_dialog)
        self.ui.action_export_excel.triggered.connect(self._export_to_excel)
        self.ui.action_export_detail_excel.triggered.connect(self._export_detail_to_excel)
        self.ui.action_export_excel_all.triggered.connect(self._export_to_excel_all)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_statistics_therapist(
            self, self.database, self.system_settings, '用藥統計', '醫師',
        )

        if self.dialog_setting['dialog_executed']:
            dialog.ui.dateEdit_start_date.setDate(self.dialog_setting['start_date'])
            dialog.ui.dateEdit_end_date.setDate(self.dialog_setting['end_date'])

            if self.dialog_setting['ins_type'] == '全部':
                dialog.ui.radioButton_all.setChecked(True)
            elif self.dialog_setting['ins_type'] == '健保':
                dialog.ui.radioButton_ins.setChecked(True)
            elif self.dialog_setting['ins_type'] == '自費':
                dialog.ui.radioButton_self.setChecked(True)

            dialog.ui.comboBox_therapist.setCurrentText(self.dialog_setting['therapist'])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        start_date = dialog.start_date()
        end_date = dialog.end_date()
        ins_type = dialog.ins_type()
        therapist = dialog.ui.comboBox_therapist.currentText()

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['start_date'] = dialog.ui.dateEdit_start_date.date()
        self.dialog_setting['end_date'] = dialog.ui.dateEdit_end_date.date()
        self.dialog_setting['ins_type'] = ins_type
        self.dialog_setting['therapist'] = therapist

        dialog.deleteLater()
        self._set_tab_widget(start_date, end_date, ins_type, therapist)

    def _get_total_discount_fee(self, ins_type, start_date, end_date, doctor):
        doctor_type_condition = f' AND Doctor = "{doctor}"' if doctor != '全部' else ''
        sql = f'''
            SELECT SUM(DiscountFee) AS total_discount_fee FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}"
                {doctor_type_condition}
        '''
        rows = self.database.select_record(sql)
        if rows:
            total_discount_fee = number_utils.get_integer(rows[0]['total_discount_fee'])
        else:
            total_discount_fee = 0
            
        return total_discount_fee

    def _set_tab_widget(self, start_date, end_date, ins_type, doctor):
        total_discount_fee = self._get_total_discount_fee(ins_type, start_date, end_date, doctor)
        self.ui.statusbar.showMessage(
            f' 統計期間: 從 {start_date[:10]} 至 {end_date[:10]} 保險: {ins_type} 醫師: {doctor} 總折扣金額: {total_discount_fee}'
        )

        # ins_type_condition = f' AND InsType = "{ins_type}"' if ins_type != '全部' else ''
        if ins_type == '健保':
            ins_type_condition = 'AND MedicineSet = 1'
        elif ins_type == '自費':
            ins_type_condition = 'AND MedicineSet >=2'
        else:
            ins_type_condition = ''

        doctor_type_condition = f' AND Doctor = "{doctor}"' if doctor != '全部' else ''

        sql = f'''
            SELECT MedicineType FROM prescript
                LEFT JOIN cases ON prescript.CaseKey = cases.CaseKey
            WHERE
                cases.CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                MedicineType IS NOT NULL AND
                MedicineType NOT IN ("穴道")
                {ins_type_condition}
                {doctor_type_condition}
            GROUP BY MedicineType
            ORDER BY FIELD(MedicineType, "檢驗", "處置", "高貴", "外用", "水藥", "複方", "單方") DESC
        '''
        rows = self.database.select_record(sql)

        self.ui.tabWidget_statistics_medicine.clear()
        for row in rows:
            self._add_statistic_medicine_sales(
                start_date, end_date, ins_type, doctor, string_utils.xstr(row['MedicineType'])
            )

    # 用藥統計內容
    def _add_statistic_medicine_sales(self, start_date, end_date, ins_type, doctor, medicine_type):
        self.tab_statistics_medicine_sales = module_utils.get_statistics_medicine_sales(
            self, self.database, self.system_settings, start_date, end_date, ins_type, doctor, medicine_type,
        )
        self.tab_statistics_medicine_sales.start_calculate()
        self.ui.tabWidget_statistics_medicine.addTab(self.tab_statistics_medicine_sales, medicine_type)

    def _export_to_excel(self):
        current_index = self.ui.tabWidget_statistics_medicine.currentIndex()
        current_tab = self.ui.tabWidget_statistics_medicine.widget(current_index)

        current_tab.export_to_excel()

    def _export_detail_to_excel(self):
        current_index = self.ui.tabWidget_statistics_medicine.currentIndex()
        current_tab = self.ui.tabWidget_statistics_medicine.widget(current_index)

        current_tab.export_detail_to_excel()

    def _export_to_excel_all(self):
        start_date = self.dialog_setting['start_date'].toString('yyyy-MM-dd')
        end_date = self.dialog_setting['end_date'].toString('yyyy-MM-dd')
        doctor = self.dialog_setting['therapist']
        if doctor == '全部':
            doctor = ''

        options = QtWidgets.QFileDialog.Options()
        excel_file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.parent,
            "匯出用藥統計",
            f'{start_date}至{end_date}{doctor}全部用藥統計表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_tab_widget_to_excel(
            excel_file_name, self.ui.tabWidget_statistics_medicine, None, [2, 4, 5, 6]
        )

        system_utils.show_message_box(
            QtWidgets.QMessageBox.Information,
            '資料匯出完成',
            f'<h3>用藥統計統計檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )
