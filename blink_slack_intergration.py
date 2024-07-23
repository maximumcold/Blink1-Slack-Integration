import os
import time 
import easygui as eg
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.errors import SlackApiError
from blink1.blink1 import Blink1

load_dotenv()

# Slack Bot API Token and the Slack App API Token
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_APP_TOKEN = os.getenv('SLACK_APP_TOKEN')

client = WebClient(token=SLACK_BOT_TOKEN)
# SocketModeClient to connect to Slack without the use of HTTP POST requests
socket_mode_client = SocketModeClient(app_token=SLACK_APP_TOKEN, web_client=client) 

# Slack user ID that is used to determine if a channel was responsed to
slack_id = '123ABC'

# Global variables to keep track of the channels and if a channel was responded to
existing_channels = set()
responded_to_channel = False
current_channel_id = None

def error_popup():
    eg.msgbox('The Python script has encountered an error and might need a restart.', 'Script encountered an error', ok_button='OK')

# Gets all the existing channels in the Slack and stores them in a set
def initialize_channels():
    global existing_channels
    try:
        response = client.conversations_list(types="public_channel,private_channel")
        channels = response['channels']
        existing_channels = set(channel['id'] for channel in channels)
    except SlackApiError as e:
        print(f"Error fetching channels: {e.response['error']}")
        error_popup()

# Turn the Blink1 light off
def turn_off_blink1():
    b1 = Blink1()
    b1.fade_to_rgb(1, 0, 0, 0)

# Turns the Blink1 light on
def flash_blink1():
    b1 = Blink1()
    b1.fade_to_rgb(1, 255, 141, 161)

# Event handler for Slack messages
def handle_message(payload):
    global last_message_timestamps, slack_id, responded_to_channel
    event = payload['event']
    
    if event['type'] == 'message':
        channel_id = event.get('channel')  # Get the channel ID of the message
        user_id = event.get('user')  # Get the user ID of the message sender
        
        print(f'Channel ID: {channel_id} Current Channel ID: {current_channel_id}')
        # Checks if the message was sent by the user and is in the current channel (newest created)
        if event.get('subtype') == 'bot_message' or event.get('subtype') == 'channel_join':
            print("Bot reponse")
        elif user_id == slack_id:
            print("Turning light off")
            turn_off_blink1()

# Event handler for incoming events
def process_events(client: SocketModeClient, req: SocketModeRequest):
    global current_channel_id
    
    # Detects events from the Events API
    if req.type == "events_api":
        payload = req.payload
        event = payload["event"]
        print(f"Received event: {event}")

        # Joins the new channel when it is created
        if event["type"] == "channel_created":
            flash_blink1()
            current_channel_id = event.get('channel')
            try:
                client.web_client.conversations_join(channel=event["channel"]["id"])
                print('Channel joined')
            except SlackApiError as e:
                print(f"Error joining channel: {e.response['error']}")
                error_popup()

        # Handles messages in the channel
        if event["type"] == 'message':
            handle_message(payload)

        response = SocketModeResponse(envelope_id=req.envelope_id)
        client.send_socket_mode_response(response)

# Add the event handler to the SocketModeClient and connect to Slack
socket_mode_client.socket_mode_request_listeners.append(process_events)
socket_mode_client.connect()

while True:
    initialize_channels()
    time.sleep(3) # Check for new channels every 3 seconds, API only a few requests per minute thus the delay