import { QueryClient } from "@tanstack/react-query";
import { clearPending } from "./pending-sends";
import { clearDrafts } from "./composer-drafts";
export const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, staleTime: 15000 } },
});
export async function resetScope() {
  await clearPending();
  clearDrafts();
  queryClient.clear();
}
