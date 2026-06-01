from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl

class TranscriptRequest(BaseModel):
	url: HttpUrl
	language: str | None = Field(default=None)


class TranscriptSegment(BaseModel):
	text: str
	start: float
	duration: float


class TranscriptResponse(BaseModel):
	source: Literal["youtube", "instagram"]
	method: str
	url: HttpUrl
	title: str | None = None
	video_id: str | None = None
	language: str | None = None
	transcript: str
	segments: list[TranscriptSegment] = Field(default_factory=list)
	metadata: dict[str, Any] = Field(default_factory=dict)