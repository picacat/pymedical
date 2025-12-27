
# 30-自購藥處方檔 	100.12.05 廣佑  保留暫不用

CREATE TABLE IF NOT EXISTS Purchase
(
    PurchaseKey	  INT AUTO_INCREMENT NOT NULL,  # 處方序號
    CaseKey	      INT NOT NULL,	  # 病歷序號
    PatientKey	  INT,	          # 系統號

    CaseDate	    DATETIME,	      # 門診日期
    InvoiceNo	    VARCHAR(20),	  # **單據號碼                                    94.04.24
    MedicineMode	VARCHAR(20),	  # **產品類型 /劑型: (丸劑, 水藥, 保養藥)        94.04.24

    MedicineSet	  INT,		        # 組別:1-健保,自費 2,3-自費             //自購:0
    MedicineType	VARCHAR(04),	  # 類別(詞庫為準): 單方,複方,水藥,外用
				                          #   高貴,藥丸,穴道,處置,器材,檢驗,檢自
    MedicineKey	  INT,		        # 詞庫處方序號
    MedicineCode	VARCHAR(05),	  # 處方碼
    MedicineName	VARCHAR(40),	  # 處方名稱

    Dosage	      DECIMAL(10,2),	# 藥品用量; 健保:日劑量; 自費:一帖(包)劑量
    Unit		      VARCHAR(10),	  # 單位
    Instruction   VARCHAR(20),	  # 用藥指示

    Price 	      DECIMAL(10,2),	# 單價
    Amount	      DECIMAL(10,2),	# 金額
    ReceiptFee	  DECIMAL(10,2),	# **實收金額         94.04.24

    ReturnDate1	  DATETIME,	      # 還款日期1
    Period1	      VARCHAR(04),	  # 還款班別1
    Cashier1	    VARCHAR(10),	  # 收費員1
    ReturnFee1  	DECIMAL(10,2),	# 還款費1

    ReturnDate2	  DATETIME,	      # 還款日期2
    Period2	      VARCHAR(04),	  # 還款班別2
    Cashier2	    VARCHAR(10),	  # 收費員2
    ReturnFee2	  DECIMAL(10,2),	# 還款費2

    ReturnDate3	  DATETIME,	      # 還款日期3
    Period3	      VARCHAR(04),	  # 還款班別3
    Cashier3	    VARCHAR(10),	  # 收費員3
    ReturnFee3	  DECIMAL(10,2),  # 還款費3

    Buyer         VARCHAR(20),    # 購藥者    Patient Name
    Vender        VARCHAR(20),    # 售藥者
    Doctor        VARCHAR(20),    # **醫師售藥者       94.04.24
    Massager      VARCHAR(20),    # **推拿師售藥者     94.04.24
    Register      VARCHAR(20),    # **掛號售藥者       94.04.24

    Remark        VARCHAR(100),   # **備註             94.04.24

    TimeStamp	    TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(PurchaseKey),
    INDEX(CaseDate, Vender, Buyer, MedicineKey)
) CHARACTER SET utf8;


