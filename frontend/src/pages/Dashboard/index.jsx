// 仪表盘页面
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Button, Table, Tag, Statistic, Spin } from 'antd'
import {
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ArrowRightOutlined,
  EyeOutlined,
  ProfileOutlined
} from '@ant-design/icons'
import { reportApi } from '../../api/report'
import { taskApi } from '../../api/task'
import { useProgressStore } from '../../stores/progressStore'

function Dashboard() {
  const navigate = useNavigate()
  const { status, fetchStatus } = useProgressStore()
  const [stats, setStats] = useState({
    reportCount: 0,
    taskCount: 0,
    inProgress: 0,
    templateCount: 0
  })
  const [recentReports, setRecentReports] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      // 获取仪表盘统计数据
      const statsResult = await taskApi.getDashboardStats()
      const statsData = statsResult.data || {}
      setStats({
        reportCount: statsData.report_count || 0,
        taskCount: statsData.task_count || 0,
        inProgress: statsData.in_progress || 0,
        templateCount: statsData.template_count || 0
      })

      // 获取可用月份列表
      const timesResult = await reportApi.getAvailableTimes('mashangzhu')
      const times = timesResult.data?.times || []

      // 获取最近生成的报告（只取5个）
      let allReports = []
      for (const time of times.slice(0, 2)) { // 只查询最近两个月份
        const result = await reportApi.getGeneratedList({
          task_id: 'mashangzhu',
          report_time: time
        })
        const reports = result.data?.reports || []
        allReports = allReports.concat(reports)
        if (allReports.length >= 5) break
      }

      // 只保留前5个
      setRecentReports(allReports.slice(0, 5))
    } catch (error) {
      console.error('加载数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  // 最近任务表格列
  const columns = [
    {
      title: '工号',
      dataIndex: 'job_id',
      key: 'job_id',
      width: 80,
      render: (jobId) => <span style={{ color: '#666' }}>{jobId || '-'}</span>
    },
    {
      title: '销售姓名',
      dataIndex: 'sale_name',
      key: 'sale_name',
      width: 100,
      render: (name) => (
        <span>
          <FileTextOutlined style={{ marginRight: 8, color: '#1890ff' }} />
          {name}
        </span>
      )
    },
    {
      title: '报告月份',
      dataIndex: 'report_time',
      key: 'report_time',
      width: 90,
      render: (time) => <Tag color="blue">{time}</Tag>
    },
    {
      title: '省区',
      dataIndex: 'province',
      key: 'province',
      width: 100,
      ellipsis: true,
      render: (text) => text || '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => navigate('/reports')}
        >
          查看
        </Button>
      )
    }
  ]

  return (
    <div>
      <div className="page-card">
        <div className="page-title">仪表盘</div>

        {/* 统计卡片 */}
        <Row gutter={16}>
          <Col span={6}>
            <div className="stat-card">
              <Statistic
                title="报告数"
                value={stats.reportCount}
                prefix={<FileTextOutlined />}
                valueStyle={{ color: '#008425' }}
              />
            </div>
          </Col>
          <Col span={6}>
            <div className="stat-card">
              <Statistic
                title="任务数"
                value={stats.taskCount}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </div>
          </Col>
          <Col span={6}>
            <div className="stat-card">
              <Statistic
                title="进行中"
                value={stats.inProgress}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </div>
          </Col>
          <Col span={6}>
            <div className="stat-card">
              <Statistic
                title="报告模板"
                value={stats.templateCount}
                prefix={<ProfileOutlined />}
                valueStyle={{ color: '#722ed1' }}
              />
            </div>
          </Col>
        </Row>
      </div>

      {/* 快捷操作 */}
      <div className="page-card">
        <div className="page-title">快捷操作</div>
        <Row gutter={16}>
          <Col>
            <Button
              type="primary"
              icon={<FileTextOutlined />}
              onClick={() => navigate('/generation')}
            >
              运行报告生成任务
            </Button>
          </Col>
          <Col>
            <Button icon={<FileTextOutlined />} onClick={() => navigate('/config/task-config')}>
              配置新的报告生成任务
            </Button>
          </Col>
          <Col>
            <Button icon={<FileTextOutlined />} onClick={() => navigate('/reports')}>
              查看全部报告
            </Button>
          </Col>
        </Row>
      </div>

      {/* 最近生成任务 */}
      <div className="page-card">
        <div className="page-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>最近生成记录</span>
          <Button type="link" onClick={() => navigate('/reports')}>
            查看全部 <ArrowRightOutlined />
          </Button>
        </div>
        <Spin spinning={loading}>
          <Table
            columns={columns}
            dataSource={recentReports}
            rowKey="file_path"
            pagination={false}
            size="small"
            locale={{ emptyText: '暂无报告' }}
          />
        </Spin>
      </div>
    </div>
  )
}

export default Dashboard