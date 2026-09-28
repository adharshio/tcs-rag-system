# Campus Placement Assistant

[![CI](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml/badge.svg)](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml)
[![CodeQL](https://github.com/<OWNER>/<REPO>/actions/workflows/codeql.yml/badge.svg)](https://github.com/<OWNER>/<REPO>/actions/workflows/codeql.yml)

An AI assistant that answers student placement questions using the college's official documents. It uses Retrieval-Augmented Generation (RAG), so every answer is grounded in real policy text and comes with sources.

> **Example:** "Can a student with 7.2 CGPA apply for Infosys?" The system finds the relevant eligibility policy and answers from it. If the documents don't contain the answer, it says so instead of inventing a rule.

## Contents

- [How it works](#how-it-works)
- [Team structure](#team-structure)
- [Repository layout](#repository-layout)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [API](#api)
- [Security](#security)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [Project status](#project-status)

## How it works

```
Placement documents (PDF, DOCX)
        │
        ▼
Document pipeline: extract, clean, chunk, add metadata
        │
        ▼
Vector database (embeddings)
        │
Student question ──► Retrieve top-K relevant chunks ──► LLM ──► Grounded answer + sources
```

1. Placement policies, eligibility rules, training calendars, and company FAQs are processed into small text chunks with metadata (document, category, company, year).
2. Chunks are embedded and stored in a vector database.
3. When a student asks a question, the most relevant chunks are retrieved.
4. The LLM writes an answer using only those chunks and lists its sources.
5. Out-of-domain or unanswerable questions are refused rather than guessed.

## Team structure

| Team | Area | Responsibility |
|---|---|---|
| 1 | Document and data pipeline | Collect, clean, chunk, and store placement documents |
| 2 | RAG / AI engine | Embeddings, vector database, retrieval, prompts, citations |
| 3 | Backend and API | FastAPI services, auth, sessions, chat history |
| 4 | Frontend | Student chat interface and placement screens |
| 5 | Testing, security, deployment | Evaluation, hardening, CI/CD, hosting, monitoring |

## Repository layout

```
.
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                 # tests, dependency audit, secret scan
│   │   └── codeql.yml             # code scanning
│   ├── dependabot.yml             # weekly dependency updates
│   ├── CODEOWNERS                 # required reviewers
│   └── pull_request_template.md   # security checklist for every PR
├── backend/
│   ├── main.py                    # hardened FastAPI skeleton
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/                     # automated security tests
├── security-tests/
│   └── run_security_checks.sh     # smoke tests against a deployed API
├── docker-compose.yml             # local dev and offline demo fallback
├── .env.example                   # environment variable template
├── SECURITY.md                    # security policy and team rules
├── DEPLOY.md                      # deployment runbook
└── README.md
```

Folders for the other teams (`frontend/`, `rag/`, `data/`) are added as their work lands.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React / Next.js, Tailwind CSS |
| Backend | Python, FastAPI |
| RAG | LangChain or LlamaIndex, embedding model, LLM |
| Vector database | ChromaDB or FAISS (Pinecone/Qdrant if hosted) |
| Database | PostgreSQL |
| Document processing | PyMuPDF, python-docx |
| Hosting | Vercel (frontend), Render or Railway (backend) |
| CI/CD and security | GitHub Actions, CodeQL, Dependabot, gitleaks |

## Getting started

### Prerequisites

- Python 3.11+
- Docker (optional, for the compose setup)
- Node.js 20+ (once the frontend exists)

### Run the backend locally

```bash
git clone https://github.com/<OWNER>/<REPO>.git
cd <REPO>

cp .env.example .env            # then fill in real values
# generate a strong secret:
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into JWT_SECRET

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# load the .env values into your shell, then:
set -a && source ../.env && set +a
uvicorn main:app --reload
```

The API runs at `http://localhost:8000`. Interactive docs are at `/docs` when `ENV` is not `production`.

### Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

### Environment variables

See [`.env.example`](.env.example). The main ones:

| Variable | Purpose |
|---|---|
| `ENV` | `development`, `staging`, or `production` |
| `JWT_SECRET` | Signs login tokens. Required, the app will not start without it |
| `ALLOWED_ORIGINS` | Comma-separated frontend URLs allowed by CORS |
| `DATABASE_URL` | PostgreSQL connection string |
| `LLM_API_KEY` | Key for the LLM provider |
| `RATE_LIMIT_CHAT` | Chat rate limit, for example `10/minute` |

Never commit a real `.env` file.

## API

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/health` | No | Health check |
| POST | `/api/chat` | Yes | Ask a placement question |
| GET | `/api/companies` | Yes | Company information (planned) |
| GET | `/api/calendar` | Yes | Training calendar (planned) |
| GET | `/api/eligibility` | Yes | Eligibility checker (planned) |

### Chat example

```http
POST /api/chat
Authorization: Bearer <token>
Content-Type: application/json

{ "question": "What companies can I apply for?" }
```

```json
{
  "answer": "Based on the current placement policy...",
  "sources": ["Placement Policy 2026", "Company Eligibility FAQ"]
}
```

Questions must be 1 to 500 characters. Until the RAG engine is connected, the endpoint returns a placeholder answer.

## Security

Security is built in from the start. The full policy and per-team rules are in [SECURITY.md](SECURITY.md).

**API protections**
- JWT authentication on every route except `/api/health`
- Rate limiting on the chat endpoint
- Input validation with length limits
- CORS restricted to the frontend domain
- Security headers on all responses
- Generic error messages, with no stack traces exposed
- API docs disabled in production

**Repository protections**
- Branch protection on `main`, with pull requests and passing CI required
- Secret scanning and push protection
- gitleaks scan of the full git history in CI
- Dependabot updates and `pip-audit` / `npm audit` in CI
- CodeQL scanning on every pull request and weekly
- CODEOWNERS review for sensitive areas

**Data rules**
- No real student data in the repo, test data, logs, or vector database
- Secrets live only in the hosting platform's secret store

**Reporting a vulnerability:** do not open a public issue. Use the repository's **Security > Report a vulnerability** option or contact the security leads listed in [SECURITY.md](SECURITY.md).

## Testing

### Automated tests

```bash
cd backend
ENV=test JWT_SECRET=test-secret-at-least-32-characters-long ALLOWED_ORIGINS=http://localhost:3000 RATE_LIMIT_CHAT=1000/minute pytest -q
```

The suite checks that unauthenticated, expired, and forged tokens are rejected, input limits are enforced, security headers are present, and unknown origins are blocked by CORS.

### Smoke tests against a deployed API

```bash
./security-tests/run_security_checks.sh https://<your-api-url> [valid-token]
```

### RAG evaluation

The evaluation set covers eligibility, policy, calendar, company FAQ, missing-information, out-of-domain, and adversarial (prompt injection) questions. Metrics tracked:

- Retrieval accuracy
- Answer correctness
- Groundedness
- Hallucination rate
- Response time (p50 and p95)

## Deployment

| Environment | Branch | Purpose |
|---|---|---|
| Staging | `dev` | Testing before release |
| Production | `main` | Live demo |

The step-by-step process, rollback instructions, and key rotation guide are in [DEPLOY.md](DEPLOY.md).

For demo day, keep the offline fallback ready: `docker compose up --build` on a laptop, plus a recorded demo.

## Contributing

1. Branch from `dev`. Never push directly to `main`.
2. Keep commits free of secrets and student data.
3. Open a pull request and complete the security checklist in the template.
4. Wait for CI to pass and get at least one review.
5. Follow the rules for your team in [SECURITY.md](SECURITY.md).

## Project status

- [x] Repository security settings and CI
- [x] Hardened API skeleton with automated security tests
- [ ] Document pipeline (Team 1)
- [ ] RAG engine connected to `/api/chat` (Team 2)
- [ ] Authentication, sessions, and chat history (Team 3)
- [ ] Student interface (Team 4)
- [ ] Evaluation results and load testing (Team 5)
- [ ] Production deployment and uptime monitoring (Team 5)

## Team

| Role | Name | Contact |
|---|---|---|
| Security and deployment | `<NAME>` | `<EMAIL>` |
| Testing and evaluation | `<NAME>` | `<EMAIL>` |

## License

Add a license before making the repository public, for example MIT.
