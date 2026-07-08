import importlib


def get_module_name(tab_name):
    """
    根據 tab_name 動態載入對應的模組與類別。
    字典格式: 'Tab名稱': ['模組檔名', '類別名稱']
    """
    module_dict = {
        "門診掛號": ["registration", "Registration"],
        "預約掛號": ["reservation", "Reservation"],
        "批價作業": ["cashier", "Cashier"],
        "藥局作業": ["pharmacy", "Pharmacy"],
        "健保卡欠還卡": ["return_card", "ReturnCard"],
        "欠還款作業": ["debt", "Debt"],
        "櫃台購藥": ["purchase_list", "PurchaseList"],
        "退貨": ["return_goods", "ReturnGoods"],
        "購買商品": ["purchase", "Purchase"],
        "自費療程實現": ["course_accomplish", "CourseAccomplish"],
        "掛號櫃台結帳": ["income", "Income"],
        "病患查詢": ["patient_list", "PatientList"],
        "健保IC卡資料上傳": ["ic_record_upload", "ICRecordUpload"],
        "醫師看診作業": ["waiting_list", "WaitingList"],
        "病歷資料": ["medical_record", "MedicalRecord"],
        "參考病歷": ["medical_record", "MedicalRecord"],
        "病歷統計": ["statistics_medical_record", "StatisticsMedicalRecord"],
        "檢驗報告查詢": ["examination_list", "ExaminationList"],
        "檢驗報告登錄": ["examination", "Examination"],
        "自費銷售記錄": ["purchase_records", "PurchaseRecords"],
        "自費銷售抽成總表": [
            "statistics_commission_summary",
            "StatisticsCommissionSummary",
        ],
        "醫師自費銷售金額總表": ["statistics_sales_summary", "StatisticsSalesSummary"],
        "收費設定": ["charge_settings", "ChargeSettings"],
        "醫師班表": ["doctor_schedule", "DoctorSchedule"],
        "藥師班表": ["pharmacist_schedule", "PharmacistSchedule"],
        "護理師跟診表": ["doctor_nurse_table", "DoctorNurseTable"],
        "使用者管理": ["users", "Users"],
        "診察資料": ["dict_diagnostic", "DictDiagnostic"],
        "處方資料": ["dict_medicine", "DictMedicine"],
        "其他資料": ["dict_misc", "DictMisc"],
        "健保藥品": ["dict_ins_drug", "DictInsDrug"],
        "病歷查詢": ["medical_record_list", "MedicalRecordList"],
        "病患資料": ["patient", "Patient"],
        "申報檢查": ["ins_check", "InsCheck"],
        "健保申報": ["ins_apply", "InsApply"],
        "健保抽審": ["ins_judge", "InsJudge"],
        "健保申復": ["ins_appeal", "InsAppeal"],
        "孕產照護報表": ["statistics_ins_pregnant", "StatisticsInsPregnant"],
        "照護機構院民資料報表": ["statistics_nursing_home", "StatisticsNursingHome"],
        "清冠一號補助清冊": ["ins_apply_infectious", "InsApplyInfectious"],
        "矯正機關內門診報表": ["statistics_correction_reg", "StatisticsCorrectionReg"],
        "診斷證明書": ["certificate_diagnosis", "CertificateDiagnosis"],
        "醫療費用證明書": ["certificate_payment", "CertificatePayment"],
        "日報表": ["statistics_daily", "StatisticsDaily"],
        "醫師統計": ["statistics_doctor", "StatisticsDoctor"],
        "醫師月報表": ["statistics_doctor_monthly", "StatisticsDoctorMonthly"],
        "醫師金額統計": ["statistics_doctor_amount", "StatisticsDoctorAmount"],
        "回診率統計": ["statistics_return_rate", "StatisticsReturnRate"],
        "未回診統計": ["statistics_no_return_rate", "StatisticsNoReturnRate"],
        "用藥統計": ["statistics_medicine", "StatisticsMedicine"],
        "健保申報業績": ["statistics_ins_performance", "StatisticsInsPerformance"],
        "醫師銷售業績統計": [
            "statistics_doctor_performance",
            "StatisticsDoctorPerformance",
        ],
        "健保門診優惠統計": ["statistics_ins_discount", "StatisticsInsDiscount"],
        "綜合業績報表": [
            "statistics_multiple_performance",
            "StatisticsMultiplePerformance",
        ],
        "業績成長統計": ["statistics_growth_rate", "StatisticsGrowthRate"],
        "自費抽成統計": ["statistics_commission", "StatisticsCommission"],
        "診數統計": ["statistics_period_count", "StatisticsPeriodCount"],
        "分院專案統計": ["statistics_branch_project", "StatisticsBranchProject"],
        "分院日報表": ["statistics_branch_daily", "StatisticsBranchDaily"],
        "推拿師統計": ["statistics_massager", "StatisticsMassager"],
        "資料回復": ["restore_records", "RestoreRecords"],
        "養生館掛號": ["massage_registration", "MassageRegistration"],
        "系統日誌": ["event_log", "EventLog"],
        "廠商資料": ["dict_supplier", "DictSupplier"],
        "進貨": ["stock_in", "StockIn"],
        "銷貨": ["stock_dispense", "StockDispense"],
        "出貨": ["stock_out", "StockOut"],
        "補貨": ["stock_replenishment", "StockReplenishment"],
        "盤點": ["stock_inventory", "StockInventory"],
        "進貨商品資料": ["goods", "Goods"],
        "物理治療預約": ["physiotherapy", "Physiotherapy"],
        "自費印花稅統計": ["statistics_stamp_duty", "StatisticsStampDuty"],
        "執行業務所得統計": ["statistics_business_income", "StatisticsBusinessIncome"],
        "何處得知本診所統計": ["statistics_trace", "StatisticsTrace"],
        "病患優待身份統計": ["statistics_discount_type", "StatisticsDiscountType"],
        "病患年齡分佈統計": [
            "statistics_patient_age_group",
            "StatisticsPatientAgeGroup",
        ],
        "健保申報分列項目表": ["statistics_ins_apply_year", "StatisticsInsApplyYear"],
        "年度診次統計": ["statistics_period_year", "StatisticsPeriodYear"],
        "醫師處方類別抽成統計": [
            "statistics_doctor_medicine",
            "StatisticsDoctorMedicine",
        ],
    }

    target_class = None

    try:
        if tab_name in module_dict:
            info = module_dict[tab_name]
            module = importlib.import_module(info[0])
            current_module = importlib.reload(module)
            target_class = getattr(current_module, info[1])
    except Exception as e:
        print(f"載入模組失敗 ({tab_name}): {e}")
        target_class = None

    return target_class


def get_module(tab_name):
    if tab_name.find("病歷資料") != -1:
        tab_name = "病歷資料"
    elif tab_name.find("病患資料") != -1:
        tab_name = "病患資料"
    elif tab_name.find("檢驗報告-") != -1:
        tab_name = "檢驗報告登錄"
    elif tab_name.find("醫療費用證明書-") != -1:
        tab_name = "醫療費用證明書"

    module_name = get_module_name(tab_name)

    return module_name


# 病歷登錄-健保處方
def get_ins_prescript_record(
    parent, database, system_settings, case_key, medicine_set, call_from
):
    import ins_prescript_record

    module = importlib.reload(ins_prescript_record)
    tab_widget = module.InsPrescriptRecord(
        parent, database, system_settings, case_key, medicine_set, call_from
    )

    return tab_widget


# 病歷登錄-專案照護
def get_ins_care_record(parent, database, system_settings, case_key, medicine_set):
    import ins_care_record

    module = importlib.reload(ins_care_record)
    tab_widget = module.InsCareRecord(
        parent, database, system_settings, case_key, medicine_set
    )

    return tab_widget


# 病歷登錄-自費處方
def get_self_prescript_record(
    parent, database, system_settings, case_key, medicine_set, call_from
):
    import self_prescript_record

    module = importlib.reload(self_prescript_record)
    tab_widget = module.SelfPrescriptRecord(
        parent, database, system_settings, case_key, medicine_set, call_from
    )

    return tab_widget


# 病歷登錄-最近病歷
def get_medical_record_recently_history(
    parent, database, system_settings, case_key, patient_key, call_from
):
    import medical_record_recently_history

    module = importlib.reload(medical_record_recently_history)
    tab_widget = module.MedicalRecordRecentlyHistory(
        parent, database, system_settings, case_key, patient_key, call_from
    )

    return tab_widget


# 病歷登錄-批價明細
def get_medical_record_fees(
    parent, database, system_settings, medical_record, case_key, patient_key, call_from
):
    import medical_record_fees

    module = importlib.reload(medical_record_fees)
    tab_widget = module.MedicalRecordFees(
        parent,
        database,
        system_settings,
        medical_record,
        case_key,
        patient_key,
        call_from,
    )

    return tab_widget


# 病歷登錄-門診資料
def get_medical_record_registration(
    parent, database, system_settings, case_key, call_from
):
    import medical_record_registration

    module = importlib.reload(medical_record_registration)
    tab_widget = module.MedicalRecordRegistration(
        parent, database, system_settings, case_key, call_from
    )

    return tab_widget


# 病歷登錄-家族病歷
def get_medical_record_family(parent, database, system_settings, case_key, call_from):
    import medical_record_family

    module = importlib.reload(medical_record_family)
    tab_widget = module.MedicalRecordFamily(
        parent, database, system_settings, case_key, call_from
    )

    return tab_widget


# 病歷登錄-檢驗報告
def get_medical_record_examination(
    parent, database, system_settings, patient_key, call_from
):
    import medical_record_examination

    module = importlib.reload(medical_record_examination)
    tab_widget = module.MedicalRecordExamination(
        parent, database, system_settings, patient_key, call_from
    )

    return tab_widget


# 病歷登錄-病歷影像
def get_medical_record_image(parent, database, system_settings, case_key, patient_key):
    import medical_record_image

    module = importlib.reload(medical_record_image)
    tab_widget = module.MedicalRecordImage(
        parent, database, system_settings, case_key, patient_key
    )

    return tab_widget


# 病歷登錄-存檔前檢查
def get_medical_record_check(parent, **kwargs):
    import medical_record_check

    module = importlib.reload(medical_record_check)
    record_check = module.MedicalRecordCheck(parent, **kwargs)

    return record_check


# 病歷登錄-備忘錄
def get_medical_record_memo(parent, database, system_settings, case_key, patient_key):
    import medical_record_memo

    module = importlib.reload(medical_record_memo)
    tab_widget = module.MedicalRecordMemo(
        parent, database, system_settings, case_key, patient_key
    )

    return tab_widget


# 病歷登錄-醫囑
def get_medical_record_order(parent, database, system_settings, case_key, call_from):
    import medical_record_order

    module = importlib.reload(medical_record_order)
    tab_widget = module.MedicalRecordOrder(
        parent, database, system_settings, case_key, call_from
    )

    return tab_widget


# 病歷登錄-兒童生長曲線圖
def get_medical_record_growth_chart(
    parent, database, system_settings, case_key, call_from
):
    import medical_record_growth_chart

    module = importlib.reload(medical_record_growth_chart)
    tab_widget = module.MedicalRecordGrowthChart(
        parent, database, system_settings, case_key, call_from
    )

    return tab_widget


# 病歷登錄-助孕照護 女
def get_pregnant_female(parent, database, system_settings, case_key, call_from):
    import pregnant_female

    module = importlib.reload(pregnant_female)
    tab_widget = module.PregnantFemale(
        parent, database, system_settings, case_key, call_from
    )

    return tab_widget


# 病歷登錄-助孕照護 男
def get_pregnant_male(parent, database, system_settings, case_key, call_from):
    import pregnant_male

    module = importlib.reload(pregnant_male)
    tab_widget = module.PregnantMale(
        parent, database, system_settings, case_key, call_from
    )

    return tab_widget


# 病歷登錄-助孕照護-中醫體質質量表
def get_physique_table(parent, database, system_settings, case_key, call_from):
    import physique_table

    module = importlib.reload(physique_table)
    widget = module.PhysiqueTable(
        parent, database, system_settings, case_key, call_from
    )

    return widget


# 病歷登錄-保胎照護
def get_keep_baby(parent, database, system_settings, case_key, call_from):
    import keep_baby

    module = importlib.reload(keep_baby)
    tab_widget = module.KeepBaby(parent, database, system_settings, case_key, call_from)

    return tab_widget


# 系統更新
def get_system_update(parent, database, system_settings):
    import system_update

    module = importlib.reload(system_update)
    widget = module.SystemUpdate(parent, database, system_settings)

    return widget


# 轉檔
def get_convert(parent, database, system_settings):
    from convert import convert

    module = importlib.reload(convert)
    dialog = module.DialogConvert(parent, database, system_settings)

    return dialog


# 資料庫檢查
def get_check_database(parent, database, system_settings, call_from):
    import check_database

    module = importlib.reload(check_database)
    widget = module.CheckDatabase(parent, database, system_settings, call_from)

    return widget


# 系統登入
def get_login(parent, database, system_settings, call_from=None):
    import login

    module = importlib.reload(login)
    dialog = module.Login(parent, database, system_settings, call_from)

    return dialog


# 登入前統計資料
def get_login_statistics(parent, database, system_settings, user_name):
    import login_statistics

    module = importlib.reload(login_statistics)
    widget = module.LoginStatistics(parent, database, system_settings, user_name)

    return widget


# 系統備份
def get_backup(parent, database, system_settings):
    import backup

    module = importlib.reload(backup)
    widget = module.Backup(parent, database, system_settings)

    return widget


# 掛號費設定
def get_charge_settings_regist(parent, *args):
    import charge_settings_regist

    module = importlib.reload(charge_settings_regist)
    widget = module.ChargeSettingsRegist(parent, *args)

    return widget


# 部份負擔設定
def get_charge_settings_share(parent, *args):
    import charge_settings_share

    module = importlib.reload(charge_settings_share)
    widget = module.ChargeSettingsShare(parent, *args)

    return widget


# 支付標準設定
def get_charge_settings_nhi(parent, *args):
    import charge_settings_nhi

    module = importlib.reload(charge_settings_nhi)
    widget = module.ChargeSettingsNHI(parent, *args)

    return widget


# 自費收費設定
def get_charge_settings_self(parent, *args):
    import charge_settings_self

    module = importlib.reload(charge_settings_self)
    widget = module.ChargeSettingsSelf(parent, *args)

    return widget


# 主訴詞庫
def get_dict_symptom(parent, *args):
    import dict_symptom

    module = importlib.reload(dict_symptom)
    widget = module.DictSymptom(parent, *args)

    return widget


# 舌診詞庫
def get_dict_tongue(parent, *args):
    import dict_tongue

    module = importlib.reload(dict_tongue)
    widget = module.DictTongue(parent, *args)

    return widget


# 脈象詞庫
def get_dict_pulse(parent, *args):
    import dict_pulse

    module = importlib.reload(dict_pulse)
    widget = module.DictPulse(parent, *args)

    return widget


# 備註詞庫
def get_dict_remark(parent, *args):
    import dict_remark

    module = importlib.reload(dict_remark)
    widget = module.DictRemark(parent, *args)

    return widget


# 病名詞庫
def get_dict_disease(parent, *args):
    import dict_disease

    module = importlib.reload(dict_disease)
    widget = module.DictDisease(parent, *args)

    return widget


# 病名詞庫
def get_dict_disease_custom(parent, *args):
    import dict_disease_custom

    module = importlib.reload(dict_disease_custom)
    widget = module.DictDiseaseCustom(parent, *args)

    return widget


# 辨證詞庫
def get_dict_distinguish(parent, *args):
    import dict_distinguish

    module = importlib.reload(dict_distinguish)
    widget = module.DictDistinguish(parent, *args)

    return widget


# 治則詞庫
def get_dict_cure(parent, *args):
    import dict_cure

    module = importlib.reload(dict_cure)
    widget = module.DictCure(parent, *args)

    return widget


# 藥品詞庫
def get_dict_drug(parent, *args):
    import dict_drug

    module = importlib.reload(dict_drug)
    widget = module.DictDrug(parent, *args)

    return widget


# 處置詞庫
def get_dict_treat(parent, *args):
    import dict_treat

    module = importlib.reload(dict_treat)
    widget = module.DictTreat(parent, *args)

    return widget


# 成方詞庫
def get_dict_compound(parent, *args):
    import dict_compound

    module = importlib.reload(dict_compound)
    widget = module.DictCompound(parent, *args)

    return widget


# 指示及醫囑
def get_dict_instruction(parent, *args):
    import dict_instruction

    module = importlib.reload(dict_instruction)
    widget = module.DictInstruction(parent, *args)

    return widget


# 醫事機構資料
def get_dict_hosp(parent, *args):
    import dict_hosp

    module = importlib.reload(dict_hosp)
    widget = module.DictHosp(parent, *args)

    return widget


# 通訊錄資料
def get_dict_address_book(parent, *args):
    import dict_address_book

    module = importlib.reload(dict_address_book)
    widget = module.DictAddressBook(parent, *args)

    return widget


# 櫃台結帳-現金收入分析
def get_income_cash_flow(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    regist_type,
    therapist,
    room,
    cashier,
    income_source,
    calculate_by_cashier,
):
    import income_cash_flow

    module = importlib.reload(income_cash_flow)
    widget = module.IncomeCashFlow(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        regist_type,
        therapist,
        room,
        cashier,
        income_source,
        calculate_by_cashier,
    )

    return widget


# 櫃台結帳-交帳明細一覽
def get_income_list(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    regist_type,
    therapist,
    room,
    tableWidget_registration,
    tableWidget_charge,
    income_source,
    income_list_columns,
):
    import income_list

    module = importlib.reload(income_list)
    widget = module.IncomeList(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        regist_type,
        therapist,
        room,
        tableWidget_registration,
        tableWidget_charge,
        income_source,
        income_list_columns,
    )

    return widget


# 櫃台結帳-自費明細表
def get_income_self_prescript(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    regist_type,
    therapist,
    room,
    cashier,
    income_source,
):
    import income_self_prescript

    module = importlib.reload(income_self_prescript)
    widget = module.IncomeSelfPrescript(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        regist_type,
        therapist,
        room,
        cashier,
        income_source,
    )

    return widget


# 櫃台結帳-專案銷售明細
def get_income_project(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    regist_type,
    therapist,
    room,
    cashier,
    income_source,
):
    import income_project

    module = importlib.reload(income_project)
    widget = module.IncomeProject(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        regist_type,
        therapist,
        room,
        cashier,
        income_source,
    )

    return widget


# 櫃台結帳-健保收費明細
def get_income_ins_list(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    regist_type,
    therapist,
    room,
    cashier,
    income_source,
):
    import income_ins_list

    module = importlib.reload(income_ins_list)
    widget = module.IncomeInsList(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        regist_type,
        therapist,
        room,
        cashier,
        income_source,
    )

    return widget


# 申報資料
def get_ins_apply_list(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    period,
    apply_type,
    clinic_id,
    case_type,
    ins_list=None,
):
    import ins_apply_list

    module = importlib.reload(ins_apply_list)
    widget = module.InsApplyList(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        period,
        apply_type,
        clinic_id,
        case_type,
        ins_list,
    )

    return widget


# 健保申報-產生申報資料
def get_ins_apply_generate_file(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    start_date,
    end_date,
    period,
    apply_type,
    clinic_id,
    pre_ins_apply,
):
    import ins_apply_generate_file

    module = importlib.reload(ins_apply_generate_file)
    widget = module.InsApplyGenerateFile(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        start_date,
        end_date,
        period,
        apply_type,
        clinic_id,
        pre_ins_apply,
    )

    return widget


# 健保申報-顯示申報統計
def get_ins_apply_calculated_data(
    parent, database, system_settings, ins_calculated_table
):
    import ins_apply_calculated_data

    module = importlib.reload(ins_apply_calculated_data)
    widget = module.InsApplyCalculatedData(
        parent, database, system_settings, ins_calculated_table
    )

    return widget


# 健保申報-計算申報統計
def get_ins_apply_calculate(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    start_date,
    end_date,
    period,
    apply_type,
    clinic_id,
):
    import ins_apply_calculate

    module = importlib.reload(ins_apply_calculate)
    widget = module.InsApplyCalculate(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        start_date,
        end_date,
        period,
        apply_type,
        clinic_id,
    )

    return widget


# 健保申報-計算合理量
def get_ins_apply_adjust_fee(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    start_date,
    end_date,
    period,
    apply_type,
    clinic_id,
    ins_calculated_table,
):
    import ins_apply_adjust_fee

    module = importlib.reload(ins_apply_adjust_fee)
    widget = module.InsApplyAdjustFee(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        start_date,
        end_date,
        period,
        apply_type,
        clinic_id,
        ins_calculated_table,
    )

    return widget


# 健保申報-申請總表
def get_ins_apply_total_fee(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    start_date,
    end_date,
    period,
    apply_type,
    clinic_id,
    ins_generate_date,
    ins_calculated_table,
):
    import ins_apply_total_fee

    module = importlib.reload(ins_apply_total_fee)
    widget = module.InsApplyTotalFee(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        start_date,
        end_date,
        period,
        apply_type,
        clinic_id,
        ins_generate_date,
        ins_calculated_table,
    )

    return widget


# 健保申報-醫護班表
def get_ins_apply_schedule_table(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    start_date,
    end_date,
    period,
    apply_type,
    clinic_id,
    ins_generate_date,
    ins_calculated_table,
):
    import ins_apply_schedule_table

    module = importlib.reload(ins_apply_schedule_table)
    widget = module.InsApplyScheduleTable(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        start_date,
        end_date,
        period,
        apply_type,
        clinic_id,
        ins_generate_date,
        ins_calculated_table,
    )

    return widget


# 健保申報-申報金額核對
def get_ins_check_apply_fee(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    start_date,
    end_date,
    period,
    apply_type,
    clinic_id,
    ins_generate_date,
    ins_total_fee,
):
    import ins_check_apply_fee

    module = importlib.reload(ins_check_apply_fee)
    widget = module.InsCheckApplyFee(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        start_date,
        end_date,
        period,
        apply_type,
        clinic_id,
        ins_generate_date,
        ins_total_fee,
    )

    return widget


# 健保申報-申報業績
def get_ins_apply_fee_performance(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    doctor,
    start_date,
    end_date,
    period,
    apply_type,
    exclude_c5,
):
    import ins_apply_fee_performance

    module = importlib.reload(ins_apply_fee_performance)
    widget = module.InsApplyFeePerformance(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        doctor,
        start_date,
        end_date,
        period,
        apply_type,
        exclude_c5,
    )

    return widget


# 健保申復-產生XML檔
def get_ins_appeal_xml(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    apply_date,
    period,
    apply_type_code,
    clinic_id,
    apply_upload_date,
):
    import ins_appeal_xml

    module = importlib.reload(ins_appeal_xml)
    widget = module.InsAppealXML(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        apply_date,
        period,
        apply_type_code,
        clinic_id,
        apply_upload_date,
    )

    return widget


# 健保申報-產生XML檔
def get_ins_apply_xml(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    start_date,
    end_date,
    period,
    apply_type,
    clinic_id,
    ins_total_fee,
    pre_ins_apply,
):
    import ins_apply_xml

    module = importlib.reload(ins_apply_xml)
    widget = module.InsApplyXML(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        start_date,
        end_date,
        period,
        apply_type,
        clinic_id,
        ins_total_fee,
        pre_ins_apply,
    )

    return widget


# 健保申報-檢視申報資料
def get_ins_apply_tab(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    period,
    apply_type,
    clinic_id,
    ins_list=None,
):
    import ins_apply_tab

    module = importlib.reload(ins_apply_tab)
    widget = module.InsApplyTab(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        period,
        apply_type,
        clinic_id,
        ins_list,
    )

    return widget


# 健保申報-巡迴醫療
def get_ins_apply_tour(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    start_date,
    end_date,
    period,
    apply_type,
    clinic_id,
):
    import ins_apply_tour

    module = importlib.reload(ins_apply_tour)
    widget = module.InsApplyTour(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        start_date,
        end_date,
        period,
        apply_type,
        clinic_id,
    )

    return widget


# 健保申報-法定傳染病通報隔離-清冠一號補助清冊
def get_ins_apply_infectious(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    period,
    apply_type,
    clinic_id,
):
    import ins_apply_infectious

    module = importlib.reload(ins_apply_infectious)
    widget = module.InsApplyInfectious(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        period,
        apply_type,
        clinic_id,
    )

    return widget


# 健保申報-健保指標
def get_ins_apply_indicator(
    parent, database, system_settings, apply_date, period, apply_type_code, clinic_id
):
    import ins_apply_indicator

    module = importlib.reload(ins_apply_indicator)
    widget = module.InsApplyIndicator(
        parent,
        database,
        system_settings,
        apply_date,
        period,
        apply_type_code,
        clinic_id,
    )

    return widget


# 申報檢查-欄位錯誤檢查
def get_check_errors(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    apply_type,
    start_date,
    end_date,
    check_empty_symptom,
):
    import check_errors

    module = importlib.reload(check_errors)
    widget = module.CheckErrors(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        apply_type,
        start_date,
        end_date,
        check_empty_symptom,
    )

    return widget


# 申報檢查-療程檢查
def get_check_course(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    apply_type,
    check_two_months,
):
    import check_course

    module = importlib.reload(check_course)
    widget = module.CheckCourse(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        apply_type,
        check_two_months,
    )

    return widget


# 申報檢查-卡序檢查
def get_check_card(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    apply_type,
    check_two_months,
):
    import check_card

    module = importlib.reload(check_card)
    widget = module.CheckCard(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        apply_type,
        check_two_months,
    )

    return widget


# 申報檢查-門診次數檢查
def get_check_medical_record_count(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    apply_type,
    treat_limit,
    diag_limit,
    moderate_acupuncture_limit,
    highly_acupuncture_limit,
    moderate_massage_limit,
    highly_massage_limit,
    merge_limit,
    treat_drug_limit,
):
    import check_medical_record_count

    module = importlib.reload(check_medical_record_count)
    widget = module.CheckMedicalRecordCount(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        apply_type,
        treat_limit,
        diag_limit,
        moderate_acupuncture_limit,
        highly_acupuncture_limit,
        moderate_massage_limit,
        highly_massage_limit,
        merge_limit,
        treat_drug_limit,
    )

    return widget


# 申報檢查-用藥天數檢查
def get_check_prescript_days(
    parent,
    database,
    system_settings,
    apply_year,
    apply_month,
    apply_type,
    duplicated_days,
    check_two_months,
):
    import check_prescript_days

    module = importlib.reload(check_prescript_days)
    widget = module.CheckPrescriptDays(
        parent,
        database,
        system_settings,
        apply_year,
        apply_month,
        apply_type,
        duplicated_days,
        check_two_months,
    )

    return widget


# 申報檢查-健保碼檢查
def get_check_ins_drug(
    parent, database, system_settings, apply_year, apply_month, apply_type
):
    import check_ins_drug

    module = importlib.reload(check_ins_drug)
    widget = module.CheckInsDrug(
        parent, database, system_settings, apply_year, apply_month, apply_type
    )

    return widget


# 申報檢查-處置檢查
def get_check_ins_treat(
    parent, database, system_settings, apply_year, apply_month, apply_type
):
    import check_ins_treat

    module = importlib.reload(check_ins_treat)
    widget = module.CheckInsTreat(
        parent, database, system_settings, apply_year, apply_month, apply_type
    )

    return widget


# 健保抽審-電子化抽審
def get_ins_upload_emr(
    parent,
    database,
    system_settings,
    apply_date,
    apply_type,
    period,
    clinic_id,
    apply_upload_date,
):
    import ins_upload_emr

    module = importlib.reload(ins_upload_emr)
    widget = module.InsUploadEMR(
        parent,
        database,
        system_settings,
        apply_date,
        apply_type,
        period,
        clinic_id,
        apply_upload_date,
    )

    return widget


# 病患資料
def get_patient_data(
    parent, database, system_settings, patient_key, call_froim, ic_card
):
    import patient_data

    module = importlib.reload(patient_data)
    widget = module.PatientData(
        parent, database, system_settings, patient_key, call_froim, ic_card
    )

    return widget


# 病患資料-初診照護
def get_patient_new_care(parent, database, system_settings, patient_key):
    import patient_new_care

    module = importlib.reload(patient_new_care)
    widget = module.PatientNewCare(parent, database, system_settings, patient_key)

    return widget


# 病患資料-初診照護


def get_patient_3H(parent, database, system_settings, patient_key):
    import patient_3H

    module = importlib.reload(patient_3H)
    widget = module.Patient3H(parent, database, system_settings, patient_key)

    return widget


# 病患資料-設定
def get_patient_settings(parent, database, system_settings, patient_key):
    import patient_settings

    module = importlib.reload(patient_settings)
    widget = module.PatientSettings(parent, database, system_settings, patient_key)

    return widget


# 自費銷售記錄
def get_purchase_records_list(parent, database, system_settings, dialog, no_zero_bonus):
    import purchase_records_list

    module = importlib.reload(purchase_records_list)
    widget = module.PurchaseRecordList(
        parent, database, system_settings, dialog, no_zero_bonus
    )

    return widget


# 掛號機首頁
def get_pycashier_home(parent, database, system_settings, ic_card):
    from slot_machine import pycashier_home

    module = importlib.reload(pycashier_home)
    widget = module.PyCashierHome(parent, database, system_settings, ic_card)

    return widget


# 掛號機掛號報到
def get_pycashier_registration(parent, database, system_settings, ic_card):
    from slot_machine import pycashier_registration

    module = importlib.reload(pycashier_registration)
    widget = module.PyCashierRegistration(parent, database, system_settings, ic_card)

    return widget


# 掛號機繳費
def get_pycashier_payment(parent, database, system_settings, ic_card, coinsys):
    from slot_machine import pycashier_payment

    module = importlib.reload(pycashier_payment)
    widget = module.PyCashierPayment(
        parent, database, system_settings, ic_card, coinsys
    )

    return widget


# 掛號機繳費完成
def get_pycashier_completed(parent, database, system_settings, ic_card):
    from slot_machine import pycashier_completed

    module = importlib.reload(pycashier_completed)
    widget = module.PyCashierCompleted(parent, database, system_settings, ic_card)

    return widget


# 掛號機首頁
def get_pycashier2_home(parent, database, system_settings, ic_card):
    from payment_machine import pycashier_home

    module = importlib.reload(pycashier_home)
    widget = module.PyCashierHome(parent, database, system_settings, ic_card)

    return widget


# 掛號機掛號報到
def get_pycashier2_registration(parent, database, system_settings, ic_card):
    from payment_machine import pycashier_registration

    module = importlib.reload(pycashier_registration)
    widget = module.PyCashierRegistration(parent, database, system_settings, ic_card)

    return widget


# 掛號機繳費
def get_pycashier2_payment(parent, database, system_settings, ic_card, coinsys):
    from payment_machine import pycashier_payment

    module = importlib.reload(pycashier_payment)
    widget = module.PyCashierPayment(
        parent, database, system_settings, ic_card, coinsys
    )

    return widget


# 掛號機繳費完成
def get_pycashier2_completed(parent, database, system_settings, ic_card):
    from payment_machine import pycashier_completed

    module = importlib.reload(pycashier_completed)
    widget = module.PyCashierCompleted(parent, database, system_settings, ic_card)

    return widget


# 百會掛號機首頁
def get_kiosk_home(parent, database, system_settings, ic_card):
    from kiosk import kiosk_home

    module = importlib.reload(kiosk_home)
    widget = module.KioskHome(parent, database, system_settings, ic_card)

    return widget


# 掛號機掛號報到
def get_kiosk_registration(parent, database, system_settings, ic_card):
    from kiosk import kiosk_registration

    module = importlib.reload(kiosk_registration)
    widget = module.KioskRegistration(parent, database, system_settings, ic_card)

    return widget


# 掛號機繳費
def get_kiosk_payment(parent, database, system_settings, ic_card):
    from kiosk import kiosk_payment

    module = importlib.reload(kiosk_payment)
    widget = module.KioskPayment(parent, database, system_settings, ic_card)

    return widget


# 掛號機繳費完成
def get_kiosk_completed(parent, database, system_settings, ic_card):
    from kiosk import kiosk_completed

    module = importlib.reload(kiosk_completed)
    widget = module.KioskCompleted(parent, database, system_settings, ic_card)

    return widget


# 資料回復
def get_restore_medical_records(parent, database, system_settings):
    import restore_medical_records

    module = importlib.reload(restore_medical_records)
    widget = module.RestoreMedicalRecords(parent, database, system_settings)

    return widget


# 分院日報表-人數統計
def get_statistics_branch_daily_person(
    parent, database, system_settings, database_list, year, month, day
):
    import statistics_branch_daily_person

    module = importlib.reload(statistics_branch_daily_person)
    widget = module.StatisticsBranchDailyPerson(
        parent, database, system_settings, database_list, year, month, day
    )

    return widget


# 分院日報表-門診金額統計
def get_statistics_branch_daily_income(
    parent, database, system_settings, database_list, year, month, day
):
    import statistics_branch_daily_income

    module = importlib.reload(statistics_branch_daily_income)
    widget = module.StatisticsBranchDailyIncome(
        parent, database, system_settings, database_list, year, month, day
    )

    return widget


# 分院專案統計
def get_statistics_branch_project_sales(
    parent,
    database,
    database_list,
    system_settings,
    start_date,
    end_date,
    ins_type,
    doctor,
    project_name,
):
    import statistics_branch_project_sales

    module = importlib.reload(statistics_branch_project_sales)
    widget = module.StatisticsBranchProjectSales(
        parent,
        database,
        database_list,
        system_settings,
        start_date,
        end_date,
        ins_type,
        doctor,
        project_name,
    )

    return widget


# 自費銷售抽成金額總表
def get_statistics_commission_amount(parent, database, system_settings, year, month):
    import statistics_commission_amount

    module = importlib.reload(statistics_commission_amount)
    widget = module.StatisticsCommissionAmount(
        parent, database, system_settings, year, month
    )

    return widget


# 日報表-人數統計
def get_statistics_daily_person(parent, database, system_settings, year, month, day):
    import statistics_daily_person

    module = importlib.reload(statistics_daily_person)
    widget = module.StatisticsDailyPerson(
        parent, database, system_settings, year, month, day
    )

    return widget


# 綜合業績報表-人數統計
def get_statistics_multiple_performance_week_person(
    parent, database, system_settings, year, month
):
    import statistics_multiple_performance_week_person

    module = importlib.reload(statistics_multiple_performance_week_person)
    widget = module.StatisticsMultiplePerformanceWeekPerson(
        parent, database, system_settings, year, month
    )

    return widget


# 綜合業績報表-週收入統計
def get_statistics_multiple_performance_week_income(
    parent, database, system_settings, year, month
):
    import statistics_multiple_performance_week_income

    module = importlib.reload(statistics_multiple_performance_week_income)
    widget = module.StatisticsMultiplePerformanceWeekIncome(
        parent, database, system_settings, year, month
    )

    return widget


# 綜合業績報表-週專案統計
def get_statistics_multiple_performance_week_project(
    parent, database, system_settings, year, month
):
    import statistics_multiple_performance_week_project

    module = importlib.reload(statistics_multiple_performance_week_project)
    widget = module.StatisticsMultiplePerformanceWeekProject(
        parent, database, system_settings, year, month
    )

    return widget


# 綜合業績報表-週醫師統計
def get_statistics_multiple_performance_week_doctor(
    parent, database, system_settings, year, month
):
    import statistics_multiple_performance_week_doctor

    module = importlib.reload(statistics_multiple_performance_week_doctor)
    widget = module.StatisticsMultiplePerformanceWeekDoctor(
        parent, database, system_settings, year, month
    )

    return widget


# 醫師統計-醫師月報表
def get_statistics_doctor_monthly_count(
    parent, database, system_settings, year, month, doctor
):
    import statistics_doctor_monthly_count

    module = importlib.reload(statistics_doctor_monthly_count)
    widget = module.StatisticsDoctorMonthlyCount(
        parent, database, system_settings, year, month, doctor
    )

    return widget


# 醫師統計-醫師人數月報表
def get_statistics_doctor_monthly_person_count(
    parent, database, system_settings, year, month, doctor
):
    import statistics_doctor_monthly_person_count

    module = importlib.reload(statistics_doctor_monthly_person_count)
    widget = module.StatisticsDoctorMonthlyPersonCount(
        parent, database, system_settings, year, month, doctor
    )

    return widget


# 醫師統計-醫師月報表-收入統計
def get_statistics_doctor_monthly_income(
    parent, database, system_settings, year, month, doctor
):
    import statistics_doctor_monthly_income

    module = importlib.reload(statistics_doctor_monthly_income)
    widget = module.StatisticsDoctorMonthlyIncome(
        parent, database, system_settings, year, month, doctor
    )

    return widget


# 醫師銷售業績統計-自費產品銷售抽成統計
def get_statistics_doctor_commission(
    parent, database, system_settings, start_date, end_date, period, ins_type, doctor
):
    import statistics_doctor_commission

    module = importlib.reload(statistics_doctor_commission)
    widget = module.StatisticsDoctorCommission(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        ins_type,
        doctor,
    )

    return widget


# 醫師銷售業績統計-專案產品銷售抽成統計
def get_statistics_doctor_project_sale(
    parent, database, system_settings, start_date, end_date, period, ins_type, doctor
):
    import statistics_doctor_project_sale

    module = importlib.reload(statistics_doctor_project_sale)
    widget = module.StatisticsDoctorProjectSale(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        ins_type,
        doctor,
    )

    return widget


# 醫師統計-門診人數統計
def get_statistics_doctor_amount_income(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    ins_type,
    doctor,
    option,
    weekday_list,
):
    import statistics_doctor_amount_income

    module = importlib.reload(statistics_doctor_amount_income)
    widget = module.StatisticsDoctorAmountIncome(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        ins_type,
        doctor,
        option,
        weekday_list,
    )

    return widget


# 醫師統計-門診人數統計
def get_statistics_doctor_amount_salary(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    ins_type,
    doctor,
    option,
    weekday_list,
):
    import statistics_doctor_amount_salary

    module = importlib.reload(statistics_doctor_amount_salary)
    widget = module.StatisticsDoctorAmountSalary(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        ins_type,
        doctor,
        option,
        weekday_list,
    )

    return widget


# 醫師統計-醫師處方類別統計
def get_statistics_doctor_medicine_percent(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    ins_type,
    doctor,
    option,
    weekday_list,
):
    import statistics_doctor_medicine_percent

    module = importlib.reload(statistics_doctor_medicine_percent)
    widget = module.StatisticsDoctorMedicinePercent(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        ins_type,
        doctor,
        option,
        weekday_list,
    )

    return widget


# 醫師統計-門診人數統計
def get_statistics_doctor_count(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    ins_type,
    doctor,
    option,
    weekday_list,
):
    import statistics_doctor_count

    module = importlib.reload(statistics_doctor_count)
    widget = module.StatisticsDoctorCount(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        ins_type,
        doctor,
        option,
        weekday_list,
    )

    return widget


# 醫師統計-門診收入統計
def get_statistics_doctor_income(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    ins_type,
    doctor,
    option,
    weekday_list,
):
    import statistics_doctor_income

    module = importlib.reload(statistics_doctor_income)
    widget = module.StatisticsDoctorIncome(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        ins_type,
        doctor,
        option,
        weekday_list,
    )

    return widget


# 醫師統計-自費銷售統計
def get_statistics_doctor_sale(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    doctor,
    option,
    weekday_list,
):
    import statistics_doctor_sale

    module = importlib.reload(statistics_doctor_sale)
    widget = module.StatisticsDoctorSale(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        doctor,
        option,
        weekday_list,
    )

    return widget


# 醫師統計-初複診統計
def get_statistics_doctor_visit_count(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    doctor,
    option,
    weekday_list,
):
    import statistics_doctor_visit_count

    module = importlib.reload(statistics_doctor_visit_count)
    widget = module.StatisticsDoctorVisitCount(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        doctor,
        option,
        weekday_list,
    )

    return widget


# 醫師統計-指定醫師初複診統計
def get_statistics_designated_doctor_visit_count(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    doctor,
    option,
    weekday_list,
):
    import statistics_designated_doctor_visit_count

    module = importlib.reload(statistics_designated_doctor_visit_count)
    widget = module.StatisticsDesignatedDoctorVisitCount(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        doctor,
        option,
        weekday_list,
    )

    return widget


# 醫師統計-門診收入總覽
def get_statistics_doctor_summary(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    doctor,
    option,
    weekday_list,
):
    import statistics_doctor_summary

    module = importlib.reload(statistics_doctor_summary)
    widget = module.StatisticsDoctorSummary(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        doctor,
        option,
        weekday_list,
    )

    return widget


# 醫師統計-醫師業績
def get_statistics_doctor_achievement(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    doctor,
    option,
    weekday_list,
):
    import statistics_doctor_achievement

    module = importlib.reload(statistics_doctor_achievement)
    widget = module.StatisticsDoctorAchievement(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        doctor,
        option,
        weekday_list,
    )

    return widget


# 醫師統計-醫師業績
def get_statistics_ins_performance_doctor(
    parent, database, system_settings, start_date, end_date, doctor, exclude_c5
):
    import statistics_ins_performance_doctor

    module = importlib.reload(statistics_ins_performance_doctor)
    widget = module.StatisticsInsPerformanceDoctor(
        parent, database, system_settings, start_date, end_date, doctor, exclude_c5
    )

    return widget


# 健保門診優惠統計-掛號費優待統計
def get_statistics_ins_discount_regist_fee(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    doctor,
    first_course,
    only_discount,
    basic_regist_fee_discount,
):
    import statistics_ins_discount_regist_fee

    module = importlib.reload(statistics_ins_discount_regist_fee)
    widget = module.StatisticsInsDiscountRegistFee(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        doctor,
        first_course,
        only_discount,
        basic_regist_fee_discount,
    )

    return widget


# 健保門診優惠統計-免收門診負擔統計
def get_statistics_ins_discount_diag_share_fee(
    parent, database, system_settings, start_date, end_date, doctor, first_course
):
    import statistics_ins_discount_diag_share_fee

    module = importlib.reload(statistics_ins_discount_diag_share_fee)
    widget = module.StatisticsInsDiscountDiagShareFee(
        parent, database, system_settings, start_date, end_date, doctor, first_course
    )

    return widget


# 健保門診優惠統計-免收藥品負擔統計
def get_statistics_ins_discount_drug_share_fee(
    parent, database, system_settings, start_date, end_date, doctor
):
    import statistics_ins_discount_drug_share_fee

    module = importlib.reload(statistics_ins_discount_drug_share_fee)
    widget = module.StatisticsInsDiscountDrugShareFee(
        parent, database, system_settings, start_date, end_date, doctor
    )

    return widget


# 健保業績-依病歷
def get_statistics_ins_performance_medical_record(
    parent, database, system_settings, start_date, end_date, doctor
):
    import statistics_ins_performance_medical_record

    module = importlib.reload(statistics_ins_performance_medical_record)
    widget = module.StatisticsInsPerformanceMedicalRecord(
        parent, database, system_settings, start_date, end_date, doctor
    )

    return widget


# 孕產照護報表-助孕照護-女
def get_statistics_ins_pregnant_female(
    parent, database, system_settings, start_date, end_date
):
    import statistics_ins_pregnant_female

    module = importlib.reload(statistics_ins_pregnant_female)
    widget = module.StatisticsInsPregnantFemale(
        parent, database, system_settings, start_date, end_date
    )

    return widget


# 孕產照護報表-助孕照護-男
def get_statistics_ins_pregnant_male(
    parent, database, system_settings, start_date, end_date
):
    import statistics_ins_pregnant_male

    module = importlib.reload(statistics_ins_pregnant_male)
    widget = module.StatisticsInsPregnantMale(
        parent, database, system_settings, start_date, end_date
    )

    return widget


# 孕產照護報表-保胎照護
def get_statistics_ins_pregnant_keep_baby(
    parent, database, system_settings, start_date, end_date
):
    import statistics_ins_pregnant_keep_baby

    module = importlib.reload(statistics_ins_pregnant_keep_baby)
    widget = module.StatisticsInsPregnantKeepBaby(
        parent, database, system_settings, start_date, end_date
    )

    return widget


# 推拿師統計-推拿人數統計
def get_statistics_massager_count(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    ins_type,
    massager,
    only_traditional_massage,
):
    import statistics_massager_count

    module = importlib.reload(statistics_massager_count)
    widget = module.StatisticsMassagerCount(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        ins_type,
        massager,
        only_traditional_massage,
    )

    return widget


# 推拿師統計-推拿人數統計總表
def get_statistics_massager_summary(
    parent, database, system_settings, start_date, end_date, only_traditional_massage
):
    import statistics_massager_summary

    module = importlib.reload(statistics_massager_summary)
    widget = module.StatisticsMassagerSummary(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        only_traditional_massage,
    )

    return widget


# 推拿師統計-推拿收入統計
def get_statistics_massager_income(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    ins_type,
    massager,
    only_traditional_massage,
):
    import statistics_massager_income

    module = importlib.reload(statistics_massager_income)
    widget = module.StatisticsMassagerIncome(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        ins_type,
        massager,
        only_traditional_massage,
    )

    return widget


# 推拿師統計-推拿業績明細
def get_statistics_massager_list(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    massager,
    only_traditional_massage,
):
    import statistics_massager_list

    module = importlib.reload(statistics_massager_list)
    widget = module.StatisticsMassagerList(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        massager,
        only_traditional_massage,
    )

    return widget


# 病歷統計-疾病排行
def get_statistics_medical_record_disease_rank(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    ins_type,
    doctor,
    option,
    weekday_list,
):
    import statistics_medical_record_disease_rank

    module = importlib.reload(statistics_medical_record_disease_rank)
    widget = module.StatisticsMedicalRecordDiseaseRank(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        ins_type,
        doctor,
        option,
        weekday_list,
    )

    return widget


# 病歷統計-看診時間統計
def get_statistics_medical_record_diag_time_length(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    ins_type,
    doctor,
    weekday_list,
):
    import statistics_medical_record_diag_time_length

    module = importlib.reload(statistics_medical_record_diag_time_length)
    widget = module.StatisticsMedicalRecordDiagTimeLength(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        ins_type,
        doctor,
        weekday_list,
    )

    return widget


# 用藥統計
def get_statistics_medicine_sales(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    ins_type,
    doctor,
    medicine_type,
):
    import statistics_medicine_sales

    module = importlib.reload(statistics_medicine_sales)
    widget = module.StatisticsMedicineSales(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        ins_type,
        doctor,
        medicine_type,
    )

    return widget


# 醫師未回診率統計
def get_statistics_no_return_rate_doctor(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    no_return_start_date,
    no_return_end_date,
    ins_type,
    treat_type,
    visit,
    doctor,
):
    import statistics_no_return_rate_doctor

    module = importlib.reload(statistics_no_return_rate_doctor)
    widget = module.StatisticsNoReturnRateDoctor(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        no_return_start_date,
        no_return_end_date,
        ins_type,
        treat_type,
        visit,
        doctor,
    )

    return widget


# 照護機構院民資料報表
def get_statistics_nursing_home_data(
    parent, database, system_settings, year, month, doctor, nursing_home
):
    import statistics_nursing_home_data

    module = importlib.reload(statistics_nursing_home_data)
    widget = module.StatisticsNursingHomeData(
        parent, database, system_settings, year, month, doctor, nursing_home
    )

    return widget


# 照護機構院民資料日報表
def get_statistics_nursing_home_daily_data(
    parent, database, system_settings, year, month, doctor, nursing_home
):
    import statistics_nursing_home_daily_data

    module = importlib.reload(statistics_nursing_home_daily_data)
    widget = module.StatisticsNursingHomeDailyData(
        parent, database, system_settings, year, month, doctor, nursing_home
    )

    return widget


# 醫師診數統計
def get_statistics_doctor_period_count(
    parent, database, system_settings, start_date, end_date, ins_type, period, doctor
):
    import statistics_doctor_period_count

    module = importlib.reload(statistics_doctor_period_count)
    widget = module.StatisticsDoctorPeriodCount(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        ins_type,
        period,
        doctor,
    )

    return widget


# 回診率統計-醫師回診率統計
def get_statistics_return_rate_doctor(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    ins_type,
    treat_type,
    visit,
    doctor,
    doctor_return_days,
    return_times,
):

    import statistics_return_rate_doctor

    module = importlib.reload(statistics_return_rate_doctor)
    widget = module.StatisticsReturnRateDoctor(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        ins_type,
        treat_type,
        visit,
        doctor,
        doctor_return_days,
        return_times,
    )

    return widget


# 回診率統計-推拿師父回診率統計
def get_statistics_return_rate_massager(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    ins_type,
    treat_type,
    visit,
    massager,
    massager_return_days,
    return_times,
):
    import statistics_return_rate_massager

    module = importlib.reload(statistics_return_rate_massager)
    widget = module.StatisticsReturnRateMassager(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        ins_type,
        treat_type,
        visit,
        massager,
        massager_return_days,
        return_times,
    )

    return widget


# 醫師自費銷售金額總表
def get_statistics_doctor_sale_summary(
    parent, database, system_settings, start_date, end_date, ins_type, doctor
):
    import statistics_doctor_sale_summary

    module = importlib.reload(statistics_doctor_sale_summary)
    widget = module.StatisticsDoctorSaleSummary(
        parent, database, system_settings, start_date, end_date, ins_type, doctor
    )

    return widget


# 候診叫號系統
def get_pybulletin3(parent, socket_server, voice_server):
    import pybulletin3

    module = importlib.reload(pybulletin3)
    tab_widget = module.PyBulletin3(parent, socket_server, voice_server)

    return tab_widget


# 進貨單記錄
def get_stock_in_list(parent, *args):
    import stock_in_list

    module = importlib.reload(stock_in_list)
    widget = module.StockInList(parent, *args)

    return widget


# 進貨單資料
def get_stock_in_data(parent, *args):
    import stock_in_data

    module = importlib.reload(stock_in_data)
    widget = module.StockInData(parent, *args)

    return widget


# 出貨單記錄
def get_stock_out_list(parent, *args):
    import stock_out_list

    module = importlib.reload(stock_out_list)
    widget = module.StockOutList(parent, *args)

    return widget


# 出貨單資料
def get_stock_out_data(parent, *args):
    import stock_out_data

    module = importlib.reload(stock_out_data)
    widget = module.StockOutData(parent, *args)

    return widget


# 業績成長統計-月統計
def get_statistics_growth_month(parent, database, system_settings, year, month):
    import statistics_growth_month

    module = importlib.reload(statistics_growth_month)
    widget = module.StatisticsGrowthMonth(
        parent, database, system_settings, year, month
    )

    return widget


# 業績成長統計-年統計
def get_statistics_growth_year(parent, database, system_settings, year, month):
    import statistics_growth_year

    module = importlib.reload(statistics_growth_year)
    widget = module.StatisticsGrowthYear(parent, database, system_settings, year, month)

    return widget


# 業績成長統計-年收入統計
def get_statistics_growth_income(parent, database, system_settings, year, month):
    import statistics_growth_income

    module = importlib.reload(statistics_growth_income)
    widget = module.StatisticsGrowthIncome(
        parent, database, system_settings, year, month
    )

    return widget


# 物理治療預約表
def get_physiotherapy_schedule(parent, database, system_settings):
    import physiotherapy_schedule

    module = importlib.reload(physiotherapy_schedule)
    widget = module.PhysiotherapySchedule(parent, database, system_settings)

    return widget


# 物理治療收入統計
def get_physiotherapy_income(parent, database, system_settings):
    import physiotherapy_income

    module = importlib.reload(physiotherapy_income)
    widget = module.PhysiotherapyIncome(parent, database, system_settings)

    return widget


# 醫師統計-門診人數統計
def get_statistics_stamp_duty_list(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    ins_type,
    doctor,
    option,
    weekday_list,
    under_250,
):
    import statistics_stamp_duty_list

    module = importlib.reload(statistics_stamp_duty_list)
    widget = module.StatisticsStampDutyList(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        ins_type,
        doctor,
        option,
        weekday_list,
        under_250,
    )

    return widget


# 統計表-執行業務所得
def get_statistics_business_income_list(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    ins_type,
    doctor,
    option,
    weekday_list,
):
    import statistics_business_income_list

    module = importlib.reload(statistics_business_income_list)
    widget = module.StatisticsBusinessIncomeList(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        ins_type,
        doctor,
        option,
        weekday_list,
    )

    return widget


# 悅兒掛號機首頁
def get_joytcm_kiosk_home(parent, database, system_settings, ic_card):
    from joytcm_kiosk import kiosk_home

    module = importlib.reload(kiosk_home)
    widget = module.KioskHome(parent, database, system_settings, ic_card)

    return widget


# 掛號機掛號報到
def get_joytcm_kiosk_registration(parent, database, system_settings, ic_card):
    from joytcm_kiosk import kiosk_registration

    module = importlib.reload(kiosk_registration)
    widget = module.KioskRegistration(parent, database, system_settings, ic_card)

    return widget


# 掛號機批價繳費
def get_joytcm_kiosk_payment(parent, database, system_settings, ic_card):
    from joytcm_kiosk import kiosk_payment

    module = importlib.reload(kiosk_payment)
    widget = module.KioskPayment(parent, database, system_settings, ic_card)

    return widget


# 掛號機取消預約掛號
def get_joytcm_kiosk_cancel_reservation(parent, database, system_settings, ic_card):
    from joytcm_kiosk import kiosk_cancel_reservation

    module = importlib.reload(kiosk_cancel_reservation)
    widget = module.KioskCancelReservation(parent, database, system_settings, ic_card)

    return widget


###############################################################################################################
# 掛號機首頁
def get_kiosk1_home(parent, database, system_settings, ic_card):
    from kiosk1 import kiosk_home

    module = importlib.reload(kiosk_home)
    widget = module.KioskHome(parent, database, system_settings, ic_card)

    return widget


# 掛號機掛號報到
def get_kiosk1_registration(parent, database, system_settings, ic_card):
    from kiosk1 import kiosk_registration

    module = importlib.reload(kiosk_registration)
    widget = module.KioskRegistration(parent, database, system_settings, ic_card)

    return widget


# 掛號機批價繳費
def get_kiosk1_payment(parent, database, system_settings, ic_card):
    from kiosk1 import kiosk_payment

    module = importlib.reload(kiosk_payment)
    widget = module.KioskPayment(parent, database, system_settings, ic_card)

    return widget


# 掛號機繳費完成
def get_kiosk1_completed(parent, database, system_settings):
    from kiosk1 import kiosk_completed

    module = importlib.reload(kiosk_completed)
    widget = module.KioskCompleted(parent, database, system_settings)

    return widget


# 自費抽成統計-銷售抽成統計
def get_statistics_commission_sale(
    parent,
    database,
    system_settings,
    start_date,
    end_date,
    period,
    seller,
    option,
    weekday_list,
):
    import statistics_commission_sale

    module = importlib.reload(statistics_commission_sale)
    widget = module.StatisticsCommissionSale(
        parent,
        database,
        system_settings,
        start_date,
        end_date,
        period,
        seller,
        option,
        weekday_list,
    )

    return widget


# 掛號機首頁
def get_pycashier3_home(parent, database, system_settings, ic_card):
    from slot_machine2 import pycashier_home

    module = importlib.reload(pycashier_home)
    widget = module.PyCashierHome(parent, database, system_settings, ic_card)

    return widget


# 掛號機掛號報到
def get_pycashier3_registration(parent, database, system_settings, ic_card):
    from slot_machine2 import pycashier_registration

    module = importlib.reload(pycashier_registration)
    widget = module.PyCashierRegistration(parent, database, system_settings, ic_card)

    return widget


# 掛號機繳費
def get_pycashier3_payment(parent, database, system_settings, ic_card, coinsys):
    from slot_machine2 import pycashier_payment

    module = importlib.reload(pycashier_payment)
    widget = module.PyCashierPayment(
        parent, database, system_settings, ic_card, coinsys
    )

    return widget


# 掛號機繳費完成
def get_pycashier3_completed(parent, database, system_settings, ic_card):
    from slot_machine2 import pycashier_completed

    module = importlib.reload(pycashier_completed)
    widget = module.PyCashierCompleted(parent, database, system_settings, ic_card)

    return widget


###############################################################################################################
# 掛號機首頁
def get_kiosk2_home(parent, database, system_settings):
    from kiosk2 import kiosk_home

    module = importlib.reload(kiosk_home)
    widget = module.KioskHome(parent, database, system_settings)

    return widget


# 掛號機掛號報到
def get_kiosk2_identity(parent, database, system_settings):
    from kiosk2 import kiosk_identity

    module = importlib.reload(kiosk_identity)
    widget = module.KioskIdentity(parent, database, system_settings)

    return widget


# 掛號機掛號報到
def get_kiosk2_registration(parent, database, system_settings):
    from kiosk2 import kiosk_registration

    module = importlib.reload(kiosk_registration)
    widget = module.KioskRegistration(parent, database, system_settings)

    return widget


# 掛號機批價繳費
def get_kiosk2_payment(parent, database, system_settings):
    from kiosk2 import kiosk_payment

    module = importlib.reload(kiosk_payment)
    widget = module.KioskPayment(parent, database, system_settings)

    return widget


# 掛號機繳費完成
def get_kiosk2_completed(parent, database, system_settings):
    from kiosk2 import kiosk_completed

    module = importlib.reload(kiosk_completed)
    widget = module.KioskCompleted(parent, database, system_settings)

    return widget


# 掛號機批價繳費
def get_kiosk2_pay(parent, database, system_settings):
    from kiosk2 import kiosk_pay

    module = importlib.reload(kiosk_pay)
    widget = module.KioskPay(parent, database, system_settings)

    return widget
