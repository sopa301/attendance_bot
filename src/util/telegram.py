from dataclasses import dataclass

from telegram.ext import Application, CallbackContext, ExtBot


class CustomContext(CallbackContext[ExtBot, dict, dict, dict]):
    """
    Custom CallbackContext class that makes `user_data` available for updates of type
    `WebhookUpdate`.
    """

    @classmethod
    def from_update(
        cls,
        update: object,
        application: "Application",
    ) -> "CustomContext":
        if isinstance(update, WebhookUpdate):
            return cls(application=application, user_id=update.user_id)
        return super().from_update(update, application)


@dataclass
class WebhookUpdate:
    """Simple dataclass to wrap a custom update type"""

    user_id: int
    payload: str


routes = {}
route_names = [
    "SELECT_NEW_OR_CONTINUE",
    "VIEW_LIST",
    "SUMMARY",
    "SETTING_STATUS",
    "GET_NUMBER_OF_EVENTS",
    "GET_TITLE",
    "GET_DETAILS",
    "GET_START_TIME",
    "GET_END_TIME",
    "SELECT_POLL_GROUP",
    "GET_POLL_NAME",
    "RECEIVE_INPUT_LIST",
    "MANAGE_ATTENDANCE_LIST",
    "RECEIVE_EDITED_LIST",
    "SELECT_POLL",
    "GET_NEW_POLL_NAME",
]
for i, route_name in enumerate(route_names):
    routes[route_name] = i
