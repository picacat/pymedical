
# 11. 初診照護  100.07.01

CREATE TABLE IF NOT EXISTS Initial
(
    InitialKey  INT AUTO_INCREMENT NOT NULL,  # 序號

    PatientKey  Int,            # 系統號
    InitialDate Date,           # 建檔日期, 初診照護日期

    Symptom     VarChar(200),   # 主訴
    PresentHistory VarChar(200),# 現病史
    PastHistory1 VARCHAR(20),   # 過去病使: 1-糖尿病   2-高血壓    3-冠心病 4-慢性阻塞性肺病
                                #           5-肺結核   6-腦中風    7-癌症   8-鼻過敏  9-氣喘
                                #          10-B型肝炎 11-慢性腎炎 12-高血脂
    PastHistory2 VarChar(200),  # 其他過去病使

#   PersonalHistory VarChar(200), 個人史
    Diet        VarChar(20),    # 飲食 1-素食 2-葷食 3-辛辣 4-冷飲 5-烤炸類
    AllergyDrug VarChar(100),   # 過敏藥物
    AllergyFood VarChar(100),   # 過敏食物

    SmokePack   Varchar(20),    # 抽煙：包/天
    SmokeYear   Varchar(20),    # 抽煙：年
    AlcoholBottle  Varchar(20), # 喝酒：瓶/天
    AlcoholYear  Varchar(20),   # 喝酒：年
    AlcoholBrand VarChar(100),  # 喝酒：酒類

    FamilyHistory1  VarChar(20),# 家族病史 1-糖尿病 2-高血壓 3-冠心病 4-腦中風 5-氣喘
                                #          6-鼻過敏 7-異位性皮膚炎
    FamilyHistory2  VarChar(200), # 其他家族病使
    FamilyCancer    VarChar(100), # 癌症種類

    BPHigh      Int,            # 收縮壓
    BPLow       Int,            # 舒張壓
    Pulse       Int,            # 脈搏
    Temperature Decimal(10, 2), # 體溫 ℃

    Conscious   VarChar(20),    # 意識 1-清醒 2-嗜睡 3-木僵 4-半昏迷 5-昏迷
    Figure      VarChar(20),    # 體格 1-肥胖 2-略胖 3-中等 4-略瘦 5-消瘦 6-壯 7-弱
    Tongue 	    VarChar(100),   # 舌診

    Smell  		VarChar(20),      # 嗅氣味：1-無異狀 2-臭
    SmellDescript VarChar(100), # 特異氣味
    Auscult     VarChar(20),    # 聽聲音：1-無異狀 2-沙啞 3-高亢 4-低微 5-氣短
    AuscultDescript VarChar(100), # 聽聲音：其他

#   問診
    Emotion	    Varchar(20),	# 情志：1-平常 2-煩躁 3-易怒 4-健忘 5-善喜
                                #       6-憂慮 7-工作或精神壓力 8-恐懼 9-易緊張
    EmotionDescript Varchar(100), # 情志：其他

    Sleep		Varchar(20),	# 睡眠：1-平常 2-難入睡 3-淺眠 4-多夢 5-易醒難再睡
                                #       6-早醒 7-徹夜不眠 8-多寐 9-常晚睡 10-睡不飽
    SleepDescript Varchar(100), # 睡眠：其他

    Face        Varchar(100),   # 五官耳鼻喉症狀說明

    Chest		Varchar(20),    # 胸部：1-無不適 2-胸悶 3-悶痛 4-脹痛 5-刺痛 6-咳血
    ChestPain	Varchar(50),    # 胸痛部位

    CoughTime	Varchar(50),    # 咳嗽時間
    CoughType	Varchar(50),    # 咳嗽性質
    SputumDescript	Varchar(50), # 痰色質量描述

    Belly		Varchar(20),	# 腹部 1-無不適 食欲（  2-正常 3-亢進 4-不佳 ）
                                #      5-泛酸   6-噯氣  7-呃逆 8-噁心 9-乾嘔  10-脹氣

    Bellyache	Varchar(50),    # 腹痛部位
    BellyacheType Varchar(20),  # 腹痛性質：1-悶痛 2-脹痛 3-絞痛 4-刺痛 5-喜按
                                #           6-拒按 7-喜熱敷
    Bowel		Varchar(20),    # 1-大便正常 2-質硬 3-顆粒 4-軟散 5-便溏
                                # 6-水瀉 7-排不淨感 8-或秘或溏 9-易便秘 10-易腹瀉
                                # 11-大便量少 12-初硬後溏
    BowelFrequency Varchar(50), # 大便 x次/x日
    Urine		Varchar(20),    # 1-小便正常 2-尿頻 3-小便不利（量少排出困難）4-尿疼 5-尿急
                                # 6-餘尿感 7-小便失禁 8-遺尿 9-漏尿 10-易尿道炎 11-小便起泡
    Micturition Varchar(50),    # 夜尿  次/夜
    Waist		Varchar(20),    # 1-無不適 2-背痛 3-腰痠 4-腰冷 5-腰重著
                                # 6-腰痛 7-腰膝無力 8-尾椎痛 9-經來酸痛
    WaistDescript Varchar(100), # 其他腰痛
    Extremity	Varchar(20),    # 四肢 1-無不適 2-疼痛 3-麻木 4-無力 5-瘦削
                                #      6-僵硬 7-抽搐 8-震顫 9-手足厥冷 10-手足心熱
    ExtremitySwell Varchar(50), # 四肢腫脹部位
    ExtremityDescript Varchar(100), # 其他四肢疼痛

    Injury	    VarChar(200),   # 相關傷病紀錄
    PulseDescript Varchar(100), # 切診脈象

    Pathologic  VarChar(200),   # 相關理學檢查
    Exam		VarChar(200),   # 相關實驗室檢驗數據

    Remark		Text,           # 其他補充說明

    Diagnosis   VarChar(200),   # 診斷
    SelfCare	VarChar(200),	# 自我照顧指導
    DietSuggest	VarChar(200),	# 飲食宜忌指導

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(InitialKey),
    INDEX(PatientKey, InitialDate)
) CHARACTER SET utf8;
