from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def read_comma_separated_list(value: str) -> list[str]:
    return [x.strip() for x in value.split(",")]


def read_boolean(value: str) -> bool:
    return value.lower() in ("true", "1", "yes")


APP_PORT = int(os.environ["APP_PORT"])
APP_HOST = os.environ["APP_HOST"]
APP_URL_PREFIX = os.environ["APP_URL_PREFIX"]

SQL_HOST = os.environ["SQL_HOST"]
SQL_USER = os.environ["SQL_USER"]
SQL_PASS = os.environ["SQL_PASS"]
SQL_DB = os.environ["SQL_DB"]
SQL_PORT = int(os.environ["SQL_PORT"])

REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ["REDIS_PORT"])
REDIS_DB = int(os.environ["REDIS_DB"])

MEILI_HOST = os.environ["MEILI_HOST"]
MEILI_PORT = int(os.environ["MEILI_PORT"])
MEILI_KEY = os.environ["MEILI_KEY"]

S3_ENABLED = read_boolean(os.environ["S3_ENABLED"])
S3_BUCKET = os.environ["S3_BUCKET"]
S3_REGION = os.environ["S3_REGION"]
S3_ENDPOINT = os.environ["S3_ENDPOINT"]
S3_ACCESS_KEY = os.environ["S3_ACCESS_KEY"]
S3_SECRET_KEY = os.environ["S3_SECRET_KEY"]

INTERNAL_RGDPS_DIRECTORY = os.getenv("INTERNAL_RGDPS_DIRECTORY", "./data")

SERVER_NAME = os.environ["SERVER_NAME"]
SERVER_COMMAND_PREFIX = os.environ["SERVER_COMMAND_PREFIX"]
SERVER_GD_URL = os.environ["SERVER_GD_URL"]

LOG_LEVEL = os.environ["LOG_LEVEL"]

LOGZIO_ENABLED = read_boolean(os.environ["LOGZIO_ENABLED"])
LOGZIO_TOKEN = os.environ["LOGZIO_TOKEN"]
LOGZIO_URL = os.environ["LOGZIO_URL"]
