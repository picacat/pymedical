
# 39. 驗方 主檔     100.07.01   一品堂

CREATE TABLE IF NOT EXISTS Experience
(
    ExperienceKey   INT AUTO_INCREMENT NOT NULL,	# 驗方序號

    ExpCode	        VARCHAR(15),	# 驗方碼
    InputCode	      VARCHAR(05),	# 輸入碼
    ExpICDCode	    VARCHAR(10),	# 病名碼 ICD9 / ICD10 5->10 103.09.10
    ExpICDName	    VARCHAR(40),	# 病名

    ExpName	        VARCHAR(40),	# 驗方名稱
    ExpMedicineName	VARCHAR(50),	# 方劑名稱

    ExpSymptom	    BLOB,	# 主訴
    ExpTongue	    BLOB,	# 舌診
    ExpPulse 	    BLOB,	# 脈象
    ExpDistincts    VARCHAR(40),	# 辨證
    ExpCure	        VARCHAR(40),	# 治則

    ExpPackage	    INT,		    # 給藥包數; 健保 / 自費
    ExpPresDays	    INT,		    # 給藥日份(帖數); 處方即一天量/一帖量
    ExpInstruction  VARCHAR(10),    # 用藥指示: 飯後,飯前,先煎,後下,沖服,包煎

    Health	        BLOB,		    # 衛教資料;  原 ExpRemark 檔;  衛教圖片於 Picture
    Remark	        BLOB,  # 備註

    TimeStamp	    TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(ExperienceKey),
    INDEX(ExpCode)
) CHARACTER SET utf8;





