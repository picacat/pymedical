
import datetime

from libs import nhi_utils


def get_treat_drug_count(database, calc_type, doctor):
    if calc_type == '當月':
        start_date = datetime.datetime.now().strftime('%Y-%m-01 00:00:00')
        end_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")
    else:
        start_date = datetime.datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.datetime.now().strftime('%Y-%m-%d 23:59:59')

    sql = f'''
        SELECT cases.CaseKey FROM cases
            LEFT JOIN dosage ON dosage.CaseKey = cases.CaseKey
        WHERE
            (cases.Doctor = "{doctor}") AND
            (cases.CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
            (cases.InsType = "健保") AND
            (cases.Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
            (cases.TreatType NOT IN ("居家醫療")) AND
            (cases.Share NOT IN ("山地離島")) AND
            (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
            (cases.Treatment IS NOT NULL) AND (LENGTH(cases.Treatment) > 0) AND
            (dosage.MedicineSet = 1 AND dosage.Days > 0)
    '''
    rows = database.select_record(sql)

    return len(rows)


def get_count_by_treat_type(database, table_name, calc_type, treat_type, doctor, merge_treat=False):
    if calc_type == '當月':
        start_date = datetime.datetime.now().strftime('%Y-%m-01 00:00:00')
        end_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")
        # end_date = datetime.datetime.now().strftime("%Y-%m-%d 23:59:59")
    else:
        start_date = datetime.datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.datetime.now().strftime('%Y-%m-%d 23:59:59')

    doctor_condition = ''
    if doctor not in ['全部', None]:
        doctor_condition = f'{table_name}.Doctor = "{doctor}" AND '

    if table_name == 'cases':
        if '內科' in treat_type or '一般' in treat_type:
            treat_condition = 'AND (Treatment IS NULL OR LENGTH(Treatment) <= 0)'
        else:
            treat_condition = f'AND (Treatment IN {tuple(treat_type)}) '
            if '中度複雜性針灸' in treat_type or '高度複雜性針灸' in treat_type or \
                    '中度複雜性傷科' in treat_type or '高度複雜性傷科' in treat_type or \
                    merge_treat:
                treat_condition += f'''AND
                    (Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
                    (Share NOT IN ("山地離島"))
                '''

        sql = f'''
            SELECT COUNT(CaseKey) AS Count FROM {table_name}
            WHERE
                InsType = "健保" AND
                {doctor_condition}
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                (Card IS NOT NULL) AND (LENGTH(Card) > 0) AND (Card != "欠卡")
                {treat_condition}
        '''
    else:
        if '全部' in treat_type:
            treat_condition = ''
        elif '內科' in treat_type or '一般' in treat_type:
            treat_condition = 'AND (cases.Treatment IS NULL OR LENGTH(Treatment) <= 0)'
        else:
            treat_condition = f'AND cases.Treatment IN {tuple(treat_type)}'
            # if '中度複雜性針灸' in treat_type or '高度複雜性針灸' in treat_type:
            #     treat_condition += f' AND (Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) '

        sql = f'''
            SELECT COUNT(cases.CaseKey) AS Count FROM {table_name}
                LEFT JOIN cases ON cases.CaseKey = wait.CaseKey
            WHERE
                cases.InsType = "健保" AND
                {doctor_condition}
                cases.CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡")
                {treat_condition}
        '''

    rows = database.select_record(sql)

    return rows[0]['Count']


def get_first_course(database, table_name, calc_type):
    if calc_type == '當月':
        start_date = datetime.datetime.now().strftime('%Y-%m-01 00:00:00')
        end_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")
    else:
        start_date = datetime.datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.datetime.now().strftime('%Y-%m-%d 23:59:59')

    sql = f'''
        SELECT Count(CaseKey) as Count FROM {table_name}
        WHERE
            InsType = "健保" AND
            CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
            (Continuance IS NULL OR Continuance <= 1)
    '''
    rows = database.select_record(sql)

    return rows[0]['Count']


def get_diag_days(database, doctor=None):
    start_date = datetime.datetime.now().strftime('%Y-%m-01 00:00:00')
    end_date = datetime.datetime.now().strftime("%Y-%m-%d 23:59:59")
    doctor_condition = ''
    if doctor is not None:
        doctor_condition = f'AND Doctor = "{doctor}"'

    sql = f'''
        SELECT CaseDate FROM cases
        WHERE
            InsType = "健保" AND
            CaseDate BETWEEN "{start_date}" AND "{end_date}"
            {doctor_condition}
            GROUP BY DayOfMonth(CaseDate)
    '''
    rows = database.select_record(sql)

    return len(rows)


def get_diag_case(database, doctor=None):
    exclude_type = nhi_utils.INFECTIOUS_TYPE + nhi_utils.OCCUPATIONAL_INJURY_TYPE

    start_date = datetime.datetime.now().strftime('%Y-%m-01 00:00:00')
    end_date = datetime.datetime.now().strftime("%Y-%m-%d 23:59:59")
    doctor_condition = ''
    if doctor is not None:
        doctor_condition = f'AND Doctor = "{doctor}"'

    sql = f'''
        SELECT CaseDate FROM cases
        WHERE
            InsType = "健保" AND
            CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
            Card != "欠卡" AND
            Injury NOT IN {tuple(exclude_type)} AND
            DiagFee > 0
            {doctor_condition}
    '''
    rows = database.select_record(sql)

    return len(rows)


def get_max_treat(database, doctor=None):
    return get_diag_days(database, doctor) * nhi_utils.TREAT_SECTION2
