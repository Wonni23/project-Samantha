This project was created by donjung, suwi, yeoju, jisopark, and sangwook as part of the ft_transcendence.

## 1. Overview (Description)

**Samantha**: An intelligent interaction platform combining Live2D avatars with conversational AI.

This application provides a highly personalized chatting experience with the virtual character 'Samantha'. It implements real-time Live2D rendering on the web through a Flutter-based frontend and combines a FastAPI backend with RAG (Retrieval-Augmented Generation) technology to store and utilize user conversation history as long-term memory. This enables interactions that understand and empathize with the user's context, going beyond a simple chatbot.

### Key Implemented Features

- **Real-time AI Chat**: Low-latency bidirectional conversation using WebSockets.
- **Web-based Live2D Avatar**: Dynamic character animation rendering utilizing PixiJS.
- **RAG-based Long-term Memory**: Embedding user-related information using `pgvector` and retrieving it according to the conversation context.
- **Multiple Authentication Methods**: Support for local email signup and social logins (Kakao, Naver, Google).
- **Structured Onboarding**: User initial setup process including profile settings and terms of service agreement.
- **Gamification Elements**: User engagement through Quest, Routine, and Store systems. | _Planned for future update_
- **Object Storage**: Management of generative AI assets and user data using MinIO.

## 2. Instructions

### Prerequisites

- **Docker**: Version 20.10 or higher
- **Required Environment Variables** (based on `docker-compose.yml`):
    - `POSTGRES_USER`: PostgreSQL database username.
    - `POSTGRES_PASSWORD`: PostgreSQL database password.
    - `POSTGRES_DB`: Default database name.
    - `S3_ENDPOINT_URL`: MinIO object storage endpoint.
    - `MINIO_ROOT_USER`: MinIO administrator ID.
    - `MINIO_ROOT_PASSWORD`: MinIO administrator password.

### Step-by-Step Setup and Execution

1. **Clone the Repository**
    ```bash
    git clone [Repository-url]
    cd Samantha
    ```
2. **Environment Variable Configuration**: Create a `.env` file containing the above variables in the root directory or `./backend` folder.
3. **Build and Run with Shellscript**
    ```bash
    ./dev.sh run
    ```

### Access Information

- **Application URL**: `http://localhost:8080` (or `https://localhost:8443`)
- **API Documentation (Swagger)**: `http://localhost:8000/docs`
- **Default Admin Account**: [TODO: To be added]

## 3. Technical Stack

- **Frontend**: **Flutter Web**. Chosen for high-performance UI rendering and cross-platform extensibility in a web environment. It uses `Riverpod` for state management and `Dio` for communication, integrating `PixiJS` and `Live2D SDK` for visual quality.
- **Backend**: **FastAPI (Python 3.10+)**. Selected for its excellent asynchronous processing performance and compatibility with LLM libraries. It uses `SQLModel` as the ORM and implements AI memory features through `pgvector`.
- **Database**: **PostgreSQL + pgvector**. Chosen to simultaneously ensure relational data stability and vector similarity search capabilities.
- **Real-time Communication**: **Socket.io**. Adopted as a low-latency bidirectional communication solution for real-time character responses and conversation streaming.
- **DevOps**: **Docker & Docker Compose**. API, DB, storage (MinIO), and web server (Nginx) are containerized to establish a consistent execution environment.

## 4. Database Schema

| Table/Entity Name | Key Fields & Types                                      | Relationships & Description                                       |
| ----------------- | ------------------------------------------------------- | ----------------------------------------------------------------- |
| `User`            | `id` (UUID), `email` (String), `password_hash` (String) | Basic user info. 1:1 with `UserContext`, 1:N with `Conversation`. |
| `UserContext`     | `id` (UUID), `user_id` (UUID), `axis_playful` (Float)   | Stores user tendencies and personalization. Belongs to `User`.    |
| `Conversation`    | `id` (UUID), `user_id` (UUID), `content` (String)       | Conversation logs and message history. Belongs to `User`.         |
| `SocialAccount`   | `id` (UUID), `user_id` (UUID), `provider` (String)      | Social OAuth integration info. Belongs to `User`.                 |
| `LifeLegacy`      | `id` (UUID), `user_id` (UUID), `embedding` (Vector)     | RAG-extracted memory (vector data). Belongs to `User`.            |
| `QuestLog`        | `id` (UUID), `user_id` (UUID), `status` (Enum)          | Tracks quest progress per user.                                   |
| `UserInventory`   | `id` (UUID), `user_id` (UUID), `item_id` (UUID)         | List of items owned by the user.                                  |

## 5. Features List

### Sia Engine: Multi-Modal AI Interaction

The core intelligence layer powered by Gemini, designed for deep emotional resonance.

- **Analysis-First Architecture**: Every user input undergoes deep analysis (Emotion, Topic, Intent) before generating a response.
- **Dynamic 5-Axis Personality**: Real-time updates to Sia's personality across 5 dimensions:
    - `Playful` (Witty/Flirting), `Feisty` (Sassy/Defiant), `Dependent` (Advice-Seeking), `Caregive` (Empathy/Soothing), `Reflective` (Deep/Legacy).
- **Advanced Pacing & Depth Control**: Proactive conversation management using `PROBE` (Active Guiding) and `ABSORB` (Empathetic Listening) modes to prevent "interrogation" feel.
- **Context-Aware Rapport System**: Dynamically adjusts Sia's linguistic style between `STRANGER` (Polite) and `FAMILY` (Casual/Banmal) based on the session's rapport tier and conversation context.

### Advanced Long-Term Memory (RAG)

Going beyond simple chat history with a sophisticated retrieval system.

- **Hybrid Search Engine**: Combines `pgvector` semantic search with keyword-based retrieval for maximum accuracy.
- **POS-Weighted Retrieval**: Uses `Kiwi` (Korean Morpheme Analyzer) to prioritize proper nouns and significant terms in memory search.
- **Life Legacy Mining**: Automatically extracts and structures user's past memories and preferences into a "Life Legacy" database.
- **Profile-Augmented Generation**: Integrates structured user profile data (Title, Preferences, Relationships) into every response.

### Real-Time Live2D Visuals

A high-fidelity visual experience that brings Sia to life.

- **Emotion-Synced Expressions**: Sia's facial expressions and body language change dynamically based on the AI's sentiment analysis.
- **Web-Optimized Rendering**: Smooth, high-performance Live2D rendering using PixiJS and Cubism SDK on Flutter Web.
- **Interactive Feedback**: Character reacts to user interactions and conversation state transitions.

### Voice-First Interface (VUI)

Natural, low-latency voice communication.

- **Streaming Voice Synthesis**: Real-time TTS (Text-to-Speech) streaming for immediate verbal responses.
- **Whisper-Powered STT**: Accurate speech recognition optimized for conversational Korean.
- **Push-to-Talk (PTT)**: Optimized UI for natural turn-taking in voice conversations.

### Secure Auth & Onboarding

Seamless and reliable user management.

- **Multi-Channel Login**: Support for Local Email, Kakao, Naver, and Google OAuth.
- **Structured Onboarding**: Guided process for profile setup (Name, Birthday, Title) and essential terms agreement.
- **Session Continuity**: Robust JWT-based authentication with refresh token support for long-lasting sessions.

### Gamification & Economy (Planned)

Systems to encourage long-term engagement.

- **Daily Quests & Routines**: Encourages regular interaction through structured activities.
- **Virtual Store**: Purchase decorative elements and persona enhancers using in-app currency.
- **Achievement System**: Rewards for reaching rapport milestones and completing memory "Life Legacies".

## 6. Implemented Modules

_Note: As an AI-specialized application, the ft_transcendence evaluation criteria have been interpreted and implemented as follows:_

- **Web | Major: Framework (2pts)**
    - **Description**: Robust asynchronous backend architecture using FastAPI and complex Single Page Application (SPA) implementation using Flutter Web.
- **Web | Major: Real-time features (2pts)**
    - **Description**: Real-time conversation and Live2D animation synchronization using Socket.io.
- **Web | Minor: Use an ORM (1pt)**
    - **Description**: PostgreSQL schema management and data modeling using SQLModel.
- **Web | Minor: Additional Browsers (1pt)**
    - **Description**: Cross-browser support including Firefox and Edge, ensuring a consistent experience beyond Chrome.
- **AI | Major: RAG System (2pts)**
    - **Description**: Vector DB integration for retrieval-augmented generation, reflecting user's past memories (e.g., bereavement, preferences) in conversations.
- **AI | Major: LLM Interface (2pts)**
    - **Description**: Gemini API integration featuring persona injection, streaming responses, and advanced error handling.
- **AI | Minor: Voice Integration (1pt)**
    - **Description**: Voice-First interface based on Whisper (STT) and ElevenLabs (TTS) for natural interaction.
- **AI | Minor: Sentiment Analysis (1pt)**
    - **Description**: Analyzing user sentiment (e.g., depression, joy) to drive adaptive response logic (comfort or playfulness).
- **User | Minor: Remote Auth (OAuth) (1pt)**
    - **Description**: Kakao and Google login integration, prioritizing accessibility for elderly users.
- **Custom | Major: Live2D Visual System (2pts)**
    - **Description**: A visual reward system that controls character expressions and behaviors based on LLM-driven sentiment analysis.

**Total Cumulative Points**: 15 points

## 7. Roles & Responsibilities

### **@donjung | Product Owner**

> **"Visionary & Architect"**
> Designs the 'Zeitgeist' and philosophy of the service beyond simple features and builds the technical backbone.

- **Product Ownership (PO):**
    - Establishing product vision and roadmap (6-week MVP goals).
    - Investment attraction (IR), sales, and external stakeholder communication.
    - Product Backlog management and final decision-making on feature priorities (P0~P3).
- **System Architecture:**
    - Designing overall service architecture and confirming data models (Schema).
    - Designing core algorithms to solve technical challenges.
- **Prompt Engineering (Persona Design):**
    - Tuning Samantha's personality, tone, and 5-axis weighting system prompts.
    - Defining roles for Analyst and Actor and writing system directives (System Prompts).

---

### **@jisopark | Tech Lead & Backend Lead**

> **"WD-40"**
> The lubricant responsible for system stability. Ensures backend robustness so the PO can focus on business.

- **Code Quality & DevOps:**
    - Backend code reviews and establishing best practices guidelines.
    - Docker/Infra environment optimization.
    - Database migration (Alembic) and integrity verification.
- **Operational Continuity:**
    - Backend development and operation deputy in PO's absence (Backup Power).
    - Emergency response (Hotfix) and performance troubleshooting.
    - Enhancing exception handling and logging systems.

---

### **@suwi | Project Manager & Frontend Lead**

> **"Commander & Builder"**
> The manager who keeps the project's heart beating and the leader responsible for the first screen users encounter.

- **Project Management (PM):**
    - Sprint schedule management and deadline monitoring.
    - Leading team meetings, issue tracking, and identifying/removing blockers.
    - Coordinating team communication and ensuring R&R compliance.
- **Frontend Lead (Flutter):**
    - Client App architecture design (State Management, Socket Handling).
    - Implementing core features (PTT logic, Optimistic UI, Audio Streaming Player).
    - Reviewing technical feasibility of UI/UX design and final quality responsibility.

---

### **@yeoju | CAO (Chief AI Officer)**

> **"Brain"**
> Researches latest AI technologies to elevate the intelligence of the service.

- **AI Research & Engineering:**
    - RAG (Retrieval-Augmented Generation) pipeline enhancement and vector search optimization.
    - Designing custom pipeline: Speech-to-text → Analyst → Bridge (RAG) → Actor → TTS.
    - Performance comparison and selection of STT/TTS/Analyst/Actor models (Latency minimization research).
    - Researching and applying Legacy Mining (autobiography data extraction) algorithms (Collaborating with PO).

---

### **@sangwook | Frontend Developer**

> **"Supporter"**
> Implements UI components and assists according to the lead's instructions.

- **UI Implementation:**
    - Implementing simple UI widgets and screen markups assigned by Frontend Lead (suwi).
    - Applying design assets and assisting with styling.
    - Handling repetitive tasks so the Lead can focus on core logic.

## 8. Project Management

- **Task Allocation**: Github Project
- **Tools Used**: Notion, Slack, Github
- **Communication Channels**: Slack

## 9. Resources

- **Flutter**: [https://docs.flutter.dev/](https://docs.flutter.dev/)
- **FastAPI**: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- **PostgreSQL**: [https://www.postgresql.org/docs/](https://www.postgresql.org/docs/)
- **pgvector**: [https://github.com/pgvector/pgvector](https://github.com/pgvector/pgvector)
- **Live2D Cubism SDK**: [https://www.live2d.com/en/sdk/](https://www.live2d.com/en/sdk/)
- **Docker**: [https://docs.docker.com/](https://docs.docker.com/)
- **AI Usage Disclosure**: [TODO: Honest disclosure of AI tool usage]

## 10. Known Limitations

Identified improvements needed based on codebase analysis:

- `frontend/lib/features/auth/data/repositories/auth_repository.dart`: Need more specific error handling logic for `DioException`.
- `frontend/lib/common/widgets/footer.dart`: Update copyright notice and app name in the footer with actual service info.
- `backend/app/sockets/events.py`: Add integration logic when per-user TTS voice fields are implemented.
- `backend/app/engine/conversation.py`: Review concurrency issues related to shared dictionary references in `MemorySessionStore`.
- `frontend/android/app/build.gradle.kts`: Android App ID and release signing configurations are set to defaults and need modification for actual deployment.
