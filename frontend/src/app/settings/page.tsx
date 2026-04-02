"use client"

import React from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Settings</h2>
        <p className="text-sm text-muted-foreground">
          Configure your scraping preferences
        </p>
      </div>

      <Tabs defaultValue="general" className="space-y-6">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="proxy">Proxy</TabsTrigger>
          <TabsTrigger value="anti-detection">Anti-Detection</TabsTrigger>
          <TabsTrigger value="export">Export</TabsTrigger>
        </TabsList>

        {/* General */}
        <TabsContent value="general">
          <Card>
            <CardHeader>
              <CardTitle>General Settings</CardTitle>
              <CardDescription>
                Basic application configuration.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-2">
                <Label htmlFor="appName">Application Name</Label>
                <Input id="appName" defaultValue="Smart Scraper" />
              </div>

              <div className="grid gap-2">
                <Label>Default Schedule</Label>
                <Select defaultValue="daily">
                  <SelectTrigger className="w-[200px]">
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

              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <Label>Notifications</Label>
                  <p className="text-xs text-muted-foreground">
                    Receive alerts when jobs complete or fail
                  </p>
                </div>
                <Switch defaultChecked />
              </div>

              <Separator />
              <Button>Save Changes</Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Proxy */}
        <TabsContent value="proxy">
          <Card>
            <CardHeader>
              <CardTitle>Proxy Configuration</CardTitle>
              <CardDescription>
                Set up proxy servers for your scraping requests.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-2">
                <Label htmlFor="proxyUrl">Proxy URL</Label>
                <Input
                  id="proxyUrl"
                  placeholder="http://proxy.example.com:8080"
                  className="font-mono text-sm"
                />
              </div>

              <div className="grid gap-2">
                <Label>Proxy Type</Label>
                <Select defaultValue="http">
                  <SelectTrigger className="w-[200px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="http">HTTP</SelectItem>
                    <SelectItem value="socks5">SOCKS5</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="proxyUser">Username</Label>
                  <Input id="proxyUser" placeholder="Optional" />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="proxyPass">Password</Label>
                  <Input
                    id="proxyPass"
                    type="password"
                    placeholder="Optional"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <Label>Proxy Rotation</Label>
                  <p className="text-xs text-muted-foreground">
                    Automatically rotate between proxy servers
                  </p>
                </div>
                <Switch />
              </div>

              <Separator />
              <div className="flex gap-2">
                <Button>Save Changes</Button>
                <Button variant="outline">Test Connection</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Anti-Detection */}
        <TabsContent value="anti-detection">
          <Card>
            <CardHeader>
              <CardTitle>Anti-Detection Settings</CardTitle>
              <CardDescription>
                Configure stealth settings to avoid being blocked.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="minDelay">Min Delay (ms)</Label>
                  <Input
                    id="minDelay"
                    type="number"
                    defaultValue="2000"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="maxDelay">Max Delay (ms)</Label>
                  <Input
                    id="maxDelay"
                    type="number"
                    defaultValue="5000"
                  />
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <Label>User-Agent Rotation</Label>
                    <p className="text-xs text-muted-foreground">
                      Randomly rotate User-Agent headers between requests
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <Label>Fingerprint Randomization</Label>
                    <p className="text-xs text-muted-foreground">
                      Randomize browser fingerprint (canvas, WebGL, fonts)
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <Label>Header Randomization</Label>
                    <p className="text-xs text-muted-foreground">
                      Randomize HTTP headers to mimic real browsers
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <Label>CAPTCHA Detection</Label>
                    <p className="text-xs text-muted-foreground">
                      Detect CAPTCHA challenges and skip gracefully
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
              </div>

              <Separator />
              <Button>Save Changes</Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Export */}
        <TabsContent value="export">
          <Card>
            <CardHeader>
              <CardTitle>Export Preferences</CardTitle>
              <CardDescription>
                Configure default export settings.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-2">
                <Label>Default Format</Label>
                <Select defaultValue="json">
                  <SelectTrigger className="w-[200px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="json">JSON</SelectItem>
                    <SelectItem value="csv">CSV</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <Label>Include Headers</Label>
                  <p className="text-xs text-muted-foreground">
                    Include column headers in CSV exports
                  </p>
                </div>
                <Switch defaultChecked />
              </div>

              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <Label>Pretty Print JSON</Label>
                  <p className="text-xs text-muted-foreground">
                    Format JSON output with indentation
                  </p>
                </div>
                <Switch defaultChecked />
              </div>

              <Separator />
              <Button>Save Changes</Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
