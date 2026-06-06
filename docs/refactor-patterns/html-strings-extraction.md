---
name: file-extraction-pattern-html-strings
auto: true
trigger: Monolithe Python avec 2+ strings HTML hardcodées > 10k chars chacune
---

# Extraction HTML strings vers fichiers static (pattern Python)

## Pourquoi
Monolithe Python avec 2+ strings HTML inline rend la maintenance inévitable (diff bruyant, navigation difficile, syntaxe Python pollue contenu HTML). Extraction vers static/ séparation logique (code Python 🔄 HTML/CSS séparé), enable caching filesystem et reload static sans redémarrage daemon.

## Procédure
1. **Localisez les strings** : `grep -n '^VAR_NAME = r"""' <file>.py` → grab line numbers
2. **Extract** : Python script qui lit les strings (entre délimiteur et `"""` close), écrit dans `bin/ui/static/<nom>.html`
3. **Loader** : créez 2 helper functions `_get_html_page()` / `_get_agents_mesh_page()` qui lisent depuis `~/_STATIC_DIR/` avec cache filesystem
4. **Replace usages** : swap `self._html(HTML_PAGE)` → `self._html(_get_html_page())` + `self._html(AGENTS_MESH_PAGE)` → `self._html(_get_agents_mesh_page())`
5. **Bootstrap** : ajoutez copie récursive `cp -r bin/ui/ ~/.local/bin/ui/` au bootstrap pour TCC-safe deployment
6. **Validate** : test endpoints JSON (diff vs baseline), screenshot Playwright

## Code / commande type
```python
# Loader function (dans module main ou config)
_STATIC_DIR = Path(__file__).parent / "ui" / "static"
_HTML_CACHE = {}

def _get_html_page():
    if "html_page" not in _HTML_CACHE:
        _HTML_CACHE["html_page"] = (_STATIC_DIR / "index.html").read_text()
    return _HTML_CACHE["html_page"]

def _get_agents_mesh_page():
    if "agents_mesh" not in _HTML_CACHE:
        _HTML_CACHE["agents_mesh"] = (_STATIC_DIR / "agents_mesh.html").read_text()
    return _HTML_CACHE["agents_mesh"]
```

## Anti-patterns à éviter
- Ne pas relire depuis disk à chaque request (cache manquant = I/O chaud)
- Ne pas copier HTML dans venv après extraction (venv est un runtime artifact, static vit dans repo)
- Ne pas utiliser symlinks pour bin/ui/ en bootstrap (TCC bloque les symlink-resolved opens si launchd-spawned)
