from fastapi import APIRouter
from pydantic import BaseModel


class HelloResponse(BaseModel):
    message: str


router = APIRouter()


@router.get("/hello", response_model=HelloResponse)
def hello() -> HelloResponse:
    return HelloResponse(message="Hello, World!")
