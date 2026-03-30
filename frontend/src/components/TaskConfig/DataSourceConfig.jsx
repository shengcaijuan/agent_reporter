// 数据源配置组件 - 任务级配置（选择全局数据源）
import { useState, useEffect } from 'react'
import {
  Card, Select, Button, Space, message, Spin, Alert, Tag
} from 'antd'
import {
  ApiOutlined, ReloadOutlined, SettingOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { dataSourceApi } from '../../api/dataSource'

const { Option } = Select

function DataSourceConfig({ taskId }) {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [globalDataSources, setGlobalDataSources] = useState([])
  const [selectedSourceId, setSelectedSourceId] = useState(null)
  const [currentSource, setCurrentSource] = useState(null)

  // 加载全局数据源列表和当前任务的数据源配置
  useEffect(() => {
    if (taskId) {
      loadData()
    }
  }, [taskId])

  const loadData = async () => {
    setLoading(true)
    try {
      // 并行加载全局数据源和任务数据源配置
      const [globalRes, taskRes] = await Promise.all([
        dataSourceApi.getGlobalDataSources(),
        dataSourceApi.getTaskDataSource(taskId)
      ])

      setGlobalDataSources(globalRes.data || [])
      const taskSource = taskRes.data || {}

      if (taskSource.id) {
        setSelectedSourceId(taskSource.id)
        setCurrentSource(taskSource)
      } else if (taskSource.error) {
        // 数据源已被删除
        setSelectedSourceId(null)
        setCurrentSource(null)
      }
    } catch (error) {
      message.error('加载数据源配置失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  // 选择数据源
  const handleSelectSource = async (sourceId) => {
    setSaving(true)
    try {
      await dataSourceApi.updateTaskDataSource(taskId, sourceId)
      setSelectedSourceId(sourceId)

      // 更新当前数据源信息
      const source = globalDataSources.find(s => s.id === sourceId)
      setCurrentSource(source || null)

      message.success('数据源配置已更新')
    } catch (error) {
      message.error('保存失败: ' + (error.message || '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  // 跳转到数据配置页面
  const goToDataSourcePage = () => {
    navigate('/data-sources')
  }

  if (loading) {
    return (
      <Card>
        <Spin />
      </Card>
    )
  }

  return (
    <Card
      title={
        <span>
          <ApiOutlined style={{ marginRight: 8 }} />
          数据源配置
        </span>
      }
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadData}>
            刷新
          </Button>
          <Button icon={<SettingOutlined />} onClick={goToDataSourcePage}>
            管理数据源
          </Button>
        </Space>
      }
    >
      <Alert
        message="选择此任务使用的数据源。生成报告时将按章节号、销售ID和时间从此数据源获取数据。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <div style={{ marginBottom: 16 }}>
        <span style={{ marginRight: 8 }}>数据源:</span>
        <Select
          value={selectedSourceId}
          onChange={handleSelectSource}
          style={{ width: 300 }}
          placeholder="请选择数据源"
          loading={saving}
          allowClear
        >
          {globalDataSources.map(source => (
            <Option
              key={source.id}
              value={source.id}
              disabled={source.is_active === false}
            >
              <Space>
                {source.name}
                {source.is_default && <Tag color="blue" style={{ marginLeft: 4 }}>默认</Tag>}
                {source.is_active === false && <Tag color="red">禁用</Tag>}
              </Space>
            </Option>
          ))}
        </Select>
      </div>

      {/* 显示当前数据源信息 */}
      {currentSource && (
        <Card size="small" title="当前数据源信息" style={{ background: '#fafafa' }}>
          <p><strong>名称:</strong> {currentSource.name}</p>
          {currentSource.description && <p><strong>描述:</strong> {currentSource.description}</p>}
          <p><strong>API地址:</strong> {currentSource.config?.base_url}</p>
          <p><strong>认证方式:</strong> {
            currentSource.config?.auth_type === 'url_param' ? 'URL参数' :
            currentSource.config?.auth_type === 'header' ? '请求头' :
            currentSource.config?.auth_type === 'bearer' ? 'Bearer Token' : currentSource.config?.auth_type
          }</p>
        </Card>
      )}

      {!currentSource && (
        <Alert
          message="未配置数据源"
          description={selectedSourceId ? "所选数据源已被删除，请重新选择" : "请选择一个数据源，或在「数据配置」页面添加新数据源"}
          type="warning"
          showIcon
        />
      )}

      {globalDataSources.length === 0 && (
        <Alert
          message="暂无可用数据源"
          description="请点击「管理数据源」按钮添加新的数据源"
          type="warning"
          showIcon
          style={{ marginTop: 16 }}
        />
      )}
    </Card>
  )
}

export default DataSourceConfig