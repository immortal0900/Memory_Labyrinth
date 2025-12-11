from pydantic import BaseModel, Field
from typing import List

class CreateDataSet(BaseModel):
    text:str
    labels:List[str]

class CreateDataSetGroup(BaseModel):
    samples:List[CreateDataSet]
