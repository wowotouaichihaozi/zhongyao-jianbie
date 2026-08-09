import { localStg } from './storage';

function readParam(searchParams: URLSearchParams, hashParams: URLSearchParams, key: string) {
  return hashParams.get(key) || searchParams.get(key) || '';
}

function normalizeRedirect(value: string) {
  if (!value || !value.startsWith('/') || value.startsWith('//')) {
    return '/dashboard';
  }

  return value;
}

function buildCleanUrl(redirect: string) {
  const baseUrl = import.meta.env.BASE_URL || '/';
  const basePath = baseUrl === '/' ? '' : baseUrl.replace(/\/$/, '');
  const path = redirect.startsWith(basePath || '/') ? redirect : `${basePath}${redirect}`;

  return `${window.location.origin}${path}`;
}

export function hasExternalAuthParams(hash = window.location.hash) {
  const normalizedHash = hash.startsWith('#') ? hash.slice(1) : hash;
  const hashParams = new URLSearchParams(normalizedHash);

  return Boolean(hashParams.get('auth_token'));
}

export function consumeExternalAuth() {
  const hash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : window.location.hash;
  const hashParams = new URLSearchParams(hash);
  const searchParams = new URLSearchParams(window.location.search);
  const token = readParam(searchParams, hashParams, 'auth_token');

  if (!token) {
    return null;
  }

  const refreshToken = readParam(searchParams, hashParams, 'refresh_token') || token;
  const redirect = normalizeRedirect(readParam(searchParams, hashParams, 'redirect'));

  localStg.set('token', token);
  localStg.set('refreshToken', refreshToken);
  window.history.replaceState(null, document.title, buildCleanUrl(redirect));

  return redirect;
}
