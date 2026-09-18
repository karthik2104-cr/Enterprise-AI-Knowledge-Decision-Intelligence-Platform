export default function SettingsPage() {
  return (
    <div>
      <h2 className="page-title">Settings</h2>
      <p className="lede">
        Runtime configuration is supplied through environment variables. This UI does not store secrets.
        Authentication is a demo JWT user, not SSO.
      </p>
      <div className="card">
        <table>
          <tbody>
            <tr>
              <td>LLM provider</td>
              <td>
                <code>LLM_PROVIDER=mock</code> (default, deterministic) or <code>openai</code>
              </td>
            </tr>
            <tr>
              <td>Embedding provider</td>
              <td>
                <code>EMBEDDING_PROVIDER=mock</code> uses hashed bag-of-words vectors, not a production embedding model
              </td>
            </tr>
            <tr>
              <td>Database</td>
              <td>
                SQLite via <code>DATABASE_URL</code> locally; PostgreSQL in Docker Compose
              </td>
            </tr>
            <tr>
              <td>Demo user</td>
              <td>analyst@northwind-demo.com — password is in <code>.env.example</code></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
