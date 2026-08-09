import * as React from 'react'
import * as ToggleGroupPrimitive from '@radix-ui/react-toggle-group'
import { cn } from '@renderer/lib/utils'

export const ToggleGroup = ToggleGroupPrimitive.Root

export const ToggleGroupItem = React.forwardRef<
  React.ElementRef<typeof ToggleGroupPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof ToggleGroupPrimitive.Item>
>(({ className, ...props }, ref) => (
  <ToggleGroupPrimitive.Item
    ref={ref}
    className={cn(
      'inline-flex h-8 w-8 shrink-0 items-center justify-center text-[#6a745a] transition-colors',
      'focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8fbc8f]',
      'disabled:pointer-events-none disabled:opacity-45',
      'data-[state=on]:bg-[#5d6b4d] data-[state=on]:text-white data-[state=on]:shadow-[0_5px_12px_rgba(93,107,77,0.18)]',
      'data-[state=off]:hover:bg-[#d4e4c1]/72',
      className
    )}
    {...props}
  />
))
ToggleGroupItem.displayName = ToggleGroupPrimitive.Item.displayName

