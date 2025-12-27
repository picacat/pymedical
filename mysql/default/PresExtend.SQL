
# 04-1. 處方擴充檔 	100.07.01

CREATE TABLE IF NOT EXISTS PresExtend
(
    PresExtendKey	INT AUTO_INCREMENT NOT NULL,  # 處方序號

    PrescriptKey    INT,	        # 處方序號  (處置簽章 存 CaseKey)
    ExtendType      VARCHAR(10),    # 類別: 處方簽章(PresSign), 處置簽章
    Content	        VARCHAR(100),	# 內容

    PRIMARY KEY(PresExtendKey),
    INDEX(PrescriptKey, ExtendType)
) CHARACTER SET utf8;


