
# 43. 流水帳    100.07.01

CREATE TABLE IF NOT EXISTS Account
(
    AccountKey	INT AUTO_INCREMENT NOT NULL,  # 費用序號

    AccountDate Date,           # 流水帳日期
    ClassCode   VarChar(05),    # 科目代號
    ClassName   VarChar(20),    # 科目名稱

    Brief	    VarChar(20),    # 摘要
    Income      INT,            # 收入
    Expense     INT,            # 支出
    Surplus     INT,            # 結餘

    Done        VARCHAR(10),    # 結算, 未結(Blank)
    Note		VARCHAR(01),	# 註記
    Remark      VARCHAR(100),   # 備註

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(AccountKey),
    INDEX(AccountDate, ClassCode, ClassName)
) CHARACTER SET utf8;


