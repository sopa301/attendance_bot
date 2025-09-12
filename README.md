Inspired by [countmeinbot](https://github.com/whipermr5/countmeinbot).

This is a bot to poll for attendance for weekly events, intended for separate Telegram groups of regular and casual members. It has polling features (with waitlisting) and attendance taking features.

It's still in development.

Live demo [here](https://telegram.me/nuspicklebot).



### Running locally
This project is made to be deployed with Vercel. Locally, it can be run by installing ngrok, creating a tunnel to the localhost port, and running `set_webhook.py` to set the telegram api endpoint to the ngrok tunnel endpoint.

run `flask --app api.app run --reload` to run serve the app locally.