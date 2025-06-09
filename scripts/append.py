#!/usr/bin/env python3
"""
 append.py
 Scans input/ for new PDF, DOC, DOCX, CSV files and appends their embeddings to the existing FAISS index and chunk store.
 Usage: place this script in `scripts/` under your project root and run:
     python append.py
"""
import os
import json
import pickle
import numpy as np
import faiss
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Document loaders
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain.document_loaders import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 1) Locate project root and load .env
BASE_DIR = Path(__file__).parents[1].resolve()
load_dotenv(dotenv_path=BASE_DIR / ".env")

# 2) Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Missing OPENAI_API_KEY in .env")
client = OpenAI(api_key=api_key)

# 3) Define paths
INPUT_DIR    = BASE_DIR / "input"
OUTPUT_DIR   = BASE_DIR / "output"
INDEX_PATH   = OUTPUT_DIR / "revops_index.faiss"
CHUNKS_PATH  = OUTPUT_DIR / "revops_chunks.pkl"
MANIFEST_PATH= OUTPUT_DIR / "processed_files.json"

# 4) Ensure output and manifest exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if not MANIFEST_PATH.exists():
    with open(MANIFEST_PATH, "w") as mf:
        json.dump([], mf)

# 5) Load processed manifest
with open(MANIFEST_PATH, "r") as mf:
    processed = set(json.load(mf))

# 6) Identify new files to process
allowed_ext = {".pdf", ".docx", ".doc", ".csv"}
candidates   = [p for p in INPUT_DIR.iterdir() if p.suffix.lower() in allowed_ext]
new_files   = [p for p in candidates if p.name not in processed]
if not new_files:
    print("No new files to process.")
    exit(0)

# 7) Load existing index and chunks
if not INDEX_PATH.exists() or not CHUNKS_PATH.exists():
    raise RuntimeError("Index or chunk store not found. Run build_index.py first.")
index = faiss.read_index(str(INDEX_PATH))
with open(CHUNKS_PATH, "rb") as cf:
    texts = pickle.load(cf)

# 8) Configure text splitter
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)

# 9) Process each new file
total_new_chunks = 0
for file_path in new_files:
    print(f"Processing {file_path.name}...")
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".pdf":
            loader = PyPDFLoader(str(file_path))
        elif suffix in {".docx", ".doc"}:
            loader = Docx2txtLoader(str(file_path))
        elif suffix == ".csv":
            loader = CSVLoader(str(file_path), encoding="utf-8")
        else:
            print(f"Skipping unsupported type: {file_path.name}")
            continue

        docs = loader.load()
    except Exception as e:
        print(f"Failed to load {file_path.name}: {e}")
        continue

    # Split and embed
    chunks = splitter.split_documents(docs)
    total_new_chunks += len(chunks)
    embeddings = []
    for chunk in chunks:
        resp = client.embeddings.create(input=chunk.page_content, model="text-embedding-3-large")
        embeddings.append(resp.data[0].embedding)
        texts.append(chunk.page_content)

    # Append to FAISS
    vecs = np.array(embeddings, dtype="float32")
    index.add(vecs)

    # Mark file as processed
    processed.add(file_path.name)

# 10) Persist updated index and texts
faiss.write_index(index, str(INDEX_PATH))
with open(CHUNKS_PATH, "wb") as cf:
    pickle.dump(texts, cf)

# 11) Update manifest
with open(MANIFEST_PATH, "w") as mf:
    json.dump(sorted(processed), mf, indent=2)

print(f"Appended {len(new_files)} file(s) with {total_new_chunks} new chunks.")

