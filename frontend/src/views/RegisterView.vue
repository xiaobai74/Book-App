<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 注册页面
     v1.7 — 水墨雪景背景由 App.vue 全局挂载（InkSnowBackground）
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div class="auth-shell">
    <div class="auth-card">
      <h1>注册</h1>
      <p class="lead">创建你的私人书架账号</p>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleRegister"
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
            placeholder="8-64位，需包含字母和数字"
            show-password
          />
          <div style="font-size:12px;color:var(--muted);margin-top:4px">密码长度 8-64 位，需包含字母和数字</div>
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            show-password
          />
        </el-form-item>

        <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon :closable="false" style="margin-bottom:8px" />

        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">
          注册
        </el-button>
      </el-form>

      <p style="margin-top:20px;font-size:13px;color:var(--muted);text-align:center">
        已有账号？<router-link to="/login">去登录</router-link>
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
  password: '',
  confirmPassword: ''
})

/** 密码验证函数 */
const validatePassword = (_rule: any, value: string, callback: Function) => {
  if (value.length < 8 || value.length > 64) {
    callback(new Error('密码长度需为 8-64 位'))
  } else if (!/[a-zA-Z]/.test(value)) {
    callback(new Error('密码需包含至少一个字母'))
  } else if (!/[0-9]/.test(value)) {
    callback(new Error('密码需包含至少一个数字'))
  } else {
    callback()
  }
}

const validateConfirm = (_rule: any, value: string, callback: Function) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { validator: validatePassword, trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' }
  ]
}

async function handleRegister() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    errorMsg.value = ''
    try {
      await authStore.register({ email: form.email.trim(), password: form.password })
      // 注册成功后自动登录
      try {
        await authStore.login({ email: form.email.trim(), password: form.password })
        router.push('/shelf')
      } catch (err: any) {
        // 注册已成功，仅登录失败——提示准确文案，用户可手动登录
        errorMsg.value = err?.response?.data?.error || err.message || '注册成功，但自动登录失败，请手动登录'
      }
    } catch (err: any) {
      errorMsg.value = err?.response?.data?.error || err.message || '注册失败'
    } finally {
      loading.value = false
    }
  })
}
</script>
