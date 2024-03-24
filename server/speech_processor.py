from enum import Enum
import json
from typing import List

import openai
from pydantic import BaseModel, ValidationError, Field

from .models import SpotCommand


SYSTEM_MESSAGE = """
You are a quadrupedal robot named Spot created by Boston Dynamics. You listen for commands from the
user, which always mention your name, and output a list of command strings directly. 
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "walk_command",
            "description": "Produces command object for walking forward or backward",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "description": "Direction to walk in",
                        "enum": ["forward", "backward", "unknown"]
                    },
                    "distance": {
                        "type": "number",
                        "description": "Distance in feet to traverse, if specified, else 0",
                    },
                    "duration": {
                        "type": "number",
                        "description": "Number of seconds to walk for, if specified, else 0",
                    },
                },
                "required": [ "direction", "distance", "duration" ]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "turn_command",
            "description": "Produces command object for turning in place",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "description": "Direction to turn, relative to Spot's facing direction",
                        "enum": ["left", "right", "unknown" ]
                    },
                    "angle": {
                        "type": "number",
                        "description": "Angle in degrees to turn, a positive number between 0 and 360",
                    },
                },
                "required": [ "direction", "angle" ]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bow_command",
            "description": "Produces command object for bowing gesture",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dance_command",
            "description": "Produces command object for dancing",
        },
    },
]

class Role(str, Enum):
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"

class Message(BaseModel):
    role: Role
    content: str


def process_speech(client: openai.OpenAI, text: str) -> List[SpotCommand]:
    model = "gpt-3.5-turbo"

    message_history = [
        Message(role=Role.SYSTEM, content=SYSTEM_MESSAGE),
        Message(role=Role.USER, content=text)
    ]
    
    first_response = client.chat.completions.create(
        model=model,
        messages=message_history,
        tools=TOOLS,
        tool_choice="auto"
    )
    first_response_message = first_response.choices[0].message

    # Handle tool requests
    commands = []
    available_functions = {
        "walk_command": _handle_walk_command,
        "turn_command": _handle_turn_command,
        "bow_command": _handle_bow_command,
        "dance_command": _handle_dance_command,
    }
    if first_response_message.tool_calls:
        # Append initial response to history, which may include tool use
        message_history.append(first_response_message)
        
        # Call tools
        for tool_call in first_response_message.tool_calls:
            # Determine which tool and what arguments to call with
            function_name = tool_call.function.name
            function_to_call = available_functions.get(function_name)
            function_args = json.loads(tool_call.function.arguments)
            print(f"Function Name={function_name}, Args={function_args}")

            # Call the tool
            function_response = function_to_call(**function_args)
            commands.append(function_response)
            
            # Append function response for GPT to continue
            message_history.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )

        response = "\n".join(commands)
        print(f"Response:\n{response}")

    return parse_commands(command_strings=commands)

def _handle_walk_command(direction: str, distance: float, duration: float) -> str:
    return f"WALK {direction} {distance} {duration}"

def _handle_turn_command(direction: str, angle: float) -> str:
    return f"TURN {direction} {angle}"

def _handle_bow_command() -> str:
    return f"BOW"

def _handle_dance_command() -> str:
    return f"DUST_OFF"

def parse_float(text: str) -> float:
    try:
        return float(text)
    except:
        return 0

def parse_commands(command_strings: List[str]) -> List[SpotCommand]:
    commands = []
    for command_string in command_strings:
        parts = command_string.split(" ")
        if len(parts) <= 0:
            continue
        if parts[0] == "WALK":
            if len(parts) == 4:
                amount = parse_float(parts[2]) * 0.3048
                duration = parse_float(parts[3])
                if amount <= 0 and duration <= 0:
                    continue
                commands.append(SpotCommand(command="WALK", dir=parts[1], amount=amount, duration=duration))
        elif parts[0] == "TURN":
            if len(parts) == 3: 
                amount = parse_float(parts[2])
                if amount <= 0:
                    continue
                commands.append(SpotCommand(command="TURN", dir=parts[1], amount=amount, duration=0))
        elif parts[0] == "BOW":
            commands.append(SpotCommand(command="BOW", dir="unknown", amount=0, duration=0))
        elif parts[0] == "DUST_OFF":
            commands.append(SpotCommand(command="DUST_OFF", dir="unknown", amount=0, duration=0))
    return commands