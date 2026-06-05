from pydantic import BaseModel


def format_sse_event(event: str, data: BaseModel) -> str:
    return f"event: {event}\ndata: {data.model_dump_json(exclude_none=True)}\n\n"