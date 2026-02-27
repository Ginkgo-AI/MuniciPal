import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Munici-Pal — City Services",
  description: "Your AI-powered municipal services assistant",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
