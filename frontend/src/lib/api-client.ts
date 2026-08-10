export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:10000";

export class ApiClient {
  static async request<T = any>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
    const response = await fetch(url, options);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    
    return response.json();
  }

  static async get<T = any>(endpoint: string, options?: RequestInit): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  static async post<T = any>(endpoint: string, data?: any, options?: RequestInit): Promise<T> {
    const headers = { 'Content-Type': 'application/json', ...options?.headers };
    return this.request<T>(endpoint, { 
      ...options, 
      method: 'POST', 
      headers, 
      body: data ? JSON.stringify(data) : undefined 
    });
  }
}
