import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import type { UserProfile } from '@/types/api';

interface ProfileStore {
  currentStep: number;
  totalSteps: number;
  profile: UserProfile;
  profileId?: string;
  isComplete: boolean;
  lastUpdated?: number;
  setStep: (step: number) => void;
  nextStep: () => void;
  prevStep: () => void;
  updateProfile: (fields: Partial<UserProfile>) => void;
  setProfileId: (id: string) => void;
  complete: () => void;
  reset: () => void;
}

const initialState = {
  currentStep: 0,
  totalSteps: 4,
  profile: {},
  profileId: undefined,
  isComplete: false,
};

export const useProfileStore = create<ProfileStore>()(
  persist(
    immer((set) => ({
      ...initialState,
      setStep: (step) =>
        set((state) => {
          state.currentStep = step;
        }),
      nextStep: () =>
        set((state) => {
          if (state.currentStep < state.totalSteps - 1) {
            state.currentStep += 1;
          }
        }),
      prevStep: () =>
        set((state) => {
          if (state.currentStep > 0) {
            state.currentStep -= 1;
          }
        }),
      updateProfile: (fields) =>
        set((state) => {
          state.profile = { ...state.profile, ...fields };
          state.lastUpdated = Date.now();
        }),
      setProfileId: (id) =>
        set((state) => {
          state.profileId = id;
        }),
      complete: () =>
        set((state) => {
          state.isComplete = true;
          state.currentStep = 0;
        }),
      reset: () => {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('yojana-profile');
        }
        set(initialState);
      },
    })),
    {
      name: 'yojana-profile',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        profile: state.profile,
        profileId: state.profileId,
        currentStep: state.currentStep,
        lastUpdated: state.lastUpdated,
      }),
      onRehydrateStorage: () => (state) => {
        if (state && state.lastUpdated) {
          const ageMs = Date.now() - state.lastUpdated;
          const maxAgeMs = 24 * 60 * 60 * 1000;
          if (ageMs > maxAgeMs) {
            useProfileStore.getState().reset();
          }
        }
      },
    }
  )
);
