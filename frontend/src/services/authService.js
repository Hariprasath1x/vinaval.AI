import { api } from "./api";

export const authService = {
  signup: async (name, email, password) => {
    const data = await api.post("/auth/signup", { name, email, password });
    if (data && data.access_token) {
      localStorage.setItem("token", data.access_token);
      if (data.refresh_token) localStorage.setItem("refresh_token", data.refresh_token);
      localStorage.setItem("user", JSON.stringify(data.user));
    }
    return data;
  },

  login: async (email, password) => {
    const data = await api.post("/auth/login", { email, password });
    if (data && data.access_token) {
      localStorage.setItem("token", data.access_token);
      if (data.refresh_token) localStorage.setItem("refresh_token", data.refresh_token);
      localStorage.setItem("user", JSON.stringify(data.user));
    }
    return data;
  },

  loginWithFirebase: async (idToken) => {
    const data = await api.post("/auth/firebase", { id_token: idToken });
    if (data && data.access_token) {
      localStorage.setItem("token", data.access_token);
      if (data.refresh_token) localStorage.setItem("refresh_token", data.refresh_token);
      localStorage.setItem("user", JSON.stringify(data.user));
    }
    return data;
  },

  forgotPassword: async (email) => {
    return await api.post("/auth/forgot-password", { email });
  },

  updateProfile: async (name) => {
    const data = await api.put("/auth/profile", { name });
    if (data) {
      localStorage.setItem("user", JSON.stringify(data));
    }
    return data;
  },

  changePassword: async (currentPassword, newPassword) => {
    return await api.put("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },

  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
  }
};
