__all__ = ["anchor2prov", "build_prov_document"]


def __getattr__(name):
    if name in __all__:
        from anchor.prov.mapper import anchor2prov, build_prov_document

        exports = {
            "anchor2prov": anchor2prov,
            "build_prov_document": build_prov_document,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
