from datetime import datetime
from enum import Enum
from io import BytesIO
import os
import traceback
from typing import List, Optional, Annotated

import openai
from pydantic import BaseModel, ValidationError, Field
from fastapi import FastAPI, status, Form, UploadFile, Depends, Request
from pydantic import BaseModel, ValidationError
from fastapi.exceptions import HTTPException
from fastapi.encoders import jsonable_encoder

from server.models import TranscriptionResponse, ProcessSpeechResponse
from server.transcription import transcribe
from server.speech_processor import process_speech


####################################################################################################
# Server API 
####################################################################################################

app = FastAPI()

class Checker:
    def __init__(self, model: BaseModel):
        self.model = model

    def __call__(self, data: str = Form(...)):
        try:
            return self.model.model_validate_json(data)
        except ValidationError as e:
            raise HTTPException(
                detail=jsonable_encoder(e.errors()),
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

@app.post("/transcribe")
async def api_transcribe(request: Request, audio: UploadFile = None):
    try:
        return TranscriptionResponse(text=transcribe(client=request.app.state.openai_client, audio_bytes=await audio.read()))
    except Exception as e:
        print(f"{traceback.format_exc()}")
        raise HTTPException(400, detail=f"{str(e)}: {traceback.format_exc()}")
    
@app.post("/process_speech")
async def api_process_speech(request: Request, text: Annotated[str, Form()]):
    try:
        return ProcessSpeechResponse(commands=process_speech(client=request.app.state.openai_client, text=text))
    except Exception as e:
        print(f"{traceback.format_exc()}")
        raise HTTPException(400, detail=f"{str(e)}: {traceback.format_exc()}")


####################################################################################################
# Program Entry Point
####################################################################################################

if __name__ == "__main__":
    # import argparse
    # parser = argparse.ArgumentParser()
    # options = parser.parse_args()

    # Instantiate a vision provider
    openai_client = openai.OpenAI()
    app.state.openai_client = openai_client

    # Run server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)