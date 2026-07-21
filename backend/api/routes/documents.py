"""
Documents API Routes — Real file upload + Gemini analysis pipeline.
"""
import os
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from bson import ObjectId
import requests
from database.models.document import DocumentModel
from database.models.user import User
from services.contract_agent import ContractAgent

router = APIRouter(prefix="/api/documents", tags=["Documents"])
contract_agent = ContractAgent()


def load_document_bytes(file: Optional[UploadFile], blob_url: Optional[str]) -> tuple[bytes, str]:
    if file is not None:
        return file.file.read(), file.filename or "uploaded-document"

    if not blob_url:
        raise HTTPException(400, "A file upload or blob_url is required")

    response = requests.get(blob_url, timeout=30)
    if response.status_code >= 400:
        raise HTTPException(400, f"Unable to fetch uploaded blob: {response.status_code}")

    filename = os.path.basename(urlparse(blob_url).path) or "uploaded-document"
    return response.content, filename


class AskQuestionRequest(BaseModel):
    question: str
    clerk_id: Optional[str] = None


@router.post("/upload")
async def upload_document(
    file: Optional[UploadFile] = File(default=None),
    blob_url: Optional[str] = Form(default=None),
    filename: Optional[str] = Form(default=None),
    document_type: str = Form(default="rent_agreement"),
    clerk_id: Optional[str] = Form(default=None),
    property_id: Optional[str] = Form(default=None),
):
    """Upload a document, extract text, and run AI analysis."""
    source_name = filename or (file.filename if file and file.filename else None) or "uploaded-document"
    file_bytes, resolved_name = load_document_bytes(file, blob_url)
    if not file_bytes:
        raise HTTPException(400, "Empty file")

    local_url = blob_url or f"upload://{resolved_name}"

    # Run the analysis pipeline
    try:
        analysis = await contract_agent.analyze_document(
            file_bytes=file_bytes,
            filename=file.filename,
            doc_type=document_type,
            user_id=clerk_id,
            property_id=property_id,
        )
    except Exception as e:
        analysis = {
            "status": "error",
            "message": f"Analysis failed: {str(e)}",
            "extracted_text": "",
            "clause_analysis": [],
            "ai_summary": "Document uploaded but analysis failed.",
            "extracted_data": {},
        }

    # Resolve user
    user_ref = None
    if clerk_id:
        user = await User.find_one(User.clerk_id == clerk_id)
        if user:
            user_ref = user.id

    # Save to MongoDB
    doc = DocumentModel(
        user=user_ref,
        property=ObjectId(property_id) if property_id and ObjectId.is_valid(property_id) else None,
        document_type=document_type,
        cloudinary_url=local_url,
        filename=source_name,
        ai_summary=analysis.get("ai_summary", ""),
        extracted_text=analysis.get("extracted_text", ""),
        extracted_data=analysis.get("extracted_data", {}),
        clause_analysis=analysis.get("clause_analysis", []),
    )
    await doc.insert()

    return {
        "status": "success",
        "document_id": str(doc.id),
        "filename": file.filename,
        "ai_summary": doc.ai_summary,
        "clause_analysis": doc.clause_analysis,
        "extracted_data": doc.extracted_data,
    }


@router.get("/")
async def list_documents(
    clerk_id: Optional[str] = Query(default=None),
):
    """List all documents for a user."""
    if clerk_id:
        user = await User.find_one(User.clerk_id == clerk_id)
        if user:
            docs = await DocumentModel.find(DocumentModel.user == user.id).to_list(length=100)
        else:
            docs = []
    else:
        # Return all documents if no user filter (for demo)
        docs = await DocumentModel.find().to_list(length=100)

    result = []
    for doc in docs:
        high_risk = sum(1 for c in (doc.clause_analysis or []) if c.get("risk_level") == "high")
        caution = sum(1 for c in (doc.clause_analysis or []) if c.get("risk_level") == "caution")

        result.append({
            "id": str(doc.id),
            "document_type": doc.document_type,
            "filename": doc.filename,
            "ai_summary": doc.ai_summary,
            "clause_count": len(doc.clause_analysis or []),
            "high_risk_clauses": high_risk,
            "caution_clauses": caution,
            "extracted_data": doc.extracted_data,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "property_id": str(doc.property) if doc.property else None,
            "url": doc.cloudinary_url,
        })

    return {"status": "success", "data": result}


@router.get("/{document_id}")
async def get_document(document_id: str):
    """Get a document with its full clause analysis."""
    if not ObjectId.is_valid(document_id):
        raise HTTPException(400, "Invalid document ID")

    doc = await DocumentModel.get(ObjectId(document_id))
    if not doc:
        raise HTTPException(404, "Document not found")

    return {
        "status": "success",
        "data": {
            "id": str(doc.id),
            "document_type": doc.document_type,
            "filename": doc.filename,
            "ai_summary": doc.ai_summary,
            "extracted_text": doc.extracted_text,
            "extracted_data": doc.extracted_data,
            "clause_analysis": doc.clause_analysis,
            "url": doc.cloudinary_url,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        },
    }


@router.post("/ask")
async def ask_documents(req: AskQuestionRequest):
    """Ask a natural language question about user's documents."""
    # Get user's documents
    docs = []
    if req.clerk_id:
        user = await User.find_one(User.clerk_id == req.clerk_id)
        if user:
            docs = await DocumentModel.find(DocumentModel.user == user.id).to_list(length=20)
    
    if not docs:
        # Fallback: use all documents (for demo)
        docs = await DocumentModel.find().to_list(length=20)

    if not docs:
        return {
            "status": "success",
            "answer": "No documents found. Please upload some documents first.",
            "sources": [],
        }

    result = await contract_agent.ask_question(req.question, docs)
    return {
        "status": "success",
        "answer": result.get("answer", "Could not find an answer."),
        "sources": result.get("sources", []),
    }


class SaveTranscriptRequest(BaseModel):
    property_id: str
    property_context: str
    clerk_id: Optional[str] = None
    transcript: List[Dict[str, str]]

@router.post("/save-transcript")
async def save_transcript(req: SaveTranscriptRequest):
    """Save a Vapi negotiation transcript as a document with an AI summary."""
    if not req.transcript:
        raise HTTPException(400, "Transcript is empty")

    summary = await contract_agent.summarize_transcript(req.transcript, req.property_context)
    
    user_ref = None
    if req.clerk_id:
        user = await User.find_one(User.clerk_id == req.clerk_id)
        if user:
            user_ref = user.id

    doc = DocumentModel(
        user=user_ref,
        property=ObjectId(req.property_id) if ObjectId.is_valid(req.property_id) else None,
        document_type="negotiation_transcript",
        filename=f"Negotiation Transcript - {req.property_context}",
        ai_summary=summary,
        extracted_text="\n".join([f"{msg.get('role', 'unknown').capitalize()}: {msg.get('content', '')}" for msg in req.transcript]),
        extracted_data={"messages": req.transcript},
    )
    await doc.insert()
    
    return {
        "status": "success",
        "document_id": str(doc.id),
        "ai_summary": summary,
    }
