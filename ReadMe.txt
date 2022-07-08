#Install modules
python -m pip install -r requirements.txt

#Run FastAPI APP
uvicorn uvicorn main:app --reload --host=0.0.0.0 --port 8000

# To check_process of the task using task_id
http://127.0.0.1:8000/api/v1/check_process/?task_id=11

# To download the processed file using task_id
http://127.0.0.1:8000/api/v1/get_processed_file/?task_id=11

# To upload files use key pr_input_file and itc_input_file when sengint the files
http://127.0.0.1:8000/api/v1/process_files/

# Use below Postman config to test the API