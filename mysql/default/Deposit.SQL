
# 07. 欠卡檔	100.07.01

CREATE TABLE IF NOT EXISTS Deposit
(
    DepositKey	INT AUTO_INCREMENT NOT NULL,  # 欠卡序號

    CaseKey	    INT NOT NULL,	# 病歷序號 (病歷資料)
    PatientKey	INT NOT NULL,	# 系統號 (基本資料)
    Name		VARCHAR(10),	    # 病患姓名

    DepositDate	DATETIME,	    # 欠卡日期
    ReturnDate	DATETIME,	    # 還卡日期
    Period	    VARCHAR(04),	# 還卡班別: 早班, 午班, 晚班
    Register	VARCHAR(10),	  # 收費員: 掛號收費
    Refunder	VARCHAR(10),	  # 還卡員: 掛號還款
    Fee	        INT,		      # 欠卡費 / 還卡費

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(DepositKey),
    INDEX(CaseKey,PatientKey, DepositDate, ReturnDate)
) CHARACTER SET utf8;

#	Functions: 還卡, 查詢, 增補, 修正, 刪除, 收據, 離開
#			   修正: 修正金額, 已還 => 未還
		
