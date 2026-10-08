import os

from tools.env_loader import load_project_env
from google.adk.models.lite_llm import LiteLlm

load_project_env()

DEFAULT_RAG_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_RESOURCE_DIRECTORY = 'data/Book'
CHROMA_PERSIST_DIRECTORY = 'data/chroma_db'

API_KEY = os.getenv("NAPI_KEY") or os.getenv("api_key")
MODEL = os.getenv("MODEL") or os.getenv("model_name")
ENDPOINT = os.getenv("ENDPOINT") or os.getenv("base_url")

if not API_KEY or not MODEL or not ENDPOINT:
    raise RuntimeError(
        "5E model config missing: set NAPI_KEY/MODEL/ENDPOINT "
        "or api_key/model_name/base_url in .env"
    )

deepseek = LiteLlm(
    model=f"{MODEL}",
    base_url=ENDPOINT,
    api_key=API_KEY,
    tool_choice="auto",
    extra_body={
        "thinking": {
            "type": "disabled"
        }
    },
    response_format={
        'type': 'json_object'
    }
)
