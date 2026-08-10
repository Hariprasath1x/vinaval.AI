import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/authService';

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in
    const storedUser = localStorage.getItem('user');
    const token = localStorage.getItem('token');
    
    if (storedUser && token) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (e) {
        authService.logout();
      }
    }
    
    // Also handle firebase token redirect if it exists in URL
    const params = new URLSearchParams(window.location.search);
    const firebaseToken = params.get('firebase_token');
    
    if (firebaseToken) {
      authService.loginWithFirebase(firebaseToken).then(data => {
        setUser(data.user);
        // Clean URL
        window.history.replaceState({}, document.title, window.location.pathname);
      }).catch(err => {
        console.error("Firebase login error:", err);
      }).finally(() => {
        setLoading(false);
      });
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const data = await authService.login(email, password);
    setUser(data.user);
    return data.user;
  };

  const signup = async (name, email, password) => {
    const data = await authService.signup(name, email, password);
    setUser(data.user);
    return data.user;
  };

  const logout = () => {
    authService.logout();
    setUser(null);
  };

  const updateProfile = async (name) => {
    const updatedUser = await authService.updateProfile(name);
    setUser(updatedUser);
    return updatedUser;
  };

  const value = {
    user,
    loading,
    login,
    signup,
    logout,
    updateProfile
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};
