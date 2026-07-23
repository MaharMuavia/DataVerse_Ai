<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://ai.google.dev/static/site-assets/images/share-ais-513315318.png" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/dde1491a-c4a7-43dc-8e03-478f80e04638

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Run the app and backend together:
   `npm run dev`

`npm run dev` starts FastAPI on `http://127.0.0.1:8000`, proxies API requests through the frontend, and starts Next.js at `https://127.0.0.1:3000` with a local development certificate.

The ignored `frontend/certificates/localhost.pem` and `localhost-key.pem` files are development-only. Generate them with OpenSSL if they are missing; never use them in production.

Manual backend command:
```powershell
cd dataverse_backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If port `8000` is already in use, stop the old backend before running `npm run dev` so the app starts with the latest API code. To intentionally reuse a running backend, set `DATAVERSE_REUSE_BACKEND=1`.
