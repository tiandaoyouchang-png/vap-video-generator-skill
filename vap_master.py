#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import json
import hashlib

def run_cmd(cmd, cwd=None):
    """Run a command and return its output"""
    print(f"Running command: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(f"Return code: {result.returncode}")
        print(f"Stderr: {result.stderr}")
        print(f"Stdout: {result.stdout}")
        sys.exit(1)
    return result.stdout

def generate_video(input_dir, output_file, fps, bitrate, platform):
    """Generate video based on platform"""
    # Get PNG files
    png_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.png')])
    print(f"Found {len(png_files)} PNG files")
    
    if not png_files:
        print("No PNG files found in input directory")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Check if input files are numbered correctly
    print("Checking input files...")
    for i, png in enumerate(png_files):
        expected_name = f"{i:03d}.png"
        if png != expected_name:
            print(f"Warning: File {png} does not match expected name {expected_name}")
    
    # Get input frame dimensions
    first_png = os.path.join(input_dir, png_files[0])
    cmd = f"ffprobe -v quiet -print_format json -show_streams '{first_png}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        width = data['streams'][0]['width']
        height = data['streams'][0]['height']
        print(f"Input frame dimensions: {width}x{height}")
    else:
        print("Could not get frame dimensions, using default")
        width = 1668
        height = 1112
    
    # Calculate output dimensions based on platform
    if platform == 'bytedance-alpha':
        # For ByteDance Alpha Player: width = input width * 2, height = input height
        output_width = width * 2
        output_height = height
        print(f"Output dimensions for Alpha Player: {output_width}x{output_height}")
    
    # Run the command based on platform
    try:
        if platform == 'tencent-vap':
            # For Tencent VAP: use specified layout
            cmd = f"ffmpeg -framerate {fps} -i '{os.path.join(input_dir, '%03d.png')}' "
            cmd += "-filter_complex '[0:v]split=2[rgb][alpha];[alpha]alphaextract[alpha_only];[rgb]scale=1668:1112[rgb_scaled];[alpha_only]scale=834:556[alpha_scaled];color=black:1680x1680[bg];[bg][rgb_scaled]overlay=0:0[bg_with_rgb];[bg_with_rgb][alpha_scaled]overlay=0:1116[out]' "
            cmd += "-map '[out]' -c:v libx264 -preset ultrafast -crf 35 -b:v 80k -frames:v 46 -y "
            cmd += f"'{output_file}'"
        else:
            # For ByteDance Alpha Player: use 1:1 left-right layout with correct dimensions
            cmd = f"ffmpeg -framerate {fps} -i '{os.path.join(input_dir, '%03d.png')}' "
            cmd += f"-filter_complex '[0:v]split=2[rgb][alpha];[alpha]alphaextract[alpha_only];[rgb]scale={width}:{height}[rgb_scaled];[alpha_only]scale={width}:{height}[alpha_scaled];[rgb_scaled][alpha_scaled]hstack=inputs=2[out]' "
            cmd += "-map '[out]' -c:v libx264 -preset ultrafast -crf 35 -b:v 80k -frames:v 46 -y "
            cmd += f"'{output_file}'"
        
        print(f"Running FFmpeg command...")
        print(f"Input directory: {input_dir}")
        print(f"Output file: {output_file}")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running FFmpeg: {result.stderr}")
            sys.exit(1)
        print("FFmpeg command completed successfully")
    except Exception as e:
        print(f"Exception running FFmpeg: {e}")
        sys.exit(1)

def calculate_md5(file_path):
    """Calculate MD5 hash of a file"""
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b''):
            md5_hash.update(byte_block)
    return md5_hash.hexdigest()

def main():
    parser = argparse.ArgumentParser(description='Generate Tencent VAP or ByteDance Alpha Player MP4 from PNG sequence')
    parser.add_argument('--input', required=True, help='Path to directory containing PNG sequence')
    parser.add_argument('--output', required=True, help='Path where final MP4 will be saved')
    parser.add_argument('--fps', type=int, default=25, help='Frames per second')
    parser.add_argument('--platform', choices=['tencent-vap', 'bytedance-alpha'], default='tencent-vap', help='Platform')
    parser.add_argument('--bitrate', type=int, default=100, help='Encoding bitrate in kbps')
    
    args = parser.parse_args()
    
    # Confirm platform with user
    print(f"Selected platform: {args.platform}")
    if args.platform == 'tencent-vap':
        print("Generating Tencent VAP video with MD5 and JSON metadata...")
    else:
        print("Generating ByteDance Alpha Player video with 1:1 left-right layout...")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate video directly in the target directory
    generate_video(args.input, args.output, args.fps, args.bitrate, args.platform)
    
    # Generate metadata based on platform
    if args.platform == 'tencent-vap':
        # Calculate MD5
        md5_hash = calculate_md5(args.output)
        md5_file = os.path.join(os.path.dirname(args.output), 'md5.txt')
        with open(md5_file, 'w') as f:
            f.write(md5_hash)
        
        # Generate vapc.json (VAP configuration file) with layout information
        vapc_file = os.path.join(os.path.dirname(args.output), 'vapc.json')
        vapc_data = {
            "info": {
                "v": 2,
                "f": 45,  # Number of frames (estimated)
                "w": 1668,  # Input frame width
                "h": 1112,  # Input frame height
                "fps": args.fps,
                "videoW": 1680,  # Output video width
                "videoH": 1680,  # Output video height
                "aFrame": [0, 1116, 834, 556],  # Alpha frame: [x, y, width, height]
                "rgbFrame": [0, 0, 1668, 1112],  # RGB frame: [x, y, width, height]
                "isVapx": 0,
                "orien": 0
            }
        }
        with open(vapc_file, 'w', encoding='utf-8') as f:
            json.dump(vapc_data, f, ensure_ascii=False, indent=2)
        
        print(f"VAP generated successfully: {args.output}")
        print(f"MD5 saved to: {md5_file}")
        print(f"VAPC JSON saved to: {vapc_file}")
    else:
        # For ByteDance Alpha Player, only generate MD5
        md5_hash = calculate_md5(args.output)
        md5_file = os.path.join(os.path.dirname(args.output), 'md5.txt')
        with open(md5_file, 'w') as f:
            f.write(md5_hash)
        
        print(f"ByteDance Alpha Player video generated successfully: {args.output}")
        print(f"MD5 saved to: {md5_file}")

if __name__ == '__main__':
    main()