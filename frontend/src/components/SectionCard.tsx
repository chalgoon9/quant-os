import type { ReactNode } from "react";

type SectionCardProps = {
  title: string;
  eyebrow?: string;
  description?: string;
  className?: string;
  action?: ReactNode;
  children: ReactNode;
};

export function SectionCard({
  title,
  eyebrow,
  description,
  className,
  action,
  children,
}: SectionCardProps) {
  return (
    <section className={`panel${className ? ` ${className}` : ""}`}>
      <header className="panel__header">
        <div>
          {eyebrow ? <p className="panel__eyebrow">{eyebrow}</p> : null}
          <h2 className="panel__title">{title}</h2>
          {description ? <p className="panel__description">{description}</p> : null}
        </div>
        {action ? <div className="panel__action">{action}</div> : null}
      </header>
      <div className="panel__body">{children}</div>
    </section>
  );
}
