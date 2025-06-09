#!/usr/bin/env python3
import os
import pickle
import numpy as np
import faiss
from pathlib import Path
from flask import Flask, render_template, request, Response
from openai import OpenAI
from xhtml2pdf import pisa
from io import BytesIO
from datetime import datetime
import duckduckgo_search

# rate-limiting imports
from flask_limiter import Limiter, RateLimitExceeded

# ─────────────────────────────────────────────────────────────
# Project root & OpenAI client
BASE_DIR = Path(__file__).parent.resolve()
api_key  = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Missing OPENAI_API_KEY in environment")
client = OpenAI(api_key=api_key)

# FAISS index + chunks
OUTPUT_DIR  = BASE_DIR / "output"
INDEX_PATH  = OUTPUT_DIR / "revops_index.faiss"
CHUNKS_PATH = OUTPUT_DIR / "revops_chunks.pkl"
if not INDEX_PATH.exists() or not CHUNKS_PATH.exists():
    raise RuntimeError("Index or chunks not found")

index = faiss.read_index(str(INDEX_PATH))
with open(CHUNKS_PATH, "rb") as f:
    texts = pickle.load(f)

# ─────────────────────────────────────────────────────────────
# DuckDuckGo fallback
def search_web(query: str, count: int = 3) -> str:
    try:
        results = duckduckgo_search.ddg(query, max_results=count)
    except Exception:
        return ""
    if not results:
        return ""
    return "\n".join(r.get("snippet","") for r in results if r.get("snippet"))

def retrieve_chunks(query: str, k: int = 5):
    resp = client.embeddings.create(input=query, model="text-embedding-3-large")
    vec  = np.array(resp.data[0].embedding, dtype="float32")[None, :]
    _, ids = index.search(vec, k)
    return [texts[i] for i in ids[0]]

# ─────────────────────────────────────────────────────────────
# Flask + Limiter setup
app = Flask(__name__)
HOME_IP = os.getenv("HOME_IP", "")

def real_ip():
    return request.headers.get("X-Real-IP", request.remote_addr)

limiter = Limiter(
    key_func=real_ip,
    default_limits=[],
    storage_uri="memory://",
    headers_enabled=True
)
limiter.init_app(app)

@limiter.request_filter
def ip_whitelist():
    return real_ip() == HOME_IP

@app.errorhandler(RateLimitExceeded)
def ratelimit_handler(e):
    html = '''<!DOCTYPE html>
<html>
<head>
  <title>Rate Limit Reached</title>
  <link rel="icon" href="https://gtmharmony.com/favicon.ico" type="image/x-icon"/>
  <style>
    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; color: #333; }
    button { background: #0056b3; color: #fff; border: none; padding: 12px 24px; font-size: 16px; border-radius: 4px; cursor: pointer; }
    button:hover { background: #004494; }
  </style>
</head>
<body>
  <h2>Rate Limit Reached</h2>
  <p>You’ve reached your daily limit.<br/>
     Contact us for more access:</p>
  <a href="mailto:dm@gtmharmony.com">
    <button>Contact Growth Harmony</button>
<p style="margin-top:10px;"><a href="mailto:dm@gtmharmony.com">dm@gtmharmony.com</a></p> 
 </a>
</body>
</html>'''
    return Response(html, status=429, mimetype='text/html')

# ─────────────────────────────────────────────────────────────
# Main SOW endpoint (GET shows form; POST generates)
@app.route("/", methods=["GET","POST"])
@limiter.limit("3 per day", methods=["POST"])
def home():
    problem      = request.form.get("problem", "")
    participants = request.form.get("participants", "")
    gtm_stack    = request.form.get("gtm_stack", "")
    timeline     = request.form.get("timeline", "")
    answer       = None

    if request.method == "POST" and "answer_html" not in request.form:
        chunks = retrieve_chunks(problem)
        if len(chunks) < 3:
            answer = (
                "I’m sorry, I don’t have enough information from our AI Enhanced Library to craft a proper SOW. "
                "Please email dm@gtmharmony.com with additional context."
            )
        else:
            doc_date = datetime.now().strftime("%B %d, %Y")
            tech_contexts = []
            for tech in [t.strip() for t in gtm_stack.split(",") if t.strip()]:
                found = [c for c in chunks if tech.lower() in c.lower()]
                tech_contexts.append("\n".join(found) if found else search_web(tech))

            formatted_chunks = ["[Document Excerpt]\n" + c for c in chunks]
            formatted_chunks += ["[Live Search]\n" + c for c in tech_contexts if c]
            context_str = "\n---\n".join(formatted_chunks)

            system_msg = (
                "Assume the problem statement is referencing something to be solved in the future. "
                "Never, ever use people or company names from embedding.\n"
                "You are an expert SOW writer for a fractional Rev Ops agency leveraging David Maxey's AI enhanced solution library.\n"
                "You have access to our AI Enhanced Library of Revenue Operations solutions, including 50+ articles and proven frameworks.\n"
                f"Your task is to draft a clean, creative, and professional Statement of Work dated {doc_date}.\n"
                "Draw on specific models, case studies, and examples in the library to propose tailored deliverables.\n"
                "Timelines should scale with deliverable count: shorter timelines = fewer deliverables; longer timelines = more.\n"
                "Output only HTML using <h1> for header, <h3> for paragraph titles, <ul>/<ol> for lists, <p> for paragraphs.\n"
                "Include a clear Deliverables section and a professional Exclusions clause covering anything not core to the problem.\n"
                "If essential details (timeline, technology, KPIs) are missing, reply: "
                "'Please provide more information including technology, processes, and KPIs.'"
            )

            user_msg = (
                "Document Date: " + doc_date + "\n"
                "Never use company names like Sinalite or Boas or Marine or anything that resembles a company name or person's name in the output\n"
                "You are a senior consultant at Rev Ops Agency preparing a formal Statement of Work.\n"
                "Incorporate problem statement, stakeholder details, timeline, GTM stack, and library insights.\n\n"
                "Use DuckDuckGo integration to pull more updated information about GTM stack capabilities and integrate into deliverables\n"
                "Context:\n" + context_str + "\n\n"
                "Problem Statement:\n" + problem + "\n\n"
                "Stakeholders / Participants:\n" + participants + "\n\n"
                "GTM Stack:\n" + gtm_stack + "\n\n"
                "Proposed Timeline:\n" + timeline + "\n\n"
                "Generate the full SOW in HTML only, with SMART deliverables and professional exclusions. "
                "The last portion should be 'Future State / Outcomes', outlining the value and outcomes."
            )

            res = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user",   "content": user_msg}
                ],
                temperature=0
            )
            raw = res.choices[0].message.content
            answer = (
                raw.strip()
                   .removeprefix("```html")
                   .removeprefix("```")
                   .removesuffix("```")
                   .strip()
            )

    return render_template(
        "index.html",
        problem=problem,
        participants=participants,
        gtm_stack=gtm_stack,
        timeline=timeline,
        answer=answer
    )

# ─────────────────────────────────────────────────────────────
# PDF export endpoint
@app.route("/export", methods=["POST"])
@limiter.limit("1 per day")
def export_pdf():
    html_body = request.form.get("answer_html", "")
    full_html = (
        "<!DOCTYPE html>\n<html>\n<head>\n"
        "  <meta charset=\"utf-8\"/>\n"
        "  <style>\n"
        "    body { font-family: Georgia, serif; margin:40px; color:#333; }\n"
        "    h1 { font-size:32pt; margin-bottom:10pt; }\n"
        "    h2 { font-size:20pt; margin-top:20pt; }\n"
        "    h3 { font-size:16pt; margin-top:15pt; }\n"
        "    p, ul, ol { font-size:12pt; line-height:1.5; }\n"
        "  </style>\n</head>\n<body>\n"
        + html_body + "\n"
        "  <div style=\"margin-top:50px;\">\n"
        "    <p>Authorized Signature: ____________________</p>\n"
        "    <p>Date: ____________________</p>\n"
        "  </div>\n</body>\n</html>"
    )
    buf = BytesIO()
    pisa_status = pisa.CreatePDF(full_html, dest=buf)
    if pisa_status.err:
        return "Error generating PDF", 500

    pdf = buf.getvalue()
    filename = f"SOW_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
