import { NavLink, Outlet } from 'react-router-dom'

import styles from './AppLayout.module.css'

function navigationClassName({ isActive }: { isActive: boolean }) {
  return [
    styles.navigationLink,
    isActive ? styles.navigationLinkActive : undefined,
  ]
    .filter(Boolean)
    .join(' ')
}

export function AppLayout() {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <NavLink className={styles.brand} to="/upload">
            AI Document Analyzer
          </NavLink>

          <nav aria-label="Primary navigation" className={styles.navigation}>
            <NavLink className={navigationClassName} end to="/upload">
              Upload
            </NavLink>
            <NavLink className={navigationClassName} end to="/history">
              History
            </NavLink>
          </nav>
        </div>
      </header>

      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}
