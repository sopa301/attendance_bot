"""Collections package initialization."""

from pymongo import MongoClient

from src.util import import_env

from .attendance_repository import AttendanceRepository
from .ban_repository import BanRepository
from .poll_group_repository import PollGroupRepository
from .poll_repository import PollRepository

env_variables = [
    "MONGO_URL",
    "MONGO_DB_NAME",
    "MONGO_POLLS_COLLECTION_NAME",
    "MONGO_GROUPS_COLLECTION_NAME",
    "MONGO_ATTENANCES_COLLECTION_NAME",
    "REDIS_URL",
]
env_config = import_env(env_variables)

client = MongoClient(env_config["MONGO_URL"])
db = client[env_config["MONGO_DB_NAME"]]
polls_collection = db[env_config["MONGO_POLLS_COLLECTION_NAME"]]
groups_collection = db[env_config["MONGO_GROUPS_COLLECTION_NAME"]]
attendance_collection = db[env_config["MONGO_ATTENANCES_COLLECTION_NAME"]]


poll_repo = PollRepository(polls_collection)
poll_group_repo = PollGroupRepository(groups_collection)
attendance_repo = AttendanceRepository(attendance_collection)
ban_repo = BanRepository(env_config["REDIS_URL"])
