Add direction() to generic template function adapter

The direction() template helper was only registered by the Kida
adapter, so sites using the generic adapter (Jinja2 and unknown
engines) had no way to detect RTL vs LTR in templates. This adds
direction() to the i18n register() call and the generic adapter,
using the site default language when no page context is available.
