import { cn } from "@/lib/utils";
import * as React from "react";

const Label = React.forwardRef<
  HTMLLabelElement,
  React.LabelHTMLAttributes<HTMLLabelElement>
>(({ className, ...props }, ref) => {
  return (
    <label
      ref={ref}
      className={cn("text-sm font-medium leading-none text-secondary-foreground", className)}
      {...props}
    />
  );
});

Label.displayName = "Label";

export { Label };
