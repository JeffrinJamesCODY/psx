from __future__ import annotations

import base64
import io
from datetime import datetime, timezone
from typing import Any

import numpy as np
import requests
from astropy.io import fits
from astropy.time import Time
from astroquery.ipac.irsa import Irsa
from PIL import Image

def _python_value(value: Any):
    if value is None:
        return None
    try:
        if np.ma.is_masked(value):
            return None
    except Exception:
        pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value

def _iso_from_mjd(value):
    if value is None:
        return None
    try:
        return Time(float(value), format="mjd").to_value("isot")
    except Exception:
        return str(value)

def _micron(value):
    if value is None:
        return None
    try:
        return float(value) * 1e6
    except Exception:
        return None

def _find_spherex_collection():
    collections = Irsa.list_collections(servicetype="SIA", filter="spherex")
    names =[str(row["collection"]) for row in collections]

    preferred = [
        name for name in names
        if "dr1" in name.lower()
    ] + [
        name for name in names 
        if "qr3" in name.lower()
    ]

    if preferred:
        return preferred[0]

    if names:
        return names[0]
    raise RuntimeError("No SPHEREx SIA Collection was returned by IRSA")

SPHEREX_COLLECTIONS = [
    "spherex_dr1",
    "spherex_qr3",
]


def find_observations(ra: float, dec: float, radius: float, limit: int = 20):
    observations = []
    errors = []

    for collection in SPHEREX_COLLECTIONS:
        try:
            table = Irsa.query_sia(
                pos=(ra, dec, radius),
                collection=collection,
                maxrec=limit,
            )

            for row in table:
                access_url = (
                    _python_value(row["access_url"])
                    if "access_url" in table.colnames
                    else None
                )

                observations.append({
                    "id": (
                        str(_python_value(row["obs_id"]))
                        if "obs_id" in table.colnames else None
                    ),
                    "collection": collection,
                    "access_url": (
                        str(access_url)
                        if access_url and str(access_url).startswith("http")
                        else None
                    ),
                    "product_type": (
                        str(_python_value(row["dataproduct_type"]))
                        if "dataproduct_type" in table.colnames else None
                    ),
                    "subtype": (
                        str(_python_value(row["dataproduct_subtype"]))
                        if "dataproduct_subtype" in table.colnames else None
                    ),
                    "instrument": (
                        str(_python_value(row["instrument_name"]))
                        if "instrument_name" in table.colnames else None
                    ),
                    "observation_time": (
                        _iso_from_mjd(_python_value(row["t_min"]))
                        if "t_min" in table.colnames else None
                    ),
                    "wavelength_min_um": (
                        _micron(_python_value(row["em_min"]))
                        if "em_min" in table.colnames else None
                    ),
                    "wavelength_max_um": (
                        _micron(_python_value(row["em_max"]))
                        if "em_max" in table.colnames else None
                    ),
                })

        except Exception as exc:
            errors.append(f"{collection}: {exc}")

    if errors and not observations:
        raise RuntimeError(
            "All SPHEREx SIA2 collection queries failed: "
            + " | ".join(errors)
        )

    return {
        "query": {
            "ra": ra,
            "dec": dec,
            "radius_deg": radius,
        },
        "collections_searched": SPHEREX_COLLECTIONS,
        "count": min(len(observations), limit),
        "observations": observations[:limit],
        "warnings": errors,
    }

def _build_cutout_url(access_url: str, ra: float, dec: float, size: float) -> str:
    separator = "&" if "?" in access_url else "?"
    return (
        f"{access_url}{separator}"
        f"center={ra:.8f},{dec:.8f}&size={size:.6f}"
    )


def _normalise_to_uint8(data: np.ndarray) -> np.ndarray:
    data = np.asarray(data, dtype=np.float32)

    finite = np.isfinite(data)
    if not finite.any():
        raise ValueError("The FITS image contains no finite pixel values.")

    values = data[finite]

    # Robust display stretch: percentile clipping + asinh.
    lo, hi = np.percentile(values, [1, 99])

    if hi <= lo:
        lo = float(values.min())
        hi = float(values.max())

    clipped = np.clip(data, lo, hi)
    scaled = (clipped - lo) / max(hi - lo, 1e-12)

    # Asinh gives faint structures a little more visibility.
    stretched = np.arcsinh(8 * scaled) / np.arcsinh(8)
    stretched[~finite] = 0

    return np.clip(stretched * 255, 0, 255).astype(np.uint8)


def make_cutout_png(access_url: str, ra: float, dec: float, size: float) -> str:
    if not access_url.startswith("https://irsa.ipac.caltech.edu/ibe/data/spherex/"):
        raise ValueError(
            "The selected observation is not an IRSA on-premises SPHEREx image URL."
        )

    cutout_url = _build_cutout_url(access_url, ra, dec, size)

    response = requests.get(cutout_url, timeout=90)
    response.raise_for_status()

    with fits.open(io.BytesIO(response.content), memmap=False) as hdul:
        data = None

        # Prefer the first 2D science image.
        for hdu in hdul:
            if getattr(hdu, "data", None) is not None:
                arr = np.asarray(hdu.data)
                if arr.ndim == 2:
                    data = arr
                    break
                if arr.ndim == 3:
                    data = arr[0]
                    break

        if data is None:
            raise ValueError("No 2D image plane was found in the SPHEREx cutout.")

        image_array = _normalise_to_uint8(data)

    image = Image.fromarray(image_array, mode="L")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)

    return base64.b64encode(buffer.getvalue()).decode("ascii")