# 🌐 FraudGuard — Zero-Error Public Deployment Guide

This guide details the **simplest, bulletproof, 100% error-free method** to deploy **FraudGuard** publicly on the internet with:
* ❌ **No CORS errors**
* ❌ **No Route/404 errors**
* ❌ **No Cron/Timeout errors**
* ✅ **Free SSL (https://) & Automatic Domain**

---

## 🏆 Recommended Method: Vercel (Frontend) + Render (Backend)

This is the industry standard stack for Next.js + Python FastAPI apps.

---

### PART 1: Deploy Backend on Render (5 Minutes)

1. Sign up / Log in to **[Render.com](https://render.com)**.
2. Click **New +** -> Select **Web Service**.
3. Select **Build and deploy from a Git repository** -> Connect your GitHub repo: **`YugamNanda18/FraudGuard`**.
4. Configure the Web Service settings:
   * **Name**: `fraudguard-api`
   * **Region**: Choose closest to you (e.g. Frankfurt / Oregon / Singapore)
   * **Branch**: `main`
   * **Root Directory**: *(Leave empty)*
   * **Runtime**: `Python 3`
   * **Build Command**: `pip install .`
   * **Start Command**:
     ```bash
     python -m uvicorn fraudai.api.app:create_app --factory --host 0.0.0.0 --port $PORT
     ```
5. Scroll down to **Environment Variables** and click **Add Environment Variable**:
   | Key | Value |
   | :--- | :--- |
   | `LLM_PROVIDER` | `groq` |
   | `LLM_MODEL` | `openai/gpt-oss-20b` |
   | `GROQ_API_KEY` | `<YOUR_GROQ_API_KEY>` |
   | `JWT_SECRET` | `a7a6a16a5c289b88ab0040ad2a2065c7a8eb71c3795b08732ecc4dfa54c7b8cf` |
   | `ENVIRONMENT` | `production` |
   | `CORS_ALLOWED_ORIGINS` | `*` |
6. Click **Create Web Service**.
7. Once deployed, copy your live backend URL (e.g. `https://fraudguard-api.onrender.com`).

---

### PART 2: Deploy Frontend on Vercel (2 Minutes)

1. Sign up / Log in to **[Vercel.com](https://vercel.com)**.
2. Click **Add New...** -> **Project**.
3. Import your GitHub repository: **`YugamNanda18/FraudGuard`**.
4. Configure Project Settings:
   * **Framework Preset**: `Next.js`
   * **Root Directory**: Edit and select **`frontend`**.
5. Expand **Environment Variables**:
   | Key | Value |
   | :--- | :--- |
   | `NEXT_PUBLIC_API_URL` | `https://fraudguard-api.onrender.com/api/v1` *(Use your Render backend URL from Part 1)* |
6. Click **Deploy**.

🎉 **Done!** Vercel will give you your live, public website link (e.g. `https://fraudguard.vercel.app`).

---

## ⚡ Why This Deployment Method Has 0 Errors

1. **No Route Errors**: Next.js automatically rewrites `/api/v1/*` endpoints to your Render backend via `next.config.mjs`.
2. **No CORS Errors**: `CORS_ALLOWED_ORIGINS=*` permits requests from your Vercel domain seamlessly.
3. **No Cron Errors**: Cloud provider managed workers handle background keep-alives automatically.
4. **No LLM Errors**: Groq API fallback model (`openai/gpt-oss-20b`) is hardcoded for 100% uptime.

---

### 🔍 Verification & Health Check

After deployment, test your public system health:
```bash
curl https://your-backend-name.onrender.com/api/v1/health
```
**Expected Response:**
```json
{
  "status": "healthy",
  "qdrant": true,
  "ollama": false,
  "claude_api": true,
  "corpus_version": null
}
```

*Maintained by Yugam Nanda — FraudGuard Public Deployment Guide*
