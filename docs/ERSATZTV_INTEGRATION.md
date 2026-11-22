# ErsatzTV-inspired Scheduling Features

> **Canonical living how-to:** [features/ERSATZTV_INTEGRATION.md](features/ERSATZTV_INTEGRATION.md)  
> **Integrations overview:** [wiki/Implementation.md](wiki/Implementation.md)

StreamTV reimplements selected schedule YAML patterns inspired by
[ErsatzTV](https://github.com/ErsatzTV/ErsatzTV) in Python under `streamtv/scheduling/`.
It is **not** a fork and does **not** vendor ErsatzTV source.

Schedules are `schedules/{n}.yml` on disk. Web create/edit is removed; `POST`/`PUT`
`/api/schedules` return **410 Gone**.
