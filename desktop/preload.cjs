"use strict";
const { contextBridge, ipcRenderer } = require("electron");
const allowed = new Set([
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
]);
contextBridge.exposeInMainWorld("watch", {
  command(name, args = {}) {
    if (!allowed.has(name))
      return Promise.reject(new Error("Unsupported app command"));
    return ipcRenderer.invoke("watch:command", name, args);
  },
  subscribe(callback) {
    const listener = (_event, value) => callback(value);
    ipcRenderer.on("watch:event", listener);
    return () => ipcRenderer.removeListener("watch:event", listener);
  },
});
