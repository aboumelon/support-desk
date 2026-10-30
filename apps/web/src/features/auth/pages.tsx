import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { z } from "zod";
import * as Label from "@radix-ui/react-label";
import { api } from "@supportdesk/api-client";
import { Brand, Button, Icon } from "../../components/ui";
import { resetScope } from "../../lib/query-client";
import { DemoIndicator } from "../../components/demo-indicator";
export function Landing() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const capabilities = useQuery({
    queryKey: ["public-capabilities"],
    queryFn: async () => {
      const result = await api.GET("/api/v1/public/capabilities");
      if (!result.data) throw Error();
      return result.data;
    },
  });
  async function start() {
    if (!capabilities.data?.demo_available || busy) return;
    setBusy(true);
    setError(false);
    try {
      const result = await api.POST("/api/v1/public/demo");
      if (!result.data) throw Error();
      await resetScope();
      await navigate({ to: "/workspace" });
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="entry-page">
      <header>
        <Link to="/" aria-label={t("brand")}>
          <Brand />
        </Link>
        {capabilities.data?.demo_available && (
          <DemoIndicator mode={capabilities.data.ai_mode} fictional />
        )}
      </header>
      <section className="entry-grid">
        <div className="entry-copy">
          <p className="eyebrow">{t("entryEyebrow")}</p>
          <h1>
            {t("entryTitle")}
            <br />
            <em>{t("entryAccent")}</em>
          </h1>
          <p>{t("intro")}</p>
          <div className="entry-actions">
            {capabilities.data?.demo_available && (
              <Button onClick={start} disabled={busy}>
                {t(busy ? "loading" : "demo")}
                <Icon name="arrow" />
              </Button>
            )}
            <Link className="button button--secondary" to="/login">
              {t("login")}
            </Link>
          </div>
          {capabilities.isLoading && <p role="status">{t("loading")}</p>}
          {capabilities.error && (
            <p role="alert">
              {t("apiUnavailable")}{" "}
              <button
                className="text-button"
                onClick={() => capabilities.refetch()}
              >
                {t("retry")}
              </button>
            </p>
          )}
          {capabilities.data && !capabilities.data.demo_available && (
            <p>{t("demoUnavailable")}</p>
          )}
          {error && (
            <p className="form-error" role="alert">
              {t("error")}
            </p>
          )}
          {capabilities.data?.demo_available && <small>{t("isolation")}</small>}
        </div>
        <div
          className="product-visual"
          role="img"
          aria-label={t("illustrationLabel")}
        >
          <span className="illustration-caption">{t("illustrationLabel")}</span>
          <div className="visual-thread">
            <i />
            <i />
            <i />
          </div>
          <div className="visual-card customer">
            <span>
              <Icon name="user" size={18} />
            </span>
            <div>
              <small>{t("customerMessage")}</small>
              <p>{t("illustrationQuestion")}</p>
            </div>
          </div>
          <div className="visual-card answer">
            <div className="visual-label">
              <Icon name="link" size={24} />
              <small>{t("sourceBackref")}</small>
            </div>
            <p>{t("illustrationAnswer")}</p>
            <span className="visual-source">{t("illustrationSource")}</span>
          </div>
          <div className="visual-handoff">
            <span>
              <i />
              <i />
            </span>
            <div>
              <small>{t("responsibility")}</small>
              <strong>{t("illustrationHandoff")}</strong>
            </div>
          </div>
        </div>
      </section>
      <footer>
        <span>{t("demoPerspectives")}</span>
        <span>
          {t("brand")} / <bdi dir="ltr">Tarvio</bdi>
        </span>
      </footer>
    </main>
  );
}
export function Login() {
  const { t } = useTranslation();
  const { register, handleSubmit } = useForm<{
    email: string;
    password: string;
  }>();
  const navigate = useNavigate();
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  return (
    <main className="entry-page auth-page">
      <header>
        <Link to="/">
          <Brand />
        </Link>
        <Link to="/">{t("back")}</Link>
      </header>
      <section className="auth-layout">
        <div className="entry-copy">
          <p className="eyebrow">{t("entryEyebrow")}</p>
          <h1>
            {t("entryTitle")}
            <br />
            <em>{t("entryAccent")}</em>
          </h1>
          <p>{t("humanBody")}</p>
        </div>
        <div className="auth-card">
          <Brand />
          <h1>{t("login")}</h1>
          <p>{t("loginHint")}</p>
          <form
            onSubmit={handleSubmit(async (values) => {
              setError(false);
              if (!z.email().safeParse(values.email).success) {
                setError(true);
                return;
              }
              setBusy(true);
              try {
                const result = await api.POST("/api/v1/auth/staff/login", {
                  body: values,
                });
                const workspaceId = result.data?.memberships[0]?.workspace_id;
                if (!workspaceId) throw Error();
                await resetScope();
                await navigate({
                  to: "/app/$workspaceId/inbox",
                  params: { workspaceId },
                });
              } catch {
                setError(true);
              } finally {
                setBusy(false);
              }
            })}
          >
            <Label.Root htmlFor="email">{t("email")}</Label.Root>
            <input
              className="field"
              id="email"
              type="email"
              dir="ltr"
              required
              autoComplete="username"
              {...register("email")}
            />
            <Label.Root htmlFor="password">{t("password")}</Label.Root>
            <input
              className="field"
              id="password"
              type="password"
              dir="ltr"
              required
              autoComplete="current-password"
              {...register("password")}
            />
            {error && (
              <p role="alert" className="form-error">
                {t("loginError")}
              </p>
            )}
            <Button disabled={busy}>{t(busy ? "loading" : "submit")}</Button>
          </form>
        </div>
      </section>
    </main>
  );
}
