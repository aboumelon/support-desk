import type { components } from "@supportdesk/api-client";
export type Document = components["schemas"]["DocumentView"];
export function documentPresentation(doc: Document) {
  const active = doc.versions.find(
    (version) => version.id === doc.active_version_id,
  );
  const latest = [...doc.versions].sort(
    (a, b) => b.version_no - a.version_no,
  )[0];
  const usable = !doc.withdrawn_at && active?.status === "ready";
  return {
    active,
    latest,
    usable,
    status: doc.withdrawn_at ? "withdrawn" : (latest?.status ?? "pending"),
  };
}
