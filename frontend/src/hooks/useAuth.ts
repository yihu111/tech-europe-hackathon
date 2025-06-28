
import { useState, useEffect } from "react";
import { User } from "@/types";

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate checking for existing auth
    const checkAuth = () => {
      const storedUser = localStorage.getItem("skillscope_user");
      if (storedUser) {
        setUser(JSON.parse(storedUser));
      }
      setLoading(false);
    };

    checkAuth();
  }, []);

  const login = (email: string, password: string) => {
    // Mock login - in production, this would call your auth API
    const mockUser: User = {
      id: "1",
      username: email.split("@")[0],
      email: email,
    };
    
    setUser(mockUser);
    localStorage.setItem("skillscope_user", JSON.stringify(mockUser));
    return Promise.resolve(mockUser);
  };

  const register = (email: string, password: string, username: string) => {
    // Mock registration - in production, this would call your auth API
    const mockUser: User = {
      id: "1",
      username: username,
      email: email,
    };
    
    setUser(mockUser);
    localStorage.setItem("skillscope_user", JSON.stringify(mockUser));
    return Promise.resolve(mockUser);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("skillscope_user");
  };

  return {
    user,
    loading,
    login,
    register,
    logout,
  };
};
