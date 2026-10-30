import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { MessageMarkdown } from "../../lib/markdown";
import { Button, Icon } from "../../components/ui";
import {
  eventLabel,
  formatDate,
  formatTime,
  messageRole,
  type Event,
} from "./presentation";
import type { useConversation } from "./use-conversation";
import type { SourceSelection } from "./source-inspector";
export type ConversationState = ReturnType<typeof useConversation>;
export function Timeline({
  state,
  selection,
  onSource,
}: {
  state: ConversationState;
  selection: SourceSelection | null;
  onSource: (messageId: string, label: string) => void;
}) {
  const { t } = useTranslation();
  const viewport = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const nearBottom = useRef(true);
  const prepending = useRef<{ height: number; top: number } | null>(null);
  const [newMessages, setNewMessages] = useState(false);
  const persisted =
    state.events.data?.pages.flatMap((page) => page.items) ?? [];
  let previousController: string | undefined;
  const controlEvents = persisted
    .map((event) => {
      const label = eventLabel(event, previousController);
      if (typeof event.data.controller === "string")
        previousController = event.data.controller;
      return { event, label };
    })
    .filter(
      (item): item is { event: Event; label: string } => item.label !== null,
    );
  const firstSeq = state.messages[0]?.event_seq ?? 0;
  const items = [
    ...state.messages.map((message) => ({
      kind: "message" as const,
      seq: message.event_seq,
      id: message.id,
      time: message.created_at,
      message,
    })),
    ...controlEvents
      .filter((item) => !state.hasOlder || item.event.seq >= firstSeq)
      .map(({ event, label }) => ({
        kind: "event" as const,
        seq: event.seq,
        id: event.event_id,
        time: event.occurred_at,
        label,
      })),
  ].sort((a, b) => a.seq - b.seq);
  const signature = `${items[0]?.id}:${items.at(-1)?.id}:${state.pending.length}:${state.draft?.text.length ?? 0}`;
  const latest = () => {
    nearBottom.current = true;
    const el = viewport.current;
    if (el) el.scrollTop = el.scrollHeight;
    setNewMessages(false);
    void state.markRead();
  };
  useLayoutEffect(() => {
    const el = viewport.current;
    if (!el) return;
    if (prepending.current) {
      el.scrollTop =
        prepending.current.top + el.scrollHeight - prepending.current.height;
      prepending.current = null;
      return;
    }
    if (nearBottom.current) latest();
    else setNewMessages(true);
  }, [signature]);
  const markRead = useRef(state.markRead);
  markRead.current = state.markRead;
  useEffect(() => {
    const observer = new ResizeObserver(() => {
      if (nearBottom.current) {
        const el = viewport.current;
        if (el) el.scrollTop = el.scrollHeight;
      }
    });
    if (content.current) observer.observe(content.current);
    const visible = () => {
      if (nearBottom.current) void markRead.current();
    };
    document.addEventListener("visibilitychange", visible);
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", visible);
    };
  }, []);
  useEffect(() => {
    if (nearBottom.current) void state.markRead();
  }, [state.messages.at(-1)?.event_seq]);
  let previousDate = "";
  return (
    <div
      className="messages-scroll"
      ref={viewport}
      onScroll={() => {
        const el = viewport.current;
        if (!el) return;
        nearBottom.current =
          el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        if (nearBottom.current) {
          setNewMessages(false);
          void state.markRead();
        }
      }}
    >
      <div className="timeline" ref={content}>
        {state.hasOlder && (
          <Button
            className="history-button"
            variant="secondary"
            disabled={state.loadingOlder}
            onClick={async () => {
              const el = viewport.current!;
              prepending.current = {
                height: el.scrollHeight,
                top: el.scrollTop,
              };
              nearBottom.current = false;
              await state.history();
            }}
          >
            {t(state.loadingOlder ? "loading" : "older")}
          </Button>
        )}
        {state.events.data?.pages.some((page) => !page.retained) && (
          <p className="timeline-notice">{t("timelineRetained")}</p>
        )}
        {state.events.error && (
          <p className="timeline-notice" role="alert">
            {t("timelineError")}
          </p>
        )}
        {state.events.hasNextPage && (
          <Button
            variant="ghost"
            onClick={() => state.events.fetchNextPage()}
            disabled={state.events.isFetchingNextPage}
          >
            {t("older")}
          </Button>
        )}
        {!items.length && (
          <div className="empty-state">
            <Icon name="inbox" />
            <p>{t("firstMessage")}</p>
          </div>
        )}
        {items.map((item) => {
          const day = formatDate(item.time),
            separator = day !== previousDate;
          previousDate = day;
          if (item.kind === "event")
            return (
              <div key={item.id}>
                {separator && (
                  <div className="date-separator">
                    <span>{day}</span>
                  </div>
                )}
                <div
                  className="timeline-row timeline-event"
                  data-seq={item.seq}
                >
                  <div className="thread-gutter" aria-hidden="true">
                    <span className="thread-node node-event" />
                  </div>
                  <div className="timeline-content">
                    <strong>{t(item.label)}</strong>
                    <time dateTime={item.time}>{formatTime(item.time)}</time>
                  </div>
                </div>
              </div>
            );
          const message = item.message;
          const role = messageRole(message);
          const read = Object.entries(
            state.snapshot.data?.read_cursors ?? {},
          ).some(
            ([reader, seq]) =>
              reader !== message.sender_actor_id && seq >= message.event_seq,
          );
          return (
            <div key={item.id}>
              {separator && (
                <div className="date-separator">
                  <span>{day}</span>
                </div>
              )}
              <div
                className={`timeline-row message-row role-${role}`}
                data-seq={item.seq}
              >
                <div className="thread-gutter" aria-hidden="true">
                  <span className={`thread-node node-${role}`} />
                </div>
                <article
                  className={`message message--${role}`}
                  data-message-id={message.id}
                >
                  <header>
                    <strong>{t(role)}</strong>
                    <span>{t(`${role}Message`)}</span>
                    <time dateTime={item.time}>{formatTime(item.time)}</time>
                  </header>
                  <MessageMarkdown body={message.body} />
                  {role === "assistant" && (
                    <div className="source-chips">
                      {[
                        ...new Set(
                          [...message.body.matchAll(/\[(S\d+)\]/g)].map(
                            (match) => match[1],
                          ),
                        ),
                      ].map((label) => (
                        <button
                          key={label}
                          aria-label={t("sourceTitle", { label })}
                          className={`source-chip ${selection?.messageId === message.id && selection.label === label ? "selected" : ""}`}
                          aria-pressed={
                            selection?.messageId === message.id &&
                            selection.label === label
                          }
                          onClick={() => onSource(message.id, label)}
                        >
                          <span>{label}</span>
                          <Icon name="link" size={16} />
                          {t("sourceTitle", { label })}
                        </button>
                      ))}
                    </div>
                  )}
                  <div className="delivery-note">
                    {t(read ? "read" : "saved")}
                  </div>
                </article>
              </div>
            </div>
          );
        })}
        {state.pending.map((item) => (
          <div
            className="timeline-row message-row role-customer"
            key={item.key}
          >
            <div className="thread-gutter" aria-hidden="true">
              <span className="thread-node node-customer" />
            </div>
            <article
              className={`message ${state.delivery[item.key] === "failed" ? "message--failed" : ""}`}
            >
              <MessageMarkdown body={item.body} />
              <div className="delivery-note" role="status">
                {t(
                  state.delivery[item.key] === "failed"
                    ? "sendFailed"
                    : "pendingSend",
                )}
                <Button
                  variant="ghost"
                  disabled={state.delivery[item.key] === "sending"}
                  onClick={() => state.transmit(item)}
                >
                  {t("retry")}
                </Button>
              </div>
            </article>
          </div>
        ))}
        {state.draft && (
          <div className="timeline-row message-row role-assistant">
            <div className="thread-gutter" aria-hidden="true">
              <span className="thread-node node-assistant" />
            </div>
            <article
              className="message message--assistant provisional"
              data-testid="ai-draft"
            >
              <MessageMarkdown body={state.draft.text} />
              <div className="streaming-status" role="status">
                <i /> {t("draft")}
              </div>
            </article>
          </div>
        )}
        {!state.draft &&
          state.snapshot.data?.active_run &&
          ["queued", "running"].includes(
            state.snapshot.data.active_run.status,
          ) && (
            <p className="streaming-status" role="status">
              {t(
                state.snapshot.data.active_run.status === "queued"
                  ? "aiQueued"
                  : "aiRunning",
              )}
            </p>
          )}
        {state.typing && (
          <p className="streaming-status" role="status">
            {t("typing")}
          </p>
        )}
      </div>
      {newMessages && (
        <Button className="new-messages" onClick={latest}>
          {t("newMessages")}
        </Button>
      )}
    </div>
  );
}
