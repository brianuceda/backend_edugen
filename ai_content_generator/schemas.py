from __future__ import annotations

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, UUID4, Field


class BlockV2(BaseModel):
    id: UUID4
    type: Literal[
        "hero",
        "heading",
        "paragraph",
        "list",
        "image",
        "callout",
        "form",
        "quiz",
        "flashcard",
    ]
    version: Literal[2] = 2
    props: Dict[str, Any] = Field(default_factory=dict)
    children: Optional[List[UUID4]] = None


class DocV2(BaseModel):
    id: UUID4
    version: Literal[2] = 2
    blocks: List[BlockV2]
    meta: Dict[str, Any] = Field(default_factory=dict)


# Optional helper to validate a candidate document structure
def validate_doc_v2(data: Any) -> DocV2:
    return DocV2.model_validate(data)

