<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 个人设置页面
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div>
    <TopNav :show-search="false" :show-settings-btn="false" :show-back-to-shelf="true" />

    <section class="section">
      <div class="container" style="max-width:560px">
        <el-button text style="margin-bottom:16px" @click="$router.push('/shelf')">← 返回书架</el-button>
        <h1 style="margin-bottom:24px;font-size:clamp(28px,4vw,36px);font-weight:700">个人设置</h1>

        <div class="card">
          <div style="margin-bottom:24px">
            <h3 style="font-size:18px;font-weight:600">账号信息</h3>
            <p style="font-size:12px;color:var(--muted);margin-top:4px">
              当前登录：{{ authStore.userEmail || '—' }}
            </p>
          </div>

          <hr class="rule" style="margin-bottom:24px" />

          <h3 style="font-size:18px;font-weight:600;margin-bottom:18px">修改密码</h3>

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

            <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon :closable="false" style="margin-bottom:8px" />
            <el-alert v-if="successMsg" :title="successMsg" type="success" show-icon :closable="false" style="margin-bottom:8px" />

            <el-button type="primary" native-type="submit" :loading="submitting" style="align-self:flex-start">
              修改密码
            </el-button>
          </el-form>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores'
import TopNav from '@/components/TopNav.vue'

const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

/** 密码复杂校验 */
const validateNewPassword = (_rule: any, value: string, callback: Function) => {
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
    { validator: validateNewPassword, trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' }
  ]
}

async function handleChangePassword() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    errorMsg.value = ''
    successMsg.value = ''

    try {
      await authStore.changePassword({
        old_password: form.old_password,
        new_password: form.new_password
      })
      successMsg.value = '密码修改成功！'
      form.old_password = ''
      form.new_password = ''
      form.confirm_password = ''
      formRef.value?.resetFields()
      ElMessage.success('密码修改成功！')
    } catch (err: any) {
      errorMsg.value = err?.response?.data?.error || err.message || '密码修改失败'
    } finally {
      submitting.value = false
    }
  })
}
</script>

<style scoped>
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 24px;
}

.rule {
  border: 0;
  border-top: 1px solid var(--border);
  margin: 0;
}
</style>
