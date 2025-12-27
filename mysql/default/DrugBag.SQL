
# 12. 藥袋標示檔 	100.07.01

CREATE TABLE IF NOT EXISTS DrugBag
(
    DrugBagKey	INT AUTO_INCREMENT NOT NULL,  # 藥袋序號
    CaseKey	    INT NOT NULL,	  # 病歷序號
    MedicineSet	INT,		        # 組別: 1-健保 2~5-自費  //99-自購  51-飲食禁忌

    DiseaseName VARCHAR(50),    # 適應症            飲食禁忌 1  SysRestrict
    Factory     VARCHAR(50),    # 藥廠名            飲食禁忌 2
    Preserved   VARCHAR(50),    # 藥品保存方式      飲食禁忌 3
    ValidDate   VARCHAR(50),    # 有效期限          飲食禁忌 4
    SideEffect  VARCHAR(50),    # 副作用            飲食禁忌 5
    Warning     VARCHAR(50),    # 警語              飲食禁忌 6

    TimeStamp	TIMESTAMP,	     # 上次異動日期

    PRIMARY KEY(DrugBagKey),
    INDEX(CaseKey)
) CHARACTER SET utf8;


