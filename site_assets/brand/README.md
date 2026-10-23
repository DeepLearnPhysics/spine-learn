# SPINE branding

`spine-logo-light.png` is an unmodified copy of the SPINE white-letter wordmark
from `spine/docs/source/_static/img/spine-logo-light.png`. Its orange is #EB7913.
The source asset SHA-256 begins `2d179fee60e4`.

`spine-logo-dark.png` is an unmodified copy of the black-letter wordmark from
`spine/docs/source/_static/img/spine-logo-dark.png`. The filenames describe the
lettering, not the site theme: light mode uses dark letters, and dark mode uses
light letters. Both the navigation and landing banner follow the selected theme.
Keep the original proportions and colors; do not recolor the logos with CSS.

`favicon.ico` uses the artwork from
`spine/docs/source/_static/img/favicon.ico`, the file selected by SPINE RTD
through `html_favicon`. That source contains a 1200×1200 PNG despite its `.ico`
extension. Here it is encoded as a genuine ICO containing 16, 32, 48, 64, 128,
and 256 pixel versions, preserving the artwork and transparency. This matches
the icon content type served by the website. MyST selects it through
`site.options.favicon`. Do not replace it with the misnamed PNG; site verification
checks the ICO header and common browser icon sizes.
