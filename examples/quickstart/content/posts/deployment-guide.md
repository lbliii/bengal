---
title: "Deploying Your Bengal Site"
date: 2025-09-18
tags: ["deployment", "hosting", "tutorial"]
description: "Learn how to deploy your Bengal site to various platforms"
---

# Deploying Your Bengal Site

Bengal sites can be deployed anywhere that serves static files. Here are some popular options.

## Netlify

1. Connect your Git repository
2. Set build command: `bengal build`
3. Set publish directory: `public`
4. Deploy!

## Vercel

Similar to Netlify:
- Build command: `bengal build`
- Output directory: `public`

## GitHub Pages

Push your `public` directory to the `gh-pages` branch.

## Self-Hosting

Use any web server (Nginx, Apache, Caddy) to serve the `public` directory.

