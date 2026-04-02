"use client"

import React from "react"
import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { mockJobs } from "@/lib/api"

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "running":
      return (
        <Badge variant="info" className="gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse-dot" />
          Running
        </Badge>
      )
    case "completed":
      return <Badge variant="success">Completed</Badge>
    case "failed":
      return <Badge variant="destructive">Failed</Badge>
    case "scheduled":
      return <Badge variant="warning">Scheduled</Badge>
    default:
      return <Badge variant="secondary">Idle</Badge>
  }
}

function timeAgo(dateStr: string): string {
  const now = new Date("2026-04-01T10:30:00Z")
  const date = new Date(dateStr)
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export function RecentJobs() {
  const recentJobs = mockJobs.slice(0, 5)

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base font-semibold">Recent Jobs</CardTitle>
        <Link
          href="/jobs"
          className="text-xs font-medium text-primary hover:underline"
        >
          View All
        </Link>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead className="hidden sm:table-cell">URL</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Last Run</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {recentJobs.map((job) => (
              <TableRow key={job.id}>
                <TableCell className="font-medium">{job.name}</TableCell>
                <TableCell className="hidden max-w-[180px] truncate text-muted-foreground sm:table-cell font-mono text-xs">
                  {job.url}
                </TableCell>
                <TableCell>
                  <StatusBadge status={job.status} />
                </TableCell>
                <TableCell className="text-right text-xs text-muted-foreground">
                  {timeAgo(job.last_run)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

export { StatusBadge }
