"use strict";
const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("node:path");
const fs = require("node:fs/promises");
const { existsSync } = require("node:fs");
const { pathToFileURL } = require("node:url");
const { Backend, validate } = require("./bridge.cjs");
let window,
  backend,
  exiting = false;
const root = path.resolve(__dirname, "..");
const indexUrl = pathToFileURL(path.join(root, "dist", "index.html")).href;
function backendLaunch() {
  if (app.isPackaged)
    return [
      path.join(
        process.resourcesPath,
        "backend",
        "openwatch-backend",
        process.platform === "win32"
          ? "openwatch-backend.exe"
          : "openwatch-backend",
      ),
      [],
    ];
  const local = path.join(
    root,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
  return [
    process.env.OPENWATCH_PYTHON ||
      (existsSync(local)
        ? local
        : process.platform === "win32"
          ? "python"
          : "python3"),
    ["-m", "openwatch.server"],
  ];
}
function trusted(event) {
  if (
    !window ||
    event.sender !== window.webContents ||
    event.senderFrame?.url !== indexUrl
  )
    throw new Error("Untrusted IPC sender");
}
const primary = app.requestSingleInstanceLock();
if (!primary) app.quit();
app.on("second-instance", () => {
  if (window) {
    if (window.isMinimized()) window.restore();
    window.show();
    window.focus();
  }
});
app
  .whenReady()
  .then(() => {
    if (!primary) return;
    const [command, args] = backendLaunch();
    backend = new Backend(
      command,
      [...args, "--data-dir", app.getPath("userData")],
      { cwd: app.isPackaged ? process.resourcesPath : root },
    );
    backend.on("event", (message) => {
      if (window && !window.isDestroyed())
        window.webContents.send("watch:event", message);
    });
    backend.on("diagnostic", (message) => {
      if (window && !window.isDestroyed())
        window.webContents.send("watch:event", {
          event: "diagnostic",
          data: { message },
        });
    });
    ipcMain.handle("watch:command", async (event, command, args = {}) => {
      trusted(event);
      validate(command, args);
      if (command === "export") {
        const choice = await dialog.showSaveDialog(window, {
          defaultPath: "openwatch-observations.json",
          filters: [{ name: "JSON observations", extensions: ["json"] }],
        });
        if (choice.canceled || !choice.filePath) return { canceled: true };
        const data = await backend.request("export");
        await fs.writeFile(choice.filePath, JSON.stringify(data, null, 2), {
          mode: 0o600,
        });
        return { saved: true };
      }
      return backend.request(command, args);
    });
    window = new BrowserWindow({
      width: 1230,
      height: 850,
      minWidth: 980,
      minHeight: 700,
      title: "OpenWatch Lab",
      backgroundColor: "#f5f5ef",
      webPreferences: {
        preload: path.join(__dirname, "preload.cjs"),
        contextIsolation: true,
        sandbox: true,
        nodeIntegration: false,
        webSecurity: true,
        spellcheck: false,
      },
    });
    window.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
    window.webContents.on("will-navigate", (event, url) => {
      if (url !== indexUrl) event.preventDefault();
    });
    window.loadFile(path.join(root, "dist", "index.html"));
    window.on("closed", () => {
      window = null;
    });
    app.on("activate", () => {
      if (window) window.show();
    });
  })
  .catch((error) => {
    dialog.showErrorBox("OpenWatch Lab could not start", error.message);
    app.quit();
  });
app.on("window-all-closed", () => app.quit());
app.on("before-quit", (event) => {
  if (!backend || exiting) return;
  event.preventDefault();
  exiting = true;
  Promise.race([
    backend.request("disconnect").catch(() => {}),
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ]).finally(() => {
    backend.close();
    app.quit();
  });
});
