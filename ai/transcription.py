import asyncio
import os
import time
from typing import Awaitable, Callable

from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
from deepgram.clients.live.v1.client import LiveClient
from deepgram.clients.live.v1.async_client import AsyncLiveClient
from deepgram.clients.live.v1.response import OpenResponse, SpeechStartedResponse, LiveResultResponse, MetadataResponse, UtteranceEndResponse, ErrorResponse, CloseResponse
import openai


####################################################################################################
# Whisper
####################################################################################################

client = openai.OpenAI()

def transcribe(filepath: str) -> str:
    with open(filepath, mode="rb") as fp:
        transcript = client.audio.translations.create(
            model="whisper-1", 
            file=fp
        )
        return transcript.text


####################################################################################################
# Deepgram
####################################################################################################

class DeepgramTranscriber:
    def __init__(self, on_sentence_received: Callable[[str], Awaitable[None]]):
        deepgram_client = DeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))
        self._is_open = False
        self._on_sentence_received = on_sentence_received
        self._deepgram_connection: AsyncLiveClient = deepgram_client.listen.asynclive.v(version="1")
        self._deepgram_connection.on(LiveTranscriptionEvents.Open, self._on_open)
        self._deepgram_connection.on(LiveTranscriptionEvents.Transcript, self._on_message)
        self._deepgram_connection.on(LiveTranscriptionEvents.Metadata, self._on_metadata)
        self._deepgram_connection.on(LiveTranscriptionEvents.SpeechStarted, self._on_speech_started)
        self._deepgram_connection.on(LiveTranscriptionEvents.UtteranceEnd, self._on_utterance_end)
        self._deepgram_connection.on(LiveTranscriptionEvents.Error, self._on_error)
        self._deepgram_connection.on(LiveTranscriptionEvents.Close, self._on_close)
        print("DeepgramTranscriber created")

    async def start(self):
        options: LiveOptions = LiveOptions(
            model="nova-2",
            punctuate=True,
            language="en-US",
            encoding="linear16",
            channels=1,
            sample_rate=16000,
            diarize=False,
            # To get UtteranceEnd, the following must be set:
            interim_results=True,
            #utterance_end_ms="1000",
            vad_events=True
        )
        await self._deepgram_connection.start(options)
        while not self._is_open:
            await asyncio.sleep(0.1)

    async def send_audio(self, audio: bytes):
        await self._deepgram_connection.send(audio)

    async def finish(self):
        await self._deepgram_connection.finish()

    async def _on_open(self, deepgram_connection: AsyncLiveClient, open: OpenResponse, **kwargs):
        print("Connection to Deepgram opened")
        self._is_open = True

    async def _on_message(self, deepgram_connection: LiveClient, result: LiveResultResponse, **kwargs):
        sentence = result.channel.alternatives[0].transcript
        print(sentence)
        if len(sentence) == 0 or not result.is_final:
            return
        await self._on_sentence_received(sentence)

    async def _on_metadata(self, deepgram_connection: AsyncLiveClient, metadata: MetadataResponse, **kwargs):
        pass

    async def _on_speech_started(self, deepgram_connection: AsyncLiveClient, speech_started: SpeechStartedResponse, **kwargs):
        pass

    async def _on_utterance_end(self, deepgram_connection: AsyncLiveClient, utterance_end: UtteranceEndResponse, **kwargs):
        pass

    async def _on_error(self, deepgram_connection: AsyncLiveClient, error: ErrorResponse, **kwargs):
        #TODO: with AsyncLiveClient, this gets called repeatedly. Need to find a way to terminate
        #      the client and then attempt to restart it, or we should just always kill socket when
        #      not transmitting audio data.
        print(f"ERROR: {type(error)}: {error}")

    async def _on_close(self, deepgram_connection: AsyncLiveClient, close: CloseResponse, **kwargs):
        print("Connection to Deepgram closed")
        self._is_open = False