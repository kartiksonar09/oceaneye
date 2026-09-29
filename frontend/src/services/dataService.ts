import { OperationalAlert, Spill, Suspect, Vessel } from '../types/api';
import { apiClient } from './apiClient';
import { mockEngine } from './mockEngine';

export const dataService = {
  async getSpills(useMock: boolean): Promise<Spill[]> {
    if (useMock) {
      return mockEngine.getSpills();
    }
    try {
      return await apiClient.get<Spill[]>('/spills');
    } catch (err) {
      console.warn('Backend /spills failed, falling back to cached mock:', err);
      return mockEngine.getSpills();
    }
  },

  async getVessels(useMock: boolean): Promise<Vessel[]> {
    if (useMock) {
      return mockEngine.getVessels();
    }
    try {
      return await apiClient.get<Vessel[]>('/vessels');
    } catch (err) {
      console.warn('Backend /vessels failed, falling back to cached mock:', err);
      return mockEngine.getVessels();
    }
  },

  async getSuspects(useMock: boolean): Promise<Suspect[]> {
    if (useMock) {
      return mockEngine.getSuspects();
    }
    try {
      return await apiClient.get<Suspect[]>('/suspects');
    } catch (err) {
      console.warn('Backend /suspects failed, falling back to cached mock:', err);
      return mockEngine.getSuspects();
    }
  },

  async getAlerts(useMock: boolean): Promise<OperationalAlert[]> {
    return mockEngine.getAlerts();
  },
};
