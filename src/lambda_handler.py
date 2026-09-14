"""
AWS Lambda entrypoint.

Mangum translates the Lambda Function URL event into an ASGI request, so the
same FastAPI app serves both `uvicorn` locally and Lambda in the cloud.
"""

from __future__ import annotations

from mangum import Mangum

from api import app

handler = Mangum(app, lifespan="on")
