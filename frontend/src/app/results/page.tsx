"use client"

import React, { useState } from "react"
import { Download, Search, ChevronDown, ChevronUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { mockResults } from "@/lib/api"

export default function ResultsPage() {
  const [search, setSearch] = useState("")
  const [expandedRow, setExpandedRow] = useState<string | null>(null)

  const filtered = mockResults.filter((r) => {
    if (!search) return true
    const str = JSON.stringify(r.data).toLowerCase()
    return str.includes(search.toLowerCase())
  })

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Results</h2>
          <p className="text-sm text-muted-foreground">
            {mockResults.length} records collected
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2">
            <Download className="h-4 w-4" />
            CSV
          </Button>
          <Button variant="outline" className="gap-2">
            <Download className="h-4 w-4" />
            JSON
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search results..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Results Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">
            Scraped Data
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead>Source</TableHead>
                <TableHead>Title / Key Data</TableHead>
                <TableHead>Scraped At</TableHead>
                <TableHead className="text-right">Fields</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((result) => {
                const isExpanded = expandedRow === result.id
                const dataKeys = Object.keys(result.data)
                const firstValue = String(
                  result.data[dataKeys[0]] ?? ""
                )

                return (
                  <React.Fragment key={result.id}>
                    <TableRow
                      className="cursor-pointer"
                      onClick={() =>
                        setExpandedRow(isExpanded ? null : result.id)
                      }
                    >
                      <TableCell className="w-8">
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="text-xs">
                          {result.job_name}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[300px] truncate font-medium">
                        {firstValue}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {new Date(result.scraped_at).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right text-sm text-muted-foreground">
                        {dataKeys.length}
                      </TableCell>
                    </TableRow>
                    {isExpanded && (
                      <TableRow>
                        <TableCell colSpan={5} className="bg-muted/30 p-4">
                          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                            {dataKeys.map((key) => (
                              <div
                                key={key}
                                className="rounded-md border border-border bg-card p-3"
                              >
                                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                                  {key}
                                </p>
                                <p className="mt-1 font-mono text-sm">
                                  {String(result.data[key])}
                                </p>
                              </div>
                            ))}
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
