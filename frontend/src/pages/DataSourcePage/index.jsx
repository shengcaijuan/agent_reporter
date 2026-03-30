// 数据源管理页面
import { useState, useEffect } from 'react'
import {
  Card, Table, Button, Space, Modal, Form, Input, Select, InputNumber,
  Switch, message, Popconfirm, Tag, Divider, Alert, Spin
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ApiOutlined,
  CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined
} from '@ant-design/icons'
import { dataSourceApi } from '../../api/dataSource'

const { Option } = Select
const { Password } = Input

// 认证类型选项
const AUTH_TYPE_OPTIONS = [
  { value: 'url_param', label: 'URL参数' },
  { value: 'header', label: '请求头' },
  { value: 'bearer', label: 'Bearer Token' }
]

function DataSourcePage() {
  const [loading, setLoading] = useState(false)
  const [dataSources, setDataSources] = useState([])
  const [modalVisible, setModalVisible] = useState(false)
  const [editingSource, setEditingSource] = useState(null)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [form] = Form.useForm()

  // 加载数据源列表
  useEffect(() => {
    loadDataSources()
  }, [])

  const loadDataSources = async () => {
    setLoading(true)
    try {
      const response = await dataSourceApi.getGlobalDataSources()
      setDataSources(response.data || [])
    } catch (error) {
      message.error('加载数据源失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  // 打开新增/编辑弹窗
  const handleOpenModal = (record = null) => {
    setEditingSource(record)
    setTestResult(null)

    if (record) {
      form.setFieldsValue({
        name: record.name,
        description: record.description,
        base_url: record.config?.base_url,
        auth_type: record.config?.auth_type || 'url_param',
        auth_key_name: record.config?.auth_key_name || 'apikey',
        api_key: record.config?.api_key,
        timeout: record.config?.timeout || 15,
        ssl_verify: record.config?.ssl_verify || false,
        job_id_field: record.request_params?.job_id_field || 'ZEMPLOYEE',
        time_field: record.request_params?.time_field || 'CALMONTH',
        module_field: record.request_params?.module_field || 'MOUDLE',
        is_active: record.is_active !== false
      })
    } else {
      form.resetFields()
      form.setFieldsValue({
        auth_type: 'url_param',
        auth_key_name: 'apikey',
        timeout: 15,
        ssl_verify: false,
        job_id_field: 'ZEMPLOYEE',
        time_field: 'CALMONTH',
        module_field: 'MOUDLE',
        is_active: true
      })
    }

    setModalVisible(true)
  }

  // 保存数据源
  const handleSave = async () => {
    try {
      const values = await form.validateFields()

      const data = {
        type: 'api',
        name: values.name,
        description: values.description,
        config: {
          base_url: values.base_url,
          auth_type: values.auth_type,
          auth_key_name: values.auth_key_name,
          api_key: values.api_key,
          timeout: values.timeout,
          ssl_verify: values.ssl_verify
        },
        request_params: {
          job_id_field: values.job_id_field,
          time_field: values.time_field,
          module_field: values.module_field
        },
        is_default: false,
        is_active: values.is_active
      }

      if (editingSource) {
        await dataSourceApi.updateGlobalDataSource(editingSource.id, data)
        message.success('数据源更新成功')
      } else {
        await dataSourceApi.createGlobalDataSource(data)
        message.success('数据源创建成功')
      }

      setModalVisible(false)
      loadDataSources()
    } catch (error) {
      if (!error.errorFields) {
        message.error('保存失败: ' + (error.message || '未知错误'))
      }
    }
  }

  // 删除数据源
  const handleDelete = async (id) => {
    try {
      await dataSourceApi.deleteGlobalDataSource(id)
      message.success('数据源删除成功')
      loadDataSources()
    } catch (error) {
      message.error('删除失败: ' + (error.detail || error.message || '未知错误'))
    }
  }

  // 测试连接
  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const values = await form.validateFields(['base_url', 'api_key', 'auth_type', 'auth_key_name'])

      const result = await dataSourceApi.testConnection({
        base_url: values.base_url,
        api_key: values.api_key,
        auth_type: values.auth_type,
        auth_key_name: values.auth_key_name
      })

      setTestResult(result)
      if (result.success) {
        message.success('连接测试成功')
      } else {
        message.warning('连接测试失败')
      }
    } catch (error) {
      if (!error.errorFields) {
        setTestResult({ success: false, message: error.message || '未知错误' })
        message.error('连接测试失败: ' + (error.message || '未知错误'))
      }
    } finally {
      setTesting(false)
    }
  }

  // 表格列定义
  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 250,
      render: (text, record) => (
        <Space>
          {text}
          {record.is_default && <Tag color="blue">默认</Tag>}
          {record.is_active === false && <Tag color="red">禁用</Tag>}
        </Space>
      )
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    },
    {
      title: 'API地址',
      dataIndex: ['config', 'base_url'],
      key: 'base_url',
      ellipsis: true,
      width: 800
    },
    {
      title: '认证方式',
      dataIndex: ['config', 'auth_type'],
      key: 'auth_type',
      width: 200,
      align: 'center',
      render: (type) => AUTH_TYPE_OPTIONS.find(o => o.value === type)?.label || type
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 200,
      align: 'center',
      render: (active) => (
        <Tag color={active !== false ? 'green' : 'default'}>
          {active !== false ? '启用' : '禁用'}
        </Tag>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 400,
      align: 'center',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleOpenModal(record)}
          >
            编辑
          </Button>
          {!record.is_default && (
            <Popconfirm
              title="确定删除此数据源吗？"
              onConfirm={() => handleDelete(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
              >
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      )
    }
  ]

  return (
    <div className="page-card">
      <div className="page-title">
        <ApiOutlined style={{ marginRight: 8 }} />
        数据源管理
      </div>

      <Card>
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => handleOpenModal()}
            >
              新增数据源
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadDataSources}
            >
              刷新
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={dataSources}
          rowKey="id"
          loading={loading}
          pagination={false}
          scroll={{ x: 900 }}
        />
      </Card>

      {/* 新增/编辑弹窗 */}
      <Modal
        title={editingSource ? '编辑数据源' : '新增数据源'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
        width={700}
        okText="保存"
        cancelText="取消"
        footer={[
          <Button key="cancel" onClick={() => setModalVisible(false)}>
            取消
          </Button>,
          <Button
            key="test"
            icon={<ApiOutlined />}
            loading={testing}
            onClick={handleTest}
          >
            测试连接
          </Button>,
          <Button key="save" type="primary" onClick={handleSave}>
            保存
          </Button>
        ]}
      >
        <Form form={form} layout="vertical">
          {/* 基本信息 */}
          <Form.Item name="name" label="数据源名称" rules={[{ required: true, message: '请输入数据源名称' }]}>
            <Input placeholder="请输入数据源名称" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="数据源描述（可选）" />
          </Form.Item>

          <Form.Item name="is_active" label="启用状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Divider>连接配置</Divider>

          {/* 连接配置 */}
          <Form.Item
            name="base_url"
            label="API地址"
            rules={[
              { required: true, message: '请输入API地址' },
              { pattern: /^https?:\/\/.*/, message: '请输入有效的URL（以http://或https://开头）' }
            ]}
          >
            <Input placeholder="https://api.example.com/endpoint" />
          </Form.Item>

          <Space size="large" style={{ width: '100%' }}>
            <Form.Item name="auth_type" label="认证方式" rules={[{ required: true }]}>
              <Select style={{ width: 180 }}>
                {AUTH_TYPE_OPTIONS.map(opt => (
                  <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item name="auth_key_name" label="参数名称" rules={[{ required: true }]}>
              <Input placeholder="apikey" style={{ width: 180 }} />
            </Form.Item>
          </Space>

          <Form.Item name="api_key" label="API密钥" rules={[{ required: true, message: '请输入API密钥' }]}>
            <Password placeholder="请输入API密钥" />
          </Form.Item>

          <Space size="large" style={{ width: '100%' }}>
            <Form.Item name="timeout" label="超时时间(秒)">
              <InputNumber min={5} max={120} style={{ width: 120 }} />
            </Form.Item>

            <Form.Item name="ssl_verify" label="SSL验证" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>

          <Divider>请求参数映射</Divider>

          <Alert
            message="请求参数映射用于将系统参数映射到API所需的参数名"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Space size="large" style={{ width: '100%' }}>
            <Form.Item name="job_id_field" label="工号字段名">
              <Input placeholder="ZEMPLOYEE" style={{ width: 150 }} />
            </Form.Item>

            <Form.Item name="time_field" label="时间字段名">
              <Input placeholder="CALMONTH" style={{ width: 150 }} />
            </Form.Item>

            <Form.Item name="module_field" label="模块字段名">
              <Input placeholder="MOUDLE" style={{ width: 150 }} />
            </Form.Item>
          </Space>

          {/* 测试结果 */}
          {testResult && (
            <Alert
              message={testResult.success ? '连接成功' : '连接失败'}
              description={testResult.message}
              type={testResult.success ? 'success' : 'error'}
              icon={testResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
              showIcon
              style={{ marginTop: 16 }}
            />
          )}
        </Form>
      </Modal>
    </div>
  )
}

export default DataSourcePage