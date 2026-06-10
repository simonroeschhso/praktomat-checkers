from __future__ import annotations
from dataclasses import dataclass
from typing import Union
from utils import *
from exercise import YamlDict
import yaml


@dataclass
class LlmTutorConfig:
    apikey: str

    @staticmethod
    def parse(v: YamlDict):
        apikey = v.get("apikey")
        if apikey is None:
            raise ValueError("Missing required config value: llmTutorConfig.apikey")
        if not isinstance(apikey, str):
            raise TypeError("Config value llmTutorConfig.apikey must be a string")
        return LlmTutorConfig(apikey)


@dataclass
class Config:
    llmTutorConfig: LlmTutorConfig

    @staticmethod
    def parse(v: YamlDict):
        llm_tutor_raw = v.get("llmTutorConfig", {})
        if llm_tutor_raw is None:
                llm_tutor_raw = {}
        if not isinstance(llm_tutor_raw, dict):
            raise TypeError("Config value llmTutorConfig must be a dictionary")

        llm_tutor_cfg = LlmTutorConfig.parse(YamlDict(llm_tutor_raw))
        return Config(llmTutorConfig=llm_tutor_cfg)
    

def parseConfig(yamlPath: str) -> Config:
    s = readFile(yamlPath)
    ymlDict = yaml.safe_load(s)
    cfg = Config.parse(YamlDict(ymlDict))
    debug(f"Parsed config from {yamlPath}: {cfg}")
    return cfg