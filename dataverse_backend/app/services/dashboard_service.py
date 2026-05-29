from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.schemas import User
from ..db.models import Conversation, Dataset, User as UserModel, Workspace
from .billing_service import build_billing_overview
from .model_catalog import get_model_catalog


def assemble_dashboard_summary(
    *,
    user: Dict[str, Any],
    workspaces: Iterable[Dict[str, Any]],
    datasets: Iterable[Dict[str, Any]],
    conversations: Iterable[Dict[str, Any]],
    billing_overview: Dict[str, Any],
    model_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    workspace_list = list(workspaces)
    dataset_list = list(datasets)
    conversation_list = list(conversations)

    datasets_by_workspace: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for dataset in dataset_list:
        datasets_by_workspace[str(dataset["workspace_id"])].append(dataset)

    conversations_by_workspace: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for conversation in conversation_list:
        conversations_by_workspace[str(conversation["workspace_id"])].append(conversation)

    workspace_cards = []
    for workspace in workspace_list:
        workspace_id = str(workspace["id"])
        workspace_cards.append(
            {
                **workspace,
                "dataset_count": len(datasets_by_workspace[workspace_id]),
                "conversation_count": len(conversations_by_workspace[workspace_id]),
                "ready_dataset_count": sum(
                    1 for dataset in datasets_by_workspace[workspace_id] if dataset.get("status") == "ready"
                ),
            }
        )

    recent_conversations = sorted(
        conversation_list,
        key=lambda item: item.get("updated_at", ""),
        reverse=True,
    )[:5]

    return {
        "user": user,
        "billing": billing_overview,
        "ai_catalog": model_catalog,
        "stats": {
            "workspace_count": len(workspace_list),
            "dataset_count": len(dataset_list),
            "conversation_count": len(conversation_list),
            "ready_dataset_count": sum(1 for dataset in dataset_list if dataset.get("status") == "ready"),
        },
        "workspaces": workspace_cards,
        "recent_conversations": recent_conversations,
    }


async def build_dashboard_summary_for_user(*, db: AsyncSession, current_user: User) -> Dict[str, Any]:
    current_plan = "free"
    if current_user.id:
        user_model = await db.get(UserModel, current_user.id)
        if user_model and user_model.plan:
            current_plan = user_model.plan

    workspace_result = await db.execute(
        select(Workspace).where(Workspace.user_id == current_user.id).order_by(Workspace.updated_at.desc())
    )
    workspaces = workspace_result.scalars().all()
    workspace_ids = [workspace.id for workspace in workspaces]

    datasets: List[Dataset] = []
    conversations: List[Conversation] = []

    if workspace_ids:
        dataset_result = await db.execute(
            select(Dataset).where(Dataset.workspace_id.in_(workspace_ids)).order_by(Dataset.updated_at.desc())
        )
        datasets = list(dataset_result.scalars().all())

        conversation_result = await db.execute(
            select(Conversation)
            .where(Conversation.workspace_id.in_(workspace_ids))
            .order_by(Conversation.updated_at.desc())
        )
        conversations = list(conversation_result.scalars().all())

    return assemble_dashboard_summary(
        user=current_user.model_dump(),
        workspaces=[
            {
                "id": str(workspace.id),
                "name": workspace.name,
                "description": workspace.description,
                "created_at": workspace.created_at.isoformat(),
                "updated_at": workspace.updated_at.isoformat(),
            }
            for workspace in workspaces
        ],
        datasets=[
            {
                "id": str(dataset.id),
                "workspace_id": str(dataset.workspace_id),
                "name": dataset.name,
                "status": dataset.status,
                "row_count": dataset.row_count,
                "col_count": dataset.col_count,
                "updated_at": dataset.updated_at.isoformat(),
            }
            for dataset in datasets
        ],
        conversations=[
            {
                "id": str(conversation.id),
                "workspace_id": str(conversation.workspace_id),
                "title": conversation.title,
                "updated_at": conversation.updated_at.isoformat(),
            }
            for conversation in conversations
        ],
        billing_overview=build_billing_overview(
            user_id=current_user.id or "",
            email=current_user.email,
            current_plan=current_plan,
        ),
        model_catalog=get_model_catalog(),
    )
