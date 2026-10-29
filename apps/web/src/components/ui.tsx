import {
  useEffect,
  useId,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";

export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    inbox: (
      <>
        <path d="M4 5h16v14H4z" />
        <path d="M4 14h5l2 2h2l2-2h5" />
      </>
    ),
    book: (
      <>
        <path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z" />
        <path d="M8 4v16" />
      </>
    ),
    user: (
      <>
        <circle cx="12" cy="8" r="3" />
        <path d="M5 20c.8-4 3.1-6 7-6s6.2 2 7 6" />
      </>
    ),
    logout: (
      <>
        <path d="M10 5H5v14h5" />
        <path d="M13 8l4 4-4 4M8 12h9" />
      </>
    ),
    search: (
      <>
        <circle cx="10.5" cy="10.5" r="6" />
        <path d="m15 15 4 4" />
      </>
    ),
    close: <path d="m6 6 12 12M18 6 6 18" />,
    send: (
      <>
        <path d="m4 5 16 7-16 7 3-7z" />
        <path d="M7 12h13" />
      </>
    ),
    plus: <path d="M12 5v14M5 12h14" />,
    upload: (
      <>
        <path d="M12 16V4m0 0L8 8m4-4 4 4" />
        <path d="M5 14v6h14v-6" />
      </>
    ),
    link: (
      <>
        <path d="M10 13a4 4 0 0 0 5.7.1l2.4-2.4A4 4 0 0 0 12.4 5l-1.3 1.3" />
        <path d="M14 11a4 4 0 0 0-5.7-.1l-2.4 2.4a4 4 0 0 0 5.7 5.7l1.3-1.3" />
      </>
    ),
    arrow: <path d="M8 5l7 7-7 7" />,
    copy: (
      <>
        <rect x="8" y="8" width="11" height="11" rx="1" />
        <path d="M16 8V5H5v11h3" />
      </>
    ),
    settings: (
      <>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2" />
      </>
    ),
  };
  return (
    <svg
      className="icon"
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}
export function Brand({ light = false }: { light?: boolean }) {
  const { t } = useTranslation();
  return (
    <span className={`tarvio-brand ${light ? "light" : ""}`}>
      <svg
        role="img"
        aria-label={t("brandLabel")}
        width="40"
        height="40"
        viewBox="0 0 40 40"
        fill="none"
      >
        <path
          d="M8 12.5C8 9.5 10.4 7 13.5 7H27M32 27.5C32 30.5 29.6 33 26.5 33H13"
          stroke="currentColor"
          strokeWidth="3.2"
        />
        <path
          d="M27 7v9.5L13 23v10"
          stroke={light ? "#AEB8FF" : "#354AE8"}
          strokeWidth="3.2"
        />
      </svg>
      <span>
        <strong>{t("brand")}</strong>
        <small>{t("latinBrand")}</small>
      </span>
    </span>
  );
}
export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
}) {
  return (
    <button {...props} className={`button button--${variant} ${className}`} />
  );
}
export function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty-state">
      <span className="empty-glyph">
        <Icon name="inbox" />
      </span>
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}
export function useMedia(query: string) {
  const [matches, setMatches] = useState(
    () => window.matchMedia(query).matches,
  );
  useEffect(() => {
    const media = window.matchMedia(query);
    const update = () => setMatches(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, [query]);
  return matches;
}
export function Modal({
  title,
  onClose,
  children,
  className = "",
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  className?: string;
}) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const trigger = document.activeElement as HTMLElement | null;
    const dialog = ref.current!;
    const root = document.getElementById("root");
    const wasInert = root?.inert ?? false;
    if (root) root.inert = true;
    dialog.showModal();
    const focusables = () =>
      Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((node) => node.getClientRects().length > 0);
    focusables()[0]?.focus();
    const trap = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const nodes = focusables();
      const first = nodes[0],
        last = nodes.at(-1);
      if (!first) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      if (
        !dialog.contains(document.activeElement) ||
        (event.shiftKey && document.activeElement === first)
      ) {
        event.preventDefault();
        (event.shiftKey ? last : first)?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    const cancel = (event: Event) => {
      event.preventDefault();
      close.current();
    };
    dialog.addEventListener("cancel", cancel);
    dialog.addEventListener("keydown", trap);
    return () => {
      dialog.removeEventListener("cancel", cancel);
      dialog.removeEventListener("keydown", trap);
      dialog.close();
      if (root) root.inert = wasInert;
      if (trigger?.isConnected) trigger.focus();
    };
  }, []);
  return createPortal(
    <div className="tarvio modal-host">
      <dialog
        ref={ref}
        className={`dialog ${className}`}
        aria-modal="true"
        tabIndex={-1}
        aria-labelledby={id}
        onClick={(event) => {
          if (event.target === event.currentTarget) {
            const rect = event.currentTarget.getBoundingClientRect();
            if (
              event.clientX < rect.left ||
              event.clientX > rect.right ||
              event.clientY < rect.top ||
              event.clientY > rect.bottom
            )
              onClose();
          }
        }}
      >
        <header>
          <h2 id={id}>{title}</h2>
          <Button
            variant="ghost"
            onClick={onClose}
            aria-label={t("closeDialog")}
          >
            <Icon name="close" />
          </Button>
        </header>
        {children}
      </dialog>
    </div>,
    document.body,
  );
}
