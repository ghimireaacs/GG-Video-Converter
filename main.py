import os
import sys
import subprocess
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from threading import Thread

# ----- Configuration -----
APP_NAME = "Ghost Gaming Vertical Video Converter"
VERSION = "1.2.0"
DEFAULT_WATERMARK = "default_watermark.png"
SUPPORTED_FORMATS = ['.mp4', '.mov', '.avi', '.mkv', '.wmv']
FFMPEG_TIMEOUT = 600  # 10 minutes

# ----- META DATA -----

# ----- Logging Setup -----
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("converter.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(APP_NAME)

# ----- Exception Classes -----
class ConversionError(Exception):
    """Base conversion error class"""

class FFmpegNotFoundError(ConversionError):
    """Raised when FFmpeg binaries are missing"""

class InvalidInputError(ConversionError):
    """Raised for invalid input files"""

class ConversionTimeoutError(ConversionError):
    """Raised when conversion times out"""

# ----- Utility Functions -----
def get_resource_path(*path_parts):
    """Get path to bundled resources with proper handling"""
    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, *path_parts)
    except Exception as e:
        logger.error(f"Resource path error: {str(e)}")
        raise

def safe_path(path):
    """Normalize path without adding quotes"""
    return os.path.normpath(path)

def validate_path(path, is_file=False):
    """Validate input path existence and permissions"""
    if not path:
        raise InvalidInputError("No path specified")
    
    clean_path = os.path.normpath(path)
    if not os.path.exists(clean_path):
        raise InvalidInputError(f"Path does not exist: {clean_path}")
    
    if is_file and not os.path.isfile(clean_path):
        raise InvalidInputError(f"Not a file: {clean_path}")
    
    if not os.access(clean_path, os.R_OK):
        raise InvalidInputError(f"Read permission denied: {clean_path}")

# ----- Core Converter Class -----
class VideoConverter:
    QUALITY_PRESETS = {
        'high': {'preset': 'slow', 'crf': '18', 'video_bitrate': '5M', 'audio_bitrate': '320k'},
        'medium': {'preset': 'medium', 'crf': '23', 'video_bitrate': '2M', 'audio_bitrate': '192k'},
        'low': {'preset': 'faster', 'crf': '28', 'video_bitrate': '1M', 'audio_bitrate': '128k'}
    }

    def __init__(self):
        self.ffmpeg, self.ffprobe = self._find_ffmpeg()
        self._cancelled = False

    def _find_ffmpeg(self):
        """Locate FFmpeg binaries with validation"""
        try:
            ffmpeg_path = get_resource_path('ffmpeg', 'ffmpeg.exe')
            ffprobe_path = get_resource_path('ffmpeg', 'ffprobe.exe')

            ffmpeg_path = os.path.normpath(ffmpeg_path)
            ffprobe_path = os.path.normpath(ffprobe_path)

            if not all(os.path.exists(p) for p in [ffmpeg_path, ffprobe_path]):
                raise FFmpegNotFoundError("FFmpeg binaries not found")

            return ffmpeg_path, ffprobe_path
        except Exception as e:
            logger.error(f"FFmpeg location error: {str(e)}")
            raise

    def convert(self, input_path, output_path, quality='high', zoom=1.0, watermark=None, opacity=0.7, wm_width=150, wm_height=150):
        """Main conversion method"""
        self._cancelled = False
        try:
             # Validate watermark dimensions first
            try:
                wm_width = int(wm_width)
                wm_height = int(wm_height)
                if wm_width < 10 or wm_height < 10:
                    raise ValueError
            except ValueError:
                raise ConversionError("Invalid watermark dimensions (min 10x10 pixels)")
            
            # Immediate path validation
            if not os.path.exists(input_path):
                raise InvalidInputError(f"Input file not found: {input_path}")
                
            input_path = safe_path(input_path)
            output_path = safe_path(output_path)
            
            # Rest of the conversion logic remains the same
            self._validate_input(input_path)
            self._create_output_dir(output_path)
            crop_params = self._get_crop_params(input_path, zoom)
            cmd = self._build_command(input_path, output_path, crop_params, quality, watermark, opacity, wm_width, wm_height)
            return self._run_ffmpeg(cmd)
        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}")
            raise
    
    def _validate_input(self, input_path):
        """Validate input file"""
        validate_path(input_path, is_file=True)
        if os.path.getsize(input_path) == 0:
            raise InvalidInputError("Input file is empty")

    def _create_output_dir(self, output_path):
        """Create output directory with validation"""
        output_dir = os.path.dirname(output_path)
        try:
            os.makedirs(output_dir, exist_ok=True)
            if not os.access(output_dir, os.W_OK):
                raise PermissionError(f"Write permission denied: {output_dir}")
        except OSError as e:
            raise ConversionError(f"Failed to create output directory: {str(e)}")

    def _get_crop_params(self, input_path, zoom):
        """Calculate crop parameters using FFprobe"""
        try:
            cmd = [self.ffprobe, '-v', 'error', '-select_streams', 'v:0',
                   '-show_entries', 'stream=width,height', '-of', 'csv=p=0', input_path]
            
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            width, height = map(int, result.stdout.strip().split(','))
            return self._calculate_crop(width, height, zoom)
        except subprocess.CalledProcessError as e:
            raise ConversionError(f"FFprobe error: {e.stderr.strip()}")

    def _calculate_crop(self, width, height, zoom):
        """Calculate crop dimensions and position with validation"""
        try:
            target_ratio = 9/16
            source_ratio = width / height

            if source_ratio > target_ratio:
                crop_w = int(height * target_ratio)
                crop_h = height
                crop_x = (width - crop_w) // 2
                crop_y = 0
            else:
                crop_h = int(width / target_ratio)
                crop_w = width
                crop_x = 0
                crop_y = (height - crop_h) // 2

            if zoom > 1.0:
                crop_w = max(100, int(crop_w / zoom))
                crop_h = max(100, int(crop_h / zoom))
                crop_x = min(max(0, crop_x + (width - crop_w) // 2), width - crop_w)
                crop_y = min(max(0, crop_y + (height - crop_h) // 2), height - crop_h)

            if crop_w <= 0 or crop_h <= 0:
                raise ValueError("Invalid crop dimensions")

            return {'w': crop_w, 'h': crop_h, 'x': crop_x, 'y': crop_y}
        except (ValueError, ZeroDivisionError) as e:
            raise ConversionError(f"Crop calculation error: {str(e)}")

    def _build_command(self, input_path, output_path, crop, quality, 
                  watermark, opacity, wm_width, wm_height):
        """Build FFmpeg command with watermark sizing"""
        preset = self.QUALITY_PRESETS[quality.lower()]
        base_cmd = [
            self.ffmpeg, '-y', '-hide_banner',
            '-i', safe_path(input_path),
            '-vf', f"crop={crop['w']}:{crop['h']}:{crop['x']}:{crop['y']},scale=1080:1920",
            '-c:v', 'libx264',
            '-preset', preset['preset'],
            '-crf', preset['crf'],
            '-maxrate', preset['video_bitrate'],
            '-bufsize', '10M',
            '-pix_fmt', 'yuv420p',
            '-profile:v', 'high',
            '-level', '4.2',
            '-c:a', 'aac',
            '-b:a', preset['audio_bitrate'],
            '-ar', '48000',
            safe_path(output_path)
        ]

        if watermark and os.path.exists(watermark):
            return [
                self.ffmpeg, '-y', '-hide_banner',
                '-i', safe_path(input_path),
                '-i', safe_path(watermark),
                '-filter_complex',
                f"[0:v]crop={crop['w']}:{crop['h']}:{crop['x']}:{crop['y']},"
                f"scale=1080:1920[base];"
                f"[1:v]scale={wm_width}:{wm_height},"
                f"format=rgba,colorchannelmixer=aa={opacity}[wm];"
                f"[base][wm]overlay=main_w-overlay_w-10:main_h-overlay_h-10[outv]",
                '-map', '[outv]',
                '-map', '0:a?',
                '-c:v', 'libx264',
                '-preset', preset['preset'],
                '-crf', preset['crf'],
                '-maxrate', preset['video_bitrate'],
                '-bufsize', '10M',
                '-pix_fmt', 'yuv420p',
                '-profile:v', 'high',
                '-level', '4.2',
                '-c:a', 'aac',
                '-b:a', preset['audio_bitrate'],
                '-ar', '48000',
                safe_path(output_path)
            ]
        
        return base_cmd

    def _run_ffmpeg(self, cmd):
        """Execute FFmpeg command with proper space handling"""
        try:
            logger.debug(f"Executing command: {cmd}")
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=FFMPEG_TIMEOUT,
                check=True  # This will raise error on non-zero return code
            )
            return True
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg Error ({e.returncode}):\n{e.stderr}"
            raise ConversionError(error_msg)
        except Exception as e:
            raise ConversionError(f"Execution failed: {str(e)}")

    def _parse_ffmpeg_error(self, output):
        """Extract relevant error message from FFmpeg output"""
        errors = [line for line in output.split('\n') if 'error' in line.lower()]
        return '\n'.join(errors[-3:]) if errors else "Unknown FFmpeg error"

    def cancel(self):
        """Cancel current conversion"""
        self._cancelled = True

# ----- GUI Application -----
class ConverterApp:
    def __init__(self, root):
        self.root = root
        self.converter = None
        self.current_task = None
        self.watermark_path = None
        self._initialize_resources()
        self.setup_gui()
        self.setup_styles()

    def _initialize_resources(self):
        """Verify and initialize required resources"""
        try:
            self.converter = VideoConverter()
            self._verify_default_watermark()
        except FFmpegNotFoundError as e:
            messagebox.showerror("Critical Error", str(e))
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Failed to initialize: {str(e)}")
            self.root.destroy()

    def _verify_default_watermark(self):
        """Check if default watermark exists"""
        default_wm = get_resource_path('assets', DEFAULT_WATERMARK)
        if not os.path.exists(default_wm):
            messagebox.showwarning("Missing Default Watermark",
                f"Default watermark not found at:\n{default_wm}\n"
                "You can still use custom watermarks.")

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.configure('TFrame', padding=5)
        self.style.configure('TButton', padding=5)
        self.style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        self.root.geometry("680x520")

    def setup_gui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Input Section
        input_frame = ttk.LabelFrame(main_frame, text="Input Settings")
        input_frame.grid(row=0, column=0, columnspan=3, sticky='ew', pady=5)

        ttk.Label(input_frame, text="Source:").grid(row=0, column=0, padx=5, sticky='w')
        self.input_entry = ttk.Entry(input_frame, width=50)
        self.input_entry.grid(row=0, column=1, padx=5)
        ttk.Button(input_frame, text="File", command=self.browse_file).grid(row=0, column=2, padx=5)
        ttk.Button(input_frame, text="Folder", command=self.browse_folder).grid(row=0, column=3, padx=5)

        # Output Section
        output_frame = ttk.LabelFrame(main_frame, text="Output Settings")
        output_frame.grid(row=1, column=0, columnspan=3, sticky='ew', pady=5)

        ttk.Label(output_frame, text="Destination:").grid(row=0, column=0, padx=5, sticky='w')
        self.output_entry = ttk.Entry(output_frame, width=50)
        self.output_entry.grid(row=0, column=1, padx=5)
        ttk.Button(output_frame, text="Browse", command=self.browse_output).grid(row=0, column=2, padx=5)

        # Settings Section
        settings_frame = ttk.LabelFrame(main_frame, text="Conversion Settings")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky='ew', pady=5)

        ttk.Label(settings_frame, text="Quality:").grid(row=0, column=0, padx=5, sticky='w')
        self.quality_var = tk.StringVar(value='high')
        ttk.Combobox(settings_frame, textvariable=self.quality_var, 
                    values=['high', 'medium', 'low'], width=8).grid(row=0, column=1, padx=5)

        ttk.Label(settings_frame, text="Zoom:").grid(row=0, column=2, padx=5)
        self.zoom_var = tk.DoubleVar(value=1.0)
        ttk.Spinbox(settings_frame, from_=1.0, to=3.0, increment=0.1,
                   textvariable=self.zoom_var, width=4).grid(row=0, column=3, padx=5)

        # Watermark Section
        watermark_frame = ttk.LabelFrame(main_frame, text="Watermark Settings")
        watermark_frame.grid(row=3, column=0, columnspan=3, sticky='ew', pady=5)

        self.wm_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(watermark_frame, text="Enable", variable=self.wm_var,
                    command=self.toggle_watermark).grid(row=0, column=0, padx=5)

        ttk.Button(watermark_frame, text="Select", command=self.browse_watermark).grid(row=0, column=1, padx=5)

        # Add width and height controls
        ttk.Label(watermark_frame, text="Width:").grid(row=0, column=2, padx=5)
        self.wm_width = ttk.Spinbox(watermark_frame, from_=50, to=500, width=5)
        self.wm_width.set(150)  # Default width
        self.wm_width.grid(row=0, column=3, padx=5)

        ttk.Label(watermark_frame, text="Height:").grid(row=0, column=4, padx=5)
        self.wm_height = ttk.Spinbox(watermark_frame, from_=50, to=500, width=5)
        self.wm_height.set(150)  # Default height
        self.wm_height.grid(row=0, column=5, padx=5)

        ttk.Label(watermark_frame, text="Opacity:").grid(row=0, column=6, padx=5)
        self.wm_opacity = ttk.Scale(watermark_frame, from_=0.0, to=1.0, value=0.7)
        self.wm_opacity.grid(row=0, column=7, padx=5, sticky='ew')
        # Progress Section
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=4, column=0, columnspan=3, sticky='ew', pady=10)

        self.progress = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate')
        self.progress.pack(fill=tk.X, expand=True)
        self.status = ttk.Label(progress_frame, text="Ready", anchor=tk.W)
        self.status.pack(fill=tk.X)

        # Control Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=10)

        ttk.Button(btn_frame, text="Convert", command=self.start_conversion).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.cancel_conversion).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Exit", command=self.root.destroy).pack(side=tk.RIGHT, padx=5)

    def browse_file(self):
        """Handle file selection with instant validation"""
        path = filedialog.askopenfilename(filetypes=[("Video Files", " ".join(SUPPORTED_FORMATS))])
        if path:
            clean_path = safe_path(path)
            if not os.path.exists(clean_path):
                messagebox.showerror("Error", "Selected file does not exist!")
                return
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, clean_path)

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, os.path.normpath(path))

    def browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, os.path.normpath(path))

    def browse_watermark(self):
        """Handle watermark selection with validation"""
        path = filedialog.askopenfilename(
            filetypes=[("PNG Files", "*.png"), ("JPEG Files", "*.jpg *.jpeg")]
        )
        if path:
            clean_path = os.path.normpath(path)
            if not clean_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                messagebox.showerror("Error", "Watermark must be PNG or JPEG")
                return
            if not os.path.exists(clean_path):
                messagebox.showerror("Error", "Selected watermark file not found")
                return
            self.wm_var.set(True)
            self.watermark_path = clean_path
            self.toggle_watermark()

    def toggle_watermark(self):
        state = 'normal' if self.wm_var.get() else 'disabled'
        for child in self.watermark_frame.winfo_children()[1:]:
            child.configure(state=state)

    def start_conversion(self):
        if self.current_task and self.current_task.is_alive():
            return

        input_path = self.input_entry.get()
        output_dir = self.output_entry.get()
        params = {
            'quality': self.quality_var.get(),
            'zoom': self.zoom_var.get(),
            'watermark': self._get_watermark_path(),
            'opacity': self.wm_opacity.get(),
            'wm_width': self.wm_width.get(),
            'wm_height': self.wm_height.get()
        }

        try:
            validate_path(input_path)
            validate_path(output_dir)
        except InvalidInputError as e:
            messagebox.showerror("Error", str(e))
            return

        self.current_task = Thread(target=self.run_conversion, args=(input_path, output_dir, params))
        self.current_task.start()

    def _get_watermark_path(self):
        """Get validated watermark path with error handling"""
        if not self.wm_var.get():
            return None

        # Use custom watermark if selected
        if self.watermark_path:
            if os.path.exists(self.watermark_path):
                return safe_path(self.watermark_path)
            messagebox.showerror("Error", "Custom watermark file not found!")
            return None

        # Fallback to default watermark
        default_wm = get_resource_path('assets', DEFAULT_WATERMARK)
        default_wm = os.path.normpath(default_wm)
        
        if os.path.exists(default_wm):
            return safe_path(default_wm)
        
        messagebox.showerror("Error", "Default watermark not found!")
        return None

    def run_conversion(self, input_path, output_dir, params):
        try:
            if os.path.isfile(input_path):
                output_file = os.path.join(output_dir, f"vertical_{os.path.basename(input_path)}")
                self.converter.convert(input_path, output_file, **params)
                self.update_status("Conversion complete!")
            else:
                self.convert_batch(input_path, output_dir, params)
        except ConversionError as e:
            self.show_error(str(e))
        finally:
            self.progress['value'] = 0

    def convert_batch(self, input_dir, output_dir, params):
        video_files = []
        for ext in SUPPORTED_FORMATS:
            video_files.extend(Path(input_dir).glob(f"*{ext}"))
            video_files.extend(Path(input_dir).glob(f"*{ext.upper()}"))

        total = len(video_files)
        for idx, video in enumerate(video_files):
            output_path = os.path.join(output_dir, f"vertical_{video.name}")
            try:
                self.update_status(f"Processing {idx+1}/{total}: {video.name}")
                self.converter.convert(str(video), output_path, **params)
                self.progress['value'] = (idx + 1) / total * 100
            except ConversionError as e:
                logger.error(f"Failed to convert {video}: {str(e)}")

        self.update_status(f"Completed {len(video_files)} conversions")

    def cancel_conversion(self):
        if self.converter:
            self.converter.cancel()
        self.update_status("Conversion cancelled")

    def update_status(self, message):
        self.status.config(text=message)
        self.root.update_idletasks()

    def show_error(self, message):
        messagebox.showerror("Conversion Error", message)

if __name__ == "__main__":
    root = tk.Tk()
    root.title(f"{APP_NAME} v{VERSION}")
    app = ConverterApp(root)
    root.mainloop()