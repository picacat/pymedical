
# 22. 健保人次檔    100.07.01

CREATE TABLE IF NOT EXISTS InsTreat
(
    InsTreatKey	    INT AUTO_INCREMENT NOT NULL,  # 健保人次序號

    InsTreatNo	    INT,		      # 健保人次編號
    Applydate	      VARCHAR(05),	# 費用年月: YYYMM
    ApplyPeriod	    VARCHAR(06),	# 申報期間: 全月(新), 上半月(舊), 下半月(新)
    Content	        VARCHAR(200),	# 統計內容

    TimeStamp	    TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(InsTreatKey),
    INDEX(InsTreatNo)
) CHARACTER SET utf8;

# 編號 00 健保申報日期
# ApplyDateRecord:
#   ApplyOrganizeDate   VARCHAR(10) 1 -最近資料整理日期 (上傳日期)  YYYY/MM/DD (西曆)
#   ApplyStartDate      VARCHAR(10) 11-申報開始日期     YYYY/MM/DD (西曆)
#   ApplyStopDate       VARCHAR(10) 21-申報結束日期     YYYY/MM/DD (西曆)

# 編號 01-30(16): 診察費表資料	InsDoctorRecord
#	     01-20(15): 各醫師分配資料	1-20(10) 專任, 21-29(11-15) 支援
#	     30(16): 合計

# InsDoctorRecord:
#   DoctorType	        VARCHAR(04)	1 -醫師類別: 專任, 支援
#   DoctorName	        VARCHAR(10)	5 -醫師姓名:
#   DoctorID	          VARCHAR(10) 15-醫師身分證號
#   NurseName	          VARCHAR(10) 25-護士姓名
#   NurseID	            VARCHAR(10)	35-護士身分證號

#   Days	              INT(07),	  45-看診日數
#   CaseDiag	          INT(07),	  52-有診察費人次: 內科 + 針傷       (不含職傷,巡迴醫療人次)
#   CaseDiagTreat       INT(07),	  59-有診察費人次 針傷首次		             "
#   CaseDiagFree        INT(07),	  66-無診察費人次 針傷連續療程 2-6次	     "
#   CaseTotal	          INT(07),	  73-總就診人次 = CaseDiag 有診察費人次 +  "
#		                                              CaseDiagFree 無診察費人次  "
#   Case30	            INT(07),	  80-診察人次30     A01 / A02	       (不含職傷,巡迴醫療人次)
#       101.10.01 變更為 25 人次, Case30 延用
#   Case50	            INT(07),	  87-診察人次50     A03 / A04	       	       "
#   Case70	            INT(07),	  94-診察人次70     A05 / A06		             "
#   Case150	            INT(07),	  101-診察人次150   A07			"
#   Case151	            INT(07),	  108-診察人次151   A08			"
# end;

# 編號 31 (原存 #16 -97.07.15) 合計資料:
#   TInsTotalRecord = record
#      Doctor           INT(05)     1 -專任醫師
#      Parttime         INT(05)     6 -支援醫師
#      TotalDiagFee     INT(10)     11-調整後總診察費:含內科,針傷
#      TotalCaseDrug    INT(05)     21-總開藥人次
#      TotalCaseB6      INT(05)     26-總職傷人次
#      TotalCaseB6Diag  INT(05)     31-職傷診察人次
#      TotalCaseB6Treat INT(05)     36-總職傷針傷首次 (職傷針傷療程, 不存)
#   end;

# 編號 32 (原存 #21 -97.07.15): 例外資料 92.09.19 巡迴醫療人次, 職傷診察費, 腦疾, 初診照護
#   TInsSpecialRecord = record
#     TotalCase25       INT(05)	    1- 巡迴醫療總人次
#     TotalCase25Diag   INT(05)	    6- 巡迴醫療診察人次
#     TotalCase25Treat  INT(05)	    11-巡迴醫療  針傷首次 (有診察費人次)
#     TotalCase25Free   INT(05)	    16-巡迴醫療  針傷連續療程 2-6次
#     TotalCase25DiagFee Int(07)    21-巡迴總診察費      94.07.12

#     TotalCaseB6DiagFee int(07)    28-職傷總診察費

#     TotalCaseBrain    int(05)	    35-腦疾總人次        95.11.13
#     TotalCaseBrainDiagFee Int(07) 40-腦疾總診察費

#     TotalCaseInit     int(05)	    47-初診照護總人次    96.01.026
#     TotalCaseInitFee  Int(07)     52-初診照護總診察費

#     TotalTreatDrug    INT(07)     59-處置開藥人次 (含 B55 複傷給藥) 97.01.01
#     Filler            x(07)       59-保留00000000; void 101.02.09 移至 #33

#     TotalCaseBrainSequela         int(05)	66-腦疾後遺症總人次  98.12.31 童綜
#     TotalCaseBrainSequelaDiagFee  int(07) 71-腦疾後遺症總診察費

#     TotalCaseSpecialCare          int(05)	78-特定疾病加強照護: 小兒氣喘, 小兒腦麻 總人次   102.03.20
#                                                 腦血管疾病 103.01.01, 孕產照護總人次 104.01.08
# end;

# 編號 33: 處置資料 101.02.09
#   TInsCureRecord = record
#     TotalTreatDrug    INT(07)     1- 處置開藥人次 (含 B55 複傷給藥) 97.01.01

# 編號 49-57: 處置費表資料	49-55 於資料整理統計產生
#1-49: 複雜傷科16人次: B55, B56, B57
#2-52: 針傷給藥23人次: B41, B43, B45, B53, B55, B62
#3-51: 處置人次30   100%
#4-52: 處置人次45    90%
#5-53: Reserved
#6-54: 處置人次46		  0%  93.08.11 不給付, 超過 46 人次
#7-55: 處置人次合計	#51 + #52 + #53 + #54
#8-56: 處置費			  各段合計; 調整後
#9-57: 診察費			  各段合計, 調整後  void 102.03.15

# InsTreatRecord
#   AcupB41	      INT(07),	1-針灸給藥  B41	人次 / 金額
#   AcupB42	      INT(07),	8-針灸	    B42	人次 / 金額
#   MassB53	      INT(07),	15-傷科給藥 B53	人次 / 金額
#   MassB54	      INT(07),	22-傷科	    B54	人次 / 金額
#   DislB61	      INT(07),	29-脫臼首次 B61	人次 / 金額
#   DislB62	      INT(07),	36-脫臼給藥 B62	人次 / 金額
#   DislB63	      INT(07),	43-脫臼	    B63	人次 / 金額

#   TotalMassage  INT(07),	50-傷科小計 = 傷科+脫臼 B53+B54+B61+B62
#   TotalTreat	  INT(07),	57-處置合計 = 針灸+傷科+脫臼: B41+B42 +B53+B54 +B61+B62+B63 + B43+B44+B45+B46 +
#                                                         B55+B56+B57(複雜傷科)
#   AcupB43	      INT(07),	64-電針給藥 B43 人次/金額    (含職傷人次)       93.08.10
#   AcupB44	      INT(07),	71-電針	    B44 人次/金額

#   AcupB45	      INT(07),	78-複針給藥 B45 人次/金額    (含職傷人次)       95.03.12
#   AcupB46	      INT(07),	85-複雜針灸 B46 人次/金額

#   MassB55       INT(07),  92-複傷給藥
#   MassB56       INT(07),  99-複雜傷科
#   MassB57       INT(07), 106-複雜骨折

# 編號 61-67: 處置費表資料-針傷合併治療
#   1-61: 複雜傷科 16 人次: 針灸: B82, B83, B84; 電針: B87, B88, B89; 複針:B92, B93, B94
#   2-62: 針傷給藥 30 人次: 針灸: B80, B82,      電針: B85, B87       複針:B90, B92
#   3-63: 處置人次30   100%
#   4-64: 處置人次45    90% 針灸: B81, B83, B84  電針: B86, B88, B89; 複針:B91, B93, B94
# 	5-65-Reserved,
#   6-66: 處置人次46		 0% 超過 46 人次, 不給付
#   7-67: 處置人次合計
#   8-68: 處置費			  各段合計; 調整後
#   9-69: 診察費			  各段合計, 調整後  102.03.15 void, unknown

#   MixTreatB80   INT(07),   1-針灸治療: 傷科治療(給藥)
#   MixTreatB81   INT(07),   8-          傷科治療(無藥)
#   MixTreatB82   INT(07),  15-          複雜傷科(給藥)
#   MixTreatB83   INT(07),  22-          複雜傷科(無藥)
#   MixTreatB84   INT(07),  29-          骨折脫臼
#   MixTreatB85   INT(07),  36-電針治療: 傷科治療(給藥)
#   MixTreatB86   INT(07),  43-          傷科治療(無藥)
#   MixTreatB87   INT(07),  50-          複雜傷科(給藥)
#   MixTreatB88   INT(07),  57-          複雜傷科(無藥)
#   MixTreatB89   INT(07),  64-          骨折脫臼
#   MixTreatB90   INT(07),  71-複雜針灸: 傷科治療(給藥)
#   MixTreatB91   INT(07),  78-          傷科治療(無藥)
#   MixTreatB92   INT(07),  85-          複雜傷科(給藥)
#   MixTreatB93   INT(07),  92-          複雜傷科(無藥)
#   MixTreatB94   INT(07),  99-          骨折脫臼

# end;


