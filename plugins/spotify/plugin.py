from src.tools import open_app


PLUGIN_NAME = "spotify"
PLUGIN_CAPABILITIES = ["music", "audio"]


def open_spotify():
    return open_app("spotify")


def register_tools(registry):
    registry.register_external_tool(
        name="open_spotify",
        description="Abre Spotify y activa el flujo de música",
        schema={"type": "object", "properties": {}},
        func=open_spotify,
        risk="safe",
        source="plugin",
        keywords=["spotify", "música", "musica", "audio", "play"],
        capabilities=PLUGIN_CAPABILITIES,
        plugin_name=PLUGIN_NAME,
    )