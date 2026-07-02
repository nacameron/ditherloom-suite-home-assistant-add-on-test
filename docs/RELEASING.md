# Releasing Home Assistant Versions

This project uses two repositories:

- Private source repo: `F:/ditherloom-suite-home-assistant-add-on`
- Public HACS repo: `F:/ditherloom-suite-home-assistant-add-on-test-repo`

Make and verify changes in the private repo first. Mirror only release-safe files
to the public repo after tests pass.

## Version Fields

For a new Home Assistant integration release, bump both:

```text
custom_components/ditherloom_suite_ha_addon/manifest.json
custom_components/ditherloom_suite_ha_addon/const.py
```

The public GitHub release tag must match the manifest version:

```text
v<manifest version>
```

Example:

```text
manifest version 0.1.78 -> public tag v0.1.78
```

## Private Repo Checklist

1. Search the Obsidian vault for the touched feature, lock, or provider.
2. Make the source change in the private repo.
3. Update docs, notices, and guardrail tests when behavior, attribution, release
   contents, providers, fonts, assets, or dependencies change.
4. Run:

```text
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe scripts/check_release_guards.py
```

5. Commit and push `main` in the private repo.

## Public Repo Checklist

1. Copy only release-safe files to:

```text
F:/ditherloom-suite-home-assistant-add-on-test-repo
```

2. Do not copy secrets, local app state, private caches, tokens, `.ppenc` files,
   transient previews, or private evidence.
3. Run the same tests against the public checkout. If the public checkout does
   not have its own virtual environment, it is acceptable to use the private
   repo `.venv` while keeping the working directory on the public repo:

```text
F:/ditherloom-suite-home-assistant-add-on/.venv/Scripts/python.exe -m pytest -q
F:/ditherloom-suite-home-assistant-add-on/.venv/Scripts/python.exe scripts/check_release_guards.py
```

4. Commit and push `main` in the public repo.

## GitHub Release

HACS and the update entity use the public GitHub release/tag.

For a new version:

```text
git tag v<version>
git push origin main
git push origin v<version>
gh release create v<version> --repo nacameron/ditherloom-suite-home-assistant-add-on-test --title "Ditherloom Suite Home Assistant Add On v<version>" --notes "<release notes>"
```

For a compliance-only correction to an already-published version, move the
existing tag to the new public commit and update the release notes:

```text
git tag -f v<version> HEAD
git push --force origin v<version>
gh release edit v<version> --repo nacameron/ditherloom-suite-home-assistant-add-on-test --notes "<updated release notes>"
```

After any public release change, verify:

```text
gh release list --repo nacameron/ditherloom-suite-home-assistant-add-on-test --limit 20
git ls-remote --tags origin v*
F:/ditherloom-suite-home-assistant-add-on/.venv/Scripts/python.exe scripts/check_release_guards.py
```

The expected public state is exactly one visible release and exactly one `v*`
tag for the current manifest version.

## Vault Update

After a meaningful release, update the Obsidian vault with:

- changed files,
- pushed commits,
- tests/guards run,
- public release URL/tag,
- anything intentionally not changed.
