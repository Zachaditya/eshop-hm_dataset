import "./globals.css";
import type { Metadata } from "next";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import CartProvider from "@/components/CartProvider";
import AuthProvider from "@/components/AuthProvider";
import AgentChat from "@/components/AgentChat";
import { Suspense } from "react";

export const metadata: Metadata = {
  title: "Ecom",
  description: "Minimal ecommerce storefront",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-neutral-50 text-neutral-900">
        <AuthProvider>
          <CartProvider>
            <div className="flex min-h-screen flex-col">
              <Suspense>
                <Navbar />
              </Suspense>

              <main className="flex-1">{children}</main>
              <Footer />
            </div>
          </CartProvider>
        </AuthProvider>
        <AgentChat />
      </body>
    </html>
  );
}
