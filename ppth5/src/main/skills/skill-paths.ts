import { app } from 'electron'
import { is } from '@electron-toolkit/utils'
import path from 'node:path'
import { SYSTEM_SKILLS_SOURCE_PATH } from './skill-contract'

export function resolveBuiltinSkillsSourcePath(): string {
  return is.dev
    ? path.join(process.cwd(), 'resources', 'skills')
    : path.join(process.resourcesPath, 'app.asar.unpacked', 'resources', 'skills')
}

export function resolveInstalledSkillsPath(): string {
  return path.join(app.getPath('userData'), is.dev ? 'skills-dev' : 'skills')
}

export function getSystemSkillsSourcePath(): string {
  return SYSTEM_SKILLS_SOURCE_PATH
}
