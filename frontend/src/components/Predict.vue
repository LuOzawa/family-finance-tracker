<template>
  <div>
    <el-row :gutter="16">
      <!-- ARIMA 预测图 -->
      <el-col :span="15">
        <el-card shadow="hover" v-loading="predictLoading">
          <template #header>
            <div style="display:flex;align-items:center;justify-content:space-between">
              <span>月度支出 ARIMA 预测</span>
              <el-select v-model="periods" size="small" style="width:100px" @change="fetchPredict">
                <el-option :value="3" label="预测3个月" />
                <el-option :value="6" label="预测6个月" />
              </el-select>
            </div>
          </template>
          <div v-if="predictNote" style="color:#e6a23c;font-size:12px;margin-bottom:8px;padding:4px 8px;background:#fdf6ec;border-radius:4px">
            提示：{{ predictNote }}
          </div>
          <div ref="predictRef" style="width:100%;height:360px" />
        </el-card>
      </el-col>

      <!-- 健康评分 -->
      <el-col :span="9">
        <el-card shadow="hover" v-loading="healthLoading">
          <template #header>财务健康评分</template>
          <div ref="gaugeRef" style="width:100%;height:220px" />
          <el-divider />
          <div v-if="healthData.grade">
            <el-row :gutter="8" style="margin-bottom:12px">
              <el-col :span="12" v-for="(val, key) in healthData.details" :key="key">
                <div style="text-align:center;padding:6px;background:#f5f7fa;border-radius:4px;margin-bottom:6px">
                  <div style="font-size:11px;color:#909399">{{ key }}</div>
                  <div style="font-size:18px;font-weight:bold;color:#409eff">{{ val }}<span style="font-size:11px;color:#c0c4cc">/25</span></div>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 健康建议 -->
    <el-card shadow="hover" style="margin-top:16px" v-if="healthData.suggestions?.length">
      <template #header>
        <span>财务分析建议</span>
        <el-tag style="margin-left:8px" :type="gradeTagType">
          {{ healthData.grade_desc }} ({{ healthData.score }}分)
        </el-tag>
      </template>
      <el-row :gutter="12">
        <el-col :span="12" v-for="(s, i) in healthData.suggestions" :key="i">
          <el-alert
            :title="s"
            :type="s.includes('良好') || s.includes('优秀') || s.includes('保持') ? 'success' : 'warning'"
            :closable="false"
            show-icon
            style="margin-bottom:8px"
          />
        </el-col>
      </el-row>
    </el-card>

    <!-- 预测数据明细 -->
    <el-card shadow="hover" style="margin-top:16px" v-if="predictions.length">
      <template #header>预测数据明细</template>
      <el-table :data="predictions" border stripe size="small">
        <el-table-column prop="month" label="预测月份" width="130" />
        <el-table-column prop="predicted_amount" label="预测支出(元)" align="right">
          <template #default="{ row }">
            <span style="color:#e6a23c;font-weight:bold">¥{{ row.predicted_amount }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="method" label="预测方法">
          <template #default="{ row }">
            <el-tag size="small" :type="row.method === 'arima' ? 'success' : 'info'">
              {{ row.method === 'arima' ? 'ARIMA模型' : '均值基准' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

const router = useRouter()
const predictLoading = ref(false)
const healthLoading = ref(false)
const periods = ref(3)
const predictNote = ref('')
const predictions = ref([])
const healthData = ref({ score: 0, grade: '', grade_desc: '', details: {}, suggestions: [] })

const predictRef = ref(null)
const gaugeRef = ref(null)
let predictChart = null
let gaugeChart = null

const gradeTagType = computed(() => {
  const g = healthData.value.grade
  return g === 'A' ? 'success' : g === 'B' ? '' : g === 'C' ? 'warning' : 'danger'
})

async function fetchPredict() {
  predictLoading.value = true
  predictNote.value = ''
  try {
    const res = await axios.get(`/api/analytics/predict?periods=${periods.value}`, { withCredentials: true })
    const data = res.data
    predictions.value = data.predictions || []
    predictNote.value = data.note || ''
    await nextTick()
    renderPredict(data.historical || [], data.predictions || [])
  } catch (e) {
    if (e.response?.status === 401) router.push('/login')
    else ElMessage.error('预测数据加载失败')
  } finally {
    predictLoading.value = false
  }
}

async function fetchHealth() {
  healthLoading.value = true
  try {
    const res = await axios.get('/api/analytics/health', { withCredentials: true })
    healthData.value = res.data
    await nextTick()
    renderGauge(res.data.score, res.data.grade_desc)
  } catch (e) {
    ElMessage.error('健康评分加载失败')
  } finally {
    healthLoading.value = false
  }
}

function renderPredict(historical, preds) {
  if (!predictRef.value) return
  if (!predictChart) predictChart = echarts.init(predictRef.value)

  const histData = historical.map(h => [h.month, h.amount])
  const predData = preds.map(p => [p.month, p.predicted_amount])

  const lastHistMonth = historical.length ? historical[historical.length - 1].month : null
  const bridgeData = lastHistMonth && predData.length
    ? [[lastHistMonth, historical[historical.length - 1].amount], ...predData]
    : predData

  predictChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: params => params.map(p => `${p.seriesName}: ¥${p.value[1]}`).join('<br/>')
    },
    legend: { top: 0, data: ['历史支出', 'ARIMA预测'] },
    grid: { left: 65, right: 20, bottom: 40, top: 40 },
    xAxis: { type: 'category', data: [...histData.map(d => d[0]), ...predData.map(d => d[0])], axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', name: '元', axisLabel: { formatter: '¥{value}' } },
    series: [
      {
        name: '历史支出',
        type: 'line',
        data: histData,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { color: '#409eff', width: 2 },
        itemStyle: { color: '#409eff' },
        areaStyle: { color: 'rgba(64,158,255,0.12)' },
      },
      {
        name: 'ARIMA预测',
        type: 'line',
        data: bridgeData,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { color: '#e6a23c', width: 2, type: 'dashed' },
        itemStyle: { color: '#e6a23c' },
        label: { show: true, formatter: '¥{c}', color: '#e6a23c' },
      },
    ],
  })
}

function renderGauge(score, desc) {
  if (!gaugeRef.value) return
  if (!gaugeChart) gaugeChart = echarts.init(gaugeRef.value)
  gaugeChart.setOption({
    series: [{
      type: 'gauge',
      min: 0,
      max: 100,
      splitNumber: 5,
      radius: '85%',
      center: ['50%', '60%'],
      axisLine: {
        lineStyle: {
          width: 18,
          color: [[0.4, '#f56c6c'], [0.65, '#e6a23c'], [0.8, '#409eff'], [1, '#67c23a']],
        },
      },
      pointer: { width: 5, length: '60%' },
      axisTick: { show: false },
      splitLine: { length: 12, lineStyle: { color: '#fff', width: 2 } },
      axisLabel: { fontSize: 11, color: '#606266' },
      detail: {
        formatter: '{value}',
        fontSize: 30,
        fontWeight: 'bold',
        color: score >= 80 ? '#67c23a' : score >= 65 ? '#409eff' : score >= 45 ? '#e6a23c' : '#f56c6c',
        offsetCenter: [0, '30%'],
      },
      title: {
        offsetCenter: [0, '55%'],
        fontSize: 13,
        color: '#909399',
      },
      data: [{ value: score, name: desc || '综合评分' }],
    }],
  })
}

onMounted(async () => {
  await Promise.all([fetchPredict(), fetchHealth()])
})

onUnmounted(() => {
  if (predictChart) { predictChart.dispose(); predictChart = null }
  if (gaugeChart) { gaugeChart.dispose(); gaugeChart = null }
})
</script>
