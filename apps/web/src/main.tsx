import { clearPending } from "./lib/pending-sends";
import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import {
  createRootRoute,
  createRoute,
  createRouter,
  RouterProvider,
  Outlet,
  Link,
  useNavigate,
  useParams,
} from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { z } from "zod";
import * as Label from "@radix-ui/react-label";
import i18n from "i18next";
import { initReactI18next, useTranslation } from "react-i18next";
import { api, type components } from "@supportdesk/api-client";
import fa from "./locales/fa.json";
import en from "./locales/en.json";
import "./styles/app.css";

const Desk = React.lazy(() =>
  import("./features/conversation/desk").then((module) => ({
    default: module.Desk,
  })),
);
const Knowledge = React.lazy(() =>
  import("./features/knowledge/knowledge").then((module) => ({
    default: module.Knowledge,
  })),
);
i18n.use(initReactI18next).init({
  resources: { fa: { translation: fa }, en: { translation: en } },
  lng: "fa",
  fallbackLng: "fa",
  interpolation: { escapeValue: false },
});
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, staleTime: 15000 } },
});
type Session = components["schemas"]["SessionView"];

function Shell() {
  const { t } = useTranslation();
  return (
    <div className="shell">
      <header>
        <Link to="/" className="brand">
          <span className="brand-icon">ن</span>
          <strong>{t("brand")}</strong>
          <span className="brand-sub">{t("product")}</span>
        </Link>
        <nav>
          <span className="fixture">
            <i />
            {t("fixture")}
          </span>
          <Link to="/login">{t("login")} ↗</Link>
        </nav>
      </header>
      <Outlet />
      <footer>
        <span>
          {t("brand")} / {t("product")}
        </span>
        <span>{t("fixtureNote")}</span>
      </footer>
    </div>
  );
}
function Landing() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  async function start() {
    setBusy(true);
    setError(false);
    try {
      const { data, error } = await api.POST("/api/v1/public/demo");
      if (error || !data) throw Error();
      await clearPending();
      queryClient.clear();
      await navigate({ to: "/workspace" });
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="landing">
      <div className="hero">
        <span className="eyebrow">{t("product")} / ۰۱</span>
        <h1>{t("tagline")}</h1>
        <p>{t("intro")}</p>
        <div className="actions">
          <button onClick={start} disabled={busy}>
            {t(busy ? "loading" : "demo")} <span>←</span>
          </button>
          <Link className="secondary" to="/login">
            {t("login")}
          </Link>
        </div>
        {error && (
          <p role="alert" className="error">
            {t("error")}
          </p>
        )}
        <small>{t("isolation")}</small>
      </div>
      <aside className="hero-art" aria-hidden="true">
        <div className="orbit orbit-one" />
        <div className="orbit orbit-two" />
        <span className="art-label">{t("brand")}</span>
        <div className="bubble one">
          <span />
          <span />
          <span />
        </div>
        <div className="bubble two">✓</div>
        <div className="art-caption">
          {t("secure")} <b>↗</b>
        </div>
      </aside>
      <section className="features">
        {["isolation", "human", "grounded"].map((key, index) => (
          <article key={key}>
            <span className="number">۰{index + 1}</span>
            <h2>{t(key)}</h2>
            <p>{t(key + "Body")}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
function Login() {
  const { t } = useTranslation();
  const { register, handleSubmit } = useForm<{
    email: string;
    password: string;
  }>();
  const navigate = useNavigate();
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  return (
    <main className="auth-page">
      <div className="auth-card">
        <span className="eyebrow">{t("operator")}</span>
        <h1>{t("login")}</h1>
        <form
          onSubmit={handleSubmit(async (values) => {
            setError(false);
            if (!z.email().safeParse(values.email).success) {
              setError(true);
              return;
            }
            setBusy(true);
            try {
              const { data, error } = await api.POST(
                "/api/v1/auth/staff/login",
                {
                  body: values,
                },
              );
              const workspaceId = data?.memberships[0]?.workspace_id;
              if (error || !workspaceId) throw Error();
              await clearPending();
              queryClient.clear();
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
            id="email"
            type="email"
            dir="ltr"
            autoComplete="username"
            required
            {...register("email")}
          />
          <Label.Root htmlFor="password">{t("password")}</Label.Root>
          <input
            id="password"
            type="password"
            dir="ltr"
            autoComplete="current-password"
            required
            {...register("password")}
          />
          {error && (
            <p role="alert" className="error">
              {t("error")}
            </p>
          )}
          <button disabled={busy}>{t(busy ? "loading" : "submit")}</button>
        </form>
        <Link to="/">{t("back")}</Link>
      </div>
    </main>
  );
}
function Workspace() {
  const { t } = useTranslation();
  const params = useParams({ strict: false });
  const [audience, setAudience] = useState<"customer" | "staff">(
    location.pathname.startsWith("/app/") ? "staff" : "customer",
  );
  const [knowledge, setKnowledge] = useState(
    location.pathname.endsWith("/knowledge") ||
      location.pathname.endsWith("/settings"),
  );
  const navigate = useNavigate();
  const session = useQuery({
    queryKey: ["session", audience],
    queryFn: async () => {
      const result =
        audience === "customer"
          ? await api.GET("/api/v1/customer/session")
          : await api.GET("/api/v1/auth/staff/me");
      if (!result.data) throw Error();
      return result.data;
    },
  });
  const scopedSession =
    session.data && audience === "staff" && params.workspaceId
      ? {
          ...session.data,
          memberships: session.data.memberships.filter(
            (m) => m.workspace_id === params.workspaceId,
          ),
        }
      : session.data;
  async function logout(value: Session) {
    const headers = { "X-CSRF-Token": value.csrf_token };
    const result =
      audience === "customer"
        ? await api.POST("/api/v1/customer/logout", { headers })
        : await api.POST("/api/v1/auth/staff/logout", { headers });
    if (!result.error) {
      await clearPending();
      queryClient.clear();
      await navigate({ to: "/" });
    }
  }
  return (
    <main className="workspace-page">
      <aside className="sidebar">
        <span className="eyebrow">{t("workspace")}</span>
        <h2>{t("welcome")}</h2>
        <button
          className={audience === "customer" ? "selected" : "ghost"}
          onClick={() => {
            setAudience("customer");
            setKnowledge(false);
          }}
        >
          {t("customer")}
        </button>
        <button
          className={audience === "staff" ? "selected" : "ghost"}
          onClick={() => {
            setAudience("staff");
            setKnowledge(false);
          }}
        >
          {t("operator")}
        </button>
        {audience === "staff" &&
          scopedSession?.memberships.some((m) => m.role === "admin") && (
            <button
              className={knowledge ? "selected" : "ghost"}
              onClick={() => setKnowledge(true)}
            >
              {t("knowledge")}
            </button>
          )}
      </aside>
      <section className="workspace-content">
        <span className="eyebrow">{t("sessions")}</span>
        {session.isLoading ? (
          <p>{t("loading")}</p>
        ) : session.error ? (
          <p role="alert">{t("sessionExpired")}</p>
        ) : (
          scopedSession && (
            <>
              <React.Suspense fallback={<p>{t("loading")}</p>}>
                {knowledge && audience === "staff" ? (
                  <Knowledge session={scopedSession} />
                ) : (
                  <Desk
                    key={`${audience}:${params.workspaceId ?? "demo"}:${params.conversationId ?? ""}`}
                    session={scopedSession}
                    audience={audience}
                    initialConversation={params.conversationId}
                  />
                )}
              </React.Suspense>
              <button
                className="secondary logout"
                onClick={() => logout(scopedSession)}
              >
                {t("logout")}
              </button>
            </>
          )
        )}
      </section>
    </main>
  );
}
function CustomerEntry() {
  const { t } = useTranslation();
  const { publicKey } = chatRoute.useParams();
  const session = useQuery({
    queryKey: ["public-session", publicKey],
    queryFn: async () => {
      const current = await api.GET("/api/v1/customer/session");
      if (current.data?.public_key === publicKey) return current.data;
      const created = await api.POST(
        "/api/v1/public/workspaces/{public_key}/visitor-sessions",
        { params: { path: { public_key: publicKey } } },
      );
      if (!created.data) throw Error();
      await clearPending();
      queryClient.removeQueries({ queryKey: ["snapshot", "customer"] });
      return created.data;
    },
  });
  if (!session.data)
    return (
      <main className="auth-page">
        {t(session.error ? "error" : "loading")}
      </main>
    );
  return (
    <main className="customer-page">
      <React.Suspense fallback={<p>{t("loading")}</p>}>
        <Desk audience="customer" session={session.data} />
      </React.Suspense>
    </main>
  );
}
const rootRoute = createRootRoute({ component: Shell });
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: Landing,
});
const demoRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/demo",
  component: Landing,
});
const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: Login,
});
const workspaceRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/workspace",
  component: Workspace,
});
const chatRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/chat/$publicKey",
  component: CustomerEntry,
});
const inboxRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app/$workspaceId/inbox",
  component: Workspace,
});
const conversationRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app/$workspaceId/conversations/$conversationId",
  component: Workspace,
});
const knowledgeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app/$workspaceId/knowledge",
  component: Workspace,
});
const settingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app/$workspaceId/settings",
  component: Workspace,
});
const router = createRouter({
  routeTree: rootRoute.addChildren([
    indexRoute,
    demoRoute,
    loginRoute,
    workspaceRoute,
    chatRoute,
    inboxRoute,
    conversationRoute,
    knowledgeRoute,
    settingsRoute,
  ]),
});
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>,
);
