import { useEffect, useRef } from "react";

const FOCUSABLE =
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Traps keyboard focus inside `ref` while `active` is true.
 * - Moves focus to the first focusable element on activation.
 * - Traps Tab / Shift+Tab within the container.
 * - Closes the dialog on Escape via `onClose`.
 * - Restores focus to the previously focused element on deactivation.
 */
const useFocusTrap = (
    ref: React.RefObject<HTMLElement | null>,
    active: boolean,
    onClose: () => void
): void => {
    const previousFocus = useRef<HTMLElement | null>(null);

    useEffect(() => {
        if (!active) return;

        // Save the element that had focus before the modal opened
        previousFocus.current = document.activeElement as HTMLElement;

        // Move focus to the first focusable element inside the modal
        const el = ref.current;
        if (el) {
            const first = el.querySelectorAll<HTMLElement>(FOCUSABLE)[0];
            first?.focus();
        }

        const handleKeyDown = (e: KeyboardEvent) => {
            if (!ref.current) return;

            if (e.key === "Escape") {
                e.preventDefault();
                onClose();
                return;
            }

            if (e.key !== "Tab") return;

            const focusable = Array.from(ref.current.querySelectorAll<HTMLElement>(FOCUSABLE));
            if (focusable.length === 0) return;

            const first = focusable[0];
            const last = focusable[focusable.length - 1];

            if (e.shiftKey) {
                if (document.activeElement === first) {
                    e.preventDefault();
                    last.focus();
                }
            } else {
                if (document.activeElement === last) {
                    e.preventDefault();
                    first.focus();
                }
            }
        };

        document.addEventListener("keydown", handleKeyDown);

        return () => {
            document.removeEventListener("keydown", handleKeyDown);
            // Restore focus to the element that was focused before the modal opened
            previousFocus.current?.focus();
        };
    }, [active, ref, onClose]);
};

export default useFocusTrap;
