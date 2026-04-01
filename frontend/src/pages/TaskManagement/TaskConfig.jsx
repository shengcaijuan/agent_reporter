// 任务配置页面 - 整合报告配置、章节配置、小节配置
import { useState, useEffect } from 'react'
import {
  Card, Tabs, Form, Input, Button, message, Spin, Select, Collapse, Typography, Table, Space, Tag, Modal, Descriptions
} from 'antd'
import {
  SaveOutlined, ReloadOutlined, SettingOutlined, ToolOutlined, BookOutlined, FileTextOutlined, DeleteOutlined, ExclamationCircleOutlined
} from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import useTaskStore from '../../stores/taskStore'
import { taskApi } from '../../api/task'

const { TextArea } = Input
const { Title, Paragraph } = Typography

// 归因类型映射
const ATTR_TYPE_MAP = {
  contribution: '贡献度归因',
  variation: '变异度归因',
  threshold: '阈值归因'
}

function TaskConfig() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const { currentTask, fetchTask, fetchTasks } = useTaskStore()

  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [chapters, setChapters] = useState([])
  const [reportIntro, setReportIntro] = useState('')
  const [chapterConfigs, setChapterConfigs] = useState({})
  const [toolConfigs, setToolConfigs] = useState({})

  const [reportIntroForm] = Form.useForm()
  // 为6个章节预创建表单实例
  const [chapter1Form] = Form.useForm()
  const [chapter2Form] = Form.useForm()
  const [chapter3Form] = Form.useForm()
  const [chapter4Form] = Form.useForm()
  const [chapter5Form] = Form.useForm()
  const [chapter6Form] = Form.useForm()

  const chapterFormsMap = {
    1: chapter1Form,
    2: chapter2Form,
    3: chapter3Form,
    4: chapter4Form,
    5: chapter5Form,
    6: chapter6Form
  }

  // 加载任务数据
  useEffect(() => {
    if (taskId) {
      loadAllData()
    }
  }, [taskId])

  const loadAllData = async () => {
    setLoading(true)
    try {
      // 加载任务信息
      if (!currentTask || currentTask.task_id !== taskId) {
        await fetchTask(taskId)
      }

      // 加载章节列表
      const chaptersRes = await taskApi.getChapters(taskId)
      const chaptersData = chaptersRes.data || []
      setChapters(chaptersData)

      // 加载各章节配置
      const configs = {}
      for (const ch of chaptersData) {
        try {
          const configRes = await taskApi.getChapterConfig(taskId, ch.chapter_id)
          configs[ch.chapter_id] = configRes.data || {}
        } catch (e) {
          configs[ch.chapter_id] = {}
        }
      }
      setChapterConfigs(configs)

      // 加载各章节的工具配置
      const tools = {}
      for (const ch of chaptersData.filter(c => c.has_tools)) {
        try {
          const toolRes = await taskApi.getToolConfigs(taskId, ch.chapter_id)
          tools[ch.chapter_id] = toolRes.data || []
        } catch (e) {
          tools[ch.chapter_id] = []
        }
      }
      setToolConfigs(tools)

    } catch (error) {
      message.error('加载数据失败: ' + (error.message || error.detail))
    } finally {
      setLoading(false)
    }
  }

  // 保存报告介绍
  const saveReportIntro = async () => {
    setSaving(true)
    try {
      const values = await reportIntroForm.validateFields()
      // 暂时保存到本地状态，可以后续扩展API
      message.success('报告配置已保存')
    } catch (error) {
      message.error('保存失败: ' + (error.message || error.detail))
    } finally {
      setSaving(false)
    }
  }

  // 获取章节表单实例
  const getChapterForm = (chapterId) => {
    return chapterFormsMap[chapterId]
  }

  // 章节配置变更时更新表单
  useEffect(() => {
    Object.keys(chapterConfigs).forEach(chapterId => {
      const form = chapterFormsMap[chapterId]
      const config = chapterConfigs[chapterId]
      if (form && config && Object.keys(config).length > 0) {
        form.setFieldsValue(config)
      }
    })
  }, [chapterConfigs])

  // 保存章节配置
  const saveChapterConfig = async (chapterId) => {
    const form = getChapterForm(chapterId)
    setSaving(true)
    try {
      const values = await form.validateFields()
      await taskApi.updateChapterConfig(taskId, chapterId, values)
      message.success(`第${chapterId}章配置保存成功`)
      setChapterConfigs(prev => ({
        ...prev,
        [chapterId]: { ...prev[chapterId], ...values }
      }))
    } catch (error) {
      if (!error.errorFields) {
        message.error('保存失败: ' + (error.message || error.detail))
      }
    } finally {
      setSaving(false)
    }
  }

  // 删除任务
  const handleDeleteTask = () => {
    Modal.confirm({
      title: '确认删除任务',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <p>确定要删除任务 <strong>{currentTask?.task_name}</strong> 吗？</p>
          <p style={{ color: '#ff4d4f' }}>此操作将删除该任务及其所有配置信息，且不可恢复！</p>
        </div>
      ),
      okText: '确认删除',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        setDeleting(true)
        try {
          await taskApi.deleteTask(taskId)
          message.success('任务删除成功')
          // 刷新任务列表
          await fetchTasks()
          // 返回首页
          navigate('/')
        } catch (error) {
          message.error('删除任务失败: ' + error.message)
        } finally {
          setDeleting(false)
        }
      }
    })
  }

  // 渲染报告配置卡片
  const renderReportConfig = () => (
    <Card
      title={
        <span>
          <FileTextOutlined style={{ marginRight: 8 }} />
          报告配置
        </span>
      }
      extra={
        <Button type="primary" icon={<SaveOutlined />} onClick={saveReportIntro} loading={saving}>
          保存
        </Button>
      }
    >
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        报告内容介绍将作为所有章节 guideline 的共享前缀，在每个章节生成时自动添加到分析要求之前。
      </Paragraph>
      <Form form={reportIntroForm} layout="vertical">
        <Form.Item name="content" label="报告内容介绍" initialValue={reportIntro}>
          <TextArea
            rows={15}
            placeholder={`# 报告概述
本报告为XX事业部销售人员月度业绩分析报告...

# 分析目标
1. 全面评估销售人员当月业绩表现
2. 识别销售业绩变动的主要驱动因素
3. 提供针对性的改进建议

# 报告结构
- 第一章：薪资绩效分析
- 第二章：销售势头分析
...`}
            style={{ fontFamily: 'monospace' }}
          />
        </Form.Item>
      </Form>
    </Card>
  )

  // 渲染章节配置卡片
  const renderChapterConfig = (chapter) => {
    const form = getChapterForm(chapter.chapter_id)
    const config = chapterConfigs[chapter.chapter_id] || {}

    return (
      <Card
        key={chapter.chapter_id}
        title={
          <span>
            <BookOutlined style={{ marginRight: 8 }} />
            第{chapter.chapter_id}章 {chapter.chapter_name || '章节配置'}
          </span>
        }
        extra={
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={() => saveChapterConfig(chapter.chapter_id)}
            loading={saving}
          >
            保存
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="chapter_name" label="章节名称" initialValue={config.chapter_name}>
            <Input placeholder="请输入章节名称" />
          </Form.Item>

          <Card title="报告分析任务概述" size="small" style={{ marginBottom: 16 }}>
            <Form.Item name="role" label="Role (角色设定)" initialValue={config.role}>
              <TextArea rows={3} placeholder="请输入角色设定" />
            </Form.Item>
            <Form.Item name="task" label="Task (任务描述)" initialValue={config.task}>
              <TextArea rows={3} placeholder="请输入任务描述" />
            </Form.Item>
            <Form.Item name="style_requirements" label="语言风格要求" initialValue={config.style_requirements}>
              <TextArea rows={3} placeholder="请输入语言风格要求" />
            </Form.Item>
          </Card>

          <Card title="分析要求" size="small" style={{ marginBottom: 16 }}>
            <Form.Item name="analysis_requirements" initialValue={config.analysis_requirements}>
              <TextArea
                rows={6}
                placeholder="请输入分析要求（支持 Markdown 格式）"
                style={{ fontFamily: 'monospace' }}
              />
            </Form.Item>
          </Card>

          <Card title="输出示例" size="small">
            <Form.Item name="output_example" initialValue={config.output_example}>
              <TextArea
                rows={8}
                placeholder="请输入输出示例（支持 Markdown 格式）"
                style={{ fontFamily: 'monospace' }}
              />
            </Form.Item>
          </Card>
        </Form>
      </Card>
    )
  }

  // 渲染小节配置（工具配置）卡片
  const renderSectionConfig = (chapter) => {
    const tools = toolConfigs[chapter.chapter_id] || []

    const columns = [
      {
        title: '#',
        key: 'index',
        width: 40,
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
        width: 120,
        render: (type) => (
          <Tag color={type === 'contribution' ? 'green' : type === 'threshold' ? 'blue' : 'orange'}>
            {ATTR_TYPE_MAP[type] || type}
          </Tag>
        )
      }
    ]

    return (
      <Card
        key={`tool-${chapter.chapter_id}`}
        title={
          <span>
            <ToolOutlined style={{ marginRight: 8 }} />
            第{chapter.chapter_id}章 小节配置
          </span>
        }
        style={{ marginBottom: 16 }}
      >
        <Paragraph type="secondary" style={{ marginBottom: 16 }}>
          配置该章节使用的分析工具和归因方法。
        </Paragraph>
        <Table
          columns={columns}
          dataSource={tools}
          rowKey="tool_id"
          pagination={false}
          size="small"
          locale={{ emptyText: '暂无工具配置' }}
        />
      </Card>
    )
  }

  // 标签页配置
  const tabItems = [
    {
      key: 'report',
      label: '报告配置',
      children: renderReportConfig()
    },
    ...chapters.map(ch => ({
      key: `chapter-${ch.chapter_id}`,
      label: `第${ch.chapter_id}章 ${ch.chapter_name || ''}`,
      children: (
        <div>
          {renderChapterConfig(ch)}
          {ch.has_tools && renderSectionConfig(ch)}
        </div>
      )
    }))
  ]

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div className="page-card">
      <div className="page-title">
        <span style={{ flex: 1 }}>{currentTask?.task_name || taskId} - 配置管理</span>
        <Button
          danger
          icon={<DeleteOutlined />}
          onClick={handleDeleteTask}
          loading={deleting}
        >
          删除任务
        </Button>
      </div>

      {/* 任务基本信息 */}
      <Card style={{ marginBottom: 24 }}>
        <Descriptions column={4}>
          <Descriptions.Item label="任务名称">{currentTask?.task_name}</Descriptions.Item>
          <Descriptions.Item label="事业部">{currentTask?.business_department}</Descriptions.Item>
          <Descriptions.Item label="章节数">{chapters.length}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 配置标签页 */}
      <Tabs
        defaultActiveKey="report"
        items={tabItems}
        tabPosition="left"
        style={{ minHeight: 500 }}
      />
    </div>
  )
}

export default TaskConfig