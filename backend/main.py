from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from spherex import find_observations, make_cutout_png

app = FastAPI(
    title="PSX Stellar SphereX API",
    description="Backend for the PSX Stellar SPHEREx exploration interface.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def psxhealth():
    return {"status": "ok", "service": "psx-api"}

@app.get("/api/psxhealth")
def observations(
    ra: float = Query(..., ge=0, lt=360),
    dec: float = Query(..., ge=-90, le=90),
    radius: float = Query(0.1, gt =0, le=2),
    limit: int = Query(20, ge=1, le=100),
):
    try:
        return find_observations(ra, dec, radius, limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"SPHEREx/IRSA query failed: {exc}") from exc


@app.get("/api/spherex/cutout")
def cutout(
    url: str = Query(..., min_length=10),
    ra: float = Query(..., ge=0, lt=360),
    dec: float = Query(..., ge=-90, le=90),
    size: float = Query(0.1, gt=0, le=1),
):
    try:
        png = make_cutout_png(url, ra, dec, size)
        return {
            "image": f"data:image/png;base64,{png}",
            "ra": ra,
            "dec": dec,
            "size_deg": size,
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"SPHEREx cutout failed: {exc}") from exc

