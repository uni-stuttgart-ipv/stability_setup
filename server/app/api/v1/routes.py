from fastapi import APIRouter
from app.schemas import Item
from typing import List

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/items", response_model=List[Item])
async def list_items():
    return [
        {"id": 1, "name": "Example item", "description": "A sample boilerplate item."}
    ]


@router.post("/items", response_model=Item, status_code=201)
async def create_item(item: Item):
    return item
