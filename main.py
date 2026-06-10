from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from extraction import router as extraction_router
from data import router as data_router
from prediction import router as prediction_router

app = FastAPI(
    title="Match Predictor API",
    description="Application de prédiction de matchs basée sur les cotes.",
    version="1.0.0"
)

# CORS - autoriser le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure les routers
app.include_router(extraction_router)
app.include_router(data_router)
app.include_router(prediction_router)

# Servir le frontend statique
frontend_path = Path(__file__).parent / "frontend"
if not frontend_path.exists():
    frontend_path = Path(__file__).parent

if (frontend_path / "index.html").exists() and (frontend_path / "predict.html").exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(frontend_path / "index.html"))

    @app.get("/predict")
    async def serve_predict():
        return FileResponse(str(frontend_path / "predict.html"))

    @app.get("/results")
    async def serve_results():
        return FileResponse(str(frontend_path / "results.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "message": "Match Predictor API is running."}
