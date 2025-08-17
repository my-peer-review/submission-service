# app/database/gridfs_storage.py
from __future__ import annotations

import hashlib
from typing import AsyncIterator, Optional, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from app.database.base import BinaryStorage
from app.schemas.file import StoredFile, FileInfo

class GridFSStorage(BinaryStorage):
    """
    Implementazione BinaryStorage basata su MongoDB GridFS (Motor 3.7.x / PyMongo 4.x).

    Regole API Motor:
      - open_upload_stream(...)     -> NON è coroutine (ritorna subito GridIn)
      - open_download_stream(...)   -> È coroutine (va await-ata, ritorna GridOut)
      - read/write/close            -> metodi async (vanno await-ati)
    """

    def __init__(
        self,
        *,
        bucket: AsyncIOMotorGridFSBucket,
        bucket_name: str = "uploads",
        read_chunk: int = 1024 * 1024,
    ):
        self.bucket = bucket
        self.bucket_name = bucket_name
        self.read_chunk = read_chunk

    async def upload(
        self,
        *,
        filename: str,
        content_type: Optional[str],
        data: AsyncIterator[bytes],
        metadata: Optional[dict[str, Any]] = None,
    ) -> StoredFile:
        """
        Carica un file in GridFS in streaming (no filesystem locale).
        """
        meta = dict(metadata or {})
        if content_type:
            meta.setdefault("contentType", content_type)

        # open_upload_stream: NON async
        grid_in = self.bucket.open_upload_stream(filename=filename, metadata=meta)

        hasher = hashlib.sha256()
        size = 0
        try:
            async for chunk in data:
                size += len(chunk)
                hasher.update(chunk)
                await grid_in.write(chunk)  # async
        finally:
            # close è async
            res = grid_in.close()
            # close() è awaitable nelle versioni attuali
            try:
                await res
            except TypeError:
                # fallback nel raro caso fosse sinc
                pass

        file_id = str(grid_in._id)
        return StoredFile(
            file_id=file_id,
            filename=filename,
            size=size,
            content_type=content_type,
            checksum=hasher.hexdigest(),
            uri=f"gridfs://{self.bucket_name}/{file_id}",
            metadata=meta,
        )

    async def stream(self, file_id: str) -> AsyncIterator[bytes]:
        """
        Restituisce uno stream async del contenuto del file.
        """
        # open_download_stream: È async
        s = await self.bucket.open_download_stream(ObjectId(file_id))
        try:
            while True:
                chunk = await s.read(self.read_chunk)  # async
                if not chunk:
                    break
                yield chunk
        finally:
            close = getattr(s, "close", None)
            if callable(close):
                res = close()
                try:
                    await res  # async
                except TypeError:
                    pass

    async def info(self, file_id: str) -> Optional[FileInfo]:
        """
        Ritorna metadati base (filename, content_type, size) senza scaricare il file.
        """
        try:
            s = await self.bucket.open_download_stream(ObjectId(file_id))
        except Exception:
            return None

        try:
            metadata = getattr(s, "metadata", None) or {}
            return FileInfo(
                file_id=file_id,
                filename=getattr(s, "filename", None),
                content_type=metadata.get("contentType"),
                size=getattr(s, "length", None),
                metadata=metadata,
            )
        finally:
            close = getattr(s, "close", None)
            if callable(close):
                res = close()
                try:
                    await res
                except TypeError:
                    pass

    async def delete(self, file_id: str) -> bool:
        """
        Elimina un file da GridFS.
        """
        try:
            await self.bucket.delete(ObjectId(file_id))
            return True
        except Exception:
            return False
