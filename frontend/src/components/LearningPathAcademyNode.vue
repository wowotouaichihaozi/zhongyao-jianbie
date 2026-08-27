<template>
  <span
    class="academy-node"
    :class="[`stage-${normalizedStage}`, `state-${state}`]"
    :style="{ '--academy-growth': growthScale }"
    :data-landmark="landmarkName"
    aria-hidden="true"
  >
    <svg class="academy-node__scene academy-node__scene--vector" viewBox="0 0 320 240">
      <ellipse class="landmark-shadow" cx="160" cy="205" :rx="shadowRadius" ry="18" />

      <!-- 01: a deliberately small scholar's hut with a visible reading desk. -->
      <g v-if="normalizedStage === 1" class="landmark landmark-study-hut" transform="translate(-80 -80) scale(1.5)">
        <path class="terrace-side" d="m85 171 75 40 75-40v13l-75 40-75-40Z" />
        <path class="terrace-top" d="m85 171 75-40 75 40-75 40Z" />
        <path class="garden-bed" d="m94 171 26-14 18 10-26 14Z" />
        <path class="garden-lines" d="m101 169 18-9m-11 14 18-9" />
        <path class="hut-wall-left" d="m126 126 34 18v46l-34-18Z" />
        <path class="hut-wall-right" d="m160 144 34-18v46l-34 18Z" />
        <path class="timber" d="M134 135v39m17-34v43m18-43v43m17-48v39" />
        <path class="roof-main" d="m113 126 47-31 48 31-48 27Z" />
        <path class="roof-under" d="m113 126 47 27 48-27-4 10-44 26-43-25Z" />
        <path class="roof-ridge" d="m119 124 41-25 42 25m-86 2-12 1 11-9m90 8 11 1-10-9" />
        <path class="roof-tiles" d="m160 99-34 27m34-27 35 27m-35 24-39-24m39 24 40-24" />
        <path class="door" d="m149 158 11 6 11-6v27l-11 6-11-6Z" />
        <path class="moon-window" d="M134 154a12 12 0 0 1 24 0v18l-12 6-12-6Z" />
        <path class="bracket-set" d="m123 139 8 4 8-4m42 0 8 4 8-4" />
        <path class="study-desk" d="m181 180 21-11 15 8-21 11Zm15 8v10m-12-17v10m24-18v10" />
        <path class="scroll" d="m188 177 8-4 8 4-8 4Z" />
        <path class="herb-stem" d="M112 164v-19m0 8-8-5m8 10 9-7" />
        <circle class="herb-leaf" cx="104" cy="148" r="4" />
        <circle class="herb-leaf" cx="121" cy="151" r="4" />
      </g>

      <!-- 02: a broad medicinal garden and apothecary greenhouse. -->
      <g v-else-if="normalizedStage === 2" class="landmark landmark-herb-garden" transform="translate(3 3) scale(.98)">
        <path class="terrace-side" d="m37 169 123 55 123-55v13l-123 55-123-55Z" />
        <path class="terrace-top" d="m37 169 123-55 123 55-123 55Z" />
        <g class="garden-plots">
          <path d="m54 169 35-16 25 11-35 16Zm39 18 35-16 25 11-35 16Zm112-22 32-14 25 11-32 15Zm-40 20 32-15 25 11-32 15Z" />
          <path class="garden-lines" d="m62 168 26-12m-17 17 26-12m5 25 25-12m-17 17 25-12m78-16 24-10m-15 15 24-11m-72 26 24-11m-15 16 24-11" />
        </g>
        <g class="apothecary-building" transform="translate(-16 -16) scale(1.12)">
          <path class="apothecary-wall-left" d="m88 126 47 23v43l-47-22Z" />
          <path class="apothecary-wall-right" d="m135 149 42-21v43l-42 21Z" />
          <path class="timber" d="M98 132v43m13-36v43m14-36v42m20-35v34m17-42v34" />
          <path class="roof-main" d="m77 125 57-31 56 29-55 31Z" />
          <path class="roof-under" d="m77 125 58 29 55-31-3 10-52 30-54-28Z" />
          <path class="roof-ridge" d="m84 123 50-25 48 25m-101 2-11 2 9-9m108 6 11 2-9-9" />
          <path class="architectural-detail" d="m134 98-44 27m44-27 43 25m-43 27-50-25m50 25 49-27M98 133v34m14-27v34m36-36v35m14-42v34" />
        </g>
        <g class="glass-house" transform="translate(-23 -18) scale(1.11)">
          <path class="glass-fill" d="m172 143 39-22 42 22v40l-42 23-39-21Z" />
          <path d="m172 143 39-22 42 22-42 22Zm0 0 39 22 42-22m-81 0v42l39 21 42-23v-40m-42-22v85m-19-74v64m39-85v63" />
          <path d="M172 143q39-43 81 0" />
        </g>
        <path class="water-channel" d="m44 186 112 49 119-53" />
        <circle class="herb-leaf" cx="64" cy="151" r="5" />
        <circle class="herb-leaf" cx="260" cy="153" r="5" />
      </g>

      <!-- 03: four diagnosis rooms orbit a pulse-reading core. -->
      <g v-else-if="normalizedStage === 3" class="landmark landmark-diagnosis-court">
        <path class="terrace-side" d="m42 158 118 68 118-68v14l-118 68-118-68Z" />
        <path class="terrace-top" d="m42 158 118-68 118 68-118 68Z" />
        <path class="court-path" d="M160 105v102M72 158h176M98 123l124 70m0-70L98 193" />
        <ellipse class="diagnosis-ring" cx="160" cy="159" rx="48" ry="28" />
        <ellipse class="diagnosis-core" cx="160" cy="159" rx="32" ry="19" />
        <path class="pulse-line" d="m137 160 10-1 5-9 8 19 8-25 7 16h10" />
        <path class="diagnosis-halo" d="M126 159a34 18 0 0 1 68 0M135 159a25 12 0 0 0 50 0" />
        <g class="diagnosis-columns">
          <g transform="translate(160 120)"><ellipse cy="13" rx="5" ry="3" /><path d="M-5 0h10v13H-5Z" /><ellipse rx="5" ry="3" /></g>
          <g transform="translate(205 133)"><ellipse cy="13" rx="5" ry="3" /><path d="M-5 0h10v13H-5Z" /><ellipse rx="5" ry="3" /></g>
          <g transform="translate(217 166)"><ellipse cy="13" rx="5" ry="3" /><path d="M-5 0h10v13H-5Z" /><ellipse rx="5" ry="3" /></g>
          <g transform="translate(115 133)"><ellipse cy="13" rx="5" ry="3" /><path d="M-5 0h10v13H-5Z" /><ellipse rx="5" ry="3" /></g>
          <g transform="translate(103 166)"><ellipse cy="13" rx="5" ry="3" /><path d="M-5 0h10v13H-5Z" /><ellipse rx="5" ry="3" /></g>
        </g>
        <g class="court-pavilion pavilion-top" transform="translate(-38 -30) scale(1.24)">
          <path class="small-wall" d="m135 116 25 14 25-14v25l-25 14-25-14Z" />
          <path class="roof-main" d="m126 114 34-22 35 22-35 20Z" />
          <path class="roof-under" d="m126 114 34 20 35-20-3 8-32 19-31-18Z" />
        </g>
        <g class="court-pavilion pavilion-left" transform="translate(-21 -38) scale(1.24)">
          <path class="small-wall" d="m62 151 25 14 25-14v25l-25 14-25-14Z" />
          <path class="roof-main" d="m53 149 34-22 35 22-35 20Z" />
          <path class="roof-under" d="m53 149 34 20 35-20-3 8-32 19-31-18Z" />
        </g>
        <g class="court-pavilion pavilion-right" transform="translate(-56 -38) scale(1.24)">
          <path class="small-wall" d="m208 151 25 14 25-14v25l-25 14-25-14Z" />
          <path class="roof-main" d="m199 149 34-22 35 22-35 20Z" />
          <path class="roof-under" d="m199 149 34 20 35-20-3 8-32 19-31-18Z" />
        </g>
        <g class="court-pavilion pavilion-front" transform="translate(-38 -46) scale(1.24)">
          <path class="small-wall" d="m135 184 25 14 25-14v25l-25 14-25-14Z" />
          <path class="roof-main" d="m126 182 34-22 35 22-35 20Z" />
          <path class="roof-under" d="m126 182 34 20 35-20-3 8-32 19-31-18Z" />
        </g>
        <g class="court-posts"><circle cx="111" cy="116" r="3" /><circle cx="209" cy="116" r="3" /><circle cx="111" cy="202" r="3" /><circle cx="209" cy="202" r="3" /></g>
      </g>

      <!-- 04: a wide lecture academy with two wings and an open-book forum. -->
      <g v-else-if="normalizedStage === 4" class="landmark landmark-lecture-academy" transform="translate(16 12) scale(.9)">
        <path class="terrace-side" d="m28 170 132 62 132-62v13l-132 57-132-57Z" />
        <path class="terrace-top" d="m28 170 132-62 132 62-132 62Z" />
        <path class="academy-plaza" d="m93 190 67-35 68 35-68 34Z" />
        <g class="lecture-wing wing-left">
          <path class="wing-wall" d="m43 154 58 29 52-27v32l-52 28-58-29Z" />
          <path class="roof-main" d="m32 151 69-37 67 35-67 39Z" />
          <path class="roof-under" d="m32 151 69 37 67-39-4 10-63 37-65-35Z" />
        </g>
        <g class="lecture-wing wing-right">
          <path class="wing-wall" d="m167 156 52 27 58-29v33l-58 29-52-28Z" />
          <path class="roof-main" d="m152 149 67-35 69 37-69 37Z" />
          <path class="roof-under" d="m152 149 67 39 69-37-4 10-65 35-63-37Z" />
        </g>
        <g class="lecture-main">
          <path class="hall-wall" d="m101 109 59 31 59-31v57l-59 32-59-32Z" />
          <path class="timber" d="M113 116v55m16-47v56m16-48v56m30-56v56m16-64v56m16-64v55" />
          <path class="roof-main" d="m84 107 76-45 77 45-77 43Z" />
          <path class="roof-under" d="m84 107 76 43 77-43-4 12-73 42-72-41Z" />
          <path class="roof-ridge" d="m92 105 68-39 69 39m-140 2-14 2 12-11m145 8 14 2-12-11" />
          <path class="roof-tiles" d="m160 66-58 41m58-41 59 41m-59 39-68-39m68 39 69-39" />
          <path class="door" d="m145 161 15 8 15-8v28l-15 9-15-9Z" />
        </g>
        <g class="lecture-upper">
          <path class="upper-wall" d="m126 79 34 18 34-18v31l-34 18-34-18Z" />
          <path class="upper-lattice" d="M136 85v31m12-25v31m36-37v31m-12-25v31" />
          <path class="upper-roof" d="m111 77 49-31 50 31-50 29Z" />
          <path class="upper-eave" d="m111 77 49 29 50-29-4 11-46 28-45-28Z" />
          <path class="curved-eave" d="M111 77q-10 5-18-1m117 1q10 5 18-1M119 73l41-23 42 23" />
          <path class="architectural-detail" d="m160 50-39 27m39-27 40 27m-40 25-44-25m44 25 45-25M134 86l26 14 27-14" />
          <path class="balcony-rail" d="m127 105 33 18 34-18m-58 5v14m12-8v14m36-20v14m-12-8v14" />
        </g>
        <path class="open-book" d="m126 203 34 8 34-8-3 15-31 8-31-8Zm34 8v15" />
        <path class="knowledge-ring" d="M109 206c13-20 89-20 102 0" />
      </g>

      <!-- 05: a vertical archive pagoda, unlike the preceding horizontal campus. -->
      <g v-else-if="normalizedStage === 5" class="landmark landmark-archive-pagoda" transform="translate(-32 -24) scale(1.2)">
        <path class="terrace-side" d="m69 187 91 44 91-44v12l-91 41-91-41Z" />
        <path class="terrace-top" d="m69 187 91-44 91 44-91 44Z" />
        <g class="pagoda-floor floor-low">
          <path class="pagoda-wall" d="m111 145 49 24 49-24v42l-49 25-49-25Z" />
          <path class="archive-shelves" d="M121 151v39m13-32v39m52-46v39m-13-32v39" />
          <path class="roof-main" d="m91 143 69-39 70 39-70 39Z" />
          <path class="roof-under" d="m91 143 69 39 70-39-5 13-65 38-64-37Z" />
        </g>
        <g class="pagoda-floor floor-mid">
          <path class="pagoda-wall" d="m121 101 39 20 39-20v36l-39 21-39-21Z" />
          <path class="archive-shelves" d="M130 106v34m13-27v34m47-41v34m-13-27v34" />
          <path class="roof-main" d="m103 99 57-34 58 34-58 33Z" />
          <path class="roof-under" d="m103 99 57 33 58-33-5 12-53 32-52-32Z" />
        </g>
        <g class="pagoda-floor floor-high">
          <path class="pagoda-wall" d="m132 63 28 15 28-15v28l-28 15-28-15Z" />
          <path class="roof-main" d="m117 61 43-27 44 27-44 26Z" />
          <path class="roof-under" d="m117 61 43 26 44-26-4 10-40 25-39-25Z" />
        </g>
        <g class="pagoda-balconies">
          <path d="m105 146 55 31 56-31m-101 5v17m15-9v17m60-25v17m15-9v17" />
          <path d="m116 102 44 25 45-25m-79 5v15m13-8v15m55-22v15m-13-8v15" />
          <path d="m128 65 32 18 33-18m-56 5v13m46-13v13" />
        </g>
        <g class="archive-orbits">
          <ellipse cx="160" cy="130" rx="77" ry="42" />
          <circle cx="83" cy="130" r="3" />
          <circle cx="237" cy="130" r="3" />
        </g>
        <path class="roof-ridge" d="M160 35V17m-8 12 8-15 8 15m-48 31-11 2 10-10m82 8 11 2-10-10m-96 47-12 2 10-11m112 9 12 2-10-11m-124 53-15 2 13-12m136 10 15 2-13-12" />
        <path class="architectural-detail" d="m160 38-32 23m32-23 33 23m-33 22-37-22m37 22 38-22m-1 5-45 33m8-31-45 31m45 28-51-28m51 28 52-28m-52 5-57 39m57-39 58 39m-58 35-64-35m64 35 65-35" />
        <g class="pagoda-lanterns"><circle cx="111" cy="108" r="4" /><circle cx="209" cy="108" r="4" /><circle cx="98" cy="153" r="4" /><circle cx="222" cy="153" r="4" /></g>
        <path class="pagoda-steps" d="m130 207 30 15 30-15 14 7-44 22-44-22Z" />
      </g>

      <!-- 06: a monumental palace with towers, terraces, water and a knowledge core. -->
      <g v-else class="landmark landmark-knowledge-palace" transform="translate(21 16) scale(.87)">
        <path class="terrace-side" d="m18 172 142 66 142-66v14l-142 54-142-54Z" />
        <path class="terrace-top" d="m18 172 142-66 142 66-142 66Z" />
        <path class="water-terrace" d="m43 174 117-54 117 54-117 54Z" />
        <path class="ceremony-path" d="m139 224 21-11 21 11-21 11Zm21-11V136" />
        <g class="palace-side palace-left">
          <path class="tower-wall" d="m48 146 36 19 36-19v37l-36 19-36-19Z" />
          <path class="roof-main" d="m37 144 47-29 48 29-48 27Z" />
          <path class="roof-under" d="m37 144 47 27 48-27-4 10-44 26-43-25Z" />
        </g>
        <g class="palace-side palace-right">
          <path class="tower-wall" d="m200 146 36 19 36-19v37l-36 19-36-19Z" />
          <path class="roof-main" d="m188 144 48-29 47 29-47 27Z" />
          <path class="roof-under" d="m188 144 48 27 47-27-4 11-43 25-44-26Z" />
        </g>
        <g class="palace-main lower-palace" transform="translate(-19 -17) scale(1.12)">
          <path class="tower-wall" d="m108 117 52 28 52-28v50l-52 28-52-28Z" />
          <path class="timber" d="M120 124v47m15-39v47m50-55v47m-15-39v47" />
          <path class="roof-main" d="m91 115 69-41 70 41-70 39Z" />
          <path class="roof-under" d="m91 115 69 39 70-39-5 13-65 37-64-37Z" />
        </g>
        <g class="palace-main upper-palace" transform="translate(-29 -22) scale(1.18)">
          <path class="tower-wall" d="m126 76 34 18 34-18v34l-34 18-34-18Z" />
          <path class="roof-main" d="m112 74 48-30 49 30-49 28Z" />
          <path class="roof-under" d="m112 74 48 28 49-28-4 11-45 27-44-27Z" />
        </g>
        <g class="palace-crown" transform="translate(-35 -23) scale(1.22)">
          <path class="tower-wall" d="m139 43 21 11 21-11v22l-21 11-21-11Z" />
          <path class="roof-main" d="m128 41 32-21 33 21-33 19Z" />
          <path class="roof-under" d="m128 41 32 19 33-19-4 9-29 18-28-18Z" />
          <path class="curved-eave" d="M128 41q-9 5-16-1m81 1q9 5 16-1" />
          <path class="crown-spire" d="M160 22V8m-8 11 8-14 8 14" />
        </g>
        <g class="palace-columns">
          <g transform="translate(113 180)"><ellipse cy="19" rx="6" ry="3" /><path d="M-6 0h12v19H-6Z" /><ellipse rx="6" ry="3" /></g>
          <g transform="translate(136 192)"><ellipse cy="19" rx="6" ry="3" /><path d="M-6 0h12v19H-6Z" /><ellipse rx="6" ry="3" /></g>
          <g transform="translate(184 192)"><ellipse cy="19" rx="6" ry="3" /><path d="M-6 0h12v19H-6Z" /><ellipse rx="6" ry="3" /></g>
          <g transform="translate(207 180)"><ellipse cy="19" rx="6" ry="3" /><path d="M-6 0h12v19H-6Z" /><ellipse rx="6" ry="3" /></g>
        </g>
        <path class="roof-ridge" d="m115 73-12 2 10-11m94 10 12 2-10-11m-115 49-14 2 12-12m136 10 14 2-12-12" />
        <path class="architectural-detail" d="m160 24-25 17m25-17 26 17m-26 16-29-16m29 16 30-16m-30 7-55 41m55-41 56 41m-56 37-62-37m62 37 63-37m-139 57 32-18m128 0 32 18" />
        <path class="palace-balustrade" d="M52 177l32 17 32-17m88 0 32 17 32-17M57 173v17m13-10v17m180-24v17m-13-10v17" />
        <g class="knowledge-core">
          <ellipse cx="160" cy="135" rx="29" ry="17" />
          <circle cx="160" cy="126" r="12" />
          <path d="M126 135c10-37 58-37 68 0M160 108V91m-37 27-14-8m88 8 14-8" />
        </g>
        <path class="ceremonial-gate" d="m126 206 34-18 34 18-34 19Zm7-4v22m54-22v22" />
        <g class="beacons"><circle cx="35" cy="171" r="4" /><circle cx="285" cy="171" r="4" /><circle cx="85" cy="207" r="4" /><circle cx="235" cy="207" r="4" /></g>
      </g>

      <path class="academy-scan" d="M45 210h230" />
    </svg>

    <span class="academy-node__badge">
      <Check v-if="state === 'done'" :size="15" stroke-width="3" />
      <LockKeyhole v-else-if="state === 'locked'" :size="14" stroke-width="2.4" />
      <Sparkles v-else :size="14" stroke-width="2.4" />
    </span>
    <span class="academy-node__plaque">{{ label }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { Check, LockKeyhole, Sparkles } from 'lucide-vue-next'

const landmarkNames = ['study-hut', 'herb-garden', 'diagnosis-court', 'lecture-academy', 'archive-pagoda', 'knowledge-palace']

const props = defineProps({
  stage: { type: Number, default: 1 },
  growth: { type: Number, default: 0 },
  label: { type: String, default: '' },
  state: { type: String, default: 'locked' },
})

const normalizedStage = computed(() => Math.min(6, Math.max(1, Math.round(props.stage))))
const landmarkName = computed(() => landmarkNames[normalizedStage.value - 1])
const growthScale = computed(() => (0.92 + Math.min(1, Math.max(0, props.growth)) * 0.08).toFixed(3))
const shadowRadius = computed(() => 62 + normalizedStage.value * 7)
</script>

<style scoped>
.academy-node {
  position: absolute;
  left: 50%;
  top: 50%;
  display: block;
  width: 320px;
  height: 240px;
  color: #1c6654;
  transform: translate(-50%, -57%) scale(var(--academy-growth));
  transform-origin: center bottom;
  transition: transform 360ms cubic-bezier(0.22, 1, 0.36, 1), filter 260ms ease;
}

:global(.week-overview-map .map-dot .academy-node) {
  animation: academy-route-node-enter 340ms cubic-bezier(0.22, 1, 0.36, 1) backwards;
  animation-delay: calc(20ms + var(--academy-enter-index, 0) * 25ms);
}

@keyframes academy-route-node-enter {
  from {
    opacity: 0;
    transform: translate(-50%, -43%) scale(calc(var(--academy-growth) - 0.035));
  }
}

.academy-node__scene { display: block; width: 100%; height: 100%; overflow: visible; filter: drop-shadow(0 12px 11px rgba(36, 74, 61, 0.17)); user-select: none; }
.landmark-shadow {
  fill: rgba(42, 72, 61, 0.15);
  transform-box: fill-box;
  transform-origin: center;
  transition: opacity 300ms ease, transform 360ms cubic-bezier(0.22, 1, 0.36, 1);
}
.terrace-side { fill: #8aa697; stroke: #668274; stroke-width: 1.5; }
.terrace-top { fill: #dce9df; stroke: #6f9383; stroke-width: 1.5; }
.roof-main { fill: #285f50; stroke: #20483d; stroke-width: 1.6; stroke-linejoin: round; }
.roof-under { fill: #d0a04b; stroke: #885f26; stroke-width: 1; }
.roof-ridge, .crown-spire { fill: none; stroke: #d0a04b; stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round; }
.roof-tiles { fill: none; stroke: rgba(224, 184, 102, 0.5); stroke-width: 1; }
.architectural-detail { fill: none; stroke: rgba(227, 191, 111, 0.72); stroke-width: 1; stroke-linecap: round; stroke-linejoin: round; }
.hut-wall-left, .apothecary-wall-left, .hall-wall, .pagoda-wall, .tower-wall, .small-wall, .wing-wall { fill: #eee4cc; stroke: #7a7b6c; stroke-width: 1.25; }
.hut-wall-right, .apothecary-wall-right { fill: #cdbfa1; stroke: #6e7468; stroke-width: 1.25; }
.timber, .archive-shelves { fill: none; stroke: #a85e3f; stroke-width: 2.2; }
.door { fill: #98573c; stroke: #6f3d2d; stroke-width: 1.2; }
.garden-bed, .garden-plots path:not(.garden-lines) { fill: #acc790; stroke: #698463; stroke-width: 1; }
.garden-lines, .herb-stem { fill: none; stroke: #3d7658; stroke-width: 1.5; stroke-linecap: round; }
.herb-leaf { fill: #6b9b68; stroke: #f1e4b5; stroke-width: 1; }
.study-desk, .scroll { fill: #e3ca94; stroke: #8e6840; stroke-width: 1.2; }
.moon-window { fill: #557f70; stroke: #d2a34d; stroke-width: 1.4; }
.bracket-set { fill: none; stroke: #a85e3f; stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; }
.glass-house { fill: none; stroke: #6e9c91; stroke-width: 1.5; }
.glass-fill { fill: rgba(172, 221, 214, 0.36); }
.water-channel, .court-path, .knowledge-ring { fill: none; stroke: #51a795; stroke-width: 2; stroke-linecap: round; stroke-dasharray: 3 5; }
.diagnosis-ring { fill: #e9dfc8; stroke: #b48b42; stroke-width: 2; }
.diagnosis-core { fill: #2a695a; stroke: #d6ad5c; stroke-width: 2; }
.pulse-line { fill: none; stroke: #f3d27c; stroke-width: 2.2; stroke-linejoin: round; }
.diagnosis-halo { fill: none; stroke: rgba(240, 205, 117, 0.9); stroke-width: 1.4; stroke-dasharray: 3 4; }
.diagnosis-columns path, .palace-columns path { fill: #d6c7a7; stroke: #856c50; stroke-width: 1; }
.diagnosis-columns ellipse, .palace-columns ellipse { fill: #e9dec3; stroke: #876d4e; stroke-width: 1; }
.court-posts circle, .beacons circle { fill: #d0a04b; stroke: #fff3cf; stroke-width: 1.4; }
.academy-plaza { fill: #edf1e6; stroke: #81a493; stroke-width: 1.4; }
.upper-wall { fill: #e8ddc4; stroke: #76776b; stroke-width: 1.3; }
.upper-lattice { fill: none; stroke: #9d593e; stroke-width: 2; }
.upper-roof { fill: #214f43; stroke: #d0a04b; stroke-width: 1.6; }
.upper-eave { fill: #3a735f; stroke: #886329; stroke-width: 1; }
.curved-eave { fill: none; stroke: #d0a04b; stroke-width: 2.1; stroke-linecap: round; stroke-linejoin: round; }
.balcony-rail, .pagoda-balconies { fill: none; stroke: #9d593e; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.open-book { fill: #f8eed3; stroke: #a2743d; stroke-width: 1.5; }
.pagoda-lanterns circle { fill: #d98f43; stroke: #fff2c3; stroke-width: 1.4; }
.archive-orbits { fill: none; stroke: #65a996; stroke-width: 1.4; stroke-dasharray: 4 7; }
.archive-orbits circle { fill: #d4a34c; stroke: #fff1c7; stroke-width: 1; }
.pagoda-steps, .ceremonial-gate { fill: #e7dcc4; stroke: #917f68; stroke-width: 1.3; }
.water-terrace { fill: #b9dcd4; stroke: #5c9a8b; stroke-width: 1.5; }
.palace-balustrade { fill: none; stroke: #9d593e; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }
.ceremony-path { fill: #eee4cd; stroke: #a08b6b; stroke-width: 1.2; }
.knowledge-core ellipse { fill: rgba(27, 104, 88, 0.3); stroke: #d4ae5a; stroke-width: 1.5; }
.knowledge-core circle { fill: #55c8ad; stroke: #f1d88a; stroke-width: 2; }
.knowledge-core path { fill: none; stroke: #61cdb6; stroke-width: 1.8; stroke-linecap: round; stroke-dasharray: 4 5; }
.academy-scan { fill: none; stroke: rgba(38, 190, 155, 0.65); stroke-dasharray: 4 10; stroke-width: 1.4; }

.academy-node__badge {
  position: absolute;
  top: 34%;
  right: 7%;
  display: grid;
  place-items: center;
  width: 29px;
  height: 29px;
  border: 3px solid rgba(255, 255, 255, 0.9);
  border-radius: 50%;
  color: #fff;
  background: #0d8c6e;
  box-shadow: 0 7px 15px rgba(25, 82, 65, 0.22);
}

.stage-1 .academy-node__badge { right: 16%; }
.stage-5 .academy-node__badge { top: 25%; right: 12%; }
.stage-6 .academy-node__badge { top: 22%; right: 4%; }

.academy-node__plaque {
  position: absolute;
  left: 50%;
  bottom: -3px;
  min-width: 58px;
  padding: 5px 10px;
  border: 1px solid rgba(42, 103, 82, 0.38);
  border-radius: 4px;
  color: #174f41;
  background: rgba(250, 252, 246, 0.95);
  box-shadow: 0 5px 12px rgba(35, 72, 59, 0.12);
  font-size: 13px;
  font-weight: 900;
  line-height: 1;
  white-space: nowrap;
  transform: translateX(-50%);
}

.state-done .academy-node__badge { background: #0a8f6d; }
.state-current .academy-node__badge { background: #c7892d; }
.state-locked { filter: saturate(0.62) opacity(0.86); }
.state-locked .academy-node__badge { color: #5e7168; background: #e7ede9; }

:global(.map-dot:hover .academy-node),
:global(.map-dot:focus-visible .academy-node),
:global(.map-dot[data-active='true'] .academy-node) {
  filter: saturate(1.08) drop-shadow(0 16px 16px rgba(26, 88, 69, 0.18));
  transform: translate(-50%, -66%) scale(calc(var(--academy-growth) + 0.025));
}

:global(.map-dot:hover .academy-node .landmark-shadow),
:global(.map-dot:focus-visible .academy-node .landmark-shadow),
:global(.map-dot[data-active='true'] .academy-node .landmark-shadow) {
  opacity: 0.52;
  transform: scaleX(0.8);
}

:global(.map-dot.current .academy-node .academy-scan) { animation: academy-scan-flow 2.4s linear infinite; }
@keyframes academy-scan-flow { to { stroke-dashoffset: -28; } }

@media (max-width: 600px) {
  .academy-node { width: 204px; height: 153px; }
  .academy-node__plaque { bottom: -5px; font-size: 12px; }
  .academy-node__badge { width: 27px; height: 27px; }

  :global(.map-dot:hover .academy-node),
  :global(.map-dot:focus-visible .academy-node),
  :global(.map-dot[data-active='true'] .academy-node) {
    transform: translate(-50%, -61%) scale(calc(var(--academy-growth) + 0.015));
  }
}

@media (prefers-reduced-motion: reduce) {
  .academy-node { transition: none; }
  :global(.week-overview-map .map-dot .academy-node) { animation: none; }
  :global(.map-dot.current .academy-node .academy-scan) { animation: none; }
}
</style>
