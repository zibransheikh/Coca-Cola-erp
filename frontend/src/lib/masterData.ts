import { api } from "@/lib/api";

export type FieldType = "text" | "number" | "decimal" | "boolean" | "date" | "select";

export interface SelectOption {
  value: string | number;
  label: string;
}

export interface FieldConfig {
  name: string;
  label: string;
  type: FieldType;
  required?: boolean;
  options?: SelectOption[];
}

export interface ColumnConfig<T> {
  key: keyof T & string;
  label: string;
  render?: (row: T) => React.ReactNode;
}

export interface ResourceConfig<T extends { id: number; is_active?: boolean }> {
  title: string;
  endpoint: string;
  columns: ColumnConfig<T>[];
  createFields: FieldConfig[];
  editFields: FieldConfig[];
}

export async function listResource<T>(endpoint: string): Promise<T[]> {
  const { data } = await api.get<T[]>(endpoint);
  return data;
}

export async function createResource<T>(endpoint: string, payload: Record<string, unknown>): Promise<T> {
  const { data } = await api.post<T>(endpoint, payload);
  return data;
}

export async function updateResource<T>(
  endpoint: string,
  id: number,
  payload: Record<string, unknown>
): Promise<T> {
  const { data } = await api.put<T>(`${endpoint}/${id}`, payload);
  return data;
}
