"""
backend/viewmodels — Capa ViewModel.

Cada módulo construye la estructura de datos completa que necesita
una pantalla específica. La UI solo renderiza lo que recibe aquí.

Flujo:
    UI → ViewModel.build(...) → Services → Core → Repositories → SQLite
"""
