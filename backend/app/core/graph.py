import os
from typing import Annotated, Literal
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from .chat import data_retreival,metadata_fetch
from ..model.chat_model import ChatState
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")



# ==========================================
# 1. DEFINE THE TOOLS (The Agent's Actions)
# ==========================================
@tool
def get_video_metadata(video_id: str) -> dict:
    """
    Fetch exact numerical metadata for a video (views, likes, comments, engagement rate, creator, followers).
    Use this strictly when asked about engagement rates, follower counts, or exact metrics.
    """
    cleaned_id = str(video_id).strip("'\" ")
    
    try:
        results = metadata_fetch(cleaned_id)
        print(results)
        if not results:
            return {"error": f"No metadata found for Video {cleaned_id}"}
            
        return results
        
    except KeyError:
        return {"error": f"Video ID '{cleaned_id}' does not exist in metadata records."}
    except Exception as exc:
        return {"error": f"Failed to fetch metadata for Video {cleaned_id}: {str(exc)}"}


@tool
def search_transcript(query: str, video_id: str = None,top_k: int = 3) -> str:
    """
        Search transcript chunks.

        Use when:
        - asking about hook
        - opening
        - CTA
        - storytelling
        - objections
        - retention
        - specific topic

        Parameters:
        query: what to search
        video_id: target video
        top_k: number of chunks

        Returns transcript excerpts.
    """
    results = data_retreival(query,top_k,video_id)

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
researcher_llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL,temperature=0.2, api_key=GEMINI_API_KEY).bind_tools(tools)

def researcher_node(state: ChatState):
    """Gathers data and writes a raw, factual summary."""
    v1 = state.get("video1") or {}
    v2 = state.get("video2") or {}

    v1_id = v1.get("video_id") or v1.get("result", {}).get("video_id") or "unknown"
    v2_id = v2.get("video_id") or v2.get("result", {}).get("video_id") or "unknown"
    
    v1_title = v1.get("title") or v1.get("result", {}).get("title") or "Unknown Title"
    v2_title = v2.get("title") or v2.get("result", {}).get("title") or "Unknown Title"
    
    v1_url = v1.get("url") or "unknown"
    v2_url = v2.get("url") or "unknown"
    legend_context = (
        f"You are analyzing two specific videos already loaded in the session state:\n"
        f"- Video 1:\n"
        f"  - ID: '{v1_id}'\n"
        f"  - Title: '{v1_title}'\n"
        f"  - URL: {v1_url}\n"
        f"- Video 2:\n"
        f"  - ID: '{v2_id}'\n"
        f"  - Title: '{v2_title}'\n"
        f"  - URL: {v2_url}\n\n"
        f"Map the user's natural language references (e.g., 'first video', 'Instagram reel') to these details. "
        f"If the user asks for basic properties like the title or URL, answer immediately using this context without calling tools."
    )

    system_prompt = SystemMessage(content=(
        "You are a research agent. Your job is to use tools to fetch exact metrics or look at session context.\n\n"
        "Rules:\n"
        "1. If the answer requires transcript deep-dives, ALWAYS call search_transcript.\n"
        "2. If the answer requires extra performance metrics (views, likes, comments), call get_video_metadata.\n"
        "3. If the information is already provided in your session context list below, use it directly.\n"
        "4. Never invent or estimate metrics.\n\n"
        f"{legend_context}"
    ))
    
    messages = [system_prompt] + state["messages"]
    response = researcher_llm.invoke(messages)
    print("Model Response Hooks:", response.tool_calls)
    return {"messages": [response]}


# ==========================================
# NODE 2: THE COPYWRITER (Focus: Engagement)
# ==========================================
copywriter_llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL,temperature=0.7, api_key=GEMINI_API_KEY)

def copywriter_node(state: ChatState):
    """Transforms raw facts into creator strategy or answers casual questions naturally."""
    raw_data = state["messages"][-1].content if state["messages"] else ""
    
    current_user_query = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            current_user_query = msg.content
            break
            
    if not current_user_query and state["messages"]:
        current_user_query = state["messages"][0].content
    
    system_prompt = SystemMessage(content=(
        "You are an expert social video strategist and helpful chat assistant.\n\n"
        "Your job is to look at the 'Raw Research Data' and address the 'User Request'.\n\n"
        "CRITICAL RESPONSE RULES:\n"
        "1. If the User Request is a basic informational question (e.g., asking if you can see a video, "
        "asking for a title, a URL, saying hello, or basic troubleshooting), DO NOT use the 3-part Strategy Report layout. "
        "Answer the question directly, naturally, and concisely using the provided research data context.\n"
        "2. Only generate a structured creator strategy report if the user is explicitly asking for performance insights, "
        "video breakdowns, hooks, or actionable improvements. For strategy reports, you MUST use this layout:\n"
        "   - 🎯 The Vibe Check: A brutal, one-sentence truth about the performance.\n"
        "   - 📊 The Evidence: Cite transcript excerpts and metrics provided.\n"
        "   - 🚀 The Playbook: 2 short, actionable steps for the next video."
    ))

    rewrite_prompt = HumanMessage(content=(
        f"User Request: '{current_user_query}'\n\n"
        f"Raw Research Data:\n{raw_data}\n\n"
        f"Formulate the final response for the user following the rules above."
    ))
    
    response = copywriter_llm.invoke([system_prompt, rewrite_prompt])
    
    return {"messages": [response]}



# ==========================================
# ROUTING LOGIC
# ==========================================
def should_continue(state):
    last = state["messages"][-1]

    if getattr(last, "tool_calls", None):
        return "tools"

    return "copywriter"


# ==========================================
# BUILD THE GRAPH
# ==========================================
graph = StateGraph(ChatState)

graph.add_node("researcher", researcher_node)
graph.add_node("tools", ToolNode(tools))
graph.add_node("copywriter", copywriter_node)

# graph.add_edge(START,"router")
graph.add_edge(START, "researcher")
graph.add_conditional_edges(
    "researcher",
    should_continue,
    {
        "tools": "tools",
        "copywriter": "copywriter",
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
    
    state = {
        "messages": [HumanMessage(content=query)],
        "video1": user_content[0],
        "video2": user_content[1],
    }
    
    async for event, data in agent_app.astream(state, config, stream_mode="messages"):
        if data.get("langgraph_node") == "copywriter":
            if event.content:
                yield event.content