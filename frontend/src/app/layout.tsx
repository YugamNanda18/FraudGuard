import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FraudAI Agent",
  description:
    "AI-powered fraud prevention and regulatory compliance assistant",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className="dark">
      <body className="h-screen overflow-hidden">{children}</body>
    </html>
  );
}
