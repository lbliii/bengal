---
name: scaffold-site
description: Scaffold a new Bengal documentation, blog, or marketing site from a built-in template. Use when creating a new Bengal site, starting from scratch, or choosing a site template/preset.
---

# Scaffold a Bengal Site

Create a new site as a **site author**. This skill covers `bengal new site` and
built-in templates only. It does not cover contributing to Bengal itself.

Requires **Python 3.14+**. If `bengal new site --help` fails, install first:

```bash
pip install bengal
```

Other install paths (uv, pipx, from source) are in
[/docs/get-started/installation/](https://lbliii.github.io/bengal/docs/get-started/installation/).

## Procedure

### Step 1: Discover templates

```bash
bengal new site --help
```

`--template` values from help: `default`, `blog`, `docs`, `portfolio`,
`product`, `resume`, `landing`, `changelog` (default: `default`).

`--theme` is the visual theme (default: `default`).

`--init-preset` skips the wizard and initializes with one of: `blog`, `docs`,
`portfolio`, `product`, `resume`.

### Step 2: Create the site

**Fastest path** (README):

```bash
bengal new site --name mysite && cd mysite && bengal serve
```

**Non-interactive template** (README):

```bash
bengal new site --name my-docs --template docs
bengal new site --name my-blog --template blog
bengal new site --name portfolio --template portfolio
```

**Interactive wizard** (no arguments; prompts for name, base URL, and preset):

```bash
bengal new site
```

**Skip the wizard with a preset:**

```bash
bengal new site --name my-docs --init-preset docs
```

Then:

```bash
cd my-docs
bengal serve
```

The dev server defaults to `http://localhost:5173` (`bengal serve --help`).

### Step 3: Pick a template

| Template     | Description                         |
|--------------|-------------------------------------|
| `default`    | Basic site structure; home page     |
| `blog`       | Personal/professional blog          |
| `docs`       | Technical documentation             |
| `portfolio`  | Showcase work                       |
| `product`    | Product site with listings          |
| `resume`     | Professional resume/CV              |
| `landing`    | Single-page landing                 |
| `changelog`  | Release notes timeline              |

Do not invent template names. If a name is not in `bengal new site --help`,
treat it as **TODO** and ask the author.

## After scaffolding

- Edit site identity in `config/` (preferred) or `bengal.toml`. See the
  **configure-site** skill and
  [/docs/ship/configuration/](https://lbliii.github.io/bengal/docs/ship/configuration/).
- Add pages with `bengal new page`. See the **write-content** skill.
- Preview with `bengal serve`. Production build: `bengal build`.

## Docs to read

- [/docs/get-started/](https://lbliii.github.io/bengal/docs/get-started/)
- [/docs/get-started/quickstart-writer/](https://lbliii.github.io/bengal/docs/get-started/quickstart-writer/)
- [/docs/get-started/scaffold-your-site/](https://lbliii.github.io/bengal/docs/get-started/scaffold-your-site/)

## Checklist

- [ ] `bengal new site --help` lists the template you intend to use
- [ ] Site created with `--name` and optional `--template` / `--init-preset`
- [ ] `cd` into the new directory
- [ ] `bengal serve` loads in the browser
- [ ] No template or flag was invented; unknowns are TODO
