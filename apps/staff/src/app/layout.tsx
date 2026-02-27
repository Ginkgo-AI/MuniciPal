import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Munici-Pal — Staff Mission Control",
  description: "Staff dashboard for municipal AI operations",
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
