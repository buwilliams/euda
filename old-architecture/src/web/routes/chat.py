"""
Chat and conversation routes for Euno web API.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...agents.base import create_agent
from ...agents.friend import FRIEND_TOOLS, FRIEND_HANDLERS
from ...tools.shared.log import write_log_entry
from ...tools.friend.conversation_history import (
    save_message, get_conversation_data, get_recent_conversations,
    delete_conversation, load_conversation_into_context,
    _get_session_file, _get_daily_file, _ensure_dirs
)


router = APIRouter(tags=["chat"])

# Session storage (in-memory)
sessions: dict = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    clear_chat: bool = False


class ForkRequest(BaseModel):
    session_id: str


def get_or_create_session(session_id: Optional[str] = None) -> tuple[str, object]:
    """Get an existing session or create a new one."""
    if session_id and session_id in sessions:
        return session_id, sessions[session_id]["agent"]

    new_id = session_id or str(uuid.uuid4())
    agent = create_agent(
        persona_name="friend",
        tools=FRIEND_TOOLS
    )

    sessions[new_id] = {
        "agent": agent,
        "created": datetime.now(),
        "last_used": datetime.now()
    }

    return new_id, agent


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the Friend Agent."""
    from ...tools.friend.conversation import (
        reset_clear_flag, was_clear_requested,
        reset_delete_flag, was_delete_requested
    )

    session_id, agent = get_or_create_session(request.session_id)

    try:
        reset_clear_flag()
        reset_delete_flag()

        sessions[session_id]["last_used"] = datetime.now()
        response = agent.process(request.message, FRIEND_HANDLERS)

        clear_chat = was_clear_requested()
        delete_chat = was_delete_requested()

        if delete_chat:
            delete_conversation(session_id)
            clear_chat = True

        if clear_chat:
            agent.clear_context()
            new_session_id = str(uuid.uuid4())
            sessions[new_session_id] = {
                "agent": create_agent("friend", FRIEND_TOOLS),
                "created": datetime.now(),
                "last_used": datetime.now()
            }
            session_id = new_session_id

        if not clear_chat:
            write_log_entry(
                content=f"**Me:** {request.message}\n\n**Friend:** {response}",
                source="conversation",
                entry_type="chat"
            )
            save_message(
                session_id=session_id,
                user_message=request.message,
                assistant_response=response
            )

        return ChatResponse(
            response=response,
            session_id=session_id,
            clear_chat=clear_chat
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat_legacy(request: ChatRequest):
    """Legacy chat endpoint for compatibility."""
    return await chat(request)


@router.get("/api/sessions")
async def list_sessions():
    """List active sessions."""
    return {
        "count": len(sessions),
        "sessions": [
            {
                "id": sid,
                "created": s["created"].isoformat(),
                "last_used": s["last_used"].isoformat()
            }
            for sid, s in sessions.items()
        ]
    }


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/api/sessions/new")
async def create_new_session():
    """Create a new session."""
    new_session_id = str(uuid.uuid4())
    agent = create_agent(persona_name="friend", tools=FRIEND_TOOLS)

    sessions[new_session_id] = {
        "agent": agent,
        "created": datetime.now(),
        "last_used": datetime.now()
    }

    return {"session_id": new_session_id}


@router.get("/api/conversations/recent")
async def get_recent_convos(count: int = 5):
    """Get recent conversations with previews."""
    content = get_recent_conversations(count)
    return {"content": content}


@router.get("/api/conversations/history")
async def get_history(session_id: str = None, date: str = None):
    """Load conversation history for display in UI."""
    if not session_id and not date:
        return {"error": "Provide either session_id or date parameter"}

    data = get_conversation_data(session_id=session_id, date=date)
    return data


@router.get("/api/conversations/recent/structured")
async def get_recent_convos_structured(count: int = 20):
    """Get recent conversations as structured JSON for the History panel."""
    _ensure_dirs()
    all_sessions = []
    today = datetime.now()

    for i in range(30):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_file = _get_daily_file(date)
        if daily_file.exists():
            with open(daily_file, 'r') as f:
                daily_data = json.load(f)
            all_sessions.extend(daily_data.get("sessions", []))
        if len(all_sessions) >= count * 2:
            break

    seen = set()
    sessions_with_data = []
    for session_id in all_sessions:
        if session_id in seen:
            continue
        seen.add(session_id)
        session_file = _get_session_file(session_id)
        if session_file.exists():
            with open(session_file, 'r') as f:
                data = json.load(f)
            messages = data.get("messages", [])
            preview_parts = []
            preview_len = 0
            for msg in messages:
                if preview_len >= 300:
                    break
                user_text = msg.get("user", "").strip()
                if user_text:
                    preview_parts.append(f"You: {user_text}")
                    preview_len += len(user_text)
                assistant_text = msg.get("assistant", "").strip()
                if assistant_text and preview_len < 300:
                    preview_parts.append(f"Euno: {assistant_text}")
                    preview_len += len(assistant_text)
            preview = "\n".join(preview_parts)[:500] if preview_parts else "No preview"
            sessions_with_data.append({
                "session_id": session_id,
                "date": data.get("updated", data.get("created", ""))[:10],
                "time": data.get("updated", data.get("created", ""))[11:16],
                "message_count": len(messages),
                "preview": preview
            })

    sessions_with_data.sort(key=lambda x: x.get("date", "") + x.get("time", ""), reverse=True)
    return {"conversations": sessions_with_data[:count]}


@router.post("/api/conversations/fork")
async def fork_conversation(request: ForkRequest):
    """Fork an existing conversation into a new session."""
    messages = load_conversation_into_context(session_id=request.session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")

    new_session_id = str(uuid.uuid4())
    agent = create_agent(persona_name="friend", tools=FRIEND_TOOLS)

    context = agent.get_context()
    for msg in messages:
        context.append({"role": msg["role"], "content": msg["content"]})

    sessions[new_session_id] = {
        "agent": agent,
        "created": datetime.now(),
        "last_used": datetime.now(),
        "forked_from": request.session_id
    }

    return {
        "new_session_id": new_session_id,
        "forked_from": request.session_id,
        "messages": messages
    }


@router.delete("/api/conversations/{session_id}")
async def delete_conversation_endpoint(session_id: str):
    """Permanently delete a conversation from history."""
    result = delete_conversation(session_id)
    if "No conversation found" in result:
        raise HTTPException(status_code=404, detail=result)
    return {"status": "success", "message": result}
