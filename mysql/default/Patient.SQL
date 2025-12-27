
# 02. 基本資料檔    100.07.01

CREATE TABLE IF NOT EXISTS Patient
(
    PatientKey  INT AUTO_INCREMENT NOT NULL, # 系統號 (初診預約-999,999; 參考病歷-999,998; 自購藥-999,997)
    CardNo      VARCHAR(12),    # 健保IC卡卡片號碼
    ChartNo     VARCHAR(10),    # 病歷號        原 RegistNo
    Name        VARCHAR(20),    # 病患姓名
    Era         VARCHAR(01),    # 年號 民國前: - / Blank    void 16.05.01
    Birthday    DATE,           # 出生日期
    ID          VARCHAR(10),    # 身份證號

    Nationality VARCHAR(04),    # 國籍
    Gender      VARCHAR(04),    # 性別          原 Sex
    Telephone	  VARCHAR(15),	  # 聯絡電話 (Home)
    Officephone VARCHAR(15),	  # 聯絡電話 (Office)
    Cellphone	  VARCHAR(15),	  # 行動電話
    Email       VARCHAR(50),

    ZipCode	    VARCHAR(05),	  # 郵遞區號
    Address	    VARCHAR(50),	  # 聯絡地址
    Marriage	  VARCHAR(10),	  # 婚姻狀況: 已婚, 未婚, 單身
    Education	  VARCHAR(10),	  # 教育程度: 國小, 國中, 高中, 大專, 碩士, 博士
    Occupation  VARCHAR(10),	  # 職業類別: 工,商,農漁業, 軍公教, 自由業, 服務業, 其他

    DiscountType VARCHAR(20),	  # 優待類別: 榮民, 福保(低收入戶), 重大傷病, 職業傷害,
                                # (掛號費)  員工, 眷屬, 親友, 老人, 其他
#    DiscountType VARCHAR(20),	# 優待類別: 員工,眷屬,親友,殘障,僧侶, 教友,老人,榮民,福保
                                #       VIP, 一般   void 103.04.07 以樂
    DiscountReason VARCHAR(40),	# 優待原因: 在職員工姓名

    InsType	      VARCHAR(10),	  # 保險:健保, 自費, 榮民, 低收入戶(福保), 重大傷病
    PrivateInsurance VARCHAR(10), # 民間保險:國泰人壽,新光人壽, ...

    FamilyPatientKey VARCHAR(10), # 家族代表: 以系統號為主
    Reference	    VARCHAR(10),	  # 介紹人 / 聯絡人, 家族?
    Trace 	      VARCHAR(02),	  # 可否追蹤: 是, 否
    TraceTime	    VARCHAR(04),	  # 追蹤時間: 日間, 晚上,早上,中午,下午
    TraceType	    VARCHAR(10),	  # 追蹤方式: 電話, 郵寄

    InitDate	    DATETIME,	      # 初診日期
    LastDate	    DATETIME,	      # 上次門診

    Allergy	      BLOB,	          # 過敏
    History	      BLOB,	          # 病史
    Description   BLOB,	          # 特殊用途: 以樂 16.07.13 雲端藥歷

    Remark	      BLOB,	          # 備註
    Note		      VARCHAR(01),	  # 註記

    TimeStamp     TIMESTAMP,	    # 紀錄異動日期

    PRIMARY KEY(PatientKey),
    INDEX(Birthday)
) CHARACTER SET utf8;
