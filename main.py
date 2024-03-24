import asyncio
import os
import time
from typing import List, Tuple

import openai
from spot_controller import SpotController
import cv2
import numpy as np

from server.client import transcribe, process_speech
from server.models import SpotCommand


ROBOT_IP = "10.0.0.3"#os.environ['ROBOT_IP']
SPOT_USERNAME = "admin"#os.environ['SPOT_USERNAME']
SPOT_PASSWORD = "2zqa8dgw7lor"#os.environ['SPOT_PASSWORD']


def capture_image():
    camera_capture = cv2.VideoCapture(0)
    rv, image = camera_capture.read()
    print(f"Image Dimensions: {image.shape}")
    camera_capture.release()
    cv2.imwrite(f'/merklebot/job_data/camera_{time.time()}.jpg', image)

async def get_commands() -> List[SpotCommand]:
    filepath="recording.wav"
    chunk_duration = 5
    cmd = f'arecord -vv --format=cd --device={os.environ["AUDIO_INPUT_DEVICE"]} -r 48000 --duration={chunk_duration} -c 1 {filepath}'
    os.system(cmd)
    sentence = await transcribe(filepath=filepath)
    commands = await process_speech(text=sentence)
    print(f"Transcription: {sentence}")
    print(f"Commands: {commands}")
    return commands

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

async def main():
    with SpotController(username=SPOT_USERNAME, password=SPOT_PASSWORD, robot_ip=ROBOT_IP) as spot:
        current_pos = np.array([0.0,0.0])   # x is forward, y is sideways
        current_forward = np.array([1.0,0.0])
        start_time = time.time()
        while time.time() - start_time < 60:
            commands = await get_commands()
            points, current_pos, current_forward = compute_trajectory(commands=commands, current_pos=current_pos, forward=current_forward)
            for point in points:
                spot.move_to_goal(goal_x=point[0], goal_y=point[1])

    exit()

    print("Playing sound")
    os.system(f"ffplay -nodisp -autoexit -loglevel quiet {sample_name}")
    
    # # Capture image

    # Use wrapper in context manager to lease control, turn on E-Stop, power on the robot and stand up at start
    # and to return lease + sit down at the end
    with SpotController(username=SPOT_USERNAME, password=SPOT_PASSWORD, robot_ip=ROBOT_IP) as spot:

        time.sleep(2)
        capture_image()
        # Move head to specified positions with intermediate time.sleep
        spot.move_head_in_points(yaws=[0.2, 0],
                                 pitches=[0.3, 0],
                                 rolls=[0.4, 0],
                                 sleep_after_point_reached=1)
        capture_image()
        time.sleep(3)

        # Make Spot to move by goal_x meters forward and goal_y meters left
        spot.move_to_goal(goal_x=0.5, goal_y=0)
        time.sleep(3)
        capture_image()

        # Control Spot by velocity in m/s (or in rad/s for rotation)
        spot.move_by_velocity_control(v_x=-0.3, v_y=0, v_rot=0, cmd_duration=2)
        capture_image()
        time.sleep(3)


if __name__ == '__main__':
    asyncio.run(main())
