import json
from dataclasses import dataclass
import os
from typing import Any, Dict

@dataclass(frozen=True)
class AppConfig:
    base_url: str
    token_file: str
    timeout_seconds: int

    limit: int
    bulldog_api_url: str
    segment_id: int
    test_tag_name: str
    exclude_tag_id: int
    exclude_tag_name: str
    default_include_tag_id: int
    default_include_tag_name: str

    create_endpoint: str

    history_file: str
    failed_creation_file: str
    input_dir: str
    output_dir: str

    @staticmethod
    def load(path: str = "config.json") -> "AppConfig":
        with open(path, "r", encoding="utf-8") as f:
            raw: Dict[str, Any] = json.load(f)

        base_url = raw["base_url"]
        if not base_url.endswith("/"):
            base_url += "/"

        input_dir = raw.get("input_dir", "./data")
        output_dir = raw.get("output_dir", "./generated")
        os.makedirs(output_dir, exist_ok=True) # Ensure the output directory exists

        return AppConfig(
            base_url=base_url,
            token_file=os.path.join(output_dir, raw.get("token_file", "mautic_tokens.json")),
            timeout_seconds=int(raw.get("timeout_seconds", 30)),

            limit=int(raw.get("limit", 0)),

            bulldog_api_url=os.getenv("BULLDOG_API_URL", raw.get("bulldog_api_url", "")),
            segment_id=int(raw.get("segment_id", 0)),
            test_tag_name=str(raw.get("test_tag_name", "Test")),
            exclude_tag_id=int(raw.get("exclude_tag_id", 0)),
            exclude_tag_name=str(raw.get("exclude_tag_name", "Done")),
            default_include_tag_id=int(raw.get("default_include_tag_id", 0)),
            default_include_tag_name=str(raw.get("default_include_tag_name", "Default-Bulldog")),
            create_endpoint=raw.get("create_endpoint", "api/contacts/new"),
            history_file=os.path.join(output_dir, raw.get("history_file", "contact_history.json")),
            failed_creation_file=os.path.join(output_dir, raw.get("failed_creation_file", "failed_creations.json")),
            input_dir=input_dir,
            output_dir=output_dir,
        )