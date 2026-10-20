import React, { createContext, useContext, useEffect } from 'react';

export type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
  isDark: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  useEffect(() => {
    const root = document.documentElement;
    const body = document.body;
    
    // Completely remove dark mode and enforce light theme across the entire project
    root.classList.remove('dark');
    root.classList.add('light');
    root.setAttribute('data-theme', 'light');
    body.classList.remove('dark-theme');
    body.classList.add('light-theme');
    
    localStorage.setItem('cryptevid_theme', 'light');
  }, []);

  const toggleTheme = () => {
    // Light theme only - no-op
  };

  const setTheme = () => {
    // Light theme only - no-op
  };

  return (
    <ThemeContext.Provider value={{ theme: 'light', toggleTheme, setTheme, isDark: false }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export default ThemeContext;
