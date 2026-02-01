# Python virtual environment & requirements

Steps to create the virtual environment and install dependencies (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

PowerShell activation alternative (if execution policy blocks script):

```powershell
.\.venv\Scripts\activate
```

Files created:
- requirements.txt — package list

---

## Railway / Docker deployment (summary)

This project can be deployed to Railway or any Docker-hosting platform. Key points:

- For production, enable Elasticsearch security and set a strong `ELASTIC_PASSWORD`. The docker-compose in this repo defaults `xpack.security.enabled` to **true** for secure deployments;
- On Railway, add the environment variables securely in the project settings (do NOT commit secrets to the repo). Use the Railway UI to set `ELASTIC_PASSWORD`, `ES_HOST` (usually `http://elasticsearch:9200`), `ES_USER` (defaults to `elastic`), and `PORT` (Railway will provide a dynamic port via `PORT` env variable).

### Recommended env variables to set (use `.env.example` as a template)
- `ELASTIC_PASSWORD` — strong password for the `elastic` user
- `ES_HOST` — `http://elasticsearch:9200` when using Docker service linking
- `ES_USER` — `elastic`
- `PORT` — Railway sets this automatically; default local value is `8000`

### Railway deployment notes
1. Push this repository to GitHub (or connect your repo to Railway).
2. On Railway, create a new project and connect the repo.
3. In project settings, add environment variables (copy from `.env.example` and fill in secure values).
   - **Important:** Set a strong `ELASTIC_PASSWORD` before deploying (see guidance below).
4. Deploy (Railway will build your Docker image using `Dockerfile`).
5. Verify the service is healthy and `ES_HOST` resolves to `http://elasticsearch:9200` inside the Railway environment.

> Note: `xpack.security.enabled=true` enables authentication on Elasticsearch; use `ELASTIC_PASSWORD` (set above).

#### Setting `ELASTIC_PASSWORD` (recommended)
- Generate a strong password locally (example):

```bash
# openssl method
openssl rand -base64 32

# or pwgen (if available)
pwgen -s 20 1
```

- On Railway: add `ELASTIC_PASSWORD` in the project Environment Variables (do NOT commit this to git).

- Locally (for `docker-compose` testing): create a local `.env` file in the project root (this file is ignored by default in `.gitignore`):

```
# .env
ELASTIC_PASSWORD=your_strong_password_here
ES_HOST=http://elasticsearch:9200
ES_USER=elastic
PORT=8000
```

Then run:

```bash
docker-compose up -d --build
```

- In PowerShell (session):

```powershell
$env:ELASTIC_PASSWORD = "<your_strong_password_here>"
# then run
docker-compose up -d --build
```

- On a DigitalOcean Droplet or other Linux server (session):

```bash
export ELASTIC_PASSWORD="<your_strong_password_here>"
docker-compose up -d --build
```

> Security note: Never commit secrets to the repository. Use Railway/hosted secrets or environment management for production.


