import { apiClient } from './client';
import type { UserProfile, ProfileResponse } from '@/types/api';

export const createProfile = async (profile: UserProfile): Promise<ProfileResponse> => {
  const response = await apiClient.post('/profiles', profile);
  return response.data;
};

export const getProfile = async (profileId: string): Promise<UserProfile> => {
  const response = await apiClient.get(`/profiles/${profileId}`);
  return response.data;
};

export const updateProfile = async (profileId: string, fields: Partial<UserProfile>): Promise<ProfileResponse> => {
  const response = await apiClient.patch(`/profiles/${profileId}`, fields);
  return response.data;
};
