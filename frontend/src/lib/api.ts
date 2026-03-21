import { supabase } from "./supabase";
import { config } from "./config";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async getHeaders(): Promise<Record<string, string>> {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session) {
      throw new Error("Not authenticated");
    }

    return {
      Authorization: `Bearer ${session.access_token}`,
    };
  }

  async get(path: string): Promise<Response> {
    const headers = await this.getHeaders();
    return fetch(`${this.baseUrl}${path}`, { headers });
  }

  async post(path: string, body?: Record<string, unknown>): Promise<Response> {
    const headers = await this.getHeaders();
    return fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async postFormData(
    path: string,
    formData: FormData,
    extraHeaders?: Record<string, string>,
  ): Promise<Response> {
    const headers = await this.getHeaders();
    return fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { ...headers, ...extraHeaders },
      body: formData,
    });
  }
}

export const apiClient = new ApiClient(config.apiUrl);
