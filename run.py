"""
MedLens - Server Runner Script
Starts the FastAPI application with Uvicorn.
"""

import uvicorn
import os
import sys

# Ensure medlens root directory is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if __name__ == "__main__":
    print("=================================================================")
    print("  MedLens — AI-Powered Clinical Information Intelligence Platform")
    print("  Starting on: http://127.0.0.1:8000")
    print("  Docs available at: http://127.0.0.1:8000/docs")
    print("=================================================================")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
