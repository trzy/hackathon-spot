import asyncio
import os
import time
from typing import Awaitable, Callable

import pyaudio
import wave

import ai
from server.client import transcribe, process_speech

async def transcribe_audio(audio: bytes, sampling_rate: int = 44100, sample_bits: int = 16) -> str:
    with wave.open("recording.wav", 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(int(sample_bits / 8))
        wf.setframerate(sampling_rate)
        wf.writeframes(audio)
    return await transcribe(filepath="recording.wav")

async def run_speech_processor(speech_queue: asyncio.Queue):
    while True:
        speech_text = await speech_queue.get()
        speech_text = speech_text.strip()
        print(f"Speaker: {speech_text}")
        if len(speech_text) > 0:
            commands = await process_speech(text=speech_text)
            print(f"Commands: {commands}")

async def run_recorder(speech_queue: asyncio.Queue):
    audio = pyaudio.PyAudio()
    sampling_rate = 44100
    num_seconds_per_chunk = 5
    buffer_frames = num_seconds_per_chunk * sampling_rate
    stream = audio.open(rate=sampling_rate, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=buffer_frames)

    recording_time = 30
    while True:
    #for i in range(0, int(recording_time / num_seconds_per_chunk)):
        data = stream.read(buffer_frames)
        speech_text = await transcribe_audio(audio=data)
        await speech_queue.put(speech_text)

    stream.stop_stream()
    stream.close()
    audio.terminate()

async def main():
    speech_queue = asyncio.Queue()
    await asyncio.gather(run_recorder(speech_queue=speech_queue), run_speech_processor(speech_queue=speech_queue))

if __name__ == "__main__":
    asyncio.run(main())