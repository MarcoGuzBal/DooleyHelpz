// Get the API URL - detect production vs development
const getApiUrl = (): string => {
  // 1. Priority: Use environment variable if set (works for local .env AND Vercel env vars)
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  // 2. Fallback: Auto-detect production environment if no env var is set
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    // If on Vercel or any non-localhost, use Fly.io backend as default
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return 'https://dooley-devs.fly.dev';
    }
  }

  // 3. Default: Localhost
  return 'http://localhost:5002';
};

export const API_URL = getApiUrl();

// Helper function to make API calls with proper error handling
export async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ success: boolean; data?: T; error?: string }> {
  try {
    const url = `${API_URL}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    const data = await response.json();

    if (!response.ok) {
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
    console.error(`API call to ${endpoint} failed:`, error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Network error",
    };
  }
}

// Typed API functions
export const api = {
  // Get user data
  getUserData: async (sharedId: number) => {
    return apiCall<{
      success: boolean;
      has_courses: boolean;
      has_preferences: boolean;
      has_saved_schedule: boolean;
      courses: any;
      preferences: any;
      saved_schedule: any;
    }>(`/api/user-data/${sharedId}`);
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
  generateSchedule: async (sharedId: number, numRecommendations = 10) => {
    return apiCall<{
      success: boolean;
      schedules: any[];
      count: number;
      metadata: any;
    }>(`/api/generate-schedule`, {
      method: "POST",
      body: JSON.stringify({
        shared_id: sharedId,
        num_recommendations: numRecommendations,
      }),
    });
  },

  // Save schedule
  saveSchedule: async (sharedId: number, schedule: any) => {
    return apiCall(`/api/save-schedule`, {
      method: "POST",
      body: JSON.stringify({
        shared_id: sharedId,
        schedule,
      }),
    });
  },

  // Get saved schedule
  getSavedSchedule: async (sharedId: number) => {
    return apiCall<{
      success: boolean;
      schedule: any;
    }>(`/api/saved-schedule/${sharedId}`);
  },

  // Modify schedule (add/remove course)
  modifySchedule: async (
    sharedId: number,
    action: "add" | "remove",
    courseCode: string,
    priorityRank?: number,
    currentSchedule?: any[]
  ) => {
    return apiCall(`/api/modify-schedule`, {
      method: "POST",
      body: JSON.stringify({
        shared_id: sharedId,
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
};