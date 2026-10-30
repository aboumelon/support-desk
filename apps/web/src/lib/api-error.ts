export function errorCode(value: unknown): string | undefined {
  return typeof value === "object" &&
    value !== null &&
    "code" in value &&
    typeof value.code === "string"
    ? value.code
    : undefined;
}
export function errorDetails(value: unknown): Record<string, unknown> {
  if (
    typeof value === "object" &&
    value !== null &&
    "details" in value &&
    typeof value.details === "object" &&
    value.details !== null
  )
    return value.details as Record<string, unknown>;
  return {};
}
export function errorKey(value: unknown) {
  const code = errorCode(value);
  return (
    (
      {
        RATE_LIMITED: "resourceLimit",
        STORAGE_CAPACITY_REACHED: "resourceLimit",
        INGESTION_CAPACITY_REACHED: "resourceLimit",
        DEMO_CAPACITY_REACHED: "resourceLimit",
        FORBIDDEN: "permissionError",
        FILE_TOO_LARGE: "fileTooLarge",
        UNSUPPORTED_DOCUMENT: "unsupportedDocument",
        INVALID_TITLE: "invalidTitle",
        ASSISTANT_UNAVAILABLE: "nothingReady",
        ASSISTANT_DISABLED: "assistantDisabled",
        ASSISTANT_REQUIRES_KNOWLEDGE: "nothingReady",
        SESSION_EXPIRED: "sessionExpired",
      } as Record<string, string>
    )[code ?? ""] ?? "error"
  );
}
