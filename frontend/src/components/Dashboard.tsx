import { useEffect, useState } from "react";
import { Grid } from "./Grid";

export function Dashboard() {
  const [started, setStarted] = useState(false);
  const [humidity, setHumidity] = useState(0);
  const [windSpeed, setWindSpeed] = useState(0);
  const [windDirection, setWindDirection] = useState("");

  useEffect(() => {
    const fetchEnv = async () => {
      try {
        const res = await fetch("http://localhost:8000/grid");
        if (!res.ok) return;
        const data = await res.json();
        setWindSpeed(data.wind_speed ?? 0);
        setWindDirection(data.wind_direction ?? "");
        setHumidity(data.humidity ?? 0);
      } catch {
        // backend may not be running yet
      }
    };

    const id = setInterval(fetchEnv, 1200);
    fetchEnv();
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Enter") setStarted(true);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <main className="min-h-screen bg-zinc-950 text-white">
      {!started && (
        <section
          className="relative flex min-h-screen items-center justify-center bg-cover bg-center px-6"
          style={{ backgroundImage: "url('/forest.jpg')" }}
        >
          <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-black/45 to-zinc-950" />
          <div className="relative z-10 mx-auto max-w-4xl text-center">
            <div className="mb-5 inline-flex items-center rounded-full border border-emerald-300/30 bg-black/40 px-4 py-2 text-sm text-emerald-100 backdrop-blur">
              Wind {windSpeed} m/s toward {windDirection || "N"} | Humidity {humidity} %
            </div>
            <h1 className="text-5xl font-bold tracking-normal text-white md:text-7xl">Wildfire Detection System</h1>
            <p className="mx-auto mt-5 max-w-2xl text-lg text-zinc-200">
              Live fire spread simulation with service dispatch messages, operational telemetry, and configurable response units.
            </p>
            <button
              onClick={() => setStarted(true)}
              className="mt-8 rounded-md bg-emerald-500 px-6 py-3 text-sm font-bold text-zinc-950 shadow-lg shadow-emerald-950/40 hover:bg-emerald-400"
            >
              Open Operations Console
            </button>
            <div className="mt-4 text-sm text-zinc-300">Press Enter to begin</div>
          </div>
        </section>
      )}

      {started && (
        <section className="mx-auto min-h-screen w-full max-w-[1720px] px-5 py-5">
          <header className="mb-4 flex flex-wrap items-end justify-between gap-3 border-b border-zinc-800 pb-4">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-emerald-300">Operations Console</div>
              <h1 className="mt-1 text-3xl font-semibold tracking-normal">Wildfire Detection System</h1>
            </div>
            <div className="flex flex-wrap gap-2 text-xs text-zinc-300">
              <span className="rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2">Wind {windSpeed} m/s toward {windDirection || "N"}</span>
              <span className="rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2">Humidity {humidity} %</span>
            </div>
          </header>
          <Grid />
        </section>
      )}
    </main>
  );
}
