import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { catalogueApi } from './api'
import { ArtworkImage, bannerFor, EmptyState, EpisodeCard, ErrorState, Loading, PosterCard } from './components'
import type { Catalogue, Show } from './types'

const categories = ['adventure','folk','friendship','india','language','learning','maths','music','nature','reading','science','singalong','stories','travel','values']
const languages = ['en', 'hi']
function useDebounced(value: string, delay = 300) { const [debounced, setDebounced] = useState(value); useEffect(() => { const timer = setTimeout(() => setDebounced(value), delay); return () => clearTimeout(timer) }, [value, delay]); return debounced }

function SearchControls({ value, setValue, category, setCategory, language, setLanguage }: { value: string; setValue: (x: string) => void; category: string; setCategory: (x: string) => void; language: string; setLanguage: (x: string) => void }) { const active = [value && `Search: ${value}`, category && `Category: ${category}`, language && `Language: ${language}`].filter(Boolean); return <section className="search"><input aria-label="Search catalogue" placeholder="Search shows, episodes, or categories" value={value} onChange={e => setValue(e.target.value)} /><select aria-label="Filter by category" value={category} onChange={e => setCategory(e.target.value)}><option value="">All categories</option>{categories.map(item => <option key={item}>{item}</option>)}</select><select aria-label="Filter by language" value={language} onChange={e => setLanguage(e.target.value)}><option value="">All languages</option>{languages.map(item => <option key={item}>{item.toUpperCase()}</option>)}</select>{active.length > 0 && <div className="active"><span>{active.join(' · ')}</span><button onClick={() => { setValue(''); setCategory(''); setLanguage('') }}>Clear filters</button></div>}</section> }

export function HomePage() {
  const [text, setText] = useState(''); const [category, setCategory] = useState(''); const [language, setLanguage] = useState(''); const q = useDebounced(text)
  const searching = Boolean(q || category || language)
  const catalogue = useQuery({ queryKey: ['catalogue'], queryFn: catalogueApi.current, enabled: !searching })
  const search = useQuery({ queryKey: ['catalogue-search', q, category, language], queryFn: () => catalogueApi.search({ q, category, language }), enabled: searching })
  const result = searching ? search : catalogue
  if (result.isLoading) return <main><SearchControls value={text} setValue={setText} category={category} setCategory={setCategory} language={language} setLanguage={setLanguage}/><Loading/></main>
  if (result.error) return <main><SearchControls value={text} setValue={setText} category={category} setCategory={setCategory} language={language} setLanguage={setLanguage}/><ErrorState error={result.error} retry={() => result.refetch()}/></main>
  const data = result.data as Catalogue; const featured = data.sections.find(section => section.id === 'featured')?.shows[0] ?? data.sections[0]?.shows[0]
  return <main><SearchControls value={text} setValue={setText} category={category} setCategory={setCategory} language={language} setLanguage={setLanguage}/>{data.sections.length === 0 ? <EmptyState/> : <>{featured && !searching && <Hero show={featured}/>}<div className="rows">{data.sections.map(section => <section className="content-row" key={section.id}><h2>{section.id}</h2><div className="row-scroll">{section.shows.map(show => <PosterCard key={show.id} show={show}/>)}</div></section>)}</div></>}</main>
}

function Hero({ show }: { show: Show }) { return <section className="hero"><ArtworkImage artwork={bannerFor(show)} kind="banner" alt={`${show.title} banner`}/><div className="hero-copy"><p>Featured</p><h1>{show.title}</h1><p>{show.synopsis || 'A new Peblo story to enjoy together.'}</p><Link className="watch" to={`/shows/${show.slug}`}>Explore show</Link></div></section> }

export function ShowPage() {
  const { slug } = useParams(); const query = useQuery({ queryKey: ['catalogue'], queryFn: catalogueApi.current });
  if (query.isLoading) return <main><Loading/></main>; if (query.error) return <main><ErrorState error={query.error} retry={() => query.refetch()}/></main>
  const show = query.data!.sections.flatMap(section => section.shows).find(item => item.slug === slug)
  if (!show) return <main><div className="state"><h2>Show not found</h2><p>This show is not in the current published catalogue.</p><Link to="/">Back to browsing</Link></div></main>
  return <main className="show-detail"><Link className="back" to="/">← Browse all shows</Link><section className="detail-hero"><ArtworkImage artwork={bannerFor(show)} kind="banner" alt={`${show.title} banner`}/><div><h1>{show.title}</h1><p>{show.synopsis || 'No synopsis available.'}</p><div className="tags">{show.categories.map(category => <span key={category}>{category}</span>)}</div></div></section><section><h2>Episodes</h2>{show.seasons.map(season => <div className="season" key={season.season_number}><h3>Season {season.season_number}</h3>{season.episodes.map(entry => <EpisodeCard key={entry.content_group} entry={entry}/>)}</div>)}</section>{show.trailers.length > 0 && <section className="trailers"><h2>Trailers</h2>{show.trailers.map(entry => <EpisodeCard key={entry.content_group} entry={entry}/>)}</section>}</main>
}
