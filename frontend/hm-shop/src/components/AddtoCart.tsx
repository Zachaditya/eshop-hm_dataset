"use client";

import { useEffect, useRef, useState } from "react";
import { useCart } from "@/components/CartProvider";
import {
  AnimatePresence,
  motion,
  useAnimationControls,
  useReducedMotion,
} from "framer-motion";

export function AddtoCart({ productId }: { productId: string }) {
  const { add } = useCart();
  const reduceMotion = useReducedMotion();

  const controls = useAnimationControls();

  const [loading, setLoading] = useState(false);
  const [added, setAdded] = useState(false);

  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, []);

  async function handleAdd() {
    if (loading) return;

    setLoading(true);
    try {
      await add(productId, 1);

      // success state
      setAdded(true);
      if (timerRef.current) window.clearTimeout(timerRef.current);
      timerRef.current = window.setTimeout(() => setAdded(false), 900);

      // ✅ spring "pop" without keyframes
      if (!reduceMotion) {
        const spring = {
          type: "spring" as const,
          stiffness: 200,
          damping: 28,
          mass: 1.0,
        };

        // pop up then settle back
        controls.start({ scale: 1.02, transition: spring }).then(() => {
          controls.start({ scale: 1, transition: spring });
        });
      }
    } catch (e: any) {
      console.error(e);
      alert(e?.message ?? String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.button
      type="button"
      disabled={loading}
      onClick={handleAdd}
      animate={controls}
      initial={{ scale: 1 }}
      whileTap={reduceMotion ? undefined : { scale: 0.98 }}
      className="relative overflow-hidden rounded-xl bg-neutral-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-60"
    >
      {/* Loading shimmer sweep */}
      <AnimatePresence>
        {loading && !reduceMotion ? (
          <motion.span
            aria-hidden
            className="pointer-events-none absolute inset-0"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.span
              className="absolute -inset-y-6 -left-24 w-24 rotate-12 bg-white/15 blur-sm"
              initial={{ x: 0 }}
              animate={{ x: 320 }}
              transition={{
                duration: 0.7,
                ease: "easeInOut",
                repeat: Infinity,
              }}
            />
          </motion.span>
        ) : null}
      </AnimatePresence>

      {/* Label swap */}
      <span className="relative inline-flex items-center gap-2">
        <AnimatePresence mode="popLayout" initial={false}>
          {added ? (
            <motion.span
              key="added"
              initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
              className="inline-flex items-center gap-2"
            >
              <motion.span
                aria-hidden
                initial={reduceMotion ? { scale: 1 } : { scale: 0.7 }}
                animate={{ scale: 1 }}
                transition={
                  reduceMotion
                    ? { duration: 0 }
                    : ({
                        type: "spring" as const,
                        stiffness: 420,
                        damping: 22,
                      } as const)
                }
              >
                ✓
              </motion.span>
              Added
            </motion.span>
          ) : loading ? (
            <motion.span
              key="loading"
              initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
            >
              Adding…
            </motion.span>
          ) : (
            <motion.span
              key="idle"
              initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
            >
              Add to cart
            </motion.span>
          )}
        </AnimatePresence>
      </span>
    </motion.button>
  );
}
