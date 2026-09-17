from pydantic import BaseModel


class AssistantQuestion(BaseModel):
    question: str


class AssistantAnswerRead(BaseModel):
    intent: str
    answer: str
    supporting_data: dict
