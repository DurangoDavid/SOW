#!/usr/bin/env python3
# build_index.py

import os
import pickle
import numpy as np
import faiss
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

# Document loaders
from langchain_community.document_loaders import (
    PyPDFLoader,
    BSHTMLLoader,
    Docx2txtLoader,
    TextLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Paths and chunk settings
BASE_DIR    = Path(__file__).parents[1]
INPUT_DIR   = BASE_DIR / "input"
OUTPUT_DIR  = BASE_DIR / "output"
CHUNK_SIZE  = 500
CHUNK_OVERLAP = 100

# 1) Load all docs
docs = []
for file_path in INPUT_DIR.iterdir():
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".pdf":
            loader = PyPDFLoader(str(file_path))
        elif suffix in {".html", ".htm"}:
            # use builtin HTML parser to avoid requiring lxml
            loader = BSHTMLLoader(
                str(file_path),
                bs_kwargs={"features": "html.parser"}
            )
        elif suffix == ".docx":
            loader = Docx2txtLoader(str(file_path))
        elif suffix in {".txt", ".md"}:
            loader = TextLoader(str(file_path), encoding="utf-8")
        else:
            print(f"Skipping unsupported type: {file_path.name}")
            continue

        pages = loader.load()
        docs.extend(pages)
        print(f"Loaded {file_path.name}: {len(pages)} pages")
    except Exception as e:
        print(f"Failed to load {file_path.name}: {e}")

# 2) Split into chunks
splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP
)
chunks = splitter.split_documents(docs)
print(f"Split into {len(chunks)} chunks")

# 3) Embed each chunk
embeddings = []
texts = []
for chunk in chunks:
    txt = chunk.page_content
    try:
        resp = client.embeddings.create(
            input=txt,
            model="text-embedding-3-large"
        )
        vec = resp.data[0].embedding
        embeddings.append(vec)
        texts.append(txt)
    except Exception as e:
        print(f"Embedding failed: {e}")

if not embeddings:
    print("No embeddings created. Exiting.")
    exit(1)

# 4) Build FAISS index
dim   = len(embeddings[0])
index = faiss.IndexFlatL2(dim)
index.add(np.array(embeddings, dtype="float32"))

# 5) Save outputs
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
faiss.write_index(index, str(OUTPUT_DIR / "revops_index.faiss"))
with open(OUTPUT_DIR / "revops_chunks.pkl", "wb") as f:
    pickle.dump(texts, f)

print("✅ Index built: output/revops_index.faiss")
print("✅ Chunks saved: output/revops_chunks.pkl")
