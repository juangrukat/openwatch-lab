"use strict";
const { spawn } = require("node:child_process");
const { createInterface } = require("node:readline");
const { EventEmitter } = require("node:events");
class Backend extends EventEmitter {
  constructor(command, args, options = {}) {
    super();
    this.next = 1;
    this.pending = new Map();
    this.stopped = false;
    this.child = spawn(command, args, {
      ...options,
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });
    createInterface({ input: this.child.stdout }).on("line", (line) => {
      try {
        if (line.length > 2_000_000)
          throw new Error("Backend response exceeds limit");
        const msg = JSON.parse(line);
        if (msg.event) this.emit("event", msg);
        else if (this.pending.has(msg.id)) {
          const entry = this.pending.get(msg.id);
          clearTimeout(entry.timer);
          this.pending.delete(msg.id);
          if (msg.error) entry.reject(new Error(msg.error.message));
          else entry.resolve(msg.result);
        }
      } catch (error) {
        this.emit("diagnostic", error.message);
      }
    });
    this.child.stderr.on("data", (data) =>
      this.emit("diagnostic", data.toString().slice(0, 4000)),
    );
    this.child.on("error", (error) => this.fail(error));
    this.child.on("exit", (code, signal) => {
      this.stopped = true;
      this.fail(
        new Error(
          `Bluetooth backend stopped (${signal || code}). Restart the app to reconnect.`,
        ),
      );
      this.emit("event", { event: "backend_exit", data: { code, signal } });
    });
  }
  fail(error) {
    for (const entry of this.pending.values()) {
      clearTimeout(entry.timer);
      entry.reject(error);
    }
    this.pending.clear();
  }
  request(command, args = {}) {
    if (this.stopped || !this.child.stdin.writable)
      return Promise.reject(new Error("Bluetooth backend is unavailable"));
    const id = this.next++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error("Operation timed out. Check the watch connection."));
      }, 90_000);
      this.pending.set(id, { resolve, reject, timer });
      this.child.stdin.write(
        JSON.stringify({ id, command, args }) + "\n",
        (error) => {
          if (error) {
            clearTimeout(timer);
            this.pending.delete(id);
            reject(error);
          }
        },
      );
    });
  }
  close() {
    this.child.stdin.end();
    const timer = setTimeout(() => this.child.kill(), 4000);
    timer.unref();
  }
}
const COMMANDS = new Set([
  "state",
  "scan",
  "connect",
  "disconnect",
  "demo",
  "refresh",
  "sync",
  "history",
  "packets",
  "export",
  "set_setting",
  "set_alarm",
  "measure",
  "notify",
  "find",
  "background_stage",
  "background_start",
  "background_cancel",
]);
function validate(command, args) {
  if (!COMMANDS.has(command)) throw new Error("Unsupported app command");
  if (!args || typeof args !== "object" || Array.isArray(args))
    throw new Error("Arguments must be an object");
  if (JSON.stringify(args).length > 8192)
    throw new Error("Arguments exceed size limit");
}
module.exports = { Backend, validate };
