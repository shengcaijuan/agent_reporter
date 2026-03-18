// 进度任务历史状态管理（带持久化）
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useProgressTaskStore = create(
  persist(
    (set, get) => ({
      // 正在运行/已暂停的任务
      activeTasks: [],
      // 已完成的任务（保留）
      completedTasks: [],

      // 添加新任务
      addTask: (task) => {
        set((state) => ({
          activeTasks: [...state.activeTasks, task]
        }))
      },

      // 更新任务状态
      updateTask: (batchId, updates) => {
        set((state) => {
          // 先在 activeTasks 中查找
          const activeIndex = state.activeTasks.findIndex(t => t.batchId === batchId)
          if (activeIndex !== -1) {
            const updatedTask = { ...state.activeTasks[activeIndex], ...updates }

            // 如果状态变为 completed，移动到 completedTasks
            if (updates.status === 'completed') {
              return {
                activeTasks: state.activeTasks.filter(t => t.batchId !== batchId),
                completedTasks: [...state.completedTasks, updatedTask]
              }
            }

            // 否则更新 activeTasks
            const newActiveTasks = [...state.activeTasks]
            newActiveTasks[activeIndex] = updatedTask
            return { activeTasks: newActiveTasks }
          }

          // 在 completedTasks 中查找
          const completedIndex = state.completedTasks.findIndex(t => t.batchId === batchId)
          if (completedIndex !== -1) {
            const newCompletedTasks = [...state.completedTasks]
            newCompletedTasks[completedIndex] = { ...newCompletedTasks[completedIndex], ...updates }
            return { completedTasks: newCompletedTasks }
          }

          return state
        })
      },

      // 删除任务
      removeTask: (batchId) => {
        set((state) => ({
          activeTasks: state.activeTasks.filter(t => t.batchId !== batchId),
          completedTasks: state.completedTasks.filter(t => t.batchId !== batchId)
        }))
      },

      // 获取任务详情
      getTask: (batchId) => {
        const state = get()
        return state.activeTasks.find(t => t.batchId === batchId) ||
               state.completedTasks.find(t => t.batchId === batchId)
      },

      // 获取所有任务（用于导航菜单）
      getAllTasks: () => {
        const state = get()
        return [...state.activeTasks, ...state.completedTasks]
      },

      // 清空已完成任务
      clearCompleted: () => {
        set({ completedTasks: [] })
      },

      // 重置所有
      reset: () => {
        set({ activeTasks: [], completedTasks: [] })
      }
    }),
    {
      name: 'progress-tasks', // localStorage key
    }
  )
)