"""Conversation and messaging routes.

Conversations are chat sessions between users and AI agents.
Each conversation is associated with a workspace and optionally a dataset.

Streaming:
- POST /messages returns Server-Sent Events (SSE) stream
- Events: thinking, analysis_update, visualization, insight, response, error
"""
from __future__ import annotations

import asyncio
import json
from typing import List
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import get_current_user
from ..core.logger import logger
from ..api.schemas import User, MessageCreate, ConversationResponse
from ..db.base import get_session
from ..db.models import Workspace, Conversation, Message, Dataset
from ..workflow import run_analysis, add_message as add_to_session, load_session
from ..workflow.langgraph_runtime import run_graph_query

router = APIRouter()


@router.post("/{workspace_id}/conversations", response_model=dict, status_code=201)
async def create_conversation(
    workspace_id: str,
    dataset_id: str | None = None,
    title: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Create a new conversation in a workspace.
    
    Parameters:
        workspace_id: Workspace ID
        dataset_id: Optional dataset ID to analyze
        title: Optional conversation title
    
    Returns: Created conversation
    """
    try:
        # Verify workspace belongs to user
        workspace = await db.get(Workspace, workspace_id)
        if not workspace or str(workspace.user_id) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # If dataset_id provided, verify it exists in this workspace
        if dataset_id:
            dataset = await db.get(Dataset, dataset_id)
            if not dataset or str(dataset.workspace_id) != workspace_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Dataset not found in this workspace"
                )
        
        # Create conversation
        conversation = Conversation(
            user_id=current_user.id,
            workspace_id=workspace_id,
            dataset_id=dataset_id,
            title=title or "New Conversation"
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        logger.info(f"Conversation created: {conversation.id}")
        
        return {
            "id": str(conversation.id),
            "title": conversation.title,
            "dataset_id": str(conversation.dataset_id) if conversation.dataset_id else None,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating conversation"
        )


@router.get("/{workspace_id}/conversations", response_model=List[dict])
async def list_conversations(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """List all conversations in a workspace."""
    try:
        workspace = await db.get(Workspace, workspace_id)
        if not workspace or str(workspace.user_id) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        stmt = select(Conversation).where(
            Conversation.workspace_id == workspace_id
        ).order_by(Conversation.updated_at.desc())
        result = await db.execute(stmt)
        conversations = result.scalars().all()
        
        return [
            {
                "id": str(c.id),
                "title": c.title,
                "dataset_id": str(c.dataset_id) if c.dataset_id else None,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat()
            }
            for c in conversations
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing conversations"
        )


@router.get("/{workspace_id}/conversations/{conversation_id}", response_model=dict)
async def get_conversation(
    workspace_id: str,
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get a conversation and its message history."""
    try:
        workspace = await db.get(Workspace, workspace_id)
        if not workspace or str(workspace.user_id) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        conversation = await db.get(Conversation, conversation_id)
        if not conversation or str(conversation.workspace_id) != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Load messages
        stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc())
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        return {
            "id": str(conversation.id),
            "title": conversation.title,
            "dataset_id": str(conversation.dataset_id) if conversation.dataset_id else None,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "messages": [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "message_type": m.message_type,
                    "created_at": m.created_at.isoformat(),
                    "payload_json": m.payload_json
                }
                for m in messages
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting conversation"
        )


@router.post("/{workspace_id}/conversations/{conversation_id}/messages")
async def send_message(
    workspace_id: str,
    conversation_id: str,
    message_data: MessageCreate,
    use_graph: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Send a message to a conversation and get streaming AI response.
    
    Uses Server-Sent Events (SSE) to stream agent responses.
    
    Event types:
    - thinking: Agent is processing
    - analysis_update: Analysis results available
    - visualization: Chart specifications
    - insight: Business insight text
    - response: Final response with all data
    - error: Error occurred
    
    Returns: text/event-stream with SSE events
    """
    try:
        # Verify access
        workspace = await db.get(Workspace, workspace_id)
        if not workspace or str(workspace.user_id) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        conversation = await db.get(Conversation, conversation_id)
        if not conversation or str(conversation.workspace_id) != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Save user message to database
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=message_data.content,
            message_type=message_data.message_type or "text"
        )
        db.add(user_message)
        await db.commit()
        await db.refresh(user_message)
        
        logger.info(f"User message saved: {user_message.id}")
        
        # Create SSE event generator
        async def event_generator():
            """Generate SSE events from agent orchestrator."""
            session_id = f"{conversation_id}:{uuid.uuid4()}"
            
            try:
                # Add to session memory
                add_to_session(session_id, "user", message_data.content)
                
                # Send thinking
                yield f"data: {json.dumps({'type': 'thinking', 'data': '🤔 Analyzing your query...'})}\n\n"
                await asyncio.sleep(0.1)
                
                if use_graph:
                    dataset_path_override = None
                    if conversation.dataset_id:
                        dataset = await db.get(Dataset, conversation.dataset_id)
                        if dataset:
                            dataset_path_override = dataset.storage_path

                    result = await run_graph_query(
                        session_id=session_id,
                        user_query=message_data.content,
                        db=db,
                        thread_id=conversation_id,
                        dataset_path_override=dataset_path_override,
                    )
                else:
                    # Run existing legacy workflow
                    result = await run_analysis(
                        session_id=session_id,
                        user_query=message_data.content,
                        dataset_id=str(conversation.dataset_id) if conversation.dataset_id else None
                    )
                
                # Stream analysis results
                if result.get("analysis_results"):
                    analysis_event = {
                        "type": "analysis_update",
                        "data": result["analysis_results"]
                    }
                    yield f"data: {json.dumps(analysis_event)}\n\n"
                    await asyncio.sleep(0.1)

                if result.get("insights"):
                    insight_data = result.get("insights")
                    if isinstance(insight_data, list):
                        analysis_event = {
                            "type": "analysis_update",
                            "data": {"insights": insight_data}
                        }
                        yield f"data: {json.dumps(analysis_event)}\n\n"
                        await asyncio.sleep(0.1)
                
                # Stream visualization if available
                if result.get("viz_spec"):
                    viz_event = {
                        "type": "visualization",
                        "data": result["viz_spec"]
                    }
                    yield f"data: {json.dumps(viz_event)}\n\n"
                    await asyncio.sleep(0.1)
                elif result.get("visualizations"):
                    viz_event = {
                        "type": "visualization",
                        "data": {"charts": result.get("visualizations")}
                    }
                    yield f"data: {json.dumps(viz_event)}\n\n"
                    await asyncio.sleep(0.1)
                
                # Stream insight
                final_response = result.get("final_response", "Analysis complete")
                insight_event = {
                    "type": "insight",
                    "data": final_response
                }
                yield f"data: {json.dumps(insight_event)}\n\n"
                await asyncio.sleep(0.1)
                
                # Save assistant response to database
                response_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=final_response,
                    message_type="insight",
                    payload_json={
                        "intent": result.get("intent", {}),
                        "analysis": result.get("analysis_results", {}),
                        "visualization": result.get("viz_spec"),
                    }
                )
                db.add(response_msg)
                await db.commit()
                
                # Send final response with all data
                response_event = {
                    "type": "response",
                    "data": {
                        "text": final_response,
                        "intent": result.get("intent", {}),
                        "viz": result.get("viz_spec"),
                        "analysis_complete": True,
                        "ml_job": result.get("ml_results"),
                    }
                }
                yield f"data: {json.dumps(response_event)}\n\n"
                
                logger.info(f"[SSE] Stream completed for conversation {conversation_id}")
                
            except Exception as e:
                logger.error(f"[SSE] Error generating events: {e}", exc_info=True)
                error_event = {
                    "type": "error",
                    "error": str(e)
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                
                # Save error message to database
                try:
                    error_msg = Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=f"Error: {str(e)}",
                        message_type="error",
                        payload_json={"error": str(e)}
                    )
                    db.add(error_msg)
                    await db.commit()
                except:
                    logger.error("Failed to save error message")
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing message"
        )
