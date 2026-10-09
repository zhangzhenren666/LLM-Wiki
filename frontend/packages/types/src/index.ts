/**
 * 全局共享类型定义
 * 由 @wiki/types 包统一导出，供前端各模块使用。
 */

/** 后端统一响应包裹 */
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T | null;
}

/** 健康检查数据 */
export interface HealthData {
  status: string;
  version: string;
}

/** 健康检查统一响应 */
export type HealthResponse = ApiResponse<HealthData>;

/** 知识库 */
export interface KnowledgeBase {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

/** 创建/编辑知识库入参 */
export interface KnowledgeBaseInput {
  name: string;
  description?: string | null;
}

/** 知识库响应包裹 */
export type KnowledgeBaseResponse = ApiResponse<KnowledgeBase>;
export type KnowledgeBaseListResponse = ApiResponse<KnowledgeBase[]>;

/** 页面状态 */
export type PageStatus = 'draft' | 'published' | 'archived';

/** Wiki 页面 */
export interface Page {
  id: number;
  knowledge_base_id: number;
  parent_id: number | null;
  title: string;
  slug: string;
  content: string;
  status: PageStatus;
  tags: string[];
  created_at: string;
  updated_at: string;
}

/** 创建/编辑页面入参 */
export interface PageInput {
  title: string;
  slug?: string | null;
  parent_id?: number | null;
  content?: string;
  status?: PageStatus;
}

/** 页面响应包裹 */
export type PageResponse = ApiResponse<Page>;
export type PageListResponse = ApiResponse<Page[]>;

/** 反向引用 */
export interface BacklinkRead {
  id: number;
  title: string;
  slug: string;
  knowledge_base_id: number;
  source: string;
}

export type BacklinksResponse = ApiResponse<BacklinkRead[]>;

/** 关系类型 */
export type RelationType = 'related' | 'references' | 'depends_on' | 'parent';

/** 关系实体 */
export interface RelationRead {
  id: number;
  knowledge_base_id: number;
  source_page_id: number;
  target_page_id: number;
  relation_type: string;
  source: string;
  created_at: string;
  updated_at: string;
}

/** 创建关系入参 */
export interface RelationCreateInput {
  source_page_id: number;
  target_page_id: number;
  relation_type: RelationType;
}

/** 页面关系条目（含关联页面信息） */
export interface PageRelationItem {
  id: number;
  source_page_id: number;
  target_page_id: number;
  relation_type: string;
  source: string;
  related_page: { id: number; title: string; slug: string } | null;
  created_at: string;
}

/** 页面关系响应数据 */
export interface PageRelationsData {
  outgoing: PageRelationItem[];
  incoming: PageRelationItem[];
}

export type RelationListResponse = ApiResponse<RelationRead[]>;
export type RelationResponse = ApiResponse<RelationRead>;
export type PageRelationsResponse = ApiResponse<PageRelationsData>;

/** 图谱节点 */
export interface GraphNode {
  id: number;
  label: string;
  title: string;
  slug: string;
  knowledge_base_id: number;
}

/** 图谱边 */
export interface GraphEdge {
  id: number;
  source: number;
  target: number;
  relation_type: string;
  label: string;
}

/** 图谱响应数据 */
export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export type GraphResponse = ApiResponse<GraphData>;

/** 文档导入状态 */
export type ImportStatus = 'pending' | 'importing' | 'success' | 'failed';

/** 文档实体 */
export interface DocumentRead {
  id: number;
  knowledge_base_id: number;
  file_name: string;
  file_type: string | null;
  import_status: ImportStatus;
  page_id: number | null;
  error_message: string | null;
  created_at: string;
}

export type DocumentResponse = ApiResponse<DocumentRead>;

/** 搜索匹配类型 */
export type MatchType = 'title' | 'tag' | 'content';

/** 单条搜索结果 */
export interface SearchResult {
  page_id: number;
  title: string;
  slug: string;
  knowledge_base_id: number;
  knowledge_base_name: string | null;
  match_type: MatchType;
  snippet: string | null;
  tags: string[];
}

/** 分页搜索结果 */
export interface PaginatedSearchResponse {
  items: SearchResult[];
  total: number;
  page: number;
  page_size: number;
  query: string;
}

export type SearchResponse = ApiResponse<PaginatedSearchResponse>;

/** 大模型配置 */
export interface ModelConfig {
  id: number;
  name: string;
  base_url: string;
  model_name: string;
  timeout_seconds: number;
  is_active: boolean;
  is_default: boolean;
  /** 是否已配置 API Key（后端绝不返回明文） */
  api_key_configured: boolean;
  created_at: string;
  updated_at: string;
}

/** 创建/编辑模型配置入参（api_key 在编辑时不填表示保留原值） */
export interface ModelConfigInput {
  name: string;
  base_url: string;
  model_name: string;
  api_key?: string | null;
  timeout_seconds?: number;
  is_active?: boolean;
  is_default?: boolean;
}

/** 测试连接结果 */
export interface ModelConfigTestResult {
  success: boolean;
  message: string;
  reply?: string | null;
}

export type ModelConfigResponse = ApiResponse<ModelConfig>;
export type ModelConfigListResponse = ApiResponse<ModelConfig[]>;
export type ModelConfigTestResponse = ApiResponse<ModelConfigTestResult>;

/** 文档处理任务状态 */
export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'needs_attention';

/** 处理记录步骤 */
export interface TaskStepRead {
  id: number;
  task_id: number;
  step_name: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  page_id: number | null;
  relation_id: number | null;
  created_at: string;
}

/** 文档处理任务（详情，含步骤） */
export interface DocumentTaskRead {
  id: number;
  document_id: number;
  knowledge_base_id: number;
  request_id: string | null;
  status: TaskStatus;
  attempts: number;
  max_attempts: number;
  progress: number;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  steps: TaskStepRead[];
}

/** 文档处理任务列表项（不含步骤） */
export interface DocumentTaskListItem {
  id: number;
  document_id: number;
  knowledge_base_id: number;
  request_id: string | null;
  status: TaskStatus;
  attempts: number;
  max_attempts: number;
  progress: number;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export type DocumentTaskResponse = ApiResponse<DocumentTaskRead>;
export type DocumentTaskListResponse = ApiResponse<DocumentTaskListItem[]>;
