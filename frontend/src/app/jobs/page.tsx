"use client"

import React from "react"
import { JobTable } from "@/components/jobs/job-table"
import { JobForm } from "@/components/jobs/job-form"
import { mockJobs } from "@/lib/api"

export default function JobsPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Scraping Jobs</h2>
          <p className="text-sm text-muted-foreground">
            {mockJobs.length} jobs configured
          </p>
        </div>
        <JobForm />
      </div>

      {/* Table */}
      <JobTable />
    </div>
  )
}
