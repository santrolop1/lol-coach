import { j as jsxRuntimeExports, H as History } from "./index-9YZ7FH_t.js";
function MatchesPage() {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(ComingSoon, { icon: History, title: "Partidas", description: "Historial completo con análisis V2 por rol y campeón.", sprint: "E-4" });
}
function ComingSoon({ icon: Icon, title, description, sprint }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex h-full flex-col items-center justify-center gap-4 p-8 text-center", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "rounded-xl bg-secondary p-5", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Icon, { className: "h-10 w-10 text-muted-foreground" }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold", children: title }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-1 text-sm text-muted-foreground max-w-xs", children: description })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs font-mono text-muted-foreground/50 bg-secondary px-2 py-1 rounded", children: [
      "Sprint ",
      sprint
    ] })
  ] });
}
export {
  MatchesPage as default
};
