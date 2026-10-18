import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  Battery,
  Bell,
  Bluetooth,
  Check,
  ChevronRight,
  Code2,
  Database,
  FlaskConical,
  Heart,
  History,
  Info,
  Languages,
  Link2,
  LoaderCircle,
  LockKeyhole,
  Radio,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Signal,
  Square,
  Target,
  Terminal,
  Unplug,
  Watch,
  Waves,
  X,
} from "lucide-react";
import type {
  Alarm,
  Capability,
  Device,
  Observation,
  Packet,
  State,
} from "./types";
import "./style.css";
const EMPTY: State = {
  connected: false,
  demo: false,
  info: {},
  settings: {},
  alarms: [],
  capabilities: [],
  services: [],
};
const tabs = [
  ["overview", "Overview", Activity],
  ["history", "Health history", History],
  ["controls", "Watch controls", Settings2],
  ["lab", "Device lab", FlaskConical],
  ["about", "About the project", Info],
] as const;
const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const fmt = (value: number | undefined | null) =>
  value == null ? "—" : value.toLocaleString();
const short = (uuid: string) =>
  uuid.startsWith("0000") ? uuid.slice(4, 8).toUpperCase() : uuid;
function App() {
  const [state, setState] = useState<State>(EMPTY),
    [tab, setTab] = useState("overview"),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [devices, setDevices] = useState<Device[]>([]),
    [showDevices, setShowDevices] = useState(false),
    [records, setRecords] = useState<Observation[]>([]),
    [packets, setPackets] = useState<Packet[]>([]),
    [filter, setFilter] = useState("all");
  const [backend, setBackend] = useState(!!window.watch),
    [samples, setSamples] = useState<number[]>([]);
  const invoke = async <T,>(
    command: string,
    args: Record<string, unknown> = {},
  ): Promise<T> => {
    if (!window.watch)
      throw Error("Open this interface in the OpenWatch Lab desktop app.");
    return window.watch.command<T>(command, args);
  };
  const loadHistory = () => invoke<Observation[]>("history").then(setRecords);
  const run = async <T,>(
    label: string,
    command: string,
    args: Record<string, unknown> = {},
    success?: string,
  ): Promise<T | undefined> => {
    setBusy(label);
    setError("");
    setNotice("");
    try {
      const value = await invoke<T>(command, args);
      if (success) setNotice(success);
      return value;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return undefined;
    } finally {
      setBusy("");
    }
  };
  useEffect(() => {
    if (!window.watch) {
      setError(
        "Desktop bridge unavailable. Use npm run dev to start the full application.",
      );
      return;
    }
    const off = window.watch.subscribe((message) => {
      if (message.event === "state") setState(message.data as unknown as State);
      if (message.event === "heart_rate") {
        setSamples((values) => [
          ...values.slice(-29),
          Number(message.data.bpm),
        ]);
      }
      if (message.event === "backend_exit") {
        setBackend(false);
        setState((s) => ({
          ...s,
          connected: false,
          measurement: null,
          heart_rate: null,
        }));
        setError("Bluetooth backend stopped. Restart OpenWatch Lab.");
      }
      if (message.event === "find_phone")
        setNotice("Your watch is looking for this computer.");
      if (message.event === "warning") setError(String(message.data.message));
      if (message.event === "history_changed") loadHistory().catch(() => {});
    });
    invoke<State>("state")
      .then(setState)
      .catch((e) => {
        setError(String(e));
        setBackend(false);
      });
    return off;
  }, []);
  useEffect(() => {
    if (tab === "history") loadHistory().catch((e) => setError(String(e)));
    if (tab === "lab")
      invoke<Packet[]>("packets")
        .then(setPackets)
        .catch(() => {});
  }, [tab, state.demo]);
  const scan = async () => {
    setShowDevices(true);
    const list = await run<Device[]>("Scanning nearby devices", "scan");
    if (list) setDevices(list);
  };
  const connected = state.connected || state.demo;
  const writable =
    state.connected && !state.demo && !!state.profile_verified && !busy;
  const refresh = () =>
    run<State>("Reading watch", "refresh", {}, "Watch values refreshed.");
  const sync = async () => {
    const result = await run<{ fetched: number; warnings: string[] }>(
      "Fetching stored records",
      "sync",
    );
    if (result) {
      setNotice(
        `Fetched ${result.fetched} records. Repeated syncs do not create duplicates.${result.warnings.length ? " Some workout data could not be decoded." : ""}`,
      );
      loadHistory().catch(() => {});
    }
  };
  const setSetting = async (name: string, value: number) => {
    await run(
      "Verifying setting",
      "set_setting",
      { name, value },
      "Setting saved and verified on the watch.",
    );
  };
  const demo = async () => {
    const value = await run<State>("Opening synthetic preview", "demo");
    if (value) {
      setState(value);
      setShowDevices(false);
      setSamples([]);
    }
  };
  const connectionLabel = state.demo
    ? "Synthetic preview"
    : state.connected
      ? "Connected directly"
      : "No watch connected";
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="wordmark">
          <div className="logo">
            <Watch size={25} />
          </div>
          <div>
            openwatch<span>LAB / 0.1</span>
          </div>
        </div>
        <div className="nav-label">YOUR WORKSPACE</div>
        <nav>
          {tabs.map(([id, label, Icon]) => (
            <button
              key={id}
              className={tab === id ? "nav active" : "nav"}
              onClick={() => setTab(id)}
            >
              <Icon size={18} />
              {label}
              {tab === id && <ChevronRight size={14} />}
            </button>
          ))}
        </nav>
        <div className="side-bottom">
          <div className="privacy-icon">
            <LockKeyhole size={17} />
          </div>
          <strong>Yours, by default.</strong>
          <p>
            No account. No vendor cloud.
            <br />
            Your records stay on this computer.
          </p>
          <span className="open-source">
            <span /> OPEN SOURCE
          </span>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="crumb">
            WORKSPACE <ChevronRight size={13} />{" "}
            {tabs.find((t) => t[0] === tab)?.[1]}
          </div>
          <div className="top-right">
            <span
              className={
                "status-dot " +
                (state.connected ? "online" : state.demo ? "demo" : "")
              }
            />
            {connectionLabel}
            <button
              className="icon-button"
              title="Refresh watch values"
              aria-label="Refresh watch values"
              disabled={!state.connected || !!busy}
              onClick={refresh}
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </header>
        <div className="content">
          {state.demo && (
            <div className="demo-banner">
              <FlaskConical size={16} />
              <span>
                <b>Synthetic preview.</b> Sample values only. Watch controls are
                disabled and nothing is saved to your health database.
              </span>
              <button
                onClick={() =>
                  run("Leaving preview", "disconnect").then(() => {
                    setState(EMPTY);
                    setSamples([]);
                  })
                }
              >
                Exit preview
              </button>
            </div>
          )}
          {error && (
            <div role="alert" className="alert error">
              <Info size={17} />
              <span>{error}</span>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={15} />
              </button>
            </div>
          )}
          {notice && (
            <div role="status" className="alert success">
              <Check size={17} />
              <span>{notice}</span>
              <button
                aria-label="Dismiss notification"
                onClick={() => setNotice("")}
              >
                <X size={15} />
              </button>
            </div>
          )}
          {busy && (
            <div role="status" className="working">
              <LoaderCircle className="spin" size={15} />
              {busy}…
            </div>
          )}
          {tab === "overview" && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">A DIRECT CONNECTION</div>
                  <h1>
                    Your watch. <em>Your data.</em>
                  </h1>
                  <p>A little less lock-in. A lot more possibility.</p>
                </div>
                <button
                  className="button primary"
                  disabled={!!busy || !backend}
                  onClick={scan}
                >
                  <Bluetooth size={17} />
                  {connected ? "Switch watch" : "Connect a watch"}
                  <ArrowRight size={16} />
                </button>
              </div>
              <section className="device-card">
                <div className="watch-art">
                  <div className="watch-band" />
                  <div className="watch-face">
                    <span>open</span>
                    <strong>
                      {state.connected
                        ? "linked"
                        : state.demo
                          ? "demo"
                          : "ready"}
                    </strong>
                    <div className="tiny-bars">
                      <i />
                      <i />
                      <i />
                      <i />
                      <i />
                    </div>
                  </div>
                </div>
                <div className="device-summary">
                  <span className="eyebrow">
                    {connected ? "YOUR DEVICE" : "READY WHEN YOU ARE"}
                  </span>
                  <h2>{state.device?.name || "Make the connection."}</h2>
                  <p>
                    {connected
                      ? `${state.info.manufacturer || "Bluetooth watch"} · ${state.info.software || "Version unavailable"}`
                      : "Pair directly over Bluetooth. No registration required by the tested O20 operations."}
                  </p>
                  <div className="device-tags">
                    <span>
                      <ShieldCheck size={13} />
                      Local connection
                    </span>
                    <span>
                      <Code2 size={13} />
                      {state.adapter || "Extensible adapters"}
                    </span>
                  </div>
                </div>
                <div className="device-actions">
                  {state.connected ? (
                    <>
                      <span className="pill">
                        <span />
                        CONNECTED
                      </span>
                      <button
                        className="text-button"
                        disabled={!!busy}
                        onClick={() => run("Disconnecting", "disconnect")}
                      >
                        Disconnect <Unplug size={14} />
                      </button>
                    </>
                  ) : (
                    <>
                      <span className="connection-orbit">
                        <Radio size={24} />
                      </span>
                      {!state.demo && (
                        <button
                          className="text-button"
                          onClick={demo}
                          disabled={!!busy || !backend}
                        >
                          Explore a preview <ArrowRight size={14} />
                        </button>
                      )}
                    </>
                  )}
                </div>
              </section>
              <div className="section-line">
                <h3>Right now</h3>
                <span>
                  {state.demo
                    ? "SYNTHETIC VALUES"
                    : state.connected
                      ? "READ DIRECTLY FROM YOUR WATCH"
                      : "WAITING FOR A DEVICE"}
                </span>
              </div>
              <div className="metrics">
                <Metric
                  title="Daily steps"
                  icon={<Activity size={18} />}
                  value={fmt(connected ? state.activity?.steps : null)}
                  unit="steps"
                  subtitle={
                    connected
                      ? `Goal ${fmt(Number(state.settings.goal) || 0)} steps`
                      : "Connect to read today’s total"
                  }
                >
                  <div className="goal-track">
                    <i
                      style={{
                        width: `${connected ? Math.min(100, ((state.activity?.steps || 0) / Math.max(1, Number(state.settings.goal) || 4000)) * 100) : 0}%`,
                      }}
                    />
                  </div>
                </Metric>
                <Metric
                  title="Heart rate"
                  icon={<Heart size={18} />}
                  value={fmt(connected ? state.heart_rate?.bpm : null)}
                  unit="bpm"
                  subtitle={
                    state.demo
                      ? "Synthetic example"
                      : state.heart_rate
                        ? "Live standard Bluetooth stream"
                        : "No live reading received"
                  }
                >
                  <Sparkline
                    values={
                      state.demo ? [70, 72, 71, 74, 72, 73, 71, 72] : samples
                    }
                  />
                </Metric>
                <Metric
                  title="Battery"
                  icon={<Battery size={19} />}
                  value={fmt(connected ? state.battery?.percent : null)}
                  unit="%"
                  subtitle={
                    state.demo
                      ? "Synthetic example"
                      : connected
                        ? state.battery?.charging
                          ? "Charging · Moyoung offset decoded"
                          : "Read from the watch"
                        : "No battery value yet"
                  }
                >
                  <div className="battery-bars">
                    {Array.from({ length: 14 }, (_, i) => (
                      <i
                        key={i}
                        className={
                          connected &&
                          i < ((state.battery?.percent || 0) / 100) * 14
                            ? "filled"
                            : ""
                        }
                      />
                    ))}
                  </div>
                </Metric>
              </div>
              <div className="bottom-grid">
                <section className="panel records-callout">
                  <div className="panel-icon">
                    <History size={20} />
                  </div>
                  <h3>Bring your records home.</h3>
                  <p>
                    Retrieve manual oxygen, stress, and workout records. Keep
                    their source and timestamps intact.
                  </p>
                  <button
                    className="button secondary"
                    disabled={!state.connected || !!busy}
                    onClick={sync}
                  >
                    Sync stored records <ArrowDownToLine size={16} />
                  </button>
                  <button
                    className="text-button"
                    onClick={() => setTab("history")}
                  >
                    View local history <ArrowRight size={14} />
                  </button>
                </section>
                <section className="panel roadmap">
                  <div className="eyebrow">BUILT IN THE OPEN</div>
                  <h3>One watch is a beginning.</h3>
                  <p>
                    Shared APIs. Documented packets. Independent device
                    adapters. A starting point for the next watch.
                  </p>
                  <div className="roadmap-row">
                    <span className="small-dot" />
                    O20 / Moyoung V2
                    <span className="subtle-badge">FIRST ADAPTER</span>
                  </div>
                  <button className="text-button" onClick={() => setTab("lab")}>
                    Explore what’s supported <ArrowRight size={14} />
                  </button>
                </section>
              </div>
            </>
          )}
          {tab === "history" && (
            <>
              <PageTitle
                eyebrow="YOUR LOCAL ARCHIVE"
                title="Health history"
                subtitle="Stored observations retain their source. An old reading is never presented as a new measurement."
              />
              <div className="toolbar">
                <div className="segments">
                  {["all", "oxygen", "stress", "workout"].map((kind) => (
                    <button
                      key={kind}
                      className={filter === kind ? "selected" : ""}
                      onClick={() => setFilter(kind)}
                    >
                      {kind === "all"
                        ? "All records"
                        : kind[0].toUpperCase() + kind.slice(1)}
                    </button>
                  ))}
                </div>
                <div className="toolbar-actions">
                  <button
                    className="button secondary"
                    disabled={!!busy}
                    onClick={() =>
                      run(
                        "Exporting records",
                        "export",
                        {},
                        "Export saved locally.",
                      )
                    }
                  >
                    <ArrowDownToLine size={15} />
                    Export JSON
                  </button>
                  <button
                    className="button primary"
                    disabled={!state.connected || !!busy}
                    onClick={sync}
                  >
                    <RefreshCw size={15} />
                    Sync watch
                  </button>
                </div>
              </div>
              <section className="panel history-panel">
                {records.filter((r) => filter === "all" || r.kind === filter)
                  .length === 0 ? (
                  <Empty
                    icon={<Database size={29} />}
                    title="No records here yet"
                    text="Connect a watch and sync its stored records. A freshly reset watch may have no history to retrieve."
                  />
                ) : (
                  <div className="records-list">
                    {records
                      .filter((r) => filter === "all" || r.kind === filter)
                      .map((row) => (
                        <div className="record-row" key={row.id}>
                          <div className={"record-icon " + row.kind}>
                            {row.kind === "oxygen" ? (
                              <Waves size={21} />
                            ) : row.kind === "stress" ? (
                              <Activity size={21} />
                            ) : (
                              <Watch size={21} />
                            )}
                          </div>
                          <div>
                            <strong>
                              {row.kind === "oxygen"
                                ? "Blood oxygen"
                                : row.kind === "stress"
                                  ? "Stress"
                                  : "Workout"}
                            </strong>
                            <small>
                              {String(row.data.time || row.received_at)} ·{" "}
                              {String(row.data.origin || "watch")}
                            </small>
                          </div>
                          <div className="record-value">
                            {row.kind === "workout"
                              ? `${row.data.steps ?? "—"} steps`
                              : `${row.data.value ?? "—"}${row.kind === "oxygen" ? "%" : ""}`}
                            <small>
                              {row.kind === "workout"
                                ? `${row.data.elapsed_seconds ?? "—"} sec · distance ${row.data.distance_raw ?? "—"} raw`
                                : "Stored record"}
                            </small>
                          </div>
                          <details>
                            <summary>Details</summary>
                            <pre>{JSON.stringify(row.data, null, 2)}</pre>
                          </details>
                        </div>
                      ))}
                  </div>
                )}
              </section>
            </>
          )}
          {tab === "controls" && (
            <>
              <PageTitle
                eyebrow="READ. CHANGE. VERIFY."
                title="Watch controls"
                subtitle="Setting changes are read back from the watch. Firmware changes and resets are excluded."
              />
              {(!state.connected || state.demo || !state.profile_verified) && (
                <div className="inline-note">
                  <LockKeyhole size={16} />
                  {state.demo
                    ? "Preview is read-only."
                    : !state.connected
                      ? "Connect a supported watch to use controls."
                      : "Writes require the validated O20 firmware profile."}
                </div>
              )}
              <div className="controls-grid">
                <section className="panel">
                  <div className="section-heading">
                    <Target size={19} />
                    <h3>Everyday settings</h3>
                  </div>
                  <NumberSetting
                    label="Daily step goal"
                    value={Number(state.settings.goal) || 4000}
                    disabled={!writable}
                    save={(v) => setSetting("goal", v)}
                  />
                  <SelectSetting
                    label="Language"
                    value={Number(state.settings.language) || 0}
                    disabled={!writable}
                    options={[
                      [0, "English"],
                      [1, "Chinese"],
                      [2, "Japanese"],
                      [3, "Korean"],
                      [4, "German"],
                      [5, "French"],
                      [6, "Spanish"],
                      [7, "Arabic"],
                      [8, "Russian"],
                      [12, "Portuguese"],
                    ]}
                    save={(v) => setSetting("language", v)}
                  />
                  <SelectSetting
                    label="Time format byte"
                    value={Number(state.settings.time_format) || 0}
                    disabled={!writable}
                    options={[
                      [0, "Format 0"],
                      [1, "Format 1"],
                    ]}
                    save={(v) => setSetting("time_format", v)}
                  />
                  <SelectSetting
                    label="Measurement units byte"
                    value={Number(state.settings.units) || 0}
                    disabled={!writable}
                    options={[
                      [0, "Units 0"],
                      [1, "Units 1"],
                    ]}
                    save={(v) => setSetting("units", v)}
                  />
                  <SelectSetting
                    label="Raise-to-wake byte"
                    value={Number(state.settings.raise_wrist) || 0}
                    disabled={!writable}
                    options={[
                      [0, "State 0"],
                      [1, "State 1"],
                    ]}
                    save={(v) => setSetting("raise_wrist", v)}
                  />
                  <SelectSetting
                    label="Movement reminder"
                    value={Number(state.settings.sedentary) || 0}
                    disabled={!writable}
                    options={[
                      [0, "Off"],
                      [1, "On"],
                    ]}
                    save={(v) => setSetting("sedentary", v)}
                  />
                  <p className="footnote">
                    Raw enum labels remain explicit where on-watch meaning has
                    not been visually validated.
                  </p>
                </section>
                <section className="panel">
                  <div className="section-heading">
                    <Heart size={19} />
                    <h3>Measurements & signals</h3>
                  </div>
                  <p>
                    Live heart rate uses the standard Bluetooth stream. Fresh
                    live oxygen values remain experimental.
                  </p>
                  <div className="measure-buttons">
                    <button
                      className="button secondary"
                      disabled={!writable}
                      onClick={() =>
                        run("Starting heart rate", "measure", {
                          kind: "heart_rate",
                        })
                      }
                    >
                      <Heart size={16} />
                      Heart rate
                    </button>
                    <button
                      className="button secondary"
                      disabled={!writable}
                      onClick={() =>
                        run("Starting oxygen", "measure", { kind: "oxygen" })
                      }
                    >
                      <Waves size={16} />
                      Oxygen
                    </button>
                  </div>
                  <button
                    className="button stop"
                    disabled={!state.connected || !!busy || !state.measurement}
                    onClick={() =>
                      run("Stopping measurement", "measure", { kind: null })
                    }
                  >
                    <Square size={14} />
                    Stop measurement
                  </button>
                  <span className="footnote">
                    {state.measurement
                      ? `Active: ${state.measurement}`
                      : "No measurement started by this session."}
                  </span>
                  <hr />
                  <button
                    className="button secondary full"
                    disabled={!writable}
                    onClick={() =>
                      run(
                        "Sending find signal",
                        "find",
                        {},
                        "Find-watch signal sent. The device may play a sound without opening a screen.",
                      )
                    }
                  >
                    <Signal size={16} />
                    Find my watch
                  </button>
                  <button
                    className="button secondary full"
                    disabled={!writable}
                    onClick={() =>
                      run(
                        "Sending local test message",
                        "notify",
                        { text: "OpenWatch test" },
                        "Local test message sent. This is not a real SMS.",
                      )
                    }
                  >
                    <Bell size={16} />
                    Send a test notification
                  </button>
                  <SelectSetting
                    label="Built-in watch face"
                    value={Number(state.settings.watch_face) || 2}
                    disabled={!writable}
                    options={[
                      [2, "Face 2"],
                      [3, "Face 3"],
                    ]}
                    save={(v) => setSetting("watch_face", v)}
                  />
                </section>
              </div>
              <section className="panel alarm-panel">
                <div className="section-heading">
                  <Bell size={19} />
                  <h3>Smart alarms</h3>
                  <span className="subtle-badge">3 SLOTS</span>
                </div>
                <p>
                  Weekly alarms. Sunday is the first repeat day. Editing one
                  slot preserves the others.
                </p>
                <div className="alarms">
                  {[0, 1, 2].map((slot) => (
                    <AlarmEditor
                      key={`${slot}-${JSON.stringify(state.alarms[slot])}`}
                      slot={slot}
                      alarm={state.alarms[slot]}
                      disabled={!writable}
                      save={async (args) => {
                        await run(
                          "Saving and verifying alarm",
                          "set_alarm",
                          args,
                          "Alarm verified on the watch.",
                        );
                      }}
                    />
                  ))}
                </div>
              </section>
            </>
          )}
          {tab === "lab" && (
            <>
              <PageTitle
                eyebrow="A TOOLKIT, NOT A BLACK BOX"
                title="Device lab"
                subtitle="Inspect declared capabilities, GATT services, and this session’s packet traffic."
              />
              <div className="lab-grid">
                <section className="panel">
                  <div className="section-heading">
                    <ShieldCheck size={19} />
                    <h3>Capability map</h3>
                  </div>
                  {(state.capabilities.length ? state.capabilities : []).map(
                    (cap) => (
                      <div className="cap-row" key={cap.id}>
                        <div>
                          <strong>{cap.name}</strong>
                          {cap.note && <small>{cap.note}</small>}
                        </div>
                        <span className={"cap-status " + cap.status}>
                          {cap.status}
                        </span>
                      </div>
                    ),
                  )}
                  {!state.capabilities.length && (
                    <Empty
                      icon={<Link2 size={25} />}
                      title="Choose a device"
                      text="Capabilities appear only after a supported adapter is selected."
                    />
                  )}
                </section>
                <section className="panel">
                  <div className="section-heading">
                    <Bluetooth size={19} />
                    <h3>Device identity</h3>
                  </div>
                  {Object.entries(state.info).map(([key, value]) => (
                    <div className="info-row" key={key}>
                      <span>{key}</span>
                      <code>{value}</code>
                    </div>
                  ))}
                  <div className="info-row">
                    <span>Transport</span>
                    <code>CoreBluetooth / WinRT via Bleak</code>
                  </div>
                  <div className="info-row">
                    <span>Windows hardware</span>
                    <span className="cap-status partial">untested</span>
                  </div>
                  <div className="info-row">
                    <span>Fresh-host pairing</span>
                    <span className="cap-status partial">untested</span>
                  </div>
                  <p className="footnote">
                    Account-free operations passed after a watch reset on the
                    same Mac. Existing host Bluetooth state was not cleared.
                  </p>
                </section>
              </div>
              <section className="panel">
                <div className="section-heading">
                  <Code2 size={19} />
                  <h3>Bluetooth services</h3>
                </div>
                {state.services.map((service) => (
                  <details className="service-detail" key={service.uuid}>
                    <summary>
                      <code>{short(service.uuid)}</code>
                      <span>
                        {service.characteristics.length} characteristics
                      </span>
                    </summary>
                    {service.characteristics.map((char) => (
                      <div className="info-row" key={char.uuid}>
                        <code>{short(char.uuid)}</code>
                        <small>{char.properties.join(" · ")}</small>
                      </div>
                    ))}
                  </details>
                ))}
                {!state.services.length && (
                  <p>No real device service inventory loaded.</p>
                )}
              </section>
              <section className="panel packet-panel">
                <div className="section-heading">
                  <Terminal size={18} />
                  <h3>Packet inspector</h3>
                  <button
                    className="text-button"
                    onClick={() =>
                      invoke<Packet[]>("packets")
                        .then(setPackets)
                        .catch((e) => setError(String(e)))
                    }
                  >
                    Refresh log <RefreshCw size={14} />
                  </button>
                </div>
                <p>
                  Local, bounded to 200 fragments. Packets can contain health
                  values. This log is not included in observation exports.
                </p>
                <div className="packet-log">
                  {packets.length ? (
                    packets.map((packet, index) => (
                      <div key={index}>
                        <time>{packet.time.slice(11, 23)}</time>
                        <b className={packet.direction}>
                          {packet.direction.toUpperCase()}
                        </b>
                        <code>{packet.hex}</code>
                      </div>
                    ))
                  ) : (
                    <span>No packets captured in this session.</span>
                  )}
                </div>
              </section>
            </>
          )}
          {tab === "about" && (
            <>
              <PageTitle
                eyebrow="OPEN BY DESIGN"
                title="A starting point for the next watch."
                subtitle="OpenWatch Lab separates the interface, Bluetooth transport, and device protocol so each can evolve independently."
              />
              <div className="about-grid">
                <section className="panel">
                  <div className="panel-icon">
                    <Code2 size={23} />
                  </div>
                  <h3>Add an adapter, keep the app.</h3>
                  <p>
                    The adapter template and protocol specification live in the
                    source project. Synthetic fixtures let contributors test a
                    decoder without owning your device or accessing your health
                    data.
                  </p>
                  <div className="code-path">
                    adapter-template/ → adapters/ → capabilities
                  </div>
                  <p className="footnote">
                    Application: AGPL-3.0-or-later. Protocol/interface
                    documentation and synthetic fixtures: CC0-1.0. Gadgetbridge
                    is acknowledged as protocol reference material.
                  </p>
                </section>
                <section className="panel">
                  <div className="panel-icon">
                    <Database size={23} />
                  </div>
                  <h3>Your computer is the destination.</h3>
                  <p>
                    No login, telemetry, vendor SDK or cloud account. The app
                    uses a local SQLite database and exports only when you
                    choose to save a file.
                  </p>
                  <div className="storage-path">
                    {state.storage_path || "Local application-data directory"}
                  </div>
                </section>
              </div>
              <section className="panel">
                <h3>What this release establishes</h3>
                <p>
                  A functional first adapter and a desktop foundation. It is not
                  a universal watch standard, a medical instrument, or a claim
                  that every listed feature works on every firmware. Windows
                  packages require building and hardware testing on Windows.
                  Mobile transports are future work.
                </p>
                <p>
                  The Device lab keeps verified, partial, and unavailable
                  features distinct. Firmware replacement and watch resets are
                  deliberately outside this milestone.
                </p>
              </section>
            </>
          )}
          <footer>
            <span>
              <LockKeyhole size={12} />
              LOCAL FIRST. ACCOUNT FREE.
            </span>
            <span>OpenWatch Lab · Community foundation</span>
          </footer>
        </div>
      </main>
      {showDevices && (
        <div className="modal-backdrop">
          <section
            className="device-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="connect-title"
          >
            <button
              className="modal-close icon-button"
              aria-label="Close device picker"
              onClick={() => setShowDevices(false)}
            >
              <X size={20} />
            </button>
            <div className="panel-icon">
              <Bluetooth size={23} />
            </div>
            <h2 id="connect-title">Find your watch.</h2>
            <p>
              Nearby Bluetooth devices. O20 profiles are recognized from their
              advertisement; other devices are inspection-only.
            </p>
            <div className="device-results">
              {[
                ...devices,
                ...(state.known_devices || [])
                  .filter((d) => !devices.some((found) => found.id === d.id))
                  .map((d) => ({ ...d, supported: true })),
              ].map((device) => (
                <button
                  className="device-result"
                  key={device.id}
                  disabled={!!busy}
                  onClick={async () => {
                    const value = await run<State>(
                      "Connecting and reading watch",
                      "connect",
                      { id: device.id },
                    );
                    if (value) {
                      setState(value);
                      setShowDevices(false);
                      setSamples([]);
                    }
                  }}
                >
                  <Watch size={23} />
                  <div>
                    <strong>{device.name}</strong>
                    <small>
                      {device.supported
                        ? "O20 adapter available"
                        : "Inspect services only"}
                    </small>
                  </div>
                  <span>
                    {device.rssi == null
                      ? "Saved device"
                      : `${device.rssi} dBm`}
                  </span>
                  <ChevronRight size={16} />
                </button>
              ))}
              {!devices.length && (
                <Empty
                  icon={
                    busy ? (
                      <LoaderCircle className="spin" size={25} />
                    ) : (
                      <Bluetooth size={25} />
                    )
                  }
                  title={busy ? "Listening nearby…" : "No devices found"}
                  text="Keep the watch awake and close to your computer. Allow Bluetooth access if the system asks."
                />
              )}
            </div>
            <div className="modal-bottom">
              <button
                className="button secondary"
                disabled={!!busy}
                onClick={scan}
              >
                <RefreshCw size={15} />
                Scan again
              </button>
              <button className="text-button" disabled={!!busy} onClick={demo}>
                Use synthetic preview <ArrowRight size={14} />
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
function PageTitle({
  eyebrow,
  title,
  subtitle,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="page-heading simple">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
    </div>
  );
}
function Metric({
  title,
  icon,
  value,
  unit,
  subtitle,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  value: string;
  unit: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <section className="metric">
      <div className="metric-heading">
        <span>{title}</span>
        {icon}
      </div>
      <div className="metric-number">
        {value}
        <small>{unit}</small>
      </div>
      <p>{subtitle}</p>
      {children}
    </section>
  );
}
function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2)
    return (
      <div className="no-stream">
        <span />
        <span />
        <span />
        <span />
        <span />
      </div>
    );
  const min = Math.min(...values) - 4,
    max = Math.max(...values) + 4;
  return (
    <svg
      className="sparkline"
      viewBox="0 0 250 35"
      preserveAspectRatio="none"
      aria-label="Recent heart-rate trend"
    >
      <polyline
        points={values
          .map(
            (v, i) =>
              `${(i / (values.length - 1)) * 250},${33 - ((v - min) / (max - min)) * 30}`,
          )
          .join(" ")}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      />
    </svg>
  );
}
function Empty({
  icon,
  title,
  text,
}: {
  icon: React.ReactNode;
  title: string;
  text: string;
}) {
  return (
    <div className="empty">
      <div>{icon}</div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}
function NumberSetting({
  label,
  value,
  disabled,
  save,
}: {
  label: string;
  value: number;
  disabled: boolean;
  save: (v: number) => void;
}) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  return (
    <div className="setting-row">
      <label htmlFor="step-goal">{label}</label>
      <div className="inline-input">
        <input
          id="step-goal"
          type="number"
          min="100"
          max="100000"
          step="100"
          disabled={disabled}
          value={draft}
          onChange={(e) => setDraft(Number(e.target.value))}
        />
        <button
          className="small-button"
          disabled={
            disabled ||
            draft === value ||
            !Number.isInteger(draft) ||
            draft < 100 ||
            draft > 100000
          }
          onClick={() => save(draft)}
        >
          Save
        </button>
      </div>
    </div>
  );
}
function SelectSetting({
  label,
  value,
  disabled,
  options,
  save,
}: {
  label: string;
  value: number;
  disabled: boolean;
  options: [number, string][];
  save: (v: number) => void;
}) {
  return (
    <div className="setting-row">
      <label>{label}</label>
      <select
        aria-label={label}
        value={value}
        disabled={disabled}
        onChange={(e) => save(Number(e.target.value))}
      >
        {!options.some((o) => o[0] === value) && (
          <option value={value}>Device value {value}</option>
        )}
        {options.map(([v, name]) => (
          <option key={v} value={v}>
            {name}
          </option>
        ))}
      </select>
    </div>
  );
}
function AlarmEditor({
  slot,
  alarm,
  disabled,
  save,
}: {
  slot: number;
  alarm?: Alarm;
  disabled: boolean;
  save: (args: Record<string, unknown>) => Promise<void>;
}) {
  const [time, setTime] = useState(
      `${String(alarm?.hour ?? 7).padStart(2, "0")}:${String(alarm?.minute || 0).padStart(2, "0")}`,
    ),
    [days, setDays] = useState(alarm?.weekdays || 62),
    [enabled, setEnabled] = useState(alarm?.enabled ?? true);
  const submit = (clear = false) => {
    const [hour, minute] = time.split(":").map(Number);
    return save({
      slot,
      enabled: clear ? false : enabled,
      hour,
      minute,
      weekdays: days,
      clear,
    });
  };
  return (
    <div className="alarm-editor">
      <div className="alarm-title">
        <span>SLOT {slot + 1}</span>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={enabled}
            disabled={disabled}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          Enabled
        </label>
      </div>
      <input
        className="alarm-time"
        aria-label={`Alarm slot ${slot + 1} time`}
        type="time"
        value={time}
        disabled={disabled}
        onChange={(e) => setTime(e.target.value)}
      />
      <div className="days">
        {dayNames.map((day, index) => (
          <button
            key={day}
            title={day}
            aria-label={`${day} alarm slot ${slot + 1}`}
            aria-pressed={!!(days & (1 << index))}
            className={days & (1 << index) ? "chosen" : ""}
            disabled={disabled}
            onClick={() => setDays(days ^ (1 << index))}
          >
            {day[0]}
          </button>
        ))}
      </div>
      <div className="alarm-actions">
        <button
          className="small-button"
          disabled={disabled || !days || !/^\d\d:\d\d$/.test(time)}
          onClick={() => submit()}
        >
          Save & verify
        </button>
        <button
          className="text-button"
          disabled={disabled || !alarm || alarm.empty}
          onClick={() => submit(true)}
        >
          Clear
        </button>
      </div>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
