# Backend

This directory will contain the Python backend used by both the FastAPI server and Celery workers.

The code is divided by responsibility rather than by framework. HTTP and Celery are delivery mechanisms around shared application use cases and domain rules.

