---
name: chart-visualization
description: This skill should be used when the user wants to visualize data. It intelligently selects the most suitable chart type from 26 available options, extracts parameters based on detailed specifications, and generates a chart image using a JavaScript script.
compatibility:
  nodejs: ">=18.0.0"
---

# Chart Visualization Skill

This skill transforms structured data into visual charts using ECharts JSON rendered directly from Markdown.

## Workflow

To visualize data, follow these steps:

### 1. Intelligent Chart Selection
Analyze the user's data features to determine the most appropriate chart type:

- **Time series**: ECharts `line`; use dual y-axes when metrics have different scales.
- **Comparisons**: ECharts `bar`.
- **Part-to-whole**: ECharts `pie` or `treemap`.
- **Relationships**: ECharts `scatter`, `graph`, or `sankey`.
- **Distribution**: ECharts `boxplot`, histogram-style `bar`, or `scatter`.
- **Progress / funnel**: ECharts `gauge` or `funnel`.

### 2. Parameter Extraction
Extract the data from the user's input or MCP/tool result and map it to an ECharts `option` object. Include title, tooltip, legend, grid, axes, series, and readable labels.

### 3. Markdown Chart Generation
Return an ECharts JSON block directly in the final Markdown response:

````markdown
```echarts
{
  "height": 360,
  "option": {
    "title": { "text": "Chart title", "left": "left" },
    "tooltip": { "trigger": "axis" },
    "legend": { "top": 24 },
    "grid": { "left": 40, "right": 40, "top": 72, "bottom": 40 },
    "xAxis": { "type": "category", "data": ["4-1", "4-2"] },
    "yAxis": { "type": "value" },
    "series": [{ "type": "line", "smooth": true, "data": [0, 1] }]
  }
}
```
````

The fenced block content MUST be strict JSON parseable by `JSON.parse`:

- Use double-quoted strings only.
- Do not use JavaScript functions, comments, trailing commas, `undefined`, `NaN`, or `Infinity`.
- Use ECharts string templates such as `"formatter": "{b}: {c}"` instead of callback functions.
- For conditional colors or labels, precompute per-data-item objects instead of using JavaScript functions.

### 4. Result Return
Return the Markdown chart block with a short interpretation of the key insight. If the user explicitly asks for a downloadable chart artifact, also write a descriptive `.echarts.json` file such as `rainfall-trend.echarts.json` to `/mnt/user-data/outputs` and call `present_files`.

## Reference Material
The `references/` directory contains legacy chart descriptions. Prefer native ECharts option syntax over those legacy tool payloads.

## License

This `SKILL.md` is provided by [antvis/chart-visualization-skills](https://github.com/antvis/chart-visualization-skills).
Licensed under the [MIT License](https://github.com/antvis/chart-visualization-skills/blob/master/LICENSE).