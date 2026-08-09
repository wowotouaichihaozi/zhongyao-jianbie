export const PRODUCT_SKILLS_ROUTE = '/.ohmyppt-skills/'
export const SYSTEM_SKILLS_SOURCE_PATH = '/system/'

export const LAYOUT_SKILL_NAME = 'oh-my-ppt-layout'
export const DATA_ANIM_SKILL_NAME = 'oh-my-ppt-data-anim'
export const CHART_SKILL_NAME = 'oh-my-ppt-chart'
export const SOURCE_READING_SKILL_NAME = 'oh-my-ppt-source-reading'

export const REQUIRED_PRODUCT_SKILL_NAMES = [
  LAYOUT_SKILL_NAME,
  DATA_ANIM_SKILL_NAME,
  CHART_SKILL_NAME,
  SOURCE_READING_SKILL_NAME,
] as const

export type RequiredProductSkillName = (typeof REQUIRED_PRODUCT_SKILL_NAMES)[number]

export function formatSkillUsageRequirement(skillName: RequiredProductSkillName): string {
  return `Use the DeepAgents Skills System entry for ${skillName}; read that skill's SKILL.md before applying this capability.`
}
