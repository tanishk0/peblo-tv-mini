import { Link, NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import { ApiError } from './api'
import { useAuth } from './auth'

export function Loading() { return <div className="state loading" role="status"><b>Loading</b><p>Please wait while we get your content.</p></div> }
export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) { if (error instanceof ApiError && error.status === 403) return <PermissionDenied />; return <div className="state error" role="alert"><h2>We could not load this page</h2><p>{error instanceof Error ? error.message : 'Please check your connection and try again.'}</p>{retry && <button onClick={retry}>Try again</button>}</div> }
export function PermissionDenied() { return <div className="state permission"><h2>You do not have access to this page</h2><p>Ask an administrator if you need permission to publish content.</p><Link className="button secondary" to="/shows">Go to shows</Link></div> }
export function Protected({ admin = false }: { admin?: boolean }) { const { user, loading } = useAuth(); const location = useLocation(); if (loading) return <Loading />; if (!user) return <Navigate to="/login" state={{ from: location }} replace />; if (admin && user.role !== 'admin') return <PermissionDenied />; return <Outlet /> }
export function Shell() { const { user, logout } = useAuth(); return <><header><Link to="/shows" className="brand">Peblo CMS</Link><nav aria-label="CMS sections"><NavLink to="/shows">Shows</NavLink><NavLink to="/episodes">Episodes</NavLink>{user?.role === 'admin' && <NavLink to="/publish">Publish</NavLink>}</nav><span className="user">{user?.email} · {user?.role}</span><button className="link" onClick={logout}>Sign out</button></header><main><Outlet /></main></> }
