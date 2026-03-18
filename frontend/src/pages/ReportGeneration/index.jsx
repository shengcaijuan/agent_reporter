// 报告生成页面
import {
    PlayCircleOutlined,
    TeamOutlined,
    UserOutlined
} from '@ant-design/icons'
import {
    Alert,
    Button,
    Card,
    Col,
    Divider,
    Form,
    Input,
    InputNumber,
    message,
    Radio,
    Row,
    Select,
    Space,
    Statistic,
    Table, Tag
} from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { taskApi } from '../../api/task'
import { useProgressStore } from '../../stores/progressStore'
import useTaskStore from '../../stores/taskStore'

const { Option } = Select
const { Search } = Input

function ReportGeneration() {
  const navigate = useNavigate()
  const { startGeneration } = useProgressStore()
  const { tasks, fetchTasks } = useTaskStore()
  const [form] = Form.useForm()

  const [loading, setLoading] = useState(false)
  const [selectedTask, setSelectedTask] = useState(null)
  const [salesList, setSalesList] = useState([])
  const [filteredSales, setFilteredSales] = useState([])
  const [filterOptions, setFilterOptions] = useState({
    regions: [],
    provinces: [],
    sale_classes: []
  })
  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const [filterType, setFilterType] = useState('all')
  const [searchText, setSearchText] = useState('')
  const [filterRegion, setFilterRegion] = useState(null)
  const [filterProvince, setFilterProvince] = useState(null)
  const [filterSaleClass, setFilterSaleClass] = useState(null)

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  // 加载销售人员数据
  const loadSalesData = async (taskId) => {
    if (!taskId) return
    setLoading(true)
    try {
      const response = await taskApi.getSales(taskId)
      const data = response.data
      setSalesList(data.sales || [])
      setFilteredSales(data.sales || [])
      setFilterOptions(data.filters || { regions: [], provinces: [], sale_classes: [] })
      setSelectedRowKeys([])
    } catch (error) {
      message.error('加载销售人员数据失败: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  // 任务选择变更
  const handleTaskChange = (taskId) => {
    setSelectedTask(taskId)
    loadSalesData(taskId)
    // 重置筛选条件
    setSearchText('')
    setFilterRegion(null)
    setFilterProvince(null)
    setFilterSaleClass(null)
    setFilterType('all')
  }

  // 应用筛选条件
  const applyFilters = async () => {
    if (!selectedTask) return
    setLoading(true)
    try {
      const params = {}
      if (searchText) params.search = searchText
      if (filterRegion) params.region = filterRegion
      if (filterProvince) params.province = filterProvince
      if (filterSaleClass) params.sale_class = filterSaleClass

      const response = await taskApi.getSales(selectedTask, params)
      setFilteredSales(response.data.sales || [])
      setSelectedRowKeys([])
    } catch (error) {
      message.error('筛选失败: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  // 搜索和筛选变化时重新加载
  useEffect(() => {
    if (selectedTask) {
      applyFilters()
    }
  }, [searchText, filterRegion, filterProvince, filterSaleClass])

  // 筛选类型改变
  const handleFilterTypeChange = (e) => {
    const type = e.target.value
    setFilterType(type)
    if (type === 'all') {
      setSelectedRowKeys([])
    }
  }

  // 开始生成
  const handleGenerate = async () => {
    try {
      const values = await form.validateFields()
      setLoading(true)

      // 根据筛选类型确定销售人员
      let saleIds = []
      if (filterType === 'specific') {
        saleIds = selectedRowKeys
      }

      const params = {
        task_id: selectedTask,
        time: String(values.time),  // 转换为字符串
        max_concurrent: values.max_concurrent,
        sale_filter: {
          type: filterType,
          job_ids: saleIds,
          region: filterRegion,
          province: filterProvince,
          sale_class: filterSaleClass
        }
      }

      // 获取任务名称
      const selectedTaskInfo = tasks.find(t => t.task_id === selectedTask)
      const taskName = selectedTaskInfo?.task_name || selectedTask

      // 启动生成，传入任务名称
      const result = await startGeneration(params, taskName)
      message.success('任务已启动')

      // 跳转到带 batchId 的进度页面
      navigate(`/progress/${result.batch_id}`)
    } catch (error) {
      message.error(error.detail || '启动失败')
    } finally {
      setLoading(false)
    }
  }

  // 表格列定义
  const columns = [
    {
      title: '工号',
      dataIndex: 'job_id',
      key: 'job_id',
      width: 100
    },
    {
      title: '姓名',
      dataIndex: 'sale_name',
      key: 'sale_name',
      width: 100
    },
    {
      title: '岗位',
      dataIndex: 'sale_class',
      key: 'sale_class',
      width: 140,
      render: (text) => text ? <Tag color="blue">{text}</Tag> : '-'
    },
    {
      title: '省区',
      dataIndex: 'province',
      key: 'province',
      width: 120,
      ellipsis: true
    },
    {
      title: '大区',
      dataIndex: 'region',
      key: 'region',
      width: 100,
      ellipsis: true
    },
    {
      title: '城市运营分部',
      dataIndex: 'city_operation_department',
      key: 'city_operation_department',
      ellipsis: true
    }
  ]

  // 行选择配置
  const rowSelection = {
    selectedRowKeys,
    onChange: (keys) => setSelectedRowKeys(keys),
    getCheckboxProps: (record) => ({
      disabled: filterType !== 'specific'
    })
  }

  return (
    <div className="page-card">
      <div className="page-title">报告生成</div>

      <Form
        form={form}
        layout="vertical"
        initialValues={{
          time: '202601',
          max_concurrent: 50
        }}
      >
        <Card title="生成参数配置" style={{ marginBottom: 16 }}>
          <Row gutter={24}>
            <Col span={8}>
              <Form.Item
                name="task"
                label="选择任务"
                rules={[{ required: true, message: '请选择任务' }]}
              >
                <Select
                  placeholder="选择报告任务"
                  onChange={handleTaskChange}
                  loading={loading}
                >
                  {tasks.map(task => (
                    <Option key={task.task_id} value={task.task_id}>
                      {task.task_name || task.task_id}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="time"
                label="分析月份"
                rules={[{ required: true, message: '请选择分析月份' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="如: 202601"
                  min={202001}
                  max={209912}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="max_concurrent"
                label="并发等级（数量）"
                tooltip="同时生成报告的数量上线"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={1}
                  max={100}
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {selectedTask && (
          <Card title="销售人员选择" style={{ marginBottom: 16 }}>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Search
                  placeholder="搜索姓名或工号"
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  onSearch={applyFilters}
                  allowClear
                />
              </Col>
              <Col span={4}>
                <Select
                  placeholder="选择大区"
                  value={filterRegion}
                  onChange={setFilterRegion}
                  allowClear
                  style={{ width: '100%' }}
                >
                  {filterOptions.regions.map(r => (
                    <Option key={r} value={r}>{r}</Option>
                  ))}
                </Select>
              </Col>
              <Col span={4}>
                <Select
                  placeholder="选择省区"
                  value={filterProvince}
                  onChange={setFilterProvince}
                  allowClear
                  style={{ width: '100%' }}
                >
                  {filterOptions.provinces.map(p => (
                    <Option key={p} value={p}>{p}</Option>
                  ))}
                </Select>
              </Col>
              <Col span={4}>
                <Select
                  placeholder="选择岗位"
                  value={filterSaleClass}
                  onChange={setFilterSaleClass}
                  allowClear
                  style={{ width: '100%' }}
                >
                  {filterOptions.sale_classes.map(s => (
                    <Option key={s} value={s}>{s}</Option>
                  ))}
                </Select>
              </Col>
            </Row>

            <Divider />

            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={12}>
                <Radio.Group value={filterType} onChange={handleFilterTypeChange}>
                  <Radio value="all">全部销售人员</Radio>
                  <Radio value="filter">使用筛选结果</Radio>
                  <Radio value="specific">指定销售人员</Radio>
                </Radio.Group>
              </Col>
              <Col span={12} style={{ textAlign: 'right' }}>
                <Space size="large">
                  <Statistic
                    title="总人数"
                    value={salesList.length}
                    prefix={<TeamOutlined />}
                  />
                  <Statistic
                    title="筛选结果"
                    value={filteredSales.length}
                    prefix={<UserOutlined />}
                    valueStyle={{ color: '#1890ff' }}
                  />
                  {filterType === 'specific' && (
                    <Statistic
                      title="已选择"
                      value={selectedRowKeys.length}
                      prefix={<UserOutlined />}
                      valueStyle={{ color: '#52c41a' }}
                    />
                  )}
                </Space>
              </Col>
            </Row>

            <Table
              columns={columns}
              dataSource={filteredSales}
              rowKey="job_id"
              loading={loading}
              rowSelection={rowSelection}
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条`
              }}
              scroll={{ x: 800 }}
              size="small"
            />

            <Divider />

            <Space>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                loading={loading}
                onClick={handleGenerate}
                disabled={!selectedTask}
              >
                开始生成
              </Button>
            </Space>
          </Card>
        )}

        {!selectedTask && (
          <Alert
            message="请先选择一个报告任务"
            description="选择任务后将显示销售人员列表"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
      </Form>
    </div>
  )
}

export default ReportGeneration