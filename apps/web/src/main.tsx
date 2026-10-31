import React, { useEffect } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import {
  createRootRoute,
  createRoute,
  createRouter,
  RouterProvider,
  Outlet,
  Link,
  useLocation,
  useNavigate,
  useParams,
  redirect,
} from "@tanstack/react-router";
import i18n from "i18next";
import { initReactI18next, useTranslation } from "react-i18next";
import { api } from "@supportdesk/api-client";
import { clearPending } from "./lib/pending-sends";
import { clearDrafts } from "./lib/composer-drafts";
import { queryClient, resetScope } from "./lib/query-client";
import { Brand, Button, EmptyState, Icon } from "./components/ui";
import { DemoIndicator } from "./components/demo-indicator";
import type { Audience, Session } from "./features/conversation/presentation";
import fa from "./locales/fa.json";
import en from "./locales/en.json";
import "@fontsource-variable/estedad";
import "@fontsource-variable/inter";
import "./styles/app.css";

const Landing = React.lazy(() =>
  import("./features/auth/pages").then((module) => ({
    default: module.Landing,
  })),
);
const Login = React.lazy(() =>
  import("./features/auth/pages").then((module) => ({ default: module.Login })),
);
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
function useSession(audience: Audience) {
  return useQuery({
    queryKey: ["session", audience],
    queryFn: async () => {
      const result =
        audience === "customer"
          ? await api.GET("/api/v1/customer/session")
          : await api.GET("/api/v1/auth/staff/me");
      if (result.data) return result.data;
      if ([401, 403].includes(result.response.status)) return null;
      throw Error();
    },
  });
}
function Shell() {
  const { t } = useTranslation();
  return (
    <div className="tarvio" dir="rtl">
      <React.Suspense
        fallback={
          <div className="route-status" role="status">
            {t("loading")}
          </div>
        }
      >
        <Outlet />
      </React.Suspense>
    </div>
  );
}
function Rail({
  session,
  customer,
  section,
  onLogout,
}: {
  session: Session;
  customer: Session | null | undefined;
  section: string;
  onLogout: () => void;
}) {
  const { t } = useTranslation();
  const membership = session.memberships[0];
  const workspaceId = membership.workspace_id;
  const canCustomer =
    customer?.workspace_id === workspaceId && customer.public_key;
  return (
    <aside className="rail" aria-label={t("mainNav")}>
      <Link to="/" className="rail__brand" aria-label={t("brand")}>
        <Brand light />
      </Link>
      <nav className="rail__nav">
        <Link
          className={section === "inbox" ? "active" : ""}
          to="/app/$workspaceId/inbox"
          params={{ workspaceId }}
        >
          <Icon name="inbox" />
          <span>{t("inbox")}</span>
        </Link>
        {membership.role === "admin" && (
          <>
            <Link
              className={section === "knowledge" ? "active" : ""}
              to="/app/$workspaceId/knowledge"
              params={{ workspaceId }}
            >
              <Icon name="book" />
              <span>{t("knowledge")}</span>
            </Link>
          </>
        )}
      </nav>
      <div className="rail__bottom">
        <span className="demo-label" title={membership.name}>
          {t(membership.role)}
        </span>
        {canCustomer && (
          <Link to="/chat/$publicKey" params={{ publicKey: canCustomer }}>
            <Icon name="user" />
            <span>{t("customerView")}</span>
          </Link>
        )}
        <button onClick={onLogout}>
          <Icon name="logout" />
          <span>{t("logout")}</span>
        </button>
      </div>
    </aside>
  );
}
function CustomerFrame({
  session,
  staff,
  onLogout,
}: {
  session: Session;
  staff: Session | null | undefined;
  onLogout: () => void;
}) {
  const { t } = useTranslation();
  const membership = staff?.memberships.find(
    (m) => m.workspace_id === session.workspace_id,
  );
  return (
    <main className="customer-page">
      <header className="customer-header">
        <Link to="/">
          <Brand />
        </Link>
        <DemoIndicator
          fictional={session.fictional_data ?? false}
          mode={
            session.ai_available === false
              ? "disabled"
              : session.provider_mode === "fake"
                ? "simulated"
                : "live"
          }
        />
        <div className="customer-actions">
          {membership && (
            <Link
              className="button button--secondary"
              to="/app/$workspaceId/inbox"
              params={{ workspaceId: membership.workspace_id }}
            >
              {t("staffView")}
            </Link>
          )}
          <Button variant="ghost" onClick={onLogout} aria-label={t("logout")}>
            <Icon name="logout" />
          </Button>
        </div>
      </header>
      <div className="customer-layout">
        <React.Suspense fallback={<p role="status">{t("loading")}</p>}>
          <Desk
            key={`${session.workspace_id}:${session.actor_id}`}
            session={session}
            audience="customer"
          />
        </React.Suspense>
      </div>
    </main>
  );
}
function Workspace() {
  const { t } = useTranslation();
  const params = useParams({ strict: false });
  const pathname = useLocation({ select: (location) => location.pathname });
  const staffRoute = pathname.startsWith("/app/");
  const audience: Audience = staffRoute ? "staff" : "customer";
  const staff = useSession("staff");
  const customer = useSession("customer");
  const session = staffRoute ? staff : customer;
  const navigate = useNavigate();
  const membership = staff.data?.memberships.find(
    (m) =>
      m.workspace_id ===
      (params.workspaceId ?? staff.data?.memberships[0]?.workspace_id),
  );
  const scoped =
    staff.data && membership
      ? { ...staff.data, memberships: [membership] }
      : null;
  useEffect(() => {
    if (!staffRoute && customer.data === null && staff.data?.memberships[0])
      void navigate({
        to: "/app/$workspaceId/inbox",
        params: { workspaceId: staff.data.memberships[0].workspace_id },
      });
  }, [customer.data, staff.data, staffRoute]);
  async function logout(value: Session) {
    const headers = { "X-CSRF-Token": value.csrf_token };
    const result =
      audience === "customer"
        ? await api.POST("/api/v1/customer/logout", { headers })
        : await api.POST("/api/v1/auth/staff/logout", { headers });
    if (!result.error) {
      await resetScope();
      await navigate({ to: "/" });
    }
  }
  if (session.isLoading)
    return (
      <div className="route-status" role="status">
        {t("loading")}
      </div>
    );
  if (!session.data || (staffRoute && !scoped))
    return (
      <main className="route-status">
        <Brand />
        <p role="alert">
          {t(
            session.error
              ? "apiUnavailable"
              : staffRoute && staff.data
                ? "accessDenied"
                : "sessionExpired",
          )}
        </p>
        <Link className="button button--primary" to="/login">
          {t("login")}
        </Link>
        <Link to="/demo">{t("demo")}</Link>
      </main>
    );
  if (!staffRoute)
    return (
      <CustomerFrame
        session={session.data}
        staff={staff.data}
        onLogout={() => logout(session.data!)}
      />
    );
  const section = pathname.endsWith("/knowledge")
    ? "knowledge"
    : pathname.endsWith("/settings")
      ? "settings"
      : "inbox";
  return (
    <main
      className={`workspace-shell ${section === "inbox" ? "inbox-workspace" : ""}`}
    >
      <Rail
        session={scoped!}
        customer={customer.data}
        section={section}
        onLogout={() => logout(scoped!)}
      />
      <div className="workspace-content">
        <header className="workspace-status">
          <DemoIndicator
            fictional={membership?.fictional_data ?? false}
            mode={
              scoped!.ai_available === false
                ? "disabled"
                : scoped!.provider_mode === "fake"
                  ? "simulated"
                  : "live"
            }
          />
        </header>
        <React.Suspense
          fallback={
            <p className="route-status" role="status">
              {t("loading")}
            </p>
          }
        >
          {section !== "inbox" ? (
            <div className="workspace-scroll">
              {membership?.role === "admin" ? (
                <Knowledge key={membership.workspace_id} session={scoped!} />
              ) : (
                <EmptyState title={t("accessDenied")} text={t("readOnly")} />
              )}
            </div>
          ) : (
            <Desk
              key={`${membership!.workspace_id}:${membership!.actor_id}`}
              session={scoped!}
              audience="staff"
              initialConversation={params.conversationId}
            />
          )}
        </React.Suspense>
      </div>
    </main>
  );
}
function CustomerEntry() {
  const { t } = useTranslation();
  const { publicKey } = chatRoute.useParams();
  const staff = useSession("staff");
  const navigate = useNavigate();
  const session = useQuery({
    queryKey: ["public-session", publicKey],
    queryFn: async () => {
      const current = await api.GET("/api/v1/customer/session");
      if (current.data?.public_key === publicKey) return current.data;
      if (!current.data && ![401, 403].includes(current.response.status))
        throw Error();
      const result = await api.POST(
        "/api/v1/public/workspaces/{public_key}/visitor-sessions",
        { params: { path: { public_key: publicKey } } },
      );
      if (!result.data) throw Error();
      await clearPending();
      clearDrafts();
      queryClient.removeQueries({ queryKey: ["snapshot", "customer"] });
      return result.data;
    },
  });
  if (!session.data)
    return (
      <div className="route-status">
        <Brand />
        <p role={session.error ? "alert" : "status"}>
          {t(session.error ? "error" : "loading")}
        </p>
        {session.error && (
          <>
            <Button onClick={() => session.refetch()}>{t("retry")}</Button>
            <Link to="/">{t("back")}</Link>
          </>
        )}
      </div>
    );
  return (
    <CustomerFrame
      session={session.data}
      staff={staff.data}
      onLogout={async () => {
        const result = await api.POST("/api/v1/customer/logout", {
          headers: { "X-CSRF-Token": session.data!.csrf_token },
        });
        if (!result.error) {
          await resetScope();
          await navigate({ to: "/" });
        }
      }}
    />
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
  beforeLoad: ({ params }) => {
    throw redirect({
      to: "/app/$workspaceId/knowledge",
      params: { workspaceId: params.workspaceId },
      replace: true,
    });
  },
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
