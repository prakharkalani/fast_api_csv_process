from datetime import date, datetime
from pydantic import BaseModel


class Tasks(BaseModel):
    task_id : int
    is_processed : bool
    processed_date : datetime
    start_date : datetime
    output_path : str
    error : str
    is_failed : bool

    class Config:
        orm_mode = True