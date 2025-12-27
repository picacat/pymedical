
# 2022.11.05 申復檔

CREATE TABLE IF NOT EXISTS InsReply
(
    InsReplyKey	        INT AUTO_INCREMENT NOT NULL,  # 健保申復序號

    ClinicID	        VARCHAR(10),    # 院所代號
    ApplyDate	        VARCHAR(05),	# 費用年月: YYYMM
    ApplyPeriod	        VARCHAR(06),	# 申報期間: 全月(新),上半月(舊院所),下半月(新院所)
    ApplyType	        VARCHAR(01),	# 申報類別: 1-送核  2-補報
    CaseType	        VARCHAR(02),	# 案件分類: 21-一般 ...
    Sequence            INT,		    # 流水號
    Sample	            VARCHAR(10),	# 樣本註記: 0-統扣 1-立意 2-歸戶 3-隨機 4-全審
    Point1	            INT,	        # 立意抽樣受理點數
    Point2	            INT,	        # 電腦核減受理點數
    Point3	            INT,	        # 回推核減受理點數
    Reject	            VARCHAR(10),	# 整件核減: Y-整件核減 不填-無整件核減

    OrderSeq	        INT,	        # 醫令序號
    InsCode	            VARCHAR(12),	# 醫令代碼
    ChangeSeq           INT,	        # 改支序號
    Percent             INT,		    # 醫令受理成數: 090, 100, 105
    Quantity            INT,		    # 醫令受理數量
    Point               INT,		    # 醫令受理點數
    FileLink	        VARCHAR(2),	    # 醫令申復檔案連結 Y/N
    Reason1	            VARCHAR(1000),  # 醫令申復理由1
    Reason2	            VARCHAR(1000),  # 醫令申復理由2

    RejectCode	        VARCHAR(10),	# 核減代碼
    ReplyPercent        INT,		    # 申復成數: 090, 100, 105
    ReplyQuantity	    INT,		    # 申復數量
    ReplyPoint	        INT,		    # 申復數點數
    ReplyFileLink	    VARCHAR(2),	    # 申復檔案連結 Y/N
    ReplyReason1	    VARCHAR(1000),  # 申復理由1
    ReplyReason2	    VARCHAR(1000),  # 申復理由2

    Note		        VARCHAR(01),	# 註記, 列印用
    Message	            VARCHAR(40),	# 錯誤訊息

    TimeStamp	      TIMESTAMP,    # 上次異動日期

    PRIMARY KEY(InsReplyKey),
    INDEX(ApplyDate, CaseType, Sequence)
) CHARACTER SET utf8;

