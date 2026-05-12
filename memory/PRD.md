# Tutor Metodológico Minimalista — SYVREN

## Problema
Aplicación de tutor de IA con protocolo estricto: nunca entrega el resultado final, solo guía con (1) Archivo de Datos, (2) un solo Paso Activo, (3) Acción de Cierre (pregunta).

## Arquitectura
- Backend: FastAPI + MongoDB + Claude Sonnet 4.5 vía emergentintegrations
- Frontend: React 19 + Tailwind + react-markdown + KaTeX
- Branding: SYVREN — paleta dark navy + azul eléctrico/cian

## Implementado (2026-05)
- Sesiones de chat (CRUD) persistidas en MongoDB
- Multi-turn con contexto histórico
- 3 secciones renderizadas visualmente (data-testids)
- 4 prompts de ejemplo en estado vacío
- Sidebar con historial, borrar sesión
- Logo SYVREN + texto a la derecha en sidebar y estado vacío
- Tema oscuro navy adaptado al logo
- Tests backend 10/10 pasando

## Backlog / Próximas mejoras
- P2: Truncar historial a últimas N turns para optimizar tokens
- P2: Streaming de respuestas
- P2: Exportar conversación a PDF/Markdown
- P2: Modo "examen" con bloqueo total de pistas
