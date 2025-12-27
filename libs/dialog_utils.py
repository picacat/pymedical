# -*- coding: utf-8 -*-
import importlib
import os

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QPushButton

from libs import system_utils


def get_font():
    font = QFont()
    font.setPixelSize(16)

    return font


def get_dialog(title, label, text_value, input_mode, height, width):
    font = get_font()
    input_dialog = QInputDialog()
    input_dialog.setFont(font)
    input_dialog.setInputMode(input_mode)
    input_dialog.resize(height, width)
    input_dialog.setWindowTitle(title)
    input_dialog.setLabelText(label)
    input_dialog.setTextValue(text_value)
    input_dialog.setOkButtonText('確定')
    input_dialog.setCancelButtonText('取消')

    return input_dialog


def get_message_box(title, icon, text, info_text, ok_button='確定', cancel_button='取消'):
    font = get_font()
    msg_box = QMessageBox()
    msg_box.setFont(font)
    msg_box.setIcon(icon)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setInformativeText(info_text)
    msg_box.addButton(QPushButton(cancel_button), QMessageBox.NoRole)
    msg_box.addButton(QPushButton(ok_button), QMessageBox.YesRole)

    return msg_box


def message_box(title, message, hint):
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setInformativeText(hint)
    msg_box.setStandardButtons(QMessageBox.NoButton)

    return msg_box


def message_box_with_button(title, message, hint):
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setInformativeText(hint)
    msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)

    return msg_box


# 病歷登錄-過去病歷
def get_dialog_medical_record_past_history(parent, database, system_settings, case_key, patient_key, call_from):
    from dialog import dialog_medical_record_past_history

    module = importlib.reload(dialog_medical_record_past_history)
    dialog = module.DialogMedicalRecordPastHistory(
        parent, database, system_settings, case_key, patient_key, call_from
    )

    return dialog


# 病歷登錄-主訴快選詞庫
def get_dialog_diagnostic_picker(parent, database, system_settings, sender, diagnostic_type, clean_input_code):
    from dialog import dialog_diagnostic_picker

    module = importlib.reload(dialog_diagnostic_picker)
    dialog = module.DialogDiagnosticPicker(
        parent, database, system_settings, sender, diagnostic_type, clean_input_code,
    )

    return dialog


# 病歷登錄-病名詞庫
def get_dialog_disease_picker(parent, database, system_settings, icd_code):
    from dialog import dialog_disease_picker

    module = importlib.reload(dialog_disease_picker)
    dialog = module.DialogDiseasePicker(parent, database, system_settings, icd_code)

    return dialog


# 病歷登錄-診察詞庫
def get_dialog_inquiry(parent, database, system_settings, dialog_type, text_edit):
    from dialog import dialog_inquiry

    module = importlib.reload(dialog_inquiry)
    dialog = module.DialogInquiry(parent, database, system_settings, dialog_type, text_edit)

    return dialog


# 病歷登錄-診察詞庫-主訴詞庫
def get_dialog_symptom(parent, database, system_settings, groups_name, text_edit):
    from dialog import dialog_symptom

    module = importlib.reload(dialog_symptom)
    dialog = module.DialogSymptom(parent, database, system_settings, groups_name, text_edit)

    return dialog


# 病歷登錄-診察詞庫-舌診詞庫
def get_dialog_tongue(parent, database, system_settings, groups_name, text_edit):
    from dialog import dialog_tongue

    module = importlib.reload(dialog_tongue)
    dialog = module.DialogTongue(parent, database, system_settings, groups_name, text_edit)

    return dialog


# 病歷登錄-診察詞庫-舌診詞庫
def get_dialog_tongue_list(parent, database, system_settings, groups_name, text_edit):
    from dialog import dialog_tongue_list

    module = importlib.reload(dialog_tongue_list)
    dialog = module.DialogTongueList(parent, database, system_settings, groups_name, text_edit)

    return dialog


# 病歷登錄-診察詞庫-脈象表
def get_dialog_pulse_picker(parent, database, system_settings, text_edit):
    from dialog import dialog_pulse_picker

    module = importlib.reload(dialog_pulse_picker)
    dialog = module.DialogPulsePicker(parent, database, system_settings, text_edit)

    return dialog


# 病歷登錄-診察詞庫-脈象詞庫
def get_dialog_pulse(parent, database, system_settings, groups_name, text_edit):
    from dialog import dialog_pulse

    module = importlib.reload(dialog_pulse)
    dialog = module.DialogPulse(parent, database, system_settings, groups_name, text_edit)

    return dialog


# 病歷登錄-診察詞庫-備註詞庫
def get_dialog_remark(parent, database, system_settings, groups_name, text_edit):
    from dialog import dialog_remark

    module = importlib.reload(dialog_remark)
    dialog = module.DialogRemark(parent, database, system_settings, groups_name, text_edit)

    return dialog


# 病歷登錄-診察詞庫-國泰詞庫
def get_dialog_symptom_kt(parent, database, system_settings, text_edit, text_edit_tongue):
    from dialog import dialog_symptom_kt

    module = importlib.reload(dialog_symptom_kt)
    dialog = module.DialogSymptomKT(parent, database, system_settings, text_edit, text_edit_tongue)

    return dialog


# 病歷登錄-診察詞庫-辨證詞庫
def get_dialog_diagnosis(parent, database, system_settings, dialog_type, text_edit, text_edit_cure):
    from dialog import dialog_diagnosis

    module = importlib.reload(dialog_diagnosis)
    dialog = module.DialogDiagnosis(parent, database, system_settings, dialog_type, text_edit, text_edit_cure)

    return dialog


# 病歷登錄-病名詞庫
def get_dialog_disease(parent, database, system_settings, case_key, text_edit, line_edit,
                       line_special_code, lineEdit_disease_code2, lineEdit_disease_name2, disease_type):
    from dialog import dialog_disease, dialog_disease2

    if system_settings.field('病名版面') == '版面2':
        module = importlib.reload(dialog_disease2)
    else:
        module = importlib.reload(dialog_disease)

    dialog = module.DialogDisease(
        parent, database, system_settings, case_key, text_edit, line_edit,
        line_special_code, lineEdit_disease_code2, lineEdit_disease_name2, disease_type)

    return dialog

# 病歷登錄-病名詞庫
def get_dialog_external_causes(parent, database, system_settings, case_key, lineEdit_disease_code2, lineEdit_disease_name2):
    from dialog import dialog_external_causes
    module = importlib.reload(dialog_external_causes)
    
    dialog = module.DialogExternalCauses(
        parent, database, system_settings, case_key, lineEdit_disease_code2, lineEdit_disease_name2)

    return dialog


# 病歷登錄-處方詞庫
def get_dialog_medicine(parent, database, system_settings, tableWidget_prescript, medicine_set, dict_type):
    from dialog import dialog_medicine

    module = importlib.reload(dialog_medicine)
    dialog = module.DialogMedicine(
        parent, database, system_settings, tableWidget_prescript, medicine_set, dict_type)

    return dialog


# 病歷登錄-檢驗報告
def get_dialog_examination(parent, database, system_settings, tableWidget_prescript, medicine_set):
    from dialog import dialog_examination

    module = importlib.reload(dialog_examination)
    dialog = module.DialogExamination(parent, database, system_settings, tableWidget_prescript, medicine_set)

    return dialog


# 病歷登錄-參考病歷
def get_dialog_medical_record_reference(parent, database, system_settings, case_key):
    from dialog import dialog_medical_record_reference

    module = importlib.reload(dialog_medical_record_reference)
    dialog = module.DialogMedicalRecordReference(parent, database, system_settings, case_key)

    return dialog


# 病歷登錄-參考處方
def get_dialog_reference_prescript(parent, database, system_settings, icd_code):
    from dialog import dialog_reference_prescript

    module = importlib.reload(dialog_reference_prescript)
    dialog = module.DialogReferencePrescript(parent, database, system_settings, icd_code)

    return dialog


# 病歷登錄-顯示分院病歷
def get_dialog_medical_record_hosts(parent, database, system_settings, patient_id):
    from dialog import dialog_medical_record_hosts

    module = importlib.reload(dialog_medical_record_hosts)
    dialog = module.DialogMedicalRecordHosts(parent, database, system_settings, patient_id)

    return dialog


# 病歷登錄-處方集
def get_dialog_medical_record_collection(parent, database, system_settings, case_date):
    from dialog import dialog_medical_record_collection

    module = importlib.reload(dialog_medical_record_collection)
    dialog = module.DialogMedicalRecordCollection(parent, database, system_settings, case_date)

    return dialog


# 病歷登錄-經驗方
def get_dialog_medical_record_experience(parent, database, system_settings, case_date, medicine_set):
    from dialog import dialog_medical_record_experience

    module = importlib.reload(dialog_medical_record_experience)
    dialog = module.DialogMedicalRecordExperience(parent, database, system_settings, case_date, medicine_set)

    return dialog


# 病歷登錄-新增主訴詞庫
def get_dialog_add_diagnostic_dict(parent, database, system_settings, clinic_type, selected_text):
    from dialog import dialog_add_diagnostic_dict

    module = importlib.reload(dialog_add_diagnostic_dict)
    dialog = module.DialogAddDiagnosticDict(parent, database, system_settings, clinic_type, selected_text)

    return dialog


# 病歷登錄-影像病歷
def get_dialog_capture_image(parent, database, system_settings, case_key, patient_key, call_from):
    from dialog import dialog_capture_image

    module = importlib.reload(dialog_capture_image)
    dialog = module.DialogCaptureImage(parent, database, system_settings, case_key, patient_key, call_from)

    return dialog


# 病歷登錄-檢驗所報告
def get_dialog_exam_result(parent, database, system_settings, patient_key):
    from dialog import dialog_exam_result

    module = importlib.reload(dialog_exam_result)
    dialog = module.DialogExamResult(parent, database, system_settings, patient_key)

    return dialog


# 病歷登錄-診前檢查
def get_dialog_exam_precheck(parent, database, system_settings, case_key, call_from):
    from dialog import dialog_exam_precheck

    module = importlib.reload(dialog_exam_precheck)
    dialog = module.DialogExamPrecheck(parent, database, system_settings, case_key, call_from)

    return dialog


# 病歷登錄-中西藥交互作用
def get_dialog_conflict_drug(parent, database, system_settings, doctor_id, patient_id, table_widget):
    from dialog import dialog_conflict_drug
    module = importlib.reload(dialog_conflict_drug)

    dialog = module.DialogConflictDrug(parent, database, system_settings, doctor_id, patient_id, table_widget)

    return dialog


# 病歷登錄-病歷版本記錄
def get_dialog_medical_record_version_history(parent, database, system_settings, case_key):
    from dialog import dialog_medical_record_version_history

    module = importlib.reload(dialog_medical_record_version_history)
    dialog = module.DialogMedicalRecordVersionHistory(parent, database, system_settings, case_key)

    return dialog


# 病歷登錄-健保處方-鍵盤輸入處方/處置詞庫
def get_dialog_input_medicine(parent, database, system_settings, medicine_groups, medicine_set,
                              tableWidget_prescript, previous_medicine_name, keyword):
    from dialog import dialog_input_medicine

    module = importlib.reload(dialog_input_medicine)
    dialog = module.DialogInputMedicine(
        parent, database, system_settings, medicine_groups, medicine_set,
        tableWidget_prescript, previous_medicine_name, keyword,
    )

    return dialog


# 病歷登錄-健保處方-方劑詞庫
def get_dialog_compound_json(parent, database, system_settings, medicine_set, tableWidget_prescript):
    from dialog import dialog_compound_json

    module = importlib.reload(dialog_compound_json)
    dialog = module.DialogCompoundJson(
        parent, database, system_settings, medicine_set, tableWidget_prescript)

    return dialog


# 病歷登錄-健保處方-電針詞庫
def get_dialog_electric_acupuncture(parent, database, system_settings):
    from dialog import dialog_electric_acupuncture

    module = importlib.reload(dialog_electric_acupuncture)
    dialog = module.DialogElectricAcupuncture(parent, database, system_settings)

    return dialog


# 病歷登錄-健保處方-複雜針灸詞庫
def get_dialog_complicated_acupuncture(parent, database, system_settings, treatment, second_treatment,
                                       disease_code, diag_date, tableWidget_treat):
    from dialog import dialog_complicated_acupuncture

    module = importlib.reload(dialog_complicated_acupuncture)
    dialog = module.DialogComplicatedAcupuncture(
        parent, database, system_settings, treatment, second_treatment, disease_code, diag_date, tableWidget_treat
    )

    return dialog


# 病歷登錄-健保處方-複雜傷科詞庫
def get_dialog_complicated_massage(parent, database, system_settings, treatment, second_treatment,
                                   diag_date, tableWidget_treat):
    from dialog import dialog_complicated_massage

    module = importlib.reload(dialog_complicated_massage)
    dialog = module.DialogComplicatedMassage(
        parent, database, system_settings, treatment, second_treatment, diag_date, tableWidget_treat
    )

    return dialog


# 病歷登錄-健保處方-藥品說明/顯示成本
def get_dialog_rich_text(parent, database, system_settings, text_format, medicine_key, description):
    from dialog import dialog_rich_text

    module = importlib.reload(dialog_rich_text)
    dialog = module.DialogRichText(
        parent, database, system_settings, text_format, medicine_key, description
    )

    return dialog


# 病歷登錄-健保處方-開啟藥品圖書館
def get_dialog_medicine_library(parent, database, system_settings, medicine_name, medicine_type):
    from dialog import dialog_medicine_library

    module = importlib.reload(dialog_medicine_library)
    dialog = module.DialogMedicineLibrary(
        parent, database, system_settings, medicine_name, medicine_type
    )

    return dialog



# 病歷登錄-顯示病患備忘錄
def get_dialog_patient_memo(parent, database, system_settings, patient_key):
    from dialog import dialog_patient_memo

    module = importlib.reload(dialog_patient_memo)
    dialog = module.DialogPatientMemo(
        parent, database, system_settings, patient_key
    )

    return dialog


# 病歷登錄-健保處方-針灸穴位圖
def get_dialog_acupuncture_point(parent, database, system_settings):
    from dialog import dialog_acupuncture_point

    module = importlib.reload(dialog_acupuncture_point)
    dialog = module.DialogAcupuncturePoint(parent, database, system_settings)

    return dialog


# 病歷登錄-健保處方-治療時間
def get_dialog_treat_time(parent, database, system_settings, diag_date, treatment, second_treatment):
    from dialog import dialog_treat_time

    module = importlib.reload(dialog_treat_time)
    dialog = module.DialogTreatTime(parent, database, system_settings, diag_date, treatment, second_treatment)

    return dialog


# 病歷登錄-健保處方-治療部位
def get_dialog_treat_position(parent, database, system_settings, treatment, tableWidget_treat):
    from dialog import dialog_treat_position

    module = importlib.reload(dialog_treat_position)
    dialog = module.DialogTreatPosition(parent, database, system_settings, treatment, tableWidget_treat)

    return dialog


# 病歷登錄-健保處方-輔助治療
def get_dialog_treat_auxiliary(parent, database, system_settings, treatment, tableWidget_treat):
    from dialog import dialog_treat_auxiliary

    module = importlib.reload(dialog_treat_auxiliary)
    dialog = module.DialogTreatAuxiliary(parent, database, system_settings, treatment, tableWidget_treat)

    return dialog


# 病歷登錄-自費處方-專案詞庫
def get_dialog_project(parent, database, system_settings, tableWidget_prescript, medicine_set):
    from dialog import dialog_project

    module = importlib.reload(dialog_project)
    dialog = module.DialogProject(parent, database, system_settings, tableWidget_prescript, medicine_set)

    return dialog


# 列印選擇健保或自費
def get_dialog_select_medicine_set(parent, database, system_settings, case_key, form_type):
    from dialog import dialog_select_medicine_set

    module = importlib.reload(dialog_select_medicine_set)
    dialog = module.DialogSelectMedicineSet(parent, database, system_settings, case_key, form_type)

    return dialog


# 病歷查詢-查詢視窗
def get_dialog_medical_record_list(parent, database, system_settings):
    from dialog import dialog_medical_record_list

    module = importlib.reload(dialog_medical_record_list)
    dialog = module.DialogMedicalRecordList(parent, database, system_settings)

    return dialog


# 病歷查詢-設定批價班別視窗
def get_dialog_medical_record_done(parent, database, system_settings, case_key, property_name):
    from dialog import dialog_medical_record_done

    module = importlib.reload(dialog_medical_record_done)
    dialog = module.DialogMedicalRecordDone(parent, database, system_settings, case_key, property_name)

    return dialog


# 診斷證明開立視窗
def get_dialog_certificate_diagnosis(parent, database, system_settings, certificate_key):
    from dialog import dialog_certificate_diagnosis

    module = importlib.reload(dialog_certificate_diagnosis)
    dialog = module.DialogCertificateDiagnosis(
        parent, database, system_settings, certificate_key
    )

    return dialog


# 診斷證明-查詢資料
def get_dialog_certificate_query(parent, database, system_settings, call_from):
    from dialog import dialog_certificate_query

    module = importlib.reload(dialog_certificate_query)
    dialog = module.DialogCertificateQuery(parent, database, system_settings, call_from)

    return dialog


# 醫療費用證明書-開立證明
def get_dialog_certificate_payment(parent, database, system_settings, auto_create_list):
    from dialog import dialog_certificate_payment

    module = importlib.reload(dialog_certificate_payment)
    dialog = module.DialogCertificatePayment(parent, database, system_settings, auto_create_list)

    return dialog


# 醫療費用證明書-批價檢查明細
def get_dialog_certificate_items(parent, database, system_settings, tableWidget_certificate_items, correct_list):
    from dialog import dialog_certificate_items

    module = importlib.reload(dialog_certificate_items)
    dialog = module.DialogCertificateItems(
        parent, database, system_settings, tableWidget_certificate_items, correct_list,
    )

    return dialog


# 醫療費用證明書-新增病歷
def get_dialog_medical_record_picker(parent, database, system_settings, case_date, patient_key):
    from dialog import dialog_medical_record_picker

    module = importlib.reload(dialog_medical_record_picker)
    dialog = module.DialogMedicalRecordPicker(
        parent, database, system_settings, case_date, patient_key,
    )

    return dialog


# 選擇病患視窗: 診斷證明, 醫療費用證明書 ...
def get_dialog_select_patient(parent, database, system_settings, table_name, primary_key_field, keyword):
    from dialog import dialog_select_patient

    module = importlib.reload(dialog_select_patient)
    dialog = module.DialogSelectPatient(
        parent, database, system_settings, table_name, primary_key_field, keyword
    )

    return dialog


# 掛號顯示選擇病患視窗
def get_dialog_patient(parent, database, system_settings, rows):
    from dialog import dialog_patient

    module = importlib.reload(dialog_patient)
    dialog = module.DialogPatient(parent, database, system_settings, rows)

    return dialog


# 病歷登錄-顯示劑量視窗
def get_dialog_dosage(parent, database, system_settings, table_widget_prescript, ins_type):
    from dialog import dialog_dosage

    module = importlib.reload(dialog_dosage)
    dialog = module.DialogDosage(
        parent, database, system_settings, table_widget_prescript, ins_type
    )

    return dialog


# 病歷登錄-顯示單位視窗
def get_dialog_unit(parent, database, system_settings, table_widget_prescript, ins_type):
    from dialog import dialog_unit

    module = importlib.reload(dialog_unit)
    dialog = module.DialogUnit(
        parent, database, system_settings, table_widget_prescript, ins_type
    )

    return dialog


# 病歷登錄-顯示劑量視窗
def get_dialog_youtube(parent, database, system_settings):
    from dialog import dialog_youtube

    module = importlib.reload(dialog_youtube)
    dialog = module.DialogYouTube(parent, database, system_settings)

    return dialog


# 病歷登錄-顯示服法視窗
def get_dialog_prescript_instruction(parent, database, system_settings, table_widget_prescript, ins_type):
    from dialog import dialog_prescript_instruction

    module = importlib.reload(dialog_prescript_instruction)
    dialog = module.DialogPrescriptInstruction(
        parent, database, system_settings, table_widget_prescript, ins_type
    )

    return dialog


# 病歷登錄-整合醫療照護
def get_dialog_integrate_care(parent, database, system_settings, case_key):
    from dialog import dialog_integrate_care

    module = importlib.reload(dialog_integrate_care)
    dialog = module.DialogIntegrateCare(parent, database, system_settings, case_key)

    return dialog


# 取得日期
def get_dialog_calendar(parent, database, system_settings, call_from):
    from dialog import dialog_calendar

    module = importlib.reload(dialog_calendar)
    dialog = module.DialogCalendar(parent, database, system_settings, call_from)

    return dialog


# 取得日期時間
def get_dialog_schedule(parent, database, system_settings, time_list):
    from dialog import dialog_schedule

    module = importlib.reload(dialog_schedule)
    dialog = module.DialogSchedule(parent, database, system_settings, time_list)

    return dialog


# 取得診號起始號
def get_dialog_start_no(parent, database, system_settings, doctor,
                        start_no1, start_no2, start_no3, exclude_doctor):
    from dialog import dialog_start_no

    module = importlib.reload(dialog_start_no)
    dialog = module.DialogStartNo(
        parent, database, system_settings, doctor, start_no1, start_no2, start_no3, exclude_doctor)

    return dialog


# 取得診號起始號
def get_dialog_web_bulletin(parent, database, system_settings, title=None, content=None):
    from dialog import dialog_web_bulletin

    module = importlib.reload(dialog_web_bulletin)
    dialog = module.DialogWebBulletin(parent, database, system_settings, title, content)

    return dialog


# 收費設定 輸入健保支付標準
def get_dialog_input_nhi(parent, database, system_settings, charge_settings_key):
    from dialog import dialog_input_nhi

    module = importlib.reload(dialog_input_nhi)
    dialog = module.DialogInputNHI(parent, database, system_settings, charge_settings_key)

    return dialog


# 收費設定 輸入掛號費
def get_dialog_input_regist(parent, database, system_settings, charge_settings_key):
    from dialog import dialog_input_regist

    module = importlib.reload(dialog_input_regist)
    dialog = module.DialogInputRegist(parent, database, system_settings, charge_settings_key)

    return dialog


# 收費設定 輸入掛號費優待
def get_dialog_input_discount(parent, database, system_settings, charge_settings_key):
    from dialog import dialog_input_discount

    module = importlib.reload(dialog_input_discount)
    dialog = module.DialogInputDiscount(parent, database, system_settings, charge_settings_key)

    return dialog


# 收費設定 輸入水藥費
def get_dialog_herb_fee_setting(parent, database, system_settings, charge_settings_key):
    from dialog import dialog_herb_fee_setting

    module = importlib.reload(dialog_herb_fee_setting)
    dialog = module.DialogHerbFeeSetting(parent, database, system_settings, charge_settings_key)

    return dialog


# 收費設定 輸入部份負擔
def get_dialog_input_share(parent, database, system_settings, charge_settings_key, charge_type):
    from dialog import dialog_input_share

    module = importlib.reload(dialog_input_share)
    dialog = module.DialogInputShare(parent, database, system_settings, charge_settings_key, charge_type)

    return dialog


# 欠還款作業-新增欠款
def get_dialog_add_debt(parent, database, system_settings):
    from dialog import dialog_add_debt

    module = importlib.reload(dialog_add_debt)
    dialog = module.DialogAddDebt(parent, database, system_settings)

    return dialog


# 欠還款作業-現金還款
def get_dialog_debt(parent, database, system_settings, debt_key, case_key):
    from dialog import dialog_debt

    module = importlib.reload(dialog_debt)
    dialog = module.DialogDebt(parent, database, system_settings, debt_key, case_key)

    return dialog


# 盤點-新增盤點
def get_dialog_add_inventory(parent, database, system_settings, inventory_key):
    from dialog import dialog_add_inventory

    module = importlib.reload(dialog_add_inventory)
    dialog = module.DialogAddInventory(parent, database, system_settings, inventory_key)

    return dialog


# 廠商資料-輸入資料
def get_dialog_input_supplier(parent, database, system_settings, supplier_key):
    from dialog import dialog_input_supplier

    module = importlib.reload(dialog_input_supplier)
    dialog = module.DialogInputSupplier(parent, database, system_settings, supplier_key)

    return dialog


# 處方詞庫-成方輸入藥品資料
def get_dialog_input_drug(parent, database, system_settings, medicine_type, medicine_key):
    from dialog import dialog_input_drug

    module = importlib.reload(dialog_input_drug)
    dialog = module.DialogInputDrug(parent, database, system_settings, medicine_type, medicine_key)

    return dialog


# 診察詞庫-新增診察詞庫
def get_dialog_input_diagnostic(parent, database, system_settings, diagnostic_key):
    from dialog import dialog_input_diagnostic

    module = importlib.reload(dialog_input_diagnostic)
    dialog = module.DialogInputDiagnostic(parent, database, system_settings, diagnostic_key)

    return dialog


# 病名詞庫-新增病名詞庫
def get_dialog_input_disease(parent, database, system_settings, groups_name, call_from):
    from dialog import dialog_input_disease

    module = importlib.reload(dialog_input_disease)
    dialog = module.DialogInputDisease(parent, database, system_settings, groups_name, call_from)

    return dialog


# 病名詞庫-編輯病名詞庫
def get_dialog_edit_disease(parent, database, system_settings, disease_key):
    from dialog import dialog_edit_disease

    module = importlib.reload(dialog_edit_disease)
    dialog = module.DialogEditDisease(parent, database, system_settings, disease_key)

    return dialog


# 護理師班表-輸入班表
def get_dialog_nurse_schedule(parent, database, system_settings, schedule_type, schedule_date,
                              person, period1, period2, period3):

    from dialog import dialog_nurse_schedule

    module = importlib.reload(dialog_nurse_schedule)
    dialog = module.DialogNurseSchedule(
        parent, database, system_settings, schedule_type, schedule_date, person, period1, period2, period3)

    return dialog


# 藥師班表-輸入班表
def get_dialog_pharmacist_schedule(parent, database, system_settings, schedule_date, period1, period2, period3):
    from dialog import dialog_pharmacist_schedule

    module = importlib.reload(dialog_pharmacist_schedule)
    dialog = module.DialogPharmacistSchedule(
        parent, database, system_settings, schedule_date, period1, period2, period3)

    return dialog


# 選擇年月
def get_dialog_date_picker(parent, database, system_settings, call_from):
    from dialog import dialog_date_picker

    module = importlib.reload(dialog_date_picker)
    dialog = module.DialogDatePicker(parent, database, system_settings, call_from)

    return dialog


# 醫師班表-依診別輸入班表
def get_dialog_doctor_schedule(parent, database, system_settings, schedule_key):
    from dialog import dialog_doctor_schedule

    module = importlib.reload(dialog_doctor_schedule)
    dialog = module.DialogDoctorSchedule(parent, database, system_settings, schedule_key)

    return dialog


# 醫師班表-依班別輸入班表
def get_dialog_doctor_schedule_period(parent, database, system_settings, weekday, period):
    from dialog import dialog_doctor_schedule_period

    module = importlib.reload(dialog_doctor_schedule_period)
    dialog = module.DialogDoctorSchedulePeriod(parent, database, system_settings, weekday, period)

    return dialog


# 醫師班表-新增臨時班表
def get_dialog_temporary_schedule(parent, database, system_settings, temporary_schedule_key=None):
    from dialog import dialog_temporary_schedule

    module = importlib.reload(dialog_temporary_schedule)
    dialog = module.DialogTemporarySchedule(parent, database, system_settings, temporary_schedule_key)

    return dialog


#  檢驗報告查詢
def get_dialog_examination_list(parent, database, system_settings):
    from dialog import dialog_examination_list

    module = importlib.reload(dialog_examination_list)
    dialog = module.DialogExaminationList(parent, database, system_settings)

    return dialog


#  檢驗報告查詢
def get_dialog_ic_record_upload(parent, database, system_settings, call_from):
    from dialog import dialog_ic_record_upload

    module = importlib.reload(dialog_ic_record_upload)
    dialog = module.DialogICRecordUpload(parent, database, system_settings, call_from)

    return dialog


# 醫事人員統計查詢
def get_dialog_statistics_therapist(parent, database, system_settings, call_from, doctor_type):
    from dialog import dialog_statistics_therapist

    module = importlib.reload(dialog_statistics_therapist)
    dialog = module.DialogStatisticsTherapist(parent, database, system_settings, call_from, doctor_type)

    return dialog


# 系統設定
def get_dialog_system_settings(parent, database, system_settings):
    from dialog import dialog_system_settings

    module = importlib.reload(dialog_system_settings)
    dialog = module.DialogSystemSettings(parent, database, system_settings)

    return dialog


# 功能表醒目設定
def get_dialog_menu_setting(parent, database, system_settings):
    from dialog import dialog_menu_setting

    module = importlib.reload(dialog_menu_setting)
    dialog = module.DialogMenuSetting(parent, database, system_settings)

    return dialog


# 教學影片
def get_dialog_tutorial_videos(parent, database, system_settings):
    from dialog import dialog_tutorial_videos

    module = importlib.reload(dialog_tutorial_videos)
    dialog = module.DialogTutorialVideos(parent, database, system_settings)

    return dialog


# 分院資料設定
def get_dialog_hosts(parent, database, system_settings):
    from dialog import dialog_hosts

    module = importlib.reload(dialog_hosts)
    dialog = module.DialogHosts(parent, database, system_settings)

    return dialog


# 匯入病歷資料
def get_dialog_import_medical_record(parent, database, system_settings):
    from dialog import dialog_import_medical_record

    module = importlib.reload(dialog_import_medical_record)
    dialog = module.DialogImportMedicalRecord(parent, database, system_settings)

    return dialog


# 匯入居家藍芽病歷資料
def get_dialog_import_home_care(parent, database, system_settings):
    from dialog import dialog_import_home_care

    module = importlib.reload(dialog_import_home_care)
    dialog = module.DialogImportHomeCare(parent, database, system_settings)

    return dialog


# 健保卡讀卡機
def get_dialog_ic_card(parent, database, system_settings):
    from dialog import dialog_ic_card

    module = importlib.reload(dialog_ic_card)
    dialog = module.DialogICCard(parent, database, system_settings)

    return dialog


# 健保卡就醫資料
def get_dialog_ic_card_record(parent, database, system_settings, ic_card):
    from dialog import dialog_ic_card_record

    module = importlib.reload(dialog_ic_card_record)
    dialog = module.DialogICCardRecord(parent, database, system_settings, ic_card)

    return dialog


# 匯出電子病歷
def get_dialog_export_emr_xml(parent, database, system_settings):
    from dialog import dialog_export_emr_xml

    module = importlib.reload(dialog_export_emr_xml)
    dialog = module.DialogExportEMRXml(parent, database, system_settings)

    return dialog


# 匯出病歷JSON
def get_dialog_export_medical_record_json(parent, database, system_settings):
    from dialog import dialog_export_medical_record_json

    module = importlib.reload(dialog_export_medical_record_json)
    dialog = module.DialogExportMedicalRecordJSON(parent, database, system_settings)

    return dialog


# 資料庫修復
def get_dialog_database_repair(parent, database, system_settings):
    from dialog import dialog_database_repair

    module = importlib.reload(dialog_database_repair)
    dialog = module.DialogDatabaseRepair(parent, database, system_settings)

    return dialog


# 候診系統設定
def get_dialog_bulletin_settings(parent, database, system_settings):
    from dialog import dialog_bulletin_settings

    module = importlib.reload(dialog_bulletin_settings)
    dialog = module.DialogBulletinSettings(parent, database, system_settings)

    return dialog


# 掛號機零錢箱設定
def get_dialog_cashier_machine_settings(parent, database, system_settings):
    from dialog import dialog_cashier_machine_settings

    module = importlib.reload(dialog_cashier_machine_settings)
    dialog = module.DialogCashierMachineSettings(parent, database, system_settings)

    return dialog


# 預約登錄
def get_dialog_reservation_booking(parent, database, system_settings, reservation_date, period,
                                   doctor, reserve_no, patient_key):
    from dialog import dialog_reservation_booking

    module = importlib.reload(dialog_reservation_booking)
    dialog = module.DialogReservationBooking(
        parent, database, system_settings, reservation_date, period, doctor, reserve_no, patient_key)

    return dialog


# 物理治療預約登錄
def get_dialog_physiotherapy_booking(parent, database, system_settings, physiotherapy_date, physiotherapy_time,
                                     physiotherapy):
    from dialog import dialog_physiotherapy_booking

    module = importlib.reload(dialog_physiotherapy_booking)
    dialog = module.DialogPhysiotherapyBooking(
        parent, database, system_settings, physiotherapy_date, physiotherapy_time, physiotherapy)

    return dialog


# 更改預約
def get_dialog_reservation_modify(parent, database, system_settings, reserve_key):
    from dialog import dialog_reservation_modify

    module = importlib.reload(dialog_reservation_modify)
    dialog = module.DialogReservationModify(
        parent, database, system_settings, reserve_key)

    return dialog


# 預約查詢
def get_dialog_reservation_query(parent, database, system_settings):
    from dialog import dialog_reservation_query

    module = importlib.reload(dialog_reservation_query)
    dialog = module.DialogReservationQuery(
        parent, database, system_settings)

    return dialog


# 暫停預約設定
def get_dialog_off_day_setting(parent, database, system_settings, table_name):
    from dialog import dialog_off_day_setting

    module = importlib.reload(dialog_off_day_setting)
    dialog = module.DialogOffDaySetting(parent, database, system_settings, table_name)

    return dialog


# 預約權限設定
def get_dialog_permission_list_setting(parent, database, system_settings):
    from dialog import dialog_permission_list_setting

    module = importlib.reload(dialog_permission_list_setting)
    dialog = module.DialogPermissionListSetting(parent, database, system_settings)

    return dialog


# 自動設定預約一覽表
def get_dialog_auto_reservation_table(parent, database, system_settings, period):
    from dialog import dialog_auto_reservation_table

    module = importlib.reload(dialog_auto_reservation_table)
    dialog = module.DialogAutoReservationTable(parent, database, system_settings, period)

    return dialog


# 取得日期區間
def get_dialog_date_duration(parent, database, system_settings):
    from dialog import dialog_date_duration

    module = importlib.reload(dialog_date_duration)
    dialog = module.DialogDateDuration(parent, database, system_settings)

    return dialog

# 取得日期區間
def get_dialog_date_period(parent, database, system_settings):
    from dialog import dialog_date_period

    module = importlib.reload(dialog_date_period)
    dialog = module.DialogDatePeriod(parent, database, system_settings)

    return dialog


# 掛號櫃台結帳查詢
def get_dialog_income(parent, database, system_settings, call_from):
    from dialog import dialog_income

    module = importlib.reload(dialog_income)
    dialog = module.DialogIncome(parent, database, system_settings, call_from)

    return dialog


# 掛號過去病歷視窗
def get_dialog_past_history(parent, database, system_settings):
    from dialog import dialog_past_history

    module = importlib.reload(dialog_past_history)
    dialog = module.DialogPastHistory(parent, database, system_settings)

    return dialog


# 健保申報-顯示療程病歷
def get_dialog_course_list(parent, database, system_settings, case_key_list):
    from dialog import dialog_course_list

    module = importlib.reload(dialog_course_list)
    dialog = module.DialogCourseList(parent, database, system_settings, case_key_list)

    return dialog


# 健保申報-修改申報資料
def get_dialog_ins_list_edit(parent, database, system_settings, ins_apply_key, sequence, case_date, end_date):
    from dialog import dialog_ins_list_edit

    module = importlib.reload(dialog_ins_list_edit)
    dialog = module.DialogInsListEdit(
        parent, database, system_settings, ins_apply_key, sequence, case_date, end_date)

    return dialog


# 健保申報-設定日期
def get_dialog_ins_apply(parent, database, system_settings):
    from dialog import dialog_ins_apply

    module = importlib.reload(dialog_ins_apply)
    dialog = module.DialogInsApply(parent, database, system_settings)

    return dialog


# 輸入健保申復資料
def get_dialog_ins_appeal(parent, database, system_settings,
                          apply_date, apply_period, apply_type_code, ins_appeal_key):
    from dialog import dialog_ins_appeal

    module = importlib.reload(dialog_ins_appeal)
    dialog = module.DialogInsAppeal(
        parent, database, system_settings, apply_date, apply_period, apply_type_code, ins_appeal_key)

    return dialog


# 輸入健保申復醫令資料
def get_dialog_ins_appeal_items(parent, database, system_settings, apply_date,
                                ins_appeal_items_key, ins_appeal_key):
    from dialog import dialog_ins_appeal_items

    module = importlib.reload(dialog_ins_appeal_items)
    dialog = module.DialogInsAppealItems(
        parent, database, system_settings, apply_date, ins_appeal_items_key, ins_appeal_key)

    return dialog


# 病歷登錄-加強照護-選取加強照護支付標準
def get_dialog_ins_care(parent, database, system_settings, treat_type):
    from dialog import dialog_ins_care

    module = importlib.reload(dialog_ins_care)
    dialog = module.DialogInsCare(parent, database, system_settings, treat_type)

    return dialog


# 申報檢查-設定日期
def get_dialog_ins_check(parent, database, system_settings):
    from dialog import dialog_ins_check

    module = importlib.reload(dialog_ins_check)
    dialog = module.DialogInsCheck(parent, database, system_settings)

    return dialog


# 申報抽沈-設定日期
def get_dialog_ins_judge(parent, database, system_settings):
    from dialog import dialog_ins_judge

    module = importlib.reload(dialog_ins_judge)
    dialog = module.DialogInsJudge(parent, database, system_settings)

    return dialog


# 養生管-新增預約
def get_dialog_massage_reservation(parent, database, system_settings, massager,
                                   reservation_date, period, start_time, end_time, massage_case_key):
    from dialog import dialog_massage_reservation

    module = importlib.reload(dialog_massage_reservation)
    dialog = module.DialogMassageReservation(
        parent, database, system_settings, massager,
        reservation_date, period, start_time, end_time, massage_case_key)

    return dialog


# 醫囑詞庫
def get_dialog_simple_dict(parent, database, system_settings):
    from dialog import dialog_simple_dict

    module = importlib.reload(dialog_simple_dict)
    dialog = module.DialogSimpleDict(parent, database, system_settings)

    return dialog


# 地址詞庫
def get_dialog_address(parent, database, system_settings, line_edit):
    from dialog import dialog_address

    module = importlib.reload(dialog_address)
    dialog = module.DialogAddress(parent, database, system_settings, line_edit)

    return dialog


# 拷貝分院病患資料
def get_dialog_select_remote_patient(parent, database, system_settings):
    from dialog import dialog_select_remote_patient

    module = importlib.reload(dialog_select_remote_patient)
    dialog = module.DialogSelectRemotePatient(parent, database, system_settings)

    return dialog


# 病患查詢選擇
def get_dialog_patient_list(parent, database, system_settings):
    from dialog import dialog_patient_list

    module = importlib.reload(dialog_patient_list)
    dialog = module.DialogPatientList(parent, database, system_settings)

    return dialog


# 病患查詢選擇
def get_dialog_purge_temp_patient(parent, database, system_settings):
    from dialog import dialog_purge_temp_patient

    module = importlib.reload(dialog_purge_temp_patient)
    dialog = module.DialogPurgeTempPatient(parent, database, system_settings)

    return dialog


# 匯出病患查詢的病歷
def get_dialog_patient_medical_record(parent, database, system_settings, tableWidget):
    from dialog import dialog_patient_medical_record

    module = importlib.reload(dialog_patient_medical_record)
    dialog = module.DialogPatientMedicalRecord(parent, database, system_settings, tableWidget)

    return dialog


# 統計日期及醫師
def get_dialog_ins_date_doctor(parent, database, system_settings, call_from):
    from dialog import dialog_ins_date_doctor

    module = importlib.reload(dialog_ins_date_doctor)
    dialog = module.DialogInsDateDoctor(parent, database, system_settings, call_from)

    return dialog


# 櫃台購藥查詢
def get_dialog_purchase_list(parent, database, system_settings):
    from dialog import dialog_purchase_list

    module = importlib.reload(dialog_purchase_list)
    dialog = module.DialogPurchaseList(parent, database, system_settings)

    return dialog


# 銷售記錄查詢
def get_dialog_purchase_query(parent, database, system_settings):
    from dialog import dialog_purchase_query

    module = importlib.reload(dialog_purchase_query)
    dialog = module.DialogPurchaseQuery(parent, database, system_settings)

    return dialog


# 分院連線設定-新增資料
def get_dialog_input_host(parent, database, system_settings, hosts_key):
    from dialog import dialog_input_host

    module = importlib.reload(dialog_input_host)
    dialog = module.DialogInputHost(parent, database, system_settings, hosts_key)

    return dialog


# 病歷回復-查看JSON內容
def get_dialog_view_medical_record_json(parent, database, system_settings, backup_records_key):
    from dialog import dialog_view_medical_record_json

    module = importlib.reload(dialog_view_medical_record_json)
    dialog = module.DialogViewMedicalRecordJSON(parent, database, system_settings, backup_records_key)

    return dialog


# 回診統計
def get_dialog_statistics_return_rate(parent, database, system_settings, call_from):
    from dialog import dialog_statistics_return_rate

    module = importlib.reload(dialog_statistics_return_rate)
    dialog = module.DialogStatisticsReturnRate(parent, database, system_settings, call_from)

    return dialog


# 未回診統計
def get_dialog_statistics_no_return_rate(parent, database, system_settings, call_from):
    from dialog import dialog_statistics_no_return_rate

    module = importlib.reload(dialog_statistics_no_return_rate)
    dialog = module.DialogStatisticsNoReturnRate(parent, database, system_settings, call_from)

    return dialog


# 換貨資料-療程商品消費記錄
def get_dialog_purchase_course_list(parent, database, system_settings, case_key, medicine_key, invoice_no):
    from dialog import dialog_purchase_course_list

    module = importlib.reload(dialog_purchase_course_list)
    dialog = module.DialogPurchaseCourseList(
        parent, database, system_settings, case_key, medicine_key, invoice_no)

    return dialog


# 新增使用者
def get_dialog_input_user(parent, database, system_settings, person_key):
    from dialog import dialog_input_user

    module = importlib.reload(dialog_input_user)
    dialog = module.DialogInputUser(parent, database, system_settings, person_key)

    return dialog


# 設定使用者權限
def get_dialog_permission(parent, database, system_settings, person_key):
    from dialog import dialog_permission

    module = importlib.reload(dialog_permission)
    dialog = module.DialogPermission(parent, database, system_settings, person_key)

    return dialog


# 新增藥品抽成
def get_dialog_commission(parent, database, system_settings, person_list):
    from dialog import dialog_commission

    module = importlib.reload(dialog_commission)
    dialog = module.DialogCommission(parent, database, system_settings, person_list)

    return dialog


# 辨證詞庫
def get_dialog_distinguish(parent, database, system_settings, groups_name, text_edit, text_edit_cure):
    from dialog import dialog_distinguish

    module = importlib.reload(dialog_distinguish)
    dialog = module.DialogDistinguish(parent, database, system_settings, groups_name, text_edit, text_edit_cure)

    return dialog


# 治則詞庫
def get_dialog_cure(parent, database, system_settings, groups_name, text_edit):
    from dialog import dialog_cure

    module = importlib.reload(dialog_cure)
    dialog = module.DialogCure(parent, database, system_settings, groups_name, text_edit)

    return dialog


# 還卡
def get_dialog_return_card(parent, database, system_settings, deposit_key, case_key, patient_key):
    from dialog import dialog_return_card

    module = importlib.reload(dialog_return_card)
    dialog = module.DialogReturnCard(parent, database, system_settings, deposit_key, case_key, patient_key)

    return dialog


# 新增欠卡
def get_dialog_add_deposit(parent, database, system_settings):
    from dialog import dialog_add_deposit

    module = importlib.reload(dialog_add_deposit)
    dialog = module.DialogAddDeposit(parent, database, system_settings)

    return dialog


# 退貨
def get_dialog_return_goods(parent, database, system_settings, case_key, medicine_key, medicine_name, invoice_no):
    from dialog import dialog_return_goods

    module = importlib.reload(dialog_return_goods)
    dialog = module.DialogReturnGoods(
        parent, database, system_settings, case_key, medicine_key, medicine_name, invoice_no)

    return dialog


# 換貨
def get_dialog_exchange_goods(
        parent, database, system_settings, case_key, medicine_key, medicine_set,
        medicine_name, quantity, invoice_no, receipt_fee):
    from dialog import dialog_exchange_goods

    module = importlib.reload(dialog_exchange_goods)
    dialog = module.DialogExchangeGoods(
        parent, database, system_settings, case_key, medicine_key, medicine_set,
        medicine_name, quantity, invoice_no, receipt_fee)

    return dialog


# 銷售人員設定
def get_dialog_set_person(parent, database, system_settings, case_key, prescript_key, set_type):
    from dialog import dialog_set_person

    module = importlib.reload(dialog_set_person)
    dialog = module.DialogSetPerson(
        parent, database, system_settings, case_key, prescript_key, set_type)

    return dialog


# 預約掛號-醫師整月班表
def get_dialog_doctor_month_schedule(parent, database, system_settings, doctor, year, month):
    from dialog import dialog_doctor_month_schedule

    module = importlib.reload(dialog_doctor_month_schedule)
    dialog = module.DialogDoctorMonthSchedule(parent, database, system_settings, doctor, year, month)

    return dialog


# 服用方式-醫師看診作業-自費頁 2023-10-10 神農中醫
def get_dialog_instruction(parent, database, system_settings):
    from dialog import dialog_instruction

    module = importlib.reload(dialog_instruction)
    dialog = module.DialogInstruction(parent, database, system_settings)

    return dialog


# 診斷證明開立視窗
def get_dialog_add_return_goods(parent, database, system_settings, return_goods_key):
    from dialog import dialog_add_return_goods

    module = importlib.reload(dialog_add_return_goods)
    dialog = module.DialogAddReturnGoods(
        parent, database, system_settings, return_goods_key
    )

    return dialog


# 配藥視窗
def get_dialog_pharmacy_dosage(
        parent, database, system_settings, prescript_key, medicine_key, medicine_code, medicine_set, scale_time):
    from dialog import dialog_pharmacy_dosage

    module = importlib.reload(dialog_pharmacy_dosage)
    dialog = module.DialogPharmacyDosage(
        parent, database, system_settings, prescript_key, medicine_key, medicine_code, medicine_set, scale_time)

    return dialog


# 配藥視窗
def get_dialog_medicine_settings(parent, database, system_settings):
    from dialog import dialog_medicine_settings

    module = importlib.reload(dialog_medicine_settings)
    dialog = module.DialogMedicineSettings(parent, database, system_settings)

    return dialog


# 配藥視窗
def get_dialog_medicine_code(parent, database, system_settings, medicine_key):
    from dialog import dialog_medicine_code

    module = importlib.reload(dialog_medicine_code)
    dialog = module.DialogMedicineCode(parent, database, system_settings, medicine_key)

    return dialog


# 病歷登錄-健保處方-方劑詞庫
def get_dialog_insert_compound(parent, database, system_settings, tableWidget_prescript):
    from dialog import dialog_insert_compound

    module = importlib.reload(dialog_insert_compound)
    dialog = module.DialogInsertCompound(
        parent, database, system_settings, tableWidget_prescript)

    return dialog


def get_save_dialog_filename(parent, last_directory, default_filename):
    last_dir = system_utils.get_last_directory(last_directory)
    filename = os.path.join(last_dir, default_filename)

    options = QFileDialog.Options()
    filename, _ = QFileDialog.getSaveFileName(
        parent, last_directory,
        filename,
        "word檔案 (*.docx)", options=options
    )
    if not filename:
        return None

    system_utils.set_last_directory(last_directory, filename)
    
    return filename


# 無效的健保碼檢查 2925-09-24 港香蘭無效16品項
def get_dialog_invalid_ins_drug(parent, database, system_settings):
    from dialog import dialog_invalid_ins_drug

    module = importlib.reload(dialog_invalid_ins_drug)
    dialog = module.DialogInvalidInsDrug(
        parent, database, system_settings)

    return dialog
