from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class DocumentEntity:
    id: int
    content: int  # This is the OID — a reference to the large object
    created_at: Optional[datetime]
    deleted_at: Optional[datetime]
    name: str
    size: int
    type: str
    updated_at: Optional[datetime]
    chat_id: int
    source: str
