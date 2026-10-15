export async function api(path, { method = 'GET', body, signal } = {}) {
  const headers = {};
  if (method !== 'GET') {
    const token = await api('/auth/csrf');
    headers['X-CSRFToken'] = token.csrf_token;
    headers['Content-Type'] = 'application/json';
  }
  let response;
  try {
    response = await fetch(`/api${path}`, {
      method, headers, signal, credentials: 'same-origin',
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('No hay conexión con el servicio. Inténtalo de nuevo.');
  }
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok || (response.status !== 204 && !data)) {
    const error = new Error(data?.error?.message || 'El servicio no está disponible. Inténtalo de nuevo.');
    error.status = response.status;
    throw error;
  }
  return data;
}
