// Get the API URL - detect production vs development
const getApiUrl = (): string => {
  // 1. Always use localhost for development (http://localhost:5173)
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      const devUrl = 'http://localhost:8080';
      console.log("API URL (localhost development):", devUrl);
      return devUrl;
    }
  }

  // 2. Priority: Use environment variable if set (for production)
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) {
    const cleanUrl = envUrl.trim().split(' ')[0];
    console.log("API URL from env:", cleanUrl);
    return cleanUrl;
  }

  // 3. Default: Localhost
  console.log("API URL (localhost default):", 'http://localhost:8080');
  return 'http://localhost:8080';
};

export const API_URL = getApiUrl();

// Log the URL at startup for debugging
console.log("=== API Configuration ===");
console.log("Final API_URL:", API_URL);
console.log("Raw VITE_API_URL:", import.meta.env.VITE_API_URL);
console.log("========================");

// Helper function to make API calls with proper error handling
export async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ success: boolean; data?: T; error?: string }> {
  const url = `${API_URL}${endpoint}`;
  
  console.log(`API Call: ${options.method || 'GET'} ${url}`);
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    console.log(`API Response: ${response.status} ${response.statusText}`);

    const data = await response.json();

    if (!response.ok) {
      console.error("API Error Response:", data);
      return {
        success: false,
        error: data.error || `HTTP ${response.status}`,
      };
    }

    return {
      success: true,
      data,
    };
  } catch (error) {
    // More detailed error logging
    console.error(`API call to ${url} failed:`, error);
    
    let errorMessage = "Network error";
    if (error instanceof Error) {
      errorMessage = error.message;
      
      // Provide more helpful messages for common errors
      if (error.message.includes("NetworkError") || error.message.includes("Failed to fetch")) {
        errorMessage = `Cannot connect to server at ${API_URL}. Check if the backend is running.`;
      } else if (error.message.includes("CORS")) {
        errorMessage = `CORS error - the backend at ${API_URL} is not allowing requests from this origin.`;
      }
    }
    
    return {
      success: false,
      error: errorMessage,
    };
  }
}

// Typed API functions
export const api = {
  // Get user data by Firebase UID
  getUserData: async (uid: string) => {
    return apiCall<{
      success: boolean;
      has_courses: boolean;
      has_preferences: boolean;
      has_saved_schedule: boolean;
      courses: any;
      preferences: any;
      saved_schedule: any;
    }>(`/api/user-data/${uid}`);
  },

  // Upload courses
  uploadCourses: async (data: any) => {
    return apiCall(`/api/userCourses`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Save preferences
  savePreferences: async (data: any) => {
    return apiCall(`/api/preferences`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Generate schedule
  generateSchedule: async (uid: string, numRecommendations = 10) => {
    return apiCall<{
      success: boolean;
      schedules: any[];
      count: number;
      metadata: any;
    }>(`/api/generate-schedule`, {
      method: "POST",
      body: JSON.stringify({
        uid: uid,
        num_recommendations: numRecommendations,
      }),
    });
  },

  // Save schedule
  saveSchedule: async (uid: string, schedule: any) => {
    return apiCall(`/api/save-schedule`, {
      method: "POST",
      body: JSON.stringify({
        uid: uid,
        schedule,
      }),
    });
  },

  // Get saved schedule
  getSavedSchedule: async (uid: string) => {
    return apiCall<{
      success: boolean;
      schedule: any;
    }>(`/api/saved-schedule/${uid}`);
  },

  // Modify schedule (add/remove course)
  modifySchedule: async (
    uid: string,
    action: "add" | "remove",
    courseCode: string,
    priorityRank?: number,
    currentSchedule?: any[]
  ) => {
    return apiCall(`/api/modify-schedule`, {
      method: "POST",
      body: JSON.stringify({
        uid: uid,
        action,
        course_code: courseCode,
        priority_rank: priorityRank,
        current_schedule: currentSchedule,
      }),
    });
  },

  // Search courses
  searchCourses: async (query: string, limit = 20) => {
    return apiCall<{
      success: boolean;
      courses: any[];
      count: number;
    }>(`/api/search-courses?q=${encodeURIComponent(query)}&limit=${limit}`);
  },

  // Health check
  healthCheck: async () => {
    return apiCall<{
      status: string;
      mongodb: string;
      recommendation_engine: string;
    }>(`/api/health`);
  },

  // Register user (save UID to backend after Firebase signup)
  registerUser: async (uid: string, email: string) => {
    return apiCall<{
      success: boolean;
      message: string;
      uid: string;
      user_id: string;
    }>(`/api/register-user`, {
      method: "POST",
      body: JSON.stringify({ uid, email }),
    });
  },
};