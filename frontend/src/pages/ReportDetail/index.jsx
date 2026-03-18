// 报告详情页面
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card, Descriptions, Button, Space, Tag, Tabs, Empty, Spin, message
} from 'antd'
import {
  ArrowLeftOutlined,
  DownloadOutlined,
  FilePdfOutlined,
  FileTextOutlined,
  FileMarkdownOutlined
} from '@ant-design/icons'
import { reportApi } from '../../api/report'

function ReportDetail() {
  const { reportId } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [detail, setDetail] = useState(null)
  const [activeChapter, setActiveChapter] = useState('1')

  useEffect(() => {
    loadDetail()
  }, [reportId])

  const loadDetail = async () => {
    setLoading(true)
    try {
      const result = await reportApi.getDetail(reportId)
      setDetail(result)
    } catch (error) {
      console.error('加载报告详情失败:', error)
      message.error('加载报告详情失败')
    } finally {
      setLoading(false)
    }
  }

  // 下载报告
  const handleDownload = async (fileType) => {
    try {
      const result = await reportApi.getDownloadUrl(reportId, fileType)
      if (result.download_url) {
        window.open(result.download_url, '_blank')
      } else {
        message.error('文件不存在')
      }
    } catch (error) {
      message.error('下载失败')
    }
  }

  // 章节选项卡
  const chapterTabs = [
    { key: '1', label: '1. 薪资绩效分析' },
    { key: '2', label: '2. 销售动能分析' },
    { key: '3', label: '3. 毛利率分析' },
    { key: '4', label: '4. 费用分析' },
    { key: '5', label: '5. 行销行为分析' },
    { key: '6', label: '6. 总结' }
  ]

  if (loading) {
    return (
      <div className="page-card" style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!detail) {
    return (
      <div className="page-card">
        <Empty description="报告不存在" />
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Button onClick={() => navigate('/reports')}>返回列表</Button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-card">
        <div className="page-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>报告详情 - {detail.sale_name} ({detail.job_id})</span>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/reports')}>
            返回列表
          </Button>
        </div>

        {/* 基本信息 */}
        <Descriptions bordered column={3} style={{ marginBottom: 24 }}>
          <Descriptions.Item label="姓名">{detail.sale_name}</Descriptions.Item>
          <Descriptions.Item label="工号">{detail.job_id}</Descriptions.Item>
          <Descriptions.Item label="省区">{detail.province}</Descriptions.Item>
          <Descriptions.Item label="大区">{detail.region}</Descriptions.Item>
          <Descriptions.Item label="事业部">{detail.business_department}</Descriptions.Item>
          <Descriptions.Item label="岗位">{detail.sale_class}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={detail.status === 'completed' ? 'success' : 'error'}>
              {detail.status === 'completed' ? '已完成' : '失败'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="生成时间">
            {detail.generated_time ? new Date(detail.generated_time).toLocaleString() : '-'}
          </Descriptions.Item>
        </Descriptions>

        {/* 下载按钮 */}
        <Space style={{ marginBottom: 24 }}>
          <Button
            type="primary"
            icon={<FilePdfOutlined />}
            onClick={() => handleDownload('pdf')}
          >
            下载 PDF
          </Button>
          <Button
            icon={<FileTextOutlined />}
            onClick={() => handleDownload('html')}
          >
            下载 HTML
          </Button>
          <Button
            icon={<FileMarkdownOutlined />}
            onClick={() => handleDownload('md')}
          >
            下载 Markdown
          </Button>
        </Space>
      </div>

      {/* 报告预览 */}
      <div className="page-card">
        <div className="page-title">报告预览</div>

        <Tabs
          activeKey={activeChapter}
          onChange={setActiveChapter}
          items={chapterTabs}
        />

        {detail.pdf_path ? (
          <div className="report-preview">
            <iframe
              src={detail.pdf_path}
              title="报告预览"
            />
          </div>
        ) : (
          <Empty description="报告文件不可用" />
        )}
      </div>
    </div>
  )
}

export default ReportDetail