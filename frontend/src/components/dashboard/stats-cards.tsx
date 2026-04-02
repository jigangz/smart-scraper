"use client"

import React from "react"
import { motion } from "framer-motion"
import { Activity, Briefcase, Database, TrendingUp } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"

const stats = [
  {
    label: "Total Jobs",
    value: "24",
    change: "+12%",
    changeType: "positive" as const,
    icon: Briefcase,
    iconColor: "text-blue-400",
    iconBg: "bg-blue-400/10",
  },
  {
    label: "Active Scrapers",
    value: "3",
    change: "Running",
    changeType: "neutral" as const,
    icon: Activity,
    iconColor: "text-emerald-400",
    iconBg: "bg-emerald-400/10",
    pulse: true,
  },
  {
    label: "Data Points",
    value: "15,420",
    change: "+23%",
    changeType: "positive" as const,
    icon: Database,
    iconColor: "text-violet-400",
    iconBg: "bg-violet-400/10",
  },
  {
    label: "Success Rate",
    value: "94.2%",
    change: "+2.1%",
    changeType: "positive" as const,
    icon: TrendingUp,
    iconColor: "text-amber-400",
    iconBg: "bg-amber-400/10",
  },
]

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

export function StatsCards() {
  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
    >
      {stats.map((stat) => (
        <motion.div key={stat.label} variants={item}>
          <Card className="overflow-hidden">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                  <p className="text-3xl font-bold tracking-tight">
                    {stat.value}
                  </p>
                </div>
                <div
                  className={`flex h-12 w-12 items-center justify-center rounded-xl ${stat.iconBg}`}
                >
                  <stat.icon
                    className={`h-6 w-6 ${stat.iconColor} ${stat.pulse ? "animate-pulse" : ""}`}
                  />
                </div>
              </div>
              <div className="mt-3 flex items-center gap-1">
                <span
                  className={
                    stat.changeType === "positive"
                      ? "text-xs font-medium text-emerald-400"
                      : "text-xs font-medium text-muted-foreground"
                  }
                >
                  {stat.change}
                </span>
                {stat.changeType === "positive" && (
                  <span className="text-xs text-muted-foreground">
                    from last week
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </motion.div>
  )
}
