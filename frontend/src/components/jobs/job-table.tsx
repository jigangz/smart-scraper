"use client"

import React from "react"
import { motion } from "framer-motion"
import { Play, Pencil, Trash2, Zap, Globe, Shield } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/dashboard/recent-jobs"
import { mockJobs } from "@/lib/api"

const modeConfig = {
  fast: { label: "Fast", icon: Zap, variant: "secondary" as const },
  dynamic: { label: "Dynamic", icon: Globe, variant: "outline" as const },
  stealth: { label: "Stealth", icon: Shield, variant: "default" as const },
}

function ModeBadge({ mode }: { mode: "fast" | "dynamic" | "stealth" }) {
  const config = modeConfig[mode] || modeConfig.fast
  const Icon = config.icon
  return (
    <Badge variant={config.variant} className="gap-1 text-xs">
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  )
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

export function JobTable() {
  return (
    <div className="rounded-lg border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>URL</TableHead>
            <TableHead>Mode</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Schedule</TableHead>
            <TableHead>Last Run</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {mockJobs.map((job, i) => (
            <motion.tr
              key={job.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="border-b transition-colors hover:bg-muted/50"
            >
              <TableCell className="font-medium">{job.name}</TableCell>
              <TableCell className="max-w-[200px] truncate font-mono text-xs text-muted-foreground">
                {job.url}
              </TableCell>
              <TableCell>
                <ModeBadge mode={job.mode || "fast"} />
              </TableCell>
              <TableCell>
                <StatusBadge status={job.status} />
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {job.schedule}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {timeAgo(job.last_run)}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex items-center justify-end gap-1">
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Play className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </TableCell>
            </motion.tr>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
