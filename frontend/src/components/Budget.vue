<template>
  <div>
    <!-- 本月预算执行状态 -->
    <el-card shadow="hover" style="margin-bottom:16px">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span>{{ currentMonth }} 预算执行情况</span>
          <el-button size="small" type="primary" @click="dialogVisible = true">+ 设置预算</el-button>
        </div>
      </template>

      <div v-if="!budgetStatus.length" style="text-align:center;color:#909399;padding:40px">
        暂无预算设置，点击右上角"设置预算"开始管理
      </div>

      <el-row :gutter="16">
        <el-col :span="12" v-for="b in budgetStatus" :key="b.id" style="margin-bottom:12px">
          <el-card
            shadow="never"
            :style="`border-left:4px solid ${statusColor(b.status)}`"
          >
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <span style="font-weight:bold;font-size:14px">{{ b.category }}</span>
              <el-tag :type="statusTagType(b.status)" size="small">{{ statusText(b.status) }}</el-tag>
            </div>
            <el-progress
              :percentage="Math.min(b.percentage, 100)"
              :color="progressColor(b.percentage)"
              :stroke-width="12"
              style="margin-bottom:6px"
            />
            <div style="display:flex;justify-content:space-between;font-size:12px;color:#606266">
              <span>已用 <b style="color:#f56c6c">¥{{ b.actual }}</b></span>
              <span>预算 ¥{{ b.monthly_limit }}</span>
              <span>剩余 <b :style="`color:${b.remaining >= 0 ? '#67c23a' : '#f56c6c'}`">¥{{ b.remaining }}</b></span>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 预算配置表格 -->
    <el-card shadow="hover">
      <template #header>预算配置列表</template>
      <el-table :data="budgets" border stripe size="small" v-loading="loading">
        <el-table-column prop="category" label="分类" />
        <el-table-column prop="monthly_limit" label="月度预算(元)" align="right">
          <template #default="{ row }">¥{{ row.monthly_limit.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">修改</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editId ? '修改预算' : '设置预算'" width="380px" :close-on-click-modal="false">
      <el-form :model="form" label-width="75px">
        <el-form-item label="分类">
          <el-select v-model="form.category" :disabled="!!editId" style="width:100%">
            <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="月度上限">
          <el-input-number v-model="form.monthly_limit" :min="0" :precision="2" :step="100" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveBudget">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const CATEGORIES = ['餐饮', '交通', '购物', '娱乐', '医疗', '教育', '住房', '水电', '其他']

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editId = ref(null)
const budgets = ref([])
const budgetStatus = ref([])
const currentMonth = ref('')
const form = ref({ category: '', monthly_limit: 0 })

function statusColor(s) {
  return s === 'over' ? '#f56c6c' : s === 'warning' ? '#e6a23c' : '#67c23a'
}
function statusTagType(s) {
  return s === 'over' ? 'danger' : s === 'warning' ? 'warning' : 'success'
}
function statusText(s) {
  return s === 'over' ? '已超预算' : s === 'warning' ? '接近上限' : '正常'
}
function progressColor(pct) {
  if (pct >= 100) return '#f56c6c'
  if (pct >= 80) return '#e6a23c'
  return '#67c23a'
}

async function fetchAll() {
  loading.value = true
  try {
    const [b, s] = await Promise.all([
      axios.get('/api/budgets', { withCredentials: true }),
      axios.get('/api/analytics/budget-status', { withCredentials: true }),
    ])
    budgets.value = b.data
    budgetStatus.value = s.data.budgets
    currentMonth.value = s.data.month
  } catch (e) {
    if (e.response?.status === 401) router.push('/login')
    else ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function openEdit(row) {
  editId.value = row.id
  form.value = { category: row.category, monthly_limit: row.monthly_limit }
  dialogVisible.value = true
}

function closeDialog() {
  dialogVisible.value = false
  editId.value = null
  form.value = { category: '', monthly_limit: 0 }
}

async function saveBudget() {
  if (!form.value.category) { ElMessage.warning('请选择分类'); return }
  saving.value = true
  try {
    if (editId.value) {
      await axios.put(`/api/budgets/${editId.value}`, form.value, { withCredentials: true })
    } else {
      await axios.post('/api/budgets', form.value, { withCredentials: true })
    }
    closeDialog()
    ElMessage.success('保存成功')
    fetchAll()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确认删除该预算设置？', '提示', { type: 'warning' })
    await axios.delete(`/api/budgets/${id}`, { withCredentials: true })
    ElMessage.success('已删除')
    fetchAll()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

onMounted(fetchAll)
</script>
