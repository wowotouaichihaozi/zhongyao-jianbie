<script setup>
import { Handle, Position } from '@vue-flow/core'
import {
  Check,
  CircleAlert,
  CircleDashed,
  Clock3,
  LoaderCircle,
} from 'lucide-vue-next'

const props = defineProps({
  data: { type: Object, required: true },
})

function statusIcon() {
  if (props.data.status === 'completed') return Check
  if (props.data.status === 'failed') return CircleAlert
  if (props.data.status === 'waiting') return Clock3
  if (props.data.status === 'running') return LoaderCircle
  return CircleDashed
}
</script>

<template>
  <div class="video-workflow-node" :class="[`is-${data.status}`, { 'is-selected': data.selected }]">
    <Handle type="target" :position="Position.Left" />
    <div class="video-node-head">
      <component :is="statusIcon()" :size="16" :class="{ spin: data.status === 'running' }" />
      <span>{{ data.label }}</span>
      <b>{{ data.progress }}%</b>
    </div>
    <div class="video-node-track"><span :style="{ width: `${data.progress}%` }" /></div>
    <p>{{ data.message || data.hint }}</p>
    <Handle type="source" :position="Position.Right" />
  </div>
</template>
