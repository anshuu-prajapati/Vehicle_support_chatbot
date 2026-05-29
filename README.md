# AI Support System 🤖🔧

An AI-powered WhatsApp Support Assistant for industrial machines using FastAPI, PostgreSQL, Qdrant Vector Database, Sentence Transformers, RAG (Retrieval-Augmented Generation), and Groq LLM.

---

# Overview

This project allows users to send machine-related issues through WhatsApp and receive intelligent troubleshooting guidance.

The system combines:

* Semantic Search (Qdrant)
* Knowledge Base (PostgreSQL)
* RAG Pipeline
* Groq LLM (Llama 3.3 70B)
* WhatsApp Cloud API
* Conversation History

Example:

User:

Machine becomes very hot

Bot:

It appears your machine is overheating.

Please try:

1. Clean cooling vents
2. Check coolant circulation
3. Inspect cooling fan

If the issue persists, reply BOOK SERVICE.

---

# Architecture

WhatsApp User
↓
Meta WhatsApp Cloud API
↓
Webhook (FastAPI)
↓
RAG Service
↓
Qdrant Vector Search
↓
PostgreSQL Knowledge Base
↓
Groq LLM
↓
WhatsApp Reply

---

# Tech Stack

Backend

* Python 3.11+
* FastAPI
* Uvicorn

Database

* PostgreSQL

Vector Database

* Qdrant

Embeddings

* Sentence Transformers
* all-MiniLM-L6-v2

LLM

* Groq API
* llama-3.3-70b-versatile

Messaging

* WhatsApp Cloud API

ORM

* SQLAlchemy

Environment

* Python Dotenv

---

# Project Structure

ai-support-system/

app/

├── api/

│   ├── problems.py

│   ├── solutions.py

│   ├── search.py

│   ├── rag.py

│   └── webhook.py

│

├── ai/

│   ├── embeddings.py

│   ├── search.py

│   ├── ingest.py

│   ├── ingest_problems.py

│   └── groq_llm.py

│

├── services/

│   ├── rag_service.py

│   ├── ai_response_service.py

│   ├── whatsapp_service.py

│   ├── chat_service.py

│   └── memory_service.py

│

├── db/

│   ├── database.py

│   └── models/

│       ├── problem.py

│       ├── solution.py

│       ├── chat_message.py

│       └── **init**.py

│

├── core/

│   └── config.py

│

├── main.py

│

data/

.env

requirements.txt

README.md

---

# Database Models

Problem

Stores machine problems.

Fields:

* id
* title
* description
* severity
* machine_model

Example:

Machine Overheating

---

Solution

Stores troubleshooting steps.

Fields:

* id
* problem_id
* step_number
* description

Example:

1. Clean cooling vents
2. Check coolant circulation
3. Inspect cooling fan

---

ChatMessage

Stores user conversations.

Fields:

* id
* phone_number
* user_message
* bot_response
* created_at

Used for:

* Chat history
* Memory
* Analytics

---

# RAG Workflow

Step 1

User sends:

Machine becomes very hot

Step 2

Sentence Transformer generates embeddings.

Model:

all-MiniLM-L6-v2

Step 3

Qdrant performs semantic search.

Result:

Machine Overheating

Step 4

PostgreSQL fetches solutions.

Step 5

Groq LLM generates a natural response.

Step 6

WhatsApp sends response to user.

---

# Environment Variables

Create a .env file.

DATABASE_URL=postgresql://postgres:password@localhost:5432/ai_support

META_VERIFY_TOKEN=myverifytoken

META_ACCESS_TOKEN=your_meta_access_token

META_PHONE_NUMBER_ID=your_phone_number_id

GROQ_API_KEY=your_groq_api_key

---

# Installation

Clone project

git clone <repository>

cd ai-support-system

Create virtual environment

python -m venv venv

Activate

Windows:

venv\Scripts\activate

Install dependencies

pip install -r requirements.txt

---

# PostgreSQL Setup

Create database

CREATE DATABASE ai_support;

Update DATABASE_URL inside .env

Start FastAPI

uvicorn app.main:app --reload

---

# Qdrant Setup

Run Qdrant

docker run -p 6333:6333 qdrant/qdrant

Dashboard

http://localhost:6333/dashboard

Create collection

python -m app.ai.ingest

Load problems into vector database

python -m app.ai.ingest_problems

---

# API Documentation

Swagger

http://127.0.0.1:8000/docs

Available APIs

Problems

GET /problems

POST /problems

Solutions

GET /solutions

POST /solutions

Semantic Search

GET /search

RAG

GET /ask

Webhook

GET /webhook

POST /webhook

---

# WhatsApp Integration

Uses Meta WhatsApp Cloud API.

Flow:

WhatsApp
↓
Webhook
↓
RAG
↓
LLM
↓
Reply

For local testing:

ngrok http 8000

Configure callback URL in Meta Developer Dashboard.

---

# Example Query

User:

Machine becomes very hot

RAG Output:

Machine Overheating

LLM Output:

It appears your machine is overheating.

Please try:

1. Clean cooling vents
2. Check coolant circulation
3. Inspect cooling fan

If the issue persists, reply BOOK SERVICE.

---

# Future Enhancements

* Conversation Memory
* Ticket Management
* Technician Booking
* Image Analysis
* Multi-language Support
* Admin Dashboard
* Analytics Dashboard
* PDF Service Reports
* Predictive Maintenance
* Voice Support

---

# Author

Built using:

* FastAPI
* PostgreSQL
* Qdrant
* Sentence Transformers
* Groq LLM
* WhatsApp Cloud API

AI Support System © 2026
