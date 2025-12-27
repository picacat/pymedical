
# 09. 圖形檔主檔  105.01.12
# For Patient, Cases, Experience(驗方) Created 101.12.21 Medical.Picture 稍不同

CREATE TABLE IF NOT EXISTS Picture
(
    PictureKey  INT AUTO_INCREMENT NOT NULL,    # 圖形序號

    PatientKey	INT,	        # 系統號
    Name	      VARCHAR(10),	# 病患姓名
    CaseKey	    INT,		      # 病歷序號
    CaseDate	  DATETIME,     # 就醫日期

    PictureType VARCHAR(10),  # 類別: 基本資料, 病歷資料, 驗方資料
#    Image  	    LONGBLOB,  	# 圖片      原 PictureName VarChar(100) -> Image LONGBLOB
                              # void 105.01.12

    TimeStamp   TIMESTAMP,	  # 紀錄異動日期

    PRIMARY KEY(PictureKey),
    INDEX(PatientKey, CaseKey)
) CHARACTER SET utf8;
