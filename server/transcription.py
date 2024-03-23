from datetime import datetime
from enum import Enum
from io import BytesIO
import os
import traceback
from typing import List, Optional, Annotated

import openai

def transcribe(client: openai.OpenAI, audio_bytes: bytes) -> str:
    # Create a file-like object for Whisper API to consume
    buffer = BytesIO(initial_bytes=audio_bytes)
    buffer.name = "voice.mp4"
    # Whisper
    transcript = client.audio.translations.create(
        model="whisper-1", 
        file=buffer,
    )
    return transcript.text