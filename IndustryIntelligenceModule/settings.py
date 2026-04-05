"""Environment-backed settings for industry intelligence."""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


class IndustrySettings:
    """Centralized config access for the industry intelligence module."""

    MODEL_NAME: Optional[str] = os.getenv("model_name")
    BASE_URL: Optional[str] = os.getenv("base_url")
    API_KEY: Optional[str] = os.getenv("api_key")

    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        messages: list[str] = []

        if not cls.MODEL_NAME:
            messages.append("model_name 未设置")
        if not cls.BASE_URL:
            messages.append("base_url 未设置")
        if not cls.API_KEY:
            messages.append("api_key 未设置")

        if messages:
            return False, messages

        return True, ["行业情报模型配置已就绪"]


settings = IndustrySettings()
