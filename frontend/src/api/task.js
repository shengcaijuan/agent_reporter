// 任务管理 API
import request from './request'

export const taskApi = {
  // 获取任务列表
  getTasks: () => request.get('/tasks'),

  // 获取单个任务
  getTask: (taskId) => request.get(`/tasks/${taskId}`),

  // 创建任务
  createTask: (data) => request.post('/tasks', data),

  // 更新任务
  updateTask: (taskId, data) => request.put(`/tasks/${taskId}`, data),

  // 删除任务
  deleteTask: (taskId) => request.delete(`/tasks/${taskId}`),

  // 获取仪表盘统计数据
  getDashboardStats: () => request.get('/tasks/stats/dashboard'),

  // 同步任务索引
  syncTaskIndex: () => request.post('/tasks/sync-index'),

  // 获取报告介绍
  getReportIntro: (taskId) => request.get(`/tasks/${taskId}/intro`),

  // 更新报告介绍
  updateReportIntro: (taskId, content) => request.put(`/tasks/${taskId}/intro`, { content }),

  // 获取章节列表
  getChapters: (taskId) => request.get(`/tasks/${taskId}/chapters`),

  // 添加章节
  addChapter: (taskId) => request.post(`/tasks/${taskId}/chapters`),

  // 删除章节
  deleteChapter: (taskId, chapterId) => request.delete(`/tasks/${taskId}/chapters/${chapterId}`),

  // 获取章节配置
  getChapterConfig: (taskId, chapterId) => request.get(`/tasks/${taskId}/chapters/${chapterId}`),

  // 更新章节配置
  updateChapterConfig: (taskId, chapterId, config) => request.put(`/tasks/${taskId}/chapters/${chapterId}`, config),

  // 获取工具配置
  getToolConfigs: (taskId, chapterId) => request.get(`/tasks/${taskId}/tools/${chapterId}`),

  // 创建工具配置
  createToolConfig: (taskId, chapterId, config) => request.post(`/tasks/${taskId}/tools/${chapterId}`, config),

  // 更新工具配置
  updateToolConfig: (taskId, chapterId, toolId, config) => request.put(`/tasks/${taskId}/tools/${chapterId}/${toolId}`, config),

  // 更新工具配置列表（批量）
  updateToolConfigs: (taskId, chapterId, config) => request.put(`/tasks/${taskId}/tools/${chapterId}`, config),

  // 删除工具配置
  deleteToolConfig: (taskId, chapterId, toolId) => request.delete(`/tasks/${taskId}/tools/${chapterId}/${toolId}`),

  // 获取报告样式配置
  getWrappingConfig: (taskId) => request.get(`/tasks/${taskId}/wrapping`),

  // 更新报告样式配置
  updateWrappingConfig: (taskId, config) => request.put(`/tasks/${taskId}/wrapping`, config),

  // 获取销售人员列表
  getSales: (taskId, params = {}) => request.get(`/tasks/${taskId}/sales`, { params })
}

export default taskApi