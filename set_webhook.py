from util import import_env
import requests

# import env variables
env_variables = ["DEPLOYMENT_URL", "BOT_TOKEN"]
env_config = import_env(env_variables)

# Dummy Telegram webhook data
data = {
    "update_id": 123456789,  # Dummy update ID
    "message": {
        "message_id": 1,
        "from": {
            "id": 1234567890,  # Dummy user ID
            "is_bot": False,
            "first_name": "Test",
            "username": "test_user",
            "language_code": "en"
        },
        "chat": {
            "id": 1234567890,  # Same as user ID for private chats
            "first_name": "Test",
            "username": "test_user",
            "type": "private"
        },
        "date": 1672531200,  # A valid timestamp
        "text": "/start"
    }
}



def set_telegram_webhook():
    url = f"https://api.telegram.org/bot{env_config['BOT_TOKEN']}/setWebhook"
    webhook_url = env_config["DEPLOYMENT_URL"] 
    payload = {"url": webhook_url}
    response = requests.post(url, json=payload)
    print(response.json())  # Check the response from Telegram
    # send a dummy to force the app to start
    # response = requests.post(webhook_url, json=data, headers={"Content-Type": "application/json"})
    # Print response
    # print("Status Code:", response.status_code)

if __name__ == "__main__":
    set_telegram_webhook()