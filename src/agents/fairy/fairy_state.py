from langgraph.graph import MessagesState
from pydantic import BaseModel,Field
from typing import List
class FairyState(MessagesState):
    pass

class FairyOutput(BaseModel):
    message:str = Field(description="응답한 메시지")