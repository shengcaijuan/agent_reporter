// 配置状态管理
import { create } from 'zustand'
import { configApi } from '../api/config'

export const useConfigStore = create((set, get) => ({
  // 章节列表
  chapters: [],
  // 当前选中的章节
  currentChapter: 1,
  // 章节配置
  chapterConfig: null,
  // 工具配置列表
  toolConfigs: [],
  // 当前编辑的工具
  editingTool: null,
  // 加载状态
  loading: false,
  // 保存状态
  saving: false,

  // 获取章节列表
  fetchChapters: async () => {
    try {
      const chapters = await configApi.getChapters()
      set({ chapters })
    } catch (error) {
      console.error('获取章节列表失败:', error)
    }
  },

  // 设置当前章节
  setCurrentChapter: (chapterId) => {
    set({ currentChapter: chapterId })
    get().fetchChapterConfig(chapterId)
    get().fetchToolConfigs(chapterId)
  },

  // 获取章节配置
  fetchChapterConfig: async (chapterId) => {
    set({ loading: true })
    try {
      const config = await configApi.getChapterConfig(chapterId)
      set({ chapterConfig: config, loading: false })
    } catch (error) {
      console.error('获取章节配置失败:', error)
      set({ loading: false })
    }
  },

  // 保存章节配置
  saveChapterConfig: async (config) => {
    set({ saving: true })
    try {
      await configApi.updateChapterConfig(get().currentChapter, config)
      set({ chapterConfig: config, saving: false })
      return true
    } catch (error) {
      console.error('保存章节配置失败:', error)
      set({ saving: false })
      return false
    }
  },

  // 获取工具配置列表
  fetchToolConfigs: async (chapterId) => {
    try {
      const configs = await configApi.getToolConfigs(chapterId)
      set({ toolConfigs: configs })
    } catch (error) {
      console.error('获取工具配置失败:', error)
    }
  },

  // 创建工具配置
  createToolConfig: async (config) => {
    try {
      const newConfig = await configApi.createToolConfig(get().currentChapter, config)
      set(state => ({
        toolConfigs: [...state.toolConfigs, newConfig]
      }))
      return true
    } catch (error) {
      console.error('创建工具配置失败:', error)
      return false
    }
  },

  // 更新工具配置
  updateToolConfig: async (toolId, config) => {
    try {
      await configApi.updateToolConfig(get().currentChapter, toolId, config)
      set(state => ({
        toolConfigs: state.toolConfigs.map(t =>
          t.tool_id === toolId ? { ...t, ...config } : t
        )
      }))
      return true
    } catch (error) {
      console.error('更新工具配置失败:', error)
      return false
    }
  },

  // 删除工具配置
  deleteToolConfig: async (toolId) => {
    try {
      await configApi.deleteToolConfig(get().currentChapter, toolId)
      set(state => ({
        toolConfigs: state.toolConfigs.filter(t => t.tool_id !== toolId)
      }))
      return true
    } catch (error) {
      console.error('删除工具配置失败:', error)
      return false
    }
  },

  // 设置编辑中的工具
  setEditingTool: (tool) => {
    set({ editingTool: tool })
  }
}))