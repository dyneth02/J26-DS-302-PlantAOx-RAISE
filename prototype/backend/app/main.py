from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import c1, c2, c3, c4, meta


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the live-computation models/data once at startup (not per-request) so the
    # 3 new live endpoints (C1 retrieval, C2 RNIS, C3 perturbation) stay demo-responsive.
    from app.live import c1_retrieval, c2_rnis, c3_perturbation

    c1_retrieval.load_c1_state()
    c2_rnis.load_c2_state()
    c3_perturbation.load_c3_state()
    yield


app = FastAPI(
    title="PlantAOx-RAISE Prototype API",
    description="Backend API for the PlantAOx-RAISE proposal prototype",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta.router, prefix="/api", tags=["Project"])
app.include_router(c1.router, prefix="/api/c1", tags=["C1 AOP-ProCon"])
app.include_router(c2.router, prefix="/api/c2", tags=["C2 PU-AOP"])
app.include_router(c3.router, prefix="/api/c3", tags=["C3 AOP-BCS"])
app.include_router(c4.router, prefix="/api/c4", tags=["C4 PlantAOP-Screen"])


@app.get("/")
def root():
    return {"project": "PlantAOx-RAISE", "prototype": True, "status": "API running"}
