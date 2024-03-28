from __future__ import annotations

import os
from dataclasses import dataclass
from json import dump
from json import load
from typing import Any
from typing import get_type_hints

from rgdps import logger


@dataclass
class Config:
    http_port: int = 8922
    http_url_prefix: str = "/database"
    http_host: str = "127.0.0.1"
    sql_host: str = "localhost"
    sql_user: str = "root"
    sql_db: str = "rgdps"
    sql_pass: str = "password"
    sql_port: int = 3306
    srv_name: str = "RealistikGDPS"
    srv_stateless: bool = False
    srv_command_prefix: str = "/"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    meili_host: str = "localhost"
    meili_port: int = 7700
    meili_key: str = "master_key"
    s3_enabled: bool = False
    s3_bucket: str = "rgdps"
    s3_region: str = ""
    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    local_root: str = "/data"
    log_level: str = "INFO"


def read_config_json() -> dict[str, Any]:
    with open("config.json") as f:
        return load(f)


def write_config(config: Config):
    with open("config.json", "w") as f:
        dump(config.__dict__, f, indent=4)


def load_json_config() -> Config:
    """Loads the config from the file, handling config updates.

    Note:
        Raises `SystemExit` on config update.
    """

    config_dict = {}

    if os.path.exists("config.json"):
        config_dict = read_config_json()

    # Compare config json attributes with config class attributes
    missing_keys = [key for key in Config.__annotations__ if key not in config_dict]

    # Remove extra fields
    for key in tuple(
        config_dict,
    ):  # Tuple cast is necessary to create a copy of the keys.
        if key not in Config.__annotations__:
            del config_dict[key]

    # Create config regardless, populating it with missing keys.
    config = Config(**config_dict)

    if missing_keys:
        logger.info(f"Your config has been updated with {len(missing_keys)} new keys.")
        logger.debug("Missing keys: " + ", ".join(missing_keys))
        write_config(config)
        raise SystemExit(0)

    return config


def _env_is_true(value: str | None) -> bool:
    if not isinstance(value, str):
        return False

    return value.lower() in ("true", "1")


def load_env_config() -> Config:
    conf = Config()

    for key, cast in get_type_hints(conf).items():
        if (env_value := os.environ.get(key.upper())) is not None:
            if cast is bool:
                env_value = _env_is_true(env_value)
            setattr(conf, key, cast(env_value))

    return conf


def load_config() -> Config:
    if _env_is_true(os.environ.get("USE_ENV_CONFIG")):
        return load_env_config()
    return load_json_config()


config = load_config()
