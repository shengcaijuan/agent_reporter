// 进度状态管理
import { create } from 'zustand'
import { wsClient } from '../api/websocket'
import { reportApi } from '../api/report'
import { useProgressTaskStore } from './progressTaskStore'

export const useProgressStore = create((set, get) => ({
  // 任务状态
  batchId: null,
  taskId: null,
  taskName: null,      // 任务名称
  reportTime: null,    // 报告月份
  status: 'idle', // idle, running, paused, completed, error
  total: 0,
  completed: 0,
  failed: 0,
  inProgress: 0,
  paused: 0,  // 暂停的任务数
  isLoading: false,  // 恢复时的加载状态
  startTime: null,
  // 当前处理的销售
  currentSales: [],
  // 等待处理的销售
  pendingSales: [],
  // 日志
  logs: [],
  // 最大日志数量
  maxLogs: 100,

  // 初始化 WebSocket
  initWebSocket: () => {
    wsClient.connect()

    wsClient.on('progress', (data) => {
      set({
        taskId: data.task_id,
        batchId: data.batch_id,
        taskName: data.task_name,
        reportTime: data.report_time,
        total: data.total,
        completed: data.completed,
        failed: data.failed,
        inProgress: data.in_progress,
        paused: data.paused || 0,
        status: data.status,
        isLoading: false,  // 收到进度更新，关闭加载状态
        // 更新销售列表
        currentSales: data.processing_sales || [],
        pendingSales: data.pending_sales || []
      })

      // 同步更新到 progressTaskStore
      if (data.batch_id) {
        useProgressTaskStore.getState().updateTask(data.batch_id, {
          total: data.total,
          completed: data.completed,
          failed: data.failed,
          status: data.status
        })
      }
    })

    wsClient.on('log', (data) => {
      set(state => {
        const logs = [{ ...data, id: Date.now() }, ...state.logs].slice(0, state.maxLogs)
        return { logs }
      })
    })

    wsClient.on('completed', (data) => {
      set({
        status: 'completed',
        total: data.total,
        completed: data.completed,
        failed: data.failed,
        currentSales: [],
        pendingSales: []
      })

      // 同步更新到 progressTaskStore
      if (get().batchId) {
        useProgressTaskStore.getState().updateTask(get().batchId, {
          status: 'completed',
          total: data.total,
          completed: data.completed,
          failed: data.failed
        })
      }
    })
  },

  // 断开 WebSocket
  disconnectWebSocket: () => {
    wsClient.disconnect()
  },

  // 开始生成
  startGeneration: async (params, taskName) => {
    try {
      const response = await reportApi.generate(params)
      // 适配新的返回格式
      const data = response.data || response
      const displayName = taskName ? `${taskName}_${params.time}` : `${params.task_id}_${params.time}`

      set({
        batchId: data.batch_id,
        taskId: data.task_id,
        taskName: taskName || data.task_name || params.task_id,
        reportTime: params.time,
        status: 'running',
        total: data.total_count,
        completed: 0,
        failed: 0,
        inProgress: 0,
        logs: [],
        currentSales: [],
        pendingSales: [],
        startTime: new Date().toISOString()
      })

      // 添加到 progressTaskStore
      useProgressTaskStore.getState().addTask({
        batchId: data.batch_id,
        taskId: data.task_id,
        taskName: taskName || data.task_name || params.task_id,
        reportTime: params.time,
        displayName: displayName,
        status: 'running',
        startTime: new Date().toISOString(),
        total: data.total_count,
        completed: 0,
        failed: 0
      })

      return data
    } catch (error) {
      console.error('启动生成失败:', error)
      throw error
    }
  },

  // 恢复生成
  resumeGeneration: async () => {
    try {
      // 先设置加载状态
      set({ isLoading: true })

      const response = await reportApi.resume()
      const data = response.data || response
      set({
        batchId: data.batch_id,
        taskId: data.task_id,
        status: 'running',
        total: data.total_count,
        paused: 0,  // 重置暂停数量
        isLoading: false,  // API 返回后关闭加载
        logs: [],
        startTime: new Date().toISOString()
      })
      return data
    } catch (error) {
      console.error('恢复生成失败:', error)
      set({ isLoading: false })  // 失败时关闭加载
      throw error
    }
  },

  // 暂停任务
  pauseTask: async () => {
    try {
      const response = await reportApi.pause()
      const data = response.data || response

      // 更新本地状态
      set(state => {
        // 将当前正在处理的销售状态改为"暂停中"
        const pausedSales = state.currentSales.map(sale => ({
          ...sale,
          stage: '暂停中'
        }))

        return {
          status: 'paused',
          inProgress: 0,
          paused: data.paused || state.inProgress,
          currentSales: pausedSales
        }
      })
    } catch (error) {
      console.error('暂停任务失败:', error)
    }
  },

  // 获取状态
  fetchStatus: async () => {
    try {
      const response = await reportApi.getStatus()
      const status = response.data || response
      set({
        batchId: status.batch_id,
        taskId: status.task_id,
        taskName: status.task_name,
        reportTime: status.report_time,
        status: status.status,
        total: status.total,
        completed: status.completed,
        failed: status.failed,
        inProgress: status.in_progress,
        paused: status.paused || 0,
        startTime: status.start_time,
        // 更新销售列表
        currentSales: status.processing_sales || [],
        pendingSales: status.pending_sales || []
      })
    } catch (error) {
      console.error('获取状态失败:', error)
    }
  },

  // 清除日志
  clearLogs: () => {
    set({ logs: [] })
  },

  // 清除状态
  clearStatus: async () => {
    try {
      await reportApi.clearStatus()
      // 重置本地状态
      set({
        batchId: null,
        taskId: null,
        taskName: null,
        reportTime: null,
        status: 'idle',
        total: 0,
        completed: 0,
        failed: 0,
        inProgress: 0,
        paused: 0,
        isLoading: false,
        currentSales: [],
        pendingSales: [],
        logs: [],
        startTime: null
      })
    } catch (error) {
      console.error('清除状态失败:', error)
      throw error
    }
  },

  // 重置状态
  reset: () => {
    set({
      batchId: null,
      taskId: null,
      taskName: null,
      reportTime: null,
      status: 'idle',
      total: 0,
      completed: 0,
      failed: 0,
      inProgress: 0,
      paused: 0,
      isLoading: false,
      currentSales: [],
      pendingSales: [],
      logs: [],
      startTime: null
    })
  }
}))