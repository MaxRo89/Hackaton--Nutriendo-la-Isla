# Nutriendo la Isla

Plataforma web para conectar restaurantes con excedentes de comida y personas beneficiarias en Ciudad del Carmen, Campeche.

## Equipo

- Ángel Jesús Paredes García — achuy.paredes@gmail.com
- Daniela Moncerat Mojarras López — danielamojarras@gmail.com
- Marcela del Carmen Olan Chan — marcelaolan196@gmail.com
- José Román Rosario Rosado — 230898@mail.unacar.mx
- Rosendo Maximiliano Rodriguez Alvarado — rmax9910@gmail.com

Nombre del equipo: Umizumi

## Idea del proyecto

Nutriendo la Isla nace como una solución digital para reducir el desperdicio de alimentos y, al mismo tiempo, apoyar a personas que necesitan acceso a comida de forma segura y organizada. La plataforma permite a restaurantes publicar excedentes, a beneficiarios solicitar acceso y a revisores validar las solicitudes de manera humana y transparente.

El proyecto se desarrolla como una demo local con datos ficticios, enfocada en la responsabilidad social, la trazabilidad de procesos y la claridad en la toma de decisiones.

## Problema que resuelve

En muchas comunidades, especialmente en zonas con desigualdad económica, se desperdicia una gran cantidad de alimentos aptos para consumo por falta de canales eficaces para redistribuirlos. Al mismo tiempo, personas que podrían beneficiarse de esos excedentes no tienen un mecanismo claro, seguro y transparente para acceder a ellos.

Muchos restaurantes y organizaciones también carecen de una herramienta simple para publicar excedentes, registrar información clave de manejo y coordinación, y garantizar una revisión responsable del proceso.

Nutriendo la Isla busca cerrar esa brecha con una solución digital sencilla, accesible y centrada en la comunidad:

- restaurantes publican donaciones de manera responsable
- beneficiarios presentan una solicitud de acceso
- revisores validan cada caso con criterio humano
- la plataforma facilita la coordinación y el seguimiento del proceso
- la IA acompaña la revisión con sugerencias útiles, sin reemplazar la decisión humana

## Solución

Nutriendo la Isla es una plataforma web diseñada para conectar excedentes de alimentos con personas que necesitan apoyo, reduciendo desperdicio y promoviendo una redistribución más responsable y organizada.

La solución combina:

- publicación de donaciones por parte de restaurantes
- flujo de solicitud y validación para beneficiarios
- panel de revisión con decisiones motivadas y apelaciones
- IA opcional para detectar información faltante y resumir casos de manera neutral

## Impacto

Con esta solución buscamos generar un impacto social y operativo positivo:

- reducir el desperdicio de alimentos
- facilitar acceso a comida para personas en situación vulnerable
- fortalecer la colaboración entre restaurantes y comunidad
- digitalizar la gestión de donaciones de forma responsable y segura
- crear un modelo replicable para ciudades y comunidades con necesidades similares

Nuestra propuesta no solo optimiza procesos, también genera confianza: la revisión es humana, la toma de decisiones es transparente y la IA solo acompaña, sin automatizar decisiones sensibles.

## Funcionalidades principales

- Registro y autenticación por roles: restaurante, beneficiario y revisor
- Solicitud de acceso para beneficiarios con consentimiento y revisión humana
- Perfil de restaurante con punto de recogida ficticio
- Publicación de donaciones con información básica de alimentos
- Descubrimiento de donaciones disponibles por parte de beneficiarios aprobados
- Solicitudes y confirmación de entrega
- Panel de revisión con decisiones motivadas y apelaciones
- IA opcional para apoyar tareas concretas y útiles:
  - detectar si una donación está incompleta y sugerir campos faltantes como alérgenos, conservación, manipulación o información clave para la recogida
  - resumir de manera neutral la solicitud del beneficiario para ayudar al revisor a revisar más rápido el contexto del caso
  - apoyar la claridad del proceso sin reemplazar la evaluación humana
- La IA nunca decide automáticamente aprobación, rechazo o puntaje de personas, ni sustituye la responsabilidad del revisor

## Stack tecnológico

- Frontend: React + Vite + Bootstrap
- Backend: Flask + SQLAlchemy + SQLite
- Autenticación y roles: Flask-Login + CSRF
- IA opcional: Gemini API con degradación elegante si no hay clave configurada

## Reglas de negocio importantes

- La IA ayuda a detectar información faltante y resumir contextos, pero no toma decisiones.
- La IA no aprueba ni rechaza beneficiarios.
- La IA no puntúa la necesidad económica ni mide “merecimiento”.
- El revisor humano siempre valida la solicitud y escribe el motivo de la decisión.
- Si no hay API key de Gemini, la plataforma sigue funcionando normalmente.
- Las donaciones y solicitudes se manejan con revisión responsable, sin automatizar decisiones sensibles.

## Estructura del repositorio

```text
nutriendo-la-isla-starter/
├── backend/
│   ├── app/
│   ├── tests/
│   ├── pyproject.toml
│   ├── requirements.lock
│   └── wsgi.py
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── docs/
├── .env.example
├── .gitignore
├── README.md
└── .env   # local, ignorado por Git, no publicarse
```

## Configuración local

1. Copia el archivo de ejemplo:

```bash
cp .env.example .env
```

2. Si deseas usar Gemini real, agrega tu clave en el archivo .env:

```env
GEMINI_API_KEY=tu_clave_aqui
```

3. No subas este archivo al repositorio público; está ignorado por Git.

## Ejecutar el proyecto

### Backend

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock
pip install --no-deps -e .
python -m flask --app wsgi db upgrade
python -m flask --app wsgi run --host 127.0.0.1 --port 5001 --debug
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Luego abre:

```text
http://127.0.0.1:5173
```

## Demo local

La aplicación incluye usuarios ficticios para pruebas rápidas, y se puede sembrar la demo con:

```bash
cd backend
. .venv/bin/activate
python -m flask --app wsgi seed-demo
```

Credenciales demo:

- restaurante: restaurant@demo.invalid
- beneficiario: beneficiary@demo.invalid
- revisor: reviewer@demo.invalid
- contraseña: DemoPassword123!

## Seguridad y privacidad

- La clave de Gemini se guarda únicamente en el archivo local .env.
- El repositorio público no incluye secretos reales.
- El proyecto usa datos ficticios para demostrar el flujo.
- No se procesan datos sensibles reales ni información personal de terceros en la demo.

## Estado del proyecto

Este proyecto está pensado para un hackathon: demuestra una solución completa, funcional y responsable para la reducción del desperdicio alimentario, con una capa de revisión humana y un uso opcional de IA como herramienta de apoyo.

## Licencia

Proyecto desarrollado con fines de demostración para hackathon y aprendizaje tecnológico.

## Contacto

Si deseas colaborar o hacer pruebas del proyecto, puedes contactar con cualquiera de los miembros del equipo indicados arriba.
