
# 05. 候診名單檔 	100.07.01
# Relative to 病歷處方檔;   檔案每天清除

CREATE TABLE IF NOT EXISTS Wait
(
    WaitKey	    INT AUTO_INCREMENT NOT NULL,	# 候診序號
    CaseKey	    INT NOT NULL,	# 病歷序號
    CaseDate	  DATETIME NOT NULL, # 就醫日期

    PatientKey	INT NOT NULL,	# 系統號
    Name		    VARCHAR(20),	# 病患姓名

    Visit 	    VARCHAR(04),	# 初診, 複診
    RegistType  VARCHAR(10),  # 掛號類別: 一般, 預約, 撤掛    原 RegistTypex
    TreatType	  VARCHAR(10),	# 就醫類別: 一般(直接門診),     原 RegistType
                #   針灸治療, 針灸給藥, 傷科治療, 傷科給藥, 脫臼整復, 脫臼給藥,
                #   電針治療, 電針給藥, 複雜針灸, 複針給藥, 複雜傷科, 複傷給藥, 複雜骨折(複骨B57)

                # 純自費    : 民俗調理,
                # 健保      : 一般+民俗(內科), 針灸+民俗, 針藥+民俗, 傷科+民俗, 傷藥+民俗
                #             電針+民俗, 電藥+民俗
                # 代領藥    : 長期臥床(J1), 遠洋漁業(J2)
                # 其他      : 特殊, 外治, 拿藥, 同上, 自購藥,
                # 慢箋 (慢性病連續處方箋) 17.10.30

                # 巡迴醫療  : 巡迴偏遠, 巡迴山地, 巡迴離島

                # 特定疾病加強照護: 小兒氣喘, 小兒腦麻, 腦血管疾病
                #   小兒氣喘(C9), 小兒腦麻 (C0 小兒腦性麻痹)  102.03.15 陳立德
                #   腦血管疾病(CA 腦血管疾病及顱腦損傷)       103.01.01 懷恩堂
                #   乳癌照護(JE), 肝癌照護(JF, CaseType:22)   105.03.11
                #   兒童鼻炎(JG, CaseType:22)                 16.09.01

    Share 	    VARCHAR(08),	# 負擔類別:中醫:S/R10,基層醫療(S10/S20),
	                            # 重大傷病(001),低收入戶(003),榮民(004),油症(901),
      		                    # 三歲兒童(902),其他(009),職業病(006),職病初診(006),
		                          # 職病複診(006),職業傷害(006),職傷初診(006),職傷複診(006)
    InsType	    VARCHAR(04),	# 保險類別: 健保, 自費, 民俗
    Card		    VARCHAR(06),	# 健保卡號: 欠卡,061-069:職業傷害
    Continuance	INT,		      # 療程次序:01-06

    Period 	    VARCHAR(04),  # 班別: 早班, 午班, 晚班  102.02.25
    Room		    INT DEFAULT 1 NOT NULL,	# 診療室:01 - 10
    MassageRoom	INT,		      # 理療室:11 - 20

    RegistNo	  INT,		      # 就診號:000-999 (每日)
    MassageNo	  INT,		      # 理療號:000-999 (每日)

    Doctor	    VARCHAR(10),	# 醫師; 相同醫師名單用-from SchedDoctor 醫師班表
    Massager	  VARCHAR(10),	# 理療員

    DoctorDone	ENUM("False","True") NOT NULL,  # 診療結束
    MassageDone ENUM("False","True") NOT NULL, # 理療結束
    ChargeDone	ENUM("False","True") NOT NULL,  # 批價結束
    DrugDone	  ENUM("False","True") NOT NULL,  # 給藥結束

    Remark	    VARCHAR(100),	# 備註

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(WaitKey),
    INDEX(CaseKey, CaseDate, PatientKey)
) CHARACTER SET utf8;


