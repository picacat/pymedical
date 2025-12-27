set dest_dir=z:\pymedical\convert\cvt_kt
del %dest_dir%\.sql

mysqldump kthis typeid > %dest_dir%\typeid.sql
mysqldump kthis users > %dest_dir%\users.sql
mysqldump kthis unit > %dest_dir%\unit.sql
mysqldump kthis eatway > %dest_dir%\eatway.sql
mysqldump kthis allmenu > %dest_dir%\allmenu.sql
mysqldump kthis allmenuw > %dest_dir%\allmenuw.sql
mysqldump kthis bookchp > %dest_dir%\bookchp.sql

mysqldump kthis patient > %dest_dir%\patient.sql
mysqldump kthis patientg > %dest_dir%\patientg.sql

mysqldump kthis hisopdd > %dest_dir%\hisopdd.sql
mysqldump kthis hisopdo > %dest_dir%\hisopdo.sql
mysqldump kthis hisopdc > %dest_dir%\hisopdc.sql

mysqldump kthis history > %dest_dir%\history.sql