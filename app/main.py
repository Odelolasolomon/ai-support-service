from dotenv import load_dotenv
from fastapi import FastAPI

from app.models import ( ChatRequest, ChatResponse)

from app.service import handle_message

load_dotenv()

app = FastAPI(
    title= "AI customer Support API",
    version="1.0"
)

@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post (
    "/chat", 
    response_model=ChatResponse 

)

def chat(request: ChatRequest):
    result = handle_message(
        customer_id = request.customer_id,
        message=request.message 

    )

    return ChatResponse(**result)