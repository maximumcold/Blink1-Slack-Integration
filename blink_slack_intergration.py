import os
import time 
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
slack_id = 'U07BMJZUWKF'

# Global variables to keep track of the channels and if a channel was responded to
existing_channels = set()
responded_to_channel = False
current_channel_id = None


# Checks to see if any new channels were created and joins them, runs every 3 seconds
def check_new_channels():
    global existing_channels, responded_to_channel, current_channel_id
    try:
        # Retrieves the channels from Slack
        response = client.conversations_list(types="public_channel,private_channel")
        channels = response['channels']
        channel_ids = set([channel['id'] for channel in channels]) 
        
        # Checks for new channels and if so, joins them and sets responded_to_channel to True
        new_channels = channel_ids - existing_channels
        
        if new_channels:
            # Join new channels
            responded_to_channel = True
            for channel_id in new_channels:
                try:
                    client.conversations_join(channel=channel_id)
                except SlackApiError as e:
                    print(f"Error joining channel: {e.response['error']}")
                    
            # Update the existing channels
            existing_channels = channel_ids
    except SlackApiError as e:
        print(f"Error fetching channels: {e}")

# Gets all the existing channels in the Slack and stores them in a set
def initialize_channels():
    global existing_channels
    try:
        response = client.conversations_list(types="public_channel,private_channel")
        channels = response['channels']
        existing_channels = set(channel['id'] for channel in channels)
    except SlackApiError as e:
        print(f"Error fetching channels: {e.response['error']}")

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
     
        # Checks if the message was sent by the user and is in the current channel (newest created)
        if user_id == slack_id and channel_id == current_channel_id:
            responded_to_channel = False
            turn_off_blink1()

# Event handler for incoming events
def process_events(client: SocketModeClient, req: SocketModeRequest):
    global current_channel_id
    
    # Detects events from the Events API
    if req.type == "events_api":
        payload = req.payload
        event = payload["event"]
        print(f"Received event: {event['type']}")

        # Joins the new channel when it is created
        if event["type"] == "channel_created":
            current_channel_id = event["channel"]["id"]
            try:
                client.web_client.conversations_join(channel=event["channel"]["id"])
            except SlackApiError as e:
                print(f"Error joining channel: {e.response['error']}")

        # Handles messages in the channel
        if event["type"] == "message":
            handle_message(payload)

        response = SocketModeResponse(envelope_id=req.envelope_id)
        client.send_socket_mode_response(response)

# Add the event handler to the SocketModeClient and connect to Slack
socket_mode_client.socket_mode_request_listeners.append(process_events)
socket_mode_client.connect()

initialize_channels()

while True:
    check_new_channels()
    while responded_to_channel:
        flash_blink1()
    time.sleep(3) # Check for new channels every 3 seconds, API only a few requests per minute thus the delay