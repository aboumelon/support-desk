import http from "k6/http";
import ws from "k6/ws";
import { check, sleep } from "k6";
import { Trend, Counter } from "k6/metrics";
const clients = JSON.parse(open("../.local/benchmark-sessions.json"));
const commit = new Trend("message_commit_ms", true);
const delivery = new Trend("message_delivery_ms", true);
const failures = new Counter("message_failures");
const replayed = new Counter("durable_frames");
const duration = Number(__ENV.DURATION_SECONDS || 600);
const recovery = __ENV.RECOVERY === "1";
export const options = {
  scenarios: {
    chat: {
      executor: "per-vu-iterations",
      vus: 200,
      iterations: 1,
      maxDuration: `${duration + 40}s`,
    },
  },
  thresholds: {
    message_commit_ms: ["p(95)<300"],
    message_delivery_ms: recovery ? ["max<20000"] : ["p(95)<1000"],
    message_failures: ["count==0"],
  },
};
function uuid() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = Math.floor(Math.random() * 16);
    return (c === "x" ? r : (r & 3) | 8).toString(16);
  });
}
export default function () {
  const fixture = clients[__VU - 1];
  const started = Date.now();
  let cursor = 1;
  let nextSend = started + (__VU - 1) * 200;
  let reconnects = 0;
  let burstSent = false;
  const acknowledged = new Set();
  const received = new Set();
  failures.add(0);
  const origin = "http://localhost:5173";
  const base = `http://127.0.0.1:${__VU % 2 === 0 ? 19001 : 19002}`;
  const headers = {
    Origin: origin,
    Cookie: `sd_visitor=${fixture.token}`,
    "X-CSRF-Token": fixture.csrf,
  };
  while (Date.now() - started < duration * 1000) {
    const remaining = duration * 1000 - (Date.now() - started);
    const response = ws.connect(
      `${base.replace("http:", "ws:")}/api/v1/realtime/customer`,
      { headers },
      (socket) => {
        socket.on("open", () =>
          socket.send(
            JSON.stringify({
              protocol_version: 1,
              type: "subscribe",
              conversation_id: fixture.conversation,
              after_seq: cursor,
            }),
          ),
        );
        socket.on("message", (raw) => {
          const event = JSON.parse(raw);
          if (event.type === "ping")
            socket.send(JSON.stringify({ protocol_version: 1, type: "pong" }));
          if (event.seq) {
            cursor = Math.max(cursor, event.seq);
            replayed.add(1);
          }
          if (event.type === "message.created") {
            try {
              const body = JSON.parse(event.data.body);
              if (body.benchmarkClientId) received.add(body.benchmarkClientId);
              if (body.benchmarkSentAt)
                delivery.add(Date.now() - body.benchmarkSentAt);
            } catch {}
          }
        });
        socket.setInterval(() => {
          const elapsed = (Date.now() - started) / 1000;
          if (recovery && elapsed >= duration - 5) return;
          if (elapsed >= 240 && elapsed < 250) {
            if (burstSent || Date.now() < started + 240000 + (__VU - 1) * 50)
              return;
            burstSent = true;
          } else if (Date.now() < nextSend) return;
          const clientId = uuid();
          const body = {
            client_message_id: clientId,
            body: JSON.stringify({
              benchmarkSentAt: Date.now(),
              benchmarkClientId: clientId,
              client: __VU,
            }),
          };
          const result = http.post(
            `${base}/api/v1/customer/conversations/${fixture.conversation}/messages`,
            JSON.stringify(body),
            { headers: { ...headers, "Content-Type": "application/json" } },
          );
          commit.add(result.timings.duration);
          if (!check(result, { "message committed": (r) => r.status === 201 }))
            failures.add(1);
          else acknowledged.add(clientId);
          nextSend =
            Date.now() + (elapsed >= 240 && elapsed < 250 ? 10000 : 40000);
        }, 200);
        socket.setTimeout(
          () => socket.close(),
          Math.min(
            remaining,
            reconnects === 0
              ? (recovery ? duration * 500 : 300000) + (__VU % 20) * 200
              : remaining,
          ),
        );
      },
    );
    check(response, { "websocket connected": (r) => r && r.status === 101 });
    reconnects++;
    sleep(0.1);
  }
  if (recovery)
    check(null, {
      "all acknowledged messages delivered after recovery": () =>
        [...acknowledged].every((id) => received.has(id)),
    });
}
