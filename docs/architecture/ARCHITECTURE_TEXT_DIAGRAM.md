# UAH Architecture (Text Diagram)

Copy-paste friendly diagram for slides, README screenshots, or forms that only accept plain text.

```text
UAH (Unified Application Hub)
=============================

                    [ PostgreSQL ]
                          ^
                          |
              +-----------+-----------+
              |     FastAPI Backend   |
              |  API  Auth  Sessions  |
              |  Jobs  Resume  Gmail  |
              |  Celery + Redis queues |
              +-----------+-----------+
                          |
            +-------------+-------------+
            |             |             |
    [ Frontend SPA ]  [ Landing SPA ] [ Browser Extension MV3 ]
    Vue + Vite        Vue + Vite       Vue + adapters + SW
    /api via proxy    public static      /api with cookies
    
Environments (conceptual):

  LOCAL     docker-compose.local.yml + host Vite
  DEV       docker-compose.yml (integrated stack)
  BETA      docker-compose.beta.yml + tunnel / isolated resources
```

This file stays in sync conceptually with [ARCHITECTURE.md](ARCHITECTURE.md).
