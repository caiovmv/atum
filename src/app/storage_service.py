"""
storage_service — abstração unificada para storage de objetos.

Backends suportados:
  minio  → S3-compatible via boto3 (MinIO, AWS S3, Cloudflare R2, etc.)
  local  → filesystem local (fallback para dev sem MinIO)

Configuração via variáveis de ambiente:
  STORAGE_BACKEND   = minio | local  (default: local)
  MINIO_ENDPOINT    = http://minio:9000
  MINIO_ACCESS_KEY  = minioadmin
  MINIO_SECRET_KEY  = minioadmin123
  MINIO_REGION      = us-east-1  (opcional)

Buckets criados automaticamente no startup:
  loombeat-hls     → segmentos HLS
  loombeat-music   → arquivos de áudio
  loombeat-covers  → capas de álbuns/filmes
"""

from __future__ import annotations

import logging
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

_log = logging.getLogger(__name__)

BUCKET_HLS    = "loombeat-hls"
BUCKET_MUSIC  = "loombeat-music"
BUCKET_COVERS = "loombeat-covers"

ALL_BUCKETS = [BUCKET_HLS, BUCKET_MUSIC, BUCKET_COVERS]


# ─── protocolo / interface ────────────────────────────────────────────────────

class StorageBackend(ABC):
    """Interface unificada para operações de objeto."""

    @abstractmethod
    def upload_file(self, bucket: str, key: str, local_path: Path, content_type: str = "application/octet-stream") -> None:
        """Faz upload de um arquivo local para o backend."""

    @abstractmethod
    def upload_fileobj(self, bucket: str, key: str, fileobj: BinaryIO, content_type: str = "application/octet-stream") -> None:
        """Faz upload de um file-like object para o backend."""

    @abstractmethod
    def download_file(self, bucket: str, key: str, local_path: Path) -> None:
        """Baixa um objeto do backend para um arquivo local."""

    @abstractmethod
    def presign_get(self, bucket: str, key: str, expires_sec: int = 3600) -> str:
        """Gera URL pré-assinada para GET (leitura temporária)."""

    @abstractmethod
    def delete(self, bucket: str, key: str) -> None:
        """Remove um objeto do backend."""

    @abstractmethod
    def exists(self, bucket: str, key: str) -> bool:
        """Verifica se um objeto existe no backend."""

    @abstractmethod
    def object_size(self, bucket: str, key: str) -> int:
        """Retorna o tamanho em bytes de um objeto."""

    @abstractmethod
    def list_objects(self, bucket: str, prefix: str = "") -> list[str]:
        """Lista chaves de objetos no bucket com o prefix dado."""

    @abstractmethod
    def bucket_size_bytes(self, bucket: str, prefix: str = "") -> int:
        """Retorna o tamanho total em bytes de todos os objetos no prefix."""

    @abstractmethod
    def ensure_buckets(self) -> None:
        """Cria os buckets padrão se não existirem."""


# ─── backend MinIO / S3 ───────────────────────────────────────────────────────

class MinIOBackend(StorageBackend):
    """Backend S3-compatible usando boto3."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
    ) -> None:
        import boto3
        from botocore.config import Config

        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )
        self._endpoint = endpoint

    def upload_file(self, bucket: str, key: str, local_path: Path, content_type: str = "application/octet-stream") -> None:
        self._client.upload_file(
            str(local_path), bucket, key,
            ExtraArgs={"ContentType": content_type},
        )

    def upload_fileobj(self, bucket: str, key: str, fileobj: BinaryIO, content_type: str = "application/octet-stream") -> None:
        self._client.upload_fileobj(
            fileobj, bucket, key,
            ExtraArgs={"ContentType": content_type},
        )

    def download_file(self, bucket: str, key: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._client.download_file(bucket, key, str(local_path))

    def presign_get(self, bucket: str, key: str, expires_sec: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_sec,
        )

    def delete(self, bucket: str, key: str) -> None:
        self._client.delete_object(Bucket=bucket, Key=key)

    def exists(self, bucket: str, key: str) -> bool:
        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except self._client.exceptions.ClientError:
            return False

    def object_size(self, bucket: str, key: str) -> int:
        resp = self._client.head_object(Bucket=bucket, Key=key)
        return int(resp["ContentLength"])

    def list_objects(self, bucket: str, prefix: str = "") -> list[str]:
        keys: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys

    def bucket_size_bytes(self, bucket: str, prefix: str = "") -> int:
        total = 0
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                total += obj.get("Size", 0)
        return total

    def ensure_buckets(self) -> None:
        existing = {b["Name"] for b in self._client.list_buckets().get("Buckets", [])}
        for bucket in ALL_BUCKETS:
            if bucket not in existing:
                self._client.create_bucket(Bucket=bucket)
                _log.info("storage: bucket criado → %s", bucket)


# ─── backend local (filesystem) ──────────────────────────────────────────────

class LocalBackend(StorageBackend):
    """Backend filesystem para desenvolvimento sem MinIO."""

    def __init__(self, base_dir: str = "/tmp/loombeat-storage") -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, bucket: str, key: str) -> Path:
        p = self._base / bucket / key
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def upload_file(self, bucket: str, key: str, local_path: Path, content_type: str = "application/octet-stream") -> None:
        dest = self._path(bucket, key)
        shutil.copy2(local_path, dest)

    def upload_fileobj(self, bucket: str, key: str, fileobj: BinaryIO, content_type: str = "application/octet-stream") -> None:
        dest = self._path(bucket, key)
        with open(dest, "wb") as f:
            shutil.copyfileobj(fileobj, f)

    def download_file(self, bucket: str, key: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self._path(bucket, key), local_path)

    def presign_get(self, bucket: str, key: str, expires_sec: int = 3600) -> str:
        # Em modo local retorna caminho direto (não é uma URL assinada real)
        return f"/storage-local/{bucket}/{key}"

    def delete(self, bucket: str, key: str) -> None:
        p = self._path(bucket, key)
        if p.exists():
            p.unlink()

    def exists(self, bucket: str, key: str) -> bool:
        return self._path(bucket, key).exists()

    def object_size(self, bucket: str, key: str) -> int:
        p = self._path(bucket, key)
        return p.stat().st_size if p.exists() else 0

    def list_objects(self, bucket: str, prefix: str = "") -> list[str]:
        base = self._base / bucket
        if not base.exists():
            return []
        result = []
        for p in base.rglob("*"):
            if p.is_file():
                rel = str(p.relative_to(base))
                if rel.startswith(prefix):
                    result.append(rel)
        return result

    def bucket_size_bytes(self, bucket: str, prefix: str = "") -> int:
        return sum(
            Path(self._base / bucket / k).stat().st_size
            for k in self.list_objects(bucket, prefix)
            if (self._base / bucket / k).exists()
        )

    def ensure_buckets(self) -> None:
        for bucket in ALL_BUCKETS:
            (self._base / bucket).mkdir(parents=True, exist_ok=True)


# ─── singleton / factory ──────────────────────────────────────────────────────

_backend: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """Retorna o backend de storage configurado (singleton)."""
    global _backend
    if _backend is None:
        _backend = _build_backend()
    return _backend


def _build_backend() -> StorageBackend:
    mode = os.getenv("STORAGE_BACKEND", "local").lower()

    if mode == "minio":
        endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
        region = os.getenv("MINIO_REGION", "us-east-1")
        _log.info("storage: usando backend MinIO → %s", endpoint)
        return MinIOBackend(endpoint, access_key, secret_key, region)

    base_dir = os.getenv("LOCAL_STORAGE_DIR", "/tmp/loombeat-storage")
    _log.info("storage: usando backend local → %s", base_dir)
    return LocalBackend(base_dir)


def init_storage() -> None:
    """Garante que os buckets existam. Chamar no startup da aplicação."""
    try:
        storage = get_storage()
        storage.ensure_buckets()
        _log.info("storage: buckets verificados/criados com sucesso")
    except Exception:
        _log.exception("storage: falha ao inicializar buckets")


# ─── helpers de key convenção ────────────────────────────────────────────────

def hls_prefix(family_id: str, library_id: int, file_index: int) -> str:
    """Prefixo padrão para segmentos HLS de um item."""
    return f"{family_id}/{library_id}_{file_index}/"


def music_key(family_id: str, filename: str) -> str:
    """Chave padrão para arquivo de música no bucket loombeat-music."""
    return f"{family_id}/{filename}"


def cover_key(item_id: str, ext: str = "jpg") -> str:
    """Chave padrão para capa de álbum/filme no bucket loombeat-covers."""
    return f"{item_id}.{ext}"
