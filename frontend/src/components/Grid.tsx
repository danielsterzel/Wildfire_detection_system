import { useEffect, useMemo, useState } from "react";

interface Cell {
  row: number;
  col: number;
  symbol_type: string;
  sector_id: number;
  sector_type: string;
  fire_level?: number;
  burn_level?: number;
  extinguish_level?: number;
}

interface Agent {
  agent_id: string;
  type: string;
  row: number;
  col: number;
  state: string;
}

interface SimulationStats {
  tick: number;
  running: boolean;
  fire_count: number;
  burned_count: number;
  tree_count: number;
  agent_count: number;
  simulation_session_id?: string | null;
}

interface SimulationMessage {
  id: number;
  tick: number;
  topic: string;
  direction: string;
  payload: Record<string, unknown>;
  timestamp: number;
}

interface GridData {
  cells: Cell[];
  wind_speed?: number;
  wind_direction?: string;
  humidity?: number;
  sectors?: { id: string; row_from: number; row_to: number; col_from: number; col_to: number; is_on_fire: boolean }[];
  agents?: Agent[];
  messages?: SimulationMessage[];
  stats?: SimulationStats;
}

type ActivePanel = "messages" | "dispatch" | "sensors" | "rules" | "config";

const API_BASE = "http://localhost:8000";
const DEFAULT_GRID_SIZE = 20;
const CELL_SIZE = 26;
const GAP = 1;
const DEFAULT_CONFIG = {
  rows: 20,
  columns: 20,
  sectors: [
    { row: 10, column: 10, sectorType: "TREE", initialState: { fireLevel: 35 } },
    { row: 11, column: 10, sectorType: "TREE", initialState: { fireLevel: 15 } },
  ],
  fireBrigades: [
    { fireBrigadeId: 1, row: 0, col: 0 },
    { fireBrigadeId: 2, row: 19, col: 19 },
  ],
  foresterPatrols: [{ foresterPatrolId: 1, row: 19, col: 0 }],
};

const cellClass = (symbolType: string): string => {
  switch (symbolType) {
    case "TREE":
      return "bg-emerald-700 hover:bg-emerald-600";
    case "FIRE":
      return "bg-red-600 hover:bg-red-500 animate-pulse shadow-[0_0_12px_rgba(239,68,68,0.7)]";
    case "BURNED":
      return "bg-zinc-700 hover:bg-zinc-600";
    case "WATER":
      return "bg-sky-600 hover:bg-sky-500";
    default:
      return "bg-zinc-500";
  }
};

const asText = (value: unknown) => {
  if (value === null || value === undefined || value === "") return "n/a";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
};

export function Grid() {
  const [gridData, setGridData] = useState<GridData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPaused, setIsPaused] = useState(false);
  const [tickInterval, setTickInterval] = useState(0.75);
  const [selectedAgent, setSelectedAgent] = useState("FB-1");
  const [configText, setConfigText] = useState(JSON.stringify(DEFAULT_CONFIG, null, 2));
  const [currentConfig, setCurrentConfig] = useState<Record<string, unknown>>(DEFAULT_CONFIG);
  const [messages, setMessages] = useState<SimulationMessage[]>([]);
  const [activePanel, setActivePanel] = useState<ActivePanel>("dispatch");
  const [showRawMessages, setShowRawMessages] = useState(false);
  const [showRawConfig, setShowRawConfig] = useState(false);
  const [configError, setConfigError] = useState("");
  const [actionError, setActionError] = useState("");
  const [rabbitStatus, setRabbitStatus] = useState("unknown");

  const fetchGrid = async () => {
    try {
      const response = await fetch(`${API_BASE}/grid`);
      const data = await response.json();
      setGridData(data);
      setLoading(false);
    } catch (error) {
      console.error("Failed to fetch grid:", error);
      setLoading(false);
    }
  };

  const fetchMessages = async () => {
    try {
      const response = await fetch(`${API_BASE}/messages?limit=60`);
      const data = await response.json();
      setMessages(data.messages ?? []);
    } catch (error) {
      console.error("Failed to fetch messages:", error);
    }
  };

  const fetchConfig = async () => {
    try {
      const response = await fetch(`${API_BASE}/config`);
      const data = await response.json();
      if (data.config) setCurrentConfig(data.config);
    } catch (error) {
      console.error("Failed to fetch config:", error);
    }
  };

  const fetchHealth = async () => {
    try {
      const response = await fetch(`${API_BASE}/health`);
      const data = await response.json();
      setRabbitStatus(data.rabbitmq ?? "unknown");
    } catch {
      setRabbitStatus("unreachable");
    }
  };

  const postJson = async (path: string, body: unknown = {}) => {
    setActionError("");
    const response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      const message = error.detail || "Request failed";
      setActionError(message);
      throw new Error(message);
    }
    await fetchGrid();
    await fetchMessages();
  };

  useEffect(() => {
    fetchGrid();
    fetchConfig();
    fetchHealth();
    if (!isPaused) {
      const interval = setInterval(() => {
        fetchGrid();
        fetchMessages();
        fetchConfig();
        fetchHealth();
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [isPaused]);

  const rowCount = useMemo(() => {
    if (!gridData?.cells.length) return DEFAULT_GRID_SIZE;
    return Math.max(...gridData.cells.map((cell) => cell.row), DEFAULT_GRID_SIZE - 1) + 1;
  }, [gridData]);

  const colCount = useMemo(() => {
    if (!gridData?.cells.length) return DEFAULT_GRID_SIZE;
    return Math.max(...gridData.cells.map((cell) => cell.col), DEFAULT_GRID_SIZE - 1) + 1;
  }, [gridData]);

  const grid = useMemo(() => {
    const matrix: (Cell | null)[][] = Array(rowCount)
      .fill(null)
      .map(() => Array(colCount).fill(null));
    gridData?.cells.forEach((cell) => {
      if (cell.row < rowCount && cell.col < colCount) matrix[cell.row][cell.col] = cell;
    });
    return matrix;
  }, [colCount, gridData, rowCount]);

  const serviceMessages = messages.filter((message) => message.topic.includes("dispatch.fire_services"));
  const sensorMessages = messages.filter((message) => message.topic.includes("telemetry.sensors"));
  const busMessages = messages.filter((message) => !message.topic.includes("dispatch.fire_services") && !message.topic.includes("telemetry.sensors"));
  const latestSummaryMessage = messages.find((message) => message.topic.includes("telemetry.summary"));
  const activeMessages = (activePanel === "dispatch" ? serviceMessages : activePanel === "messages" ? busMessages : sensorMessages).toSorted(
    (a, b) => b.id - a.id,
  );

  const currentConfigSectors = Array.isArray(currentConfig.sectors) ? currentConfig.sectors : [];
  const currentConfigBrigades = Array.isArray(currentConfig.fireBrigades) ? currentConfig.fireBrigades : [];
  const currentConfigPatrols = Array.isArray(currentConfig.foresterPatrols) ? currentConfig.foresterPatrols : [];

  const orderSelectedAgent = async (row: number, col: number) => {
    const path = selectedAgent.startsWith("FP-") ? "/orderForestPatrol" : "/orderFireBrigade";
    const payload = selectedAgent.startsWith("FP-")
      ? { agentId: selectedAgent, action: "PATROL", row, col }
      : { agentId: selectedAgent, action: "EXTINGUISH", row, col };
    await postJson(path, payload).catch(() => undefined);
  };

  const startWithConfig = async () => {
    setConfigError("");
    let parsedConfig: unknown;
    try {
      parsedConfig = JSON.parse(configText);
    } catch (error) {
      setConfigError(error instanceof Error ? error.message : "Invalid JSON");
      return;
    }
    await postJson("/stop_simulation").catch(() => undefined);
    await postJson("/run_simulation", parsedConfig).catch((error) => {
      setConfigError(error instanceof Error ? error.message : "Could not start simulation");
    });
    await fetchConfig();
  };

  const messageLabel = (topic: string) => {
    if (topic.includes("dispatch.fire_services")) return "Fire services dispatch";
    if (topic.includes("temp_humidity")) return "Temperature / humidity sensor";
    if (topic.includes("wind_speed")) return "Wind speed sensor";
    if (topic.includes("wind_direction")) return "Wind direction sensor";
    if (topic.includes("litter_moisture")) return "Litter moisture sensor";
    if (topic.includes("co2")) return "CO2 sensor";
    if (topic.includes("pm2_5")) return "PM2.5 sensor";
    if (topic.includes("camera")) return "Camera smoke detection";
    if (topic.includes("fire_brigade_actions")) return "Fire brigade order";
    if (topic.includes("forester_actions")) return "Patrol order";
    if (topic.includes("lifecycle")) return "Lifecycle";
    if (topic.includes("agents.batch")) return "Agent telemetry";
    if (topic.includes("summary")) return "Simulation summary";
    if (topic.includes("events")) return "Simulation event";
    if (topic.includes("speed")) return "Speed change";
    return "Message";
  };

  const messageRoute = (topic: string) => {
    if (topic.includes("dispatch.fire_services")) return "Simulation -> Fire services";
    if (topic.includes("telemetry.sensors")) return "Sector sensors -> Telemetry bus";
    if (topic.includes("control")) return "UI / API -> Simulation";
    if (topic.includes("telemetry")) return "Simulation -> UI / Support";
    if (topic.includes("events")) return "Simulation -> Event stream";
    return "Simulation bus";
  };

  if (loading) {
    return <div className="rounded-lg bg-zinc-950 p-8 text-center text-white">Loading simulation...</div>;
  }

  if (!gridData) {
    return <div className="rounded-lg bg-zinc-950 p-8 text-center text-white">Failed to load grid</div>;
  }

  return (
    <div className="w-full space-y-4 text-zinc-100">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
        <Metric label="Tick" value={gridData.stats?.tick ?? 0} />
        <Metric label="Fires" value={gridData.stats?.fire_count ?? 0} tone="danger" />
        <Metric label="Burned" value={gridData.stats?.burned_count ?? 0} />
        <Metric label="Wind" value={`${gridData.wind_speed ?? 0} m/s -> ${gridData.wind_direction ?? "N"}`} />
        <Metric label="Humidity" value={`${gridData.humidity ?? 0} %`} />
        <Metric label="RabbitMQ" value={rabbitStatus} />
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3 shadow-2xl">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-white">Operational Map</h2>
            <p className="text-xs text-zinc-400">Click a cell to send the selected unit.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button onClick={() => postJson("/run_simulation").catch(() => undefined)} className="rounded-md bg-emerald-700 px-3 py-1.5 text-xs font-bold text-white hover:bg-emerald-600">Start</button>
            <button onClick={() => postJson("/stop_simulation").catch(() => undefined)} className="rounded-md bg-red-700 px-3 py-1.5 text-xs font-bold text-white hover:bg-red-600">Stop</button>
            <button onClick={() => postJson("/step", { ticks: 1 }).catch(() => undefined)} className="rounded-md bg-sky-700 px-3 py-1.5 text-xs font-bold text-white hover:bg-sky-600">Step</button>
            <button onClick={() => setIsPaused(!isPaused)} className="rounded-md bg-zinc-700 px-3 py-1.5 text-xs font-bold text-white hover:bg-zinc-600">{isPaused ? "Resume UI" : "Pause UI"}</button>
            <select value={selectedAgent} onChange={(event) => setSelectedAgent(event.target.value)} className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-white">
              {(gridData.agents ?? []).map((agent) => <option key={agent.agent_id} value={agent.agent_id}>{agent.agent_id}</option>)}
            </select>
            <input type="number" min="0.05" step="0.05" value={tickInterval} onChange={(event) => setTickInterval(Number(event.target.value))} className="w-20 rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-white" />
            <button onClick={() => postJson("/set_speed", { tickInterval }).catch(() => undefined)} className="rounded-md bg-zinc-700 px-3 py-1.5 text-xs font-bold text-white hover:bg-zinc-600">Speed</button>
          </div>
        </div>

        {actionError && <div className="mb-3 rounded-md border border-red-700 bg-red-950 px-3 py-2 text-sm text-red-100">{actionError}</div>}

        <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_430px]">
          <div className="overflow-auto rounded-lg border border-zinc-800 bg-black p-4">
            <div className="mx-auto w-fit">
              <div
                className="relative grid rounded-md bg-zinc-950 p-1"
                style={{
                  gridTemplateColumns: `repeat(${colCount}, ${CELL_SIZE}px)`,
                  gap: `${GAP}px`,
                }}
              >
                {(gridData.sectors ?? []).map((sector) => {
                  const top = sector.row_from * (CELL_SIZE + GAP) + 4;
                  const left = sector.col_from * (CELL_SIZE + GAP) + 4;
                  const width = (sector.col_to - sector.col_from + 1) * CELL_SIZE + (sector.col_to - sector.col_from) * GAP;
                  const height = (sector.row_to - sector.row_from + 1) * CELL_SIZE + (sector.row_to - sector.row_from) * GAP;
                  return (
                    <div
                      key={sector.id}
                      className="pointer-events-none absolute rounded"
                      style={{
                        top,
                        left,
                        width,
                        height,
                        border: `2px solid ${sector.is_on_fire ? "rgba(248,113,113,0.95)" : "rgba(255,255,255,0.25)"}`,
                      }}
                    />
                  );
                })}
                {(gridData.agents ?? []).map((agent) => {
                  const top = agent.row * (CELL_SIZE + GAP) + 7;
                  const left = agent.col * (CELL_SIZE + GAP) + 7;
                  const isFireBrigade = agent.type === "fire_brigade";
                  return (
                    <div
                      key={agent.agent_id}
                      title={`${agent.agent_id} ${agent.state}`}
                      className="pointer-events-none absolute z-10 rounded-full border-2 border-white shadow-lg"
                      style={{
                        top,
                        left,
                        width: CELL_SIZE - 8,
                        height: CELL_SIZE - 8,
                        backgroundColor: isFireBrigade ? "#2563eb" : "#facc15",
                      }}
                    />
                  );
                })}
                {grid.map((row, rowIdx) =>
                  row.map((cell, colIdx) => (
                    <button
                      key={`${rowIdx}-${colIdx}`}
                      onClick={() => orderSelectedAgent(rowIdx, colIdx)}
                      className={`${cell ? cellClass(cell.symbol_type) : "bg-zinc-600"} border border-black/30 transition focus:outline-none focus:ring-2 focus:ring-white`}
                      style={{ width: CELL_SIZE, height: CELL_SIZE }}
                      title={`sector ${cell?.sector_id ?? "n/a"} (${cell?.sector_type ?? "unknown"}) row ${rowIdx}, col ${colIdx}, fire ${cell?.fire_level ?? 0}`}
                    />
                  )),
                )}
              </div>
            </div>
          </div>

          <aside className="min-h-[620px] rounded-lg border border-zinc-800 bg-zinc-900/80 p-3">
            <div className="mb-3 grid grid-cols-5 gap-1 rounded-md bg-zinc-950 p-1 text-xs">
              <TabButton active={activePanel === "dispatch"} onClick={() => setActivePanel("dispatch")} label="Dispatch" />
              <TabButton active={activePanel === "messages"} onClick={() => setActivePanel("messages")} label="Messages" />
              <TabButton active={activePanel === "sensors"} onClick={() => setActivePanel("sensors")} label="Sensors" />
              <TabButton active={activePanel === "rules"} onClick={() => setActivePanel("rules")} label="Rules" />
              <TabButton active={activePanel === "config"} onClick={() => setActivePanel("config")} label="Config" />
            </div>

            {activePanel === "config" ? (
              <ConfigPanel
                configText={configText}
                configError={configError}
                currentConfig={currentConfig}
                currentConfigSectors={currentConfigSectors}
                currentConfigBrigades={currentConfigBrigades}
                currentConfigPatrols={currentConfigPatrols}
                showRawConfig={showRawConfig}
                onApply={startWithConfig}
                onConfigTextChange={setConfigText}
                onToggleRaw={() => setShowRawConfig(!showRawConfig)}
              />
            ) : activePanel === "rules" ? (
              <RulesPanel summaryMessage={latestSummaryMessage} />
            ) : (
              <MessagePanel
                messages={activeMessages}
                showRaw={showRawMessages}
                emptyText={activePanel === "dispatch" ? "No dispatch messages yet. Start the simulation and wait for telemetry ticks." : activePanel === "sensors" ? "No sensor messages yet. They are emitted every telemetry cycle." : "No bus messages yet."}
                onRefresh={fetchMessages}
                onToggleRaw={() => setShowRawMessages(!showRawMessages)}
                labelForTopic={messageLabel}
                routeForTopic={messageRoute}
              />
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}

function RulesPanel({ summaryMessage }: { summaryMessage?: SimulationMessage }) {
  const productions = Array.isArray(summaryMessage?.payload.productions) ? summaryMessage.payload.productions : [];
  const appliedRules = Array.isArray(summaryMessage?.payload.lastAppliedRules) ? summaryMessage.payload.lastAppliedRules : [];
  const rewritingSystem = summaryMessage?.payload.rewritingSystem ?? "local-grid-production-system";

  return (
    <div className="flex h-[590px] flex-col">
      <div className="mb-3">
        <h3 className="text-sm font-bold text-white">Applied Rewriting Rules</h3>
        <p className="mt-1 text-xs text-zinc-400">Live view of the production system used by the fire simulation.</p>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto rounded-md bg-black/70 p-3 text-xs text-zinc-200">
        <div className="rounded-md border border-zinc-800 bg-zinc-950 p-3">
          <div className="text-zinc-500">Model</div>
          <div className="mt-1 font-mono text-emerald-200">{asText(rewritingSystem)}</div>
          <div className="mt-2 text-zinc-400">
            Object-based, contextual and parametric interpretation of a rewriting system inspired by L-systems.
          </div>
        </div>

        <div className="rounded-md border border-zinc-800 bg-zinc-950 p-3">
          <div className="mb-2 font-semibold text-zinc-300">Productions</div>
          {productions.length === 0 ? (
            <p className="text-zinc-500">Start the simulation to receive production rules from summary messages.</p>
          ) : (
            <div className="space-y-2">
              {productions.map((production, index) => (
                <div key={`${asText(production)}-${index}`} className="rounded bg-black px-2 py-2 font-mono text-[11px] text-zinc-200">
                  {asText(production)}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-md border border-zinc-800 bg-zinc-950 p-3">
          <div className="mb-2 font-semibold text-zinc-300">Last Applied Rules</div>
          {appliedRules.length === 0 ? (
            <p className="text-zinc-500">No rule application reported in the latest summary yet.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {appliedRules.map((rule, index) => (
                <span key={`${asText(rule)}-${index}`} className="rounded bg-amber-950 px-2 py-1 font-mono text-[11px] text-amber-100">
                  {asText(rule)}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-md border border-zinc-800 bg-zinc-950 p-3">
          <div className="mb-2 font-semibold text-zinc-300">How To Read It</div>
          <div className="space-y-1 text-zinc-400">
            <div><span className="text-zinc-300">Symbol:</span> one map cell with terrain, fire level, burn level and sensor context.</div>
            <div><span className="text-zinc-300">Context:</span> neighboring cells, wind, humidity, terrain type and patrol state.</div>
            <div><span className="text-zinc-300">Generation:</span> each tick rewrites the grid into the next fire state.</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value, tone = "default" }: { label: string; value: string | number; tone?: "default" | "danger" }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
      <div className="text-xs uppercase tracking-wide text-zinc-500">{label}</div>
      <div className={`mt-1 text-xl font-semibold ${tone === "danger" ? "text-red-300" : "text-white"}`}>{value}</div>
    </div>
  );
}

function TabButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`rounded px-2 py-2 font-semibold ${active ? "bg-white text-zinc-950" : "text-zinc-300 hover:bg-zinc-800"}`}>
      {label}
    </button>
  );
}

function MessagePanel({
  messages,
  showRaw,
  emptyText,
  onRefresh,
  onToggleRaw,
  labelForTopic,
  routeForTopic,
}: {
  messages: SimulationMessage[];
  showRaw: boolean;
  emptyText: string;
  onRefresh: () => void;
  onToggleRaw: () => void;
  labelForTopic: (topic: string) => string;
  routeForTopic: (topic: string) => string;
}) {
  return (
    <div className="flex h-[590px] flex-col">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-sm font-bold text-white">Message Stream</h3>
        <div className="flex gap-2">
          <button onClick={onToggleRaw} className="rounded-md bg-zinc-700 px-3 py-1 text-xs font-bold text-white hover:bg-zinc-600">{showRaw ? "Pretty" : "Raw JSON"}</button>
          <button onClick={onRefresh} className="rounded-md bg-zinc-700 px-3 py-1 text-xs font-bold text-white hover:bg-zinc-600">Refresh</button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto rounded-md bg-black/70 p-2">
        {messages.length === 0 ? (
          <p className="text-xs text-zinc-500">{emptyText}</p>
        ) : (
          <div className="space-y-2">
            {messages.map((message) => <MessageCard key={message.id} message={message} showRaw={showRaw} label={labelForTopic(message.topic)} route={routeForTopic(message.topic)} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function MessageCard({ message, showRaw, label, route }: { message: SimulationMessage; showRaw: boolean; label: string; route: string }) {
  const fire = message.payload.fire as Record<string, unknown> | undefined;
  const environment = message.payload.environment as Record<string, unknown> | undefined;
  const fireLocation = fire?.location as Record<string, unknown> | undefined;
  return (
    <article className="rounded-md border border-zinc-800 bg-zinc-900 p-3 text-xs">
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-white">{label}</span>
        <span className="text-zinc-500">bus id #{message.id} • tick {message.tick}</span>
      </div>
      <div className="mt-1 font-mono text-[11px] text-zinc-500">{message.topic}</div>
      {showRaw ? (
        <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words rounded bg-black p-2 text-[11px] text-zinc-300">{JSON.stringify(message, null, 2)}</pre>
      ) : (
        <div className="mt-3 space-y-1 text-zinc-300">
          {"title" in message.payload && <div className="mb-2 rounded bg-red-950 px-2 py-1 font-semibold text-red-100">{asText(message.payload.title)}</div>}
          <div><span className="text-zinc-500">Route:</span> {route}</div>
          <div><span className="text-zinc-500">Event:</span> {asText(message.payload.event)}</div>
          {"recipient" in message.payload && <div><span className="text-zinc-500">To:</span> {asText(message.payload.recipient)}</div>}
          {"agentId" in message.payload && <div><span className="text-zinc-500">Agent:</span> {asText(message.payload.agentId)}</div>}
          {"sensorId" in message.payload && <div><span className="text-zinc-500">Sensor:</span> {asText(message.payload.sensorId)}</div>}
          {"sectorId" in message.payload && <div><span className="text-zinc-500">Sector:</span> {asText(message.payload.sectorId)} ({asText(message.payload.sectorType)})</div>}
          {"task" in message.payload && <div><span className="text-zinc-500">Task:</span> {asText(message.payload.task)}</div>}
          {"temperature" in message.payload && <div><span className="text-zinc-500">Temperature:</span> {asText(message.payload.temperature)} {asText(message.payload.temperatureUnit)}</div>}
          {"humidity" in message.payload && <div><span className="text-zinc-500">Humidity:</span> {asText(message.payload.humidity)} {asText(message.payload.humidityUnit)}</div>}
          {"windSpeed" in message.payload && <div><span className="text-zinc-500">Wind speed:</span> {asText(message.payload.windSpeed)} {asText(message.payload.windSpeedUnit)}</div>}
          {"windDirection" in message.payload && <div><span className="text-zinc-500">Wind direction:</span> {asText(message.payload.windDirection)} ({asText(message.payload.windDirectionUnit)})</div>}
          {"litterMoisture" in message.payload && <div><span className="text-zinc-500">Litter moisture:</span> {asText(message.payload.litterMoisture)} {asText(message.payload.litterMoistureUnit)}</div>}
          {"co2" in message.payload && <div><span className="text-zinc-500">CO2:</span> {asText(message.payload.co2)} {asText(message.payload.co2Unit)}</div>}
          {"pm2_5" in message.payload && <div><span className="text-zinc-500">PM2.5:</span> {asText(message.payload.pm2_5)} {asText(message.payload.pm2_5Unit)}</div>}
          {"smokeDetected" in message.payload && <div><span className="text-zinc-500">Smoke:</span> {asText(message.payload.smokeDetected)} level {asText(message.payload.smokeLevel)} {asText(message.payload.smokeLevelUnit)}</div>}
          {fire && <div><span className="text-zinc-500">Fire:</span> row {asText(fire.row)}, col {asText(fire.col)}, level {asText(fire.fireLevel)}</div>}
          {fireLocation && <div><span className="text-zinc-500">Lat/Lon:</span> {asText(fireLocation.latitude)}, {asText(fireLocation.longitude)}</div>}
          {environment && <div><span className="text-zinc-500">Wind:</span> {asText(environment.windSpeed)} {asText(environment.windSpeedUnit)} toward {asText(environment.windDirection)} ({asText(environment.windDirectionUnit)}), humidity {asText(environment.humidity)} {asText(environment.humidityUnit)}</div>}
          {"recommendation" in message.payload && <div className="pt-1 text-amber-200">{asText(message.payload.recommendation)}</div>}
          {"batch" in message.payload && Array.isArray(message.payload.batch) && <div><span className="text-zinc-500">Agents in batch:</span> {message.payload.batch.length}</div>}
        </div>
      )}
    </article>
  );
}

function ConfigPanel({
  configText,
  configError,
  currentConfig,
  currentConfigSectors,
  currentConfigBrigades,
  currentConfigPatrols,
  showRawConfig,
  onApply,
  onConfigTextChange,
  onToggleRaw,
}: {
  configText: string;
  configError: string;
  currentConfig: Record<string, unknown>;
  currentConfigSectors: unknown[];
  currentConfigBrigades: unknown[];
  currentConfigPatrols: unknown[];
  showRawConfig: boolean;
  onApply: () => void;
  onConfigTextChange: (value: string) => void;
  onToggleRaw: () => void;
}) {
  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-sm font-bold text-white">Loaded Configuration</h3>
        <div className="flex gap-2">
          <button onClick={onToggleRaw} className="rounded-md bg-zinc-700 px-3 py-1 text-xs font-bold text-white hover:bg-zinc-600">{showRawConfig ? "Summary" : "Raw JSON"}</button>
          <button onClick={onApply} className="rounded-md bg-emerald-700 px-3 py-1 text-xs font-bold text-white hover:bg-emerald-600">Apply</button>
        </div>
      </div>
      {showRawConfig ? (
        <textarea value={configText} onChange={(event) => onConfigTextChange(event.target.value)} spellCheck={false} className="h-[535px] w-full resize-none rounded-md border border-zinc-800 bg-black p-3 font-mono text-xs text-zinc-100 outline-none focus:border-emerald-500" />
      ) : (
        <div className="space-y-3 text-xs text-zinc-200">
          <div className="grid grid-cols-2 gap-2">
            <Metric label="Map" value={`${Number(currentConfig.rows ?? 0)} x ${Number(currentConfig.columns ?? 0)}`} />
            <Metric label="Fire Points" value={currentConfigSectors.length} tone="danger" />
            <Metric label="Brigades" value={currentConfigBrigades.length} />
            <Metric label="Patrols" value={currentConfigPatrols.length} />
          </div>
          <div className="rounded-md border border-zinc-800 bg-black/70 p-3">
            <div className="mb-2 font-semibold text-zinc-300">Initial fire sectors</div>
            <div className="flex flex-wrap gap-1">
              {currentConfigSectors.length === 0 ? (
                <span className="text-zinc-500">No explicit sectors loaded.</span>
              ) : (
                currentConfigSectors.slice(0, 10).map((sector, index) => {
                  const item = sector as Record<string, unknown>;
                  const state = (item.initialState ?? {}) as Record<string, unknown>;
                  return <span key={`${item.row}-${item.column}-${index}`} className="rounded bg-red-950 px-2 py-1 text-red-100">r{asText(item.row)} c{asText(item.column)} fire {asText(state.fireLevel)}</span>;
                })
              )}
            </div>
          </div>
        </div>
      )}
      {configError && <p className="mt-2 text-xs text-red-300">{configError}</p>}
    </div>
  );
}
