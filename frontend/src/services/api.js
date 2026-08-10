const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const getHeaders = (isJson = true) => {
  const headers = {};
  if (isJson) {
    headers["Content-Type"] = "application/json";
  }
  const token = localStorage.getItem("token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
};

const handleResponse = async (response) => {
  if (!response.ok) {
    let detail = "";
    try {
      const errorData = await response.json();
      detail = errorData.detail || `HTTP error ${response.status}`;
    } catch (e) {
      detail = `HTTP error ${response.status}`;
    }
    throw new Error(detail);
  }
  
  if (response.status === 204) {
    return true; // No content
  }

  return response.json();
};

export const api = {
  get: async (endpoint, params = {}) => {
    const url = new URL(`${BASE_URL}${endpoint}`);
    Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
    const response = await fetch(url, {
      method: "GET",
      headers: getHeaders(),
    });
    return handleResponse(response);
  },

  post: async (endpoint, data, isJson = true) => {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      method: "POST",
      headers: getHeaders(isJson),
      body: isJson ? JSON.stringify(data) : data,
    });
    return handleResponse(response);
  },

  put: async (endpoint, data) => {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      method: "PUT",
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  delete: async (endpoint) => {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      method: "DELETE",
      headers: getHeaders(),
    });
    return handleResponse(response);
  },
  
  // Custom streamer for RAG Chat
  streamPost: async function* (endpoint, data) {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      let detail = "Streaming request failed.";
      try {
        const errorData = await response.json();
        detail = errorData.detail || detail;
      } catch (e) {}
      throw new Error(detail);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ""; // Keep the incomplete line in the buffer
      
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const payload = line.substring(6);
          if (payload === "[DONE]") {
            return;
          }
          try {
            const chunk = JSON.parse(payload);
            if (typeof chunk === 'string') {
              yield chunk;
            } else if (chunk.error) {
              yield `\n\n❌ Error: ${chunk.error}`;
            }
          } catch (e) {
            yield payload;
          }
        }
      }
    }
  }
};
