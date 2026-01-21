Inspired by [countmeinbot](https://github.com/whipermr5/countmeinbot).

This is a bot to poll for attendance for weekly events, intended for separate Telegram groups of regular and casual members. It has polling features and attendance taking features.

It's still in development.

Live demo [here](https://telegram.me/nuspicklebot).

### Hosting
This project is made to be deployed with Vercel. Requires MongoDB and Redis. Instructions to be added.


### Running locally

1. Install ngrok  
   Download from: https://ngrok.com/download

2. Install dependencies  
   ```bash
   pip install -e .
    ```

3. Create a tunnel to localhost port (5000 by default)

   ```bash
   ngrok http 5000
   ```

4. Set the Telegram webhook

   ```bash
   python set_webhook.py
   ```

5. Run the app

   ```bash
   flask --app src.api.app run --reload
   ```


