import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { connect } from "../lib/realtime/client";
class Socket {
  static OPEN = 1;
  static instances: Socket[] = [];
  readyState = 1;
  sent: string[] = [];
  closed = false;
  onopen: () => void = () => {};
  onclose: () => void = () => {};
  onerror: () => void = () => {};
  onmessage: (event: { data: string }) => void = () => {};
  constructor(public url: string) {
    Socket.instances.push(this);
  }
  send(frame: string) {
    this.sent.push(frame);
  }
  close() {
    this.closed = true;
    this.onclose();
  }
  frame(seq: number) {
    this.onmessage({
      data: JSON.stringify({
        protocol_version: 1,
        type: "message.created",
        event_id: "11111111-1111-4111-8111-111111111111",
        conversation_id: "22222222-2222-4222-8222-222222222222",
        seq,
        occurred_at: "2026-10-29T00:00:00Z",
        data: { body: "fixture" },
      }),
    });
  }
}
const flush = async () => {
  for (let i = 0; i < 10; i++) await Promise.resolve();
};
beforeEach(() => {
  vi.useFakeTimers();
  Socket.instances = [];
  vi.stubGlobal("WebSocket", Socket);
  vi.stubGlobal("location", { protocol: "http:", host: "localhost:5173" });
  vi.stubGlobal("window", new EventTarget());
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
describe("committed replay cursor", () => {
  it("applies duplicates once and reconnects from the last applied sequence after a gap", async () => {
    const applied: number[] = [];
    const stop = connect(
      "customer",
      "workspace",
      "22222222-2222-4222-8222-222222222222",
      0,
      async (event) => {
        applied.push(event.seq);
      },
      () => {},
      () => {},
    );
    const socket = Socket.instances[0];
    socket.onopen();
    socket.frame(1);
    socket.frame(1);
    await flush();
    expect(applied).toEqual([1]);
    socket.frame(3);
    await flush();
    expect(socket.closed).toBe(true);
    await vi.advanceTimersByTimeAsync(2000);
    const resumed = Socket.instances[1];
    resumed.onopen();
    expect(JSON.parse(resumed.sent[0]).after_seq).toBe(1);
    expect(resumed.url).not.toContain("token");
    stop();
  });
  it("does not acknowledge an event whose cache application failed", async () => {
    const stop = connect(
      "staff",
      "workspace",
      "22222222-2222-4222-8222-222222222222",
      4,
      async () => {
        throw Error("cache unavailable");
      },
      () => {},
      () => {},
    );
    const socket = Socket.instances[0];
    socket.onopen();
    socket.frame(5);
    await flush();
    expect(socket.closed).toBe(true);
    await vi.advanceTimersByTimeAsync(2000);
    const resumed = Socket.instances[1];
    resumed.onopen();
    expect(JSON.parse(resumed.sent[0]).after_seq).toBe(4);
    stop();
  });
});
