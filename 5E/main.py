import litellm
import uvicorn
from fastapi import FastAPI
from google.adk import Runner
from google.genai import types
from starlette.middleware.cors import CORSMiddleware

from apis import router


async def call_agent_async(query:str, runner:Runner, user_id,session_id):
    content=types.Content(
        role='user',
        parts=[
            types.Part(
                text=query
            )
        ]
    )

    final_response_text="Agent did not produce a final response"

    async for event in runner.run_async(user_id=user_id,session_id=session_id,new_message=content):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text=event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                final_response_text=f"Agent escalated: {event.error_message or 'No specific message'}"
            break

    print(f"<<< Agent Response: {final_response_text}")


app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

app.include_router(router=router)


if __name__ =='__main__':
    litellm._turn_on_debug()
    uvicorn.run(app, host='0.0.0.0', port=8000)