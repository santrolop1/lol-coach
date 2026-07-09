import { c as createLucideIcon, d as useQuery, b as apiClient, j as jsxRuntimeExports, m as motion, e as Badge, B as Button, R as RefreshCw, S as Skeleton, f as formatScore, g as cn, s as scoreToBg, h as formatPercent, M as Minus } from "./index-9YZ7FH_t.js";
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const CircleAlert = createLucideIcon("CircleAlert", [
  ["circle", { cx: "12", cy: "12", r: "10", key: "1mglay" }],
  ["line", { x1: "12", x2: "12", y1: "8", y2: "12", key: "1pkeuh" }],
  ["line", { x1: "12", x2: "12.01", y1: "16", y2: "16", key: "4dfq90" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const TrendingDown = createLucideIcon("TrendingDown", [
  ["polyline", { points: "22 17 13.5 8.5 8.5 13.5 2 7", key: "1r2t7k" }],
  ["polyline", { points: "16 17 22 17 22 11", key: "11uiuu" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const TrendingUp = createLucideIcon("TrendingUp", [
  ["polyline", { points: "22 7 13.5 15.5 8.5 10.5 2 17", key: "126l90" }],
  ["polyline", { points: "16 7 22 7 22 13", key: "kwv8wd" }]
]);
const dashboardKeys = {
  all: ["dashboard"]
};
function useDashboard() {
  return useQuery({
    queryKey: dashboardKeys.all,
    queryFn: () => apiClient.get("/dashboard").then((r) => r.data),
    refetchInterval: 3e4,
    staleTime: 15e3
  });
}
const FADE_UP = {
  hidden: { opacity: 0, y: 12 },
  visible: (i) => ({ opacity: 1, y: 0, transition: { delay: i * 0.08, duration: 0.3 } })
};
function DashboardPage() {
  const { data, isLoading, isError, refetch } = useDashboard();
  if (isLoading) return /* @__PURE__ */ jsxRuntimeExports.jsx(DashboardSkeleton, {});
  if (isError) return /* @__PURE__ */ jsxRuntimeExports.jsx(DashboardError, { onRetry: refetch });
  const adc = data?.roles?.ADC;
  const top = data?.roles?.TOP;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-6 space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      motion.div,
      {
        variants: FADE_UP,
        initial: "hidden",
        animate: "visible",
        custom: 0,
        className: "flex items-end justify-between",
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs font-medium uppercase tracking-widest text-muted-foreground mb-1", children: "Invocador" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-2xl font-bold", children: data?.player_name ?? "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mt-1", children: [
              data?.rank && /* @__PURE__ */ jsxRuntimeExports.jsx(Badge, { variant: "secondary", children: data.rank }),
              data?.lp != null && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm text-muted-foreground", children: [
                data.lp,
                " LP"
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-muted-foreground", children: data?.sync_label ?? "" })
            ] })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(Button, { variant: "ghost", size: "icon", onClick: () => refetch(), className: "h-8 w-8", children: /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: "h-4 w-4 text-muted-foreground" }) })
        ]
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 gap-4", children: [
      { role: "ADC", data: adc },
      { role: "TOP", data: top }
    ].map(({ role, data: roleData }, i) => /* @__PURE__ */ jsxRuntimeExports.jsx(
      motion.div,
      {
        variants: FADE_UP,
        initial: "hidden",
        animate: "visible",
        custom: i + 1,
        children: /* @__PURE__ */ jsxRuntimeExports.jsx(RoleCard, { role, data: roleData })
      },
      role
    )) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      motion.div,
      {
        variants: FADE_UP,
        initial: "hidden",
        animate: "visible",
        custom: 3,
        className: "surface p-4 text-center text-sm text-muted-foreground",
        children: "Las pantallas de Coaching, Partidas y Draft se integran en E-4."
      }
    )
  ] });
}
function RoleCard({ role, data }) {
  const hasData = data?.has_data !== false && data != null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "surface p-5 space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-semibold uppercase tracking-widest text-muted-foreground", children: role }),
      hasData && data.confidence_level && /* @__PURE__ */ jsxRuntimeExports.jsx(Badge, { variant: "outline", className: "text-xs", children: data.confidence_level })
    ] }),
    !hasData ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "py-4 text-center text-sm text-muted-foreground", children: "Sin datos suficientes" }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-end gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: cn("text-4xl font-bold tabular-nums", scoreToBg(data.overall_score ?? 0).split(" ")[0].replace("bg-", "text-")), children: formatScore(data.overall_score) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "pb-1", children: /* @__PURE__ */ jsxRuntimeExports.jsx(TrendIcon, { trend: data.trend }) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-2 text-xs", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Metric, { label: "Winrate", value: formatPercent(data.winrate) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Metric, { label: "Partidas", value: String(data.sample_size ?? 0) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Metric, { label: "Prioridad", value: data.top_priority ?? "—", wide: true })
      ] }),
      data.primary_problem && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "rounded-md bg-secondary/50 px-3 py-2 text-xs text-muted-foreground", children: data.primary_problem })
    ] })
  ] });
}
function Metric({ label, value, wide }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: cn("space-y-0.5", wide && "col-span-2"), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted-foreground/70", children: label }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "font-medium text-foreground truncate", children: value })
  ] });
}
function TrendIcon({ trend }) {
  if (!trend) return null;
  if (trend === "improving") return /* @__PURE__ */ jsxRuntimeExports.jsx(TrendingUp, { className: "h-4 w-4 text-emerald-400" });
  if (trend === "declining") return /* @__PURE__ */ jsxRuntimeExports.jsx(TrendingDown, { className: "h-4 w-4 text-red-400" });
  return /* @__PURE__ */ jsxRuntimeExports.jsx(Minus, { className: "h-4 w-4 text-muted-foreground" });
}
function DashboardSkeleton() {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-6 space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Skeleton, { className: "h-3 w-20" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(Skeleton, { className: "h-8 w-48" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(Skeleton, { className: "h-4 w-32" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 gap-4", children: [0, 1].map((i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "surface p-5 space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Skeleton, { className: "h-3 w-12" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(Skeleton, { className: "h-10 w-20" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 gap-2", children: [0, 1, 2, 3].map((j) => /* @__PURE__ */ jsxRuntimeExports.jsx(Skeleton, { className: "h-8" }, j)) })
    ] }, i)) })
  ] });
}
function DashboardError({ onRetry }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex h-full flex-col items-center justify-center gap-4 p-8", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "h-8 w-8 text-destructive" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-muted-foreground", children: "Error al cargar el dashboard" }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(Button, { variant: "outline", size: "sm", onClick: onRetry, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: "h-4 w-4" }),
      " Reintentar"
    ] })
  ] });
}
export {
  DashboardPage as default
};
