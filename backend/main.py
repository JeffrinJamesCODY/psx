from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from spherex import make_cube_channel_png


app = FastAPI(
    title="PSX Stellar SPHEREx API",
    description=(
        "Backend for the PSX Stellar SPHEREx "
        "exploration interface."
    ),
    version="0.2.0",
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
def health():
    return {
        "status": "ok",
        "service": "psx-api",
    }


@app.get("/api/spherex/cube")
def spherex_cube(
    ra: float = Query(
        ...,
        ge=0,
        lt=360,
    ),
    dec: float = Query(
        ...,
        ge=-90,
        le=90,
    ),
    channel: int = Query(
        0,
        ge=0,
        le=101,
    ),
):
    """
    Retrieve one spectral channel from
    the SPHEREx DR1 All-Sky Cube.
    """

    try:

        return make_cube_channel_png(
            ra=ra,
            dec=dec,
            channel=channel,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "SPHEREx cube request failed: "
                f"{exc}"
            ),
        ) from exc