"use client";

/**
 * Card (UX-3 U19) — empacota a superfície `.card` do Presença.
 * `as` permite `section`/`article` etc. sem mudar o visual (mesma classe).
 */
import React from "react";

export function Card({
  as: Tag = "div",
  className,
  children,
  ...rest
}: React.HTMLAttributes<HTMLElement> & { as?: React.ElementType }) {
  return (
    <Tag className={["card", className].filter(Boolean).join(" ")} {...rest}>
      {children}
    </Tag>
  );
}
