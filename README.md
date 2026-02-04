# PhenoLIP Project Page

Project webpage for the CVPR 2026 paper:

**PhenoLIP: Integrating Phenotype Ontology Knowledge into Medical Vision–Language Pretraining**

*Ziqing Fan, Cheng Liang, Chaoyi Wu, Ya Zhang, Yanfeng Wang, Weidi Xie*

## Quick Start

### View Locally

Simply open `index.html` in your web browser:
```bash
open index.html  # macOS
xdg-open index.html  # Linux
start index.html  # Windows
```

Or use a local web server:
```bash
python -m http.server 8000
# Then visit http://localhost:8000
```

### Deploy to GitHub Pages

1. Create a new GitHub repository (e.g., `phenolip-webpage`)

2. Push this directory to GitHub:
```bash
git init
git add .
git commit -m "Initial commit: PhenoLIP project webpage

Co-Authored-By: Warp <agent@warp.dev>"
git remote add origin https://github.com/YOUR_USERNAME/phenolip-webpage.git
git branch -M main
git push -u origin main
```

3. Enable GitHub Pages:
   - Go to repository Settings → Pages
   - Source: Deploy from a branch
   - Branch: main → /(root)
   - Click Save

4. Your website will be available at:
   ```
   https://YOUR_USERNAME.github.io/phenolip-webpage/
   ```

## Structure

```
phenolip-webpage/
├── index.html          # Main webpage
├── resources/          # Images and assets
│   ├── overview.png    # Main overview figure
│   ├── pipeline.png    # Method pipeline diagram
│   ├── bibtex.txt      # BibTeX citation
│   └── *.png           # Additional figures
└── README.md           # This file
```

## Updating Content

### Update Links

When your paper/dataset/demo links are available, update the following sections in `index.html`:

- Line 222: `<a href='#'>[Paper]</a>` → Replace `#` with paper URL
- Line 232: `<a href='#'>[Dataset]</a>` → Replace `#` with dataset URL
- Line 237: `<a href='#'>[Demo]</a>` → Replace `#` with demo URL
- Line 545: `<a href="#">[Paper]</a>` → Replace `#` with paper URL

### Update Images

Place new images in the `resources/` directory and reference them in `index.html`:
```html
<img src="./resources/your-image.png"/>
```

## Key Metrics Displayed

- 524K+ image-text pairs
- 3,000+ phenotypes
- 7,800+ benchmark pairs
- 36.56% zero-shot accuracy
- +8.85% improvement over BiomedCLIP
- +15.03% improvement over BIOMEDICA

## Citation

If you use this webpage template or find PhenoLIP useful, please cite:

```bibtex
@inproceedings{fan2026phenolip,
  title={PhenoLIP: Integrating Phenotype Ontology Knowledge into Medical Vision--Language Pretraining},
  author={Fan, Ziqing and Liang, Cheng and Wu, Chaoyi and Zhang, Ya and Wang, Yanfeng and Xie, Weidi},
  booktitle={Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)},
  year={2026}
}
```

## License

The webpage template is based on the [webpage-template](https://github.com/richzhang/webpage-template) by Phillip Isola and Richard Zhang.