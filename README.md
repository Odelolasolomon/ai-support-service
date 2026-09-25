# AI Customer Support Service

A lightweight, hybrid FastAPI microservice designed for first-line customer support automation. The service combines rule-based intent routing, deterministic order verification, grounded LLM retrieval (OpenAI `gpt-4o-mini`), and safe fallback escalation to human support agents.

---

## Video Walkthrough

[Watch the assessment walkthrough video](https://github.com/Odelolasolomon/ai-support-service/blob/main/Assesment_explanation.mp4)

[Download the video from the repository](https://github.com/Odelolasolomon/ai-support-service/raw/main/Assesment_explanation.mp4)

---

## Request Lifecycle

Each incoming message goes through a tiered decision tree before invoking external model APIs:

```
Incoming Request (customer_id, message)
                  │
                  ▼
         [ Intent Classification ]
                  │
       ┌──────────┼──────────────┐
       ▼          ▼              ▼
[ order_status ]  [ knowledge_q ]  [ unknown_intent ]
       │          │              │
       │          ▼              │
       │     FAQ Search (local)  │
       │          │              │
       │     ┌────┴────┐         │
       │   Match     No Match    │
       │     │         │         │
       │     ▼         │         │
       │   OpenAI      │         │
       │  Grounding    │         │
       │     │         │         │
       │     └────┬────┘         │
       ▼          ▼              ▼
 [ Order Lookup ] [ Escalate Handler ]
       │                 │
       ▼                 ▼
   Response          Response
 (escalate: false)  (escalate: true)
```

1. **Schema Validation**: FastAPI validates incoming JSON against `ChatRequest` (minimum length checks for `customer_id` and `message`).
2. **Intent Classification**: Evaluates pattern matches:
   - Order tokens (`ord_`, `ord-`) route to `order_status`.
   - Keyword triggers (`refund`, `delivery`, `password`) route to `knowledge_question`.
   - Unrecognized queries immediately route to human escalation.
3. **Execution & Guardrails**:
   - **Order Lookups**: Deterministic regex extraction (`\bORD[-_]\d+\b`) and database lookup. If the order does not exist or belongs to another customer, the request immediately flags `escalate: true` to prevent unauthorized data exposure.
   - **Knowledge Base Retrieval**: Exact FAQ matches are fed into `gpt-4o-mini` with strict system constraints (`temperature=0`, grounded context only, zero-retries, 8.0s timeout).
   - **Escalation Fallback**: Any model timeout, missing context, or unhandled intent triggers a standardized fallback payload instead of a 500 server crash.

---

## Project Structure

```
ai-customer-support/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application initialization & routing
│   ├── models.py        # Pydantic request & response schemas
│   ├── knowledge.py     # Mock database (orders) & local FAQ knowledge store
│   └── service.py       # Intent router, regex extractors, OpenAI integration
├── tests/
│   └── test_main.py     # Test suite (health checks, order routing, fallbacks)
├── .env.example         # Template for environment variables
├── requirements.txt     # Python package dependencies
└── README.md
```

---

## Configuration

The application reads configuration from environment variables (or a local `.env` file via `python-dotenv`).

Copy the template:

```bash
cp .env.example .env
```

Set the following variables in `.env`:

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `open_api_key` | Yes | — | OpenAI API Secret Key (`sk-proj-...`) |
| `open_ai_model` | No | `gpt-4o-mini` | OpenAI completion model ID |

*(Note: The service also supports standard `OPENAI_API_KEY` and `OPENAI_MODEL` environment variable names).*

---

## Local Development

### 1. Requirements
* Python 3.11+
* pip

### 2. Setup Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv myvenv
.\myvenv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv myvenv
source myvenv/bin/activate
pip install -r requirements.txt
```

### 3. Start the Server

Run using Uvicorn with auto-reload:

```bash
uvicorn app.main:app --reload --port 8000
```

Once running:
* **Interactive API Docs (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **OpenAPI Schema**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## API Reference

### Health Check

```http
GET /health
```

**Response (200 OK):**
```json
{
  "status": "healthy"
}
```

---

### Chat Endpoint

```http
POST /chat
Content-Type: application/json
```

#### Request Payload
```json
{
  "customer_id": "cust_1",
  "message": "what is the status of ord_1"
}
```

#### Sample Responses

**1. Order Status (Verified Match):**
```json
{
  "intent": "order_status",
  "answer": "Your order ORD_1 is currently shipped.",
  "escalate": false
}
```

**2. Grounded FAQ (Knowledge Base + LLM):**
```json
{
  "intent": "knowledge_question",
  "answer": "Customer refunds are processed within 14 business days.",
  "escalate": false
}
```

**3. Unhandled Query or Unauthorized Access (Human Escalation):**
```json
{
  "intent": "unknown_intent",
  "answer": "I cannot give a very reliable answer or resolve to this request. I will refer it to a human support agent.",
  "escalate": true
}
```

---

## Running Tests

Test suites are implemented using `pytest` and `httpx.AsyncClient` via FastAPI's `TestClient`.

Run tests with verbose output:

```bash
python -m pytest -v
```

### Covered Test Cases:
* `test_health`: Verifies service readiness and endpoint health.
* `test_order_lookup`: Validates end-to-end extraction, customer identity verification, and status resolution.
* `test_unknown_question`: Verifies that out-of-scope inquiries fail safely with `escalate: true`.

---

## Design Decisions & Security Considerations

* **Hybrid Architecture over Pure Prompting**: Account queries and database lookups do not pass through the LLM. Order status is resolved deterministically in code. This avoids prompt injection exploits, eliminates LLM hallucinations on sensitive transaction data, and saves API tokens.
* **Tenant Isolation**: Orders are strictly scoped to the requesting `customer_id`. Looking up another user's order ID returns `None`, forcing a safe human escalation rather than leaking data.
* **Zero Temperature & Low Token Cap**: OpenAI completions run with `temperature=0` and `max_tokens=100` to enforce concise, repeatable, factual responses grounded strictly in the provided FAQ context.
* **Fail-Safe Fallback**: Any upstream network timeout (capped at 8.0s), authentication error, or missing context is caught at runtime and returns an escalation response with status code `200` instead of breaking client client-side state with an uncaught `500`.

---

# Production Scaling & Architecture Deep Dive

This section documents the design decisions I made building this AI customer support system, along with how I'd evolve it for production scale. I've kept the MVP intentionally lean, but the reasoning below reflects how I think about taking a project like this from prototype to something that could actually run in production.

## How would I scale this system?

My approach is to deploy multiple stateless FastAPI application instances horizontally behind a load balancer (e.g. AWS ALB or NGINX). I designed the application to hold no local state across requests, so any instance can serve any request.

- **State & Persistence**: I'd move conversation history, audit logs, and customer records from in-memory dictionaries into PostgreSQL.
- **Caching Layer**: I'd place Redis in front of the database for repeated FAQ lookups, active session caches, and order status results with short TTLs.
- **Asynchronous Workers**: I'd offload heavy or external operations (e.g. ticket creation, email dispatch, webhook triggers) to background workers using Celery or ARQ backed by Redis.

## How would I prevent hallucinations?

I don't think prompt instructions alone can guarantee factual accuracy — I'd rather build systemic guardrails than rely on the model behaving:

- **Strict Grounding**: Restrict LLM answers to approved company knowledge bases and confine operations strictly to verified tools.
- **Retrieval Quality Evaluation**: Score retrieval confidence before passing context to the model. If evidence is missing or scores fall below threshold, don't guess — escalate directly to a human agent.
- **Deterministic Isolation**: This is the principle I care about most here — I keep core business operations (account balances, order lookups, order cancellations) out of LLM text generation entirely, and resolve them through deterministic, typed code paths instead. The LLM decides *what* to call, never *what the answer is* for anything numeric or transactional.

## What happens when the LLM fails?

In my implementation, I enforce an explicit HTTP request timeout (8.0s) and catch provider errors to return an escalation decision (`escalate: true`) rather than fabricating an answer or failing open. I'd rather the system admit uncertainty than pretend to know something it doesn't.

In production, I'd reinforce this with:

- **Circuit Breakers**: Trip the circuit (e.g. via `tenacity` or Envoy) if upstream provider error rates or latency thresholds exceed limits, immediately routing queries to human queues without waiting for timeouts.
- **Structured Logging & Telemetry**: Emit structured JSON logs with correlation IDs (`request_id`) and configure real-time alert thresholds on provider failure rates (e.g. Datadog, Prometheus/Grafana, PagerDuty).

## What would I improve for production?

- **Ticket Creation Pipeline**: Connect the `escalate: true` branch to an actual ticketing platform (Zendesk, Linear, Jira Service Management) to automatically generate a support ticket with conversation context.
- **Persistent Conversation History**: Multi-turn dialogue support persisted in PostgreSQL with rolling window caching in Redis.
- **Semantic Retrieval (RAG)**: Upgrade from substring keyword matching to dense vector embeddings.
- **Comprehensive Test Suite**: Expand unit tests with integration testing, property-based tests, and automated evaluation sets for intent accuracy.
- **Observability & Tracing**: Instrument endpoints with OpenTelemetry for distributed tracing across external API boundaries.
- **Access Control**: Replace client-supplied `customer_id` with verified JWT bearer tokens parsed by authentication middleware.
- **CI/CD Pipeline**: Automated test execution, linting (`ruff`, `mypy`), container builds via Docker, and blue/green deployment orchestration.

---

## Vector Database Recommendations (for Semantic Search)

When upgrading `knowledge.py` from substring keyword matching to full vector retrieval (RAG), here's how I'd weigh the options:

| Vector Database | Best For | Why I'd pick it |
|---|---|---|
| **pgvector (PostgreSQL)** *(My default recommendation)* | General Production | Keeps operational complexity minimal. Embeddings live directly alongside customer and order tables in PostgreSQL, so I get ACID transactions and relational joins without adding a new infrastructure dependency. |
| **Qdrant** | High-Throughput & Advanced Filtering | Written in Rust, highly optimized for latency, and supports advanced payload-based filtering (e.g. filtering FAQs by customer tier, product type, or locale before calculating cosine similarity). |
| **Pinecone** | Fully Managed Serverless | Zero operational overhead, fully managed cloud scaling, and built-in hybrid search (dense + sparse keyword retrieval). |
| **Chroma** | Local & Prototyping | Lightweight, embeddable, and ideal for quick development or self-hosted test suites without running extra cloud services. |

---

## My Production Roadmap

- [ ] Replace in-memory dictionaries with async PostgreSQL / SQLAlchemy models.
- [ ] Implement JWT/OAuth2 bearer authentication in middleware instead of trusting client-supplied `customer_id`.
- [ ] Migrate knowledge base to `pgvector` or `Qdrant` using `text-embedding-3-small`.
- [ ] Add Redis-backed sliding window rate limiting (via `slowapi`).
- [ ] Integrate OpenTelemetry instrumentation for distributed tracing and LLM latency monitoring.