<script setup lang="tsx">
import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { NButton, NInput, NPopconfirm, NSelect, NSpace, NSwitch, NTag } from 'naive-ui';
import { fetchAdminUsers, resetAdminUserPassword, updateAdminUserRole, updateAdminUserStatus } from '@/service/api';

const router = useRouter();
const loading = ref(false);
const rows = ref<any[]>([]);
const hiddenUsernames = new Set(['codex-preview']);
const pagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] });
const filters = reactive({ keyword: '', role: null as string | null, status: null as string | null });
const resetPassword = ref('Admin@123456');

async function loadData() {
  loading.value = true;
  const { data, error } = await fetchAdminUsers({
    current: pagination.page,
    size: pagination.pageSize,
    keyword: filters.keyword,
    role: filters.role,
    status: filters.status
  });
  if (!error && data) {
    const records = data.records || [];
    rows.value = records.filter((row: any) => !hiddenUsernames.has(String(row.username || '').trim().toLowerCase()));
    pagination.itemCount = Math.max(0, Number(data.total || 0) - (records.length - rows.value.length));
  }
  loading.value = false;
}

async function changeStatus(row: any, enabled: boolean) {
  const { error } = await updateAdminUserStatus(row.id, enabled);
  if (!error) {
    window.$message?.success(enabled ? '账号已启用' : '账号已禁用');
    await loadData();
  }
}

async function changeRole(row: any, role: 'user' | 'admin') {
  const { error } = await updateAdminUserRole(row.id, role);
  if (!error) {
    window.$message?.success('角色已更新');
    await loadData();
  }
}

async function resetPasswordFor(row: any) {
  const { error } = await resetAdminUserPassword(row.id, resetPassword.value);
  if (!error) window.$message?.success(`已为 ${row.username} 重置密码`);
}

const columns: any[] = [
  { title: 'ID', key: 'id', width: 72 },
  { title: '账号', key: 'username', minWidth: 130 },
  { title: '昵称', key: 'displayName', minWidth: 130 },
  { title: '邮箱', key: 'email', minWidth: 190, ellipsis: { tooltip: true } },
  {
    title: '角色',
    key: 'role',
    width: 132,
    render: (row: any) => (
      <NSelect
        size="small"
        value={row.role}
        options={[
          { label: '用户', value: 'user' },
          { label: '管理员', value: 'admin' }
        ]}
        onUpdateValue={(value: 'user' | 'admin') => changeRole(row, value)}
      />
    )
  },
  {
    title: '状态',
    key: 'status',
    width: 120,
    render: (row: any) => (
      <NSwitch value={row.status !== 'disabled'} onUpdateValue={(value: boolean) => changeStatus(row, value)}>
        {{
          checked: () => '启用',
          unchecked: () => '禁用'
        }}
      </NSwitch>
    )
  },
  { title: '画像报告', key: 'reportCount', width: 110 },
  { title: '智能体任务', key: 'taskCount', width: 120 },
  { title: '最近登录', key: 'lastLoginAt', width: 175 },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    fixed: 'right',
    render: (row: any) => (
      <NSpace>
        <NButton size="small" type="primary" ghost onClick={() => router.push(`/manage/user-detail/${row.id}`)}>
          详情
        </NButton>
        <NPopconfirm onPositiveClick={() => resetPasswordFor(row)}>
          {{
            trigger: () => (
              <NButton size="small" tertiary type="warning">
                重置密码
              </NButton>
            ),
            default: () => `确认将密码重置为 ${resetPassword.value}？`
          }}
        </NPopconfirm>
      </NSpace>
    )
  }
];

function onPageChange(page: number) {
  pagination.page = page;
  loadData();
}

function onPageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize;
  pagination.page = 1;
  loadData();
}

onMounted(loadData);
</script>

<template>
  <div class="user-admin-page">
    <header class="page-head">
      <div>
        <h1>用户管理</h1>
        <p>查看每个用户的画像、资源任务、活跃记录，并进行账号管理。</p>
      </div>
      <NButton type="primary" round secondary @click="loadData">
        <template #icon>
          <SvgIcon icon="mdi:refresh" />
        </template>
        刷新
      </NButton>
    </header>

    <NCard :bordered="false" class="filter-card">
      <NSpace align="center" wrap>
        <NInput v-model:value="filters.keyword" clearable placeholder="搜索账号、昵称或邮箱" class="filter-input" />
        <NSelect
          v-model:value="filters.role"
          clearable
          placeholder="角色"
          class="filter-select"
          :options="[
            { label: '用户', value: 'user' },
            { label: '管理员', value: 'admin' }
          ]"
        />
        <NSelect
          v-model:value="filters.status"
          clearable
          placeholder="状态"
          class="filter-select"
          :options="[
            { label: '启用', value: 'enabled' },
            { label: '禁用', value: 'disabled' }
          ]"
        />
        <NInput v-model:value="resetPassword" placeholder="默认重置密码" class="filter-input" />
        <NButton type="primary" @click="loadData">查询</NButton>
      </NSpace>
    </NCard>

    <NCard :bordered="false" class="table-card">
      <NDataTable
        remote
        :loading="loading"
        :columns="columns"
        :data="rows"
        :scroll-x="1500"
        :pagination="pagination"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      />
    </NCard>
  </div>
</template>

<style scoped>
.user-admin-page {
  min-height: 100%;
  padding: 8px;
  background: linear-gradient(135deg, #f7fffc 0%, #f3fbf8 45%, #eef9f5 100%);
}

.page-head,
.filter-card,
.table-card {
  border-radius: 22px;
  box-shadow: 0 14px 34px rgba(15, 118, 110, 0.07);
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  padding: 24px 28px;
  background: #fff;
}

.page-head h1 {
  margin: 0 0 8px;
  color: #172033;
  font-size: 28px;
}

.page-head p {
  margin: 0;
  color: #667085;
}

.filter-card {
  margin-bottom: 18px;
}

.filter-input {
  width: 220px;
}

.filter-select {
  width: 150px;
}
</style>
