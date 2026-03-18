// 报告模板库管理页面
import { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Button,
  Input,
  Modal,
  Form,
  message,
  Popconfirm,
  Tag,
  Space,
  Spin,
  Empty,
  Typography,
  Tooltip,
  Upload,
  Segmented
} from 'antd'
import {
  PlusOutlined,
  UploadOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  FileTextOutlined,
  CodeOutlined
} from '@ant-design/icons'
import { templateApi } from '../../api/template'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

function TemplateLibrary() {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')

  // 模态框状态
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [previewModalVisible, setPreviewModalVisible] = useState(false)
  const [currentTemplate, setCurrentTemplate] = useState(null)
  const [currentTemplateContent, setCurrentTemplateContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [previewMode, setPreviewMode] = useState('rendered') // 'rendered' | 'code'

  const [form] = Form.useForm()

  useEffect(() => {
    loadTemplates()
  }, [])

  const loadTemplates = async () => {
    setLoading(true)
    try {
      const response = await templateApi.getTemplates()
      setTemplates(response.data || [])
    } catch (error) {
      message.error('加载模板列表失败')
    } finally {
      setLoading(false)
    }
  }

  // 过滤模板列表
  const filteredTemplates = templates.filter(t =>
    t.template_name?.toLowerCase().includes(searchText.toLowerCase()) ||
    t.description?.toLowerCase().includes(searchText.toLowerCase())
  )

  // 格式化文件大小
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  // 新建模板
  const handleCreate = () => {
    setCurrentTemplate(null)
    form.resetFields()
    form.setFieldsValue({
      template_name: '',
      description: '',
      content: ''
    })
    setEditModalVisible(true)
  }

  // 编辑模板
  const handleEdit = async (template) => {
    setLoading(true)
    try {
      const response = await templateApi.getTemplate(template.template_id)
      setCurrentTemplate(response.data)
      form.setFieldsValue({
        template_name: response.data.template_name,
        description: response.data.description,
        content: response.data.content
      })
      setEditModalVisible(true)
    } catch (error) {
      message.error('加载模板详情失败')
    } finally {
      setLoading(false)
    }
  }

  // 保存模板
  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)

      if (currentTemplate) {
        // 更新
        await templateApi.updateTemplate(currentTemplate.template_id, values)
        message.success('模板更新成功')
      } else {
        // 创建
        await templateApi.createTemplate(values)
        message.success('模板创建成功')
      }

      setEditModalVisible(false)
      loadTemplates()
    } catch (error) {
      if (!error.errorFields) {
        message.error('保存模板失败: ' + (error.message || '未知错误'))
      }
    } finally {
      setSaving(false)
    }
  }

  // 删除模板
  const handleDelete = async (templateId) => {
    try {
      await templateApi.deleteTemplate(templateId)
      message.success('模板删除成功')
      loadTemplates()
    } catch (error) {
      message.error(error.response?.data?.detail || '删除模板失败')
    }
  }

  // 预览模板
  const handlePreview = async (template) => {
    setCurrentTemplate(template)
    setPreviewMode('rendered')
    setPreviewModalVisible(true)
    // 获取模板内容用于代码视图
    try {
      const response = await templateApi.getTemplate(template.template_id)
      setCurrentTemplateContent(response.data.content || '')
    } catch (error) {
      setCurrentTemplateContent('')
    }
  }

  // 上传模板文件
  const handleUpload = async (file) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      await templateApi.uploadTemplate(formData)
      message.success('模板上传成功')
      loadTemplates()
    } catch (error) {
      message.error('上传模板失败: ' + (error.message || '未知错误'))
    }

    return false // 阻止默认上传行为
  }

  return (
    <div>
      <div className="page-card">
        <div className="page-title">报告模板库</div>
        <Text type="secondary">
          管理报告生成使用的 HTML 模板，可创建、编辑、删除模板。
        </Text>
      </div>

      <Card>
        {/* 操作栏 */}
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建模板
            </Button>
            <Upload
              accept=".html"
              showUploadList={false}
              beforeUpload={handleUpload}
            >
              <Button icon={<UploadOutlined />}>上传模板</Button>
            </Upload>
          </Space>

          <Input.Search
            placeholder="搜索模板..."
            style={{ width: 250 }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            allowClear
          />
        </div>

        {/* 模板列表 */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: 50 }}>
            <Spin size="large" />
          </div>
        ) : filteredTemplates.length === 0 ? (
          <Empty description="暂无模板，点击「新建模板」或「上传模板」开始" />
        ) : (
          <Row gutter={[16, 16]}>
            {filteredTemplates.map((template) => (
              <Col xs={24} sm={12} md={8} lg={6} key={template.template_id}>
                <Card
                  hoverable
                  size="small"
                  title={
                    <Space>
                      <FileTextOutlined />
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 150 }}>
                        {template.template_name}
                      </span>
                    </Space>
                  }
                  extra={
                    template.is_default && (
                      <Tag color="green" icon={<CheckCircleOutlined />}>默认</Tag>
                    )
                  }
                  style={{ height: '100%' }}
                >
                  <Paragraph
                    ellipsis={{ rows: 2 }}
                    style={{ minHeight: 44, color: '#666', marginBottom: 12 }}
                  >
                    {template.description || '暂无描述'}
                  </Paragraph>

                  <div style={{ fontSize: 12, color: '#999', marginBottom: 12 }}>
                    <div>大小: {formatFileSize(template.file_size)}</div>
                    {template.updated_at && (
                      <div>更新: {new Date(template.updated_at).toLocaleDateString()}</div>
                    )}
                  </div>

                  <Space wrap size="small">
                    <Tooltip title="预览">
                      <Button
                        size="small"
                        icon={<EyeOutlined />}
                        onClick={() => handlePreview(template)}
                      />
                    </Tooltip>
                    <Tooltip title="编辑">
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => handleEdit(template)}
                      />
                    </Tooltip>
                    {!template.is_default && (
                      <Popconfirm
                        title="确定删除此模板？"
                        onConfirm={() => handleDelete(template.template_id)}
                        okText="确定"
                        cancelText="取消"
                      >
                        <Tooltip title="删除">
                          <Button
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                          />
                        </Tooltip>
                      </Popconfirm>
                    )}
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Card>

      {/* 编辑模板模态框 */}
      <Modal
        title={currentTemplate ? '编辑模板' : '新建模板'}
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        onOk={handleSave}
        confirmLoading={saving}
        width={900}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="模板名称"
                name="template_name"
                rules={[{ required: true, message: '请输入模板名称' }]}
              >
                <Input placeholder="输入模板名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="描述" name="description">
                <Input placeholder="输入模板描述（可选）" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            label={<><CodeOutlined /> HTML 内容</>}
            name="content"
            rules={[{ required: true, message: '请输入 HTML 内容' }]}
          >
            <TextArea
              rows={20}
              placeholder="输入 HTML 模板代码..."
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 预览模板模态框 */}
      <Modal
        title={`预览: ${currentTemplate?.template_name || ''}`}
        open={previewModalVisible}
        onCancel={() => setPreviewModalVisible(false)}
        footer={null}
        width={1000}
        style={{ top: 20 }}
      >
        <div style={{ marginBottom: 12 }}>
          <Segmented
            value={previewMode}
            onChange={setPreviewMode}
            options={[
              { label: '渲染预览', value: 'rendered' },
              { label: 'HTML代码', value: 'code' }
            ]}
          />
        </div>
        <div style={{ height: '70vh', overflow: 'auto', border: '1px solid #eee', borderRadius: 4 }}>
          {previewMode === 'rendered' && currentTemplateContent && (
            <iframe
              srcDoc={currentTemplateContent}
              style={{ width: '100%', height: '100%', border: 'none' }}
              title="模板预览"
            />
          )}
          {previewMode === 'code' && (
            <pre style={{ margin: 0, padding: 16, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 12 }}>
              {currentTemplateContent}
            </pre>
          )}
        </div>
      </Modal>
    </div>
  )
}

export default TemplateLibrary