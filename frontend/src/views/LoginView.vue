<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 登录页面
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div class="auth-shell">
    <div class="auth-card">
      <h1>登录</h1>
      <p class="lead">欢迎回来，请登录你的账号</p>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="form.email"
            type="email"
            placeholder="请输入邮箱地址"
            autocomplete="email"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            autocomplete="current-password"
            show-password
          />
        </el-form-item>

        <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon :closable="false" style="margin-bottom:8px" />

        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">
          登录
        </el-button>
      </el-form>

      <p style="margin-top:20px;font-size:13px;color:var(--muted);text-align:center">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores'

const authStore = useAuthStore()
const router = useRouter()

const formRef = ref<FormInstance>()
const loading = ref(false)
const errorMsg = ref('')

const form = reactive({
  email: '',
  password: ''
})

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

async function handleLogin() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    errorMsg.value = ''
    try {
      await authStore.login({ email: form.email.trim(), password: form.password })
      router.push('/shelf')
    } catch (err: any) {
      errorMsg.value = err?.response?.data?.error || err.message || '登录失败'
    } finally {
      loading.value = false
    }
  })
}
</script>
