import { request } from '../request';

export function fetchAdminDashboard() {
  return request<any>({ url: '/admin/dashboard' });
}

export function fetchAdminUsers(params: Record<string, any>) {
  return request<any>({ url: '/admin/users', params });
}

export function fetchAdminUserDetail(id: string | number) {
  return request<any>({ url: `/admin/users/${id}` });
}

export function updateAdminUserStatus(id: string | number, enabled: boolean) {
  return request<any>({
    url: `/admin/users/${id}/status`,
    method: 'patch',
    data: { enabled }
  });
}

export function updateAdminUserRole(id: string | number, role: 'user' | 'admin') {
  return request<any>({
    url: `/admin/users/${id}/role`,
    method: 'patch',
    data: { role }
  });
}

export function resetAdminUserPassword(id: string | number, password: string) {
  return request<any>({
    url: `/admin/users/${id}/reset-password`,
    method: 'post',
    data: { password }
  });
}

export function fetchAdminAgentsOverview() {
  return request<any>({ url: '/admin/agents/overview' });
}

export function fetchAdminLogs(params: Record<string, any>) {
  return request<any>({ url: '/admin/logs', params });
}

export function fetchAdminRuntime(limit = 80) {
  return request<any>({ url: '/admin/runtime', params: { limit }, timeout: 8000 });
}
