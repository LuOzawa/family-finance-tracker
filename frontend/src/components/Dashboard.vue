<template>
  <div>
    <!-- 汇总卡片 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-label">总记录数</div>
            <div class="stat-value" style="color:#409eff">{{ records.length }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-label">总支出</div>
            <div class="stat-value" style="color:#f56c6c">¥{{ totalAmount.toFixed(2) }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-label">月均支出</div>
            <div class="stat-value" style="color:#e6a23c">¥{{ monthlyAvg }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-label">分类数</div>
            <div class="stat-value" style="color:#67c23a">{{ categoryCount }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选栏 -->
    <el-card shadow="never" style="margin-bottom:16px" body-style="padding:12px">
      <el-row :gutter="12" align="middle">
        <el-col :span="10">
          <el-date-picker
            v-model="filterDates"
            type="daterange"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            size="small"
            style="width:100%"
          />
        </el-col>
        <el-col :span="5">
          <el-select v-model="filterCategory" clearable placeholder="按分类筛选" size="small" style="width:100%">
            <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-col>
        <el-col :span="9">
          <el-button size="small" type="primary" @click="applyFilter">筛选</el-button>
          <el-button size="small" @click="resetFilter">重置</el-button>
          <el-button size="small" type="success" @click="openDialog()">+ 新增记录</el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 表格 + 图表 -->
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="hover">
          <el-table :data="records" border stripe size="small" max-height="420" v-loading="loading">
            <el-table-column prop="date" label="日期" width="115" sortable />
            <el-table-column prop="category" label="分类" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="tagType(row.category)">{{ row.category }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="金额(元)" width="110" align="right" sortable>
              <template #default="{ row }">
                <span style="color:#f56c6c;font-weight:bold">¥{{ row.amount.toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="note" label="备注" show-overflow-tooltip />
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
                <el-button link type="danger" size="small" @click="handleDelete(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>各分类支出汇总</template>
          <div ref="chartRef" style="width:100%;height:380px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editId ? '编辑记录' : '新增记录'" width="420px" :close-on-click-modal="false">
      <el-form :model="form" label-width="65px">
        <el-form-item label="日期">
          <el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width:100%" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" placeholder="请选择分类" style="width:100%">
            <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number v-model="form.amount" :min="0" :precision="2" :step="10" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" placeholder="可选" maxlength="100" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRecord">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'

const CATEGORIES = ['餐饮', '交通', '购物', '娱乐', '医疗', '教育', '住房', '水电', '其他']
const TAG_TYPES = ['', 'success', 'warning', 'danger', 'info', '']

const router = useRouter()
const records = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editId = ref(null)
const saving = ref(false)
const chartRef = ref(null)
let chart = null

const filterDates = ref(null)
const filterCategory = ref('')
const form = ref({ date: '', category: '', amount: 0, note: '' })

const totalAmount = computed(() => records.value.reduce((s, r) => s + r.amount, 0))
const categoryCount = computed(() => new Set(records.value.map(r => r.category)).size)
const monthlyAvg = computed(() => {
  if (!records.value.length) return '0.00'
  const months = new Set(records.value.map(r => r.date.slice(0, 7))).size || 1
  return (totalAmount.value / months).toFixed(2)
})

function tagType(cat) {
  return TAG_TYPES[CATEGORIES.indexOf(cat) % TAG_TYPES.length] || ''
}

async function fetchRecords(params = {}) {
  loading.value = true
  try {
    const res = await axios.get('/api/records', { params, withCredentials: true })
    records.value = res.data
    await nextTick()
    renderChart()
  } catch (e) {
    if (e.response?.status === 401) router.push('/login')
    else ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function applyFilter() {
  const params = {}
  if (filterDates.value?.length === 2) {
    params.date_from = filterDates.value[0]
    params.date_to = filterDates.value[1]
  }
  if (filterCategory.value) params.category = filterCategory.value
  fetchRecords(params)
}

function resetFilter() {
  filterDates.value = null
  filterCategory.value = ''
  fetchRecords()
}

function openDialog(row = null) {
  editId.value = row ? row.id : null
  form.value = row
    ? { date: row.date, category: row.category, amount: row.amount, note: row.note }
    : { date: new Date().toISOString().slice(0, 10), category: '', amount: 0, note: '' }
  dialogVisible.value = true
}

async function saveRecord() {
  if (!form.value.date || !form.value.category) {
    ElMessage.warning('日期和分类为必填项')
    return
  }
  saving.value = true
  try {
    if (editId.value) {
      await axios.put(`/api/records/${editId.value}`, form.value, { withCredentials: true })
    } else {
      await axios.post('/api/records', form.value, { withCredentials: true })
    }
    dialogVisible.value = false
    ElMessage.success('保存成功')
    fetchRecords()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确认删除该记录？', '提示', {
      type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消',
    })
    await axios.delete(`/api/records/${id}`, { withCredentials: true })
    ElMessage.success('删除成功')
    fetchRecords()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

function renderChart() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const map = {}
  records.value.forEach(r => { map[r.category] = (map[r.category] || 0) + r.amount })
  const cats = Object.keys(map)
  const amounts = cats.map(c => parseFloat(map[c].toFixed(2)))
  chart.setOption({
    tooltip: { trigger: 'axis', formatter: params => `${params[0].name}<br/>¥${params[0].value}` },
    grid: { left: 60, right: 20, bottom: 40, top: 30 },
    xAxis: { type: 'category', data: cats, axisLabel: { rotate: cats.length > 5 ? 30 : 0 } },
    yAxis: { type: 'value', name: '元', axisLabel: { formatter: '¥{value}' } },
    series: [{
      type: 'bar',
      data: amounts,
      itemStyle: { color: '#409eff', borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top', formatter: '¥{c}' },
    }],
  })
}

onMounted(fetchRecords)
onUnmounted(() => { if (chart) { chart.dispose(); chart = null } })
</script>

<style scoped>
.stat-card { text-align: center; padding: 4px 0; }
.stat-label { color: #909399; font-size: 13px; }
.stat-value { font-size: 26px; font-weight: bold; margin-top: 6px; }
</style>
