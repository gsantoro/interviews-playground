from fastapi import FastAPI

from app.routers import health, hello

app = FastAPI(title="one-signal")

app.include_router(health.router)
app.include_router(hello.router)
