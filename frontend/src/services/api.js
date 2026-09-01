const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1";

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

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

const handleResponse = async (response) => {
  if (!response.ok) {
    let detail = "";
    try {
      const errorData = await response.json();
      detail = errorData.detail || `HTTP error ${response.status}`;
    } catch (e) {
      console.warn(e);
      detail = `HTTP error ${response.status}`;
    }
    const err = new Error(detail);
    err.status = response.status;
    throw err;
  }
  
  if (response.status === 204) {
    return true; // No content
  }

  return response.json();
};

const fetchWithRetry = async (url, options) => {
  let response = await fetch(url, options);
  
  if (response.status === 401 && localStorage.getItem("refresh_token")) {
    if (isRefreshing) {
      return new Promise(function(resolve, reject) {
        failedQueue.push({ resolve, reject });
      }).then(token => {
        options.headers["Authorization"] = 'Bearer ' + token;
        return fetch(url, options);
      }).catch(err => {
        return Promise.reject(err);
      });
    }

    isRefreshing = true;

    try {
      const refreshResponse = await fetch(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: localStorage.getItem("refresh_token") })
      });
      
      if (!refreshResponse.ok) {
        throw new Error("Refresh token expired or invalid");
      }
      
      const data = await refreshResponse.json();
      localStorage.setItem("token", data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("refresh_token", data.refresh_token);
      }
      
      processQueue(null, data.access_token);
      options.headers["Authorization"] = 'Bearer ' + data.access_token;
      response = await fetch(url, options);
    } catch (err) {
      processQueue(err, null);
      localStorage.removeItem("token");
      localStorage.removeItem("refresh_token");
      // Could dispatch a logout event here, but reloading handles it
      window.location.reload();
      throw err;
    } finally {
      isRefreshing = false;
    }
  }

  return handleResponse(response);
};

export const api = {
  get: async (endpoint, params = {}) => {
    const fullUrl = `${BASE_URL}${endpoint}`;
    const baseOrigin = typeof window !== 'undefined' && window.location ? window.location.origin : 'http://localhost';
    const url = (fullUrl.startsWith('http://') || fullUrl.startsWith('https://'))
      ? new URL(fullUrl)
      : new URL(fullUrl, baseOrigin);

    Object.keys(params).forEach(key => {
      if (params[key] !== undefined && params[key] !== null) {
        url.searchParams.append(key, params[key]);
      }
    });

    return fetchWithRetry(url.toString(), {
      method: "GET",
      headers: getHeaders(),
    });
  },

  post: async (endpoint, data, isJson = true) => {
    return fetchWithRetry(`${BASE_URL}${endpoint}`, {
      method: "POST",
      headers: getHeaders(isJson),
      body: isJson ? JSON.stringify(data) : data,
    });
  },

  put: async (endpoint, data) => {
    return fetchWithRetry(`${BASE_URL}${endpoint}`, {
      method: "PUT",
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
  },

  delete: async (endpoint) => {
    return fetchWithRetry(`${BASE_URL}${endpoint}`, {
      method: "DELETE",
      headers: getHeaders(),
    });
  },
  
  // Custom streamer for RAG Chat
  
  // Custom streamer for object payloads (Quiz, Flashcards)
  streamObjects: async function* (endpoint, data) {
    let options = {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify(data),
    };
    
    let response = await fetch(`${BASE_URL}${endpoint}`, options);
    
    if (response.status === 401 && localStorage.getItem("refresh_token")) {
      try {
        await api.get('/health');
        options.headers = getHeaders();
        response = await fetch(`${BASE_URL}${endpoint}`, options);
      } catch (e) {
        console.warn("Stream refresh token failed", e);
      }
    }
    
    if (!response.ok) {
      let detail = "Streaming request failed.";
      try {
        const errorData = await response.json();
        detail = errorData.detail || detail;
      } catch (e) {
        console.warn(e);
      }
      throw new Error(detail);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const messages = buffer.split('\n\n');
      buffer = messages.pop() || "";
      
      for (const message of messages) {
        if (!message.trim()) continue;
        
        let eventName = "message";
        let eventData = "";
        
        const lines = message.split('\n');
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventName = line.substring(7).trim();
          } else if (line.startsWith("data: ")) {
            eventData += line.substring(6);
          }
        }
        
        if (eventData) {
          try {
            const parsedData = JSON.parse(eventData);
            yield { event: eventName, data: parsedData };
          } catch (e) {
            // ignore malformed JSON
          }
        }
      }
    }
  },

  streamPost: async function* (endpoint, data) {
    // Basic retry logic for streaming
    let options = {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify(data),
    };
    
    let response = await fetch(`${BASE_URL}${endpoint}`, options);
    
    // Check for 401 - if so, try a normal fetchWithRetry to refresh token, then retry stream
    if (response.status === 401 && localStorage.getItem("refresh_token")) {
      // Trigger a dummy fetchWithRetry to handle the refresh queue
      try {
        await api.get('/health'); // This will trigger the refresh token flow in fetchWithRetry
        options.headers = getHeaders(); // update headers
        response = await fetch(`${BASE_URL}${endpoint}`, options);
      } catch (e) {
        console.warn("Stream refresh token failed", e);
      }
    }
    
    if (!response.ok) {
      let detail = "Streaming request failed.";
      try {
        const errorData = await response.json();
        detail = errorData.detail || detail;
      } catch (e) {
        console.warn(e);
      }
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
            console.warn("Stream parsing error", e);
            yield payload;
          }
        }
      }
    }
  }
};
