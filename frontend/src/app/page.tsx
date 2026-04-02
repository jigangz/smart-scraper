"use client"

import React from "react"
import Link from "next/link"
import { Plus, Database } from "lucide-react"
import { Button } from "@/components/ui/button"
import { StatsCards } from "@/components/dashboard/stats-cards"
import { ActivityChart } from "@/components/dashboard/activity-chart"
import { RecentJobs } from "@/components/dashboard/recent-jobs"

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-sm text-muted-foreground">
            Overview of your scraping operations
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/jobs">
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              New Job
            </Button>
          </Link>
          <Link href="/results">
            <Button variant="outline" className="gap-2">
              <Database className="h-4 w-4" />
              View Results
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats */}
      <StatsCards />

      {/* Charts & Recent Jobs */}
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <ActivityChart />
        </div>
        <div className="lg:col-span-2">
          <RecentJobs />
        </div>
      </div>
    </div>
  )
}
