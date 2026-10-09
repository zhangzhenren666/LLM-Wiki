/**
 * 应用配置
 * 为各模块提供统一配置读取入口。
 */

/** 后端 API 基础地址，可通过环境变量 NEXT_PUBLIC_API_BASE_URL 覆盖 */
export const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

/** 应用名称 */
export const APP_NAME = 'Wiki 知识库';

/** 应用版本 */
export const APP_VERSION = '0.1.0';
