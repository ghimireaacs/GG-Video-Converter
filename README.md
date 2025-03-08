# Vertical Video Converter 🎥↕️

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-important)](https://ffmpeg.org)

Convert horizontal videos to vertical format (9:16) for social media platforms like TikTok, Instagram Reels, and YouTube Shorts. Built with Python and Tkinter.

![GUI Screenshot](./screenshot/GUI%20Screenshot.png)

## Features ✨

- **Vertical Conversion**: Convert any video to 1080x1920 (9:16) format
- **Batch Processing**: Convert entire folders of videos at once
- **Watermark Support**: Add customizable watermarks with opacity control
- **Quality Presets**: High/Medium/Low encoding options
- **Smart Cropping**: Automatic center cropping with zoom control
- **Cross-Platform**: Windows/macOS/Linux support
- **GUI Interface**: User-friendly graphical interface

## Installation 📦

### Requirements

- Python 3.10+
- FFmpeg (included in repository)
- Tkinter (usually included with Python)

```bash
git clone https://github.com/ghimireaacs/GG-Video-Converter.git
cd vertical-video-converter
pip install -r requirements.txt
```

## Usage 🚀

### From Source

```bash
python main.py
```

### Built Executable

```bash
./dist/VerticalVideoConverter
```

## GUI Overview 🖥️

1. **Input/Output Settings**

   - Select single file or folder for batch processing
   - Choose output directory

2. **Conversion Parameters**

   - Quality preset selection (High/Medium/Low)
   - Zoom factor adjustment (1.0-3.0)

3. **Watermark Configuration**

   - Enable/disable watermark
   - Custom watermark image support
   - Opacity control (0.0-1.0)
   - Size adjustment (50-500px)

4. **Progress Tracking**
   - Real-time conversion progress
   - Detailed status updates
   - Error handling with notifications

## Configuration ⚙️

### Directory Structure

```
vertical-video-converter/
├── ffmpeg/          # FFmpeg binaries
├  ├── ffmpeg.exe
├  ├── ffprobe.exe
├── assets/          # Default watermark
├── src/             # Application source code

```

## Build from Source 🔨

Requires PyInstaller:

```bash
pip install pyinstaller
pyinstaller build.spec
```

## Contributing 🤝

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments 🙏

- FFmpeg team for the amazing multimedia framework
- Python community for Tkinter GUI tools
- PyInstaller for packaging support

---

**Note**: This software uses FFmpeg under the LGPLv2.1 license. Please ensure you comply with FFmpeg's licensing requirements when distributing.

```

Key elements included:
1. Badges for quick project status viewing
2. Clear feature highlights with emojis
3. Visual directory structure
4. Detailed build/install instructions
5. Contribution guidelines
6. Licensing information
7. Responsive design elements

To complete the README:
1. Add actual screenshot (replace `screenshot.png`)
2. Update repository URLs
3. Add your license file
4. Customize acknowledgments section
5. Add any additional documentation links

```
