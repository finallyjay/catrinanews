// Records the site while the Catrina reads the broadside, for the demo video.
//
// Headless Chrome (muted) plays every calavera with "Listen to the broadside"; we
// capture screencast frames and the wall-clock moment each audio starts. Then
// scripts/montar_demo.py rebuilds the video with ffmpeg and lays the original MP3s
// at those moments, so lips (well, jaw) and voice line up.
//
// Usage: node scripts/grabar_demo.mjs <chrome-debug-port> <url> <out-dir>

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const [port, url, outDir] = process.argv.slice(2);
mkdirSync(join(outDir, "frames"), { recursive: true });

const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
const ws = new WebSocket(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));

let id = 0;
const pending = new Map();
const handlers = {};
ws.addEventListener("message", (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  } else if (msg.method && handlers[msg.method]) {
    handlers[msg.method](msg.params);
  }
});
const send = (method, params = {}) =>
  new Promise((resolve) => {
    const n = ++id;
    pending.set(n, resolve);
    ws.send(JSON.stringify({ id: n, method, params }));
  });
const evaluate = (expression) => send("Runtime.evaluate", { expression, awaitPromise: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const frames = [];
const events = [];
let done = false;

handlers["Page.screencastFrame"] = ({ data, metadata, sessionId }) => {
  const file = `f${String(frames.length).padStart(5, "0")}.jpg`;
  writeFileSync(join(outDir, "frames", file), Buffer.from(data, "base64"));
  frames.push({ file, t: metadata.timestamp });
  send("Page.screencastFrameAck", { sessionId });
};
handlers["Runtime.bindingCalled"] = ({ name, payload }) => {
  const [kind, index] = payload.split(":");
  events.push({ kind, index: Number(index), t: Date.now() / 1000 });
  if (kind === "ended" && Number(index) === lastIndex) done = true;
};

await send("Page.enable");
await send("Runtime.enable");
await send("Runtime.addBinding", { name: "reportar" });
await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url });
await sleep(2500);

// English UI for the judges, and a hook on every audio's play/ended.
await evaluate(`setLang("en"); window.scrollTo(0, 0);`);
const lastIndex = (await evaluate(`document.querySelectorAll("audio").length - 1`)).result.result.value;
await evaluate(`
  document.querySelectorAll("audio").forEach(function (a, i) {
    a.addEventListener("play", function () { reportar("play:" + i); });
    a.addEventListener("ended", function () { reportar("ended:" + i); });
  });
`);

await send("Page.startScreencast", { format: "jpeg", quality: 85, maxWidth: 1280, maxHeight: 720 });
const start = Date.now() / 1000;
await sleep(2500); // a moment on the masthead before she starts
await evaluate(`escucharHoja()`);

const deadline = Date.now() + 10 * 60 * 1000;
while (!done && Date.now() < deadline) await sleep(250);
await sleep(2000);
await send("Page.stopScreencast");
const end = Date.now() / 1000;

writeFileSync(join(outDir, "timeline.json"), JSON.stringify({ start, end, frames, events }, null, 2));
console.log(`${frames.length} frames, ${events.filter((e) => e.kind === "play").length} clips, ${(end - start).toFixed(1)} s`);
ws.close();
process.exit(0);
