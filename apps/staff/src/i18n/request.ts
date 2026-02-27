import { getRequestConfig } from "next-intl/server";
import { locales, defaultLocale } from "./routing";

export default getRequestConfig(async () => {
  const locale = "en";
  const safeLocale = locales.includes(locale as (typeof locales)[number])
    ? locale
    : defaultLocale;
  return {
    locale: safeLocale,
    messages: (await import(`../../messages/${safeLocale}.json`)).default,
  };
});
