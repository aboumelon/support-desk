import { describe, expect, it, vi } from "vitest";
import { documentPresentation } from "../features/knowledge/presentation";
import {
  eventLabel,
  responsibility,
  type Conversation,
  type Event,
} from "../features/conversation/presentation";
import { singleFlight } from "../lib/single-flight";

describe("backend-owned presentation", () => {
  it("keeps an older active version usable while its replacement processes or fails", () => {
    const version = {
      id: "old",
      version_no: 1,
      status: "ready",
      error_code: null,
      embedding_revision: "pinned",
    };
    const doc = {
      id: "doc",
      title: "Fixture",
      active_version_id: "old",
      withdrawn_at: null,
      versions: [
        { ...version, id: "new", version_no: 2, status: "processing" },
        version,
      ],
    };
    expect(documentPresentation(doc).active?.id).toBe("old");
    expect(documentPresentation(doc).usable).toBe(true);
    doc.versions[0].status = "failed";
    expect(documentPresentation(doc).usable).toBe(true);
    expect(
      documentPresentation({ ...doc, withdrawn_at: "2026-10-29T00:00:00Z" })
        .usable,
    ).toBe(false);
  });
  it("uses authenticated assignment and never manufactures a historical handoff actor", () => {
    const conversation = {
      status: "open",
      controller: "human",
      assigned_actor_id: "another-actor",
    } as Conversation;
    expect(responsibility(conversation, "me")).toBe("other");
    const legacy: Event = {
      protocol_version: 1,
      event_id: "event",
      conversation_id: "conversation",
      occurred_at: "2026-10-29T00:00:00Z",
      seq: 4,
      type: "conversation.control_changed",
      data: { controller: "queue" },
    };
    expect(eventLabel(legacy, "human")).toBe("timeline_release");
    expect(eventLabel(legacy, "bot")).toBe("timeline_handoff");
    expect(
      eventLabel({
        ...legacy,
        data: { controller: "queue", action: "release" },
      }),
    ).toBe("timeline_release");
  });
  it("coalesces concurrent retries and permits a later retry after transport failure", async () => {
    let complete!: () => void;
    const run = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          complete = resolve;
        }),
    );
    const first = singleFlight("stable-message-identity", run);
    const second = singleFlight("stable-message-identity", run);
    await Promise.resolve();
    expect(run).toHaveBeenCalledTimes(1);
    expect(first).toBe(second);
    complete();
    await first;
    await expect(
      singleFlight("stable-message-identity", async () => {
        throw Error("network");
      }),
    ).rejects.toThrow("network");
    const retry = vi.fn(async () => {});
    await singleFlight("stable-message-identity", retry);
    expect(retry).toHaveBeenCalledTimes(1);
  });
});
