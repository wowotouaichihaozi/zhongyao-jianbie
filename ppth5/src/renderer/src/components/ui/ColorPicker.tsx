import { useEffect, useRef, useState } from 'react'
import { HexColorInput, RgbaStringColorPicker } from 'react-colorful'
import { Popover, PopoverContent, PopoverTrigger } from './Popover'

interface ColorPickerProps {
  value: string | undefined
  onChange: (value: string) => void
  onCommit?: (value: string) => void
  className?: string
}

function parseColor(value: string | undefined): { hex: string; alpha: number } {
  if (!value) return { hex: '#000000', alpha: 1 }

  const rgbaMatch = value.match(/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\)$/)
  if (rgbaMatch) {
    const r = parseInt(rgbaMatch[1])
    const g = parseInt(rgbaMatch[2])
    const b = parseInt(rgbaMatch[3])
    const a = rgbaMatch[4] !== undefined ? parseFloat(rgbaMatch[4]) : 1
    const hex = '#' + [r, g, b].map((c) => c.toString(16).padStart(2, '0')).join('')
    return { hex, alpha: Math.round(a * 100) / 100 }
  }

  if (value.startsWith('#')) {
    if (value.length === 9) {
      const hex = value.slice(0, 7)
      const alpha = Math.round((parseInt(value.slice(7, 9), 16) / 255) * 100) / 100
      return { hex, alpha }
    }
    return { hex: value.slice(0, 7), alpha: 1 }
  }

  return { hex: '#000000', alpha: 1 }
}

function toRgbaString(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function formatColor(hex: string, alpha: number): string {
  if (alpha >= 1) return hex
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

export function ColorPicker({ value, onChange, onCommit, className }: ColorPickerProps) {
  const { hex, alpha } = parseColor(value)
  const [open, setOpen] = useState(false)
  const [tempHex, setTempHex] = useState(hex)
  const [tempAlpha, setTempAlpha] = useState(alpha)
  const alphaRef = useRef<HTMLInputElement>(null)
  const latestColorRef = useRef(formatColor(hex, alpha))

  useEffect(() => {
    const { hex: newHex, alpha: newAlpha } = parseColor(value)
    setTempHex(newHex)
    setTempAlpha(newAlpha)
    latestColorRef.current = formatColor(newHex, newAlpha)
  }, [value])

  const commitColor = (newHex: string, newAlpha: number) => {
    const nextColor = formatColor(newHex, newAlpha)
    latestColorRef.current = nextColor
    onChange(nextColor)
  }

  const displayColor = alpha >= 1 ? hex : toRgbaString(hex, alpha)

  return (
    <div className={className}>
      <Popover
        open={open}
        onOpenChange={(nextOpen) => {
          setOpen(nextOpen)
          if (!nextOpen) onCommit?.(latestColorRef.current)
        }}
      >
        <PopoverTrigger asChild>
          <button
            type="button"
            className="h-8 w-10 shrink-0 cursor-pointer rounded-full border border-[#c8d6ba]/70 p-1"
            style={{ backgroundColor: 'transparent' }}
          >
            <div
              className="h-full w-full rounded-full"
              style={{
                backgroundColor: displayColor,
                backgroundImage:
                  alpha < 1
                    ? 'linear-gradient(45deg, #ccc 25%, transparent 25%), linear-gradient(-45deg, #ccc 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #ccc 75%), linear-gradient(-45deg, transparent 75%, #ccc 75%)'
                    : undefined,
                backgroundSize: alpha < 1 ? '6px 6px' : undefined,
                backgroundPosition: alpha < 1 ? '0 0, 0 3px, 3px -3px, -3px 0' : undefined,
              }}
            />
          </button>
        </PopoverTrigger>
        <PopoverContent
          className="color-picker-popover w-[208px] rounded-lg border border-[#c8d6ba]/60 bg-[#f0faf5] p-3 shadow-[0_8px_30px_-6px_rgba(74,59,42,0.18)]"
          align="start"
          sideOffset={8}
        >
          <RgbaStringColorPicker
            color={toRgbaString(tempHex, tempAlpha)}
            onChange={(color) => {
              const m = color.match(/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\)$/)
              if (m) {
                const newHex =
                  '#' +
                  [m[1], m[2], m[3]].map((c) => parseInt(c).toString(16).padStart(2, '0')).join('')
                const newAlpha = m[4] !== undefined ? parseFloat(m[4]) : 1
                setTempHex(newHex)
                setTempAlpha(newAlpha)
                commitColor(newHex, newAlpha)
              }
            }}
          />

          <div className="mt-3 flex items-center gap-2">
            {/* hex input */}
            <div className="relative flex-1">
              <span className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-[#a0967e]">
                #
              </span>
              <HexColorInput
                color={tempHex}
                onChange={(newHex) => {
                  setTempHex(newHex)
                  commitColor(newHex, tempAlpha)
                }}
                className="color-picker-input h-7 w-full rounded-lg border border-[#c8d6ba]/60 bg-[#faf6ee] pl-4 pr-2 text-[11px] tracking-wide text-[#3f4b35] outline-none transition-colors focus:border-[#9bb98a]"
              />
            </div>
            {/* alpha input */}
            <div className="flex items-center gap-1">
              <input
                ref={alphaRef}
                type="number"
                min={0}
                max={100}
                value={Math.round(tempAlpha * 100)}
                onChange={(e) => {
                  const val = Math.min(100, Math.max(0, Number(e.target.value)))
                  const newAlpha = val / 100
                  setTempAlpha(newAlpha)
                  commitColor(tempHex, newAlpha)
                }}
                className="color-picker-input h-7 w-[42px] rounded-lg border border-[#c8d6ba]/60 bg-[#faf6ee] px-1.5 text-right text-[11px] text-[#3f4b35] outline-none transition-colors focus:border-[#9bb98a]"
              />
              <span className="text-[10px] text-[#a0967e]">%</span>
            </div>
          </div>

          <style>{`
            .color-picker-popover .react-colorful {
              width: 100% !important;
              height: auto !important;
              border-radius: 6px !important;
            }
            .color-picker-popover .react-colorful__saturation {
              height: 128px !important;
              border-radius: 6px 6px 0 0 !important;
              border-bottom: 12px solid #000 !important;
            }
            .color-picker-popover .react-colorful__hue {
              height: 12px !important;
              border-radius: 0 !important;
            }
            .color-picker-popover .react-colorful__alpha {
              height: 12px !important;
              border-radius: 0 0 6px 6px !important;
            }
            .color-picker-popover .react-colorful__pointer {
              width: 14px !important;
              height: 14px !important;
              border: 2px solid #fff !important;
              box-shadow: 0 0 0 1px rgba(0,0,0,0.12), 0 1px 3px rgba(0,0,0,0.25) !important;
              border-radius: 50% !important;
            }
            .color-picker-popover .react-colorful__hue .react-colorful__pointer,
            .color-picker-popover .react-colorful__alpha .react-colorful__pointer {
              width: 10px !important;
              height: 10px !important;
              top: 50% !important;
              transform: translate(-50%, -50%) !important;
            }
            /* hide number input spinners */
            .color-picker-input::-webkit-inner-spin-button,
            .color-picker-input::-webkit-outer-spin-button {
              -webkit-appearance: none;
              margin: 0;
            }
            .color-picker-input[type=number] {
              -moz-appearance: textfield;
            }
          `}</style>
        </PopoverContent>
      </Popover>
    </div>
  )
}
