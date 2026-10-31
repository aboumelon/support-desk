import { useLayoutEffect, useRef, type RefObject } from "react";
import {
  readPanePosition,
  savePanePosition,
  type PanePosition,
} from "./inbox-view";

// Keep panes mounted. display:none can clamp scrollTop to zero, so only a visible,
// settled viewport may replace the last user position. Anchors survive text reflow.
export function usePanePosition({
  viewport,
  scope,
  enabled,
  visible,
  ready = true,
  anchorAttribute,
  onRestore,
}: {
  viewport: RefObject<HTMLDivElement | null>;
  scope: string;
  enabled: boolean;
  visible: boolean;
  ready?: boolean;
  anchorAttribute: "data-message-id" | "data-conversation-id";
  onRestore?: (bottom: boolean) => void;
}) {
  const saved = useRef<PanePosition | null>(null);
  const dimensions = useRef({ width: 0, height: 0 });
  const restoring = useRef(false);
  const options = useRef({ enabled, visible, ready, onRestore });
  options.current = { enabled, visible, ready, onRestore };

  const remember = () => {
    const el = viewport.current;
    if (
      !el ||
      !options.current.enabled ||
      !options.current.visible ||
      !options.current.ready ||
      restoring.current ||
      !el.getClientRects().length ||
      el.clientWidth !== dimensions.current.width ||
      el.clientHeight !== dimensions.current.height
    )
      return false;
    const top = el.getBoundingClientRect().top;
    const anchor = Array.from(
      el.querySelectorAll<HTMLElement>(`[${anchorAttribute}]`),
    ).find((node) => node.getBoundingClientRect().bottom > top);
    saved.current = {
      top: el.scrollTop,
      bottom: el.scrollHeight - el.scrollTop - el.clientHeight < 80,
      anchor: anchor?.getAttribute(anchorAttribute) ?? undefined,
      offset: anchor ? anchor.getBoundingClientRect().top - top : undefined,
    };
    savePanePosition(scope, saved.current);
    return true;
  };

  useLayoutEffect(() => {
    if (!enabled) return;
    saved.current = readPanePosition(scope);
    const el = viewport.current;
    if (!el || !visible || !ready) return;
    let frame = 0;
    const restore = () => {
      if (!el.getClientRects().length) return;
      restoring.current = true;
      dimensions.current = { width: el.clientWidth, height: el.clientHeight };
      const position = saved.current;
      if (position) {
        const anchor = Array.from(
          el.querySelectorAll<HTMLElement>(`[${anchorAttribute}]`),
        ).find(
          (node) => node.getAttribute(anchorAttribute) === position.anchor,
        );
        if (position.bottom) el.scrollTop = el.scrollHeight;
        else if (anchor && position.offset !== undefined)
          el.scrollTop +=
            anchor.getBoundingClientRect().top -
            el.getBoundingClientRect().top -
            position.offset;
        else el.scrollTop = position.top;
        options.current.onRestore?.(position.bottom);
      }
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        restoring.current = false;
      });
    };
    restore();
    const observer = new ResizeObserver(restore);
    observer.observe(el);
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
      restoring.current = false;
    };
  }, [scope, enabled, visible, ready, anchorAttribute, viewport]);

  return remember;
}
