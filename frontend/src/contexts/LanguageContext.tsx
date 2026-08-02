import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { translate } from "../lib/i18n";
import type { Lang } from "../lib/i18n";

interface LanguageContextValue {
  lang: Lang;
  toggle: () => void;
  t: (text: string) => string;
}

const LanguageContext = createContext<LanguageContextValue>({
  lang: "id",
  toggle: () => {},
  t: (text) => text,
});

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(
    () => (localStorage.getItem("c3mr:lang") === "en" ? "en" : "id"),
  );

  useEffect(() => {
    localStorage.setItem("c3mr:lang", lang);
    document.documentElement.lang = lang;
  }, [lang]);

  return (
    <LanguageContext.Provider
      value={{ lang, toggle: () => setLang(l => (l === "id" ? "en" : "id")), t: (text) => translate(lang, text) }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export const useLang = () => useContext(LanguageContext);
