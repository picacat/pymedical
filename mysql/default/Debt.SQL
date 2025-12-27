
# 08. 欠款檔    100.07.01

CREATE TABLE IF NOT EXISTS Debt
(
    DebtKey	    INT AUTO_INCREMENT NOT NULL,  # 欠款序號
    CaseKey	    INT NOT NULL,	# 病歷序號
    PatientKey	INT NOT NULL,	# 系統號 (基本資料)
    DebtType	VARCHAR(10),	# 欠款類別: 掛號欠款, 批價欠款
    Name		    VARCHAR(10),	# 病患姓名
    CaseDate	  DATETIME,	    # 欠款日期
    Period 	    VARCHAR(04),	# 欠款班別: 早班, 午班, 晚班
    Doctor	    VARCHAR(10),	# 醫師姓名
    Fee		      INT,		      # 門診當日實際欠款金額

#   最多三次還款
    ReturnDate1	DATETIME,	    # 還款日期1
    Period1	    VARCHAR(04),	# 還款班別1
    Cashier1   	VARCHAR(10),	# 收費員1
    Fee1		    INT,		      # 還款費1

    ReturnDate2	DATETIME,	    # 還款日期2
    Period2	    VARCHAR(04),	# 還款班別2
    Cashier2	  VARCHAR(10),	# 收費員2
    Fee2		    INT,		      # 還款費2

    ReturnDate3	DATETIME,	    # 還款日期3
    Period3	    VARCHAR(04),	# 還款班別3
    Cashier3	  VARCHAR(10),	# 收費員3
    Fee3		    INT,		      # 還款費3

    TotalReturn	INT,		      # 還款合計. 結清: 還款 >= 欠款
				                      #	    尚欠: 還款 <  欠款
				                      # 尚欠金額 = 欠款 - 還款; 隨時存入病歷資料檔

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(DebtKey),
    INDEX(CaseKey, PatientKey, CaseDate)
) CHARACTER SET utf8;


