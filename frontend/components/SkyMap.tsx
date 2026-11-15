"use client";

import { useEffect, useRef } from "react";

type SkyMapProps = {
  onSkyClick: (ra: number, dec: number) => void;
};

export default function SkyMap({ onSkyClick }: SkyMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const onSkyClickRef = useRef(onSkyClick);

  onSkyClickRef.current = onSkyClick;

  useEffect(() => {
    let aladin: any;
    let disposed = false;

    async function initialiseAladin() {
      if (!containerRef.current) return;

      // Load Aladin only in the browser
      const { default: A } = await import("aladin-lite");

      if (disposed || !containerRef.current) return;

      await A.init;

      if (disposed || !containerRef.current) return;

      aladin = A.aladin(containerRef.current, {
        target: "180 0",
        fov: 70,
        cooFrame: "ICRS",
        projection: "AIT",
        showCooGrid: true,
        showCooGridControl: true,
        showZoomControl: true,
        showFullscreenControl: true,
        showLayersControl: true,
        showFrame: true,
        showFov: true,
        showCooLocation: true,
        showSimbadPointerControl: false,
      });

      // DSS Color background
      const survey = A.imageHiPS(
        "https://stpubdata.s3.us-east-1.amazonaws.com/mast/skybackgrounds/DSSColor"
      );

      aladin.setImageSurvey(survey);

      aladin.on(
        "click",
        (event: { ra?: number; dec?: number }) => {
          if (
            typeof event?.ra === "number" &&
            typeof event?.dec === "number"
          ) {
            onSkyClickRef.current(event.ra, event.dec);
          }
        }
      );
    }

    initialiseAladin();

    return () => {
      disposed = true;

      if (containerRef.current) {
        containerRef.current.replaceChildren();
      }
    };
  }, []);

  return <div ref={containerRef} className="sky-map" />;
}