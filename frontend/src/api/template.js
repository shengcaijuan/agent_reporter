// 模板管理 API
import request from './request'

export const templateApi = {
  // 获取模板列表
  getTemplates: () => request.get('/templates'),

  // 获取单个模板详情
  getTemplate: (templateId) => request.get(`/templates/${templateId}`),

  // 创建模板
  createTemplate: (data) => request.post('/templates', data),

  // 更新模板
  updateTemplate: (templateId, data) => request.put(`/templates/${templateId}`, data),

  // 删除模板
  deleteTemplate: (templateId) => request.delete(`/templates/${templateId}`),

  // 应用模板到任务
  applyTemplate: (templateId, taskId) =>
    request.post(`/templates/${templateId}/apply`, { task_id: taskId }),

  // 上传模板文件
  uploadTemplate: (formData, onUploadProgress) =>
    request.post('/templates/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress
    }),

  // 获取模板预览URL
  getPreviewUrl: (templateId) => `/api/templates/${templateId}/preview`
}

export default templateApi