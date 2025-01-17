import os
from dotenv import dotenv_values

def import_env(variables: list):
    # assume either all or none of the variables are present (because we either load all or none of them)
    all_present = all(var in os.environ for var in variables)
    if all_present:
        return {var: os.environ[var] for var in variables}
    else:
        return dotenv_values(".env")
