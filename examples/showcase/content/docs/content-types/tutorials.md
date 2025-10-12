---
title: Tutorials
description: Create step-by-step educational guides and learning paths
type: doc
weight: 4
tags: ["content-types", "tutorials", "education"]
toc: true
---

# Tutorials

**Purpose**: Create step-by-step educational guides for learners.

## What You'll Learn

- Create tutorial content
- Structure learning paths
- Add difficulty levels
- Write effective instructions

## When to Use

Use tutorials for:

- **Step-by-step guides** - Complete workflows
- **Learning paths** - Progressive skill building
- **How-to articles** - Task-based instructions
- **Educational content** - Teaching materials

## Basic Structure

```markdown
---
title: Python for Beginners
description: Learn Python programming from scratch
type: tutorial
difficulty: beginner
duration: 60
prerequisites: ["Basic computer skills"]
---

# Python for Beginners

Learn Python programming step by step.

## What You'll Learn

- Python basics
- Variables and data types
- Functions and loops

## Prerequisites

- Computer with Python installed
- Text editor
- Basic command line knowledge

## Step 1: Setup

Install Python...

## Step 2: First Program

Write your first program...

## Next Steps

Continue with [Intermediate Python](intermediate-python.md).
```

## Tutorial-Specific Frontmatter

### difficulty

Skill level required:

```yaml
---
difficulty: beginner      # beginner, intermediate, advanced
---
```

### duration

Estimated completion time (minutes):

```yaml
---
duration: 30   # 30 minutes
---
```

### prerequisites

What learners need first:

```yaml
---
prerequisites:
  - "Python installed"
  - "Basic command line knowledge"
  - "Completed beginner tutorial"
---
```

## Tutorial Structure

### Introduction

- What learners will achieve
- What they'll learn
- Prerequisites
- Estimated duration

### Main Steps

Number steps clearly:

```markdown
## Step 1: Setup Environment

Install required tools...

## Step 2: Create Project

Initialize your project...

## Step 3: Write Code

Start coding...
```

### Checkpoint Sections

Verify progress:

```markdown
## Checkpoint

Before continuing, ensure:

- [ ] Environment configured
- [ ] Project created
- [ ] Code runs without errors
```

### Conclusion

- Summary of what was learned
- Next steps
- Additional resources

## Complete Example

```markdown
---
title: Build Your First Static Site
description: Create and deploy a static site from scratch
type: tutorial
difficulty: beginner
duration: 45
prerequisites:
  - "Python 3.8 or higher"
  - "Basic command line knowledge"
tags: ["tutorial", "beginner", "static-sites"]
---

# Build Your First Static Site

Learn to create and deploy your first static website.

## What You'll Learn

- Install Bengal
- Create a new site
- Add content
- Build and preview
- Deploy to production

## Prerequisites

Before starting, ensure you have:

- Python 3.8+ installed
- Basic terminal/command prompt knowledge
- Text editor (VS Code, Sublime, etc.)

## Estimated Time

⏱️ 45 minutes

## Step 1: Install Bengal

Open your terminal and run:

\`\`\`bash
pip install bengal
\`\`\`

Verify installation:

\`\`\`bash
bengal --version
\`\`\`

```{success} Installation Complete
You should see the Bengal version number.
```

## Step 2: Create Your Site

Create a new site:

\`\`\`bash
bengal new site mysite
cd mysite
\`\`\`

Your site structure:

\`\`\`
mysite/
├── bengal.toml
├── content/
│   └── _index.md
└── assets/
\`\`\`

## Step 3: Add Content

Create your first page:

\`\`\`bash
bengal new page about
\`\`\`

Edit `content/about.md`:

\`\`\`markdown
---
title: About
---

# About Me

I'm learning static sites!
\`\`\`

## Step 4: Build and Preview

Build your site:

\`\`\`bash
bengal build
\`\`\`

Start the development server:

\`\`\`bash
bengal serve
\`\`\`

Visit `http://localhost:5173` in your browser.

```{tip} Live Reload
The server automatically rebuilds when you save files!
```

## Step 5: Deploy

Deploy to Netlify:

1. Create account at netlify.com
2. Drag `public/` folder to Netlify
3. Your site is live!

## Checkpoint

✅ You've completed:

- [x] Installed Bengal
- [x] Created a site
- [x] Added content
- [x] Built and previewed locally
- [x] Deployed to production

## What You Learned

- How to install and set up Bengal
- Creating and organizing content
- Building and previewing sites
- Deploying to production

## Next Steps

Ready to learn more?

- **[Add Blog Posts](blog-tutorial.md)** - Create a blog
- **[Customize Themes](theme-tutorial.md)** - Make it yours
- **[Advanced Features](../advanced/)** - Level up

## Additional Resources

- [Documentation](../documentation.md)
- [Writing Guide](../writing/)
- [Community Discord](https://discord.gg/example)
```

## Best Practices

### Use Clear Steps

```markdown
✅ Good (numbered steps):
## Step 1: Install Tools
## Step 2: Create Project
## Step 3: Configure Settings

❌ Vague:
## First Thing
## Next
## Finally
```

### Show Expected Results

```markdown
✅ Include results:
Run this command:
\`\`\`bash
bengal --version
\`\`\`

You should see:
\`\`\`
Bengal 0.2.0
\`\`\`

❌ No verification:
Run `bengal --version`
(No indication of what to expect)
```

### Add Visual Aids

- Screenshots of results
- Code output examples
- Diagrams of concepts
- Highlighted important parts

### Include Checkpoints

```markdown
## Checkpoint

Before continuing:

- [ ] Server is running
- [ ] Page loads in browser
- [ ] No error messages
```

## Difficulty Levels

### Beginner

- Basic concepts
- Step-by-step detail
- Minimal prerequisites
- Extensive explanations

### Intermediate

- Assumes basic knowledge
- Faster paced
- Some prerequisites
- Less hand-holding

### Advanced

- Complex topics
- Multiple prerequisites
- Assumes experience
- Focus on why, not just how

## Quick Reference

**Minimal tutorial:**
```yaml
---
title: Tutorial Title
type: tutorial
difficulty: beginner
---
```

**Complete tutorial:**
```yaml
---
title: Tutorial Title
description: What you'll build
type: tutorial
difficulty: beginner
duration: 30
prerequisites:
  - "Prerequisite 1"
  - "Prerequisite 2"
tags: ["tutorial", "beginner"]
---
```

## Next Steps

- **[Blog Posts](blog-posts.md)** - Write articles
- **[Documentation](documentation.md)** - Technical docs
- **[Content Organization](../writing/content-organization.md)** - Structure
- **[Directives](../directives/)** - Rich content

## Related

- [Content Types Overview](index.md) - All types
- [Writing Guide](../writing/) - Content basics
- [Markdown Basics](../writing/markdown-basics.md) - Formatting
