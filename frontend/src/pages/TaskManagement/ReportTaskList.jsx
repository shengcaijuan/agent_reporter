// 报告任务管理页面
import { useState, useEffect } from 'react'
import {
  Table, Button, Modal, Form, Input, message, Popconfirm, Space, Tag, Card
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, SettingOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import useTaskStore from '../../stores/taskStore'

function ReportTaskList() {
  const navigate = useNavigate()
  const {
    tasks, loading, saving, fetchTasks, createTask, updateTask, deleteTask
  } = useTaskStore()

  const [modalVisible, setModalVisible] = useState(false)
  const [editingTask, setEditingTask] = useState(null)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  // 打开新建/编辑弹窗
  const handleOpenModal = (task = null) => {
    setEditingTask(task)
    if (task) {
      form.setFieldsValue(task)
    } else {
      form.resetFields()
    }
    setModalVisible(true)
  }

  // 关闭弹窗
  const handleCloseModal = () => {
    setModalVisible(false)
    setEditingTask(null)
    form.resetFields()
  }

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editingTask) {
        await updateTask(editingTask.task_id, values)
        message.success('任务更新成功')
      } else {
        const newTask = await createTask(values)
        message.success('任务创建成功')
        // 创建成功后跳转到配置页面
        navigate(`/config/report-intro?task_id=${newTask.task_id}`)
      }
      handleCloseModal()
    } catch (error) {
      // 错误已在store中处理
    }
  }

  // 删除任务
  const handleDelete = async (taskId) => {
    try {
      await deleteTask(taskId)
      message.success('任务删除成功')
    } catch (error) {
      // 错误已在store中处理
    }
  }

  // 跳转到配置页面
  const handleConfig = (taskId) => {
    navigate(`/config/report-intro?task_id=${taskId}`)
  }

  // 表格列定义
  const columns = [
    {
      title: '任务名称',
      dataIndex: 'task_name',
      key: 'task_name',
      width: 200,
    },
    {
      title: '事业部',
      dataIndex: 'business_department',
      key: 'business_department',
      width: 180,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '章节数',
      dataIndex: 'chapters',
      key: 'chapters',
      width: 80,
      align: 'center',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      align: 'center',
      render: (status) => (
        <Tag color={status === 'active' ? 'green' : 'default'}>
          {status === 'active' ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time) => time ? new Date(time).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<SettingOutlined />}
            onClick={() => handleConfig(record.task_id)}
          >
            配置
          </Button>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleOpenModal(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除此任务吗？"
            description="删除后将无法恢复相关配置"
            onConfirm={() => handleDelete(record.task_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              loading={saving}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="page-card">
      <div className="page-title">
        <span>报告任务管理</span>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => handleOpenModal()}
        >
          新建任务
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="task_id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>

      {/* 新建/编辑任务弹窗 */}
      <Modal
        title={editingTask ? '编辑任务' : '新建任务'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={handleCloseModal}
        confirmLoading={saving}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
        >
          <Form.Item
            name="task_name"
            label="任务名称"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="例如：马上住事业部销售报告" />
          </Form.Item>

          <Form.Item
            name="business_department"
            label="事业部"
            rules={[{ required: true, message: '请输入事业部名称' }]}
          >
            <Input placeholder="例如：马上住焕新事业部" />
          </Form.Item>

          <Form.Item
            name="description"
            label="任务描述"
          >
            <Input.TextArea
              rows={3}
              placeholder="请输入任务描述..."
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ReportTaskList