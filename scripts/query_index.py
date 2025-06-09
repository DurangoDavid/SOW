#!/usr/bin/env python3
import os
import pickle
import numpy as np
import faiss
from dotenv import load_dotenv
from openai import OpenAI

# load your env and API client
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# paths
BASE_DIR  = os.path.dirname(os.path.dirname(__file__))
IDX_PATH  = os.path.join(BASE_DIR, "output", "revops_index.faiss")
CHUNK_PATH= os.path.join(BASE_DIR, "output", "revops_chunks.pkl")

# load index and texts
index   = faiss.read_index(IDX_PATH)
with open(CHUNK_PATH, "rb") as f:
    texts = pickle.load(f)

def retrieve(question, k=5):
    # embed the question
    resp = client.embeddings.create(input=question, model="text-embedding-3-large")
    qvec = np.array(resp.data[0].embedding, dtype="float32")[None, :]
    # search
    D, I = index.search(qvec, k)
    return [texts[i] for i in I[0]]

def answer(question):
    # get context
    ctx_chunks = retrieve(question)
    # build prompt
    prompt = (
        "You are a RevOps expert. Use the context below to answer.\n\n"
        "Context:\n" + "\n---\n".join(ctx_chunks) + "\n\n"
        f"Question: {question}\nAnswer:"
    )
    # call GPT
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0
    )
    return resp.choices[0].message.content

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python query_index.py \"Your question here\"")
        sys.exit(1)
    q = sys.argv[1]
    print(answer(q))
