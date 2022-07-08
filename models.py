from email.policy import default
from enum import auto
from sklearn.metrics import auc
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.types import DateTime
from database import Base

class Tasks(Base):
    """This clas will be used as database table to stored task details when
    use will submit files to process"""
    __tablename__ = "Tasks"
    task_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    error = Column(String, default="No error")
    is_failed = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)
    processed_date = Column(DateTime)
    start_date = Column(DateTime)
    output_path = Column(String)