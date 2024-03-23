import asyncio
import os
import time
from typing import Awaitable, Callable

import pyaudio
import wave

import ai
from server.client import transcribe


async def main():
    t0 = time.perf_counter()
    audio = pyaudio.PyAudio()
    sampling_rate = 44100
    stream = audio.open(rate=sampling_rate, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=44100)
    chunks = []
    for i in range(0, int(10 * sampling_rate / 44100)):
        data = stream.read(44100)
        chunks.append(data)
    stream.stop_stream()
    stream.close()
    audio.terminate()
    
    with wave.open("test.wav", 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sampling_rate)
        wf.writeframes(b''.join(chunks))

    t1 = time.perf_counter()

    print(f"{t1-t0} seconds")

    print(await transcribe(filepath="test.wav"))


if __name__ == "__main__":
    asyncio.run(main())