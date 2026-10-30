import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api } from "@supportdesk/api-client";
import { Button, EmptyState, Icon, Modal } from "../../components/ui";
import { errorKey } from "../../lib/api-error";
import { reference, type Session } from "../conversation/presentation";
import { documentPresentation, type Document } from "./presentation";

type Dialog =
  | { type: "upload"; document?: Document }
  | { type: "withdraw"; document: Document }
  | null;
export function Knowledge({ session }: { session: Session }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const workspace = session.memberships[0]?.workspace_id ?? "";
  const isAdmin = session.memberships[0]?.role === "admin";
  const path = { workspace_id: workspace };
  const headers = { "X-CSRF-Token": session.csrf_token };
  const [dialog, setDialog] = useState<Dialog>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [pendingEnabled, setPendingEnabled] = useState<boolean | null>(null);
  const details = useQuery({
    queryKey: ["workspace", "staff", workspace],
    enabled: isAdmin,
    queryFn: async () => {
      const result = await api.GET("/api/v1/staff/workspaces/{workspace_id}", {
        params: { path },
      });
      if (!result.data) throw Error();
      return result.data;
    },
  });
  const documents = useQuery({
    queryKey: ["knowledge", "staff", workspace],
    enabled: isAdmin,
    refetchInterval: 3000,
    queryFn: async () => {
      const result = await api.GET(
        "/api/v1/staff/workspaces/{workspace_id}/knowledge/documents",
        { params: { path } },
      );
      if (!result.data) throw Error();
      return result.data;
    },
  });
  const refresh = () =>
    qc.invalidateQueries({ queryKey: ["knowledge", "staff", workspace] });
  const hasReady =
    documents.data?.some((doc) => documentPresentation(doc).usable) ?? false;
  const enabled = pendingEnabled ?? details.data?.ai_enabled ?? false;
  if (!isAdmin)
    return <EmptyState title={t("accessDenied")} text={t("readOnly")} />;
  return (
    <section className="knowledge-page">
      <header className="page-heading">
        <div>
          <p className="eyebrow">
            {t("workspace")} / {session.memberships[0].name}
          </p>
          <h1>{t("knowledge")}</h1>
          <p>{t("knowledgeHint")}</p>
        </div>
        <Button
          onClick={() => {
            setError("");
            setDialog({ type: "upload" });
          }}
        >
          <Icon name="plus" />
          {t("addDocument")}
        </Button>
      </header>
      <section className={`activation-panel ${!hasReady ? "disabled" : ""}`}>
        <div>
          <strong>{t("enableAssistant")}</strong>
          <p>
            {t(
              session.ai_available === false
                ? "assistantDisabled"
                : hasReady
                  ? "groundedBody"
                  : "nothingReady",
            )}
          </p>
        </div>
        <label className="switch">
          <span className="sr-only">{t("enableAssistant")}</span>
          <input
            type="checkbox"
            aria-label={t("enableAssistant")}
            checked={enabled}
            aria-busy={busy}
            disabled={
              busy ||
              !details.data ||
              (session.ai_available === false && !enabled) ||
              (!hasReady && !enabled)
            }
            onChange={async (event) => {
              const value = event.target.checked;
              setPendingEnabled(value);
              setBusy(true);
              setError("");
              try {
                const result = await api.PUT(
                  "/api/v1/staff/workspaces/{workspace_id}/assistant",
                  { params: { path }, headers, body: { enabled: value } },
                );
                if (!result.data) {
                  setError(t(errorKey(result.error)));
                  return;
                }
                const savedEnabled = result.data.enabled;
                qc.setQueryData<typeof details.data>(
                  ["workspace", "staff", workspace],
                  (current) =>
                    current
                      ? { ...current, ai_enabled: savedEnabled }
                      : current,
                );
                await qc.invalidateQueries({
                  queryKey: ["workspace", "staff", workspace],
                });
              } catch {
                setError(t("apiUnavailable"));
              } finally {
                setPendingEnabled(null);
                setBusy(false);
              }
            }}
          />
          <span />
        </label>
      </section>
      {(error || details.error) && (
        <p className="form-error" role="alert">
          {error || t("error")}
        </p>
      )}
      <section className="document-section">
        <div className="section-heading">
          <div>
            <h2>{t("documents")}</h2>
            <span>
              {t("documentCount", { count: documents.data?.length ?? 0 })}
            </span>
          </div>
          <p>{t("uploadReal")}</p>
        </div>
        {documents.isLoading ? (
          <p className="list-notice" role="status">
            {t("loading")}
          </p>
        ) : documents.error ? (
          <p className="list-notice form-error" role="alert">
            {t("error")}
          </p>
        ) : !documents.data?.length ? (
          <EmptyState title={t("emptyKnowledge")} text={t("knowledgeHint")} />
        ) : (
          <div className="document-table">
            <div className="doc-row doc-head">
              <span>{t("documentTitle")}</span>
              <span>{t("versionAndFile")}</span>
              <span>{t("status")}</span>
              <span>{t("actions")}</span>
            </div>
            {documents.data.map((doc) => {
              const { active, latest, usable, status } =
                documentPresentation(doc);
              return (
                <article
                  className="document-entry"
                  key={doc.id}
                  data-testid={`document-${doc.id}`}
                >
                  <div className="doc-row">
                    <span className="doc-title">
                      <i>
                        <Icon name="book" size={18} />
                      </i>
                      <strong>{doc.title}</strong>
                    </span>
                    <span className="doc-file">
                      {usable ? (
                        <>
                          <b>
                            {t("activeVersion")}{" "}
                            <bdi dir="ltr">v{active!.version_no}</bdi>
                          </b>
                          <small>
                            {active?.id && (
                              <bdi dir="ltr">#{reference(active.id)}</bdi>
                            )}
                          </small>
                        </>
                      ) : (
                        <small>{t("noActiveVersion")}</small>
                      )}
                      {latest && latest.id !== active?.id && (
                        <small>
                          {t("latestVersion")}{" "}
                          <bdi dir="ltr">v{latest.version_no}</bdi>
                        </small>
                      )}
                    </span>
                    <span className="doc-state">
                      <em className={`doc-status status-${status}`}>
                        {["pending", "processing"].includes(status) && <i />}
                        {t(status)}
                      </em>
                      {usable && latest?.id !== active?.id && (
                        <small>{t("activePreserved")}</small>
                      )}
                      {latest?.error_code && (
                        <small className="form-error">
                          {t("jobFailed")} ·{" "}
                          <bdi dir="ltr">{latest.error_code}</bdi>
                        </small>
                      )}
                    </span>
                    <span className="doc-actions">
                      <button
                        onClick={() =>
                          setDialog({ type: "upload", document: doc })
                        }
                        disabled={Boolean(doc.withdrawn_at)}
                      >
                        {t("replaceDocument")}
                      </button>
                      <button
                        onClick={() =>
                          setDialog({ type: "withdraw", document: doc })
                        }
                        disabled={Boolean(doc.withdrawn_at) || busy}
                      >
                        {t("withdraw")}
                      </button>
                    </span>
                  </div>
                  <details className="version-list">
                    <summary>{t("versionHistory")}</summary>
                    <ul>
                      {[...doc.versions]
                        .sort((a, b) => b.version_no - a.version_no)
                        .map((version) => (
                          <li key={version.id}>
                            <bdi dir="ltr">
                              v{version.version_no} · #{reference(version.id)}
                            </bdi>
                            <span>{t(version.status)}</span>
                            {usable && version.id === active?.id && (
                              <strong>{t("activeVersion")}</strong>
                            )}
                          </li>
                        ))}
                    </ul>
                  </details>
                </article>
              );
            })}
          </div>
        )}
        <button
          className="upload-zone"
          onClick={() => setDialog({ type: "upload" })}
        >
          <Icon name="upload" />
          <strong>{t("chooseFile")}</strong>
          <small>{t("uploadHint")}</small>
        </button>
      </section>
      {dialog?.type === "upload" && (
        <UploadDialog
          key={dialog.document?.id ?? "new"}
          session={session}
          document={dialog.document}
          onClose={() => setDialog(null)}
          onUploaded={async () => {
            setDialog(null);
            await refresh();
          }}
        />
      )}
      {dialog?.type === "withdraw" && (
        <Modal title={t("withdrawTitle")} onClose={() => setDialog(null)}>
          <p>{t("withdrawHint", { title: dialog.document.title })}</p>
          {error && (
            <p role="alert" className="form-error">
              {error}
            </p>
          )}
          <div className="dialog-actions">
            <Button
              variant="danger"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setError("");
                try {
                  const result = await api.DELETE(
                    "/api/v1/staff/workspaces/{workspace_id}/knowledge/documents/{document_id}",
                    {
                      params: {
                        path: { ...path, document_id: dialog.document.id },
                      },
                      headers,
                    },
                  );
                  if (result.error) {
                    setError(t(errorKey(result.error)));
                    return;
                  }
                  setDialog(null);
                  await refresh();
                } catch {
                  setError(t("error"));
                } finally {
                  setBusy(false);
                }
              }}
            >
              {t("confirmWithdraw")}
            </Button>
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => setDialog(null)}
            >
              {t("cancel")}
            </Button>
          </div>
        </Modal>
      )}
    </section>
  );
}
function UploadDialog({
  session,
  document: target,
  onClose,
  onUploaded,
}: {
  session: Session;
  document?: Document;
  onClose: () => void;
  onUploaded: () => Promise<void>;
}) {
  const { t } = useTranslation();
  const [title, setTitle] = useState(target?.title ?? "");
  const [file, setFile] = useState<File>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const attempt = useRef<string | undefined>(undefined);
  const inFlight = useRef(false);
  const choose = (next?: File) => {
    if (!next) return;
    attempt.current = undefined;
    if (!/\.(md|txt|pdf)$/i.test(next.name)) {
      setFile(undefined);
      setError(t("invalidFile"));
      return;
    }
    if (next.size > 10 * 1024 * 1024) {
      setFile(undefined);
      setError(t("fileTooLarge"));
      return;
    }
    setFile(next);
    setError("");
    if (!title) setTitle(next.name.replace(/\.[^.]+$/, ""));
  };
  return (
    <Modal
      title={t(target ? "replaceDocument" : "addDocument")}
      onClose={onClose}
    >
      <p>{t("uploadReal")}</p>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          if (inFlight.current) return;
          if (!title.trim()) {
            setError(t("invalidTitle"));
            return;
          }
          if (!file) {
            setError(t("invalidFile"));
            return;
          }
          inFlight.current = true;
          setBusy(true);
          setError("");
          attempt.current ??= crypto.randomUUID();
          const form = new FormData();
          form.set("title", title.trim());
          form.set("file", file);
          const options = {
            params: {
              path: {
                workspace_id: session.memberships[0].workspace_id,
                document_id: target?.id ?? "",
              },
              header: { "Idempotency-Key": attempt.current },
            },
            headers: { "X-CSRF-Token": session.csrf_token },
            body: { title: title.trim(), file: file.name },
            bodySerializer: () => form,
          };
          try {
            const result = target
              ? await api.POST(
                  "/api/v1/staff/workspaces/{workspace_id}/knowledge/documents/{document_id}/versions",
                  options,
                )
              : await api.POST(
                  "/api/v1/staff/workspaces/{workspace_id}/knowledge/documents",
                  options,
                );
            if (!result.data) {
              setError(t(errorKey(result.error)));
              return;
            }
            await onUploaded();
          } catch {
            setError(t("uploadFailed"));
          } finally {
            inFlight.current = false;
            setBusy(false);
          }
        }}
      >
        <label className="form-label">
          {t("documentTitle")}
          <input
            className="field"
            value={title}
            maxLength={200}
            required
            onChange={(event) => {
              setTitle(event.target.value);
              attempt.current = undefined;
            }}
            disabled={Boolean(target) || busy}
          />
        </label>
        <label
          className="file-picker"
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            if (!busy) choose(event.dataTransfer.files[0]);
          }}
        >
          <Icon name="upload" />
          <span>
            <strong dir="auto">{file?.name ?? t("chooseFile")}</strong>
            <small>{t("uploadHint")}</small>
          </span>
          <input
            aria-label={t("documentFile")}
            type="file"
            accept=".md,.txt,.pdf"
            disabled={busy}
            onChange={(event) => choose(event.target.files?.[0])}
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div className="dialog-actions">
          <Button disabled={busy}>{t(busy ? "loading" : "upload")}</Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("cancel")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
