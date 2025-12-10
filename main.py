from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.routes import auth, api_key, wallet

app = FastAPI(
    title="Wallet Service API",
    description="Backend wallet service with Paystack integration",
    version="1.0.0",
    swagger_ui_parameters={
        "persistAuthorization": True
    }
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(api_key.router)
app.include_router(wallet.router)


@app.get("/")
async def root():
    return {
        "message": "Wallet Service API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth/google",
            "api_keys": "/keys/create",
            "wallet": "/wallet/balance"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}