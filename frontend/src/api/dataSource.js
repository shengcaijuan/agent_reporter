// 数据源配置 API
import request from './request'

export const dataSourceApi = {
  // ==================== 全局数据源管理 ====================

  // 获取全局数据源列表
  getGlobalDataSources: () => request.get('/data-sources'),

  // 创建全局数据源
  createGlobalDataSource: (data) => request.post('/data-sources', data),

  // 获取指定数据源详情
  getGlobalDataSource: (sourceId) => request.get(`/data-sources/${sourceId}`),

  // 更新全局数据源
  updateGlobalDataSource: (sourceId, data) => request.put(`/data-sources/${sourceId}`, data),

  // 删除全局数据源
  deleteGlobalDataSource: (sourceId) => request.delete(`/data-sources/${sourceId}`),

  // ==================== 任务级数据源配置 ====================

  // 获取任务数据源配置
  getTaskDataSource: (taskId) => request.get(`/data-sources/tasks/${taskId}`),

  // 更新任务数据源配置（关联到全局数据源）
  updateTaskDataSource: (taskId, dataSourceId) => request.put(`/data-sources/tasks/${taskId}`, null, {
    params: { data_source_id: dataSourceId }
  }),

  // ==================== 测试连接 ====================

  // 测试数据源连接
  testConnection: (config) => request.post('/data-sources/test', config)
}

export default dataSourceApi