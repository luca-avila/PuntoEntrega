import { divIcon, type LatLngLiteral } from "leaflet";
import { useEffect } from "react";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";

const DEFAULT_CENTER: LatLngLiteral = { lat: -34.6037, lng: -58.3816 };
const DEFAULT_ZOOM = 13;

const LOCATION_MARKER_ICON = divIcon({
  className: "",
  html: '<span style="display:block;width:18px;height:18px;border-radius:9999px;background:hsl(var(--primary));border:2px solid hsl(var(--card));box-shadow:0 0 0 4px hsl(var(--primary) / 0.2),0 2px 8px rgba(0,0,0,0.45);"></span>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

interface LocationMapPickerProps {
  selectedPoint: LatLngLiteral | null;
  onSelectPoint: (point: LatLngLiteral) => void;
}

function MapClickSelector({
  onSelectPoint,
}: {
  onSelectPoint: (point: LatLngLiteral) => void;
}) {
  useMapEvents({
    click(event) {
      onSelectPoint(event.latlng);
    },
  });

  return null;
}

function MapCenterUpdater({ center }: { center: LatLngLiteral }) {
  const map = useMap();

  useEffect(() => {
    map.setView(center);
  }, [center, map]);

  return null;
}

export function LocationMapPicker({ selectedPoint, onSelectPoint }: LocationMapPickerProps) {
  const center = selectedPoint ?? DEFAULT_CENTER;

  return (
    <div className="overflow-hidden rounded-md border">
      <MapContainer
        center={center}
        className="h-[320px] w-full"
        scrollWheelZoom
        zoom={DEFAULT_ZOOM}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        <MapClickSelector onSelectPoint={onSelectPoint} />
        <MapCenterUpdater center={center} />
        {selectedPoint ? <Marker icon={LOCATION_MARKER_ICON} position={selectedPoint} /> : null}
      </MapContainer>
    </div>
  );
}
