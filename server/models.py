from enum import Enum
from typing import List

from pydantic import BaseModel, ValidationError, Field

class SpotCommand(BaseModel):
    command: str
    dir: str
    amount: float
    duration: float


class TranscriptionResponse(BaseModel):
    text: str

class ProcessSpeechResponse(BaseModel):
    commands: List[SpotCommand]
