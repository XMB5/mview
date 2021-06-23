import sys
import subprocess
import json


class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    NO_UNDERLINE = '\033[24m'
    FG_RED = '\033[91m'
    FG_GREEN = '\033[92m'
    FG_YELLOW = '\033[93m'
    FG_BLUE = '\033[94m'
    FG_MAGENTA = '\033[95m'
    FG_CYAN = '\033[96m'
    BG_RED = '\033[41m'


def pretty_time(seconds_str):
    # could use -sexagesimal ffprobe command line instead
    # but then we can't format it exactly how we want
    if '.' in seconds_str:
        dot_index = seconds_str.index('.')
        frac_part = int(seconds_str[dot_index + 1:])  # microseconds
        whole_part = int(seconds_str[:dot_index])
    else:
        frac_part = 0
        whole_part = int(seconds_str)

    seconds = whole_part % 60
    minutes = (whole_part // 60) % 60
    hours = whole_part // 3600

    return f'{hours:02}:{minutes:02}:{seconds:02}.{frac_part:06}'


def pretty_size(byte_size_str):
    byte_size = int(byte_size_str)
    bytes_units = [
        (1024 ** 3, 'GiB'),
        (1024 ** 2, 'MiB'),
        (1024, 'KiB')
    ]
    for unit_size, unit_suffix in bytes_units:
        if byte_size > unit_size:
            return f'{(byte_size / unit_size):.2f} {unit_suffix}'
    return f'{byte_size} bytes'


def pretty_framerate(framerate):
    if '/' in framerate:
        slash_index = framerate.index('/')
        numerator = int(framerate[:slash_index])
        denominator = int(framerate[slash_index + 1:])
        if numerator == 0 and denominator == 0:
            return None
        elif numerator == 24000 and denominator == 1001:
            return '23.976'
        elif numerator == 30000 and denominator == 1001:
            return '29.97'
        elif numerator == 60000 and denominator == 1001:
            return '59.94'
        else:
            return f'{(numerator/denominator):g}'
    else:
        return framerate


def pretty_bitrate(bitrate_str):
    bitrate = int(bitrate_str)
    bitrate_units = [
        (1024**2, 'mbps'),
        (1024, 'kbps')
    ]
    for unit_size, unit_suffix in bitrate_units:
        if bitrate > unit_size:
            return f'{(bitrate / unit_size):.2f} {unit_suffix}'
    return f'{bitrate} bps'


def ffprobe(media_file):
    result = subprocess.run(['ffprobe',
                             '-v', 'fatal',
                             '-print_format', 'json',
                             '-show_entries', 'format:stream:chapters',
                             '--',
                             media_file], capture_output=True, encoding='utf8', timeout=15)
    if result.returncode != 0 or len(result.stderr) > 0:
        raise IOError(f'exit code {result.returncode}: {result.stderr}')

    return json.loads(result.stdout)


def process_file(media_file):
    filename = media_file[media_file.rindex('/') + 1:] if '/' in media_file else media_file
    print(f'{Colors.FG_RED}{Colors.BOLD}{Colors.UNDERLINE}{filename}{Colors.RESET}')

    ffprobe_output = ffprobe(media_file)
    duration = pretty_time(ffprobe_output['format']['duration'])
    size = pretty_size(ffprobe_output['format']['size'])
    bitrate = pretty_bitrate(ffprobe_output['format']['bit_rate'])
    print(f'{Colors.FG_GREEN}{duration} | {size} | {bitrate}{Colors.RESET}')

    if len(ffprobe_output['chapters']) > 0:
        print(Colors.FG_BLUE, end='')
        for i, chapter in enumerate(ffprobe_output['chapters']):
            start_time = chapter['start_time'].rstrip('0').rstrip('.')
            title = chapter['tags']['title']
            if i > 0:
                print(' - ', end='')
            print(f'{title} {start_time}', end='')
        print(Colors.RESET)

    for stream in ffprobe_output['streams']:
        stream_index = stream['index']
        codec_type = stream['codec_type']
        codec_name = stream['codec_name']

        if codec_type == 'video':
            width = stream['width']
            height = stream['height']
            framerate = pretty_framerate(stream['avg_frame_rate'])
            whf = f'{width}x{height}@{framerate}' if framerate is not None else f'{width}x{height} static'
            interlaced = 'field_order' in stream and stream['field_order'] != 'progressive'
            pix_fmt = stream['pix_fmt']
            bit_depth = stream.get('bits_per_raw_sample')
            bit_depth_text = f' {bit_depth}bit' if bit_depth else ''
            print(f'{Colors.FG_CYAN}{stream_index}) {codec_name} {whf}{" interlaced" if interlaced else ""} {pix_fmt}{bit_depth_text}{Colors.RESET}')

        elif codec_type == 'audio' or codec_type == 'subtitle':
            infos = []
            if 'language' in stream['tags']:
                infos.append(stream['tags']['language'])
            if 'title' in stream['tags']:
                infos.append(stream['tags']['title'])
            if len(infos) > 0:
                info_text = ' | ' + ' - '.join(infos)
            else:
                info_text = ''
            color = Colors.FG_MAGENTA if codec_type == 'audio' else Colors.FG_YELLOW
            channel_layout_addition = (' ' + stream['channel_layout']) if 'channel_layout' in stream else ''
            print(f'{color}{stream_index}) {codec_name}{channel_layout_addition}{info_text}{Colors.RESET}')

        else:
            print(f'{Colors.BG_RED}{stream_index}) (unknown codec type {codec_type}){Colors.RESET}')


def main():
    media_files = sys.argv[1:]
    if len(media_files) == 0:
        sys.exit('missing media files')
    else:
        for media_file in media_files:
            process_file(media_file)


if __name__ == '__main__':
    main()


