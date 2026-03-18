// 报告信息配置区域组件
import { Form, Input } from 'antd'

const { TextArea } = Input

function ReportInfoSection({ form, initialValues }) {
  return (
    <Form
      form={form}
      layout="inline"
      initialValues={initialValues}
      style={{ marginBottom: 24 }}
    >
      <Form.Item
        name="task_name"
        label="任务名称"
        rules={[{ required: true, message: '请输入任务名称' }]}
        style={{ marginRight: 24, marginBottom: 0 }}
      >
        <Input placeholder="例如：马上住事业部销售报告" style={{ width: 300 }} />
      </Form.Item>

      <Form.Item
        name="business_department"
        label="所属事业部"
        rules={[{ required: true, message: '请输入事业部名称' }]}
        style={{ marginRight: 24, marginBottom: 0 }}
      >
        <Input placeholder="例如：马上住焕新事业部" style={{ width: 250 }} />
      </Form.Item>

      <Form.Item
        name="description"
        label="任务描述"
        style={{ marginBottom: 0 }}
      >
        <TextArea
          rows={1}
          placeholder="请输入任务描述..."
          style={{ width: 300 }}
        />
      </Form.Item>
    </Form>
  )
}

export default ReportInfoSection