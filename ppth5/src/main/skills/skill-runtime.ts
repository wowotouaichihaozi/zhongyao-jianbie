let installedSkillsPath: string | null = null
let skillsReadyPromise: Promise<unknown> = Promise.resolve(null)

export function setSkillsRuntime(options: {
  installedSkillsPath: string
  ready: Promise<unknown>
}): void {
  installedSkillsPath = options.installedSkillsPath
  skillsReadyPromise = options.ready
}

export function getInstalledSkillsPath(): string | null {
  return installedSkillsPath
}

export function waitForSkillsReady(): Promise<unknown> {
  return skillsReadyPromise
}
