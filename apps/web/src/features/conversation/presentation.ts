import type { components } from "@supportdesk/api-client";
export type Session = components["schemas"]["SessionView"];
export type Conversation = components["schemas"]["ConversationView"];
export type Message = components["schemas"]["MessageView"];
export type Event = components["schemas"]["DurableEvent"];
export type Snapshot = components["schemas"]["Snapshot"];
export type Audience = "customer" | "staff";
export const reference = (id: string) => id.slice(0, 8).toUpperCase();
export const actorFor = (session: Session, workspace: string) =>
  session.actor_id ??
  session.memberships.find((m) => m.workspace_id === workspace)?.actor_id;
export function responsibility(
  conversation: Conversation,
  actor?: string,
  run?: Snapshot["active_run"],
) {
  if (conversation.status === "resolved") return "resolved";
  if (conversation.controller === "queue") return "queue";
  if (conversation.controller === "human")
    return conversation.assigned_actor_id === actor ? "me" : "other";
  return run && ["running", "queued"].includes(run.status)
    ? "generating"
    : "bot";
}
export const messageRole = (message: Message) =>
  message.sender_kind === "visitor"
    ? "customer"
    : message.sender_kind === "assistant"
      ? "assistant"
      : "operator";
export const formatTime = (value: string) =>
  new Intl.DateTimeFormat("fa-IR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
export const formatDate = (value: string) =>
  new Intl.DateTimeFormat("fa-IR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date(value));
export function eventLabel(event: Event, previous?: string) {
  if (event.type === "conversation.resolved") return "timeline_resolve";
  if (event.type === "conversation.reopened") return "timeline_reopen";
  if (event.type !== "conversation.control_changed") return null;
  const action = event.data.action;
  if (
    typeof action === "string" &&
    ["handoff", "claim", "release", "reassign", "return-to-bot"].includes(
      action,
    )
  )
    return `timeline_${action}`;
  // Legacy events have no action: only describe the persisted transition we know.
  if (event.data.controller === "queue")
    return previous === "human" ? "timeline_release" : "timeline_handoff";
  if (event.data.controller === "human")
    return previous === "human" ? "timeline_reassign" : "timeline_claim";
  if (event.data.controller === "bot") return "timeline_return-to-bot";
  return "timeline_control";
}
