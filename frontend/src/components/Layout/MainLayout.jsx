// 主布局组件
import { useState, useEffect, useRef, useCallback } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Dropdown, Avatar, Button, Spin } from 'antd'
import {
  DashboardOutlined,
  SettingOutlined,
  FileTextOutlined,
  LineChartOutlined,
  FolderOutlined,
  UserOutlined,
  LogoutOutlined,
  PlusOutlined,
  FolderOpenOutlined,
  CloudServerOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  FormatPainterOutlined
} from '@ant-design/icons'
import { useAuthStore } from '../../stores/authStore'
import useTaskStore from '../../stores/taskStore'
import { useProgressTaskStore } from '../../stores/progressTaskStore'

const { Header, Sider, Content } = Layout

// 侧边栏宽度范围
const MIN_SIDER_WIDTH = 150
const MAX_SIDER_WIDTH = 400
const DEFAULT_SIDER_WIDTH = 220

// 根据任务状态返回图标
const getTaskStatusIcon = (status) => {
  switch (status) {
    case 'running':
      return <SyncOutlined spin style={{ color: '#1890ff' }} />
    case 'paused':
      return <PauseCircleOutlined style={{ color: '#faad14' }} />
    case 'completed':
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />
    default:
      return <LineChartOutlined />
  }
}

function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { username, logout } = useAuthStore()
  const { tasks, loading, fetchTasks } = useTaskStore()
  const { activeTasks, completedTasks } = useProgressTaskStore()
  const [collapsed, setCollapsed] = useState(false)

  // 可调整宽度的侧边栏
  const [siderWidth, setSiderWidth] = useState(DEFAULT_SIDER_WIDTH)
  const [isResizing, setIsResizing] = useState(false)
  const siderRef = useRef(null)

  // 获取任务列表
  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  // 处理拖拽调整宽度
  const handleMouseDown = useCallback((e) => {
    e.preventDefault()
    setIsResizing(true)
  }, [])

  const handleMouseMove = useCallback((e) => {
    if (!isResizing) return

    const newWidth = e.clientX
    if (newWidth >= MIN_SIDER_WIDTH && newWidth <= MAX_SIDER_WIDTH) {
      setSiderWidth(newWidth)
    }
  }, [isResizing])

  const handleMouseUp = useCallback(() => {
    setIsResizing(false)
  }, [])

  // 添加全局鼠标事件监听
  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizing, handleMouseMove, handleMouseUp])

  // 动态生成配置管理子菜单
  const configSubMenu = [
    {
      key: '/config/task-config',
      icon: <PlusOutlined />,
      label: '配置新报告任务'
    }
  ]

  // 添加已有的报告任务
  if (tasks && tasks.length > 0) {
    configSubMenu.push({
      type: 'divider',
      key: 'task-divider'
    })
    tasks.forEach(task => {
      configSubMenu.push({
        key: `/config/task-config?task_id=${task.task_id}`,
        icon: <FolderOpenOutlined />,
        label: task.task_name || task.business_department
      })
    })
  }

  // 动态生成进度监控子菜单
  const progressSubMenu = []

  // 添加正在运行/暂停的任务
  if (activeTasks && activeTasks.length > 0) {
    activeTasks.forEach(task => {
      progressSubMenu.push({
        key: `/progress/${task.batchId}`,
        icon: getTaskStatusIcon(task.status),
        label: task.displayName || `${task.taskName}_${task.reportTime}`
      })
    })
  }

  // 添加已完成的任务
  if (completedTasks && completedTasks.length > 0) {
    if (activeTasks && activeTasks.length > 0) {
      progressSubMenu.push({
        type: 'divider',
        key: 'completed-divider'
      })
    }
    completedTasks.forEach(task => {
      progressSubMenu.push({
        key: `/progress/${task.batchId}`,
        icon: getTaskStatusIcon('completed'),
        label: task.displayName || `${task.taskName}_${task.reportTime}`
      })
    })
  }

  // 如果没有任何任务，进度监控不显示子菜单
  const progressMenuItem = progressSubMenu.length > 0
    ? {
        key: 'progress',
        icon: <LineChartOutlined />,
        label: '进度监控',
        children: progressSubMenu
      }
    : {
        key: '/progress',
        icon: <LineChartOutlined />,
        label: '进度监控'
      }

  // 菜单项
  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '仪表盘'
    },
    {
      key: 'config',
      icon: <SettingOutlined />,
      label: '配置管理',
      children: configSubMenu
    },
    {
      key: '/generation',
      icon: <FileTextOutlined />,
      label: '报告生成'
    },
    progressMenuItem,
    {
      key: '/reports',
      icon: <FolderOutlined />,
      label: '报告列表'
    },
    {
      key: '/templates',
      icon: <FormatPainterOutlined />,
      label: '报告模板库'
    },
    {
      key: '/model-config',
      icon: <CloudServerOutlined />,
      label: '模型配置'
    }
  ]

  // 用户菜单
  const userMenuItems = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: async () => {
        await logout()
        navigate('/login')
      }
    }
  ]

  // 处理菜单点击
  const handleMenuClick = ({ key }) => {
    navigate(key)
  }

  // 获取当前选中的菜单
  const getSelectedKeys = () => {
    const path = location.pathname
    if (path === '/') return ['/']

    // 对于任务配置页面，需要包含 task_id 参数来匹配
    if (path === '/config/task-config') {
      const taskId = new URLSearchParams(location.search).get('task_id')
      if (taskId) {
        return [`/config/task-config?task_id=${taskId}`]
      }
      return ['/config/task-config']
    }

    // 对于进度监控页面，支持 batchId 参数
    if (path === '/progress') {
      const batchId = location.pathname.split('/progress/')[1]
      if (batchId) {
        return [`/progress/${batchId}`]
      }
      return ['/progress']
    }

    // 进度监控子菜单项
    if (path.startsWith('/progress/')) {
      return [path]
    }

    return [path]
  }

  // 获取展开的菜单
  const getOpenKeys = () => {
    const path = location.pathname
    if (path.startsWith('/config')) return ['config']
    if (path.startsWith('/progress')) return ['progress']
    return []
  }

  return (
    <Layout className="main-layout">
      <Sider
        ref={siderRef}
        className="main-sider"
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        width={siderWidth}
        style={{ width: collapsed ? 80 : siderWidth }}
      >
        {/* Logo 区域 */}
        <div className="sider-logo">
          <img src="/assets/logo.svg" alt="三棵树" />
          {!collapsed && <span>智能报告系统</span>}
        </div>

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={getSelectedKeys()}
          defaultOpenKeys={getOpenKeys()}
          items={menuItems}
          onClick={handleMenuClick}
        />

        {/* 拖拽调整宽度的手柄 */}
        {!collapsed && (
          <div
            className="sider-resize-handle"
            onMouseDown={handleMouseDown}
            style={{
              position: 'absolute',
              right: 0,
              top: 0,
              bottom: 0,
              width: '4px',
              cursor: 'col-resize',
              backgroundColor: isResizing ? '#1890ff' : 'transparent',
              zIndex: 100,
              transition: 'background-color 0.2s'
            }}
          />
        )}
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : siderWidth, transition: 'margin-left 0.2s' }}>
        <Header className="main-header" style={{ left: collapsed ? 80 : siderWidth, transition: 'left 0.2s' }}>
          <div className="logo">
            <img src="/assets/logo.svg" alt="三棵树" />
            <span>三棵树AI智能单兵分析报告平台</span>
          </div>
          <div className="user-info">
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Avatar icon={<UserOutlined />} style={{ backgroundColor: 'rgba(255,255,255,0.2)' }} />
                <span>{username}</span>
              </div>
            </Dropdown>
          </div>
        </Header>
        <Content className="main-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout