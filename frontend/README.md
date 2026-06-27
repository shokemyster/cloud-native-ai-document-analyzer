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

## Routes

- `/upload` — select a PDF or CSV document.
- `/history` — view the processing-history state.
- `/jobs/:jobId` — view the identity and eventual state of one analysis job.

The UI is intentionally not connected to a backend yet. It does not simulate uploads or job results.

`src/` contains authored source code. `public/` is reserved for static files copied unchanged into the frontend build. Generated dependencies and build output are excluded from version control.
