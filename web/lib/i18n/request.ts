import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";

export const LOCALES = ["en", "hi"] as const;
export type Locale = (typeof LOCALES)[number];

export default getRequestConfig(async () => {
  const store = await cookies();
  const raw = store.get("virasat_locale")?.value;
  const locale: Locale = raw === "hi" ? "hi" : "en";
  return { locale, messages: (await import(`../../messages/${locale}.json`)).default };
});
