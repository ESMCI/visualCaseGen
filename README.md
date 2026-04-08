[![DOI](https://joss.theoj.org/papers/10.21105/joss.09130/status.svg)](https://doi.org/10.21105/joss.09130)

# visualCaseGen

Welcome to **visualCaseGen**, an intuitive graphical user interface (GUI) designed to simplify the workflow of creating Community Earth System Model v.3 (CESM3) cases. With visualCaseGen, users can effortlessly explore and define component sets (compsets), select or customize grid resolutions, and prepare their CESM cases, all through an interactive and user-friendly platform that runs on Jupyter notebooks.

## Key Features

- **Guided Configuration**: visualCaseGen guides users through the main steps of configuring CESM cases, ensuring that all necessary components are included while preventing incompatible selections.
  
- **Standard and Custom Options**: Users can choose from predefined standard compsets and grids or create custom configurations tailored to specific modeling needs.

- **Real-Time Compatibility Checks**: As you make selections, visualCaseGen highlights incompatible options, helping you navigate the complexities of model configurations effectively.

- **Easy Navigation**: The tool breaks down the configuration process into three clear stages:
  1. **Compset Selection**: Choose from standard or custom compsets, including all associated models and physics options.
  2. **Grid Configuration**: Select or create grids tailored for your application, ensuring compatibility across individual component grids and compsets.
  3. **Case Launch**: Finalize your configuration and create your CESM case with a few clicks.

## User Manual

For detailed instructions on how to use visualCaseGen, including setup and configuration guidance, please refer to the [User Manual](https://esmci.github.io/visualCaseGen/).

## Citing 

If you use visualCaseGen in your research, please cite it as follows:

Altuntas, A., Simpson, I.R., Bachman, S.D., Venumuddula, M., Levis, S., Dobbins, B., Sacks, W.J. and
Danabasoglu, G., 2026. "visualCaseGen: An SMT-based Experiment Configurator for Community Earth System
Model." Journal of Open Source Software, 11(119), p.9130. doi: [10.21105/joss.09130](https://doi.org/10.21105/joss.09130).

BibTeX entry:

```bibtex
@article{altuntas2026visualcasegen,
  title={visualCaseGen: An SMT-based Experiment Configurator for Community Earth System Model},
  author={Altuntas, Alper and Simpson, Isla R and Bachman, Scott D and Venumuddula, Manish and Levis, Samuel and Dobbins, Brian and Sacks, William J and Danabasoglu, Gokhan},
  journal={Journal of Open Source Software},
  volume={11},
  number={119},
  pages={9130},
  year={2026}
}
```