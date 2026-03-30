// 报告相关 API
import api from './request'

export const reportApi = {
  // 启动报告生成（支持批量）
  generate: (params) => {
    return api.post('/reports/generate', params)
  },

  // 从中断处恢复
  resume: () => {
    return api.post('/reports/resume')
  },

  // 暂停任务
  pause: () => {
    return api.post('/reports/pause')
  },

  // 获取任务状态
  getStatus: () => {
    return api.get('/reports/status')
  },

  // 清除任务状态
  clearStatus: () => {
    return api.post('/reports/clear')
  },

  // 获取报告列表
  getList: (params) => {
    return api.get('/reports', { params })
  },

  // 获取可用的报告月份列表
  getAvailableTimes: (taskId) => {
    return api.get('/reports/available-times', { params: { task_id: taskId } })
  },

  // 获取已生成的HTML报告列表（从文件系统）
  getGeneratedList: (params) => {
    // params: { task_id, report_time }
    return api.get('/reports/generated/list', { params })
  },

  // 获取已生成报告的HTML内容
  getGeneratedContent: (params) => {
    // params: { filename, file_path, task_id, report_time }
    return api.get('/reports/generated/content', { params })
  },

  // 删除指定报告（删除整个销售文件夹）
  deleteGenerated: (params) => {
    // params: { file_path, task_id, report_time }
    return api.delete('/reports/generated/delete', { params })
  },

  // 批量删除报告
  batchDeleteGenerated: (params) => {
    // params: { file_paths, task_id, report_time }
    return api.post('/reports/generated/batch-delete', params)
  },

  // 获取销售人员列表
  getSales: (taskId, params = {}) => {
    return api.get('/reports/sales', { params: { task_id: taskId, ...params } })
  },

  // 获取组织架构
  getOrganization: (taskId) => {
    return api.get('/reports/organization', { params: { task_id: taskId } })
  },

  // 获取报告详情
  getDetail: (reportId) => {
    return api.get(`/reports/${reportId}`)
  },

  // 获取下载路径
  getDownloadUrl: (reportId, fileType) => {
    return api.get(`/reports/${reportId}/download`, { params: { file_type: fileType } })
  },

  // 获取报告日志
  getLogs: (params) => {
    // params: { file_path, task_id, report_time }
    return api.get('/reports/logs', { params })
  }
}