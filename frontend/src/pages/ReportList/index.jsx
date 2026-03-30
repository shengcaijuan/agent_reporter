// 报告列表页面
import { useState, useEffect } from 'react'
import {
  Card, Table, Button, Select, Space, Tag, Modal, Spin, message, Input, Popconfirm, Tabs
} from 'antd'
import {
  EyeOutlined,
  ReloadOutlined,
  FileTextOutlined,
  SearchOutlined,
  DeleteOutlined,
  FileSearchOutlined
} from '@ant-design/icons'
import { reportApi } from '../../api/report'

const { Option } = Select

function ReportList() {
  const [loading, setLoading] = useState(false)
  const [reports, setReports] = useState([])
  const [total, setTotal] = useState(0)
  const [searchText, setSearchText] = useState('')
  const [availableTimes, setAvailableTimes] = useState([])
  const [filters, setFilters] = useState({
    taskId: 'mashangzhu',
    reportTime: ''
  })

  // 批量选中状态
  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const [batchDeleteLoading, setBatchDeleteLoading] = useState(false)

  // 弹窗相关状态
  const [previewVisible, setPreviewVisible] = useState(false)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewContent, setPreviewContent] = useState('')
  const [currentReport, setCurrentReport] = useState(null)

  // 日志弹窗相关状态
  const [logVisible, setLogVisible] = useState(false)
  const [logLoading, setLogLoading] = useState(false)
  const [logData, setLogData] = useState({ sale_name: '', logs: [] })

  useEffect(() => {
    loadAvailableTimes()
  }, [filters.taskId])

  useEffect(() => {
    if (filters.reportTime) {
      loadReports()
    }
  }, [filters.reportTime, filters.taskId])

  const loadAvailableTimes = async () => {
    try {
      const result = await reportApi.getAvailableTimes(filters.taskId)
      const times = result.data?.times || []
      setAvailableTimes(times)
      // 自动选择第一个（最新的）月份
      if (times.length > 0 && !filters.reportTime) {
        setFilters(prev => ({ ...prev, reportTime: times[0] }))
      }
    } catch (error) {
      console.error('加载可用月份失败:', error)
    }
  }

  const loadReports = async () => {
    setLoading(true)
    try {
      const result = await reportApi.getGeneratedList({
        task_id: filters.taskId,
        report_time: filters.reportTime
      })
      setReports(result.data?.reports || [])
      setTotal(result.data?.total || 0)
    } catch (error) {
      console.error('加载报告列表失败:', error)
      message.error('加载报告列表失败')
    } finally {
      setLoading(false)
    }
  }

  // 搜索过滤
  const filteredReports = reports.filter(report =>
    report.sale_name?.includes(searchText) ||
    report.job_id?.includes(searchText) ||
    report.region?.includes(searchText) ||
    report.province?.includes(searchText)
  )

  // 阅览报告
  const handlePreview = async (record) => {
    setCurrentReport(record)
    setPreviewVisible(true)
    setPreviewLoading(true)
    setPreviewContent('')

    try {
      const result = await reportApi.getGeneratedContent({
        file_path: record.file_path,
        task_id: filters.taskId,
        report_time: filters.reportTime
      })
      setPreviewContent(result.data?.html_content || '')
    } catch (error) {
      console.error('加载报告内容失败:', error)
      message.error('加载报告内容失败')
      setPreviewContent('<p style="color: red;">加载报告内容失败</p>')
    } finally {
      setPreviewLoading(false)
    }
  }

  // 关闭弹窗
  const handlePreviewClose = () => {
    setPreviewVisible(false)
    setPreviewContent('')
    setCurrentReport(null)
  }

  // 查看日志
  const handleViewLog = async (record) => {
    setCurrentReport(record)
    setLogVisible(true)
    setLogLoading(true)
    setLogData({ sale_name: '', logs: [] })

    try {
      const result = await reportApi.getLogs({
        file_path: record.file_path,
        task_id: filters.taskId,
        report_time: filters.reportTime
      })
      setLogData(result.data || { sale_name: record.sale_name, logs: [] })
    } catch (error) {
      console.error('加载日志失败:', error)
      // 显示详细错误信息
      const errorMsg = error?.detail || error?.message || '加载日志失败'
      message.error(errorMsg)
      setLogData({ sale_name: record.sale_name, logs: [{ name: '错误', content: errorMsg }] })
    } finally {
      setLogLoading(false)
    }
  }

  // 关闭日志弹窗
  const handleLogClose = () => {
    setLogVisible(false)
    setLogData({ sale_name: '', logs: [] })
  }

  // 删除报告
  const handleDelete = async (record) => {
    try {
      const result = await reportApi.deleteGenerated({
        file_path: record.file_path,
        task_id: filters.taskId,
        report_time: filters.reportTime
      })
      if (result.success) {
        message.success(result.message || '删除成功')
        // 刷新列表
        loadReports()
      } else {
        message.error(result.message || '删除失败')
      }
    } catch (error) {
      console.error('删除报告失败:', error)
      message.error(error.response?.data?.detail || '删除失败')
    }
  }

  // 批量删除报告
  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要删除的报告')
      return
    }

    setBatchDeleteLoading(true)
    try {
      const result = await reportApi.batchDeleteGenerated({
        file_paths: selectedRowKeys,
        task_id: filters.taskId,
        report_time: filters.reportTime
      })
      if (result.success) {
        message.success(result.message || '批量删除成功')
        setSelectedRowKeys([])
        // 刷新列表
        loadReports()
      } else {
        message.error(result.message || '批量删除失败')
      }
    } catch (error) {
      console.error('批量删除报告失败:', error)
      message.error(error.response?.data?.detail || '批量删除失败')
    } finally {
      setBatchDeleteLoading(false)
    }
  }

  // 表格行选择配置
  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys) => {
      setSelectedRowKeys(newSelectedRowKeys)
    },
    selections: [
      Table.SELECTION_ALL,
      Table.SELECTION_INVERT,
      Table.SELECTION_NONE,
    ],
  }

  // 表格列定义
  const columns = [
    {
      title: '序号',
      key: 'index',
      width: 60,
      fixed: 'left',
      render: (_, __, index) => index + 1
    },
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
      fixed: 'left',
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
      title: '事业部',
      dataIndex: 'business_department',
      key: 'business_department',
      width: 140,
      ellipsis: true
    },
    {
      title: '大区',
      dataIndex: 'region',
      key: 'region',
      width: 100,
      ellipsis: true,
      render: (text) => text || '-'
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
      title: '城市经营部',
      dataIndex: 'city_operation_department',
      key: 'city_operation_department',
      width: 120,
      ellipsis: true,
      render: (text) => text || '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="primary"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record)}
          >
            阅览
          </Button>
          <Button
            size="small"
            icon={<FileSearchOutlined />}
            onClick={() => handleViewLog(record)}
          >
            日志
          </Button>
          <Popconfirm
            title="确认删除"
            description={`确定要删除【${record.sale_name}】的报告吗？此操作将删除该销售的所有报告文件。`}
            onConfirm={() => handleDelete(record)}
            okText="确定"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button
              danger
              size="small"
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <div className="page-card">
      <div className="page-title">已生成报告列表</div>

      {/* 筛选条件 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <span>报告任务:</span>
          <Select
            value={filters.taskId}
            onChange={(value) => setFilters({ ...filters, taskId: value })}
            style={{ width: 200 }}
          >
            <Option value="mashangzhu">马上住焕新事业部</Option>
          </Select>
          <span>报告月份:</span>
          <Select
            value={filters.reportTime}
            onChange={(value) => setFilters({ ...filters, reportTime: value })}
            style={{ width: 120 }}
            placeholder="选择月份"
          >
            {availableTimes.map(time => (
              <Option key={time} value={time}>{time}</Option>
            ))}
          </Select>
          <span>姓名/工号:</span>
          <Input
            placeholder="搜索姓名/工号"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 140 }}
            prefix={<SearchOutlined />}
            allowClear
          />
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={loadReports}
          >
            刷新
          </Button>
          {selectedRowKeys.length > 0 && (
            <Popconfirm
              title="确认批量删除"
              description={`确定要删除选中的 ${selectedRowKeys.length} 份报告吗？此操作将删除对应销售的所有报告文件。`}
              onConfirm={handleBatchDelete}
              okText="确定"
              cancelText="取消"
              okButtonProps={{ danger: true, loading: batchDeleteLoading }}
            >
              <Button
                danger
                icon={<DeleteOutlined />}
                loading={batchDeleteLoading}
              >
                批量删除 ({selectedRowKeys.length})
              </Button>
            </Popconfirm>
          )}
        </Space>
      </Card>

      {/* 统计信息 */}
      <Card size="small" style={{ marginBottom: 16, background: '#f6ffed' }}>
        <Space>
          <span>共 <strong style={{ color: '#52c41a' }}>{total}</strong> 份报告</span>
          {searchText && (
            <span>，筛选后 <strong style={{ color: '#1890ff' }}>{filteredReports.length}</strong> 份</span>
          )}
        </Space>
      </Card>

      {/* 表格 */}
      <Table
        columns={columns}
        dataSource={filteredReports}
        rowKey="file_path"
        loading={loading}
        scroll={{ x: 1000 }}
        rowSelection={rowSelection}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`
        }}
      />

      {/* 报告预览弹窗 */}
      <Modal
        title={
          <span>
            <FileTextOutlined style={{ marginRight: 8 }} />
            报告预览 - {currentReport?.sale_name}
          </span>
        }
        open={previewVisible}
        onCancel={handlePreviewClose}
        footer={null}
        width={1000}
        centered
        bodyStyle={{
          height: '80vh',
          overflow: 'auto',
          padding: 0
        }}
      >
        {previewLoading ? (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%'
          }}>
            <Spin size="large" tip="加载中..." />
          </div>
        ) : (
          <div
            style={{ padding: 16 }}
            dangerouslySetInnerHTML={{ __html: previewContent }}
          />
        )}
      </Modal>

      {/* 日志弹窗 */}
      <Modal
        title={
          <span>
            <FileSearchOutlined style={{ marginRight: 8 }} />
            生成日志 - {logData.sale_name || currentReport?.sale_name}
          </span>
        }
        open={logVisible}
        onCancel={handleLogClose}
        footer={null}
        width={1200}
        centered
        bodyStyle={{
          height: '80vh',
          overflow: 'hidden',
          padding: 0
        }}
      >
        {logLoading ? (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%'
          }}>
            <Spin size="large" tip="加载日志中..." />
          </div>
        ) : logData.logs.length === 0 ? (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%',
            color: '#999'
          }}>
            暂无日志
          </div>
        ) : logData.logs.length === 1 ? (
          // 单个日志文件，直接显示
          <div style={{
            height: '100%',
            overflow: 'auto',
            padding: 16,
            background: '#1e1e1e',
            color: '#d4d4d4',
            fontFamily: 'Consolas, Monaco, "Courier New", monospace',
            fontSize: 12,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all'
          }}>
            {logData.logs[0].content || '(空)'}
          </div>
        ) : (
          // 多个日志文件，使用 Tabs 切换
          <Tabs
            defaultActiveKey="0"
            style={{ height: '100%' }}
            tabBarStyle={{ padding: '0 16px', marginBottom: 0 }}
            items={logData.logs.map((log, index) => ({
              key: String(index),
              label: log.name,
              children: (
                <div style={{
                  height: 'calc(80vh - 46px)',
                  overflow: 'auto',
                  padding: 16,
                  background: '#1e1e1e',
                  color: '#d4d4d4',
                  fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                  fontSize: 12,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all'
                }}>
                  {log.content || '(空)'}
                </div>
              )
            }))}
          />
        )}
      </Modal>
    </div>
  )
}

export default ReportList