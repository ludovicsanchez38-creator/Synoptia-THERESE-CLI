"""Outils web : WebFetch et WebSearch."""

import re
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from .base import Tool, ToolResult


class WebFetchTool(Tool):
    """Récupère le contenu d'une page web."""

    name = "web_fetch"
    description = (
        "Récupère le contenu d'une URL et l'extrait en texte lisible. "
        "Utile pour lire de la documentation, des articles, ou du contenu web."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "L'URL à récupérer",
            },
            "extract_main": {
                "type": "boolean",
                "description": "Extraire uniquement le contenu principal. Par défaut: true",
            },
        },
        "required": ["url"],
    }

    async def execute(
        self,
        url: str,
        extract_main: bool = True,
        **kwargs: Any,
    ) -> ToolResult:
        """Récupère et parse une page web."""
        try:
            # Valider l'URL
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
            elif parsed.scheme == "http":
                url = url.replace("http://", "https://", 1)

            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0,
                headers={
                    "User-Agent": "THERESE-CLI/0.1 (https://github.com/synoptia/therese-cli)"
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            if "text/html" in content_type:
                # Parser HTML basique
                html = response.text
                text = self._html_to_text(html, extract_main)
            elif "application/json" in content_type:
                text = response.text
            elif "text/" in content_type:
                text = response.text
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Type de contenu non supporté: {content_type}",
                )

            # Tronquer si trop long
            if len(text) > 50000:
                text = text[:50000] + "\n\n... [contenu tronqué]"

            return ToolResult(
                success=True,
                output=f"# Contenu de {url}\n\n{text}",
            )

        except httpx.HTTPStatusError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur HTTP {e.response.status_code}: {url}",
            )
        except httpx.RequestError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur de requête: {e}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur: {e}",
            )

    def _html_to_text(self, html: str, extract_main: bool) -> str:
        """Convertit HTML en texte lisible."""
        # Supprimer scripts et styles
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<nav[^>]*>.*?</nav>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<footer[^>]*>.*?</footer>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<header[^>]*>.*?</header>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Extraire le main si demandé
        if extract_main:
            main_match = re.search(r"<main[^>]*>(.*?)</main>", html, flags=re.DOTALL | re.IGNORECASE)
            if main_match:
                html = main_match.group(1)
            else:
                article_match = re.search(r"<article[^>]*>(.*?)</article>", html, flags=re.DOTALL | re.IGNORECASE)
                if article_match:
                    html = article_match.group(1)

        # Convertir les headers
        for i in range(1, 7):
            html = re.sub(rf"<h{i}[^>]*>(.*?)</h{i}>", rf"\n\n{'#' * i} \1\n", html, flags=re.DOTALL | re.IGNORECASE)

        # Convertir les paragraphes
        html = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", html, flags=re.DOTALL | re.IGNORECASE)

        # Convertir les listes
        html = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", html, flags=re.DOTALL | re.IGNORECASE)

        # Convertir le code
        html = re.sub(r"<pre[^>]*>(.*?)</pre>", r"\n```\n\1\n```\n", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", html, flags=re.DOTALL | re.IGNORECASE)

        # Convertir les liens
        html = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", html, flags=re.DOTALL | re.IGNORECASE)

        # Supprimer les autres tags
        html = re.sub(r"<[^>]+>", "", html)

        # Nettoyer les espaces
        html = re.sub(r"\n\s*\n", "\n\n", html)
        html = re.sub(r"  +", " ", html)

        # Décoder les entités HTML basiques
        html = html.replace("&nbsp;", " ")
        html = html.replace("&amp;", "&")
        html = html.replace("&lt;", "<")
        html = html.replace("&gt;", ">")
        html = html.replace("&quot;", '"')
        html = html.replace("&#39;", "'")

        return html.strip()


class WebSearchTool(Tool):
    """Recherche sur le web (via DuckDuckGo)."""

    name = "web_search"
    description = (
        "Recherche sur le web pour trouver des informations récentes. "
        "Retourne les résultats de recherche avec titres, URLs et descriptions."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "La requête de recherche",
            },
            "num_results": {
                "type": "integer",
                "description": "Nombre de résultats. Par défaut: 5",
            },
        },
        "required": ["query"],
    }

    async def execute(
        self,
        query: str,
        num_results: int = 5,
        **kwargs: Any,
    ) -> ToolResult:
        """Effectue une recherche web."""
        try:
            # Utiliser DuckDuckGo HTML (pas d'API key nécessaire)
            search_url = "https://html.duckduckgo.com/html/"

            async with httpx.AsyncClient(
                timeout=15.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            ) as client:
                response = await client.post(
                    search_url,
                    data={"q": query, "b": ""},
                )
                response.raise_for_status()

            html = response.text

            # Parser les résultats
            results = []
            pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<a[^>]*class="result__snippet"[^>]*>(.*?)</a>'

            for match in re.finditer(pattern, html, re.DOTALL):
                if len(results) >= num_results:
                    break

                url = match.group(1)
                # DuckDuckGo encode les URLs
                if "uddg=" in url:
                    url_match = re.search(r"uddg=([^&]+)", url)
                    if url_match:
                        from urllib.parse import unquote
                        url = unquote(url_match.group(1))

                title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
                snippet = re.sub(r"<[^>]+>", "", match.group(3)).strip()

                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                })

            if not results:
                return ToolResult(
                    success=True,
                    output=f"Aucun résultat trouvé pour: {query}",
                )

            # Formater les résultats
            output_lines = [f"# Résultats pour \"{query}\"\n"]
            for i, r in enumerate(results, 1):
                output_lines.append(f"## {i}. {r['title']}")
                output_lines.append(f"🔗 {r['url']}")
                output_lines.append(f"{r['snippet']}\n")

            return ToolResult(success=True, output="\n".join(output_lines))

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur de recherche: {e}",
            )
