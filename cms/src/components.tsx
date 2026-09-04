import { Link, Navigate, Outlet, useLocation } from 'react-router-dom'
import { ApiError } from './api'
import { useAuth } from './auth'

export function Loading() { return <p className="state">Loading…</p> }
export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) { if (error instanceof ApiError && error.status === 403) return <PermissionDenied />; return <div className="state error"><p>{error instanceof Error ? error.message : 'Unable to load data.'}</p>{retry && <button onClick={retry}>Try again</button>}</div> }
export function PermissionDenied() { return <div className="state"><h2>Permission denied</h2><p>Your account does not have access to this area. Ask an administrator if you need publishing access.</p></div> }
export function Protected({ admin = false }: { admin?: boolean }) { const { user, loading } = useAuth(); const location = useLocation(); if (loading) return <Loading />; if (!user) return <Navigate to="/login" state={{ from: location }} replace />; if (admin && user.role !== 'admin') return <PermissionDenied />; return <Outlet /> }
export function Shell() { const { user, logout } = useAuth(); return <><header><Link to="/shows" className="brand">Peblo CMS</Link><nav><Link to="/shows">Content</Link>{user?.role === 'admin' && <Link to="/publish">Publish</Link>}</nav><span className="user">{user?.email} · {user?.role}</span><button className="link" onClick={logout}>Sign out</button></header><main><Outlet /></main></> }
