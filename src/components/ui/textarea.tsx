import * as React from "react"

import { cn } from "@/lib/utils"

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[80px] w-full rounded-[14px] border border-white/55 bg-white/40 px-3 py-2 text-sm shadow-[inset_0_1px_2px_hsl(258_62%_40%/0.08),inset_0_1px_0_hsl(0_0%_100%/0.7)] backdrop-blur-xl backdrop-saturate-[1.6] ring-offset-background placeholder:text-muted-foreground transition-colors focus-visible:outline-none focus-visible:border-primary/50 focus-visible:bg-white/55 focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Textarea.displayName = "Textarea"

export { Textarea }