from typing import Annotated, Any

from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages

class VideoContext(TypedDict):
    url: str
    video_id: str
    result: dict[str, Any]

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    video1: VideoContext
    video2: VideoContext