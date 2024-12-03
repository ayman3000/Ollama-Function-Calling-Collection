import os
import streamlit as st
import asyncio
from ollama import ChatResponse
import ollama

# Home automation functions

def turn_on_light(room: str) -> str:
    """
    Turn on the light in a specific room.

    Args:
        room (str): The room where the light should be turned on.

    Returns:
        str: Confirmation message.
    """
    st.session_state[f"{room}_light_state"] = "ON"
    return f"Light in the {room} is now ON."

def turn_off_light(room: str) -> str:
    """
    Turn off the light in a specific room.

    Args:
        room (str): The room where the light should be turned off.

    Returns:
        str: Confirmation message.
    """
    st.session_state[f"{room}_light_state"] = "OFF"
    return f"Light in the {room} is now OFF."

def set_temperature(room: str, temperature: int) -> str:
    """
    Set the temperature of a specific room.

    Args:
        room (str): The room where the temperature should be set.
        temperature (int): The desired temperature.

    Returns:
        str: Confirmation message.
    """
    st.session_state[f"{room}_temperature"] = temperature
    return f"Temperature in the {room} is now set to {temperature}°C."

# Tools can still be manually defined and passed into chat
turn_on_light_tool = {
    'type': 'function',
    'function': {
        'name': 'turn_on_light',
        'description': 'Turn on the light in a specific room',
        'parameters': {
            'type': 'object',
            'required': ['room'],
            'properties': {
                'room': {'type': 'string', 'description': 'The room where the light should be turned on'},
            },
        },
    },
}

turn_off_light_tool = {
    'type': 'function',
    'function': {
        'name': 'turn_off_light',
        'description': 'Turn off the light in a specific room',
        'parameters': {
            'type': 'object',
            'required': ['room'],
            'properties': {
                'room': {'type': 'string', 'description': 'The room where the light should be turned off'},
            },
        },
    },
}

set_temperature_tool = {
    'type': 'function',
    'function': {
        'name': 'set_temperature',
        'description': 'Set the temperature of a specific room',
        'parameters': {
            'type': 'object',
            'required': ['room', 'temperature'],
            'properties': {
                'room': {'type': 'string', 'description': 'The room where the temperature should be set'},
                'temperature': {'type': 'integer', 'description': 'The desired temperature in Celsius'},
            },
        },
    },
}

# Async function to handle the LLM decision
async def main():
    client = ollama.AsyncClient()
    prompt = st.session_state.get("user_input", "Turn on the light in the living room")

    available_functions = {
        'turn_on_light': turn_on_light,
        'turn_off_light': turn_off_light,
        'set_temperature': set_temperature
    }

    response: ChatResponse = await client.chat(
        'qwen2.5-coder:7b', # Replace with your LLM name
        messages=[
            {'role': 'system',
              'content': "If the room name is more than one word, concatenate with '_' in the response. Translate into English numbers "
                         "and  room names to the closest names in our list ['living_room','bedroom'] before responding, if the prompt is in another language."},
            {'role': 'user', 'content': prompt}
        ] ,
        tools=[turn_on_light_tool, turn_off_light_tool, set_temperature_tool]  # Passing the tools
    )

    print(f"Response: {response}")

    # This is where we check if the model is suggesting an action
    if response.message.tool_calls:
        for tool in response.message.tool_calls:
            if function_to_call := available_functions.get(tool.function.name):
                output_message = function_to_call(**tool.function.arguments)
                st.session_state['last_action_message'] = output_message
            else:
                st.session_state['last_action_message'] = f'Function {tool.function.name} not found'
    else:
        st.session_state['last_action_message'] = response.message.content

# Streamlit UI setup
st.set_page_config(page_title="Home Automation Simulator", layout="wide")

st.title("Home Automation LLM Simulator")
st.sidebar.title("Instructions")
st.sidebar.write("Enter a command like 'Turn on the light in the kitchen', and watch the magic happen!")

# Visualize the apartment layout
st.subheader("Apartment Layout")


# Get the current states for the rooms
living_room_bk_color = "white" if st.session_state.get('living_room_light_state', 'OFF') == 'ON' else 'black'
living_room_color = "black" if st.session_state.get('living_room_light_state', 'OFF') == 'ON' else 'white'
bedroom_bk_color = "white" if st.session_state.get('bedroom_light_state', 'OFF') == 'ON' else 'black'
bedroom_color = "black" if st.session_state.get('bedroom_light_state', 'OFF') == 'ON' else 'white'
living_room_temp = st.session_state.get('living_room_temperature', 'Not Set')
bedroom_temp = st.session_state.get('bedroom_temperature', 'Not Set')

# Render the HTML table with the appropriate room states

st.markdown(f"""
    <table style='width: 100%; border-collapse: collapse;'>
        <tr>
            <td style='border: 1px solid black; padding: 20px; text-align: center;color: {living_room_color}; background-color: {living_room_bk_color};'>Living Room</td>
            <td style='border: 1px solid black; padding: 20px; text-align: center;color: {bedroom_color}; background-color: {bedroom_bk_color};'>Bedroom</td>
        </tr>
        <tr>
            <td style='border: 1px solid black; padding: 20px; text-align: center;'>Temperature: {living_room_temp}°C</td>
            <td style='border: 1px solid black; padding: 20px; text-align: center;'>Temperature: {bedroom_temp}°C</td>
        </tr>
    </table>
"""
            , unsafe_allow_html=True
            )


# Display the last action message if available
if 'last_action_message' in st.session_state:
    st.success(st.session_state['last_action_message'])

# User input section
st.subheader("Enter your custom command below:")
user_input = st.text_input("You:", placeholder="e.g., Turn on the light in the living room", key='user_input')

# Button to execute the custom command
if st.button("Execute Command"):
    if user_input:
        try:
            asyncio.run(main())
            st.rerun()
        except Exception as e:
            st.error(f"An error occurred: {e}")
