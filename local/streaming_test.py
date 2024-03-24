import asyncio
import os
import time
from typing import Awaitable, Callable, List, Tuple

import pyaudio
import wave
import numpy as np

import ai
from server.client import transcribe, process_speech
from server.models import SpotCommand

def normalize(v):
    norm = np.linalg.norm(v)
    if norm == 0: 
       return v
    return v / norm

def rotate(v: np.ndarray, degrees: float) -> np.ndarray:
    angle = degrees * np.pi / 180
    r = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    return np.matmul(r, v)

def compute_trajectory(commands: List[SpotCommand], current_pos: np.ndarray, forward: np.ndarray) -> Tuple[List[np.ndarray], np.ndarray, np.ndarray]:
    points = []
    for command in commands:
        if command.command == "WALK":
            dir = -1.0 if command.dir == "backward" else 1.0
            distance = min(command.amount, 3.0)
            current_pos += normalize(dir * forward) * distance
            points.append(current_pos.copy())
        elif command.command == "TURN":
            dir = -1.0 if command.dir == "right" else 1.0
            degrees = abs(command.amount) * dir
            forward = rotate(v=forward, degrees=degrees)
    return (points, current_pos, forward)

async def transcribe_audio(audio: bytes, sampling_rate: int = 44100, sample_bits: int = 16) -> str:
    with wave.open("recording.wav", 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(int(sample_bits / 8))
        wf.setframerate(sampling_rate)
        wf.writeframes(audio)
    return await transcribe(filepath="recording.wav")

async def run_speech_processor(speech_queue: asyncio.Queue):
    current_pos = np.array([0.0,0.0])   # x is forward, y is sideways
    forward = np.array([1.0,0.0])
    while True:
        speech_text = await speech_queue.get()
        speech_text = speech_text.strip()
        print(f"Speaker: {speech_text}")
        if len(speech_text) > 0:
            commands = await process_speech(text=speech_text)
            print(f"Commands: {commands}")
            trajectory, current_pos, forward = compute_trajectory(commands=commands, current_pos=current_pos, forward=forward)
            for point in trajectory:
                print(f"  {point}")

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