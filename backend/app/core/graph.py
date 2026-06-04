import json
import os
from typing import Literal, Optional
from .chat import ensure_metadata_loaded
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from .chat import data_retreival, metadata_fetch
from ..model.chat_model import ChatState
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")


# ==========================================
# 0. STRICT PARAMETER SCHEMAS (Fixes Groq Validation)
# ==========================================
class SearchTranscriptArgs(BaseModel):
    query: str = Field(
        description="The keyword or conceptual topic to search for in transcript chunks (e.g., 'hook', 'CTA')."
    )
    video_id: Optional[str] = Field(
        default=None, 
        description="The target video ID string to isolate the search. Optional."
    )
    top_k: int = Field(
        default=3, 
        description="Number of chunks to pull back. CRITICAL: This must be a strict integer number (e.g., 3), never wrap it in quotes or pass it as a string."
    )


# ==========================================
# 1. DEFINE THE TOOLS (The Agent's Actions)
# ==========================================
@tool
def get_video_metadata(video_id: str) -> dict:
    """
    Fetch the metadata and performance metrics for a video (views, likes, comments, engagement rate, uploader, channel, title, duration).
    Use this when asked about video metadata, metrics, performance, or to check if metadata is available.
    """
    print(f"\n[TOOL] get_video_metadata")
    cleaned_id = str(video_id).strip("'\" ")
    
    try:
        results = metadata_fetch(cleaned_id)
        if not results:
            return {"error": f"No metadata found for Video {cleaned_id}"}
            
        return results
        
    except KeyError:
        return {"error": f"Video ID '{cleaned_id}' does not exist in metadata records."}
    except Exception as exc:
        return {"error": f"Failed to fetch metadata for Video {cleaned_id}: {str(exc)}"}


@tool(args_schema=SearchTranscriptArgs)
def search_transcript(query: str, video_id: Optional[str] = None, top_k: int = 3) -> str:
    """
    Search transcript chunks for video strategies, hooks, retention, hooks, and openings.
    """
    print(f"\n[TOOL] search_transcript")
    results = data_retreival(query, top_k, video_id)

    if not results:
        return f"No transcript segments found matching '{query}'."

    formatted_chunks = []
    for item in results:
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        tag = item.get("video_id") or video_id or "unknown"
        formatted_chunks.append(f"[Video {tag}] {content}")

    if not formatted_chunks:
        return f"No transcript segments found matching '{query}'."

    return "\n\n".join(formatted_chunks)


tools = [get_video_metadata, search_transcript]


# ==========================================
# NODE 1: THE RESEARCHER (Focus: Accuracy)
# ==========================================
researcher_llm = ChatGroq(
    model=GROQ_MODEL,
    temperature=0.3,
    groq_api_key=GROQ_API_KEY,
).bind_tools(tools)

def researcher_node(state: ChatState):
    """Evaluates context, calls tools, and answers simple factual queries immediately."""
    print("\n[AGENT] researcher")
    v1 = state.get("video1") or {}
    v2 = state.get("video2") or {}
    v1_id = v1.get("video_id") or v1.get("result", {}).get("video_id") or "unknown"
    v2_id = v2.get("video_id") or v2.get("result", {}).get("video_id") or "unknown"
    v1_title = v1.get("title") or v1.get("result", {}).get("title") or "Unknown Title"
    v2_title = v2.get("title") or v2.get("result", {}).get("title") or "Unknown Title"
    
    legend_context = (
        f"Session Video Data:\n"
        f"- Video 1 ID: '{v1_id}' | Title: '{v1_title}'\n"
        f"- Video 2 ID: '{v2_id}' | Title: '{v2_title}'\n"
    )
    system_prompt = SystemMessage(content=(
        f"{legend_context}\n"
        "You are an expert factual coordinator. Analyze the user request and follow these rules strictly:\n\n"
        "1. For casual inputs (e.g., 'Hi', 'hello'), reply naturally and concisely in plain text immediately.\n"
        "2. If the user asks for a direct metric, count, property, or specific text snippet, "
        "call the necessary tool to fetch the data. Pass integers as raw numerical numbers, never as strings.\n"
        "3. If and ONLY if the user explicitly asks for a comparison, breakdown, deep strategic analysis, or an explanation of performance, "
        "gather the data via tools first. Once you have the data in context, output exactly this single keyword block: [ROUTING_TO_STRATEGIST] and stop."
    ))
    
    messages = [system_prompt] + state["messages"]
    response = researcher_llm.invoke(messages)
    return {"messages": [response]}


# ==========================================
# NODE 2: THE COPYWRITER (Focus: Engagement)
# ==========================================
copywriter_llm = ChatGroq(
    model=GROQ_MODEL,
    temperature=0.7,
    groq_api_key=GROQ_API_KEY,
)

def copywriter_node(state: ChatState):
    """Processes raw tool logs and explicitly answers the user's targeted metric question."""
    current_user_query = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            current_user_query = msg.content
            break

    extracted_tool_data = []
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            break 
        if msg.type == "tool":
            extracted_tool_data.append(f"Source Data ({msg.name}): {msg.content}")
            
    raw_research = "\n\n".join(extracted_tool_data)
    
    system_prompt = SystemMessage(content=(
        "You are an elite, human-like video strategist. Your job is to interpret raw database statistics "
        "and address the User Request with extreme precision. Follow these critical style rules:\n\n"
        "1. NEVER output raw unformatted floats. Always round numbers to 1 or 2 decimal places.\n"
        "2. FOCUS ON THE USER'S QUERY.\n"
        "3. IGNORE INTERNAL TAGS: If you see '[ROUTING_TO_STRATEGIST]', delete it entirely.\n"
        "4. Sound like an experienced industry producer—punchy, objective, and deeply tactical."
    ))

    rewrite_prompt = HumanMessage(content=(
        f"User Request: '{current_user_query}'\n\n"
        f"Raw Research Data Available:\n{raw_research}\n\n"
        f"Synthesize this into a high-value strategy report answering their exact query."
    ))
    
    response = copywriter_llm.invoke([system_prompt, rewrite_prompt])
    return {"messages": [response]}


# ==========================================
# ROUTING LOGIC & GRAPH COMPILATION (Unchanged)
# ==========================================
def should_continue(state: ChatState) -> Literal["tools", "copywriter", "end"]:
    last_msg = state["messages"][-1]

    if getattr(last_msg, "tool_calls", None):
        return "tools"
        
    if "[ROUTING_TO_STRATEGIST]" in getattr(last_msg, "content", ""):
        return "copywriter"

    return "end"

graph = StateGraph(ChatState)
graph.add_node("researcher", researcher_node)
graph.add_node("tools", ToolNode(tools))
graph.add_node("copywriter", copywriter_node)

graph.add_edge(START, "researcher")
graph.add_conditional_edges(
    "researcher",
    should_continue,
    {
        "tools": "tools",
        "copywriter": "copywriter",
        "end": END
    }
)
graph.add_edge("tools", "researcher")
graph.add_edge("copywriter", END)

memory = MemorySaver()
agent_app = graph.compile(checkpointer=memory)


# ==========================================
# ASYNCHRONOUS STREAMING INTERFACE
# ==========================================
async def run_chat_stream(query: str, user_content: list, user_id: str, chat_id: str):
    """
    Yields text tokens in real-time as they are generated by the Copywriter node,
    preserving memory and executing background tools automatically.
    """
    thread_id = f"user:{user_id}:chat:{chat_id}"
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 10
    }
    
    for video in user_content:
        vid_id = video.get("video_id") or video.get("result", {}).get("video_id")
        vid_url = video.get("url")
        if vid_id and vid_url:
            ensure_metadata_loaded(vid_id, vid_url)
            
    state = {
        "messages": [HumanMessage(content=query)],
        "video1": user_content[0] if len(user_content) > 0 else {},
        "video2": user_content[1] if len(user_content) > 1 else {},
    }
    
    async for event in agent_app.astream_events(state, config, version="v2"):
        kind = event["event"]
        
        if kind == "on_chain_start":
            node_name = event.get("metadata", {}).get("langgraph_node") or event.get("name")
            if node_name in ["researcher", "tools", "copywriter"]:
                yield f"data: {json.dumps({'type': 'node_start', 'node': node_name})}\n\n"
                
        elif kind == "on_chain_end":
            node_name = event.get("metadata", {}).get("langgraph_node") or event.get("name")
            if node_name in ["researcher", "tools", "copywriter"]:
                yield f"data: {json.dumps({'type': 'node_end', 'node': node_name})}\n\n"
                
        elif kind == "on_tool_start":
            tool_name = event.get("name")
            tool_input = event.get("data", {}).get("input", {})
            yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name, 'input': tool_input})}\n\n"
            
        elif kind == "on_tool_end":
            tool_name = event.get("name")
            tool_output = event.get("data", {}).get("output", "")
            if not isinstance(tool_output, str):
                tool_output = str(tool_output)
            yield f"data: {json.dumps({'type': 'tool_end', 'tool': tool_name, 'output': tool_output[:300]})}\n\n"
            
        elif kind == "on_chat_model_stream":
            node = event.get("metadata", {}).get("langgraph_node")
            if node == "copywriter":
                content = event.get("data", {}).get("chunk", {}).content
                if content:
                    yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"