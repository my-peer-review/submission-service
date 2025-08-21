from typing import Any, Optional
from pydantic import BaseModel

class StoredFile(BaseModel):
    file_id: str
    filename: str
    size: int
    content_type: Optional[str] = None
    uri: str                  
    checksum: Optional[str] = None
    metadata: dict[str, Any] = {}

class FileInfo(BaseModel):
    file_id: str
    filename: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None
    metadata: dict[str, Any] = {}