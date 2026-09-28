import asyncio
import secrets
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.models import Provider
from app.openbao import OpenBaoClient


app = FastAPI(title="Integration Aggregator")

openbao = OpenBaoClient()

# In-memory OAuth state
oauth_states = {}

# In-memory async request state
request_status = {}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    return {"status": "ready"}


@app.post("/providers")
async def register_provider(provider: Provider):
    try:
        await openbao.register_provider(
            name=provider.name,
            client_id=provider.client_id,
            client_secret=provider.client_secret,
        )

        return {
            "message": "Provider registered",
            "provider": provider.name,
        }

    except Exception as exc:
        print("REGISTER PROVIDER ERROR:", type(exc).__name__, str(exc))
        raise HTTPException(
            status_code=502,
            detail="Failed to register provider",
        )


@app.post("/providers/{provider}/users/{user}/connect")
async def connect_user(provider: str, user: str):
    state = secrets.token_urlsafe(32)

    oauth_states[state] = {
        "provider": provider,
        "user": user,
    }

    try:
        result = await openbao.create_auth_code_url(
            server=provider,
            redirect_url="http://127.0.0.1:8080/callback",
            scopes=["repo"],
            state=state,
        )

        return {
            "authorization_url": result["data"]["url"],
        }

    except Exception as exc:
        oauth_states.pop(state, None)

        print(
            "CREATE AUTH URL ERROR:",
            type(exc).__name__,
            str(exc),
        )

        raise HTTPException(
            status_code=502,
            detail="Failed to create authorization URL",
        )


@app.get("/callback")
async def callback(code: str, state: str):
    oauth_state = oauth_states.pop(state, None)

    if oauth_state is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state",
        )

    provider = oauth_state["provider"]
    user = oauth_state["user"]

    try:
        await openbao.exchange_code(
            name=user,
            server=provider,
            code=code,
            redirect_url="http://127.0.0.1:8080/callback",
        )

        return {
            "message": "OAuth connection successful",
            "provider": provider,
            "user": user,
        }

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Failed to exchange authorization code",
        )


async def retrieve_token(
    request_id: str,
    provider: str,
    user: str,
):
    try:
        result = await openbao.get_credential(
            name=user,
            server=provider,
        )

        credential = result.get("data", {})

        request_status[request_id] = {
            "status": "completed",
            "result": {
                "access_token": credential.get("access_token"),
                "expire_time": credential.get("expire_time"),
                "server": credential.get("server"),
                "type": credential.get("type"),
            },
        }

    except Exception:
        request_status[request_id] = {
            "status": "failed",
            "error": "Failed to retrieve credential",
        }


@app.get("/requests/{request_id}")
async def get_request_status(request_id: str):
    request = request_status.get(request_id)

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Request not found",
        )

    return {
        "request_id": request_id,
        **request,
    }


@app.get("/{provider}/{user}", status_code=202)
async def get_token(provider: str, user: str):
    request_id = str(uuid.uuid4())

    request_status[request_id] = {
        "status": "pending",
    }

    asyncio.create_task(
        retrieve_token(
            request_id=request_id,
            provider=provider,
            user=user,
        )
    )

    return JSONResponse(
        status_code=202,
        content={
            "request_id": request_id,
            "status": "pending",
        },
        headers={
            "Location": f"/requests/{request_id}",
        },
    )