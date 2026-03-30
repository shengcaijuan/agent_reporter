// 小节配置项组件
import { Form, Input, Button, Space } from 'antd'
import { DeleteOutlined } from '@ant-design/icons'

const { TextArea } = Input

function SectionConfigItem({ section, index, onUpdate, onDelete }) {
  const handleFieldChange = (field, value) => {
    onUpdate(index, { ...section, [field]: value })
  }

  const handleRequirementChange = (reqIndex, value) => {
    const newRequirements = [...(section.requirements || [])]
    newRequirements[reqIndex] = value
    onUpdate(index, { ...section, requirements: newRequirements })
  }

  const addRequirement = () => {
    const newRequirements = [...(section.requirements || []), '']
    onUpdate(index, { ...section, requirements: newRequirements })
  }

  const deleteRequirement = (reqIndex) => {
    const newRequirements = (section.requirements || []).filter((_, i) => i !== reqIndex)
    onUpdate(index, { ...section, requirements: newRequirements })
  }

  return (
    <div style={{
      border: '1px solid #d9d9d9',
      borderRadius: 6,
      padding: 16,
      marginBottom: 12,
      background: '#fafafa'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <span style={{ fontWeight: 500 }}>小节 {index + 1}</span>
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={() => onDelete(index)}
        >
          删除小节
        </Button>
      </div>

      <Form.Item label="小节名称" style={{ marginBottom: 12 }}>
        <Input
          value={section.section_name || ''}
          onChange={(e) => handleFieldChange('section_name', e.target.value)}
          placeholder="请输入小节名称"
        />
      </Form.Item>

      <div style={{ marginBottom: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontWeight: 500 }}>分析要求</span>
          <Button type="link" onClick={addRequirement}>
            + 添加要求
          </Button>
        </div>
        {(section.requirements || []).map((req, reqIndex) => (
          <div key={reqIndex} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <TextArea
              value={req}
              onChange={(e) => handleRequirementChange(reqIndex, e.target.value)}
              placeholder={`要求 ${reqIndex + 1}`}
              autoSize={{ minRows: 1, maxRows: 3 }}
              style={{ flex: 1 }}
            />
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => deleteRequirement(reqIndex)}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

export default SectionConfigItem