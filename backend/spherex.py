
from __future__ import annotations

import base64
import io
import os
import threading
from pathlib import Path
from typing import Any

import numpy as np
import requests
from astropy.io import fits
from astropy.coordinates import SkyCoord
from astropy_healpix import HEALPix
from PIL import Image


# Official SPHEREx DR1 All-Sky Cube location.
IRSA_BASE = (
    "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/"
    "hips5_cube/hips_20261026/Norder5"
)

# HEALPix order 5.
HPX = HEALPix(
    nside=32,
    order="nested",
    frame="icrs",
)

# Store downloaded cubes locally rather than in RAM.
CACHE_DIR = Path(__file__).resolve().parent / "spherex_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Prevent simultaneous downloads of the same pixel.
_locks_guard = threading.Lock()
_pixel_locks: dict[int, threading.Lock] = {}


def _get_pixel_lock(pixel: int) -> threading.Lock:
    with _locks_guard:
        if pixel not in _pixel_locks:
            _pixel_locks[pixel] = threading.Lock()

        return _pixel_locks[pixel]


def _normalise_to_uint8(data: np.ndarray) -> np.ndarray:
    data = np.asarray(data, dtype=np.float32)

    finite = np.isfinite(data)

    if not finite.any():
        raise ValueError(
            "The selected SPHEREx channel contains no valid pixels."
        )

    values = data[finite]

    lo, hi = np.percentile(values, [1, 99])

    if hi <= lo:
        lo = float(values.min())
        hi = float(values.max())

    clipped = np.clip(data, lo, hi)

    scaled = (clipped - lo) / max(hi - lo, 1e-12)

    stretched = (
        np.arcsinh(8 * scaled)
        / np.arcsinh(8)
    )

    stretched[~finite] = 0

    return np.clip(
        stretched * 255,
        0,
        255,
    ).astype(np.uint8)


def _ra_dec_to_healpix(ra: float, dec: float) -> int:
    sky = SkyCoord(
        ra=ra,
        dec=dec,
        unit="deg",
        frame="icrs",
    )

    return int(HPX.skycoord_to_healpix(sky))


def _cube_url(pixel: int) -> str:
    directory = (pixel // 10000) * 10000

    return (
        f"{IRSA_BASE}/Dir{directory}/"
        f"Npix{pixel}_cube.fits"
    )


def _download_cube(pixel: int) -> Path:
    """
    Download a cube once and save it to disk.
    Later requests reuse the saved FITS file.
    """

    cube_path = CACHE_DIR / f"Npix{pixel}_cube.fits"

    # Only one request per pixel can download at a time.
    with _get_pixel_lock(pixel):

        if cube_path.exists() and cube_path.stat().st_size > 0:
            print(
                f"[SPHEREx] Using disk cache: {cube_path}",
                flush=True,
            )
            return cube_path

        url = _cube_url(pixel)

        temporary_path = CACHE_DIR / f"Npix{pixel}_cube.part"

        print(
            f"[SPHEREx] Downloading cube for pixel {pixel}",
            flush=True,
        )
        print(f"[SPHEREx] URL: {url}", flush=True)

        try:
            downloaded = 0

            with requests.get(
                url,
                stream=True,
                timeout=(20, 300),
            ) as response:

                response.raise_for_status()

                expected_size = int(
                    response.headers.get("content-length", 0)
                )

                print(
                    f"[SPHEREx] Expected size: "
                    f"{expected_size / (1024 * 1024):.1f} MB",
                    flush=True,
                )

                with open(temporary_path, "wb") as file:

                    for chunk in response.iter_content(
                        chunk_size=8 * 1024 * 1024
                    ):

                        if not chunk:
                            continue

                        file.write(chunk)
                        downloaded += len(chunk)

                        print(
                            f"[SPHEREx] Downloaded "
                            f"{downloaded / (1024 * 1024):.1f} MB",
                            flush=True,
                        )

            if downloaded == 0:
                raise ValueError(
                    "The SPHEREx server returned an empty cube."
                )

            if expected_size and downloaded != expected_size:
                raise ValueError(
                    f"Incomplete cube download: "
                    f"{downloaded} of {expected_size} bytes."
                )

            # Atomic rename: incomplete downloads never become cache files.
            os.replace(temporary_path, cube_path)

            print(
                f"[SPHEREx] Cube saved: {cube_path}",
                flush=True,
            )

            return cube_path

        except Exception:
            if temporary_path.exists():
                temporary_path.unlink()

            raise


def _extract_channel(
    cube_path: Path,
    channel: int,
) -> tuple[np.ndarray, float]:

    with fits.open(
        cube_path,
        mode="readonly",
        memmap=True,
    ) as hdul:

        if "IMAGE" not in hdul:
            raise ValueError(
                "SPHEREx cube does not contain an IMAGE extension."
            )

        image = hdul["IMAGE"].data

        if image is None:
            raise ValueError(
                "SPHEREx IMAGE extension contains no data."
            )

        if image.ndim != 3:
            raise ValueError(
                f"Unexpected SPHEREx IMAGE dimensions: {image.shape}"
            )

        number_of_channels = image.shape[0]

        if not 0 <= channel < number_of_channels:
            raise ValueError(
                f"Channel must be between 0 and "
                f"{number_of_channels - 1}."
            )

        # Copy the selected channel before closing the FITS file.
        channel_image = np.asarray(
            image[channel],
            dtype=np.float32,
        ).copy()

        wavelength = None

        if "SPECTRAL_CHANNELS" in hdul:

            table = hdul["SPECTRAL_CHANNELS"].data

            if table is not None:

                possible_columns = [
                    "WAVELENGTH",
                    "WAVELENGTH_CENTER",
                    "WAVELENGTH_CEN",
                    "LAMBDA",
                ]

                column_name = next(
                    (
                        name
                        for name in possible_columns
                        if name in table.names
                    ),
                    None,
                )

                if column_name is not None:
                    wavelength = float(
                        table[column_name][channel]
                    )

        if wavelength is None:
            wavelength = float(channel)

        return channel_image, wavelength


def make_cube_channel_png(
    ra: float,
    dec: float,
    channel: int = 0,
) -> dict[str, Any]:

    if not 0 <= ra < 360:
        raise ValueError("RA must be between 0 and 360 degrees.")

    if not -90 <= dec <= 90:
        raise ValueError("Dec must be between -90 and +90 degrees.")

    if not 0 <= channel <= 101:
        raise ValueError("Channel must be between 0 and 101.")

    pixel = _ra_dec_to_healpix(ra, dec)

    print(
        f"[SPHEREx] RA={ra}, Dec={dec}, "
        f"Channel={channel}, Pixel={pixel}",
        flush=True,
    )

    # Download once, then reuse the local file for every channel.
    cube_path = _download_cube(pixel)

    print(
        f"[SPHEREx] Extracting channel {channel}",
        flush=True,
    )

    image_data, wavelength = _extract_channel(
        cube_path,
        channel,
    )

    print(
        "[SPHEREx] Channel extracted successfully",
        flush=True,
    )

    image_array = _normalise_to_uint8(image_data)

    image = Image.fromarray(image_array, mode="L")

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG",
        optimize=True,
    )

    png = base64.b64encode(
        buffer.getvalue()
    ).decode("ascii")

    return {
        "image": f"data:image/png;base64,{png}",
        "ra": ra,
        "dec": dec,
        "healpix_order": 5,
        "healpix_pixel": pixel,
        "channel": channel,
        "wavelength_um": wavelength,
    }
