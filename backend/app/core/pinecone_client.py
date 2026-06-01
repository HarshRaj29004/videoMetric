import os
from dotenv import load_dotenv
from pinecone import Pinecone


load_dotenv()

# Initialize Pinecone client and index (safe if env vars missing)
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
PC = Pinecone(api_key=PINECONE_API_KEY) if (Pinecone and PINECONE_API_KEY) else None
INDEX = PC.Index(host=PINECONE_INDEX) if PC and PINECONE_INDEX else None
NAMESPACE = os.getenv("NAMESPACE")
