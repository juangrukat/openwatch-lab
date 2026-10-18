export interface Device {
  id: string;
  name: string;
  supported?: boolean;
  adapter?: string;
  rssi?: number;
}
export interface Alarm {
  slot: number;
  enabled: boolean;
  hour: number;
  minute: number;
  weekdays: number;
  empty: boolean;
}
export interface Capability {
  id: string;
  name: string;
  status: "verified" | "partial" | "unverified" | "unavailable";
  write: boolean;
  note?: string;
}
export interface State {
  connected: boolean;
  demo: boolean;
  device?: Device | null;
  adapter?: string | null;
  profile_verified?: boolean;
  info: Record<string, string>;
  settings: Record<string, number | string | string[] | undefined>;
  alarms: Alarm[];
  battery?: { percent: number | null; charging: boolean };
  activity?: { steps: number; distance_raw: number; calories_raw: number };
  heart_rate?: { bpm: number; origin: string; received_at?: string } | null;
  measurement?: string | null;
  capabilities: Capability[];
  services: {
    uuid: string;
    characteristics: { uuid: string; properties: string[] }[];
  }[];
  known_devices?: Device[];
  storage_path?: string;
  warning?: string;
}
export interface Observation {
  id: number;
  device: string;
  kind: string;
  received_at: string;
  data: Record<string, unknown>;
}
export interface Packet {
  time: string;
  direction: string;
  hex: string;
}
export interface WatchEvent {
  event: string;
  data: Record<string, unknown>;
}
declare global {
  interface Window {
    watch?: {
      command<T = unknown>(
        name: string,
        args?: Record<string, unknown>,
      ): Promise<T>;
      subscribe(callback: (value: WatchEvent) => void): () => void;
    };
  }
}
