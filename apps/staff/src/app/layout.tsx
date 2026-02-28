import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { IntlProvider } from "@/i18n/intl-provider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "MuniciPal — Staff Mission Control",
  description: "Staff dashboard for municipal AI operations",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} min-h-screen antialiased`}>
        <IntlProvider initialLocale="en">
          {children}
        </IntlProvider>
      </body>
    </html>
  );
}
