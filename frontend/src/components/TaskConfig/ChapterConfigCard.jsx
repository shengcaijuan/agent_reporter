// 章节配置卡片组件
import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Card, Form, Input, Button, Collapse, Space, Tag, message, Spin, Switch, Select, Tooltip
} from 'antd'
import {
  DeleteOutlined, PlusOutlined, SettingOutlined, ToolOutlined,
  FileTextOutlined, FormatPainterOutlined, DatabaseOutlined, InfoCircleOutlined
} from '@ant-design/icons'
import { taskApi } from '../../api/task'
import SectionConfigItem from './SectionConfigItem'
import ToolConfigTable from './ToolConfigTable'

const { TextArea } = Input
const { Panel } = Collapse
const { Option } = Select

// 章节类型映射
const CHAPTER_TYPE_MAP = {
  simple: '简单章节',
  with_tools: '带工具章节',
  summary: '总结章节'
}

// 事业部选项
const BUSINESS_UNIT_OPTIONS = [
  { value: 'mashangzhu', label: '马上住焕新事业部', disabled: false },
  { value: 'gongchengqi', label: '工程漆事业部', disabled: true },
  { value: 'fangshiqi', label: '仿石漆事业部', disabled: true }
]

// 数据接口选项
const DATA_INTERFACE_OPTIONS = {
  'mashangzhu': [
    { value: 'performance', label: '绩效分析' },
    { value: 'sales_dynamics', label: '销售动能分析' },
    { value: 'gross_margin', label: '毛利率与产品结构' },
    { value: 'receivables', label: '费用与应收账款风险' },
    { value: 'marketing_behavior', label: '行销行为诊断' }
  ]
}

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

  // 清理
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }
    }
  }, [])

  return debouncedCallback
}

function ChapterConfigCard({
  taskId,
  chapter,
  index,
  onDelete,
  canDelete,
  onUpdate,
  initialConfig,   // 外部传入的初始配置（用于演示模式）
  initialTools     // 外部传入的初始工具列表（用于演示模式）
}) {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [config, setConfig] = useState(initialConfig || null)
  const [tools, setTools] = useState(initialTools || [])
  const [activeKeys, setActiveKeys] = useState(['sections'])

  // 数据配置状态
  const [dataConfig, setDataConfig] = useState({
    business_unit: initialConfig?.data_config?.business_unit || undefined,
    data_interface: initialConfig?.data_config?.data_interface || undefined
  })

  // 当外部配置变化时更新
  useEffect(() => {
    if (initialConfig) {
      setConfig(initialConfig)
      if (initialConfig.data_config) {
        setDataConfig({
          business_unit: initialConfig.data_config.business_unit || undefined,
          data_interface: initialConfig.data_config.data_interface || undefined
        })
      }
    }
  }, [initialConfig])

  // 当外部工具列表变化时更新
  useEffect(() => {
    if (initialTools) {
      setTools(initialTools)
    }
  }, [initialTools])

  // 加载章节配置
  useEffect(() => {
    if (taskId && chapter?.chapter_id && !initialConfig) {
      loadChapterConfig()
    }
    if (taskId && chapter?.chapter_id && !initialTools) {
      loadToolConfigs()
    }
  }, [taskId, chapter?.chapter_id])

  const loadChapterConfig = async () => {
    setLoading(true)
    try {
      const response = await taskApi.getChapterConfig(taskId, chapter.chapter_id)
      const configData = response.data || {}
      setConfig(configData)

      // 初始化数据配置
      if (configData.data_config) {
        setDataConfig({
          business_unit: configData.data_config.business_unit || undefined,
          data_interface: configData.data_config.data_interface || undefined
        })
      }
    } catch (error) {
      console.error('加载章节配置失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadToolConfigs = async () => {
    try {
      const response = await taskApi.getToolConfigs(taskId, chapter.chapter_id)
      // 处理返回的数据格式
      const toolData = response.data
      if (toolData && typeof toolData === 'object' && toolData.tools) {
        setTools(toolData.tools)
      } else if (Array.isArray(toolData)) {
        setTools(toolData)
      } else {
        setTools([])
      }
    } catch (error) {
      console.error('加载工具配置失败:', error)
      setTools([])
    }
  }

  // 实际保存到后端（不带提示）
  const doSaveConfig = useCallback(async (newConfig) => {
    try {
      await taskApi.updateChapterConfig(taskId, chapter.chapter_id, {
        ...config,
        ...newConfig,
        chapter_id: chapter.chapter_id
      })
      setConfig(prev => ({ ...prev, ...newConfig }))
    } catch (error) {
      console.error('自动保存失败:', error)
    }
  }, [taskId, chapter.chapter_id, config])

  // 防抖保存
  const debouncedSave = useDebounce(doSaveConfig, 800)

  // 手动保存（带提示）
  const saveChapterConfig = async (newConfig, showMessage = true) => {
    setSaving(true)
    try {
      await taskApi.updateChapterConfig(taskId, chapter.chapter_id, {
        ...config,
        ...newConfig,
        chapter_id: chapter.chapter_id
      })
      setConfig(prev => ({ ...prev, ...newConfig }))
      if (showMessage) {
        message.success('保存成功')
      }
    } catch (error) {
      message.error('保存失败: ' + error.message)
    } finally {
      setSaving(false)
    }
  }

  // 保存工具配置
  const saveToolConfigs = async (toolId, toolConfig, isDeleteAll = false) => {
    setSaving(true)
    try {
      if (isDeleteAll) {
        // 删除场景：保存新的工具列表
        const chapterToolsData = {
          chapter_id: chapter.chapter_id,
          chapter_name: chapter.chapter_name,
          tools: toolConfig
        }
        await taskApi.updateToolConfigs(taskId, chapter.chapter_id, chapterToolsData)
        setTools(toolConfig)
      } else if (toolId) {
        // 更新现有工具
        await taskApi.updateToolConfig(taskId, chapter.chapter_id, toolId, toolConfig)
        loadToolConfigs()
      } else {
        // 创建新工具
        await taskApi.createToolConfig(taskId, chapter.chapter_id, toolConfig)
        loadToolConfigs()
      }
      message.success('保存成功')
    } catch (error) {
      message.error('保存失败: ' + error.message)
    } finally {
      setSaving(false)
    }
  }

  // 更新章节名称（实时更新本地，防抖保存到后端）
  const handleNameChange = (e) => {
    const newName = e.target.value
    onUpdate(index, { ...chapter, chapter_name: newName })
    debouncedSave({ chapter_name: newName })
  }

  // 更新章节类型（立即保存，因为是选择操作）
  const handleTypeChange = (type) => {
    onUpdate(index, { ...chapter, chapter_type: type, has_tools: type === 'with_tools' })
    saveChapterConfig({ chapter_type: type, has_tools: type === 'with_tools' })
  }

  // 更新小节（立即保存，因为是明确的操作）
  const updateSections = (newSections) => {
    saveChapterConfig({ sections: newSections })
  }

  // 添加小节
  const addSection = () => {
    const newSections = [...(config?.sections || []), { section_name: '', requirements: [] }]
    updateSections(newSections)
  }

  // 更新小节内容（防抖保存）
  const updateSection = (secIndex, newSection) => {
    const newSections = [...(config?.sections || [])]
    newSections[secIndex] = newSection
    setConfig(prev => ({ ...prev, sections: newSections }))
    debouncedSave({ sections: newSections })
  }

  // 删除小节（立即保存，因为是明确操作）
  const deleteSection = (secIndex) => {
    const newSections = (config?.sections || []).filter((_, i) => i !== secIndex)
    setConfig(prev => ({ ...prev, sections: newSections }))
    saveChapterConfig({ sections: newSections })
  }

  // 更新输出示例（防抖保存）
  const handleOutputExampleChange = (e) => {
    const value = e.target.value
    setConfig(prev => ({ ...prev, output_example: value }))
    debouncedSave({ output_example: value })
  }

  // 更新语言风格（防抖保存）
  const handleStyleChange = (e) => {
    const text = e.target.value
    const requirements = text.split('\n').filter(Boolean)
    setConfig(prev => ({ ...prev, style_requirements: requirements }))
    debouncedSave({ style_requirements: requirements })
  }

  // 数据配置 - 事业部变化处理
  const handleBusinessUnitChange = (value) => {
    const newDataConfig = {
      business_unit: value,
      data_interface: undefined
    }
    setDataConfig(newDataConfig)
    saveChapterConfig({ data_config: newDataConfig }, false)
  }

  // 数据配置 - 数据接口变化处理
  const handleDataInterfaceChange = (value) => {
    const newDataConfig = {
      ...dataConfig,
      data_interface: value
    }
    setDataConfig(newDataConfig)
    saveChapterConfig({ data_config: newDataConfig }, false)
  }

  if (loading) {
    return (
      <Card style={{ marginBottom: 16 }}>
        <Spin />
      </Card>
    )
  }

  return (
    <Card
      style={{ marginBottom: 16 }}
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span>第 {chapter.chapter_id} 章</span>
          <Input
            value={chapter.chapter_name}
            onChange={handleNameChange}
            style={{ width: 200 }}
            placeholder="章节名称"
          />
          <Select
            value={chapter.chapter_type || 'simple'}
            onChange={handleTypeChange}
            style={{ width: 130 }}
            options={[
              { value: 'simple', label: '简单章节' },
              { value: 'with_tools', label: '带工具章节' },
              { value: 'summary', label: '总结章节' }
            ]}
          />
          <Tag color={chapter.has_tools ? 'blue' : 'default'}>
            {CHAPTER_TYPE_MAP[chapter.chapter_type] || '简单章节'}
          </Tag>
        </div>
      }
      extra={
        canDelete && (
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            onClick={() => onDelete(index)}
          >
            删除章节
          </Button>
        )
      }
    >
      <Collapse
        activeKey={activeKeys}
        onChange={(keys) => setActiveKeys(keys)}
        bordered={false}
      >
        {/* 数据配置 */}
        <Panel
          header={
            <span>
              <DatabaseOutlined style={{ marginRight: 8 }} />
              数据配置
            </span>
          }
          key="data"
        >
          <Space size="large">
            <div>
              <span style={{ marginRight: 8 }}>事业部:</span>
              <Select
                value={dataConfig.business_unit}
                onChange={handleBusinessUnitChange}
                style={{ width: 200 }}
                placeholder="请选择事业部"
              >
                {BUSINESS_UNIT_OPTIONS.map(option => (
                  <Option
                    key={option.value}
                    value={option.value}
                    disabled={option.disabled}
                  >
                    {option.disabled ? (
                      <Tooltip title="数据接口未开发">
                        <span style={{ color: '#bfbfbf' }}>{option.label}</span>
                      </Tooltip>
                    ) : (
                      option.label
                    )}
                  </Option>
                ))}
              </Select>
            </div>
            <div>
              <span style={{ marginRight: 8 }}>数据接口:</span>
              <Select
                value={dataConfig.data_interface}
                onChange={handleDataInterfaceChange}
                style={{ width: 200 }}
                placeholder="请先选择事业部"
                disabled={!dataConfig.business_unit}
              >
                {dataConfig.business_unit && DATA_INTERFACE_OPTIONS[dataConfig.business_unit]?.map(option => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
              {!dataConfig.business_unit && (
                <Tooltip title="请先选择事业部">
                  <InfoCircleOutlined style={{ marginLeft: 8, color: '#bfbfbf' }} />
                </Tooltip>
              )}
            </div>
          </Space>
        </Panel>

        {/* 小节配置 */}
        <Panel
          header={
            <span>
              <FileTextOutlined style={{ marginRight: 8 }} />
              小节配置
            </span>
          }
          key="sections"
        >
          <div style={{ marginBottom: 12 }}>
            <Button type="dashed" icon={<PlusOutlined />} onClick={addSection}>
              添加小节
            </Button>
          </div>
          {(config?.sections || []).map((section, secIndex) => (
            <SectionConfigItem
              key={secIndex}
              section={section}
              index={secIndex}
              onUpdate={updateSection}
              onDelete={deleteSection}
            />
          ))}
          {(config?.sections || []).length === 0 && (
            <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>
              暂无小节，点击上方按钮添加
            </div>
          )}
        </Panel>

        {/* 输出示例 */}
        <Panel
          header={
            <span>
              <FileTextOutlined style={{ marginRight: 8 }} />
              输出示例
            </span>
          }
          key="output"
        >
          <TextArea
            value={config?.output_example || ''}
            onChange={handleOutputExampleChange}
            placeholder="请输入输出示例（支持 Markdown 格式）"
            rows={8}
            style={{ fontFamily: 'monospace' }}
          />
        </Panel>

        {/* 工具函数配置 */}
        {chapter.chapter_type === 'with_tools' && (
          <Panel
            header={
              <span>
                <ToolOutlined style={{ marginRight: 8 }} />
                工具函数配置
                <Tag color="blue" style={{ marginLeft: 8 }}>
                  {tools.length} 个工具
                </Tag>
              </span>
            }
            key="tools"
          >
            <ToolConfigTable
              tools={tools}
              onSave={saveToolConfigs}
              loading={saving}
            />
          </Panel>
        )}

        {/* 语言风格 */}
        <Panel
          header={
            <span>
              <FormatPainterOutlined style={{ marginRight: 8 }} />
              语言风格
            </span>
          }
          key="style"
        >
          <TextArea
            value={(config?.style_requirements || []).join('\n')}
            onChange={handleStyleChange}
            placeholder="每行一条风格要求，如：&#10;专业、简洁、逻辑清晰；&#10;请输出段落文字；&#10;报告采用第二人称「您」。"
            rows={6}
          />
        </Panel>
      </Collapse>
    </Card>
  )
}

export default ChapterConfigCard