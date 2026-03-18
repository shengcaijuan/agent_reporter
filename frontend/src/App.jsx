import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import MainLayout from './components/Layout/MainLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import ReportGeneration from './pages/ReportGeneration'
import ProgressMonitor from './pages/ProgressMonitor'
import ReportList from './pages/ReportList'
import ReportDetail from './pages/ReportDetail'

// 任务管理相关页面
import TaskConfig from './pages/TaskManagement/TaskConfig'
import TaskConfigPage from './pages/TaskManagement/TaskConfigPage'
import ReportIntroConfig from './pages/TaskManagement/ReportIntroConfig'
import ChapterGuidelineConfig from './pages/ConfigManagement/ChapterGuidelineConfig'
import ToolAgentConfig from './pages/ConfigManagement/ToolAgentConfig'

// 模型配置页面
import ModelConfig from './pages/ModelConfig'

// 模板库页面
import TemplateLibrary from './pages/TemplateLibrary'

function App() {
  const { isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          {/* 配置管理路由 */}
          <Route path="config/task/:taskId" element={<TaskConfig />} />
          {/* 统一配置页面 */}
          <Route path="config/task-config" element={<TaskConfigPage />} />
          <Route path="config/report-intro" element={<ReportIntroConfig />} />
          <Route path="config/chapter" element={<ChapterGuidelineConfig />} />
          <Route path="config/tool" element={<ToolAgentConfig />} />
          {/* 报告生成相关路由 */}
          <Route path="generation" element={<ReportGeneration />} />
          <Route path="progress" element={<ProgressMonitor />} />
          <Route path="progress/:batchId" element={<ProgressMonitor />} />
          <Route path="reports" element={<ReportList />} />
          <Route path="reports/:reportId" element={<ReportDetail />} />
          {/* 模板库路由 */}
          <Route path="templates" element={<TemplateLibrary />} />
          {/* 模型配置路由 */}
          <Route path="model-config" element={<ModelConfig />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App