import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import './index.css'

// 主题配置 - 绿白色调
const theme = {
  token: {
    colorPrimary: '#008425',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#008425',
    borderRadius: 6,
  },
  components: {
    Menu: {
      darkItemBg: '#006d1f',
      darkItemSelectedBg: '#008425',
      darkItemHoverBg: '#00a831',
    },
    Layout: {
      headerBg: '#008425',
      siderBg: '#006d1f',
    },
    Button: {
      primaryColor: '#fff',
    }
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider theme={theme} locale={zhCN}>
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)