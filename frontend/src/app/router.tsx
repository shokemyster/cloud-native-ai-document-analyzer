import { Navigate, createBrowserRouter } from 'react-router-dom'

import { AppLayout } from '../components/AppLayout/AppLayout'
import { UploadPage } from '../features/documents/pages/UploadPage'
import { HistoryPage } from '../features/jobs/pages/HistoryPage'
import { JobDetailPage } from '../features/jobs/pages/JobDetailPage'
import { NotFoundPage } from './NotFoundPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <Navigate replace to="/upload" />,
      },
      {
        path: 'upload',
        element: <UploadPage />,
      },
      {
        path: 'history',
        element: <HistoryPage />,
      },
      {
        path: 'jobs/:jobId',
        element: <JobDetailPage />,
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
])
