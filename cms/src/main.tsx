import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth'
import { Protected, Shell } from './components'
import { EpisodeListPage, LoginPage, ShowFormPage, ShowListPage, ShowManagementPage, PublishPage } from './pages'
import './styles.css'

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } })
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={queryClient}><AuthProvider><BrowserRouter><Routes><Route path="/login" element={<LoginPage />} /><Route element={<Protected />}><Route element={<Shell />}><Route path="/shows" element={<ShowListPage />} /><Route path="/shows/new" element={<ShowFormPage />} /><Route path="/shows/:showId/edit" element={<ShowFormPage />} /><Route path="/shows/:showId" element={<ShowManagementPage />} /><Route path="/episodes" element={<EpisodeListPage />} /><Route element={<Protected admin />}><Route path="/publish" element={<PublishPage />} /></Route></Route></Route><Route path="*" element={<Navigate to="/shows" replace />} /></Routes></BrowserRouter></AuthProvider></QueryClientProvider></React.StrictMode>)
