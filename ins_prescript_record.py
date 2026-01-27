# -*- coding: utf-8 -*-

import datetime
import json

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton, QTableView
from libs import (case_utils, class_utils, db_utils, dialog_utils, nhi_utils,
                  number_utils, patient_utils, personnel_utils,
                  prescript_utils, stock_utils, string_utils, system_utils,
                  ui_utils)


# 輸入健保處方 2018.04.14
class InsPrescriptRecord(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(InsPrescriptRecord, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.medicine_set = args[3]
        self.call_from = args[4]
        self.vegetarian_warned = False
        self.packages = None
        self.pres_days = None
        self.instruction = None

        if self.parent.medical_record is None:
            self.case_date = None
            self.diag_date = None
            self.course = 0
        else:
            self.case_date = self.parent.medical_record['CaseDate']
            self.diag_date = self.parent.medical_record['DiagDate']
            self.course = number_utils.get_integer(self.parent.medical_record['Continuance'])

        self.copy_from = None
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.signal_off = True
        self.dosage_limitation = number_utils.get_integer(self.system_settings.field('劑量上限'))
        self.check_total_dosage_event = self.system_settings.field('健保處方給藥劑量上限檢查時機')
        self.check_total_costs_event = self.system_settings.field('健保用藥成本上限檢查時機')
        self.no_ins_cost = self.system_settings.field('不要顯示健保用藥成本')
        self.no_massage = self.system_settings.field('不申報傷科治療')
        self.is_vegetarian = False
        vegetarian = patient_utils.get_patient_extension_settings(
            self.database, self.parent.patient_key, '吃素')
        if vegetarian == 'Y':
            self.is_vegetarian = True

        self.popup_menu = self.system_settings.field('刪除處方啟用彈出式選單')
        self.ins_drug_fee_limitation = number_utils.get_integer(self.system_settings.field('健保用藥成本上限'))
        if self.system_settings.field('詞庫視窗顯示方式') == '彈出式視窗':
            self.duplicate_warning = False
        else:
            self.duplicate_warning = True

        person_edit_mode = personnel_utils.get_person_field_value(self.database, self.user_name, 'IME')
        if person_edit_mode == '編輯模式':
            self.prescript_edit_mode = 'Y'
        else:
            self.prescript_edit_mode = self.system_settings.field('處方輸入編輯模式')

        self._set_ui()
        self._set_signal()

        self._read_cases()
        self._read_prescript()
        self.signal_off = False

        self._set_permission()

        self.ask_diag_only = False
        if self.parent.tab_registration is None:
            treat_type = None
        else:
            treat_type = self.parent.tab_registration.ui.comboBox_treat_type.currentText()

        if treat_type == '醫療諮詢':
            self.ui.radioButton_diag.setChecked(True)
            self._set_prescript_enabled(False)
        elif treat_type == '居家醫療':
            self.ui.checkBox_pharmacy.setChecked(False)
            self.ui.checkBox_pharmacy.setEnabled(False)
            self.parent.tab_registration.ui.comboBox_pharmacy_type.setEnabled(False)
            self._set_pharmacy()

        self.ask_diag_only = True

        self.default_moderate_acupuncture_time, self.default_highly_acupuncture_time = \
            prescript_utils.get_default_complicated_acupuncture_time(self.system_settings)
        self.default_moderate_massage_time, self.default_highly_massage_time = \
            prescript_utils.get_default_complicated_massage_time(self.system_settings)

        self.medicine_sort = self.system_settings.field('處方排序')

    def _set_prescript_enabled(self, enabled):
        self.ui.tableWidget_prescript.setEnabled(enabled)
        self.ui.groupBox_treat.setEnabled(enabled)
        self.ui.comboBox_package.setEnabled(enabled)
        self.ui.comboBox_pres_days.setEnabled(enabled)
        self.ui.comboBox_instruction.setEnabled(enabled)
        self.ui.comboBox_treatment.setEnabled(enabled)
        self.ui.toolButton_dictionary.setEnabled(enabled)
        self.ui.toolButton_compound_json.setEnabled(enabled)
        self.ui.label_package.setEnabled(enabled)
        self.ui.label_pres_days.setEnabled(enabled)
        self.ui.label_instruction.setEnabled(enabled)
        self.ui.checkBox_pharmacy.setEnabled(enabled)
        self.ui.toolButton_instruction.setEnabled(enabled)
        self.ui.toolButton_insert_compound.setEnabled(enabled)

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INS_PRESCRIPT_RECORD, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_prescript = class_utils.get_table_widget(self.ui.tableWidget_prescript, self.database)
        self.table_widget_prescript.set_column_hidden([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.table_widget_prescript.set_parent(self.parent.parent)
        self.table_widget_treat = class_utils.get_table_widget(self.ui.tableWidget_treat, self.database)
        self.table_widget_treat.set_column_hidden([0, 1, 2, 3, 4, 5, 6, 7])

        self.ui.tableWidget_prescript.setDragEnabled(True)
        self.ui.tableWidget_prescript.setAcceptDrops(True)
        self.ui.tableWidget_treat.setDragEnabled(True)
        self.ui.tableWidget_treat.setAcceptDrops(True)

        if self.system_settings.field('處方劑量欄位可以排序') == 'Y':
            self.ui.tableWidget_prescript.horizontalHeader().setSectionsClickable(True)
        else:
            self.ui.tableWidget_prescript.horizontalHeader().setSectionsClickable(False)

        # self.ui.radioButton_medicine.setStyleSheet("""
        #     QRadioButton::checked {
        #         color: red;
        #         font-weight: bold;
        #     }
        # """)
        self.ui.radioButton_diag.setStyleSheet("""
            QRadioButton::checked {
                color: red;
                font-weight: bold;
            }
        """)

        if self.system_settings.field('病歷主訴大字體') == 'Y':
            self.ui.tableWidget_prescript.setStyleSheet(self.ui.tableWidget_prescript.styleSheet() + 'font-size: 24px;')

        self.ui.label_total_dosage_setting.setVisible(False)
        self.ui.doubleSpinBox_total_dosage.setVisible(False)
        self.ui.checkBox_no_pharmacy.setVisible(False)
        if self.system_settings.field('比例法劑量') == 'Y':
            self.ui.tableWidget_prescript.setHorizontalHeaderItem(
                13, QtWidgets.QTableWidgetItem('比例')
            )
            self.ui.label_total_dosage_setting.setVisible(True)
            self.ui.doubleSpinBox_total_dosage.setVisible(True)
            self.ui.checkBox_no_pharmacy.setVisible(True)
            if self.call_from == '醫師看診作業' and self.system_settings.field('健保處方預設不調劑') == 'Y':
                self.ui.checkBox_no_pharmacy.setChecked(True)

        self._set_table_width()
        self._set_combo_box()
        self.set_treat_ui()

        self.ui.tableWidget_prescript.viewport().installEventFilter(self)
        self.ui.tableWidget_treat.viewport().installEventFilter(self)

        try:
            vegetarian = patient_utils.get_patient_extension_settings(
                self.database, self.parent.medical_record['PatientKey'], '吃素')
            if vegetarian == 'Y':
                item = QtWidgets.QTableWidgetItem("處方名稱 (病人吃素)")
                item.setForeground(QtGui.QBrush(QtGui.QColor("red")))  # 設定字體顏色為紅色

                self.ui.tableWidget_prescript.setHorizontalHeaderItem(
                    prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'], item)
        except Exception:
            pass

    # 滑鼠右鍵刪除處方
    def eventFilter(self, source, event):
        if self.popup_menu == 'Y':
            return False

        if event.type() == QtCore.QEvent.MouseButtonRelease and \
                event.button() == QtCore.Qt.RightButton:
            if source is self.ui.tableWidget_prescript.viewport():
                self.remove_medicine()
            elif source is self.ui.tableWidget_treat.viewport():
                self.remove_treat()

        try:
            return super(InsPrescriptRecord, self).eventFilter(source, event)
        except TypeError:
            return False

    def _get_start_treatment(self):
        treatment = None

        start_date = self.case_date.date()
        patient_key = self.parent.medical_record['PatientKey']
        card = self.parent.medical_record['Card']

        last_month = (datetime.date(start_date.year, start_date.month, 1) - datetime.timedelta(1)).replace(day=1)
        case_start_date = f'{last_month} 00:00:00'
        case_end_date = f'{start_date} 00:00:00'

        sql = f'''
            SELECT Treatment FROM cases
            WHERE
                (PatientKey = {patient_key}) AND
                (CaseDate BETWEEN "{case_start_date}" AND "{case_end_date}") AND
                (InsType = "健保") AND
                (Continuance = 1) AND
                (Card = "{card}")
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            treatment = string_utils.xstr(row['Treatment'])

        return treatment

    def _get_treatment_model(self):
        if self.case_key is None:
            start_date = nhi_utils.INS_TREAT_2021_DATE
        else:
            start_date = case_utils.get_course_start_date(
                self.database, self.parent.medical_record['PatientKey'], self.case_date,
                self.parent.medical_record['Card'],
                self.parent.medical_record['Continuance'],
            )

        ins_treat_list = nhi_utils.get_ins_treat_selection_list(start_date)
        model = QtGui.QStandardItemModel()
        model.appendRow(QtGui.QStandardItem(None))

        # case_date = self.parent.medical_record['CaseDate']
        # patient_key = self.parent.medical_record['PatientKey']
        # card = self.parent.medical_record['Card']
        # course = self.parent.medical_record['Continuance']

        # first_treatment = registration_utils.get_first_course_treatment(
        #     self.database, self.system_settings, case_date, patient_key, card, course
        # )

        primary_treatment, secondary_treatment = case_utils.extract_treatment(
            self.parent.medical_record['Treatment'])
        for treatment in ins_treat_list:
            ins_code = nhi_utils.TREAT_DICT[treatment]

            if self.no_massage == 'Y':
                if (primary_treatment in [None, ''] or
                    primary_treatment not in [None, ''] and '傷科' not in primary_treatment) and \
                        ins_code[0] not in ['D']:  # 非針灸不顯示
                    continue

            if self.course >= 2:
                if ins_code in nhi_utils.TREAT_COURSE_2_EXCLUDE:
                    continue

                # if first_treatment in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT and \
                #         ins_code in nhi_utils.COMPLICATED_ACUPUNCTURE_CODE + nhi_utils.COMPLICATED_MASSAGE_CODE:
                #     continue
            else:
                if ins_code in nhi_utils.TREAT_COURSE_1_EXCLUDE:
                    continue

            sql = f'''
                SELECT Amount FROM charge_settings
                WHERE
                    InsCode = "{ins_code}"
            '''
            rows = self.database.select_record(sql)
            fee = 0 if len(rows) <= 0 else number_utils.get_integer(rows[0]['Amount'])

            ins_fee_item = QtGui.QStandardItem(string_utils.xstr(fee))
            ins_fee_item.setTextAlignment(QtCore.Qt.AlignRight)
            model.appendRow([
                QtGui.QStandardItem(ins_code),
                QtGui.QStandardItem(treatment),
                ins_fee_item,
            ])

        model.setHeaderData(0, QtCore.Qt.Horizontal, '代碼')
        model.setHeaderData(1, QtCore.Qt.Horizontal, '處置項目')
        model.setHeaderData(2, QtCore.Qt.Horizontal, '點數')

        for row_no in range(1, model.rowCount()):
            index = model.index(row_no, 0)
            treat_code = model.data(index)

            if 'B41' <= treat_code <= 'B49':
                color = QtGui.QBrush(QtCore.Qt.darkMagenta)
            elif 'B51' <= treat_code <= 'B59':
                color = QtGui.QBrush(QtCore.Qt.darkGreen)
            elif 'B61' <= treat_code <= 'B69':
                color = QtGui.QBrush(QtCore.Qt.darkRed)
            elif 'D01' <= treat_code <= 'D99':
                color = QtGui.QBrush(QtCore.Qt.darkMagenta)
            elif 'E01' <= treat_code <= 'E08':
                color = QtGui.QBrush(QtCore.Qt.darkGreen)
            elif 'F01' <= treat_code <= 'F99':
                color = QtGui.QBrush(QtCore.Qt.darkBlue)
            else:
                color = QtGui.QBrush(QtCore.Qt.darkRed)

            for col_no in range(3):
                model.setData(
                    model.index(row_no, col_no),
                    color,
                    QtCore.Qt.ForegroundRole
                )

        return model

    def _get_treatment_view(self, combobox_treatment):
        view = QTableView(combobox_treatment)

        view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        view.setAlternatingRowColors(True)
        view.setFixedWidth(450)

        return view

    def set_treat_ui(self):
        model = self._get_treatment_model()
        view = self._get_treatment_view(self.ui.comboBox_treatment)

        self.ui.comboBox_treatment.setModel(model)
        self.ui.comboBox_treatment.setModelColumn(1)
        self.ui.comboBox_treatment.setView(view)
        view.setColumnWidth(0, 50)
        view.setColumnWidth(1, 300)
        view.setColumnWidth(2, 60)

        self.ui.tableWidget_treat.setRowCount(0)
        self.ui.comboBox_second_treatment.setVisible(False)

    def _set_combo_box(self):
        ui_utils.set_combo_box(self.ui.comboBox_package, nhi_utils.PACKAGE, None)
        ui_utils.set_combo_box(self.ui.comboBox_pres_days, nhi_utils.PRESDAYS, None)
        ui_utils.set_instruction_combo_box(self.database, self.ui.comboBox_instruction)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_add_medicine.clicked.connect(lambda: self.append_null_medicine(insert_row_no=None))
        self.ui.toolButton_remove_medicine.clicked.connect(self.remove_medicine)
        self.ui.toolButton_add_treat.clicked.connect(self.append_null_treat)
        self.ui.toolButton_remove_treat.clicked.connect(self.remove_treat)

        self.ui.toolButton_dictionary.clicked.connect(self.open_medicine_dictionary)
        self.ui.toolButton_compound_json.clicked.connect(self._open_dialog_compound_json)

        self.ui.toolButton_dosage.clicked.connect(self._open_dosage)
        self.ui.toolButton_treat_dictionary.clicked.connect(self._open_treat_dictionary)
        self.ui.toolButton_set_prescript_remark.clicked.connect(self._set_prescript_remark)

        self.ui.toolButton_acupuncture_point.clicked.connect(self._show_acupuncture_point)
        self.ui.toolButton_show_costs.clicked.connect(self._show_costs)
        self.ui.toolButton_medicine_info.clicked.connect(self._show_medicine_description)
        self.ui.toolButton_open_medicine_library.clicked.connect(self._open_medicine_library)
        self.ui.toolButton_treat_info.clicked.connect(self._show_treat_description)
        self.ui.toolButton_clear_medical_record.clicked.connect(self._clear_medical_record)
        self.ui.toolButton_copy.clicked.connect(self._copy_prescript)
        self.ui.toolButton_copy_to_append.clicked.connect(self._copy_to_append_prescript)
        self.ui.toolButton_clear_medicine.clicked.connect(lambda: self._clear_medicine(warning=True))
        self.ui.toolButton_clear_treat.clicked.connect(lambda: self._clear_treat(warning=True))

        self.ui.toolButton_complicated_acupuncture.clicked.connect(self._combo_box_treat_changed)
        self.ui.toolButton_insert_compound.clicked.connect(self._insert_compound)

        self.ui.toolButton_set_treat_time.clicked.connect(self._open_treat_time_dialog)
        self.ui.toolButton_set_treat_position.clicked.connect(self._open_treat_position_dialog)
        self.ui.toolButton_set_treat_auxiliary.clicked.connect(self._open_treat_auxiliary_dialog)
        self.ui.toolButton_instruction.clicked.connect(self._set_instruction)

        self.ui.comboBox_pres_days.currentTextChanged.connect(self.pres_days_changed)
        self.ui.comboBox_package.currentTextChanged.connect(self.package_changed)
        self.ui.comboBox_instruction.currentTextChanged.connect(self.instruction_changed)

        self.ui.tableWidget_prescript.itemChanged.connect(self._prescript_item_changed)
        self.ui.tableWidget_prescript.itemSelectionChanged.connect(self._prescript_item_selection_changed)
        self.ui.tableWidget_prescript.doubleClicked.connect(self._open_prescript_dialog)

        self.ui.comboBox_treatment.currentTextChanged.connect(self._combo_box_treat_changed)
        self.ui.comboBox_second_treatment.currentTextChanged.connect(self._combo_box_second_treat_changed)

        self.ui.tableWidget_prescript.keyPressEvent = self._table_widget_prescript_key_press
        self.ui.tableWidget_treat.keyPressEvent = self._table_widget_treat_key_press
        self.ui.tableWidget_prescript.cellClicked.connect(self._prescript_cell_clicked)
        self.ui.tableWidget_treat.cellClicked.connect(self._prescript_cell_clicked)
        self.ui.tableWidget_prescript.dropEvent = self.prescript_drop_event
        self.ui.tableWidget_treat.dropEvent = self.treat_drop_event

        self.ui.checkBox_pharmacy.clicked.connect(self._set_pharmacy)
        self.ui.comboBox_package.keyPressEvent = self._combo_box_package_key_press
        self.ui.comboBox_pres_days.keyPressEvent = self._combo_box_pres_days_key_press
        self.ui.doubleSpinBox_total_dosage.valueChanged.connect(self._total_dosage_value_changed)
        # self.ui.groupBox_prescript.toggled.connect(self._group_box_prescript_toggled)
        self.ui.radioButton_medicine.clicked.connect(self._set_free_diag)
        self.ui.radioButton_diag.clicked.connect(self._set_free_diag)

        if self.popup_menu == 'Y':
            self.ui.tableWidget_prescript.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        self.ui.tableWidget_prescript.customContextMenuRequested.connect(self._show_medicine_context_menu)
        self.ui.checkBox_print_receipt.clicked.connect(self._print_receipt_clicked)

    def _show_medicine_context_menu(self, pos):
        menu = QtWidgets.QMenu()
        menu.addAction(ui_utils.ICON_REMOVE, '刪除處方', self.remove_medicine)
        menu.addAction(ui_utils.ICON_ADD, '插入處方', self.insert_medicine)
        menu.addSeparator()
        menu.addAction(ui_utils.ICON_REDO, '拷貝健保處方至自費1', self._copy_prescript)
        menu.addAction(ui_utils.ICON_FINISH, '拷貝健保處方至新增自費頁', self._copy_to_append_prescript)
        menu.addSeparator()
        menu.addAction(ui_utils.ICON_DICT, '顯示藥品詞庫', self.open_medicine_dictionary)
        menu.addAction(ui_utils.ICON_HELP, '顯示藥品說明', self._show_medicine_description)
        menu.addAction(ui_utils.ICON_INFO, '顯示用藥成本', self._show_costs)
        menu.addSeparator()
        menu.addAction(ui_utils.ICON_CLEAR, '刪除全部處方', self._clear_medicine)

        font = QtGui.QFont('微軟正黑體', 14)
        font.setBold(True)
        menu.setFont(font)
        menu.exec_(self.ui.tableWidget_prescript.viewport().mapToGlobal(pos))

    def _toggle_medicine_tool_buttons(self, toggle):
        self.ui.toolButton_add_medicine.setEnabled(toggle)
        self.ui.toolButton_remove_medicine.setEnabled(toggle)
        self.ui.toolButton_clear_medicine.setEnabled(toggle)
        self.ui.toolButton_show_costs.setEnabled(toggle)
        self.ui.toolButton_dictionary.setEnabled(toggle)
        self.ui.toolButton_dosage.setEnabled(toggle)
        self.ui.toolButton_copy.setEnabled(toggle)
        self._prescript_item_selection_changed()

    def _toggle_treat_tool_buttons(self, toggle):
        self.ui.toolButton_add_treat.setEnabled(toggle)
        self.ui.toolButton_remove_treat.setEnabled(toggle)
        self.ui.toolButton_clear_treat.setEnabled(toggle)
        self.ui.toolButton_treat_dictionary.setEnabled(toggle)

        self.ui.toolButton_set_treat_time.setEnabled(toggle)
        self.ui.toolButton_set_treat_position.setEnabled(toggle)
        self.ui.toolButton_set_treat_auxiliary.setEnabled(toggle)

        self.ui.toolButton_acupuncture_point.setEnabled(toggle)

    def _set_free_diag(self):
        if self.ui.radioButton_medicine.isChecked():
            self.parent.tab_registration.ui.comboBox_treat_type.setCurrentText('內科')
            self._set_prescript_enabled(True)
            return

        if self.course >= 2:
            system_utils.show_message_box(
                QMessageBox.Critical,
                '不可設為醫療諮詢(問診)',
                '<font size="5" color="red"><b>療程第二次以上不可設定為醫療諮詢(問診).</b></font>',
                '療程第二次以上設為醫療諮詢(問診)無法申請健保費用.'
            )
            self.ui.radioButton_medicine.setChecked(True)
            self.ui.radioButton_medicine.setStyleSheet('color: red;')
            self._set_prescript_enabled(True)
            return

        if not self.ask_diag_only:
            return

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('醫療諮詢')
        msg_box.setText(
            '''
                <font size="5" color="red">
                  <b>
                    確定改為醫療諮詢 (問診) 嗎?
                  </b>
                </font>
            ''',
        )
        msg_box.setInformativeText("改為醫療諮詢(問診)後, 所有的內服藥及處置均會清除.")
        msg_box.addButton(QPushButton("是"), QMessageBox.YesRole)
        msg_box.addButton(QPushButton("否"), QMessageBox.NoRole)
        answer = msg_box.exec_()
        if answer == QMessageBox.RejectRole:
            self.ui.radioButton_medicine.setChecked(True)
            self._set_prescript_enabled(True)
            return

        self._set_diag_only()
        self._set_prescript_enabled(False)

    # 設定問診
    def _set_diag_only(self):
        self._clear_medicine()
        self._clear_treat()
        self.parent.tab_registration.ui.comboBox_treat_type.setCurrentText('醫療諮詢')

    def _combo_box_package_key_press(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Return or key == QtCore.Qt.Key_Enter:
            self.ui.comboBox_pres_days.setFocus(True)

        return QtWidgets.QComboBox.keyPressEvent(self.ui.comboBox_package, event)

    def _combo_box_pres_days_key_press(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Return or key == QtCore.Qt.Key_Enter:
            self.ui.comboBox_instruction.setFocus(True)

        return QtWidgets.QComboBox.keyPressEvent(self.ui.comboBox_pres_days, event)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(self.database, '醫師看診作業', '病歷登錄', self.user_name) == 'Y':
            return

        if personnel_utils.get_permission(self.database, '病歷資料', '病歷修正', self.user_name) == 'Y':
            return

        self.ui.toolButton_clear_medical_record.setEnabled(False)
        self.ui.toolButton_add_medicine.setEnabled(False)
        self.ui.toolButton_remove_medicine.setEnabled(False)
        self.ui.toolButton_clear_medicine.setEnabled(False)
        self.ui.toolButton_copy.setEnabled(False)
        self.ui.toolButton_dictionary.setEnabled(False)
        self.ui.toolButton_dosage.setEnabled(False)
        self.ui.toolButton_show_costs.setEnabled(False)
        self.ui.toolButton_medicine_info.setEnabled(False)
        self.ui.toolButton_open_medicine_library.setEnabled(False)

        self.ui.comboBox_package.setEnabled(False)
        self.ui.comboBox_pres_days.setEnabled(False)
        self.ui.comboBox_instruction.setEnabled(False)

        self.ui.toolButton_add_treat.setEnabled(False)
        self.ui.toolButton_remove_treat.setEnabled(False)
        self.ui.toolButton_clear_treat.setEnabled(False)
        self.ui.toolButton_treat_dictionary.setEnabled(False)

        self.ui.toolButton_set_treat_time.setEnabled(False)
        self.ui.toolButton_set_treat_position.setEnabled(False)
        self.ui.toolButton_set_treat_auxiliary.setEnabled(False)

        self.ui.toolButton_acupuncture_point.setEnabled(False)

        self.ui.tableWidget_prescript.setEnabled(False)
        self.ui.tableWidget_treat.setEnabled(False)

        self.ui.checkBox_pharmacy.setEnabled(False)

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            for col_no in range(self.ui.tableWidget_prescript.columnCount()):
                item = self.ui.tableWidget_prescript.item(row_no, col_no)
                if item is None:
                    continue

                item.setForeground(QtGui.QColor('black'))

        for row_no in range(self.ui.tableWidget_treat.rowCount()):
            for col_no in range(self.ui.tableWidget_treat.columnCount()):
                item = self.ui.tableWidget_treat.item(row_no, col_no)
                if item is None:
                    continue

                item.setForeground(QtGui.QColor('black'))

    def prescript_drop_event(self, event):
        current_table_widget = event.source()

        source_row = current_table_widget.currentRow()
        target_item = current_table_widget.itemAt(event.pos())

        if target_item is None:
            target_row = current_table_widget.rowCount()
        else:
            target_row = target_item.row()

        medicine_name = current_table_widget.item(
            source_row, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']
        )
        if medicine_name is None:
            return

        medicine_name = medicine_name.text()
        if medicine_name == '':
            return

        prescript_row = []
        for col_no in range(current_table_widget.columnCount()):
            prescript_row.append(current_table_widget.item(source_row, col_no))

        current_table_widget.insertRow(target_row)
        for col_no in range(len(prescript_row)):
            current_table_widget.setItem(
                target_row, col_no,
                QtWidgets.QTableWidgetItem(prescript_row[col_no])
            )
            self._adjust_prescript_align(target_row, col_no)

        # medicine_key_item = prescript_row[prescript_utils.INS_PRESCRIPT_COL_NO['MedicineKey']]
        # if medicine_key_item is not None:
        #     database._add_prescript_info_button(target_row, medicine_key_item.text())

        if target_row > source_row:
            remove_row = source_row
        else:
            remove_row = source_row + 1

        current_table_widget.removeRow(remove_row)
        current_table_widget.resizeRowsToContents()

        if target_row < source_row:
            move_row = target_row
        else:
            move_row = target_row - 1

        current_table_widget.setCurrentCell(move_row, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'])
        self._set_total_dosage()
        self._set_total_cost()

    def treat_drop_event(self, event):
        table_widget = event.source()

        source_row = table_widget.currentRow()
        target_item = table_widget.itemAt(event.pos())

        if target_item is None:
            target_row = table_widget.rowCount()
        else:
            target_row = target_item.row()

        treat_name = table_widget.item(
            source_row, prescript_utils.INS_TREAT_COL_NO['MedicineName']
        )

        if treat_name is None:
            return

        treat_name = treat_name.text()
        if treat_name == '':
            return

        treat_row = []
        for col_no in range(table_widget.columnCount()):
            treat_row.append(table_widget.item(source_row, col_no))

        table_widget.insertRow(target_row)
        for col_no in range(len(treat_row)):
            table_widget.setItem(
                target_row, col_no,
                QtWidgets.QTableWidgetItem(treat_row[col_no])
            )

        if target_row > source_row:
            remove_row = source_row
        else:
            remove_row = source_row + 1

        table_widget.removeRow(remove_row)
        table_widget.resizeRowsToContents()

        if target_row < source_row:
            move_row = target_row
        else:
            move_row = target_row - 1

        table_widget.setCurrentCell(move_row, prescript_utils.INS_TREAT_COL_NO['MedicineName'])

    def _table_widget_prescript_key_press(self, event):
        if self.system_settings.field('不要自動切換輸入法') == 'Y':
            pass
        else:
            system_utils.set_keyboard_layout('英文')

        key = event.key()
        current_row = self.ui.tableWidget_prescript.currentRow()
        current_column = self.ui.tableWidget_prescript.currentColumn()

        if key == QtCore.Qt.Key_Delete or key == QtCore.Qt.Key_F5:
            self.remove_medicine()
        elif key == QtCore.Qt.Key_Insert:
            self.insert_medicine()
        elif key == QtCore.Qt.Key_Up:
            if self.ui.tableWidget_prescript.item(
                    current_row, prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptKey']) is None:
                self.ui.tableWidget_prescript.removeRow(current_row)
                return

            if self.ui.tableWidget_prescript.currentColumn() == prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']:
                self._set_dosage_format(current_row, current_column)
                self.check_total_dosage(current_row)
                self.check_total_costs(current_row)
            # elif current_column == prescript_utils.INS_PRESCRIPT_COL_NO['Instruction']:
            #     self._set_dosage_percent()
        elif key == QtCore.Qt.Key_Down:
            if current_row == self.ui.tableWidget_prescript.rowCount() - 1 and \
                    self.ui.tableWidget_prescript.item(
                        current_row, prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptKey']) is not None:
                self.append_null_medicine()

            if self.ui.tableWidget_prescript.currentColumn() == prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']:
                self._set_dosage_format(current_row, current_column)
                self.check_total_dosage(current_row)
                self.check_total_costs(current_row)
            # elif current_column == prescript_utils.INS_PRESCRIPT_COL_NO['Instruction']:
            #     self._set_dosage_percent()
        elif key == QtCore.Qt.Key_Return or key == QtCore.Qt.Key_Enter:
            if current_column == prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']:
                self.open_medicine_dialog()
            elif current_column == prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']:
                self._set_dosage_format(current_row, current_column)
                if current_row < self.ui.tableWidget_prescript.rowCount() - 1:
                    self.ui.tableWidget_prescript.setCurrentCell(
                        current_row + 1,
                        prescript_utils.INS_PRESCRIPT_COL_NO['Dosage'],
                    )
                elif current_row == self.ui.tableWidget_prescript.rowCount() - 1:
                    self.append_null_medicine()
                    self.ui.tableWidget_prescript.setCurrentCell(
                        current_row+1,
                        prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'],
                    )
                #     self.ui.comboBox_package.setFocus(True)

                self.check_total_dosage(current_row)
                self.check_total_costs(current_row)
            elif current_column == prescript_utils.INS_PRESCRIPT_COL_NO['Instruction']:
                if current_row < self.ui.tableWidget_prescript.rowCount() - 1:
                    self.ui.tableWidget_prescript.setCurrentCell(
                        current_row + 1,
                        prescript_utils.INS_PRESCRIPT_COL_NO['Instruction'],
                    )
                elif current_row == self.ui.tableWidget_prescript.rowCount() - 1:
                    self.append_null_medicine()
                    self.ui.tableWidget_prescript.setCurrentCell(
                        current_row+1,
                        prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'],
                    )

                # if self.doubleSpinBox_total_dosage.value() > 0:
                #     self._set_dosage_percent()
        self.ui.tableWidget_prescript.setFocus()
        if self.prescript_edit_mode == 'Y' and current_column in [
                prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'],
                prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']]:
            self.ui.tableWidget_prescript.edit(self.ui.tableWidget_prescript.currentIndex())

        return QtWidgets.QTableWidget.keyPressEvent(self.ui.tableWidget_prescript, event)

    def _total_dosage_value_changed(self):
        self._set_dosage_percent()

    def _is_manual_percent(self):
        manual_percent = False

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_type = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO['MedicineType'], row_no
            )
            if medicine_type not in ['單方', '複方']:
                continue

            medicine_name = self.table_widget_prescript.field_value(
                prescript_utils.SELF_PRESCRIPT_COL_NO['MedicineName'], row_no
            )
            if medicine_name in ['自費粉藥']:
                continue

            numerator = self.table_widget_prescript.field_value(
                prescript_utils.SELF_PRESCRIPT_COL_NO['Instruction'], row_no
            )
            if numerator == '0':
                manual_percent = True
                break

        return manual_percent

    def _is_numerator_completed(self):
        numerator_completed = False
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            unit = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO['Unit'], row_no
            )
            if unit not in ['克']:
                continue

            medicine_type = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO['MedicineType'], row_no
            )
            if medicine_type not in ['單方', '複方']:
                continue

            numerator = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO['Instruction'], row_no
            )
            medicine_name = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'], row_no
            )
            if medicine_name not in ['', None] and numerator in ['', None]:
                numerator_completed = False
                self._clear_all_dosages()
                break
            else:
                numerator_completed = True

        return numerator_completed

    def _get_denominator(self):
        denominator = 0
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_type = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO['MedicineType'], row_no
            )
            if medicine_type not in ['單方', '複方']:
                continue

            percent = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO['Instruction'], row_no
            )
            if percent in ['', None]:
                continue
            else:
                denominator += number_utils.get_float(percent)

        return denominator

    def _clear_all_dosages(self):
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            self.ui.tableWidget_prescript.setItem(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage'],
                QtWidgets.QTableWidgetItem(None)
            )

    def _get_percent_total_dosage(self):
        total_dosage = self.doubleSpinBox_total_dosage.value()

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_type = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO['MedicineType'], row_no
            )
            if medicine_type not in ['單方', '複方']:
                continue

            numerator = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO['Instruction'], row_no
            )
            numerator = number_utils.get_float(numerator)

            medicine_name = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'], row_no
            )
            if medicine_name not in ['', None] and numerator == 0:  # 扣掉instruction = 0的劑量
                dosage = self.table_widget_prescript.field_value(
                    prescript_utils.INS_PRESCRIPT_COL_NO['Dosage'], row_no
                )
                dosage = number_utils.get_float(dosage)
                total_dosage -= dosage

        return total_dosage

    def _set_dosage_percent(self):
        total_dosage = self._get_percent_total_dosage()
        if total_dosage <= 0:
            return

        # if self._is_manual_percent():
        #     return

        if not self._is_numerator_completed():
            self._clear_all_dosages()
            return

        denominator = self._get_denominator()

        try:
            self.ui.tableWidget_prescript.itemChanged.disconnect()
        except Exception:
            pass
        
        col_no = prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_type = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO['MedicineType'], row_no
            )
            if medicine_type not in ['單方', '複方']:
                continue

            numerator = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO['Instruction'], row_no
            )
            if numerator in ['', None, 0, '0']:
                continue

            try:
                numerator = number_utils.get_float(numerator)
                dosage = (total_dosage * numerator) / denominator
                dosage = round(dosage, 1)
                self.ui.tableWidget_prescript.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem(str(dosage))
                )
                current_item = self.ui.tableWidget_prescript.item(row_no, col_no)
                current_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            except Exception:
                pass

        self.ui.tableWidget_prescript.itemChanged.connect(self._prescript_item_changed)
        self._set_total_dosage()
        self._set_total_cost()

        self.check_total_dosage(row_no)
        self.check_total_costs(row_no)

    def _set_dosage_format(self, row_no, col_no):
        if self.system_settings.field('劑量模式') in ['日劑量', '總量']:
            dosage_format = '.1f'
        else:
            dosage_format = '.2f'

        self.table_widget_prescript.set_cell_text_format(
            row_no, col_no, dosage_format, 'float',
        )

    def open_medicine_dialog(self):
        current_row = self.ui.tableWidget_prescript.currentRow()
        self.ui.tableWidget_prescript.setCurrentCell(
            current_row, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']
        )
        self.ui.tableWidget_prescript.setCurrentCell(
            current_row, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']
        )
        item = self.ui.tableWidget_prescript.item(
            current_row, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']
        )
        if item is None or item.text() == '':
            if self.ui.tableWidget_prescript.rowCount() >= 2:
                self.ui.tableWidget_prescript.removeRow(current_row)
                self.ui.tableWidget_prescript.setCurrentCell(
                    0, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']
                )
            return

        previous_medicine_name = self.table_widget_prescript.field_value(
            prescript_utils.INS_PRESCRIPT_COL_NO['BackupMedicineName']
        )

        if item.text() == previous_medicine_name:
            if current_row < self.ui.tableWidget_prescript.rowCount() - 1:
                self.ui.tableWidget_prescript.setCurrentCell(
                    current_row + 1, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'],
                    )
            elif current_row == self.ui.tableWidget_prescript.rowCount() - 1:
                self.ui.tableWidget_prescript.setCurrentCell(
                    0, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage'],
                    )
            return

        keyword = item.text()
        keyword = string_utils.replace_ascii_char(['\\', '"', '\''], keyword)

        if self.system_settings.field('健保處方詞庫只顯示單方複方') == 'Y':
            medicine_type_condition = 'AND (MedicineType in ("單方", "複方") OR (MedicineType = "成方" AND Unit = "克"))'
        else:
            # medicine_type_condition = '''
            #     AND (MedicineType NOT IN ("水藥", "外用", "高貴", "穴道", "處置", "器材", "檢驗")) OR 
            #     (MedicineType = "成方" AND Unit != "錢"))
            # '''
            medicine_type_condition = '''
                AND (MedicineType NOT IN ("水藥", "外用", "高貴", "穴道", "處置", "器材", "檢驗"))
            '''

        sql = f'''
            SELECT * FROM medicine
            WHERE
                (MedicineName like "%{keyword}%" OR
                 InputCode LIKE "{keyword}%" OR
                 MedicineCode = "{keyword}" OR
                 InsCode = "{keyword}")
                {medicine_type_condition}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            item.setText(previous_medicine_name)
        elif len(rows) == 1:
            deactivate = string_utils.xstr(rows[0]['Deactivate'])
            non_nhi = string_utils.xstr(rows[0]['NonNHI'])
            medicine_name = string_utils.xstr(rows[0]['MedicineName'])
            if deactivate != '':
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    '藥品已停用',
                    f'<font color="red"><h3>{medicine_name}已經停用<br>停用原因: {deactivate}</h3></font>',
                    '請開立其他藥品',
                )
                item.setText(previous_medicine_name)
                return
            elif non_nhi == 'Y':
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    '自費藥品專用',
                    f'<font color="red"><h3>{medicine_name}僅可用於自費處方</h3></font>',
                    '請開立其他藥品',
                )
                item.setText(previous_medicine_name)
                return

            dosage = rows[0]['Dosage']
            if dosage is not None:
                dosage = number_utils.get_float(dosage)

            if not self.append_prescript(rows[0], dosage=dosage):
                item.setText(None)
                return

            if current_row == self.ui.tableWidget_prescript.rowCount() - 1:
                self.append_null_medicine()
            else:
                self.ui.tableWidget_prescript.setCurrentCell(
                    current_row + 1,
                    prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'],
                )
        else:
            dialog = dialog_utils.get_dialog_input_medicine(
                self, self.database, self.system_settings, '健保藥品', self.medicine_set,
                self.ui.tableWidget_prescript, previous_medicine_name, keyword,
            )
            dialog.exec_()
            dialog.deleteLater()

    def _table_widget_treat_key_press(self, event):
        if self.system_settings.field('不要自動切換輸入法') == 'Y':
            pass
        else:        
            system_utils.set_keyboard_layout('英文')

        key = event.key()
        current_row = self.ui.tableWidget_treat.currentRow()

        if key == QtCore.Qt.Key_Delete or key == QtCore.Qt.Key_F5:
            self.remove_treat()
        elif key == QtCore.Qt.Key_Up:
            if self.ui.tableWidget_treat.item(
                    current_row, prescript_utils.INS_TREAT_COL_NO['PrescriptKey']) is None:
                self.ui.tableWidget_treat.removeRow(current_row)
                return
        elif key == QtCore.Qt.Key_Down:
            if current_row == self.ui.tableWidget_treat.rowCount() - 1 and \
                    self.ui.tableWidget_treat.item(
                        current_row, prescript_utils.INS_TREAT_COL_NO['PrescriptKey']) is not None:
                self.append_null_treat()
        elif key == QtCore.Qt.Key_Return or key == QtCore.Qt.Key_Enter:
            if self.ui.tableWidget_treat.currentColumn() == prescript_utils.INS_TREAT_COL_NO['MedicineName']:
                self.open_treat_dialog()

        if self.prescript_edit_mode == 'Y':
            self.ui.tableWidget_treat.edit(self.ui.tableWidget_treat.currentIndex())

        return QtWidgets.QTableWidget.keyPressEvent(self.ui.tableWidget_treat, event)

    def open_treat_dialog(self):
        current_row = self.ui.tableWidget_treat.currentRow()

        self.ui.tableWidget_treat.setCurrentCell(
            current_row, prescript_utils.INS_TREAT_COL_NO['InsCode']
        )
        self.ui.tableWidget_treat.setCurrentCell(
            current_row, prescript_utils.INS_TREAT_COL_NO['MedicineName']
        )
        item = self.ui.tableWidget_treat.item(
            current_row, prescript_utils.INS_TREAT_COL_NO['MedicineName']
        )
        if item is None or item.text() == '':
            return

        previous_medicine_name = self.table_widget_treat.field_value(
            prescript_utils.INS_TREAT_COL_NO['BackupMedicineName']
        )

        if item.text() == previous_medicine_name:
            return

        keyword = item.text()
        keyword = string_utils.replace_ascii_char(['\\', '"', '\''], keyword)

        medicine_type_condition = ''
        if self.ui.comboBox_treatment.currentText() in nhi_utils.ACUPUNCTURE_TREAT:
            medicine_type_condition = '''
                AND (MedicineType IN ("穴道", "處置", "外用") OR (MedicineType = "成方" AND Unit = "次"))
            '''
        elif self.ui.comboBox_treatment.currentText() in nhi_utils.MASSAGE_TREAT:
            medicine_type_condition = '''
                AND (MedicineType in ("處置", "穴道", "外用") OR (MedicineType = "成方" AND Unit = "次"))
            '''

        sql = f'''
            SELECT * FROM medicine
            WHERE
                (MedicineName like "{keyword}%" OR
                InputCode LIKE "{keyword}%" OR
                MedicineCode = "{keyword}" OR
                InsCode = "{keyword}")
                {medicine_type_condition}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            item.setText(previous_medicine_name)
        elif len(rows) == 1:
            medicine_type = string_utils.xstr(rows[0]['MedicineType'])
            if medicine_type == '成方':
                medicine_key = rows[0]['MedicineKey']
                prescript_utils.extract_compound(
                    self, self.database, self.system_settings, medicine_key, None,
                )
                return

            # self.append_treat(rows[0], check_duplicate=False)
            self.append_treat(rows[0])
            if current_row == self.ui.tableWidget_treat.rowCount() - 1:
                self.append_null_treat()
            else:
                self.ui.tableWidget_treat.setCurrentCell(
                    current_row + 1,
                    prescript_utils.INS_TREAT_COL_NO['MedicineName'],
                )
        else:
            dialog = dialog_utils.get_dialog_input_medicine(
                self, self.database, self.system_settings, '健保處置', self.medicine_set,
                self.ui.tableWidget_treat, previous_medicine_name, keyword,
            )
            dialog.exec_()
            dialog.deleteLater()

    def append_prescript(self, row, dosage=None, set_dosage_percent=True, duplicate_warning=None):
        old_dosage = self.table_widget_prescript.field_value(
            prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']
        )
        if old_dosage not in ['', None]:
            dosage = old_dosage

        medicine_key = string_utils.xstr(row['MedicineKey'])
        medicine_name = string_utils.xstr(row['MedicineName'])

        if self.is_vegetarian and prescript_utils.is_animal_derived(self.database, medicine_key):
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle('含動物性成份藥品')
            msg_box.setText(
                f'''
                    <font color="red"><h3>
                        注意！本藥品「{medicine_name}」含動物性成份, 此病人吃素是否繼續開立?
                    </h3></font>'''
            )
            msg_box.setInformativeText("請確定是否繼續給藥.")
            msg_box.addButton(QPushButton("繼續給藥"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            append_medicine = msg_box.exec_()
            self.vegetarian_warned = True
            if append_medicine == QMessageBox.RejectRole:
                return False

        deactivate = prescript_utils.get_medicine_deactivate(self.database, medicine_key)
        if deactivate not in ['', None]:
            system_utils.show_message_box(
                QMessageBox.Critical,
                '藥品已停用',
                f'<font color="red"><h3>{medicine_name}已經停用<br>停用原因: {deactivate}</h3></font>',
                '請開立其他藥品',
            )
            return False

        in_price = prescript_utils.get_medicine_field(
            self.database, medicine_key, 'InPrice'
        )
        if in_price is not None and in_price > 0:
            info = '$'
        else:
            info = ''

        medicine_type = string_utils.xstr(row['MedicineType'])

        if duplicate_warning is None:
            duplicate_warning = self.duplicate_warning
            
        if prescript_utils.check_prescript_duplicates(
                self.ui.tableWidget_prescript,
                medicine_type,
                prescript_utils.INS_PRESCRIPT_COL_NO['MedicineKey'], medicine_key,
                duplicate_warning=duplicate_warning):
            return False

        dosage_mode = self.system_settings.field('劑量模式')
        if dosage_mode in [None, '']:
            dosage_mode = '日劑量'

        medicine_type = string_utils.xstr(row['MedicineType'])
        unit = string_utils.xstr(row['Unit'])

        try:
            instruction = row['Instruction']
        except Exception:
            instruction = None

        if (self.system_settings.field('比例法劑量') == 'Y' or self.doubleSpinBox_total_dosage.value() > 0) and \
                medicine_type in ['單方', '複方'] and unit in ['克'] and instruction in [None, '']:
            instruction = 1

        prescript_row = [
            [prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptKey'], '-1'],
            [prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptNo'],
             string_utils.xstr(self.ui.tableWidget_prescript.currentRow() + 1)],
            [prescript_utils.INS_PRESCRIPT_COL_NO['CaseKey'], string_utils.xstr(self.case_key)],
            [prescript_utils.INS_PRESCRIPT_COL_NO['CaseDate'], string_utils.xstr(self.case_date)],
            [prescript_utils.INS_PRESCRIPT_COL_NO['MedicineSet'], string_utils.xstr(self.medicine_set)],
            [prescript_utils.INS_PRESCRIPT_COL_NO['MedicineType'], medicine_type],
            [prescript_utils.INS_PRESCRIPT_COL_NO['MedicineKey'], medicine_key],
            [prescript_utils.INS_PRESCRIPT_COL_NO['InsCode'], string_utils.xstr(row['InsCode'])],
            [prescript_utils.INS_PRESCRIPT_COL_NO['DosageMode'], self.system_settings.field('劑量模式')],
            [prescript_utils.INS_PRESCRIPT_COL_NO['BackupMedicineName'], string_utils.xstr(row['MedicineName'])],
            [prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'], medicine_name],
            [prescript_utils.INS_PRESCRIPT_COL_NO['Dosage'], string_utils.get_formatted_str(dosage_mode, dosage)],
            [prescript_utils.INS_PRESCRIPT_COL_NO['Unit'], unit],
            [prescript_utils.INS_PRESCRIPT_COL_NO['Instruction'], string_utils.xstr(instruction)],
            [prescript_utils.INS_PRESCRIPT_COL_NO['Info'], info],
        ]
        self.set_prescript(prescript_row)
        if self.medicine_set == 1:  # 健保預設給藥日份
            self.set_default_pres_days()

        db_utils.increment_hit_rate(self.database, 'medicine', 'MedicineKey', medicine_key)

        if set_dosage_percent and self.doubleSpinBox_total_dosage.value() > 0:
            self._set_dosage_percent()

        return True

    def set_prescript(self, row, row_no=None, sort_prescript=True):
        medicine_key = row[prescript_utils.INS_PRESCRIPT_COL_NO['MedicineKey']][1]
        medicine_type = row[prescript_utils.INS_PRESCRIPT_COL_NO['MedicineType']][1]
        if medicine_type == '成方':
            prescript_utils.extract_compound(
                self, self.database, self.system_settings, medicine_key, None,
            )
            return

        if row_no is None:
            row_no = self.ui.tableWidget_prescript.currentRow()

        for item in row:
            self.ui.tableWidget_prescript.setItem(
                row_no, item[0], QtWidgets.QTableWidgetItem(item[1])
            )

            current_item = self.ui.tableWidget_prescript.item(row_no, item[0])
            if item[0] in [
                prescript_utils.INS_PRESCRIPT_COL_NO['Unit'],
                prescript_utils.INS_PRESCRIPT_COL_NO['Instruction'],
                prescript_utils.INS_PRESCRIPT_COL_NO['Info'],
            ] and current_item is not None:
                current_item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            elif item[0] in [prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']] and current_item is not None:
                current_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        ins_code = row[prescript_utils.INS_PRESCRIPT_COL_NO['InsCode']][1]
        if ins_code == '':
            for column in range(self.ui.tableWidget_prescript.columnCount()):
                item = self.ui.tableWidget_prescript.item(row_no, column)
                if item is not None:
                    item.setForeground(QtGui.QColor('blue'))

        # medicine_key = medical_row[prescript_utils.INS_PRESCRIPT_COL_NO['MedicineKey']][1]
        # database._add_prescript_info_button(row_no, medicine_key)
        self.ui.tableWidget_prescript.resizeRowsToContents()

        if sort_prescript and self.medicine_sort == '處方類別':
            self._sort_prescript_by_medicine_type(row, row_no, medicine_type)

    def _sort_prescript_by_medicine_type(self, row, row_no, medicine_type):
        exclude_medicine_type = '單方'

        if medicine_type == exclude_medicine_type:
            return

        insert_index = None
        for i in range(self.ui.tableWidget_prescript.rowCount()):
            item = self.ui.tableWidget_prescript.item(
                i, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineType']
            )
            if item is None:
                continue

            current_medicine_type = item.text()
            if current_medicine_type == exclude_medicine_type:
                insert_index = i
                break

        if insert_index is None:
            return

        if row_no <= insert_index:
            return

        self.ui.tableWidget_prescript.removeRow(row_no)
        self.ui.tableWidget_prescript.insertRow(insert_index)
        self.set_prescript(row, insert_index, sort_prescript=False)

    def append_treat(self, row, show_duplicate_warning=None):
        medicine_type = string_utils.xstr(row['MedicineType'])
        medicine_key = string_utils.xstr(row['MedicineKey'])
        medicine_name = string_utils.xstr(row['MedicineName'])

        if show_duplicate_warning is not None:
            duplicate_warning = show_duplicate_warning
        else:
            duplicate_warning = self.duplicate_warning

        if prescript_utils.check_prescript_duplicates(
                self.ui.tableWidget_treat,
                medicine_type,
                prescript_utils.INS_TREAT_COL_NO['MedicineName'], medicine_name,
                duplicate_warning=duplicate_warning):
            return

        treat_row = [
            [prescript_utils.INS_TREAT_COL_NO['PrescriptKey'], '-1'],
            [prescript_utils.INS_TREAT_COL_NO['CaseKey'], string_utils.xstr(self.case_key)],
            [prescript_utils.INS_TREAT_COL_NO['CaseDate'], string_utils.xstr(self.case_date)],
            [prescript_utils.INS_TREAT_COL_NO['MedicineSet'], string_utils.xstr(self.medicine_set)],
            [prescript_utils.INS_TREAT_COL_NO['MedicineType'], medicine_type],
            [prescript_utils.INS_TREAT_COL_NO['MedicineKey'], medicine_key],
            [prescript_utils.INS_TREAT_COL_NO['InsCode'], string_utils.xstr(row['InsCode'])],
            [prescript_utils.INS_TREAT_COL_NO['BackupMedicineName'], medicine_name],
            [prescript_utils.INS_TREAT_COL_NO['MedicineName'], medicine_name],
        ]

        self.set_treat(treat_row)
        db_utils.increment_hit_rate(self.database, 'medicine', 'MedicineKey', medicine_key)

    def _get_row_no(self, treat_name):
        current_row_no = None

        for row_no in range(self.ui.tableWidget_treat.rowCount()):
            item = self.ui.tableWidget_treat.item(row_no, prescript_utils.INS_TREAT_COL_NO['MedicineName'])
            if item is None:
                continue

            medicine_name = item.text()
            if treat_name in medicine_name:
                current_row_no = row_no

        return current_row_no

    def set_treat(self, treat_row):
        row_no = self.ui.tableWidget_treat.currentRow()

        treat_name = treat_row[prescript_utils.INS_TREAT_COL_NO['MedicineName']][1]
        if '治療時間' in treat_name:
            self._clear_treat_time('治療時間')
            row_no = 0
            self.ui.tableWidget_treat.insertRow(row_no)
        elif '治療開始' in treat_name:
            self._clear_treat_time('治療開始')
            row_no = 1
            self.ui.tableWidget_treat.insertRow(row_no)
        elif '治療結束' in treat_name:
            self._clear_treat_time('治療結束')
            row_no = 2
            self.ui.tableWidget_treat.insertRow(row_no)
        elif '輔助治療' in treat_name:
            new_row_no = self._get_row_no('輔助治療')
            if new_row_no is None:
                new_row_no = self._get_row_no('治療結束')

            if new_row_no is not None:
                row_no = new_row_no + 1

            self.ui.tableWidget_treat.insertRow(row_no)
        elif '治療部位' in treat_name:
            new_row_no = self._get_row_no('治療部位')
            if new_row_no is None:
                new_row_no = self._get_row_no('輔助治療')
                if new_row_no is None:
                    new_row_no = self._get_row_no('治療結束')

            if new_row_no is not None:
                row_no = new_row_no + 1
            else:
                row_no = 0

            self.ui.tableWidget_treat.insertRow(row_no)

        for item in treat_row:
            self.ui.tableWidget_treat.setItem(
                row_no, item[0],
                QtWidgets.QTableWidgetItem(item[1])
            )

    def _get_treat_row_no(self, treat_name):
        for row_no in range(self.ui.tableWidget_treat.rowCount()):
            item = self.ui.tableWidget_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO['MedicineName']
            )
            if item is None:
                continue

            if treat_name in item.text():
                return row_no

    def _set_table_width(self):
        medicine_width = [
            70,
            100, 100, 100, 100, 100, 100, 100, 100, 100,
            250, 60, 50, 50, 10,
        ]
        treat_width = [
            70,
            100, 100, 100, 100, 100, 100, 100,
            150,
        ]

        self.table_widget_prescript.set_table_heading_width(medicine_width)
        self.table_widget_treat.set_table_heading_width(treat_width)

    def _read_cases(self):
        if self.case_key is None:
            return

        sql = f'''
            SELECT Continuance, TreatType, PharmacyType, Treatment, DoctorDone FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        row = self.database.select_record(sql)[0]
        self.treatment = row['Treatment']
        self.doctor_done = row['DoctorDone']

        if self.doctor_done == 'True':
            self.ui.toolButton_clear_medical_record.setEnabled(False)

        if string_utils.xstr(row['PharmacyType']) == '申報':
            self.ui.checkBox_pharmacy.setChecked(True)

        if number_utils.get_integer(row['Continuance']) >= 2:
            self.ui.radioButton_medicine.setChecked(True)
            self.ui.radioButton_diag.setEnabled(False)
        #     self.ui.groupBox_prescript.setTitle('內服藥')
        #     self.ui.groupBox_prescript.setCheckable(False)

    def _read_prescript(self):
        if self.case_key is None:
            self.append_null_medicine()
            return

        try:
            self.ui.tableWidget_prescript.itemChanged.disconnect()
        except Exception:
            pass

        self._read_medicine()
        self.ui.tableWidget_prescript.itemChanged.connect(self._prescript_item_changed)

        self._read_treat()
        self._read_dosage()
        self._read_misc()

        self._calculate_total_costs()

        self.append_null_medicine()
        if self.treatment is not None or str(self.treatment).strip() != '':
            self.append_null_treat()

    def _read_dosage(self):
        sql = f'''
            SELECT * FROM dosage
            WHERE
                CaseKey = {self.case_key} AND
                MedicineSet = {self.medicine_set}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self.ui.comboBox_package.setCurrentText(string_utils.xstr(row['Packages']))
        self.ui.comboBox_pres_days.setCurrentText(string_utils.xstr(row['Days']))
        self.ui.comboBox_instruction.setCurrentText(string_utils.xstr(row['Instruction']))

        try:
            self.ui.doubleSpinBox_total_dosage.valueChanged.disconnect()
        except Exception:
            pass

        try:
            total_dosage = number_utils.get_float(row['TotalDosage'])
            if total_dosage > 0:
                self.ui.doubleSpinBox_total_dosage.setValue(total_dosage)
        except Exception:
            pass

        self.ui.doubleSpinBox_total_dosage.valueChanged.connect(self._total_dosage_value_changed)

        if row['Remark'] == '本頁不印':
            self.ui.checkBox_print_receipt.setChecked(True)
            self._print_receipt_clicked(True, prompt_warning=False)
        if row['NoPharmacy'] == 'Y':
            self.ui.checkBox_no_pharmacy.setChecked(True)

        if number_utils.get_float(row['TotalDosage']) > 0:
            self.ui.tableWidget_prescript.setHorizontalHeaderItem(
                13, QtWidgets.QTableWidgetItem('比例')
            )
            self.ui.label_total_dosage_setting.setVisible(True)
            self.ui.doubleSpinBox_total_dosage.setVisible(True)

    def _read_misc(self):
        sql = f'''
            SELECT * FROM dosage
            WHERE
                CaseKey = {self.case_key} AND
                MedicineSet = {self.medicine_set}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self.ui.comboBox_package.setCurrentText(string_utils.xstr(row['Packages']))
        self.ui.comboBox_pres_days.setCurrentText(string_utils.xstr(row['Days']))
        self.ui.comboBox_instruction.setCurrentText(string_utils.xstr(row['Instruction']))

        try:
            self.ui.doubleSpinBox_total_dosage.valueChanged.disconnect()
        except Exception:
            pass

        try:
            total_dosage = number_utils.get_float(row['TotalDosage'])
            if total_dosage > 0:
                self.ui.doubleSpinBox_total_dosage.setValue(total_dosage)
        except Exception:
            pass

        self.ui.doubleSpinBox_total_dosage.valueChanged.connect(self._total_dosage_value_changed)

        if number_utils.get_float(row['TotalDosage']) > 0:
            self.ui.tableWidget_prescript.setHorizontalHeaderItem(
                13, QtWidgets.QTableWidgetItem('比例')
            )
            self.ui.label_total_dosage_setting.setVisible(True)
            self.ui.doubleSpinBox_total_dosage.setVisible(True)

    def _read_medicine(self):
        medicine_groups = nhi_utils.get_medicine_type(self.database, '藥品類別')
        if len(medicine_groups) <= 0:
            return

        sql = f'''
            SELECT prescript.*, medicine.InPrice FROM prescript
                LEFT JOIN medicine ON prescript.MedicineKey = medicine.MedicineKey
            WHERE
                CaseKey = {self.case_key} AND
                MedicineSet = {self.medicine_set} AND
                prescript.MedicineType NOT IN ("穴道", "處置", "外用")
            ORDER BY PrescriptNo, PrescriptKey
        '''
        self.table_widget_prescript.set_db_data(sql, self._set_medicine_data)

    def _set_medicine_data(self, row_no, row):
        medicine_key = row['MedicineKey']
        dosage = string_utils.xstr(row['Dosage'])
        ins_code = string_utils.xstr(row['InsCode'])
        in_price = number_utils.get_float(row['InPrice'])
        if in_price > 0:
            in_price_mark = '$'
        else:
            in_price_mark = ''

        if dosage != '':
            if self.system_settings.field('劑量模式') in ['日劑量', '總量']:
                dosage = f"{row['Dosage']:.1f}"
            elif self.system_settings.field('劑量模式') == '次劑量':
                dosage = f"{row['Dosage']:.2f}"

        prescript_row = [
            string_utils.xstr(row['PrescriptKey']),
            string_utils.xstr(row['PrescriptNo']),
            string_utils.xstr(row['CaseKey']),
            string_utils.xstr(row['CaseDate']),
            string_utils.xstr(row['MedicineSet']),
            string_utils.xstr(row['MedicineType']),
            string_utils.xstr(medicine_key),
            ins_code,
            string_utils.xstr(row['DosageMode']),
            string_utils.xstr(row['MedicineName']),
            string_utils.xstr(row['MedicineName']),
            dosage,
            string_utils.xstr(row['Unit']),
            string_utils.xstr(row['Instruction']),
            in_price_mark,
        ]

        for col_no in range(len(prescript_row)):
            self.ui.tableWidget_prescript.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(prescript_row[col_no])
            )

            self._adjust_prescript_align(row_no, col_no)
            if ins_code == '':
                self.ui.tableWidget_prescript.item(
                    row_no, col_no).setForeground(
                    QtGui.QColor('blue')
                )

        # database._add_prescript_info_button(row_no, medicine_key)

    def _adjust_prescript_align(self, row_no, col_no):
        if col_no in [prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']]:
            self.ui.tableWidget_prescript.item(
                row_no, col_no).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )
        elif col_no in [
            prescript_utils.INS_PRESCRIPT_COL_NO['Unit'],
            prescript_utils.INS_PRESCRIPT_COL_NO['Instruction'],
            prescript_utils.INS_PRESCRIPT_COL_NO['Info'],
        ]:
            self.ui.tableWidget_prescript.item(
                row_no, col_no).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
            )

    def _add_prescript_info_button(self, row_no, medicine_key):
        description = prescript_utils.get_medicine_description(self.database, medicine_key)

        button = QtWidgets.QPushButton()
        button.setIcon(QtGui.QIcon('./icons/gtk-info.svg'))
        button.setFlat(True)
        if description is None:
            button.setEnabled(False)

        button.clicked.connect(lambda: self._show_medicine_description(description))

        self.ui.tableWidget_prescript.setCellWidget(
            row_no, prescript_utils.INS_PRESCRIPT_COL_NO['Info'], button)

    def _show_medicine_description(self):
        medicine_key_item = self.ui.tableWidget_prescript.item(
            self.ui.tableWidget_prescript.currentRow(),
            prescript_utils.SELF_PRESCRIPT_COL_NO['MedicineKey']
        )
        if medicine_key_item is None:
            return

        medicine_key = medicine_key_item.text()
        description = prescript_utils.get_medicine_description(self.database, medicine_key)
        # if description is None:
        #     return

        dialog = dialog_utils.get_dialog_rich_text(
            self, self.database, self.system_settings, 'rich_text', medicine_key, description
        )
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

    def _open_medicine_library(self):
        medicine_name = self.ui.tableWidget_prescript.item(
            self.ui.tableWidget_prescript.currentRow(),
            prescript_utils.SELF_PRESCRIPT_COL_NO['MedicineName']
        )
        if medicine_name in ['', None]:
            return

        medicine_name = medicine_name.text()
        try:
            medicine_type = self.ui.tableWidget_prescript.item(
                self.ui.tableWidget_prescript.currentRow(),
                prescript_utils.SELF_PRESCRIPT_COL_NO['MedicineType']).text()
        except Exception:
            return

        dialog = dialog_utils.get_dialog_medicine_library(
            self, self.database, self.system_settings, medicine_name, medicine_type
        )
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

    def _show_treat_description(self):
        medicine_key_item = self.ui.tableWidget_treat.item(
            self.ui.tableWidget_treat.currentRow(),
            prescript_utils.INS_TREAT_COL_NO['MedicineKey']
        )
        if medicine_key_item is None:
            return

        medicine_key = medicine_key_item.text()
        description = prescript_utils.get_medicine_description(self.database, medicine_key)
        # if description is None:
        #     return

        dialog = dialog_utils.get_dialog_rich_text(
            self, self.database, self.system_settings, 'rich_text', medicine_key, description
        )
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

    def _read_treat(self):
        self._extract_treat()
        self._read_treat_prescript()

    # def _extract_treat(self, treatment=None):
    #     self.ui.comboBox_treatment.setCurrentIndex(0)

    #     if self.treatment in ['', None] and treatment is None:
    #         return

    #     if self.treatment in ['中度針灸合併高度傷科', '高度針灸合併高度傷科']:  # 轉先前舊的高度傷科
    #         self.treatment += '起始次'
    #     elif self.treatment in ['中度針灸合併高度傷科療程2-6次', '高度針灸合併高度傷科療程2-6次']:
    #         self.treatment = self.treatment.replace('療程2-6次', '') + '後續治療'

    #     if treatment is not None:
    #         self.treatment = treatment

    #     if self.treatment not in nhi_utils.ACUPUNCTURE_MERGE_TREAT:  # 非針灸合併傷科治療
    #         self.ui.comboBox_treatment.setCurrentText(self.treatment)
    #         return

    #     for primary_treatment in nhi_utils.PRIMARY_ACUPUNCTURE_TREAT:
    #         if primary_treatment in self.treatment:
    #             if primary_treatment == '中度針灸':
    #                 primary_treatment = '中度複雜性針灸'
    #             elif primary_treatment == '高度針灸':
    #                 primary_treatment = '高度複雜性針灸'

    #             break

    #     for secondary_treatment in nhi_utils.SECONDARY_MASSAGE_TREAT:
    #         if secondary_treatment in self.treatment:
    #             if secondary_treatment == '中度傷科':
    #                 secondary_treatment = '中度複雜性傷科'
    #             elif secondary_treatment == '高度傷科':
    #                 secondary_treatment = '高度複雜性傷科'
    #             elif secondary_treatment == '中度傷科合併特殊疾病':
    #                 secondary_treatment = '中度複雜性傷科合併特殊疾病'

    #             break

    #     self.ui.comboBox_treatment.setCurrentText(primary_treatment)
    #     self.ui.comboBox_second_treatment.setCurrentText(secondary_treatment)

    # 2023-05-23
    def _extract_treat(self, treatment=None):
        self.ui.comboBox_treatment.setCurrentIndex(0)
        if treatment is not None:
            self.treatment = treatment

        primary_treatment, secondary_treatment = case_utils.extract_treatment(self.treatment)
        if self.course >= 2 and secondary_treatment in ['中度複雜性傷科', '高度複雜性傷科']:
            secondary_treatment = '一般傷科'

        if (primary_treatment != '高度複雜性傷科' and secondary_treatment != '高度複雜性傷科') and \
           self.system_settings.field('不申報高度複雜性傷科') == 'Y':
            index = self.ui.comboBox_treatment.findText("高度複雜性傷科")
            if index != -1:
                self.ui.comboBox_treatment.removeItem(index)
                
        self.ui.comboBox_treatment.setCurrentText(primary_treatment)
        self.ui.comboBox_second_treatment.setCurrentText(secondary_treatment)

        if self.no_massage == 'Y':
            if secondary_treatment in ['', None]:
                self.ui.comboBox_second_treatment.setVisible(False)

    def _read_treat_prescript(self):
        medicine_groups = nhi_utils.get_medicine_type(self.database, '處置類別')
        medicine_groups += ['外用']

        if len(medicine_groups) <= 0:
            return

        sql = f'''
            SELECT * FROM prescript WHERE
                CaseKey = {self.case_key} AND
                MedicineSet = {self.medicine_set} AND
                MedicineType IN {tuple(medicine_groups)} AND
                MedicineName NOT IN {tuple(nhi_utils.INS_TREAT)}
            ORDER BY PrescriptKey
        '''
        self.table_widget_treat.set_db_data(sql, self._set_treat_data, None)

    def _set_treat_data(self, rec_no, rec):
        treat_rec = [
            string_utils.xstr(rec['PrescriptKey']),
            string_utils.xstr(rec['CaseKey']),
            string_utils.xstr(rec['CaseDate']),
            string_utils.xstr(rec['MedicineSet']),
            string_utils.xstr(rec['MedicineType']),
            string_utils.xstr(rec['MedicineKey']),
            string_utils.xstr(rec['InsCode']),
            string_utils.xstr(rec['MedicineName']),
            string_utils.xstr(rec['MedicineName']),
        ]

        for column in range(len(treat_rec)):
            self.ui.tableWidget_treat.setItem(
                rec_no, column,
                QtWidgets.QTableWidgetItem(treat_rec[column])
            )

    # 增加處方資料
    def append_null_medicine(self, insert_row_no=None):
        row_count = self.table_widget_prescript.row_count()
        if row_count <= 0:
            self._insert_medicine_row(row_count)
            return

        if insert_row_no is not None:
            row_no = insert_row_no
            check_row_no = row_no
        else:
            row_no = row_count
            check_row_no = row_no - 1

        item = self.ui.tableWidget_prescript.item(
            check_row_no, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'])
        if item is None or item.text().strip() == '':
            return

        self._insert_medicine_row(row_no)

        self.ui.tableWidget_prescript.setCurrentCell(
            row_no, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'],
        )

    # 增加處方資料
    def insert_medicine(self):
        current_row_no = self.ui.tableWidget_prescript.currentRow()
        self.append_null_medicine(insert_row_no=current_row_no)

    # 增加處方資料
    def append_null_treat(self):
        if self.ui.comboBox_treatment.currentText() == '':
            return

        row_count = self.table_widget_treat.row_count()
        if row_count <= 0:
            self._insert_treat_row(row_count)
            return

        item = self.ui.tableWidget_treat.item(
            row_count-1, prescript_utils.INS_TREAT_COL_NO['MedicineName'])
        if item is None or item.text().strip() == '':
            return

        self._insert_treat_row(row_count)

    def _insert_medicine_row(self, index):
        self.ui.tableWidget_prescript.setFocus(True)
        self.ui.tableWidget_prescript.insertRow(index)
        self.ui.tableWidget_prescript.setCurrentCell(
            index, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']
        )

        self.ui.tableWidget_prescript.setItem(
            index, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage'], QtWidgets.QTableWidgetItem(None)
        )
        self.ui.tableWidget_prescript.item(
            index, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _insert_treat_row(self, index):
        self.ui.tableWidget_treat.setFocus(True)
        self.ui.tableWidget_treat.insertRow(index)
        self.ui.tableWidget_treat.setCurrentCell(
            index, prescript_utils.INS_TREAT_COL_NO['MedicineName']
        )

    def set_default_pres_days(self):
        if self.ui.tableWidget_prescript.rowCount() <= 0:
            return

        if self.ui.tableWidget_prescript.item(
                0, prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptKey']) is None:
            return

        if self.ui.comboBox_package.currentText() != '':
            return

        if self.ui.comboBox_pres_days.currentText() != '':
            return

        if self.packages is not None and self.packages > 0:
            self.ui.comboBox_package.setCurrentText(string_utils.xstr(self.packages))
        else:
            self.ui.comboBox_package.setCurrentText(self.system_settings.field('給藥包數'))

        if self.pres_days is not None and self.pres_days > 0:
            self.ui.comboBox_pres_days.setCurrentText(string_utils.xstr(self.pres_days))
        else:
            self.ui.comboBox_pres_days.setCurrentText(self.system_settings.field('給藥天數'))

        if self.instruction not in ['', None]:
            self.ui.comboBox_instruction.setCurrentText(self.instruction)
        else:
            self.ui.comboBox_instruction.setCurrentText(self.system_settings.field('用藥指示'))

    # 刪除處方
    def remove_medicine(self):
        if self.parent.is_closed:
            return

        index = self.ui.tableWidget_prescript.currentRow()
        self.ui.tableWidget_prescript.removeRow(index)

        if self.ui.tableWidget_prescript.rowCount() <= 1:
            item = self.ui.tableWidget_prescript.item(0, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'])
            if item is None or item.text() == '':
                self.ui.comboBox_package.setCurrentText(None)
                self.ui.comboBox_pres_days.setCurrentText(None)
                self.ui.comboBox_instruction.setCurrentText(None)
                self.append_null_medicine()

        self._set_total_dosage()
        self._set_total_cost()
        self._set_dosage_percent()

        self.parent.calculate_ins_fees()
        # if (string_utils.xstr(self.parent.medical_record['Share']) in nhi_utils.INFECTIOUS_TYPE or
        #    string_utils.xstr(self.parent.medical_record['Injury']) in nhi_utils.INFECTIOUS_TYPE):
        #     self.parent.calculate_ins_fees()

        self.ui.tableWidget_prescript.setFocus()

    # 刪除處置
    def remove_treat(self):
        index = self.ui.tableWidget_treat.currentRow()
        self.ui.tableWidget_treat.removeRow(index)

        if self.ui.tableWidget_treat.rowCount() <= 0:
            self.append_null_treat()

    def _check_dosage_limitation(self, check_type='input'):
        if check_type == 'input' and self.check_total_dosage_event == '存檔時檢查':
            return True

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_key = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineKey']
            )
            if medicine_key is None:
                continue

            medicine_key = medicine_key.text()
            if medicine_key == '':
                continue

            medicine_name = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']
            )
            if medicine_name is None:
                continue

            dosage = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']
            )
            if dosage is None:
                continue

            sql = f'''
                SELECT MinDosage, MaxDosage FROM medicine
                WHERE
                    MedicineKey = {medicine_key}
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                continue

            min_dosage = number_utils.get_float(rows[0]['MinDosage'])
            max_dosage = number_utils.get_float(rows[0]['MaxDosage'])

            if min_dosage == 0 and max_dosage == 0:
                continue

            medicine_name = medicine_name.text()
            dosage = number_utils.get_float(dosage.text())
                
            error_message = None
            if min_dosage > 0 and dosage < min_dosage:
                error_message = f'{medicine_name} 最小用量為 {min_dosage} 公克'
            elif max_dosage > 0 and dosage > max_dosage:
                error_message = f'{medicine_name} 最大用量為 {max_dosage} 公克'

            if error_message is not None:
                msg_box = QtWidgets.QMessageBox()
                msg_box.setIcon(QtWidgets.QMessageBox.Warning)
                msg_box.setWindowTitle('警告')
                msg_box.setText(error_message)
                msg_box.addButton(QtWidgets.QPushButton('確定'), QtWidgets.QMessageBox.YesRole)
                msg_box.exec_()
                return False

        return True

    def save_prescript(self, check_prescript=True):
        if check_prescript:
            if not self.check_total_dosage(check_type='save'):
                return False

            if not self.check_total_costs(check_type='save'):
                return False

            try:
                if not self._check_dosage_limitation(check_type='save'):
                    return False
            except Exception:
                pass
                
        self._save_dosage()
        self._save_medicine()
        self._save_treatment()
        self._save_treat()

        if self.system_settings.field('調整庫存量') == '即時調整' and self.parent.record_saved:
            stock_utils.adjust_ins_prescript(self.database, self.case_key)

        return True

    def _save_dosage(self):
        sql = f'''
            DELETE FROM dosage
            WHERE
                CaseKey = {self.case_key} AND
                MedicineSet = {self.medicine_set}
        '''
        self.database.exec_sql(sql)
        pres_days = number_utils.get_integer(self.ui.comboBox_pres_days.currentText())
        if pres_days <= 0:
            return

        packages = number_utils.get_integer(self.ui.comboBox_package.currentText())

        total_dosage = self.ui.doubleSpinBox_total_dosage.value()
        if total_dosage == 0.0:
            total_dosage = None

        fields = [
            'CaseKey', 'MedicineSet', 'Packages', 'Days', 'TotalDosage', 'Instruction', 'NoPharmacy', 'Remark']

        if self.ui.checkBox_print_receipt.isChecked():
            remark = '本頁不印'
        else:
            remark = None

        if self.ui.checkBox_no_pharmacy.isChecked():
            no_pharmacy = 'Y'
        else:
            no_pharmacy = None

        data = [
            self.case_key,
            self.medicine_set,
            packages,
            pres_days,
            total_dosage,
            self.ui.comboBox_instruction.currentText(),
            no_pharmacy,
            remark,
        ]
        self.database.insert_record('dosage', fields, data)

    def _save_medicine(self):
        prescript_data_set = []
        for i in range(self.ui.tableWidget_prescript.rowCount()):
            prescript_row = []
            for j in range(self.ui.tableWidget_prescript.columnCount()):
                try:
                    value = self.ui.tableWidget_prescript.item(i, j).text().strip()
                    prescript_row.append(value if value != '' else None)
                except AttributeError:
                    prescript_row.append(None)

            prescript_data_set.append(prescript_row)

        self.delete_not_exists_prescript(prescript_data_set, '藥品類別')

        prescript_no = 0  # 重編 PrescriptNo
        for items in prescript_data_set:
            if items[prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptKey']] is None:
                continue

            # 處理 Dosage 欄位為空或非數字的情況
            dosage_index = prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']
            dosage = items[dosage_index]
            if dosage is None or (isinstance(dosage, str) and dosage.strip() == ''):
                items[dosage_index] = None
            else:
                try:
                    items[dosage_index] = float(dosage)  # 確保是 float，可加強健壯性
                except ValueError:
                    items[dosage_index] = None  # 若不能轉為 float，也改為 None

            prescript_no += 1
            items[prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptNo']] = str(prescript_no)

            if items[prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptKey']] == '-1':
                self.insert_prescript(items)
            else:
                self.update_prescript(items)

    # def _save_medicine(self):
    #     prescript_data_set = []
    #     for i in range(self.ui.tableWidget_prescript.rowCount()):
    #         prescript_row = []
    #         for j in range(self.ui.tableWidget_prescript.columnCount()):
    #             try:
    #                 value = self.ui.tableWidget_prescript.item(i, j).text().strip()
    #                 prescript_row.append(value if value != '' else None)
    #             except AttributeError:
    #                 prescript_row.append(None)

    #         prescript_data_set.append(prescript_row)

    #     self.delete_not_exists_prescript(prescript_data_set, '藥品類別')

    #     prescript_no = 0  # 重編 PrescriptNo
    #     for items in prescript_data_set:
    #         if items[prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptKey']] is None:
    #             continue

    #         if items[prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']] == '':
    #             items[prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']] = None

    #         prescript_no += 1
    #         items[prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptNo']] = str(prescript_no)

    #         if items[prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptKey']] == '-1':
    #             self.insert_prescript(items)
    #         else:
    #             self.update_prescript(items)

    def _save_treatment(self):
        primary_treatment = self.ui.comboBox_treatment.currentText()
        secondary_treatment = self.ui.comboBox_second_treatment.currentText()
        course = number_utils.get_integer(self.course)
        treatment = nhi_utils.get_treatment(
            self.database, self.case_key, primary_treatment, secondary_treatment, course)

        fields = ['Treatment']
        data = [treatment]
        self.database.update_record('cases', fields, 'CaseKey', self.case_key, data)

    def _save_treat(self):
        treat_data_set = []
        for i in range(self.ui.tableWidget_treat.rowCount()):
            treat_row = []
            for j in range(self.ui.tableWidget_treat.columnCount()):
                try:
                    treat_row.append(self.ui.tableWidget_treat.item(i, j).text())
                except AttributeError:
                    treat_row.append(None)

            treat_data_set.append(treat_row)

        self.delete_not_exists_prescript(treat_data_set, '處置類別')

        for items in treat_data_set:
            if items[prescript_utils.INS_TREAT_COL_NO['PrescriptKey']] is None:
                continue

            if items[prescript_utils.INS_TREAT_COL_NO['PrescriptKey']] == '-1':
                self.insert_treat(items)
            else:
                self.update_treat(items)

    # 刪除不在tableWidget內的處方
    def delete_not_exists_prescript(self, prescript_data_set, medicine_type):
        medicine_type_list = nhi_utils.get_medicine_type(self.database, medicine_type)
        if len(medicine_type_list) <= 0:
            return

        prescript_key_list = []
        for items in prescript_data_set:
            prescript_key_list.append(items[prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptKey']])

        sql = f'''
            SELECT * FROM prescript
            WHERE
                CaseKey = {self.case_key} AND
                MedicineSet = {self.medicine_set} AND
                MedicineType in {tuple(medicine_type_list)}
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            prescript_key = row['PrescriptKey']
            if str(row['PrescriptKey']) not in prescript_key_list:
                self.database.exec_sql(f'''
                    DELETE FROM prescript
                    WHERE
                        PrescriptKey = {prescript_key}
                ''')
                self.database.exec_sql(f'''
                    DELETE FROM presextend
                    WHERE
                        PrescriptKey = {prescript_key}
                ''')

    # 插入處方資料至資料庫內
    def insert_prescript(self, items):
        fields = [
            'PrescriptNo', 'CaseKey', 'CaseDate',
            'MedicineSet', 'MedicineType', 'MedicineKey', 'InsCode', 'DosageMode',
            'MedicineName', 'Dosage', 'Unit', 'Instruction',
        ]

        data = [
            items[prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptNo']],
            self.case_key,
            items[prescript_utils.INS_PRESCRIPT_COL_NO['CaseDate']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['MedicineSet']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['MedicineType']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['MedicineKey']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['InsCode']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['DosageMode']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['Unit']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['Instruction']],
        ]
        self.database.insert_record('prescript', fields, data)

    # 插入處置資料至資料庫內
    def insert_treat(self, items):
        fields = [
            'CaseKey', 'CaseDate',
            'MedicineSet', 'MedicineType', 'MedicineKey', 'InsCode',
            'MedicineName'
        ]

        data = [
            items[prescript_utils.INS_TREAT_COL_NO['CaseKey']],
            items[prescript_utils.INS_TREAT_COL_NO['CaseDate']],
            items[prescript_utils.INS_TREAT_COL_NO['MedicineSet']],
            items[prescript_utils.INS_TREAT_COL_NO['MedicineType']],
            items[prescript_utils.INS_TREAT_COL_NO['MedicineKey']],
            items[prescript_utils.INS_TREAT_COL_NO['InsCode']],
            items[prescript_utils.INS_TREAT_COL_NO['MedicineName']],
        ]
        self.database.insert_record('prescript', fields, data)

    # 更新處方資料至資料庫內
    def update_prescript(self, items):
        if items[6] == '':
            items[6] = None

        fields = [
            'PrescriptNo', 'CaseKey', 'CaseDate',
            'MedicineSet', 'MedicineType', 'MedicineKey', 'InsCode', 'DosageMode',
            'MedicineName', 'Dosage', 'Unit', 'Instruction',
        ]
        data = [
            items[prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptNo']],
            self.case_key,
            items[prescript_utils.INS_PRESCRIPT_COL_NO['CaseDate']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['MedicineSet']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['MedicineType']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['MedicineKey']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['InsCode']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['DosageMode']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['Unit']],
            items[prescript_utils.INS_PRESCRIPT_COL_NO['Instruction']],
        ]
        self.database.update_record(
            'prescript', fields, 'PrescriptKey', items[0], data)

    # 更新處置資料至資料庫內
    def update_treat(self, items):
        fields = [
            'CaseKey', 'CaseDate',
            'MedicineSet', 'MedicineType', 'MedicineKey', 'InsCode',
            'MedicineName'
        ]
        data = [
            items[prescript_utils.INS_TREAT_COL_NO['CaseKey']],
            items[prescript_utils.INS_TREAT_COL_NO['CaseDate']],
            items[prescript_utils.INS_TREAT_COL_NO['MedicineSet']],
            items[prescript_utils.INS_TREAT_COL_NO['MedicineType']],
            items[prescript_utils.INS_TREAT_COL_NO['MedicineKey']],
            items[prescript_utils.INS_TREAT_COL_NO['InsCode']],
            items[prescript_utils.INS_TREAT_COL_NO['MedicineName']],
        ]
        self.database.update_record(
            'prescript', fields, 'PrescriptKey', items[0], data)

    # 還原json處方
    def copy_prescript_from_json(self, backup_records_key, json_medical_record, json_rows, medicine_set):
        self.copy_from = '病歷拷貝'

        self._copy_treatment_from_json(json_medical_record, json_rows)
        self._copy_medicine_from_json(backup_records_key, json_rows, medicine_set)
        self.check_total_dosage()
        self.check_total_costs()

        self.copy_from = None

    def _copy_treatment_from_json(self, json_medical_record, json_rows):
        self.ui.tableWidget_treat.clearContents()
        self.ui.tableWidget_treat.setRowCount(0)

        treatment = string_utils.xstr(json_medical_record['Treatment'])
        start_date = case_utils.get_course_start_date(
            self.database, self.parent.medical_record['PatientKey'], self.case_date,
            self.parent.medical_record['Card'],
            self.parent.medical_record['Continuance'],
        )
        if start_date >= nhi_utils.INS_TREAT_2021_DATE:
            treatment = case_utils.convert_new_treatment(treatment)
            if treatment in [
                '中度複雜性傷科', '高度複雜性傷科', '中度複雜性傷科合併特殊疾病', '脫臼整復復位', '骨折復位'] and \
                    self.course >= 2:
                treatment = '一般傷科'
        else:
            treatment = case_utils.convert_old_treatment(treatment)

        self.ui.comboBox_treatment.setCurrentText(treatment)

        for row in json_rows:
            medicine_name = string_utils.xstr(row['MedicineName'])
            if medicine_name in [None, '']:
                continue

            if '治療開始' in medicine_name or '治療結束' in medicine_name:
                treat_time = self._replace_treat_time(json_rows, medicine_name, treatment)
                row['MedicineName'] = treat_time

            self.append_null_treat()
            self.append_treat(row)

        self.ui.tableWidget_treat.resizeRowsToContents()

    def _copy_medicine_from_json(self, backup_records_key, json_rows, medicine_set):
        self.ui.tableWidget_prescript.clearContents()
        self.ui.tableWidget_prescript.setRowCount(0)

        for row_no, row in enumerate(json_rows):
            if row['MedicineName'] is None:
                continue

            if row['MedicineSet'] != medicine_set:
                continue

            if row['MedicineType'] not in ['單方', '複方']:
                continue

            self.append_null_medicine()
            self.append_prescript(row, row['Dosage'])
            self._set_dosage_format(row_no, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage'])

        self.ui.tableWidget_prescript.resizeRowsToContents()

        pres_days = case_utils.get_pres_days_from_json(self.database, backup_records_key)
        packages = case_utils.get_packages_from_json(self.database, backup_records_key)
        instruction = case_utils.get_instruction_from_json(self.database, backup_records_key)

        self.ui.comboBox_pres_days.setCurrentText(string_utils.xstr(pres_days))
        self.ui.comboBox_package.setCurrentText(string_utils.xstr(packages))
        self.ui.comboBox_instruction.setCurrentText(string_utils.xstr(instruction))

    # 拷貝json處方
    def copy_prescript_json(self, extension_json_key, copy_from=None):
        self.copy_from = copy_from
        self._copy_medicine_json(extension_json_key)
        self._copy_treat_json(extension_json_key)

        self.ui.tableWidget_prescript.resizeRowsToContents()
        self.check_total_dosage()
        self.check_total_costs()

        self.copy_from = None

    def _copy_medicine_json(self, extension_json_key):
        self.ui.tableWidget_prescript.clearContents()
        self.ui.tableWidget_prescript.setRowCount(0)
        sql = f'''
            SELECT * FROM extension_json
            WHERE
                ExtensionJSONKey = {extension_json_key}
        '''
        json_rows = self.database.select_record(sql)
        if len(json_rows) <= 0:
            return

        json_row = json_rows[0]
        prescript_rows = json.loads(json_row['JSON'])['prescript']

        for row_no, row in enumerate(prescript_rows):
            if row['medicine_name'] is None:
                continue

            self.append_null_medicine()
            self.append_medicine_json(row, row['dosage'])
            self._set_dosage_format(row_no, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage'])

        pres_days = case_utils.get_json_pres_days(self.database, json_row)
        packages = case_utils.get_json_packages(self.database, json_row)
        instruction = case_utils.get_json_instruction(self.database, json_row)

        self.ui.comboBox_pres_days.setCurrentText(string_utils.xstr(pres_days))
        self.ui.comboBox_package.setCurrentText(string_utils.xstr(packages))
        self.ui.comboBox_instruction.setCurrentText(string_utils.xstr(instruction))

    def _copy_treat_json(self, extension_json_key):
        self.ui.tableWidget_treat.clearContents()
        self.ui.tableWidget_treat.setRowCount(0)
        sql = f'''
            SELECT * FROM extension_json
            WHERE
                ExtensionJSONKey = {extension_json_key}
        '''
        json_rows = self.database.select_record(sql)
        if len(json_rows) <= 0:
            return

        json_row = json_rows[0]

        medical_record_row = json.loads(json_row['JSON'])['diagnostic']
        treatment = medical_record_row['treatment']
        start_date = case_utils.get_course_start_date(
            self.database, self.parent.medical_record['PatientKey'], self.case_date,
            self.parent.medical_record['Card'],
            self.parent.medical_record['Continuance'],
        )
        if start_date >= nhi_utils.INS_TREAT_2021_DATE:
            treatment = case_utils.convert_new_treatment(treatment)
            if treatment in [
                '中度複雜性傷科', '高度複雜性傷科', '中度複雜性傷科合併特殊疾病', '脫臼整復復位', '骨折復位'] and \
                    self.course >= 2:
                treatment = '一般傷科'
        else:
            treatment = case_utils.convert_old_treatment(treatment)

        self.ui.comboBox_treatment.setCurrentText(treatment)

        prescript_rows = json.loads(json_row['JSON'])['prescript']

        for row_no, row in enumerate(prescript_rows):
            if row['medicine_name'] is None:
                continue

            self.append_null_treat()
            self.append_treat_json(row)

    def append_medicine_json(self, json_row, dosage=None):
        medicine_type = string_utils.xstr(json_row['medicine_type'])
        if medicine_type not in ['單方', '複方']:
            return

        if dosage is None:
            dosage = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']
            )

        medicine_key = string_utils.xstr(json_row['medicine_key'])
        in_price = prescript_utils.get_medicine_field(
            self.database, medicine_key, 'InPrice'
        )
        if in_price is not None and in_price > 0:
            info = '$'
        else:
            info = ''

        if prescript_utils.check_prescript_duplicates(
                self.ui.tableWidget_prescript,
                medicine_type,
                prescript_utils.INS_PRESCRIPT_COL_NO['MedicineKey'], medicine_key,
                duplicate_warning=self.duplicate_warning):
            return

        prescript_row = [
            [prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptKey'], '-1'],
            [prescript_utils.INS_PRESCRIPT_COL_NO['PrescriptNo'],
             string_utils.xstr(self.ui.tableWidget_prescript.currentRow() + 1)],
            [prescript_utils.INS_PRESCRIPT_COL_NO['CaseKey'], string_utils.xstr(self.case_key)],
            [prescript_utils.INS_PRESCRIPT_COL_NO['CaseDate'], string_utils.xstr(self.case_date)],
            [prescript_utils.INS_PRESCRIPT_COL_NO['MedicineSet'], string_utils.xstr(self.medicine_set)],
            [prescript_utils.INS_PRESCRIPT_COL_NO['MedicineType'], string_utils.xstr(json_row['medicine_type'])],
            [prescript_utils.INS_PRESCRIPT_COL_NO['MedicineKey'], medicine_key],
            [prescript_utils.INS_PRESCRIPT_COL_NO['InsCode'], string_utils.xstr(json_row['ins_code'])],
            [prescript_utils.INS_PRESCRIPT_COL_NO['DosageMode'], self.system_settings.field('劑量模式')],
            [prescript_utils.INS_PRESCRIPT_COL_NO['BackupMedicineName'], string_utils.xstr(json_row['medicine_name'])],
            [prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName'], string_utils.xstr(json_row['medicine_name'])],
            [prescript_utils.INS_PRESCRIPT_COL_NO['Dosage'], string_utils.xstr(dosage)],
            [prescript_utils.INS_PRESCRIPT_COL_NO['Unit'], string_utils.xstr(json_row['unit'])],
            [prescript_utils.INS_PRESCRIPT_COL_NO['Instruction'], None],
            [prescript_utils.INS_PRESCRIPT_COL_NO['Info'], info],
        ]

        self.set_prescript(prescript_row)
        if self.medicine_set == 1:  # 健保預設給藥日份
            self.set_default_pres_days()

        db_utils.increment_hit_rate(self.database, 'medicine', 'MedicineKey', medicine_key)

    def append_treat_json(self, json_row):
        medicine_type = string_utils.xstr(json_row['medicine_type'])
        if medicine_type in ['單方', '複方']:
            return

        medicine_key = string_utils.xstr(json_row['medicine_key'])

        if prescript_utils.check_prescript_duplicates(
                self.ui.tableWidget_treat,
                medicine_type,
                prescript_utils.INS_TREAT_COL_NO['MedicineKey'], medicine_key,
                duplicate_warning=self.duplicate_warning):
            return

        prescript_row = [
            [prescript_utils.INS_TREAT_COL_NO['PrescriptKey'], '-1'],
            [prescript_utils.INS_TREAT_COL_NO['CaseKey'], string_utils.xstr(self.case_key)],
            [prescript_utils.INS_TREAT_COL_NO['CaseDate'], string_utils.xstr(self.case_date)],
            [prescript_utils.INS_TREAT_COL_NO['MedicineSet'], string_utils.xstr(self.medicine_set)],
            [prescript_utils.INS_TREAT_COL_NO['MedicineType'], string_utils.xstr(json_row['medicine_type'])],
            [prescript_utils.INS_TREAT_COL_NO['MedicineKey'], medicine_key],
            [prescript_utils.INS_TREAT_COL_NO['InsCode'], string_utils.xstr(json_row['ins_code'])],
            [prescript_utils.INS_TREAT_COL_NO['BackupMedicineName'], string_utils.xstr(json_row['medicine_name'])],
            [prescript_utils.INS_TREAT_COL_NO['MedicineName'], string_utils.xstr(json_row['medicine_name'])],
        ]

        self.set_treat(prescript_row)
        db_utils.increment_hit_rate(self.database, 'medicine', 'MedicineKey', medicine_key)

    # 拷貝過去病歷的處方
    def copy_past_prescript(self, case_key, copy_from=None):
        self.copy_from = copy_from
        self._copy_past_medicine(case_key)

        self.ui.tableWidget_prescript.resizeRowsToContents()
        self.check_total_dosage()
        self.check_total_costs()

        self.copy_from = None

    def _copy_past_medicine(self, case_key):
        self.ui.tableWidget_prescript.clearContents()
        self.ui.tableWidget_prescript.setRowCount(0)
        self.ui.doubleSpinBox_total_dosage.setValue(0)

        if type(self.copy_from) is int and self.copy_from >= 2:
            sql = f'''
                SELECT
                    prescript.MedicineKey, prescript.MedicineType, prescript.MedicineName,
                    prescript.InsCode, prescript.Dosage, prescript.Unit, prescript.Instruction,
                    medicine.NonNHI
                FROM prescript
                    LEFT JOIN medicine ON prescript.MedicineKey = medicine.MedicineKey
                WHERE
                    CaseKey = {case_key} AND
                    MedicineSet = {self.copy_from}
                ORDER BY PrescriptKey
            '''
        else:
            sql = f'''
                SELECT
                    prescript.MedicineKey, prescript.MedicineType, prescript.MedicineName,
                    prescript.InsCode, prescript.Dosage, prescript.Unit, prescript.Instruction,
                    medicine.NonNHI
                FROM prescript
                    LEFT JOIN medicine ON prescript.MedicineKey = medicine.MedicineKey
                WHERE
                    CaseKey = {case_key} AND
                    prescript.MedicineSet = {self.medicine_set} AND
                    prescript.MedicineType NOT IN ("穴道", "處置", "檢驗")
                ORDER BY PrescriptKey
            '''

        rows = self.database.select_record(sql)
        non_nhi_medicine = []
        for row_no, row in enumerate(rows):
            if row['MedicineName'] is None:
                continue

            if row['NonNHI'] == 'Y':
                non_nhi_medicine.append(row['MedicineName'])
                continue

            self.append_null_medicine()
            self.append_prescript(row, row['Dosage'])
            self._set_dosage_format(row_no, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage'])

        pres_days = case_utils.get_pres_days(self.database, case_key, self.medicine_set)
        packages = case_utils.get_packages(self.database, case_key, self.medicine_set)
        instruction = case_utils.get_instruction(self.database, case_key, self.medicine_set)
        total_dosage = case_utils.get_total_dosage(self.database, case_key, self.medicine_set)

        self.ui.comboBox_pres_days.setCurrentText(string_utils.xstr(pres_days))
        self.ui.comboBox_package.setCurrentText(string_utils.xstr(packages))
        self.ui.comboBox_instruction.setCurrentText(string_utils.xstr(instruction))

        self._set_total_dosage()

        if total_dosage > 0:
            try:
                self.ui.doubleSpinBox_total_dosage.valueChanged.disconnect()
            except Exception:
                pass

            self.ui.doubleSpinBox_total_dosage.setValue(total_dosage)
            self.ui.doubleSpinBox_total_dosage.valueChanged.connect(self._total_dosage_value_changed)

        if len(non_nhi_medicine) > 0:
            medicine_list_html = "<br>".join(non_nhi_medicine)
            msg_content = (
                f'<font size="5" color="red"><b>'
                f'{medicine_list_html}<br>'
                f'僅用於自費，請配合開立至自費處方。'
                f'</b></font>'
            )

            system_utils.show_message_box(
                QMessageBox.Critical,
                '非健保用藥',
                msg_content,
                '請檢查處方內容'
            )

    # 拷貝過去病歷的處方
    def copy_past_treat(self, case_key, copy_from=None):
        self.copy_from = copy_from
        self._copy_past_treat(case_key)

        self.ui.tableWidget_treat.resizeRowsToContents()
        self.copy_from = None  # 拷貝完要恢復可以自動彈出電針視窗的狀態

    def _convert_treatment(self, treatment):
        try:
            start_date = case_utils.get_course_start_date(
                self.database, self.parent.medical_record['PatientKey'], self.case_date,
                self.parent.medical_record['Card'],
                self.parent.medical_record['Continuance'],
            )
        except Exception:
            start_date = datetime.date.today()

        if start_date is not None and start_date >= nhi_utils.INS_TREAT_2021_DATE:
            treatment = case_utils.convert_new_treatment(treatment)
            if self.course >= 2 and treatment in [
                '中度複雜性傷科', '高度複雜性傷科', '中度複雜性傷科合併特殊疾病', '脫臼整復復位', '骨折復位'
            ]:
                treatment = '一般傷科'
            elif self.course <= 1 and treatment in [
                '中度針灸合併中度傷科療程2-6次', '高度針灸合併中度傷科療程2-6次',
            ]:
                treatment = treatment.replace('療程2-6次', '')
            elif self.course >= 2 and treatment in [
                '中度針灸合併中度傷科', '高度針灸合併中度傷科',
            ]:
                treatment += '療程2-6次'
            elif self.course >= 2 and treatment in [
                '中度針灸合併高度傷科起始次', '高度針灸合併高度傷科起始次',
            ]:
                treatment = treatment.replace('起始次', '') + '後續治療'
        else:
            treatment = case_utils.convert_old_treatment(treatment)

        return treatment

    def _copy_past_treat(self, case_key):
        self.ui.tableWidget_treat.clearContents()
        self.ui.tableWidget_treat.setRowCount(0)

        sql = f'''
            SELECT Treatment FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        row = self.database.select_record(sql)[0]

        treatment = string_utils.xstr(row['Treatment'])
        treatment = self._convert_treatment(treatment)
        self._extract_treat(treatment)

        sql = f'''
            SELECT * FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineType IN ("穴道", "處置") AND
                MedicineSet = {self.medicine_set}
            ORDER BY PrescriptKey
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            medicine_name = string_utils.xstr(row['MedicineName'])
            if medicine_name in [None, '']:
                continue

            if '治療開始' in medicine_name or '治療結束' in medicine_name:
                treat_time = self._replace_treat_time(rows, medicine_name, treatment)
                row['MedicineName'] = treat_time

            self.append_null_treat()
            self.append_treat(row)

    def _replace_treat_time(self, rows, medicine_name, treatment):
        if '治療開始' in medicine_name:
            medicine_name = f'治療開始:{self.diag_date.time().strftime("%H:%M")}'
        elif '治療結束' in medicine_name:
            minutes = self._get_minutes(rows, treatment)
            medicine_name = f'治療結束:{(self.diag_date + datetime.timedelta(minutes=minutes)).time().strftime("%H:%M")}'

        return medicine_name

    def _get_minutes(self, rows, treatment):
        if treatment in ['中度複雜性針灸']:
            minutes = self.default_moderate_acupuncture_time
        elif treatment in ['中度複雜性傷科']:
            minutes = self.default_moderate_massage_time
        elif treatment in ['高度複雜性針灸']:
            minutes = self.default_highly_acupuncture_time
        elif treatment in ['高度複雜性傷科']:
            minutes = self.default_highly_massage_time
        else:
            minutes = self.default_highly_acupuncture_time

        try:
            for row in rows:
                medicine_name = string_utils.xstr(row['MedicineName'])
                if '治療時間' in medicine_name or '分鐘' in medicine_name:
                    # medicine_name = medicine_name.removeprefix('治療時間:')
                    # medicine_name = medicine_name.removesuffix('分鐘')
                    medicine_name = medicine_name.split('治療時間:')[1]
                    medicine_name = medicine_name.split('分鐘')[0]
                    minutes = number_utils.get_integer(medicine_name.strip())
                    break
        except Exception:
            pass

        return minutes

    # 拷貝過去病歷的處方
    def copy_host_prescript(self, database, case_key, copy_from=None):
        self.copy_from = copy_from
        self._copy_host_medicine(database, case_key)
        self._set_total_dosage()

        self.ui.tableWidget_prescript.resizeRowsToContents()

        # pres_days = case_utils.get_host_pres_days(database, case_key)
        # packages = case_utils.get_host_packages(database, case_key)
        # instruction = case_utils.get_host_instruction(database, case_key)

        pres_days = case_utils.get_pres_days(database, case_key)
        packages = case_utils.get_packages(database, case_key)
        instruction = case_utils.get_instruction(database, case_key)

        self.ui.comboBox_pres_days.setCurrentText(string_utils.xstr(pres_days))
        self.ui.comboBox_package.setCurrentText(string_utils.xstr(packages))
        self.ui.comboBox_instruction.setCurrentText(instruction)
        self.copy_from = None

    def _copy_host_medicine(self, database, case_key):
        self.ui.tableWidget_prescript.clearContents()
        self.ui.tableWidget_prescript.setRowCount(0)
        sql = f'''
            SELECT * FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = {self.medicine_set} AND
                MedicineType NOT IN ("穴道", "處置", "檢驗")
            ORDER BY PrescriptKey
        '''
        rows = database.select_record(sql)
        for row_no, row in enumerate(rows):
            if row['MedicineName'] is None:
                continue

            self.append_null_medicine()
            self.append_prescript(row, row['Dosage'])
            self._set_dosage_format(row_no, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage'])

    # 拷貝過去病歷的處方
    def copy_host_treat(self, database, case_key, copy_from=None):
        self.copy_from = copy_from
        self._copy_host_treat(database, case_key)

        self.ui.tableWidget_treat.resizeRowsToContents()
        self.copy_from = None

    def _copy_host_treat(self, database, case_key):
        self.ui.tableWidget_treat.clearContents()
        self.ui.tableWidget_treat.setRowCount(0)
        self.set_treat_ui()
        sql = f'''
            SELECT CaseDate, Treatment FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        row = database.select_record(sql)[0]
        treatment = string_utils.xstr(row['Treatment'])
        treatment = self._convert_treatment(treatment)
        self._extract_treat(treatment)

        sql = f'''
            SELECT * FROM prescript WHERE
                CaseKey = {case_key} AND
                MedicineType IN ("穴道", "處置") AND
                MedicineSet = {self.medicine_set}
            ORDER BY PrescriptKey
        '''
        rows = database.select_record(sql)
        for row in rows:
            if row['MedicineName'] is None:
                continue

            self.append_null_treat()
            self.append_treat(row)

    # 檢查複雜性針灸是否超過限量
    def _check_complicated_acupuncture_limit(self):
        if self.signal_off:
            return

        # if self.system_settings.field('自動轉換一般針灸') != 'Y':
        #     return

        try:
            injury_type = self.parent.tab_registration.ui.comboBox_injury_type.currentText()
        except AttributeError:
            injury_type = None

        try:
            share_type = self.parent.tab_registration.ui.comboBox_share_type.currentText()
        except AttributeError:
            share_type = None

        try:
            regist_type = self.parent.tab_registration.ui.comboBox_reg_type.currentText()
        except AttributeError:
            regist_type = None

        try:
            treat_type = self.parent.tab_registration.ui.comboBox_treat_type.currentText()
        except AttributeError:
            treat_type = None

        if injury_type in nhi_utils.OCCUPATIONAL_INJURY_TYPE or \
                share_type in ["山地離島"] or \
                treat_type in ["居家醫療"] or \
                regist_type in ["照護機構中醫照護"]:
            return

        primary_treatment = self.ui.comboBox_treatment.currentText()
        secondary_treatment = self.ui.comboBox_second_treatment.currentText()
        try:
            course = number_utils.get_integer(self.parent.tab_registration.comboBox_course.currentText())
        except Exception:
            course = None

        treatment = nhi_utils.get_treatment(
            self.database, self.case_key, primary_treatment, secondary_treatment, course)
        treatment = prescript_utils.truncate_treatment(treatment)

        if treatment not in nhi_utils.COMPLICATED_ACUPUNCTURE_TREAT + nhi_utils.MERGE_TREAT:
            return

        if treatment in nhi_utils.MERGE_TREAT:
            check_acupuncture_list = nhi_utils.MERGE_TREAT
            max_acupuncture_times = nhi_utils.MAX_MERGE_TREAT
            merge_treatment = True
        elif treatment in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST:
            check_acupuncture_list = nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST
            max_acupuncture_times = nhi_utils.MAX_MODERATE_COMPLICATED_ACUPUNCTURE
            merge_treatment = False
        elif treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST:
            check_acupuncture_list = nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST
            max_acupuncture_times = nhi_utils.MAX_HIGHLY_COMPLICATED_ACUPUNCTURE
            merge_treatment = False
        else:
            return
        
        try:
            doctor = self.parent.tab_registration.ui.comboBox_doctor.currentText()
        except AttributeError:
            doctor = ''

        if doctor == '':
            doctor = self.user_name
            
        try:
            doctor_treat_times = case_utils.get_treatment_times_by_doctor(
                self.database, self.case_date, check_acupuncture_list, doctor
            ) + 1  # 包含今天的次數
            
            if merge_treatment:
                avg_acupuncture_times = case_utils.get_merge_treatment_times(
                    self.database, self.case_date, treatment,
                )
            else:
                avg_acupuncture_times = case_utils.get_complicated_acupuncture_times(
                    self.database, self.case_date, treatment,
                )

            if treatment in check_acupuncture_list and \
               avg_acupuncture_times > max_acupuncture_times and \
               doctor_treat_times > max_acupuncture_times:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    '超過複雜性針灸或針傷合併限量',
                    f'''
                        <font color="red"><h3>{doctor}醫師本月的{treatment}次數已達{doctor_treat_times}次,
                        超過{max_acupuncture_times}次的限量, 即將改為一般針灸!</h3></font>''',
                    f'如果強行申報{treatment}將會被健保署行政核刪'
                )
                if merge_treatment:
                    self.ui.comboBox_second_treatment.setCurrentText(None)
                else:
                    self.ui.comboBox_treatment.setCurrentText('一般針灸')
        except AttributeError:
            pass

    def _set_group_box_treat_title(self, title):
        self.ui.groupBox_treat.setStyleSheet(None)
        self.ui.groupBox_treat.setTitle(title)

        if title != '治療處置':
            self.ui.groupBox_treat.setStyleSheet('color: darkMagenta')

    # 處置內容變更
    def _combo_box_treat_changed(self, sender):
        if self.system_settings.field('不要自動切換輸入法') == 'Y':        
            pass
        else:
            system_utils.set_keyboard_layout('英文')

        if self.system_settings.field('不要轉換一般針灸') == 'Y':
            pass
        else:
            self._check_complicated_acupuncture_limit()

        treatment = self.ui.comboBox_treatment.currentText()
        second_treatment = self.ui.comboBox_second_treatment.currentText()
        self._set_group_box_treat_title('治療處置')

        if treatment not in nhi_utils.COMPLICATED_ACUPUNCTURE_TREAT and \
                treatment not in nhi_utils.COMPLICATED_MASSAGE_TREAT:
            self._clear_treat_time()
            self._clear_treat_position()
            self._clear_treat_auxiliary()

        if treatment == '':
            self.ui.tableWidget_treat.setRowCount(0)
        elif treatment in ['電針', '電針治療'] and second_treatment in [None, ''] and \
                self.copy_from != '病歷拷貝':
            self._open_electric_acupuncture_dialog()
        elif treatment in nhi_utils.COMPLICATED_ACUPUNCTURE_TREAT and self.copy_from != '病歷拷貝':
            self._open_complicated_acupuncture_dialog(treatment, second_treatment)
        elif self.parent.age_year is not None and self.parent.age_year < 7 and \
                treatment in nhi_utils.MASSAGE_TREAT and self.copy_from != '病歷拷貝':
            self._set_group_box_treat_title('未滿七歲傷科治療')
            self._open_complicated_massage_dialog(treatment, second_treatment)
        elif treatment in nhi_utils.COMPLICATED_MASSAGE_TREAT + nhi_utils.DISLOCATE_TREAT and \
                self.copy_from != '病歷拷貝':
            self._open_complicated_massage_dialog(treatment, second_treatment)
        elif second_treatment in nhi_utils.COMPLICATED_MASSAGE_TREAT + nhi_utils.DISLOCATE_TREAT and \
                self.copy_from != '病歷拷貝':
            self._open_complicated_massage_dialog(treatment, second_treatment)

        if not sender:
            if treatment in ['一般針灸', '針灸治療']:
                self._open_complicated_acupuncture_dialog(treatment, second_treatment)
            elif treatment in ['一般傷科', '傷科治療']:
                self._open_complicated_massage_dialog(treatment, second_treatment)

        self.set_second_treatment()

        self._set_ins_care_treat()
        self.parent.calculate_ins_fees()

        self.append_null_treat()

    # 處置內容變更
    def _combo_box_second_treat_changed(self, sender):
        if self.system_settings.field('不要轉換一般針灸') == 'Y':
            pass
        else:
            self._check_complicated_acupuncture_limit()

        self.parent.calculate_ins_fees()
        primary_treatment = self.ui.comboBox_treatment.currentText()
        second_treatment = self.ui.comboBox_second_treatment.currentText()
        # 2025-06-04 取消，有些醫師需要一般針灸也輸入治療時間跟部位
        # if (second_treatment == '' or second_treatment not in nhi_utils.COMPLICATED_MASSAGE_TREAT) and \
        #         primary_treatment not in nhi_utils.COMPLICATED_ACUPUNCTURE_TREAT and \
        #         primary_treatment not in nhi_utils.COMPLICATED_MASSAGE_TREAT:
        #     self._clear_treat_time()
        #     self._clear_treat_position()
        #     self._clear_treat_auxiliary()

        if primary_treatment in nhi_utils.ACUPUNCTURE_TREAT and \
                second_treatment in nhi_utils.COMPLICATED_MASSAGE_TREAT and self.copy_from != '病歷拷貝':
            self._open_complicated_acupuncture_dialog(primary_treatment, second_treatment)

        self.append_null_treat()
        self.ui.comboBox_second_treatment.setVisible(True)

        if self.no_massage == 'Y':
            if second_treatment in ['', None]:
                self.ui.comboBox_second_treatment.setVisible(False)

    # 設定針灸合併治療
    def set_second_treatment(self):
        treatment = self.ui.comboBox_treatment.currentText()
        try:
            if treatment not in nhi_utils.SELECTION_ACUPUNCTURE_TREAT or \
                    self.parent.tab_registration.ui.comboBox_treat_type.currentText() == '居家醫療':
                self.ui.comboBox_second_treatment.setCurrentIndex(0)
                self.ui.comboBox_second_treatment.setVisible(False)
                return
        except Exception:
            pass

        second_treatment = self.ui.comboBox_second_treatment.currentText()

        self.ui.comboBox_second_treatment.setVisible(True)
        model = self._get_second_treatment_model()
        view = self._get_treatment_view(self.ui.comboBox_second_treatment)

        self.ui.comboBox_second_treatment.setModel(model)
        self.ui.comboBox_second_treatment.setModelColumn(1)
        self.ui.comboBox_second_treatment.setView(view)
        view.setColumnWidth(0, 50)
        view.setColumnWidth(1, 300)
        view.setColumnWidth(2, 60)

        if second_treatment == '一般傷科':
            self.ui.comboBox_second_treatment.setCurrentIndex(1)

    def _get_second_treatment_model(self):
        ins_treat_list = nhi_utils.MASSAGE_TREAT_2021 + nhi_utils.DISLOCATE_TREAT_2021

        # 2024-05-17 療程2-6次不可申報高度傷科 懷恩堂
        if self.parent.tab_registration is not None:
            course = number_utils.get_integer(self.parent.tab_registration.ui.comboBox_course.currentText())
            treat_type = self.parent.tab_registration.ui.comboBox_treat_type.currentText()
            if course >= 2:
                # ins_treat_list = ['一般傷科', '中度複雜性傷科']   2025-05-27 陳立德 支付標準不可申報中度複傷
                if '中度傷科' in treat_type or '中度複雜性傷科' in treat_type:
                    ins_treat_list = ['一般傷科', '中度複雜性傷科']
                elif '高度傷科' in treat_type or '高度複雜性傷科' in treat_type:
                    ins_treat_list = ['一般傷科', '高度複雜性傷科']
                else:
                    ins_treat_list = ['一般傷科']

        model = QtGui.QStandardItemModel()
        model.appendRow(QtGui.QStandardItem(None))

        for treatment in ins_treat_list:
            ins_code = nhi_utils.TREAT_DICT[treatment]
            sql = f'''
                SELECT Amount FROM charge_settings
                WHERE
                    InsCode = "{ins_code}"
            '''
            rows = self.database.select_record(sql)
            fee = 0 if len(rows) <= 0 else number_utils.get_integer(rows[0]['Amount'])

            ins_fee_item = QtGui.QStandardItem(string_utils.xstr(fee))
            ins_fee_item.setTextAlignment(QtCore.Qt.AlignRight)
            model.appendRow([
                QtGui.QStandardItem(ins_code),
                QtGui.QStandardItem(treatment),
                ins_fee_item,
            ])

        model.setHeaderData(0, QtCore.Qt.Horizontal, '代碼')
        model.setHeaderData(1, QtCore.Qt.Horizontal, '處置項目')
        model.setHeaderData(2, QtCore.Qt.Horizontal, '點數')

        for row_no in range(1, model.rowCount()):
            index = model.index(row_no, 0)
            treat_code = model.data(index)

            if 'B41' <= treat_code <= 'B49':
                color = QtGui.QBrush(QtCore.Qt.darkMagenta)
            elif 'B51' <= treat_code <= 'B59':
                color = QtGui.QBrush(QtCore.Qt.darkGreen)
            elif 'B61' <= treat_code <= 'B69':
                color = QtGui.QBrush(QtCore.Qt.darkRed)
            elif 'D01' <= treat_code <= 'D99':
                color = QtGui.QBrush(QtCore.Qt.darkMagenta)
            elif 'E01' <= treat_code <= 'E08':
                color = QtGui.QBrush(QtCore.Qt.darkGreen)
            elif 'F01' <= treat_code <= 'F99':
                color = QtGui.QBrush(QtCore.Qt.darkBlue)
            else:
                color = QtGui.QBrush(QtCore.Qt.darkRed)

            for col_no in range(3):
                model.setData(
                    model.index(row_no, col_no),
                    color,
                    QtCore.Qt.ForegroundRole
                )

        return model

    def _set_ins_care_treat(self):
        if self.parent.tab_registration is None:
            return

        treat_type = self.parent.tab_registration.ui.comboBox_treat_type.currentText()
        if treat_type not in nhi_utils.IMPROVE_CARE_TREAT:
            return

        treatment = self.ui.comboBox_treatment.currentText()
        pres_days = number_utils.get_integer(self.ui.comboBox_pres_days.currentText())
        course = number_utils.get_integer(self.parent.tab_registration.ui.comboBox_course.currentText())

        medicine_set = 11
        ins_care = self.parent.tab_list[medicine_set-1]
        if ins_care is not None:
            if treat_type == '助孕照護':
                ins_care.set_aid_pregnant_treat(treatment, pres_days, course)
            elif treat_type == '保胎照護':
                ins_care.set_keep_baby_treat(treatment, pres_days, course)
            elif treat_type in nhi_utils.CANCER_CARE_TREAT:
                ins_care.set_cancer_treat(treatment)
            elif treat_type == '慢性腎病照護':
                ins_care.set_kidney_prescript(pres_days, treatment, self.course)

    def _check_vegetarian(self):
        if self.call_from in ['參考病歷']:
            return

        if self.vegetarian_warned:
            return

        pres_days = number_utils.get_integer(self.ui.comboBox_pres_days.currentText())
        if self.doctor_done == 'True' or pres_days <= 0:
            return

        if self.is_vegetarian:
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Warning,
                '吃素提醒',
                '''<font size="5" color="red">
                    <b>注意! 此病患吃素，請留意是否開立含動物性成份藥物.</b>
                </font>
                ''',
                '請詢問病患是否吃素.'
            )
            self.vegetarian_warned = True

    # 藥日變更重新批價
    def pres_days_changed(self):
        pres_days = self.ui.comboBox_pres_days.currentText()
        currect_pres_days = ''
        for alpha in pres_days:
            if not alpha.isdigit():
                self.ui.comboBox_pres_days.setCurrentText(currect_pres_days)
                return

            currect_pres_days += alpha

        self._set_ins_care_pres_days()
        self._set_ins_care_treat()
        self.parent.calculate_ins_fees()

        if self.parent.tab_registration is None:
            treat_type = None
        else:
            treat_type = self.parent.tab_registration.ui.comboBox_treat_type.currentText()

        # if treat_type in nhi_utils.CANCER_CARE_TREAT and self.ui.comboBox_pres_days.currentText() == '':
        #     self.ui.comboBox_pres_days.setCurrentText('7')  # 至少七天藥

        self._check_vegetarian()

        if number_utils.get_integer(self.ui.comboBox_pres_days.currentText()) > 0:
            self.pres_days = number_utils.get_integer(self.ui.comboBox_pres_days.currentText())

        self.ui.comboBox_pres_days.setFocus(True)

    # 包變更
    def package_changed(self):
        package = self.ui.comboBox_package.currentText()
        currect_package = ''
        for alpha in package:
            if not alpha.isdigit():
                self.ui.comboBox_package.setCurrentText(currect_package)
                return

            currect_package += alpha

        if number_utils.get_integer(self.ui.comboBox_package.currentText()) > 0:
            self.packages = number_utils.get_integer(self.ui.comboBox_package.currentText())

    # 服法變更
    def instruction_changed(self):
        if self.ui.comboBox_instruction.currentText() not in ['', None]:
            self.instruction = self.ui.comboBox_instruction.currentText()

    def _set_ins_care_pres_days(self):
        if self.parent.tab_registration is None:
            return

        treat_type = self.parent.tab_registration.ui.comboBox_treat_type.currentText()
        if treat_type not in nhi_utils.CANCER_CARE_TREAT:
            return

        pres_days = number_utils.get_integer(self.ui.comboBox_pres_days.currentText())

        medicine_set = 11
        ins_care = self.parent.tab_list[medicine_set-1]
        if ins_care is not None:
            if treat_type in nhi_utils.CANCER_CARE_TREAT:
                ins_care.set_cancer_prescript(pres_days)
            elif treat_type in ['慢性腎病照護']:
                treatment = self.ui.comboBox_treatment.currentText()
                ins_care.set_kidney_prescript(pres_days, treatment, self.course)

    # 開啟電針儀選擇視窗
    def _open_electric_acupuncture_dialog(self):
        if self.signal_off:
            return

        dialog = dialog_utils.get_dialog_electric_acupuncture(self, self.database, self.system_settings)
        dialog.exec_()

        electric_acupuncture_list = dialog.get_electric_acupuncture_list()

        self.ui.tableWidget_treat.setRowCount(0)
        for item in electric_acupuncture_list:
            row = {
                'MedicineType': '穴道',
                'MedicineKey': None,
                'InsCode': None,
                'MedicineName': item
            }
            self.append_null_treat()
            self.append_treat(row)

        dialog.deleteLater()
        self.append_null_treat()

    # 開啟複雜性針灸選擇視窗
    def _open_complicated_acupuncture_dialog(self, treatment, second_treatment):
        if self.signal_off:
            return

        disease_code = self.parent.lineEdit_disease_code1.text()
        dialog = dialog_utils.get_dialog_complicated_acupuncture(
            self, self.database, self.system_settings, treatment, second_treatment, disease_code, self.diag_date,
            self.ui.tableWidget_treat,
        )

        if not dialog.exec_():
            dialog.deleteLater()
            return

        if dialog.accept_treats:
            self._set_complicated_acupuncture_treatments(dialog)
            self._set_complicated_acupuncture_point(dialog)
            self._set_complicated_massage_treat(dialog)
            self.append_null_treat()

        dialog.deleteLater()

    def _set_complicated_acupuncture_treatments(self, dialog):
        treatment_list = self._get_treatment_list_interval(dialog)

        check_box_treatment_list = [
            dialog.ui.checkBox_1,
            dialog.ui.checkBox_2,
            dialog.ui.checkBox_3,
            dialog.ui.checkBox_4,
            dialog.ui.checkBox_5,
            dialog.ui.checkBox_6,
            dialog.ui.checkBox_7,
            dialog.ui.checkBox_8,
            dialog.ui.checkBox_9,
            dialog.ui.checkBox_10,
        ]

        for check_box in check_box_treatment_list:
            if check_box.isChecked():
                treatment_list.append(f'輔助治療:{check_box.text()}')

        check_box_position_list = [
            dialog.ui.checkBox_c1,
            dialog.ui.checkBox_c2,
            dialog.ui.checkBox_c3,
            dialog.ui.checkBox_c4,
            dialog.ui.checkBox_c5,
            dialog.ui.checkBox_c6,
            dialog.ui.checkBox_c7,

            dialog.ui.checkBox_lu1,
            dialog.ui.checkBox_lu2,
            dialog.ui.checkBox_lu3,
            dialog.ui.checkBox_lu4,
            dialog.ui.checkBox_lu5,
            dialog.ui.checkBox_lu6,
            dialog.ui.checkBox_lu7,

            dialog.ui.checkBox_lb1,
            dialog.ui.checkBox_lb2,
            dialog.ui.checkBox_lb3,
            dialog.ui.checkBox_lb4,
            dialog.ui.checkBox_lb5,
            dialog.ui.checkBox_lb6,

            dialog.ui.checkBox_ru1,
            dialog.ui.checkBox_ru2,
            dialog.ui.checkBox_ru3,
            dialog.ui.checkBox_ru4,
            dialog.ui.checkBox_ru5,
            dialog.ui.checkBox_ru6,
            dialog.ui.checkBox_ru7,

            dialog.ui.checkBox_rb1,
            dialog.ui.checkBox_rb2,
            dialog.ui.checkBox_rb3,
            dialog.ui.checkBox_rb4,
            dialog.ui.checkBox_rb5,
            dialog.ui.checkBox_rb6,
        ]
        for check_box in check_box_position_list:
            if check_box.isChecked():
                treatment_list.append(f'治療部位:{check_box.text()}')

        self._clear_complicated_treat('穴道')
        for item in treatment_list:
            row = {
                'MedicineType': '穴道',
                'MedicineKey': None,
                'InsCode': None,
                'MedicineName': item
            }
            self.append_null_treat()
            self.append_treat(row)

    def _set_complicated_acupuncture_point(self, dialog):
        table_widget = dialog.tableWidget_acupuncture_point
        for row_no in range(table_widget.rowCount()):
            for col_no in range(table_widget.columnCount()):
                check_box = table_widget.cellWidget(row_no, col_no)
                if check_box is None:
                    continue

                if check_box.isChecked():
                    acupuncture_point = check_box.text()
                    row = {
                        'MedicineType': '穴道',
                        'MedicineKey': self._get_medicine_key_from_acupuncture_point(acupuncture_point),
                        'InsCode': None,
                        'MedicineName': acupuncture_point,
                    }
                    self.append_null_treat()
                    self.append_treat(row)

    def _set_complicated_massage_treat(self, dialog):
        treatment_list = []

        check_box_massage_list = [
            dialog.ui.checkBox_massage1,
            dialog.ui.checkBox_massage2,
            dialog.ui.checkBox_massage3,
            dialog.ui.checkBox_massage4,
            dialog.ui.checkBox_massage5,
            dialog.ui.checkBox_massage6,
            dialog.ui.checkBox_massage7,
            dialog.ui.checkBox_massage8,
            dialog.ui.checkBox_massage9,
            dialog.ui.checkBox_massage10,
            dialog.ui.checkBox_massage11,
            dialog.ui.checkBox_massage12,
            dialog.ui.checkBox_massage13,
            dialog.ui.checkBox_massage14,
            dialog.ui.checkBox_massage15,
            dialog.ui.checkBox_massage16,
            dialog.ui.checkBox_massage17,
            dialog.ui.checkBox_massage18,
            dialog.ui.checkBox_massage19,
        ]
        for check_box in check_box_massage_list:
            if check_box.isChecked():
                treatment_list.append(check_box.text())

        self._clear_complicated_treat('處置')
        for item in treatment_list:
            row = {
                'MedicineType': '處置',
                'MedicineKey': None,
                'InsCode': None,
                'MedicineName': item
            }
            self.append_null_treat()
            self.append_treat(row)

    def _get_medicine_key_from_acupuncture_point(self, acupuncture_point):
        sql = '''
            SELECT MedicineKey FROM medicine
            WHERE
                MedicineName = "{acupuncture_point}" AND
                MedicineType = "穴道"
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return rows[0]['MedicineKey']

    # 開啟複雜性傷科選擇視窗
    def _open_complicated_massage_dialog(self, treatment, second_treatment):
        if self.signal_off:
            return

        dialog = dialog_utils.get_dialog_complicated_massage(
            self, self.database, self.system_settings, treatment, second_treatment,
            self.diag_date, self.ui.tableWidget_treat,
        )
        if not dialog.exec_():
            dialog.deleteLater()
            return

        self._set_complicated_massage_treatments(dialog)
        self.append_null_treat()

        dialog.deleteLater()

    def _get_treatment_list_interval(self, dialog, treatment_list=None):
        if treatment_list is None:
            treatment_list = []

        minutes = dialog.ui.spinBox_time.value()
        start_time = dialog.ui.timeEdit_start_time.time().toString("hh:mm")
        end_time = dialog.ui.timeEdit_end_time.time().toString("hh:mm")
        treatment_list.append(f'治療時間:{minutes}分鐘')
        treatment_list.append(f'治療開始:{start_time}')
        treatment_list.append(f'治療結束:{end_time}')

        return treatment_list

    def _clear_complicated_treat(self, treat_type):
        for row_no in range(self.ui.tableWidget_treat.rowCount()-1, -1, -1):
            treat_name_item = self.ui.tableWidget_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO['MedicineName']
            )
            medicine_type_item = self.ui.tableWidget_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO['MedicineType']
            )
            if treat_name_item is None or medicine_type_item is None:
                continue

            treat_name = treat_name_item.text()
            medicine_type = medicine_type_item.text()

            if treat_type == '穴道' and ('治療' in treat_name or '輔助' in treat_name):
                self.ui.tableWidget_treat.removeRow(row_no)

            if medicine_type == treat_type:  # 上面的treat_name的medicine_type 也是
                self.ui.tableWidget_treat.removeRow(row_no)

    def _clear_treat_time(self, assign_treat=None):
        for row_no in range(self.ui.tableWidget_treat.rowCount()-1, -1, -1):
            treat_name_item = self.ui.tableWidget_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO['MedicineName']
            )
            if treat_name_item is None:
                self.ui.tableWidget_treat.removeRow(row_no)
                continue

            treat_name = treat_name_item.text()
            if assign_treat is not None:
                if assign_treat in treat_name:
                    self.ui.tableWidget_treat.removeRow(row_no)
                    return
                else:
                    continue

            if '治療開始:' in treat_name or '治療結束:' in treat_name or '治療時間:' in treat_name:
                self.ui.tableWidget_treat.removeRow(row_no)

    def _clear_treat_position(self):
        for row_no in range(self.ui.tableWidget_treat.rowCount()-1, -1, -1):
            treat_name_item = self.ui.tableWidget_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO['MedicineName']
            )
            if treat_name_item is None:
                self.ui.tableWidget_treat.removeRow(row_no)
                continue

            treat_name = treat_name_item.text()
            if '治療部位:' in treat_name:
                self.ui.tableWidget_treat.removeRow(row_no)

    def _clear_treat_auxiliary(self):
        for row_no in range(self.ui.tableWidget_treat.rowCount()-1, -1, -1):
            treat_name_item = self.ui.tableWidget_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO['MedicineName']
            )
            if treat_name_item is None:
                self.ui.tableWidget_treat.removeRow(row_no)
                continue

            treat_name = treat_name_item.text()
            if '輔助治療:' in treat_name:
                self.ui.tableWidget_treat.removeRow(row_no)

    def _set_complicated_massage_treatments(self, dialog):
        treatment_list = self._get_treatment_list_interval(dialog)

        check_box_complicated_treatment_list = [
            dialog.ui.checkBox_1,
            dialog.ui.checkBox_2,
            dialog.ui.checkBox_3,
            dialog.ui.checkBox_4,
            dialog.ui.checkBox_5,
            dialog.ui.checkBox_6,
            dialog.ui.checkBox_7,
            dialog.ui.checkBox_8,
            dialog.ui.checkBox_9,
            dialog.ui.checkBox_10,
        ]
        for check_box in check_box_complicated_treatment_list:
            if check_box.isChecked():
                treatment_list.append(f'輔助治療: {check_box.text()}')

        check_box_position_list = [
            dialog.ui.checkBox_c1,
            dialog.ui.checkBox_c2,
            dialog.ui.checkBox_c3,
            dialog.ui.checkBox_c4,
            dialog.ui.checkBox_c5,
            dialog.ui.checkBox_c6,
            dialog.ui.checkBox_c7,

            dialog.ui.checkBox_lu1,
            dialog.ui.checkBox_lu2,
            dialog.ui.checkBox_lu3,
            dialog.ui.checkBox_lu4,
            dialog.ui.checkBox_lu5,
            dialog.ui.checkBox_lu6,
            dialog.ui.checkBox_lu7,

            dialog.ui.checkBox_lb1,
            dialog.ui.checkBox_lb2,
            dialog.ui.checkBox_lb3,
            dialog.ui.checkBox_lb4,
            dialog.ui.checkBox_lb5,
            dialog.ui.checkBox_lb6,

            dialog.ui.checkBox_ru1,
            dialog.ui.checkBox_ru2,
            dialog.ui.checkBox_ru3,
            dialog.ui.checkBox_ru4,
            dialog.ui.checkBox_ru5,
            dialog.ui.checkBox_ru6,
            dialog.ui.checkBox_ru7,

            dialog.ui.checkBox_rb1,
            dialog.ui.checkBox_rb2,
            dialog.ui.checkBox_rb3,
            dialog.ui.checkBox_rb4,
            dialog.ui.checkBox_rb5,
            dialog.ui.checkBox_rb6,
        ]
        for check_box in check_box_position_list:
            if check_box.isChecked():
                treatment_list.append(f'治療部位: {check_box.text()}')

        check_box_treatment_item_list = [  # 推拿八法
            dialog.ui.checkBox_item1,
            dialog.ui.checkBox_item2,
            dialog.ui.checkBox_item3,
            dialog.ui.checkBox_item4,
            dialog.ui.checkBox_item5,
            dialog.ui.checkBox_item6,
            dialog.ui.checkBox_item7,
            dialog.ui.checkBox_item8,
            dialog.ui.checkBox_item9,
            dialog.ui.checkBox_item10,
            dialog.ui.checkBox_item11,
            dialog.ui.checkBox_item12,
            dialog.ui.checkBox_item13,
            dialog.ui.checkBox_item14,
            dialog.ui.checkBox_item15,
            dialog.ui.checkBox_item16,
            dialog.ui.checkBox_item17,
            dialog.ui.checkBox_item18,
            dialog.ui.checkBox_item19,
        ]
        for check_box in check_box_treatment_item_list:
            if check_box.isChecked():
                treatment_list.append(f'{check_box.text()}')

        self._clear_complicated_treat('處置')
        for item in treatment_list:
            row = {
                'MedicineType': '處置',
                'MedicineKey': None,
                'InsCode': None,
                'MedicineName': item
            }
            self.append_null_treat()
            self.append_treat(row, show_duplicate_warning=False)

    def open_medicine_dictionary(self):
        self.parent.open_dictionary(self.medicine_set, '健保處方')

    def _open_treat_dictionary(self):
        treatment = self.ui.comboBox_treatment.currentText()

        if treatment in nhi_utils.MASSAGE_TREAT:
            treat = '健保傷科處置'
        else:
            treat = '健保針灸處置'

        self.parent.open_dictionary(self.medicine_set, treat)

    def _set_prescript_remark(self):
        row = prescript_utils.get_prescript_remark_row(self.parent, self.database, self.case_key)
        if row is None:
            return

        self.append_null_medicine()
        self.append_prescript(row, 0)

    def _open_treat_time_dialog(self):
        treatment = self.ui.comboBox_treatment.currentText()
        second_treatment = self.ui.comboBox_second_treatment.currentText()

        dialog = dialog_utils.get_dialog_treat_time(
            self, self.database, self.system_settings, self.diag_date, treatment, second_treatment,
        )
        if not dialog.exec_():
            dialog.deleteLater()
            return

        self._clear_treat_time()
        treat_time_list = dialog.treat_time_list
        for item in treat_time_list:
            row = {
                'MedicineType': '處置',
                'MedicineKey': None,
                'InsCode': None,
                'MedicineName': item
            }
            self.append_null_treat()
            self.append_treat(row)

        dialog.deleteLater()

    def _open_treat_position_dialog(self):
        treatment = self.ui.comboBox_treatment.currentText()

        dialog = dialog_utils.get_dialog_treat_position(
            self, self.database, self.system_settings, treatment, self.ui.tableWidget_treat
        )
        if not dialog.exec_():
            dialog.deleteLater()
            return

        self._clear_treat_position()
        treat_position_list = dialog.treat_position_list
        for check_box in treat_position_list:
            if check_box.isChecked():
                row = {
                    'MedicineType': '處置',
                    'MedicineKey': None,
                    'InsCode': None,
                    'MedicineName': f'治療部位:{check_box.text()}',
                }
                self.append_null_treat()
                self.append_treat(row)

        dialog.deleteLater()

    def _open_treat_auxiliary_dialog(self):
        treatment = self.ui.comboBox_treatment.currentText()

        dialog = dialog_utils.get_dialog_treat_auxiliary(
            self, self.database, self.system_settings, treatment, self.ui.tableWidget_treat
        )
        if not dialog.exec_():
            dialog.deleteLater()
            return

        self._clear_treat_auxiliary()

        treat_auxiliary_list = dialog.treat_auxiliary_list
        for check_box in treat_auxiliary_list:
            if check_box.isChecked():
                row = {
                    'MedicineType': '處置',
                    'MedicineKey': None,
                    'InsCode': None,
                    'MedicineName': f'輔助治療:{check_box.text()}',
                }
                self.append_null_treat()
                self.append_treat(row)

        dialog.deleteLater()

    def _prescript_cell_clicked(self):
        if self.system_settings.field('不要自動切換輸入法') == 'Y':     
            pass
        else:
            system_utils.set_keyboard_layout('英文')

    def _prescript_item_selection_changed(self):
        self.ui.toolButton_remove_medicine.setEnabled(True)
        self.ui.toolButton_clear_medicine.setEnabled(True)
        self.ui.toolButton_dosage.setEnabled(True)
        self.ui.toolButton_medicine_info.setEnabled(True)
        self.ui.toolButton_open_medicine_library.setEnabled(True)
        self.ui.toolButton_show_costs.setEnabled(True)
        self.ui.toolButton_copy.setEnabled(True)

        if (self.call_from != '醫師看診作業' and
                self.user_name != '超級使用者' and
                personnel_utils.get_permission(self.database, '病歷資料', '病歷修正', self.user_name) != 'Y'):
            enabled = False
        elif self.ui.tableWidget_prescript.item(0, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']) is None:
            enabled = False
        else:
            enabled = True

        self.ui.toolButton_remove_medicine.setEnabled(enabled)
        self.ui.toolButton_clear_medicine.setEnabled(enabled)
        self.ui.toolButton_dosage.setEnabled(enabled)
        self.ui.toolButton_medicine_info.setEnabled(enabled)
        self.ui.toolButton_open_medicine_library.setEnabled(enabled)
        self.ui.toolButton_show_costs.setEnabled(enabled)
        self.ui.toolButton_set_prescript_remark.setEnabled(enabled)
        self.ui.toolButton_copy.setEnabled(enabled)
        self.ui.toolButton_copy_to_append.setEnabled(enabled)

        # medicine_key_item = self.ui.tableWidget_prescript.item(
        #     self.ui.tableWidget_prescript.currentRow(),
        #     prescript_utils.INS_PRESCRIPT_COL_NO['MedicineKey']
        # )
        # if medicine_key_item is None:
        #     return

        # description = prescript_utils.get_medicine_description(self.database, medicine_key_item.text())
        # if description is None:
        #     self.ui.toolButton_medicine_info.setEnabled(False)

    def _prescript_item_changed(self, item):
        if item is None:
            return

        col_no = item.column()

        if col_no == prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']:
            self._set_total_dosage()
            self._set_total_cost()
            # if self.parent.medical_record is not None and \
            #     (string_utils.xstr(self.parent.medical_record['Share']) in nhi_utils.INFECTIOUS_TYPE or
            #      string_utils.xstr(self.parent.medical_record['Injury']) in nhi_utils.INFECTIOUS_TYPE):
            #     self.parent.calculate_ins_fees()
        elif col_no == prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']:
            medicine_name = item.text()
            if '清冠一號' in medicine_name:
                self.parent.calculate_ins_fees()
        elif col_no == prescript_utils.INS_PRESCRIPT_COL_NO['Instruction']:
            self._set_dosage_percent()

    def _open_dosage(self):
        medicine_name_item = self.ui.tableWidget_prescript.item(
            0, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']
        )
        if medicine_name_item is None:
            return

        self.ui.tableWidget_prescript.setCurrentCell(0, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage'])
        self._open_prescript_dialog()

    def _open_prescript_dialog(self):
        prescript_utils.open_prescript_dialog(
            self, self.database, self.system_settings, self.ui.tableWidget_prescript, '健保'
        )

    def _set_total_dosage(self):
        total_dosage, _ = prescript_utils.get_total_dosage(
            self.ui.tableWidget_prescript, database=self.database, medicine_set=1)
        self.ui.label_total_dosage.setText(f'總量: {total_dosage:.1f}')

    def _set_total_cost(self):
        if self.no_ins_cost == 'Y':
            self.ui.label_total_costs.setText(None)
            return

        total_costs = self._calculate_total_costs()

        if total_costs == 0:
            self.ui.label_total_costs.setText(None)
        else:
            self.ui.label_total_costs.setText(f'({total_costs:.1f})')

    def check_total_dosage(self, current_row=None, check_type='input'):
        if check_type == 'input' and self.check_total_dosage_event == '存檔時檢查':
            return True

        if self.dosage_limitation is None or self.dosage_limitation <= 0:  # 未設定, 不檢查
            return True

        if current_row is None:
            current_row = self.ui.tableWidget_prescript.currentRow()

        total_dosage, _ = prescript_utils.get_total_dosage(
            self.ui.tableWidget_prescript, database=self.database, medicine_set=1)

        if total_dosage <= self.dosage_limitation:  # 未超過劑量上限
            return True

        if self.parent.medical_record['Injury'] in nhi_utils.INFECTIOUS_TYPE or \
           self.parent.medical_record['Share'] in nhi_utils.INFECTIOUS_TYPE:  # 確診病歷不設限
            return True

        col_no = prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']
        self.ui.tableWidget_prescript.setCurrentCell(current_row, col_no)
        self.ui.tableWidget_prescript.setItem(
            current_row, col_no, QtWidgets.QTableWidgetItem('')
        )
        self._set_dosage_format(current_row, col_no)

        system_utils.show_message_box(
            QtWidgets.QMessageBox.Critical,
            '劑量檢查',
            f'''<font size="5" color="red">
                 <b>給藥超過系統設定{self.dosage_limitation}克的劑量上限, 請重新調整劑量.</b>
               </font>
            ''',
            '請重新調整劑量, 或更改系統設定的劑量上限.'
        )
        total_dosage, _ = prescript_utils.get_total_dosage(
            self.ui.tableWidget_prescript, database=self.database, medicine_set=1)
        self.ui.label_total_dosage.setText(f'總量: {total_dosage:.1f}')

        return False

    def check_total_costs(self, current_row=None, check_type='input'):
        if check_type == 'input' and self.check_total_costs_event == '存檔時檢查':
            return True

        if self.ins_drug_fee_limitation is None or self.ins_drug_fee_limitation <= 0:  # 未設定, 不檢查
            return True

        if current_row is None:
            current_row = self.ui.tableWidget_prescript.currentRow()

        total_costs = self._calculate_total_costs()

        if total_costs <= self.ins_drug_fee_limitation:  # 未超過劑量上限
            return True

        if self.parent.medical_record['Injury'] in nhi_utils.INFECTIOUS_TYPE or \
           self.parent.medical_record['Share'] in nhi_utils.INFECTIOUS_TYPE:  # 確診病歷不設限
            return True

        col_no = prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']
        self.ui.tableWidget_prescript.setCurrentCell(current_row, col_no)
        self.ui.tableWidget_prescript.setItem(
            current_row, col_no, QtWidgets.QTableWidgetItem('')
        )
        self._set_dosage_format(current_row, col_no)

        system_utils.show_message_box(
            QtWidgets.QMessageBox.Critical,
            '健保用藥成本檢查',
            f'''<font size="5" color="red">
                 <b>健保用藥成本超過系統設定{self.ins_drug_fee_limitation}元的成本上限, 請重新調整.</b>
               </font>
            ''',
            '請重新調整處方, 或更改系統設定的健保用藥成本上限.'
        )

        total_costs = self._calculate_total_costs()
        self.ui.label_total_costs.setText(f'({total_costs:.1f})')

        return False

    def _calculate_total_costs(self):
        total_costs = 0.0
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            dosage_item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage'])
            if dosage_item is None:
                continue

            medicine_key_item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineKey'])
            if medicine_key_item is None:
                continue

            medicine_key = medicine_key_item.text()
            if medicine_key == '':
                continue

            sql = f'''
                SELECT InPrice FROM medicine
                WHERE
                    MedicineKey = {medicine_key}
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                continue

            cost = number_utils.get_float(rows[0]['InPrice'])
            try:
                dosage = number_utils.get_float(dosage_item.text())
            except ValueError:
                dosage = 0

            total_costs += dosage * cost

        return total_costs

    def _show_costs(self):
        pres_days = number_utils.get_integer(self.ui.comboBox_pres_days.currentText())
        if pres_days <= 0:
            pres_days = 1

        html = prescript_utils.get_costs_html(
            self.database, self.ui.tableWidget_prescript, pres_days,
            prescript_utils.INS_PRESCRIPT_COL_NO
        )
        dialog = dialog_utils.get_dialog_rich_text(
            self, self.database, self.system_settings, 'html', None, html
        )
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

    def _clear_medical_record(self):
        self.parent.clear_medical_record()

        if self.parent.clear_medical_record_option:
            self._clear_medicine()
            self._clear_treat()

            self.parent.ui.textEdit_symptom.setFocus()

    def _clear_medicine(self, warning=False):
        if self.ui.tableWidget_prescript.rowCount() <= 0:
            return

        if warning:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle('清除處方資料')
            msg_box.setText("<font size='4' color='red'><b>確定清除全部的處方?</b></font>")
            msg_box.setInformativeText("注意！處方清除後, 將無法回復!")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            clear_medicine = msg_box.exec_()
            if clear_medicine:
                return

        self.ui.tableWidget_prescript.setRowCount(0)
        self.ui.comboBox_package.setCurrentText(None)
        self.ui.comboBox_pres_days.setCurrentText(None)
        self.ui.comboBox_instruction.setCurrentText(None)
        self.ui.toolButton_add_medicine.animateClick()

    def _clear_treat(self, warning=False):
        if self.ui.comboBox_treatment.currentText() == '':
            return

        if warning:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle('清除處置資料')
            msg_box.setText("<font size='4' color='red'><b>確定清除全部的處置?</b></font>")
            msg_box.setInformativeText("注意！處置清除後, 將無法回復!")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            clear_treat = msg_box.exec_()
            if clear_treat:
                return

        self.ui.comboBox_treatment.setCurrentIndex(0)

    def _show_acupuncture_point(self):
        dialog = dialog_utils.get_dialog_acupuncture_point(self, self.database, self.system_settings)
        if not dialog.exec_():
            dialog.deleteLater()
            return

        acupuncture_point_list = dialog.acupuncture_point_list
        dialog.deleteLater()

        if len(acupuncture_point_list) <= 0:
            return

        self.ui.comboBox_treatment.setCurrentText('針灸治療')
        row = {
            'MedicineType': '穴道',
            'MedicineKey': None,
            'InsCode': None
        }

        for acupuncture_point in acupuncture_point_list:
            row['MedicineName'] = acupuncture_point
            self.append_null_treat()
            self.append_treat(row)

    # 拷貝健保處方至自費處方
    def _copy_prescript(self):
        new_tab = self.parent.tab_list[1]
        if new_tab is None:
            return

        new_tab.copy_from_ins_prescript(
            self.ui.tableWidget_prescript,
            self.ui.comboBox_package,
            self.ui.comboBox_pres_days,
            self.ui.comboBox_instruction,
            self.ui.doubleSpinBox_total_dosage,
        )
        self.parent.tabWidget_prescript.setCurrentIndex(1)
        new_tab.append_null_medicine()

    # 拷貝健保處方至新增自費處方
    def _copy_to_append_prescript(self):
        new_tab = self.parent.add_prescript_tab()
        new_tab.copy_from_ins_prescript(
            self.ui.tableWidget_prescript,
            self.ui.comboBox_package,
            self.ui.comboBox_pres_days,
            self.ui.comboBox_instruction,
            self.ui.doubleSpinBox_total_dosage,
        )
        self.parent.tabWidget_prescript.setCurrentIndex(self.parent.tabWidget_prescript.count()-1)
        new_tab.append_null_medicine()

    def copy_from_self_prescript(self, table_widget_self_prescript,
                                 packages, pres_days, instruction, total_dosage):
        warning_count = 0
        for row_no in range(table_widget_self_prescript.rowCount()):
            row = dict()
            medicine_key_item = table_widget_self_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['MedicineKey'])
            if medicine_key_item is None:
                continue
            medicine_name = table_widget_self_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['MedicineName']).text()
            if medicine_name in ['自費粉藥', '自費水藥']:
                continue

            medicine_key = medicine_key_item.text()
            row['MedicineKey'] = medicine_key
            row['MedicineType'] = table_widget_self_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['MedicineType']).text()
            row['Price'] = table_widget_self_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['Price']).text()
            row['Amount'] = table_widget_self_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['Amount']).text()
            row['InsCode'] = table_widget_self_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['InsCode']).text()
            row['MedicineName'] = medicine_name
            row['Unit'] = table_widget_self_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['Unit']).text()
            row['Instruction'] = table_widget_self_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['Instruction']).text()
            dosage = table_widget_self_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['Dosage']).text()

            if row['InsCode'] == '':
                row['InsCode'] = prescript_utils.get_medicine_field(
                    self.database, medicine_key, 'InsCode'
                )

            if row['MedicineType'] in ['穴道', '處置']:
                if self.ui.comboBox_treatment.currentText() == '':
                    if row['MedicineType'] in ['穴道']:
                        self.ui.comboBox_treatment.setCurrentText('針灸治療')
                    else:
                        self.ui.comboBox_treatment.setCurrentText('傷科治療')

                self.append_null_treat()
                self.append_treat(row)
            else:
                self.append_null_medicine()
                if warning_count >= 1:  # 顯示過就不要再顯示提醒
                    show_warning = False
                else:
                    show_warning = True
                    
                if not self.append_prescript(
                        row, dosage,set_dosage_percent=False, duplicate_warning=show_warning):
                    warning_count += 1
                    self.append_null_medicine()
                    continue

                self._set_dosage_format(row_no, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage'])

        self.ui.doubleSpinBox_total_dosage.setValue(total_dosage)

        self.ui.comboBox_package.setCurrentText(packages)
        self.ui.comboBox_pres_days.setCurrentText(pres_days)
        self.ui.comboBox_instruction.setCurrentText(instruction)

        if self.ui.comboBox_treatment.currentText() == '':
            self.ui.tableWidget_prescript.setCurrentCell(
                self.ui.tableWidget_prescript.rowCount()-1, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']
            )

        self.parent.tabWidget_prescript.setCurrentIndex(0)

    def _set_pharmacy(self):
        if self.ui.checkBox_pharmacy.isChecked():
            pharmacy_type = '申報'
        else:
            pharmacy_type = '不申報'

        self.parent.tab_registration.comboBox_pharmacy_type.setCurrentText(pharmacy_type)
        self.parent.calculate_ins_fees()

    def _set_instruction(self):
        dialog = dialog_utils.get_dialog_instruction(self, self.database, self.system_settings)
        if not dialog.exec_():
            dialog.deleteLater()
            return

        instruction = dialog.get_instruction()
        if instruction != '':
            self.ui.comboBox_instruction.setCurrentText(instruction)

        dialog.deleteLater()

    def _open_dialog_compound_json(self):
        dialog = dialog_utils.get_dialog_compound_json(
            self, self.database, self.system_settings, self.medicine_set,
            self.ui.tableWidget_prescript,
        )
        dialog.exec_()
        dialog.deleteLater()

    def _insert_compound(self):
        dialog = dialog_utils.get_dialog_insert_compound(
            self, self.database, self.system_settings, self.ui.tableWidget_prescript,
        )
        dialog.exec_()
        dialog.deleteLater()

    def _print_receipt_clicked(self, checked, prompt_warning=True):
        if checked and prompt_warning:
            reply = QMessageBox.question(
                self,
                "確認不印",
                "您確定要設定不印健保單據嗎？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                self.ui.checkBox_print_receipt.blockSignals(True)
                self.ui.checkBox_print_receipt.setChecked(False)
                self.ui.checkBox_print_receipt.blockSignals(False)
                self.ui.checkBox_print_receipt.setStyleSheet(None)
                return  # 提早結束，避免下面再設定紅色樣式

        # 勾選時變紅色，否則清除樣式
        style_sheet = 'color: red; font-weight: bold' if checked else None
        self.ui.checkBox_print_receipt.setStyleSheet(style_sheet)

