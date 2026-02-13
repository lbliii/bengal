---
title: The Bengal Ecosystem
description: A structured reactive stack — every layer written in pure Python for 3.14t free-threading
draft: false
weight: 50
lang: en
type: doc
tags:
- about
- ecosystem
keywords:
- ecosystem
- bengal
- purr
- chirp
- pounce
- kida
- patitas
- rosettes
icon: layers
---

# The Bengal Ecosystem

A structured reactive stack — every layer written in pure Python for 3.14t free-threading.

## Stack Overview

```mermaid
flowchart TB
    subgraph contentLayer [Content Layer]
        Patitas[Patitas - Markdown Parser]
        Rosettes[Rosettes - Syntax Highlighter]
    end

    subgraph renderLayer [Rendering Layer]
        Kida[Kida - Template Engine]
    end

    subgraph appLayer [Application Layer]
        Chirp[Chirp - Web Framework]
    end

    subgraph transportLayer [Transport Layer]
        Pounce[Pounce - ASGI Server]
    end

    subgraph orchestrationLayer [Orchestration]
        Bengal[Bengal - Static Site Gen]
        Purr[Purr - Content Runtime]
    end

    Rosettes --> Patitas
    Patitas --> Kida
    Kida --> Chirp
    Chirp --> Pounce
    Chirp --> Patitas
    Bengal --> Patitas
    Bengal --> Kida
    Purr --> Pounce
    Purr --> Bengal
```

| | | | |
|--:|---|---|---|
| **ᓚᘏᗢ** | **Bengal** | Static site generator ← You are here | [Docs](https://lbliii.github.io/bengal/) |
| **∿∿** | [Purr](https://github.com/lbliii/purr) | Content runtime | — |
| **⌁⌁** | [Chirp](https://github.com/lbliii/chirp) | Web framework | [Docs](https://lbliii.github.io/chirp/) |
| **=^..^=** | [Pounce](https://github.com/lbliii/pounce) | ASGI server | [Docs](https://lbliii.github.io/pounce/) |
| **)彡** | [Kida](https://github.com/lbliii/kida) | Template engine | [Docs](https://lbliii.github.io/kida/) |
| **ฅᨐฅ** | [Patitas](https://github.com/lbliii/patitas) | Markdown parser | [Docs](https://lbliii.github.io/patitas/) |
| **⌾⌾⌾** | [Rosettes](https://github.com/lbliii/rosettes) | Syntax highlighter | [Docs](https://lbliii.github.io/rosettes/) |

Python-native. Free-threading ready. No npm required.
