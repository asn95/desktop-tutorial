import { useEffect, useMemo, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { formatCurrency } from "../../lib/format";
import type { Target } from "../../types/target";
import { useLang } from "../../contexts/LanguageContext";

const STATUS_COLOR: Record<string, string> = {
  pending: "#E81E28",
  in_progress: "#d97706",
  completed: "#16a34a",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Menunggu",
  in_progress: "Sedang Berjalan",
  completed: "Selesai",
};

interface TargetMapProps {
  targets: Target[];
}

/** Isi popup dirakit sebagai node DOM; textContent tidak pernah menafsirkan markup. */
function popupEl(name: string, address: string, meta: string): HTMLElement {
  const el = document.createElement("div");
  const strong = document.createElement("strong");
  strong.textContent = name;
  const addr = document.createElement("div");
  addr.textContent = address;
  const info = document.createElement("div");
  info.textContent = meta;
  el.append(strong, addr, info);
  return el;
}

export function TargetMap({ targets }: TargetMapProps) {
  // dialias: `t` sudah dipakai sebagai variabel Target di file ini
  const { t: tr } = useLang();
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);

  const located = useMemo(
    () => targets.filter((t) => t.latitude != null && t.longitude != null),
    [targets]
  );
  // Data polling 10 detik menghasilkan array baru terus-menerus; render ulang
  // marker + fitBounds hanya bila isi petanya benar-benar berubah.
  const signature = useMemo(
    () => located.map((t) => `${t.id}:${t.status}:${t.latitude},${t.longitude}`).join("|"),
    [located]
  );

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const container = containerRef.current;
    const map = L.map(container, {
      scrollWheelZoom: false, // scroll dua jari tetap menggulir halaman, bukan peta
      touchZoom: true,        // pinch di layar sentuh (iPhone/Android)
      zoomSnap: 0.25,         // langkah zoom halus untuk gesture pinch
    }).setView([-2.5, 118], 4); // Indonesia
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);

    // Pinch trackpad (Mac) tiba sebagai wheel event dengan ctrlKey=true —
    // zoom hanya untuk gesture itu, wheel biasa dibiarkan menggulir halaman.
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey) return;
      e.preventDefault(); // cegah browser men-zoom seluruh halaman
      map.setZoomAround(
        map.mouseEventToLatLng(e),
        map.getZoom() + (e.deltaY < 0 ? 0.5 : -0.5)
      );
    };
    container.addEventListener("wheel", onWheel, { passive: false });

    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    return () => {
      container.removeEventListener("wheel", onWheel);
      map.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const layer = layerRef.current;
    if (!map || !layer) return;
    layer.clearLayers();
    if (located.length === 0) return;

    for (const t of located) {
      const status = STATUS_COLOR[t.status] ? t.status : "pending";
      L.circleMarker([t.latitude as number, t.longitude as number], {
        radius: 7,
        color: STATUS_COLOR[status],
        weight: 2,
        fillColor: STATUS_COLOR[status],
        fillOpacity: 0.35,
      })
        // Elemen, bukan string HTML. Nama dan alamat nasabah datang dari unggahan
        // CSV — bukan ketikan manajer — dan bindPopup memasang string sebagai
        // innerHTML. Satu baris CSV bernama `<img src=x onerror=...>` sudah cukup
        // untuk mencuri token dari localStorage begitu ada yang mengklik pin-nya.
        .bindPopup(popupEl(t.customerName, t.address, `${formatCurrency(t.amountDue)} · ${tr(STATUS_LABEL[status])}`))
        .addTo(layer);
    }
    map.fitBounds(
      L.latLngBounds(located.map((t) => [t.latitude as number, t.longitude as number])),
      { padding: [24, 24], maxZoom: 12 }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature]);

  return (
    // `isolate` membentuk stacking context sendiri. Leaflet memberi z-index 400
    // pada panel peta dan 1000 pada kontrol zoom; tanpa ini keduanya bersaing
    // langsung dengan header sticky (z-30) dan menutupinya saat halaman digulir.
    <section className="isolate overflow-hidden rounded-md border border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
        <h3 className="text-sm font-semibold text-gray-900">{tr("Peta Sebaran Target")}</h3>
        <span className="text-xs text-gray-400">
          {located.length} {tr("dari")} {targets.length} {tr("target berkoordinat")}
        </span>
      </div>
      <div className="relative">
        <div ref={containerRef} className="h-[340px] w-full" />
        {located.length === 0 && (
          <div className="pointer-events-none absolute inset-0 z-[500] flex items-center justify-center bg-white/70">
            <p className="max-w-xs text-center text-xs text-gray-500">
              {tr("Belum ada target dengan koordinat pada periode ini. Koordinat terisi otomatis beberapa saat setelah CSV diunggah.")}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
