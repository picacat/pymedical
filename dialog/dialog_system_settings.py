# -*- coding: utf-8 -*-
"""系統設定."""

import json
import os

from classes import table_widget
from libs import (alleypin_utils, class_utils, dialog_utils, nhi_utils,
                  number_utils, printer_utils, registration_utils,
                  string_utils, system_utils, ui_utils)
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QInputDialog


class DialogSystemSettings(QtWidgets.QDialog):
    """系統設定."""

    def __init__(self, parent=None, *args):
        """初始化."""
        super(DialogSystemSettings, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_settings()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_SETTINGS, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.tabWidget_settings.setCurrentIndex(0)
        self._set_combo_box()
        self.table_widget_station_list = class_utils.get_table_widget(
            self.ui.tableWidget_station_list, self.database,
        )
        self.table_widget_start_no = class_utils.get_table_widget(
            self.ui.tableWidget_start_no, self.database,
        )
        self.table_widget_bulletin = class_utils.get_table_widget(
            self.ui.tableWidget_bulletin, self.database,
        )
        self.table_widget_notice = class_utils.get_table_widget(
            self.ui.tableWidget_notice, self.database,
        )
        self._start_no_changed()
        self._set_table_widget_width()

        system_utils.disable_mouse_wheel(self, QtWidgets.QComboBox)
        system_utils.disable_mouse_wheel(self, QtWidgets.QSpinBox)
        system_utils.disable_mouse_wheel(self, QtWidgets.QDoubleSpinBox)
        system_utils.disable_mouse_wheel(self, QtWidgets.QDateTimeEdit)

        self.ui.tableWidget_bulletin._sorter = table_widget.TableDragDropSorter(
            self.ui.tableWidget_bulletin
        )
        self.ui.tableWidget_notice._sorter = table_widget.TableDragDropSorter(
            self.ui.tableWidget_notice
        )

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.button_accepted)
        self.ui.buttonBox.rejected.connect(self.button_rejected)
        self.ui.spinBox_station_no.valueChanged.connect(self.spin_button_value_changed)
        self.ui.toolButton_emr_path.clicked.connect(self._get_emr_path)
        self.ui.toolButton_get_dir.clicked.connect(self._get_clinic_dir)
        self.ui.toolButton_get_external_dir.clicked.connect(self._get_external_dir)
        self.ui.toolButton_get_database_physical_dir.clicked.connect(self._get_database_physical_dir)
        self.ui.toolButton_get_database_dir.clicked.connect(self._get_database_dir)
        self.ui.toolButton_get_image_path.clicked.connect(self._get_image_path)
        self.ui.toolButton_electronic_prescript_path.clicked.connect(self._get_electronic_prescript_path)
        self.ui.toolButton_cashier_machine_path.clicked.connect(self._get_cashier_machine_path)
        self.ui.toolButton_blood_measure_path.clicked.connect(self._get_blood_measure_path)
        self.ui.pushButton_detect_com_port.clicked.connect(self._detect_com_port)

        self.ui.radioButton_reg_normal.clicked.connect(self._set_area_combo_box)
        self.ui.radioButton_reg_home_care.clicked.connect(self._set_area_combo_box)
        self.ui.radioButton_reg_long_term_care.clicked.connect(self._set_area_combo_box)
        self.ui.radioButton_reg_far.clicked.connect(self._set_area_combo_box)
        self.ui.radioButton_reg_mountain.clicked.connect(self._set_area_combo_box)
        self.ui.radioButton_reg_island.clicked.connect(self._set_area_combo_box)
        self.ui.radioButton_reg_correction.clicked.connect(self._set_area_combo_box)
        self.ui.comboBox_resource.currentTextChanged.connect(self._set_area_combo_box)

        self.ui.toolButton_add_start_no.clicked.connect(self._add_start_no)
        self.ui.toolButton_remove_start_no.clicked.connect(self._remove_start_no)
        self.ui.toolButton_edit_start_no.clicked.connect(self._edit_start_no)

        self.ui.toolButton_refresh.clicked.connect(self._read_settings)

        self.ui.tableWidget_start_no.itemSelectionChanged.connect(self._start_no_changed)
        self.ui.comboBox_division.currentTextChanged.connect(self._set_area_combo_box)

        # self.ui.checkBox_print_total_dosage.clicked.connect(self._check_print_total_dosage)  # TODO
        # self.ui.checkBox_print_ins_total_dosage.clicked.connect(self._check_print_ins_total_dosage)  # TODO

        self.ui.pushButton_webhook.clicked.connect(self._add_webhook)

        self.ui.toolButton_add_bulletin.clicked.connect(self._add_web_bulletin)
        self.ui.toolButton_remove_bulletin.clicked.connect(self._remove_web_bulletin)
        self.ui.toolButton_edit_bulletin.clicked.connect(self._edit_web_bulletin)
        self.ui.tableWidget_bulletin.doubleClicked.connect(self._edit_web_bulletin)

        self.ui.toolButton_add_notice.clicked.connect(self._add_notice)
        self.ui.toolButton_remove_notice.clicked.connect(self._remove_notice)
        self.ui.toolButton_edit_notice.clicked.connect(self._edit_notice)
        self.ui.checkBox_new_opening.clicked.connect(self._set_new_clinic_smart_card)

    def _set_new_clinic_smart_card(self):
        if self.ui.checkBox_new_opening.isChecked():
            self.ui.checkBox_new_clinic_smart_card.setEnabled(True)
        else:
            self.ui.checkBox_new_clinic_smart_card.setEnabled(False)
            self.ui.checkBox_new_clinic_smart_card.setChecked(False)

    # def _check_print_total_dosage(self):  # TODO
    #     if self.ui.checkBox_print_total_dosage.isChecked():
    #         self.ui.checkBox_print_ins_total_dosage.setChecked(False)

    # def _check_print_ins_total_dosage(self):  # TODO
    #     if self.ui.checkBox_print_ins_total_dosage.isChecked():
    #         self.ui.checkBox_print_total_dosage.setChecked(False)

    # def eventFilter(self, source, event):
    #     if (event.type() == QtCore.QEvent.Wheel and isinstance(source, QtWidgets.QComboBox)):
    #         return True

    #     return super(DialogSystemSettings, self).eventFilter(source, event)

    def _set_combo_box(self):
        ui_utils.set_combo_box(
            self.ui.comboBox_theme,
            QtWidgets.QStyleFactory.keys()
        )
        ui_utils.set_combo_box(self.ui.comboBox_division, nhi_utils.DIVISION)
        ui_utils.set_instruction_combo_box(self.database, self.ui.comboBox_instruction)
        ui_utils.set_combo_box(self.ui.comboBox_color, ['紅色', '綠色', '藍色', '灰色', '自訂1'])
        ui_utils.set_combo_box(self.ui.comboBox_medical_record_page, ['版面1', '版面2'])
        ui_utils.set_combo_box(self.ui.comboBox_disease_layout, ['版面1', '版面2'])

        ui_utils.set_combo_box(self.ui.comboBox_ins_receipt_size_unit, ['英吋', '毫米'], '英吋')
        ui_utils.set_combo_box(self.ui.comboBox_ins_receipt_margin_unit, ['英吋', '毫米'], '毫米')
        ui_utils.set_combo_box(self.ui.comboBox_self_receipt_size_unit, ['英吋', '毫米'], '英吋')
        ui_utils.set_combo_box(self.ui.comboBox_self_receipt_margin_unit, ['英吋', '毫米'], '毫米')

        ui_utils.set_combo_box(
            self.ui.comboBox_led_port,
            ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_scale_port,
            ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
        )
        ui_utils.set_combo_box(self.ui.comboBox_disease_group, ['常用病名', '所有病名', '自訂病名', '傷骨科'])
        ui_utils.set_combo_box(self.ui.comboBox_default_treat_type, ['內科', '一般針灸', '一般傷科'], '內科')

        self._set_combo_box_printer()

        ui_utils.set_combo_box_item_color(
            self.ui.comboBox_color, [
                QtGui.QBrush(QtCore.Qt.red),
                QtGui.QBrush(QtCore.Qt.darkGreen),
                QtGui.QBrush(QtCore.Qt.blue),
                QtGui.QBrush(QtCore.Qt.darkGray),
            ]
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_resource,
            nhi_utils.RESOURCE_TYPE,
        )
        rate_type = ['%', '$']
        ui_utils.set_combo_box(self.ui.comboBox_ins_diag_rate_type, rate_type)
        ui_utils.set_combo_box(self.ui.comboBox_ins_treat_rate_type, rate_type)
        ui_utils.set_combo_box(self.ui.comboBox_self_drug_rate_type, rate_type)
        ui_utils.set_combo_box(self.ui.comboBox_self_treat_rate_type, rate_type)

    def _set_table_widget_width(self):
        width = [90, 150, 150, 100, 100, 120, 220, 70]
        self.table_widget_station_list.set_table_heading_width(width)

        width = [100, 130, 130, 130]
        self.table_widget_start_no.set_table_heading_width(width)

        width = [200, 400]
        self.table_widget_bulletin.set_table_heading_width(width)

        self.table_widget_notice.set_table_heading_width([560])

    def _set_area_combo_box(self):
        self._set_correction_combo_box()
        self._set_tour_combo_box()
        self._set_resource_combo_box()

    def _set_tour_combo_box(self):
        self.ui.comboBox_tour_area.clear()
        self.ui.label_tour_area.setEnabled(False)
        self.ui.comboBox_tour_area.setEnabled(False)

        if not self.ui.radioButton_reg_mountain.isChecked() and \
           not self.ui.radioButton_reg_far.isChecked() and \
           not self.ui.radioButton_reg_island.isChecked():
            return

        if self.ui.radioButton_reg_mountain.isChecked():
            regist_type = '巡迴山地'
        elif self.ui.radioButton_reg_far.isChecked():
            regist_type = '巡迴偏遠'
        elif self.ui.radioButton_reg_island.isChecked():
            regist_type = '巡迴離島'

        tour_area_list = nhi_utils.get_area_list(regist_type)
        self.ui.label_tour_area.setEnabled(True)
        self.ui.comboBox_tour_area.setEnabled(True)
        ui_utils.set_combo_box(self.ui.comboBox_tour_area, tour_area_list, None)

        self.ui.comboBox_resource.setCurrentText('一般')

    def _set_correction_combo_box(self):
        current_text = self.ui.comboBox_correction_area.currentText()

        self.ui.comboBox_correction_area.clear()

        division = self.ui.comboBox_division.currentText()
        correction_area_list = nhi_utils.get_area_list('矯正機關內門診', division)

        ui_utils.set_combo_box(self.ui.comboBox_correction_area, correction_area_list, current_text)

    def _set_resource_combo_box(self):
        if not self.ui.radioButton_reg_normal.isChecked():
            return

        self.ui.comboBox_tour_area.clear()
        self.ui.label_tour_area.setEnabled(False)
        self.ui.comboBox_tour_area.setEnabled(False)

        regist_type = self.ui.comboBox_resource.currentText()
        if regist_type not in ['前往資源不足地區']:
            return

        tour_area_list = nhi_utils.get_area_list(regist_type)
        self.ui.label_tour_area.setEnabled(True)
        self.ui.comboBox_tour_area.setEnabled(True)
        ui_utils.set_combo_box(self.ui.comboBox_tour_area, tour_area_list, None)

    def _set_combo_box_printer(self):
        printer_list = printer_utils.get_printer_list()
        print_mode = printer_utils.PRINT_MODE

        ui_utils.set_combo_box(self.ui.comboBox_regist_printer, printer_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_reservation_printer, printer_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_ins_prescript_printer, printer_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_self_prescript_printer, printer_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_ins_receipt_printer, printer_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_self_receipt_printer, printer_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_bag_printer, printer_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_massage_printer, printer_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_massage_printer2, printer_list, None)

        ui_utils.set_combo_box(self.ui.comboBox_misc_printer, printer_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_misc2_printer, printer_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_misc3_printer, printer_list, None)

        ui_utils.set_combo_box(self.ui.comboBox_report_printer, printer_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_report_printer_paper_size, printer_utils.PAPER_SIZE, None)

        for combo_box in self.findChildren(QtWidgets.QComboBox):
            combo_box.setView(QtWidgets.QListView())

        ui_utils.set_combo_box(
            self.ui.comboBox_regist_form,
            printer_utils.PRINT_REGISTRATION_FORM, None
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_massage_form,
            printer_utils.PRINT_MASSAGE_FORM, None
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_reservation_form,
            printer_utils.PRINT_RESERVATION_FORM, None
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_ins_prescript_form,
            printer_utils.PRINT_PRESCRIPTION_INS_FORM, None
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_self_prescript_form,
            printer_utils.PRINT_PRESCRIPTION_SELF_FORM, None
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_ins_receipt_form,
            printer_utils.PRINT_RECEIPT_INS_FORM, None
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_self_receipt_form,
            printer_utils.PRINT_RECEIPT_SELF_FORM, None
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_misc_form,
            printer_utils.PRINT_MISC_FORM, None
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_misc2_form,
            printer_utils.PRINT_MISC_FORM, None
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_misc3_form,
            printer_utils.PRINT_MISC_FORM, None
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_bag_form,
            printer_utils.PRINT_PRESCRIPTION_BAG_FORM, None
        )

        ui_utils.set_combo_box(self.ui.comboBox_regist_print_mode, print_mode, None)
        ui_utils.set_combo_box(self.ui.comboBox_reservation_print_mode, print_mode, None)
        ui_utils.set_combo_box(self.ui.comboBox_ins_prescript_print_mode, print_mode, None)
        ui_utils.set_combo_box(self.ui.comboBox_self_prescript_print_mode, print_mode, None)
        ui_utils.set_combo_box(self.ui.comboBox_ins_receipt_print_mode, print_mode, None)
        ui_utils.set_combo_box(self.ui.comboBox_self_receipt_print_mode, print_mode, None)
        ui_utils.set_combo_box(self.ui.comboBox_bag_print_mode, print_mode, None)
        ui_utils.set_combo_box(self.ui.comboBox_massage_print_mode, printer_utils.PRINT_MODE2, None)
        ui_utils.set_combo_box(self.ui.comboBox_misc_print_mode, print_mode, None)
        ui_utils.set_combo_box(self.ui.comboBox_misc2_print_mode, print_mode, None)
        ui_utils.set_combo_box(self.ui.comboBox_misc3_print_mode, print_mode, None)

        ui_utils.set_combo_box(self.ui.comboBox_report_print_mode, print_mode, None)

    ###################################################################################################################
    # 讀取設定檔
    def _read_settings(self):
        self._read_clinic_settings()
        self._read_charge_settings()
        self._read_regist_no_settings()
        self._read_registration_settings()
        self._read_doctor_settings()
        self._read_printer_settings()
        self._read_reader_settings()
        self._read_misc()
        self._read_station_list()
        self._read_bulletin()
        self._read_notice()

    # 讀取院所設定
    def _read_clinic_settings(self):
        self.ui.lineEdit_clinic_name.setText(self.system_settings.field('院所名稱'))
        self.ui.lineEdit_clinic_id.setText(self.system_settings.field('院所代號'))
        self.ui.lineEdit_invoice_no.setText(self.system_settings.field('統一編號'))
        self.ui.lineEdit_owner.setText(self.system_settings.field('負責醫師'))
        self.ui.lineEdit_owner_cert.setText(self.system_settings.field('醫師證號'))
        self.ui.lineEdit_clinic_cert.setText(self.system_settings.field('開業證號'))
        self.ui.lineEdit_telephone.setText(self.system_settings.field('院所電話'))
        self.ui.lineEdit_address.setText(self.system_settings.field('院所地址'))
        self.ui.lineEdit_email.setText(self.system_settings.field('電子郵件'))
        self.ui.lineEdit_period1.setText(self.system_settings.field('早班時間'))
        self.ui.lineEdit_period2.setText(self.system_settings.field('午班時間'))
        self.ui.lineEdit_period3.setText(self.system_settings.field('晚班時間'))
        self.ui.spinBox_nurse.setValue(number_utils.get_integer(self.system_settings.field('護士人數')))
        self.ui.spinBox_pharmacist.setValue(number_utils.get_integer(self.system_settings.field('藥師人數')))

        self._set_check_box(self.ui.checkBox_pharmacy_fee, '申報藥事服務費')
        self._set_check_box(self.ui.checkBox_init_fee, '申報初診照護')
        self._set_check_box(self.ui.checkBox_new_opening, '新特約期間')
        self._set_check_box(self.ui.checkBox_new_clinic_smart_card, '新特約期間使用晶片讀卡機')

        if self.ui.checkBox_new_opening.isChecked():
            self.ui.checkBox_new_clinic_smart_card.setEnabled(True)
        else:
            self.ui.checkBox_new_clinic_smart_card.setEnabled(False)
            self.ui.checkBox_new_clinic_smart_card.setChecked(False)

        self._set_check_box(self.ui.checkBox_acupuncture_cert, '針灸認證合格')
        self._set_check_box(self.ui.checkBox_no_highly_massage, '不申報高度複雜性傷科')        
        self._set_check_box(self.ui.checkBox_pres_days_duplicated, '當日用藥重複檢查次日起算')
        self._set_check_box(self.ui.checkBox_check_injury_period, '檢查損傷診斷碼')
        self._set_check_box(self.ui.checkBox_check_same_disease_pres_days, '檢查相同診斷碼用藥天數')
        self._set_check_box(self.ui.checkBox_check_duplicate_2_days, '用藥重複二日不能存檔')

        self._set_check_box(self.ui.checkBox_ins_prescript_only, '健保自費分開')
        self._set_check_box(self.ui.checkBox_single_self_case, '同自費只算一筆')

        self._set_check_box(self.ui.checkBox_no_convert_general_treat, '不要轉換一般針灸')
        self._set_check_box(self.ui.checkBox_cellphone_required, '行動電話必填')
        self._set_check_box(self.ui.checkBox_only_ins_case, '病歷查詢預設健保')
        self._set_check_box(self.ui.checkBox_yesterday, '日期查詢預設為昨日')
        self._set_check_box(self.ui.checkBox_show_total, '病歷查詢顯示合計')
        self._set_check_box(self.ui.checkBox_regist_yesterday_diag, '隔日過卡不能存檔')
        self._set_check_box(self.ui.checkBox_diagnostic_data_required, '診斷資料必填')
        self._set_check_box(self.ui.checkBox_show_disease4, '顯示次診斷3')
        self._set_check_box(self.ui.checkBox_ins_dosage_non_zero, '健保開藥劑量必須大於0')
        self._set_check_box(self.ui.checkBox_same_disease_course2, '療程同病名超過兩個')
        self._set_check_box(self.ui.checkBox_strict_special_code, '慢性病開藥檢查')

        self._set_date_edit(self.ui.dateEdit_acupuncture_date, '針灸認證合格日期')
        self._set_date_edit(self.ui.dateEdit_ins_judge_init_date, '電子化抽審初診日期')
        self._set_date_edit(self.ui.dateEdit_new_init_date, '新診所初診日期')

        self.ui.comboBox_division.setCurrentText(self.system_settings.field('健保業務'))
        self.ui.spinBox_dosage_limitation.setValue(number_utils.get_integer(self.system_settings.field('劑量上限')))
        self.ui.spinBox_dosage_minimum.setValue(number_utils.get_integer(self.system_settings.field('最低劑量')))
        self.ui.spinBox_dosage_minimum2.setValue(number_utils.get_integer(self.system_settings.field('6歲以下最低劑量')))

        self.ui.spinBox_default_self_prescript_tab.setValue(
            number_utils.get_integer(self.system_settings.field('預設空白自費頁')))

        self.ui.spinBox_ins_drug_fee_limitation.setValue(
            number_utils.get_integer(self.system_settings.field('健保用藥成本上限')))
        self.ui.comboBox_resource.setCurrentText(self.system_settings.field('資源類別'))

        self.ui.spinBox_case_page_count.setValue(
            number_utils.get_integer(self.system_settings.field('病歷查詢一頁筆數')))

        self._set_radio_button(
            [
                self.ui.radioButton_reg_normal,
                self.ui.radioButton_reg_home_care,
                self.ui.radioButton_reg_long_term_care,
                self.ui.radioButton_reg_far,
                self.ui.radioButton_reg_mountain,
                self.ui.radioButton_reg_island,
                self.ui.radioButton_reg_correction
            ],
            ['一般門診', '居家醫療', '照護機構中醫照護', '巡迴偏遠', '巡迴山地', '巡迴離島', '矯正機關內門診'],
            '掛號類別'
        )
        self._set_area_combo_box()
        self.ui.comboBox_tour_area.setCurrentText(self.system_settings.field('巡迴區域'))
        self.ui.comboBox_correction_area.setCurrentText(self.system_settings.field('矯正機關'))

        self._set_radio_button(
            [
                self.ui.radioButton_ic_xml1,
                self.ui.radioButton_ic_xml2,
            ],
            ['1.0', '2.0'],
            '健保IC卡資料上傳格式'
        )
        self._set_radio_button(
            [
                self.ui.radioButton_west_date,
                self.ui.radioButton_tw_date,
            ],
            ['西元年', '民國年'],
            '日期格式'
        )
        self._set_radio_button(
            [
                self.ui.radioButton_dialog_model,
                self.ui.radioButton_dialog_popup,
            ],
            ['對話視窗', '彈出式視窗'],
            '詞庫視窗顯示方式'
        )

        self._set_check_box(self.ui.checkBox_check_course_pres_days_once, '檢查療程開藥超過1次')
        self._set_radio_button(
            [
                self.ui.radioButton_once1,
                self.ui.radioButton_once2,
            ],
            ['存檔提醒', '無法存檔'],
            '療程開藥超過1次存檔'
        )

        self._set_check_box(self.ui.checkBox_check_same_disease, '內科同病名超過3次')
        self._set_radio_button(
            [
                self.ui.radioButton_same1,
                self.ui.radioButton_same2,
            ],
            ['存檔提醒', '無法存檔'],
            '內科同病名超過3次存檔'
        )

        self.ui.lineEdit_exam_url.setText(self.system_settings.field('檢驗所伺服器'))
        self.ui.lineEdit_exam_login_id.setText(self.system_settings.field('檢驗所用戶代碼'))
        self.ui.lineEdit_exam_login_pwd.setText(self.system_settings.field('檢驗所密碼'))

        self._set_check_box(self.ui.checkBox_course_disease, '療程不同病名不能存檔')
        self._set_check_box(self.ui.checkBox_medicine_duplicated, '開藥連續三次相同不能存檔')
        self._set_check_box(self.ui.checkBox_medicine_two_times, '療程開藥兩次以上提醒')
        self._set_check_box(self.ui.checkBox_check_receipt_diag_share_fee, '檢查門診負擔多退少補')
        self._set_check_box(self.ui.checkBox_calc_treat_drug, '統計針傷給藥人數')
        self._set_check_box(self.ui.checkBox_no_massage, '不申報傷科治療')
        self._set_check_box(self.ui.checkBox_check_deposit_fee, '欠卡申報點數檢查')

        self._set_radio_button(
            [
                self.ui.radioButton_query_asc,
                self.ui.radioButton_query_desc,
            ],
            ['升冪', '降冪'],
            '病歷查詢日期排序'
        )

        self.ui.spinBox_moderate_acupuncture_time.setValue(
            number_utils.get_integer(self.system_settings.field('預設中度複雜性針灸治療時間')))
        self.ui.spinBox_highly_acupuncture_time.setValue(
            number_utils.get_integer(self.system_settings.field('預設高度複雜性針灸治療時間')))
        self.ui.spinBox_moderate_massage_time.setValue(
            number_utils.get_integer(self.system_settings.field('預設中度複雜性傷科治療時間')))
        self.ui.spinBox_highly_massage_time.setValue(
            number_utils.get_integer(self.system_settings.field('預設高度複雜性傷科治療時間')))

        self.ui.lineEdit_print_massage_address.setText(self.system_settings.field('民俗調理單地址'))
        self.ui.lineEdit_print_massage_remark.setText(self.system_settings.field('民俗調理單備註'))

        self.ui.lineEdit_vhc_token.setText(self.system_settings.field('虛擬健保卡授權憑證'))
        self._set_check_box(self.ui.checkBox_alleypin, 'alleypin')
        self.ui.lineEdit_app_id.setText(self.system_settings.field('appID'))
        self.ui.lineEdit_secret.setText(self.system_settings.field('secret'))
        self.ui.lineEdit_webhook.setText(self.system_settings.field('webhook'))

        self._set_check_box(self.ui.checkBox_hainachuan, 'hainachuan')
        self._set_check_box(self.ui.checkBox_sync_seq_number, '線上看診號同步')
        self._set_check_box(self.ui.checkBox_sync_all_seq_number, '廣播叫號同步所有線上看診號')
        self.ui.lineEdit_webservice.setText(self.system_settings.field('webservice'))
        self.ui.lineEdit_username.setText(self.system_settings.field('預約網站後台帳號'))
        self.ui.lineEdit_password.setText(self.system_settings.field('預約網站後台密碼'))

    # 讀取自費設定
    def _read_charge_settings(self):
        self._set_radio_button(
            [
                self.ui.radioButton_discount_group,
                self.ui.radioButton_discount_individual
            ],
            ['統一折扣', '個別折扣'],
            '自費折扣方式'
        )
        self._set_radio_button(
            [
                self.ui.radioButton_total_fee,
                self.ui.radioButton_round,
                self.ui.radioButton_ceiling,
                self.ui.radioButton_chop,
            ],
            ['原價', '四捨五入', '無條件進位', '無條件捨去'],
            '自費折扣進位'
        )
        self._set_radio_button(
            [
                self.ui.radioButton_tail1,
                self.ui.radioButton_tail2
            ],
            ['尾數為0', '尾數為0或5'],
            '自費折扣尾數'
        )
        self._set_radio_button(
            [
                self.ui.radioButton_checkout_by_charge,
                self.ui.radioButton_checkout_by_registration
            ],
            ['批價班別', '掛號班別'],
            '櫃台結帳班別'
        )
        self._set_check_box(self.ui.checkBox_no_discount, '無折扣批價計算')
        self._set_check_box(self.ui.checkBox_not_charge_done, '櫃台結帳列出未完診名單')
        self._set_check_box(self.ui.checkBox_charge_done_allow, '所有資料都已批價才能結帳')
        self._set_check_box(self.ui.checkBox_no_auto_charge, '手動批價')
        self._set_check_box(self.ui.checkBox_sync_share_fee, '部份負擔連動')
        self._set_check_box(self.ui.checkBox_video_charge, '視訊診療須經過批價作業')
        self._set_check_box(self.ui.checkBox_charge_by_cashier, '掛號收費批價進行')
        self._set_check_box(self.ui.checkBox_sync_drug_price, '拷貝處方藥價更新')
        self._set_check_box(self.ui.checkBox_charge_by_kiosk, '在掛號機批價繳費')

        self.ui.spinBox_ins_diag_rate.setValue(number_utils.get_integer(self.system_settings.field('診察費抽成率')))
        self.ui.spinBox_ins_treat_rate.setValue(number_utils.get_integer(self.system_settings.field('診療費抽成率')))
        self.ui.spinBox_self_drug_rate.setValue(number_utils.get_integer(self.system_settings.field('自費藥品抽成率')))
        self.ui.spinBox_self_treat_rate.setValue(number_utils.get_integer(self.system_settings.field('自費針傷抽成率')))

        self.ui.comboBox_ins_diag_rate_type.setCurrentText(self.system_settings.field('診察費抽成類別'))
        self.ui.comboBox_ins_treat_rate_type.setCurrentText(self.system_settings.field('診察費抽成類別'))
        self.ui.comboBox_self_drug_rate_type.setCurrentText(self.system_settings.field('自費藥品抽成類別'))
        self.ui.comboBox_self_treat_rate_type.setCurrentText(self.system_settings.field('自費針傷抽成類別'))
        self.ui.lineEdit_tc_massage_field_name.setText(self.system_settings.field('民俗調理欄位名稱'))        
        
    # 讀取診號設定
    def _read_regist_no_settings(self):
        self._set_check_box(self.ui.checkBox_period_reset, '分班')
        self._set_check_box(self.ui.checkBox_room_reset, '分診')
        self.ui.spinBox_start_no1.setValue(number_utils.get_integer(self.system_settings.field('早班起始號')))
        self.ui.spinBox_start_no2.setValue(number_utils.get_integer(self.system_settings.field('午班起始號')))
        self.ui.spinBox_start_no3.setValue(number_utils.get_integer(self.system_settings.field('晚班起始號')))
        self.ui.spinBox_start_drug_no.setValue(number_utils.get_integer(self.system_settings.field('領藥起始號')))
        max_regist_no = number_utils.get_integer(self.system_settings.field('診號累加器最大號'))
        if max_regist_no == 0:
            max_regist_no = 9999

        self.ui.spinBox_max_regist_no.setValue(max_regist_no)
        self._set_radio_button([self.ui.radioButton_consecutive,
                                self.ui.radioButton_odd,
                                self.ui.radioButton_even,
                                self.ui.radioButton_reservation_table,
                                self.ui.radioButton_odd_sequence,
                                self.ui.radioButton_sequence,
                               ],
                               ['連續號', '單號', '雙號', '預約班表', '單號順序', '就醫順序'],
                               '現場掛號給號模式')
        self._set_radio_button([self.ui.radioButton_arrival1,
                                self.ui.radioButton_arrival2,
                                self.ui.radioButton_arrival3,
                                self.ui.radioButton_arrival4,
                                self.ui.radioButton_arrival_sequence,
                                ],
                               ['根據班表設定', '根據現場設定', '零號', '雙號順序', '就醫順序'],
                               '預約報到給號模式')
        self._set_check_box(self.ui.checkBox_fill_reg_no, '優先遞補現場號')
        self._set_check_box(self.ui.checkBox_reservation_table_no_time, '預約班表不顯示時間')
        self._set_check_box(self.ui.checkBox_reservation_current_doctor, '預約選擇當診醫師')
        self._set_check_box(self.ui.checkBox_show_memo, '顯示備忘錄')
        self._set_check_box(self.ui.checkBox_same_memo, '備忘錄以病患鍵為主')
        self._set_check_box(self.ui.checkBox_popup_menu, '刪除處方啟用彈出式選單')
        self._set_check_box(self.ui.checkBox_release_reserve_no, '釋出預約號')
        self._set_check_box(self.ui.checkBox_reserve_twice, '同日預約兩次')
        self._set_check_box(self.ui.checkBox_reserve_doctor_limit, '預約次數不同醫師分別計算')
        self._set_check_box(self.ui.checkBox_reserve_allow_today, '開放當日網路預約')
        self._set_check_box(self.ui.checkBox_cancel_reserve_today, '當日可以取消網路預約')
        self._set_check_box(self.ui.checkBox_no_waiting_progress, '網路預約不顯示看診進度')
        self._set_check_box(self.ui.checkBox_no_first_reservation, '不開放初診網路預約')
        self._set_check_box(self.ui.checkBox_arrival_late, '預約遲到寫入掛號備註')
        self._set_check_box(self.ui.checkBox_over_number, '預約過號寫入掛號備註')        
        self._set_check_box(self.ui.checkBox_show_last_case_remark, '預約名單顯示上次病歷備註')
        self._set_check_box(self.ui.checkBox_show_late_number, '預約過號顯示過號序號')
        
        self.ui.spinBox_reservation_limit.setValue(
            number_utils.get_integer(self.system_settings.field('預約次數限制'))
        )
        self.ui.spinBox_absent.setValue(
            number_utils.get_integer(self.system_settings.field('爽約次數'))
        )
        self.ui.spinBox_reservation_period.setValue(
            number_utils.get_integer(self.system_settings.field('爽約期間'))
        )
        return_card_days = registration_utils.get_return_card_days(self.system_settings)
        self.ui.spinBox_return_card_days.setValue(return_card_days)
        self.ui.spinBox_max_reserve_weeks.setValue(
            number_utils.get_integer(self.system_settings.field('網路預約開放週數'))
        )
        self.ui.spinBox_no_return_days.setValue(number_utils.get_integer(self.system_settings.field('未回診天數')))

        self._read_start_no()

    def _read_start_no(self):
        keyword = '指定診別起始號'

        self.ui.tableWidget_start_no.setRowCount(0)
        sql = f'''
            SELECT * FROM system_settings
            WHERE
                StationNo = 0 AND
                Field LIKE "{keyword}-%"
            ORDER BY SystemSettingsKey
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        for row_no, row in enumerate(rows):
            room = row['Field'].split('-')[1]
            start_no_json = self.system_settings.field(f'{keyword}-{room}')
            if start_no_json in ['', None]:
                return

            start_no_dict = json.loads(start_no_json)
            self.ui.tableWidget_start_no.setRowCount(self.ui.tableWidget_start_no.rowCount()+1)
            start_no_data = [room, start_no_dict['早班'], start_no_dict['午班'], start_no_dict['晚班']]
            for col_no in range(len(start_no_data)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, start_no_data[col_no])
                self.ui.tableWidget_start_no.setItem(row_no, col_no, item)
                if col_no in [0]:
                    self.ui.tableWidget_start_no.item(row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
                elif col_no in [1, 2, 3]:
                    self.ui.tableWidget_start_no.item(row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    # 讀取掛號設定
    def _read_registration_settings(self):
        self._set_radio_button([self.ui.radioButton_ins,
                                self.ui.radioButton_self],
                               ['健保', '自費'],
                               '預設門診類別')
        self._set_radio_button([self.ui.radioButton_multi_sales,
                                self.ui.radioButton_single_sales],
                               ['複選', '單選'],
                               '自購藥銷售人員')
        self.ui.spinBox_diag_count.setValue(number_utils.get_integer(self.system_settings.field('首次警告次數')))
        self.ui.spinBox_treat_count.setValue(number_utils.get_integer(self.system_settings.field('針傷警告次數')))
        self._set_check_box(self.ui.checkBox_doctor_treat, '醫師親自處置')
        self._set_check_box(self.ui.checkBox_massager_fee, '自動帶出民俗調理費')
        self._set_check_box(self.ui.checkBox_first_massage_fee, '療程首次民俗調理費')
        self._set_check_box(self.ui.checkBox_display_self_massage, '候診名單顯示自費民俗調理')
        self._set_radio_button(
            [
                self.ui.radioButton_deposit_date1,
                self.ui.radioButton_deposit_date2,
                self.ui.radioButton_deposit_date3,
                self.ui.radioButton_deposit_date4,
            ],
            ['上個月1日', '上個月20日', '本月1日', '10天前'],
            '欠卡日期檢查範圍'
        )
        self._set_radio_button(
            [
                self.ui.radioButton_order_by_default,
                self.ui.radioButton_order_by_time,
                self.ui.radioButton_order_by_regist_no,
            ],
            ['預設排序', '時間排序', '診號排序'],
            '掛號候診名單排序方式'
        )
        self._set_check_box(self.ui.checkBox_register_current_doctor, '掛號選擇當診醫師')
        self._set_check_box(self.ui.checkBox_day14, '掛號療程14日未完成提醒')
        self._set_check_box(self.ui.checkBox_interrupt_course, '療程中斷不續療程')
        self._set_check_box(self.ui.checkBox_past_history_show_symptom, '掛號過去病歷顯示主訴')
        self._set_check_box(self.ui.checkBox_past_history_show_massage, '掛號過去病歷顯示民俗調理')
        self._set_check_box(self.ui.checkBox_no_regist_no_duplicate, '掛號診號不可重複')
        self._set_check_box(self.ui.checkBox_regist_visit_count, '掛號作業顯示初診統計')
        self._set_check_box(self.ui.checkBox_auto_last_treat_type, '掛號新療程自動帶出上次就醫類別')
        self._set_check_box(self.ui.checkBox_debt_stop_regist, '欠款未還不能掛號')
        self._set_check_box(self.ui.checkBox_show_purchase_case, '掛號已就診名單顯示自購藥病歷')
        self._set_check_box(self.ui.checkBox_show_massage_fee, '掛號名單顯示民俗調理費')
        self._set_check_box(self.ui.checkBox_no_change_doctor, '掛號診別更改不要連動醫師姓名')                

    # 看診設定
    def _read_doctor_settings(self):
        self.ui.spinBox_room.setValue(number_utils.get_integer(self.system_settings.field('診療室')))
        self.ui.spinBox_count_per_page.setValue(
            number_utils.get_integer(self.system_settings.field('過去病歷一頁筆數'))
        )
        self.ui.comboBox_medical_record_page.setCurrentText(self.system_settings.field('病歷版面'))
        self.ui.comboBox_disease_layout.setCurrentText(self.system_settings.field('病名版面'))
        self.ui.comboBox_led_port.setCurrentText(self.system_settings.field('叫號燈連接埠'))
        self.ui.comboBox_scale_port.setCurrentText(self.system_settings.field('電子秤連接埠'))

        scale_time = self.system_settings.field('電子秤測重時間')
        if scale_time is None:
            scale_time = 1.5
        else:
            scale_time = number_utils.get_float(scale_time)

        self.ui.doubleSpinBox_scale_time.setValue(scale_time)

        self.ui.lineEdit_led_ip.setText(self.system_settings.field('叫號燈ip'))
        self.ui.lineEdit_led_port.setText(self.system_settings.field('叫號燈port'))
        self._set_check_box(self.ui.checkBox_ring_bell, '叫號燈響鈴')

        self._set_check_box(self.ui.checkBox_copy_past, '自動顯示過去病歷')
        self._set_check_box(self.ui.checkBox_only_symptom, '過去病歷診察資料只顯示主訴')
        self._set_check_box(self.ui.checkBox_no_patient_remark, '病歷資料不顯示病患備註')
        self._set_check_box(self.ui.checkBox_copy_self_prescript, '預設拷貝自費處方')
        self._set_check_box(self.ui.checkBox_copy_ins_past_medicine, '預設拷貝健保針傷科處方用藥')
        self._set_check_box(self.ui.checkBox_copy_remark, '預設拷貝備註')
        self._set_check_box(self.ui.checkBox_show_massage, '過去病歷顯示民俗調理')
        self._set_check_box(self.ui.checkBox_show_massager, '過去病歷顯示推拿師父')
        self._set_check_box(self.ui.checkBox_auto_cashier, '自動完成批價作業')
        self._set_check_box(self.ui.checkBox_display_custom, '健保處方詞庫顯示自訂類別')
        self._set_check_box(self.ui.checkBox_order_by_icd, '病名詞庫以病名碼排序')
        self._set_check_box(self.ui.checkBox_diag_timer, '顯示看診計時器')
        self._set_check_box(self.ui.checkBox_hit_rate_by_medicine_type, '處方點擊率依照處方類別排序')
        self._set_check_box(self.ui.checkBox_no_separator, '最近病歷不顯示分隔線')
        self._set_check_box(self.ui.checkBox_case_large_font, '病歷主訴大字體')
        self._set_check_box(self.ui.checkBox_no_switch_ime, '不要自動切換輸入法')        
        self._set_check_box(self.ui.checkBox_show_all_statistics, '候診名單病歷統計顯示全院統計')
        self._set_check_box(self.ui.checkBox_no_ins_prescript, '健保處方預設不調劑')
        self._set_check_box(self.ui.checkBox_show_simple, '過去病歷顯示精簡顯示頁')

        self._set_check_box(self.ui.checkBox_ime_en, '望聞問切輸入法預設英數')
        self._set_check_box(self.ui.checkBox_ime_zh, '診斷碼輸入法預設中文')
        self._set_check_box(self.ui.checkBox_prescript_edit_mode, '處方輸入編輯模式')

        self._set_check_box(self.ui.checkBox_hide_reserve_time, '醫師候診名單隱藏預約時間')
        self._set_check_box(self.ui.checkBox_hide_wait_time, '醫師候診名單隱藏候診時間')
        self._set_check_box(self.ui.checkBox_set_waiting_list, '自動切換醫師候診名單')
        self._set_check_box(self.ui.checkBox_no_beep, '醫師候診名單不要提示音')
        self._set_check_box(self.ui.checkBox_sort_dosage, '處方劑量欄位可以排序')
        self._set_check_box(self.ui.checkBox_fixed_waiting_list_width, '醫師候診名單欄位固定寬度')
        self._set_check_box(self.ui.checkBox_same_doctor, '病歷存檔檢查醫師姓名')
        self._set_check_box(self.ui.checkBox_check_fees, '病歷存檔檢查補退掛號費用')
        self._set_check_box(self.ui.checkBox_no_location_light_color, '處方無存放位置淡色顯示')
        self._set_check_box(self.ui.checkBox_display_ins_drug, '健保處方詞庫只顯示單方複方')
        self._set_check_box(self.ui.checkBox_no_instruction_pres_days, '單一處方服法不可取代用藥天數')
        self._set_check_box(self.ui.checkBox_no_insufficent_medicine, '庫存量不足不要提醒')
        self._set_check_box(self.ui.checkBox_no_zero_price, '單日計價輸入藥品不要歸零')
        self._set_check_box(self.ui.checkBox_no_complicated_treat_dialog, '輸入病名後不要彈出複雜性針傷提示視窗')
        self._set_check_box(self.ui.checkBox_reservation_current_period, '醫師候診名單只顯示當班預約資料')
        self._set_check_box(self.ui.checkBox_herb_only, '處方詞庫僅列出水藥')
        self._set_check_box(self.ui.checkBox_symptom_br, '主訴換行')
        self.ui.comboBox_disease_group.setCurrentText(self.system_settings.field('病名詞庫預設類別'))
        self.ui.comboBox_default_treat_type.setCurrentText(self.system_settings.field('預設就醫類別'))

        self.ui.spinBox_packages.setValue(number_utils.get_integer(self.system_settings.field('給藥包數')))
        self.ui.spinBox_days.setValue(number_utils.get_integer(self.system_settings.field('給藥天數')))
        self.ui.comboBox_instruction.setCurrentText(self.system_settings.field('用藥指示'))
        self._set_radio_button([self.ui.radioButton_dosage1,
                                self.ui.radioButton_dosage2,
                                self.ui.radioButton_dosage3],
                               ['日劑量', '次劑量', '總量'],
                               '劑量模式')
        self._set_check_box(self.ui.checkBox_dosage_percent, '比例法劑量')
        self._set_check_box(self.ui.checkBox_no_ins_cost, '不要顯示健保用藥成本')

        self._set_radio_button([self.ui.radioButton_auto_chart_no1,
                                self.ui.radioButton_auto_chart_no2],
                               ['無', '身份證後四碼'],
                               '自動產生病歷號')
        self._set_radio_button([self.ui.radioButton_self_room,
                                self.ui.radioButton_doctor_room,
                                self.ui.radioButton_all_room],
                               ['指定診別', '醫師診別', '所有診別'],
                               '候診名單顯示診別')
        self._set_radio_button([self.ui.radioButton_order_no,
                                self.ui.radioButton_order_time],
                               ['診號排序', '時間排序'],
                               '看診排序')
        self._set_radio_button([self.ui.radioButton_order_medicine_key,
                                self.ui.radioButton_order_medicine_type],
                               ['開藥順序', '處方類別'],
                               '處方排序')
        self._set_radio_button([self.ui.radioButton_by_dict_name,
                                self.ui.radioButton_by_hit_rate,
                                self.ui.radioButton_by_timestamp],
                               ['詞庫名稱', '點擊率', '最後點擊時戳'],
                               '詞庫排序')
        self._set_radio_button([self.ui.radioButton_by_diag_name,
                                self.ui.radioButton_by_diag_hit_rate,
                                self.ui.radioButton_by_diag_timestamp],
                               ['詞庫名稱', '點擊率', '最後點擊時戳'],
                               '診察詞庫排序')
        self._set_radio_button([self.ui.radioButton_normal_price,
                                self.ui.radioButton_single_day_price],
                               ['正常計價', '單日計價'],
                               '自費處方預設計價方式')
        self._set_radio_button([self.ui.radioButton_input_dosage,
                               self.ui.radioButton_save_dosage],
                               ['輸入處方時檢查', '存檔時檢查'],
                               '健保處方給藥劑量上限檢查時機')
        self._set_radio_button([self.ui.radioButton_input_costs,
                               self.ui.radioButton_save_costs],
                               ['輸入處方時檢查', '存檔時檢查'],
                               '健保用藥成本上限檢查時機')
        self._set_radio_button([self.ui.radioButton_normal_view,
                               self.ui.radioButton_simple_view],
                               ['詳細檢視', '精簡檢視'],
                               '病歷查詢檢視方式')

        self.ui.lineEdit_tongue1.setText(self.system_settings.field('舌診1'))
        self.ui.lineEdit_tongue2.setText(self.system_settings.field('舌診2'))
        self.ui.lineEdit_tongue3.setText(self.system_settings.field('舌診3'))
        self.ui.lineEdit_tongue4.setText(self.system_settings.field('舌診4'))
        self.ui.lineEdit_tongue5.setText(self.system_settings.field('舌診5'))

        self.ui.lineEdit_pulse1.setText(self.system_settings.field('脈象1'))
        self.ui.lineEdit_pulse2.setText(self.system_settings.field('脈象2'))
        self.ui.lineEdit_pulse3.setText(self.system_settings.field('脈象3'))
        self.ui.lineEdit_pulse4.setText(self.system_settings.field('脈象4'))
        self.ui.lineEdit_pulse5.setText(self.system_settings.field('脈象5'))
        self.ui.lineEdit_pulse6.setText(self.system_settings.field('脈象6'))
        self.ui.lineEdit_pulse7.setText(self.system_settings.field('脈象7'))
        self.ui.lineEdit_pulse8.setText(self.system_settings.field('脈象8'))
        self.ui.lineEdit_pulse9.setText(self.system_settings.field('脈象9'))
        self.ui.lineEdit_pulse10.setText(self.system_settings.field('脈象10'))

    def _read_printer_settings(self):
        self.ui.comboBox_regist_print_mode.setCurrentText(self.system_settings.field('列印門診掛號單'))
        self.ui.comboBox_reservation_print_mode.setCurrentText(self.system_settings.field('列印預約掛號單'))
        self.ui.comboBox_ins_prescript_print_mode.setCurrentText(self.system_settings.field('列印健保處方箋'))
        self.ui.comboBox_self_prescript_print_mode.setCurrentText(self.system_settings.field('列印自費處方箋'))
        self.ui.comboBox_ins_receipt_print_mode.setCurrentText(self.system_settings.field('列印健保醫療收據'))
        self.ui.comboBox_self_receipt_print_mode.setCurrentText(self.system_settings.field('列印自費醫療收據'))
        self.ui.comboBox_bag_print_mode.setCurrentText(self.system_settings.field('列印藥袋'))
        self.ui.comboBox_massage_print_mode.setCurrentText(self.system_settings.field('列印民俗調理單'))
        self.ui.comboBox_misc_print_mode.setCurrentText(self.system_settings.field('列印其他收據'))
        self.ui.comboBox_misc2_print_mode.setCurrentText(self.system_settings.field('列印其他收據2'))
        self.ui.comboBox_misc3_print_mode.setCurrentText(self.system_settings.field('列印其他收據3'))

        self.ui.comboBox_regist_form.setCurrentText(self.system_settings.field('門診掛號單格式'))
        self.ui.comboBox_reservation_form.setCurrentText(self.system_settings.field('預約掛號單格式'))
        self.ui.comboBox_ins_prescript_form.setCurrentText(self.system_settings.field('健保處方箋格式'))
        self.ui.comboBox_self_prescript_form.setCurrentText(self.system_settings.field('自費處方箋格式'))
        self.ui.comboBox_ins_receipt_form.setCurrentText(self.system_settings.field('健保醫療收據格式'))
        self.ui.comboBox_self_receipt_form.setCurrentText(self.system_settings.field('自費醫療收據格式'))
        self.ui.comboBox_bag_form.setCurrentText(self.system_settings.field('藥袋格式'))
        self.ui.comboBox_massage_form.setCurrentText(self.system_settings.field('民俗調理單格式'))
        self.ui.comboBox_misc_form.setCurrentText(self.system_settings.field('其他收據格式'))
        self.ui.comboBox_misc2_form.setCurrentText(self.system_settings.field('其他收據2格式'))
        self.ui.comboBox_misc3_form.setCurrentText(self.system_settings.field('其他收據3格式'))

        self.ui.comboBox_regist_printer.setCurrentText(self.system_settings.field('門診掛號單印表機'))
        self.ui.comboBox_reservation_printer.setCurrentText(self.system_settings.field('預約掛號單印表機'))
        self.ui.comboBox_ins_prescript_printer.setCurrentText(self.system_settings.field('健保處方箋印表機'))
        self.ui.comboBox_self_prescript_printer.setCurrentText(self.system_settings.field('自費處方箋印表機'))
        self.ui.comboBox_ins_receipt_printer.setCurrentText(self.system_settings.field('健保醫療收據印表機'))
        self.ui.comboBox_self_receipt_printer.setCurrentText(self.system_settings.field('自費醫療收據印表機'))
        self.ui.comboBox_bag_printer.setCurrentText(self.system_settings.field('藥袋印表機'))
        self.ui.comboBox_massage_printer.setCurrentText(self.system_settings.field('民俗調理單印表機'))
        self.ui.comboBox_massage_printer2.setCurrentText(self.system_settings.field('民俗調理單印表機2'))
        self.ui.comboBox_misc_printer.setCurrentText(self.system_settings.field('其他收據印表機'))
        self.ui.comboBox_misc2_printer.setCurrentText(self.system_settings.field('其他收據2印表機'))
        self.ui.comboBox_misc3_printer.setCurrentText(self.system_settings.field('其他收據3印表機'))

        self.ui.comboBox_report_print_mode.setCurrentText(self.system_settings.field('列印報表'))
        self.ui.comboBox_report_printer.setCurrentText(self.system_settings.field('報表印表機'))
        self.ui.comboBox_report_printer_paper_size.setCurrentText(self.system_settings.field('報表印表機紙張大小'))

        self.ui.lineEdit_certificate_payment_title.setText(self.system_settings.field('醫療費用證明書抬頭'))
        self.ui.lineEdit_folk_massage_name.setText(self.system_settings.field('民俗調理項目名稱'))
        self.ui.lineEdit_folk_massage_title.setText(self.system_settings.field('民俗調理收據抬頭'))
        self.ui.lineEdit_medicine_fee_field_name.setText(self.system_settings.field('醫療費用證明自費藥費欄位名稱'))
        self.ui.lineEdit_treat_fee_field_name.setText(self.system_settings.field('醫療費用證明自費處置欄位名稱'))
        self.ui.lineEdit_misc_fee_field_name.setText(self.system_settings.field('醫療費用證明其他費用欄位名稱'))
        self.ui.lineEdit_total_fee_field_name.setText(self.system_settings.field('醫療費用證明自費金額欄位名稱'))
        self.ui.lineEdit_total_fee_field_name2.setText(self.system_settings.field('醫療費用自付明細自費金額欄位名稱'))
        self.ui.plainTextEdit_tax_remark.setPlainText(self.system_settings.field('醫療費用收據自訂報稅備註'))

        self.ui.lineEdit_indication.setText(self.system_settings.field('自訂適應症'))
        self.ui.lineEdit_print_font.setText(self.system_settings.field('列印預設字體'))
        self.ui.lineEdit_custom_clinic_name.setText(self.system_settings.field('自訂院所名稱'))

        # self._set_check_box(self.ui.checkBox_print_total_dosage, '列印藥品總量')  # TODO
        # self._set_check_box(self.ui.checkBox_print_daily_dosage, '列印藥品日量')  # TODO
        # self._set_check_box(self.ui.checkBox_print_ins_total_dosage, '列印健保藥品總量')  # TODO
        self._set_check_box(self.ui.checkBox_print_location, '列印藥品存放位置')
        self._set_check_box(self.ui.checkBox_location_before_medicine, '列印藥品存放位置在處方名稱前面')
        self._set_check_box(self.ui.checkBox_print_remark, '列印病歷備註')
        self._set_check_box(self.ui.checkBox_print_alias, '列印處方別名')
        self._set_check_box(self.ui.checkBox_print_folk_massage, '列印民俗調理')
        self._set_check_box(self.ui.checkBox_print_clinic_name, '列印院所名稱')
        self._set_check_box(self.ui.checkBox_print_regist_non_zero, '掛號收據無金額不列印')
        self._set_check_box(self.ui.checkBox_print_massager, '列印推拿師父')
        self._set_check_box(self.ui.checkBox_print_reservation_no, '列印預約號碼')
        self._set_check_box(self.ui.checkBox_print_treat, '列印穴道處置')
        self._set_check_box(self.ui.checkBox_print_no_treat_fee, '費用總表合併處置費至藥費')
        self._set_check_box(self.ui.checkBox_print_treatment, '列印針傷處置名稱')
        self._set_check_box(self.ui.checkBox_no_tax_hint, '不印報稅提示')
        self._set_check_box(self.ui.checkBox_print_stamp_duty, '列印印花稅總繳')
        self._set_check_box(self.ui.checkBox_no_print_prescript, '費用收據不印處方')
        self._set_check_box(self.ui.checkBox_no_print_fee, '處方箋不印費用明細')
        self._set_check_box(self.ui.checkBox_no_print_discount, '不印折扣')
        self._set_check_box(self.ui.checkBox_print_qrcode, '列印條碼')
        self._set_check_box(self.ui.checkBox_self_prescript_package_dosage, '自費處方次劑量')
        self._set_check_box(self.ui.checkBox_order_by_location, '列印處方依照存放位置排序')
        self._set_check_box(self.ui.checkBox_no_massage_list, '開立費用證明不要列出民俗調理')
        self._set_check_box(self.ui.checkBox_print_certificate_diagnosis_date, '列印診斷證明日期明細')
        self._set_check_box(self.ui.checkBox_print_symptom_limitation, '列印主訴字數限制')
        self._set_check_box(self.ui.checkBox_print_medicine_limitation, '列印處方字數限制')
        self._set_check_box(self.ui.checkBox_self_daily_dosage, '自費收據列印日量')
        self._set_check_box(self.ui.checkBox_print_prescript_total_dosage, '處方箋列印總量')
        self._set_check_box(self.ui.checkBox_ins_receipt, '健保費用收據同時輸出至掛號印表機')
        self._set_check_box(self.ui.checkBox_self_receipt, '自費費用收據同時輸出至掛號印表機')
        self._set_check_box(self.ui.checkBox_print_registration, '加印一張掛號單')

        self._set_check_box(self.ui.groupBox_ins_receipt_size, '自訂健保醫療收據尺寸邊界')
        self._set_check_box(self.ui.groupBox_self_receipt_size, '自訂自費醫療收據尺寸邊界')

        self.ui.doubleSpinBox_ins_receipt_width.setValue(
            number_utils.get_float(self.system_settings.field('健保醫療收據寬度')))
        self.ui.doubleSpinBox_ins_receipt_length.setValue(
            number_utils.get_float(self.system_settings.field('健保醫療收據長度')))
        self.ui.doubleSpinBox_self_receipt_width.setValue(
            number_utils.get_float(self.system_settings.field('自費醫療收據寬度')))
        self.ui.doubleSpinBox_self_receipt_length.setValue(
            number_utils.get_float(self.system_settings.field('自費醫療收據長度')))

        self.ui.comboBox_ins_receipt_size_unit.setCurrentText(self.system_settings.field('健保醫療收據尺寸單位'))
        self.ui.comboBox_self_receipt_size_unit.setCurrentText(self.system_settings.field('自費醫療收據尺寸單位'))

        self.ui.doubleSpinBox_ins_receipt_left_margin.setValue(
            number_utils.get_float(self.system_settings.field('健保醫療收據左邊界')))
        self.ui.doubleSpinBox_ins_receipt_top_margin.setValue(
            number_utils.get_float(self.system_settings.field('健保醫療收據上邊界')))
        self.ui.comboBox_ins_receipt_margin_unit.setCurrentText(
            self.system_settings.field('健保醫療收據邊界單位'))

        self.ui.doubleSpinBox_self_receipt_left_margin.setValue(
            number_utils.get_float(self.system_settings.field('自費醫療收據左邊界')))
        self.ui.doubleSpinBox_self_receipt_top_margin.setValue(
            number_utils.get_float(self.system_settings.field('自費醫療收據上邊界')))
        self.ui.comboBox_self_receipt_margin_unit.setCurrentText(
            self.system_settings.field('自費醫療收據邊界單位'))

        self.ui.spinBox_symptom_count.setValue(number_utils.get_integer(self.system_settings.field('列印主訴字數')))
        self.ui.spinBox_medicine_character_count.setValue(
            number_utils.get_integer(self.system_settings.field('列印處方字數')))
        self._set_check_box(self.ui.checkBox_agreement, '自費同意書自費1金額')
        self._set_radio_button(
            [self.ui.radioButton_print_order1, self.ui.radioButton_print_order2, self.ui.radioButton_print_order3],
            ['列印順序1', '列印順序2', '列印順序3'],
            '病歷存檔列印順序'
        )
        self._set_radio_button(
            [self.ui.radioButton_print_total_dosage,
             self.ui.radioButton_print_daily_dosage,
             self.ui.radioButton_print_all_dosage],
            ['總量', '日量', '日量+總量'],
            '收費收據列印劑量'
        )
        self._set_radio_button(
            [self.ui.radioButton_print_horizontal, self.ui.radioButton_print_vertical],
            ['水平列印', '垂直列印'],
            '處方列印方向'
        )
        self._set_radio_button(
            [self.ui.radioButton_elec_prescript1, self.ui.radioButton_elec_prescript2],
            ['格式1', '格式2'],
            '電子處方箋格式'
        )
        self._set_check_box(self.ui.checkBox_print_self_fee, '列印所有收費收據費用明細')
        self._set_check_box(self.ui.checkBox_print_each_self_fee, '列印所有收費收據各自金額')
        self._set_check_box(self.ui.checkBox_print_bg_color, '列印報表雙色印刷')
        self._set_check_box(self.ui.checkBox_print_no_dosage_receipt, '自費加印無劑量收據')

        self.ui.spinBox_prescript_font_size.setValue(
            number_utils.get_integer(self.system_settings.field('費用收據處方欄字體大小')))
        self.ui.spinBox_certificate_diag_default_fee.setValue(
            number_utils.get_integer(self.system_settings.field('醫療費用證明預設金額')))

    def _read_reader_settings(self):
        self._set_check_box(self.ui.checkBox_use_webcam, '使用webcam讀取虛擬健保卡')
        self._set_check_box(self.ui.checkBox_use_reader, '使用讀卡機')
        self._set_check_box(self.ui.checkBox_run_csfsim, '自動開啟雲端安全模組主控台')
        self.ui.spinBox_ic_reader_port.setValue(
            number_utils.get_integer(self.system_settings.field('健保卡讀卡機連接埠'))
        )
        self._set_radio_button([self.ui.radioButton_smart_card_reader,
                                self.ui.radioButton_nhi_card_reader],
                               ['晶片讀卡機', '健保讀卡機'],
                               '讀卡機類型')
        self._set_radio_button([self.ui.radioButton_cshis5,
                                self.ui.radioButton_cshis6],
                               ['cshis5', 'cshis6'],
                               '讀卡機控制軟體版本')
        self._set_check_box(self.ui.checkBox_read_record, '讀取卡片就醫記錄')
        self._set_check_box(self.ui.checkBox_read_disease, '讀取卡片重大傷病')
        self._set_radio_button([self.ui.radioButton_regist_secure,
                                self.ui.radioButton_doctor_secure],
                               ['掛號', '診療'],
                               '產生安全簽章位置')
        self._set_radio_button([self.ui.radioButton_doctor_write,
                                self.ui.radioButton_regist_write,
                                self.ui.radioButton_charge_write],
                               ['診療', '掛號', '批價'],
                               '產生醫令簽章位置')
        self._set_check_box(self.ui.checkBox_vhc_card_operation, '虛擬健保卡統一在掛號作業')
        self._set_check_box(self.ui.checkBox_cshis_test_ip, '使用測試環境')
        self.ui.lineEdit_sam_id.setText(self.system_settings.field('SAMID'))

    def _get_css_font_size(self):
        css_file = os.path.join(
            system_utils.BASE_DIR, system_utils.CSS_PATH, system_utils.get_css_file(self.system_settings)
        )
        s = open(css_file, 'r', encoding='utf-8').read()
        font_size = 18
        for i in range(12, 33):
            _size = f'font-size: {i}px;'
            if s.find(_size) > 0:
                font_size = i
                break

        return font_size

    def _get_css_font_weight(self):
        css_file = os.path.join(
            system_utils.BASE_DIR, system_utils.CSS_PATH, system_utils.get_css_file(self.system_settings)
        )
        s = open(css_file, 'r', encoding='utf-8').read()

        if s.find('font-weight: bold; /* system */') > 0:
            return 'font-weight: bold; /* system */'
        else:
            return 'font-weight: normal; /* system */'

    def _read_misc(self):
        self.ui.spinBox_station_no.setValue(number_utils.get_integer(self.system_settings.field('工作站編號')))
        self.ui.lineEdit_position.setText(self.system_settings.field('工作站位置'))
        self.ui.comboBox_theme.setCurrentText(self.system_settings.field('外觀主題'))
        self.ui.comboBox_color.setCurrentText(self.system_settings.field('外觀顏色'))

        font_size = self._get_css_font_size()
        self.ui.spinBox_font_size.setValue(font_size)

        self.ui.lineEdit_emr_path.setText(self.system_settings.field('電子病歷交換檔輸出路徑'))
        self.ui.lineEdit_clinic_dir.setText(self.system_settings.field('資料路徑'))
        self.ui.lineEdit_external_backup_dir.setText(self.system_settings.field('異地備份路徑'))
        self.ui.lineEdit_database_physical_dir.setText(self.system_settings.field('伺服器物理備份路徑'))
        self.ui.lineEdit_database_dir.setText(self.system_settings.field('伺服器資料來源'))
        self.ui.lineEdit_image_path.setText(self.system_settings.field('影像檔路徑'))
        self.ui.lineEdit_electronic_prescript_path.setText(self.system_settings.field('電子處方箋路徑'))
        self.ui.lineEdit_cashier_machine_path.setText(self.system_settings.field('掛號機錢箱路徑'))
        self.ui.lineEdit_blood_measure_path.setText(self.system_settings.field('血壓計路徑'))
        self._set_check_box(self.ui.checkBox_side_bar, '顯示側邊欄')
        self._set_check_box(self.ui.checkBox_font_weight, '粗體字')
        self._set_check_box(self.ui.checkBox_do_not_display_bulletin, '不要顯示最新消息')
        self._set_check_box(self.ui.checkBox_self_emr, '匯出電子病歷包含自費病歷')
        self._set_check_box(self.ui.checkBox_use_docker, '使用docker')
        self._set_radio_button([
                self.ui.radioButton_single_instance,
                self.ui.radioButton_multi_instance],
            ['獨立執行', '多個執行'],
            '醫療系統執行個體'
        )
        self._set_radio_button([
                self.ui.radioButton_real_time_stock,
                self.ui.radioButton_batch_stock],
            ['即時調整', '批次調整'],
            '調整庫存量'
        )
        self._set_check_box(self.ui.checkBox_voice_server, '廣播叫號主機')
        self._set_check_box(self.ui.checkBox_voice_no_call_room, '叫號不包含診療室')
        self._set_check_box(self.ui.checkBox_voice_call_name, '叫號包含病患姓名')
        self._set_check_box(self.ui.checkBox_voice_call_next, '叫號包含下一位請準備')
        self._set_check_box(self.ui.checkBox_voice_with_led, '叫號同時啟動叫號燈')
        self._set_check_box(self.ui.checkBox_import_all_database, '執行匯入全部資料庫')
        self._set_check_box(self.ui.checkBox_sync_in_price, '輸入進貨資料同步更新藥品進價')

        self.ui.lineEdit_archive_database_name.setText(self.system_settings.field('封存資料庫名稱'))
        self.ui.lineEdit_voice_call_format.setText(self.system_settings.field('自訂叫號格式'))

    ###################################################################################################################
    # 設定檔存檔
    def _save_settings(self):
        self._save_clinic_settings()
        self._save_charge_settings()
        self._save_regist_no_settings()
        self._save_registration_settings()
        self._save_doctor_settings()
        self._save_printer_settings()
        self._save_reader_settings()
        self._save_misc()

        self._adjust_settings()

    # 寫入院所設定
    def _save_clinic_settings(self):
        self.system_settings.post('院所名稱', self.ui.lineEdit_clinic_name.text())
        self.system_settings.post('院所代號', self.ui.lineEdit_clinic_id.text())
        self.system_settings.post('統一編號', self.ui.lineEdit_invoice_no.text())
        self.system_settings.post('負責醫師', self.ui.lineEdit_owner.text())
        self.system_settings.post('醫師證號', self.ui.lineEdit_owner_cert.text())
        self.system_settings.post('開業證號', self.ui.lineEdit_clinic_cert.text())
        self.system_settings.post('院所電話', self.ui.lineEdit_telephone.text())
        self.system_settings.post('院所地址', self.ui.lineEdit_address.text())
        self.system_settings.post('電子郵件', self.ui.lineEdit_email.text())
        self.system_settings.post('早班時間', self.ui.lineEdit_period1.text())
        self.system_settings.post('午班時間', self.ui.lineEdit_period2.text())
        self.system_settings.post('晚班時間', self.ui.lineEdit_period3.text())
        self.system_settings.post('護士人數', self.ui.spinBox_nurse.value())
        self.system_settings.post('藥師人數', self.ui.spinBox_pharmacist.value())
        self._save_check_box(self.ui.checkBox_pharmacy_fee, '申報藥事服務費')
        self._save_check_box(self.ui.checkBox_init_fee, '申報初診照護')
        self._save_check_box(self.ui.checkBox_new_opening, '新特約期間')
        self._save_check_box(self.ui.checkBox_new_clinic_smart_card, '新特約期間使用晶片讀卡機')
        self._save_check_box(self.ui.checkBox_acupuncture_cert, '針灸認證合格')
        self._save_check_box(self.ui.checkBox_no_highly_massage, '不申報高度複雜性傷科')
        self._save_check_box(self.ui.checkBox_pres_days_duplicated, '當日用藥重複檢查次日起算')
        self._save_check_box(self.ui.checkBox_check_injury_period, '檢查損傷診斷碼')
        self._save_check_box(self.ui.checkBox_check_same_disease_pres_days, '檢查相同診斷碼用藥天數')
        self._save_check_box(self.ui.checkBox_check_duplicate_2_days, '用藥重複二日不能存檔')

        self._save_check_box(self.ui.checkBox_ins_prescript_only, '健保自費分開')
        self._save_check_box(self.ui.checkBox_single_self_case, '同自費只算一筆')

        self._save_check_box(self.ui.checkBox_no_convert_general_treat, '不要轉換一般針灸')
        self._save_check_box(self.ui.checkBox_cellphone_required, '行動電話必填')
        self._save_check_box(self.ui.checkBox_only_ins_case, '病歷查詢預設健保')
        self._save_check_box(self.ui.checkBox_yesterday, '日期查詢預設為昨日')
        self._save_check_box(self.ui.checkBox_show_total, '病歷查詢顯示合計')
        self._save_check_box(self.ui.checkBox_regist_yesterday_diag, '隔日過卡不能存檔')
        self._save_check_box(self.ui.checkBox_diagnostic_data_required, '診斷資料必填')
        self._save_check_box(self.ui.checkBox_show_disease4, '顯示次診斷3')
        self._save_check_box(self.ui.checkBox_ins_dosage_non_zero, '健保開藥劑量必須大於0')
        self._save_check_box(self.ui.checkBox_same_disease_course2, '療程同病名超過兩個')
        self._save_check_box(self.ui.checkBox_strict_special_code, '慢性病開藥檢查')

        self._save_date_edit(self.ui.dateEdit_acupuncture_date, '針灸認證合格日期')
        self._save_date_edit(self.ui.dateEdit_ins_judge_init_date, '電子化抽審初診日期')
        self._save_date_edit(self.ui.dateEdit_new_init_date, '新診所初診日期')

        self.system_settings.post('健保業務', self.ui.comboBox_division.currentText())
        self.system_settings.post('劑量上限', self.ui.spinBox_dosage_limitation.value())
        self.system_settings.post('最低劑量', self.ui.spinBox_dosage_minimum.value())
        self.system_settings.post('6歲以下最低劑量', self.ui.spinBox_dosage_minimum2.value())
        self.system_settings.post('預設空白自費頁', self.ui.spinBox_default_self_prescript_tab.value())

        self.system_settings.post('健保用藥成本上限', self.ui.spinBox_ins_drug_fee_limitation.value())
        self.system_settings.post('病歷查詢一頁筆數', self.ui.spinBox_case_page_count.value())
        self.system_settings.post('資源類別', self.ui.comboBox_resource.currentText())
        self.system_settings.post('巡迴區域', self.ui.comboBox_tour_area.currentText())
        self.system_settings.post('矯正機關', self.ui.comboBox_correction_area.currentText())
        self._save_radio_button([
                self.ui.radioButton_reg_normal,
                self.ui.radioButton_reg_home_care,
                self.ui.radioButton_reg_long_term_care,
                self.ui.radioButton_reg_far,
                self.ui.radioButton_reg_mountain,
                self.ui.radioButton_reg_island,
                self.ui.radioButton_reg_correction
            ],
            ['一般門診', '居家醫療', '照護機構中醫照護', '巡迴偏遠', '巡迴山地', '巡迴離島', '矯正機關內門診'],
            '掛號類別'
        )
        self._save_check_box(self.ui.checkBox_check_course_pres_days_once, '檢查療程開藥超過1次')
        self._save_radio_button(
            [
                self.ui.radioButton_once1,
                self.ui.radioButton_once2,
            ],
            ['存檔提醒', '無法存檔'],
            '療程開藥超過1次存檔'
        )
        self._save_radio_button(
            [
                self.ui.radioButton_ic_xml1,
                self.ui.radioButton_ic_xml2,
            ],
            ['1.0', '2.0'],
            '健保IC卡資料上傳格式'
        )
        self._save_radio_button(
            [
                self.ui.radioButton_west_date,
                self.ui.radioButton_tw_date,
            ],
            ['西元年', '民國年'],
            '日期格式'
        )
        self._save_radio_button(
            [
                self.ui.radioButton_dialog_model,
                self.ui.radioButton_dialog_popup,
            ],
            ['對話視窗', '彈出式視窗'],
            '詞庫視窗顯示方式'
        )

        self._save_check_box(self.ui.checkBox_check_same_disease, '內科同病名超過3次')
        self._save_radio_button(
            [
                self.ui.radioButton_same1,
                self.ui.radioButton_same2,
            ],
            ['存檔提醒', '無法存檔'],
            '內科同病名超過3次存檔'
        )

        self.system_settings.post('檢驗所伺服器', self.ui.lineEdit_exam_url.text())
        self.system_settings.post('檢驗所用戶代碼', self.ui.lineEdit_exam_login_id.text())
        self.system_settings.post('檢驗所密碼', self.ui.lineEdit_exam_login_pwd.text())

        self._save_check_box(self.ui.checkBox_course_disease, '療程不同病名不能存檔')
        self._save_check_box(self.ui.checkBox_medicine_duplicated, '開藥連續三次相同不能存檔')
        self._save_check_box(self.ui.checkBox_medicine_two_times, '療程開藥兩次以上提醒')
        self._save_check_box(self.ui.checkBox_check_receipt_diag_share_fee, '檢查門診負擔多退少補')
        self._save_check_box(self.ui.checkBox_calc_treat_drug, '統計針傷給藥人數')
        self._save_check_box(self.ui.checkBox_no_massage, '不申報傷科治療')
        self._save_check_box(self.ui.checkBox_check_deposit_fee, '欠卡申報點數檢查')

        self._save_radio_button(
            [
                self.ui.radioButton_query_asc,
                self.ui.radioButton_query_desc,
            ],
            ['升冪', '降冪'],
            '病歷查詢日期排序'
        )

        self.system_settings.post('預設中度複雜性針灸治療時間', self.ui.spinBox_moderate_acupuncture_time.value())
        self.system_settings.post('預設高度複雜性針灸治療時間', self.ui.spinBox_highly_acupuncture_time.value())
        self.system_settings.post('預設中度複雜性傷科治療時間', self.ui.spinBox_moderate_massage_time.value())
        self.system_settings.post('預設高度複雜性傷科治療時間', self.ui.spinBox_highly_massage_time.value())

        self.system_settings.post('民俗調理單地址', self.ui.lineEdit_print_massage_address.text())
        self.system_settings.post('民俗調理單備註', self.ui.lineEdit_print_massage_remark.text())
        self.system_settings.post('虛擬健保卡授權憑證', self.ui.lineEdit_vhc_token.text())
        self._save_check_box(self.ui.checkBox_alleypin, 'alleypin')
        self.system_settings.post('appID', self.ui.lineEdit_app_id.text())
        self.system_settings.post('secret', self.ui.lineEdit_secret.text())
        self.system_settings.post('webhook', self.ui.lineEdit_webhook.text())

        self._save_check_box(self.ui.checkBox_hainachuan, 'hainachuan')
        self._save_check_box(self.ui.checkBox_sync_seq_number, '線上看診號同步')
        self._save_check_box(self.ui.checkBox_sync_all_seq_number, '廣播叫號同步所有線上看診號')
        self.system_settings.post('webservice', self.ui.lineEdit_webservice.text())
        self.system_settings.post('預約網站後台帳號', self.ui.lineEdit_username.text())
        self.system_settings.post('預約網站後台密碼', self.ui.lineEdit_password.text())

    # 讀取自費設定
    def _save_charge_settings(self):
        self._save_radio_button(
            [
                self.ui.radioButton_total_fee,
                self.ui.radioButton_round,
                self.ui.radioButton_ceiling,
                self.ui.radioButton_chop,
            ],
            ['原價', '四捨五入', '無條件進位', '無條件捨去'],
            '自費折扣進位'
        )
        self._save_radio_button(
            [
                self.ui.radioButton_tail1,
                self.ui.radioButton_tail2
            ],
            ['尾數為0', '尾數為0或5'],
            '自費折扣尾數'
        )
        self._save_radio_button(
            [
                self.ui.radioButton_discount_group,
                self.ui.radioButton_discount_individual
            ],
            ['統一折扣', '個別折扣'],
            '自費折扣方式'
        )
        self._save_radio_button(
            [
                self.ui.radioButton_checkout_by_charge,
                self.ui.radioButton_checkout_by_registration
            ],
            ['批價班別', '掛號班別'],
            '櫃台結帳班別'
        )
        self._save_check_box(self.ui.checkBox_no_discount, '無折扣批價計算')
        self._save_check_box(self.ui.checkBox_not_charge_done, '櫃台結帳列出未完診名單')
        self._save_check_box(self.ui.checkBox_charge_done_allow, '所有資料都已批價才能結帳')
        self._save_check_box(self.ui.checkBox_no_auto_charge, '手動批價')
        self._save_check_box(self.ui.checkBox_sync_share_fee, '部份負擔連動')
        self._save_check_box(self.ui.checkBox_video_charge, '視訊診療須經過批價作業')
        self._save_check_box(self.ui.checkBox_charge_by_cashier, '掛號收費批價進行')
        self._save_check_box(self.ui.checkBox_sync_drug_price, '拷貝處方藥價更新')
        self._save_check_box(self.ui.checkBox_charge_by_kiosk, '在掛號機批價繳費')

        self.system_settings.post('診察費抽成率', self.ui.spinBox_ins_diag_rate.value())
        self.system_settings.post('診療費抽成率', self.ui.spinBox_ins_treat_rate.value())
        self.system_settings.post('自費藥品抽成率', self.ui.spinBox_self_drug_rate.value())
        self.system_settings.post('自費針傷抽成率', self.ui.spinBox_self_treat_rate.value())

        self.system_settings.post('診察費抽成類別', self.ui.comboBox_ins_diag_rate_type.currentText())
        self.system_settings.post('診療費抽成類別', self.ui.comboBox_ins_treat_rate_type.currentText())
        self.system_settings.post('自費藥品抽成類別', self.ui.comboBox_self_drug_rate_type.currentText())
        self.system_settings.post('自費針傷抽成類別', self.ui.comboBox_self_treat_rate_type.currentText())
        self.system_settings.post('民俗調理欄位名稱', self.ui.lineEdit_tc_massage_field_name.text())        

    # 寫入診號控制
    def _save_regist_no_settings(self):
        self._save_check_box(self.ui.checkBox_period_reset, '分班')
        self._save_check_box(self.ui.checkBox_room_reset, '分診')
        self.system_settings.post('早班起始號', self.ui.spinBox_start_no1.value())
        self.system_settings.post('午班起始號', self.ui.spinBox_start_no2.value())
        self.system_settings.post('晚班起始號', self.ui.spinBox_start_no3.value())
        self.system_settings.post('領藥起始號', self.ui.spinBox_start_drug_no.value())
        self.system_settings.post('診號累加器最大號', self.ui.spinBox_max_regist_no.value())
        self._save_radio_button([
            self.ui.radioButton_consecutive,
            self.ui.radioButton_odd,
            self.ui.radioButton_even,
            self.ui.radioButton_reservation_table,
            self.ui.radioButton_odd_sequence,
            self.ui.radioButton_sequence,
            ],
            ['連續號', '單號', '雙號', '預約班表', '單號順序', '就醫順序'],
            '現場掛號給號模式'
        )
        self._save_radio_button([
            self.ui.radioButton_arrival1,
            self.ui.radioButton_arrival2,
            self.ui.radioButton_arrival3,
            self.ui.radioButton_arrival4,
            self.ui.radioButton_arrival_sequence,
            ],
            ['根據班表設定', '根據現場設定', '零號', '雙號順序', '就醫順序'],
            '預約報到給號模式'
        )
        self._save_check_box(self.ui.checkBox_fill_reg_no, '優先遞補現場號')        
        self._save_check_box(self.ui.checkBox_reservation_table_no_time, '預約班表不顯示時間')
        self._save_check_box(self.ui.checkBox_reservation_current_doctor, '預約選擇當診醫師')
        self._save_check_box(self.ui.checkBox_show_memo, '顯示備忘錄')
        self._save_check_box(self.ui.checkBox_same_memo, '備忘錄以病患鍵為主')
        self._save_check_box(self.ui.checkBox_popup_menu, '刪除處方啟用彈出式選單')
        self._save_check_box(self.ui.checkBox_release_reserve_no, '釋出預約號')
        self._save_check_box(self.ui.checkBox_reserve_twice, '同日預約兩次')
        self._save_check_box(self.ui.checkBox_reserve_doctor_limit, '預約次數不同醫師分別計算')
        self._save_check_box(self.ui.checkBox_reserve_allow_today, '開放當日網路預約')
        self._save_check_box(self.ui.checkBox_cancel_reserve_today, '當日可以取消網路預約')
        self._save_check_box(self.ui.checkBox_no_waiting_progress, '網路預約不顯示看診進度')
        self._save_check_box(self.ui.checkBox_no_first_reservation, '不開放初診網路預約')
        self._save_check_box(self.ui.checkBox_arrival_late, '預約遲到寫入掛號備註')
        self._save_check_box(self.ui.checkBox_over_number, '預約過號寫入掛號備註')        
        self._save_check_box(self.ui.checkBox_show_last_case_remark, '預約名單顯示上次病歷備註')
        self._save_check_box(self.ui.checkBox_show_late_number, '預約過號顯示過號序號')
        
        self.system_settings.post('預約次數限制', self.ui.spinBox_reservation_limit.value())
        self.system_settings.post('爽約次數', self.ui.spinBox_absent.value())
        self.system_settings.post('爽約期間', self.ui.spinBox_reservation_period.value())
        self.system_settings.post('還卡期限', self.ui.spinBox_return_card_days.value())
        self.system_settings.post('網路預約開放週數', self.ui.spinBox_max_reserve_weeks.value())
        self.system_settings.post('未回診天數', self.ui.spinBox_no_return_days.value())
        self._save_start_no()

    def _save_start_no(self):
        keyword = '指定診別起始號'
        self.database.exec_sql(f'DELETE FROM system_settings WHERE Field LIKE "{keyword}-%"')

        row_count = self.ui.tableWidget_start_no.rowCount()
        if row_count <= 0:
            return

        start_no_dict = {}
        for row_no in range(row_count):
            room = self.ui.tableWidget_start_no.item(row_no, 0).text()
            field_name = f'{keyword}-{room}'

            start_no_1 = self.ui.tableWidget_start_no.item(row_no, 1).text()
            start_no_2 = self.ui.tableWidget_start_no.item(row_no, 2).text()
            start_no_3 = self.ui.tableWidget_start_no.item(row_no, 3).text()
            start_no_dict['早班'] = int(start_no_1)
            start_no_dict['午班'] = int(start_no_2)
            start_no_dict['晚班'] = int(start_no_3)
            start_no_json = json.dumps(start_no_dict, separators=(',', ':'))

            self.system_settings.post(field_name, start_no_json)

    def _save_bulletin(self):
        self.database.exec_sql('DELETE FROM bulletin')

        row_count = self.ui.tableWidget_bulletin.rowCount()
        if row_count <= 0:
            return

        fields = ['Title', 'Content']
        for row_no in range(row_count):
            title = self.ui.tableWidget_bulletin.item(row_no, 0).text()
            content = self.ui.tableWidget_bulletin.item(row_no, 1).text()

            self.database.insert_record('bulletin', fields, [title, content])

    def _save_notice(self):
        self.database.exec_sql('DELETE FROM case_extension WHERE ExtensionType = "網站注意事項"')

        row_count = self.ui.tableWidget_notice.rowCount()
        if row_count <= 0:
            return

        fields = ['CaseKey', 'ExtensionType', 'Content']
        for row_no in range(row_count):
            content = self.ui.tableWidget_notice.item(row_no, 0).text()

            self.database.insert_record('case_extension', fields, [0, '網站注意事項', content])

    # 寫入掛號設定
    def _save_registration_settings(self):
        self._save_radio_button([self.ui.radioButton_ins,
                                 self.ui.radioButton_self],
                                ['健保', '自費'],
                                '預設門診類別')
        self._save_radio_button([self.ui.radioButton_multi_sales,
                                 self.ui.radioButton_single_sales],
                                ['複選', '單選'],
                                '自購藥銷售人員')
        self.system_settings.post('首次警告次數', self.ui.spinBox_diag_count.value())
        self.system_settings.post('針傷警告次數', self.ui.spinBox_treat_count.value())
        self._save_radio_button(
            [
                self.ui.radioButton_deposit_date1,
                self.ui.radioButton_deposit_date2,
                self.ui.radioButton_deposit_date3,
                self.ui.radioButton_deposit_date4,
            ],
            ['上個月1日', '上個月20日', '本月1日', '10天前'],
            '欠卡日期檢查範圍'
        )
        self._save_radio_button(
            [
                self.ui.radioButton_order_by_default,
                self.ui.radioButton_order_by_time,
                self.ui.radioButton_order_by_regist_no,
            ],
            ['預設排序', '時間排序', '診號排序'],
            '掛號候診名單排序方式'
        )
        self._save_check_box(self.ui.checkBox_register_current_doctor, '掛號選擇當診醫師')
        self._save_check_box(self.ui.checkBox_day14, '掛號療程14日未完成提醒')
        self._save_check_box(self.ui.checkBox_interrupt_course, '療程中斷不續療程')
        self._save_check_box(self.ui.checkBox_past_history_show_symptom, '掛號過去病歷顯示主訴')
        self._save_check_box(self.ui.checkBox_past_history_show_massage, '掛號過去病歷顯示民俗調理')
        self._save_check_box(self.ui.checkBox_no_regist_no_duplicate, '掛號診號不可重複')
        self._save_check_box(self.ui.checkBox_regist_visit_count, '掛號作業顯示初診統計')
        self._save_check_box(self.ui.checkBox_auto_last_treat_type, '掛號新療程自動帶出上次就醫類別')
        self._save_check_box(self.ui.checkBox_debt_stop_regist, '欠款未還不能掛號')
        self._save_check_box(self.ui.checkBox_show_purchase_case, '掛號已就診名單顯示自購藥病歷')
        self._save_check_box(self.ui.checkBox_show_massage_fee, '掛號名單顯示民俗調理費')
        self._save_check_box(self.ui.checkBox_no_change_doctor, '掛號診別更改不要連動醫師姓名')        

        self._save_bulletin()
        self._save_notice()

    # 看診設定
    def _save_doctor_settings(self):
        self.system_settings.post('診療室', self.ui.spinBox_room.value())
        self.system_settings.post('過去病歷一頁筆數', self.ui.spinBox_count_per_page.value())
        self.system_settings.post('病歷版面', self.ui.comboBox_medical_record_page.currentText())
        self.system_settings.post('病名版面', self.ui.comboBox_disease_layout.currentText())
        self._save_check_box(self.ui.checkBox_copy_past, '自動顯示過去病歷')
        self._save_check_box(self.ui.checkBox_only_symptom, '過去病歷診察資料只顯示主訴')
        self._save_check_box(self.ui.checkBox_no_patient_remark, '病歷資料不顯示病患備註')
        self._save_check_box(self.ui.checkBox_copy_self_prescript, '預設拷貝自費處方')
        self._save_check_box(self.ui.checkBox_copy_ins_past_medicine, '預設拷貝健保針傷科處方用藥')
        self._save_check_box(self.ui.checkBox_copy_remark, '預設拷貝備註')
        self._save_check_box(self.ui.checkBox_round, '折扣四捨五入')
        self._save_check_box(self.ui.checkBox_show_massage, '過去病歷顯示民俗調理')
        self._save_check_box(self.ui.checkBox_show_massager, '過去病歷顯示推拿師父')
        self._save_check_box(self.ui.checkBox_auto_cashier, '自動完成批價作業')
        self._save_check_box(self.ui.checkBox_display_custom, '健保處方詞庫顯示自訂類別')
        self._save_check_box(self.ui.checkBox_order_by_icd, '病名詞庫以病名碼排序')
        self._save_check_box(self.ui.checkBox_diag_timer, '顯示看診計時器')
        self._save_check_box(self.ui.checkBox_hit_rate_by_medicine_type, '處方點擊率依照處方類別排序')
        self._save_check_box(self.ui.checkBox_no_separator, '最近病歷不顯示分隔線')
        self._save_check_box(self.ui.checkBox_case_large_font, '病歷主訴大字體')
        self._save_check_box(self.ui.checkBox_no_switch_ime, '不要自動切換輸入法')
        self._save_check_box(self.ui.checkBox_show_all_statistics, '候診名單病歷統計顯示全院統計')
        self._save_check_box(self.ui.checkBox_no_ins_prescript, '健保處方預設不調劑')
        self._save_check_box(self.ui.checkBox_show_simple, '過去病歷顯示精簡顯示頁')

        self._save_check_box(self.ui.checkBox_ime_en, '望聞問切輸入法預設英數')
        self._save_check_box(self.ui.checkBox_ime_zh, '診斷碼輸入法預設中文')
        self._save_check_box(self.ui.checkBox_prescript_edit_mode, '處方輸入編輯模式')

        self._save_check_box(self.ui.checkBox_hide_reserve_time, '醫師候診名單隱藏預約時間')
        self._save_check_box(self.ui.checkBox_hide_wait_time, '醫師候診名單隱藏候診時間')
        self._save_check_box(self.ui.checkBox_set_waiting_list, '自動切換醫師候診名單')
        self._save_check_box(self.ui.checkBox_no_beep, '醫師候診名單不要提示音')
        self._save_check_box(self.ui.checkBox_sort_dosage, '處方劑量欄位可以排序')
        self._save_check_box(self.ui.checkBox_fixed_waiting_list_width, '醫師候診名單欄位固定寬度')
        self._save_check_box(self.ui.checkBox_same_doctor, '病歷存檔檢查醫師姓名')
        self._save_check_box(self.ui.checkBox_check_fees, '病歷存檔檢查補退掛號費用')
        self._save_check_box(self.ui.checkBox_no_location_light_color, '處方無存放位置淡色顯示')
        self._save_check_box(self.ui.checkBox_display_ins_drug, '健保處方詞庫只顯示單方複方')
        self._save_check_box(self.ui.checkBox_no_instruction_pres_days, '單一處方服法不可取代用藥天數')
        self._save_check_box(self.ui.checkBox_no_insufficent_medicine, '庫存量不足不要提醒')
        self._save_check_box(self.ui.checkBox_no_zero_price, '單日計價輸入藥品不要歸零')        
        self._save_check_box(self.ui.checkBox_no_complicated_treat_dialog, '輸入病名後不要彈出複雜性針傷提示視窗')
        self._save_check_box(self.ui.checkBox_reservation_current_period, '醫師候診名單只顯示當班預約資料')
        self._save_check_box(self.ui.checkBox_herb_only, '處方詞庫僅列出水藥')
        self._save_check_box(self.ui.checkBox_symptom_br, '主訴換行')
        self.system_settings.post('病名詞庫預設類別', self.ui.comboBox_disease_group.currentText())
        self.system_settings.post('預設就醫類別', self.ui.comboBox_default_treat_type.currentText())

        self.system_settings.post('給藥包數', self.ui.spinBox_packages.value())
        self.system_settings.post('給藥天數', self.ui.spinBox_days.value())
        self.system_settings.post('用藥指示', self.ui.comboBox_instruction.currentText())
        self._save_check_box(self.ui.checkBox_doctor_treat, '醫師親自處置')
        self._save_check_box(self.ui.checkBox_massager_fee, '自動帶出民俗調理費')
        self._save_check_box(self.ui.checkBox_first_massage_fee, '療程首次民俗調理費')
        self._save_check_box(self.ui.checkBox_display_self_massage, '候診名單顯示自費民俗調理')
        self._save_radio_button([self.ui.radioButton_dosage1,
                                 self.ui.radioButton_dosage2,
                                 self.ui.radioButton_dosage3],
                                ['日劑量', '次劑量', '總量'],
                                '劑量模式')
        self._save_check_box(self.ui.checkBox_dosage_percent, '比例法劑量')
        self._save_check_box(self.ui.checkBox_no_ins_cost, '不要顯示健保用藥成本')

        self._save_radio_button([self.ui.radioButton_auto_chart_no1,
                                 self.ui.radioButton_auto_chart_no2],
                                ['無', '身份證後四碼'],
                                '自動產生病歷號')
        self._save_radio_button([self.ui.radioButton_self_room,
                                 self.ui.radioButton_doctor_room,
                                 self.ui.radioButton_all_room],
                                ['指定診別', '醫師診別', '所有診別'],
                                '候診名單顯示診別')
        self._save_radio_button([self.ui.radioButton_order_no,
                                 self.ui.radioButton_order_time],
                                ['診號排序', '時間排序'],
                                '看診排序')
        self._save_radio_button([self.ui.radioButton_order_medicine_key,
                                 self.ui.radioButton_order_medicine_type],
                                ['開藥順序', '處方類別'],
                                '處方排序')
        self._save_radio_button([self.ui.radioButton_by_dict_name,
                                 self.ui.radioButton_by_hit_rate,
                                 self.ui.radioButton_by_timestamp],
                                ['詞庫名稱', '點擊率', '最後點擊時戳'],
                                '詞庫排序')
        self._save_radio_button([self.ui.radioButton_by_diag_name,
                                 self.ui.radioButton_by_diag_hit_rate,
                                 self.ui.radioButton_by_diag_timestamp],
                                ['詞庫名稱', '點擊率', '最後點擊時戳'],
                                '診察詞庫排序')
        self._save_radio_button([self.ui.radioButton_normal_price,
                                self.ui.radioButton_single_day_price],
                                ['正常計價', '單日計價'],
                                '自費處方預設計價方式')
        self._save_radio_button([self.ui.radioButton_input_dosage,
                                 self.ui.radioButton_save_dosage],
                                ['輸入處方時檢查', '存檔時檢查'],
                                '健保處方給藥劑量上限檢查時機')
        self._save_radio_button([self.ui.radioButton_input_costs,
                                 self.ui.radioButton_save_costs],
                                ['輸入處方時檢查', '存檔時檢查'],
                                '健保用藥成本上限檢查時機')
        self._save_radio_button([self.ui.radioButton_normal_view,
                                 self.ui.radioButton_simple_view],
                                ['詳細檢視', '精簡檢視'],
                                '病歷查詢檢視方式')

        self.system_settings.post('舌診1', self.ui.lineEdit_tongue1.text())
        self.system_settings.post('舌診2', self.ui.lineEdit_tongue2.text())
        self.system_settings.post('舌診3', self.ui.lineEdit_tongue3.text())
        self.system_settings.post('舌診4', self.ui.lineEdit_tongue4.text())
        self.system_settings.post('舌診5', self.ui.lineEdit_tongue5.text())

        self.system_settings.post('脈象1', self.ui.lineEdit_pulse1.text())
        self.system_settings.post('脈象2', self.ui.lineEdit_pulse2.text())
        self.system_settings.post('脈象3', self.ui.lineEdit_pulse3.text())
        self.system_settings.post('脈象4', self.ui.lineEdit_pulse4.text())
        self.system_settings.post('脈象5', self.ui.lineEdit_pulse5.text())
        self.system_settings.post('脈象6', self.ui.lineEdit_pulse6.text())
        self.system_settings.post('脈象7', self.ui.lineEdit_pulse7.text())
        self.system_settings.post('脈象8', self.ui.lineEdit_pulse8.text())
        self.system_settings.post('脈象9', self.ui.lineEdit_pulse9.text())
        self.system_settings.post('脈象10', self.ui.lineEdit_pulse10.text())

    def _save_printer_settings(self):
        self.system_settings.post('列印門診掛號單', self.ui.comboBox_regist_print_mode.currentText())
        self.system_settings.post('列印預約掛號單', self.ui.comboBox_reservation_print_mode.currentText())
        self.system_settings.post('列印健保處方箋', self.ui.comboBox_ins_prescript_print_mode.currentText())
        self.system_settings.post('列印自費處方箋', self.ui.comboBox_self_prescript_print_mode.currentText())
        self.system_settings.post('列印健保醫療收據', self.ui.comboBox_ins_receipt_print_mode.currentText())
        self.system_settings.post('列印自費醫療收據', self.ui.comboBox_self_receipt_print_mode.currentText())
        self.system_settings.post('列印藥袋', self.ui.comboBox_bag_print_mode.currentText())
        self.system_settings.post('列印民俗調理單', self.ui.comboBox_massage_print_mode.currentText())
        self.system_settings.post('列印其他收據', self.ui.comboBox_misc_print_mode.currentText())
        self.system_settings.post('列印其他收據2', self.ui.comboBox_misc2_print_mode.currentText())
        self.system_settings.post('列印其他收據3', self.ui.comboBox_misc3_print_mode.currentText())

        self.system_settings.post('門診掛號單格式', self.ui.comboBox_regist_form.currentText())
        self.system_settings.post('預約掛號單格式', self.ui.comboBox_reservation_form.currentText())
        self.system_settings.post('健保處方箋格式', self.ui.comboBox_ins_prescript_form.currentText())
        self.system_settings.post('自費處方箋格式', self.ui.comboBox_self_prescript_form.currentText())
        self.system_settings.post('健保醫療收據格式', self.ui.comboBox_ins_receipt_form.currentText())
        self.system_settings.post('自費醫療收據格式', self.ui.comboBox_self_receipt_form.currentText())
        self.system_settings.post('藥袋格式', self.ui.comboBox_bag_form.currentText())
        self.system_settings.post('民俗調理單格式', self.ui.comboBox_massage_form.currentText())
        self.system_settings.post('其他收據格式', self.ui.comboBox_misc_form.currentText())
        self.system_settings.post('其他收據2格式', self.ui.comboBox_misc2_form.currentText())
        self.system_settings.post('其他收據3格式', self.ui.comboBox_misc3_form.currentText())

        self.system_settings.post('門診掛號單印表機', self.ui.comboBox_regist_printer.currentText())
        self.system_settings.post('預約掛號單印表機', self.ui.comboBox_reservation_printer.currentText())
        self.system_settings.post('健保處方箋印表機', self.ui.comboBox_ins_prescript_printer.currentText())
        self.system_settings.post('自費處方箋印表機', self.ui.comboBox_self_prescript_printer.currentText())
        self.system_settings.post('健保醫療收據印表機', self.ui.comboBox_ins_receipt_printer.currentText())
        self.system_settings.post('自費醫療收據印表機', self.ui.comboBox_self_receipt_printer.currentText())
        self.system_settings.post('藥袋印表機', self.ui.comboBox_bag_printer.currentText())
        self.system_settings.post('民俗調理單印表機', self.ui.comboBox_massage_printer.currentText())
        self.system_settings.post('民俗調理單印表機2', self.ui.comboBox_massage_printer2.currentText())
        self.system_settings.post('其他收據印表機', self.ui.comboBox_misc_printer.currentText())
        self.system_settings.post('其他收據2印表機', self.ui.comboBox_misc2_printer.currentText())
        self.system_settings.post('其他收據3印表機', self.ui.comboBox_misc3_printer.currentText())

        self.system_settings.post('列印報表', self.ui.comboBox_report_print_mode.currentText())
        self.system_settings.post('報表印表機', self.ui.comboBox_report_printer.currentText())
        self.system_settings.post('報表印表機紙張大小', self.ui.comboBox_report_printer_paper_size.currentText())

        self.system_settings.post('醫療費用證明書抬頭', self.ui.lineEdit_certificate_payment_title.text())
        self.system_settings.post('民俗調理項目名稱', self.ui.lineEdit_folk_massage_name.text())
        self.system_settings.post('民俗調理收據抬頭', self.ui.lineEdit_folk_massage_title.text())
        self.system_settings.post('醫療費用證明自費藥費欄位名稱', self.ui.lineEdit_medicine_fee_field_name.text())
        self.system_settings.post('醫療費用證明自費處置欄位名稱', self.ui.lineEdit_treat_fee_field_name.text())
        self.system_settings.post('醫療費用證明其他費用欄位名稱', self.ui.lineEdit_misc_fee_field_name.text())
        self.system_settings.post('醫療費用證明自費金額欄位名稱', self.ui.lineEdit_total_fee_field_name.text())
        self.system_settings.post('醫療費用自付明細自費金額欄位名稱', self.ui.lineEdit_total_fee_field_name2.text())
        self.system_settings.post('醫療費用收據自訂報稅備註', self.ui.plainTextEdit_tax_remark.toPlainText())

        self.system_settings.post('自訂適應症', self.ui.lineEdit_indication.text())
        self.system_settings.post('列印預設字體', self.ui.lineEdit_print_font.text())
        self.system_settings.post('自訂院所名稱', self.ui.lineEdit_custom_clinic_name.text())

        # self._save_check_box(self.ui.checkBox_print_total_dosage, '列印藥品總量')  # TODO
        # self._save_check_box(self.ui.checkBox_print_daily_dosage, '列印藥品日量')  # TODO
        # self._save_check_box(self.ui.checkBox_print_ins_total_dosage, '列印健保藥品總量')  # TODO
        self._save_check_box(self.ui.checkBox_print_location, '列印藥品存放位置')
        self._save_check_box(self.ui.checkBox_location_before_medicine, '列印藥品存放位置在處方名稱前面')
        self._save_check_box(self.ui.checkBox_print_remark, '列印病歷備註')
        self._save_check_box(self.ui.checkBox_print_alias, '列印處方別名')
        self._save_check_box(self.ui.checkBox_print_folk_massage, '列印民俗調理')
        self._save_check_box(self.ui.checkBox_print_regist_non_zero, '掛號收據無金額不列印')
        self._save_check_box(self.ui.checkBox_print_clinic_name, '列印院所名稱')
        self._save_check_box(self.ui.checkBox_print_massager, '列印推拿師父')
        self._save_check_box(self.ui.checkBox_print_reservation_no, '列印預約號碼')
        self._save_check_box(self.ui.checkBox_print_treat, '列印穴道處置')
        self._save_check_box(self.ui.checkBox_print_no_treat_fee, '費用總表合併處置費至藥費')
        self._save_check_box(self.ui.checkBox_print_treatment, '列印針傷處置名稱')
        self._save_check_box(self.ui.checkBox_no_tax_hint, '不印報稅提示')
        self._save_check_box(self.ui.checkBox_print_stamp_duty, '列印印花稅總繳')
        self._save_check_box(self.ui.checkBox_no_print_prescript, '費用收據不印處方')
        self._save_check_box(self.ui.checkBox_no_print_fee, '處方箋不印費用明細')
        self._save_check_box(self.ui.checkBox_no_print_discount, '不印折扣')
        self._save_check_box(self.ui.checkBox_print_qrcode, '列印條碼')
        self._save_check_box(self.ui.checkBox_self_prescript_package_dosage, '自費處方次劑量')
        self._save_check_box(self.ui.checkBox_order_by_location, '列印處方依照存放位置排序')
        self._save_check_box(self.ui.checkBox_no_massage_list, '開立費用證明不要列出民俗調理')
        self._save_check_box(self.ui.checkBox_print_certificate_diagnosis_date, '列印診斷證明日期明細')
        self._save_check_box(self.ui.checkBox_print_symptom_limitation, '列印主訴字數限制')
        self._save_check_box(self.ui.checkBox_print_medicine_limitation, '列印處方字數限制')
        self._save_check_box(self.ui.checkBox_self_daily_dosage, '自費收據列印日量')
        self._save_check_box(self.ui.checkBox_print_prescript_total_dosage, '處方箋列印總量')
        self._save_check_box(self.ui.checkBox_ins_receipt, '健保費用收據同時輸出至掛號印表機')
        self._save_check_box(self.ui.checkBox_self_receipt, '自費費用收據同時輸出至掛號印表機')
        self._save_check_box(self.ui.checkBox_print_registration, '加印一張掛號單')

        self._save_check_box(self.ui.groupBox_ins_receipt_size, '自訂健保醫療收據尺寸邊界')
        self.system_settings.post('健保醫療收據寬度', self.ui.doubleSpinBox_ins_receipt_width.value())
        self.system_settings.post('健保醫療收據長度', self.ui.doubleSpinBox_ins_receipt_length.value())
        self.system_settings.post('健保醫療收據尺寸單位', self.ui.comboBox_ins_receipt_size_unit.currentText())

        self.system_settings.post('健保醫療收據左邊界', self.ui.doubleSpinBox_ins_receipt_left_margin.value())
        self.system_settings.post('健保醫療收據上邊界', self.ui.doubleSpinBox_ins_receipt_top_margin.value())
        self.system_settings.post('健保醫療收據邊界單位', self.ui.comboBox_ins_receipt_margin_unit.currentText())

        self._save_check_box(self.ui.groupBox_self_receipt_size, '自訂自費醫療收據尺寸邊界')
        self.system_settings.post('自費醫療收據寬度', self.ui.doubleSpinBox_self_receipt_width.value())
        self.system_settings.post('自費醫療收據長度', self.ui.doubleSpinBox_self_receipt_length.value())
        self.system_settings.post('自費醫療收據尺寸單位', self.ui.comboBox_self_receipt_size_unit.currentText())

        self.system_settings.post('自費醫療收據左邊界', self.ui.doubleSpinBox_self_receipt_left_margin.value())
        self.system_settings.post('自費醫療收據上邊界', self.ui.doubleSpinBox_self_receipt_top_margin.value())
        self.system_settings.post('自費醫療收據邊界單位', self.ui.comboBox_self_receipt_margin_unit.currentText())

        self.system_settings.post('列印主訴字數', self.ui.spinBox_symptom_count.value())
        self.system_settings.post('列印處方字數', self.ui.spinBox_medicine_character_count.value())
        self._save_check_box(self.ui.checkBox_agreement, '自費同意書自費1金額')
        self._save_radio_button(
            [self.ui.radioButton_print_order1, self.ui.radioButton_print_order2, self.ui.radioButton_print_order3],
            ['列印順序1', '列印順序2', '列印順序3'],
            '病歷存檔列印順序'
        )
        self._save_radio_button(
            [self.ui.radioButton_print_total_dosage,
             self.ui.radioButton_print_daily_dosage,
             self.ui.radioButton_print_all_dosage],
            ['總量', '日量', '日量+總量'],
            '收費收據列印劑量'
        )
        self._save_radio_button(
            [self.ui.radioButton_print_horizontal, self.ui.radioButton_print_vertical],
            ['水平列印', '垂直列印'],
            '處方列印方向'
        )
        self._save_radio_button(
            [self.ui.radioButton_elec_prescript1, self.ui.radioButton_elec_prescript2],
            ['格式1', '格式2'],
            '電子處方箋格式'
        )
        self._save_check_box(self.ui.checkBox_print_self_fee, '列印所有收費收據費用明細')
        self._save_check_box(self.ui.checkBox_print_each_self_fee, '列印所有收費收據各自金額')
        self._save_check_box(self.ui.checkBox_print_bg_color, '列印報表雙色印刷')
        self._save_check_box(self.ui.checkBox_print_no_dosage_receipt, '自費加印無劑量收據')

        self.system_settings.post('費用收據處方欄字體大小', self.ui.spinBox_prescript_font_size.value())
        self.system_settings.post('醫療費用證明預設金額', self.ui.spinBox_certificate_diag_default_fee.value())

    def _save_reader_settings(self):
        self._save_check_box(self.ui.checkBox_use_webcam, '使用webcam讀取虛擬健保卡')
        self._save_check_box(self.ui.checkBox_use_reader, '使用讀卡機')
        self._save_check_box(self.ui.checkBox_run_csfsim, '自動開啟雲端安全模組主控台')
        self.system_settings.post('健保卡讀卡機連接埠', self.ui.spinBox_ic_reader_port.value())
        self._save_radio_button([self.ui.radioButton_smart_card_reader,
                                 self.ui.radioButton_nhi_card_reader],
                                ['晶片讀卡機', '健保讀卡機'],
                                '讀卡機類型')
        self._save_radio_button([self.ui.radioButton_cshis5,
                                self.ui.radioButton_cshis6],
                                ['cshis5', 'cshis6'],
                                '讀卡機控制軟體版本')
        self._save_check_box(self.ui.checkBox_read_record, '讀取卡片就醫記錄')
        self._save_check_box(self.ui.checkBox_read_disease, '讀取卡片重大傷病')
        self._save_radio_button([self.ui.radioButton_regist_secure,
                                 self.ui.radioButton_doctor_secure],
                                ['掛號', '診療'],
                                '產生安全簽章位置')

        self._save_radio_button([self.ui.radioButton_doctor_write,
                                 self.ui.radioButton_regist_write,
                                 self.ui.radioButton_charge_write],
                                ['診療', '掛號', '批價'],
                                '產生醫令簽章位置')
        self._save_check_box(self.ui.checkBox_vhc_card_operation, '虛擬健保卡統一在掛號作業')
        self._save_check_box(self.ui.checkBox_cshis_test_ip, '使用測試環境')
        self.system_settings.post('SAMID', self.ui.lineEdit_sam_id.text())

    def _save_misc(self):
        self.system_settings.post('工作站編號', str(self.ui.spinBox_station_no.value()))
        self.system_settings.post('工作站位置', self.ui.lineEdit_position.text())
        self.system_settings.post('外觀主題', self.ui.comboBox_theme.currentText())
        self.system_settings.post('外觀顏色', self.ui.comboBox_color.currentText())
        self.system_settings.post('電子病歷交換檔輸出路徑', self.ui.lineEdit_emr_path.text())
        self.system_settings.post('資料路徑', self.ui.lineEdit_clinic_dir.text())
        self.system_settings.post('異地備份路徑', self.ui.lineEdit_external_backup_dir.text())
        self.system_settings.post('伺服器物理備份路徑', self.ui.lineEdit_database_physical_dir.text())
        self.system_settings.post('伺服器資料來源', self.ui.lineEdit_database_dir.text())
        self.system_settings.post('影像檔路徑', self.ui.lineEdit_image_path.text())
        self.system_settings.post('電子處方箋路徑', self.ui.lineEdit_electronic_prescript_path.text())
        self.system_settings.post('掛號機錢箱路徑', self.ui.lineEdit_cashier_machine_path.text())
        self.system_settings.post('血壓計路徑', self.ui.lineEdit_blood_measure_path.text())
        self.system_settings.post('叫號燈連接埠', self.ui.comboBox_led_port.currentText())
        self.system_settings.post('叫號燈ip', self.ui.lineEdit_led_ip.text())
        self.system_settings.post('叫號燈port', self.ui.lineEdit_led_port.text())
        self.system_settings.post('電子秤連接埠', self.ui.comboBox_scale_port.currentText())
        self.system_settings.post('電子秤測重時間', self.ui.doubleSpinBox_scale_time.value())

        self._save_check_box(self.ui.checkBox_ring_bell, '叫號燈響鈴')

        self._save_check_box(self.ui.checkBox_side_bar, '顯示側邊欄')
        self._save_check_box(self.ui.checkBox_font_weight, '粗體字')
        self._save_check_box(self.ui.checkBox_do_not_display_bulletin, '不要顯示最新消息')
        self._save_check_box(self.ui.checkBox_self_emr, '匯出電子病歷包含自費病歷')
        self._save_check_box(self.ui.checkBox_use_docker, '使用docker')
        self._save_font_size()
        self._save_radio_button([
                self.ui.radioButton_single_instance,
                self.ui.radioButton_multi_instance],
            ['獨立執行', '多個執行'],
            '醫療系統執行個體'
        )
        self._save_radio_button([
                self.ui.radioButton_real_time_stock,
                self.ui.radioButton_batch_stock],
            ['即時調整', '批次調整'],
            '調整庫存量'
        )
        self._save_check_box(self.ui.checkBox_voice_server, '廣播叫號主機')
        self._save_check_box(self.ui.checkBox_voice_no_call_room, '叫號不包含診療室')
        self._save_check_box(self.ui.checkBox_voice_call_name, '叫號包含病患姓名')
        self._save_check_box(self.ui.checkBox_voice_call_next, '叫號包含下一位請準備')        
        self._save_check_box(self.ui.checkBox_voice_with_led, '叫號同時啟動叫號燈')
        self._save_check_box(self.ui.checkBox_import_all_database, '執行匯入全部資料庫')
        self._save_check_box(self.ui.checkBox_sync_in_price, '輸入進貨資料同步更新藥品進價')  # 2024.01.31 仲明堂

        self.system_settings.post('封存資料庫名稱', self.ui.lineEdit_archive_database_name.text())
        self.system_settings.post('自訂叫號格式', self.ui.lineEdit_voice_call_format.text())

        self._save_font_weight()

    def _save_font_size(self):
        css_file = os.path.join(
            system_utils.BASE_DIR, system_utils.CSS_PATH, system_utils.get_css_file(self.system_settings)
        )
        font_size = self._get_css_font_size()
        if self.ui.spinBox_font_size.value() == font_size:
            return

        size = self.ui.spinBox_font_size.value()
        new_size = f'font-size: {size}px;'

        s = open(css_file, 'r', encoding='utf-8').read()
        for i in range(12, 33):
            font_size = f'font-size: {i}px;'
            if s.find(font_size) < 0:
                continue

            s = s.replace(font_size, new_size)

            f = open(css_file, 'w', encoding='utf8')
            f.write(s)
            f.close()
            break

    def _save_font_weight(self):
        css_file = os.path.join(
            system_utils.BASE_DIR, system_utils.CSS_PATH, system_utils.get_css_file(self.system_settings)
        )
        current_font_weight = self._get_css_font_weight()

        if self.ui.checkBox_font_weight.isChecked():
            new_font_weight = 'font-weight: bold; /* system */'
        else:
            new_font_weight = 'font-weight: normal; /* system */'

        if current_font_weight == new_font_weight:
            return

        s = open(css_file, 'r', encoding='utf-8').read()
        s = s.replace(current_font_weight, new_font_weight)

        f = open(css_file, 'w', encoding='utf8')
        f.write(s)
        f.close()

    # 取得電子病歷輸出路徑
    def _get_emr_path(self):
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory(
            self, "選擇電子病歷交換檔路徑",
            self.ui.lineEdit_emr_path.text(), options=options
        )
        if directory:
            self.ui.lineEdit_emr_path.setText(directory)

    def _get_clinic_dir(self):
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory(
            self, "取得院所專屬資料夾",
            '請選擇院所專用資料夾, 以供申報及備份使用', options=options
        )
        if directory:
            self.ui.lineEdit_clinic_dir.setText(directory)

    def _get_external_dir(self):
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory(
            self, "取得院所專屬資料夾",
            '請選擇外接備份裝置資料夾, 以供申報及備份使用', options=options
        )
        if directory:
            self.ui.lineEdit_external_backup_dir.setText(directory)

    def _get_database_physical_dir(self):
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory(
            self, "取得外接硬碟資料夾",
            '請選擇外接備份裝置資料夾, 以供備份使用', options=options
        )
        if directory:
            self.ui.lineEdit_database_physical_dir.setText(directory)

    def _get_database_dir(self):
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory(
            self, "取得資料庫來源",
            '請選擇資料庫來源資料夾, 以供備份使用', options=options
        )
        if directory:
            self.ui.lineEdit_database_dir.setText(directory)

    # 取得影像檔路徑
    def _get_image_path(self):
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory(
            self, "選擇影像檔路徑",
            self.ui.lineEdit_image_path.text(), options=options
        )
        if directory:
            self.ui.lineEdit_image_path.setText(directory)

    # 取得電子處方箋路徑
    def _get_electronic_prescript_path(self):
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory(
            self, "選擇電子處方箋路徑",
            self.ui.lineEdit_electronic_prescript_path.text(), options=options
        )
        if directory:
            self.ui.lineEdit_electronic_prescript_path.setText(directory)

    # 取得掛號機錢箱路徑
    def _get_cashier_machine_path(self):
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory(
            self, "選擇掛號機錢箱路徑",
            self.ui.lineEdit_cashier_machine_path.text(), options=options
        )
        if directory:
            self.ui.lineEdit_cashier_machine_path.setText(directory)

    # 取得血壓計路徑
    def _get_blood_measure_path(self):
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory(
            self, "選擇血壓計路徑",
            self.ui.lineEdit_blood_measure_path.text(), options=options
        )
        if directory:
            self.ui.lineEdit_blood_measure_path.setText(directory)

    ###########################################################################################################
    # 讀取 check_box 的資料
    def _set_check_box(self, check_box, field):
        if self.system_settings.field(field) == 'Y':
            check_box.setChecked(True)
        else:
            check_box.setChecked(False)

    # 讀取 check_box 的資料
    def _set_date_edit(self, date_edit, field):
        date = self.system_settings.field(field)
        if date is None:
            return

        year, month, day = date.split('-')
        date_edit.setDate(QtCore.QDate(int(year), int(month), int(day)))

    # 讀取 radio_button
    def _set_radio_button(self, radio_buttons, values, field):
        for radio_button, value in zip(radio_buttons, values):
            if self.system_settings.field(field) == value:
                radio_button.setChecked(True)
                break

    ###################################################################################################################
    # 寫入 check_box 的資料
    def _save_check_box(self, check_box, field):
        if check_box.isChecked():
            self.system_settings.post(field, 'Y')
        else:
            self.system_settings.post(field, 'N')

    # 寫入 date_edit 的資料
    def _save_date_edit(self, date_edit, field):
        date = date_edit.date().toString('yyyy-MM-dd')
        self.system_settings.post(field, date)

    # 寫入 radio_button
    def _save_radio_button(self, radio_buttons, values, field):
        select_value = None
        for radio_button, value in zip(radio_buttons, values):
            if radio_button.isChecked():
                select_value = value
                break

        self.system_settings.post(field, select_value)

    # OK
    def button_accepted(self):
        self._save_settings()
        del self.system_settings

    # Cancel
    def button_rejected(self):
        del self.system_settings

    # 更改工作站編號
    def spin_button_value_changed(self):
        self.system_settings = class_utils.get_system_settings(
            self.database, self.parent.config_file, self.ui.spinBox_station_no.value()
        )
        self.ui.spinBox_station_no.setFocus()

    def _detect_com_port(self):
        MAX_PORT = 16
        progress_dialog = QtWidgets.QProgressDialog(
            '正在偵測讀卡機連接埠中, 請稍後...', '取消', 0, MAX_PORT, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        com_port = None
        for i in range(MAX_PORT):
            progress_dialog.setValue(i)
            result = ic_card.cshis.csOpenCom(i)
            if result == 0:  # 成功
                com_port = i + 1
                break

        progress_dialog.setValue(MAX_PORT)
        if com_port is not None:
            self.ui.spinBox_ic_reader_port.setValue(com_port)
        else:
            self.ui.spinBox_ic_reader_port.setValue(0)
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Critical,
                '偵測失敗',
                '<font size="5" color="red"><b>偵測不到讀卡機, 請檢查讀卡機是否連接正確.</b></font>',
                '請確定讀卡機是否連接, 或VPN網路是否暢通.'
            )

    def _read_station_list(self):
        sql = '''
            SELECT StationNo FROM system_settings
            WHERE
                StationNo > 0
            GROUP BY StationNo
        '''
        self.table_widget_station_list.set_db_data(sql, self._set_table_widget_station_list)

    def _read_bulletin(self):
        sql = '''
            SELECT * from bulletin
            WHERE
                Title IS NOT NULL AND LENGTH(Title) > 0
            ORDER BY BulletinKey
        '''
        self.table_widget_bulletin.set_db_data(sql, self._set_table_widget_bulletin)

    def _set_table_widget_bulletin(self, row_no, row):
        title = row['Title']
        content = row['Content']
        bulletin_row = [
            title,
            content,
        ]

        for col_no in range(len(bulletin_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, bulletin_row[col_no])
            self.ui.tableWidget_bulletin.setItem(
                row_no, col_no, item,
            )

    def _read_notice(self):
        sql = '''
            SELECT * from case_extension
            WHERE
                ExtensionType = "網站注意事項"
            ORDER BY CaseExtensionKey
        '''
        self.table_widget_notice.set_db_data(sql, self._set_table_widget_notice)

    def _set_table_widget_notice(self, row_no, row):
        notice = row['Content']
        notice_row = [
            notice,
        ]

        for col_no in range(len(notice_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, notice_row[col_no])
            self.ui.tableWidget_notice.setItem(
                row_no, col_no, item,
            )

    def _set_table_widget_station_list(self, row_no, row):
        station_no = row['StationNo']
        station_position = self._get_system_settings_value(station_no, '工作站位置')
        ip_address = self._get_system_settings_value(station_no, '使用者ip')
        room = self._get_system_settings_value(station_no, '診療室')
        use_ic_reader = self._get_system_settings_value(station_no, '使用讀卡機')
        user = self._get_system_settings_value(station_no, '使用者')
        login_time = self._get_system_settings_value(station_no, '登入日期')

        station_list_row = [
            station_no,
            station_position,
            ip_address,
            room,
            use_ic_reader,
            user,
            login_time,
        ]

        for col_no in range(len(station_list_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, station_list_row[col_no])
            self.ui.tableWidget_station_list.setItem(
                row_no, col_no, item,
            )
            if col_no in [0]:
                self.ui.tableWidget_station_list.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [3, 4]:
                self.ui.tableWidget_station_list.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

        self._set_cancel_button(row_no)

    def _set_cancel_button(self, row_no):
        station_no = self.ui.tableWidget_station_list.item(row_no, 0).text()

        button = QtWidgets.QPushButton(self.ui.tableWidget_station_list)
        button.setIcon(QtGui.QIcon('./icons/cancel.svg'))
        button.setFlat(True)
        button.clicked.connect(lambda: self._remove_station_row(station_no))

        self.ui.tableWidget_station_list.setCellWidget(row_no, 7, button)

    def _remove_station_row(self, station_no):
        msg_box = dialog_utils.get_message_box(
            '刪除工作站設定', QtWidgets.QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定刪除{station_no}號工作站的全部設定?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        sql = f'''
            DELETE FROM system_settings
            WHERE
                StationNo = {station_no}
        '''
        self.database.exec_sql(sql)

        self.ui.tableWidget_station_list.removeRow(self.ui.tableWidget_station_list.currentRow())

    def _get_system_settings_value(self, station_no, field_name):
        sql = f'''
            SELECT Value FROM system_settings
            WHERE
                StationNo = {station_no} AND
                Field = "{field_name}"
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return ''

        return string_utils.xstr(rows[0]['Value'])

    def _adjust_settings(self):
        self._delete_local_settings('折扣四捨五入')

    def _delete_local_settings(self, field):
        station_no = self.system_settings.station_no
        sql = f'''
            DELETE FROM system_settings
            WHERE
                StationNo = {station_no} AND
                Field = "{field}"
        '''
        self.database.exec_sql(sql)

    def _get_exclude_room(self):
        if self.ui.tableWidget_start_no.rowCount() <= 0:
            return None

        exclude_room = []
        for row_no in range(self.ui.tableWidget_start_no.rowCount()):
            room = self.ui.tableWidget_start_no.item(row_no, 0).text()
            exclude_room.append(room)

        return exclude_room

    def _add_start_no(self):
        exclude_room = self._get_exclude_room()

        dialog = dialog_utils.get_dialog_start_no(
            self, self.database, self.system_settings, None, None, None, None, exclude_room
        )

        if dialog.exec_():
            room = dialog.ui.comboBox_room.currentText()
            start_no_1 = dialog.ui.spinBox_start_no_1.value()
            start_no_2 = dialog.ui.spinBox_start_no_2.value()
            start_no_3 = dialog.ui.spinBox_start_no_3.value()
            self._insert_start_no(room, start_no_1, start_no_2, start_no_3)

        dialog.deleteLater()
        self._start_no_changed()

    def _remove_start_no(self):
        row_no = self.ui.tableWidget_start_no.currentRow()
        self.ui.tableWidget_start_no.removeRow(row_no)

        self._start_no_changed()

    def _edit_start_no(self):
        row_no = self.ui.tableWidget_start_no.currentRow()
        room = self.ui.tableWidget_start_no.item(row_no, 0).text()
        start_no_1 = self.ui.tableWidget_start_no.item(row_no, 1).text()
        start_no_2 = self.ui.tableWidget_start_no.item(row_no, 2).text()
        start_no_3 = self.ui.tableWidget_start_no.item(row_no, 3).text()

        dialog = dialog_utils.get_dialog_start_no(
            self, self.database, self.system_settings, room, start_no_1, start_no_2, start_no_3, None,
        )

        if dialog.exec_():
            room = dialog.ui.comboBox_room.currentText()
            start_no_1 = dialog.ui.spinBox_start_no_1.value()
            start_no_2 = dialog.ui.spinBox_start_no_2.value()
            start_no_3 = dialog.ui.spinBox_start_no_3.value()
            self._modify_start_no(row_no, room, start_no_1, start_no_2, start_no_3)

        dialog.deleteLater()
        self._start_no_changed()

    def _insert_start_no(self, room, start_no_1, start_no_2, start_no_3):
        row_no = self.ui.tableWidget_start_no.rowCount()
        self.ui.tableWidget_start_no.setRowCount(row_no+1)
        start_no_row = [room, start_no_1, start_no_2, start_no_3]
        for col_no in range(len(start_no_row)):
            self.ui.tableWidget_start_no.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(string_utils.xstr(start_no_row[col_no]))
            )
            if col_no in [1, 2, 3]:
                self.ui.tableWidget_start_no.item(
                    row_no, col_no).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _modify_start_no(self, row_no, room, start_no_1, start_no_2, start_no_3):
        start_no_record = [room, start_no_1, start_no_2, start_no_3]
        for col_no in range(len(start_no_record)):
            self.ui.tableWidget_start_no.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(string_utils.xstr(start_no_record[col_no]))
            )
            if col_no in [1, 2, 3]:
                self.ui.tableWidget_start_no.item(
                    row_no, col_no).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _start_no_changed(self):
        if self.ui.tableWidget_start_no.rowCount() <= 0:
            enabled = False
        else:
            enabled = True

        self.ui.toolButton_remove_start_no.setEnabled(enabled)
        self.ui.toolButton_edit_start_no.setEnabled(enabled)

    def _add_web_bulletin(self):
        dialog = dialog_utils.get_dialog_web_bulletin(self, self.database, self.system_settings)

        if dialog.exec_():
            title = dialog.ui.lineEdit_title.text()
            content = dialog.ui.plainTextEdit_content.toPlainText()
            self._insert_web_bulletin(title, content)

        dialog.deleteLater()

    def _edit_web_bulletin(self):
        if self.ui.tableWidget_bulletin.rowCount() <= 0:
            return

        title = self.ui.tableWidget_bulletin.item(self.ui.tableWidget_bulletin.currentRow(), 0).text()
        content = self.ui.tableWidget_bulletin.item(self.ui.tableWidget_bulletin.currentRow(), 1).text()

        dialog = dialog_utils.get_dialog_web_bulletin(
            self, self.database, self.system_settings, title=title, content=content)

        if dialog.exec_():
            title = dialog.ui.lineEdit_title.text()
            content = dialog.ui.plainTextEdit_content.toPlainText()
            self._modify_web_bulletin(self.ui.tableWidget_bulletin.currentRow(), title, content)

        dialog.deleteLater()

    def _remove_web_bulletin(self):
        msg_box = dialog_utils.get_message_box(
            '刪除公告', QtWidgets.QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定刪除此筆公告內容?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        current_row = self.ui.tableWidget_bulletin.currentRow()
        self.ui.tableWidget_bulletin.removeRow(current_row)

    def _insert_web_bulletin(self, title, content):
        row_no = self.ui.tableWidget_bulletin.rowCount()
        self.ui.tableWidget_bulletin.setRowCount(row_no+1)

        bulletin_row = [title, content]
        for col_no in range(len(bulletin_row)):
            self.ui.tableWidget_bulletin.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(string_utils.xstr(bulletin_row[col_no]))
            )

    def _modify_web_bulletin(self, row_no, title, content):
        bulletin_row = [title, content]
        for col_no in range(len(bulletin_row)):
            self.ui.tableWidget_bulletin.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(string_utils.xstr(bulletin_row[col_no]))
            )

    def _add_webhook(self):
        alleypin_utils.add_webhook(self.system_settings)

    def _add_notice(self):
        dialog = QInputDialog()
        dialog.setWindowTitle("輸入網站注意事項")
        dialog.setLabelText("請輸入注意事項:")
        dialog.resize(400, 100)

        if not dialog.exec_():
            return

        row_no = self.ui.tableWidget_notice.rowCount()
        self.ui.tableWidget_notice.setRowCount(row_no+1)
        text = dialog.textValue()
        self.ui.tableWidget_notice.setItem(row_no, 0, QtWidgets.QTableWidgetItem(text))

    def _edit_notice(self):
        if self.ui.tableWidget_notice.rowCount() <= 0:
            return

        row_no = self.ui.tableWidget_notice.currentRow()
        content = self.ui.tableWidget_notice.item(row_no, 0).text()

        dialog = QInputDialog()
        dialog.setWindowTitle("輸入網站注意事項")
        dialog.setLabelText("請輸入注意事項:")
        dialog.resize(400, 100)
        dialog.setTextValue(content)

        if not dialog.exec_():
            return

        text = dialog.textValue()
        self.ui.tableWidget_notice.setItem(row_no, 0, QtWidgets.QTableWidgetItem(text))

    def _remove_notice(self):
        if self.ui.tableWidget_notice.rowCount() <= 0:
            return

        msg_box = dialog_utils.get_message_box(
            '刪除注意事項', QtWidgets.QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定刪除此筆注意事項?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        current_row = self.ui.tableWidget_notice.currentRow()
        self.ui.tableWidget_notice.removeRow(current_row)
