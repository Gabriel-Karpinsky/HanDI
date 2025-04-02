# HanDI

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/Gabriel-Karpinsky/Project-Robots-Everywhere-Group-15">
    <img src="images/logo.png" alt="Logo" width="80" height="80">
  </a>

<h3 align="center">HanDI</h3>

  <p align="center">
    A brief description of what this project does and who it's for.
    <br />
    <a href="https://github.com/Gabriel-Karpinsky/Project-Robots-Everywhere-Group-15"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/Gabriel-Karpinsky/Project-Robots-Everywhere-Group-15">View Demo</a>
    ·
    <a href="https://github.com/Gabriel-Karpinsky/Project-Robots-Everywhere-Group-15/issues">Report Bug</a>
    ·
    <a href="https://github.com/Gabriel-Karpinsky/Project-Robots-Everywhere-Group-15/issues">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

[![Product Name Screen Shot][product-screenshot]](https://example.com)

Provide a brief overview of your project here. Explain what the project is, its purpose, and the problems it aims to solve.

<p align="right">(<a href="#top">back to top</a>)</p>

### Built With

List the major frameworks/libraries used in your project here. For example:

* [Python](https://www.python.org/)
* [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)
* [VCV Rack](https://vcvrack.com/)

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

To set up this project locally, follow these steps.

### Prerequisites

Ensure you have the following installed:

* **Python 3.9 - 3.12**: [Download Python](https://www.python.org/downloads/)
* **loopMIDI**: [Download loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)

### Installation

1. **Clone the repository**:
   ```sh
   git clone https://github.com/Gabriel-Karpinsky/Project-Robots-Everywhere-Group-15.git
   ```
2. **Navigate to the project directory**:
   ```sh
   cd Project-Robots-Everywhere-Group-15
   ```
3. **Create a virtual environment**:
   ```sh
   python -m venv venv
   ```
4. **Activate the virtual environment**:
   - On Windows:
     ```sh
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```sh
     source venv/bin/activate
     ```
5. **Install the required packages**:
   ```sh
   pip install -r requirements.txt
   ```
6. **Set up loopMIDI**:
   - Install loopMIDI from [here](https://www.tobias-erichsen.de/software/loopmidi.html).
   - Open loopMIDI and create a port named "Python to VCV".

7. **Install a MIDI-compatible software**:
   - Use a software of your choice that accepts MIDI input. For example, [VCV Rack](https://vcvrack.com/).

**Note**: If you encounter the following error:

```
DLL load failed while importing _framework_bindings: A dynamic link library (DLL) initialization routine failed.
```

Install the Microsoft Visual C++ runtime:

```sh
pip install msvc-runtime
```

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->
## Usage

Provide instructions and examples on how to use your project. Include screenshots as needed.

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- ROADMAP -->
## Roadmap

Outline the planned features and improvements for the project.

- [x] Feature 1
- [ ] Feature 2
- [ ] Feature 3

See the [open issues](https://github.com/Gabriel-Karpinsky/Project-Robots-Everywhere-Group-15/issues) for a full list of proposed features and known issues.

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would improve this project, please fork the repository and create a pull request. You can also open an issue with the tag "enhancement".

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for 
