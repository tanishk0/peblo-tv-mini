import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { HomePage, ShowPage } from './pages'
import './styles.css'

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 30_000 } } })
function Layout({ children }: { children: React.ReactNode }) { return <><header><Link to="/">peblo <span>tv</span></Link><p>Stories for curious young minds</p></header>{children}</> }
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={queryClient}><BrowserRouter><Layout><Routes><Route path="/" element={<HomePage/>}/><Route path="/shows/:slug" element={<ShowPage/>}/></Routes></Layout></BrowserRouter></QueryClientProvider></React.StrictMode>)
