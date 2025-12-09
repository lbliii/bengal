# Research: ElevenLabs TTS Integration for Documentation

**Status**: Research  
**Created**: 2025-12-09  
**Author**: AI Assistant  
**Related**: `plan/active/rfc-media-embed-directives.md`, ElevenLabs API docs

---

## Executive Summary

Investigating the feasibility of integrating ElevenLabs text-to-speech (TTS) capabilities to enable audio narration of Bengal documentation. This would allow users to listen to documentation content, improving accessibility and enabling consumption in contexts where reading isn't practical (commuting, exercising, etc.).

**Key Finding**: ElevenLabs offers both REST and WebSocket APIs suitable for this use case. Integration is feasible at multiple levels (build-time generation, client-side streaming, or hybrid).

---

## ElevenLabs API Overview

### Available APIs

Based on [ElevenLabs documentation](https://elevenlabs.io/docs/overview/intro):

| API | Use Case | Latency | Best For |
|-----|----------|---------|----------|
| **REST TTS** | Full text, static generation | Higher (~1-3s) | Build-time audio generation |
| **WebSocket TTS** | Streaming, real-time | Low (~75ms for Flash) | Interactive/live playback |
| **Speech-to-Text** | Transcription | - | Not applicable |

### Key Models

| Model | Latency | Quality | Languages | Use Case |
|-------|---------|---------|-----------|----------|
| **Eleven Flash v2.5** | ~75ms | Good | 32 | Real-time streaming |
| **Eleven Turbo v2.5** | Medium | High | 32 | Balance quality/speed |
| **Eleven Multilingual v2** | Higher | Highest | 29 | Long-form, quality |
| **Eleven v3 (Alpha)** | Higher | Expressive | 70+ | Dramatic delivery |

### WebSocket API Details

From [WebSocket API Reference](https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-stream-input):

```yaml
endpoint: wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input

output_formats:
  - mp3_44100_128 (recommended for quality)
  - mp3_22050_32 (smaller files)
  - pcm_16000 (raw audio)
  - opus_48000_64 (efficient streaming)

features:
  - Partial text streaming (chunks)
  - Word-to-audio alignment data
  - Voice settings (stability, similarity_boost, speed)
  - Auto mode for natural pacing
```

---

## Integration Architecture Options

### Option A: Build-Time Generation (Recommended for Start)

Generate audio files during site build for documentation pages.

```
┌─────────────────────────────────────────────────────────────┐
│                    Bengal Build Pipeline                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Audio Generation Phase                    │
│                                                             │
│  1. Extract clean text from page content                    │
│  2. Check cache for existing audio                          │
│  3. Call ElevenLabs REST API for changed pages              │
│  4. Save MP3 to assets directory                            │
│  5. Update page metadata with audio path                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Audio Player Injection                    │
│                                                             │
│  - Add audio player component to page template              │
│  - Reference generated MP3 file                             │
│  - Include playback controls                                │
└─────────────────────────────────────────────────────────────┘
```

**Pros**:
- Simple architecture
- No client-side API calls
- Works offline after build
- Cacheable CDN-friendly assets
- Predictable costs

**Cons**:
- Increased build time
- Storage requirements for audio files
- Stale audio if content changes without rebuild

### Option B: Client-Side Streaming

Stream audio on-demand when user clicks play button.

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   User Browser   │───▶│   Bengal Site    │───▶│  ElevenLabs API  │
│                  │◀───│   (Static)       │◀───│  (WebSocket)     │
└──────────────────┘    └──────────────────┘    └──────────────────┘

Flow:
1. User clicks "Listen" button
2. JS extracts visible text content
3. Opens WebSocket to ElevenLabs
4. Streams audio chunks to Web Audio API
5. Plays audio in real-time
```

**Pros**:
- No build-time processing
- Always up-to-date with page content
- Smaller initial site payload
- Lower storage costs

**Cons**:
- Requires API key exposure (or proxy)
- Per-request API costs
- Network dependency for playback
- More complex client-side code

### Option C: Hybrid Approach

Pre-generate for stable docs, stream for dynamic content.

```yaml
strategy:
  stable_docs:       # API Reference, Tutorials
    method: build-time
    trigger: content_hash_change
    cache: persistent
    
  dynamic_content:   # Blog, Changelog
    method: client-stream
    trigger: on_demand
    cache: session_only
```

---

## Proposed Bengal Integration

### New Directive: `:::{audio-tts}`

Extend the existing audio directive system with TTS capabilities:

```markdown
<!-- Generate audio from page content -->
:::{audio-tts}
:voice: rachel
:model: eleven_multilingual_v2
:::

<!-- Generate audio from specific content -->
:::{audio-tts}
:voice: rachel
:source: section  # Only this section
:::

This section will be read aloud when the directive is rendered.
:::
```

### New Page Frontmatter Option

```yaml
---
title: Getting Started
tts:
  enabled: true
  voice: rachel
  model: eleven_turbo_v2_5
  exclude_selectors:
    - ".code-block"
    - ".navigation"
---
```

### New Config Section

```yaml
# config/_default/tts.yaml
tts:
  provider: elevenlabs
  enabled: false  # Off by default
  
  elevenlabs:
    api_key: ${ELEVENLABS_API_KEY}  # From environment
    default_voice: rachel
    default_model: eleven_turbo_v2_5
    output_format: mp3_44100_128
    
  generation:
    mode: build_time  # build_time | on_demand | hybrid
    cache_dir: .cache/tts/
    max_chars_per_request: 5000  # ElevenLabs limit
    
  player:
    position: top  # top | bottom | floating
    show_speed_control: true
    show_download: true
```

### Module Structure

```
bengal/
├── tts/                          # NEW: TTS subsystem
│   ├── __init__.py
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract provider interface
│   │   └── elevenlabs.py        # ElevenLabs implementation
│   ├── extractor.py             # Text extraction from HTML
│   ├── generator.py             # Audio generation orchestrator
│   └── cache.py                 # TTS-specific caching
│
├── rendering/
│   └── plugins/
│       └── directives/
│           └── audio.py         # Extend with TTS directive
│
└── themes/
    └── default/
        └── assets/
            ├── css/
            │   └── components/
            │       └── _audio-player.css
            └── js/
                └── audio-player.js
```

---

## Implementation Considerations

### Text Extraction

**Challenge**: Extract clean, readable text from rendered HTML.

```python
class TextExtractor:
    """Extract clean text for TTS from HTML content."""
    
    EXCLUDE_SELECTORS = [
        "pre",           # Code blocks
        "code",          # Inline code
        ".admonition",   # Callouts (optional)
        "nav",           # Navigation
        ".breadcrumb",   # Breadcrumbs
        "script",        # Scripts
        "style",         # Styles
    ]
    
    def extract(self, html: str, exclude: list[str] | None = None) -> str:
        """Extract readable text from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove excluded elements
        for selector in (exclude or self.EXCLUDE_SELECTORS):
            for el in soup.select(selector):
                el.decompose()
        
        # Get text with natural spacing
        text = soup.get_text(separator=" ", strip=True)
        
        # Clean up
        text = self._normalize_whitespace(text)
        text = self._handle_special_chars(text)
        
        return text
```

### Caching Strategy

```python
@dataclass
class TTSCacheEntry:
    """Cache entry for generated audio."""
    content_hash: str      # Hash of source text
    audio_path: str        # Path to generated MP3
    voice_id: str          # Voice used
    model_id: str          # Model used
    created_at: datetime
    duration_seconds: float
    character_count: int

class TTSCache:
    """Cache manager for TTS audio files."""
    
    def get_or_generate(
        self, 
        text: str, 
        voice: str, 
        model: str,
        generator: TTSGenerator
    ) -> Path:
        """Get cached audio or generate new."""
        cache_key = self._make_key(text, voice, model)
        
        if cached := self._get_cached(cache_key):
            return cached.audio_path
        
        # Generate new audio
        audio_path = generator.generate(text, voice, model)
        self._store(cache_key, audio_path, text)
        
        return audio_path
```

### API Rate Limits and Costs

**ElevenLabs Pricing** (as of late 2024):

| Plan | Characters/Month | Price | Per 1K chars |
|------|-----------------|-------|--------------|
| Free | 10,000 | $0 | - |
| Starter | 30,000 | $5/mo | $0.17 |
| Creator | 100,000 | $22/mo | $0.22 |
| Pro | 500,000 | $99/mo | $0.20 |
| Scale | 2,000,000 | $330/mo | $0.17 |

**Estimation for Bengal site**:
- ~50 documentation pages
- ~2,000 characters average per page
- ~100,000 characters total
- **Creator plan (~$22/mo) sufficient for full site**

### Security Considerations

1. **API Key Protection**:
   - Never expose in client-side code
   - Use environment variables
   - Consider server proxy for on-demand generation

2. **Input Sanitization**:
   - Strip potentially malicious content before TTS
   - Limit maximum text length
   - Validate voice/model parameters

3. **Rate Limiting**:
   - Implement per-user rate limits for on-demand mode
   - Queue requests during high traffic

---

## Alternative Providers

For comparison, other TTS options:

| Provider | Quality | Latency | Cost | Notes |
|----------|---------|---------|------|-------|
| **ElevenLabs** | Excellent | ~75ms-1s | $0.17-0.22/1K | Best quality |
| **OpenAI TTS** | Very Good | ~500ms | $0.015/1K | Good value |
| **Google Cloud TTS** | Good | ~200ms | $0.004/1K | Cheapest |
| **Amazon Polly** | Good | ~200ms | $0.004/1K | AWS integration |
| **Microsoft Azure** | Good | ~200ms | $0.004/1K | Azure integration |

**Recommendation**: Start with ElevenLabs for quality, consider OpenAI as cost-effective alternative.

---

## User Experience Design

### Audio Player Component

```html
<div class="bengal-audio-player" data-audio-src="/assets/audio/getting-started.mp3">
  <button class="play-pause" aria-label="Play/Pause">
    <svg class="icon-play">...</svg>
    <svg class="icon-pause">...</svg>
  </button>
  
  <div class="progress-container">
    <div class="progress-bar"></div>
    <span class="time-current">0:00</span>
    <span class="time-total">5:32</span>
  </div>
  
  <div class="controls">
    <button class="speed" aria-label="Playback speed">1x</button>
    <button class="skip-back" aria-label="Skip back 10s">-10s</button>
    <button class="skip-forward" aria-label="Skip forward 10s">+10s</button>
    <a class="download" href="..." download aria-label="Download audio">⬇</a>
  </div>
</div>
```

### Accessibility Features

- Keyboard navigation (Space to play, arrows to seek)
- ARIA labels for all controls
- Screen reader announcements for state changes
- Visible focus indicators
- Reduced motion option (no animations)

### Progressive Enhancement

```javascript
// Only initialize if audio is available and supported
if ('HTMLAudioElement' in window && document.querySelector('[data-audio-src]')) {
  initializeAudioPlayer();
}
```

---

## Proof of Concept Plan

### Phase 1: Basic Build-Time Generation (MVP)

1. **Create TTS Provider Interface**
   - Abstract base class for TTS providers
   - ElevenLabs implementation

2. **Add Text Extractor**
   - HTML to clean text conversion
   - Configurable exclusions

3. **Build Integration**
   - Post-render hook to generate audio
   - Simple file caching

4. **Basic Player**
   - HTML5 audio element with minimal styling
   - Play/pause only

**Estimated Effort**: 15-20 hours

### Phase 2: Enhanced Features

1. **Smart Caching** - Content-hash based cache invalidation
2. **Player Enhancements** - Speed control, skip, download
3. **Section-Level Audio** - Generate per-section, not just per-page
4. **Progress Persistence** - Remember playback position

**Estimated Effort**: 20-25 hours

### Phase 3: Advanced Features

1. **WebSocket Streaming** - For on-demand generation
2. **Multiple Providers** - OpenAI, Google Cloud support
3. **Voice Selection UI** - Let users choose preferred voice
4. **Offline Support** - Service worker for cached audio

**Estimated Effort**: 30-40 hours

---

## Open Questions

1. **Scope**: Should TTS be opt-in per page or site-wide toggle?
2. **Content Types**: Should we support blog posts, not just docs?
3. **Multilingual**: How to handle multi-language sites?
4. **Code Blocks**: Skip entirely or announce "code block skipped"?
5. **Updates**: How to handle incremental updates (only changed sections)?
6. **Mobile UX**: How should player behave on mobile devices?
7. **Analytics**: Should we track audio engagement metrics?

---

## Next Steps

1. **Decision**: Build-time vs. streaming vs. hybrid approach
2. **PoC**: Create minimal proof-of-concept with ElevenLabs REST API
3. **User Research**: Survey Bengal users on audio documentation interest
4. **RFC**: If PoC successful, draft full RFC with architecture details

---

## References

- [ElevenLabs Documentation](https://elevenlabs.io/docs/overview/intro)
- [ElevenLabs WebSocket API](https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-stream-input)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [WCAG 2.1 Audio Accessibility](https://www.w3.org/WAI/media/av/)
- Bengal Audio Directive: `bengal/rendering/plugins/directives/figure.py`

