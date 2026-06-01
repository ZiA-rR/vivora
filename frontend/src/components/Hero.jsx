// Top-of-page brand header: monogram badge + title + tagline.
export default function Hero() {
  return (
    <header className="flex items-center gap-4 py-2">
      <div className="flex h-13 w-13 items-center justify-center rounded-xl border-[1.5px] border-teal bg-navy font-serif text-3xl font-bold leading-none text-teal">
        V
      </div>
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-ink">Vivora</h1>
        <p className="mt-0.5 text-sm text-muted">
          Turn any GitHub repo into a viva-ready brief — profile, Q&amp;A, report
          and slides.
        </p>
      </div>
    </header>
  );
}
