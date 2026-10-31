import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api } from "@supportdesk/api-client";
import { Button, Icon, Modal, useMedia } from "../../components/ui";
import { errorCode } from "../../lib/api-error";
import type { Audience } from "./presentation";

export type SourceSelection = {
  conversationId: string;
  messageId: string;
  label: string;
};
export function SourceInspector({
  selection,
  audience,
  workspace,
  onClose,
}: {
  selection: SourceSelection;
  audience: Audience;
  workspace: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  // Phase 1's fixed-width staff index leaves too little reading space for a
  // third pane below 1440px. Reuse the existing dialog; customer policy is unchanged.
  const narrow = useMedia(
    audience === "staff" ? "(max-width: 1439px)" : "(max-width: 1199px)",
  );
  const source = useQuery({
    queryKey: [
      "citation",
      audience,
      workspace,
      selection.conversationId,
      selection.messageId,
      selection.label,
    ],
    staleTime: 0,
    queryFn: async () => {
      const params = {
        path: {
          workspace_id: workspace,
          conversation_id: selection.conversationId,
          message_id: selection.messageId,
          label: selection.label,
        },
      };
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
      if (
        result.response.status === 410 &&
        errorCode(result.error) === "SOURCE_UNAVAILABLE"
      )
        return null;
      if (!result.data) throw Error();
      return result.data;
    },
  });
  const title = source.data?.title ?? t("sourceNote");
  const content = (
    <>
      <p className="eyebrow">
        {t("sourceNote")} · <bdi dir="ltr">{selection.label}</bdi>
      </p>
      {source.isLoading || source.isFetching ? (
        <p role="status">{t("sourceLoading")}</p>
      ) : source.error ? (
        <div className="unavailable">
          <Icon name="link" />
          <p role="alert">{t("sourceError")}</p>
          <Button variant="secondary" onClick={() => source.refetch()}>
            {t("retry")}
          </Button>
        </div>
      ) : !source.data?.available ? (
        <div className="unavailable">
          <Icon name="link" />
          <h3>{t("sourceUnavailable")}</h3>
          <p>{t("sourceUnavailableHint")}</p>
        </div>
      ) : (
        <>
          <dl className="source-meta">
            <dt>{t("sourceSection")}</dt>
            <dd>{source.data.locator}</dd>
          </dl>
          <blockquote dir="auto">{source.data.excerpt}</blockquote>
          <div className="source-backref">
            <span className="source-number">{selection.label}</span>
            <strong>{t("sourceBackref")}</strong>
          </div>
          <p className="source-caveat">{t("sourceCaveat")}</p>
        </>
      )}
    </>
  );
  if (narrow)
    return (
      <Modal title={title} onClose={onClose} className="source-sheet">
        {content}
      </Modal>
    );
  return (
    <aside className="source-inspector" aria-label={t("sourceNote")}>
      <header>
        <h2>{title}</h2>
        <Button variant="ghost" aria-label={t("sourceClose")} onClick={onClose}>
          <Icon name="close" />
        </Button>
      </header>
      {content}
    </aside>
  );
}
