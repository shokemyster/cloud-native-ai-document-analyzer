# Frontend source

- `app/` owns application bootstrap, routing, and top-level providers.
- `components/` contains reusable presentation components that are not specific to one business feature.
- `features/` groups UI and state by user capability, such as uploads or analysis history.
- `lib/` contains technical utilities and external-service clients.
- `types/` contains shared TypeScript types that genuinely cross feature boundaries.

Feature-specific code should remain in its feature directory instead of being moved prematurely into global folders.

