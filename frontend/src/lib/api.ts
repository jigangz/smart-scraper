const BASE_URL = "http://localhost:8000"

export interface Job {
  id: string
  name: string
  url: string
  selectors: Record<string, string>
  schedule: string
  mode: "fast" | "dynamic" | "stealth"
  status: "running" | "completed" | "failed" | "scheduled" | "idle"
  created_at: string
  last_run: string
  results_count: number
}

export interface Result {
  id: string
  job_id: string
  job_name: string
  data: Record<string, string | number>
  scraped_at: string
}

export interface Stats {
  total_jobs: number
  active_jobs: number
  total_results: number
  success_rate: number
  recent_activity: { date: string; count: number }[]
}

// ── Mock Data ────────────────────────────────────────────────────────────────

export const mockJobs: Job[] = [
  {
    id: "job-001",
    name: "Amazon Product Tracker",
    url: "https://www.amazon.com/s?k=wireless+headphones",
    selectors: { title: ".s-title-instructions-style span", price: ".a-price-whole", rating: ".a-icon-alt" },
    schedule: "Every 30 min",
    mode: "stealth",
    status: "running",
    created_at: "2026-03-15T08:30:00Z",
    last_run: "2026-04-01T10:28:00Z",
    results_count: 2340,
  },
  {
    id: "job-002",
    name: "eBay Electronics Monitor",
    url: "https://www.ebay.com/sch/i.html?_nkw=laptop",
    selectors: { title: ".s-item__title", price: ".s-item__price", condition: ".SECONDARY_INFO" },
    schedule: "Hourly",
    mode: "dynamic",
    status: "completed",
    created_at: "2026-03-18T14:00:00Z",
    last_run: "2026-04-01T09:00:00Z",
    results_count: 1856,
  },
  {
    id: "job-003",
    name: "Hacker News Top Stories",
    url: "https://news.ycombinator.com/",
    selectors: { title: ".titleline a", score: ".score", comments: ".subline a:last-child" },
    schedule: "Daily",
    mode: "fast",
    status: "completed",
    created_at: "2026-03-20T09:00:00Z",
    last_run: "2026-04-01T06:00:00Z",
    results_count: 4520,
  },
  {
    id: "job-004",
    name: "Real Estate Listings",
    url: "https://www.zillow.com/homes/for_sale/",
    selectors: { address: ".list-card-addr", price: ".list-card-price", beds: ".list-card-details li:first-child" },
    schedule: "Every 30 min",
    mode: "stealth",
    status: "failed",
    created_at: "2026-03-22T11:15:00Z",
    last_run: "2026-04-01T10:15:00Z",
    results_count: 890,
  },
  {
    id: "job-005",
    name: "Weather Data Collector",
    url: "https://weather.com/weather/tenday/",
    selectors: { day: ".DetailsSummary--daypartName", temp: ".DetailsSummary--tempValue", desc: ".DetailsSummary--extendedData" },
    schedule: "Daily",
    mode: "dynamic",
    status: "scheduled",
    created_at: "2026-03-25T16:45:00Z",
    last_run: "2026-03-31T16:45:00Z",
    results_count: 210,
  },
  {
    id: "job-006",
    name: "GitHub Trending Repos",
    url: "https://github.com/trending",
    selectors: { repo: ".h3 a", description: "p.col-9", stars: ".d-inline-block.float-sm-right" },
    schedule: "One-time",
    mode: "fast",
    status: "idle",
    created_at: "2026-03-28T20:00:00Z",
    last_run: "2026-03-28T20:05:00Z",
    results_count: 75,
  },
]

export const mockResults: Result[] = [
  { id: "res-001", job_id: "job-001", job_name: "Amazon Product Tracker", data: { title: "Sony WH-1000XM5 Wireless Headphones", price: 278.00, rating: "4.6 out of 5", reviews: 12453, seller: "Amazon.com" }, scraped_at: "2026-04-01T10:28:00Z" },
  { id: "res-002", job_id: "job-001", job_name: "Amazon Product Tracker", data: { title: "Apple AirPods Pro (2nd Gen)", price: 189.99, rating: "4.7 out of 5", reviews: 89201, seller: "Amazon.com" }, scraped_at: "2026-04-01T10:28:00Z" },
  { id: "res-003", job_id: "job-001", job_name: "Amazon Product Tracker", data: { title: "Bose QuietComfort Ultra", price: 329.00, rating: "4.5 out of 5", reviews: 5672, seller: "Bose Official" }, scraped_at: "2026-04-01T10:28:00Z" },
  { id: "res-004", job_id: "job-002", job_name: "eBay Electronics Monitor", data: { title: "MacBook Pro 16\" M3 Max 36GB", price: 2849.00, rating: "N/A", condition: "Brand New", bids: 0 }, scraped_at: "2026-04-01T09:00:00Z" },
  { id: "res-005", job_id: "job-002", job_name: "eBay Electronics Monitor", data: { title: "Dell XPS 15 i7 32GB RAM", price: 1299.50, rating: "N/A", condition: "Refurbished", bids: 3 }, scraped_at: "2026-04-01T09:00:00Z" },
  { id: "res-006", job_id: "job-002", job_name: "eBay Electronics Monitor", data: { title: "ThinkPad X1 Carbon Gen 11", price: 987.00, rating: "N/A", condition: "Used - Like New", bids: 7 }, scraped_at: "2026-04-01T09:00:00Z" },
  { id: "res-007", job_id: "job-003", job_name: "Hacker News Top Stories", data: { title: "Show HN: I built a web scraper that bypasses any anti-bot", score: 842, comments: 234, rank: 1 }, scraped_at: "2026-04-01T06:00:00Z" },
  { id: "res-008", job_id: "job-003", job_name: "Hacker News Top Stories", data: { title: "The future of AI agents in web automation", score: 651, comments: 189, rank: 2 }, scraped_at: "2026-04-01T06:00:00Z" },
  { id: "res-009", job_id: "job-003", job_name: "Hacker News Top Stories", data: { title: "PostgreSQL 18 released with major performance improvements", score: 523, comments: 156, rank: 3 }, scraped_at: "2026-04-01T06:00:00Z" },
  { id: "res-010", job_id: "job-004", job_name: "Real Estate Listings", data: { address: "742 Evergreen Terrace, Springfield", price: 485000, beds: 4, baths: 2, sqft: 2200 }, scraped_at: "2026-04-01T10:15:00Z" },
  { id: "res-011", job_id: "job-004", job_name: "Real Estate Listings", data: { address: "1640 Riverside Dr, Hill Valley", price: 725000, beds: 3, baths: 3, sqft: 3100 }, scraped_at: "2026-04-01T10:15:00Z" },
  { id: "res-012", job_id: "job-005", job_name: "Weather Data Collector", data: { day: "Tuesday", high: "72F", low: "58F", description: "Partly Cloudy", precipitation: "10%" }, scraped_at: "2026-03-31T16:45:00Z" },
]

export const mockStats: Stats = {
  total_jobs: 24,
  active_jobs: 3,
  total_results: 15420,
  success_rate: 94.2,
  recent_activity: [
    { date: "2026-03-25", count: 1842 },
    { date: "2026-03-26", count: 2104 },
    { date: "2026-03-27", count: 1956 },
    { date: "2026-03-28", count: 2340 },
    { date: "2026-03-29", count: 1780 },
    { date: "2026-03-30", count: 2567 },
    { date: "2026-03-31", count: 2831 },
  ],
}

// ── Activity Chart Data (30 days) ────────────────────────────────────────────

export const mockActivityData = Array.from({ length: 30 }, (_, i) => {
  const date = new Date("2026-03-02")
  date.setDate(date.getDate() + i)
  const dayStr = date.toISOString().split("T")[0]
  const base = 80 + Math.floor(Math.random() * 120)
  const failed = 2 + Math.floor(Math.random() * 13)
  return { date: dayStr, successful: base, failed }
})

// ── API Functions (with mock fallbacks) ──────────────────────────────────────

export async function fetchJobs(): Promise<Job[]> {
  try {
    const res = await fetch(`${BASE_URL}/api/jobs`)
    if (!res.ok) throw new Error("Failed")
    return await res.json()
  } catch {
    return mockJobs
  }
}

export async function fetchJob(id: string): Promise<Job | undefined> {
  try {
    const res = await fetch(`${BASE_URL}/api/jobs/${id}`)
    if (!res.ok) throw new Error("Failed")
    return await res.json()
  } catch {
    return mockJobs.find((j) => j.id === id)
  }
}

export async function createJob(data: Partial<Job>): Promise<Job> {
  try {
    const res = await fetch(`${BASE_URL}/api/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error("Failed")
    return await res.json()
  } catch {
    return { ...mockJobs[0], ...data, id: `job-${Date.now()}` }
  }
}

export async function deleteJob(id: string): Promise<void> {
  try {
    await fetch(`${BASE_URL}/api/jobs/${id}`, { method: "DELETE" })
  } catch {
    // Mock: no-op
  }
}

export async function runJob(id: string): Promise<void> {
  try {
    await fetch(`${BASE_URL}/api/jobs/${id}/run`, { method: "POST" })
  } catch {
    // Mock: no-op
  }
}

export async function fetchResults(jobId?: string): Promise<Result[]> {
  try {
    const url = jobId ? `${BASE_URL}/api/results/${jobId}` : `${BASE_URL}/api/results`
    const res = await fetch(url)
    if (!res.ok) throw new Error("Failed")
    return await res.json()
  } catch {
    return jobId ? mockResults.filter((r) => r.job_id === jobId) : mockResults
  }
}

export async function exportResults(jobId: string, format: "csv" | "json"): Promise<string> {
  try {
    const res = await fetch(`${BASE_URL}/api/results/${jobId}/export?format=${format}`)
    if (!res.ok) throw new Error("Failed")
    return await res.text()
  } catch {
    return format === "json" ? JSON.stringify(mockResults, null, 2) : "title,price,rating\nMock,0,N/A"
  }
}

export async function fetchStats(): Promise<Stats> {
  try {
    const res = await fetch(`${BASE_URL}/api/stats`)
    if (!res.ok) throw new Error("Failed")
    return await res.json()
  } catch {
    return mockStats
  }
}
