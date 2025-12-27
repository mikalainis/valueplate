# 🥗 Value Plate
**Intelligent Grocery Planning & Budget Optimization**

Value Plate is a high-performance microservices application designed to take the mental load off grocery shopping. By combining a dedicated Python planning engine with a secure Go-based authentication gateway, Value Plate ensures you get the best nutritional value for your budget in under 5 seconds.

---

## 🚀 The 5-Second KPI
Value Plate is architected for speed. Our core performance goal is to generate a fully optimized, aisle-sorted grocery plan within **5 seconds** of a user request, regardless of inventory complexity.

---

## 🛠 Tech Stack
Value Plate uses a modern, distributed architecture:

* **Auth Service:** Built with **Go (Golang)** & **GraphQL (gqlgen)**. Integrates with **Firebase Admin SDK** for secure identity management and **PostgreSQL** for persistent user data.
* **Plan Engine:** A high-speed **Python** service that processes grocery data, optimizes shopping paths, and manages real-time inventory.
* **Frontend:** A responsive **React** dashboard (Vite) for a seamless user experience.
* **Infrastructure:** Containerized with **Docker & Docker Compose** for consistent deployment across Google Cloud Platform (GCP).

---

## 📂 Repository Structure
```text
.
├── auth-service/     # Go GraphQL Gateway & Firebase Integration
├── plan-engine/      # Python logic for grocery optimization
├── frontend/         # React (Vite) user interface
├── docker-compose.yml # Orchestration for local development
└── serviceAccountKey.json # Firebase Admin credentials (GIT IGNORED)