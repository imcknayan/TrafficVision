/**
 * TrafficVision AI - Unified Frontend API Client & State Manager
 * Milestone 1 & Milestone 2 Integrated Client
 */

const API_CONFIG = {
  baseURL: "http://localhost:8000/api/v1",
  timeoutMs: 12000,
  defaultHeaders: {
    "Content-Type": "application/json",
  },
};

// ── Session & Authentication State Manager ──────────────────────────────────
class AuthManager {
  constructor(storage = typeof window !== "undefined" ? window.localStorage : null) {
    this.storage = storage;
  }

  static getStorage() {
    return typeof window !== "undefined" ? window.localStorage : null;
  }

  static getToken() {
    const s = AuthManager.getStorage();
    if (!s) return null;
    return s.getItem("auth_token") || s.getItem("token") || null;
  }

  static setToken(token) {
    const s = AuthManager.getStorage();
    if (!s) return;
    if (token) {
      s.setItem("auth_token", token);
      s.setItem("token", token);
    } else {
      AuthManager.clear();
    }
  }

  static getRefreshToken() {
    const s = AuthManager.getStorage();
    if (!s) return null;
    return s.getItem("refresh_token") || null;
  }

  static getRole() {
    const s = AuthManager.getStorage();
    if (!s) return null;
    return s.getItem("auth_role") || s.getItem("role") || null;
  }

  static getUserName() {
    const s = AuthManager.getStorage();
    if (!s) return "User";
    return s.getItem("auth_user_name") || s.getItem("user_name") || "User";
  }

  static getUserId() {
    const s = AuthManager.getStorage();
    if (!s) return null;
    return s.getItem("auth_user_id") || null;
  }

  static setSession({ access_token, refresh_token, role, name, user_id } = {}) {
    const s = AuthManager.getStorage();
    if (!s) return;
    if (access_token) {
      s.setItem("auth_token", access_token);
      s.setItem("token", access_token);
    }
    if (refresh_token) {
      s.setItem("refresh_token", refresh_token);
    }
    if (role) {
      s.setItem("auth_role", role);
      s.setItem("role", role);
    }
    if (name) {
      s.setItem("auth_user_name", name);
      s.setItem("user_name", name);
    }
    if (user_id) {
      s.setItem("auth_user_id", user_id);
    }
  }

  static getSession() {
    return {
      access_token: AuthManager.getToken(),
      refresh_token: AuthManager.getRefreshToken(),
      role: AuthManager.getRole(),
      name: AuthManager.getUserName(),
      user_id: AuthManager.getUserId(),
    };
  }

  static clear() {
    const s = AuthManager.getStorage();
    if (!s) return;
    s.removeItem("auth_token");
    s.removeItem("token");
    s.removeItem("refresh_token");
    s.removeItem("auth_role");
    s.removeItem("role");
    s.removeItem("auth_user_name");
    s.removeItem("user_name");
    s.removeItem("auth_user_id");
  }

  static isAuthenticated() {
    return Boolean(AuthManager.getToken());
  }

  static getDashboardUrl(role) {
    const r = String(role || "").toUpperCase();
    if (r === "ADMIN") {
      return "Admin dashboard.html";
    }
    if (r === "OPERATOR" || r === "TRAFFIC_OPERATOR") {
      return "operator dashboard.html";
    }
    return "public dashboard.html";
  }

  static guardPage(allowedRoles = null) {
    if (typeof window === "undefined") return;
    const token = AuthManager.getToken();
    if (!token) {
      window.location.href = "Login.html";
      return;
    }

    if (allowedRoles && Array.isArray(allowedRoles) && allowedRoles.length > 0) {
      const currentRole = (AuthManager.getRole() || "").toUpperCase();
      const normalizedAllowed = allowedRoles.map((r) => r.toUpperCase());
      const roleMatches =
        normalizedAllowed.includes(currentRole) ||
        (currentRole === "TRAFFIC_OPERATOR" && normalizedAllowed.includes("OPERATOR")) ||
        (currentRole === "OPERATOR" && normalizedAllowed.includes("TRAFFIC_OPERATOR")) ||
        (currentRole === "PUBLIC" && (normalizedAllowed.includes("USER") || normalizedAllowed.includes("PUBLIC"))) ||
        (currentRole === "USER" && (normalizedAllowed.includes("PUBLIC") || normalizedAllowed.includes("USER")));

      if (!roleMatches) {
        window.location.href = AuthManager.getDashboardUrl(currentRole);
      }
    }
  }

  // Instance methods for compatibility
  getToken() {
    return AuthManager.getToken();
  }

  setToken(token) {
    AuthManager.setToken(token);
  }

  clear() {
    AuthManager.clear();
  }

  isAuthenticated() {
    return AuthManager.isAuthenticated();
  }

  applyAuthHeaders(headers = {}) {
    const token = AuthManager.getToken();
    if (!token) return headers;
    return {
      ...headers,
      Authorization: `Bearer ${token}`,
    };
  }

  async refreshToken() {
    const refreshToken = AuthManager.getRefreshToken();
    if (!refreshToken) return null;
    try {
      const res = await authAPI.refresh(refreshToken);
      return res?.access_token || null;
    } catch {
      return null;
    }
  }
}

const authManager = new AuthManager();

function logout() {
  AuthManager.clear();
  if (typeof window !== "undefined") {
    window.location.href = "Login.html";
  }
}

// ── Generic API Error & Fetch Helper ─────────────────────────────────────────
function createApiError(message, status = null, payload = null) {
  const error = new Error(message);
  error.status = status;
  error.payload = payload;
  return error;
}

function buildQueryString(params = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    searchParams.append(key, String(value));
  });
  return searchParams.toString();
}

async function apiFetch(endpoint, options = {}) {
  const baseUrl = endpoint.startsWith("http")
    ? endpoint
    : `${API_CONFIG.baseURL}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
  const controller = new AbortController();
  const timeoutMs = options.timeout ?? API_CONFIG.timeoutMs;
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const headers = authManager.applyAuthHeaders({
    ...API_CONFIG.defaultHeaders,
    ...(options.headers || {}),
  });

  try {
    const response = await fetch(baseUrl, {
      ...options,
      headers,
      signal: controller.signal,
    });

    const text = await response.text();
    let payload = null;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch {
      payload = text;
    }

    if (!response.ok) {
      const detail =
        payload && typeof payload === "object"
          ? payload.detail || payload.message || payload.error
          : payload;
      const message =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail) && detail[0]?.msg
          ? detail[0].msg
          : `Request failed (${response.status})`;

      if (response.status === 401 && !endpoint.includes("/auth/login")) {
        AuthManager.clear();
      }

      throw createApiError(message, response.status, payload);
    }

    return payload;
  } catch (error) {
    if (error && error.name === "AbortError") {
      throw createApiError("Request timed out", 408, null);
    }
    if (error && error.status) {
      throw error;
    }
    if (error && error.message && !error.message.includes("fetch")) {
      throw createApiError(error.message, null, null);
    }
    throw createApiError("Backend unavailable or network error", 503, null);
  } finally {
    clearTimeout(timer);
  }
}

// ── Congestion Badge & Formatting Helpers ─────────────────────────────────────
function normalizeCongestionLevel(value) {
  const raw = String(value || "").trim().toLowerCase();
  if (!raw) return "Low";
  if (raw.includes("severe")) return "Severe";
  if (raw.includes("high")) return "High";
  if (raw.includes("medium") || raw.includes("med")) return "Medium";
  return "Low";
}

function getCongestionBadgeClass(level) {
  const normalized = normalizeCongestionLevel(level);
  const map = {
    Low: "badge-success",
    Medium: "badge-warning",
    High: "badge-danger",
    Severe: "badge-danger",
  };
  return map[normalized] || "badge-secondary";
}

function getCongestionLabel(value) {
  return normalizeCongestionLevel(value);
}

// ── Authentication API Client (M1) ──────────────────────────────────────────
const authAPI = {
  async register(name, email, password, role = "public") {
    let normalizedRole = "public";
    const r = String(role || "").toLowerCase();
    if (r === "admin") normalizedRole = "admin";
    else if (r === "operator" || r === "traffic_operator") normalizedRole = "traffic_operator";
    else normalizedRole = "public";

    const payload = {
      name: String(name || "").trim(),
      email: String(email || "").trim(),
      password: String(password || ""),
      role: normalizedRole,
    };

    return await apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async login(email, password) {
    const payload = {
      email: String(email || "").trim(),
      password: String(password || ""),
    };

    const response = await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (response && response.access_token) {
      AuthManager.setSession({
        access_token: response.access_token,
        refresh_token: response.refresh_token,
        role: response.role,
        name: response.name || (email ? email.split("@")[0] : "User"),
        user_id: response.user_id,
      });
    }

    return response;
  },

  async refresh(refreshToken = null) {
    const token = refreshToken || AuthManager.getRefreshToken();
    if (!token) {
      throw createApiError("No refresh token available", 401, null);
    }

    const response = await apiFetch("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: token }),
    });

    if (response && response.access_token) {
      AuthManager.setSession({
        access_token: response.access_token,
        refresh_token: token,
        role: AuthManager.getRole(),
        name: AuthManager.getUserName(),
        user_id: AuthManager.getUserId(),
      });
    }

    return response;
  },

  async getMe() {
    return await apiFetch("/auth/me");
  },
};

// ── Fallback Corridors & Road Telemetry ───────────────────────────────────────
const FALLBACK_ROADS = [
  { road_id: "R001", road_name: "Main Expressway", speed: "52 km/h", avg_speed_kmph: 52, density: 5.6, congestion_level: "Low", vehicle_count: 84 },
  { road_id: "R002", road_name: "Central Avenue", speed: "41 km/h", avg_speed_kmph: 41, density: 6.75, congestion_level: "Low", vehicle_count: 95 },
  { road_id: "R003", road_name: "West Ring Road", speed: "38 km/h", avg_speed_kmph: 38, density: 7.43, congestion_level: "Medium", vehicle_count: 110 },
  { road_id: "R004", road_name: "North Boulevard", speed: "65 km/h", avg_speed_kmph: 65, density: 0.22, congestion_level: "Low", vehicle_count: 12 },
  { road_id: "R005", road_name: "Industrial Highway", speed: "29 km/h", avg_speed_kmph: 29, density: 11.33, congestion_level: "Medium", vehicle_count: 145 },
  { road_id: "R006", road_name: "Airport Corridor", speed: "18 km/h", avg_speed_kmph: 18, density: 22.4, congestion_level: "High", vehicle_count: 230 },
  { road_id: "R007", road_name: "Harbor Tunnel Approach", speed: "12 km/h", avg_speed_kmph: 12, density: 29.8, congestion_level: "Severe", vehicle_count: 285 },
];

// ── Traffic Monitoring API Client (M1) ───────────────────────────────────────
const trafficAPI = {
  async getLiveTraffic() {
    try {
      const response = await apiFetch("/traffic/live");

      if (response && Array.isArray(response.data)) {
        return response.data.map((road) => ({
          ...road,
          speed: `${road.average_speed} km/h`,
          avg_speed_kmph: road.average_speed,
        }));
      }

      return FALLBACK_ROADS;
    } catch {
      return FALLBACK_ROADS;
    }
  },
  

  async getDensitySummary() {
    try {
      const response = await apiFetch("/traffic/density");
      if (response && typeof response === "object" && (response.total_roads || response.average_density !== undefined)) {
        return response;
      }
      return this._fallbackDensity();
    } catch {
      return this._fallbackDensity();
    }
  },

  _fallbackDensity() {
    return {
      total_roads: 7,
      total_roads_monitored: 7,
      total_vehicle_count: 961,
      average_density: 11.93,
      average_network_density: 11.93,
      maximum_density: 29.8,
      minimum_density: 0.22,
      high_congestion_roads: 1,
      severe_congestion_roads: 1,
      congested_segments: 2,
      timestamp: new Date().toISOString(),
    };
  },

  async getRoadTraffic(roadId) {
    if (!roadId) {
      throw createApiError("roadId is required", 400, null);
    }

    try {
      const response = await apiFetch(`/traffic/road/${encodeURIComponent(String(roadId))}`);
      if (response && typeof response === "object") {
        return response;
      }
    } catch (error) {
      if (error && error.status === 404) {
        // Fall through to fallback
      }
    }

    const match = FALLBACK_ROADS.find((r) => r.road_id === roadId) || FALLBACK_ROADS[0];
    return {
      road_id: match.road_id,
      road_name: match.road_name,
      speed: match.speed,
      avg_speed_kmph: match.avg_speed_kmph,
      density: match.density,
      congestion_level: match.congestion_level,
      vehicle_count: match.vehicle_count,
      history: [
        { updated_at: new Date(Date.now() - 300000).toISOString(), vehicle_count: match.vehicle_count - 10, density: Math.max(1, match.density - 1.2), avg_speed_kmph: match.avg_speed_kmph + 2 },
        { updated_at: new Date(Date.now() - 600000).toISOString(), vehicle_count: match.vehicle_count - 25, density: Math.max(1, match.density - 2.8), avg_speed_kmph: match.avg_speed_kmph + 5 },
        { updated_at: new Date(Date.now() - 900000).toISOString(), vehicle_count: match.vehicle_count - 40, density: Math.max(1, match.density - 4.1), avg_speed_kmph: match.avg_speed_kmph + 8 },
      ],
    };
  },
};

// ── Prediction & AI Engine API Client (M1) ──────────────────────────────────
const predictAPI = {
  async predictCongestion({ road_id, vehicle_count, average_speed, timestamp } = {}) {
    if (!road_id) {
      throw createApiError("road_id is required", 400, null);
    }
    const query = buildQueryString({ road_id, vehicle_count, average_speed, timestamp });
    try {
      const response = await apiFetch(`/predict/congestion?${query}`);
      if (response && typeof response === "object") return response;
    } catch {
      // Fallback prediction
    }
    const road = FALLBACK_ROADS.find((r) => r.road_id === road_id) || FALLBACK_ROADS[0];
    return {
      road_id: road.road_id,
      predicted_level: road.congestion_level,
      confidence: 0.88,
      factors: { density: road.density, avg_speed: road.avg_speed_kmph },
    };
  },

  async getCongestion(roadId) {
    return await this.predictCongestion({ road_id: roadId });
  },

  async getPeakHours(roadId) {
    if (!roadId) throw createApiError("road_id is required", 400, null);
    const query = buildQueryString({ road_id: roadId });
    try {
      const response = await apiFetch(`/predict/peak-hours?${query}`);
      if (response && typeof response === "object") return response;
    } catch {
      // Fallback peak hours
    }
    return this._fallbackPeakData(roadId);
  },

  async getPeakHourPrediction(roadId = "R006") {
    return await this.getPeakHours(roadId);
  },

  _fallbackPeakData(roadId) {
    const road = FALLBACK_ROADS.find((r) => r.road_id === roadId) || FALLBACK_ROADS[0];
    return {
      road_id: road.road_id,
      road_name: road.road_name,
      generated_by: "heuristic-fallback-v1",
      peak_hours: [
        { hour: 6, density: 4.2 },
        { hour: 7, density: 9.8 },
        { hour: 8, density: 24.5 },
        { hour: 9, density: 29.1 },
        { hour: 10, density: 18.6 },
        { hour: 11, density: 12.3 },
        { hour: 12, density: 14.1 },
        { hour: 13, density: 13.5 },
        { hour: 14, density: 15.8 },
        { hour: 15, density: 19.2 },
        { hour: 16, density: 26.4 },
        { hour: 17, density: 31.2 },
        { hour: 18, density: 28.7 },
        { hour: 19, density: 21.0 },
        { hour: 20, density: 11.4 },
      ],
    };
  },

  async predictDelay({ road_id, distance_km, vehicle_count, average_speed, timestamp } = {}) {
    if (!road_id) throw createApiError("road_id is required", 400, null);
    const query = buildQueryString({ road_id, distance_km, vehicle_count, average_speed, timestamp });
    try {
      const response = await apiFetch(`/predict/delay?${query}`);
      if (response && typeof response === "object") return response;
    } catch {
      // Fallback delay
    }
    const road = FALLBACK_ROADS.find((r) => r.road_id === road_id) || FALLBACK_ROADS[0];
    const dist = distance_km || 5.0;
    const freeFlow = Math.round((dist / 60) * 60);
    const liveTime = Math.round((dist / Math.max(10, road.avg_speed_kmph)) * 60);
    return {
      road_id: road.road_id,
      road_name: road.road_name,
      delay_minutes: Math.max(0, liveTime - freeFlow),
      free_flow_time_min: freeFlow,
      current_time_min: liveTime,
    };
  },

  async getAllDelayEstimates() {
    return FALLBACK_ROADS.map((road) => {
      const dist = road.road_id === "R001" ? 14.2 : road.road_id === "R006" ? 11.5 : road.road_id === "R007" ? 6.8 : 5.4;
      const freeFlow = Math.round((dist / 60) * 60);
      const liveTime = Math.round((dist / Math.max(10, road.avg_speed_kmph)) * 60);
      const delay = Math.max(0, liveTime - freeFlow);
      return {
        road_id: road.road_id,
        road_name: road.road_name,
        length_km: dist,
        delay_minutes: delay,
        congestion_level: road.congestion_level,
        free_flow_time_min: freeFlow,
        current_time_min: liveTime,
        current_speed: road.avg_speed_kmph,
        status_color: delay > 10 ? "text-rose-400" : delay > 4 ? "text-yellow-400" : "text-emerald-400",
      };
    });
  },

  getAllRoadForecasts(horizonMinutes = 30) {
    const factor = horizonMinutes / 30;
    return FALLBACK_ROADS.map((road) => {
      const delta = (road.density >= 20 ? 3.5 : road.density >= 10 ? 1.8 : -0.5) * factor;
      const predDensity = Math.max(0.1, Math.round((road.density + delta) * 10) / 10);
      const predLevel = predDensity >= 28 ? "Severe" : predDensity >= 20 ? "High" : predDensity >= 10 ? "Medium" : "Low";
      const predSpeed = Math.max(10, Math.round(road.avg_speed_kmph - delta * 1.5));
      return {
        road_id: road.road_id,
        road_name: road.road_name,
        current_density: road.density,
        predicted_density: predDensity,
        predicted_speed: predSpeed,
        predicted_level: predLevel,
        trend: delta > 0 ? "Worsening Congestion" : delta < 0 ? "Clearing Up" : "Stable Flow",
        confidence: 0.89,
      };
    });
  },

  getTemporalForecast(roadId, horizonMinutes = 30) {
    const forecasts = this.getAllRoadForecasts(horizonMinutes);
    return forecasts.find((f) => f.road_id === roadId) || forecasts[0];
  },

  async downloadPredictionReport(format = "csv") {
    const corridors = this.getAllRoadForecasts(30);
    const filename = `TrafficVision_Prediction_Report_${new Date().toISOString().substring(0, 10)}.${format}`;
    let content = "";

    if (format === "json") {
      content = JSON.stringify(corridors, null, 2);
    } else {
      const header = "road_id,road_name,current_density,predicted_density,predicted_speed,predicted_level,trend\n";
      const rows = corridors.map((c) => `"${c.road_id}","${c.road_name}",${c.current_density},${c.predicted_density},${c.predicted_speed},"${c.predicted_level}","${c.trend}"`).join("\n");
      content = header + rows;
    }

    if (typeof window !== "undefined" && typeof document !== "undefined") {
      const blob = new Blob([content], { type: format === "json" ? "application/json" : "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }

    return { filename, count: corridors.length };
  },
};

const predictionAPI = predictAPI;

// ── Road Network Geometry & Hub Coordinates (M2) ─────────────────────────────
const ROAD_NETWORK_GEOMETRY = {
  center: [26.1445, 91.7362],
  zoom: 13,
  segments: {
    R001: {
      road_id: "R001",
      road_name: "Main Expressway",
      coordinates: [
        [26.155, 91.720],
        [26.150, 91.728],
        [26.145, 91.735],
        [26.140, 91.745],
        [26.135, 91.755],
      ],
    },
    R002: {
      road_id: "R002",
      road_name: "Central Avenue / Downtown Grid",
      coordinates: [
        [26.145, 91.735],
        [26.142, 91.738],
        [26.139, 91.741],
        [26.135, 91.746],
      ],
    },
    R003: {
      road_id: "R003",
      road_name: "West Ring Road",
      coordinates: [
        [26.160, 91.710],
        [26.152, 91.715],
        [26.144, 91.722],
        [26.136, 91.728],
        [26.128, 91.735],
      ],
    },
    R004: {
      road_id: "R004",
      road_name: "North Boulevard",
      coordinates: [
        [26.165, 91.725],
        [26.160, 91.735],
        [26.155, 91.745],
        [26.150, 91.755],
      ],
    },
    R005: {
      road_id: "R005",
      road_name: "Industrial Highway",
      coordinates: [
        [26.135, 91.755],
        [26.130, 91.765],
        [26.125, 91.775],
        [26.120, 91.785],
      ],
    },
    R006: {
      road_id: "R006",
      road_name: "Airport Corridor",
      coordinates: [
        [26.145, 91.735],
        [26.148, 91.742],
        [26.152, 91.750],
        [26.158, 91.760],
        [26.165, 91.770],
      ],
    },
    R007: {
      road_id: "R007",
      road_name: "Harbor Tunnel Approach",
      coordinates: [
        [26.144276, 91.736153],
        [26.144677, 91.735485],
        [26.144911, 91.734374],
        [26.145403, 91.732133],
        [26.135000, 91.725000],
        [26.125000, 91.718000],
        [26.115802, 91.708609],
      ],
    },
  },
};

const NETWORK_HUBS = [
  { id: "downtown", name: "Downtown Central Hub", coords: [26.144276, 91.736153], icon: "business", color: "#8dcdff" },
  { id: "tech-park", name: "Tech Park / Harbor Node", coords: [26.115802, 91.708609], icon: "memory", color: "#00affe" },
  { id: "airport", name: "International Airport Hub", coords: [26.165, 91.770], icon: "flight", color: "#bdc2ff" },
  { id: "harbor", name: "Harbor Logistics Terminal", coords: [26.112, 91.705], icon: "directions_boat", color: "#cdbdff" },
  { id: "industrial", name: "East Industrial Park", coords: [26.120, 91.785], icon: "factory", color: "#facc15" },
  { id: "west-end", name: "West Ring Interchange", coords: [26.128, 91.735], icon: "explore", color: "#4ade80" },
  { id: "north-gate", name: "North Gateway Hub", coords: [26.165, 91.725], icon: "navigation", color: "#f87171" },
];

// ── Route Analysis API Client (M2) ──────────────────────────────────────────
const routeAPI = {
  getHubs() {
    return NETWORK_HUBS;
  },

  getAllRoadGeometries() {
    return ROAD_NETWORK_GEOMETRY.segments;
  },

  async optimizeRoute(origin, destination) {
    if (!origin || !destination) {
      throw createApiError("origin and destination are required (format: lat,lng)", 400, null);
    }
    const query = buildQueryString({ origin, destination });
    return await apiFetch(`/route/optimize?${query}`);
  },

  async getAlternateRoutes(origin, destination) {
    if (!origin || !destination) {
      throw createApiError("origin and destination are required (format: lat,lng)", 400, null);
    }
    const query = buildQueryString({ origin, destination });
    return await apiFetch(`/route/alternate?${query}`);
  },

  async getTravelTime(routeId) {
    if (!routeId) throw createApiError("routeId is required", 400, null);
    const query = buildQueryString({ route_id: routeId });
    return await apiFetch(`/route/travel-time?${query}`);
  },

  async getRoadConditions(roadId) {
    if (!roadId) throw createApiError("roadId is required", 400, null);
    const query = buildQueryString({ road_id: roadId });
    return await apiFetch(`/route/conditions?${query}`);
  },

  async rankRoutes(routes) {
    if (!Array.isArray(routes) || routes.length === 0) {
      return [];
    }
    const payload = {
      routes: routes.map((route) => ({
        route_id: route.route_id,
        distance_km: route.distance_km,
        roads: Array.isArray(route.roads) ? route.roads : [],
        base_duration_minutes: route.base_duration_minutes ?? null,
      })),
    };

    const response = await apiFetch("/route/rank", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (!Array.isArray(response)) {
      throw createApiError("Malformed response: expected an array", 502, response);
    }
    return response;
  },

  async calculateRoutes(originId, destId, mode = "fastest") {
    const originHub = NETWORK_HUBS.find((h) => h.id === originId) || NETWORK_HUBS[0];
    const destHub = NETWORK_HUBS.find((h) => h.id === destId) || NETWORK_HUBS[1];

    const originCoord = `${originHub.coords[0]},${originHub.coords[1]}`;
    const destCoord = `${destHub.coords[0]},${destHub.coords[1]}`;

    let liveRoute = null;
    let alternateRoutes = [];
    let travelTimeInfo = null;
    let roadCond = null;
    let dataSource = "fallback";

    // 1. Try real M2 backend optimize endpoint via Gateway
    try {
      liveRoute = await this.optimizeRoute(originCoord, destCoord);
      if (liveRoute && liveRoute.route_id) {
        dataSource = "backend";
        try {
          travelTimeInfo = await this.getTravelTime(liveRoute.route_id);
        } catch {}
      }
    } catch {
      // Backend / OSRM offline, will construct heuristic fallback
    }

    // 2. Try real M2 alternate routes
    try {
      alternateRoutes = await this.getAlternateRoutes(originCoord, destCoord);
    } catch {}

    // 3. Try real M2 road conditions
    try {
      roadCond = await this.getRoadConditions("R001");
    } catch {
      roadCond = { road_id: "R001", status: "CLEAR", hazards: [], road_work_present: false };
    }

    // Construct unified route analysis payload matching Route-analysis.html
    const primaryPath = liveRoute?.path || [
      originHub.coords,
      [(originHub.coords[0] + destHub.coords[0]) / 2 + 0.005, (originHub.coords[1] + destHub.coords[1]) / 2 - 0.005],
      destHub.coords,
    ];

    const primaryDist = liveRoute?.distance_km || 5.39;
    const primaryDuration = travelTimeInfo?.estimated_minutes || Math.round(primaryDist * 1.5);
    const primaryDelay = Math.max(0, Math.round(primaryDuration * 0.15));

    const routes = [
      {
        route_id: liveRoute?.route_id || "route-ca624d0c7a10",
        route_name: `Express Corridor (${originHub.name.split(" ")[0]} → ${destHub.name.split(" ")[0]})`,
        route_type: "Fastest",
        is_recommended: true,
        duration_minutes: primaryDuration,
        distance_km: primaryDist,
        delay_minutes: primaryDelay,
        worst_congestion: primaryDelay > 5 ? "High" : "Low",
        ai_confidence: 0.94,
        coordinates: primaryPath,
        segments: [
          { road_id: "R001", road_name: "Main Expressway", length_km: Math.round(primaryDist * 0.6 * 10) / 10, current_speed: 52, speed_limit: 60, density: 5.6, congestion_level: "Low", segment_time_min: Math.round(primaryDuration * 0.5) },
          { road_id: "R002", road_name: "Central Avenue", length_km: Math.round(primaryDist * 0.4 * 10) / 10, current_speed: 41, speed_limit: 50, density: 6.75, congestion_level: "Low", segment_time_min: Math.round(primaryDuration * 0.5) },
        ],
      },
      {
        route_id: (alternateRoutes[1]?.route_id) || "route-alt-94bf2a",
        route_name: `Ring Road Arterial Bypass`,
        route_type: "Alternate",
        is_recommended: false,
        duration_minutes: Math.round(primaryDuration * 1.25),
        distance_km: Math.round((primaryDist * 1.3) * 10) / 10,
        delay_minutes: Math.max(1, Math.round(primaryDelay * 0.6)),
        worst_congestion: "Medium",
        ai_confidence: 0.87,
        coordinates: [
          originHub.coords,
          [(originHub.coords[0] + destHub.coords[0]) / 2 - 0.008, (originHub.coords[1] + destHub.coords[1]) / 2 + 0.008],
          destHub.coords,
        ],
        segments: [
          { road_id: "R003", road_name: "West Ring Road", length_km: Math.round(primaryDist * 0.7 * 10) / 10, current_speed: 38, speed_limit: 60, density: 7.43, congestion_level: "Medium", segment_time_min: Math.round(primaryDuration * 0.7) },
          { road_id: "R005", road_name: "Industrial Highway", length_km: Math.round(primaryDist * 0.6 * 10) / 10, current_speed: 29, speed_limit: 50, density: 11.33, congestion_level: "Medium", segment_time_min: Math.round(primaryDuration * 0.55) },
        ],
      },
    ];

    return {
      origin: originHub,
      destination: destHub,
      mode,
      data_source: dataSource,
      road_conditions: roadCond || { status: "CLEAR", hazards: [], road_work_present: false },
      routes,
    };
  },
};

// ── Operator Management API Client (Admin Dashboard) ────────────────────────
const operatorAPI = {
  getOperators() {
    const defaultOps = [
      { id: "op-101", name: "Chandan Kumar", email: "chandan@test.com", sector: "Downtown Grid (R002)", shift: "Morning", status: "Active", created_at: "2026-09-24" },
      { id: "op-102", name: "Marcus Vance", email: "m.vance@trafficvision.ai", sector: "Airport Corridor (R006)", shift: "Day", status: "Active", created_at: "2026-09-20" },
      { id: "op-103", name: "Elena Rostova", email: "e.rostova@trafficvision.ai", sector: "Harbor Tunnel (R007)", shift: "Night", status: "Active", created_at: "2026-09-18" },
      { id: "op-104", name: "David Kim", email: "d.kim@trafficvision.ai", sector: "West Ring Road (R003)", shift: "Flexible", status: "Standby", created_at: "2026-09-22" },
    ];
    const s = AuthManager.getStorage();
    if (!s) return defaultOps;
    try {
      const stored = s.getItem("tv_operators");
      if (stored) return JSON.parse(stored);
    } catch {}
    s.setItem("tv_operators", JSON.stringify(defaultOps));
    return defaultOps;
  },

  async addOperator({ name, email, sector, shift, password }) {
    if (!name || !email) throw createApiError("Name and email are required", 400, null);

    // Optionally register operator in auth service if password provided
    if (password && password.length >= 8) {
      try {
        await authAPI.register(name, email, password, "traffic_operator");
      } catch (err) {
        // If already registered or offline, continue to add to local registry
        console.warn("Operator auth register notice:", err.message);
      }
    }

    const ops = this.getOperators();
    const newOp = {
      id: `op-${Date.now().toString().slice(-4)}`,
      name: String(name).trim(),
      email: String(email).trim().toLowerCase(),
      sector: sector || "Unassigned Sector",
      shift: shift || "General",
      status: "Active",
      created_at: new Date().toISOString().substring(0, 10),
    };
    ops.unshift(newOp);
    const s = AuthManager.getStorage();
    s?.setItem("tv_operators", JSON.stringify(ops));
    return newOp;
  },

  async removeOperator(id) {
    let ops = this.getOperators();
    ops = ops.filter((o) => o.id !== id);
    const s = AuthManager.getStorage();
    s?.setItem("tv_operators", JSON.stringify(ops));
    return { success: true };
  },
};

// ── Alerts API Client (M3) ──────────────────────────────────────────────────
const alertAPI = {
  async getMyAlerts(role = null) {
    try {
      const query = buildQueryString({ role: role || AuthManager.getRole() });
      const res = await apiFetch(`/alerts/my${query ? `?${query}` : ""}`);
      if (Array.isArray(res)) return res;
    } catch {}
    return [];
  },

  async getActiveAlerts(road_id = null) {
    try {
      const query = buildQueryString({ road_id });
      const res = await apiFetch(`/alerts/active${query ? `?${query}` : ""}`);
      if (Array.isArray(res)) return res;
    } catch {}
    return [];
  },

  async markAsRead(alertId) {
    if (!alertId) throw createApiError("alertId is required", 400);
    return await apiFetch(`/alerts/${encodeURIComponent(String(alertId))}/read`, {
      method: "POST",
    });
  },

  async createAlert({ type, severity, road_id, message }) {
    return await apiFetch("/alerts", {
      method: "POST",
      body: JSON.stringify({ type, severity, road_id, message }),
    });
  },
};

// ── Analytics API Client (M3) ────────────────────────────────────────────────
const analyticsAPI = {
  async getTrends(roadId = "R001", range = "day") {
    const query = buildQueryString({ road_id: roadId, range });
    return await apiFetch(`/analytics/trends?${query}`);
  },

  async getHeatmap(range = "day") {
    const query = buildQueryString({ range });
    return await apiFetch(`/analytics/heatmap?${query}`);
  },

  async getReports(range = "week", format = "csv") {
    const query = buildQueryString({ range, format });
    return await apiFetch(`/analytics/reports?${query}`);
  },
};

// ── AI Insights API Client (M3) ──────────────────────────────────────────────
const aiInsightsAPI = {
  async getAnomalies(roadId = null, threshold = 0.35) {
    const query = buildQueryString({ road_id: roadId, threshold });
    return await apiFetch(`/ai/anomalies${query ? `?${query}` : ""}`);
  },

  async getRecommendations(roadId = "R006") {
    const query = buildQueryString({ road_id: roadId });
    return await apiFetch(`/ai/recommendations?${query}`);
  },
};

// ── Global & Module Scope Exports ─────────────────────────────────────────────
if (typeof window !== "undefined") {
  window.API_CONFIG = API_CONFIG;
  window.AuthManager = AuthManager;
  window.authManager = authManager;
  window.authAPI = authAPI;
  window.trafficAPI = trafficAPI;
  window.predictAPI = predictAPI;
  window.predictionAPI = predictionAPI;
  window.routeAPI = routeAPI;
  window.operatorAPI = operatorAPI;
  window.alertAPI = alertAPI;
  window.analyticsAPI = analyticsAPI;
  window.aiInsightsAPI = aiInsightsAPI;
  window.ROAD_NETWORK_GEOMETRY = ROAD_NETWORK_GEOMETRY;
  window.NETWORK_HUBS = NETWORK_HUBS;
  window.getCongestionBadgeClass = getCongestionBadgeClass;
  window.getCongestionLabel = getCongestionLabel;
  window.logout = logout;
  window.apiFetch = apiFetch;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    API_CONFIG,
    AuthManager,
    authManager,
    authAPI,
    trafficAPI,
    predictAPI,
    predictionAPI,
    routeAPI,
    operatorAPI,
    alertAPI,
    analyticsAPI,
    aiInsightsAPI,
    ROAD_NETWORK_GEOMETRY,
    NETWORK_HUBS,
    getCongestionBadgeClass,
    getCongestionLabel,
    logout,
    apiFetch,
  };
}

