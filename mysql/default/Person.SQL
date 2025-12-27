
# 51. 人事檔	    100.07.01

CREATE TABLE IF NOT EXISTS Person
(
    PersonKey   INT AUTO_INCREMENT NOT NULL, # 系統號

    Code	      VARCHAR(10),	# 員工編號, 代碼
    Name        VARCHAR(20),
    Birthday    DATE,
    ID          VARCHAR(10),  # 身分證號
    Gender      VARCHAR(2),   # 性別: 男/女

    Address	    VARCHAR(50),	# 聯絡地址
    Telephone	  VARCHAR(15),	# 聯絡電話 (Home)
    Cellphone	  VARCHAR(15),	# 行動電話
    EMail       VARCHAR(50),	# 電子郵件

    Department  Varchar(20),  # 所屬單位
    Position	  VARCHAR(10),  # 職務: 院長, 主任, 醫師, 支援醫師, 理療師
		  	                      #       藥師, 護士, 職員, 其他
    FullTime    Varchar(10),  # 職別: 專職/兼職
    InitDate    DATE,         # 任職日期
    QuitDate    DATE,	        # 離職日期    支援到期日期 105.03.18 陳立德

    Password	  VARCHAR(06),	# 使用系統密碼
    Priority	  VARCHAR(100), # 使用系統 Y/N
    IME         VARCHAR(30),  # 中文輸入  IMEName
    HPCCardNo   VARCHAR(20),  # 醫事人員卡號
    Certificate VARCHAR(50),  # 醫師/護士/藥師 證書號碼

    College     VARCHAR(10),  # 畢業學校
    Major       VARCHAR(10),  # 科系
    Education   VARCHAR(08),  # 教育程度: 博士,碩士,大學,專科,高中,初中,小學,其他
    BankAccount Varchar(20),  # 銀行帳號

    InputDate   DATE,         # 建檔日期
    UpdateDate  DATE,	        # 更新日期

    Remark      VARCHAR(100),	# 備註
    TimeStamp   TIMESTAMP,	  # 紀錄異動日期

    PRIMARY KEY(PersonKey),
    INDEX(Code, Name, ID, Birthday)
) CHARACTER SET utf8;
#
#(
#    PersonKey	  INT AUTO_INCREMENT NOT NULL,  # 密碼序號
#    Name		    VARCHAR(10),	# 姓名
#    Code		    VARCHAR(05),	# 代碼
#    Position	  VARCHAR(10),	# 職務: 院長,主任,醫師,支援醫師,理療師
				                      #       藥師,護士,職員,其他
#    ID		      VARCHAR(10),	# 身份證號
#    Telephone	  VARCHAR(15),	# 聯絡電話
#    Cellphone	  VARCHAR(15),	# 行動電話
#    Password	  VARCHAR(06),	# 密碼
#    Priority	  INT,		      # 等級 1-9

#    IME         VARCHAR(30),  # 中文輸入
#    HPCCardNo   VARCHAR(20),  # 醫事人員卡號
#    Certificate VARCHAR(50),  # 醫師/護士/藥師 證書號碼

#    TimeStamp	TIMESTAMP,	    # 上次易動日期

#    PRIMARY KEY(PersonKey),
#    INDEX(Code)
#) CHARACTER SET utf8;

