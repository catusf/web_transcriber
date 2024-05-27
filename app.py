from flask import Flask, render_template, request, redirect, url_for, send_file
import os
import subprocess
import re
import requests
from pytube import YouTube
import speech_recognition as sr

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'files'

def transcribe_audio(file_path):
    recognizer = sr.Recognizer()

    print('Starting transcription')

    # Convert video file to audio file
    audio_file_path = file_path.replace('.mp4', '.wav')
    command = f'ffmpeg -v quiet -y -i "{file_path}" "{audio_file_path}"'
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        return f"Error converting file: {str(e)}", None

    # Transcribe audio
    with sr.AudioFile(audio_file_path) as source:
        audio_data = recognizer.record(source)

    try:
        text = recognizer.recognize_whisper(audio_data)
    except sr.UnknownValueError:
        text = "Could not understand audio"
    except sr.RequestError as e:
        text = "Error with the service: {0}".format(e)

    # Generate .srt file
    srt_filename = generate_srt(text, file_path)

    return text, srt_filename

def generate_srt(transcript, file_path):
    srt_filename = os.path.splitext(file_path)[0] + '.srt'
    srt_content = ''
    counter = 1
    
    print(srt_filename)
    
    lines = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', transcript)

    for i, line in enumerate(lines):
        srt_content += f"{counter}\n"
        counter += 1

        line_time = '00:00:00,000 --> 00:00:10,000\n'  # Example timing, adjust as needed
        srt_content += line_time
        srt_content += f"{line}\n\n"

    with open(srt_filename, 'w', encoding='utf-8') as file:
        file.write(srt_content)

    return srt_filename

def download_file(url, output_path):
    local_filename = os.path.join(output_path, url.split('/')[-1])
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                if chunk:
                    f.write(chunk)
    return local_filename

@app.route('/')
def index():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload():
    file_path = None

    # Check if the request contains a file
    if 'file' in request.files and request.files['file'].filename != '':
        file = request.files['file']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
    
    # Check if the request contains a URL
    if 'youtube_url' in request.form and request.form['youtube_url'] != '':
        url = request.form['youtube_url']
        if "youtube.com" in url or "youtu.be" in url:
            yt = YouTube(url)
            yt.streams.filter(only_audio=True).first().download(output_path=app.config['UPLOAD_FOLDER'])
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], yt.title + '.mp4')
        else:
            file_path = download_file(url, app.config['UPLOAD_FOLDER'])

    # If neither a file nor a URL is provided, redirect back to the form
    if file_path is None:
        return redirect(request.url)

    # Process the file
    transcript, srt_filename = transcribe_audio(file_path)

    # If there's an error in transcription, handle it
    if srt_filename is None:
        return "Error in transcription process."

    # Refresh the list of files and render the template
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('index.html', files=files)

@app.route('/download/<path:filename>')
def download(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

@app.route('/empty', methods=['POST'])
def empty_folder():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    for file_name in files:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)
    return redirect(url_for('index'))

if __name__ == '__main__':
    file_path = '7bdc73aa-cc05-b7e0-6bec-bf9434f4c68c.m4a'
    transcribe_audio(file_path)

    #app.run(debug=True)

