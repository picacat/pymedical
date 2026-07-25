

def cvt_pymedical_groups(database):
    fields = [
        'DictGroupsType', 'DictGroupsTopLevel', 'DictGroupsName'
    ]

    sql = 'TRUNCATE dict_groups'
    database.exec_sql(sql)

    data = ['主訴類別', None, '內科']
    database.insert_record('dict_groups', fields, data)
    data = ['主訴類別', None, '婦科']
    database.insert_record('dict_groups', fields, data)
    data = ['主訴類別', None, '兒科']
    database.insert_record('dict_groups', fields, data)
    data = ['主訴類別', None, '傷骨科']
    database.insert_record('dict_groups', fields, data)
    data = ['舌診類別', None, '舌質']
    database.insert_record('dict_groups', fields, data)
    data = ['舌診類別', None, '舌苔']
    database.insert_record('dict_groups', fields, data)
    data = ['舌診類別', None, '其他']
    database.insert_record('dict_groups', fields, data)
    data = ['脈象類別', None, '一般']
    database.insert_record('dict_groups', fields, data)
    data = ['脈象', '一般', '一般']
    database.insert_record('dict_groups', fields, data)
    data = ['備註類別', None, '一般']
    database.insert_record('dict_groups', fields, data)
    data = ['備註', '一般', '一般']
    database.insert_record('dict_groups', fields, data)
    data = ['辨證類別', None, '內科']
    database.insert_record('dict_groups', fields, data)
    data = ['辨證類別', None, '傷骨科']
    database.insert_record('dict_groups', fields, data)
    data = ['治則類別', None, '內科']
    database.insert_record('dict_groups', fields, data)
    data = ['治則類別', None, '傷骨科']
    database.insert_record('dict_groups', fields, data)

    data = ['健保藥品類別', None, '單方']
    database.insert_record('dict_groups', fields, data)
    data = ['健保藥品類別', None, '複方']
    database.insert_record('dict_groups', fields, data)

    data = ['藥品類別', None, '單方']
    database.insert_record('dict_groups', fields, data)
    data = ['藥品類別', None, '複方']
    database.insert_record('dict_groups', fields, data)
    data = ['藥品類別', None, '水藥']
    database.insert_record('dict_groups', fields, data)
    data = ['藥品類別', None, '外用']
    database.insert_record('dict_groups', fields, data)
    data = ['藥品類別', None, '高貴']
    database.insert_record('dict_groups', fields, data)
    data = ['藥品類別', None, '器材']
    database.insert_record('dict_groups', fields, data)

    data = ['處置類別', None, '穴道']
    database.insert_record('dict_groups', fields, data)
    data = ['處置類別', None, '處置']
    database.insert_record('dict_groups', fields, data)
    data = ['處置類別', None, '其他']
    database.insert_record('dict_groups', fields, data)
    data = ['處置類別', None, '照護']
    database.insert_record('dict_groups', fields, data)
    data = ['處置類別', None, '檢驗']
    database.insert_record('dict_groups', fields, data)
    data = ['成方類別', None, '成方']
    database.insert_record('dict_groups', fields, data)


def cvt_groups_name(database, source_db, product_type, progress_bar):
    fields = [
        'DictGroupsType', 'DictGroupsTopLevel', 'DictGroupsName'
    ]

    if product_type == 'Med2000':
        group_file = 'clinicgroups'
    else:
        group_file = 'groups'

    sql = f'''
        SELECT * FROM {group_file}
        ORDER BY GroupsType, GroupsName
    '''
    rows = source_db.select_record(sql)
    progress_bar.setMaximum(len(rows))
    progress_bar.setValue(0)
    for row in rows:
        progress_bar.setValue(progress_bar.value() + 1)

        if row['GroupsType'] in ['內科', '婦科', '傷科']:
            dict_groups_type = '主訴'
        elif row['GroupsType'] in ['內辨', '傷辨']:
            dict_groups_type = '辨證'
        elif row['GroupsType'] in ['內治', '傷治']:
            dict_groups_type = '治則'
        else:
            continue

        if dict_groups_type == '主訴':
            dict_groups_top_level = row['GroupsType']
            if dict_groups_top_level == '傷科':
                dict_groups_top_level = '傷骨科'
        elif row['GroupsType'] in ['內辨', '內治']:
            dict_groups_top_level = '內科'
        elif row['GroupsType'] in ['傷辨', '傷治']:
            dict_groups_top_level = '傷骨科'
        else:
            dict_groups_top_level = None

        dict_groups_name = row['GroupsName']

        data = [
            dict_groups_type,
            dict_groups_top_level,
            dict_groups_name
        ]
        database.insert_record('dict_groups', fields, data)


def cvt_tongue_groups(database, source_db, progress_bar):
    fields = [
        'DictGroupsType', 'DictGroupsTopLevel', 'DictGroupsName'
    ]

    sql = 'SELECT * FROM clinic WHERE ClinicType = "舌診" GROUP BY Groups ORDER BY Groups'
    rows = source_db.select_record(sql)

    progress_bar.setValue(0)
    progress_bar.setMaximum(len(rows))
    for row in rows:
        progress_bar.setValue(progress_bar.value() + 1)

        try:
            groups = row['Groups']
        except KeyError:
            groups = row['groups']

        if groups is None:
            continue

        dict_groups_type = '舌診'
        dict_groups_name = str(groups)

        if dict_groups_name.find('舌') > 0:
            dict_groups_top_level = '舌質'
        elif dict_groups_name.find('苔') > 0:
            dict_groups_top_level = '舌苔'
        else:
            dict_groups_top_level = '其他'

        data = [
            dict_groups_type,
            dict_groups_top_level,
            dict_groups_name
        ]
        database.insert_record('dict_groups', fields, data)


def cvt_pulse_groups(source_db):
    sql = 'UPDATE clinic SET groups = "一般" WHERE ClinicType = "脈象"'
    source_db.exec_sql(sql)


def cvt_remark_groups(source_db):
    sql = 'UPDATE clinic SET groups = "一般" WHERE ClinicType = "備註"'
    source_db.exec_sql(sql)


def cvt_pymedical_disease_groups(database):
    fields = [
        'DictGroupsType', 'DictGroupsTopLevel', 'DictGroupsName'
    ]

    disease_type = 'AB感染症和寄生蟲'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'A08病毒及其他特定腸道感染']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'A09感染性胃腸炎及大腸炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'A36白喉']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'A37百日咳']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'A38猩紅熱']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'A40敗血症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'A46丹毒']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'A50梅毒']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'A54淋病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'A56披衣菌感染']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'A59滴蟲病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'A60疱疹']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'A71砂眼']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'B00疱疹病毒性感染']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'B01水痘']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'B02帶狀疱疹']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'B05麻疹']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'B07病毒性疣']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'B15病毒性肝炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'B20人類免疫不全病毒疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'B26腮腺炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'B35皮癬']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'B36表淺性黴菌病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'B37念珠菌病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'B85蝨病及陰蝨']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'B86疥瘡']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'CD腫瘤'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C00唇,舌,口惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C11鼻,咽,食道惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C16胃,腸惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C21肛門及肛(門)管惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C22肝,膽,胰臟惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C23膽囊惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C24膽道惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C33呼吸系統惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C38心臟惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C40肢體骨關節惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C43惡性黑色素瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C44皮膚惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C46肉瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C47神經系統惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C50乳房惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C51女性生殖器官惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C60男性生殖器官惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C64泌尿器官惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C71腦部惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C73內分泌腺體惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C77其他惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'C91白血病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D00原位癌']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D10口及咽部之良性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D12結腸,直腸,肛門之良性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D13消化系統之良性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D15胸腔器官之良性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D16骨骼及關節軟骨之良性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D17良性脂肪瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D18血管瘤及淋巴管瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D21結締組織之良性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D22黑色素細胞痣']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D23皮膚良性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D24乳房良性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D25女性生殖器官良性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D29男性生殖器官良性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D30泌尿器官良性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D35內分泌腺體良性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D36其他良性腫瘤']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'D血液和造血器官'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D50貧血']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D69紫斑症及其他出血性病態']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D70白血球疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D73脾臟疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D75其他血液與造血器官疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'D81複合性免疫缺乏症']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'E內分泌,營養和代謝'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E00甲狀腺疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E08起因於潛在病的糖尿病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E09藥物或化學物導致之糖尿病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E10第1型糖尿病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E11第2型糖尿病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E16低血糖']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E20副甲狀腺低下症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E22腦下腺功能亢進']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E23腦下腺功能低下']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E25腎上腺性生殖疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E26高醛固酮症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E27其他腎上腺疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E28卵巢功能障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E29睪丸功能障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E30青春期疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E34其他內分泌疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E40營養不良']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E50維生素缺乏']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E61其他營養元素缺乏']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E66體重過重及肥胖']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E67營養過度']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E70胺基酸代謝疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E73乳糖酶缺乏']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E74碳水化合物代謝疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E78脂蛋白代謝疾患及其他血脂症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E79嘌呤及嘧啶代謝疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E80紫質症及膽紅素代謝疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E83礦物質代謝疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E87體液,電解質及酸鹼平衡疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'E88其他代謝疾患']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'F精神與行為'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F01失智症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F04生理狀況之精神疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F10酒精相關疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F11藥物濫用']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F17尼古丁依賴']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F20精神分裂症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F30躁症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F32鬱症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F40焦慮症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F42強迫症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F43嚴重壓力反應與適應障礙症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F44解離性和轉化症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F50飲食疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F51睡眠疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F52性功能障礙症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F60特定人格疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F63衝動疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F64性別認同疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F65性倒錯']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F70智能不足']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F80發展疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F90注意力缺失過動疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F91行為疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F93兒童或青少年期功能疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F95抽搐症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'F98兒童及青少年期行為情緒疾患']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'G神經系統與感覺器官'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G00腦膜炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G04腦炎,脊髓炎及腦脊髓炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G10舞蹈症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G11遺傳性共濟失調']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G12脊髓性肌肉萎縮及相關症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G20帕金森氏病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G24肌張力不全']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G25顫抖']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G30阿茲海默氏病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G35多發性硬化症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G40癲癇']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G43偏頭痛']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G44其他頭痛症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G45短暫性腦缺血發作症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G46腦血管症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G47睡眠疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G50三叉神經疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G51顏面神經疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G52其他腦神經疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G54神經根及神經叢疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G56上肢單一神經病變']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G57下肢單一神經病變']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G70重症肌無力及其他肌肉神經疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G71肌肉特發性疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G80嬰兒腦性麻痺']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G81偏癱']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G82下身癱瘓[截癱]及四肢癱']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G83其他麻痺性症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G89痛，他處未分類']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G90自主神經系統疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G91水腦症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'G93腦其他疾患']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'H眼睛及其附屬器官'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H00眼瞼疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H04淚道系統疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H05眼窩疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H10結膜疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H15鞏膜疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H16角膜疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H20虹膜疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H25白內障']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H27水晶體疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H30視網膜疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H40青光眼']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H43玻璃體疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H44眼球疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H47視神經疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H49斜視']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H51雙眼運動疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H52屈光調節疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H53視覺障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H54失明及低視力']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H55眼球震顫及不規則眼球運動']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H57眼睛及附屬器官其他疾患']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'H耳與乳突'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H60外耳疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H65中耳疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H68耳咽管疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H70乳突疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H71中耳膽脂瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H72鼓膜疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H74中耳乳突疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H80耳硬化症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H81前庭功能疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H83內耳疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H90耳聾']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H92耳痛及積液']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'H93耳部其他疾患']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'I循環系統'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I00風濕性心臟病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I10本態性高血壓']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I11高血壓性心臟及腎臟病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I15續發性高血壓']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I20心絞痛']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I21心肌梗塞']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I24缺血性心臟病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I26肺栓塞']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I27肺性心臟病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I28肺血管疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I30心包膜炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I34非風濕性二尖瓣疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I40心肌疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I46心跳休止']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I47心搏過速']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I48心房顫動']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I49心臟節律不整']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I50心臟衰竭']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I51其他心臟疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I60非外傷性蜘蛛網膜下腔出血']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I61非外傷性腦出血']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I63腦梗塞']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I65腦動脈阻塞及狹窄']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I67腦血管疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I69腦血管疾病後遺症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I70動脈粥樣硬化']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I71動脈瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I73末梢血管疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I74動脈栓塞及血栓症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I77其他動脈疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I78毛細血管疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I80靜脈炎及血栓靜脈炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I83下肢靜脈曲張']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I85其他部位靜脈曲張']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I88淋巴管和淋巴結疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'I95低血壓']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'J呼吸系統'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J00急性鼻咽炎（感冒）']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J01急性鼻竇炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J02急性咽炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J03急性扁桃腺炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J04急性喉炎和氣管炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J05急性阻塞性喉炎和會厭炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J06急性上呼吸道感染']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J09流行性感冒']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J12病毒性肺炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J13細菌性肺炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J18肺炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J20急性支氣管炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J22急性下呼吸道感染']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J30過敏性鼻炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J31慢性鼻炎,鼻咽炎及咽炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J32慢性鼻竇炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J33鼻息肉']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J34鼻及鼻竇疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J35慢性扁桃腺疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J37慢性喉炎及喉氣管炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J38聲帶及喉部疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J40支氣管炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J43肺氣腫']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J44慢性阻塞性肺病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J45氣喘']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J47支氣管擴張症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J60塵肺症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J68吸入外物所致之肺炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J80成人呼吸窘迫症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J81肺水腫']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J85肺和縱膈膿瘍']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J93氣胸']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J94其他肋膜病況']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'J96呼吸衰竭']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'K消化系統'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K02齲齒']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K05齒齦炎及牙周疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K09口腔部位囊腫']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K11唾液腺疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K12口腔炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K13唇及口腔黏膜疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K14舌疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K20食道炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K21胃食道逆流性疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K22食道其他疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K25胃潰瘍']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K26十二指腸潰瘍']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K27消化性潰瘍']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K29胃炎及十二指腸炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K30消化不良']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K31胃及十二指腸其他疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K35闌尾疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K40疝氣']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K50克隆氏病(局部性腸炎)']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K51結腸炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K56腸阻塞']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K57腸憩室性疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K58激躁性腸症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K59便秘及腹瀉']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K60肛門裂隙及瘻管']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K61肛門及直腸疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K63腸其他疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K64痔瘡及肛門周圍靜脈血栓']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K65腹膜疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K70酒精性肝疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K71毒性肝疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K72肝衰竭']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K73慢性肝炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K74肝纖維化及硬化']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K75發炎性肝疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K76肝其他疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K80膽結石']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K81膽囊疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K83膽管炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K85胰臟疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K90腸吸收不良']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'K92消化系統其他疾病']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'L皮膚及皮下組織'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L01膿痂疹']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L02皮膚膿瘍，癤和癰']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L03蜂窩組織炎和急性淋巴管炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L05潛毛性囊腫和瘻管']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L08皮膚及皮下組織的其他局部感染']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L10天疱瘡']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L13水疱性疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L20異位性皮膚炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L21脂漏性皮膚炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L22尿布疹']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L23接觸性皮膚炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L26剝落性皮膚炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L27內服物質所致之皮膚炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L28慢性單純苔癬和癢疹']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L30其他皮膚炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L40乾癬']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L42玫瑰糠疹']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L43扁平苔癬']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L44鱗屑性丘疹樣疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L49紅疹剝落']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L50蕁麻疹']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L51紅斑']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L55曬傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L56紫外線照射皮膚疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L60指(趾)甲疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L63圓禿落髮']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L67髮色及髮幹異常']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L68多毛症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L70痤瘡']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L71酒渣']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L72皮膚及皮下組織毛囊疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L74汗腺疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L80白斑']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L81色素沉著疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L82脂漏性角化症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L83黑棘皮症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L84雞眼及胼胝']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L85表皮增厚']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L89壓迫性潰瘍']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L90皮膚萎縮性疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L91皮膚肥厚性疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L92皮膚及皮下組織肉芽腫疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L93紅斑性狼瘡']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'L94局限性結締組織疾患']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'M肌肉骨骼系統及結締組織'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M00化膿性關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M01感染及寄生蟲所致關節感染']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M02感染後及反應性關節病變']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M05類風濕性關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M08幼年型關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M10痛風']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M11結晶性關節病變']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M12其他關節病變']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M13其他關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M14多關節病症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M16髖部骨關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M17膝部骨關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M18腕掌關節骨關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M19其他骨關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M1A慢性痛風']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M20手指及(足)趾後天性變形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M21其他後天性肢體變形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M22髕骨疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M23膝內在障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M24其他關節障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M25其他關節疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M32全身性紅斑性狼瘡']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M33皮多肌炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M34全身性硬化症(硬皮症)']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M35結締組織其他全身性侵犯']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M40脊椎後彎症及脊椎前彎症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M41脊椎側彎症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M42脊椎骨軟骨症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M43其他變形性背部病變']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M45僵直性脊椎炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M46其他發炎性脊椎病變']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M47退化性脊椎炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M48其他脊椎病變']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M50頸椎椎間盤疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M51胸椎,胸腰椎及腰薦椎椎間盤疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M53其他背部病變']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M54背痛']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M60肌炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M61肌肉鈣化及骨化']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M62肌肉其他疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M65滑膜炎及腱鞘炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M66滑膜及肌腱自發性破裂']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M67滑膜及肌腱其他疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M70過度使用及壓力軟組織疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M71其他滑囊病變']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M72纖維母細胞性疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M75肩部病灶']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M76下肢軟組織附著處病變，足除外']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M77其他軟組織附著處病變']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M80骨質疏鬆症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M83成人軟骨症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M85骨密度及構造其他疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M86骨髓炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M87骨壞死']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M88變形性骨炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M89其他骨疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M91幼年型髖部及骨盆骨軟骨症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'M93其他軟骨疾患']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'N生殖泌尿系統'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N00急性腎炎症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N02慢性腎炎症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N04腎病症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N10腎小管－間質腎炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N13阻塞性及逆流性泌尿道病變']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N17急性腎衰竭']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N18慢性腎臟疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N20腎結石及輸尿管結石']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N21下泌尿道結石']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N23未特定之腎絞痛']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N25腎小管功能不良疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N26未特定腎臟萎縮']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N28腎及輸尿管其他疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N30膀胱炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N31膀胱神經肌肉機功能障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N32其他膀胱疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N34尿道炎及尿道症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N35尿道狹窄']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N36尿道疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N39泌尿系統疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N40攝護腺疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N43陰囊水腫和精液囊腫']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N44睪丸疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N46男性不孕症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N47包皮疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N48陰莖疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N49男性生殖器官炎性疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N52男性勃起障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N53男性性功能障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N60乳房發育不良']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N61乳房疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N70輸卵管炎和卵巢炎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N71子宮及子宮頸炎性疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N73女性骨盆炎性疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N75前庭大腺疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N76陰道及女外陰其他炎症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N80子宮內膜異位症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N81女性生殖器脫垂']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N82女性生殖道瘻管']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N83卵巢,輸卵管疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N84女性生殖道息肉']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N85子宮及子宮頸非炎性疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N89陰道非炎性疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N90女外陰及會陰非炎性疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N91無月經,月經過少及稀少']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N92月經過多,頻繁且不規則']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N93子宮及陰道異常出血']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N94女性生殖器官及月經週期疼痛']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N95停經疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N96習慣性流產']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N97女性不孕症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'N98人工受孕相關併發症']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'O妊娠,生產與產褥期合併症'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O00子宮外孕']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O01葡萄胎']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O03自然流產']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O04終止妊娠']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O09高危險妊娠之監測']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O10妊娠,生產及產褥期本態性高血壓']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O11高血壓性疾患伴有加重蛋白尿']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O12妊娠性水腫及蛋白尿無高血壓']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O13妊娠性高血壓無明顯蛋白尿']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O14子癇前症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O15子癇症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O16母體高血壓']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O20早期妊娠出血']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O21妊娠孕吐']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O22妊娠靜脈併發症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O23妊娠生殖泌尿道感染']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O24妊娠,生產及產褥期糖尿病']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O25妊娠,生產及產褥期營養不良']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O26妊娠引起其他狀況的母體照護']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O368特定胎兒問題的母體照護']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O40羊水及羊膜疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O46產前出血']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O47假性陣痛']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O72產後出血']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O86產褥期感染']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O87產褥期靜脈併發症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O90產褥期併發症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O92妊娠與產褥期乳房及乳汁分泌疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'O99妊娠及產褥期母體感染']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'P源於週產期的指引'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'P58新生兒黃疸']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'Q先天性畸形,變形與染色體異常'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q00無腦症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q02小頭症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q03先天性水腦症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q04腦先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q05脊椎裂']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q06脊髓先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q07神經系統先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q11無眼症,小眼畸形及巨眼畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q17耳先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q18顏面及頸先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q20心臟先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q27血管系統先天性畸形 ']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q28循環系統先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q30鼻先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q31喉先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q32氣管和支氣管先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q33先天性肺畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q35唇腭裂']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q38舌,口腔及咽先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q39食道先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q40消化道先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q41腸先天性缺損,閉鎖狹窄與畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q50輸卵管及子宮先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q51子宮及子宮頸先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q52女性生殖器先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q53隱睪及睪丸異位']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q54尿道下裂']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q55男性生殖器先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q56性別不明及假性陰陽人']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q60腎無發育及腎其他縮減缺陷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q62先天性腎盂阻塞缺陷及輸尿管畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q63先天性腎畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q64先天性泌尿系統畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q65先天性髖部變形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q66先天性足變形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q67先天性肌肉骨骼變形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q69多指[趾]']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q70併指[趾]']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q71先天性上肢完全缺損']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q72先天性下肢完全缺損']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q73先天性肢體短縮缺陷及畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q75先天性顱骨及顏面骨畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q76先天性脊椎及骨胸廓畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q77骨發育不良及脊椎生長缺陷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q80先天性魚鱗癬']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q81水疱性表皮鬆解症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q82皮膚先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q83乳房先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q84體表先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q85斑痣性瘤症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q89其他先天性畸形']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q90唐氏症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Q91染色體異常']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'R症狀,癥候與臨床異常'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R00心搏異常']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R03異常血壓']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R04呼吸道出血']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R05咳嗽']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R06呼吸異常']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R07喉嚨痛及胸痛']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R09循環及呼吸系統症狀']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R10腹痛及骨盆痛']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R11噁心及嘔吐']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R12胸口灼熱感']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R13吞嚥不能及吞嚥困難']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R14胃腸脹氣']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R15大便失禁']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R16肝腫大及脾腫大']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R17未特定性黃疸']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R18腹水']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R19消化系統及腹部症狀']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R20皮膚感覺障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R21皮疹及其他皮膚出疹']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R22皮膚及皮下組織局部腫脹,腫塊及小腫塊']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R23皮膚改變']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R25異常不自主運動']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R26異常步態及移動性異常']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R27協同作用缺乏']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R29神經及肌肉骨骼系統症狀及徵候']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R30排尿及相關疼痛']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R31血尿']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R32尿失禁']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R33尿滯留']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R34無尿及少尿']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R35多尿']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R36尿道分泌物']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R37性功能障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R39生殖系統其他症狀及徵候']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R40嗜眠,木僵及昏迷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R41認知功能與察覺能力症狀及徵候']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R42頭暈及目眩']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R43嗅覺及味覺障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R44感覺及知覺症狀及徵候']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R45情緒狀態症狀及徵候']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R46外觀及行為症狀及徵候']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R47言語障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R48讀字困難']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R49嗓音共振異常']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R50不明原因發燒']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R51頭痛與疼痛']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R53乏力及疲勞']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R55暈厥及虛脫']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R56痙攣']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R57休克及出血']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R59淋巴結腫大']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R60水腫']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R61全身性多汗症']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R62兒童期及成人生理發育不符正常預期']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R63飲食攝取症狀及徵候']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R65全身炎症及感染症狀及徵候']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R68其他一般性症狀及徵候']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R71血液異常']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'R80尿液異常']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'ST傷害,中毒與其他外因'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S00頭部表淺損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S03頭部關節及韌帶脫臼及扭傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S04腦神經損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S06顱內損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S07頭部壓砸傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S09頭部其他損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S10頸部表淺性損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S13頸部關節及韌帶脫臼及扭傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S14頸部神經及脊髓損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S16頸部肌肉，筋膜和肌腱損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S17頸部壓砸傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S19頸部損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S20胸部表淺性損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S23胸部關節及靱帶之扭傷及脫位']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S24胸椎脊髓及神經損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S28胸部壓砸傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S30腹部,下背部和骨盆和外生殖器官表淺性損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S33腰部,腰椎,骨盆關節和韌帶脫臼,扭傷及拉傷(勞損)']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S37泌尿和骨盆腔器官傷害']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S40肩膀和上臂表淺性損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S43肩帶的關節和韌帶脫臼和扭傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S44肩部和上臂神經損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S46肩部肌肉,筋膜和肌腱損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S47肩部和上臂壓砸傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S49肩部及上臂損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S50肘部表淺損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S53手肘關節及韌帶脫臼及拉傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S54前臂區位神經損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S56前臂區位肌肉,筋膜及肌腱損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S57手肘及前臂壓砸傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S59側性手肘及前臂損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S60腕部,手部及手指表淺損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S63腕部及手部關節及韌帶脫臼及扭傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S64腕及手部位之神經損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S66腕和手位於肌肉,筋膜及肌腱損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S67腕,手部及手指壓砸傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S69腕,手及手指損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S70髖及大腿表淺性損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S72股骨閉鎖性骨折']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S73髖關節及韌帶之脫臼及扭傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S74神經在髖及大腿處損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S76髖肌肉,筋膜及肌腱在髖及大腿處之損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S77髖及大腿壓砸傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S79髖及大腿損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S80膝及小腿表淺性損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S82小腿,包括踝部閉鎖性骨折']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S83膝關節及韌帶脫臼及扭傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S84小腿神經損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S86肌肉,筋膜,跟鍵損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S87小腿壓砸(擠壓)傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S89小腿損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S90踝部,足部及腳趾表淺性損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S92足部與腳趾骨折,足踝除外']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S93踝,足,趾關節及韌帶脫臼和扭傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S94踝和足神經損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S96踝和足肌肉和肌腱損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S97踝及足部壓砸傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'S99踝部和足其他損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'T07未特定多處損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'T14身體損傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'T20頭,臉及頸程度燒傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'T21軀幹燒傷及腐蝕傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'T22肩部及上肢燒傷及腐蝕傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'T23腕及手燒傷及腐蝕傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'T24下肢燒燙傷及腐蝕傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'T25踝及足燒燙傷和腐蝕傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'T33表淺性凍傷']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'T67熱及光的影響']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'T68體溫過低']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'T69溫度降低的其他之影響']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'T71窒息']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'T76受虐及遺棄']
    database.insert_record('dict_groups', fields, data)

    disease_type = 'VWY罹病與致死之外因'
    data = ['病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'V00行人運輸工具之意外事故']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'W01在同一平面上滑倒,絆倒及踉蹌']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'W19跌倒']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'W21被運動設備撞擊或擊中']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'W22撞擊或被其他物體撞擊']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'W23被物件鉤住,壓砸,卡住或夾到']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'W50意外被人打,撞,踢,擰(扭),咬或抓(傷)']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Y80物理治療裝置備的不良事件']
    database.insert_record('dict_groups', fields, data)
    data = ['病名', disease_type, 'Y84醫療處置引起病人異常反應']
    database.insert_record('dict_groups', fields, data)


def cvt_pymedical_other_groups(source_db):
    sql = 'UPDATE clinic SET ClinicType = "辨證" WHERE ClinicType = "內辨"'
    source_db.exec_sql(sql)
    sql = 'UPDATE clinic SET ClinicType = "辨證" WHERE ClinicType = "傷辨"'
    source_db.exec_sql(sql)
    sql = 'UPDATE clinic SET ClinicType = "治則" WHERE ClinicType = "內治"'
    source_db.exec_sql(sql)
    sql = 'UPDATE clinic SET ClinicType = "治則" WHERE ClinicType = "傷治"'
    source_db.exec_sql(sql)


def cvt_disease_treat(database):
    sql = 'DELETE FROM dict_groups WHERE DictGroupsType IN ("傷骨科病名類別", "傷骨科病名")'
    database.exec_sql(sql)

    fields = [
        'DictGroupsType', 'DictGroupsTopLevel', 'DictGroupsName'
    ]

    disease_type = '01頭部'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01頭部']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02頭皮']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '03臉頰']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '04臉部']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '05眼瞼']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '06眼眶']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '07鼻']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '08耳']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '09唇']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '10顱骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '11顱內']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '12腦']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '13頷骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '14鼻骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '15鼻中膈']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '16下頷']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '17關節及韌帶']
    database.insert_record('dict_groups', fields, data)

    disease_type = '02腦神經'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01眼視神經']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02動眼神經']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '03滑車神經']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '04三叉神經']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '05外展神經']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '06顏面神經']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '07聽神經']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '08副神經']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '09腦神經']
    database.insert_record('dict_groups', fields, data)

    disease_type = '03頸部'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01頸部']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02頸椎']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '03咽喉']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '04韌帶']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '05甲狀腺']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '06頸部關節']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '07頸部其他']
    database.insert_record('dict_groups', fields, data)

    disease_type = '04胸部'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01胸部']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02乳房']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '03胸壁']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '04胸椎']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '05胸骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '06肋骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '07連枷胸']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '08胸腔']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '09心臟']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '10胸部關節']
    database.insert_record('dict_groups', fields, data)

    disease_type = '05腹部'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01腹部']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02腹壁']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '03骨盆']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '04生殖器']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '05肛門']
    database.insert_record('dict_groups', fields, data)

    disease_type = '06背部'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01背部']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02下背']
    database.insert_record('dict_groups', fields, data)

    disease_type = '07腰及骨盆'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01腰']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02腰(部)']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '03腰椎']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '04尾骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '05恥骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '06坐骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '07髖臼']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '08脊椎']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '09薦椎']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '10骼骨']
    database.insert_record('dict_groups', fields, data)

    disease_type = '08肩部'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01肩部']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02肩膀']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '03上臂']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '04肩及上臂']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '05鎖骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '06肩胛骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '07肱骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '08肩帶']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '09旋轉肌']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '10二頭肌']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '11三頭肌']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '12肩關節']
    database.insert_record('dict_groups', fields, data)

    disease_type = '09手肘'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01手肘']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02前臂']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '03尺骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '04橈骨']
    database.insert_record('dict_groups', fields, data)

    disease_type = '10腕及手部'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01腕部']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02手部']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '03腕及手']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '04腕關節']
    database.insert_record('dict_groups', fields, data)

    disease_type = '11手指'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01手指']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02拇指']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '03食指']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '04中指']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '05無名指']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '06小指']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '07指甲']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '08指骨間關節']
    database.insert_record('dict_groups', fields, data)

    disease_type = '12髖及大腿'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01髖部']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02股骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '03大腿']
    database.insert_record('dict_groups', fields, data)

    disease_type = '13膝及小腿'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01膝部']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02小腿']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '03髕股']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '04脛骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '05腓骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '06半月板']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '07膝關節']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '08脛腓關節']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '09副韌帶']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '10十字韌帶']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '11阿基里斯跟腱']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '12腓神經']
    database.insert_record('dict_groups', fields, data)

    disease_type = '14踝及足部'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01踝部']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02內踝']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '03外踝']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '04足部']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '05跟骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '06距骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '07跗骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '08蹠骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '09踝關節']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '10蹠神經']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '11足部其他關節']
    database.insert_record('dict_groups', fields, data)

    disease_type = '15腳趾'
    data = ['傷骨科病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['傷骨科病名', disease_type, '01腳趾']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '02趾骨']
    database.insert_record('dict_groups', fields, data)
    data = ['傷骨科病名', disease_type, '03趾指間關節']
    database.insert_record('dict_groups', fields, data)


def cvt_disease_common(database):
    sql = 'DELETE FROM dict_groups WHERE DictGroupsType IN ("常用病名類別", "常用病名")'
    database.exec_sql(sql)

    fields = [
        'DictGroupsType', 'DictGroupsTopLevel', 'DictGroupsName'
    ]

    disease_type = '01腦血管'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)

    data = ['常用病名', disease_type, '01蜘蛛網膜出血']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02腦出血']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03顱內出血']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04腦梗塞']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05蜘蛛網膜後遺症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06腦出血後遺症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07顱內出血後遺症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08腦梗塞後遺症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09腦血管疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10腦血管疾病後遺症']
    database.insert_record('dict_groups', fields, data)

    disease_type = '02眼耳'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01麥粒腫']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02霰粒腫']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03淚腺炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04溢淚']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05淚眼症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06乾眼症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07結膜炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08結膜疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09白內障']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10視網膜疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11青光眼']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12眼球疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13視覺障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14眼睛疼痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15外耳炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16中耳炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17梅尼爾氏症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18眩暈']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19內耳疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '20耳聾']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '21耳痛及積液']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '22耳鳴']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '23聽覺異常']
    database.insert_record('dict_groups', fields, data)

    disease_type = '03牙齒口腔食道'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01齲齒']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02齒髓炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03齒齦炎及牙周病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04唾液腺疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05口腔炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06唇及口腔黏膜疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07舌疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08食道炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09胃食道逆流']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10食道其他疾病']
    database.insert_record('dict_groups', fields, data)

    disease_type = '04呼吸胸腔'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01感冒']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02流行性感冒']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03急性上呼吸道感染']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04阻塞性喉炎會厭炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05肺炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06過敏性鼻炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07慢性鼻炎咽炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08慢性鼻竇炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09鼻息肉']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10鼻及鼻竇疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11扁桃腺慢性疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12喉氣管疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13上呼吸道其他疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14肺氣腫']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15支氣管炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16氣喘']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17支氣管擴張症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18塵肺症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19肺水腫']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '20慢性阻塞性肺病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '21間質性肺病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '22呼吸異常']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '23其他呼吸衰竭']
    database.insert_record('dict_groups', fields, data)

    disease_type = '05心臟血管'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01心臟病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02缺血性心臟病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03二尖瓣疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04心臟節律不整']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05不明確心臟病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06高血壓']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07低血壓']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08心絞痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09心肌炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10心臟肥大']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11心悸']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12心搏異常']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13心臟無力']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14末梢血管疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15動脈粥樣硬化']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16動脈瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17栓塞及血栓']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18動脈及小動脈疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19下肢靜脈曲張']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '20食道靜脈曲張']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '21其他靜脈曲張']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '22循環系統疾患']
    database.insert_record('dict_groups', fields, data)

    disease_type = '06血液及免疫'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01血小板增多症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02缺鐵性貧血']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03維生素缺乏貧血']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04葉酸缺乏貧血']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05營養性貧血']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06酵素貧血']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07地中海型貧血']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08其他貧血']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09凝血缺陷']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10紫斑症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11白血球疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12脾臟']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13免疫缺乏']
    database.insert_record('dict_groups', fields, data)

    disease_type = '07內分泌代謝'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01甲狀腺疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02第一型糖尿病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03第二型糖尿病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04胰臟疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05副甲狀腺低下']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06腦下腺功能亢進']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07腎上腺疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08卵巢功能障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09睪丸功能障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10青春期疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11其他內分泌疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12營養不良']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13維生素缺乏']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14其他元素缺乏']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15肥胖']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16血脂症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17嘌呤嘧啶代謝']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18礦物質代謝']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19新陳代謝疾患']
    database.insert_record('dict_groups', fields, data)

    disease_type = '08肝膽胰臟'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01脂肪肝']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02酒精性肝炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03酒精性肝硬化']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04病毒性肝炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05慢性肝炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06肝纖維及硬化']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07發炎性肝疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08其他肝病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09膽結石']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10膽囊炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11膽道疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12急性胰臟炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13胰臟其他疾病']
    database.insert_record('dict_groups', fields, data)

    disease_type = '09胃腸肛門'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01胃潰瘍']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02十二指腸潰瘍']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03消化性潰瘍']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04胃空腸潰瘍']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05胃炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06十二指腸炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07消化不良']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08胃其他疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09闌尾炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10局部腸炎-小腸']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11局部腸炎-大腸']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12感染性胃腸炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13其他胃腸炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14腸躁症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15便秘']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16功能性腸疾']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17腸其他疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18腸吸收不良']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19肛門及直腸']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '20痔瘡']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '21腹膜炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '22腹脹']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '23腹瀉']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '24腹痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '25胃腸息肉']
    database.insert_record('dict_groups', fields, data)

    disease_type = '10腎臟泌尿'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01急性腎炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02慢性腎炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03腎病症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04腎炎症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05腎小管']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06泌尿道病變']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07腎衰竭']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08慢性腎臟病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09血尿']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10蛋白尿']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11排尿困難']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12尿失禁']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13無尿']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14多尿']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15尿滯留']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16腎泌尿道結石']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17膀胱炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18尿道疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19泌尿道感染']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '20攝護腺增大']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '21攝護腺炎']
    database.insert_record('dict_groups', fields, data)

    disease_type = '11男性生殖'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01陰囊水腫']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02睪丸炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03不孕']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04包皮疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05陰莖疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06其他生殖器官疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07勃起障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08性功能障礙']
    database.insert_record('dict_groups', fields, data)

    disease_type = '12女性生殖'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01乳房發育不良']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02其他乳房疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03輸卵管卵巢炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04子宮炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05子宮頸炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06骨盆炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07陰道及外陰炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08子宮內膜異位']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09生殖器脫垂']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10生殖道廔管']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11卵巢囊腫']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12生殖道息肉']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13子宮疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14子宮頸疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15其他陰道疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16外陰會陰疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17白帶']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18月經過少']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19月經過多']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '20月經不規則']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '21異常出血']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '22生殖器月經疼痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '23停經疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '24習慣性流產']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '25不孕']
    database.insert_record('dict_groups', fields, data)

    disease_type = '13妊娠'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01自然流產']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02子宮外孕']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03水腫']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04蛋白尿']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05子癇症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06妊娠高血壓']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07母體高血壓']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08早期出血']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09孕吐']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10妊娠糖尿病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11泌乳疾患']
    database.insert_record('dict_groups', fields, data)

    disease_type = '14皮膚皮下'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01膿痂疹']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02膿瘍,癤及癰']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03蜂窩組織炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04皮膚皮下局部感染']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05天泡瘡']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06水泡性疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07異位性皮膚炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08濕疹']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09脂漏性皮膚炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10接觸性皮膚炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11苔蘚']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12癢疹']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13其他皮膚炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14乾癬']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15蕁麻疹']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16曬傷']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17紫外線皮膚炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18非游離輻射皮膚炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19指(趾)甲疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '20痤瘡']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '21禿髮']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '22髮色及髮幹異常']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '23多毛症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '24毛囊疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '25汗腺疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '26白斑']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '27色素沉著疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '28脂漏性角化症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '29表皮增厚']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '30紅斑性狼瘡']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '31其他皮膚疾患']
    database.insert_record('dict_groups', fields, data)

    disease_type = '15神經系統'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01腦炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02截癱及四肢癱']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03帕金森氏症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04阿茲海默症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05神經退化']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06多發性硬化症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07癲癇']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08週期性嘔吐']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09偏頭痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10頭痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11腦血管症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12睡眠疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13三叉神經疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14顏面神經疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15腦神經疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16神經根叢疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17上肢神經病變']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18下肢神經病變']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19重症肌無力']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '20嬰兒腦性麻痺']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '21偏癱']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '22麻痺症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '23脊髓疾病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '24其他神經疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '25小腦共濟失調']
    database.insert_record('dict_groups', fields, data)

    disease_type = '16肌肉骨骼'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01化膿性關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02類風濕關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03痛風']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04關節病變']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05多關節病症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06肩關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07肘關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08腕關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09腕掌關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10手部關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11髖關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12膝關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13踝足關節炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14關節痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15骨刺']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16結節狀多動脈炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17紅斑性狼瘡']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18皮多肌炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19全身性硬化症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '20結締組織全身侵犯']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '21脊椎疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '22僵直性脊椎炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '23背部病變背痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '24椎間盤疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '25腰痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '26坐骨神經痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '27神經根病變']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '28肌肉疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '29肌炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '30板機指']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '31滑膜腱鞘炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '32腱鞘囊腫']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '33軟組織疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '34筋膜炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '35肩部病灶']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '36肌痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '37骨質疏鬆']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '38成人軟骨症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '39骨髓炎']
    database.insert_record('dict_groups', fields, data)

    disease_type = '17感染'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01感染性腸胃炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02丹毒']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03白喉']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04百日咳']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05敗血症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06性病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07腦炎腦膜炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08登革熱']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09水痘']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10病毒性肝炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11腮腺炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12皮癬']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13念珠菌']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14黴菌病']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15腸道蠕蟲']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16蝨病及陰蝨']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17疥癬']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18人類免疫不全']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19帶狀疱疹']
    database.insert_record('dict_groups', fields, data)

    disease_type = '18精神與行為'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01失智症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02失憶']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03譫妄']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04精神疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05成癮症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06思覺失調']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07分裂情感']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08躁症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09重鬱症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10畏懼性焦慮症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11其他焦慮症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12歇斯底里']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13非精神病之精神疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14飲食疾患']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15睡眠障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16性功能障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17抽搐症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18遺尿屎症']
    database.insert_record('dict_groups', fields, data)

    disease_type = '19症狀異常'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01心搏異常']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02異常血壓']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03呼吸道出血']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04咳嗽']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05呼吸異常']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06喉嚨痛及胸痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07腹痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08噁心及嘔吐']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09吞嚥困難']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10胃腸脹氣']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11大便失禁']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12肝脾腫大']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13腹水']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14消化系統徵候']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15皮膚感覺障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16腫塊或腫脹']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17排尿異常']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18其他排尿異常']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19性功能障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '20嗜睡及昏迷']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '21頭暈及目眩']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '22嗅覺味覺障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '23情緒狀態']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '24語言障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '25嗓音共振異常']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '26發燒']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '27頭痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '28疼痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '29乏力及疲勞']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '30痙攣']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '31淋巴結腫大']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '32水腫']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '33多汗症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '34飲食異常']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '35蛋白尿及糖尿']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '36熱中暑']
    database.insert_record('dict_groups', fields, data)

    disease_type = '20婦科'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01月經不調']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02經前症候群']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03痛經']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04不孕症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05崩漏']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06白帶']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07更年期障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08乳房腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09乳腺炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10乳汁不足']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11安胎']
    database.insert_record('dict_groups', fields, data)

    disease_type = '21兒科'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01感冒']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02支氣管炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03鼻過敏']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04鼻竇炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05氣喘']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06口瘡']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07便秘']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08腹瀉腹痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09皮膚炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10中耳炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11黃疸']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12紫斑']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13過動症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14分離焦慮']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15週期性頭痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16過度啼哭']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17遺尿屎症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18發展遲緩']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19發育不良']

    disease_type = '22腫瘤'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01鼻咽惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02食道惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03胃惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04小腸惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05結腸惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06直腸惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07肝惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08胰臟惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09肺惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10乳房惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11子宮頸惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12子宮惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13卵巢惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14攝護腺惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15腎臟惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16膀胱惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17甲狀腺惡性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18良性脂肪瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19血管淋巴管瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '20子宮平滑肌瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '21乳房良性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '22子宮良性腫瘤']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '23卵巢良性腫瘤']
    database.insert_record('dict_groups', fields, data)

    disease_type = '23針灸科'
    data = ['常用病名類別', None, disease_type]
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '01中風後遺症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '02三叉神經痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '03顏面神經麻痺']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '04頸椎壓迫症後群']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '05下背痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '06五十肩']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '07高爾夫球肘']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '08網球肘']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '09媽媽手']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '10板機指']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '11過敏性鼻炎']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '12氣喘']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '13月經不順']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '14經痛']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '15更年期障礙']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '16精神官能症']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '17耳嗚']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '18失眠']
    database.insert_record('dict_groups', fields, data)
    data = ['常用病名', disease_type, '19減肥']
    database.insert_record('dict_groups', fields, data)
