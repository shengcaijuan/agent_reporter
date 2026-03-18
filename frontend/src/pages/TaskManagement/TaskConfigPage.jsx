// 报告任务配置主页面
import { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Card, Button, message, Spin, Typography, Form, Modal
} from 'antd'
import {
  SaveOutlined, PlusOutlined, ArrowLeftOutlined, DeleteOutlined, ExclamationCircleOutlined
} from '@ant-design/icons'
import { taskApi } from '../../api/task'
import ReportInfoSection from '../../components/TaskConfig/ReportInfoSection'
import ChapterConfigCard from '../../components/TaskConfig/ChapterConfigCard'
import WrappingConfigSection from '../../components/TaskConfig/WrappingConfigSection'
import useTaskStore from '../../stores/taskStore'

const { Title, Text } = Typography

function TaskConfigPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const taskId = searchParams.get('task_id')
  const { fetchTasks } = useTaskStore()

  // 防止 StrictMode 双重调用
  const isCreatingRef = useRef(false)

  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [taskInfo, setTaskInfo] = useState(null)
  const [chapters, setChapters] = useState([])

  const [reportForm] = Form.useForm()

  // 自动创建新任务（使用 ref 防止 StrictMode 双重调用）
  useEffect(() => {
    if (!taskId && !isCreatingRef.current) {
      isCreatingRef.current = true
      createNewTask()
    }
  }, [taskId])

  // 创建新任务
  const createNewTask = async () => {
    setLoading(true)
    try {
      const response = await taskApi.createTask({
        task_name: '新报告任务',
        business_department: '',
        description: ''
      })

      const newTaskId = response.data?.task_id
      if (!newTaskId) {
        throw new Error('创建任务失败：未返回任务ID')
      }
      message.success('任务创建成功')

      await fetchTasks()
      navigate(`/config/task-config?task_id=${newTaskId}`, { replace: true })
    } catch (error) {
      const errorMsg = error.detail || error.message || '创建任务失败'
      message.error(errorMsg)
      navigate('/')
    } finally {
      setLoading(false)
    }
  }

  // 加载数据
  useEffect(() => {
    if (taskId) {
      loadTaskData()
    }
  }, [taskId])

  const loadTaskData = async () => {
    setLoading(true)
    try {
      const taskRes = await taskApi.getTask(taskId)
      const taskData = taskRes.data
      setTaskInfo(taskData)

      reportForm.setFieldsValue({
        task_name: taskData.task_name,
        business_department: taskData.business_department,
        description: taskData.description
      })

      const chaptersRes = await taskApi.getChapters(taskId)
      setChapters(chaptersRes.data || [])
    } catch (error) {
      message.error('加载数据失败: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  // 保存报告信息
  const saveReportInfo = async () => {
    try {
      const values = await reportForm.validateFields()
      await taskApi.updateTask(taskId, values)
      message.success('报告信息保存成功')
    } catch (error) {
      if (!error.errorFields) {
        message.error('保存失败: ' + error.message)
      }
    }
  }

  // 添加章节
  const handleAddChapter = async () => {
    setSaving(true)
    try {
      const response = await taskApi.addChapter(taskId)
      const newChapter = response.data
      setChapters(prev => [...prev, newChapter])
      message.success('章节添加成功')
    } catch (error) {
      message.error('添加章节失败: ' + error.message)
    } finally {
      setSaving(false)
    }
  }

  // 删除章节
  const handleDeleteChapter = async (index) => {
    const chapter = chapters[index]
    try {
      await taskApi.deleteChapter(taskId, chapter.chapter_id)
      setChapters(prev => prev.filter((_, i) => i !== index))
      message.success('章节删除成功')
    } catch (error) {
      message.error('删除章节失败: ' + error.message)
    }
  }

  // 更新章节
  const handleUpdateChapter = (index, newChapter) => {
    setChapters(prev => {
      const newList = [...prev]
      newList[index] = newChapter
      return newList
    })
  }

  // 返回任务列表
  const handleBack = () => {
    navigate('/')
  }

  // 删除任务
  const handleDeleteTask = () => {
    Modal.confirm({
      title: '确认删除任务',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <p>确定要删除任务 <strong>{taskInfo?.task_name}</strong> 吗？</p>
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
          await fetchTasks()
          navigate('/')
        } catch (error) {
          message.error('删除任务失败: ' + error.message)
        } finally {
          setDeleting(false)
        }
      }
    })
  }

  if (!taskId) {
    return (
      <div className="page-card">
        <Spin spinning={loading} tip="正在创建任务...">
          <div style={{ height: 300 }} />
        </Spin>
      </div>
    )
  }

  return (
    <div className="page-card">
      <div className="page-title">
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={handleBack}
          style={{ marginRight: 16 }}
        >
          返回
        </Button>
        <span style={{ flex: 1 }}>
          报告任务配置 - {taskInfo?.task_name || taskId}
        </span>
        <Button
          danger
          icon={<DeleteOutlined />}
          onClick={handleDeleteTask}
          loading={deleting}
        >
          删除任务
        </Button>
      </div>

      <Spin spinning={loading}>
        {/* 报告信息配置 */}
        <Card title="报告信息" style={{ marginBottom: 24 }}>
          <ReportInfoSection
            form={reportForm}
            initialValues={{
              task_name: taskInfo?.task_name,
              business_department: taskInfo?.business_department,
              description: taskInfo?.description
            }}
          />
          <div style={{ textAlign: 'right', marginTop: 16 }}>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={saveReportInfo}
            >
              保存报告信息
            </Button>
          </div>
        </Card>

        {/* 章节配置 */}
        <Card
          title="章节配置"
          extra={
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAddChapter}
              loading={saving}
            >
              添加章节
            </Button>
          }
          style={{ marginBottom: 24 }}
        >
          {chapters.map((chapter, index) => (
            <ChapterConfigCard
              key={chapter.chapter_id}
              taskId={taskId}
              chapter={chapter}
              index={index}
              onDelete={handleDeleteChapter}
              onUpdate={handleUpdateChapter}
              canDelete={chapters.length > 1}
            />
          ))}
          {chapters.length === 0 && (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
              暂无章节，点击上方按钮添加
            </div>
          )}
        </Card>

        {/* 报告样式配置 */}
        <WrappingConfigSection
          taskId={taskId}
          chapters={chapters}
        />
      </Spin>
    </div>
  )
}

export default TaskConfigPage