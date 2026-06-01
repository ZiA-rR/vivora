// Small reusable presentational pieces shared across the app.

export function Spinner({ className = "" }) {
  return (
    <span
      className={
        "inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent " +
        className
      }
      aria-hidden="true"
    />
  );
}

// Primary = teal→blue gradient. Secondary = outlined. Both share shape.
export function Button({
  children,
  onClick,
  disabled = false,
  loading = false,
  variant = "primary",
  type = "button",
  className = "",
}) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold " +
    "transition disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none " +
    "focus-visible:ring-2 focus-visible:ring-teal/60";
  const styles =
    variant === "primary"
      ? "bg-gradient-to-br from-teal to-blue text-navy hover:brightness-110"
      : "border border-teal/40 bg-surface2 text-ink hover:border-teal hover:bg-surface";
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${base} ${styles} ${className}`}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
}

// A link styled like a secondary button — used for file downloads.
export function DownloadLink({ href, children }) {
  return (
    <a
      href={href}
      className="inline-flex items-center justify-center gap-2 rounded-xl border border-teal/40 bg-surface2 px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-teal hover:bg-surface"
    >
      {children}
    </a>
  );
}

export function Card({ children, className = "" }) {
  return (
    <section
      className={
        "rounded-2xl border border-white/5 bg-surface p-5 sm:p-6 " + className
      }
    >
      {children}
    </section>
  );
}

export function SectionTitle({ children, hint }) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold tracking-tight text-ink">{children}</h2>
      {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
    </div>
  );
}
