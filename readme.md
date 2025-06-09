
# AI-Powered Statement of Work (SOW) Generator

A dynamic, AI-powered SOW generator that creates professional Statements of Work leveraging OpenAI's embeddings and completions, FAISS for efficient vector retrieval, DuckDuckGo integration for real-time tech context, and Flask for the web interface.

---

## 🚀 Overview

This tool streamlines the creation of tailored Statements of Work (SOWs) by intelligently combining user-provided details, an internal knowledge base, and real-time web data. Ideal for consultants, agencies, and teams needing consistent, high-quality SOW documents.

---

## 🛠️ Core Features

- Customizable Input: Collects structured inputs (Problem Statement, Stakeholders, GTM Stack, Timeline).
- AI-Enhanced Contextualization: Integrates your document library with real-time search results to generate contextually accurate SOWs.
- Real-Time Web Search: Automatically retrieves and integrates relevant context via DuckDuckGo if internal documentation lacks coverage.
- Exportable PDFs: One-click export of generated SOWs to PDF.
- IP-Based Rate Limiting: Built-in daily limits per IP address, with configurable exceptions.

---

## 📁 Project Structure

```
├── input/                  # Documents to be indexed (PDF, DOCX, CSV)
├── output/                 # Generated FAISS indices & embeddings
├── scripts/                # Index management utilities
│   ├── append.py           # Append new docs to existing embeddings
│   └── build_index.py      # Build initial embeddings & indices
├── templates/
│   └── index.html          # Web UI
├── .env                    # Environment variables
├── requirements.txt        # Python dependencies
└── sow.py                  # Main Flask application
```

---

## 🔧 Installation & Setup

### Step 1: Clone Repository

```
git clone git@github.com:DurangoDavid/SOW.git && cd SOW
```

### Step 2: Set Up Python Environment

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Create `.env` file at the project root:

```
OPENAI_API_KEY=your_openai_api_key
HOME_IP=your_static_home_ip
```

---

## 📚 Managing Embeddings

### Initial Setup:

```
python scripts/build_index.py
```

### Adding New Documents:

```
python scripts/append.py
```

---

## 🚀 Launching the Web App

Start Flask server:

```
python sow.py
```

Access at:

```
http://localhost:8000
```

---

## 🛡️ Rate Limiting

- Default limit:
  - 3 SOW generations/day per IP
  - 1 PDF export/day per IP

---

## 🔑 Security

Store API keys securely in environment variables.

---

## ⚠️ License

MIT License. Use at your own risk.

```
MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
```

---

## 📧 Support

[dm@gtmharmony.com](mailto:dm@gtmharmony.com)
