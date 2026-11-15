import Link from "next/link";

export default function Home() {
  return (
    <main className="landing">
      <nav className="nav">
        <div className="brand">
          <span>ProjectPSX</span>
        </div>

        <Link className="nav-link" href="/explore">
          Explore
        </Link>
      </nav>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">NASA SPACE APPS · SPHEREx</p>

          <h1>
            Explore the sky.
            <br />
            Find what changed.
          </h1>

          <p className="hero-text">
            ProjectPSX is a scientific exploration interface for
            searching public SPHEREx observations, comparing regions
            of the sky, and investigating unusual changes.
          </p>

          <div className="hero-actions">
            <Link className="primary-button" href="/explore">
              Explore the sky →
            </Link>

            <a
              className="secondary-button"
              href="https://irsa.ipac.caltech.edu/Missions/spherex.html"
              target="_blank"
              rel="noreferrer"
            >
              SPHEREx data ↗
            </a>
          </div>
        </div>

        <div className="hero-orbit">
          <div className="orbit orbit-a" />
          <div className="orbit orbit-b" />
          <div className="planet" />
          <div className="planet-label">SPHEREx</div>
        </div>
      </section>

      <section className="feature-grid">
        <article>
          <span>01</span>
          <h2>Navigate</h2>
          <p>
            Pick any region of the sky using an interactive
            astronomical map.
          </p>
        </article>

        <article>
          <span>02</span>
          <h2>Query</h2>
          <p>
            Find relevant SPHEREx observations through NASA/IPAC IRSA.
          </p>
        </article>

        <article>
          <span>03</span>
          <h2>Investigate</h2>
          <p>
            Inspect images and compare observations for potentially
            interesting changes.
          </p>
        </article>
      </section>
    </main>
  );
}