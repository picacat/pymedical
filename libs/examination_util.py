
from libs import string_utils


# 檢查項目
EXAMINATION_LIST = [
    ['身體檢查', 'Systolic B.P.', '收縮壓', None, 139, 'mm/Hg', None],
    ['身體檢查', 'Diastolic B.P.', '舒張壓', None, 89, 'mm/Hg', None],
    ['身體檢查', 'Pulse', '脈搏', 55, 99, '次/分', None],
    ['身體檢查', 'Height', '身高', None, None, '公分', None],
    ['身體檢查', 'Weight', '體重', None, None, '公斤', None],
    ['身體檢查',
        'BMI', '身體質量指數', 18.5, 24, None,
        '過重：24≦BMI＜27 輕度肥胖：27≦BMI＜30 中度肥胖：30≦BMI＜35 重度肥胖：BMI≧35'
     ],

    ['血液檢查', 'W.B.C. Count', '白血球計數', 4.0, 9.8, '10^3/uL', None],
    ['血液檢查', 'R.B.C. Count', '紅血球計數', 4.2, 6.2, '10^6/uL', None],
    ['血液檢查', 'Hemoglobin', '血色素', 12.9, 18, 'gm/dL', None],
    ['血液檢查', 'Hematocrit', '血球容積比值', 38, 53, '%', None],
    ['血液檢查', 'M.C.V.', '紅血球平均體積', 80, 98, 'fL', None],
    ['血液檢查', 'M.C.H.', '紅血球平均血紅素', 27, 33, 'pg', None],
    ['血液檢查', 'M.C.H.C.', '平均血色素濃度', 31, 36, 'g/dL', None],
    ['血液檢查', 'Platelet', '血小板計數', 120, 400, '10^3/uL', None],
    ['血液檢查', 'Neturophil Segment', '嗜中性白血球', 42, 74, '%', None],
    ['血液檢查', 'Lymphocyte', '淋巴球', 20, 56, '%', None],
    ['血液檢查', 'Monocyte', '單核球', 0, 12, '%', None],
    ['血液檢查', 'Eosinophilic', '嗜伊紅白血球', 0, 5, '%', None],
    ['血液檢查', 'Basophilic', '嗜鹹性白血球', 0, 2, '%', None],

    ['肝功能', 'S.G.O.T (AST)', '麩草轉氨基脢', 0, 39, 'U/L', None],
    ['肝功能', 'S.G.P.T (ALT)', '麩丙酮轉氨基脢', 0, 41, 'U/L', None],
    ['肝功能', 'r-GTP (GGT)', '丙種麩晞轉移酵素', 9, 64, 'U/L', None],
    ['肝功能', 'ALK-P', '鹼性磷酸脢', 34, 104, 'U/L', '9-15歲上限為4倍'],

    ['肝功能', 'Total Bilirubin', '總膽紅素值', 0.30, 1.00, 'mg/dl', None],
    ['肝功能', 'Direct Bilirubin', '直接膽紅素', 0.03, 0.18, 'mg/dL', None],
    ['肝功能', 'Total Protein', '總蛋白', 6.4, 8.9, 'g/dl', None],
    ['肝功能', 'Albumin', '白蛋白', 3.5, 5.7, 'g/dl', None],
    ['肝功能', 'Globulin', '球蛋白', 2.0, 4.0, 'g/dl', None],
    ['肝功能', 'A/G Ratio', '蛋白比值', 1.1, 2.5, 'g/dl', None],

    ['腎功能', 'B.U.N.', '尿素氮', 7, 25, 'mg/dl', None],
    ['腎功能', 'Creatinine', '肌酸酐', 0.2, 1.3, 'mg/dl', None],
    ['腎功能', 'e-GFR', '腎絲球過濾率', 90, None, 'ml/min/1.7', '>=90正常; 60-89.9依臨床判定; 30-59.9中度腎病變; 15-29.9重度腎病變'],

    ['特殊尿液', 'Micro albumin', '尿中微量白蛋白', None, 3.0, 'mg/dL', None],
    ['特殊尿液', 'Urine protein', '尿中蛋白質濃度', None, 21, 'mg/dL', None],
    ['特殊尿液', 'Urine creatinine', '尿中肌酸酐濃度', 60, 250, 'mg/dL', None],
    ['特殊尿液', 'Ur-ACr', '尿中微蛋白/肌酸酐', None, 30, 'mg/g', None],
    ['特殊尿液', 'UR-P.CR', '尿中蛋白/肌酸酐', None, 150, 'mg/g', None],

    ['痛風指標', 'Uric Acid', '尿酸', 4.4, 7.6, 'mg/dl', None],

    ['血糖檢查', 'AC Sugar', '空腹血糖', 60, 99, 'mg/dl', '60-99正常; 100-125空腹血糖耐受不良'],
    ['血糖檢查', 'HbA1c', '糖化血色素', None, 5.6, 'mg/dl', '<=5.6正常; 5.7-6.4糖尿病前期'],

    ['胰臟檢查', 'Amylase', '胰澱粉酵素', 29, 103, 'U/L', None],

    ['酯肪檢查', 'Total Cholesterol', '血清總膽固醇', None, 200, 'mg/dl', None],
    ['酯肪檢查', 'Triglyceride', '三酸甘油酯', None, 150, 'mg/dl', None],
    ['酯肪檢查', 'HDL Cholesterol', '高密度膽固醇', 40, None, 'mg/dl', None],
    ['酯肪檢查', 'LDL Cholesterol', '低密度脂蛋白膽固醇', None, 130, 'mg/dl', None],

    ['電解質', 'Sodium [Na]', '鈉離子', 136, 146, 'meq/L', None],
    ['電解質', 'Potassium [K]', '鉀離子', 3.5, 5.5, 'meq/L', None],
    ['電解質', 'Calcium [Ca]', '血中鈣', 8.6, 10.3, 'mg/dl', None],
    ['電解質', 'Phosphorus [P]', '血中磷', 2.5, 5.0, 'mg/dl', None],

    ['尿液檢查', 'Color', '尿顏色', 'Yellow', 'Yellow', None, None],
    ['尿液檢查', 'Protein', '尿蛋白', '-', '-', None, None],
    ['尿液檢查', 'Sugar', '尿糖', '-', '-', None, None],
    ['尿液檢查', 'Urobilinogen', '尿膽素元', 'Normal', 'Normal', None, None],
    ['尿液檢查', 'Bilirubin', '尿膽紅素', '-', '-', None, None],
    ['尿液檢查', 'Ketones', '尿丙酮', '-', '-', None, None],
    ['尿液檢查', 'PH', '尿酸鹼度', 5.0, 8.0, 'Ph', None],
    ['尿液檢查', 'OB', '潛血反應', '-', '-', None, None],
    ['尿液檢查', 'U-RBC', '尿紅血球', 0, 4, 'HPF', None],
    ['尿液檢查', 'U-WBC', '尿白血球', 0, 4, 'HPF', None],
    ['尿液檢查', 'Epithelial Cells', '上皮細胞', 0, 4, 'HPF', None],
    ['尿液檢查', 'Pus Cell', '膿細胞', 0, 1, 'HPF', None],
    ['尿液檢查', 'Crystal', '結晶體', '-', '-', 'HPF', None],
    ['尿液檢查', 'Cast', '尿圓柱', '-', '-', 'HPF', None],
    ['尿液檢查', 'Bacteria', '細菌', '-', '-', 'HPF', None],
    ['尿液檢查', 'Specific Gravity', '比重', 1.000, 1.030, None, None],
]


def get_examination_item_html(database, examination_key, groups):
    examination_item_list = []
    for row in EXAMINATION_LIST:
        if row[0] == groups:
            examination_item_list.append([row[1], row[2], row[5]])

    item_html = ''

    for item in examination_item_list:
        english_item = string_utils.xstr(item[0])
        chinese_item = string_utils.xstr(item[1])
        unit = string_utils.xstr(item[2])

        sql = f'''
            SELECT TestResult FROM examination_item
            WHERE
                ExaminationKey = {examination_key} AND
                ExaminationItem = "{chinese_item}"
        '''
        rows = database.select_record(sql)

        if len(rows) <= 0:
            test_result = ''
        else:
            test_result = string_utils.xstr(rows[0]['TestResult'])

        item_html += f'''
            <tr>
                <td>{english_item}</td>
                <td>{chinese_item}</td>
                <td align="center">{test_result}</td>
                <td align="center">{unit}</td>
            </tr>
        '''

    return item_html


def get_examination_html(database, examination_key):
    examination_groups = []
    for row in EXAMINATION_LIST:
        groups = row[0]
        if groups not in examination_groups:
            examination_groups.append(groups)

    groups_html = ''
    for groups in examination_groups:
        item_html = get_examination_item_html(database, examination_key, groups)
        groups_html += f'''
            <tr bgcolor="LightGray">
                <td colspan="4"><center>{groups}</center></td>
            </tr>
            {item_html}
        '''

    html = f'''
        <html>
          <body>
            <h4><center>檢驗報告</center></h4>
            <br>
            <table align=center cellpadding="2" cellspacing="0" width="98%"
             style="border-width: 1px; border-style: solid;">
              <thead>
                <tr bgcolor="LightGray">
                <th>英文名稱</th>
                <th>中文名稱</th>
                <th>檢驗結果</th>
                <th>單位</th>
              </thead>
              <tbody>
                {groups_html}
              </tbody>
            </table>
          </body>
        </html>
    '''

    return html
