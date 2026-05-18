# Contributing to AegisNova OS

Thank you for your interest in contributing! This guide covers how to add new tools, themes, and improvements.

## Code of Conduct

All contributions must comply with our [Legal Notice](LEGAL_NOTICE.md). Tools added must be for **legitimate security testing only**.

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-tool`
3. Make your changes
4. Test locally (see below)
5. Submit a pull request

## Adding New Security Tools

### Red-Team Tools

1. Add the package name to `overlay/packages/redteam.list.chroot`
2. Update `meta-packages/redteam-meta/DEBIAN/control` Depends field
3. Add a one-line description in the README tool table
4. If the tool requires configuration, add it to `overlay/configs/`

### Blue-Team Tools

1. Add the package name to `overlay/packages/blueteam.list.chroot`
2. Update `meta-packages/blueteam-meta/DEBIAN/control` Depends field
3. If the tool needs a systemd unit, add it to `overlay/systemd/`

## Adding Apple-Style Themes

### GTK/GNOME Shell Themes

1. Add the theme's git clone and install commands to `overlay/theme/install-macos-theme.sh`
2. Update `overlay/theme/macos-theme.conf` with the new theme names
3. Update `overlay/scripts/macos-theme-switcher.sh` to support the new theme

### Wallpapers

1. Place wallpaper files (JPG/PNG, min 3840×2160) in `overlay/theme/wallpapers/`
2. They'll automatically be included in the random rotation

### Icon/Cursor Themes

1. Add installation to `overlay/theme/install-macos-theme.sh`
2. Update the theme switcher config and script

## Swapping the LLM Backend

Edit the following files to change the AI model:

| File | Variable | Example |
|------|----------|---------|
| `overlay/systemd/ai-shell.service` | `LLAMA_MODEL` | `/opt/aegisnova/models/llama-3-8b-Q4.gguf` |
| `overlay/docker/redteam-auto.yml` | `LLM_MODEL` | `gpt-4o` or `claude-3-sonnet` |
| `overlay/docker/blue-analyst.yml` | `LLM_ENDPOINT` | `https://api.openai.com/v1` |

For cloud APIs, set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `/etc/aegisnova/env`.

## Testing Locally

```bash
# Build kernel
sudo ./build_kernel.sh

# Build ISO
sudo ./custom_iso.sh

# Boot in QEMU
qemu-system-x86_64 -m 4G -cdrom AegisNova-v1.0.iso -enable-kvm

# Run smoke tests
./tests/smoke-test.sh AegisNova-v1.0.iso
```

## Pull Request Guidelines

- Keep PRs focused on a single feature or fix
- Update documentation for any user-facing changes
- Ensure the CI pipeline passes
- Security tools must be from reputable open-source projects
- Include the tool's license in your PR description

## License

By contributing, you agree that your contributions will be licensed under the project's GPL-3.0 license.
