// 工具函数配置表格组件
import { useState, useEffect } from 'react'
import {
  Table, Button, Modal, Form, Input, Select, Card, Space, Tag, message, Divider, InputNumber
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, SaveOutlined, MinusCircleOutlined
} from '@ant-design/icons'

const { TextArea } = Input
const { Option } = Select

// 归因类型映射
const ATTR_TYPE_MAP = {
  contribution: '贡献度归因',
  variation: '变异度归因',
  threshold: '阈值归因'
}

// 阈值类型映射
const THRESHOLD_TYPE_MAP = {
  TARGET_ACHIEVEMENT: '目标达成',
  AVERAGE_DEALER_CREDIT_LIMIT_PER_HOUSEHOLD: '户均经销授信金额',
  RECEIVABLES_CONCENTRATION_RATE: '当月应收集中率',
  DUE_RECEIVABLES_COLLECTION_RATE: '当月到期回款率',
  HISTORICAL_OVERDUE_RECEIVABLES_COLLECTION_RATE: '历史逾期回款率',
  PROBABILITY_OF_OVERDUE_IN_THE_CURRENT_YEAR: '当年逾期概率',
  RATIO_OF_OVERDUE_RECEIVABLES_EXCEEDING_30_DAYS: '逾期超过30天比例'
}

function ToolConfigTable({ tools = [], onSave, loading }) {
  const [modalVisible, setModalVisible] = useState(false)
  const [editingTool, setEditingTool] = useState(null)
  const [saving, setSaving] = useState(false)
  // 追踪当前选择的归因类型，用于动态渲染表单
  const [currentAttrType, setCurrentAttrType] = useState(null)
  // 阈值类型的指标列表
  const [thresholdIndicators, setThresholdIndicators] = useState([])

  const [form] = Form.useForm()
  const [indicatorsForm] = Form.useForm()

  // 打开编辑弹窗
  const handleEdit = (record) => {
    setEditingTool(record)
    const attrType = record.attr_type
    setCurrentAttrType(attrType)

    form.setFieldsValue({
      tool_name: record.tools_config?.tool_name || record.tool_name,
      tool_description: record.tools_config?.tool_description || record.tool_description,
      attr_type: attrType,
      class_name_root: record.class_name_root
    })

    // 根据归因类型设置指标配置
    if (attrType === 'contribution') {
      indicatorsForm.setFieldsValue({
        parent_indicator: record.indicators_config?.parent_indicator,
        dimension: record.indicators_config?.dimension,
        relation_type: record.indicators_config?.relation_type,
        child_indicators: Array.isArray(record.indicators_config?.child_indicators)
          ? record.indicators_config.child_indicators.join('\n')
          : record.indicators_config?.child_indicators
      })
    } else if (attrType === 'variation') {
      indicatorsForm.setFieldsValue({
        indicators: Array.isArray(record.indicators_config)
          ? record.indicators_config.join('\n')
          : (typeof record.indicators_config === 'object' && record.indicators_config?.indicators)
            ? record.indicators_config.indicators.join('\n')
            : ''
      })
    } else if (attrType === 'threshold') {
      // 解析阈值配置
      const configList = Array.isArray(record.indicators_config)
        ? record.indicators_config
        : []
      setThresholdIndicators(configList)
    }

    setModalVisible(true)
  }

  // 打开新建弹窗
  const handleCreate = () => {
    setEditingTool(null)
    setCurrentAttrType(null)
    setThresholdIndicators([])
    form.resetFields()
    indicatorsForm.resetFields()
    setModalVisible(true)
  }

  // 归因类型变更处理
  const handleAttrTypeChange = (value) => {
    setCurrentAttrType(value)
    indicatorsForm.resetFields()
    if (value === 'threshold') {
      setThresholdIndicators([])
    }
  }

  // 添加阈值指标项
  const addThresholdIndicator = () => {
    setThresholdIndicators(prev => [...prev, { indicator: '', threshold_type: '', baseline: '' }])
  }

  // 更新阈值指标项
  const updateThresholdIndicator = (index, field, value) => {
    setThresholdIndicators(prev => {
      const newList = [...prev]
      newList[index] = { ...newList[index], [field]: value }
      return newList
    })
  }

  // 删除阈值指标项
  const removeThresholdIndicator = (index) => {
    setThresholdIndicators(prev => prev.filter((_, i) => i !== index))
  }

  // 保存工具配置
  const handleSave = async () => {
    try {
      const values = await form.validateFields()

      // 处理指标配置
      let indicatorsConfig = {}
      if (currentAttrType === 'contribution') {
        const indicators = await indicatorsForm.validateFields()
        indicatorsConfig = {
          parent_indicator: indicators.parent_indicator,
          dimension: indicators.dimension,
          relation_type: indicators.relation_type,
          child_indicators: indicators.child_indicators?.split('\n').filter(Boolean) || []
        }
      } else if (currentAttrType === 'variation') {
        const indicators = await indicatorsForm.validateFields()
        indicatorsConfig = indicators.indicators?.split('\n').filter(Boolean) || []
      } else if (currentAttrType === 'threshold') {
        // 使用状态中的阈值指标列表
        indicatorsConfig = thresholdIndicators.filter(item => item.indicator && item.threshold_type)
      }

      const config = {
        attr_type: currentAttrType,
        class_name_root: values.class_name_root,
        indicators_config: indicatorsConfig,
        tools_config: {
          tool_name: values.tool_name,
          tool_description: values.tool_description
        }
      }

      setSaving(true)
      await onSave(editingTool ? editingTool.tool_id : null, config)
      setModalVisible(false)
    } catch (error) {
      if (!error.errorFields) {
        message.error('操作失败: ' + error.message)
      }
    } finally {
      setSaving(false)
    }
  }

  // 删除工具配置
  const handleDelete = (toolId) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除该工具配置吗？',
      okText: '删除',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        const newTools = tools.filter(t => t.tool_id !== toolId)
        await onSave(null, newTools, true)
      }
    })
  }

  // 表格列定义
  const columns = [
    {
      title: '#',
      key: 'index',
      width: 40,
      render: (_, __, index) => index + 1
    },
    {
      title: '工具名称',
      dataIndex: ['tools_config', 'tool_name'],
      key: 'tool_name',
      ellipsis: true
    },
    {
      title: '工具描述',
      dataIndex: ['tools_config', 'tool_description'],
      key: 'tool_description',
      ellipsis: true
    },
    {
      title: '归因类型',
      dataIndex: 'attr_type',
      key: 'attr_type',
      width: 120,
      render: (type) => (
        <Tag color={type === 'contribution' ? 'green' : type === 'threshold' ? 'blue' : 'orange'}>
          {ATTR_TYPE_MAP[type] || type}
        </Tag>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.tool_id)}
          />
        </Space>
      )
    }
  ]

  // 根据归因类型渲染指标配置表单
  const renderIndicatorsForm = () => {
    if (currentAttrType === 'contribution') {
      return (
        <Card title="指标配置（贡献度归因）" size="small">
          <Form.Item name="parent_indicator" label="父指标" rules={[{ required: true, message: '请输入父指标' }]}>
            <Input placeholder="如：收入" />
          </Form.Item>
          <Form.Item name="dimension" label="分析维度" rules={[{ required: true, message: '请输入分析维度' }]}>
            <Input placeholder="如：核心产品分类维度" />
          </Form.Item>
          <Form.Item name="relation_type" label="关系类型" rules={[{ required: true, message: '请选择关系类型' }]}>
            <Select placeholder="选择关系类型">
              <Option value="additive">加法分解</Option>
              <Option value="multiplicative">乘法分解</Option>
            </Select>
          </Form.Item>
          <Form.Item name="child_indicators" label="子指标列表" rules={[{ required: true, message: '请输入子指标列表' }]}>
            <TextArea
              rows={6}
              placeholder="每行一个子指标，如：&#10;多彩涂料产品&#10;其他外墙产品&#10;真石质感产品"
            />
          </Form.Item>
        </Card>
      )
    }

    if (currentAttrType === 'variation') {
      return (
        <Card title="指标配置（变异度归因）" size="small">
          <Form.Item name="indicators" label="分析指标列表" rules={[{ required: true, message: '请输入分析指标列表' }]}>
            <TextArea
              rows={8}
              placeholder="每行一个指标，如：&#10;多彩涂料产品销售量&#10;其他外墙产品销售量&#10;真石质感产品销售量"
            />
          </Form.Item>
        </Card>
      )
    }

    if (currentAttrType === 'threshold') {
      return (
        <Card title="指标配置（阈值归因）" size="small">
          <div style={{ marginBottom: 12 }}>
            <Button type="dashed" icon={<PlusOutlined />} onClick={addThresholdIndicator}>
              添加阈值指标
            </Button>
          </div>

          {thresholdIndicators.length === 0 && (
            <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>
              点击上方按钮添加阈值指标配置
            </div>
          )}

          {thresholdIndicators.map((item, index) => (
            <Card
              key={index}
              size="small"
              style={{ marginBottom: 12, background: '#fafafa' }}
              extra={
                <Button
                  type="text"
                  danger
                  icon={<MinusCircleOutlined />}
                  onClick={() => removeThresholdIndicator(index)}
                >
                  删除
                </Button>
              }
            >
              <Form.Item label="指标名称" required>
                <Input
                  value={item.indicator}
                  onChange={(e) => updateThresholdIndicator(index, 'indicator', e.target.value)}
                  placeholder="如：高值品收入"
                />
              </Form.Item>
              <Form.Item label="阈值类型" required>
                <Select
                  value={item.threshold_type}
                  onChange={(value) => updateThresholdIndicator(index, 'threshold_type', value)}
                  placeholder="选择阈值类型"
                >
                  {Object.entries(THRESHOLD_TYPE_MAP).map(([key, label]) => (
                    <Option key={key} value={key}>{label}</Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item label="基准值">
                <Input
                  value={item.baseline}
                  onChange={(e) => updateThresholdIndicator(index, 'baseline', e.target.value)}
                  placeholder="如：高值品收入目标（可选）"
                />
              </Form.Item>
            </Card>
          ))}
        </Card>
      )
    }

    return null
  }

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          添加工具
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={tools}
        rowKey="tool_id"
        pagination={false}
        size="small"
        loading={loading}
        locale={{ emptyText: '暂无工具配置' }}
      />

      {/* 编辑弹窗 */}
      <Modal
        title={editingTool ? '编辑工具配置' : '添加工具配置'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        width={750}
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
              <Select placeholder="选择归因类型" onChange={handleAttrTypeChange}>
                <Option value="contribution">贡献度归因</Option>
                <Option value="variation">变异度归因</Option>
                <Option value="threshold">阈值归因</Option>
              </Select>
            </Form.Item>
            {(currentAttrType === 'variation' || currentAttrType === 'threshold') && (
              <Form.Item name="class_name_root" label="类名前缀">
                <Input placeholder="如：Chapter2SalesVolume（可选）" />
              </Form.Item>
            )}
          </Card>
        </Form>

        <Form form={indicatorsForm} layout="vertical">
          {renderIndicatorsForm()}
        </Form>
      </Modal>
    </div>
  )
}

export default ToolConfigTable