// 模型配置页面
import { useState, useEffect } from 'react'
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Radio,
  Space,
  message,
  Divider,
  Spin,
  Typography,
  Switch,
  Alert
} from 'antd'
import {
  CloudServerOutlined,
  LaptopOutlined,
  SaveOutlined,
  ReloadOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'
import { modelConfigApi } from '../../api/modelConfig'

const { Title, Text } = Typography
const { Option } = Select

function ModelConfig() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [modelType, setModelType] = useState('cloud')
  const [config, setConfig] = useState(null)
  const [defaultModelType, setDefaultModelType] = useState('cloud')

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const result = await modelConfigApi.getConfig()
      setConfig(result.data)
      setDefaultModelType(result.data.default_model_type)
      setModelType(result.data.default_model_type)

      // 设置表单初始值
      const currentModel = result.data.models[result.data.default_model_type]
      form.setFieldsValue({
        model_type: result.data.default_model_type,
        model_name: currentModel.model_name,
        api_key: currentModel.api_key,
        base_url: currentModel.base_url || '',
        description: currentModel.description || ''
      })
    } catch (error) {
      message.error('加载模型配置失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  const handleModelTypeChange = (e) => {
    const newType = e.target.value
    setModelType(newType)

    if (config && config.models[newType]) {
      const modelInfo = config.models[newType]
      form.setFieldsValue({
        model_type: newType,
        model_name: modelInfo.model_name,
        api_key: modelInfo.api_key,
        base_url: modelInfo.base_url || '',
        description: modelInfo.description || ''
      })
    }
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)

      // 更新模型配置
      await modelConfigApi.updateModel({
        model_type: values.model_type,
        model_name: values.model_name,
        api_key: values.api_key,
        base_url: values.base_url,
        description: values.description
      })

      // 设置为默认模型类型
      await modelConfigApi.setDefaultType(values.model_type)

      setDefaultModelType(values.model_type)
      message.success('模型配置保存成功')
      loadConfig()
    } catch (error) {
      if (error.errorFields) {
        return
      }
      message.error('保存模型配置失败: ' + (error.message || '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    if (config && config.models[modelType]) {
      const modelInfo = config.models[modelType]
      form.setFieldsValue({
        model_type: modelType,
        model_name: modelInfo.model_name,
        api_key: modelInfo.api_key,
        base_url: modelInfo.base_url || '',
        description: modelInfo.description || ''
      })
      message.info('已重置为保存的配置')
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Spin size="large" tip="加载配置中..." />
      </div>
    )
  }

  return (
    <div>
      <div className="page-card">
        <div className="page-title">模型配置</div>
        <Text type="secondary">
          配置报告生成使用的 LLM 模型。选择并配置模型后，点击保存即可生效。
        </Text>
      </div>

      {/* 当前使用的模型提示 */}
      {config && (
        <Alert
          message={
            <Space>
              <CheckCircleOutlined style={{ color: '#52c41a' }} />
              <span>
                当前使用：
                <strong>
                  {defaultModelType === 'cloud' ? '云端模型' : '本地模型'}
                </strong>
                （{config.models[defaultModelType]?.model_name}）
              </span>
            </Space>
          }
          type="success"
          style={{ marginBottom: 16 }}
        />
      )}

      <Card>
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            model_type: 'cloud'
          }}
        >
          {/* 模型类型选择 */}
          <Form.Item label="选择模型类型" name="model_type">
            <Radio.Group onChange={handleModelTypeChange} value={modelType}>
              <Radio.Button value="cloud">
                <CloudServerOutlined style={{ marginRight: 8 }} />
                云端模型
              </Radio.Button>
              <Radio.Button value="local">
                <LaptopOutlined style={{ marginRight: 8 }} />
                本地模型
              </Radio.Button>
            </Radio.Group>
          </Form.Item>

          <Divider />

          {/* 模型详细信息 */}
          <Title level={5}>
            {modelType === 'cloud' ? '云端模型配置' : '本地模型配置'}
          </Title>
          <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
            配置并保存后，该模型将作为报告生成的默认模型
          </Text>

          <Form.Item
            label="模型名称"
            name="model_name"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input placeholder="如：qwen3.5-plus" />
          </Form.Item>

          <Form.Item
            label="API Key"
            name="api_key"
            rules={[{ required: true, message: '请输入 API Key' }]}
          >
            <Input.Password placeholder="请输入 API Key" />
          </Form.Item>

          <Form.Item
            label="Base URL"
            name="base_url"
            rules={[{ required: true, message: '请输入 Base URL' }]}
            extra="API 服务地址，如阿里云：https://dashscope.aliyuncs.com/compatible-mode/v1"
          >
            <Input placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" />
          </Form.Item>

          <Form.Item label="描述" name="description">
            <Input.TextArea
              rows={2}
              placeholder="模型配置描述（可选）"
            />
          </Form.Item>

          <Divider />

          {/* 操作按钮 */}
          <Form.Item>
            <Space>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSave}
                loading={saving}
              >
                保存并使用此模型
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleReset}
              >
                重置
              </Button>
            </Space>
          </Form.Item>
        </Form>

        {/* 配置信息提示 */}
        {config && (
          <div style={{
            marginTop: 16,
            padding: 12,
            background: '#f5f5f5',
            borderRadius: 4
          }}>
            <Text type="secondary">
              最后更新时间: {config.last_updated || '未记录'}
            </Text>
          </div>
        )}
      </Card>
    </div>
  )
}

export default ModelConfig