"""全局配置: .env(敏感) + config.yaml(非敏感),唯一入口 Settings."""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_base_url: str = Field(default="https://api.openai.com/v1")
    llm_api_key: str = Field(default="sk-please-change")
    llm_model: str = Field(default="gpt-4o-mini")
    llm_provider: str = Field(default="api")  # api | deepseek-web
    deepseek_headless: bool = Field(default=True)
    deepseek_profile: str = Field(default="data/deepseek-profile")
    deepseek_max_chars: int = Field(default=100000)
    deepseek_think: bool = Field(default=False)
    deepseek_search: bool = Field(default=False)

    onebot_http_url: str = Field(default="http://127.0.0.1:3000")
    onebot_ws_url: str = Field(default="ws://127.0.0.1:3001")
    onebot_access_token: str = Field(default="")

    wechat_mode: str = Field(default="ferry")
    wechat_ferry_url: str = Field(default="http://127.0.0.1:19088")

    askbot_host: str = Field(default="0.0.0.0")
    askbot_port: int = Field(default=8000)
    askbot_config: str = Field(default="config/config.yaml")

    # config.yaml 非敏感部分,加载后填充
    yaml_config: dict = Field(default_factory=dict, exclude=True)

    def load_yaml(self) -> dict:
        path = Path(os.getenv("ASKBOT_CONFIG", self.askbot_config))
        example = Path("config/config.example.yaml")
        target = path if path.exists() else example
        if not target.exists():
            return {}
        data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
        self.yaml_config = data
        return data


settings = Settings()
