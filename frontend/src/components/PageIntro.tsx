type PageIntroProps = {
  title: string;
  description: string;
  note?: string;
};

export function PageIntro({ title, description, note }: PageIntroProps) {
  return (
    <section className="page-intro">
      <p className="page-intro__eyebrow">안내</p>
      <h1 className="page-intro__title">{title}</h1>
      <p className="page-intro__description">{description}</p>
      {note ? <p className="page-intro__note">{note}</p> : null}
    </section>
  );
}
