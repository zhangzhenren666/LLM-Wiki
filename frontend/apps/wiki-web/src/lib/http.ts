/**
 * 统一 HTTP 客户端
 *
 * 封装对后端的请求：
 * - 统一拼接基础地址
 * - 统一 JSON 解析
 * - 统一错误处理（抛出 ApiError）
 */

import { API_BASE_URL } from '@wiki/config';

/** 统一 API 错误 */
export interface ApiErrorInfo {
  /** HTTP 状态码 */
  status: number;
  /** 后端返回的业务码 */
  code?: string;
  /** 错误信息 */
  message: string;
  /** 是否属于网络/连接类错误（后端未启动等） */
  isNetworkError: boolean;
}

/** 统一的 API 错误类 */
export class ApiError extends Error implements ApiErrorInfo {
  status: number;
  code?: string;
  isNetworkError: boolean;

  constructor(info: ApiErrorInfo) {
    super(info.message);
    this.name = 'ApiError';
    this.status = info.status;
    this.code = info.code;
    this.isNetworkError = info.isNetworkError;
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  /** 请求体对象，会自动 JSON 序列化 */
  body?: unknown;
  /** 自定义请求头 */
  headers?: Record<string, string>;
  /** 传递给 fetch 的附加选项 */
  init?: RequestInit;
}

/**
 * 通用请求方法。
 * 默认在服务端/客户端都可使用；若在服务端组件中调用并需要缓存，
 * 请在 init 中传入 { next: { revalidate } }。
 */
export async function request<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = 'GET', body, headers, init } = options;

  const isBodyPresent = body !== undefined;
  // 仅在有请求体时才设置 Content-Type，避免 GET 请求触发 CORS 预检
  const finalHeaders: Record<string, string> = {
    ...(isBodyPresent ? { 'Content-Type': 'application/json' } : {}),
    ...headers,
  };

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: finalHeaders,
      body: isBodyPresent ? JSON.stringify(body) : undefined,
      ...init,
    });
  } catch {
    // 网络层错误：后端未启动、跨域失败等
    throw new ApiError({
      status: 0,
      message: '无法连接到后端服务，请确认后端已启动。',
      isNetworkError: true,
    });
  }

  if (!response.ok) {
    let message = `请求失败: HTTP ${response.status}`;
    let code: string | undefined;
    try {
      const data = (await response.json()) as Partial<ApiErrorInfo>;
      if (typeof data.message === 'string') {
        message = data.message;
      }
      code = data.code;
    } catch {
      // 响应体不是合法 JSON 时保留默认信息
    }
    throw new ApiError({
      status: response.status,
      code,
      message,
      isNetworkError: false,
    });
  }

  // 204 No Content 无响应体
  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

/** 便捷方法 */
export const http = {
  get: <T>(path: string, init?: RequestInit) => request<T>(path, { init }),
  post: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, { method: 'POST', body, init }),
  put: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, { method: 'PUT', body, init }),
  patch: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, { method: 'PATCH', body, init }),
  delete: <T>(path: string, init?: RequestInit) =>
    request<T>(path, { method: 'DELETE', init }),
};
