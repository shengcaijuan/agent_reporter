// 工具函数配置页面（支持任务选择）
import { useState, useEffect } from 'react'
import {
  Tabs, Table, Button, Modal, Form, Input, Select, Card, Space, Tag, message, Spin, Steps
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SaveOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined
} from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import useTaskStore from '../../stores/taskStore'
import { taskApi } from '../../api/task'

const { TextArea } = Input
const { Option } = Select

// 归因类型映射
const ATTR_TYPE_MAP = {
  contribution: '贡献度归因',
  variation: '变异度归因',
  threshold: '阈值归因'
}

function ToolAgentConfig() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const taskId = searchParams.get('task_id')

  const { tasks, currentTask, fetchTasks, fetchTask } = useTaskStore()

  const [chapters, setChapters] = useState([])
  const [currentChapter, setCurrentChapter] = useState(2) // 默认第2章，因为工具配置从第2章开始
  const [toolConfigs, setToolConfigs] = useState([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingTool, setEditingTool] = useState(null)

  const [form] = Form.useForm()
  const [indicatorsForm] = Form.useForm()

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  useEffect(() => {
    if (taskId) {
      loadTaskData()
    }
  }, [taskId])

  useEffect(() => {
    if (taskId && currentChapter) {
      loadToolConfigs()
    }
  }, [taskId, currentChapter])

  const loadTaskData = async () => {
    setLoading(true)
    try {
      // 加载任务信息
      if (!currentTask || currentTask.task_id !== taskId) {
        await fetchTask(taskId)
      }

      // 加载章节列表
      const chaptersRes = await taskApi.getChapters(taskId)
      setChapters(chaptersRes.data || [])
    } catch (error) {
      message.error('加载数据失败: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const loadToolConfigs = async () => {
    if (!taskId) return
    setLoading(true)
    try {
      const response = await taskApi.getToolConfigs(taskId, currentChapter)
      setToolConfigs(response.data || [])
    } catch (error) {
      console.error('加载工具配置失败:', error)
      setToolConfigs([])
    } finally {
      setLoading(false)
    }
  }

  // 章节选项卡（工具配置从第2章开始到第5章）
  const tabItems = chapters
    .filter(ch => ch.chapter_id >= 2 && ch.chapter_id <= 5)
    .map(ch => ({
      key: ch.chapter_id.toString(),
      label: `第${ch.chapter_id}章 ${ch.chapter_name}`
    }))

  // 切换章节
  const handleTabChange = (key) => {
    setCurrentChapter(parseInt(key))
  }

  // 任务选择变更
  const handleTaskChange = (newTaskId) => {
    navigate(`/config/tool?task_id=${newTaskId}`)
  }

  // 打开编辑弹窗
  const handleEdit = (record) => {
    setEditingTool(record)
    form.setFieldsValue({
      tool_name: record.tool_name,
      tool_description: record.tool_description,
      attr_type: record.attr_type
    })

    // 根据归因类型设置指标配置
    if (record.attr_type === 'contribution') {
      indicatorsForm.setFieldsValue({
        parent_indicator: record.indicators_config?.parent_indicator,
        dimension: record.indicators_config?.dimension,
        relation_type: record.indicators_config?.relation_type,
        child_indicators: Array.isArray(record.indicators_config?.child_indicators)
          ? record.indicators_config.child_indicators.join('\n')
          : record.indicators_config?.child_indicators
      })
    } else if (record.attr_type === 'variation') {
      indicatorsForm.setFieldsValue({
        indicators: Array.isArray(record.indicators_config?.indicators)
          ? record.indicators_config.indicators.join('\n')
          : record.indicators_config?.indicators
      })
    } else if (record.attr_type === 'threshold') {
      indicatorsForm.setFieldsValue({
        indicators_config: typeof record.indicators_config === 'string'
          ? record.indicators_config
          : JSON.stringify(record.indicators_config, null, 2)
      })
    }

    setModalVisible(true)
  }

  // 打开新建弹窗
  const handleCreate = () => {
    setEditingTool(null)
    form.resetFields()
    indicatorsForm.resetFields()
    setModalVisible(true)
  }

  // 保存工具配置
  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      const indicators = await indicatorsForm.validateFields()

      // 处理指标配置
      let indicatorsConfig = {}
      if (values.attr_type === 'contribution') {
        indicatorsConfig = {
          parent_indicator: indicators.parent_indicator,
          dimension: indicators.dimension,
          relation_type: indicators.relation_type,
          child_indicators: indicators.child_indicators?.split('\n').filter(Boolean) || []
        }
      } else if (values.attr_type === 'variation') {
        indicatorsConfig = {
          indicators: indicators.indicators?.split('\n').filter(Boolean) || []
        }
      } else if (values.attr_type === 'threshold') {
        try {
          indicatorsConfig = JSON.parse(indicators.indicators_config || '[]')
        } catch {
          message.error('指标配置JSON格式错误')
          return
        }
      }

      const config = {
        ...values,
        indicators_config: indicatorsConfig,
        class_name_root: values.tool_name // 使用工具名作为类名前缀
      }

      setSaving(true)
      if (editingTool) {
        await taskApi.updateToolConfig(taskId, currentChapter, editingTool.tool_id, config)
        message.success('更新成功')
      } else {
        await taskApi.createToolConfig(taskId, currentChapter, config)
        message.success('创建成功')
      }

      setModalVisible(false)
      loadToolConfigs()
    } catch (error) {
      if (!error.errorFields) {
        message.error('操作失败: ' + error.message)
      }
    } finally {
      setSaving(false)
    }
  }

  // 删除工具配置
  const handleDelete = async (toolId) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除该工具配置吗？',
      okText: '删除',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          await taskApi.deleteToolConfig(taskId, currentChapter, toolId)
          message.success('删除成功')
          loadToolConfigs()
        } catch (error) {
          message.error('删除失败: ' + error.message)
        }
      }
    })
  }

  const handlePrev = () => {
    navigate(`/config/chapter?task_id=${taskId}`)
  }

  const handleFinish = () => {
    message.success('配置完成')
    navigate('/config/tasks')
  }

  // 表格列定义
  const columns = [
    {
      title: '#',
      key: 'index',
      width: 50,
      render: (_, __, index) => index + 1
    },
    {
      title: '工具名称',
      dataIndex: 'tool_name',
      key: 'tool_name',
      ellipsis: true
    },
    {
      title: '工具描述',
      dataIndex: 'tool_description',
      key: 'tool_description',
      ellipsis: true
    },
    {
      title: '归因类型',
      dataIndex: 'attr_type',
      key: 'attr_type',
      render: (type) => (
        <Tag color={type === 'contribution' ? 'green' : type === 'threshold' ? 'blue' : 'orange'}>
          {ATTR_TYPE_MAP[type] || type}
        </Tag>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.tool_id)}
          >
            删除
          </Button>
        </Space>
      )
    }
  ]

  // 根据归因类型渲染指标配置表单
  const renderIndicatorsForm = () => {
    const attrType = form.getFieldValue('attr_type')

    if (attrType === 'contribution') {
      return (
        <Card title="指标配置（贡献度归因）" size="small">
          <Form.Item name="parent_indicator" label="父指标">
            <Input placeholder="如：收入" />
          </Form.Item>
          <Form.Item name="dimension" label="分析维度">
            <Input placeholder="如：核心产品分类维度" />
          </Form.Item>
          <Form.Item name="relation_type" label="关系类型">
            <Select placeholder="选择关系类型">
              <Option value="additive">加法分解</Option>
              <Option value="multiplicative">乘法分解</Option>
            </Select>
          </Form.Item>
          <Form.Item name="child_indicators" label="子指标列表">
            <TextArea
              rows={4}
              placeholder="每行一个子指标，如：&#10;多彩涂料产品&#10;其他外墙产品&#10;真石质感产品"
            />
          </Form.Item>
        </Card>
      )
    }

    if (attrType === 'variation') {
      return (
        <Card title="指标配置（变异度归因）" size="small">
          <Form.Item name="indicators" label="分析指标列表">
            <TextArea
              rows={6}
              placeholder="每行一个指标，如：&#10;多彩涂料产品销售量&#10;其他外墙产品销售量"
            />
          </Form.Item>
        </Card>
      )
    }

    if (attrType === 'threshold') {
      return (
        <Card title="指标配置（阈值归因）" size="small">
          <Form.Item name="indicators_config" label="指标配置（JSON格式）">
            <TextArea
              rows={8}
              placeholder='[{"indicator": "高值品收入", "threshold_type": "TARGET_ACHIEVEMENT", "baseline": "高值品收入目标"}]'
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>
        </Card>
      )
    }

    return null
  }

  if (!taskId) {
    return (
      <div className="page-card">
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <p>请先选择一个任务</p>
          <Select
            placeholder="选择任务"
            style={{ width: 300 }}
            onChange={handleTaskChange}
            options={tasks.map(t => ({
              value: t.task_id,
              label: t.task_name
            }))}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="page-card">
      <div className="page-title">
        <span>工具函数配置 - {currentTask?.task_name || taskId}</span>
        <Select
          value={taskId}
          style={{ width: 250, marginLeft: 16 }}
          onChange={handleTaskChange}
          options={tasks.map(t => ({
            value: t.task_id,
            label: t.task_name
          }))}
        />
      </div>

      {/* 配置步骤指引 */}
      <Card style={{ marginBottom: 24 }}>
        <Steps
          current={3}
          items={[
            { title: '新建任务', description: '创建报告任务' },
            { title: '报告介绍', description: '配置共享内容' },
            { title: '章节配置', description: '配置分析要求' },
            { title: '工具配置', description: '配置工具函数' },
          ]}
        />
      </Card>

      <Tabs
        activeKey={currentChapter.toString()}
        items={tabItems}
        onChange={handleTabChange}
        className="chapter-tabs"
      />

      <Spin spinning={loading}>
        <div style={{ marginBottom: 16, marginTop: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            添加新工具
          </Button>
        </div>

        <Table
          className="tool-config-table"
          columns={columns}
          dataSource={toolConfigs}
          rowKey="tool_id"
          pagination={false}
        />
      </Spin>

      {/* 编辑弹窗 */}
      <Modal
        title={editingTool ? '编辑工具配置' : '添加工具配置'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        width={700}
        footer={[
          <Button key="cancel" onClick={() => setModalVisible(false)}>
            取消
          </Button>,
          <Button key="save" type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
            保存
          </Button>
        ]}
      >
        <Form form={form} layout="vertical">
          <Card title="基本信息" size="small" style={{ marginBottom: 16 }}>
            <Form.Item
              name="tool_name"
              label="工具名称"
              rules={[{ required: true, message: '请输入工具名称' }]}
            >
              <Input placeholder="如：income_core_product_dim_analysis_tool" />
            </Form.Item>
            <Form.Item name="tool_description" label="工具描述">
              <Input placeholder="如：归因分析收入指标核心产品分类维度情况" />
            </Form.Item>
            <Form.Item
              name="attr_type"
              label="归因类型"
              rules={[{ required: true, message: '请选择归因类型' }]}
            >
              <Select placeholder="选择归因类型">
                <Option value="contribution">贡献度归因</Option>
                <Option value="variation">变异度归因</Option>
                <Option value="threshold">阈值归因</Option>
              </Select>
            </Form.Item>
          </Card>
        </Form>

        <Form form={indicatorsForm} layout="vertical">
          {renderIndicatorsForm()}
        </Form>
      </Modal>

      {/* 操作按钮 */}
      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={handlePrev}
          style={{ marginRight: 8 }}
        >
          上一步：章节配置
        </Button>
        <Button
          type="primary"
          onClick={handleFinish}
        >
          完成配置
        </Button>
      </div>
    </div>
  )
}

export default ToolAgentConfig