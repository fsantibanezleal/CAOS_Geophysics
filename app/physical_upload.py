"""Strict physical JSON original upload; no projected-CSV metadata or numerics."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.errors import ApiError
from app.physical_contract import M, decode_source, integer
from app.physical_wire import parse_root
from app.schemas import RawUploadInput, SourceInput

FORMAT = 'gravity_stations_json'
SOURCE_LIMIT = 16 * M


class PhysicalSchemaInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    schema_version: Literal['gravity-stations-1']


class PhysicalRawUploadInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    filename: str = Field(min_length=1, max_length=255)
    mime: Literal['application/json']
    format: Literal['gravity_stations_json']
    source: SourceInput
    physical: PhysicalSchemaInput

    @field_validator('filename')
    @classmethod
    def filename_is_original_basename(cls, value):
        return RawUploadInput.safe_filename(value)


def parse_physical_upload_header(raw):
    """Whole-source duplicate/token admission before framework coercion."""
    value = decode_source([raw.encode('utf-8', 'strict')], max_bytes=16384, depth=8, nodes=2048)
    source = value.get('source') if type(value) is dict else None
    if type(source) is dict and source.get('expected_bytes') is not None:
        integer(source['expected_bytes'], 1, SOURCE_LIMIT)
    return PhysicalRawUploadInput.model_validate(value)


def validate_physical_upload(path, meta):
    if not isinstance(meta, PhysicalRawUploadInput) or not meta.filename.lower().endswith('.json'):
        raise ApiError(415, 'mime_format_mismatch', 'Filename, MIME and declared format must agree')
    path = Path(path)
    # Count real EOF under the parser cap; no stat-only bound or object coercion.
    def chunks():
        with path.open('rb') as stream:
            while chunk := stream.read(65536):
                yield chunk
    try:
        parse_root(chunks())
    except (ValueError, UnicodeError):
        raise ApiError(422, 'physical_contract_invalid', 'Physical original JSON is not structurally eligible') from None
