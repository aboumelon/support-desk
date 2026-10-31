import { getDraft, setDraft } from "../../lib/composer-drafts";

export const STAFF_SINGLE_PANE = "(max-width: 1119px)";
export const inboxFilters = ["open", "queue", "mine", "resolved"] as const;
export type InboxFilter = (typeof inboxFilters)[number];
export type InboxView = { filter: InboxFilter; query: string };

// UI-only state shares the existing actor/workspace-scoped, logout-cleared storage.
export function readInboxView(scope: string): InboxView {
  try {
    const value = JSON.parse(getDraft(`${scope}:inbox-view`));
    return {
      filter: inboxFilters.includes(value?.filter) ? value.filter : "open",
      query: typeof value?.query === "string" ? value.query.slice(0, 120) : "",
    };
  } catch {
    return { filter: "open", query: "" };
  }
}
export function saveInboxView(scope: string, view: InboxView) {
  setDraft(`${scope}:inbox-view`, JSON.stringify(view));
}

export type PanePosition = {
  top: number;
  bottom: boolean;
  anchor?: string;
  offset?: number;
};
export function readPanePosition(scope: string): PanePosition | null {
  try {
    const value = JSON.parse(getDraft(`${scope}:scroll`));
    if (
      !value ||
      !Number.isFinite(value.top) ||
      value.top < 0 ||
      typeof value.bottom !== "boolean"
    )
      return null;
    return {
      top: value.top,
      bottom: value.bottom,
      anchor: typeof value.anchor === "string" ? value.anchor : undefined,
      offset: Number.isFinite(value.offset) ? value.offset : undefined,
    };
  } catch {
    return null;
  }
}
export function savePanePosition(scope: string, position: PanePosition) {
  setDraft(`${scope}:scroll`, JSON.stringify(position));
}
