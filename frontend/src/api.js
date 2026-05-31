import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

export const fetchOverview = async () => {
  const response = await axios.get(`${API_BASE}/overview`);
  return response.data;
};

export const fetchOutlets = async (limit = 50, offset = 0, province = "All", distributor = "All", search = "") => {
  const params = new URLSearchParams();
  params.append('limit', limit);
  params.append('offset', offset);
  if (province !== "All") params.append('province', province);
  if (distributor !== "All") params.append('distributor', distributor);
  if (search) params.append('search', search);

  const response = await axios.get(`${API_BASE}/outlets?${params.toString()}`);
  return response.data;
};

export const fetchFilters = async () => {
  const response = await axios.get(`${API_BASE}/outlets/filters`);
  return response.data;
};

export const fetchXAIList = async () => {
  const response = await axios.get(`${API_BASE}/xai/list`);
  return response.data;
};

export const fetchXAIExplanation = async (outletId) => {
  const response = await axios.get(`${API_BASE}/xai/${outletId}`);
  return response.data;
};

export const fetchBudget = async () => {
  const response = await axios.get(`${API_BASE}/budget`);
  return response.data;
};
