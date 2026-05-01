"""Schemas connected with MinIO are defined here."""

from pydantic import BaseModel, Field


class MinioImagesURL(BaseModel):
    """Response model containing URLs for full-size and preview images."""

    image_url: str = Field(..., description="minio url to full image")
    preview_url: str = Field(..., description="minio url for preview image")


class MinioImageURL(BaseModel):
    """Response model for a single project image URL."""

    project_id: int = Field(..., description="project identifier")
    url: str = Field(..., description="minio url for preview image")


class MinioFile(BaseModel):
    """Response model for a file stored in MinIO with its download URL."""

    url: str = Field(..., description="minio presigned url to get file")
    filename: str = Field(..., description="display file name")
