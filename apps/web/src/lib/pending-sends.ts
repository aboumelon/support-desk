export type PendingSend = {
  key: string;
  scope: string;
  client_message_id: string;
  body: string;
};
function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("supportdesk-pending", 1);
    request.onupgradeneeded = () =>
      request.result.createObjectStore("sends", { keyPath: "key" });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
export async function savePending(item: PendingSend): Promise<void> {
  const db = await open();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction("sends", "readwrite");
      tx.objectStore("sends").put(item);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
export async function removePending(key: string): Promise<void> {
  const db = await open();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction("sends", "readwrite");
      tx.objectStore("sends").delete(key);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
export async function pendingFor(scope: string): Promise<PendingSend[]> {
  const db = await open();
  try {
    return await new Promise((resolve, reject) => {
      const request = db.transaction("sends").objectStore("sends").getAll();
      request.onsuccess = () =>
        resolve(
          (request.result as PendingSend[]).filter(
            (item) => item.scope === scope,
          ),
        );
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}
export async function clearPending(): Promise<void> {
  const db = await open();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction("sends", "readwrite");
      tx.objectStore("sends").clear();
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
