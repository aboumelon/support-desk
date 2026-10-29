const prefix = "tarvio:draft:";
export function getDraft(scope: string) {
  try {
    return sessionStorage.getItem(prefix + scope) ?? "";
  } catch {
    return "";
  }
}
export function setDraft(scope: string, value: string) {
  try {
    if (value) sessionStorage.setItem(prefix + scope, value);
    else sessionStorage.removeItem(prefix + scope);
  } catch {
    /* Composer remains usable if storage is denied. */
  }
}
export function clearDrafts() {
  try {
    Object.keys(sessionStorage)
      .filter((key) => key.startsWith(prefix))
      .forEach((key) => sessionStorage.removeItem(key));
  } catch {
    /* Storage may be unavailable. */
  }
}
