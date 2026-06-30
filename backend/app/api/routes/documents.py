"""REST endpoints for document metadata and uploads."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_document_analysis_service,
    get_document_service,
    get_session,
)
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.schemas.document_analysis import DocumentAnalysisResponse
from app.schemas.processing_job import ProcessingJobResponse
from app.services.analyses import (
    AnalysisDocumentNotFoundError,
    DocumentAnalysisNotFoundError,
    DocumentAnalysisService,
)
from app.services.documents import (
    DocumentNotFoundError,
    DocumentService,
    DocumentTooLargeError,
    EmptyDocumentError,
    InvalidFilenameError,
    JobEnqueueError,
    UnsupportedDocumentTypeError,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF or CSV document")],
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentUploadResponse:
    """Persist an uploaded document and enqueue background processing."""

    try:
        result = await service.upload(session, file)
    except InvalidFilenameError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid filename is required",
        ) from exc
    except UnsupportedDocumentTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and CSV documents are supported",
        ) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded document is empty",
        ) from exc
    except DocumentTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Uploaded document exceeds the configured size limit",
        ) from exc
    except JobEnqueueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Document persisted but processing could not be queued",
                "document_id": str(exc.document_id),
                "job_id": str(exc.job_id),
            },
        ) from exc
    finally:
        await file.close()

    return DocumentUploadResponse(
        document=DocumentResponse.model_validate(result.document),
        job=ProcessingJobResponse.model_validate(result.job),
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[DocumentService, Depends(get_document_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentListResponse:
    """Return document metadata using bounded offset pagination."""

    documents, total = await service.list(
        session,
        limit=limit,
        offset=offset,
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(item) for item in documents],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{document_id}/analysis", response_model=DocumentAnalysisResponse)
async def get_document_analysis(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[
        DocumentAnalysisService,
        Depends(get_document_analysis_service),
    ],
) -> DocumentAnalysisResponse:
    """Return the latest persisted analysis state for a document."""

    try:
        analysis = await service.get_latest(session, document_id)
    except AnalysisDocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        ) from exc
    except DocumentAnalysisNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document analysis not found",
        ) from exc

    return DocumentAnalysisResponse.model_validate(analysis)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    """Return metadata for one uploaded document."""

    try:
        document = await service.get(session, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        ) from exc

    return DocumentResponse.model_validate(document)
