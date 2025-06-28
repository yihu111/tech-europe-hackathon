from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class Job(BaseModel):
    title: str
    location: str
    description: str
    job_url: str
    interview_url: str
    application_deadline: Optional[date] = None

class JobList(BaseModel):
    jobs: List[Job]
