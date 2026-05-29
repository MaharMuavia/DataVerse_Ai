"""Workspace management routes.

Workspaces are user-owned containers for datasets and analyses.
Each user can have multiple workspaces for organizing projects.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import get_current_user
from ..core.logger import logger
from ..api.schemas import User
from ..db.base import get_session
from ..db.models import Workspace, User as UserModel

router = APIRouter()


class WorkspaceCreate(BaseModel):
    """Request to create a workspace."""
    name: str
    description: str | None = None


class WorkspaceResponse(BaseModel):
    """Workspace response schema."""
    id: str
    name: str
    description: str | None
    created_at: str
    updated_at: str


@router.post("/", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Create a new workspace for the current user.
    
    Parameters:
        name: Workspace name
        description: Optional workspace description
    
    Returns: Created workspace object
    """
    try:
        # Create workspace
        workspace = Workspace(
            user_id=current_user.id,
            name=workspace_data.name,
            description=workspace_data.description
        )
        db.add(workspace)
        await db.commit()
        await db.refresh(workspace)
        
        logger.info(f"Workspace created: {workspace.id} for user {current_user.username}")
        
        return WorkspaceResponse(
            id=str(workspace.id),
            name=workspace.name,
            description=workspace.description,
            created_at=workspace.created_at.isoformat(),
            updated_at=workspace.updated_at.isoformat()
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating workspace"
        )


@router.get("/", response_model=List[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    List all workspaces for the current user.
    
    Returns: List of workspace objects
    """
    try:
        stmt = select(Workspace).where(Workspace.user_id == current_user.id)
        result = await db.execute(stmt)
        workspaces = result.scalars().all()
        
        return [
            WorkspaceResponse(
                id=str(w.id),
                name=w.name,
                description=w.description,
                created_at=w.created_at.isoformat(),
                updated_at=w.updated_at.isoformat()
            )
            for w in workspaces
        ]
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing workspaces"
        )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Get a specific workspace.
    
    The workspace must belong to the current user (authorization check).
    """
    try:
        workspace = await db.get(Workspace, workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Check authorization
        if str(workspace.user_id) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return WorkspaceResponse(
            id=str(workspace.id),
            name=workspace.name,
            description=workspace.description,
            created_at=workspace.created_at.isoformat(),
            updated_at=workspace.updated_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting workspace"
        )
