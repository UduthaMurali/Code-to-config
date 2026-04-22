# Even-Odd Checker — Code-to-Config Drift Demo

A minimal **Flask** web app that demonstrates **automated code-to-config drift
detection** in a GitHub Actions CI/CD pipeline — as described in the paper
*"Automated Prevention of Code-to-Config Drift in CI/CD Pipelines"*.

---

## 📁 Project Structure

```
even-odd-drift-demo/
├── app.py                        # Flask app (reads env vars)
├── drift_checker.py              # Drift detection script (AST-based)
├── docker-compose.yml            # Deployment config (declares env vars)
├── .env.example                  # Example .env file (declares env vars)
├── k8s/
│   └── deployment.yaml           # Kubernetes deployment (declares env vars)
├── Dockerfile
├── requirements.txt
└── .github/
    └── workflows/
        └── drift-check.yml       # GitHub Actions pipeline
```

---

## 🚀 Quick Start (Local)

```bash
# 1. Clone / download the project
cd even-odd-drift-demo

# 2. Copy the example env file
cp .env.example .env

# 3a. Run with Docker Compose (recommended)
docker-compose up --build

# 3b. OR run directly with Python
pip install -r requirements.txt
python app.py

# 4. Open http://localhost:5000
```

---

## ☁️ Push to GitHub (one-time setup)

```bash
# Inside the project folder:
git init
git add .
git commit -m "Initial commit: even-odd app with drift checker"

# Create a new repo on GitHub (e.g. github.com/new), then:
git remote add origin https://github.com/<YOUR_USERNAME>/<REPO_NAME>.git
git branch -M main
git push -u origin main
```

The GitHub Actions pipeline is now active. Any Pull Request to `main` will
automatically run the drift checker.

---

## 🎬 Live Demo: Showing Code-to-Config Drift

### Step 1 — Verify the baseline (no drift)

```bash
pip install pyyaml
python drift_checker.py
```

Expected output:
```
## ✅ No Drift Detected
All environment variables referenced in code are declared in the deployment configuration.
```

---

### Step 2 — Introduce drift (simulate a developer mistake)

Create a new branch and add a new environment variable to `app.py` **without**
updating the config files:

```bash
git checkout -b feature/add-analytics
```

Add this line anywhere near the top of `app.py`:

```python
ANALYTICS_KEY = os.getenv("ANALYTICS_KEY")   # ← new, not in config!
```

Save the file, then run the drift checker locally:

```bash
python drift_checker.py
```

Expected output:
```
## ❌ Config Drift Detected!

| Variable      | Source File |
|---------------|-------------|
| `ANALYTICS_KEY` | `app.py`  |

> Action Required: Add the missing variables to your deployment configuration.
```

---

### Step 3 — Open a Pull Request and watch GitHub block it

```bash
git add app.py
git commit -m "feat: add analytics tracking (missing config!)"
git push origin feature/add-analytics
```

1. Go to your GitHub repo → **Pull Requests** → **New Pull Request**
2. Select `feature/add-analytics` → `main`
3. Watch the **"Code-to-Config Drift Check"** action run automatically
4. The pipeline **fails** and posts a comment like this on the PR:

> ## 🔍 Drift Checker Report
>
> ## ❌ Config Drift Detected!
>
> | Variable | Source File |
> |----------|-------------|
> | `ANALYTICS_KEY` | `app.py` |
>
> **Action Required:** Add the missing variables before this PR can be merged.

---

### Step 4 — Fix the drift and watch the pipeline pass

Add the missing variable to `docker-compose.yml`:

```yaml
environment:
  ...
  ANALYTICS_KEY: "your-analytics-key-here"   # ← fix
```

Also add it to `.env.example`:

```
ANALYTICS_KEY=your-analytics-key-here
```

And to `k8s/deployment.yaml` under `env:`:

```yaml
- name: ANALYTICS_KEY
  value: "your-analytics-key-here"
```

Then commit and push:

```bash
git add docker-compose.yml .env.example k8s/deployment.yaml
git commit -m "fix: declare ANALYTICS_KEY in all deployment configs"
git push origin feature/add-analytics
```

The pipeline re-runs and now shows:

> ## ✅ No Drift Detected

The PR is unblocked and can be merged. ✓

---

## 🔍 How the Drift Checker Works

`drift_checker.py` performs three steps:

1. **Scan code** — walks all `*.py` files using Python's `ast` module and
   finds every `os.getenv("VAR")` / `os.environ["VAR"]` call.

2. **Scan configs** — reads declared variable names from:
   - `docker-compose.yml` → `services > <svc> > environment`
   - `.env.example` → `KEY=value` lines
   - `k8s/*.yaml` → `spec > containers > env > name`

3. **Compare** — reports variables present in code but missing from configs
   (critical drift) and variables declared in configs but unused in code
   (dead configuration).

---

## 🔧 Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `Even-Odd Checker` | Title shown in the UI |
| `APP_VERSION` | `1.0.0` | Version shown in the UI |
| `APP_PORT` | `5000` | Port Flask listens on |
| `SECRET_KEY` | *(dev only)* | Flask session secret |
| `DEBUG_MODE` | `false` | Enable Flask debug mode |
| `MAX_INPUT` | `1000000` | Maximum allowed number |
| `BG_COLOR` | `#f0f4f8` | Page background colour |
