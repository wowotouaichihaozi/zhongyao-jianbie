import { computed, shallowRef } from 'vue'

const controller = shallowRef(null)

export function useAvatarDebug() {
  const available = computed(() => Boolean(controller.value))
  const status = computed(() => controller.value?.status?.value || '未进入数字人页面')
  const resumeRequired = computed(() => Boolean(controller.value?.resumeRequired?.value))

  function registerAvatarController(nextController) {
    controller.value = nextController
  }

  function unregisterAvatarController(nextController) {
    if (!nextController || controller.value === nextController) {
      controller.value = null
    }
  }

  async function runAvatarAction(action, ...args) {
    const target = controller.value?.actions?.[action]
    if (!target) {
      throw new Error('数字人控制器未就绪')
    }
    return target(...args)
  }

  return {
    controller,
    available,
    status,
    resumeRequired,
    registerAvatarController,
    unregisterAvatarController,
    runAvatarAction,
  }
}
