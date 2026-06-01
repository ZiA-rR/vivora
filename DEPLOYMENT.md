# Vivora Deployment

This app deploys cleanly as two services:

- FastAPI backend from the repo root.
- React/Vite frontend from `frontend/`.

Do not commit `.env`. Add secrets only in the hosting dashboards.

## Backend: Render

1. Push this repository to GitHub.
2. In Render, create a new Web Service from the repo.
3. Use the Docker environment. Render will read `render.yaml`.
4. Add these environment variables:

```text
GOOGLE_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
VIVORA_LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash-lite
GROQ_MODEL=llama-3.1-8b-instant
FRONTEND_ORIGIN=https://your-frontend-domain.vercel.app
```

5. After deploy, open:

```text
https://your-render-service.onrender.com/api/health
```

You should see `{"status":"ok", ...}`.

## Frontend: Vercel

1. Create a new Vercel project from the same GitHub repo.
2. Set the Root Directory to `frontend`.
3. Use:

```text
Build Command: npm run build
Output Directory: dist
```

4. Add this environment variable:

```text
VITE_API_BASE=https://your-render-service.onrender.com
```

5. Deploy the frontend.
6. Copy the Vercel domain back into Render as `FRONTEND_ORIGIN`.

## Local Commands

Backend:

```powershell
& "L:\dev-venvs\vivamate-ai\Scripts\Activate.ps1"
uvicorn main:app --reload --port 8000
```

Frontend:

```powershell
npm run dev --prefix frontend
```

If you keep developing from `L:\vivora-frontend`, copy the final frontend files back into `frontend/` before pushing.
