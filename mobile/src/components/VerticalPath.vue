<template>
  <ol class="vertical-path" aria-label="纵向学习路径">
    <li v-for="(node,index) in nodes" :key="node.id" :ref="el => setCurrentRef(el,node)" :class="node.state">
      <button class="path-node" type="button" :disabled="node.state==='locked'" :aria-expanded="expandedId===node.id" @click="toggle(node)">
        <span class="node-marker"><Check v-if="node.state==='done'" :size="18" /><LockKeyhole v-else-if="node.state==='locked'" :size="15" /><span v-else>{{ String(index+1).padStart(2,'0') }}</span></span>
        <span class="node-copy"><small>{{ label(node,index) }}</small><strong>{{ node.title }}</strong><em>{{ stateLabel(node.state) }}</em></span>
        <ChevronDown :size="18" :class="{rotated:expandedId===node.id}" />
      </button>
      <div v-if="expandedId===node.id" class="node-detail">
        <p>{{ node.description || '该节点将结合当前画像与学习进度展开。' }}</p>
        <div class="node-meta"><span>{{ resourceName(node.resourceType) }}</span><span>进度 {{ progress(node) }}%</span></div>
        <div class="progress-track"><i :style="{width:`${progress(node)}%`}"></i></div>
        <button v-if="node.state!=='locked'" class="primary-btn" type="button" @click="$emit('open',node)">{{ node.state==='done'?'重新查看':'进入任务' }}<ArrowRight :size="16" /></button>
      </div>
    </li>
  </ol>
</template>
<script setup>
import { nextTick,onMounted,ref,watch } from 'vue';import { ArrowRight,Check,ChevronDown,LockKeyhole } from 'lucide-vue-next'
const props=defineProps({nodes:{type:Array,default:()=>[]},modelValue:{type:String,default:''}});const emit=defineEmits(['update:modelValue','open']);const expandedId=ref(props.modelValue);const currentRef=ref(null)
watch(()=>props.modelValue,v=>expandedId.value=v);watch(()=>props.nodes,()=>selectDefault(),{deep:true})
function selectDefault(){if(expandedId.value)return;const node=props.nodes.find(x=>x.state==='current')||props.nodes.find(x=>x.state==='available');if(node){expandedId.value=node.id;emit('update:modelValue',node.id);nextTick(()=>{if(typeof currentRef.value?.scrollIntoView==='function')currentRef.value.scrollIntoView({block:'center',behavior:'smooth'})})}}
function setCurrentRef(el,node){if(node.state==='current')currentRef.value=el}
function toggle(node){expandedId.value=expandedId.value===node.id?'':node.id;emit('update:modelValue',expandedId.value)}
function label(node,index){return node.resourceType==='week'?`第 ${node.order||index+1} 周`:`任务 ${String(index+1).padStart(2,'0')}`}
function stateLabel(s){return {done:'已完成',current:'进行中',available:'待开始',locked:'未解锁'}[s]||s}
function resourceName(v){return {week:'周学习计划',question_bank:'练习题库',ppt:'PPT 课件',document:'学习文档',mindmap:'思维导图',video:'讲解视频',generated_video:'AI 视频',animation:'教学动画'}[v]||'学习任务'}
function progress(n){return n.state==='done'?100:n.state==='current'?60:0}
onMounted(selectDefault)
</script>
<style scoped>.vertical-path{margin:0;padding:0;list-style:none}.vertical-path>li{position:relative;padding:0 0 18px 42px}.vertical-path>li:before{content:"";position:absolute;top:0;bottom:0;left:17px;width:2px;background:#cfdcd5}.vertical-path>li:last-child:before{bottom:auto;height:34px}.vertical-path>li.done:before{background:#3b926e}.path-node{width:100%;min-height:82px;display:grid;grid-template-columns:minmax(0,1fr) 20px;align-items:center;gap:8px;padding:14px 13px;border:1px solid #dce5e0;border-radius:7px;background:white;color:#26372f;text-align:left}.path-node:disabled{opacity:.62}.node-marker{position:absolute;left:0;top:24px;z-index:2;width:36px;height:36px;display:grid;place-items:center;border:2px solid #cfdcd5;border-radius:50%;background:#f4f7f5;color:#65776d;font-size:10px;font-weight:850}.done .node-marker{border-color:#3b926e;background:#3b926e;color:white}.current .node-marker{border-color:#176f4b;background:white;color:#176f4b;box-shadow:0 0 0 5px rgba(23,111,75,.12)}.node-copy{display:grid;min-width:0;gap:4px}.node-copy small{color:#176f4b;font-size:9px;font-weight:800}.node-copy strong{font-size:14px;line-height:1.4}.node-copy em{color:#78867f;font-size:10px;font-style:normal}.path-node svg{transition:transform .2s}.path-node svg.rotated{transform:rotate(180deg)}.node-detail{margin-top:7px;padding:15px;border-left:2px solid #176f4b;background:#edf5f1}.node-detail p{margin:0;color:#53665c;font-size:12px;line-height:1.65}.node-meta{display:flex;justify-content:space-between;gap:10px;margin:13px 0 7px;color:#176f4b;font-size:10px;font-weight:750}.node-detail .primary-btn{width:100%;margin-top:14px}</style>
