from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import try_on, accounts, brands, analytics, loyalty, vault, fit

app = FastAPI(title="Sway Lane Studio API", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(try_on.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(brands.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(loyalty.router, prefix="/api")
app.include_router(vault.router, prefix="/api")
app.include_router(fit.router, prefix="/api")
app.include_router(fit.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.1.0"}
