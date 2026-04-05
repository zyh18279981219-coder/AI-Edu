from datetime import datetime
from typing import Any, Dict, List, Optional
import threading

from DatabaseModule.sqlite_store import get_sqlite_store


class LLMLogger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.store = get_sqlite_store()
        self._initialized = True

    def log_llm_call(
        self,
        messages: List[Dict[str, str]],
        response: Any,
        model: str,
        module: str,
        metadata: Optional[Dict] = None,
        username: Optional[str] = None,
    ):
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "username": username or "unknown",
                "module": module,
                "metadata": metadata or {},
                "request": {"model": model, "messages": messages},
                "response": self._extract_response_data(response),
            }

            with self._lock:
                self.store.append_llm_log(log_entry)
        except Exception as e:
            print(f"Failed to log LLM call: {e}")

    def _extract_response_data(self, response: Any) -> Dict:
        try:
            if hasattr(response, "response_metadata"):
                metadata = response.response_metadata
                return {
                    "id": metadata.get("id", ""),
                    "object": metadata.get("object", "chat.completion"),
                    "created": metadata.get("created", int(datetime.now().timestamp())),
                    "model": metadata.get("model", ""),
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": getattr(response, "content", str(response)),
                            },
                            "finish_reason": metadata.get("finish_reason", "stop"),
                        }
                    ],
                    "usage": {
                        "prompt_tokens": metadata.get("token_usage", {}).get("prompt_tokens", 0),
                        "completion_tokens": metadata.get("token_usage", {}).get("completion_tokens", 0),
                        "total_tokens": metadata.get("token_usage", {}).get("total_tokens", 0),
                    },
                    "system_fingerprint": metadata.get("system_fingerprint", ""),
                }
            return {
                "id": "",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": "",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": getattr(response, "content", str(response)),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
                "system_fingerprint": "",
            }
        except Exception as e:
            print(f"Failed to extract response data: {e}")
            return {"error": str(e), "content": str(response)}

def get_llm_logger() -> LLMLogger:
    return LLMLogger()
