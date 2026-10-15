# Instrucciones para el agente — Nutriendo la Isla

## Objetivo
Construir un MVP web responsivo para conectar restaurantes donantes con personas beneficiarias de Ciudad del Carmen. Leer primero `docs/CONTEXTO_PROYECTO.md`, `docs/REQUISITOS.md`, `docs/REGLAS_NEGOCIO.md` y `docs/PLAN_IMPLEMENTACION.md`.

## Stack obligatorio
- Frontend: React + Vite + Bootstrap 5.
- Backend: Python + Flask; API REST JSON.
- Base de datos: SQLite con SQLAlchemy.
- Mapas: React Leaflet + OpenStreetMap, con atribución visible.
- IA: opcional y desacoplada; no bloquear el MVP si el modelo local no está disponible.

## Reglas de trabajo
1. Antes de implementar, explica brevemente los archivos que cambiarás y el objetivo de la fase.
2. Implementa solo la fase solicitada, sin añadir funciones no aprobadas.
3. No inventes negocios, personas ni donaciones reales: usa datos de prueba claramente etiquetados.
4. Nunca uses IA para aceptar o rechazar automáticamente a una persona por necesidad socioeconómica. El modelo solo ayuda a revisar completitud y ordenar solicitudes; la decisión final corresponde a un revisor humano, con apelación.
5. No solicites datos sensibles innecesarios; minimiza retención y nunca muestres encuestas a restaurantes u otros beneficiarios.
6. No declares seguro un alimento basándote en una foto o texto de IA. Exige controles verificables y revisión responsable.
7. Usa contraseñas con hash seguro, validación en servidor y autorización por rol. No subas secretos al repositorio.
8. Mantén componentes pequeños, nombres claros y documentación actualizada.
9. Al finalizar cada fase, indica comandos para probarla, resultados y tareas pendientes.
