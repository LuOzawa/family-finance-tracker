<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h2>家庭理财记账系统</h2>
      <el-form :model="form" label-width="70px" @keyup.enter="handleLogin">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" clearable />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-button type="primary" :loading="loading" style="width:100%;margin-top:8px" @click="handleLogin">
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const form = ref({ username: 'admin', password: 'admin' })

async function handleLogin() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const res = await axios.post('/api/login', form.value, { withCredentials: true })
    if (res.data.success) {
      localStorage.setItem('isLoggedIn', '1')
      ElMessage.success('登录成功')
      router.push('/home')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 380px;
  border-radius: 8px;
}

h2 {
  text-align: center;
  margin: 0 0 24px;
  color: #303133;
  font-size: 20px;
}
</style>
