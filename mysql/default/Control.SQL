
# 01. 系統控制檔    100.07.01

CREATE TABLE IF NOT EXISTS Control
(
    ControlKey	INT AUTO_INCREMENT NOT NULL,	# 控制序號
    StationNo	  INT,		      # *工作站編號, 原 ControlNo
                              #  00-全院   01-99 各工作站
    Item        VARCHAR(20),  # *項目名稱
    Content	    VARCHAR(100),	# 控制內容

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(ControlKey),
    INDEX(StationNo)
) CHARACTER SET utf8;

# Content: 所有數字(9): 右靠補零 (須固定欄寬); 文字: 左靠補空白
# Item,         Content,        Comments

#*******************************************************************************
# 全院資料
# * 1.系統資料 00:
# 1-1 廣播網路      IPBroadcast VARCHAR(100) 廣播網路 192.168.0.[255]
# 1-2 系統使用時間
#       UseDate	    VARCHAR(10)  1-系統使用日期, YYYY/MM/DD (西元);
#                                  以第一台主機為準.
#		                               系統自動比對使用日期/電腦日期;
#                                  不同年, 收據編號為00;
#		                           不同日, 就診控制號為 00, 班別為早班.
#       UsePeriod	VARCHAR(04) 11-目前系統使用班別: 早班,午班,晚班(掛號時變更班別)
#       Schedule1	VARCHAR(04) 15-早班時間 HHMM  24時制
#       Schedule2	VARCHAR(04) 19-午班時間 HHMM
#       Schedule3	VARCHAR(04) 23-晚班時間 HHMM

# * 2.院所基本資料 00:
# 2-1 院所名稱
#       ClinicID    VARCHAR(20)  1-健保局編號
#       ClinicName  VARCHAR(80) 21-院所名稱

# 2-2 院所資料
#       ClinicSeries VARCHAR(20) 1-院所系列
#       ClinicType	VARCHAR(04)  21-院所類別: 中醫, 西醫, 牙醫
#       ClinicClass VARCHAR(10)  25-院所等級: 基層院所, 地區醫院, 區域醫院, 教學醫院
#       Division    VARCHAR(10)  35-台北分局, 北區分局, 中區分局, 南區分局, 高屏分局,東區分局
#       InvoiceNo   VARCHAR(10)  45-統一編號

# 2-3 院所證照
#       ClinicDoctor	    VARCHAR(20)  1-負責醫師
#       ClinicCertificate VARCHAR(40) 21-院所開業執照號碼
#       DoctorCertificate VARCHAR(40) 61-醫師執照號碼 (負責醫師證書號碼)

# 2-4 院所連絡資料
#       ClinicTelephone   VARCHAR(15) 院所電話
#       ClinicAddress	    VARCHAR(50) 院所地址
# 2-5 院所電子郵件 Email  VARCHAR(100) 電子郵件

# 2-6系統等級   Priority    VARCHAR(100) 系統被使用等級 : 0-9 依系統程式 SysPriority

# * 3.院所一般資料 00:
# 3-1 醫事人員
#       NurseNo		      INT(04)  1-護士數
#       PharmacistNo    INT(04)  5-專任藥師數, 醫師有藥師執照不算 (兼任)

# 3-2 數量限定
#       DrugLimit	      INT(04)  1-給藥總量上限, 成本考量:  9999 不限,
#                                Ratio: 處方比例總量 Redefined 新竹 16.12.12
#       RegistCaseMonths INT(04) 5-掛號病歷查詢月份         9999-全部
#       CaseCopyLimit   INT(04)  9-病歷拷貝顯示月份範圍     9999-全部
#       CaseCountLimit	INT(04) 13-掛號門診總次數(健保+自費)-警告: 當月 >=, BEEP
#       TreatCountLimit	INT(04) 17-掛號針傷總次數-警告(健保): 超過即警告用, 當月 >=, BEEP
#       DiagCountLimit	INT(04) 21-掛號診察費次數-警告(健保): 當月 >=, BEEP
#       PresDaysLimit   INT(04) 25-藥日檢查重複間隔日數
#       DiseaseLimit    INT(04) 29-相同病名警告次數     原參數設定 DiseaseWarning
#       DosageAge       INT(04) 33-給藥總量最低限度-年齡:  0 不限
#       AgeDosage       INT(04) 37-給藥總量最低限度-劑量:  0 不限

# 3-3 相關模式
#       ChartNoMode	    VARCHAR(08)  1-病歷編號模式: 自行輸入, 生日+ID4(身份證後四碼),
#                                                    生日序號, 系統序號(6碼), 流水號
#       CasesInsSelf    VARCHAR(04)  9-健保自費病歷: 共用 (同一筆病歷 Case1-9),
#                                                    分開 (不同筆病歷 CasMedicine)
#       ContinuanceSaveMode VARCHAR(08) 13-連續療程處置內容不一致: 無法存檔, 可以選擇
#       DoctorListMode	VARCHAR(08) 21-醫師查詢名單模式:全部(不分醫師不分診), 相同診別,
#                                      相同醫師, 候診全部-候診名單顯示全部,已就診顯示相同醫師
#       RemainMode 	    VARCHAR(04) 29-掛號候診名單顯示模式, 不同日時: 保留, 清除
#       AutoRegContinue VARCHAR(02) 33- ICCard 掛號自動連續療程: 是/否

#       SetSchedule     VARCHAR(04) 35-班別設定: 自動, 手動
#       TreatType       VARCHAR(10) 39-就醫類別: 一般,巡迴偏遠,巡迴山地,巡迴離島(Regist used)
#                                      一般+民俗, 針灸+民俗(健保), 針藥+民俗(健保) ...
#       ProofDiagnosis  VARCHAR(04) 49-診斷證明重複: 可以, 不可, 選擇
#       ProofReceipt    VARCHAR(04) 53-收費證明重複: 可以, 不可, 選擇
#       ProofReceiptItems VARCHAR(04) 57-收費證明明細修改: 可以, 不可

# * 4.資源不足/巡迴醫療資料 00:
# 4-1 資源不足/巡迴醫療
#       CruiseLocation  VARCHAR(20)  1-巡迴醫療地區
#       ResourceLack    VARCHAR(20) 21-資源類別: 一般, 資源不足巡迴醫療, 資源不足開業
#                                                偏遠地區長期進駐 (申報CaseType = 25)

# * 5.院所健保資料 00:
# 5-1 申報資料
#       Filler          VARCHAR(10)  1-
#       AcupunctureDate VARCHAR(10) 11-針灸標準認證合格日期 YYYY/MM/DD (西元)
#       ApplyMedia	    VARCHAR(08) 21-申報媒體: 磁片申報 (DTL=45000, ORD=3000),
#				                                 網路申報 (DTL, ORD= 99999)
#       WriteICCard     VARCHAR(04) 29-安全簽章寫入位置: 掛號, 診療, 批價, 未定
#       InitialVisit    VARCHAR(02) 33-初診照護健保申報: 是/否
#       SortBy          VARCHAR(08) 35-健保申報排序方式: 門診日期, 系統號
#       ICCardDiagnosis VARCHAR(02) 43-診療資料(金額, 病名, 處置, 醫令) 寫入 IC卡: 是/否
#       UploadPresSign  VARCHAR(02) 45-空白處方簽章上傳: 是/否
#       DTLSymptomPrint VARCHAR(04) 47-醫令主訴列印: 列印/不印
#       InsGross        VARCHAR(02) 51-總額支付評鑑合格: 是/否
#       InsPassword     VARCHAR(20) 53-網路申報登入密碼
#       InsReceiveNo    VARCHAR(20) 73-網路申報收件序號; 健保申報回傳, 不用寫檔
#       ApplyPharmacyFee VARCHAR(02) 93-調劑費申報(病歷登錄預設): 申報, 不報  101.06.05

# * 6.序號資料 00:
# 6-1 編號控制
#       CtrlReceiptYearly INT(06)    1-收據年編號: 以年為單位, 每年從 00 開始;
#					                             一般院所- QryCases['YearlyNo1']
#                                      龍潭敏盛- QryCases['YearlyNo2'] 有部分負擔 & 自費金額
#       CtrlChargeYearly INT(06)     7-收費年編號: 以年為單位, 每年從 00 開始;
#                                      Cases['YearlyNo3']
#       CtrlChargeDaily	INT(04)     13-批價控制號: 全院所, 每日從 00 開始
#       CtrlDrugDaily   INT(04)     17-給藥控制號: 全院所, 每日從 00 開始

#       DiagControlMode	VARCHAR(12) 21-就診號控制類別: 不分班不分診, 不分班分診
#						                               分班不分診, 分班分診
#       StartNo1	    INT(04)       33-早班就診增加號 (灌水)
#       StartNo2	    INT(04)       37-午班就診增加號 (灌水)
#       StartNo3	    INT(04)       41-晚班就診增加號 (灌水)
#       ReserveNoMode	VARCHAR(04)   45-預約診號模式: 不分, 單號, 雙號, 間距, 區間, 班表
#                                      不分- 現場就診號/預約號, 取最大值 (避免重複)
#                                      單號- 預約單號: 1, 3, 5 ...  現場門診雙號: 2, 4, 6 ...
#                                      雙號- 預約雙號: 2, 4, 6 ...  現場門診單號: 1, 3, 5 ...
#                                      間距- 預約在先: 間距 5: 1, 6, 11, 16 ...  (重安)
#                                            現場門診: 2-5, 7-10, 12-15, ...
#                                      區間- 預約在先: 1-5,  11-15, 21-25 ...
#                                            現場門診: 6-10, 16-20, 26-30 ...
#                                      班表- 預約報到時, 依診號設定
#                                            診號 0 (未設定)-預約報到時, 現場就診號/預約號, 取最大值(避免重複)
#       RegistNoMode	VARCHAR(04)   49-現場掛號診號模式: 預約診號模式: 班表 only
#                                      單號, 雙號 (明確)
#                                      不分 - 預約診號 0 (未設定)-預約報到時, 現場就診號/預約號, 取最大值(避免重複)
#                                           - 預約診號 > 0, 避開預約診號, 取最大值
#       ReserveStartNo INT(04)      53-預約起始號: 現場保留號; 預約模式為 [不分].
#       ReserveRange  INT(04)       57-預約間距號: 預約模式: 間距 5: 1, 6, 11, 16
#                                                  預約模式: 區間 5: 1-5, 11-15, 21-25 ...
# 6-2-1 叫號控制                       104.11.24 悅兒叫號系統 APP
#       CurrentRegistNo1 int(04)      1-目前就診號    1 診  16.12.28
#       CurrentDoctor1   VARCHAR(10)  5-目前看診醫師
#       CurrentRegistNo2 int(04)      1-目前就診號    2 診
#       CurrentDoctor2   VARCHAR(10)  5-目前看診醫師
#       CurrentRegistNo3 int(04)      1-目前就診號
#       CurrentDoctor3   VARCHAR(10)  5-目前看診醫師  3 診
#       CurrentRegistNo4 int(04)      1-目前就診號
#       CurrentDoctor4   VARCHAR(10)  5-目前看診醫師  4 診
#       CurrentRegistNo5 int(04)      1-目前就診號
#       CurrentDoctor5   VARCHAR(10)  5-目前看診醫師  5 診

# 6-2 就診控制號                     void 101.06.26
#       DiagControlNo01	INT(04)      1-就診控制號1: 就診控制編號,每日從 00 開始;
#			                                  鍵盤可輸入(含灌水號); 不分診時: 以就診號控制 1 為準
#       DiagControlNo02	INT(04)      5-就診控制號2:
#       DiagControlNo03  INT(04)      9-就診控制號3
#       DiagControlNo04	INT(04)     13-就診控制號4
#       DiagControlNo05	INT(04)     17-就診控制號5
#       DiagControlNo06	INT(04)     21-就診控制號6
#       DiagControlNo07	INT(04)     25-就診控制號7
#       DiagControlNo08	INT(04)     29-就診控制號8
#       DiagControlNo09	INT(04)     33-就診控制號9
#       DiagControlNo10	INT(04)     37-就診控制號10
#
# 6-3 預約時間間隔 (預約模式: 現場)   void 101.06.26
#       ReserveInterval01   INT(04) 1- 1診: 預約時間
#       ReserveInterval02   INT(04) 5- 2診: 預約時間
#       ReserveInterval03   INT(04) 9- 3診: 預約時間
#       ReserveInterval04   INT(04) 13-4診: 預約時間
#       ReserveInterval05   INT(04) 17-5診: 預約時間
#       ReserveInterval06   INT(04) 21-6診: 預約時間
#       ReserveInterval07   INT(04) 25-7診: 預約時間
#       ReserveInterval08   INT(04) 29-8診: 預約時間
#       ReserveInterval09   INT(04) 33-9診: 預約時間
#       ReserveInterval10   INT(04) 37-10診:預約時間

# * 7.公佈欄資料 00:
# 7-1 公佈欄資料 Bulletin
#       BulletinStartDate VARCHAR(10) YYYY/MM/DD (西元)  2008/06/13
#       BulletinStopDate  VARCHAR(10) YYYY/MM/DD (西元)
#       BulletinFilePath  VARCHAR(50) 公佈欄文字檔路徑名稱
# 7-2 公佈欄簽章1         occurs 5 times
#       SignDate01        VARCHAR(10) YYYY/MM/DD (西元)
#       SignName01        VARCHAR(10)
#       ...
#       SignDate05        VARCHAR(10) YYYY/MM/DD (西元)
#       SignName05        VARCHAR(10)
# 7-3 公佈欄簽章2         occurs 5 times
#       SignDate06        VARCHAR(10) YYYY/MM/DD (西元)
#       SignName06        VARCHAR(10)
#       ...
#       SignDate10        VARCHAR(10) YYYY/MM/DD (西元)
#       SignName10        VARCHAR(10)
# 7-4 公佈欄簽章3         occurs 5 times
#       SignDate11        VARCHAR(10) YYYY/MM/DD (西元)
#       SignName11        VARCHAR(10)
#       ...
#       SignDate15        VARCHAR(10) YYYY/MM/DD (西元)
#       SignName15        VARCHAR(10)
# 7-5 公佈欄簽章4         occurs 5 times
#       SignDate16        VARCHAR(10) YYYY/MM/DD (西元)
#       SignName16        VARCHAR(10)
#       ...
#       SignDate20        VARCHAR(10) YYYY/MM/DD (西元)
#       SignName20        VARCHAR(10)

# * 8.全銜附記資料 00:
# 8-1   掛號收據附記      RegistRemark    VARCHAR(100)掛號收據附記
# 8-2   收費明細全銜      ChargeTitle     VARCHAR(100)收費明細全銜 (內含院所名稱)PrintPres(處方收據)
# 8-3   收費明細附記      ChargeRemark    VARCHAR(100)收費明細附記
# 8-4   診斷證明全銜      DiagTitle	    VARCHAR(100) 診斷證明全銜 (內含院所名稱)
# 8-5   診斷證明附記      DiagRemark 	    VARCHAR(100) 診斷明細附記
# 8-7   收費證明明細全銜  ReceiptTitle1  VARCHAR(100) 收費證明全銜-列印明細 (內含院所名稱)
# 8-8   收費證明收據全銜  ReceiptTitle2  VARCHAR(100) 收費證明全銜-列印收據 (內含院所名稱)
# 8-6   收費證明單全銜    ReceiptTitle3	VARCHAR(100) 收費證明全銜-醫療費用證明單(內含院所名稱)
# 8-9   收費證明明細附記  ReceiptRemark1 VARCHAR(100) 收費證明附記-列印明細
# 8-10  收費證明收據附記  ReceiptRemark2 VARCHAR(100) 收費證明附記-列印收據

# * 9.各項路徑設定 00:
# 9-1 系統更新來源路徑  MedUpdatePath VARCHAR(100) 系統更新來源路徑 for MedUpdate.exe, *.dll
#                                                  空白(單機) 不必更新
# 9-2 資料庫路徑        DataPath    VARCHAR(100) 申報檔路徑: 申報XML路徑 申報YYYMM.XML, 申報上半月YYYMM.XML
#                                                與資料庫路徑(MYSQL)一致
# 9-3 申報上傳路徑      UploadPath  VARCHAR(100) 申報文字檔路徑: TOTFA,DTLFA,ORDFA,HERBF  void 101.01
#                                                網際網路上傳路徑 (XML -> ZIP)
# 9-4 電子病歷交換檔路徑 EMRPath    VARCHAR(100) 捷達世

# 9-5 影像檔路徑        ImagePath   VARCHAR(100) 影像資料 R/W (Patient, CasPicture-JPG, 驗方)
                        # void 101.12.21 影像資料直接存入 Database (Image.SQL)
# 9-6 套表路徑          OfficePath  VARCHAR(100) 醫師班表 R   (Medical-DOC檔),
#                                                巡迴醫療路徑 (InsCruise-Excel)
# 9-7 電子病歷抽審檔路徑 EMRExamPath VARCHAR(100) 捷達世

#                                                腦疾路徑     (CasSearch-Excel)
# 9-7 備份路徑1         BackupPath1 VARCHAR(100) 強制寫入 XML
# 9-8 備份路徑2         BackupPath2 VARCHAR(100)
# 9-9 備份路徑3         BackupPath3 VARCHAR(100)
# 9-10備份路徑4         BackupPath4 VARCHAR(100)

# *10.藥袋標示 00:
#10-1 藥廠名稱          DrugFactory     VARCHAR(100) 藥廠名稱
#10-2 藥品保存方式      DrugPreserved   VARCHAR(100) 藥品保存方式
#10-3 藥品有效期限      DrugValidDate   VARCHAR(100) 藥品有效期限
#10-4 藥品副作用        DrugSideEffect  VARCHAR(100) 藥品副作用
#10-5 藥品警語          DrugWarning     VARCHAR(100) 藥品警語

# *11.舊院所資料 00:
#11-1 舊院所名稱
#       OldClinicID     VARCHAR(20) 健保局編號
#       OldClinicName   VARCHAR(80) 院所名稱
#11-3 舊負責醫師        OldClinicDoctor VARCHAR(100)
#11-4 舊院所連絡資料
#       OldClinicTelephone  VARCHAR(15) 舊院所電話
#       OldClinicAddress    VARCHAR(50) 舊院所地址

# *12.健保指標資料 00:  100.00%, $1234567, LeftJust, 10 bytes each item
#12-1 健保指標值1       occurs 10 times
#       Indicator01      VARCHAR(10)
#       ...
#       Indicator10     VARCHAR(10)
#12-2 健保指標值2       occurs 10 times
#       Indicator11     VARCHAR(10)
#       ...
#       Indicator20     VARCHAR(10)
#12-3 健保指標值3       occurs 10 times
#       Indicator21     VARCHAR(10)
#       ...
#       Indicator30     VARCHAR(10)
#12-4 健保指標值4       occurs 10 times
#       Indicator31     VARCHAR(10)
#       ...
#       Indicator40     VARCHAR(10)
#12-5 健保指標值5       occurs 10 times
#       Indicator41     VARCHAR(10)
#       ...
#       Indicator50     VARCHAR(10)

# *13.購買資料 00:
# 13-1 購買資料
#       Publisher	    VARCHAR(20) 1 -出品公司:友杏資訊
#       PublisherTel  VARCHAR(10) 21-出品公司電話:033700229
#       Dealer   	    VARCHAR(20) 31-經銷商
#       ProductNo	    VARCHAR(12) 51-產品序號 xx1234yyyy
#       Stations		  INT(02)	    63-安裝總機器數
#       InstallDate 	VARCHAR(10) 65-安裝日期:YYYY/MM/DD (西元)
#       ExpireDate		VARCHAR(10) 75-限用期限:YYYY/MM/DD; if 00000000, Then 無限

#*******************************************************************************
# *** 各工作站:
# * 1.一般資料 1-10:
# 1-1 登入資料
#       StatLocation    VARCHAR(10)  1-工作站位置
#       Task	          VARCHAR(04) 11-作業項目: 管理 (#51), 掛號, 診療, 批價, 藥局
#       UserPriority    VARCHAR(01) 15-使用者等級 : 進入系統後  Void
#       UserName	      VARCHAR(10) 16-使用者姓名 : 進入系統後
#       LoginTime	      VARCHAR(20) 26-YYYY/MM/DD HH:MM:SS (西元)
#       LogoutTime	    VARCHAR(20) 46-YYYY/MM/DD HH:MM:SS (西元)
#       CurrentDir      VARCHAR(35) 66-進入目錄

# 1-2 掛號資料
#       QryPatientMode	  VARCHAR(06)  1-病患基本資料查詢模式: 系統號,身份證,生日,電話,姓名
#       RegistInsType     VARCHAR(04)  7-掛號保別
#       AbsentLimitDays   INT(03)     11-預約爽約未滿天數
#       AbsentLimitTimes  INT(03)     14-預約爽約已滿次數
#           爽約未滿天數內(<=), 達到爽約次數(>=), 不得預約. (掛號不檢查 103.05.12)

# 1-3 診療資料
#       Room		          INT(02)      1-診療室: 01-10
#       Package		        INT(02)      3-用藥包數
#       PresDays		      INT(02)      5-用藥天數
#       Instruction  	    VARCHAR(40)  7-健保用藥指示
#       CasePage          INT(02)     47-診療頁次
#       PastCasePage	    INT(02)     49-過去病歷顯示頁次
#       ShowHistory	      VARCHAR(02) 51-過去病歷自動顯示: 顯示/不顯
#       RemarkCopy        VARCHAR(02) 53-過去病歷備註拷貝: 是/否 (右下方-過去病歷)
#       DataTimeStamp     VARCHAR(02) 55-診療時詞庫依時間排序: 是/否
#       TabSheetMedicines	INT(02)     57-處方頁數 1-6頁
#       SelfPrescriptCopy VARCHAR(02) 59-過去病歷健保自費處方拷貝: 是/否 (右下方-過去病歷) 104.02.25

# 1-4 處方資料
#       PrescriptSort     VARCHAR(04)  1-處方排序: 類別(MedicineType), 鍵值(PrescriptKey)
#       ShowInstruction   VARCHAR(02)  5-處方指示欄位 : 顯示/不顯/比例 16.12.15
#       ShowDosage        VARCHAR(02)  7-劑量/指示視窗: 顯示/不顯
#       DosageMode        VARCHAR(04)  9-劑量模式: 日量/次量/總量
#       DrugMixed         VARCHAR(02) 13-處方檢查提示粉藥水藥混用: 是/否
#       DrugInContinuance VARCHAR(02) 15-療程中給藥警告訊息: 是/否

# 1-5 處置資料
#       FolkMassage       VARCHAR(02)  1-傷科(自費)醫師是否親自處置-是,否(民俗調理)
#       PositionMode      VARCHAR(04)  3-針傷處置部位輸入模式: 文字(WinPosition), 圖形(WinPosFigure)
#       CompAcupuncture   VARCHAR(08)  7-成方: 針灸  (處置勾選, 自動匯入)
#       CompEAcupuncture  VARCHAR(08) 15-成方: 電針  (處置勾選, 自動匯入)
#       CompMassage       VARCHAR(08) 23-成方: 傷科  (處置勾選, 自動匯入)

# 1-6 IC卡資料
#       ICComPort       INT(02)      1-讀卡機連接埠 COM: 00-off, 01-99
#       ICReader        INT(02)      3-讀卡機 Driver 1-東元(虹堡) 2-瑛茂CR0210 3-瑛茂CR0310 4-創群
#       ICCardSevere    VARCHAR(02)  5-顯示重大傷病: 顯示/不顯 (掛號)
#       ICCardRecords   VARCHAR(02)  7-顯示 6次紀錄: 顯示/不顯 (掛號)
#       CloudUsed   	  VARCHAR(02)  9-使用雲端藥歷系統: 是/否        104.08.12
#                                      是-每次使用 WinICCard 時, 均須 Open ICComPort
#                                      否-每次使用 WinICCard 時, 不須 Open ICComPort; 進入 Medical 時, 開啟 1 次

# 1-7 相關資料
#       FontName        VARCHAR(20)  1-字型名稱
#       FontSize        INT(02)     21-字型大小
#       WaitSort        VARCHAR(08) 23-診號排序: 時間排序/診號排序 MedDoctor
#       Picture         VARCHAR(02) 31-視訊設備: 是/否
#       ShowReserve     VARCHAR(02) 33-候診名單-顯示預約名單: 顯示/不顯
#       ShowAbnormal    VARCHAR(02) 35-候診名單-顯示異常分析: 顯示/不顯
#       DocWaitStatist  VARCHAR(04) 37-候診名單-醫師診療 診次統計: 全月/當日
#       ShowChartNo     VARCHAR(06) 41-病歷號顯示: 系統號, 病歷號 (系統號為原則)
#       AddressFuzzy  	VARCHAR(02) 47-地址模糊查詢: 是/否
#       LEDComPort      INT(02)     49-叫號燈連接埠 COM: 00-off, 01-99
#       WeightComPort   INT(02)     51-體重機連接埠 COM: 00-off, 01-99
#       ExitBackup      VARCHAR(02) 53-系統右上角強迫離開備份: 是/否  105.02.24

# * 2.列表資料 1-10:
# 2-1 掛號收據1         (PrintRegist)
#       RegistMode1	    VARCHAR(04)  1-列印模式(掛號存檔): 不印, 列印, 收費, 選擇
#       RegistForm1		  VARCHAR(02)  5-收據格式: 1-5.5"套表,  2-3.0"套表
#       RegistTitle1	  VARCHAR(04)  7-收據診所名稱: 不印/列印
#       RegistMassager1 VARCHAR(04) 11-掛號收據列印理療師: 不印, 代號, 姓名, 全部(代號+姓名)
#       MassagerLabel1  VARCHAR(04) 15-掛號收據列印理療師欄位名稱: 不印/列印
#       RegistPrinterName1 VARCHAR(40) 19-掛號收據印表機名稱

# 2-2 掛號收據2
#       RegistMode2	    VARCHAR(04)  1-列印模式(掛號存檔): 不印, 列印, 收費, 選擇
#       RegistForm2		  VARCHAR(02)  5-收據格式: 1-5.5"套表,  2-3.0"套表
#       RegistTitle2	  VARCHAR(04)  7-收據診所名稱: 不印/列印
#       RegistMassager2 VARCHAR(04) 11-掛號收據列印理療師: 不印, 代號, 姓名, 全部(代號+姓名)
#       MassagerLabel2  VARCHAR(04) 15-掛號收據列印理療師欄位名稱: 不印/列印
#       RegistPrinterName2 VARCHAR(40) 19-掛號收據印表機名稱

# 2-3 預約單            (PrintReserve)
#       ReserveMode	    VARCHAR(04)  1-預約列印模式: 不印/列印
#       ReserveForm		  VARCHAR(02)  5-預約單格式
#       ReserveTitle	  VARCHAR(04)  7-收據診所名稱: 不印/列印
#       ReservePrinterName  VARCHAR(40) 11-列表機名稱

# 2-4 健保處方箋        (PrintPres)
#       PresInsMode	    VARCHAR(04)  1-處方列印模式:不印,列印,藥品,隨機,首次(處置),純自,(純)針傷
#       PresInsForm     VARCHAR(02)  5-處方箋格式  01-99
#       PresInsPrinterName  VARCHAR(40) 7-列表機名稱

# 2-5 自費處方箋        (PrintPres)
#       PresSelfMode	  VARCHAR(04)  1-處方列印模式:不印,列印,藥品,隨機,首次(處置),純自,(純)針傷
#       PresSelfForm    VARCHAR(02)  5-處方箋格式  01-99
#       PresSelfPrinterName VARCHAR(40) 7-列表機名稱

# 2-6 健保費用收據      (PrintPres)
#       ChargeInsMode	  VARCHAR(04)  1-收費列印模式:不印,列印,藥品,隨機,首次(處置),純自
#       ChargeInsForm   VARCHAR(02)  5-收費箋格式  01-99
#       ChargeInsPrinterName  VARCHAR(40) 7-列表機名稱

# 2-7 自費費用收據      (PrintPres)
#       ChargeSelfMode	VARCHAR(04)  1-收費列印模式:不印,列印,藥品,隨機,首次(處置),純自
#       ChargeSelfForm  VARCHAR(02)  5-收費箋格式  01-99
#       ChargeSelfPrinterName VARCHAR(40) 7-列表機名稱

# 2-8 健保其他收據      (PrintPres)
#       OtherInsMode	  VARCHAR(04)  1-其他列印模式:不印,列印,藥品,隨機,首次(處置),純自
#       OtherInsForm    VARCHAR(02)  5-其他箋格式  01-99
#       OtherInsPrinterName VARCHAR(40) 7-列表機名稱
# 2-9 自費其他收據      (PrintPres)
#       OtherSelfMode	  VARCHAR(04)  1-其他列印模式:不印,列印,藥品,隨機,首次(處置),純自
#       OtherSelfForm   VARCHAR(02)  5-其他箋格式  01-99
#       OtherSelfPrinterName VARCHAR(40) 7-列表機名稱

# 2-10 藥袋             (PrintPres)
#       DrugBagMode     VARCHAR(04)  1-列印模式: 不印/列印/藥品
#       DrugBagForm		  VARCHAR(02)  5-藥袋格式
#       DrugBagPrinterName  VARCHAR(40) 7-列表機名稱

# 2-11 其他相關列印
#   PrintCaseMode	  VARCHAR(04)  1-實體病歷列印模式: 連續/跳頁    void 101.10.29
#   PresMassager    VARCHAR(04)  5-處方箋列印理療師: 不印, 代號, 姓名, 全部(代號+姓名)
#   PresPrintTime   VARCHAR(04)  9-處方箋,收據列印門診時間: 不印/列印 Form 1, 2
#   PresPrintDisease VARCHAR(04)13-收費收據, 列印適應症: 不印/列印;  Form 1, 2
#   RegPrintFolk    VARCHAR(04) 17-掛號收據民俗調理(健保+民俗): 不印,列印,同張(不印),選擇(存檔)
#   DrugBagNotes    VARCHAR(04) 21-藥袋標示加印注意事項: 不印/列印 (Form53)
#   PrintRemark     VARCHAR(04) 25-處方箋-主訴列印備註: 不印/列印 原 Medicine.ini
#   PresLocation    VARCHAR(04) 29-列印處方位置: 不印, 列印 101.04.13 Form 2
#   PresTotalDosage VARCHAR(04) 33-列印處方總量: 不印, 列印 101.04.13 Form 2 電子病歷
#   ChargeInsSelf   VARCHAR(04) 37-列印收費收據(費用明細)-健保自費: 同張, 分開
#   PaperSize       VARCHAR(04) 41-QuickReport-PaperSize: 預設(Letter), A4      16.09.19

