import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <section aria-labelledby="not-found-heading">
      <header className="page-header">
        <h1 id="not-found-heading">Page not found</h1>
        <p className="page-description">
          The requested page does not exist.
        </p>
      </header>

      <Link className="text-link" to="/upload">
        Return to upload
      </Link>
    </section>
  )
}
