export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="loading" role="status">
      <div className="skeleton" />
      <div className="skeleton short" />
      <div className="muted">{label}</div>
    </div>
  );
}

export function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      <div className="muted">{body}</div>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="error" role="alert">
      Something went wrong
      <div className="detail">{message}</div>
    </div>
  );
}

export function Toast({ message }: { message: string | null }) {
  if (!message) return null;
  return <div className="toast">{message}</div>;
}
