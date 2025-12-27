
# 圖形檔 	16.07.06  黃政平  used MySQL/Med2000    (Structure 類似 Medical)

CREATE TABLE Image
(
    ImageKey    INT AUTO_INCREMENT NOT NULL,    # 圖形序號
    PatientKey	INT,	        # 系統號
    Name		    VARCHAR(20),	# 病患姓名

    CaseKey	    INT,		      # 病歷序號    黃政平 not used
    CaseDate	  DATETIME,     # 就醫日期

    ImageType   VARCHAR(04),  # 類別: 基本, 病歷
    ImageName   VARCHAR(100), # 圖片檔名    路徑 from ControlRecord
        # 基本資料 FileName: '基本' + PatientKey(6) + '-' + CaseDate(14) + '.JPG'
        #          CaseDate: Datetime 20160701123456
        # 病歷資料 FileName: '病歷' + PatientKey(6) + '-' + CaseDate(14) + '.JPG'
        #          CaseDate: Datetime 20160701123456

    TimeStamp   TIMESTAMP,	  # 紀錄異動日期

    PRIMARY KEY(ImageKey),
    INDEX(PatientKey, CaseKey)
) CHARACTER SET utf8;
