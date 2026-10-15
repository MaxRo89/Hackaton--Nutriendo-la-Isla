# Plan de implementación por fases

## Secuencia aprobada (sustituye el plan inicial de abajo)

0. Acuerdos: arquitectura revisada; decisiones en DECISIONES.md.
1. Base ejecutable: React/Vite/Bootstrap, Flask, SQLite, migraciones y salud de API.
2. Identidad: registro, sesión, CSRF, revisor interno y restaurantes ficticios preautorizados.
3. Solicitud de acceso: formulario mínimo, consentimiento, edición y estado.
4. Revisión humana: decisiones motivadas, información adicional y apelaciones.
5. Donaciones: perfil, ubicación y publicación con información obligatoria.
6. Descubrimiento: mapa React Leaflet/OSM, lista y detalle para aprobados.
7. Solicitud y entrega: cantidades parciales, confirmación transaccional, cancelación y vencimiento.
8. Reportes y demo: revisión de reportes, privacidad y prueba integral.
9. IA opcional: completitud y resumen neutral sin decisiones automáticas.

Implementar solo la fase autorizada, con verificaciones e instrucciones de prueba.

Estado: fases 1 a 9 implementadas. El MVP está completo, y la fase 9 añade ayuda opcional de IA con degradación elegante y sin decisiones automáticas.

## Plan inicial conservado como referencia

## Fase 0 — Preparación
- [ ] Revisar documentos y resolver ambigüedades.
- [ ] Crear repositorio Git y `.gitignore`.
- [ ] Generar frontend Vite y backend Flask.
- [ ] Crear `.env.example` y scripts de arranque.

## Fase 1 — Base funcional
- [ ] Navegación y diseño responsivo.
- [ ] API Flask y SQLite con datos de prueba.
- [ ] Listar donaciones en tarjetas.
- [ ] Mostrar puntos de recogida en mapa OSM.

## Fase 2 — Roles y donaciones
- [ ] Registro/login seguro de restaurante y beneficiario.
- [ ] Publicación y gestión de donaciones por restaurante.
- [ ] Solicitud de donación por beneficiario aprobado.

## Fase 3 — Solicitud de acceso
- [ ] Formulario socioeconómico breve y consentimiento.
- [ ] Estado de solicitud y panel de revisión humana.
- [ ] Revisión, motivos y apelación.

## Fase 4 — IA opcional y presentación
- [ ] Probar modelo local ligero solo para resumir/comprobar completitud.
- [ ] Demostración de extremo a extremo con datos ficticios.
- [ ] README, pruebas y pitch.

## Criterio de éxito del MVP
Una cuenta restaurante publica una donación; una cuenta beneficiaria aprobada la encuentra en mapa, solicita y confirma una recogida de prueba.
