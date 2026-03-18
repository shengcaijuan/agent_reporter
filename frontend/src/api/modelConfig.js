// 模型配置 API
import api from './request'

export const modelConfigApi = {
  /**
   * 获取模型配置
   */
  getConfig: () => {
    return api.get('/model-config')
  },

  /**
   * 更新模型配置（完整更新）
   * @param {Object} data - 配置数据
   * @param {string} [data.default_model_type] - 默认模型类型
   * @param {Object} [data.models] - 模型配置
   */
  updateConfig: (data) => {
    return api.put('/model-config', data)
  },

  /**
   * 更新单个模型配置
   * @param {Object} data - 模型数据
   * @param {string} data.model_type - 模型类型 (cloud/local)
   * @param {string} [data.name] - 模型名称
   * @param {string} [data.model_name] - 模型标识
   * @param {string} [data.api_key] - API Key
   * @param {string} [data.base_url] - Base URL
   * @param {string} [data.description] - 描述
   * @param {boolean} [data.enabled] - 是否启用
   */
  updateModel: (data) => {
    return api.patch('/model-config/model', data)
  },

  /**
   * 设置默认模型类型
   * @param {string} modelType - 模型类型 (cloud/local)
   */
  setDefaultType: (modelType) => {
    return api.put(`/model-config/default-type?model_type=${modelType}`)
  }
}