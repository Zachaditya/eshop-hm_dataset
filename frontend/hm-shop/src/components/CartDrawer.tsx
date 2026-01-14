"use client";

import { CartContents } from "@/components/CartContents";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

export function CartDrawer({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* backdrop */}
          <motion.button
            aria-label="Close cart"
            className="absolute inset-0 bg-black/40"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{
              opacity: 1,
              transition: { duration: reduceMotion ? 0 : 0.18 },
            }}
            exit={{
              opacity: 0,
              transition: { duration: reduceMotion ? 0 : 0.12 },
            }}
          />

          {/* panel (RIGHT) */}
          <motion.div
            className="absolute top-0 right-0 h-full w-full max-w-md bg-white p-5 shadow-xl"
            initial={reduceMotion ? { x: 0 } : { x: "100%" }}
            animate={
              reduceMotion
                ? { x: 0 }
                : {
                    x: 0,
                    transition: {
                      type: "spring",
                      stiffness: 220,
                      damping: 28,
                      mass: 1.0,
                    },
                  }
            }
            exit={
              reduceMotion
                ? { x: 0 }
                : {
                    x: "100%",
                    transition: { duration: 0.22, ease: "easeInOut" },
                  }
            }
          >
            <div className="flex items-center justify-between">
              <div className="text-lg font-semibold">Cart</div>
              <button className="text-sm underline" onClick={onClose}>
                Close →
              </button>
            </div>

            <div className="mt-4">
              <CartContents
                onCheckoutDone={(orderId) => {
                  alert(`Order placed: ${orderId}`);
                  onClose();
                }}
              />
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
