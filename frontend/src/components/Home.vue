<template>
  <el-container style="min-height:100vh">
    <!-- 侧边栏 -->
    <el-aside width="200px" style="background:#304156;flex-shrink:0">
      <div style="padding:18px 20px;color:#fff;font-size:15px;font-weight:bold;border-bottom:1px solid #435573;white-space:nowrap">
        家庭理财系统
      </div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/home/dashboard">
          <span>首页概览</span>
        </el-menu-item>
        <el-menu-item index="/home/analytics">
          <span>数据分析</span>
        </el-menu-item>
        <el-menu-item index="/home/budget">
          <span>预算管理</span>
        </el-menu-item>
        <el-menu-item index="/home/predict">
          <span>智能预测</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <el-header style="background:#fff;border-bottom:1px solid #e4e7ed;display:flex;align-items:center;justify-content:space-between;padding:0 20px">
        <span style="font-size:16px;color:#303133;font-weight:500">{{ pageTitle }}</span>
        <el-button size="small" type="info" plain @click="handleLogout">退出登录</el-button>
      </el-header>
      <el-main style="background:#f5f7fa;padding:20px">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()

const PAGE_TITLES = {
  '/home/dashboard': '首页概览',
  '/home/analytics': '数据分析',
  '/home/budget': '预算管理',
  '/home/predict': '智能预测',
}
const pageTitle = computed(() => PAGE_TITLES[route.path] || '家庭理财记账系统')

async function handleLogout() {
  try {
    await axios.post('/api/logout', {}, { withCredentials: true })
  } finally {
    localStorage.removeItem('isLoggedIn')
    router.push('/login')
  }
}
</script>
