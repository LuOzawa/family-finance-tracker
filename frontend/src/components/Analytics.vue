<template>
  <div>
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="24">
        <el-card shadow="hover" v-loading="loading">
          <template #header>
            <span>月度支出趋势</span>
          </template>
          <div ref="trendRef" style="width:100%;height:300px" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 分类饼图 -->
      <el-col :span="12">
        <el-card shadow="hover" v-loading="loading">
          <template #header>分类支出占比</template>
          <div ref="pieRef" style="width:100%;height:340px" />
        </el-card>
      </el-col>

      <!-- K-means 聚类 -->
      <el-col :span="12">
        <el-card shadow="hover" v-loading="clusterLoading">
          <template #header>
            <div style="display:flex;align-items:center;justify-content:space-between">
              <span>K-means 消费聚类分析</span>
              <el-select v-model="nClusters" size="small" style="width:90px" @change="fetchCluster">
                <el-option :value="2" label="2群组" />
                <el-option :value="3" label="3群组" />
                <el-option :value="4" label="4群组" />
              </el-select>
            </div>
          </template>

          <div v-if="clusterError" style="color:#f56c6c;padding:20px;text-align:center">{{ clusterError }}</div>
          <div v-else>
            <div ref="clusterRef" style="width:100%;height:200px" />
            <el-table :data="clusterInfo" size="small" style="margin-top:8px" border>
              <el-table-column label="群组" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :style="`background:${row.color};color:#fff;border:none`">{{ row.label }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="count" label="记录数" width="75" align="center" />
              <el-table-column prop="avg_amount" label="均值(元)" align="right">
                <template #default="{ row }">¥{{ row.avg_amount }}</template>
              </el-table-column>
              <el-table-column prop="total_amount" label="合计(元)" align="right">
                <template #default="{ row }">¥{{ row.total_amount }}</template>
              </el-table-column>
              <el-table-column prop="top_category" label="主要分类" />
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- K-means 散点图 -->
    <el-row style="margin-top:16px" v-if="clusterRecords.length">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>聚类散点图（时间 × 金额）</template>
          <div ref="scatterRef" style="width:100%;height:300px" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const clusterLoading = ref(false)
const nClusters = ref(3)
const clusterError = ref('')
const clusterInfo = ref([])
const clusterRecords = ref([])

const trendRef = ref(null)
const pieRef = ref(null)
const clusterRef = ref(null)
const scatterRef = ref(null)

let trendChart = null
let pieChart = null
let clusterChart = null
let scatterChart = null

const CLUSTER_COLORS = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399']

async function fetchSummary() {
  loading.value = true
  try {
    const res = await axios.get('/api/analytics/summary', { withCredentials: true })
    const data = res.data
    await nextTick()
    renderTrend(data.monthly_totals)
    renderPie(data.category_totals)
  } catch (e) {
    if (e.response?.status === 401) router.push('/login')
    else ElMessage.error('分析数据加载失败')
  } finally {
    loading.value = false
  }
}

async function fetchCluster() {
  clusterLoading.value = true
  clusterError.value = ''
  try {
    const res = await axios.get(`/api/analytics/cluster?n_clusters=${nClusters.value}`, { withCredentials: true })
    const data = res.data
    if (data.error) {
      clusterError.value = data.error
      clusterInfo.value = []
      clusterRecords.value = []
      return
    }
    clusterInfo.value = data.clusters
    clusterRecords.value = data.records || []
    await nextTick()
    renderClusterBar(data.clusters)
    if (clusterRecords.value.length) renderScatter(data.records, data.clusters)
  } catch (e) {
    clusterError.value = '聚类分析失败，请确认数据足够'
  } finally {
    clusterLoading.value = false
  }
}

function renderTrend(monthly_totals) {
  if (!trendRef.value) return
  if (!trendChart) trendChart = echarts.init(trendRef.value)
  const months = Object.keys(monthly_totals).sort()
  const amounts = months.map(m => monthly_totals[m])
  trendChart.setOption({
    tooltip: { trigger: 'axis', formatter: params => `${params[0].name}<br/>¥${params[0].value}` },
    grid: { left: 60, right: 20, bottom: 40, top: 30 },
    xAxis: { type: 'category', data: months, axisLabel: { rotate: months.length > 6 ? 30 : 0 } },
    yAxis: { type: 'value', name: '元', axisLabel: { formatter: '¥{value}' } },
    series: [{
      type: 'line',
      data: amounts,
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { color: '#409eff', width: 3 },
      itemStyle: { color: '#409eff' },
      areaStyle: { color: 'rgba(64,158,255,0.15)' },
      label: { show: amounts.length <= 12, position: 'top', formatter: '¥{c}' },
    }],
  })
}

function renderPie(category_totals) {
  if (!pieRef.value) return
  if (!pieChart) pieChart = echarts.init(pieRef.value)
  const data = Object.entries(category_totals).map(([name, value]) => ({ name, value }))
  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { bottom: 0, left: 'center', type: 'scroll' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      data,
      label: { formatter: '{b}\n{d}%' },
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } },
    }],
  })
}

function renderClusterBar(clusters) {
  if (!clusterRef.value || !clusters.length) return
  if (!clusterChart) clusterChart = echarts.init(clusterRef.value)
  clusterChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, bottom: 30, top: 20 },
    xAxis: { type: 'category', data: clusters.map(c => c.label) },
    yAxis: { type: 'value', name: '均值(元)', axisLabel: { formatter: '¥{value}' } },
    series: [{
      type: 'bar',
      data: clusters.map((c, i) => ({
        value: c.avg_amount,
        itemStyle: { color: CLUSTER_COLORS[i % CLUSTER_COLORS.length], borderRadius: [4, 4, 0, 0] },
      })),
      label: { show: true, position: 'top', formatter: '¥{c}' },
    }],
  })
}

function renderScatter(records, clusters) {
  if (!scatterRef.value) return
  if (!scatterChart) scatterChart = echarts.init(scatterRef.value)

  const series = clusters.map((c, i) => ({
    name: c.label,
    type: 'scatter',
    symbolSize: 12,
    itemStyle: { color: CLUSTER_COLORS[i % CLUSTER_COLORS.length] },
    data: records
      .filter(r => r.cluster === i)
      .map(r => [r.date, r.amount, r.category]),
    tooltip: {
      formatter: p => `${p.data[0]}<br/>${p.data[2]}<br/>¥${p.data[1]}`,
    },
  }))

  scatterChart.setOption({
    legend: { top: 0, data: clusters.map(c => c.label) },
    grid: { left: 60, right: 20, bottom: 40, top: 40 },
    xAxis: { type: 'time', axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', name: '金额(元)', axisLabel: { formatter: '¥{value}' } },
    tooltip: { trigger: 'item' },
    series,
  })
}

onMounted(async () => {
  await fetchSummary()
  await fetchCluster()
})

onUnmounted(() => {
  [trendChart, pieChart, clusterChart, scatterChart].forEach(c => { if (c) c.dispose() })
  trendChart = pieChart = clusterChart = scatterChart = null
})
</script>
