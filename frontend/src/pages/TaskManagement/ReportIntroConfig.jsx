// 报告内容介绍配置页面
import { useState, useEffect } from 'react'
import {
  Card, Button, message, Spin, Input, Typography, Descriptions, Steps
} from 'antd'
import {
  SaveOutlined, ArrowLeftOutlined, ArrowRightOutlined
} from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { taskApi } from '../../api/task'
import useTaskStore from '../../stores/taskStore'

const { TextArea } = Input
const { Title, Paragraph } = Typography

function ReportIntroConfig() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const taskId = searchParams.get('task_id')

  const { currentTask, fetchTask } = useTaskStore()
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (taskId) {
      loadTaskData()
    }
  }, [taskId])

  const loadTaskData = async () => {
    setLoading(true)
    try {
      // 加载任务信息
      if (!currentTask || currentTask.task_id !== taskId) {
        await fetchTask(taskId)
      }

      // 加载报告介绍
      const response = await taskApi.getReportIntro(taskId)
      setContent(response.data?.content || '')
    } catch (error) {
      message.error('加载数据失败: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!taskId) {
      message.error('任务ID不存在')
      return
    }

    setSaving(true)
    try {
      await taskApi.updateReportIntro(taskId, content)
      message.success('保存成功')
    } catch (error) {
      message.error('保存失败: ' + error.message)
    } finally {
      setSaving(false)
    }
  }

  const handlePrev = () => {
    navigate('/config/tasks')
  }

  const handleNext = () => {
    handleSave()
    navigate(`/config/chapter?task_id=${taskId}`)
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!taskId) {
    return (
      <div className="page-card">
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <Title level={4}>请先选择一个任务</Title>
          <Button type="primary" onClick={() => navigate('/config/tasks')}>
            返回任务列表
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="page-card">
      <div className="page-title">
        <span>报告内容介绍 - {currentTask?.task_name || taskId}</span>
      </div>

      {/* 配置步骤指引 */}
      <Card style={{ marginBottom: 24 }}>
        <Steps
          current={1}
          items={[
            { title: '新建任务', description: '创建报告任务' },
            { title: '报告介绍', description: '配置共享内容' },
            { title: '章节配置', description: '配置分析要求' },
            { title: '工具配置', description: '配置工具函数' },
          ]}
        />
      </Card>

      {/* 任务信息 */}
      <Card title="任务信息" style={{ marginBottom: 24 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="任务名称">{currentTask?.task_name}</Descriptions.Item>
          <Descriptions.Item label="事业部">{currentTask?.business_department}</Descriptions.Item>
          <Descriptions.Item label="章节数">{currentTask?.report_structure?.total_chapters || 6}</Descriptions.Item>
          <Descriptions.Item label="状态">
            {currentTask?.status === 'active' ? '启用' : '禁用'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 报告内容介绍编辑器 */}
      <Card
        title="报告内容介绍"
        extra={
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={saving}
          >
            保存
          </Button>
        }
      >
        <Paragraph type="secondary" style={{ marginBottom: 16 }}>
          报告内容介绍将作为所有章节 guideline 的共享前缀，在每个章节生成时自动添加到分析要求之前。
          请在此填写报告的概述、分析目标、报告结构等公共内容。
        </Paragraph>

        <TextArea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={`# 报告概述
本报告为三棵树XX事业部销售人员月度业绩分析报告...

# 分析目标
1. 全面评估销售人员当月业绩表现
2. 识别销售业绩变动的主要驱动因素
3. 提供针对性的改进建议

# 报告结构
- 第一章：薪资绩效分析
- 第二章：销售势头分析
...`}
          rows={20}
          style={{
            fontFamily: 'Monaco, Menlo, Ubuntu Mono, monospace',
            fontSize: 14
          }}
        />
      </Card>

      {/* 操作按钮 */}
      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={handlePrev}
          style={{ marginRight: 8 }}
        >
          返回任务列表
        </Button>
        <Button
          type="primary"
          icon={<ArrowRightOutlined />}
          onClick={handleNext}
        >
          下一步：章节配置
        </Button>
      </div>
    </div>
  )
}

export default ReportIntroConfig