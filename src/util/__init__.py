"""Utility functions for the attendance bot."""

import os

from dotenv import dotenv_values

from .constants import *
from .date_time import *
from .encodings import *
from .errors import *
from .status import *
from .telegram import *
from .texts import *


def import_env(variables: list):
    """Imports environment variables from the system or a .env file."""
    # assume either all or none of the variables are present
    # (because we either load all or none of them)
    all_present = all(var in os.environ for var in variables)
    if all_present:
        return {var: os.environ[var] for var in variables}
    else:
        return dotenv_values(".env")
