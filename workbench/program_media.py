"""Inspect local media and export bounded excerpts with the native FFmpeg tools."""
from __future__ import annotations

import math
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

from . import edit_storage, files_service, record_io


INSPECT = 'programs.media.inspect'
CLIP = 'programs.media.clip'
PATH = {'type': 'string', 'minLength': 1, 'maxLength': 1000}
MAX_SOURCE_BYTES = 256 * 1024**2
MAX_CLIP_BYTES = 24 * 1024**2
MAX_DURATION = 30
MAX_PIXELS = 4096 * 4096
FORMATS = {'.wav': 'wav', '.flac': 'flac', '.mp3': 'mp3', '.mp4': 'mov', '.m4a': 'mov'}
FIELDS = {
    INSPECT: ({'path': PATH}, ['path']),
    CLIP: ({
        'path': PATH,
        'expected_sha256': {'type': 'string', 'minLength': 64, 'maxLength': 64},
        'start_seconds': {'type': 'number', 'minimum': 0, 'maximum': 86400},
        'duration_seconds': {'type': 'number', 'minimum': 0.25, 'maximum': MAX_DURATION},
        'destination': PATH,
    }, ['path', 'expected_sha256', 'start_seconds', 'duration_seconds', 'destination']),
}
SCOPES = {INSPECT: 'read', CLIP: 'approve'}
AUDIO_CODECS = ('aac', 'alac', 'flac', 'mp3', 'mp3float', 'opus', 'pcm_u8', 'pcm_s16le', 'pcm_s24le',
                'pcm_s32le', 'pcm_f32le', 'pcm_f64le')
VIDEO_CODECS = ('h264', 'hevc', 'mpeg4', 'av1', 'vp9')
CODECS = ','.join(AUDIO_CODECS + VIDEO_CODECS + ('mjpeg', 'png'))  # cover art can be probed


def _input(demuxer):
    # fd: reads the regular file already opened by Graphite. It stays seekable
    # and the subprocess never receives its path or access to other protocols.
    args = [
        '-protocol_whitelist', 'fd', '-format_whitelist', demuxer,
        '-codec_whitelist', CODECS, '-max_streams', '16',
        '-probesize', '4194304', '-analyzeduration', '4000000', '-f', demuxer,
    ]
    if demuxer == 'mov':
        args.extend(['-enable_drefs', '0', '-use_absolute_path', '0'])
    return args


def _duration(value):
    if value is None or value == 'N/A':
        return None
    try:
        duration = float(value)
    except (ValueError, TypeError):
        return None
    return duration if math.isfinite(duration) and duration > 0 else None


def _probe(executable, source, demuxer):
    os.lseek(source, 0, os.SEEK_SET)
    command = [
        executable, '-v', 'error', '-max_alloc', '67108864', *_input(demuxer),
        '-max_pixels', str(MAX_PIXELS),
        '-show_entries', 'format=duration:stream=index,codec_name,codec_type,width,height,channels,sample_rate'
                         ':stream_disposition=attached_pic',
        '-of', 'json', '-i', 'fd:',
    ]
    try:
        result = subprocess.run(command, stdin=source, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                check=True, timeout=5)
    except subprocess.TimeoutExpired as error:
        raise ValueError('Media inspection timed out.') from error
    except subprocess.CalledProcessError as error:
        raise ValueError('FFprobe could not read this format or codec with the installed runtime.') from error
    value = record_io.strict_json(result.stdout)
    streams = []
    for stream in value.get('streams', ()):
        kind = stream.get('codec_type')
        if kind not in ('audio', 'video') or stream.get('disposition', {}).get('attached_pic'):
            continue
        item = {'index': stream['index'], 'kind': kind, 'codec': stream.get('codec_name', 'unknown')}
        if kind == 'video':
            item.update(width=stream.get('width'), height=stream.get('height'))
        else:
            rate = stream.get('sample_rate', '')
            item.update(sample_rate=int(rate) if rate.isdecimal() else None, channels=stream.get('channels'))
        streams.append(item)
    return _duration(value.get('format', {}).get('duration')), streams


def _selected(streams):
    video = next((stream for stream in streams if stream['kind'] == 'video'), None)
    audio = next((stream for stream in streams if stream['kind'] == 'audio'), None)
    return video, audio


def _clip_reason(ffmpeg, duration, video, audio):
    if not ffmpeg:
        return 'Install FFmpeg to export excerpts.'
    if not duration or duration < 0.25:
        return 'The source needs a known duration of at least 0.25 seconds.'
    if not video and not audio:
        return 'The source has no readable audio or video stream.'
    if video:
        width, height = video.get('width') or 0, video.get('height') or 0
        if width < 2 or height < 2 or width > 8192 or height > 8192 or width * height > MAX_PIXELS:
            return 'This video exceeds the excerpt dimension limits.'
        if video['codec'] not in VIDEO_CODECS:
            return 'The video codec is outside the excerpt profile.'
    if audio and audio['codec'] not in AUDIO_CODECS:
        return 'The audio codec is outside the excerpt profile.'
    return ''


def _transcode(ffmpeg, source, target, demuxer, video, audio, start, duration):
    os.lseek(source, 0, os.SEEK_SET)
    command = [
        ffmpeg, '-v', 'error', '-nostdin', '-y', '-xerror', '-max_alloc', '67108864',
        *_input(demuxer), '-max_pixels', str(MAX_PIXELS), '-threads', '2',
        '-ss', f'{start:.6f}', '-i', 'fd:', '-t', f'{duration:.6f}', '-map_metadata', '-1', '-map_chapters', '-1',
    ]
    if video:
        command += [
            '-map', f"0:{video['index']}", '-filter_threads', '1',
            '-vf', r'scale=w=min(1280\,iw):h=min(720\,ih):force_original_aspect_ratio=decrease:force_divisible_by=2,fps=30',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', '-threads:v', '2',
        ]
    if audio:
        command += ['-map', f"0:{audio['index']}", '-c:a', 'aac' if video else 'pcm_s16le', '-ar', '48000', '-ac', '2']
    command += ['-fs', str(MAX_CLIP_BYTES), '-f', 'mp4' if video else 'wav', 'fd:']
    try:
        subprocess.run(command, stdin=source, stdout=target, stderr=subprocess.DEVNULL, check=True, timeout=15)
    except subprocess.TimeoutExpired as error:
        raise ValueError('Excerpt encoding exceeded its time budget.') from error
    except subprocess.CalledProcessError as error:
        raise ValueError('FFmpeg could not encode the excerpt with the installed runtime.') from error


def _file_identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _same_source(base, name, source, original):
    with edit_storage.parent(base, name) as (folder, leaf):
        current = os.stat(leaf, dir_fd=folder, follow_symlinks=False)
    if _file_identity(os.fstat(source)) != original or _file_identity(current) != original:
        raise ValueError('The selected media changed. Inspect it again.')


def _export(base, destination, source, verify_source, probe, ffmpeg, demuxer, video, audio, start, span):
    suffix = '.mp4' if video else '.wav'
    path = record_io.project_path(base, destination, must_exist=False)
    if path.suffix.lower() != suffix:
        raise ValueError(f'Choose a new {suffix} file inside Files.')
    with edit_storage.parent(base, destination) as (folder, name):
        try:
            os.stat(name, dir_fd=folder, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError('Choose a fresh Files path for the excerpt.')
        temporary = f'.graphite-media-{uuid4().hex}'
        fd = os.open(temporary, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder)
        try:
            _transcode(ffmpeg, source, fd, demuxer, video, audio, start, span)
            os.fsync(fd)
            os.lseek(fd, 0, os.SEEK_SET)
            output = edit_storage.fingerprint_fd(fd, maximum=MAX_CLIP_BYTES)
            measured, streams = _probe(probe, fd, FORMATS[suffix])
            output_video, output_audio = _selected(streams)
            if (measured is None or abs(measured - span) > 0.15 or
                    bool(output_video) != bool(video) or bool(output_audio) != bool(audio)):
                raise ValueError('The excerpt failed its duration or stream readback.')
            verify_source()
            with edit_storage.parent(base, destination) as (current_folder, _):
                if not os.path.samestat(os.fstat(folder), os.fstat(current_folder)):
                    raise ValueError('The destination folder changed during excerpt encoding.')
            try:
                os.link(temporary, name, src_dir_fd=folder, dst_dir_fd=folder, follow_symlinks=False)
            except FileExistsError as error:
                raise ValueError('The destination appeared during encoding. Choose a new file name.') from error
            os.fsync(folder)
        finally:
            os.close(fd)
            os.unlink(temporary, dir_fd=folder)
    return {'state': 'EXPORTED', 'path': destination, 'sha256': output['sha256'],
            'bytes': output['bytes'], 'start_seconds': start, 'duration_seconds': measured,
            'requested_duration_seconds': span, 'format': suffix[1:].upper()}


def dispatch(kernel, operation, args, principal):
    if SCOPES[operation] not in principal.scopes:
        raise ValueError('Media Bench operation is outside the authorized scope.')
    base = files_service.root(kernel, create=False).absolute()
    name = args['path']
    path = record_io.project_path(base, name)
    suffix = path.suffix.lower()
    demuxer = FORMATS.get(suffix)
    if demuxer is None:
        raise ValueError('Choose a WAV, FLAC, MP3, MP4, or M4A file from Files.')
    probe, ffmpeg = shutil.which('ffprobe'), shutil.which('ffmpeg')
    with edit_storage.parent(base, name) as (folder, leaf):
        fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder)
        try:
            original = _file_identity(os.fstat(fd))
            identity = edit_storage.fingerprint_fd(fd, maximum=MAX_SOURCE_BYTES)

            def verify_source():
                _same_source(base, name, fd, original)

            verify_source()
            summary = {'path': name, 'sha256': identity['sha256'], 'bytes': identity['bytes'],
                       'format': suffix[1:].upper(), 'tool': {'name': 'FFmpeg', 'available': bool(probe and ffmpeg)}}
            if operation == CLIP and identity['sha256'] != args['expected_sha256']:
                raise ValueError('The selected media changed. Inspect it again.')
            if not probe:
                reason = 'Install FFprobe to inspect audio or video.'
                if operation == CLIP:
                    raise ValueError(reason)
                return {**summary, 'state': 'TOOL_UNAVAILABLE', 'duration_seconds': None, 'streams': [],
                        'clip_ready': False, 'reason': reason}
            duration, streams = _probe(probe, fd, demuxer)
            verify_source()
            video, audio = _selected(streams)
            reason = _clip_reason(ffmpeg, duration, video, audio)
            if operation == INSPECT:
                return {**summary, 'state': 'READY', 'duration_seconds': duration, 'streams': streams,
                        'clip_ready': not reason, 'reason': reason, 'output_suffix': '.mp4' if video else '.wav'}
            if reason:
                raise ValueError(reason)
            start = round(args['start_seconds'], 6)
            span = round(args['duration_seconds'], 6)
            if start + span > duration + 0.000001:
                raise ValueError('The requested excerpt extends beyond the measured source duration.')
            return {**_export(base, args['destination'], fd, verify_source, probe, ffmpeg,
                              demuxer, video, audio, start, span), 'source_sha256': identity['sha256']}
        finally:
            os.close(fd)
