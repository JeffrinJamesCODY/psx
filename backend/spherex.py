from __future__ import annotations

import base64
import io
from functools import lru_cache
from typing import Any

import numpy as np
import requests
from astropy.io import fits
from astropy.coordinates import SkyCoord
from astropy_healpix import HEALPix
from PIL import Image


# Official SPHEREx DR1 All-Sky Cube location on IRSA.
IRSA_BASE = (
    "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/"
    "hips5_cube/hips_20261026/Norder5"
)


# DR1 All-Sky Cube uses HEALPix order 5.
# Nside = 2^order = 32.
HPX = HEALPix(
    nside=32,
    order="nested",
    frame="icrs",
)


def _normalise_to_uint8(data: np.ndarray) -> np.ndarray:
    """
    Convert scientific flfeoating-point image data
    into an 8-bit image suitable for a browser
    """

    data = np.asarray(data, dtype=np.float32)

    finite = np.isfinite(data)

    if not finite.any():
        raise ValueError(
            "The selected SPHEREx channel contains no valid pixels."
        )

    values = data[finite]

# Ignore extreme outliers.
    lo, hi = np.percentile(values, [1, 99])

    if hi <= lo:
        lo = float(values.min())
        hi = float(values.max())

    clipped = np.clip(data, lo, hi)

    scaled = (clipped - lo) / max(hi - lo, 1e-12)

 # Asinh stretch makes faint structures easier to see.
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


def _ra_dec_to_healpix(
    ra: float,
    dec: float,
) -> int:
    """
Convert an ICRS RA/Dec position into
    the SPHEREx HEALPix order-5 pixel
    """

    sky = SkyCoord(
        ra=ra,
        dec=dec,
        unit="deg",
        frame="icrs",
    )

    pixel = HPX.skycoord_to_healpix(sky)

    return int(pixel)


def _cube_url(pixel: int) -> str:
    """
    buildef the IRSA FITS URL for a HEALPix pixel
IRSA stores the pixels in directories based
    on pixel number.
    """

    directory = pixel // 10000

    return (
        f"{IRSA_BASE}/Dir{directory}/"
        f"Npix{pixel}_cube.fits"
    )


@lru_cache(maxsize=4)
def _download_cube(pixel: int) -> bytes:
    """
    download a cube from IRSA
    a small cache prevents repeatedly downloading
    the same FITS file when the user changes channels
    """

    url = _cube_url(pixel)

    response = requests.get(
        url,
        timeout=120,
    )

    response.raise_for_status()

    return response.content


def _extract_channel(
    fits_bytes: bytes,
    channel: int,
) -> tuple[np.ndarray, float]:
    """
    Extracts one spectral channel from
    the SPHEREx 102 channel cube and returns the image data and wavelength
    """

    with fits.open(
        io.BytesIO(fits_bytes),
        memmap=False,
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

        channel_image = np.asarray(
            image[channel],
            dtype=np.float32,
        )

        wavelength = None

    # Try to obtain the wavelength from the
        # SPECTRAL_CHANNELS table
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

# If the table has a different structure
# return the channel number instead
        if wavelength is None:
            wavelength = float(channel)

        return channel_image, wavelength


def make_cube_channel_png(
    ra: float,
    dec: float,
    channel: int = 0,
) -> dict[str, Any]:

    if not 0 <= ra < 360:
        raise ValueError(
            "RA must be between 0 and 360 degrees."
        )

    if not -90 <= dec <= 90:
        raise ValueError(
            "Dec must be between -90 and +90 degrees."
        )

    if not 0 <= channel <= 101:
        raise ValueError(
            "SPHEREx channel must be between 0 and 101."
        )

    pixel = _ra_dec_to_healpix(
        ra,
        dec,
    )

    fits_bytes = _download_cube(pixel)

    image_data, wavelength = _extract_channel(
        fits_bytes,
        channel,
    )

    image_array = _normalise_to_uint8(
        image_data
    )

    image = Image.fromarray(
        image_array,
        mode="L",
    )

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