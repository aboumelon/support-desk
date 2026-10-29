import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, type components } from "@supportdesk/api-client";
export function Knowledge({
  session,
}: {
  session: components["schemas"]["SessionView"];
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const workspace = session.memberships?.[0]?.workspace_id ?? "";
  const path = { workspace_id: workspace };
  const headers = { "X-CSRF-Token": session.csrf_token };
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [replace, setReplace] = useState<string>();
  const details = useQuery({
    queryKey: ["workspace", "staff", workspace],
    queryFn: async () => {
      const result = await api.GET("/api/v1/staff/workspaces/{workspace_id}", {
        params: { path },
      });
      if (!result.data) throw Error();
      return result.data;
    },
  });
  const enabled = details.data?.ai_enabled ?? false;
  const documents = useQuery({
    queryKey: ["knowledge", workspace],
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
  return (
    <section className="knowledge-page">
      <span className="eyebrow">{t("knowledge")}</span>
      <h1>{t("knowledgeTitle")}</h1>
      <p>{t("knowledgeHint")}</p>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setError("");
          const form = new FormData(event.currentTarget);
          const file = form.get("file") as File;
          const title = String(form.get("title"));
          const header = { "Idempotency-Key": crypto.randomUUID() };
          const options = {
            params: { path: { ...path, document_id: replace ?? "" }, header },
            headers,
            body: { title, file: file.name },
            bodySerializer: () => form,
          };
          try {
            const result = replace
              ? await api.POST(
                  "/api/v1/staff/workspaces/{workspace_id}/knowledge/documents/{document_id}/versions",
                  options,
                )
              : await api.POST(
                  "/api/v1/staff/workspaces/{workspace_id}/knowledge/documents",
                  options,
                );
            if (result.error) throw Error();
            setReplace(undefined);
            await qc.invalidateQueries({ queryKey: ["knowledge", workspace] });
          } catch {
            setError(t("error"));
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          {t("documentTitle")}
          <input name="title" required maxLength={200} />
        </label>
        <label>
          {t("documentFile")}
          <input name="file" type="file" accept=".md,.txt,.pdf" required />
        </label>
        <button disabled={busy}>
          {t(replace ? "replaceDocument" : "upload")}
        </button>
        {replace && (
          <button
            type="button"
            className="secondary"
            onClick={() => setReplace(undefined)}
          >
            {t("cancel")}
          </button>
        )}
      </form>
      <div className="ai-setting">
        <label>
          <input
            type="checkbox"
            checked={enabled}
            onChange={async (event) => {
              const value = event.target.checked;
              const result = await api.PUT(
                "/api/v1/staff/workspaces/{workspace_id}/assistant",
                { params: { path }, headers, body: { enabled: value } },
              );
              if (result.data)
                await qc.invalidateQueries({
                  queryKey: ["workspace", "staff", workspace],
                });
              else setError(t("assistantNeedsKnowledge"));
            }}
          />
          {t("enableAssistant")}
        </label>
        <small>
          {t(session.provider_mode === "fake" ? "fixtureNote" : "liveMode")}
        </small>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {documents.isLoading ? (
        <p>{t("loading")}</p>
      ) : documents.error ? (
        <p role="alert">{t("error")}</p>
      ) : (
        documents.data?.map((doc) => (
          <article key={doc.id} className="document-row">
            <div>
              <h3>{doc.title}</h3>
              <small>
                {t(
                  doc.withdrawn_at
                    ? "withdrawn"
                    : (doc.versions[0]?.status ?? "pending"),
                )}{" "}
                · {t("version")} {doc.versions[0]?.version_no}
              </small>
              {doc.versions[0]?.error_code && (
                <p className="error">{doc.versions[0].error_code}</p>
              )}
            </div>
            {!doc.withdrawn_at && (
              <div>
                <button
                  className="secondary"
                  onClick={() => setReplace(doc.id)}
                >
                  {t("replaceDocument")}
                </button>
                <button
                  className="secondary"
                  onClick={async () => {
                    const result = await api.DELETE(
                      "/api/v1/staff/workspaces/{workspace_id}/knowledge/documents/{document_id}",
                      {
                        params: { path: { ...path, document_id: doc.id } },
                        headers,
                      },
                    );
                    if (result.error) setError(t("error"));
                    else
                      await qc.invalidateQueries({
                        queryKey: ["knowledge", workspace],
                      });
                  }}
                >
                  {t("withdraw")}
                </button>
              </div>
            )}
          </article>
        ))
      )}
    </section>
  );
}
