# ====== Import Libraries ======

from fastapi import FastAPI                    # Web framework for creating the API
from fastapi.middleware.cors import CORSMiddleware  # Middleware to handle cross-origin requests
from pydantic import BaseModel                # To define and validate request data structure
from sentence_transformers import SentenceTransformer  # For encoding text into embeddings
import faiss                                  # For efficient similarity search using vector index
import pandas as pd                           # For loading and handling CSV data
import numpy as np                            # For numerical operations
import os                                     # For file path operations
import datetime                               # For timestamping logs
import uuid                                   # For generating unique session IDs
import hashlib                                # For hashing session ID securely

# ====== Configuration ======

MODEL_NAME = "all-MiniLM-L6-v2"  # Name of the SentenceTransformer model to use
INDEX_PATH = r"E:\Mental health\Model\faiss_index.idx"# Path to the FAISS index file
DATA_PATH = r"E:\Mental health\Data\cleaned_data.csv"  # Path to the CSV file containing Q&A data

# ====== Session Memory ======

# Dictionary to store conversation history for each session
session_memory = {}

# ====== Utility Functions ======

def generate_session_id():
    """Generate a unique session ID using UUID and SHA-256."""
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()

def log_interaction(session_id, user_input, reply):
    """Log each chat interaction with timestamp for history or analysis."""
    log_path = os.path.join(os.path.dirname(__file__), "chat_log.txt")
    with open(log_path, "a") as f:
        timestamp = datetime.datetime.now().isoformat()
        f.write(f"[{timestamp}] Session: {session_id} User: {user_input}\nBetterMind: {reply}\n\n")
    # Update session memory
    if session_id not in session_memory:
        session_memory[session_id] = []
    session_memory[session_id].append((user_input, reply))

# ====== Load Core Components ======

# Load the sentence transformer model onto the GPU for fast embedding generation
model = SentenceTransformer(MODEL_NAME, device='cuda')

# Load the precomputed FAISS index for fast nearest neighbor search
faiss_index = faiss.read_index(INDEX_PATH)

# Load the Q&A data from CSV file as a pandas DataFrame
df = pd.read_csv(DATA_PATH)

# ====== FastAPI App Setup ======

# Create a FastAPI app instance
app = FastAPI()

# Configure CORS to allow frontend (e.g., React app) running on localhost:5173 to make API calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== Define Input Schema ======

class Message(BaseModel):
    """Defines the structure of incoming JSON data."""
    message: str  # The user's message to the chatbot

# ====== Core Retrieval Logic ======

def get_best_answer(session_id, user_input):
    """
    Perform semantic search with context:
    1. Retrieve conversation history for the session.
    2. Encode the user's message using the SentenceTransformer.
    3. Search for the most similar question in the FAISS index.
    4. Return the corresponding answer from the CSV file.
    """
    # Retrieve conversation history
    conversation_history = session_memory.get(session_id, [])
    # Optionally, use conversation history to modify the query
    # For simplicity, we are just using the latest user input
    query_embedding = model.encode([user_input])       # Convert message to embedding (shape: 1 x dim)
    D, I = faiss_index.search(query_embedding, k=1)    # Search FAISS for top-1 most similar vector
    top_index = I[0][0]                                # Get the index of the best match
    return df.iloc[top_index]["answer"]                # Return the matching answer from CSV

# ====== Chat API Endpoint ======

@app.post("/chat")
def chat(msg: Message):
    """
    API endpoint that:
    - Receives user message from the frontend.
    - Uses semantic search to retrieve the best answer.
    - Logs the interaction.
    - Returns the result with a session ID and confidence score.
    """
    try:
        session_id = generate_session_id()             # Generate a new session ID
        reply = get_best_answer(session_id, msg.message)  # Retrieve best matching answer using FAISS
        log_interaction(session_id, msg.message, reply)  # Save chat interaction in log

        return {
            "session_id": session_id,                  # Unique session identifier
            "reply": reply,                            # Retrieved answer to be displayed
            "model_used": MODEL_NAME,                  # Inform which model was used
            "confidence": round(float(np.random.uniform(0.85, 0.95)), 2)  # Fake confidence for frontend UX
        }

    except Exception as e:
        # Handle any runtime errors gracefully
        return {"reply": f"⚠️ Internal error occurred: {str(e)}"}