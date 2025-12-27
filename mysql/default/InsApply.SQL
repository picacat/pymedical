
# 21. 健保申報檔    100.07.01
#     抽查列印時, [病名主訴] 從 [病歷檔] 讀取.
#     病歷檔 [病名主訴] 可變更, 不須重新資料整理.

CREATE TABLE IF NOT EXISTS InsApply
(
    InsApplyKey	    INT AUTO_INCREMENT NOT NULL,  # 健保申報序號

    ClinicID	      VARCHAR(10),  # 院所代號
    ApplyDate	      VARCHAR(05),	# 費用年月: YYYMM
    ApplyPeriod	    VARCHAR(06),	# 申報期間: 全月(新),上半月(舊院所),下半月(新院所)
    ApplyType	      VARCHAR(01),	# 申報類別: 1-送核  2-補報
    CaseType	      VARCHAR(02),	# 案件分類: 21-一般 22-其他(檢驗/腦疾/腦疾後遺症/地區醫院)
                                  #   24-慢性病
                                  #   25-巡迴醫療,(資源不足巡迴醫療, 偏遠地區長期進駐 100.01.01)
				                          #   29-專案(針傷)   26-複雜針灸 27-複雜傷科 B6-職傷
                                  #   J1-長期臥床代領藥       J2-遠洋漁業代領藥
                                  #   22-腦疾, 腦疾後遺症
				                          #	各類別均含職傷, 以CASE.SHARE 為準
    Sequence        INT,		      # 流水號

    SpecialCode1	  VARCHAR(02),	# 特定治療1: C3-針灸 C4-傷科 C5-脫臼
    SpecialCode2	  VARCHAR(02),	# 特定治療2
    SpecialCode3	  VARCHAR(02),	# 特定治療3
    SpecialCode4	  VARCHAR(02),	# 特定治療4
    Class 	        VARCHAR(02),	# 就醫科別: 60-中醫

    CaseDate	    DATE,		      # 就醫日期 連續療程首次日期 93.02.05
    StopDate	    DATE,		      # 結束日期

    Era		        VARCHAR(01),	# 年號
    Birthday	    DATE,		      # 出生日期
    ID		        VARCHAR(10),	# 身分證號
    Card		      VARCHAR(04),	# 健保卡號
    Injury    	  VARCHAR(01),	# 給付類別: 1-職業傷害 2-職業病 3-普通傷害 4-普通疾病
    ShareCode	    VARCHAR(03),	# 部分負擔

    Visit 	      VARCHAR(08),  # 初診照護  101.03.20   10%申報
                                # 職傷初診 17.10.23
    TransferFrom	VARCHAR(10),	# 轉入院所代號: N; 96.02.15 初診, 複診空白  101.03.20 void

    TransferOut	  VARCHAR(01),	# 是否轉出: N
    DiseaseCode1	VARCHAR(10),	# 病名1: ICD9 / ICD10 5->10 103.09.10
    DiseaseCode2	VARCHAR(10),	# 病名2: ICD Code
    DiseaseCode3	VARCHAR(10),	# 病名3: ICD Code
    SurgeryCode	  VARCHAR(04),	# 手術碼:ICD Code

    PresDays	    INT,		      # 給藥日份
    PresType	    VARCHAR(01),	# 調劑方式: 0-自行調劑 1-交付調劑 2-未開處方
    ChronicNo	    VARCHAR(10),	# 連續處方箋號: N

    DoctorName	    VARCHAR(10),# 醫師姓名 92.04.07 Inserted
                                # 92.5.8 醫師姓名   (,;) 申報算一筆, 統計算兩筆
					                      #                 非(,;) 申報算兩筆, 統計算兩筆
    DoctorID	    VARCHAR(10),	# 醫師代號: 身分證號
    PharmacistID	VARCHAR(10),	# 藥師代號: 身分證號

    DrugFee	        INT,		    # 藥費
    TreatFee	    INT,		      # 處置費 = 針灸費 + 傷科費 + 脫臼費 + 檢驗費
                                #          (照護費與檢查費(治療費))
    DiagCode	      VARCHAR(12),	# 診察費代號: A01-A08; A06A90: A04-診察費 A90:初診加成
    DiagFee	        INT,		    # 診察費

    PharmacyCode	  VARCHAR(12),# 藥服代號: A31-A32;  6次: 120010: 0-無調劑 1-A31藥師 2-A32醫師
    PharmacyFee	    INT,		    # 藥服費

    InsTotalFee	    INT,	    	# 健保合計
    ShareFee	      INT,		    # 負擔金額: TreatShare + DrugShare
    InsApplyFee	    INT,		    # 健保申請
    AgentCode	      VARCHAR(12),	# 代辦費代號
    AgentFee	      INT,		    # 代辦費

    ChronicPresDays INT,		    # 連續處方箋總日份: 0
    PatientKey	    INT,		    # 系統號
    Name		        VARCHAR(20),	# 姓名

    CaseKey1	      INT,		    # 病歷序號1: 第一次療程 或 內科
    TreatCode1	    VARCHAR(12),	# 處置醫令1: B41,B42,B53,B54,B61,B62,B63
    TreatFee1	      INT,		    # 單價(調整後) 200->180
    Percent1	      INT,		    # 處置成數1: 0, 90, 100, 105

    CaseKey2	      INT,		    # 病歷序號2: 第二次療程
    TreatCode2	    VARCHAR(12),
    TreatFee2     	INT,
    Percent2	      INT,

    CaseKey3	      INT,		    # 病歷序號3: 第三次療程
    TreatCode3	    VARCHAR(12),
    TreatFee3	      INT,
    Percent3	      INT,

    CaseKey4	      INT,		      # 病歷序號4: 第四次療程
    TreatCode4	    VARCHAR(12),
    TreatFee4	      INT,
    Percent4	      INT,

    CaseKey5	      INT,		      # 病歷序號5: 第五次療程
    TreatCode5	    VARCHAR(12),
    TreatFee5	      INT,
    Percent5	      INT,

    CaseKey6	      INT,		      # 病歷序號6: 第六次療程
    TreatCode6	    VARCHAR(12),
    TreatFee6	      INT,
    Percent6	      INT,

    Note		        VARCHAR(01),	# 註記, 列印用
    Message	        VARCHAR(40),	# 錯誤訊息

    TimeStamp	      TIMESTAMP,    # 上次異動日期

    PRIMARY KEY(InsApplyKey),
    INDEX(ApplyDate)
) CHARACTER SET utf8;

