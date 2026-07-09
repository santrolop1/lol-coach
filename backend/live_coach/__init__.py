"""
Live Coach — módulo independiente de coaching en tiempo real.

Flujo:
  LiveDataProvider → EventBus → PriorityManager → WidgetManager → Overlay

Regla: este módulo solo CONSUME información. Nunca calcula ni duplica lógica.
Toda la inteligencia viene de Game Intelligence Platform + Champion Intelligence.
"""
