import { n as Subscribable, o as shallowEqualObjects, p as hashKey, q as getDefaultState, t as notifyManager, v as useQueryClient, r as reactExports, w as noop, x as shouldThrowError, j as jsxRuntimeExports, P as Primitive, g as cn, a as useAppStore, d as useQuery, m as motion, e as Badge, B as Button, R as RefreshCw, S as Skeleton, y as toast, b as apiClient } from "./index-9YZ7FH_t.js";
import { L as LoaderCircle } from "./loader-circle-Ch6XWA6f.js";
var MutationObserver = class extends Subscribable {
  #client;
  #currentResult = void 0;
  #currentMutation;
  #mutateOptions;
  constructor(client, options) {
    super();
    this.#client = client;
    this.setOptions(options);
    this.bindMethods();
    this.#updateResult();
  }
  bindMethods() {
    this.mutate = this.mutate.bind(this);
    this.reset = this.reset.bind(this);
  }
  setOptions(options) {
    const prevOptions = this.options;
    this.options = this.#client.defaultMutationOptions(options);
    if (!shallowEqualObjects(this.options, prevOptions)) {
      this.#client.getMutationCache().notify({
        type: "observerOptionsUpdated",
        mutation: this.#currentMutation,
        observer: this
      });
    }
    if (prevOptions?.mutationKey && this.options.mutationKey && hashKey(prevOptions.mutationKey) !== hashKey(this.options.mutationKey)) {
      this.reset();
    } else if (this.#currentMutation?.state.status === "pending") {
      this.#currentMutation.setOptions(this.options);
    }
  }
  onUnsubscribe() {
    if (!this.hasListeners()) {
      this.#currentMutation?.removeObserver(this);
    }
  }
  onMutationUpdate(action) {
    this.#updateResult();
    this.#notify(action);
  }
  getCurrentResult() {
    return this.#currentResult;
  }
  reset() {
    this.#currentMutation?.removeObserver(this);
    this.#currentMutation = void 0;
    this.#updateResult();
    this.#notify();
  }
  mutate(variables, options) {
    this.#mutateOptions = options;
    this.#currentMutation?.removeObserver(this);
    this.#currentMutation = this.#client.getMutationCache().build(this.#client, this.options);
    this.#currentMutation.addObserver(this);
    return this.#currentMutation.execute(variables);
  }
  #updateResult() {
    const state = this.#currentMutation?.state ?? getDefaultState();
    this.#currentResult = {
      ...state,
      isPending: state.status === "pending",
      isSuccess: state.status === "success",
      isError: state.status === "error",
      isIdle: state.status === "idle",
      mutate: this.mutate,
      reset: this.reset
    };
  }
  #notify(action) {
    notifyManager.batch(() => {
      if (this.#mutateOptions && this.hasListeners()) {
        const variables = this.#currentResult.variables;
        const onMutateResult = this.#currentResult.context;
        const context = {
          client: this.#client,
          meta: this.options.meta,
          mutationKey: this.options.mutationKey
        };
        if (action?.type === "success") {
          try {
            this.#mutateOptions.onSuccess?.(
              action.data,
              variables,
              onMutateResult,
              context
            );
          } catch (e) {
            void Promise.reject(e);
          }
          try {
            this.#mutateOptions.onSettled?.(
              action.data,
              null,
              variables,
              onMutateResult,
              context
            );
          } catch (e) {
            void Promise.reject(e);
          }
        } else if (action?.type === "error") {
          try {
            this.#mutateOptions.onError?.(
              action.error,
              variables,
              onMutateResult,
              context
            );
          } catch (e) {
            void Promise.reject(e);
          }
          try {
            this.#mutateOptions.onSettled?.(
              void 0,
              action.error,
              variables,
              onMutateResult,
              context
            );
          } catch (e) {
            void Promise.reject(e);
          }
        }
      }
      this.listeners.forEach((listener) => {
        listener(this.#currentResult);
      });
    });
  }
};
function useMutation(options, queryClient) {
  const client = useQueryClient();
  const [observer] = reactExports.useState(
    () => new MutationObserver(
      client,
      options
    )
  );
  reactExports.useEffect(() => {
    observer.setOptions(options);
  }, [observer, options]);
  const result = reactExports.useSyncExternalStore(
    reactExports.useCallback(
      (onStoreChange) => observer.subscribe(notifyManager.batchCalls(onStoreChange)),
      [observer]
    ),
    () => observer.getCurrentResult(),
    () => observer.getCurrentResult()
  );
  const mutate = reactExports.useCallback(
    (variables, mutateOptions) => {
      observer.mutate(variables, mutateOptions).catch(noop);
    },
    [observer]
  );
  if (result.error && shouldThrowError(observer.options.throwOnError, [result.error])) {
    throw result.error;
  }
  return { ...result, mutate, mutateAsync: result.mutate };
}
var NAME = "Separator";
var DEFAULT_ORIENTATION = "horizontal";
var ORIENTATIONS = ["horizontal", "vertical"];
var Separator$1 = reactExports.forwardRef((props, forwardedRef) => {
  const { decorative, orientation: orientationProp = DEFAULT_ORIENTATION, ...domProps } = props;
  const orientation = isValidOrientation(orientationProp) ? orientationProp : DEFAULT_ORIENTATION;
  const ariaOrientation = orientation === "vertical" ? orientation : void 0;
  const semanticProps = decorative ? { role: "none" } : { "aria-orientation": ariaOrientation, role: "separator" };
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    Primitive.div,
    {
      "data-orientation": orientation,
      ...semanticProps,
      ...domProps,
      ref: forwardedRef
    }
  );
});
Separator$1.displayName = NAME;
function isValidOrientation(orientation) {
  return ORIENTATIONS.includes(orientation);
}
var Root = Separator$1;
const Separator = reactExports.forwardRef(({ className, orientation = "horizontal", decorative = true, ...props }, ref) => /* @__PURE__ */ jsxRuntimeExports.jsx(
  Root,
  {
    ref,
    decorative,
    orientation,
    className: cn(
      "shrink-0 bg-border",
      orientation === "horizontal" ? "h-px w-full" : "h-full w-px",
      className
    ),
    ...props
  }
));
Separator.displayName = Root.displayName;
const FADE_UP = {
  hidden: { opacity: 0, y: 10 },
  visible: (i) => ({ opacity: 1, y: 0, transition: { delay: i * 0.07 } })
};
function SettingsPage() {
  const queryClient = useQueryClient();
  const { theme, setTheme } = useAppStore();
  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: () => apiClient.get("/settings").then((r) => r.data)
  });
  const syncMutation = useMutation({
    mutationFn: () => apiClient.post("/settings/sync").then((r) => r.data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast({ title: "Sincronización completada", description: `${res.saved ?? 0} partidas guardadas` });
    },
    onError: () => {
      toast({ title: "Error al sincronizar", variant: "destructive" });
    }
  });
  if (isLoading) return /* @__PURE__ */ jsxRuntimeExports.jsx(SettingsSkeleton, {});
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-6 max-w-2xl space-y-8", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(motion.section, { variants: FADE_UP, initial: "hidden", animate: "visible", custom: 0, className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold uppercase tracking-widest text-muted-foreground", children: "Cuenta" }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "surface p-5 space-y-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Row, { label: "Invocador", children: data?.riot_id ? /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "font-medium", children: [
          data.riot_id,
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-muted-foreground", children: [
            "#",
            data.tag
          ] })
        ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Badge, { variant: "warning", children: "No configurado" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Separator, {}),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Row, { label: "Plataforma", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-muted-foreground", children: data?.platform_name ?? "—" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Separator, {}),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Row, { label: "Nivel", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm", children: data?.level ?? "—" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Separator, {}),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Row, { label: "Rango", children: data?.rank ? /* @__PURE__ */ jsxRuntimeExports.jsxs(Badge, { variant: "secondary", children: [
          data.rank,
          " · ",
          data.lp,
          " LP"
        ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-muted-foreground", children: "Sin clasificar" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Separator, {}),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Row, { label: "Riot API", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Badge, { variant: data?.api_key ? "success" : "warning", children: data?.api_key ? "Configurada" : "No configurada" }) })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(motion.section, { variants: FADE_UP, initial: "hidden", animate: "visible", custom: 1, className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold uppercase tracking-widest text-muted-foreground", children: "Datos" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "surface p-5", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium", children: "Sincronizar partidas" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-muted-foreground mt-0.5", children: "Descarga las últimas 50 partidas desde Riot API" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          Button,
          {
            variant: "outline",
            size: "sm",
            onClick: () => syncMutation.mutate(),
            disabled: syncMutation.isPending || !data?.is_configured,
            children: [
              syncMutation.isPending ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "h-4 w-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: "h-4 w-4" }),
              "Sincronizar"
            ]
          }
        )
      ] }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(motion.section, { variants: FADE_UP, initial: "hidden", animate: "visible", custom: 2, className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold uppercase tracking-widest text-muted-foreground", children: "Apariencia" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "surface p-5", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Row, { label: "Tema", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-2", children: ["dark", "light"].map((t) => /* @__PURE__ */ jsxRuntimeExports.jsx(
        Button,
        {
          variant: theme === t ? "default" : "outline",
          size: "sm",
          onClick: () => setTheme(t),
          children: t === "dark" ? "Oscuro" : "Claro"
        },
        t
      )) }) }) })
    ] })
  ] });
}
function Row({ label, children }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between py-0.5", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-muted-foreground", children: label }),
    children
  ] });
}
function SettingsSkeleton() {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-6 max-w-2xl space-y-8", children: [0, 1, 2].map((i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(Skeleton, { className: "h-3 w-24" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "surface p-5 space-y-4", children: [0, 1, 2].map((j) => /* @__PURE__ */ jsxRuntimeExports.jsx(Skeleton, { className: "h-8" }, j)) })
  ] }, i)) });
}
export {
  SettingsPage as default
};
