# Frontend

React and TypeScript single-page application built with Vite.

## Prerequisites

- Node.js 22.12 or newer
- npm 11 or newer

## Commands

```bash
npm install
npm run dev
npm run lint
npm run build
npm run preview
```

During development, Vite proxies `/api` requests to FastAPI at
`http://127.0.0.1:8000`. Start the backend stack before testing uploads.

## Routes

- `/upload` — select a PDF or CSV document.
- `/history` — view the processing-history state.
- `/jobs/:jobId` — view the identity and eventual state of one analysis job.

The upload page submits PDF and CSV files to the backend and redirects to the
durable processing-job status page. Active jobs are polled every two seconds
until they reach a terminal state.

`src/` contains authored source code. `public/` is reserved for static files copied unchanged into the frontend build. Generated dependencies and build output are excluded from version control.
