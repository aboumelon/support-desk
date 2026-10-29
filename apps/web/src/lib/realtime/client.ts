import Ajv from "ajv";
import schema from "../../../../../packages/api-client/src/generated/realtime.schema.json";
import type {
  DurableEvent,
  AiDelta,
  TypingUpdate,
  PresenceUpdate,
} from "../../../../../packages/api-client/src/generated/realtime";
const validate = new Ajv({ strict: false, validateFormats: false }).compile(
  schema,
);
export function connect(
  audience: "customer" | "staff",
  workspace: string,
  conversation: string,
  initialCursor: number,
  onEvent: (event: DurableEvent) => Promise<void>,
  onStatus: (status: boolean) => void,
  onEphemeral: (event: AiDelta | TypingUpdate | PresenceUpdate) => void,
) {
  let stopped = false;
  let socket: WebSocket;
  let timer: ReturnType<typeof setTimeout>;
  let cursor = initialCursor;
  let attempts = 0;
  let chain = Promise.resolve();
  function start() {
    if (stopped) return;
    socket = new WebSocket(
      `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/api/v1/realtime/${audience}${audience === "staff" ? `?workspace_id=${workspace}` : ""}`,
    );
    socket.onopen = () => {
      attempts = 0;
      onStatus(true);
      socket.send(
        JSON.stringify({
          protocol_version: 1,
          type: "subscribe",
          conversation_id: conversation,
          after_seq: cursor,
        }),
      );
    };
    socket.onmessage = (event) => {
      let frame: Record<string, unknown>;
      try {
        frame = JSON.parse(event.data);
      } catch {
        return;
      }
      if (frame.protocol_version !== 1) return;
      if (frame.type === "ping") {
        socket.send(JSON.stringify({ protocol_version: 1, type: "pong" }));
        return;
      }
      if (frame.type === "RESET_REQUIRED") {
        location.reload();
        return;
      }
      if (!validate(frame)) return;
      if (!("seq" in frame)) {
        onEphemeral(
          frame as unknown as AiDelta | TypingUpdate | PresenceUpdate,
        );
        return;
      }
      const durable = frame as unknown as DurableEvent;
      chain = chain
        .then(async () => {
          if (durable.seq <= cursor) return;
          if (durable.seq !== cursor + 1) {
            socket.close();
            return;
          }
          await onEvent(durable);
          cursor = durable.seq;
        })
        .catch(() => socket.close());
    };
    socket.onclose = () => {
      onStatus(false);
      if (!stopped)
        timer = setTimeout(
          start,
          Math.min(15000, 500 * 2 ** attempts++) * (0.7 + Math.random() * 0.6),
        );
    };
    socket.onerror = () => socket.close();
  }
  function online() {
    clearTimeout(timer);
    socket?.close();
  }
  window.addEventListener("online", online);
  start();
  const disconnect = () => {
    stopped = true;
    clearTimeout(timer);
    socket?.close();
    window.removeEventListener("online", online);
  };
  disconnect.typing = () => {
    if (socket?.readyState === WebSocket.OPEN)
      socket.send(
        JSON.stringify({
          protocol_version: 1,
          type: "typing.updated",
          conversation_id: conversation,
        }),
      );
  };
  return disconnect;
}
