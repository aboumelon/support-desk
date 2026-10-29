import { useEffect, useRef, useState } from "react";
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { api } from "@supportdesk/api-client";
import { Button, EmptyState, Icon, useMedia } from "../../components/ui";
import { getDraft, setDraft as saveDraft } from "../../lib/composer-drafts";
import {
  actorFor,
  formatTime,
  reference,
  responsibility,
  type Audience,
  type Session,
} from "./presentation";
import { useConversation } from "./use-conversation";
import { Timeline } from "./timeline";
import { SourceInspector, type SourceSelection } from "./source-inspector";

export function Desk({
  session,
  audience,
  initialConversation,
}: {
  session: Session;
  audience: Audience;
  initialConversation?: string;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const workspace =
    session.workspace_id ?? session.memberships[0]?.workspace_id ?? "";
  const actor = actorFor(session, workspace);
  const [selected, setSelected] = useState<string | null>(
    initialConversation ??
      (getDraft(`${audience}:${workspace}:${actor}:selection`) || null),
  );
  const [filter, setFilter] = useState("open");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mobileDetail, setMobileDetail] = useState(
    Boolean(
      initialConversation ||
      getDraft(`${audience}:${workspace}:${actor}:selection`),
    ),
  );
  const narrow = useMedia("(max-width:760px)");
  useEffect(() => {
    if (initialConversation) {
      setSelected(initialConversation);
      setMobileDetail(true);
    }
  }, [initialConversation]);
  const list = useInfiniteQuery({
    queryKey: ["conversations", audience, workspace, filter],
    initialPageParam: undefined as number | undefined,
    refetchInterval: 5000,
    queryFn: async ({ pageParam }) => {
      const query = {
        status: filter === "resolved" ? "resolved" : "open",
        controller: filter === "queue" ? "queue" : undefined,
        assigned_actor_id: filter === "mine" ? actor : undefined,
        before: pageParam,
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
    getNextPageParam: (last) =>
      last.length === 50
        ? Math.round(new Date(last.at(-1)!.updated_at).getTime() * 1000)
        : undefined,
  });
  const conversations = list.data?.pages.flat() ?? [];
  const visible = conversations.filter((c) =>
    c.id.toLowerCase().includes(query.trim().toLowerCase()),
  );
  useEffect(() => {
    if (!selected && !narrow && visible[0]) setSelected(visible[0].id);
  }, [list.data, narrow, selected]);
  const select = (id: string) => {
    setSelected(id);
    saveDraft(`${audience}:${workspace}:${actor}:selection`, id);
    setMobileDetail(true);
    if (audience === "staff")
      void navigate({
        to: "/app/$workspaceId/conversations/$conversationId",
        params: { workspaceId: workspace, conversationId: id },
      });
  };
  const create = async () => {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await api.POST("/api/v1/customer/conversations", {
        params: { header: { "Idempotency-Key": crypto.randomUUID() } },
        headers: { "X-CSRF-Token": session.csrf_token },
      });
      if (!result.data) throw Error();
      select(result.data.id);
      await qc.invalidateQueries({
        queryKey: ["conversations", audience, workspace],
      });
    } catch {
      setError(t("error"));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div
      className={`operator-shell ${audience === "customer" ? "customer-desk" : ""} ${mobileDetail ? "mobile-detail" : "mobile-list"}`}
    >
      <section
        className={`conversation-index ${mobileDetail ? "mobile-hidden" : ""}`}
        aria-label={t("allChats")}
      >
        <div className="index-header">
          <div>
            <p className="eyebrow">
              {audience === "staff" ? session.memberships[0]?.name : t("brand")}
            </p>
            <h1>{t(audience === "staff" ? "inbox" : "myChats")}</h1>
          </div>
          <span className="count">{conversations.length}</span>
        </div>
        {audience === "customer" && (
          <Button className="new-chat" onClick={create} disabled={busy}>
            <Icon name="plus" />
            {t("newChat")}
          </Button>
        )}
        <div className="search-wrap">
          <Icon name="search" size={18} />
          <input
            className="field"
            aria-label={t("search")}
            placeholder={t("search")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="filters" role="tablist" aria-label={t("filterLabel")}>
          {(audience === "staff"
            ? ["open", "queue", "mine", "resolved"]
            : ["open", "resolved"]
          ).map((value) => (
            <button
              key={value}
              role="tab"
              aria-selected={filter === value}
              className={filter === value ? "active" : ""}
              onClick={() => {
                setFilter(value);
                setMobileDetail(false);
              }}
            >
              {t(value === "mine" ? "assignedToMe" : value)}
            </button>
          ))}
        </div>
        <div className="conversation-list">
          {list.isLoading ? (
            <p className="list-notice" role="status">
              {t("loading")}
            </p>
          ) : list.error ? (
            <p className="list-notice" role="alert">
              {t("error")}
            </p>
          ) : !visible.length ? (
            <EmptyState
              title={t(query ? "noMatch" : "emptyInbox")}
              text={t("selectConversation")}
            />
          ) : (
            visible.map((c) => (
              <button
                className={`conversation-row ${selected === c.id ? "selected" : ""}`}
                key={c.id}
                onClick={() => select(c.id)}
                aria-label={`${t("conversation")} ${reference(c.id)}`}
              >
                {selected === c.id && <span className="edge-thread" />}
                <span className="avatar">
                  <Icon name="user" size={18} />
                </span>
                <span className="row-copy">
                  <span className="row-top">
                    <strong>{t("customer")}</strong>
                    <time dateTime={c.updated_at}>
                      {formatTime(c.updated_at)}
                    </time>
                  </span>
                  <span className="row-subject">
                    <bdi dir="ltr">#{reference(c.id)}</bdi>
                    {c.unread_count > 0 && (
                      <span className="unread-badge">{c.unread_count}</span>
                    )}
                  </span>
                  <span
                    className={`responsibility-tag state-${responsibility(c, actor)}`}
                  >
                    {t(`responsibility_${responsibility(c, actor)}`)}
                  </span>
                </span>
              </button>
            ))
          )}
          {list.hasNextPage && (
            <Button
              variant="ghost"
              disabled={list.isFetchingNextPage}
              onClick={() => list.fetchNextPage()}
            >
              {t("loadMore")}
            </Button>
          )}
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </section>
      {selected ? (
        <ConversationPane
          key={`${audience}:${workspace}:${actor}:${selected}`}
          session={session}
          audience={audience}
          workspace={workspace}
          id={selected}
          onBack={() => {
            setMobileDetail(false);
            if (audience === "staff")
              void navigate({
                to: "/app/$workspaceId/inbox",
                params: { workspaceId: workspace },
              });
          }}
          onNew={create}
        />
      ) : (
        <div className="no-selection">
          <EmptyState
            title={t("noSelection")}
            text={t(
              audience === "customer" ? "startHint" : "selectConversation",
            )}
          />
        </div>
      )}
    </div>
  );
}

function ConversationPane({
  session,
  audience,
  workspace,
  id,
  onBack,
  onNew,
}: {
  session: Session;
  audience: Audience;
  workspace: string;
  id: string;
  onBack: () => void;
  onNew: () => void;
}) {
  const { t } = useTranslation();
  const state = useConversation(session, audience, workspace, id);
  const [selection, setSelection] = useState<SourceSelection | null>(null);
  const [text, setText] = useState(() => getDraft(state.scope));
  const [copy, setCopy] = useState("");
  const composing = useRef(false);
  const sending = useRef(false);
  if (!state.snapshot.data)
    return (
      <section className="reading-pane">
        <EmptyState
          title={t(state.snapshot.error ? "error" : "loading")}
          text={t("selectConversation")}
        />
      </section>
    );
  const conversation = state.snapshot.data.conversation;
  const status = responsibility(
    conversation,
    state.actor,
    state.snapshot.data.active_run,
  );
  const canSend =
    conversation.status === "open" &&
    (audience === "customer" || conversation.assigned_actor_id === state.actor);
  const disabled = canSend
    ? undefined
    : t(
        status === "resolved"
          ? "disabledResolved"
          : status === "bot" || status === "generating"
            ? "disabledBot"
            : status === "other"
              ? "disabledOther"
              : "cannotSend",
      );
  const submit = async () => {
    if (sending.current || !canSend || !text.trim()) return;
    sending.current = true;
    try {
      if (await state.send(text)) {
        setText("");
        saveDraft(state.scope, "");
      }
    } finally {
      sending.current = false;
    }
  };
  return (
    <>
      <section
        className="reading-pane"
        aria-label={`${t("conversation")} ${reference(id)}`}
      >
        <header className="conversation-header">
          <button
            className="mobile-back"
            aria-label={t("backToList")}
            onClick={onBack}
          >
            <Icon name="arrow" />
          </button>
          <span className="avatar avatar-large">
            <Icon name="user" />
          </span>
          <div className="identity">
            <h2>{t("customer")}</h2>
            <p>
              {t("conversation")} · <bdi dir="ltr">#{reference(id)}</bdi>
            </p>
          </div>
          <span
            className={`connection ${state.connected ? "" : "warning"}`}
            role="status"
          >
            <i />
            {t(state.connected ? "connected" : "polling")}
          </span>
          <div className="header-actions">
            {status === "resolved" && (
              <Button
                disabled={state.busy}
                onClick={() => state.command("reopen", conversation)}
              >
                {t("reopen")}
              </Button>
            )}
            {audience === "staff" && status === "queue" && (
              <Button
                disabled={state.busy}
                onClick={() => state.command("claim", conversation)}
              >
                {t("claim")}
              </Button>
            )}
            {audience === "staff" && status === "me" && (
              <Button
                disabled={state.busy}
                onClick={() => state.command("resolve", conversation)}
              >
                {t("resolve")}
              </Button>
            )}
            {audience === "customer" && (
              <Button
                className="mobile-only"
                variant="secondary"
                onClick={onNew}
              >
                <Icon name="plus" />
                <span className="sr-only">{t("newChat")}</span>
              </Button>
            )}
            <details className="action-details">
              <summary aria-label={t("moreActions")}>•••</summary>
              <div className="action-menu">
                {audience === "staff" && status === "me" && (
                  <>
                    <Button
                      variant="ghost"
                      disabled={state.busy}
                      onClick={() => state.command("release", conversation)}
                    >
                      {t("release")}
                    </Button>
                    <Button
                      variant="ghost"
                      disabled={state.busy}
                      onClick={() =>
                        state.command("return-to-bot", conversation)
                      }
                    >
                      {t("returnToBot")}
                    </Button>
                  </>
                )}
                <Button
                  variant="ghost"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(id);
                      setCopy(t("copied"));
                    } catch {
                      setCopy(t("copyFailed"));
                    }
                  }}
                >
                  {t("copyReference")}
                </Button>
                {copy && <span role="status">{copy}</span>}
              </div>
            </details>
          </div>
        </header>
        <div className="reading-status">
          {!state.connected && (
            <p className="reconnect-banner" role="status">
              {t("reconnectHint")}
            </p>
          )}
          <div className={`responsibility-strip state-${status}`} role="status">
            <span className="thread-state-icon" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
            <span>
              <small>{t("responsibility")}</small>
              <strong>{t(`responsibility_${status}`)}</strong>
            </span>
            {status === "queue" && <em>{t("attention")}</em>}
          </div>
          {state.error && (
            <p className="chat-error form-error" role="alert">
              {state.error}
            </p>
          )}
        </div>
        <Timeline
          state={state}
          selection={selection}
          onSource={(messageId, label) =>
            setSelection({ conversationId: id, messageId, label })
          }
        />
        <div className="composer-wrap">
          {audience === "customer" &&
            conversation.status === "open" &&
            conversation.controller === "bot" && (
              <div className="request-row">
                <p>{t("handoffHint")}</p>
                <Button
                  variant="secondary"
                  disabled={state.busy}
                  onClick={() => state.command("handoff", conversation)}
                >
                  {t("handoff")}
                </Button>
              </div>
            )}
          {audience === "customer" && status === "queue" && (
            <p className="waiting-note">{t("waitingHint")}</p>
          )}
          {disabled && <p className="composer-disabled">{disabled}</p>}
          <form
            className="composer"
            onSubmit={(event) => {
              event.preventDefault();
              void submit();
            }}
          >
            <textarea
              aria-label={t("message")}
              placeholder={t(canSend ? "messagePlaceholder" : "cannotSend")}
              value={text}
              onChange={(event) => {
                setText(event.target.value);
                saveDraft(state.scope, event.target.value);
                state.sendTyping();
              }}
              onCompositionStart={() => {
                composing.current = true;
              }}
              onCompositionEnd={() => {
                composing.current = false;
              }}
              onKeyDown={(event) => {
                if (
                  event.key === "Enter" &&
                  !event.shiftKey &&
                  !composing.current &&
                  !event.nativeEvent.isComposing
                ) {
                  event.preventDefault();
                  void submit();
                }
              }}
              maxLength={8000}
              disabled={!canSend}
              dir="auto"
            />
            <div className="composer-bottom">
              <span>{t("composerHint")}</span>
              <Button type="submit" disabled={!canSend || !text.trim()}>
                <Icon name="send" size={18} />
                {t("send")}
              </Button>
            </div>
          </form>
          <div className="chat-note">
            <span>
              {t(session.provider_mode === "fake" ? "fixtureNote" : "liveMode")}
            </span>
            {state.peerOnline && <span>{t("peerOnline")}</span>}
          </div>
        </div>
      </section>
      {selection && (
        <SourceInspector
          selection={selection}
          audience={audience}
          workspace={workspace}
          onClose={() => setSelection(null)}
        />
      )}
    </>
  );
}
