import { labels, type Page } from '../workspace'

export default function LedgerPage({ page }: { page: Page }) {
  return <section className="welcome"><h1>{labels[page]}</h1></section>
}