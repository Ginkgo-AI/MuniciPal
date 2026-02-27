"use client";

import { useEffect, useState } from "react";
import { NextIntlClientProvider } from "next-intl";
import { LocaleProvider, useLocaleContext } from "./locale-context";
import type { Locale } from "./routing";

import enMessages from "../../messages/en.json";
import esMessages from "../../messages/es.json";

const allMessages: Record<Locale, typeof enMessages> = {
  en: enMessages,
  es: esMessages,
};

function IntlInner({ children }: { children: React.ReactNode }) {
  const { locale } = useLocaleContext();
  const [messages, setMessages] = useState(allMessages[locale]);

  useEffect(() => {
    const resolved = allMessages[locale];
    if (!resolved) {
      console.error(`No messages for locale "${locale}", falling back to English.`);
    }
    setMessages(resolved ?? allMessages.en);
  }, [locale]);

  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      {children}
    </NextIntlClientProvider>
  );
}

export function IntlProvider({
  initialLocale,
  children,
}: {
  initialLocale: Locale;
  children: React.ReactNode;
}) {
  return (
    <LocaleProvider initialLocale={initialLocale}>
      <IntlInner>{children}</IntlInner>
    </LocaleProvider>
  );
}
