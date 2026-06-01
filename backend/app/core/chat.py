import os
from pinecone import Pinecone
from dotenv import load_dotenv
from ..rag.delete import reset_vector_db
from ..rag.ingestion import chunk_and_store
from ..rag.retreival import search_chunks

load_dotenv()

ids = []
metadatas = []

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
PC = Pinecone(api_key=PINECONE_API_KEY) if PINECONE_API_KEY else None
INDEX = PC.Index(host=PINECONE_INDEX) if PC else None

def data_ingestion(transcript):
    return chunk_and_store(INDEX, ids,metadatas,transcript)

def data_retreival():
    pass

def data_delete():
    pass