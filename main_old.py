
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi import File, UploadFile, FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from fastapi.responses import StreamingResponse
from database import SessionLocal, engine
from tempfile import NamedTemporaryFile
from sqlalchemy.orm import Session
from threading import Thread
from pathlib import Path
import models, schemas
from time import sleep
from uuid import uuid4
import pandas as pd
import numpy as np
import warnings
import datetime
import math
import shutil
import io

warnings.filterwarnings('ignore')

# These vars will be passed to the funtion in csv process funtion
PR = 'VSPR.csv'
ITC = 'VS2A.csv'
dfPR ='%d/%m/%Y'
dfITC ='%d/%m/%Y'
Cessnottocheck='Yes'
missing_tax_items = ['Rate','Taxable value','Taxable mod value']

models.Base.metadata.create_all(bind=engine)
app = FastAPI()

"""
#Adding SSL support
app.add_middleware(HTTPSRedirectMiddleware)

#Adding CORS support
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
"""

def save_upload_file_tmp(upload_file: UploadFile) -> Path:
    try:
        suffix = Path(upload_file.filename).suffix
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(upload_file.file, tmp)
            tmp_path = Path(tmp.name)
    finally:
        upload_file.file.close()
    return tmp_path

def prevalidatetool(task_id, pr_input_file_path, itc_input_file_path, 
    dfPR, dfITC, Cessnottocheck, missing_tax_items):
    db = SessionLocal()

    try:
        print(f"[INFO][TID:- {task_id}] PROCESSING THE CSV FILES IN THE FUNTION WITN TASK ID:- ")
        ITC = pd.read_csv(itc_input_file_path)
        PR = pd.read_csv(pr_input_file_path)
        print(f"[INFO][TID:- {task_id}] BOTH FILES ARE LOADED USING PANDAS")

        # This sleep is added so that this funtio can take some time to process
        # This is for testing only you can remove it
        print(f"[INFO][TID:- {task_id}] SLEEPING FOR 5")
        sleep(5)
        print(f"[INFO][TID:- {task_id}] SLEEP DONE")

        ######### Add your process process code here #############



        #########################################################


        # As soon as the CSV fike gets processed we will have to add output_path of the 
        # Processed CSV file before that save it to apath using df.to_csv() function
        # Saving the processed CSV file to temp directory
        with NamedTemporaryFile(delete=False) as temp:
            # Suppose ITC is the processed file here let save it and change output_path
            # in database and mark the task as finished
            output_path = str(Path(temp.name).absolute()) + ".csv"
            ITC.to_csv(output_path, index=False)

        # when task is done we will update the database using task_id and will set output_path
        task = db.query(models.Tasks).filter(models.Tasks.task_id == task_id).one_or_none()

        if not task is None:
            print(f"[INFO][TID:- {task_id}] TASK DONE UPDAING DATABASE")
            task.is_processed = True
            task.processed_date = datetime.datetime.now()
            task.output_path = output_path
            db.add(task)
            db.commit()
    
    except Exception as e:
        task = db.query(models.Tasks).filter(models.Tasks.task_id == task_id).one_or_none()

        if not task is None:
            print(f"[INFO][TID:- {task_id}] TASK RECEIVED AN EXCEPTION UPDAING DATABASE")
            task.is_failed = True
            task.processed_date = datetime.datetime.now()
            task.error = e.message
            db.add(task)
            db.commit()
        
    db.close()

@app.post("/api/v1/process_files/")
async def process_files(bg_task:BackgroundTasks, pr_input_file: UploadFile = File(...), itc_input_file: UploadFile = File(...)):
    """This function processes the CSV files and create the task_id
    
    args: pr_input_file[UploadFile], itc_input_file[UploadFile]
    returns: dict[str, any]
    """

    db = SessionLocal()
    # Here we are saving the input files to tmp dir
    pr_input_file_path = save_upload_file_tmp(pr_input_file)
    itc_input_file_path = save_upload_file_tmp(itc_input_file)
    
    # Creating the task_id
    db_record = models.Tasks(start_date=datetime.datetime.now())
    db.add(db_record)
    db.commit()
    
    task_id = db_record.task_id
    print(f"[INFO] TASK ADDED TO THE DATABASE {db_record.task_id}")

    # Here we are calling the CSV process funtion in BG thread
    bg_task.add_task(prevalidatetool,
            task_id, pr_input_file_path, itc_input_file_path, dfPR, 
            dfITC, Cessnottocheck, missing_tax_items
    )

    db.close()

    print(f"[FILE] PR:- {pr_input_file_path}\n[FILE] ITC:- {itc_input_file_path}")
    return {"message": "Processing the CSV files", "task_id" : task_id}


@app.get("/api/v1/check_process/")
async def check_process(task_id:str):
    """This method checks the process for the given `task_id` and if task is finished successfully
    then it returns the `task_id` status
    
    args: task_id
    returns: dict[str, str]
    """

    db = SessionLocal()
    task = db.query(models.Tasks).filter(models.Tasks.task_id == task_id).one_or_none()
    if not task is None:
        print("[INFO] FOUND TASKID DETAILS:- ", task_id)
        
        if not task.is_processed and not task.is_failed:
            return {"status": "processing", "task_id": task_id}
        elif task.is_failed:
            return {"status": "failed", "task_id": task_id, "error" : task.error}
        else:
            return {"status": "processed" if task.is_processed else "processing", 
                    "task_id": task_id, "output_path" : task.output_path, 
                    "processed_time" : task.processed_date.strftime("%Y-%m-%d %H:%M:%S")}
    else:
        print("[INFO] NO TASK FOUND WITH TASK ID:- ", task_id)
        return {"error": f"No task found with task_id {task_id}"}


@app.get("/api/v1/get_processed_file/")
async def get_processed_file(task_id:str):
    """This funtion check the `task_id` if task is finished then it will return the `processed` csv file
    
    args: task_id
    returns: dict[str, str] | StreamingResponse
    """

    db = SessionLocal()
    task = db.query(models.Tasks).filter(models.Tasks.task_id == task_id).one_or_none()
    if not task is None:
        
        print("[INFO] FOUND TASK_ID DETAILS:- ", task_id)
        if not task.is_processed:
            print("[INFO] TASK IS NOT COMPLETED YET FOR TASK ID: ", task_id)
            return {"error": "Task has not been completed yet", "task_id": task_id}
        else:
            print(f"[INFO][TID:- {task_id}] RETURNING THE COMPLETED TASK CSV FILE FORM PATH:- {task.output_path}")
            stream = io.StringIO()

            df = pd.read_csv(task.output_path)
            df.to_csv(stream, index=False)
            response = StreamingResponse(iter([stream.getvalue()]),
                            media_type="text/csv"
            )
    
            response.headers["Content-Disposition"] = f"attachment; filename={str(uuid4())}.csv"
            return response
    else:
        print("[INFO] NO TASK FOUND WITH TASK ID:- ", task_id)
        return {"error": f"No task found with task_id {task_id}"}



##############################
#         TEST API URLS      #
##############################

# To check_process of the task using task_id
# http://127.0.0.1:8000/api/v1/check_process/?task_id=11

# To download the processed file using task_id
# http://127.0.0.1:8000/api/v1/get_processed_file/?task_id=11

# To upload files use key pr_input_file and itc_input_file when sengint the files
# http://127.0.0.1:8000/api/v1/process_files/