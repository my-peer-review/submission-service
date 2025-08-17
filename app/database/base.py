# app/storage/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Any

from app.schemas.file import StoredFile, FileInfo

class BinaryStorage(ABC):
    """Interfaccia astratta per storage binario (streaming)."""

    @abstractmethod
    async def upload(
        self,
        *,
        filename: str,
        content_type: Optional[str],
        data: AsyncIterator[bytes],
        metadata: Optional[dict[str, Any]] = None,
    ) -> StoredFile:
        """Carica un file da uno stream di bytes e ritorna i metadati persistiti."""
        raise NotImplementedError

    @abstractmethod
    async def stream(self, file_id: str) -> AsyncIterator[bytes]:
        """Ritorna uno stream (async iterator) dei bytes di un file."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, file_id: str) -> bool:
        """Elimina un file per id."""
        raise NotImplementedError
    
    @abstractmethod
    async def info(self, file_id: str) -> Optional[FileInfo]:  
        """Ritorna i metadati di un file per id."""
        raise NotImplementedError
