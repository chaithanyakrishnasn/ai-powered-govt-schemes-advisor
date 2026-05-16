import { apiClient } from './client';
import type { PaginatedSchemes, SchemeDetail } from '@/types/api';

export const getSchemes = async (params?: Record<string, string>): Promise<PaginatedSchemes> => {
  const response = await apiClient.get('/schemes', { params });
  return response.data;
};

export const getScheme = async (slug: string): Promise<SchemeDetail> => {
  const response = await apiClient.get(`/schemes/slug/${slug}`);
  return response.data;
};
