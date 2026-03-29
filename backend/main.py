from fastapi import FastAPI


app = FastAPI(title="ClaimMate Backend", version="0.1.0")


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

