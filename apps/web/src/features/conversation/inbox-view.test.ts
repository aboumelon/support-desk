import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearDrafts, setDraft } from "../../lib/composer-drafts";
import {
  readInboxView,
  saveInboxView,
  readPanePosition,
  savePanePosition,
  STAFF_SINGLE_PANE,
} from "./inbox-view";

beforeEach(() => {
  const values: Record<string, string> = {};
  vi.stubGlobal("sessionStorage", {
    getItem: (key: string) => values[key] ?? null,
    setItem: (key: string, value: string) => {
      values[key] = value;
      Object.defineProperty(sessionStorage, key, {
        value,
        configurable: true,
        enumerable: true,
      });
    },
    removeItem: (key: string) => {
      delete values[key];
      delete (sessionStorage as unknown as Record<string, unknown>)[key];
    },
  });
});
afterEach(() => vi.unstubAllGlobals());
describe("scoped Inbox presentation state", () => {
  it("uses the approved single-pane boundary", () =>
    expect(STAFF_SINGLE_PANE).toBe("(max-width: 1119px)"));
  it("defaults safely and validates stored view state", () => {
    expect(readInboxView("staff:w:a")).toEqual({ filter: "open", query: "" });
    setDraft("staff:w:a:inbox-view", '{"filter":"invalid","query":123}');
    expect(readInboxView("staff:w:a")).toEqual({ filter: "open", query: "" });
    setDraft("staff:w:a:inbox-view", "not-json");
    expect(readInboxView("staff:w:a").filter).toBe("open");
  });
  it("does not leak view or scroll state between actors, workspaces or conversations", () => {
    saveInboxView("staff:w:a", { filter: "mine", query: "پیگیری" });
    savePanePosition("staff:w:a:c", {
      top: 120,
      bottom: false,
      anchor: "m1",
      offset: -12,
    });
    expect(readInboxView("staff:w:a").filter).toBe("mine");
    expect(readInboxView("staff:w:b").filter).toBe("open");
    expect(readInboxView("staff:other:a").query).toBe("");
    expect(readPanePosition("staff:w:a:c")?.anchor).toBe("m1");
    expect(readPanePosition("staff:w:a:other")).toBeNull();
    clearDrafts();
    expect(readPanePosition("staff:w:a:c")).toBeNull();
    expect(readInboxView("staff:w:a").query).toBe("");
  });
  it("ignores corrupt scroll data and denied storage", () => {
    setDraft("scope:scroll", '{"top":-10,"bottom":false}');
    expect(readPanePosition("scope")).toBeNull();
    vi.stubGlobal("sessionStorage", {
      getItem() {
        throw Error("denied");
      },
      setItem() {
        throw Error("denied");
      },
    });
    expect(readInboxView("scope").filter).toBe("open");
    expect(() =>
      saveInboxView("scope", { filter: "open", query: "" }),
    ).not.toThrow();
  });
});
