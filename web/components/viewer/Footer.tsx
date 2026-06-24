export function Footer() {
  return (
    <footer className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-hairline pt-5 text-[0.75rem] text-muted">
      <span className="font-mono text-secondary">veritas</span>
      <span className="text-faint">model-agnostic leakage &amp; robustness auditor</span>
      <span className="ml-auto flex gap-4">
        <a
          href="https://github.com/shreyjain11/veritas"
          target="_blank"
          rel="noreferrer"
          className="rounded-sm text-secondary underline-offset-4 transition-colors hover:text-fg hover:underline focus-visible:outline-2 focus-visible:outline-iris"
        >
          GitHub
        </a>
        <a
          href="https://shreyjain11.github.io/veritas/"
          target="_blank"
          rel="noreferrer"
          className="rounded-sm text-secondary underline-offset-4 transition-colors hover:text-fg hover:underline focus-visible:outline-2 focus-visible:outline-iris"
        >
          Docs
        </a>
      </span>
    </footer>
  );
}
