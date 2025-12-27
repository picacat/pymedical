
# 03. 病歷資料檔    100.07.01
# Relative to 基本資料檔, 病歷處方檔, 欠卡檔, 欠款檔

CREATE TABLE IF NOT EXISTS Cases
(
    CaseKey	    INT AUTO_INCREMENT NOT NULL,	# 病歷序號
    PatientKey	INT NOT NULL,		# 系統號   (初診預約-999,999; 參考病歷-999,998; 自購藥-999,997)
    Name	      VARCHAR(20),		# 病患姓名 (Option: 有名填名, 無名填自購藥)
    CaseDate    DATETIME NOT NULL,  # 就醫日期
    StartDate   DATETIME,			  # 開始日期

    Visit 	    VARCHAR(04),	  # 初診, 複診
    RegistType  VARCHAR(10),    # 掛號類別: 一般(直接門診), 預約, 撤掛, 自購藥
    TreatType	  VARCHAR(10),    # 就醫類別: 一般(內科門診),     (原 RegistType)
                #   針灸治療, 針灸給藥, 傷科治療, 傷科給藥, 脫臼整復, 脫臼給藥,
                #   電針治療, 電針給藥, 複雜針灸, 複針給藥, 複雜傷科, 複傷給藥, 複雜骨折(複骨B57)

                # 純自費    : 民俗調理,
                # 健保      : 一般+民俗(內科), 針灸+民俗, 針藥+民俗, 傷科+民俗, 傷藥+民俗
                #             電針+民俗, 電藥+民俗

                # 巡迴醫療  : 巡迴偏遠, 巡迴山地, 巡迴離島
                # 代領藥    : 長期臥床(J1), 遠洋漁業(J2), 遠洋貨船(J3) 104.12.24 逢安
                # 其他      : 特殊, 外治, 拿藥, 同上, 自購藥(決定病歷Essential), 開立證明
                # 慢箋 (慢性病連續處方箋) 17.10.30

                # 特定疾病加強照護SpecialCare: 小兒氣喘, 小兒腦麻, 腦血管疾病, 孕產照護 (Pregnant)
                #   小兒氣喘(30-C9), 小兒腦麻 (30-C0 小兒腦性麻痹)  102.03.15 陳立德
                #   腦血管疾病(CA 腦血管疾病及顱腦損傷)         103.01.01 懷恩堂
                #   助孕照護, 保胎照護(J9, CaseType:22)         104.01.09
                #   乳癌照護(JE), 肝癌照護(JF, CaseType:22)     105.03.11
                #   兒童鼻炎(22-JG, CaseType)                   16.09.01 rhinitis

    Injury	    VARCHAR(08),	  # 給付類別:1-職業傷害, 2-職業病,
		                            #          3-普通傷害, 4-普通疾病, 8-天然災害(98.08.20 88水災)
    SpecialCode VARCHAR(02),	  # 專案類別:專案代碼(from 病名檔), 空白
    Share 	    VARCHAR(08),	  # 負擔類別:中醫:S/R10,  基層醫療(S10/S20),
	              # 001-重大傷病, 003-低收入戶, 004-榮民,     006-職業傷害, 007-山地離島,
                # 009-其他,     009-天然災害 (98.08.20 88水災),
                # 801-巡迴醫療, 98.03.04 學傳 堅持 007-山地離島
                # 901-油症,     902-三歲兒童, 903-新生兒,
		            # 006-職業病, 職病初診, 職病複診, 職業傷害, 職傷初診, 職傷複診
                # 906-替代役男 101.12.05

    InsType	    VARCHAR(04),	  # 保險類別: 健保, 自費(自購藥),
                                #           民俗 (100.02.17 明醫, Wait不存, 不經醫師)
    ApplyType	  VARCHAR(08),	  # 申報類別: 申報, 補報, 不申報
                                #           調劑不報 (醫師自行調劑, 屬於申報), 空白(屬於申報)
    Card        VARCHAR(06),	  # 健保卡序: 欠卡, 職業傷害: 061-069,
                                #           內科 or 首次 填異常卡序
    Continuance	INT,            # 療程次序: 01-06
    XCard       VARCHAR(06),	  # 異常卡序: 療程用 2-6, 職傷/巡迴醫療專用
                                # 已取得就醫序號 (內科 or 首次 or 療程)
    Period 	    VARCHAR(04),    # 班別: 早班, 午班, 晚班
    Room	      INT DEFAULT 1 NOT NULL,     # 診療室:01 - 10   自購藥設定為 9診
    MassageRoom	INT,		        # 理療室:11 - 20

    RegistNo    INT,	          # 就診號: 000-999 (每日) (含灌水號)
    MassageNo	  INT,		        # 理療號: 000-999 (每日)
    ChargeNo	  INT,		        # 收費號: 000-999 (每日) 病歷登錄時編號
    DrugNo	    INT,		        # 領藥號: 000-999 (每日) 病歷登錄時編號
    YearlyNo1	  INT,	          # 診單編號1: 000000-999999(每年) 掛號時編號 (掛號費+診負)
    YearlyNo2	  INT,	          # 診單編號2: 000000-999999(每年) 病歷登錄時編號(藥負 + 自費)
                                #                                龍潭敏盛才有
    YearlyNo3	  INT,	          # 診單編號3:000000-999999(每年)
                                # 92.10.06 龍潭敏盛 還卡時編號 (還卡費)
                                # 100.02.17 明醫: 民俗 對應 CaseKey 雙向

    Doctor	    VARCHAR(10),	  # 醫師姓名 (自購: 售藥者, 指定病患)
    Pharmacist	VARCHAR(10),	  # 藥師姓名
    Massager	  VARCHAR(10),	  # 理療員姓名
    Register	  VARCHAR(10),	  # 掛號員姓名
    Cashier	    VARCHAR(10),	  # 收費員姓名, 自購藥-售藥者, 不指定病患

#   診前檢查 (病理檢查)         Pathologic  void 102.07.01
#    Height	    Decimal(10, 2),	# 身高  cm
#    Weight	      Decimal(10, 2),	# 體重  kg    show BMI
#    Temperature  Decimal(10, 2), # 體溫  Celsuis
#    HeartBeat    INT,          # 心跳
#    BPHigh	      INT,		      # 收縮壓
#    BPLow 	      INT,		      # 舒張壓
#    GlucoseAC    INT,		      # 血糖 (飯前) 102.07.01
#    GlucosePC    INT,		      # 血糖 (飯後)

#   醫師診療
    Symptom	    BLOB,	          # 主訴,症狀
    Tongue	    BLOB,           # 舌診
    Pulse 	    BLOB,           # 脈象
    Equipment   VARCHAR(10),	  # 腦疾 / 腦疾後遺症
                # 腦疾: NNNNNNNN or YYYYYYYY
                #   1-護理衛教費   2-營養指導費 3-舌診儀 4-脈診儀 5-微循環儀
                #   6-紅外線熱象儀 7-生心理評估 8-SF-36生活品質評估 (不給付)
                # 腦疾後遺症: NNN or YYY    Sequela
                #   1-護理衛教費  2-生心理評估 3-同時執行針灸與傷外科治療(不管CheckBox/Treatment)

                # 特定疾病加強照護:                                             void 104.10.31
                # 102.03.20 小兒氣喘 NN or YY   Pant
                #   1-含氣霧吸入處置費  2-不含氣霧吸入處置費
                # 102.03.20 小兒腦麻 NN or YY   Palsy
                #   1-含藥浴吸入處置費  2-不含藥浴吸入處置費
                # 103.01.01 腦血管疾病 NN or YY   Cerebrum
                #   1-治療處置一至三次  2-治療處置四次(含)以上
                # 特定疾病加強照護: 小兒氣喘, 小兒腦麻, 腦血管疾病 於 Treatment 設定  104.10.31

    DiseaseCode1    VARCHAR(10),	# 病名碼1 ICD9 / ICD10 5->10 103.09.10
                                  #   104.01.01 用 ICD10 VARCHAR 5 -> 10
    DiseaseName1    VARCHAR(40),	# 病名1   重要名稱
    DiseaseCode2    VARCHAR(10),	# 病名碼2 ICD Code
    DiseaseName2    VARCHAR(40),	# 病名2   重要名稱
    DiseaseCode3    VARCHAR(10),	# 病名碼3 ICD Code
    DiseaseName3    VARCHAR(40),	# 病名3   重要名稱
    Distincts       VARCHAR(40),	# 辨證    103.04.18 見安: 病名4
    Cure		        VARCHAR(40),	# 治則    103.04.18 見安: 病名4-重要名稱

    Remark	        BLOB,         # 備註

    Package1        INT,	        # 給藥包數; 健保
    PresDays1	      INT,		      # 給藥日份 (帖數); 處方即一天量/一帖量
    Instruction1    VARCHAR(40),	# 用藥指示: 飯後,飯前,先煎,後下,沖服,包煎
    Package2	      INT,          # 自費 1
    PresDays2	      INT,
    Instruction2    VARCHAR(40),
    Package3	      INT,          # 自費 2
    PresDays3	      INT,
    Instruction3    VARCHAR(40),
    Package4	      INT,          # 自費 3
    PresDays4	      INT,
    Instruction4    VARCHAR(40),
    Package5	      INT,          # 自費 4
    PresDays5	      INT,
    Instruction5    VARCHAR(40),
    Package6	      INT,          # 自費 5
    PresDays6	      INT,
    Instruction6    VARCHAR(40),

    Treatment       VarChar(10), # 健保: 針灸治療, 電針治療, 複雜針灸,
                    #                    傷科治療, 脫臼整複, 複雜傷科, 複雜骨折
                    # 特定疾病加強照護:
                    #   小兒氣喘-含氣霧, 小兒氣喘-不含氣霧
                    #   小兒腦麻-含藥浴, 小兒腦麻-不含藥浴

    SelfTreatment   VarChar(10),  # 自費: 針灸治療, 傷科治療, 民俗調理, 脫臼整複
                                  #       針灸傷科, 針灸脫臼
    Position1	      VARCHAR(10),  # 部位代碼1: 2 Codes + 8 Chars for Name
            	                    # 1A頭      ,2A頸      ,3A軀幹(前),4 軀幹(後),4A背
	                                # 4B腰      ,4C股      ,5 上肢(左),5A指(左)  ,5B腕(左)
                                  # 5C肘(左)  ,5D上臂(左),5E下臂(左),5F肩(左)  ,
                                  # 6 上肢(右),6A指(右)  ,6B腕(右)  ,6C肘(右)  ,
                                  # 6D上臂(右),6E下臂(右),6F肩(右)  ,
	      	                        # 7 下肢(左),7A趾(左)  ,7B踝(左)  ,7C膝(左)  ,
                                  # 7D大腿(左),7E小腿(左),
	                                # 8 下肢(右),8A趾(右)  ,8B踝(右)  ,8C膝(右)  ,
	                                # 8D大腿(右),8E小腿    ,
    Position2	    VARCHAR(10),    # 部位代碼2

#   各項費用
    RegistFee	      INT,	  # 掛號費

    DiagFee	        INT,	  # 診察費
    InterDrugFee	  INT,	  # 內服藥費
    PharmacyFee	    INT,	  # 藥服費
    AcupunctureFee  INT,    # 針灸費 (電針費);
                            # 處置費 (TreatFee) = 針灸費+傷科費+脫臼費
    MassageFee	    INT,	  # 傷科費
    DislocateFee	  INT,	  # 脫臼費
                            # 治療費 (CureFee): 特定疾病加強照護: 腦疾-照護費與檢查費
                            #        孕產照護: 助孕照護, 保胎照護  104.01.08
    ExamFee	        INT,  	# 檢驗費

    InsTotalFee	    INT,   	# 健保合計,不含掛號費,欠卡費,還卡費
    DiagShareFee    INT,	  # 門診負擔,負擔金額=門診負擔+藥品負擔
    DrugShareFee    INT,	  # 藥品負擔
    SDiagShareFee   INT,    # 實收門診負擔
    SDrugShareFee   INT,    # 實收藥品負擔

    AgentFee	      INT,   	# 代辦費
    InsApplyFee	    INT, 	  # 健保申請

    DepositFee	    INT,  	# 欠卡費
    RefundFee       INT,    # 還卡費

    SDiagFee	      INT,	  # 自費診察費
    SDrugFee	      INT,	  # 自費一般藥費: 單方+複方+外用藥
    SHerbFee	      INT,	  # 自費水藥費
    SExpensiveFee   INT,	  # 自費高貴藥費
    SAcupunctureFee INT,	  # 自費針灸費
    SMassageFee	    INT,    # 自費傷科費  民俗調理費
    SDislocateFee   INT,  	# 自費脫臼費
    SMaterialFee    INT,    # 自費材料費: 含診斷證明, 收費證明
    SExamFee	      INT,  	# 自費檢驗費: (骨折費 105.01.28 育源堂)
    SMiscFee        INT,    # 自費其他

    SelfTotalFee	  INT,	  # 自費合計,不含掛號費,欠卡費,還卡費
    DiscountFee	    INT,	  # 減免金額
    TotalFee	      INT,	  # 應收金額 (不含掛號費, 負擔金額)
    ReceiptFee	    INT,	  # 門診當天實收金額; 門診當日欠款金額=應收-實收(Virtual 顯示)
    DebtFee		      INT,	  # 尚欠金額(欠款餘額); 還款時, 同時更新

    Status	        VARCHAR(04),	# 工作狀態: 掛號(修正),診療(醫師),查詢(病歷修正), 藥局
    DoctorDone	    ENUM("False","True") NOT NULL,  # 診療結束
    MassageDone	    ENUM("False","True") NOT NULL,  # 理療結束
    ChargeDone	    ENUM("False","True") NOT NULL,  # 批價結束
    DrugDone	      ENUM("False","True") NOT NULL,  # 給藥結束

    Reference	      ENUM("False","True") NOT NULL,  # 0-No 1-當筆參考病歷
    Note		        VARCHAR(02),    # 註記, 資料不寫檔, 暫用
    Message	        VARCHAR(40),	  # 錯誤訊息

    Security        BLOB,           # 健保IC卡安全簽章:
                    #  1-  1 - 1 Upload         正常卡序: (已取得就醫序號 94.02.18)
                    #                                     1-未上傳 2-已上傳 3-補正上傳
                    #                           異常卡序: A-未上傳 B-已上傳 C-補正上傳
                    #  2-  1 - 2 Deposit        1-正常   2-補卡
                    #  3- 13 - 3 RegistDate     YYYMMDDHHMMSS 民國年 門診/補卡日期
                    #  4- 10 -16 ClinicID       院所代碼
                    #  5-256 -26 Security       安全簽章
                    #  6- 12-282 SAM ID         安全模組代碼
                    #  7-  7-294 UploadDate     YYYMMDD 上傳日期    民國年
                    #  8-  7-301 NewBornDate    YYYMMDD 新生兒生日  民國年
                    #  9-  1-308 NoOfDelivered  新生兒胞胎註記 (胎數)
                    # 10-  1-309 NewBornMark    新生兒就醫註記 (產序)
                    # 11-  1-310 WriteCard2     病歷資料: 病名/收費/醫令 資料寫入 Y/N(Blank)

    TimeStamp	TIMESTAMP,	        # 上次異動日期

    PRIMARY KEY(CaseKey),
    INDEX(PatientKey, CaseDate)
) CHARACTER SET utf8;


