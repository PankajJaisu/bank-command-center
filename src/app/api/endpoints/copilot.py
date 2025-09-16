# src/app/api/endpoints/copilot.py
from fastapi import APIRouter, Depends, Body
from typing import Dict

from app.db import schemas
from app.modules.copilot import agent

router = APIRouter()


@router.post("/chat")
def chat_with_copilot(request: schemas.ChatRequest = Body(...)) -> Dict:
    """
    Main endpoint for interacting with the Supervity AI AP Manager.
    Receives a user message and optional context, and returns a structured
    response for the UI.
    """
    return agent.invoke_agent(
        user_message=request.message,
        current_invoice_id=request.current_invoice_id,
        history=request.history,
    )
