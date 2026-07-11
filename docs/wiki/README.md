# StreamTV Wiki (in-tree)

Canonical copy of the [StreamTV GitHub Wiki](https://github.com/roto31/StreamTV/wiki). Pages use GitHub Wiki filenames and navigation (`Title-Case.md`).

## Structure

| Page | Description |
|------|-------------|
| [Home.md](Home.md) | Wiki landing — platform distributions |
| [Documentation-Index.md](Documentation-Index.md) | Full documentation index |
| [Beginner-Guide.md](Beginner-Guide.md) | Novice users |
| [Intermediate-Guide.md](Intermediate-Guide.md) | Technicians |
| [Expert-Guide.md](Expert-Guide.md) | Engineers |
| [Installation-Guide.md](Installation-Guide.md) | Cross-platform install |
| [macOS.md](macOS.md) | macOS distribution |
| [Windows.md](Windows.md) | Windows distribution |
| [Linux.md](Linux.md) | Linux distribution |
| [Containers.md](Containers.md) | Docker / K8s / Podman |
| [API-Reference.md](API-Reference.md) | REST API |
| [Schedules.md](Schedules.md) | YAML schedules |
| [Authentication.md](Authentication.md) | Auth overview |
| [Authentication-System.md](Authentication-System.md) | Advanced auth |
| [Archive-Parser.md](Archive-Parser.md) | Archive.org channels |
| [Plex-Integration.md](Plex-Integration.md) | Plex setup |
| [Logging.md](Logging.md) | Logging system |
| [SwiftUI.md](SwiftUI.md) | SwiftUI apps |
| [Scripts-and-Tools.md](Scripts-and-Tools.md) | CLI tools |
| [Troubleshooting.md](Troubleshooting.md) | Common issues |
| [Implementation.md](Implementation.md) | Technical implementation |

## Sync to public wiki

From the private repo root:

```bash
bash scripts/sync_public_docs.sh --apply --wiki
```

Edits belong here (`docs/wiki/`); `.github/wiki/` is deprecated.
