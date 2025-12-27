
# 34. 詞庫藥品檔    100.07.01

CREATE TABLE IF NOT EXISTS Medicine
(
    MedicineKey	    INT AUTO_INCREMENT NOT NULL,  # 藥品序號
    MedicineType	  VARCHAR(04),	# 類別: 單方,複方,水藥,外用,高貴,藥丸,
				                          #	      穴道,處置,器材,成方, 檢驗, 檢自
                                  #       照護: 16.09.01 特定疾病加強照護, 配合劑型MedicineMode

    MedicineMode	  VARCHAR(20),	# 劑型: 解表,辛溫 ...
                                  #       檢驗-常用,罕用
                                  #       小兒氣喘, 小兒腦性麻痹: 102.03.15, 陳立德  Palsy
                                  #       癌症照護(JE,JF)    16.09.01
                                  #       兒童鼻炎(JG, 照護) 16.09.01

    MedicineCode  	VARCHAR(15),	# 處方碼 for BarCode
    InputCode	      VARCHAR(05),	# 輸入碼 (注音碼)
    InsCode	        VARCHAR(12),	# 健保碼
    MedicineName	  VARCHAR(40),	# 處方名稱
    MedicineAlias	  VARCHAR(40),	# 處方別名
    Unit		        VARCHAR(10),	# 單位: 克, 錢, ... 檢驗

    Dosage          Decimal(10, 2), # 預設劑量 (103.12.12 九條城)
    MinDosage          Decimal(10, 2), # 最低劑量
    MaxDosage          Decimal(10, 2), # 最高劑量
    Location        VARCHAR(20),    # 置放位置      93.03.31

    SalePrice	      Decimal(10, 2),	# 售價
    InPrice	        Decimal(10, 2), # 進價
    Charged         VARCHAR(04),	  # 計價方式: 單日, 藥日(計價)  103.12.25 九條城

    Quantity	      Decimal(10, 2),	# 庫存量
    SafeQuantity	  Decimal(10, 2),	# 安全存量
    Description	    BLOB,           # 複方說明 (方劑)

    TimeStamp	      TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(MedicineKey),
    INDEX(InsCode, InputCode)
) CHARACTER SET utf8;

