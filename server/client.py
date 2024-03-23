from typing import List

import aiohttp

from .models import TranscriptionResponse, ProcessSpeechResponse, SpotCommand

URL = "http://192.168.2.172:8000"

async def transcribe(filepath: str) -> str:
    url = f"{URL}/transcribe"
    async with aiohttp.ClientSession() as session:
        form_data = aiohttp.FormData()
        form_data.add_field('audio', open(filepath, 'rb'), filename="voice.wav")
        async with session.post(url, data=form_data) as response:
            return TranscriptionResponse.model_validate_json(json_data=await response.text()).text

async def process_speech(text: str) -> List[SpotCommand]:
    url = f"{URL}/process_speech"
    async with aiohttp.ClientSession() as session:
        form_data = aiohttp.FormData()
        form_data.add_field("text", text)
        async with session.post(url, data=form_data) as response:
            return ProcessSpeechResponse.model_validate_json(json_data=await response.text()).commands