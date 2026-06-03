import os

from dotenv import load_dotenv
from google.adk.models.lite_llm import LiteLlm

load_dotenv()

API_KEY = os.getenv("NAPI_KEY") or os.getenv("api_key")
MODEL = os.getenv("MODEL") or os.getenv("model_name")
ENDPOINT = os.getenv("ENDPOINT") or os.getenv("base_url")

if not API_KEY or not MODEL or not ENDPOINT:
    raise RuntimeError(
        "5E model config missing: set NAPI_KEY/MODEL/ENDPOINT "
        "or api_key/model_name/base_url in .env"
    )

deepseek = LiteLlm(
    model=f"openai/{MODEL}",
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

# os.environ['GOOGLE_API_KEY']='111'
# os.environ['GEMINI_API_KEY']=''
# os.environ['GOOGLE_GENAI_USE_VERTEXAI']='FALSE'
#
# deepseek=Gemini(
#     model="gemma3-1b",
#     base_url="http://127.0.0.1:8001"
# )
