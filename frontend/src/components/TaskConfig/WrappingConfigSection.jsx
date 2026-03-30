// 报告样式配置区域组件
import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Tabs, Input, Spin, message, Select, Button, Modal, Space, Tag, Segmented } from 'antd'
import { FormatPainterOutlined, FileTextOutlined, EyeOutlined, LinkOutlined } from '@ant-design/icons'
import { taskApi } from '../../api/task'
import { templateApi } from '../../api/template'

const { TextArea } = Input
const { Option } = Select

// 防抖hook
function useDebounce(callback, delay = 800) {
  const timerRef = useRef(null)

  const debouncedCallback = useCallback((...args) => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
    }
    timerRef.current = setTimeout(() => {
      callback(...args)
    }, delay)
  }, [callback, delay])

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }
    }
  }, [])

  return debouncedCallback
}

function WrappingConfigSection({ taskId, chapters }) {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [wrappingConfig, setWrappingConfig] = useState({ lay_out_requirements: [] })
  const [activeChapter, setActiveChapter] = useState(0)
  const [templates, setTemplates] = useState([])
  const [selectedTemplate, setSelectedTemplate] = useState(null)
  const [previewVisible, setPreviewVisible] = useState(false)
  const [previewTemplate, setPreviewTemplate] = useState(null)
  const [previewContent, setPreviewContent] = useState('')
  const [previewMode, setPreviewMode] = useState('rendered') // 'rendered' | 'code'

  // 加载模板列表
  useEffect(() => {
    loadTemplates()
  }, [])

  // 加载样式配置
  useEffect(() => {
    if (taskId) {
      loadWrappingConfig()
    }
  }, [taskId])

  const loadTemplates = async () => {
    setTemplatesLoading(true)
    try {
      const response = await templateApi.getTemplates()
      setTemplates(response.data || [])
    } catch (error) {
      console.error('加载模板列表失败:', error)
    } finally {
      setTemplatesLoading(false)
    }
  }

  const loadWrappingConfig = async () => {
    setLoading(true)
    try {
      const response = await taskApi.getWrappingConfig(taskId)
      const config = response.data || { lay_out_requirements: [] }
      setWrappingConfig(config)
      // 设置当前选中的模板
      if (config.selected_template) {
        setSelectedTemplate(config.selected_template)
      }
    } catch (error) {
      console.error('加载样式配置失败:', error)
    } finally {
      setLoading(false)
    }
  }

  // 应用模板
  const handleTemplateChange = async (templateId) => {
    if (templateId === selectedTemplate) return

    try {
      await templateApi.applyTemplate(templateId, taskId)
      setSelectedTemplate(templateId)
      message.success('模板应用成功')
      // 重新加载配置以更新选中状态
      loadWrappingConfig()
    } catch (error) {
      message.error('应用模板失败: ' + (error.message || '未知错误'))
    }
  }

  // 预览模板
  const handlePreview = async () => {
    if (!selectedTemplate) return
    const template = templates.find(t => t.template_id === selectedTemplate)
    setPreviewTemplate(template)
    setPreviewMode('rendered')
    // 获取模板内容
    try {
      const response = await templateApi.getTemplate(selectedTemplate)
      setPreviewContent(response.data.content || '')
    } catch (error) {
      setPreviewContent('')
      message.error('加载模板内容失败')
    }
    setPreviewVisible(true)
  }

  // 实际保存（不显示提示）
  const doSaveConfig = useCallback(async (newConfig) => {
    try {
      await taskApi.updateWrappingConfig(taskId, newConfig)
      setWrappingConfig(newConfig)
    } catch (error) {
      console.error('自动保存失败:', error)
    }
  }, [taskId])

  // 防抖保存
  const debouncedSave = useDebounce(doSaveConfig)

  // 获取指定章节的排版要求
  const getChapterRequirement = (chapterId) => {
    const found = (wrappingConfig.lay_out_requirements || []).find(
      item => item.chapter_id === chapterId
    )
    return found ? (found.requirements || []).join('\n') : ''
  }

  // 更新章节排版要求（防抖保存）
  const updateChapterRequirement = (chapterId, chapterName, text) => {
    const requirements = text.split('\n').filter(Boolean)
    const newRequirements = [...(wrappingConfig.lay_out_requirements || [])]

    const existingIndex = newRequirements.findIndex(item => item.chapter_id === chapterId)

    if (existingIndex >= 0) {
      if (requirements.length > 0) {
        newRequirements[existingIndex] = {
          ...newRequirements[existingIndex],
          requirements
        }
      } else {
        newRequirements.splice(existingIndex, 1)
      }
    } else if (requirements.length > 0) {
      newRequirements.push({
        chapter_id: chapterId,
        chapter_name: chapterName,
        requirements
      })
    }

    // 更新本地状态
    setWrappingConfig({ ...wrappingConfig, lay_out_requirements: newRequirements })
    // 防抖保存到后端
    debouncedSave({ ...wrappingConfig, lay_out_requirements: newRequirements })
  }

  // 章节选项卡
  const tabItems = chapters.map((ch, index) => ({
    key: index.toString(),
    label: `第${ch.chapter_id}章 ${ch.chapter_name}`
  }))

  // 当前选中的模板信息
  const currentTemplateInfo = templates.find(t => t.template_id === selectedTemplate)

  if (loading) {
    return (
      <Card title="报告样式配置">
        <Spin />
      </Card>
    )
  }

  if (chapters.length === 0) {
    return null
  }

  const currentChapter = chapters[activeChapter]

  return (
    <>
      {/* 报告模板选择 */}
      <Card
        title={
          <span>
            <FileTextOutlined style={{ marginRight: 8 }} />
            报告模板
          </span>
        }
        style={{ marginTop: 24 }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <span>当前模板：</span>
          <Select
            style={{ width: 280 }}
            value={selectedTemplate}
            onChange={handleTemplateChange}
            loading={templatesLoading}
            placeholder="选择报告模板"
          >
            {templates.map((template) => (
              <Option key={template.template_id} value={template.template_id}>
                <Space>
                  {template.template_name}
                  {template.is_default && <Tag color="green" style={{ marginLeft: 4 }}>默认</Tag>}
                </Space>
              </Option>
            ))}
          </Select>
          <Button
            icon={<EyeOutlined />}
            onClick={handlePreview}
            disabled={!selectedTemplate}
          >
            预览
          </Button>
          <Button
            type="link"
            icon={<LinkOutlined />}
            onClick={() => navigate('/templates')}
          >
            管理模板库
          </Button>
        </div>
        {currentTemplateInfo && (
          <div style={{ marginTop: 12, color: '#666', fontSize: 13 }}>
            <div>模板描述：{currentTemplateInfo.description || '暂无描述'}</div>
            {wrappingConfig.template_applied_at && (
              <div style={{ marginTop: 4 }}>
                应用时间：{new Date(wrappingConfig.template_applied_at).toLocaleString()}
              </div>
            )}
          </div>
        )}
      </Card>

      {/* 章节排版配置 */}
      <Card
        title={
          <span>
            <FormatPainterOutlined style={{ marginRight: 8 }} />
            章节排版配置
          </span>
        }
        style={{ marginTop: 16 }}
      >
        <p style={{ color: '#666', marginBottom: 16 }}>
          配置每个章节的排版要求，如表格展示、卡片展示等格式要求。
        </p>

        <Tabs
          activeKey={activeChapter.toString()}
          onChange={(key) => setActiveChapter(parseInt(key))}
          items={tabItems}
        />

        {currentChapter && (
          <div style={{ marginTop: 16 }}>
            <TextArea
              value={getChapterRequirement(currentChapter.chapter_id)}
              onChange={(e) => updateChapterRequirement(
                currentChapter.chapter_id,
                currentChapter.chapter_name,
                e.target.value
              )}
              placeholder={`请输入第${currentChapter.chapter_id}章的排版要求，每行一条，例如：&#10;卡片展示排名数据；&#10;表格展示绩效分数；&#10;关键详情列的文字表述不用加黑加粗。`}
              rows={6}
            />
          </div>
        )}
      </Card>

      {/* 模板预览模态框 */}
      <Modal
        title={`预览: ${previewTemplate?.template_name || ''}`}
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
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
          {previewMode === 'rendered' && previewContent && (
            <iframe
              srcDoc={previewContent}
              style={{ width: '100%', height: '100%', border: 'none' }}
              title="模板预览"
            />
          )}
          {previewMode === 'code' && (
            <pre style={{ margin: 0, padding: 16, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 12 }}>
              {previewContent}
            </pre>
          )}
        </div>
      </Modal>
    </>
  )
}

export default WrappingConfigSection