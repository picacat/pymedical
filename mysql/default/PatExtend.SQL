
# 02-1. 基本資料擴充檔 100.07.01
CREATE TABLE IF NOT EXISTS PatExtend
(
    PatExtendKey	INT AUTO_INCREMENT NOT NULL,  # 基本資料序號

    PatientKey      INT,	          # 基本資料序號
    ExtendType      VARCHAR(10),    # 類別: 預約黑名單
    Content	        VARCHAR(100),	  # 內容

    PRIMARY KEY(PatExtendKey),
    INDEX(PatientKey, ExtendType)
) CHARACTER SET utf8;


