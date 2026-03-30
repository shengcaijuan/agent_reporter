// 进度监控页面
import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Card, Progress, Button, Tag, Empty, Space, Statistic, Row, Col, Modal, message } from 'antd'
import {
  PauseOutlined,
  FolderOutlined,
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  SaveOutlined,
  InboxOutlined
} from '@ant-design/icons'
import { useProgressStore } from '../../stores/progressStore'
import { useProgressTaskStore } from '../../stores/progressTaskStore'

function ProgressMonitor() {
  const navigate = useNavigate()
  const { batchId } = useParams() // 获取 URL 中的 batchId 参数

  const {
    taskId,
    taskName,
    reportTime,
    status,
    total,
    completed,
    failed,
    inProgress,
    paused,
    isLoading,
    currentSales,
    pendingSales,
    initWebSocket,
    disconnectWebSocket,
    pauseTask,
    resumeGeneration,
    fetchStatus,
    reset,
    clearStatus
  } = useProgressStore()

  const {
    activeTasks,
    completedTasks,
    getTask,
    removeTask
  } = useProgressTaskStore()

  const [autoRefresh, setAutoRefresh] = useState(true)

  // 获取当前要显示的任务
  const currentTask = batchId ? getTask(batchId) : null

  // 判断是否有任务：优先检查 progressStore 的实时状态，再检查历史任务
  const hasRunningTask = status === 'running' || status === 'paused' || batchId
  const hasAnyTask = activeTasks.length > 0 || completedTasks.length > 0 || hasRunningTask

  useEffect(() => {
    initWebSocket()
    fetchStatus()

    return () => {
      disconnectWebSocket()
    }
  }, [])

  // 定时刷新状态
  useEffect(() => {
    if (!autoRefresh || status !== 'running') return

    const timer = setInterval(() => {
      fetchStatus()
    }, 5000)

    return () => clearInterval(timer)
  }, [autoRefresh, status])

  // 删除任务
  const handleDeleteTask = () => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除此任务记录吗？删除后无法恢复。',
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        if (batchId) {
          try {
            // 从本地存储删除任务
            removeTask(batchId)
            // 清除后端和前端状态
            await clearStatus()
            message.success('任务已删除')
            navigate('/progress')
          } catch (error) {
            console.error('删除任务失败:', error)
            message.error('删除任务失败')
          }
        }
      }
    })
  }

  // 保留任务（从已完成移动到保留区）
  const handleKeepTask = () => {
    message.success('任务已保留')
  }

  // 计算进度百分比
  const progressPercent = total > 0 ? Math.round((completed / total) * 100) : 0

  // 渲染当前正在处理的销售
  const renderCurrentSales = () => {
    // 恢复时显示加载动画：正在加载 或 状态是running但还没有处理中的任务
    if (isLoading || (status === 'running' && inProgress === 0)) {
      return (
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <SyncOutlined spin style={{ fontSize: 32, color: '#1890ff', marginBottom: 16 }} />
          <div style={{ color: '#8c8c8c', fontSize: 14 }}>正在恢复任务...</div>
        </div>
      )
    }

    if (currentSales.length === 0) {
      return <Empty description="暂无正在处理的销售" />
    }

    return (
      <div>
        {currentSales.map((sale, index) => {
          const isPaused = sale.stage === '暂停中'
          return (
            <div
              key={index}
              style={{
                padding: '12px',
                background: isPaused ? '#fffbe6' : '#f5f5f5',
                marginBottom: 8,
                borderRadius: 4,
                border: isPaused ? '1px solid #ffe58f' : 'none'
              }}
            >
              <Space>
                {isPaused ? (
                  <PauseOutlined style={{ color: '#faad14' }} />
                ) : (
                  <PlayCircleOutlined style={{ color: '#1890ff' }} />
                )}
                <strong>{sale.sale_name || sale.name}</strong>
                {sale.province && <Tag color="blue">{sale.province}</Tag>}
                <span style={{ color: isPaused ? '#faad14' : '#52c41a' }}>
                  {sale.stage || '生成中'}
                </span>
              </Space>
            </div>
          )
        })}
      </div>
    )
  }

  // 渲染等待处理的销售
  const renderPendingSales = () => {
    if (pendingSales.length === 0) {
      return <Empty description="暂无等待处理的销售" />
    }

    return (
      <div>
        {pendingSales.slice(0, 20).map((sale, index) => (
          <div
            key={index}
            style={{
              padding: '10px',
              background: '#fafafa',
              marginBottom: 6,
              borderRadius: 4,
              fontSize: '13px'
            }}
          >
            <Space>
              <ClockCircleOutlined style={{ color: '#8c8c8c' }} />
              <span>{sale.sale_name || sale.name}</span>
              {sale.province && <Tag style={{ fontSize: '11px' }}>{sale.province}</Tag>}
            </Space>
          </div>
        ))}
        {pendingSales.length > 20 && (
          <div style={{ textAlign: 'center', color: '#8c8c8c', padding: 8 }}>
            还有 {pendingSales.length - 20} 个销售等待处理...
          </div>
        )}
      </div>
    )
  }

  // 渲染无任务状态
  const renderEmptyState = () => (
    <div className="page-card">
      <div className="page-title">进度监控</div>
      <Card>
        <Empty
          image={<InboxOutlined style={{ fontSize: 80, color: '#d9d9d9' }} />}
          description={
            <span style={{ fontSize: 16, color: '#8c8c8c' }}>
              无报告任务进行
            </span>
          }
        >
          <Button type="primary" onClick={() => navigate('/generation')}>
            前往生成报告
          </Button>
        </Empty>
      </Card>
    </div>
  )

  // 如果没有任务且没有 batchId，显示空状态
  if (!batchId && !hasAnyTask) {
    return renderEmptyState()
  }

  // 如果有 batchId 但任务不存在，显示提示
  if (batchId && !currentTask) {
    return (
      <div className="page-card">
        <div className="page-title">进度监控</div>
        <Card>
          <Empty
            description="任务不存在或已被删除"
          >
            <Button onClick={() => navigate('/progress')}>
              返回进度监控
            </Button>
          </Empty>
        </Card>
      </div>
    )
  }

  return (
    <div>
      <div className="page-card">
        <div className="page-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>进度监控</span>
          <Space>
            <Tag color={
              status === 'running' ? 'processing' :
              status === 'completed' ? 'success' :
              status === 'paused' ? 'warning' :
              status === 'error' ? 'error' : 'default'
            }>
              {status === 'running' ? '进行中' :
               status === 'completed' ? '已完成' :
               status === 'paused' ? '已暂停' :
               status === 'error' ? '出错' : '空闲'}
            </Tag>
            {taskName && <span>{taskName}</span>}
            {reportTime && <span>月份: {reportTime}</span>}
          </Space>
        </div>

        <Row gutter={24} style={{ marginBottom: 24 }}>
          <Col span={12}>
            <Card>
              <div style={{ textAlign: 'center' }}>
                <Progress
                  type="circle"
                  percent={progressPercent}
                  status={status === 'running' ? 'active' : status === 'completed' ? 'success' : 'normal'}
                />
                <div style={{ marginTop: 16, fontSize: 16 }}>
                  {completed} / {total}
                </div>
              </div>
            </Card>
          </Col>
          <Col span={12}>
            <Card>
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="已完成"
                    value={completed}
                    prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="失败"
                    value={failed}
                    prefix={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Col>
              </Row>
              <Row gutter={16} style={{ marginTop: 24 }}>
                <Col span={8}>
                  <Statistic
                    title="进行中"
                    value={inProgress}
                    prefix={<SyncOutlined style={{ color: '#1890ff' }} spin={inProgress > 0} />}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="暂停"
                    value={paused}
                    prefix={<PauseOutlined style={{ color: '#faad14' }} />}
                    valueStyle={{ color: paused > 0 ? '#faad14' : undefined }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="等待中"
                    value={Math.max(0, total - completed - failed - inProgress - paused)}
                    prefix={<ClockCircleOutlined style={{ color: '#8c8c8c' }} />}
                  />
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>

        <div style={{ marginBottom: 16 }}>
          <Space>
            {/* 任务完成后的操作按钮 */}
            {status === 'completed' && batchId && (
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleKeepTask}
              >
                保留任务
              </Button>
            )}
            {/* 非运行状态时显示删除按钮 */}
            {status !== 'running' && inProgress === 0 && batchId && (
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={handleDeleteTask}
              >
                删除任务
              </Button>
            )}
            {/* 暂停状态时显示恢复按钮 */}
            {status === 'paused' && (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={resumeGeneration}
              >
                恢复任务
              </Button>
            )}
            {/* 运行中的操作按钮 */}
            {status === 'running' && (
              <Button
                icon={<PauseOutlined />}
                onClick={pauseTask}
              >
                暂停任务
              </Button>
            )}
            <Button
              icon={<FolderOutlined />}
              onClick={() => navigate('/reports')}
            >
              查看已完成报告
            </Button>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/generation')}
            >
              返回生成页
            </Button>
          </Space>
        </div>
      </div>

      <Row gutter={16}>
        <Col span={12}>
          <Card
            title={
              <Space>
                {status === 'paused' ? (
                  <PauseOutlined style={{ color: '#faad14' }} />
                ) : (
                  <PlayCircleOutlined style={{ color: '#1890ff' }} />
                )}
                <span>{status === 'paused' ? '已暂停的销售' : '当前正在处理的销售'}</span>
                <Tag color={status === 'paused' ? 'warning' : 'processing'}>{currentSales.length}</Tag>
              </Space>
            }
            style={{ height: 400, overflow: 'auto' }}
          >
            {renderCurrentSales()}
          </Card>
        </Col>
        <Col span={12}>
          <Card
            title={
              <Space>
                <ClockCircleOutlined style={{ color: '#8c8c8c' }} />
                <span>等待处理的销售</span>
                <Tag>{pendingSales.length}</Tag>
              </Space>
            }
            style={{ height: 400, overflow: 'auto' }}
          >
            {renderPendingSales()}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default ProgressMonitor