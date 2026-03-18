// 任务状态管理
import { create } from 'zustand'
import { taskApi } from '../api/task'

const useTaskStore = create((set, get) => ({
  // 状态
  tasks: [],
  currentTask: null,
  loading: false,
  saving: false,
  error: null,

  // 获取任务列表
  fetchTasks: async () => {
    set({ loading: true, error: null })
    try {
      const response = await taskApi.getTasks()
      // response 格式: { success, data: [...], total }
      const tasksData = response.data || []
      set({ tasks: tasksData, loading: false })
    } catch (error) {
      set({ error: error.message || error.detail, loading: false })
    }
  },

  // 获取单个任务
  fetchTask: async (taskId) => {
    set({ loading: true, error: null })
    try {
      const response = await taskApi.getTask(taskId)
      // response 格式: { success, data: { task_id, task_name, ... } }
      set({ currentTask: response.data, loading: false })
    } catch (error) {
      set({ error: error.message || error.detail, loading: false })
    }
  },

  // 设置当前任务
  setCurrentTask: (task) => {
    set({ currentTask: task })
  },

  // 创建任务
  createTask: async (taskData) => {
    set({ saving: true, error: null })
    try {
      const response = await taskApi.createTask(taskData)
      // response 格式: { success, message, data: { task_id, task_name, ... } }
      const newTask = response.data

      // 添加到任务列表
      set((state) => ({
        tasks: [...state.tasks, {
          task_id: newTask.task_id,
          task_name: newTask.task_name,
          business_department: newTask.business_department,
          description: newTask.description,
          report_count: 0
        }],
        saving: false
      }))

      return newTask
    } catch (error) {
      const errorMsg = error.detail || error.message || '创建失败'
      set({ error: errorMsg, saving: false })
      throw new Error(errorMsg)
    }
  },

  // 更新任务
  updateTask: async (taskId, updates) => {
    set({ saving: true, error: null })
    try {
      const response = await taskApi.updateTask(taskId, updates)
      const updatedTask = response.data

      set((state) => ({
        tasks: state.tasks.map((t) =>
          t.task_id === taskId ? {
            ...t,
            task_name: updatedTask.task_name,
            business_department: updatedTask.business_department,
            description: updatedTask.description
          } : t
        ),
        currentTask: state.currentTask?.task_id === taskId ? updatedTask : state.currentTask,
        saving: false
      }))
      return updatedTask
    } catch (error) {
      const errorMsg = error.detail || error.message || '更新失败'
      set({ error: errorMsg, saving: false })
      throw new Error(errorMsg)
    }
  },

  // 删除任务
  deleteTask: async (taskId) => {
    set({ saving: true, error: null })
    try {
      await taskApi.deleteTask(taskId)
      set((state) => ({
        tasks: state.tasks.filter((t) => t.task_id !== taskId),
        currentTask: state.currentTask?.task_id === taskId ? null : state.currentTask,
        saving: false
      }))
    } catch (error) {
      const errorMsg = error.detail || error.message || '删除失败'
      set({ error: errorMsg, saving: false })
      throw new Error(errorMsg)
    }
  },

  // 重置状态
  reset: () => {
    set({
      tasks: [],
      currentTask: null,
      loading: false,
      saving: false,
      error: null
    })
  }
}))

export default useTaskStore