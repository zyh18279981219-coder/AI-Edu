import os

from dotenv import load_dotenv
from google.adk.models.lite_llm import LiteLlm

load_dotenv()

API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")
ENDPOINT = os.getenv("ENDPOINT")

deepseek = LiteLlm(
    model=f"openai/{MODEL}",
    base_url=ENDPOINT,
    api_key=API_KEY,
    tool_choice="auto"
)

# os.environ['GOOGLE_API_KEY']='111'
# os.environ['GEMINI_API_KEY']=''
# os.environ['GOOGLE_GENAI_USE_VERTEXAI']='FALSE'
#
# deepseek=Gemini(
#     model="gemma3-1b",
#     base_url="http://127.0.0.1:8001"
# )