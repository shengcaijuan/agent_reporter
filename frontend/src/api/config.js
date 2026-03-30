// 配置相关 API
import api from './request'

export const configApi = {
  // 获取章节列表
  getChapters: () => {
    return api.get('/config/chapters')
  },

  // 获取章节配置
  getChapterConfig: (chapterId) => {
    return api.get(`/config/chapters/${chapterId}`)
  },

  // 更新章节配置
  updateChapterConfig: (chapterId, config) => {
    return api.put(`/config/chapters/${chapterId}`, config)
  },

  // 获取工具配置列表
  getToolConfigs: (chapterId) => {
    return api.get(`/config/tools/${chapterId}`)
  },

  // 创建工具配置
  createToolConfig: (chapterId, config) => {
    return api.post(`/config/tools/${chapterId}`, config)
  },

  // 更新工具配置
  updateToolConfig: (chapterId, toolId, config) => {
    return api.put(`/config/tools/${chapterId}/${toolId}`, config)
  },

  // 删除工具配置
  deleteToolConfig: (chapterId, toolId) => {
    return api.delete(`/config/tools/${chapterId}/${toolId}`)
  }
}