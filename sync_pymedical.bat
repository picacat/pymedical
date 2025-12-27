
set dest_dir=python_update\

set zip_file_name=%dest_dir%pymedical.zip
set zip=%dest_dir%7z.exe

if NOT EXIST %dest_dir% (
	mkdir %dest_dir%
)

del %zip_file_name%
cd ..

%zip% a %zip_file_name% pymedical\*.py
%zip% a %zip_file_name% pymedical\*.qm
%zip% a %zip_file_name% pymedical\*.mp3
%zip% a %zip_file_name% pymedical\complicated_treatment_disease.json
%zip% a %zip_file_name% pymedical\chronic_condition.json
%zip% a %zip_file_name% pymedical\compound.json
%zip% a %zip_file_name% pymedical\reset_smart_card.bat
%zip% a %zip_file_name% pymedical\classes\*.py
%zip% a %zip_file_name% pymedical\convert\*.py
%zip% a %zip_file_name% pymedical\css\*.css
%zip% a %zip_file_name% pymedical\dialog\*.py
%zip% a %zip_file_name% pymedical\libs\*.py
%zip% a %zip_file_name% pymedical\slot_machine\*.py
%zip% a %zip_file_name% pymedical\payment_machine\*.*
%zip% a %zip_file_name% pymedical\mysql\*.sql
%zip% a %zip_file_name% pymedical\mysql\default\*.sql
%zip% a %zip_file_name% pymedical\printer\*.py
%zip% a %zip_file_name% pymedical\ui\*.ui
%zip% a %zip_file_name% pymedical\images\*.*
%zip% a %zip_file_name% pymedical\icons\*.*
%zip% a %zip_file_name% pymedical\tables\*.*

cd pymedical
