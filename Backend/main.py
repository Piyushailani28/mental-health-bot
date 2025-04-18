from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import faiss
import pandas as pd
import numpy as np
import os
import datetime
import uuid
import hashlib
from typing import Optional
import traceback
import google.generativeai as genai

MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_PATH = r"E:\Github\mental-health-bot\Model\faiss_index.idx"
DATA_PATH = r"E:\Github\mental-health-bot\Data\cleaned_data.csv"
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "chat_log.txt")
MAX_HISTORY_TURNS = 3
session_memory = {}

google_api_key = "Your - API - Key"
genai.configure(api_key=google_api_key)
gemini_model = genai.GenerativeModel("gemini-1.5-flash-latest")

def generate_session_id():
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()

def log_interaction(session_id, user_input, reply):
    try:
        os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
        with open(LOG_FILE_PATH, "a", encoding='utf-8') as f:
            timestamp = datetime.datetime.now().isoformat()
            f.write(f"[{timestamp}] Session: {session_id}\nUser: {user_input}\nBetterMind: {reply}\n\n")
    except Exception as e:
        print(f"Error logging interaction for session {session_id}: {e}")
    if session_id not in session_memory:
        session_memory[session_id] = []
    session_memory[session_id].append((user_input, reply))

print("Loading components...")
try:
    try:
        model = SentenceTransformer(MODEL_NAME, device='cuda')
        print("SentenceTransformer model loaded on CUDA GPU.")
    except Exception as e:
        print(f"CUDA not available or error loading model on GPU: {e}. Loading on CPU.")
        model = SentenceTransformer(MODEL_NAME, device='cpu')
        print("SentenceTransformer model loaded on CPU.")
    if os.path.exists(INDEX_PATH):
        faiss_index = faiss.read_index(INDEX_PATH)
        print(f"FAISS index loaded from {INDEX_PATH}. Index size: {faiss_index.ntotal}")
    else:
        raise FileNotFoundError(f"FAISS index file not found at: {INDEX_PATH}")
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        if "answer" not in df.columns:
            raise ValueError(f"CSV file at {DATA_PATH} must contain an 'answer' column.")
        print(f"Q&A data loaded from {DATA_PATH}. Shape: {df.shape}")
        if faiss_index.ntotal != len(df):
            print(f"Warning: FAISS index size ({faiss_index.ntotal}) does not match CSV rows ({len(df)}). Ensure they correspond.")
    else:
        raise FileNotFoundError(f"Data CSV file not found at: {DATA_PATH}")
except FileNotFoundError as fnf_error:
    print(f"Error: {fnf_error}")
    print("Please ensure the INDEX_PATH and DATA_PATH variables are set correctly.")
    exit()
except Exception as e:
    print(f"An unexpected error occurred during component loading: {e}")
    traceback.print_exc()
    exit()

print("Components loaded successfully.")

app = FastAPI(
    title="BetterMind Chat API",
    description="API for the BetterMind chatbot using Sentence Transformers and FAISS",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    message: str
    session_id: Optional[str] = None

def polish_with_gemini(question: str, retrieved_answer: str, history: Optional[str] = "") -> str:
    prompt = f"""You're a helpful empathetic and Friendly but Professional mental health assistant. 
    Here is the chat history:{history}  
    User Question: {question}
    Initial answers Retrieved: {retrieved_answer}

    Please improve or rephrase the answer in a helpful and emotionally intelligent way. Keep it under 100 words.
    you are the world's best therapist.And give the measure of each prompt in a better way
    make sure the user gets the connection like a family member with you but in a Professional and formal language.Use appropriate Words 

    """
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print("Error using Gemini", e)
        return retrieved_answer

def get_best_answer(session_id: str, user_input: str):
    conversation_history = session_memory.get(session_id, [])
    context = ""
    num_turns_to_use = min(len(conversation_history), MAX_HISTORY_TURNS)
    if num_turns_to_use > 0:
        relevant_history = conversation_history[-num_turns_to_use:]
        for past_user_input, past_reply in relevant_history:
            context += f"User: {past_user_input}\nBetterMind: {past_reply}\n"
    contextual_query = context + f"User: {user_input}"
    try:
        query_embedding = model.encode([contextual_query])
        D, I = faiss_index.search(query_embedding.astype(np.float32), k=1)
        top_index = I[0][0]
        distance = D[0][0]
        max_possible_distance = 100
        confidence_score = max(0.0, 1.0 - (distance / max_possible_distance))
        confidence = round(confidence_score, 2)
        if 0 <= top_index < len(df):
            best_answer = df.iloc[top_index]["answer"]
            history_text = ""
            for u, b in conversation_history[-MAX_HISTORY_TURNS:]:
                history_text += f"User: {u}\nBetterMind: {b}\n"
            polished_response = polish_with_gemini(user_input, best_answer, history_text)
            return polished_response, confidence
        else:
            print(f"Error: FAISS returned an invalid index: {top_index}")
            return "I encountered an issue finding a relevant answer. Please try again.", 0.0
    except Exception as e:
        print(f"Error during embedding or FAISS search for session {session_id}: {e}")
        traceback.print_exc()
        return "I had trouble processing that request. Could you try rephrasing?", 0.0

@app.get("/")
def read_root():
    return {"message": "BetterMind Chat API is running."}

@app.post("/chat")
def chat(msg: Message):
    active_session_id = None
    try:
        if msg.session_id and msg.session_id in session_memory:
            active_session_id = msg.session_id
        else:
            active_session_id = generate_session_id()
            session_memory[active_session_id] = []
        reply, confidence = get_best_answer(active_session_id, msg.message)
        log_interaction(active_session_id, msg.message, reply)
        return {
            "session_id": active_session_id,
            "reply": reply,
            "model_used": MODEL_NAME,
            "confidence": confidence
        }
    except Exception as e:
        print(f"Critical error in /chat endpoint processing session {active_session_id}: {e}")
        traceback.print_exc()
        return {
            "session_id": active_session_id,
            "reply": "⚠️ An unexpected error occurred on our end. Please try again later.",
            "model_used": MODEL_NAME,
            "confidence": 0.0
        }

@app.post("/clear_memory")
def clear_all_session_memory():
    global session_memory
    count = len(session_memory)
    session_memory = {}
    print(f"Cleared {count} sessions from memory via API call.")
    return {"message": f"Successfully cleared {count} sessions from memory."}

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server with Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)