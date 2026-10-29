import { MessageMarkdown } from "../../lib/markdown";
import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, type components } from "@supportdesk/api-client";
import {
  pendingFor,
  savePending,
  removePending,
  type PendingSend,
} from "../../lib/pending-sends";
import { connect } from "../../lib/realtime/client";
type Session = components["schemas"]["SessionView"];
type Conversation = components["schemas"]["ConversationView"];
export function Desk({
  session,
  audience,
  initialConversation,
}: {
  session: Session;
  initialConversation?: string;
  audience: "customer" | "staff";
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const workspace =
    session.workspace_id ?? session.memberships?.[0]?.workspace_id ?? "";
  const [selected, setSelected] = useState<string | null>(
    initialConversation ?? null,
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState("open");
  const listKey = ["conversations", audience, workspace, filter];
  const conversations = useQuery({
    queryKey: listKey,
    refetchInterval: 5000,
    queryFn: async () => {
      const query = {
        status: filter === "resolved" ? "resolved" : "open",
        controller: filter === "queue" ? "queue" : undefined,
        assigned_actor_id:
          filter === "mine"
            ? session.memberships?.find((m) => m.workspace_id === workspace)
                ?.actor_id
            : undefined,
      };
      const result =
        audience === "customer"
          ? await api.GET("/api/v1/customer/conversations", {
              params: { query },
            })
          : await api.GET(
              "/api/v1/staff/workspaces/{workspace_id}/conversations",
              { params: { path: { workspace_id: workspace }, query } },
            );
      if (!result.data) throw Error();
      return result.data;
    },
  });
  useEffect(() => {
    // Preserve the opened transcript when its status leaves the filtered inbox.
    if (selected === null && conversations.data?.[0])
      setSelected(conversations.data[0].id);
  }, [selected, conversations.data]);
  const current = selected ?? conversations.data?.[0]?.id;
  async function create() {
    setBusy(true);
    try {
      const { data, error } = await api.POST("/api/v1/customer/conversations", {
        params: { header: { "Idempotency-Key": crypto.randomUUID() } },
        headers: { "X-CSRF-Token": session.csrf_token },
      });
      if (error || !data) throw Error();
      setSelected(data.id);
      await qc.invalidateQueries({
        queryKey: ["conversations", audience, workspace],
      });
    } catch {
      setError(t("error"));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="desk">
      <aside className="conversation-list">
        <div className="list-heading">
          <h2>{t(audience === "staff" ? "inbox" : "myChats")}</h2>
          {audience === "customer" && (
            <button onClick={create} disabled={busy}>
              {t("newChat")}
            </button>
          )}
        </div>
        <select
          aria-label={t("status")}
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value);
            setSelected(null);
          }}
        >
          <option value="open">{t("open")}</option>
          <option value="resolved">{t("resolved")}</option>
          {audience === "staff" && (
            <>
              <option value="queue">{t("queue")}</option>
              <option value="mine">{t("assignedToMe")}</option>
            </>
          )}
        </select>
        {conversations.isLoading ? (
          <p>{t("loading")}</p>
        ) : conversations.error ? (
          <p role="alert">{t("error")}</p>
        ) : (
          conversations.data?.map((c) => (
            <button
              className={`conversation-item ${c.id === current ? "current" : ""}`}
              key={c.id}
              onClick={() => setSelected(c.id)}
            >
              <span>
                {t("conversation")} <code>{c.id.slice(0, 6)}</code>
              </span>
              <small>
                {t(c.controller)} ·{" "}
                {new Date(c.updated_at).toLocaleTimeString("fa-IR", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </small>
            </button>
          ))
        )}
        {conversations.data?.length === 0 && (
          <p className="empty">{t("emptyInbox")}</p>
        )}
        {error && <p role="alert">{error}</p>}
      </aside>
      {current ? (
        <ConversationPane
          key={`${audience}:${workspace}:${current}`}
          audience={audience}
          session={session}
          workspace={workspace}
          id={current}
        />
      ) : (
        <section className="conversation-empty">
          <span>✳</span>
          <h2>{t("startConversation")}</h2>
          <p>{t("startHint")}</p>
        </section>
      )}
    </div>
  );
}
function ConversationPane({
  session,
  audience,
  workspace,
  id,
}: {
  session: Session;
  audience: "customer" | "staff";
  workspace: string;
  id: string;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const actor =
    session.actor_id ??
    session.memberships?.find((m) => m.workspace_id === workspace)?.actor_id;
  const scope = `${audience}:${workspace}:${actor}:${id}`;
  const [text, setText] = useState("");
  const [pending, setPending] = useState<PendingSend[]>([]);
  const [error, setError] = useState("");
  const [connected, setConnected] = useState(false);
  const [draft, setDraft] = useState<{
    run: string;
    attempt: number;
    index: number;
    text: string;
  }>();
  const [typing, setTyping] = useState(false);
  const [peerOnline, setPeerOnline] = useState<boolean>();
  const typingTimer = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );
  const connection = useRef<ReturnType<typeof connect> | null>(null);
  const [citation, setCitation] =
    useState<components["schemas"]["CitationView"]>();
  const [busy, setBusy] = useState(false);
  const [older, setOlder] = useState<components["schemas"]["MessageView"][]>(
    [],
  );
  const bottom = useRef<HTMLDivElement>(null);
  const viewport = useRef<HTMLDivElement>(null);
  const atBottom = useRef(true);
  const [newMessages, setNewMessages] = useState(false);
  const queryKey = ["snapshot", audience, workspace, id];
  const path = { workspace_id: workspace, conversation_id: id };
  const snapshot = useQuery({
    queryKey,
    refetchInterval: 5000,
    queryFn: async () => {
      const result =
        audience === "customer"
          ? await api.GET(
              "/api/v1/customer/conversations/{conversation_id}/snapshot",
              { params: { path } },
            )
          : await api.GET(
              "/api/v1/staff/workspaces/{workspace_id}/conversations/{conversation_id}/snapshot",
              { params: { path } },
            );
      if (!result.data) throw Error();
      return result.data;
    },
  });
  const currentSnapshot = useRef(snapshot.data);
  currentSnapshot.current = snapshot.data;
  useEffect(() => {
    if (snapshot.data?.active_run?.status !== "running") setDraft(undefined);
  }, [
    snapshot.data?.conversation.control_epoch,
    snapshot.data?.active_run?.status,
  ]);
  const initialCursor = useRef<number | undefined>(undefined);
  if (initialCursor.current === undefined && snapshot.data)
    initialCursor.current = snapshot.data.event_cursor;
  useEffect(() => {
    if (initialCursor.current === undefined) return;
    const close = connect(
      audience,
      workspace,
      id,
      initialCursor.current,
      async () => {
        await qc.invalidateQueries({
          queryKey: ["snapshot", audience, workspace, id],
        });
        await qc.invalidateQueries({
          queryKey: ["conversations", audience, workspace],
        });
      },
      (status) => {
        setConnected(status);
        if (!status) setDraft(undefined);
      },
      (event) => {
        if (event.type === "presence.updated" && event.actor_id !== actor)
          setPeerOnline(event.online);
        if (event.type === "typing.updated" && event.actor_id !== actor) {
          setTyping(true);
          clearTimeout(typingTimer.current);
          typingTimer.current = setTimeout(() => setTyping(false), 5000);
        }
        if (event.type === "ai.delta") {
          const state = currentSnapshot.current;
          if (
            !state ||
            state.conversation.controller !== "bot" ||
            state.conversation.control_epoch !== event.control_epoch
          )
            return;
          setDraft((previous) => {
            if (event.chunk_index === 0)
              return {
                run: event.run_id,
                attempt: event.attempt,
                index: 0,
                text: event.text,
              };
            if (
              !previous ||
              previous.run !== event.run_id ||
              previous.attempt !== event.attempt ||
              previous.index + 1 !== event.chunk_index
            )
              return undefined;
            return {
              ...previous,
              index: event.chunk_index,
              text: previous.text + event.text,
            };
          });
        }
      },
    );
    connection.current = close;
    return () => {
      close();
      clearTimeout(typingTimer.current);
    };
  }, [audience, workspace, id, qc, snapshot.isSuccess]);
  async function transmit(item: PendingSend) {
    const body = { client_message_id: item.client_message_id, body: item.body };
    const headers = { "X-CSRF-Token": session.csrf_token };
    const result =
      audience === "customer"
        ? await api.POST(
            "/api/v1/customer/conversations/{conversation_id}/messages",
            { params: { path }, headers, body },
          )
        : await api.POST(
            "/api/v1/staff/workspaces/{workspace_id}/conversations/{conversation_id}/messages",
            { params: { path }, headers, body },
          );
    if (result.error) throw Error();
    await removePending(item.key);
    setPending(await pendingFor(scope));
    await qc.invalidateQueries({ queryKey });
  }
  useEffect(() => {
    let cancelled = false;
    void pendingFor(scope).then(async (items) => {
      if (cancelled) return;
      setPending(items);
      for (const item of items) {
        try {
          await transmit(item);
        } catch {
          if (!cancelled) setError(t("retryHint"));
        }
      }
    });
    return () => {
      cancelled = true;
    };
  }, [scope]);
  const messages = [...older, ...(snapshot.data?.messages ?? [])].filter(
    (m, index, all) => all.findIndex((x) => x.id === m.id) === index,
  );
  const lastMessage = messages.at(-1)?.event_seq;
  useEffect(() => {
    if (atBottom.current) {
      if (viewport.current)
        viewport.current.scrollTop = viewport.current.scrollHeight;
      setNewMessages(false);
    } else setNewMessages(true);
  }, [lastMessage]);
  useEffect(() => {
    if (
      !lastMessage ||
      document.visibilityState !== "visible" ||
      !atBottom.current
    )
      return;
    const own = snapshot.data?.read_cursors[actor ?? ""] ?? 0;
    if (own >= lastMessage) return;
    const params = { path };
    const headers = { "X-CSRF-Token": session.csrf_token };
    const body = { last_read_seq: lastMessage };
    void (audience === "customer"
      ? api.PUT(
          "/api/v1/customer/conversations/{conversation_id}/read-cursor",
          { params, headers, body },
        )
      : api.PUT(
          "/api/v1/staff/workspaces/{workspace_id}/conversations/{conversation_id}/read-cursor",
          { params, headers, body },
        ));
  }, [lastMessage, actor, audience, id, workspace]);
  async function command(
    action: "claim" | "resolve" | "release" | "handoff" | "reopen",
    conversation: Conversation,
  ) {
    setBusy(true);
    setError("");
    try {
      const options = {
        params: {
          path: { ...path, action },
          header: { "Idempotency-Key": crypto.randomUUID() },
        },
        headers: {
          "X-CSRF-Token": session.csrf_token,
        },
        body: { expected_state_version: conversation.state_version },
      };
      const result =
        audience === "customer"
          ? await api.POST(
              "/api/v1/customer/conversations/{conversation_id}/{action}",
              options,
            )
          : await api.POST(
              "/api/v1/staff/workspaces/{workspace_id}/conversations/{conversation_id}/{action}",
              options,
            );
      if (result.error) throw Error();
      await qc.invalidateQueries({ queryKey });
      await qc.invalidateQueries({
        queryKey: ["conversations", audience, workspace],
      });
    } catch {
      setError(t("stateConflict"));
      await qc.invalidateQueries({ queryKey });
    } finally {
      setBusy(false);
    }
  }
  async function history() {
    const before = btoa(String(messages[0].event_seq));
    const params = { path, query: { before } };
    const result =
      audience === "customer"
        ? await api.GET(
            "/api/v1/customer/conversations/{conversation_id}/messages",
            { params },
          )
        : await api.GET(
            "/api/v1/staff/workspaces/{workspace_id}/conversations/{conversation_id}/messages",
            { params },
          );
    if (result.data) {
      const height = viewport.current?.scrollHeight ?? 0;
      setOlder((current) => [...result.data, ...current]);
      requestAnimationFrame(() => {
        if (viewport.current)
          viewport.current.scrollTop += viewport.current.scrollHeight - height;
      });
    }
  }
  async function showCitation(messageId: string, label: string) {
    const params = { path: { ...path, message_id: messageId, label } };
    const result =
      audience === "customer"
        ? await api.GET(
            "/api/v1/customer/conversations/{conversation_id}/citations/{message_id}/{label}",
            { params },
          )
        : await api.GET(
            "/api/v1/staff/workspaces/{workspace_id}/conversations/{conversation_id}/citations/{message_id}/{label}",
            { params },
          );
    if (result.data) setCitation(result.data);
    else setError(t("sourceUnavailable"));
  }
  if (!snapshot.data)
    return (
      <div className="conversation-empty">
        {t(snapshot.error ? "error" : "loading")}
      </div>
    );
  const conversation = snapshot.data.conversation;
  const canSend =
    conversation.status === "open" &&
    (audience === "customer" || conversation.assigned_actor_id === actor);
  return (
    <section className="conversation-pane">
      {citation && (
        <div
          role="dialog"
          aria-label={t("reference")}
          className="citation-panel"
        >
          <button
            onClick={() => setCitation(undefined)}
            aria-label={t("close")}
          >
            ×
          </button>
          <h3>{citation.title}</h3>
          <small>{citation.locator}</small>
          <p dir="auto">{citation.excerpt}</p>
        </div>
      )}
      <div className="chat-heading">
        <div>
          <h2>
            {t("conversation")} <code>{id.slice(0, 6)}</code>
          </h2>
          <small
            className={connected ? "connection-good" : "connection-degraded"}
          >
            {t(connected ? "connected" : "polling")} ·{" "}
            {t(conversation.controller)}{" "}
            {peerOnline !== undefined &&
              `· ${t(peerOnline ? "peerOnline" : "peerOffline")}`}
          </small>
        </div>
        <div className="control-actions">
          {conversation.status === "resolved" ? (
            <button
              disabled={busy}
              onClick={() => command("reopen", conversation)}
            >
              {t("reopen")}
            </button>
          ) : (
            <>
              {audience === "staff" && conversation.controller === "queue" && (
                <button
                  disabled={busy}
                  onClick={() => command("claim", conversation)}
                >
                  {t("claim")}
                </button>
              )}
              {audience === "staff" && conversation.controller === "human" && (
                <>
                  <button
                    disabled={busy}
                    onClick={() => command("resolve", conversation)}
                  >
                    {t("resolve")}
                  </button>
                  <button
                    disabled={busy}
                    className="secondary"
                    onClick={() => command("release", conversation)}
                  >
                    {t("release")}
                  </button>
                </>
              )}
              {audience === "customer" && conversation.controller === "bot" && (
                <button onClick={() => command("handoff", conversation)}>
                  {t("handoff")}
                </button>
              )}
            </>
          )}
        </div>
      </div>
      <div
        ref={viewport}
        className="messages"
        onScroll={() => {
          const el = viewport.current;
          if (el)
            atBottom.current =
              el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        }}
      >
        {messages.length >= 50 && (
          <button className="older secondary" onClick={history}>
            {t("older")}
          </button>
        )}
        {messages.length === 0 && (
          <div className="empty-chat">
            <span>✳</span>
            <p>{t("firstMessage")}</p>
          </div>
        )}
        {messages.map((m) => (
          <article
            key={m.id}
            className={`message ${m.sender_actor_id === actor ? "own" : "received"}`}
          >
            <span className="sender">
              {t(
                m.sender_kind === "visitor"
                  ? "customer"
                  : m.sender_kind === "assistant"
                    ? "assistant"
                    : "operator",
              )}
            </span>
            <MessageMarkdown body={m.body} />
            {m.sender_kind === "assistant" &&
              [...new Set(m.body.match(/S\d+/g) ?? [])].map((label) => (
                <button
                  className="citation-link"
                  key={label}
                  onClick={() => showCitation(m.id, label)}
                >
                  {t("reference")} {label} ↗
                </button>
              ))}
            <small>
              {new Date(m.created_at).toLocaleTimeString("fa-IR", {
                hour: "2-digit",
                minute: "2-digit",
              })}{" "}
              ·{" "}
              {t(
                m.sender_kind === "visitor" &&
                  Object.entries(snapshot.data.read_cursors).some(
                    ([reader, seq]) =>
                      reader !== snapshot.data.conversation.visitor_actor_id &&
                      seq >= m.event_seq,
                  )
                  ? "read"
                  : "saved",
              )}
            </small>
          </article>
        ))}
        {pending
          .filter(
            (p) =>
              !messages.some(
                (m) => m.client_message_id === p.client_message_id,
              ),
          )
          .map((p) => (
            <article className="message own pending" key={p.key}>
              <p dir="auto">{p.body}</p>
              <button
                onClick={() =>
                  transmit(p).catch(() => setError(t("retryHint")))
                }
              >
                {t("retry")}
              </button>
            </article>
          ))}
        {draft && (
          <article className="message received draft">
            <span>{t("draft")}</span>
            <p dir="auto">{draft.text}</p>
          </article>
        )}
        {!draft &&
          snapshot.data.active_run &&
          ["queued", "running"].includes(snapshot.data.active_run.status) && (
            <p className="generation-status">
              {t(
                snapshot.data.active_run.status === "queued"
                  ? "aiQueued"
                  : "aiRunning",
              )}
            </p>
          )}
        {typing && <small aria-live="polite">{t("typing")}</small>}
        <div ref={bottom} />
      </div>
      {newMessages && (
        <button
          className="new-message"
          onClick={() => {
            atBottom.current = true;
            if (viewport.current)
              viewport.current.scrollTop = viewport.current.scrollHeight;
            setNewMessages(false);
          }}
        >
          {t("newMessages")}
        </button>
      )}
      {error && (
        <p className="error chat-error" role="alert">
          {error}
        </p>
      )}
      <form
        className="composer"
        onSubmit={async (event) => {
          event.preventDefault();
          if (!text.trim() || busy) return;
          setBusy(true);
          setError("");
          const client_message_id = crypto.randomUUID();
          const item = {
            key: `${scope}:${client_message_id}`,
            scope,
            client_message_id,
            body: text,
          };
          try {
            await savePending(item);
            setPending(await pendingFor(scope));
            setText("");
            await transmit(item);
          } catch {
            setError(t("retryHint"));
          } finally {
            setBusy(false);
          }
        }}
      >
        <textarea
          aria-label={t("message")}
          placeholder={t(canSend ? "messagePlaceholder" : "cannotSend")}
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            connection.current?.typing();
          }}
          disabled={!canSend}
          maxLength={8000}
          dir="auto"
        />
        <button disabled={!canSend || busy || !text.trim()}>
          {t("send")} ↑
        </button>
      </form>
      <div className="chat-note" aria-live="polite">
        {t(session.provider_mode === "fake" ? "fixtureNote" : "liveMode")}
      </div>
    </section>
  );
}
