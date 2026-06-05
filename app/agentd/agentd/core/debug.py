from datetime import datetime, timezone
import json

from agentd.infrastructure.config import get_settings


def is_debug_log_enabled() -> bool:
    settings = get_settings()
    return settings.log_level == "DEBUG"


def emit_debug_log(event: str, **fields: object) -> None:
    if not is_debug_log_enabled():
        return
    payload: dict[str, object] = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'event': event,
        'fields': fields,
    }
    print(f"[agentd-debug] {json.dumps(payload, ensure_ascii=False, default=str)}", flush=True)
