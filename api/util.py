import logging
from dataclasses import dataclass
from telegram.ext import (
    Application,
    CallbackContext,
    ExtBot,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

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
route_names = ["SELECT_NEW_OR_CONTINUE", "INPUT_LIST", "EDIT_LIST", "SUMMARY", "SETTING_STATUS", \
               "GET_NUMBER_OF_EVENTS", "GET_TITLE", "GET_DETAILS", "GET_START_TIME", "GET_END_TIME",
               "SELECT_POLL_GROUP", "GET_POLL_NAME"]
for i, route_name in enumerate(route_names):
    routes[route_name] = i