<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 修改密码弹窗（v1.6 新增）
     由 TopNav 头像下拉菜单唤起；复用 authStore.changePassword
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <el-dialog
    v-model="visible"
    title="修改个人密码"
    width="min(440px, calc(100vw - 32px))"
    append-to-body
    :close-on-click-modal="false"
    destroy-on-close
  >
    <p class="account-hint">当前登录：{{ authStore.userEmail || '—' }}</p>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      @submit.prevent="handleChangePassword"
    >
      <el-form-item label="当前密码" prop="old_password">
        <el-input
          v-model="form.old_password"
          type="password"
          placeholder="请输入当前密码"
          show-password
        />
      </el-form-item>

      <el-form-item label="新密码" prop="new_password">
        <el-input
          v-model="form.new_password"
          type="password"
          placeholder="8-64位，需包含字母和数字"
          show-password
        />
      </el-form-item>

      <el-form-item label="确认新密码" prop="confirm_password">
        <el-input
          v-model="form.confirm_password"
          type="password"
          placeholder="请再次输入新密码"
          show-password
        />
      </el-form-item>

      <el-alert
        v-if="errorMsg"
        :title="errorMsg"
        type="error"
        show-icon
        :closable="false"
        style="margin-bottom:12px"
      />
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleChangePassword">
        确认修改
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores'
import { passwordComplexityValidator } from '@/utils'

const visible = defineModel<boolean>({ required: true })

const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const errorMsg = ref('')

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const validateConfirm = (_rule: any, value: string, callback: Function) => {
  if (value !== form.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  old_password: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { validator: passwordComplexityValidator, trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' }
  ]
}

async function handleChangePassword() {
  if (!formRef.value || submitting.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    errorMsg.value = ''

    try {
      await authStore.changePassword({
        old_password: form.old_password,
        new_password: form.new_password
      })
      ElMessage.success('密码修改成功！')
      visible.value = false
    } catch (err: any) {
      errorMsg.value = err?.response?.data?.error || err.message || '密码修改失败'
    } finally {
      submitting.value = false
    }
  })
}
</script>

<style scoped>
.account-hint {
  font-size: 12px;
  color: var(--muted);
  margin: 0 0 18px;
}
</style>
