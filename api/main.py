from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from agent.graph import agent_graph

app = FastAPI(
    title="Zrir House AI Agent",
    description="AI-powered sales assistant for Zrir House artisan products",
    version="1.0.0"
)

# ── Request / Response Models ──────────────────────────────────────────────────

class Message(BaseModel):
    role: str   # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []
    language: str = "EN"
    
class ChatResponse(BaseModel):
    response: str
    history: list[Message]

# ── Helper ─────────────────────────────────────────────────────────────────────

def convert_history(history: list[Message]) -> list:
    """Convert API message format to LangChain message format."""
    messages = []
    for msg in history:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
    return messages

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "online", "agent": "Zrir House AI Sales Agent"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        # Convert history to LangChain format
        history = convert_history(request.history[-5:])

        # Add the new user message
        lang_instruction = {
            "EN": "Please respond in English.",
            "FR": "Réponds en français s'il te plaît.",
            "AR": "الرجاء الرد باللغة العربية."
        }
        history.append(HumanMessage(
            content=f"{request.message}\n\n[{lang_instruction.get(request.language, 'Please respond in English.')}]"
        ))

        # Run the agent
        result = agent_graph.invoke({
            "messages": history,
            "customer_name": None,
            "last_tool_called": None
        })

        # Extract the agent's last response
        agent_response = result["messages"][-1].content

        # Build updated history for the response
        updated_history = request.history + [
            Message(role="user", content=request.message),
            Message(role="assistant", content=agent_response)
        ]

        return ChatResponse(
            response=agent_response,
            history=updated_history
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))