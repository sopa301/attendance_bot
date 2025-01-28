from util.db import *
from util import import_env
from util.encodings import *

from telegram import CallbackQuery

import requests
import json

env_vars = ["BOT_TOKEN", "DEPLOYMENT_URL"]
env_config = import_env(env_vars)

import requests
import json

# Replace with your bot's webhook URL (for example, Vercel or Render deployment)
WEBHOOK_URL = env_config["DEPLOYMENT_URL"]

# Mock Telegram update payload (sample message event)
mock_update = {
    "update_id": 123456789,
    "message": {
        "message_id": 1,
        "date": 1700000000,  # Sample Unix timestamp
        "chat": {
            "id": 987654321,  # Mock chat ID
            "type": "private",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User"
        },
        "from": {
            "id": 987654321,
            "is_bot": False,
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser",
            "language_code": "en"
        },
        "text": "Hello bot!"
    }
}



def foo(i):
  mock_callback_query = {
    "update_id": 992913233,
    "callback_query": {
        "id": "429692596269498658" + str(i),  # Unique callback query ID
        "from": {
            "id": 1000456037,  # User ID
            "is_bot": False,
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser" + str(i),
            "language_code": "en"
        },
        "chat_instance": "-6803715888701138433",
        "inline_message_id": "BQAAAIFLAgBlv6E7Pd-YZUnUres",
        "data": "p_nr_678fa613f8a5d4ef6e3b0a4a_1"  # The callback data the user clicked
    }
}
  # Send mock update to your bot's webhook
  response = requests.post(WEBHOOK_URL, data=json.dumps(mock_callback_query), headers={'Content-Type': 'application/json'})

  # Print response from the bot server
  print("Response status code:", response.status_code)
  print("Response body:", response.text)

for i in range(1):
  foo(i)