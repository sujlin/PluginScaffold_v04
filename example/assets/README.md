# Assets

Put plugin images in `assets/images/`.

`tools/build.py` reads `config/plugin.json` -> `assets.images` and embeds each image as:

```text
DependencyExport -> Appearance -> UserImage -> FileContent/Block
```

The first image is normally used as the plugin pool Appearance.
