import { useEffect, useRef, useState } from "react";
import {
  useInfiniteQuery,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api } from "@supportdesk/api-client";
import {
  pendingFor,
  removePending,
  savePending,
  type PendingSend,
} from "../../lib/pending-sends";
import { singleFlight } from "../../lib/single-flight";
import { connect } from "../../lib/realtime/client";
import { errorCode, errorDetails } from "../../lib/api-error";
import {
  actorFor,
  type Audience,
  type Conversation,
  type Event,
  type Message,
  type Session,
} from "./presentation";

export type Draft = {
  run: string;
  epoch: number;
  attempt: number;
  index: number;
  text: string;
};
export type ControlAction =
  "claim" | "release" | "handoff" | "resolve" | "reopen" | "return-to-bot";

export function useConversation(
  session: Session,
  audience: Audience,
  workspace: string,
  id: string,
) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const actor = actorFor(session, workspace);
  const scope = `${audience}:${workspace}:${actor}:${id}`;
  const path = { workspace_id: workspace, conversation_id: id };
  const queryKey = ["snapshot", audience, workspace, id];
  const eventKey = ["events", audience, workspace, id];
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(false);
  const [typing, setTyping] = useState(false);
  const [presence, setPresence] = useState<Record<string, boolean>>({});
  const [draft, setDraft] = useState<Draft>();
  const [pending, setPending] = useState<PendingSend[]>([]);
  const [delivery, setDelivery] = useState<
    Record<string, "sending" | "failed">
  >({});
  const [older, setOlder] = useState<Message[]>([]);
  const [hasOlder, setHasOlder] = useState(true);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const sending = useRef(false);
  const controlBusy = useRef(false);
  const typingTimer = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );
  const connection = useRef<ReturnType<typeof connect> | null>(null);
  const draftRef = useRef<Draft | undefined>(undefined);
  draftRef.current = draft;
  const blockedDrafts = useRef(new Set<string>());
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
  const current = useRef(snapshot.data);
  current.current = snapshot.data;
  const initialCursor = useRef<number | undefined>(undefined);
  if (initialCursor.current === undefined && snapshot.data)
    initialCursor.current = snapshot.data.event_cursor;
  const events = useInfiniteQuery({
    queryKey: eventKey,
    initialPageParam: 0,
    refetchInterval: 5000,
    queryFn: async ({ pageParam }) => {
      const fetchPage = (after: number) => {
        const params = { path, query: { after_seq: after } };
        return audience === "customer"
          ? api.GET("/api/v1/customer/conversations/{conversation_id}/events", {
              params,
            })
          : api.GET(
              "/api/v1/staff/workspaces/{workspace_id}/conversations/{conversation_id}/events",
              { params },
            );
      };
      let result = await fetchPage(pageParam);
      let retained = true;
      if (!result.data && errorCode(result.error) === "RESET_REQUIRED") {
        retained = false;
        const oldest = errorDetails(result.error).oldest_available_seq;
        if (typeof oldest !== "number" || oldest < 1)
          return { items: [] as Event[], retained };
        result = await fetchPage(oldest - 1);
      }
      if (!result.data) throw Error();
      return { items: result.data, retained };
    },
    getNextPageParam: (last) =>
      last.items.length === 100 ? last.items.at(-1)!.seq : undefined,
  });
  useEffect(() => {
    if (
      events.hasNextPage &&
      !events.isFetchingNextPage &&
      (events.data?.pages.length ?? 0) < 20
    )
      void events.fetchNextPage();
  }, [
    events.hasNextPage,
    events.isFetchingNextPage,
    events.data?.pages.length,
  ]);
  const invalidate = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey }),
      qc.invalidateQueries({
        queryKey: ["conversations", audience, workspace],
      }),
      qc.invalidateQueries({ queryKey: eventKey }),
    ]);
  };
  const discardDraft = () => {
    const value = draftRef.current;
    if (value) blockedDrafts.current.add(`${value.run}:${value.attempt}`);
    draftRef.current = undefined;
    setDraft(undefined);
  };
  useEffect(() => {
    const value = draftRef.current;
    const state = snapshot.data;
    if (
      value &&
      state &&
      (state.conversation.control_epoch !== value.epoch ||
        state.conversation.controller !== "bot" ||
        state.active_run?.id !== value.run ||
        state.active_run.status !== "running")
    )
      discardDraft();
  }, [
    snapshot.data?.conversation.control_epoch,
    snapshot.data?.active_run?.id,
    snapshot.data?.active_run?.status,
  ]);
  useEffect(() => {
    if (initialCursor.current === undefined) return;
    const stop = connect(
      audience,
      workspace,
      id,
      initialCursor.current,
      async (event) => {
        if (
          [
            "conversation.control_changed",
            "conversation.resolved",
            "conversation.reopened",
          ].includes(event.type) ||
          (event.type === "ai.run_changed" &&
            !["running", "queued"].includes(String(event.data.status)))
        )
          discardDraft();
        await invalidate();
      },
      (status) => {
        setConnected(status);
        if (!status) {
          discardDraft();
          setPresence({});
          setTyping(false);
        }
      },
      (event) => {
        if (event.type === "presence.updated" && event.actor_id !== actor)
          setPresence((values) => ({
            ...values,
            [event.actor_id]: event.online,
          }));
        if (event.type === "typing.updated" && event.actor_id !== actor) {
          setTyping(true);
          clearTimeout(typingTimer.current);
          typingTimer.current = setTimeout(() => setTyping(false), 5000);
        }
        if (event.type !== "ai.delta") return;
        const state = current.current;
        const key = `${event.run_id}:${event.attempt}`;
        if (
          !state ||
          state.conversation.controller !== "bot" ||
          state.conversation.control_epoch !== event.control_epoch ||
          state.active_run?.id !== event.run_id ||
          blockedDrafts.current.has(key)
        )
          return;
        const previous = draftRef.current;
        if (previous?.run === event.run_id && previous.attempt > event.attempt)
          return;
        if (
          previous?.run === event.run_id &&
          previous.attempt === event.attempt &&
          event.chunk_index <= previous.index
        )
          return;
        if (
          event.chunk_index !== 0 &&
          (!previous ||
            previous.run !== event.run_id ||
            previous.attempt !== event.attempt ||
            previous.index + 1 !== event.chunk_index)
        ) {
          blockedDrafts.current.add(key);
          discardDraft();
          return;
        }
        const value = {
          run: event.run_id,
          epoch: event.control_epoch,
          attempt: event.attempt,
          index: event.chunk_index,
          text: (event.chunk_index === 0 ? "" : previous!.text) + event.text,
        };
        draftRef.current = value;
        setDraft(value);
      },
    );
    connection.current = stop;
    return () => {
      stop();
      clearTimeout(typingTimer.current);
    };
  }, [audience, workspace, id, snapshot.isSuccess]);
  const messages = [...older, ...(snapshot.data?.messages ?? [])]
    .filter((m, index, all) => all.findIndex((x) => x.id === m.id) === index)
    .sort((a, b) => a.event_seq - b.event_seq);
  async function transmit(item: PendingSend) {
    setDelivery((values) => ({ ...values, [item.key]: "sending" }));
    try {
      await singleFlight(item.key, async () => {
        const options = {
          params: { path },
          headers: { "X-CSRF-Token": session.csrf_token },
          body: { client_message_id: item.client_message_id, body: item.body },
        };
        const result =
          audience === "customer"
            ? await api.POST(
                "/api/v1/customer/conversations/{conversation_id}/messages",
                options,
              )
            : await api.POST(
                "/api/v1/staff/workspaces/{workspace_id}/conversations/{conversation_id}/messages",
                options,
              );
        if (!result.data) throw Error();
        await removePending(item.key);
      });
      setPending(await pendingFor(scope));
      await invalidate();
    } catch {
      setDelivery((values) => ({ ...values, [item.key]: "failed" }));
      setError(t("retryHint"));
    }
  }
  useEffect(() => {
    let cancelled = false;
    const recover = async () => {
      const items = await pendingFor(scope);
      if (cancelled) return;
      setPending(items);
      for (const item of items) {
        if (cancelled) break;
        await transmit(item);
      }
    };
    void recover();
    window.addEventListener("online", recover);
    return () => {
      cancelled = true;
      window.removeEventListener("online", recover);
    };
  }, [scope]);
  useEffect(() => {
    const known = new Set(
      messages
        .filter((m) => m.sender_actor_id === actor)
        .map((m) => m.client_message_id),
    );
    const committed = pending.filter((p) => known.has(p.client_message_id));
    if (committed.length)
      void Promise.all(committed.map((p) => removePending(p.key))).then(
        async () => setPending(await pendingFor(scope)),
      );
  }, [snapshot.data?.event_cursor]);
  async function send(text: string) {
    if (!text.trim() || sending.current) return false;
    sending.current = true;
    setError("");
    const client_message_id = crypto.randomUUID();
    const item = {
      scope,
      key: `${scope}:${client_message_id}`,
      client_message_id,
      body: text,
    };
    try {
      await savePending(item);
      setPending(await pendingFor(scope));
      void transmit(item);
      return true;
    } catch {
      setError(t("retryHint"));
      return false;
    } finally {
      sending.current = false;
    }
  }
  async function command(action: ControlAction, conversation: Conversation) {
    if (controlBusy.current) return;
    controlBusy.current = true;
    setBusy(true);
    setError("");
    try {
      const options = {
        params: {
          path: { ...path, action },
          header: { "Idempotency-Key": crypto.randomUUID() },
        },
        headers: { "X-CSRF-Token": session.csrf_token },
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
      if (!result.data) throw Error();
      discardDraft();
    } catch {
      setError(t("stateConflict"));
    } finally {
      await invalidate();
      controlBusy.current = false;
      setBusy(false);
    }
  }
  async function history() {
    if (!messages.length || loadingOlder) return;
    setLoadingOlder(true);
    try {
      const params = {
        path,
        query: { before: btoa(String(messages[0].event_seq)) },
      };
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
      if (!result.data) throw Error();
      setOlder((items) => [...result.data, ...items]);
      setHasOlder(result.data.length === 50);
    } catch {
      setError(t("error"));
    } finally {
      setLoadingOlder(false);
    }
  }
  const readBusy = useRef(false);
  const lastRead = useRef(0);
  async function markRead() {
    const state = current.current;
    const seq = state?.messages.at(-1)?.event_seq;
    if (
      !seq ||
      !actor ||
      document.visibilityState !== "visible" ||
      readBusy.current ||
      Math.max(lastRead.current, state?.read_cursors[actor] ?? 0) >= seq
    )
      return;
    readBusy.current = true;
    const options = {
      params: { path },
      headers: { "X-CSRF-Token": session.csrf_token },
      body: { last_read_seq: seq },
    };
    try {
      const result =
        audience === "customer"
          ? await api.PUT(
              "/api/v1/customer/conversations/{conversation_id}/read-cursor",
              options,
            )
          : await api.PUT(
              "/api/v1/staff/workspaces/{workspace_id}/conversations/{conversation_id}/read-cursor",
              options,
            );
      if (result.data) lastRead.current = seq;
    } catch {
      // A read receipt can be retried when the transport recovers.
    } finally {
      readBusy.current = false;
    }
  }
  return {
    snapshot,
    actor,
    scope,
    messages,
    pending: pending.filter(
      (p) =>
        !messages.some(
          (m) =>
            m.client_message_id === p.client_message_id &&
            m.sender_actor_id === actor,
        ),
    ),
    delivery,
    transmit,
    send,
    command,
    history,
    hasOlder: hasOlder && (snapshot.data?.messages.length ?? 0) >= 50,
    loadingOlder,
    events,
    error,
    connected,
    draft,
    busy,
    typing,
    peerOnline: Object.values(presence).some(Boolean),
    markRead,
    sendTyping: () => connection.current?.typing(),
  };
}
