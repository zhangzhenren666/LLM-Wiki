/**
 * 业务 API 函数封装
 * 集中定义与后端交互的接口函数。
 */

import type {
  ApiResponse,
  BacklinksResponse,
  GraphResponse,
  HealthResponse,
  KnowledgeBaseInput,
  KnowledgeBaseListResponse,
  KnowledgeBaseResponse,
  PageInput,
  PageListResponse,
  PageRelationsResponse,
  PageResponse,
  RelationCreateInput,
  RelationListResponse,
  RelationResponse,
  DocumentResponse,
  RelationType,
  SearchResponse,
  ModelConfigInput,
  ModelConfigListResponse,
  ModelConfigResponse,
  ModelConfigTestResponse,
  DocumentTaskListResponse,
  DocumentTaskResponse,
} from '@wiki/types';
import { API_BASE_URL } from '@wiki/config';
import { http } from '@/lib/http';

/**
 * 请求后端 /health 健康检查接口
 */
export function fetchHealth(): Promise<HealthResponse> {
  return http.get<HealthResponse>('/health', { next: { revalidate: 5 } });
}

const KB_PATH = '/api/v1/knowledge-bases';

/** 查询全部知识库 */
export function listKnowledgeBases(): Promise<KnowledgeBaseListResponse> {
  return http.get<KnowledgeBaseListResponse>(KB_PATH);
}

/** 查询单个知识库 */
export function getKnowledgeBase(id: number): Promise<KnowledgeBaseResponse> {
  return http.get<KnowledgeBaseResponse>(`${KB_PATH}/${id}`);
}

/** 创建知识库 */
export function createKnowledgeBase(
  input: KnowledgeBaseInput
): Promise<KnowledgeBaseResponse> {
  return http.post<KnowledgeBaseResponse>(KB_PATH, input);
}

/** 更新知识库 */
export function updateKnowledgeBase(
  id: number,
  input: KnowledgeBaseInput
): Promise<KnowledgeBaseResponse> {
  return http.put<KnowledgeBaseResponse>(`${KB_PATH}/${id}`, input);
}

/** 删除知识库 */
export function deleteKnowledgeBase(id: number): Promise<unknown> {
  return http.delete<unknown>(`${KB_PATH}/${id}`);
}

const PAGE_PATH = '/api/v1/pages';

/** 查询知识库下的页面（支持 parent_id=0 查顶层、tag 筛选） */
export function listPages(params: {
  knowledge_base_id: number;
  parent_id?: number;
  status?: string;
  keyword?: string;
  tag?: string;
}): Promise<PageListResponse> {
  const search = new URLSearchParams();
  search.set('knowledge_base_id', String(params.knowledge_base_id));
  if (params.parent_id !== undefined && params.parent_id !== null) {
    search.set('parent_id', String(params.parent_id));
  }
  if (params.status) {
    search.set('status', params.status);
  }
  if (params.keyword) {
    search.set('keyword', params.keyword);
  }
  if (params.tag) {
    search.set('tag', params.tag);
  }
  return http.get<PageListResponse>(`${PAGE_PATH}?${search.toString()}`);
}

/** 查询单个页面 */
export function getPage(id: number): Promise<PageResponse> {
  return http.get<PageResponse>(`${PAGE_PATH}/${id}`);
}

/** 创建页面 */
export function createPage(
  input: PageInput & { knowledge_base_id: number }
): Promise<PageResponse> {
  return http.post<PageResponse>(PAGE_PATH, input);
}

/** 更新页面（所有字段可选，仅更新传入字段） */
export function updatePage(
  id: number,
  input: Partial<PageInput>
): Promise<PageResponse> {
  return http.put<PageResponse>(`${PAGE_PATH}/${id}`, input);
}

/** 删除页面 */
export function deletePage(id: number): Promise<unknown> {
  return http.delete<unknown>(`${PAGE_PATH}/${id}`);
}

/** 为页面添加标签（自动去重） */
export function addPageTags(id: number, tags: string[]): Promise<PageResponse> {
  return http.post<PageResponse>(`${PAGE_PATH}/${id}/tags`, { tags });
}

/** 从页面移除标签 */
export function removePageTags(
  id: number,
  tags: string[]
): Promise<PageResponse> {
  return http.delete<PageResponse>(
    `${PAGE_PATH}/${id}/tags?${new URLSearchParams(
      tags.map((t) => ['tags', t])
    ).toString()}`
  );
}

/** 移动页面到新父节点（parentId 为 null 表示置为顶层） */
export function movePage(
  id: number,
  parentId: number | null
): Promise<PageResponse> {
  return http.put<PageResponse>(`${PAGE_PATH}/${id}/move`, {
    parent_id: parentId,
  });
}

/** 查询知识库下出现过的所有标签 */
export function listKnowledgeBaseTags(
  kbId: number
): Promise<ApiResponse<string[]>> {
  return http.get<ApiResponse<string[]>>(`${KB_PATH}/${kbId}/tags`);
}

/** 查询页面的反向引用列表 */
export function getBacklinks(pageId: number): Promise<BacklinksResponse> {
  return http.get<BacklinksResponse>(`${PAGE_PATH}/${pageId}/backlinks`);
}

const RELATION_PATH = '/api/v1/relations';

/** 查询关系列表（可按知识库、页面、类型筛选） */
export function listRelations(params: {
  knowledge_base_id?: number;
  page_id?: number;
  relation_type?: RelationType;
}): Promise<RelationListResponse> {
  const search = new URLSearchParams();
  if (params.knowledge_base_id !== undefined) {
    search.set('knowledge_base_id', String(params.knowledge_base_id));
  }
  if (params.page_id !== undefined) {
    search.set('page_id', String(params.page_id));
  }
  if (params.relation_type) {
    search.set('relation_type', params.relation_type);
  }
  const qs = search.toString();
  return http.get<RelationListResponse>(
    qs ? `${RELATION_PATH}?${qs}` : RELATION_PATH
  );
}

/** 创建页面关系 */
export function createRelation(
  input: RelationCreateInput
): Promise<RelationResponse> {
  return http.post<RelationResponse>(RELATION_PATH, input);
}

/** 删除关系 */
export function deleteRelation(
  id: number
): Promise<ApiResponse<{ id: number }>> {
  return http.delete<ApiResponse<{ id: number }>>(`${RELATION_PATH}/${id}`);
}

/** 查询某页面的所有关系（出向 + 入向） */
export function getPageRelations(
  pageId: number
): Promise<PageRelationsResponse> {
  return http.get<PageRelationsResponse>(`${PAGE_PATH}/${pageId}/relations`);
}

const GRAPH_PATH = '/api/v1/graph';

/** 获取单页面关联图谱 */
export function getPageGraph(
  pageId: number,
  depth?: number
): Promise<GraphResponse> {
  const qs = depth ? `?depth=${depth}` : '';
  return http.get<GraphResponse>(`${GRAPH_PATH}/pages/${pageId}${qs}`);
}

/** 获取知识库整体图谱 */
export function getKbGraph(
  kbId: number,
  maxNodes?: number
): Promise<GraphResponse> {
  const qs = maxNodes ? `?max_nodes=${maxNodes}` : '';
  return http.get<GraphResponse>(
    `${GRAPH_PATH}/knowledge-bases/${kbId}${qs}`
  );
}

/** 上传文档并导入为 Wiki 页面（multipart/form-data） */
export async function uploadDocument(
  kbId: number,
  file: File
): Promise<DocumentResponse> {
  const formData = new FormData();
  formData.append('knowledge_base_id', String(kbId));
  formData.append('file', file);

  const response = await fetch(
    `${API_BASE_URL}/api/v1/documents/upload`,
    {
      method: 'POST',
      body: formData,
    }
  );

  if (!response.ok) {
    let message = `上传失败: HTTP ${response.status}`;
    try {
      const data = await response.json();
      if (typeof data.message === 'string') message = data.message;
    } catch { /* ignore */ }
    throw new Error(message);
  }

  return response.json();
}

/** 搜索页面（标题、标签、正文） */
export function searchPages(params: {
  q: string;
  knowledge_base_id?: number;
  page?: number;
  page_size?: number;
}): Promise<SearchResponse> {
  const search = new URLSearchParams();
  search.set('q', params.q);
  if (params.knowledge_base_id !== undefined) {
    search.set('knowledge_base_id', String(params.knowledge_base_id));
  }
  if (params.page !== undefined) {
    search.set('page', String(params.page));
  }
  if (params.page_size !== undefined) {
    search.set('page_size', String(params.page_size));
  }
  return http.get<SearchResponse>(`/api/v1/search?${search.toString()}`);
}

const MODEL_CONFIG_PATH = '/api/v1/model-configs';

/** 查询全部模型配置（后端不返回 API Key 明文） */
export function listModelConfigs(): Promise<ModelConfigListResponse> {
  return http.get<ModelConfigListResponse>(MODEL_CONFIG_PATH);
}

/** 创建模型配置 */
export function createModelConfig(
  input: ModelConfigInput
): Promise<ModelConfigResponse> {
  return http.post<ModelConfigResponse>(MODEL_CONFIG_PATH, input);
}

/** 更新模型配置（api_key 不填表示保留原值） */
export function updateModelConfig(
  id: number,
  input: Partial<ModelConfigInput>
): Promise<ModelConfigResponse> {
  return http.put<ModelConfigResponse>(
    `${MODEL_CONFIG_PATH}/${id}`,
    input
  );
}

/** 删除模型配置 */
export function deleteModelConfig(id: number): Promise<unknown> {
  return http.delete<unknown>(`${MODEL_CONFIG_PATH}/${id}`);
}

/** 测试模型配置的连接可用性 */
export function testModelConfig(
  id: number
): Promise<ModelConfigTestResponse> {
  return http.post<ModelConfigTestResponse>(
    `${MODEL_CONFIG_PATH}/${id}/test`
  );
}

const DOCUMENT_TASK_PATH = '/api/v1/document-tasks';

/** 查询文档处理任务列表 */
export function listDocumentTasks(params?: {
  status?: string;
  knowledge_base_id?: number;
  limit?: number;
  offset?: number;
}): Promise<DocumentTaskListResponse> {
  const search = new URLSearchParams();
  if (params) {
    if (params.status) search.set('status', params.status);
    if (params.knowledge_base_id !== undefined)
      search.set('knowledge_base_id', String(params.knowledge_base_id));
    if (params.limit !== undefined) search.set('limit', String(params.limit));
    if (params.offset !== undefined)
      search.set('offset', String(params.offset));
  }
  const qs = search.toString();
  return http.get<DocumentTaskListResponse>(
    qs ? `${DOCUMENT_TASK_PATH}?${qs}` : DOCUMENT_TASK_PATH
  );
}

/** 查询单个任务详情（含处理步骤） */
export function getDocumentTask(
  id: number
): Promise<DocumentTaskResponse> {
  return http.get<DocumentTaskResponse>(`${DOCUMENT_TASK_PATH}/${id}`);
}

/** 重试失败/需关注的任务 */
export function retryDocumentTask(
  id: number
): Promise<DocumentTaskResponse> {
  return http.post<DocumentTaskResponse>(
    `${DOCUMENT_TASK_PATH}/${id}/retry`
  );
}
