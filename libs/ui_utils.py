import os

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import QByteArray, QPoint, QSettings, QSize, Qt, QTimer
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import nhi_utils, string_utils

ICON_NO = QtGui.QIcon('./icons/gtk-no.svg')
ICON_OK = QtGui.QIcon('./icons/gtk-ok.svg')
ICON_STAR = QtGui.QIcon('./icons/gnome-app-install-star.svg')
ICON_EYE = QtGui.QIcon('./icons/eye.svg')
ICON_CHECK_LIST = QtGui.QIcon('./icons/check_list.svg')
ICON_ADD = QtGui.QIcon('./icons/gtk-add.svg')
ICON_REMOVE = QtGui.QIcon('./icons/gtk-remove.svg')
ICON_CLEAR = QtGui.QIcon('./icons/gtk-clear.svg')
ICON_HELP = QtGui.QIcon('./icons/help-contents.svg')
ICON_INFO = QtGui.QIcon('./icons/gtk-info.svg')
ICON_COPY = QtGui.QIcon('./icons/gtk-copy.svg')
ICON_FINISH = QtGui.QIcon('./icons/finish.svg')
ICON_REDO = QtGui.QIcon('./icons/redo.svg')
ICON_DICT = QtGui.QIcon('./icons/address-book-new.svg')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname("__file__")))

GRADIENT_COLOR = '''
    background: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #d5dbdb, stop: 1 #eaeded);
    color: #000000;  /* 設定字體顏色 */
'''

VIDEO_DIAG_COLOR = '''
    background: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #f3dad8, stop: 1 #f7e8e7);
    color: #000000;  /* 設定字體顏色 */
'''

INFECTIOUS_DIAG_COLOR = '''
    background: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #a7fa9f, stop: 1 #c4e0e5);
    color: #000000;  /* 設定字體顏色 */
'''

UI_PATH = "ui"
UI_PY_MEDICAL = "pymedical.ui"
UI_LOGIN = "login.ui"
UI_LOGIN_STATISTICS = "login_statistics.ui"

UI_PY_BULLETIN = "pybulletin.ui"
UI_PY_BULLETIN1 = "pybulletin1.ui"
UI_PY_BULLETIN3 = "pybulletin3.ui"
UI_PY_BULLETIN6 = "pybulletin6.ui"
UI_PY_BULLETIN7 = "pybulletin7.ui"
UI_PY_BULLETIN8 = "pybulletin8.ui"
UI_PY_BULLETIN1366 = "pybulletin1366.ui"
UI_PY_BULLETIN_2ROOMS = "pybulletin_2rooms.ui"

UI_MEDICAL_RECORD = "medical_record.ui"
UI_MEDICAL_RECORD2 = "medical_record2.ui"
UI_INS_PRESCRIPT_RECORD = "ins_prescript_record.ui"
UI_SELF_PRESCRIPT_RECORD = "self_prescript_record.ui"
UI_INS_CARE_RECORD = "ins_care_record.ui"
UI_MEDICAL_RECORD_RECENTLY_HISTORY = "medical_record_recently_history.ui"
UI_MEDICAL_RECORD_MEMO = "medical_record_memo.ui"
UI_MEDICAL_RECORD_REGISTRATION = "medical_record_registration.ui"
UI_MEDICAL_RECORD_ORDER = "medical_record_order.ui"
UI_MEDICAL_RECORD_IMAGE = "medical_record_image.ui"
UI_MEDICAL_RECORD_FEES = "medical_record_fees.ui"
UI_MEDICAL_RECORD_LIST = "medical_record_list.ui"
UI_MEDICAL_RECORD_FAMILY = "medical_record_family.ui"
UI_MEDICAL_RECORD_EXAMINATION = "medical_record_examination.ui"
UI_MEDICAL_RECORD_GROWTH_CHART = "medical_record_growth_chart.ui"
UI_PREGNANT_FEMALE = "pregnant_female.ui"
UI_PREGNANT_MALE = "pregnant_male.ui"
UI_KEEP_BABY = "keep_baby.ui"
UI_PHYSIQUE_TABLE = "physique_table.ui"

UI_SYSTEM_UPDATE = "system_update.ui"

UI_PHYSIOTHERAPY = "physiotherapy.ui"
UI_PHYSIOTHERAPY_SCHEDULE = "physiotherapy_schedule.ui"
UI_PHYSIOTHERAPY_INCOME = "physiotherapy_income.ui"

UI_PATIENT_LIST = "patient_list.ui"
UI_PATIENT = "patient.ui"
UI_PATIENT_DATA = "patient_data.ui"
UI_PATIENT_NEW_CARE = "patient_new_care.ui"
UI_PATIENT_SETTINGS = "patient_settings.ui"

UI_CERTIFICATE_DIAGNOSIS = "certificate_diagnosis.ui"
UI_CERTIFICATE_PAYMENT = "certificate_payment.ui"

UI_RETURN_CARD = "return_card.ui"
UI_REGISTRATION = "registration.ui"
UI_RESERVATION = "reservation.ui"
UI_TEMPLATE = "template.ui"
UI_WAITING_LIST = "waiting_list.ui"
UI_CASHIER = "cashier.ui"
UI_PHARMACY = "pharmacy.ui"
UI_PY_PHARMACY = "py_pharmacy.ui"
UI_INCOME = "income.ui"
UI_INCOME_CASH_FLOW = "income_cash_flow.ui"
UI_INCOME_LIST = "income_list.ui"
UI_INCOME_SELF_PRESCRIPT = "income_self_prescript.ui"
UI_INCOME_PROJECT = "income_project.ui"
UI_INCOME_INS_LIST = "income_ins_list.ui"
UI_DEBT = "debt.ui"
UI_RETURN_GOODS = "return_goods.ui"

UI_PURCHASE = "purchase.ui"
UI_PURCHASE_LIST = "purchase_list.ui"
UI_PURCHASE_RECORDS = "purchase_records.ui"
UI_PURCHASE_RECORDS_LIST = "purchase_records_list.ui"
UI_EXAMINATION_LIST = "examination_list.ui"
UI_EXAMINATION = "examination.ui"

UI_EVENT_LOG = "event_log.ui"

UI_INS_CHECK = "ins_check.ui"
UI_INS_APPLY = "ins_apply.ui"
UI_INS_APPLY_LIST = "ins_apply_list.ui"
UI_INS_APPLY_TAB = "ins_apply_tab.ui"
UI_INS_JUDGE = "ins_judge.ui"

UI_INS_APPEAL = "ins_appeal.ui"

UI_INS_APPLY_CALCULATED_DATA = "ins_apply_calculated_data.ui"
UI_INS_APPLY_TOTAL_FEE = "ins_apply_total_fee.ui"
UI_INS_CHECK_APPLY_FEE = "ins_check_apply_fee.ui"
UI_INS_DOCTOR_APPLY_FEE = "ins_doctor_apply_fee.ui"
UI_INS_APPLY_FEE_PERFORMANCE = "ins_apply_fee_performance.ui"
UI_INS_APPLY_SCHEDULE_TABLE = "ins_apply_schedule_table.ui"
UI_INS_APPLY_TOUR = "ins_apply_tour.ui"
UI_INS_APPLY_INFECTIOUS = "ins_apply_infectious.ui"
UI_INS_APPLY_INDICATOR = "ins_apply_indicator.ui"

UI_STATISTICS_MEDICAL_RECORD = "statistics_medical_record.ui"
UI_STATISTICS_MEDICAL_RECORD_DIAG_TIME_LENGTH = "statistics_medical_record_diag_time_length.ui"
UI_STATISTICS_MEDICAL_RECORD_DISEASE_RANK = "statistics_medical_record_disease_rank.ui"

UI_STATISTICS_DAILY = "statistics_daily.ui"
UI_STATISTICS_DAILY_PERSON = "statistics_daily_person.ui"

UI_STATISTICS_BRANCH_DAILY = "statistics_branch_daily.ui"
UI_STATISTICS_BRANCH_DAILY_PERSON = "statistics_branch_daily_person.ui"
UI_STATISTICS_BRANCH_DAILY_INCOME = "statistics_branch_daily_income.ui"

UI_STATISTICS_COMMISSION = "statistics_commission.ui"

UI_STATISTICS_SALES_SUMMARY = "statistics_sales_summary.ui"
UI_STATISTICS_DOCTOR = "statistics_doctor.ui"
UI_STATISTICS_DOCTOR_AMOUNT = "statistics_doctor_amount.ui"
UI_STATISTICS_DOCTOR_AMOUNT_INCOME = "statistics_doctor_amount_income.ui"
UI_STATISTICS_DOCTOR_MEDICINE_PERCENT = "statistics_doctor_medicine_percent.ui"
UI_STATISTICS_DOCTOR_COUNT = "statistics_doctor_count.ui"
UI_STATISTICS_DOCTOR_INCOME = "statistics_doctor_income.ui"
UI_STATISTICS_DOCTOR_SALE = "statistics_doctor_sale.ui"
UI_STATISTICS_DOCTOR_VISIT_COUNT = "statistics_doctor_visit_count.ui"
UI_STATISTICS_DOCTOR_SUMMARY = "statistics_doctor_summary.ui"
UI_STATISTICS_DOCTOR_ACHIEVEMENT = "statistics_doctor_achievement.ui"
UI_STATISTICS_DOCTOR_PERFORMANCE = "statistics_doctor_performance.ui"
UI_STATISTICS_DOCTOR_COMMISSION = "statistics_doctor_commission.ui"
UI_STATISTICS_DOCTOR_SALE_SUMMARY = "statistics_doctor_sale_summary.ui"
UI_STATISTICS_DOCTOR_PROJECT_SALE = "statistics_doctor_project_sale.ui"

UI_STATISTICS_COMMISSION_SALE = "statistics_commission_sale.ui"

UI_STATISTICS_STAMP_DUTY = "statistics_stamp_duty.ui"
UI_STATISTICS_STAMP_DUTY_LIST = "statistics_stamp_duty_list.ui"

UI_STATISTICS_BUSINESS_INCOME = "statistics_business_income.ui"
UI_STATISTICS_BUSINESS_INCOME_LIST = "statistics_business_income_list.ui"

UI_STATISTICS_GROWTH_RATE = "statistics_growth_rate.ui"
UI_STATISTICS_GROWTH_MONTH = "statistics_growth_month.ui"
UI_STATISTICS_GROWTH_YEAR = "statistics_growth_year.ui"
UI_STATISTICS_GROWTH_INCOME = "statistics_growth_income.ui"

UI_STATISTICS_DOCTOR_MONTHLY = "statistics_doctor_monthly.ui"
UI_STATISTICS_DOCTOR_MONTHLY_COUNT = "statistics_doctor_monthly_count.ui"
UI_STATISTICS_DOCTOR_MONTHLY_PERSON_COUNT = "statistics_doctor_monthly_person_count.ui"
UI_STATISTICS_DOCTOR_MONTHLY_INCOME = "statistics_doctor_monthly_income.ui"

UI_STATISTICS_INS_DISCOUNT = "statistics_ins_discount.ui"
UI_STATISTICS_INS_DISCOUNT_REGIST_FEE = "statistics_ins_discount_regist_fee.ui"
UI_STATISTICS_INS_DISCOUNT_DIAG_SHARE_FEE = "statistics_ins_discount_diag_share_fee.ui"
UI_STATISTICS_INS_DISCOUNT_DRUG_SHARE_FEE = "statistics_ins_discount_drug_share_fee.ui"
UI_STATISTICS_MULTIPLE_PERFORMANCE = "statistics_multiple_performance.ui"
UI_STATISTICS_MULTIPLE_PERFORMANCE_WEEK_PERSON = "statistics_multiple_performance_week_person.ui"
UI_STATISTICS_MULTIPLE_PERFORMANCE_WEEK_INCOME = "statistics_multiple_performance_week_income.ui"
UI_STATISTICS_MULTIPLE_PERFORMANCE_WEEK_PROJECT = "statistics_multiple_performance_week_project.ui"
UI_STATISTICS_MULTIPLE_PERFORMANCE_WEEK_DOCTOR = "statistics_multiple_performance_week_doctor.ui"
UI_STATISTICS_INS_PREGNANT = "statistics_ins_pregnant.ui"
UI_STATISTICS_INS_PREGNANT_FEMALE = "statistics_ins_pregnant_female.ui"
UI_STATISTICS_INS_PREGNANT_MALE = "statistics_ins_pregnant_male.ui"
UI_STATISTICS_INS_PREGNANT_KEEP_BABY = "statistics_ins_pregnant_keep_baby.ui"

UI_STATISTICS_NURSING_HOME = "statistics_nursing_home.ui"
UI_STATISTICS_NURSING_HOME_DATA = "statistics_nursing_home_data.ui"
UI_STATISTICS_NURSING_HOME_DAILY_DATA = "statistics_nursing_home_daily_data.ui"

UI_STATISTICS_PERIOD_COUNT = "statistics_doctor.ui"
UI_STATISTICS_DOCTOR_PERIOD_COUNT = "statistics_doctor_period_count.ui"

UI_STATISTICS_COMMISSION_SUMMARY = "statistics_commission_summary.ui"
UI_STATISTICS_COMMISSION_AMOUNT = "statistics_commission_amount.ui"

UI_STATISTICS_MASSAGER = "statistics_massager.ui"
UI_STATISTICS_MASSAGER_COUNT = "statistics_massager_count.ui"
UI_STATISTICS_MASSAGER_INCOME = "statistics_massager_income.ui"
UI_STATISTICS_MASSAGER_SUMMARY = "statistics_massager_summary.ui"
UI_STATISTICS_MASSAGER_LIST = "statistics_massager_list.ui"

UI_STATISTICS_INS_PERFORMANCE = "statistics_ins_performance.ui"
UI_STATISTICS_INS_PERFORMANCE_DOCTOR = "statistics_ins_performance_doctor.ui"
UI_STATISTICS_INS_PERFORMANCE_MEDICAL_RECORD = "statistics_ins_performance_medical_record.ui"

UI_STATISTICS_RETURN_RATE = "statistics_return_rate.ui"
UI_STATISTICS_NO_RETURN_RATE = "statistics_no_return_rate.ui"
UI_STATISTICS_RETURN_RATE_DOCTOR = "statistics_return_rate_doctor.ui"
UI_STATISTICS_RETURN_RATE_MASSAGER = "statistics_return_rate_massager.ui"
UI_STATISTICS_NO_RETURN_RATE_DOCTOR = "statistics_no_return_rate_doctor.ui"

UI_STATISTICS_MEDICINE = "statistics_medicine.ui"
UI_STATISTICS_MEDICINE_SALES = "statistics_medicine_sales.ui"

UI_STATISTICS_BRANCH_PROJECT = "statistics_branch_project.ui"
UI_STATISTICS_BRANCH_PROJECT_SALES = "statistics_branch_project_sales.ui"

UI_DOCTOR_SCHEDULE = "doctor_schedule.ui"
UI_PHARMACIST_SCHEDULE = "pharmacist_schedule.ui"
UI_DOCTOR_NURSE_TABLE = "doctor_nurse_table.ui"

UI_CHECK_ERRORS = "check_errors.ui"
UI_CHECK_COURSE = "check_course.ui"
UI_CHECK_CARD = "check_card.ui"
UI_CHECK_MEDICAL_RECORD_COUNT = "check_medical_record_count.ui"
UI_CHECK_PRESCRIPT_DAYS = "check_prescript_days.ui"
UI_CHECK_INS_DRUG = "check_ins_drug.ui"
UI_CHECK_INS_TREAT = "check_ins_treat.ui"

UI_COURSE_ACCOMPLISH = "course_accomplish.ui"

UI_CHARGE_SETTINGS = "charge_settings.ui"
UI_CHARGE_SETTINGS_NHI = "charge_settings_nhi.ui"
UI_CHARGE_SETTINGS_REGIST = "charge_settings_regist.ui"
UI_CHARGE_SETTINGS_SHARE = "charge_settings_share.ui"
UI_CHARGE_SETTINGS_SELF = "charge_settings_self.ui"

UI_DIALOG_DIAGNOSIS = "dialog_diagnosis.ui"
UI_DIALOG_DIAGNOSTIC_PICKER = "dialog_diagnostic_picker.ui"
UI_DIALOG_DISEASE = "dialog_disease.ui"
UI_DIALOG_DISEASE2 = "dialog_disease2.ui"
UI_DIALOG_DISEASE_PICKER = "dialog_disease_picker.ui"
UI_DIALOG_INQUIRY = "dialog_inquiry.ui"
UI_DIALOG_EXTERNAL_CAUSES = "dialog_external_causes.ui"

UI_DIALOG_IC_CARD = "dialog_ic_card.ui"
UI_DIALOG_IC_CARD_RECORD = "dialog_ic_card_record.ui"

UI_DIALOG_COMPOUND_JSON = "dialog_compound_json.ui"

UI_DIALOG_INPUT_REGIST = "dialog_input_regist.ui"
UI_DIALOG_INPUT_DISCOUNT = "dialog_input_discount.ui"
UI_DIALOG_INPUT_SHARE = "dialog_input_share.ui"
UI_DIALOG_INPUT_NHI = "dialog_input_nhi.ui"
UI_DIALOG_INPUT_DIAGNOSTIC = "dialog_input_diagnostic.ui"
UI_DIALOG_INPUT_SUPPLIER = "dialog_input_supplier.ui"
UI_DIALOG_INPUT_DISEASE = "dialog_input_disease.ui"
UI_DIALOG_INPUT_MEDICINE = "dialog_input_medicine.ui"
UI_DIALOG_INPUT_DRUG = "dialog_input_drug.ui"
UI_DIALOG_INPUT_USER = "dialog_input_user.ui"
UI_DIALOG_INPUT_HOST = "dialog_input_host.ui"
UI_DIALOG_EDIT_DISEASE = "dialog_edit_disease.ui"
UI_DIALOG_RICH_TEXT = "dialog_rich_text.ui"
UI_DIALOG_BROWSER = "dialog_browser.ui"
UI_DIALOG_PATIENT_MEMO = "dialog_patient_memo.ui"
UI_DIALOG_COMMISSION = "dialog_commission.ui"
UI_DIALOG_INS_LIST_EDIT = "dialog_ins_list_edit.ui"
UI_DIALOG_CAPTURE_IMAGE = "dialog_capture_image.ui"
UI_DIALOG_EXAM_PRECHECK = "dialog_exam_precheck.ui"
UI_DIALOG_PURCHASE = "dialog_purchase.ui"

UI_DIALOG_MEDICAL_RECORD_LIST = "dialog_medical_record_list.ui"
UI_DIALOG_MEDICAL_RECORD_PAST_HISTORY = "dialog_medical_record_past_history.ui"
UI_DIALOG_MEDICAL_RECORD_HOSTS = "dialog_medical_record_hosts.ui"
UI_DIALOG_MEDICAL_RECORD_COLLECTION = "dialog_medical_record_collection.ui"
UI_DIALOG_MEDICAL_RECORD_EXPERIENCE = "dialog_medical_record_experience.ui"
UI_DIALOG_MEDICAL_RECORD_PICKER = "dialog_medical_record_picker.ui"
UI_DIALOG_MEDICAL_RECORD_DONE = "dialog_medical_record_done.ui"
UI_DIALOG_MEDICAL_RECORD_REFERENCE = "dialog_medical_record_reference.ui"
UI_DIALOG_REFERENCE_PRESCRIPT = "dialog_reference_prescript.ui"
UI_DIALOG_MEDICINE = "dialog_medicine.ui"
UI_DIALOG_PROJECT = "dialog_project.ui"
UI_DIALOG_DOSAGE = "dialog_dosage.ui"
UI_DIALOG_UNIT = "dialog_unit.ui"
UI_DIALOG_EXAMINATION = "dialog_examination.ui"
UI_DIALOG_PRESCRIPT_INSTRUCTION = "dialog_prescript_instruction.ui"

UI_DIALOG_EXAMINATION_LIST = "dialog_examination_list.ui"
UI_DIALOG_YOUTUBE = "dialog_youtube.ui"
UI_DIALOG_TUTORIAL_VIDEOS = "dialog_tutorial_videos.ui"

UI_DIALOG_STATISTICS_THERAPIST = "dialog_statistics_therapist.ui"
UI_DIALOG_STATISTICS_RETURN_RATE = "dialog_statistics_return_rate.ui"
UI_DIALOG_STATISTICS_NO_RETURN_RATE = "dialog_statistics_no_return_rate.ui"
UI_DIALOG_INS_DATE_DOCTOR = "dialog_ins_date_doctor.ui"

UI_DIALOG_CERTIFICATE_DIAGNOSIS = "dialog_certificate_diagnosis.ui"
UI_DIALOG_CERTIFICATE_PAYMENT = "dialog_certificate_payment.ui"
UI_DIALOG_CERTIFICATE_QUERY = "dialog_certificate_query.ui"

UI_DIALOG_PAST_HISTORY = "dialog_past_history.ui"
UI_DIALOG_PATIENT = "dialog_patient.ui"
UI_DIALOG_PATIENT_LIST = "dialog_patient_list.ui"
UI_DIALOG_SELECT_PATIENT = "dialog_select_patient.ui"
UI_DIALOG_SELECT_REMOTE_PATIENT = "dialog_select_remote_patient.ui"

UI_DIALOG_RESERVATION_BOOKING = "dialog_reservation_booking.ui"
UI_DIALOG_RESERVATION_MODIFY = "dialog_reservation_modify.ui"
UI_DIALOG_RESERVATION_QUERY = "dialog_reservation_query.ui"

UI_DIALOG_PHYSIOTHERAPY_BOOKING = "dialog_physiotherapy_booking.ui"
UI_DIALOG_INSERT_COMPOUND = "dialog_insert_compound.ui"
UI_DIALOG_INVALID_INS_DRUG = "dialog_invalid_ins_drug.ui"

UI_DIALOG_ADD_DEBT = "dialog_add_debt.ui"
UI_DIALOG_ADDRESS = "dialog_address.ui"
UI_DIALOG_SETTINGS = "dialog_settings.ui"
UI_DIALOG_SYMPTOM = "dialog_symptom.ui"
UI_DIALOG_SYMPTOM_KT = "dialog_symptom_kt.ui"
UI_DIALOG_SIMPLE_DICT = "dialog_simple_dict.ui"
UI_DIALOG_TONGUE = "dialog_tongue.ui"
UI_DIALOG_PULSE = "dialog_pulse.ui"
UI_DIALOG_PULSE_PICKER = "dialog_pulse_picker.ui"
UI_DIALOG_REMARK = "dialog_remark.ui"
UI_DIALOG_DISTINGUISH = "dialog_distinguish.ui"
UI_DIALOG_CURE = "dialog_cure.ui"
UI_DIALOG_RETURN_CARD = "dialog_return_card.ui"
UI_DIALOG_IC_RECORD_UPLOAD = "dialog_ic_record_upload.ui"
UI_DIALOG_INCOME = "dialog_income.ui"
UI_DIALOG_DEBT = "dialog_debt.ui"
UI_DIALOG_ADD_INVENTORY = "dialog_add_inventory.ui"
UI_DIALOG_ELECTRIC_ACUPUNCTURE = "dialog_electric_acupuncture.ui"
UI_DIALOG_COMPLICATED_ACUPUNCTURE = "dialog_complicated_acupuncture.ui"
UI_DIALOG_COMPLICATED_MASSAGE = "dialog_complicated_massage.ui"
UI_DIALOG_ADD_RETURN_GOODS = "dialog_add_return_goods.ui"

UI_DIALOG_PHARMACY_DOSAGE = "dialog_pharmacy_dosage.ui"

UI_DIALOG_TREAT_TIME = "dialog_treat_time.ui"
UI_DIALOG_TREAT_POSITION = "dialog_treat_position.ui"
UI_DIALOG_TREAT_AUXILIARY = "dialog_treat_auxiliary.ui"

UI_DIALOG_INTEGRATE_CARE = "dialog_integrate_care.ui"

UI_DIALOG_PURCHASE_LIST = "dialog_purchase_list.ui"
UI_DIALOG_EXPORT_EMR_XML = "dialog_export_emr_xml.ui"
UI_DIALOG_EXPORT_MEDICAL_RECORD_JSON = "dialog_export_medical_record_json.ui"
UI_DIALOG_MEDICAL_RECORD_VERSION_HISTORY = "dialog_medical_record_version_history.ui"
UI_DIALOG_VIEW_MEDICAL_RECORD_JSON = "dialog_view_medical_record_json.ui"

UI_DIALOG_CALENDAR = "dialog_calendar.ui"
UI_DIALOG_SCHEDULE = "dialog_schedule.ui"
UI_DIALOG_INSTRUCTION = "dialog_instruction.ui"

UI_DIALOG_TEMPORARY_SCHEDULE = "dialog_temporary_schedule.ui"
UI_DIALOG_CASHIER_MACHINE_SETTINGS = "dialog_cashier_machine_settings.ui"
UI_DIALOG_PATIENT_MEDICAL_RECORD = "dialog_patient_medical_record.ui"
UI_DIALOG_AUTO_RESERVATION_TABLE = "dialog_auto_reservation_table.ui"
UI_DIALOG_HERB_FEE_SETTING = "dialog_herb_fee_setting.ui"

UI_DIALOG_DATE_PICKER = "dialog_date_picker.ui"
UI_DIALOG_DATE_DURATION = "dialog_date_duration.ui"
UI_DIALOG_DATE_PERIOD = "dialog_date_period.ui"

UI_DIALOG_ACUPUNCTURE_POINT = "dialog_acupuncture_point.ui"
UI_DIALOG_PERMISSION = "dialog_permission.ui"
UI_DIALOG_MENU_SETTING = "dialog_menu_setting.ui"
UI_DIALOG_HOSTS = "dialog_hosts.ui"
UI_DIALOG_ADD_DIAGNOSTIC_DICT = "dialog_add_diagnostic_dict.ui"
UI_DIALOG_ADD_DEPOSIT = "dialog_add_deposit.ui"
UI_DIALOG_IMPORT_MEDICAL_RECORD = "dialog_import_medical_record.ui"
UI_DIALOG_IMPORT_HOME_CARE = "dialog_import_home_care.ui"
UI_DIALOG_OFF_DAY_SETTING = "dialog_off_day_setting.ui"
UI_DIALOG_PERMISSION_LIST_SETTING = "dialog_permission_list_setting.ui"
UI_DIALOG_EXAM_RESULT = "dialog_exam_result.ui"
UI_DIALOG_PURCHASE_QUERY = "dialog_purchase_query.ui"
UI_DIALOG_RETURN_GOODS = "dialog_return_goods.ui"
UI_DIALOG_EXCHANGE_GOODS = "dialog_exchange_goods.ui"
UI_DIALOG_PURCHASE_COURSE_LIST = "dialog_purchase_course_list.ui"
UI_DIALOG_START_NO = "dialog_start_no.ui"
UI_DIALOG_CONFLICT_DRUG = "dialog_conflict_drug.ui"
UI_DIALOG_SET_PERSON = "dialog_set_person.ui"
UI_DIALOG_BULLETIN_SETTINGS = "dialog_bulletin_settings.ui"
UI_DIALOG_SELECT_MEDICINE_SET = "dialog_select_medicine_set.ui"
UI_DIALOG_DOCTOR_MONTH_SCHEDULE = "dialog_doctor_month_schedule.ui"

UI_DIALOG_PURGE_TEMP_PATIENT = "dialog_purge_temp_patient.ui"

UI_DIALOG_WEB_BULLETIN = "dialog_web_bulletin.ui"
UI_DIALOG_MEDICINE_SETTINGS = "dialog_medicine_settings.ui"
UI_DIALOG_MEDICINE_CODE = "dialog_medicine_code.ui"

UI_DIALOG_INS_CHECK = "dialog_ins_check.ui"
UI_DIALOG_INS_APPLY = "dialog_ins_apply.ui"

UI_DIALOG_INS_APPEAL = "dialog_ins_appeal.ui"
UI_DIALOG_INS_APPEAL_ITEMS = "dialog_ins_appeal_items.ui"

UI_DIALOG_INS_JUDGE = "dialog_ins_judge.ui"
UI_DIALOG_INS_CARE = "dialog_ins_care.ui"
UI_DIALOG_DOCTOR_SCHEDULE = "dialog_doctor_schedule.ui"
UI_DIALOG_DOCTOR_SCHEDULE_PERIOD = "dialog_doctor_schedule_period.ui"
UI_DIALOG_PHARMACIST_SCHEDULE = "dialog_pharmacist_schedule.ui"
UI_DIALOG_NURSE_SCHEDULE = "dialog_nurse_schedule.ui"
UI_DIALOG_COURSE_LIST = "dialog_course_list.ui"
UI_DIALOG_CERTIFICATE_ITEMS = "dialog_certificate_items.ui"

UI_DIALOG_DATABASE_REPAIR = "dialog_database_repair.ui"

UI_DIALOG_MASSAGE_RESERVATION = "dialog_massage_reservation.ui"
UI_DIALOG_CUSTOMER = "dialog_customer.ui"
UI_DIALOG_MASSAGE_CASE_LIST = "dialog_massage_case_list.ui"
UI_MASSAGE_PURCHASE_LIST = "massage_purchase_list.ui"
UI_MASSAGE_PURCHASE = "massage_purchase.ui"
UI_MASSAGE_INCOME = "massage_income.ui"
UI_DIALOG_MASSAGE_PURCHASE_LIST = "dialog_massage_purchase_list.ui"
UI_MASSAGE_INCOME_CASH_FLOW = "massage_income_cash_flow.ui"
UI_MASSAGE_INCOME_LIST = "massage_income_list.ui"
UI_MASSAGE_CUSTOMER_LIST = "massage_customer_list.ui"
UI_MASSAGE_CASE_LIST = "massage_case_list.ui"
UI_STATISTICS_MASSAGE = "statistics_massage.ui"
UI_STATISTICS_MASSAGE_COUNT = "statistics_massage_count.ui"
UI_STATISTICS_MASSAGE_INCOME = "statistics_massage_income.ui"
UI_STATISTICS_MASSAGE_PAYMENT = "statistics_massage_payment.ui"
UI_STATISTICS_MASSAGE_SALE = "statistics_massage_sale.ui"

UI_DICT_DIAGNOSTIC = "dict_diagnostic.ui"
UI_DICT_SYMPTOM = "dict_symptom.ui"
UI_DICT_TONGUE = "dict_tongue.ui"
UI_DICT_PULSE = "dict_pulse.ui"
UI_DICT_REMARK = "dict_remark.ui"

UI_DICT_DISEASE = "dict_disease.ui"
UI_DICT_DISEASE_CUSTOM = "dict_disease_custom.ui"

UI_DICT_DISTINGUISH = "dict_distinguish.ui"
UI_DICT_CURE = "dict_cure.ui"
UI_DICT_MEDICINE = "dict_medicine.ui"
UI_DICT_MISC = "dict_misc.ui"
UI_DICT_SUPPLIER = "dict_supplier.ui"
UI_DICT_DRUG = "dict_drug.ui"
UI_DICT_TREAT = "dict_treat.ui"
UI_DICT_EXAM = "dict_exam.ui"
UI_DICT_INSTRUCTION = "dict_instruction.ui"
UI_DICT_HOSP = "dict_hosp.ui"
UI_DICT_ADDRESS_BOOK = "dict_address_book.ui"
UI_DICT_COMPOUND = "dict_compound.ui"

UI_DICT_INS_DRUG = "dict_ins_drug.ui"

UI_STOCK_IN = "stock_in.ui"
UI_STOCK_IN_DATA = "stock_in_data.ui"
UI_STOCK_IN_LIST = "stock_in_list.ui"

UI_STOCK_OUT = "stock_out.ui"
UI_STOCK_OUT_DATA = "stock_out_data.ui"
UI_STOCK_OUT_LIST = "stock_out_list.ui"

UI_STOCK_REPLENISHMENT = "stock_replenishment.ui"
UI_STOCK_INVENTORY = "stock_inventory.ui"
UI_STOCK_DISPENSE = "stock_dispense.ui"
UI_GOODS = "goods.ui"

UI_CHARGE_CASH = "charge_cash.ui"
UI_CHOOSE_DOCTOR = "choose_doctor.ui"
UI_FIRST_VISIT_REGISTRATION = "first_visit_registration.ui"

UI_SHOW_MESSAGE = "show_message.ui"
UI_REGISTRATION_INSERT_CARD = "registration_insert_card.ui"

UI_PY_CASHIER = "pycashier.ui"
UI_PYCASHIER_HOME = "pycashier_home.ui"
UI_PYCASHIER_HOME3 = "pycashier_home3.ui"
UI_PYCASHIER_REGISTRATION = "pycashier_registration.ui"
UI_PYCASHIER_PAYMENT = "pycashier_payment.ui"
UI_PYCASHIER_COMPLETED = "pycashier_completed.ui"

UI_PY_CASHIER2 = "pycashier2.ui"
UI_PYCASHIER2_HOME = "pycashier2_home.ui"
UI_PYCASHIER2_REGISTRATION = "pycashier2_registration.ui"
UI_PYCASHIER2_PAYMENT = "pycashier2_payment.ui"
UI_PYCASHIER2_COMPLETED = "pycashier2_completed.ui"

UI_KIOSK = "kiosk.ui"
UI_KIOSK_HOME = "kiosk_home.ui"
UI_KIOSK_REGISTRATION = "kiosk_registration.ui"
UI_KIOSK_PAYMENT = "kiosk_payment.ui"
UI_KIOSK_COMPLETED = "kiosk_completed.ui"

UI_USERS = "users.ui"
UI_CONVERT = "convert.ui"
UI_IC_RECORD_UPLOAD = 'ic_record_upload.ui'
UI_STATISTICS_CORRECTION_REG = 'statistics_correction_reg.ui'
UI_STATISTICS_TRACE = 'statistics_trace.ui'
UI_STATISTICS_PATIENT_AGE_GROUP = 'statistics_patient_age_group.ui'
UI_STATISTICS_INS_APPLY_YEAR = 'statistics_ins_apply_year.ui'
UI_STATISTICS_PERIOD_YEAR = 'statistics_period_year.ui'

UI_RESTORE_RECORDS = "restore_records.ui"
UI_RESTORE_MEDICAL_RECORDS = "restore_medical_records.ui"

UI_MASSAGE_REGISTRATION = "massage_registration.ui"

THEME = ['Fusion', 'Windows', 'Cleanlooks', 'gtk2', 'motif', 'plastic', 'cde', 'qt5-ct-style']
WIN32_THEME = ['Fusion', 'Windows', 'WindowsXP', 'WindowsVista']


# 載入 ui 檔
def load_ui_file(ui_file, self, native_menu_bar=False):
    try:
        ui_file_name = os.path.join(BASE_DIR, UI_PATH, ui_file)
        ui = uic.loadUi(ui_file_name, self)
        if not native_menu_bar:
            try:
                ui.menubar.setNativeMenuBar(False)
            except Exception:
                pass
        
        # try:
        #     set_all_input_widget_shadow(ui)
        # except Exception:
        #     pass

        return ui
    except Exception:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('找不到ui檔')
        msg_box.setText(f"<font size='4' color='red'><b>找不到 {ui_file_name}, 請檢查檔案是否存在.</b></font>")
        msg_box.setInformativeText("請與本公司聯繫, 並告知上面的訊息.")
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

        return None


def set_all_input_widget_shadow(ui):
    input_types = (
        QtWidgets.QLineEdit,
        QtWidgets.QTextEdit,
        # QtWidgets.QPlainTextEdit,
        # QtWidgets.QTableWidget,
    )

    for input_class in input_types:
        for widget in ui.findChildren(input_class):
            set_focus_shadow(widget)


def set_focus_shadow(widget, color="#409EFF", blur_radius=15):
    """
    套用 Aqua 風格聚焦樣式：含藍色邊框 + 陰影效果
    """
    # 設定 QSS 樣式（統一 Aqua 邊框）
    widget.setStyleSheet(f"""
        {widget.metaObject().className()} {{
            border: 2px solid #cccccc;
            padding: 2px;
            background-color: #ffffff;
        }}

        {widget.metaObject().className()}:focus {{
            border: 2px solid {color};
            background-color: #ffffff;
        }}
    """)

    # 定義焦點事件
    def apply_shadow():
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setOffset(0, 0)
        shadow.setBlurRadius(blur_radius)
        shadow.setColor(QtGui.QColor(color))
        widget.setGraphicsEffect(shadow)

    def remove_shadow():
        widget.setGraphicsEffect(None)

    original_focus_in = widget.focusInEvent
    original_focus_out = widget.focusOutEvent

    def on_focus_in(event):
        apply_shadow()
        if original_focus_in:
            original_focus_in(event)

    def on_focus_out(event):
        remove_shadow()
        if original_focus_out:
            original_focus_out(event)

    widget.focusInEvent = on_focus_in
    widget.focusOutEvent = on_focus_out


def get_discount_type(database):
    discount_type = []
    sql = 'SELECT * from charge_settings where ChargeType IN ("掛號費優待", "自費掛號費優待")'
    rows = database.select_record(sql)
    for row in rows:
        discount_type.append(row['ItemName'])

    return [None] + nhi_utils.DISCOUNT + discount_type


# 設定 comboBox item
def set_combo_box(combobox, items, *args):
    combobox.clear()

    combobox.setMaxVisibleItems(30)
    if items == '掛號優待':
        items = get_discount_type(args[0])
        args = []

    for arg in args:
        combobox.addItem(arg)

    for item in items:
        if combobox.findText(item) < 0:  # not found
            combobox.addItem(item)


def set_combo_box_item_color(combobox, colors):
    for item_no in range(len(colors)):
        if colors is None:
            continue

        combobox.setItemData(
            item_no, colors[item_no], QtCore.Qt.TextColorRole)


# 設定輸入文字補全
def set_completer(database, sql, field, widget):
    rows = database.select_record(sql)
    if rows is None:
        return

    completer_list = []
    for row in rows:
        if type(field) is list:
            field_name = ''
            for f in field:
                field_name += row[f]
        else:
            field_name = row[field]

        completer_list.append(field_name)

    model = QtCore.QStringListModel()
    model.setStringList(completer_list)
    completer = QtWidgets.QCompleter()
    completer.setModel(model)
    completer.setCompletionColumn(2)

    if type(widget) is list:
        for w in widget:
            w.setCompleter(completer)
    else:
        widget.setCompleter(completer)


def set_table_widget_field_icon(table_widget, row_no, col_no, icon_file_name,
                                property_name, property_value, function_call):
    icon = QtGui.QIcon(icon_file_name)

    button = QtWidgets.QPushButton(table_widget)
    button.setProperty(property_name, property_value)
    button.setIcon(icon)
    button.setFlat(True)
    if function_call is not None:
        button.clicked.connect(function_call)

    table_widget.setCellWidget(row_no, col_no, button)


def set_table_widget_image(table_widget, row_no, col_no, image_file, image_size):
    image = QtWidgets.QLabel()

    image.setPixmap(QtGui.QPixmap(image_file))
    image.setMaximumWidth(image_size)
    image.setMaximumHeight(image_size)
    image.setScaledContents(True)
    table_widget.setCellWidget(row_no, col_no, image)


# 設定 instruction comboBox
def set_instruction_combo_box(database, combobox):
    set_combo_box(combobox, nhi_utils.INSTRUCTION, None)

    sql = '''
        SELECT * FROM clinic
        WHERE
            ClinicType = "指示"
        ORDER BY LENGTH(ClinicName), CAST(CONVERT(`ClinicName` using big5) AS BINARY)
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return

    ac_exist = False
    pc_exist = False
    pc_sleep_exist = False

    for row in rows:
        instruction = string_utils.xstr(row['ClinicName'])
        if instruction == '飯前':
            ac_exist = True
        elif instruction == '飯後':
            pc_exist = True
        elif instruction == '飯後睡前':
            pc_sleep_exist = True

        if instruction in nhi_utils.INSTRUCTION:
            continue

        combobox.addItem(instruction[:20])

    if not ac_exist:
        index = combobox.findText('飯前')
        if index != -1:
            combobox.removeItem(index)
    if not pc_exist:
        index = combobox.findText('飯後')
        if index != -1:
            combobox.removeItem(index)
    if not pc_sleep_exist:
        index = combobox.findText('飯後睡前')
        if index != -1:
            combobox.removeItem(index)


def get_medical_record_ui_file(system_settings):
    if system_settings.field('病歷版面') == '版面1':
        ui_file = UI_MEDICAL_RECORD
    elif system_settings.field('病歷版面') == '版面2':
        ui_file = UI_MEDICAL_RECORD2
    else:
        ui_file = UI_MEDICAL_RECORD

    return ui_file


def get_default_color(widget):
    palette = widget.palette()
    default_color = palette.color(QtGui.QPalette.Text)  # 系統預設文字顏色

    return default_color

    
def save_settings(widget, setting_group):
    settings = QSettings('__settings.ini', QSettings.IniFormat)
    settings.beginGroup(setting_group)
    try:
        # 紀錄是否最大化（下次才知道要不要 showMaximized）
        settings.setValue("maximized", widget.isMaximized())

        # 直接存目前的幾何；Qt 會把「正常狀態」大小保存好
        settings.setValue("geometry", widget.saveGeometry())  # QByteArray
        settings.setValue("size", widget.size())              # QSize（備援）
        settings.setValue("pos",  widget.pos())               # QPoint（備援）
    finally:
        settings.endGroup()


def restore_settings(widget, setting_group, qsize=QSize(858, 769), qpoint=QPoint(1054, 225)):
    settings = QSettings('__settings.ini', QSettings.IniFormat)    
    settings.beginGroup(setting_group)
    try:
        # 指定型別，避免還原失效
        geom = settings.value("geometry", QByteArray(), type=QByteArray)
        maximized = settings.value("maximized", False, bool)
        size = settings.value("size", qsize, type=QSize)
        pos  = settings.value("pos",  qpoint, type=QPoint)
    finally:
        settings.endGroup()

    # 先還原 geometry；若沒有才用 size/pos 備援
    if isinstance(geom, QByteArray) and not geom.isEmpty():
        widget.restoreGeometry(geom)
    else:
        if size is not None:
            widget.resize(size)
        if pos is not None:
            widget.move(pos)

    if maximized:
        # 幾何要先還原完，再最大化
        widget.showMaximized()

