import { useEffect, useRef, useState } from "react";

export interface LocationPoint {
  lat: number;
  lng: number;
}

interface LocationMapPickerProps {
  selectedPoint: LocationPoint | null;
  onSelectPoint: (point: LocationPoint) => void;
}

interface GoogleMapMouseEvent {
  latLng?: {
    lat: () => number;
    lng: () => number;
  };
}

interface GoogleMap {
  addListener: (eventName: "click", handler: (event: GoogleMapMouseEvent) => void) => void;
  panTo: (point: LocationPoint) => void;
  setCenter: (point: LocationPoint) => void;
  setZoom: (zoom: number) => void;
}

interface GoogleMarker {
  setMap: (map: GoogleMap | null) => void;
  setPosition: (position: LocationPoint) => void;
}

interface GoogleMapsApi {
  Map: new (
    element: HTMLElement,
    options: {
      center: LocationPoint;
      zoom: number;
      mapTypeControl: boolean;
      streetViewControl: boolean;
      fullscreenControl: boolean;
      clickableIcons: boolean;
    },
  ) => GoogleMap;
  Marker: new (options: {
    position: LocationPoint;
    map: GoogleMap;
    draggable: boolean;
  }) => GoogleMarker;
}

type GoogleMapsWindow = Window & {
  google?: {
    maps?: GoogleMapsApi;
  };
};

const DEFAULT_CENTER: LocationPoint = { lat: -34.6037, lng: -58.3816 };
const DEFAULT_ZOOM = 13;
const GOOGLE_MAPS_SCRIPT_ID = "google-maps-js-api";

let googleMapsScriptPromise: Promise<void> | null = null;

function loadGoogleMapsScript(apiKey: string): Promise<void> {
  if (!apiKey) {
    return Promise.reject(new Error("Falta configurar VITE_GOOGLE_MAPS_API_KEY."));
  }

  const mapsWindow = window as GoogleMapsWindow;

  if (mapsWindow.google?.maps) {
    return Promise.resolve();
  }

  if (googleMapsScriptPromise) {
    return googleMapsScriptPromise;
  }

  googleMapsScriptPromise = new Promise<void>((resolve, reject) => {
    const existingScript = document.getElementById(GOOGLE_MAPS_SCRIPT_ID) as HTMLScriptElement | null;

    if (existingScript) {
      existingScript.addEventListener("load", () => resolve(), { once: true });
      existingScript.addEventListener("error", () => reject(new Error("No pudimos cargar Google Maps.")), {
        once: true,
      });
      return;
    }

    const script = document.createElement("script");
    script.id = GOOGLE_MAPS_SCRIPT_ID;
    script.async = true;
    script.defer = true;
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&language=es&region=AR`;

    script.onload = () => resolve();
    script.onerror = () => reject(new Error("No pudimos cargar Google Maps."));

    document.head.appendChild(script);
  });

  return googleMapsScriptPromise;
}

export function LocationMapPicker({ selectedPoint, onSelectPoint }: LocationMapPickerProps) {
  const [loadError, setLoadError] = useState<string | null>(null);
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<GoogleMap | null>(null);
  const markerRef = useRef<GoogleMarker | null>(null);
  const onSelectPointRef = useRef(onSelectPoint);

  useEffect(() => {
    onSelectPointRef.current = onSelectPoint;
  }, [onSelectPoint]);

  useEffect(() => {
    const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY?.trim() ?? "";

    let isMounted = true;

    void loadGoogleMapsScript(apiKey)
      .then(() => {
        if (!isMounted || !mapContainerRef.current) {
          return;
        }

        const mapsWindow = window as GoogleMapsWindow;

        const maps = mapsWindow.google?.maps;
        if (!maps) {
          setLoadError("No pudimos inicializar Google Maps.");
          return;
        }

        if (!mapRef.current) {
          mapRef.current = new maps.Map(mapContainerRef.current, {
            center: DEFAULT_CENTER,
            zoom: DEFAULT_ZOOM,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: false,
            clickableIcons: false,
          });

          mapRef.current.addListener("click", (event: GoogleMapMouseEvent) => {
            const lat = event.latLng?.lat?.();
            const lng = event.latLng?.lng?.();

            if (typeof lat !== "number" || typeof lng !== "number") {
              return;
            }

            onSelectPointRef.current({ lat, lng });
          });
        }

        setLoadError(null);
      })
      .catch((error: unknown) => {
        if (!isMounted) {
          return;
        }

        const message = error instanceof Error
          ? error.message
          : "No pudimos cargar Google Maps.";
        setLoadError(message);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const mapsWindow = window as GoogleMapsWindow;

    const maps = mapsWindow.google?.maps;
    if (!maps) {
      return;
    }

    if (!selectedPoint) {
      if (markerRef.current) {
        markerRef.current.setMap(null);
        markerRef.current = null;
      }

      map.setCenter(DEFAULT_CENTER);
      map.setZoom(DEFAULT_ZOOM);
      return;
    }

    if (!markerRef.current) {
      markerRef.current = new maps.Marker({
        position: selectedPoint,
        map,
        draggable: false,
      });
    } else {
      markerRef.current.setPosition(selectedPoint);
      markerRef.current.setMap(map);
    }

    map.panTo(selectedPoint);
  }, [selectedPoint]);

  return (
    <div className="overflow-hidden rounded-md border border-border/70">
      <div className="h-[320px] w-full" ref={mapContainerRef} />
      {loadError ? (
        <div className="border-t border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {loadError}
        </div>
      ) : null}
    </div>
  );
}
