"""Dataset management routes.

Datasets are uploaded files associated with workspaces.
This module handles uploads, profiling, preview, and metadata.
"""
from __future__ import annotations

import io
import os
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import get_current_user
from ..core.logger import logger
from ..core.config import settings
from ..api.schemas import User
from ..db.base import get_session
from ..db.models import Workspace, Dataset
from .upload_parsing import parse_uploaded_dataframe

router = APIRouter()


@router.post("/{workspace_id}/datasets/upload", status_code=202)
async def upload_dataset(
    workspace_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Upload a dataset file to a workspace.
    
    Supported formats: CSV, XLSX, XLS, JSON, Parquet
    Max file size: Configured in settings (default 100MB)
    
    Returns: Dataset metadata with status "uploading"
    The server will profile the dataset asynchronously.
    """
    try:
        # Verify workspace access
        workspace = await db.get(Workspace, workspace_id)
        if not workspace or str(workspace.user_id) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Validate file
        MAX_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        contents = await file.read()
        
        if len(contents) > MAX_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit"
            )
        
        # Determine file type
        filename_lower = (file.filename or "upload").lower()
        file_type = None
        
        if filename_lower.endswith('.csv'):
            file_type = 'csv'
        elif filename_lower.endswith(('.xlsx', '.xls')):
            file_type = 'xlsx'
        elif filename_lower.endswith('.json'):
            file_type = 'json'
        elif filename_lower.endswith('.parquet'):
            file_type = 'parquet'
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format. Supported: CSV, XLSX, JSON, Parquet"
            )
        
        # Parse file to get schema
        try:
            if file_type == 'csv':
                df = parse_uploaded_dataframe(file.filename or "upload.csv", contents).head(1000)
            elif file_type == 'xlsx':
                df = parse_uploaded_dataframe(file.filename or "upload.xlsx", contents).head(1000)
            elif file_type == 'json':
                df = pd.read_json(io.BytesIO(contents))
            elif file_type == 'parquet':
                df = pd.read_parquet(io.BytesIO(contents))
        except Exception as e:
            logger.error(f"Error parsing file: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file format: {str(e)}"
            )
        
        # Create dataset record
        schema_json = {col: str(df[col].dtype) for col in df.columns}
        
        dataset = Dataset(
            workspace_id=workspace_id,
            name=file.filename or "Unnamed Dataset",
            original_filename=file.filename,
            storage_path="",
            file_type=file_type,
            row_count=len(df),
            col_count=len(df.columns),
            schema_json=schema_json,
            status="profiling"  # Will be updated after profiling
        )
        db.add(dataset)

        # Flush first so dataset.id is available for deterministic storage paths.
        await db.flush()

        # Store file using configured storage provider.
        upload_name = file.filename or "dataset_upload"
        try:
            from ..core.storage import get_storage

            storage = get_storage()
            storage_prefix = f"datasets/{workspace_id}/{dataset.id}"
            storage_path = f"{storage_prefix}/{upload_name}"
            storage.upload(storage_path, contents)
            logger.info(f"File stored: {storage_path}")
            dataset.storage_path = storage_path
        except Exception as storage_error:
            logger.warning(f"Storage error: {storage_error}")
            # Fall back to local storage for resilience in dev/local environments.
            import tempfile

            temp_dir = tempfile.gettempdir()
            storage_path = os.path.join(temp_dir, f"{workspace_id}_{upload_name}")
            with open(storage_path, 'wb') as f:
                f.write(contents)
            dataset.storage_path = storage_path

        await db.commit()
        await db.refresh(dataset)
        
        logger.info(f"Dataset uploaded: {dataset.id}")
        
        # Trigger background profiling task
        try:
            from ..core.celery_config import celery_app
            from ..tasks import profile_dataset_task
            
            # Queue profiling task
            profile_dataset_task.delay(str(dataset.id), storage_path)
            logger.info(f"Profiling task queued for dataset {dataset.id}")
        except Exception as task_error:
            logger.warning(f"Could not queue profiling task: {task_error}")
            # Continue anyway; dataset is created, just won't have profile yet
        
        return {
            "id": str(dataset.id),
            "name": dataset.name,
            "status": dataset.status,
            "row_count": dataset.row_count,
            "col_count": dataset.col_count,
            "schema": schema_json,
            "created_at": dataset.created_at.isoformat(),
            "message": "File uploaded and profiling started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error uploading dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading dataset"
        )


@router.get("/{workspace_id}/datasets", response_model=List[dict])
async def list_datasets(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """List all datasets in a workspace."""
    try:
        workspace = await db.get(Workspace, workspace_id)
        if not workspace or str(workspace.user_id) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        stmt = select(Dataset).where(
            Dataset.workspace_id == workspace_id
        ).order_by(Dataset.created_at.desc())
        result = await db.execute(stmt)
        datasets = result.scalars().all()
        
        return [
            {
                "id": str(d.id),
                "name": d.name,
                "status": d.status,
                "row_count": d.row_count,
                "col_count": d.col_count,
                "file_type": d.file_type,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat()
            }
            for d in datasets
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing datasets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing datasets"
        )


@router.get("/{workspace_id}/datasets/{dataset_id}", response_model=dict)
async def get_dataset(
    workspace_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get dataset metadata and profiling information."""
    try:
        workspace = await db.get(Workspace, workspace_id)
        if not workspace or str(workspace.user_id) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        dataset = await db.get(Dataset, dataset_id)
        if not dataset or str(dataset.workspace_id) != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )
        
        return {
            "id": str(dataset.id),
            "name": dataset.name,
            "original_filename": dataset.original_filename,
            "status": dataset.status,
            "row_count": dataset.row_count,
            "col_count": dataset.col_count,
            "file_type": dataset.file_type,
            "schema": dataset.schema_json,
            "profile": dataset.profile_json,
            "error_message": dataset.error_message,
            "created_at": dataset.created_at.isoformat(),
            "updated_at": dataset.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting dataset"
        )


@router.get("/{workspace_id}/datasets/{dataset_id}/preview", response_model=dict)
async def preview_dataset(
    workspace_id: str,
    dataset_id: str,
    rows: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get first N rows of dataset as sample."""
    try:
        workspace = await db.get(Workspace, workspace_id)
        if not workspace or str(workspace.user_id) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        dataset = await db.get(Dataset, dataset_id)
        if not dataset or str(dataset.workspace_id) != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )
        
        # Load sample from storage (works for local, MinIO, and S3 providers).
        try:
            source_buffer = None
            raw_bytes = None

            try:
                from ..core.storage import get_storage

                storage = get_storage()
                raw_bytes = storage.download(dataset.storage_path)
                source_buffer = io.BytesIO(raw_bytes)
            except Exception as storage_error:
                logger.debug(f"Storage download fallback to direct path: {storage_error}")
                if dataset.file_type in {"csv", "xlsx"}:
                    with open(dataset.storage_path, "rb") as source_file:
                        raw_bytes = source_file.read()

            if dataset.file_type == 'csv':
                df = parse_uploaded_dataframe(dataset.original_filename or "dataset.csv", raw_bytes or b"").head(rows)
            elif dataset.file_type == 'xlsx':
                df = parse_uploaded_dataframe(dataset.original_filename or "dataset.xlsx", raw_bytes or b"").head(rows)
            elif dataset.file_type == 'json':
                if source_buffer is not None:
                    df = pd.read_json(source_buffer).head(rows)
                else:
                    df = pd.read_json(dataset.storage_path).head(rows)
            elif dataset.file_type == 'parquet':
                if source_buffer is not None:
                    df = pd.read_parquet(source_buffer).head(rows)
                else:
                    df = pd.read_parquet(dataset.storage_path).head(rows)
            else:
                raise ValueError("Unsupported file type")
        except Exception as e:
            logger.error(f"Error reading dataset: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error reading dataset file"
            )
        
        return {
            "data": df.head(rows).to_dict(orient="records"),
            "columns": list(df.columns),
            "dtypes": {col: str(df[col].dtype) for col in df.columns},
            "row_count": len(df),
            "total_row_count": dataset.row_count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error previewing dataset"
        )
