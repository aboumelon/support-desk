import { useTranslation } from "react-i18next";

export function DemoIndicator({
  mode,
  fictional,
}: {
  mode: "simulated" | "live" | "disabled";
  fictional: boolean;
}) {
  const { t } = useTranslation();
  return (
    <span className="demo-indicator">
      {fictional && <span>{t("demoData")}</span>}
      <span>{t(`aiMode_${mode}`)}</span>
    </span>
  );
}
