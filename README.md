# Know AI – AI-Powered Knowledge Assistant

Know AI is an AI-powered knowledge assistant built with Python and Flask. It allows users to upload documents, ask questions, and receive context-aware answers using Retrieval-Augmented Generation (RAG).

## Features

- User registration and login.
- JWT-based authentication.
- AI-powered conversations.
- PDF, DOCX, and TXT document uploads.
- Document text extraction and chunking.
- Semantic search using vector embeddings.
- Context-aware responses using RAG.
- Conversation memory.
- PostgreSQL database integration.
- pgvector for vector storage and similarity search.
- Docker-based application deployment.

## Technologies Used

| Category | Technologies |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Database | PostgreSQL |
| Vector Database | pgvector |
| Authentication | JWT |
| AI Model | Ollama, Llama 3.2 |
| Embeddings | Sentence Transformers |
| Containerization | Docker, Docker Compose |
| Production Server | Gunicorn |

## Project Structure

```text
ai_knowledge_assistant/
│
├── app/
│   ├── models/
│   ├── processors/
│   ├── routes/
│   ├── static/
│   ├── templates/
│   ├── tools/
│   ├── config.py
│   ├── extensions.py
│   └── __init__.py
│
├── migrations/
├── uploads/
├── Dockerfile
├── compose.yaml
├── requirements.txt
├── run.py
├── .dockerignore
└── .gitignore
```

## How It Works

1. A user registers and logs in.
2. The user starts a conversation.
3. The user can upload a PDF, DOCX, or TXT document.
4. Know AI extracts the document text and divides it into chunks.
5. Sentence Transformers generates vector embeddings.
6. The embeddings are stored in PostgreSQL using pgvector.
7. When the user asks a question, the application retrieves relevant document content.
8. The retrieved context is provided to the language model to generate a relevant response.

## Requirements

- Python
- Docker Desktop
- PostgreSQL with pgvector
- Ollama
- Git

## Environment Configuration

Create a `.env` file in the project root.

Add the following variables with your own local configuration:

```env
LLM_API_KEY=your_local_value
DATABASE_URL=your_local_database_connection
JWT_SECRET_KEY=your_secret_key
DATABASE_DOCKER_URL=your_docker_database_connection
```

Never upload your actual `.env` file or expose database passwords and secret keys.

## Run with Docker

Build and start the application:

```bash
docker compose up -d --build
```

Check the running containers:

```bash
docker compose ps
```

View application logs:

```bash
docker compose logs -f web
```

Open the application:

```text
http://localhost:5000
```

## Future Improvements

- Cloud deployment.
- Hosted language model integration.
- Improved document management.
- Additional AI tools and capabilities.
- Enhanced security and production monitoring.

## Author

Developed as a hands-on AI and full-stack development project.