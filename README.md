# PocketSmart AI - Smart Budget & Recommendation Assistant
FastAPI + SQLite + Gemini + HTML/CSS/JS

## Run
    python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env      # add your GEMINI_API_KEY
    uvicorn app.main:app --reload
Open http://127.0.0.1:8000  (API docs: /docs)
