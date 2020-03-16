import json
import os
from typing import Any


def load_json(json_path: str) -> Any:
    with open(json_path, 'r') as f:
        return json.load(f)


def delete_env(environment: str) -> None:
    if os.environ.get(environment) is not None:
        del os.environ[environment]
