ydl_opts = {
    "format": "bestaudio/best",
    "extract_flat": True,
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }
    ]
}