import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

interface ThemeContextValue {
  dark: boolean;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({ dark: false, toggle: () => {} });

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [dark, setDark] = useState(() => localStorage.getItem("c3mr:theme") === "dark");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("c3mr:theme", dark ? "dark" : "light");
  }, [dark]);

  return (
    <ThemeContext.Provider value={{ dark, toggle: () => setDark(d => !d) }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
