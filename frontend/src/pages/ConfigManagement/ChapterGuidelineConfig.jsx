// 章节分析要求配置页面（支持任务选择）
import { useState, useEffect } from 'react'
import {
  Tabs, Form, Input, Button, message, Spin, Card, Select, Steps
} from 'antd'
import {
  SaveOutlined, ReloadOutlined, ArrowLeftOutlined, ArrowRightOutlined
} from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import useTaskStore from '../../stores/taskStore'
import { taskApi } from '../../api/task'

const { TextArea } = Input

function ChapterGuidelineConfig() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const taskId = searchParams.get('task_id')

  const { tasks, currentTask, fetchTasks, fetchTask } = useTaskStore()

  const [chapters, setChapters] = useState([])
  const [currentChapter, setCurrentChapter] = useState(1)
  const [chapterConfig, setChapterConfig] = useState(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const [form] = Form.useForm()

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  useEffect(() => {
    if (taskId) {
      loadTaskData()
    }
  }, [taskId])

  useEffect(() => {
    if (chapterConfig) {
      form.setFieldsValue(chapterConfig)
    }
  }, [chapterConfig])

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

      // 加载当前章节配置
      await loadChapterConfig(currentChapter)
    } catch (error) {
      message.error('加载数据失败: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const loadChapterConfig = async (chapterId) => {
    if (!taskId) return
    try {
      const response = await taskApi.getChapterConfig(taskId, chapterId)
      setChapterConfig(response.data)
      form.setFieldsValue(response.data)
    } catch (error) {
      console.error('加载章节配置失败:', error)
      setChapterConfig(null)
    }
  }

  // 章节选项卡
  const tabItems = chapters.map(ch => ({
    key: ch.chapter_id.toString(),
    label: `第${ch.chapter_id}章 ${ch.chapter_name}`
  }))

  // 切换章节
  const handleTabChange = (key) => {
    const newChapterId = parseInt(key)
    setCurrentChapter(newChapterId)
    loadChapterConfig(newChapterId)
  }

  // 保存配置
  const handleSave = async () => {
    if (!taskId) {
      message.error('请先选择任务')
      return
    }

    try {
      const values = await form.validateFields()
      setSaving(true)

      await taskApi.updateChapterConfig(taskId, currentChapter, {
        ...values,
        chapter_id: currentChapter
      })

      message.success('配置保存成功')
      setChapterConfig(values)
    } catch (error) {
      if (error.errorFields) {
        message.error('请检查表单填写')
      } else {
        message.error('保存失败: ' + error.message)
      }
    } finally {
      setSaving(false)
    }
  }

  // 重置表单
  const handleReset = () => {
    if (chapterConfig) {
      form.setFieldsValue(chapterConfig)
    }
  }

  // 任务选择变更
  const handleTaskChange = (newTaskId) => {
    navigate(`/config/chapter?task_id=${newTaskId}`)
  }

  const handlePrev = () => {
    navigate(`/config/report-intro?task_id=${taskId}`)
  }

  const handleNext = () => {
    handleSave()
    navigate(`/config/tool?task_id=${taskId}`)
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
        <span>章节分析要求配置 - {currentTask?.task_name || taskId}</span>
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
          current={2}
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
        <Form
          form={form}
          layout="vertical"
          style={{ marginTop: 24 }}
        >
          <Card title="基本信息" style={{ marginBottom: 16 }}>
            <Form.Item name="chapter_name" label="章节名称">
              <Input placeholder="请输入章节名称" />
            </Form.Item>
          </Card>

          <Card title="报告分析任务概述" style={{ marginBottom: 16 }}>
            <Form.Item name="role" label="Role (角色设定)">
              <TextArea
                rows={4}
                placeholder="请输入角色设定"
              />
            </Form.Item>

            <Form.Item name="task" label="Task (任务描述)">
              <TextArea
                rows={4}
                placeholder="请输入任务描述"
              />
            </Form.Item>

            <Form.Item name="style_requirements" label="语言风格要求">
              <TextArea
                rows={4}
                placeholder="请输入语言风格要求"
              />
            </Form.Item>
          </Card>

          <Card title="分析要求" style={{ marginBottom: 16 }}>
            <Form.Item name="analysis_requirements">
              <TextArea
                rows={8}
                placeholder="请输入分析要求（支持 Markdown 格式）"
                style={{ fontFamily: 'monospace' }}
              />
            </Form.Item>
          </Card>

          <Card title="输出示例" style={{ marginBottom: 16 }}>
            <Form.Item name="output_example">
              <TextArea
                rows={10}
                placeholder="请输入输出示例（支持 Markdown 格式）"
                style={{ fontFamily: 'monospace' }}
              />
            </Form.Item>
          </Card>

          <div style={{ textAlign: 'right' }}>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
              style={{ marginRight: 8 }}
            >
              重置
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={saving}
              onClick={handleSave}
            >
              保存配置
            </Button>
          </div>
        </Form>
      </Spin>

      {/* 操作按钮 */}
      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={handlePrev}
          style={{ marginRight: 8 }}
        >
          上一步：报告介绍
        </Button>
        <Button
          type="primary"
          icon={<ArrowRightOutlined />}
          onClick={handleNext}
        >
          下一步：工具配置
        </Button>
      </div>
    </div>
  )
}

export default ChapterGuidelineConfig