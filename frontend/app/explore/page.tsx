"use client";

import { useState } from "react";
import SkyMap from "../../components/SkyMap";
import "./explore.css";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";

export default function ExplorePage() {
  const [ra, setRa] = useState<number | null>(null);
  const [dec, setDec] = useState<number | null>(null);

  const [channel, setChannel] = useState(0);

  const [image, setImage] = useState<string | null>(null);
  const [wavelength, setWavelength] =
    useState<number | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleSkyClick(
    clickedRa: number,
    clickedDec: number
  ) {
    setRa(clickedRa);
    setDec(clickedDec);

    setImage(null);
    setWavelength(null);
    setError(null);
  }

  async function loadSpherexChannel(
    selectedChannel = channel
  ) {
    if (ra === null || dec === null) {
      setError("Click a position on the sky first.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        ra: String(ra),
        dec: String(dec),
        channel: String(selectedChannel),
      });

      const response = await fetch(
        `${API_BASE}/api/spherex/cube?${params.toString()}`
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ?? "SPHEREx request failed."
        );
      }

      setImage(body.image);
      setWavelength(body.wavelength_um);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "SPHEREx request failed."
      );
    } finally {
      setLoading(false);
    }
  }

  function handleChannelChange(
    event: React.ChangeEvent<HTMLInputElement>
  ) {
    const newChannel = Number(event.target.value);

    setChannel(newChannel);

    if (ra !== null && dec !== null) {
      loadSpherexChannel(newChannel);
    }
  }

  return (
    <main className="explore-page">

      <header className="explore-header">
        <div>
          <div className="brand">
            PSX
          </div>

          <h1>
            PSX Explorer
          </h1>

          <p>
            Explore the infrared sky using SPHEREx
            spectral data.
          </p>
        </div>

        <div className="status">
          <span className="status-dot" />
          PSX Data Explorer
        </div>
      </header>


      <div className="explore-layout">

        {/* SKY MAP */}

        <section className="map-card">

          <div className="card-header">
            <div>
              <h2>Sky Map</h2>

              <p>
                Click on the map to select a position
              </p>
            </div>
          </div>

          <div className="map-container">
            <SkyMap
              onSkyClick={handleSkyClick}
            />
          </div>

        </section>


        {/* CONTROLS */}

        <aside className="control-card">

          <h2>Observation</h2>

          <p className="section-description">
            Select a location and explore its
            SPHEREx spectral data.
          </p>


          <div className="coordinates">

            <div className="coordinate">
              <span>Right Ascension</span>

              <strong>
                {ra !== null
                  ? `${ra.toFixed(6)}°`
                  : "—"}
              </strong>
            </div>


            <div className="coordinate">
              <span>Declination</span>

              <strong>
                {dec !== null
                  ? `${dec.toFixed(6)}°`
                  : "—"}
              </strong>
            </div>

          </div>


          <button
            className="load-button"
            onClick={() =>
              loadSpherexChannel()
            }
            disabled={
              ra === null ||
              dec === null ||
              loading
            }
          >
            {loading
              ? "Loading SPHEREx..."
              : "Load SPHEREx Data"}
          </button>


          <div className="channel-section">

            <div className="channel-header">

              <span>
                Spectral Channel
              </span>

              <strong>
                {channel}
              </strong>

            </div>


            <input
              type="range"
              min="0"
              max="101"
              value={channel}
              onChange={
                handleChannelChange
              }
            />


            <div className="range-labels">
              <span>0</span>
              <span>101</span>
            </div>

          </div>


          {wavelength !== null && (

            <div className="wavelength">

              <span>
                Wavelength
              </span>

              <strong>
                {wavelength.toFixed(3)}
                <small> μm</small>
              </strong>

            </div>

          )}


          {error && (

            <div className="error">
              {error}
            </div>

          )}

        </aside>

      </div>


      {/* IMAGE RESULT */}

      {image && (

        <section className="result-card">

          <div className="result-header">

            <div>
              <h2>
                SPHEREx Spectral Image
              </h2>

              <p>
                Channel {channel}

                {wavelength !== null &&
                  ` • ${wavelength.toFixed(3)} μm`}
              </p>
            </div>

          </div>


          <div className="image-wrapper">

            <img
              src={image}
              alt={`SPHEREx spectral channel ${channel}`}
            />

          </div>

        </section>

      )}

    </main>
  );
}