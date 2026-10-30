import { describe, expect, it } from "vitest";
import Ajv from "ajv";
import schema from "../../../../contracts/realtime.schema.json";
import validate from "../generated/realtime.validator.mjs";

const reference = new Ajv({ strict: false, validateFormats: false }).compile(
  schema,
);
const identity = {
  protocol_version: 1,
  conversation_id: "00000000-0000-0000-0000-000000000001",
};
const delta = {
  ...identity,
  type: "ai.delta",
  run_id: "00000000-0000-0000-0000-000000000002",
  control_epoch: 0,
  attempt: 1,
  chunk_index: 0,
  text: "پیام",
};
const durable = {
  ...identity,
  type: "message.created",
  event_id: "00000000-0000-0000-0000-000000000003",
  seq: 1,
  occurred_at: "2026-10-30T00:00:00Z",
  data: {
    message_id: "example",
    control_epoch: 0,
    visible: true,
    optional: null,
  },
};

describe("standalone realtime validator", () => {
  it.each([
    ["durable event", durable, true],
    ["AI delta", delta, true],
    [
      "typing",
      { ...identity, type: "typing.updated", actor_id: "actor", expires_in: 5 },
      true,
    ],
    [
      "presence",
      {
        ...identity,
        type: "presence.updated",
        actor_id: "actor",
        online: true,
      },
      true,
    ],
    ["future protocol", { ...delta, protocol_version: 2 }, false],
    ["missing required field", { ...delta, run_id: undefined }, false],
    ["invalid attempt", { ...delta, attempt: 4 }, false],
    ["negative chunk", { ...delta, chunk_index: -1 }, false],
    ["zero sequence", { ...durable, seq: 0 }, false],
    ["noninteger sequence", { ...durable, seq: 1.5 }, false],
    ["nested event data", { ...durable, data: { nested: {} } }, false],
    ["Unicode length boundary", { ...delta, text: "😀".repeat(8000) }, true],
    ["Unicode length exceeded", { ...delta, text: "😀".repeat(8001) }, false],
    ["null", null, false],
  ])("matches the schema for %s", (_name, frame, accepted) => {
    expect(validate(frame)).toBe(accepted);
    expect(validate(frame)).toBe(reference(frame));
  });
});
