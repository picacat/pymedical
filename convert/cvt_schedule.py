import mysql.connector as mysql
import progressbar
import time

cnx = mysql.connect(
    host='localhost',
    user='root',
    password='620210',
    charset='utf8',
    port='3306',
    buffered=True,
    database='st',
)
cursor = cnx.cursor(dictionary=True)

physiotherapy = '許明選'


def convert_patient():
    cursor.execute('truncate temp_patient')

    cursor.execute('select * from schedule_patient order by PatientKey')
    rows = cursor.fetchall()

    bar = progressbar.ProgressBar()
    bar.max_value = len(rows)
    for row_no, row in enumerate(rows):
        bar.update(row_no)
        patient_key = row['PatientKey']
        name  = row['Name']
        sql = f'''
            insert into temp_patient
            (TempPatientKey, Name)
            values 
            ({patient_key}, "{name}")
        '''
        try:
            cursor.execute(sql)
        except Exception:
            pass

    bar.update(len(rows))


def convert_schedule():
    cursor.execute('truncate physiotherapy_schedule')

    cursor.execute('select * from schedule order by CaseDate')
    rows = cursor.fetchall()

    bar = progressbar.ProgressBar()
    bar.max_value = len(rows)
    for row_no, row in enumerate(rows):
        bar.update(row_no)
        patient_key = row['PatientKey']
        name = row['Name']
        case_date = row['CaseDate'].strftime('%Y-%m-%d')
        case_time = row['CaseDate'].strftime('%H:%M')
        sql = f'''
            insert into physiotherapy_schedule
            (PhysiotherapyDate, PhysiotherapyTime, Physiotherapy, PatientKey, ArrivalTime, Remark)
            values 
            ("{case_date}", "{case_time}", "{physiotherapy}", {patient_key}, "{case_time}", "(初診)")
        '''
        try:
            cursor.execute(sql)
        except Exception:
            pass

    bar.update(len(rows))


def main():
    convert_patient()
    convert_schedule()

if __name__ == '__main__':
    main()

