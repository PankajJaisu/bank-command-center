"use client";
import React, {
  createContext,
  useContext,
  useState,
  ReactNode,
  useEffect,
} from "react";
import {
  getCurrentUser as fetchCurrentUser,
  type UserWithVendors,
} from "./api";

// Renaming the type for clarity
export type CurrentUser = UserWithVendors;

interface AppContextType {
  currentUser: CurrentUser | null;
  isAuthenticated: boolean;
  isLoadingAuth: boolean;
  login: (token: string) => void;
  logout: () => void;
  currentInvoiceId: string | null;
  setCurrentInvoiceId: (id: string | null) => void;
  isChatOpen: boolean;
  openChat: () => void;
  closeChat: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider = ({ children }: { children: ReactNode }) => {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true); // Start as true
  const [currentInvoiceId, setCurrentInvoiceId] = useState<string | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);

  useEffect(() => {
    const validateToken = async () => {
      const token = localStorage.getItem("authToken");
      if (token) {
        try {
          const user = await fetchCurrentUser();
          setCurrentUser(user);
          setIsAuthenticated(true);
        } catch {
          // Token is invalid or expired
          localStorage.removeItem("authToken");
          setCurrentUser(null);
          setIsAuthenticated(false);
        }
      }
      setIsLoadingAuth(false);
    };
    validateToken();
  }, []);

  const login = (token: string) => {
    localStorage.setItem("authToken", token);
    setIsLoadingAuth(true);
    fetchCurrentUser()
      .then((user) => {
        setCurrentUser(user);
        setIsAuthenticated(true);
      })
      .finally(() => setIsLoadingAuth(false));
  };

  const logout = () => {
    localStorage.removeItem("authToken");
    setCurrentUser(null);
    setIsAuthenticated(false);
    // Optionally redirect to login page
    window.location.href = "/login";
  };

  const openChat = () => setIsChatOpen(true);
  const closeChat = () => setIsChatOpen(false);

  return (
    <AppContext.Provider
      value={{
        currentUser,
        isAuthenticated,
        isLoadingAuth,
        login,
        logout,
        currentInvoiceId,
        setCurrentInvoiceId,
        isChatOpen,
        openChat,
        closeChat,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error("useAppContext must be used within an AppProvider");
  }
  return context;
};
