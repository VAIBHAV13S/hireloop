# Deploying HireLoop Live for Free (Step-by-Step Guide)

You can deploy HireLoop to a public HTTPS URL (e.g. `https://hireloop.onrender.com`) **100% free with no credit card required** in under 5 minutes.

---

### The Free Cloud Architecture

| Layer | Free Provider | Why This Provider | Free Tier Limits |
| :--- | :--- | :--- | :--- |
| **Database + Vector Search** | **[Neon.tech](https://neon.tech)** | Serverless PostgreSQL with `pgvector` pre-installed | 0.5 GB storage, instant branching, 100% free |
| **Web API & Dashboard** | **[Render.com](https://render.com)** | Auto-builds from GitHub, automatic HTTPS/TLS | Free Web Service, 512 MB RAM, spins up on visit |
| **Task Cache & Redis (Optional)** | **[Upstash.com](https://upstash.com)** | Serverless Redis with zero server maintenance | 10,000 commands/day free forever |

---

## Step 1: Create Free PostgreSQL Database on Neon (60 seconds)

1. Go to **[Neon.tech](https://neon.tech)** and sign up (using your GitHub account).
2. Click **"Create Project"** and name it `hireloop-db`.
3. Select any region (e.g., US East / Oregon) and PostgreSQL 16.
4. Neon will show you a connection string like:
   ```text
   postgres://username:password@ep-cool-base-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
5. Copy this connection string.

*(Note: HireLoop automatically runs `CREATE EXTENSION IF NOT EXISTS vector;` on first boot, so pgvector is enabled automatically!)*

---

## Step 2: Push Your Code to GitHub (60 seconds)

Make sure your `hireloop` folder is pushed to a repository on GitHub (Public or Private):
```bash
git init
git add .
git commit -m "feat: complete HireLoop AI talent platform"
git branch -M main
git remote add origin https://github.com/<your-username>/hireloop.git
git push -u origin main
```

---

## Step 3: Deploy to Render for Free (3 minutes)

1. Go to **[Render.com](https://render.com)** and sign in with GitHub.
2. Click **"New +"** in the top navigation bar and select **"Web Service"**.
3. Choose **"Build and deploy from a Git repository"** and connect your `hireloop` repository.
4. Fill in the settings:
   * **Name:** `hireloop` (or your choice, e.g. `hireloop-demo`)
   * **Region:** Same or close to your Neon DB (e.g., Oregon)
   * **Branch:** `main`
   * **Runtime:** `Python 3`
   * **Build Command:**
     ```bash
     pip install -U pip poetry && poetry export -f requirements.txt --output requirements.txt --without-hashes && pip install -r requirements.txt
     ```
   * **Start Command:**
     ```bash
     uvicorn hireloop.apps.api.app.main:app --host 0.0.0.0 --port $PORT
     ```
   * **Instance Type:** Select **Free**
5. Scroll down to **"Environment Variables"** and click **"Add Environment Variable"**:
   * `PYTHONPATH`: `.`
   * `DATABASE_URL`: *(paste the Neon connection string from Step 1)*
   * `JWT_SECRET_KEY`: `your-random-secret-key-xyz`
   * *(Optional)* `OPENAI_API_KEY`: *(paste your key if using hosted OpenAI embeddings/models, or leave blank to use the built-in deterministic local embedder)*
   * *(Optional)* `ANTHROPIC_API_KEY`: *(paste your key if using Claude for resume extraction/agent)*
6. Click **"Create Web Service"**.

---

## Step 4: Verify Your Live Deployment!

Render will build the project and launch your service.
Once the build completes (usually ~2 minutes), your service will be live at:
```text
https://hireloop-<your-id>.onrender.com/
```

### What happens automatically on first boot:
- The startup lifespan hook in `main.py` detects the Neon database.
- Runs `CREATE EXTENSION IF NOT EXISTS vector;` and creates all tables and HNSW indexes.
- Automatically seeds the 8 realistic engineering positions into the database index.
- Serves the **Designeer-crafted Live Dashboard** directly at `https://your-service.onrender.com/`!
- Serves interactive OpenAPI documentation at `https://your-service.onrender.com/docs`.

---

## Step 5: Put It On Your Resume & Job Application

Now you can proudly write on your resume and in your cover letter:
> **Live Demo:** `https://hireloop-demo.onrender.com`  
> **Source Code & Evals:** `https://github.com/<your-username>/hireloop`

This directly proves the "Good to have: Have a side project live and used by real people" and "Some experience with Docker or cloud deploys" lines in the job description!
