import json
from dataclasses import dataclass
import os
from typing import Any, Dict, List

@dataclass(frozen=True)
class AppConfig:
    base_url: str
    token_file: str
    timeout_seconds: int

    csv_path: str
    limit: int

    create_endpoint: str
    update_endpoint_template: str
    default_create_tags: List[str]
    update_tags: List[str]

    pending_update_file: str
    history_file: str
    update_log_file: str
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

            csv_path=os.path.join(input_dir, raw["csv_path"]),
            limit=int(raw.get("limit", 0)),

            create_endpoint=raw.get("create_endpoint", "api/contacts/new"),
            update_endpoint_template=raw.get("update_endpoint_template", "api/contacts/{id}/edit"),
            default_create_tags=list(raw.get("default_create_tags", [])),
            update_tags=list(raw.get("update_tags", [])),
            pending_update_file=os.path.join(output_dir, raw.get("pending_update_file", "pending_updates.json")),
            history_file=os.path.join(output_dir, raw.get("history_file", "contact_history.json")),
            update_log_file=os.path.join(output_dir, raw.get("update_log_file", "update_log.json")),
            input_dir=input_dir,
            output_dir=output_dir,
        )