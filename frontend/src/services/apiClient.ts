import { API_CONFIG } from '../config/api';

class ApiClient {
  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };

    if (API_CONFIG.AUTH_TOKEN) {
      headers[API_CONFIG.AUTH_HEADER_NAME] = API_CONFIG.AUTH_TOKEN.startsWith('Bearer ')
        ? API_CONFIG.AUTH_TOKEN
        : `Bearer ${API_CONFIG.AUTH_TOKEN}`;
    }

    return headers;
  }

  public async get<T>(endpoint: string): Promise<T> {
    const cleanBase = API_CONFIG.BASE_URL.replace(/\/+$/, '');
    const cleanEndpoint = endpoint.replace(/^\/+/, '');
    const url = `${cleanBase}/${cleanEndpoint}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown network error');
      throw new Error(`API HTTP ${response.status} (${response.statusText}): ${errorText}`);
    }

    return response.json();
  }
}

export const apiClient = new ApiClient();
