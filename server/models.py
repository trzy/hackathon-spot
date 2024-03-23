from pydantic import BaseModel, ValidationError, Field

class TranscriptionResponse(BaseModel):
    text: str
