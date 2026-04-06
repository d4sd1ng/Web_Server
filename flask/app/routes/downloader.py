from flask import Blueprint, render_template, request, jsonify
import os
import subprocess
from yt_dlp import YoutubeDL
import shutil
import re
from mutagen.easyid3 import EasyID3

downloader_bp = Blueprint('downloader', __name__)

LOCAL_BASE_PATH = "/media"
SMB_SERVER = "192.168.1.10"
SMB_SHARE = "shared"
SMB_USER = "user"
SMB_PASSWORD = "password"
NFS_SERVER = "192.168.1.20"
NFS_SHARE = "/exported"

def sanitize_filename(filename):
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    sanitized = sanitized[:255]
    return sanitized

def rename_audio_file(filepath, destination):
    try:
        audio = EasyID3(filepath)
        artist = audio.get('artist', ['Unknown Artist'])[0]
        album = audio.get('album', ['Unknown Album'])[0]
        title = audio.get('title', ['Unknown Title'])[0]
        new_filename = f"{artist} - {album} - {title}.mp3" if album != 'Unknown Album' else f"{artist} - {title}.mp3"
        new_filename = sanitize_filename(new_filename)
        new_filepath = os.path.join(destination, new_filename)
        shutil.move(filepath, new_filepath)
        return new_filepath
    except Exception as e:
        print(f"Error renaming audio file: {e}")
        return filepath

def rename_video_file(filepath, destination):
    filename = os.path.basename(filepath)
    sanitized_filename = sanitize_filename(filename)
    new_filepath = os.path.join(destination, sanitized_filename)
    shutil.move(filepath, new_filepath)
    return new_filepath

def get_existing_directories(base_path):
    return [os.path.join(base_path, name) for name in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, name))]

def get_smb_directories():
    try:
        smb_cmd = f"smbclient -U {SMB_USER}%{SMB_PASSWORD} -L {SMB_SERVER} -g"
        result = subprocess.check_output(smb_cmd, shell=True).decode('utf-8')
        directories = []
        for line in result.split('\n'):
            if "Disk|" in line:
                directories.append(line.split('|')[1])
        return directories
    except Exception as e:
        print(f"Error listing SMB directories: {e}")
        return []

def get_nfs_directories():
    try:
        nfs_cmd = f"showmount -e {NFS_SERVER}"
        result = subprocess.check_output(nfs_cmd, shell=True).decode('utf-8')
        directories = []
        for line in result.split('\n'):
            if line.startswith(NFS_SHARE):
                directories.append(line.split()[0])
        return directories
    except Exception as e:
        print(f"Error listing NFS directories: {e}")
        return []

@downloader_bp.route('/downloader', methods=['GET'])
def downloader_page():
    local_directories = get_existing_directories(LOCAL_BASE_PATH)
    smb_directories = get_smb_directories()
    nfs_directories = get_nfs_directories()
    directories = local_directories + smb_directories + nfs_directories
    return render_template('downloader.html', directories=directories)

@downloader_bp.route('/downloader/download', methods=['POST'])
def download_media():
    urls = request.form.get('urls')
    destination = request.form.get('destination')

    if not urls:
        return jsonify({"error": "URLs fehlen"}), 400

    if not destination:
        return jsonify({"error": "Zielverzeichnis fehlt"}), 400

    destination_path = os.path.join(LOCAL_BASE_PATH, destination)
    if not os.path.exists(destination_path):
        return jsonify({"error": f"Zielverzeichnis '{destination_path}' existiert nicht"}), 400

    output_template = os.path.join(destination_path, '%(title)s.%(ext)s')

    def postprocessor_hook(d):
        if d['status'] == 'finished':
            filename = d['info_dict']['_filename']
            if 'audio' in d['info_dict']['acodec']:
                new_filepath = rename_audio_file(filename, destination_path)
            else:
                new_filepath = rename_video_file(filename, destination_path)

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'postprocessor_hooks': [postprocessor_hook]
    }

    url_list = urls.splitlines()

    try:
        for url in url_list:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
        return jsonify({"message": "Downloads abgeschlossen"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
