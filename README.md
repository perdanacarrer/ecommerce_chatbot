# E-commerce Chatbot Demo

A conversational e-commerce chatbot that enables users to discover, filter, and compare products using natural language.  
The system is built with a FastAPI backend, a chat-style frontend, and real product data from Google BigQuery’s public dataset.

---

## 🚀 Features

- Chat-based product discovery
- Natural language filters:
  - Price (under / over / exact)
  - Size (S, M, L, XL, XXL, One Size)
  - Gender / recipient (gift scenarios)
  - Product category (jackets, hoodies, shirts, etc.)
- Product carousel UI with comparison support
- Quick reply buttons for guided interactions
- Context-aware conversation (e.g. “these jackets”)
- Real data from BigQuery public dataset
- Mobile-responsive chat UI
- Fully Dockerized frontend and backend

---

## 🧰 Tech Stack

### Frontend
- HTML5
- CSS3 (mobile-first, chat-style UI)
- Vanilla JavaScript
- Nginx
- Docker

### Backend
- Python 3.11
- FastAPI
- Google Cloud BigQuery client
- REST API
- Docker

### Data
- Google BigQuery public dataset  
  `bigquery-public-data.thelook_ecommerce`

---

## ⚙️ Setup Instructions

### Prerequisites
- Docker & Docker Compose
- Google Cloud project with BigQuery access
- Google Cloud Service Account key (JSON)

### Environment Variables
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
export GOOGLE_CLOUD_PROJECT=your-project-id

Ensure GOOGLE_APPLICATION_CREDENTIALS is set to a GCP service account key.

For local dev, this is enough:
• brew install --cask google-cloud-sdk 
• gcloud version 
• gcloud init
• gcloud auth application-default login
• gcloud services enable bigquery.googleapis.com
• gcloud iam service-accounts create chatbot-sa \ --display-name "Chatbot Service Account"
• gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:chatbot-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.user"

## Run locally
docker-compose up --build

Access

Frontend: http://localhost:3000
Backend API: http://localhost:8000
Health check: http://localhost:8000/health

## Repository structure
.
├── backend/
│   ├── main.py                 # FastAPI backend (chat logic, BigQuery queries)
│   ├── requirements.txt        # Python dependencies
│   └── Dockerfile              # Backend Docker configuration
│   └── tests/
│   │   └── __init__.py
│   │   └── test_helpers.py
│   │   └── test_intent_detection.py
│   │   └── test_chat_endpoint.py
│   └── venv/
│
├── frontend/
│   ├── cypress/e2e
│   │   └── chat.cy.js
│   ├── index.html              # Chat UI markup
│   ├── app.js                  # Frontend chat logic
│   ├── app.css                 # UI styling
│   ├── placeholder.svg         # Mock product image
│   └── Dockerfile              # Frontend Docker configuration
│
├── docker-compose.yml           # Orchestrates frontend & backend services
├── README.md                    # Project documentation
├── DESIGN_RATIONALE.md          # UX decisions and creative features
└── PRODUCTION_PLAN.md           # Architecture, scalability, and roadmap
├── docs/
│   ├── architecture-overview.pdf # High-level system architecture            
│   ├── backend-flow.pdf          # Backend request & intent flow 
│   ├── data-flow.pdf             # Data movement & processing flow
│   └── deployment-diagram.pdf    # Deployment & infrastructure layout

### Notes & Limitations
• Product images and stock are mocked due to dataset limitations  
• Size availability is inferred from product names 
• Checkout flow is conversational only (no payment integration)
• BigQuery is used for analytics-style queries
• A transactional database is recommended for real orders

### Future Enhancements
• LLM-powered intent detection  
• Redis-based conversation memory 
• Real product images via CDN
• Inventory & order management with transactional DB
• Authentication and user profiles
• Kubernetes deployment (GKE/EKS)

Designed for clarity, UX polish, and explainability.
