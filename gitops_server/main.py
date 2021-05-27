import hashlib
import hmac
import logging

from fastapi import FastAPI, Header, HTTPException, Request

from . import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gitops")

app = FastAPI()

# Start bg worker and monkeypatches
from gitops_server.logging_config import *  # noqa
from gitops_server.worker import get_worker  # noqa


@app.get("/")
def index():
    return {}


@app.post("/webhook")
async def webhook(request: Request, x_hub_signature: str = Header("")):
    """ Fulfil a git webhook request"""
    digest = get_digest(await request.body())

    validate_signature(x_hub_signature, digest)

    json = await request.json()

    worker = get_worker()

    await worker.enqueue(json)
    return {"enqueued": True}


def get_digest(data: bytes) -> str:
    """Calculate the digest of a webhook body.

    Uses the environment variable `GITHUB_WEBHOOK_KEY` as the secret hash key.
    """
    return hmac.new(
        settings.GITHUB_WEBHOOK_KEY.encode(), data, hashlib.sha1
    ).hexdigest()


def validate_signature(signature: str, digest: str):
    parts = signature.split("=")
    if (
        not len(parts) == 2
        or parts[0] != "sha1"
        or not hmac.compare_digest(parts[1], digest)
    ):
        raise HTTPException(400, "Invalid digest, aborting")
