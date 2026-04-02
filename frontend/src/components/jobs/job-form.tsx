"use client"

import React, { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Plus } from "lucide-react"

export function JobForm() {
  const [open, setOpen] = useState(false)

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          New Job
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>Create Scraping Job</DialogTitle>
          <DialogDescription>
            Configure a new web scraping job. Fill in the details below.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-5 py-4">
          <div className="grid gap-2">
            <Label htmlFor="name">Job Name</Label>
            <Input id="name" placeholder="e.g., Amazon Product Tracker" />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="url">Target URL</Label>
            <Input
              id="url"
              placeholder="https://example.com/products"
              className="font-mono text-sm"
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="selectors">CSS Selectors</Label>
            <Textarea
              id="selectors"
              placeholder={`{\n  "title": ".product-title",\n  "price": ".price-value",\n  "rating": ".star-rating"\n}`}
              className="min-h-[100px] font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              JSON object mapping field names to CSS selectors.
            </p>
          </div>

          <div className="grid gap-2">
            <Label>Scraping Mode</Label>
            <Select defaultValue="fast">
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fast">Fast (Pure HTTP)</SelectItem>
                <SelectItem value="dynamic">Dynamic (Playwright)</SelectItem>
                <SelectItem value="stealth">Stealth (Anti-Detection)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Fast for static sites, Dynamic for JS-rendered pages, Stealth to bypass Cloudflare and other protections.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label>Pagination</Label>
              <Select defaultValue="none">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  <SelectItem value="next-button">Next Button</SelectItem>
                  <SelectItem value="url-pattern">URL Pattern</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label>Schedule</Label>
              <Select defaultValue="once">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="once">One-time</SelectItem>
                  <SelectItem value="30min">Every 30 min</SelectItem>
                  <SelectItem value="hourly">Hourly</SelectItem>
                  <SelectItem value="daily">Daily</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex items-center justify-between rounded-lg border border-border p-4">
            <div className="space-y-0.5">
              <Label>Anti-Detection</Label>
              <p className="text-xs text-muted-foreground">
                Enable stealth mode with fingerprint randomization
              </p>
            </div>
            <Switch defaultChecked />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={() => setOpen(false)}>Create Job</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
