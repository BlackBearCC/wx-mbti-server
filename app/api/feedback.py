from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

# Placeholder for user authentication dependency
async def get_current_user_placeholder():
    # In a real app, this would validate a token and return user info
    return {"userId": "mock_user_123", "username": "testuser"}

router = APIRouter()

# --- Pydantic Models for Feedback ---

class FeedbackSubmissionRequest(BaseModel):
    feedback_type: str # e.g., "bug_report", "feature_request", "general_comment", "character_response_issue"
    subject: Optional[str] = None
    description: str
    page_url: Optional[str] = None # URL where the feedback is relevant
    character_id: Optional[str] = None # If feedback is about a specific character
    chat_message_id: Optional[str] = None # If feedback is about a specific chat message
    additional_data: Optional[Dict[str, Any]] = None

class FeedbackSubmissionResponseData(BaseModel):
    feedback_id: str
    message: str
    timestamp: datetime

class FeedbackSubmissionResponse(BaseModel):
    code: int = 200
    data: FeedbackSubmissionResponseData

# Mock database for feedback (very simplified)
fake_feedback_db: Dict[str, Dict[str, Any]] = {}

@router.post("/submit", response_model=FeedbackSubmissionResponse)
async def submit_feedback(feedback_data: FeedbackSubmissionRequest, current_user: dict = Depends(get_current_user_placeholder)):
    """提交用户反馈"""
    user_id = current_user['userId']
    timestamp = datetime.utcnow()
    feedback_id = f"fb_{timestamp.timestamp()}_{user_id[:5]}"

    # Store feedback (mock)
    fake_feedback_db[feedback_id] = {
        "feedback_id": feedback_id,
        "user_id": user_id,
        "timestamp": timestamp,
        "feedback_type": feedback_data.feedback_type,
        "subject": feedback_data.subject,
        "description": feedback_data.description,
        "page_url": feedback_data.page_url,
        "character_id": feedback_data.character_id,
        "chat_message_id": feedback_data.chat_message_id,
        "additional_data": feedback_data.additional_data,
        "status": "received" # e.g., received, under_review, resolved
    }

    return FeedbackSubmissionResponse(data=FeedbackSubmissionResponseData(
        feedback_id=feedback_id,
        message="Feedback submitted successfully. Thank you!",
        timestamp=timestamp
    ))

# Potential future endpoint for admins to view feedback
# @router.get("/list", tags=["Admin Only"])
# async def list_feedback(current_user: dict = Depends(get_current_user_placeholder)):
#     # Add admin role check here
#     return {"feedback_entries": list(fake_feedback_db.values())}