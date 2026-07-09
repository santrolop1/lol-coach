import { c as createLucideIcon, u as useNavigate, a as useAppStore, r as reactExports, j as jsxRuntimeExports, m as motion, A as AnimatePresence, B as Button, R as RefreshCw, b as apiClient, i as isNetworkError } from "./index-9YZ7FH_t.js";
import { L as LoaderCircle } from "./loader-circle-Ch6XWA6f.js";
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const CircleCheck = createLucideIcon("CircleCheck", [
  ["circle", { cx: "12", cy: "12", r: "10", key: "1mglay" }],
  ["path", { d: "m9 12 2 2 4-4", key: "dzmm74" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const CircleX = createLucideIcon("CircleX", [
  ["circle", { cx: "12", cy: "12", r: "10", key: "1mglay" }],
  ["path", { d: "m15 9-6 6", key: "1uzhvr" }],
  ["path", { d: "m9 9 6 6", key: "z0biqf" }]
]);
const POLL_INTERVAL = 1500;
const MAX_RETRIES = 20;
function LoadingPage() {
  const navigate = useNavigate();
  const { setBackendStatus, setLcuConnected } = useAppStore();
  const [checks, setChecks] = reactExports.useState([
    { id: "backend", label: "Backend FastAPI", status: "pending" },
    { id: "db", label: "Base de datos SQLite", status: "pending" },
    { id: "riot", label: "Riot API configurada", status: "pending" }
  ]);
  const [failed, setFailed] = reactExports.useState(false);
  const retriesRef = reactExports.useRef(0);
  const timer = reactExports.useRef({ id: null });
  function setCheck(id, status) {
    setChecks((prev) => prev.map((c) => c.id === id ? { ...c, status } : c));
  }
  function schedule(fn, ms) {
    if (timer.current.id) clearTimeout(timer.current.id);
    timer.current.id = setTimeout(fn, ms);
  }
  async function runHealthCheck() {
    try {
      const res = await apiClient.get("/health");
      const h = res.data;
      setCheck("backend", h.status === "ok" ? "ok" : "error");
      setCheck("db", h.db === "ok" ? "ok" : "error");
      setCheck("riot", "ok");
      setBackendStatus("connected");
      setLcuConnected(h.lcu === "connected");
      await new Promise((r) => setTimeout(r, 600));
      navigate("/", { replace: true });
    } catch (err) {
      retriesRef.current += 1;
      if (retriesRef.current >= MAX_RETRIES || !isNetworkError(err)) {
        setFailed(true);
        setCheck("backend", "error");
        setBackendStatus("error");
      } else {
        schedule(runHealthCheck, POLL_INTERVAL);
      }
    }
  }
  reactExports.useEffect(() => {
    schedule(runHealthCheck, 600);
    return () => {
      if (timer.current.id) clearTimeout(timer.current.id);
    };
  }, []);
  function retry() {
    setFailed(false);
    retriesRef.current = 0;
    setChecks((prev) => prev.map((c) => ({ ...c, status: "pending" })));
    schedule(runHealthCheck, 200);
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex h-screen flex-col items-center justify-center bg-background gap-8", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      motion.div,
      {
        initial: { opacity: 0, y: -16 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.4 },
        className: "flex flex-col items-center gap-3",
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/20 border border-primary/30 shadow-lg shadow-primary/10", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-2xl font-bold text-primary", children: "LC" }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-bold tracking-tight", children: "LoL Coach" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-muted-foreground mt-0.5", children: "Análisis inteligente de partidas" })
          ] })
        ]
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      motion.div,
      {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        transition: { delay: 0.2 },
        className: "flex flex-col gap-2.5 min-w-[240px]",
        children: checks.map((check, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
          motion.div,
          {
            initial: { opacity: 0, x: -12 },
            animate: { opacity: 1, x: 0 },
            transition: { delay: 0.3 + i * 0.1 },
            className: "flex items-center gap-3",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(StatusIcon, { status: check.status }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: check.status === "pending" ? "text-sm text-muted-foreground" : check.status === "ok" ? "text-sm text-foreground" : "text-sm text-destructive", children: check.label })
            ]
          },
          check.id
        ))
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(AnimatePresence, { children: failed && /* @__PURE__ */ jsxRuntimeExports.jsxs(
      motion.div,
      {
        initial: { opacity: 0, y: 8 },
        animate: { opacity: 1, y: 0 },
        exit: { opacity: 0 },
        className: "flex flex-col items-center gap-3 text-center",
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-sm text-muted-foreground max-w-xs", children: [
            "No se pudo conectar al backend.",
            /* @__PURE__ */ jsxRuntimeExports.jsx("br", {}),
            "¿Está FastAPI corriendo en el puerto 8765?"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(Button, { variant: "outline", size: "sm", onClick: retry, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: "h-4 w-4" }),
            "Reintentar"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: "text-xs text-muted-foreground/50 font-mono", children: "uvicorn backend.api.main:app --port 8765" })
        ]
      }
    ) }),
    !failed && /* @__PURE__ */ jsxRuntimeExports.jsxs(
      motion.div,
      {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        transition: { delay: 0.5 },
        className: "text-xs text-muted-foreground/40 flex items-center gap-1.5",
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "h-3 w-3 animate-spin" }),
          "Conectando…"
        ]
      }
    )
  ] });
}
function StatusIcon({ status }) {
  if (status === "ok") return /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheck, { className: "h-4 w-4 text-emerald-400 shrink-0" });
  if (status === "error") return /* @__PURE__ */ jsxRuntimeExports.jsx(CircleX, { className: "h-4 w-4 text-destructive  shrink-0" });
  return /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "h-4 w-4 animate-spin text-muted-foreground/50 shrink-0" });
}
export {
  LoadingPage as default
};
