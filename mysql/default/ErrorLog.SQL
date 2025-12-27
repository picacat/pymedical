
# xx. 103.06.16 錯誤檔

CREATE TABLE IF NOT EXISTS ErrorLog
(
    ErrorLogKey	  INT AUTO_INCREMENT NOT NULL,  # 錯誤序號

    ErrorFile     VARCHAR(20),	# Regist, Case1 ...
    ErrorKey      INT,	        # CaseKey, PatientKey, ...
    ErrorDate     DateTime,     #
    Description   VARCHAR(100),

    TimeStamp	  TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(ErrorLogKey),
    INDEX(ErrorFile, ErrorKey)
) CHARACTER SET utf8;

#===================================================================

