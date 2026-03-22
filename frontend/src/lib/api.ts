import { supabase } from "./supabase";
import { config } from "./config";
import { ApiError } from "./api-types";

export { ApiError } from "./api-types";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async getAuthHeader(): Promise<Record<string, string>> {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session) {
      throw new ApiError(
        {
          error_type: "AUTHENTICATION_ERROR",
          error_code: "NO_SESSION",
          error_message: "Not authenticated",
          request_id: null,
        },
        0,
      );
    }

    return {
      Authorization: `Bearer ${session.access_token}`,
    };
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      let body: unknown;
      try {
        body = await response.json();
      } catch {
        throw new ApiError(
          {
            error_type: "NETWORK_ERROR",
            error_code: "UNPARSEABLE_RESPONSE",
            error_message: `Request failed with status ${response.status}`,
            request_id: null,
          },
          response.status,
        );
      }

      const payload = body as {
        error_type?: string;
        error_code?: string;
        error_message?: string;
        request_id?: string | null;
      };

      throw new ApiError(
        {
          error_type: payload.error_type ?? "UNKNOWN_ERROR",
          error_code: payload.error_code ?? "UNKNOWN",
          error_message:
            payload.error_message ??
            `Request failed with status ${response.status}`,
          request_id: payload.request_id ?? null,
        },
        response.status,
      );
    }

    return response.json() as Promise<T>;
  }

  private async request<T>(
    path: string,
    init: RequestInit,
  ): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, init);
    } catch {
      throw new ApiError(
        {
          error_type: "NETWORK_ERROR",
          error_code: "NETWORK_FAILURE",
          error_message:
            "Unable to reach the server. Check your connection and try again.",
          request_id: null,
        },
        0,
      );
    }
    return this.handleResponse<T>(response);
  }

  async get<T>(path: string): Promise<T> {
    const headers = await this.getAuthHeader();
    return this.request<T>(path, { headers });
  }

  async post<T>(path: string, body?: Record<string, unknown>): Promise<T> {
    const headers = await this.getAuthHeader();
    return this.request<T>(path, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async postFormData<T>(
    path: string,
    formData: FormData,
    extraHeaders?: Record<string, string>,
  ): Promise<T> {
    const headers = await this.getAuthHeader();
    return this.request<T>(path, {
      method: "POST",
      headers: { ...headers, ...extraHeaders },
      body: formData,
    });
  }
}

export const apiClient = new ApiClient(config.apiUrl);
