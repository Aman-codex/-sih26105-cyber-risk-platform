from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assistant import AssistantAnswerRead, AssistantQuestion
from app.services.assistant import answer_question

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/ask", response_model=AssistantAnswerRead)
def ask(payload: AssistantQuestion, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    A deterministic, keyword-routed assistant — not a call to an external
    LLM. Every number in every answer is read straight from the platform's
    own Risk Engine / Optimizer / Compliance calculations, so it cannot
    invent a risk or financial figure. Supports 5 question categories:
    highest financial risk, main risk drivers, recommended controls,
    compliance gaps, and risk trend over time (the last one is honestly
    reported as not yet available, rather than guessed).
    Read-only; available to every role.
    """
    result = answer_question(db, current_user.organization_id, payload.question)
    return AssistantAnswerRead(intent=result.intent, answer=result.answer, supporting_data=result.supporting_data)
