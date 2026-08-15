import type { ImageGenerationProviderAdapter, ResolvedImageModelConfig } from '../types'
import { seedreamAdapter } from './seedream'

const PROVIDER_ADAPTERS: Record<
  ResolvedImageModelConfig['provider'],
  ImageGenerationProviderAdapter
> = {
  seedream: seedreamAdapter,
  agnes: seedreamAdapter,
  jimeng: seedreamAdapter,
  jimeng4: seedreamAdapter,
  siliconflow: seedreamAdapter,
  openaiCompatible: seedreamAdapter,
  gemini: seedreamAdapter
}

export function resolveImageGenerationProvider(
  provider: ResolvedImageModelConfig['provider']
): ImageGenerationProviderAdapter {
  return PROVIDER_ADAPTERS[provider]
}
