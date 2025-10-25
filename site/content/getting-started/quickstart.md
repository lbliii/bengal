---
title: Quick Start
description: Your first project in 5 minutes
weight: 30
---

# Quick Start

1. Open a terminal and navigate to a location where you'd like to create your Bengal project.
2. Run the following command:

   ```sh
   bengal new site <my-site>
   ```

3. Choose from one of the following setup scenarios:

   ```sh
   » 📝 Blog          - Personal or professional blog
   📚 Documentation   - Technical docs or guides
   💼 Portfolio       - Showcase your work
   🏢 Business        - Company or product site
   📄 Resume          - Professional resume/CV site
   📦 Blank           - Empty site, no initial structure
   ⚙️  Custom         - Define your own structure
   ```

4. Run the following commands to open and run the project:

   ```sh
   cd <my-site>
   bengal site serve
   ```

5. Navigate to `http://localhost:5173/`.

:::{tip} Already know your site sections?

Choose **Custom** and pass in a comma-separated list of top-level sections for your site (e.g., `about, get started, guides, troubleshooting`)

:::
