export function Loading({ label = "Loading…" }: { label?: string }) {
  return <div className="loading">{label}</div>;
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
  return <div className="error">Could not complete this request. {message}</div>;
}

export function Toast({ message }: { message: string | null }) {
  if (!message) return null;
  return <div className="toast">{message}</div>;
}
