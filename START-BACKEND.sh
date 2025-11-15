#!/bin/bash
cd /Users/tanmayranaware/Desktop/Projects/RCA/backend
source venv/bin/activate
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

