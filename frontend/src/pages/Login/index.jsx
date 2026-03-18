// 登录页面
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { Button, Form, Input, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'

function Login() {
  const navigate = useNavigate()
  const { login, loading } = useAuthStore()
  const [form] = Form.useForm()

  const handleSubmit = async (values) => {
    const success = await login(values.username, values.password)
    if (success) {
      message.success('登录成功')
      navigate('/')
    }
  }

  return (
    <div className="login-container">
      {/* 半透明水印 */}
      <span className="watermark watermark-top">3trees</span>
      <span className="watermark watermark-bottom">3trees</span>

      <div className="login-card">
        {/* Logo */}
        <div className="login-logo">
          <img src="/assets/logo.svg" alt="三棵树" />
        </div>

        <h1 className="login-title">三棵树智能销售报告系统</h1>

        <Form
          form={form}
          onFinish={handleSubmit}
          layout="vertical"
          autoComplete="off"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="用户名"
              size="large"
            />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
              size="large"
            />
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              loading={loading}
              block
            >
              登 录
            </Button>
          </Form.Item>
        </Form>
        <div style={{ textAlign: 'center', color: '#999', fontSize: 12 }}>
          © 2026 三棵树涂料股份有限公司 | 技术支持：帆软软件
        </div>
      </div>
    </div>
  )
}

export default Login