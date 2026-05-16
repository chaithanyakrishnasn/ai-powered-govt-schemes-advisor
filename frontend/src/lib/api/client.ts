import axios from 'axios';

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 60_000,
});

// Response interceptor — normalize error shape
apiClient.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 422) {
      console.error('422 Validation Error details:', JSON.stringify(error.response.data, null, 2));
    }
    const message =
      error.response?.data?.message ?? error.message ?? 'Unknown error';
    return Promise.reject(new Error(message));
  }
);
