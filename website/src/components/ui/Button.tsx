import React from "react";
import { cn } from "@/lib/utils";
import Link from "next/link";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
  href?: string;
}

export function Button({
  className,
  variant = "primary",
  size = "md",
  children,
  href,
  ...props
}: ButtonProps) {
  const baseStyles = "relative font-medium text-sm transition-all inline-flex items-center justify-center gap-2 rounded-xl";

  const variants = {
    primary: "bg-indigo-500 text-white hover:bg-indigo-400 shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30",
    secondary: "bg-white text-zinc-900 hover:bg-zinc-100 shadow-lg",
    outline: "border border-white/10 text-zinc-300 hover:border-indigo-500/40 hover:text-white hover:bg-white/[0.03]",
    ghost: "text-zinc-400 hover:text-white hover:bg-white/[0.04]"
  };

  const sizes = {
    sm: "px-4 py-2 text-xs",
    md: "px-6 py-3",
    lg: "px-8 py-3.5",
  };

  const finalClassName = cn(baseStyles, variants[variant], sizes[size], className);

  if (href) {
    return (
      <Link href={href} className={finalClassName}>
        {children}
      </Link>
    );
  }

  return (
    <button className={finalClassName} {...props}>
      {children}
    </button>
  );
}
