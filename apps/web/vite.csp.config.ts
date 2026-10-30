import { readFileSync } from "node:fs";
import { defineConfig } from "vite";

const caddyfile = readFileSync(
  new URL("../../deploy/Caddyfile", import.meta.url),
  "utf8",
);
const policy = caddyfile.match(/Content-Security-Policy "([^"]+)"/)?.[1];
if (!policy) throw Error("Production Caddy CSP is missing");

export default defineConfig({
  preview: {
    headers: { "Content-Security-Policy": policy },
    proxy: { "/api": { target: "http://127.0.0.1:8000", ws: true } },
  },
});
